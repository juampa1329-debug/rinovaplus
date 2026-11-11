"""Explicit P1 qualification extensions. Mutations only in fresh fault copies."""

import argparse
import concurrent.futures
import copy
import json
import shutil
import tempfile
import threading
from pathlib import Path

import pyodbc
import tools.es_schema_migrate_v2 as migration
import tools.qualify_spanish_schema as drill
from app.es_schema_profile import load, transaction
from tools.es_schema_recovery_v2 import data_fingerprint, restore
from tools.foundation_snapshot import quote_name as q


def reject(action, message):
    try:
        action()
    except ValueError as error:
        if message not in str(error):
            raise
        return str(error).split(":", 1)[0]
    raise AssertionError("Expected rejection: " + message)


def new_fault(post=False):
    document = drill.read(drill.WORK / ("main.json" if post else "state.json"))
    checkpoint = document["post_backup" if post else "empty_backup"]
    name, actual, recovery = drill.restored(checkpoint, "FAULT")
    return name, actual, drill.WORK / (name + ".wal.jsonl")


def negatives():
    results = []
    name, actual, wal = new_fault()
    with drill.admin(name) as connection:
        before = migration.shape(connection.cursor())
        connection.cursor().execute("BEGIN TRANSACTION")
        code = reject(
            lambda: drill.apply(connection, actual, wal), "caller_transaction_not_owned"
        )
        assert connection.cursor().execute("SELECT @@TRANCOUNT").fetchval() == 1
        connection.cursor().execute("ROLLBACK")
        assert before == migration.shape(connection.cursor())
        results.append(
            {
                "check": "caller_transaction_retained",
                "database": name,
                "rejection": code,
            }
        )
        wrong = {**actual, "created_at": "1900-01-01T00:00:00"}
        code = reject(lambda: drill.apply(connection, wrong, wal), "target_identity")
        results.append(
            {"check": "full_target_identity", "database": name, "rejection": code}
        )
    for label, sql, expected in [
        (
            "unknown_alias_type",
            "CREATE TYPE dbo.P1Unknown FROM nvarchar(40) NULL",
            "unrecognized_initial_user_types",
        ),
        (
            "unapproved_initial_ACL",
            "CREATE USER P1Unknown WITHOUT LOGIN",
            "initial_catalog_not_approved",
        ),
        (
            "migrator_control_overlay",
            "GRANT CONTROL TO " + q(migration.ACTOR),
            "migrator_privilege_overlay",
        ),
    ]:
        name, actual, wal = new_fault()
        with drill.admin(name) as connection:
            connection.cursor().execute(sql)
            before = migration.shape(connection.cursor())
            code = reject(lambda: drill.apply(connection, actual, wal), expected)
        with drill.admin(name) as observer:
            assert before == migration.shape(observer.cursor())
        assert not wal.exists()
        results.append({"check": label, "database": name, "rejection": code})
    # Test edited release bytes in an isolated filesystem fixture, never the release.
    with tempfile.TemporaryDirectory(prefix="cbn-es-tamper-") as temporary:
        root = Path(temporary)
        release = drill.release()
        for relative in list(release["inputs"]) + [
            "backend/migrations/cbn_spanish_schema_v2/release.json"
        ]:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(migration.ROOT / relative, target)
        package = root / "backend/migrations/cbn_spanish_schema_v2"
        with (package / "ES_B001_schema.sql").open("a") as stream:
            stream.write("\n-- isolated negative fixture\n")
        previous = migration.ROOT, migration.PACKAGE
        try:
            migration.ROOT, migration.PACKAGE = root, package
            code = reject(
                lambda: migration.release(drill.APPROVED), "unit_bytes_conflict"
            )
        finally:
            migration.ROOT, migration.PACKAGE = previous
        results.append({"check": "edited_unit_bytes_before_SQL", "rejection": code})
    main = drill.read(drill.WORK / "main.json")
    with drill.admin("master") as connection:
        existing = drill.read(drill.WORK / "state.json")["base"]
        code = reject(
            lambda: restore(connection, main["post_backup"], existing),
            "restore_existing_database",
        )
        results.append({"check": "restore_no_overwrite", "rejection": code})
        bad = copy.deepcopy(main["post_backup"])
        bad["backup_uuid"] = "00000000-0000-0000-0000-000000000000"
        target = drill.fresh("RECOVERY")
        code = reject(
            lambda: restore(connection, bad, target), "backup_identity_or_header"
        )
        assert (
            not connection.cursor()
            .execute("SELECT 1 FROM sys.databases WHERE name=?", target)
            .fetchone()
        )
        results.append(
            {"check": "backup_GUID_substitution_before_restore", "rejection": code}
        )
    drill.save(drill.WORK / "negatives.json", results)
    print(json.dumps({"negative_SQL2019_checks": len(results), "passed": True}))


