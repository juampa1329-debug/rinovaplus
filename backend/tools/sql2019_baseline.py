"""Compile a distinct SQL2019 release from preserved, reviewed CRM DDL bodies.

No legacy file or guard is changed. The new narrower guard is part of this
release, whose manifest records both full original bytes and identical DDL body.
Importing this module never connects, writes files or creates a database.
"""

import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4

from app.institutional.policy import TARGET
from app.parity_channels.catalog import metadata
from tools.cbn_foundation import acquire, target_identity
from tools.foundation_snapshot import sha

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "backend/migrations/cbn_sql2019_baseline"
ACTOR = "cbn_sql19_migrator"
VERSION = "cbn-sql19-baseline-v1"
SOURCES = [
    (
        "SQL19-B000",
        "backend/migrations/cbn_foundation/B000_journal.sql",
        "CREATE TABLE crm_meta.MigrationJournal",
    ),
    (
        "SQL19-B001",
        "backend/migrations/cbn_foundation/B001_core.sql",
        "        CREATE TABLE crm.Contact",
    ),
    (
        "SQL19-B006",
        "backend/migrations/cbn_foundation/B006_configuration.sql",
        "  CREATE TABLE crm_config.Configuration",
    ),
    (
        "SQL19-B011",
        "backend/migrations/cbn_channels_v2/B011_channels.sql",
        "-- C7_BOUNDARY",
    ),
    *[
        (
            "SQL19-CHP00" + str(i),
            "backend/migrations/cbn_channels_parity_v1/CBN-CHP00" + str(i) + ".sql",
            "-- C11_BOUNDARY",
        )
        for i in range(1, 6)
    ],
]
HEADER = """-- New SQL2019-only release. Original source files remain frozen.
SET XACT_ABORT ON;
IF @@TRANCOUNT<>1 OR USER_NAME()<>N'cbn_sql19_migrator'
 OR CONVERT(int,SERVERPROPERTY('ProductMajorVersion'))<>15
 OR (SELECT compatibility_level FROM sys.databases WHERE database_id=DB_ID())<>150
 OR SESSION_CONTEXT(N'CBN_SQL19_TARGET') IS NULL
 OR DB_NAME() COLLATE Latin1_General_100_BIN2<>
 CONVERT(nvarchar(128),SESSION_CONTEXT(N'CBN_SQL19_TARGET')) COLLATE Latin1_General_100_BIN2
 OR LEFT(DB_NAME(),7) COLLATE Latin1_General_100_BIN2<>N'CBN_P2_'
 THROW 51900,'Approved SQL2019 target, actor and transaction required.',1;
"""


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compile_release():
    from tools.historical_checkpoint import (
        C11_RELEASE_SHA256,
        CHANNEL_RELEASES,
        channel_assets,
        verify_frozen_release,
    )

    verify_frozen_release()
    channel_assets()
    if (
        digest(ROOT / "backend/migrations/cbn_channels_v2/release.json")
        != CHANNEL_RELEASES["cbn_channels_v2"]
        or digest(ROOT / "backend/migrations/cbn_channels_parity_v1/release.json")
        != C11_RELEASE_SHA256
    ):
        raise ValueError("SQL19_legacy_release_changed")
    PACKAGE.mkdir(exist_ok=True)
    units = []
    for identity, name, marker in SOURCES:
        raw = (ROOT / name).read_text(encoding="utf-8")
        if raw.count(marker) < 1:
            raise ValueError("SQL19_source_boundary_missing")
        body = raw[raw.index(marker) :]
        path = PACKAGE / (identity + ".sql")
        path.write_text(HEADER + body, encoding="utf-8")
        units.append(
            {
                "id": identity,
                "file": path.name,
                "sha256": digest(path),
                "source": name,
                "source_sha256": digest(ROOT / name),
                "body_sha256": hashlib.sha256(body.encode()).hexdigest(),
            }
        )
    manifest = {
        "version": VERSION,
        "actor": ACTOR,
        "major": 15,
        "compatibility": 150,
        "compiler_sha256": digest(Path(__file__)),
        "scope": "new_SQL2019_P2_reference_restorations_only",
        "units": units,
        "legacy_bodies_modified": False,
        "automatic_startup_DDL": False,
    }
    (PACKAGE / "release.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def release():
    data = json.loads((PACKAGE / "release.json").read_text(encoding="utf-8"))
    if data["version"] != VERSION or data["major"] != 15:
        raise ValueError("SQL19_release_scope")
    if data["compiler_sha256"] != digest(Path(__file__)):
        raise ValueError("SQL19_compiler_changed")
    for item in data["units"]:
        if (
            digest(PACKAGE / item["file"]) != item["sha256"]
            or digest(ROOT / item["source"]) != item["source_sha256"]
        ):
            raise ValueError("SQL19_release_input_changed")
    return data


def shape(cursor):
    result = metadata(cursor)
    return sha(
        {
            k: [
                r
                for r in value
                if r.get("schema_name")
                in {"crm_meta", "crm", "crm_config", "crm_channels", "crm_channels2"}
                or k == "schemas"
                and r.get("name")
                in {"crm_meta", "crm", "crm_config", "crm_channels", "crm_channels2"}
            ]
            for k, value in result.items()
            if isinstance(value, list)
            and k
            not in {"permissions", "all_permissions", "principals", "role_membership"}
        }
    )


def append(cursor, identity, unit, attempt, kind, manifest, before, after=None):
    cursor.execute(
        "INSERT crm_meta.MigrationJournal(AttemptId,UnitId,EventKind,ReleaseId,ToolVersion,ManifestSha256,UnitSha256,ShapeVersion,TargetSha256,BeforeShapeSha256,AfterShapeSha256,EvidenceRef,ApprovalRef,BackupRef,PrincipalRef,SuccessKey) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        str(attempt),
        unit["id"],
        kind,
        VERSION,
        "SQL19-native-v1",
        bytes.fromhex(manifest),
        bytes.fromhex(unit["sha256"]),
        VERSION,
        bytes.fromhex(sha(identity)),
        bytes.fromhex(before),
        bytes.fromhex(after) if after else None,
        "P1-SQL2019-restored",
        "owner-P2-20261026",
        identity["database"] + "-pre-unit",
        ACTOR,
        unit["id"] if kind == "COMMITTED" else None,
    )


def receipt(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as output:
        output.write(json.dumps(value, sort_keys=True) + "\n")
        output.flush()
        os.fsync(output.fileno())


def apply(connection, expected_identity, wal, *, fault=None):
    package = release()
    manifest = digest(PACKAGE / "release.json")
    cursor = connection.cursor()
    actual = target_identity(cursor)
    if (
        actual != expected_identity
        or not TARGET.fullmatch(actual["database"])
        or (actual["engine"], actual["compatibility"]) != (15, 150)
    ):
        raise ValueError("SQL19_target_identity")
    cursor.execute(
        "EXEC sys.sp_set_session_context @key=N'CBN_SQL19_TARGET',@value=?",
        actual["database"],
    )
    cursor.execute("EXECUTE AS USER=N'cbn_sql19_migrator';")
    try:
        acquire(cursor, "crm.schema.migrate.v1", "Session")
        acquire(cursor, "crm.local.commit", "Session")
        exists = cursor.execute(
            "SELECT OBJECT_ID('crm_meta.MigrationJournal','U')"
        ).fetchval()
        committed = []
        if exists:
            committed = [
                r[0]
                for r in cursor.execute(
                    "SELECT UnitId FROM crm_meta.MigrationJournal WHERE SuccessKey IS NOT NULL ORDER BY EventId"
                ).fetchall()
            ]
            if committed != [u["id"] for u in package["units"][: len(committed)]]:
                raise ValueError("SQL19_history_vector")
            if committed:
                last = cursor.execute(
                    "SELECT AfterShapeSha256 FROM crm_meta.MigrationJournal WHERE SuccessKey=?",
                    committed[-1],
                ).fetchval()
                if bytes(last).hex() != shape(cursor):
                    raise ValueError("SQL19_catalog_drift")
            unresolved = cursor.execute(
                "SELECT COUNT(*) FROM crm_meta.MigrationJournal s WHERE s.EventKind='STARTED' AND NOT EXISTS(SELECT 1 FROM crm_meta.MigrationJournal e WHERE e.AttemptId=s.AttemptId AND e.EventKind IN('COMMITTED','FAILED_ROLLED_BACK','RECONCILED_NOT_APPLIED'))"
            ).fetchval()
            if unresolved:
                raise ValueError("SQL19_reconciliation_required")
        else:
            present = cursor.execute(
                "SELECT COUNT(*) FROM sys.objects WHERE is_ms_shipped=0 AND schema_id IN(SCHEMA_ID('crm_meta'),SCHEMA_ID('crm'),SCHEMA_ID('crm_config'),SCHEMA_ID('crm_channels'),SCHEMA_ID('crm_channels2'))"
            ).fetchval()
            if present:
                raise ValueError("SQL19_unrecognized_existing_objects")
        for unit in package["units"]:
            if unit["id"] in committed:
                found = cursor.execute(
                    "SELECT ManifestSha256,UnitSha256 FROM crm_meta.MigrationJournal WHERE SuccessKey=?",
                    unit["id"],
                ).fetchone()
                if (
                    bytes(found[0]).hex() != manifest
                    or bytes(found[1]).hex() != unit["sha256"]
                ):
                    raise ValueError("SQL19_committed_bytes_conflict")
                continue
            before = shape(cursor)
            attempt = uuid4()
            receipt(
                wal,
                {
                    "unit": unit["id"],
                    "attempt": str(attempt),
                    "event": "STARTED",
                    "target_sha256": sha(actual),
                    "manifest": manifest,
                    "before": before,
                },
            )
            if exists:
                append(cursor, actual, unit, attempt, "STARTED", manifest, before)
            cursor.execute("BEGIN TRANSACTION;")
            try:
                cursor.execute((PACKAGE / unit["file"]).read_text(encoding="utf-8"))
                while cursor.nextset():
                    pass
                after = shape(cursor)
                if fault == unit["id"] + ":before_commit":
                    raise RuntimeError("SQL19_controlled_precommit")
                append(
                    cursor, actual, unit, attempt, "COMMITTED", manifest, before, after
                )
                cursor.execute("COMMIT;")
            except BaseException:
                from contextlib import suppress

                with suppress(Exception):
                    cursor.execute("IF @@TRANCOUNT>0 ROLLBACK;")
                receipt(
                    wal,
                    {
                        "unit": unit["id"],
                        "attempt": str(attempt),
                        "event": "FAILED_OR_UNCERTAIN",
                    },
                )
                raise
            receipt(
                wal,
                {
                    "unit": unit["id"],
                    "attempt": str(attempt),
                    "event": "COMMITTED",
                    "after": after,
                },
            )
            exists = True
            if fault == unit["id"] + ":after_commit":
                raise RuntimeError("SQL19_controlled_ack_lost")
        return {
            "units": len(package["units"]),
            "status": "accepted_releases_applied_SQL2019",
            "shape_sha256": shape(cursor),
        }
    finally:
        for resource in ("crm.local.commit", "crm.schema.migrate.v1"):
            cursor.execute(
                "EXEC sys.sp_releaseapplock @Resource=?,@LockOwner='Session'", resource
            )
        cursor.execute("REVERT;")


def reconcile(connection, expected_identity, wal):
    """Use an independent new connection. Never classify an uncertain COMMIT by error."""
    cursor = connection.cursor()
    actual = target_identity(cursor)
    if (
        actual != expected_identity
        or not TARGET.fullmatch(actual["database"])
        or actual["engine"] != 15
    ):
        raise ValueError("SQL19_reconcile_identity")
    package = release()
    manifest = digest(PACKAGE / "release.json")
    events = [
        json.loads(line) for line in Path(wal).read_text(encoding="utf-8").splitlines()
    ]
    pending = [
        e
        for e in events
        if e["event"] == "STARTED"
        and not any(
            x.get("attempt") == e["attempt"]
            and x["event"]
            in {"COMMITTED", "RECONCILED_COMMITTED", "RECONCILED_NOT_APPLIED"}
            for x in events
        )
    ]
    cursor.execute("EXECUTE AS USER=N'cbn_sql19_migrator';")
    try:
        acquire(cursor, "crm.schema.migrate.v1", "Session")
        acquire(cursor, "crm.local.commit", "Session")
        for event in pending:
            if event["manifest"] != manifest or event["target_sha256"] != sha(actual):
                raise ValueError("SQL19_WAL_binding")
            unit = next(u for u in package["units"] if u["id"] == event["unit"])
            exists = cursor.execute(
                "SELECT OBJECT_ID('crm_meta.MigrationJournal','U')"
            ).fetchval()
            success = (
                cursor.execute(
                    "SELECT ManifestSha256,UnitSha256,AfterShapeSha256 FROM crm_meta.MigrationJournal WHERE SuccessKey=?",
                    unit["id"],
                ).fetchone()
                if exists
                else None
            )
            current = shape(cursor)
            if success:
                if (
                    bytes(success[0]).hex() != manifest
                    or bytes(success[1]).hex() != unit["sha256"]
                    or bytes(success[2]).hex() != current
                ):
                    raise ValueError("SQL19_recovery_required")
                status = "RECONCILED_COMMITTED"
                append(
                    cursor,
                    actual,
                    unit,
                    event["attempt"],
                    status,
                    manifest,
                    event["before"],
                    current,
                )
            elif current == event["before"]:
                status = "RECONCILED_NOT_APPLIED"
                if exists:
                    append(
                        cursor,
                        actual,
                        unit,
                        event["attempt"],
                        status,
                        manifest,
                        event["before"],
                    )
            else:
                raise ValueError("SQL19_recovery_required")
            receipt(
                wal, {"unit": unit["id"], "attempt": event["attempt"], "event": status}
            )
        return {"reconciled": len(pending)}
    finally:
        for resource in ("crm.local.commit", "crm.schema.migrate.v1"):
            cursor.execute(
                "EXEC sys.sp_releaseapplock @Resource=?,@LockOwner='Session'", resource
            )
        cursor.execute("REVERT;")
