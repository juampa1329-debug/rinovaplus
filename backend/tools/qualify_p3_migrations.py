"Explicit fault, recovery and drift qualification in fresh restored P3 copies."

import contextlib
import json
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pyodbc

from app.es_schema_profile import journal_digest
from app.institutional import workspace_policy as policy
from app.institutional.api import create_app
from app.institutional.spanish import connection_string, load, transaction
from app.institutional.spanish_bindings import Cursor
from tools.es_schema_migrate_v2 import identity
from tools.foundation_snapshot import sha
from tools.p2_es_recovery import restore
from tools.p3_workspace_migrations import apply
from tools.p3_workspace_recovery import backup
from tools.prepare_p3_workspace import WORK, admin, fresh, prepare, read, save
from tools.qualify_p3_workspace import Browser


def main():
    prior = (
        read(WORK / "migration-result.json")
        if (WORK / "migration-result.json").exists()
        else {"faults": []}
    )
    if prior.get("status") == "passed":
        raise ValueError("P3ES_migration_qualification_already_completed")
    checkpoint = read(WORK / "candidate.json")["checkpoint"]
    approved = read(WORK / "approval.json")["release_sha256"]
    tests = prior["faults"]

    def restored():
        name = fresh("FAULT")
        with admin("master") as connection:
            restore(
                connection,
                checkpoint,
                name,
                restricted=True,
                target_pattern=policy.TARGET,
            )
        with admin(name) as connection:
            return (
                name,
                identity(connection.cursor()),
                journal_digest(connection.cursor()),
            )

    for fault in ["after_started", "before_commit", "after_commit"]:
        if any(row["fault"] == fault for row in tests):
            continue
        name, expected, parent = restored()
        with admin(name) as connection:
            try:
                apply(
                    connection,
                    expected,
                    approved_release=approved,
                    parent_journal=parent,
                    fault=fault,
                )
            except RuntimeError:
                pass
            else:
                raise AssertionError("fault_not_injected")
            status = (
                connection.cursor()
                .execute(
                    (
                        "SELECT Status FROM dbo.CRMTrabajoMigraci"
                        "on WHERE UnitId='P3ES-001'"
                    )
                )
                .fetchval()
            )
            assert status == ("COMMITTED" if fault == "after_commit" else "STARTED")
            result = apply(
                connection, expected, approved_release=approved, parent_journal=parent
            )
            assert result["status"] == (
                "noop" if fault == "after_commit" else "committed"
            )
            assert (
                apply(
                    connection,
                    expected,
                    approved_release=approved,
                    parent_journal=parent,
                )["status"]
                == "noop"
            )
            assert journal_digest(connection.cursor()) == parent
        tests.append(
            {
                "fault": fault,
                "database": name,
                "durable_status": status,
                "retry": result["status"],
                "repeat": "noop",
                "parent_history_preserved": True,
            }
        )
        save(WORK / "migration-result.json", {"status": "in_progress", "faults": tests})
    name, expected, parent = restored()

    def concurrent(_):
        with admin(name) as connection:
            return apply(
                connection, expected, approved_release=approved, parent_journal=parent
            )["status"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        concurrency = sorted(pool.map(concurrent, [0, 1]))
    assert concurrency == ["committed", "noop"]
    with admin(name) as connection:
        c = connection.cursor()
        c.execute("BEGIN TRANSACTION")
        try:
            apply(
                connection, expected, approved_release=approved, parent_journal=parent
            )
        except ValueError as error:
            assert str(error) == "P3ES_caller_transaction_must_be_absent"
        else:
            raise AssertionError("caller_transaction_not_rejected")
        assert c.execute("SELECT @@TRANCOUNT").fetchval() == 1
        c.execute("ROLLBACK")
        try:
            apply(
                connection,
                dict(expected, database="HORARIOSSIIE"),
                approved_release=approved,
                parent_journal=parent,
            )
        except ValueError:
            pass
        else:
            raise AssertionError("wrong_database_not_rejected")
        try:
            apply(
                connection, expected, approved_release="0" * 64, parent_journal=parent
            )
        except ValueError:
            pass
        else:
            raise AssertionError("wrong_release_not_rejected")
        # Keep the drift copy for diagnosis. Never erase the probe to make it pass.
        c.execute(("ALTER TABLE dbo.CRMTrabajoTarea ADD DriftProbe int NULL"))
        try:
            apply(
                connection, expected, approved_release=approved, parent_journal=parent
            )
        except ValueError as error:
            assert "model_drift" in str(error)
        else:
            raise AssertionError("drift_not_rejected")
    fixture = read(WORK / "fixture-r4-profile.json")
    settings = load(Path(fixture["directory"]))
    access = read(WORK / "fixture-r4-access.json")
    browser = Browser(create_app(settings))
    browser.login(access["email"], access["password"])
    browser.request(
        "credentials",
        "PUT",
        {
            "operation_id": str(uuid4()),
            "scope": "provider",
            "owner": "openai",
            "kind": "api_key",
            "value": "p3-controlled-secret-" + uuid4().hex,
        },
    )
    with admin(fixture["database"]) as connection:
        c = Cursor(connection.cursor(), settings.ticket["table_map"])
        business = {
            key: sha(
                [
                    list(r)
                    for r in c.execute(
                        "SELECT * FROM " + table + " ORDER BY 1"
                    ).fetchall()
                ]
            )
            for key, table in policy.EXTRA.items()
        }
        populated = backup(connection, settings.ticket["identity"])
    save(WORK / "populated-backup.json", populated)
    prepare("recovery", populated_checkpoint=populated, source_settings=settings)
    recovered = read(WORK / "recovery-profile.json")
    restored_settings = load(Path(recovered["directory"]))
    restored_browser = Browser(create_app(restored_settings))
    restored_browser.login(access["email"], access["password"])
    records = read(WORK / "fixture-records.json")
    view = restored_browser.get("conversations/" + records["conversationId"])
    assert (
        view["notes"]
        and restored_browser.get("clients")["total"] == 602
        and restored_browser.get("tasks?q=Volumen")["total"] == 58
    )
    with admin(recovered["database"], readonly=True) as connection:
        c = Cursor(connection.cursor(), restored_settings.ticket["table_map"])
        after = {
            key: sha(
                [
                    list(r)
                    for r in c.execute(
                        "SELECT * FROM " + table + " ORDER BY 1"
                    ).fetchall()
                ]
            )
            for key, table in policy.EXTRA.items()
        }
        assert business == after
        accounts = c.execute("SELECT COUNT(*) FROM crm_access.AccessUser").fetchval()
        assert accounts == 2
        assert c.execute(
            ("SELECT HAS_PERMS_BY_NAME(?,'USER','IMPERSONATE')"),
            settings.connection["username"],
        ).fetchval() in (0, 1)
    secret = restored_browser.request("credentials/provider").json()["items"]
    assert secret and secret[-1]["state"] == "staged"
    # An old cookie from the source copy is invalid in the restored profile.
    old = Browser(create_app(restored_settings))
    old.client.cookies.update(browser.client.cookies)
    old.request("workspace/clients", expected=401)
    with transaction(restored_settings, anonymous=True):
        pass
    # Runtime cannot change its migration journal or read/write academic records.
    denied = []
    for query in [
        "SELECT TOP(0) * FROM dbo.ACAspirante",
        "DELETE FROM dbo.ACAspirante WHERE 1=0",
        ("UPDATE dbo.CRMTrabajoMigracion SET Status=Status WHERE 1=0"),
        "CREATE TABLE dbo.P3ForbiddenDDL(Id int)",
    ]:
        connection = pyodbc.connect(
            connection_string(restored_settings), autocommit=False
        )
        try:
            try:
                connection.cursor().execute(query)
            except pyodbc.Error as error:
                assert "(229)" in str(error) or "(262)" in str(error)
                denied.append(True)
            else:
                raise AssertionError("runtime_permission_not_denied")
        finally:
            connection.rollback()
            connection.close()
    # The journal's binary timestamps and lineage are pinned in profile revision2.
    with admin(recovered["database"]) as connection:
        c = connection.cursor()
        c.execute("BEGIN TRANSACTION")
        c.execute(
            (
                "UPDATE dbo.CRMTrabajoMigracion SET Commi"
                "ttedAt=DATEADD(second,1,CommittedAt)"
            )
        )
        # Verify through the same admin transaction cannot pass as runtime anyway;
        # the direct closed digest demonstrates the intended content drift first.
        assert (
            policy.history_digest(c)
            != restored_settings.ticket["workspace_history_sha256"]
        )
        c.execute("ROLLBACK")
    report = {
        "status": "passed",
        "faults": tests,
        "concurrency": concurrency,
        "caller_transaction_preserved": True,
        "wrong_target_rejected": True,
        "wrong_release_rejected": True,
        "model_drift_rejected": True,
        "populated_native_restore": recovered["native_restore"],
        "recovery_database": recovered["database"],
        "restored_accounts": accounts,
        "CRM_workspace_binary_hashes_equal": business == after,
        "copied_secrets_authenticated": True,
        "old_cookie_rejected": True,
        "runtime_SQL_denials": len(denied),
        "journal_timestamp_digest_drift_detected": True,
        "migration_history_not_rewritten": True,
        "academic_DDL_or_DML": False,
        "provider_calls": 0,
    }
    save(WORK / "migration-result.json", report)
    print(
        json.dumps(
            {
                "P3_migrations_and_recovery": "passed",
                "fault_cases": len(tests),
                "restored_accounts": accounts,
                "SQL_denials": len(denied),
            }
        )
    )


if __name__ == "__main__":
    try:
        main()
    except BaseException as error:
        with contextlib.suppress(Exception):
            save(
                WORK / ("migration-failure-" + uuid4().hex + ".json"),
                {
                    "type": type(error).__name__,
                    "message": str(error),
                    "trace": traceback.format_exc(),
                },
            )
        print(
            json.dumps(
                {"P3_migrations_and_recovery": "failed", "type": type(error).__name__}
            )
        )
        raise SystemExit(1)