def drift():
    results = []
    for kind in (
        "CHECK_expression_same_count",
        "index_norecompute",
        "index_sequential_key",
        "column_type",
        "extra_view",
        "ACL_overlay",
    ):
        name, actual, wal = new_fault()
        with drill.admin(name) as connection:
            assert drill.apply(connection, actual, wal)["status"] == "committed"
            cursor = connection.cursor()
            before_count = cursor.execute(
                "SELECT COUNT(*) FROM sys.tables WHERE is_ms_shipped=0"
            ).fetchval()
            if kind == "CHECK_expression_same_count":
                row = cursor.execute(
                    "SELECT TOP(1) OBJECT_SCHEMA_NAME(parent_object_id),OBJECT_NAME(parent_object_id),name FROM sys.check_constraints ORDER BY name"
                ).fetchone()
                table = q(row[0]) + "." + q(row[1])
                cursor.execute("ALTER TABLE " + table + " DROP CONSTRAINT " + q(row[2]))
                cursor.execute(
                    "ALTER TABLE "
                    + table
                    + " WITH CHECK ADD CONSTRAINT "
                    + q(row[2])
                    + " CHECK(1=1)"
                )
            elif kind.startswith("index_"):
                row = cursor.execute(
                    "SELECT TOP(1) OBJECT_SCHEMA_NAME(object_id),OBJECT_NAME(object_id),name FROM sys.indexes WHERE object_id IN(SELECT object_id FROM sys.tables WHERE is_ms_shipped=0 AND name<>'MigrationJournal') AND type=1 ORDER BY name"
                ).fetchone()
                option = (
                    "STATISTICS_NORECOMPUTE"
                    if kind == "index_norecompute"
                    else "OPTIMIZE_FOR_SEQUENTIAL_KEY"
                )
                cursor.execute(
                    "ALTER INDEX "
                    + q(row[2])
                    + " ON "
                    + q(row[0])
                    + "."
                    + q(row[1])
                    + " SET ("
                    + option
                    + "=ON)"
                )
            elif kind == "column_type":
                cursor.execute(
                    "ALTER TABLE dbo.CRMContacto ALTER COLUMN Name nvarchar(1000) NULL"
                )
            elif kind == "extra_view":
                cursor.execute(
                    "CREATE VIEW dbo.P1UnapprovedView AS SELECT CAST(1 AS int) AS Value"
                )
            else:
                cursor.execute("GRANT EXECUTE TO " + q(migration.ACTOR))
            altered = drill.sha(migration.metadata(cursor))
            assert (
                before_count
                == cursor.execute(
                    "SELECT COUNT(*) FROM sys.tables WHERE is_ms_shipped=0"
                ).fetchval()
                == 99
            )
            expected = (
                "unexpected_routine_trigger_or_object"
                if kind == "extra_view"
                else "catalog_drift"
            )
            code = reject(lambda: drill.apply(connection, actual, wal), expected)
            assert altered == drill.sha(migration.metadata(cursor))
            results.append(
                {
                    "check": kind,
                    "database": name,
                    "table_count_unchanged": 99,
                    "rejection": code,
                }
            )
    drill.save(drill.WORK / "drift.json", results)
    print(json.dumps({"actual_catalog_drift_checks": len(results), "passed": True}))


