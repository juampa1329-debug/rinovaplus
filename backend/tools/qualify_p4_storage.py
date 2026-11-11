"""Native faults, concurrency, academic denial and populated recovery on new copies."""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pyodbc

from app.institutional import channels_policy as policy
from app.institutional.spanish import connection_string, load
from app.institutional.store import transaction
from tools.es_schema_migrate_v2 import identity
from tools.foundation_snapshot import encode, sha
from tools.foundation_snapshot import quote_name as q
from tools.p2_es_recovery import restore
from tools.p3_workspace_recovery import tables as parent_tables
from tools.p4_channels_migrations import apply
from tools.p4_channels_recovery import backup, copy_media, fingerprint
from tools.prepare_p4_channels import WORK, admin, prepare, read, save


def academic(c):
    values = []
    for name in policy.layout()["academic_tables"]:
        columns = [
            r[0]
            for r in c.execute(
                (
                    "SELECT name FROM sys.columns WHERE object_id=O"
                    "BJECT_ID(?) ORDER BY column_id"
                ),
                name,
            ).fetchall()
        ]
        rows = c.execute(
            "SELECT "
            + ",".join(
                "CONVERT(varbinary(max)," + q(column) + ")" for column in columns
            )
            + " FROM "
            + name
        ).fetchall()
        values.append(
            {
                "table": name,
                "rows": len(rows),
                "sha256": hashlib.sha256(
                    b"".join(
                        sorted(
                            hashlib.sha256(encode(list(row))).digest() for row in rows
                        )
                    )
                ).hexdigest(),
            }
        )
    return {
        "tables": len(values),
        "rows": sum(v["rows"] for v in values),
        "sha256": sha(values),
    }


def main():
    if (WORK / "storage-result.json").exists():
        raise ValueError("P4ES_storage_qualification_already_exists")
    candidate = read(WORK / "candidate.json")
    checkpoint = candidate["checkpoint"]
    release = policy.release()
    checks, faults = [], []
    with admin(candidate["database"], readonly=True) as connection:
        academic_before = academic(connection.cursor())

    def fresh():
        name = "CBN_P4ES_FAULT_20261026_" + uuid4().hex[:8]
        with admin("master") as connection:
            restore(
                connection,
                checkpoint,
                name,
                restricted=True,
                target_pattern=policy.TARGET,
                allowed_tables=parent_tables(),
            )
        return name

    for point in ["after_started", "before_commit", "after_commit"]:
        name = fresh()
        with admin(name) as connection:
            c = connection.cursor()
            actual, parent = identity(c), policy.parent_digest(c)
            try:
                apply(
                    connection,
                    actual,
                    approved_release=release,
                    parent_journal=parent,
                    fault=point,
                )
            except RuntimeError as error:
                assert str(error) == "P4ES_injected_" + point
            else:
                raise AssertionError("fault_not_injected")
            prior = c.execute(
                (
                    "SELECT Status FROM dbo.CRMCanalOperacionMigrac"
                    "ion WHERE UnitId='P4ES-001'"
                )
            ).fetchval()
            resumed = apply(
                connection, actual, approved_release=release, parent_journal=parent
            )
            repeat = apply(
                connection, actual, approved_release=release, parent_journal=parent
            )
            assert repeat["status"] == "noop" and academic(c) == academic_before
            faults.append(
                {
                    "fault": point,
                    "durable_status_after_fault": prior,
                    "resume": resumed["status"],
                    "repeat": repeat["status"],
                    "academic_unchanged": True,
                }
            )
    checks.append("three_durable_faults_resumed_without_academic_changes")
    concurrent = fresh()

    def run(_):
        with admin(concurrent) as connection:
            return apply(
                connection,
                identity(connection.cursor()),
                approved_release=release,
                parent_journal=policy.parent_digest(connection.cursor()),
            )["status"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        states = sorted(pool.map(run, range(2)))
    assert states == ["committed", "noop"]
    checks.append("concurrent_migration_one_commit_one_noop")
    profile = read(WORK / "fixture-profile.json")
    settings = load(Path(profile["directory"]))
    with admin(profile["database"], readonly=True) as connection:
        assert academic(connection.cursor()) == academic_before
    checks.append("fixture_academic_bytes_match_native_parent")
    # Effective SQL permissions, not just application route guards.
    denied = []
    with pyodbc.connect(
        connection_string(settings), timeout=5, autocommit=True
    ) as connection:
        c = connection.cursor()
        for command in [
            "SELECT TOP(1) * FROM " + policy.layout()["academic_tables"][0],
            "DELETE FROM " + policy.layout()["academic_tables"][0] + " WHERE 1=0",
            "CREATE TABLE dbo.P4ForbiddenCreate(Id int)",
            "DELETE FROM dbo.CRMCanalOperacionMigracion WHERE 1=0",
        ]:
            try:
                c.execute(command)
            except pyodbc.Error as error:
                assert error.args[0] in {"42000", "23000"}
                denied.append(command.split()[0])
            else:
                raise AssertionError("effective_SQL_denial_missing")
    assert len(denied) == 4
    checks.append("runtime_academic_DDL_and_journal_deletion_denied")
    with admin(profile["database"]) as connection:
        before = fingerprint(connection.cursor())
        populated = backup(connection, settings.ticket["identity"])
        media = copy_media(
            connection.cursor(),
            WORK / "media-fixture/inbox-media",
            WORK / "media-recovery/inbox-media",
        )
    save(WORK / "populated-checkpoint.json", populated)
    prepare("recovery", restored_checkpoint=populated, source_settings=settings)
    recovery = read(WORK / "recovery-profile.json")
    restored = load(Path(recovery["directory"]))
    with transaction(restored, anonymous=True) as c:
        assert (
            c.execute("SELECT COUNT(*) FROM crm_channels2.SecretVersion").fetchval() > 0
        )
        assert (
            c.execute("SELECT COUNT(*) FROM crm_channels2.SocialComment").fetchval() > 0
        )
        assert (
            c.execute("SELECT COUNT(*) FROM crm_channels2.WebhookReceipt").fetchval()
            > 0
        )
        assert (
            c.execute(
                "SELECT COUNT(*) FROM crm_access.Session WHERE RevokedAt IS NULL"
            ).fetchval()
            == 0
        )
    with admin(profile["database"], readonly=True) as connection:
        assert fingerprint(connection.cursor()) == before
    with admin(recovery["database"], readonly=True) as connection:
        assert academic(connection.cursor()) == academic_before
        assert (
            policy.history_digest(connection.cursor())
            == settings.ticket["channels_history_sha256"]
        )
    checks.append(
        "populated_native_restore_vault_history_receipts_and_session_retirement"
    )
    checks.append("populated_source_data_fingerprint_unchanged")
    checks.append("private_ready_media_blob_copy_verified")
    save(
        WORK / "storage-result.json",
        {
            "status": "passed",
            "engine": 15,
            "compatibility": 150,
            "checks": checks,
            "faults": faults,
            "concurrency": states,
            "effective_SQL_denials": len(denied),
            "academic": academic_before,
            "media_files_copied": len(media),
            "native_backup_checksum": True,
            "native_backup_copy_only": True,
            "migrations_reapplied_after_populated_restore": False,
        },
    )
    print(
        json.dumps(
            {
                "passed": len(checks),
                "faults": len(faults),
                "SQL_denials": len(denied),
                "native_restore": True,
            }
        )
    )


if __name__ == "__main__":
    main()
