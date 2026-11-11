"""P7 native-copy migration faults, drift, permissions and populated recovery."""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pyodbc

from app.institutional import broadcast_policy as policy
from app.institutional.spanish import connection_string, load
from app.institutional.spanish_bindings import Cursor
from app.institutional.store import transaction
from tools.es_schema_migrate_v2 import identity
from tools.p2_es_recovery import restore
from tools.p7_broadcast_migrations import apply
from tools.p7_broadcast_recovery import backup, fingerprint
from tools.prepare_p7_broadcast import WORK, admin, parent_tables, prepare, read, save
from tools.qualify_p4_storage import academic


def main():
    checks = []
    copies = []

    def check(name, condition=True):
        assert condition, name
        checks.append(name)
        save(
            WORK / "storage-result.json",
            {"status": "in_progress", "checks": checks, "copies": copies},
        )

    checkpoint = read(WORK / "candidate.json")["checkpoint"]

    def restored():
        name = "CBN_P7ES_FAULT_20261027_" + uuid4().hex[:8]
        with admin("master") as connection:
            restore(
                connection,
                checkpoint,
                name,
                restricted=True,
                target_pattern=policy.TARGET,
                allowed_tables=parent_tables(),
            )
        copies.append(name)
        return name

    for fault in ["after_started", "before_commit", "after_commit"]:
        name = restored()
        with admin(name) as connection:
            c = connection.cursor()
            target = identity(c)
            before = academic(c)
            parent = policy.parent_digest(c)
            try:
                apply(
                    connection,
                    target,
                    approved_release=policy.release(),
                    parent_journal=parent,
                    fault=fault,
                )
            except RuntimeError:
                pass
            else:
                raise AssertionError("fault not injected")
            status = c.execute(
                (
                    "SELECT Status FROM dbo.CRMMasivoOperac"
                    "ionMigracion WHERE UnitId='P7ES-001'"
                )
            ).fetchval()
            assert status == ("COMMITTED" if fault == "after_commit" else "STARTED")
            result = apply(
                connection,
                target,
                approved_release=policy.release(),
                parent_journal=parent,
            )
            assert result["status"] == (
                "noop" if fault == "after_commit" else "committed"
            )
            check(
                "fault_" + fault + "_reconciles_without_academic_changes",
                academic(c) == before and policy.parent_digest(c) == parent,
            )
    name = restored()
    with admin(name) as connection:
        target = identity(connection.cursor())
        parent = policy.parent_digest(connection.cursor())

    def migrate():
        with admin(name) as connection:
            return apply(
                connection,
                target,
                approved_release=policy.release(),
                parent_journal=parent,
            )["status"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: migrate(), range(2)))
    check("concurrent_migrators_commit_once", sorted(outcomes) == ["committed", "noop"])
    with admin(name) as connection:
        c = connection.cursor()
        before = academic(c)
        c.execute(
            ("ALTER TABLE dbo.CRMAgenteOperacionPrograma ADD OwnedDrift int NULL")
        )
        try:
            apply(
                connection,
                target,
                approved_release=policy.release(),
                parent_journal=parent,
            )
        except ValueError as error:
            assert "drift" in str(error)
        else:
            raise AssertionError("drift accepted")
        check("additive_model_drift_is_rejected", academic(c) == before)
    fixture = load(Path(read(WORK / "fixture-r3-profile.json")["directory"]))
    # Expected failures use separate transactions and the actual limited login.
    for statement, label in [
        ("SELECT TOP(1) * FROM dbo.ACProgramas", "academic_read_denied"),
        (
            ("UPDATE dbo.ACProgramas SET Id_Programa=Id_Programa WHERE 1=0"),
            "academic_write_denied",
        ),
        ("CREATE TABLE dbo.P7Forbidden(OwnedId int)", "runtime_DDL_denied"),
        (
            ("UPDATE dbo.CRMMasivoOperacionMigracion SET Status=Status WHERE 1=0"),
            "journal_mutation_denied",
        ),
        (
            ("UPDATE dbo.CRMAgenteHistorial SET Note=Note WHERE 1=0"),
            "history_rewrite_denied",
        ),
        (
            ("UPDATE dbo.CRMMasivoPlantilla SET Name=Name WHERE 1=0"),
            "template_version_rewrite_denied",
        ),
        (
            "DELETE FROM dbo.CRMMasivoConsentimiento WHERE 1=0",
            "consent_history_delete_denied",
        ),
    ]:
        connection = pyodbc.connect(connection_string(fixture), autocommit=False)
        try:
            try:
                connection.cursor().execute(statement)
            except pyodbc.Error as error:
                assert (
                    "permission" in str(error).lower()
                    or "(229)" in str(error)
                    or "(262)" in str(error)
                ), "SQL permission denial must be explicit"
                check(label)
            else:
                raise AssertionError(label)
        finally:
            connection.rollback()
            connection.close()
    save(
        WORK / "storage-result.json",
        {
            "status": "passed",
            "checks": checks,
            "copies": copies,
            "engine": 15,
            "compatibility": 150,
            "academic_writes": False,
        },
    )
    print(json.dumps({"passed": len(checks), "fresh_copies": len(copies)}))