def concurrency():
    name, actual, wal = new_fault()
    barrier = threading.Barrier(2)

    def worker():
        with drill.admin(name) as connection:
            barrier.wait(timeout=10)
            return drill.apply(connection, actual, wal)["status"]

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker) for _ in range(2)]
        outcomes = sorted(f.result(timeout=30) for f in futures)
    assert outcomes == ["committed", "noop"]
    with drill.admin(name) as connection:
        assert (
            connection.cursor()
            .execute(
                "SELECT COUNT(*) FROM crm_meta.MigrationJournal WHERE SuccessKey IS NOT NULL"
            )
            .fetchval()
            == 2
        )
        assert drill.apply(connection, actual, wal)["status"] == "noop"
    # Exercise a lost ACK during independent recovery of the WAL→SQL gap.
    gap_name, gap_actual, gap_wal = new_fault()
    with drill.admin(gap_name) as connection:
        try:
            drill.apply(
                connection,
                gap_actual,
                gap_wal,
                fault="ES-B001:after_wal_before_SQL_started",
            )
        except RuntimeError as error:
            assert str(error) == "ES_controlled_WAL_to_SQL_gap"
        else:
            raise AssertionError("gap fault absent")
    with drill.admin(gap_name) as connection:
        try:
            drill.reconcile(
                connection, gap_actual, gap_wal, fault="after_recovered_SQL_started"
            )
        except RuntimeError as error:
            assert str(error) == "ES_controlled_recovered_STARTED_ack_lost"
        else:
            raise AssertionError("recovery ACK fault absent")
    with drill.admin(gap_name) as connection:
        assert drill.reconcile(connection, gap_actual, gap_wal)["reconciled"] == [
            "RECONCILED_NOT_APPLIED"
        ]
        assert drill.apply(connection, gap_actual, gap_wal)["status"] == "committed"
        assert drill.apply(connection, gap_actual, gap_wal)["status"] == "noop"
    drill.save(
        drill.WORK / "concurrency.json",
        {
            "database": name,
            "parallel_outcomes": outcomes,
            "unique_success_keys": 2,
            "gap_recovery_ACK_database": gap_name,
            "gap_recovery_ACK_retry": "passed",
        },
    )
    print(json.dumps({"concurrent_apply_and_recovery_ACK_loss": "passed"}))


def recovery():
    state = drill.read(drill.WORK / "state.json")
    main = drill.read(drill.WORK / "main.json")
    restored, actual, post = drill.restored(main["post_backup"], "RECOVERY")
    with drill.admin(restored) as connection:
        assert migration.shape(connection.cursor()) == main["shape_sha256"]
        assert data_fingerprint(connection.cursor()) == main["post_backup"]["data"]
    # Roll back by restoring the previous schema into another new destination.
    rolled_back, previous, before = drill.restored(state["empty_backup"], "RECOVERY")
    with drill.admin(rolled_back) as connection:
        assert (
            connection.cursor()
            .execute("SELECT COUNT(*) FROM sys.tables WHERE is_ms_shipped=0")
            .fetchval()
            == 0
        )
    with drill.admin(main["database"]) as connection:
        assert (
            drill.apply(connection, main["identity"], Path(main["wal"]))["status"]
            == "noop"
        )
        assert data_fingerprint(connection.cursor()) == main["post_backup"]["data"]
    drill.save(
        drill.WORK / "recovery.json",
        {
            "post_restore_database": restored,
            "post_restore": post,
            "rollback_destination": rolled_back,
            "rollback": before,
            "previous_schema_tables": 0,
            "main_history_and_data_retained": True,
            "application_profiles_redirected": False,
        },
    )
    print(
        json.dumps(
            {
                "native_post_restore_and_previous_schema_rollback": "passed",
                "main_preserved": True,
            }
        )
    )


def snapshot():
    main = drill.read(drill.WORK / "main.json")
    own = drill.read(drill.WORK / "profile-result.json")
    with drill.admin(main["database"]) as connection:
        values = {
            "identity": migration.identity(connection.cursor()),
            "shape": migration.shape(connection.cursor()),
            "data": data_fingerprint(connection.cursor()),
        }
    settings = load(own["directory"])
    with transaction(settings) as cursor:
        values["profile_shape"] = migration.shape(cursor)
        values["profile_contact_count"] = cursor.execute(
            "SELECT COUNT(*) FROM dbo.CRMContacto"
        ).fetchval()
    with drill.admin(own["database"]) as connection:
        values["profile_data"] = data_fingerprint(connection.cursor())
    return values


