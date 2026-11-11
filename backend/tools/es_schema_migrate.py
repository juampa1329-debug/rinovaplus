"""Explicit SQL2019-only Spanish baseline. Never invoked by application startup.

The imported 98-table artifact is immutable. This new release adds one journal
in a separate schema and runs reviewed DDL under a narrowed, loginless actor.
Uncertain commits are reconciled only through an independent fresh connection.
"""

import hashlib
import json
import os
import re
from contextlib import suppress
from pathlib import Path
from uuid import uuid4

from app.parity_channels.catalog import metadata
from tools.cbn_foundation import acquire, target_identity
from tools.es_schema_catalog import compare, snapshot
from tools.foundation_snapshot import sha

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "backend/migrations/cbn_spanish_schema_v1"
VERSION = "cbn-spanish-baseline-v1"
ACTOR = "cbn_es_migrator_p1"
TARGET = re.compile(r"CBN_P1ES_(BASE|TRIAL|FAULT|RECOVERY)_20261026_[0-9a-f]{8}\Z")
UNITS = ("ES-B000", "ES-B001")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def release():
    value = json.loads((PACKAGE / "release.json").read_text(encoding="utf-8"))
    if value["version"] != VERSION or tuple(u["id"] for u in value["units"]) != UNITS:
        raise ValueError("ES_release_version_or_units")
    for name, expected in value["inputs"].items():
        if digest(ROOT / name) != expected:
            raise ValueError("ES_release_input_changed")
    return value


def identity(cursor):
    result = target_identity(cursor)
    result["created_at"] = cursor.execute(
        "SELECT CONVERT(varchar(40),create_date,126) FROM sys.databases WHERE database_id=DB_ID()"
    ).fetchval()
    return result


def guard(cursor, expected):
    actual = identity(cursor)
    if (
        actual != expected
        or not TARGET.fullmatch(actual["database"])
        or (actual["engine"], actual["compatibility"]) != (15, 150)
    ):
        raise ValueError("ES_target_identity")
    if tuple(
        cursor.execute(
            "SELECT is_trustworthy_on,is_db_chaining_on FROM sys.databases WHERE database_id=DB_ID()"
        ).fetchone()
    ) != (0, 0):
        raise ValueError("ES_unsafe_chaining")
    return actual


def shape(cursor):
    raw = metadata(cursor)
    return sha(
        {
            "model": snapshot(cursor),
            "schemas": raw["schemas"],
            "properties": raw["properties"],
            "owners": raw["object_owners"],
        }
    )


def verify_package_catalog(cursor):
    expected = json.loads(
        (PACKAGE / "expected_catalog.json").read_text(encoding="utf-8")
    )
    result = compare(snapshot(cursor, omit_journal=True), expected)
    if not result["passed"]:
        raise ValueError(
            "ES_catalog_model_drift:" + ",".join(result["differing_sections"])
        )
    return result


def batches(text):
    """Restricted SQLCMD GO splitter. Delimiters inside SQL literals are data."""
    current = []
    result = []
    quote = None
    block = 0
    for line in text.splitlines(keepends=True):
        if (
            quote is None
            and not block
            and re.fullmatch(r"\s*GO\s*(?:--[^\r\n]*)?\r?\n?", line, re.I)
        ):
            if "".join(current).strip():
                result.append("".join(current))
                current = []
            continue
        if (
            quote is None
            and not block
            and (re.match(r"\s*:", line) or re.match(r"\s*GO\s+\d", line, re.I))
        ):
            raise ValueError("ES_unsupported_SQLCMD_directive")
        current.append(line)
        i = 0
        while i < len(line):
            pair = line[i : i + 2]
            char = line[i]
            if block:
                if pair == "/*":
                    block += 1
                    i += 2
                    continue
                if pair == "*/":
                    block -= 1
                    i += 2
                    continue
            elif quote:
                close = "]" if quote == "[" else quote
                if char == close:
                    if pair == close * 2:
                        i += 2
                        continue
                    quote = None
            else:
                if pair == "--":
                    break
                if pair == "/*":
                    block = 1
                    i += 2
                    continue
                if char in {"'", '"', "["}:
                    quote = char
            i += 1
    if quote or block:
        raise ValueError("ES_unterminated_SQL_literal")
    if "".join(current).strip():
        result.append("".join(current))
    return result


def wal_events(path):
    if not Path(path).exists():
        return []
    events = []
    previous = "0" * 64
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        recorded = event.pop("hash")
        if event["previous"] != previous or sha(event) != recorded:
            raise ValueError("ES_WAL_integrity")
        previous = recorded
        events.append({**event, "hash": recorded})
    return events