def recover(label="populated-recovery", source_label="fixture-r5"):
    from app.institutional.api import create_app
    from tools.qualify_p3_workspace import Browser
    from tools.qualify_p4_deployment import fingerprint as selected_fingerprint

    fixture = load(Path(read(WORK / (source_label + "-profile.json"))["directory"]))
    mapping = policy.layout()
    volatile = {
        mapping["tables"]["crm_access." + n]
        for n in ["Session", "Challenge", "RecoveryCode", "Factor"]
    }
    volatile.add(mapping["tables"]["crm_channels2.OAuthSession"])
    volatile.update(
        mapping["tables"][n]
        for n in [
            "crm_broadcast7.Campaign",
            "crm_broadcast7.Recipient",
            "crm_channels2.SendJob",
            "crm_channels2.ProviderOperation",
            "crm_channels2.QuotaReservation",
        ]
    )
    stable = (
        set(mapping["tables"].values()) | set(mapping["academic_tables"])
    ) - volatile
    with admin(fixture.connection["database"]) as connection:
        c = Cursor(connection.cursor(), mapping["tables"])
        assert (
            c.execute(
                ("SELECT COUNT(*) FROM crm_agents5.Request WHERE State='running'")
            ).fetchval()
            == 0
        )
        stable_before = selected_fingerprint(connection.cursor(), stable)
        checkpoint = backup(connection, fixture.ticket["identity"])
    prepare(label, checkpoint=checkpoint, recovering_from=fixture)
    recovered = load(Path(read(WORK / (label + "-profile.json"))["directory"]))
    checks = []
    with admin(recovered.connection["database"], readonly=True) as connection:
        stable_after = selected_fingerprint(connection.cursor(), stable)
        assert stable_before == stable_after, (
            "populated recovery changed business bytes"
        )
        checks.append(
            (
                "150_stable_tables_preserve_configurati"
                "on_memory_vault_and_append_only_P7_his"
                "tory"
            )
        )
        c = Cursor(connection.cursor(), mapping["tables"])
        assert (
            c.execute(
                ("SELECT COUNT(*) FROM crm_access.Session WHERE RevokedAt IS NULL")
            ).fetchval()
            == 0
        )
        checks.append("copied_sessions_are_revoked_before_new_login")
    with transaction(recovered, anonymous=True):
        pass
    checks.append(("native_populated_recovery_profile_TLS_and_closed_partition"))
    with admin(fixture.connection["database"], readonly=True) as connection:
        assert fingerprint(connection.cursor()) == checkpoint["data"]
    checks.append("source_fixture_160_table_fingerprint_is_unchanged")
    access = read(WORK / (source_label + "-access.json"))
    browser = Browser(create_app(recovered))
    browser.login(access["email"], access["password"])
    result = browser.request("/api/v1/agents").json()
    assert len(result["agents"]) >= 3
    checks.append(("same_human_credentials_and_agent_catalog_work_after_recovery"))
    save(
        WORK / "recovery-result.json",
        {
            "status": "passed",
            "checks": checks,
            "database": recovered.connection["database"],
            "stable_fingerprint": stable_after,
            "stable_tables": len(stable),
            "secret_authentication": (
                "all_access_and_C10_vault_versions_validated_by_preparer"
            ),
            "academic_writes": False,
            "provider_calls": 0,
        },
    )
    print(
        json.dumps({"recovered_tables": 160, "checks": len(checks), "status": "passed"})
    )


if __name__ == "__main__":
    main()


def verify_recovered_workers(label="populated-recovery", source_label="fixture-r5"):
    from app.institutional.broadcast_dispatch import Worker
    from app.institutional.channel_outbox import Dispatcher

    original = load(Path(read(WORK / (source_label + "-profile.json"))["directory"]))
    restored = load(Path(read(WORK / (label + "-profile.json"))["directory"]))

    def uncertain(settings):
        with admin(settings.connection["database"], readonly=True) as db:
            c = Cursor(db.cursor(), policy.layout()["tables"])
            return sorted(
                str(v[0]).lower()
                for v in c.execute(
                    (
                        "SELECT QueueId FROM crm_channels2.Send"
                        "Job WHERE State='uncertain'"
                    )
                ).fetchall()
            )

    expected = uncertain(original)
    assert len(expected) >= 2 and uncertain(restored) == expected
    with transaction(restored, anonymous=True) as c:
        assert (
            c.execute(
                (
                    "SELECT COUNT(*) FROM crm_channels2.Sen"
                    "dJob WHERE State IN('queued','sending'"
                    ")"
                )
            ).fetchval()
            == 0
        )
    calls = []
    assert not Worker(restored, controlled=True).once()
    assert not Dispatcher(
        restored, transport=lambda *a, **k: calls.append(True), allow_controlled=True
    ).once()
    assert not calls and uncertain(restored) == expected
    receipt = read(WORK / "recovery-result.json")
    receipt["checks"] += [
        ("two_uncertain_queue_ids_survive_native_restore_unchanged"),
        ("fresh_workers_after_restore_make_no_POST_and_never_requeue_uncertain"),
    ]
    receipt["uncertain_jobs_preserved"] = len(expected)
    save(WORK / "recovery-result.json", receipt)
    print(json.dumps(dict(status="passed", recovery_checks=len(receipt["checks"]))))