def before_restart():
    assert not (drill.WORK / "restart-before.json").exists()
    drill.save(drill.WORK / "restart-before.json", snapshot())
    print(json.dumps({"own_SQL2019_restart_baseline": "captured"}))


def after_restart():
    current = snapshot()
    assert current == drill.read(drill.WORK / "restart-before.json")
    drill.save(
        drill.WORK / "restart.json",
        {
            "SQL2019_restart": "passed",
            "catalog_data_journal_profile_unchanged": True,
            "startup_DDL": False,
            "snapshot": current,
        },
    )
    print(json.dumps({"SQL2019_restart_catalog_data_journal_profile": "passed"}))


def sources():
    original = drill.read(drill.WORK / "sources-before.json")
    current = drill.source_snapshots()
    assert current == original, "Source preservation mismatch"
    drill.save(drill.WORK / "sources-after.json", current)
    drill.save(
        drill.WORK / "preservation.json",
        {
            "source_databases": list(current),
            "full_catalog_and_binary_data_equal": True,
            "source_databases_checked": 6,
            "academic_source_DML": False,
        },
    )
    print(json.dumps({"six_original_databases_full_catalog_binary_data": "unchanged"}))


def permissions():
    own = drill.read(drill.WORK / "profile-result.json")
    settings = load(own["directory"])
    layout = drill.read(migration.PACKAGE / "table_map.json")
    academic = layout["academic_tables"][0]
    other = sorted(
        set(layout["CRM_map"].values()) - set(settings.ticket["core_map"].values())
    )[0]
    results = []
    for label, sql, codes in [
        ("academic_read", "SELECT TOP(0) * FROM " + academic, (229,)),
        ("academic_delete", "DELETE FROM " + academic + " WHERE 1=0", (229,)),
        ("core_delete", "DELETE FROM dbo.CRMContacto WHERE 1=0", (229,)),
        ("other_CRM_read", "SELECT TOP(0) * FROM " + other, (229,)),
        ("journal_write", "DELETE FROM crm_meta.MigrationJournal WHERE 1=0", (229,)),
        ("impersonate_dbo", "EXECUTE AS USER='dbo'", (15517,)),
    ]:
        try:
            with transaction(settings) as cursor:
                cursor.execute(sql)
        except pyodbc.Error as error:
            assert any("(" + str(code) + ")" in str(error) for code in codes)
        else:
            raise AssertionError("Runtime permission accepted: " + label)
        results.append({"check": label, "SQL_permission_denied": True})
    with drill.admin("DBSIIE_CRM_Esquema_ES_20261026") as connection:
        original = migration.verify_package_catalog(connection.cursor())
        assert original["passed"]
        assert data_fingerprint(connection.cursor())["rows"] == 0
    drill.save(
        drill.WORK / "permissions.json",
        {
            "database": own["database"],
            "actual_denied_statements": results,
            "original_98_catalog_after": original,
            "original_98_data_rows_after": 0,
        },
    )
    print(
        json.dumps(
            {
                "six_actual_denied_runtime_statements": "passed",
                "original_98_catalog": "matches",
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode",
        choices=[
            "negatives",
            "drift",
            "concurrency",
            "recovery",
            "before_restart",
            "after_restart",
            "sources",
            "permissions",
        ],
    )
    parser.add_argument("--manifest-sha256", required=True)
    arguments = parser.parse_args()
    drill.APPROVED = arguments.manifest_sha256
    drill.release()
    try:
        globals()[arguments.mode]()
    except BaseException as error:
        import traceback

        drill.save(
            drill.WORK / ("extension-error-" + drill.uuid.uuid4().hex + ".json"),
            {
                "type": type(error).__name__,
                "message": str(error),
                "traceback": traceback.format_exc(),
            },
        )
        print(
            json.dumps(
                {
                    "failed": type(error).__name__,
                    "mode": arguments.mode,
                    "private_diagnostic_saved": True,
                }
            )
        )
        raise SystemExit(1)