def receipt(path, event):
    events = wal_events(path)
    previous = events[-1]["hash"] if events else "0" * 64
    value = {**event, "previous": previous}
    value["hash"] = sha(value)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    with os.fdopen(descriptor, "a", encoding="utf-8") as output:
        output.write(json.dumps(value, sort_keys=True) + "\n")
        output.flush()
        os.fsync(output.fileno())


def pending_wal(events):
    terminal = {"COMMITTED", "RECONCILED_COMMITTED", "RECONCILED_NOT_APPLIED"}
    return [
        v
        for v in events
        if v["event"] == "STARTED"
        and not any(
            x.get("attempt") == v["attempt"] and x["event"] in terminal for x in events
        )
    ]


def append(cursor, actual, unit, attempt, event, manifest, before, after=None):
    cursor.execute(
        "INSERT crm_meta.MigrationJournal(AttemptId,UnitId,EventKind,ReleaseId,ToolVersion,ManifestSha256,UnitSha256,ShapeVersion,TargetSha256,BeforeShapeSha256,AfterShapeSha256,EvidenceRef,ApprovalRef,BackupRef,PrincipalRef,SuccessKey) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        str(attempt),
        unit["id"],
        event,
        VERSION,
        "P1-ES-explicit-v1",
        bytes.fromhex(manifest),
        bytes.fromhex(unit["sha256"]),
        "p1-es-full-catalog-v1",
        bytes.fromhex(sha(actual)),
        bytes.fromhex(before),
        bytes.fromhex(after) if after else None,
        "P1-ES-SQL2019",
        "owner-20261026",
        "native-restored-before-first-apply",
        ACTOR,
        unit["id"] if event == "COMMITTED" else None,
    )


def journal_exists(cursor):
    return (
        cursor.execute("SELECT OBJECT_ID('crm_meta.MigrationJournal','U')").fetchval()
        is not None
    )


def success(cursor, unit):
    return (
        cursor.execute(
            "SELECT ManifestSha256,UnitSha256,TargetSha256,AfterShapeSha256 FROM crm_meta.MigrationJournal WHERE SuccessKey=?",
            unit["id"],
        ).fetchone()
        if journal_exists(cursor)
        else None
    )


def success_matches(row, manifest, unit, actual):
    if not row or tuple(bytes(v).hex() for v in row[:3]) != (
        manifest,
        unit["sha256"],
        sha(actual),
    ):
        raise ValueError("ES_committed_bytes_or_target_conflict")


def enter(connection, expected):
    if connection.autocommit is not True:
        raise ValueError("ES_durable_STARTED_requires_autocommit")
    cursor = connection.cursor()
    actual = guard(cursor, expected)
    cursor.execute(
        "EXEC sys.sp_set_session_context @key=N'CBN_ES_TARGET',@value=?",
        actual["database"],
    )
    cursor.execute("EXECUTE AS USER=N'cbn_es_migrator_p1'")
    try:
        acquire(cursor, "crm.schema.migrate.v1", "Session")
        acquire(cursor, "crm.local.commit", "Session")
    except BaseException:
        leave(cursor)
        raise
    return cursor, actual


def leave(cursor):
    for resource in ("crm.local.commit", "crm.schema.migrate.v1"):
        with suppress(Exception):
            cursor.execute(
                "EXEC sys.sp_releaseapplock @Resource=?,@LockOwner='Session'", resource
            )
    with suppress(Exception):
        cursor.execute("REVERT")


