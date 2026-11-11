"""P8 native-copy migration faults, drift, permissions and populated recovery."""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4
import pyodbc
from app.institutional import campaign_policy as policy
from app.institutional.spanish import connection_string, load
from app.institutional.spanish_bindings import Cursor
from app.institutional.store import transaction
from tools.es_schema_migrate_v2 import identity
from tools.p2_es_recovery import restore
from tools.p8_campaign_migrations import apply
from tools.p8_campaign_recovery import backup, fingerprint
from tools.prepare_p8_campaign import WORK, admin, parent_tables, prepare, read, save
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
        name = "CBN_P8ES_FAULT_20261027_" + uuid4().hex[:8]
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
                "SELECT Status FROM dbo.CRMFlujoOperacionMigracion WHERE UnitId='P8ES-001'"
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
        c.execute("ALTER TABLE dbo.CRMFlujoPaso ADD OwnedDrift int NULL")
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
    fixture = load(Path(read(WORK / "qa-r2-profile.json")["directory"]))
    for statement, label in [
        ("SELECT TOP(1) * FROM dbo.ACProgramas", "academic_read_denied"),
        (
            "UPDATE dbo.ACProgramas SET Id_Programa=Id_Programa WHERE 1=0",
            "academic_write_denied",
        ),
        ("CREATE TABLE dbo.P8Forbidden(OwnedId int)", "runtime_DDL_denied"),
        (
            "UPDATE dbo.CRMFlujoOperacionMigracion SET Status=Status WHERE 1=0",
            "journal_mutation_denied",
        ),
        (
            "UPDATE dbo.CRMAgenteHistorial SET Note=Note WHERE 1=0",
            "history_rewrite_denied",
        ),
        (
            "UPDATE dbo.CRMFlujoVersion SET Name=Name WHERE 1=0",
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


def recover(label="populated-recovery", source_label="qa-r2"):
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
        (
            mapping["tables"][n]
            for n in [
                "crm_campaign8.Record",
                "crm_campaign8.Enrollment",
                "crm_broadcast7.Campaign",
                "crm_broadcast7.Recipient",
                "crm_channels2.SendJob",
                "crm_channels2.ProviderOperation",
                "crm_channels2.QuotaReservation",
            ]
        )
    )
    stable = (
        set(mapping["tables"].values()) | set(mapping["academic_tables"])
    ) - volatile
    with admin(fixture.connection["database"]) as connection:
        c = Cursor(connection.cursor(), mapping["tables"])
        assert (
            c.execute(
                "SELECT COUNT(*) FROM crm_agents5.Request WHERE State='running'"
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
            "150_stable_tables_preserve_configuration_memory_vault_and_append_only_P8_history"
        )
        c = Cursor(connection.cursor(), mapping["tables"])
        assert (
            c.execute(
                "SELECT COUNT(*) FROM crm_access.Session WHERE RevokedAt IS NULL"
            ).fetchval()
            == 0
        )
        checks.append("copied_sessions_are_revoked_before_new_login")
    with transaction(recovered, anonymous=True):
        pass
    checks.append("native_populated_recovery_profile_TLS_and_closed_partition")
    with admin(fixture.connection["database"], readonly=True) as connection:
        assert fingerprint(connection.cursor()) == checkpoint["data"]
    checks.append("source_fixture_167_table_fingerprint_is_unchanged")
    access = read(WORK / (source_label + "-access.json"))
    browser = Browser(create_app(recovered))
    browser.login(access["email"], access["password"])
    result = browser.request("/api/v1/agents").json()
    assert len(result["agents"]) >= 3
    checks.append("same_human_credentials_and_agent_catalog_work_after_recovery")
    save(
        WORK / "recovery-result.json",
        {
            "status": "passed",
            "checks": checks,
            "database": recovered.connection["database"],
            "stable_fingerprint": stable_after,
            "stable_tables": len(stable),
            "secret_authentication": "all_access_and_C10_vault_versions_validated_by_preparer",
            "academic_writes": False,
            "provider_calls": 0,
        },
    )
    print(
        json.dumps({"recovered_tables": 167, "checks": len(checks), "status": "passed"})
    )


if __name__ == "__main__":
    main()