def apply(connection, expected, wal, *, fault=None):
    package = release()
    manifest = digest(PACKAGE / "release.json")
    cursor, actual = enter(connection, expected)
    try:
        if pending_wal(wal_events(wal)):
            raise ValueError("ES_independent_reconciliation_required")
        if journal_exists(cursor):
            unresolved = cursor.execute(
                "SELECT COUNT(*) FROM crm_meta.MigrationJournal s WHERE EventKind='STARTED' AND NOT EXISTS(SELECT 1 FROM crm_meta.MigrationJournal e WHERE e.AttemptId=s.AttemptId AND e.EventKind IN('COMMITTED','RECONCILED_COMMITTED','RECONCILED_NOT_APPLIED'))"
            ).fetchval()
            if unresolved:
                raise ValueError("ES_SQL_reconciliation_required")
            committed = [
                r[0]
                for r in cursor.execute(
                    "SELECT UnitId FROM crm_meta.MigrationJournal WHERE SuccessKey IS NOT NULL ORDER BY EventId"
                ).fetchall()
            ]
            if committed != list(UNITS[: len(committed)]):
                raise ValueError("ES_history_vector")
            if committed:
                last = success(cursor, package["units"][len(committed) - 1])
                if bytes(last[3]).hex() != shape(cursor):
                    raise ValueError("ES_catalog_drift")
        elif cursor.execute(
            "SELECT COUNT(*) FROM sys.objects WHERE is_ms_shipped=0"
        ).fetchval():
            raise ValueError("ES_unrecognized_existing_objects")
        applied = 0
        for unit in package["units"]:
            row = success(cursor, unit)
            if row:
                success_matches(row, manifest, unit, actual)
                continue
            before = shape(cursor)
            attempt = str(uuid4())
            start = {
                "unit": unit["id"],
                "attempt": attempt,
                "event": "STARTED",
                "target": sha(actual),
                "manifest": manifest,
                "unit_sha256": unit["sha256"],
                "before": before,
            }
            receipt(wal, start)
            if journal_exists(cursor):
                append(cursor, actual, unit, attempt, "STARTED", manifest, before)
            cursor.execute("BEGIN TRANSACTION")
            try:
                for batch in batches(
                    (PACKAGE / unit["file"]).read_text(encoding="utf-8")
                ):
                    cursor.execute(batch)
                    while cursor.nextset():
                        pass
                    if (
                        fault == unit["id"] + ":ddl_error"
                        and "CREATE TABLE [dbo].[CRMContacto]" in batch
                    ):
                        cursor.execute("CREATE TABLE dbo.P1_Controlled_Syntax_Error(")
                if unit["id"] == "ES-B000":
                    if [
                        (r[0], r[1])
                        for r in cursor.execute(
                            "SELECT SCHEMA_NAME(schema_id),name FROM sys.tables WHERE is_ms_shipped=0"
                        ).fetchall()
                    ] != [("crm_meta", "MigrationJournal")]:
                        raise ValueError("ES_bootstrap_partition")
                else:
                    verify_package_catalog(cursor)
                after = shape(cursor)
                if fault == unit["id"] + ":connection_loss_before_commit":
                    connection.close()
                    raise RuntimeError("ES_controlled_connection_loss")
                if fault == unit["id"] + ":before_commit":
                    raise RuntimeError("ES_controlled_precommit_fault")
                append(
                    cursor, actual, unit, attempt, "COMMITTED", manifest, before, after
                )
                cursor.execute("COMMIT")
                if fault == unit["id"] + ":after_commit":
                    raise RuntimeError("ES_controlled_commit_ack_lost")
            except BaseException:
                with suppress(Exception):
                    cursor.execute("IF @@TRANCOUNT>0 ROLLBACK")
                receipt(
                    wal,
                    {
                        "unit": unit["id"],
                        "attempt": attempt,
                        "event": "FAILED_OR_UNCERTAIN",
                    },
                )
                raise
            receipt(
                wal,
                {
                    "unit": unit["id"],
                    "attempt": attempt,
                    "event": "COMMITTED",
                    "after": after,
                },
            )
            applied += 1
        return {
            "status": "committed" if applied else "noop",
            "applied_units": applied,
            "shape_sha256": shape(cursor),
        }
    finally:
        leave(cursor)


def reconcile(connection, expected, wal):
    """Caller must discard the failed connection and establish a fresh one."""
    package = release()
    manifest = digest(PACKAGE / "release.json")
    cursor, actual = enter(connection, expected)
    try:
        pending = pending_wal(wal_events(wal))
        results = []
        for event in pending:
            unit = next(u for u in package["units"] if u["id"] == event["unit"])
            if (event["target"], event["manifest"], event["unit_sha256"]) != (
                sha(actual),
                manifest,
                unit["sha256"],
            ):
                raise ValueError("ES_WAL_binding_conflict")
            row = success(cursor, unit)
            current = shape(cursor)
            if row:
                success_matches(row, manifest, unit, actual)
                if bytes(row[3]).hex() != current:
                    raise ValueError("ES_recovery_required_after_commit")
                status = "RECONCILED_COMMITTED"
            elif current == event["before"]:
                status = "RECONCILED_NOT_APPLIED"
            else:
                raise ValueError("ES_recovery_required_unknown_shape")
            if journal_exists(cursor):
                append(
                    cursor,
                    actual,
                    unit,
                    event["attempt"],
                    status,
                    manifest,
                    event["before"],
                    current if row else None,
                )
            receipt(
                wal, {"unit": unit["id"], "attempt": event["attempt"], "event": status}
            )
            results.append(status)
        return {"reconciled": results}
    finally:
        leave(cursor)
