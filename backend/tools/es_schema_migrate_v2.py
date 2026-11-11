"""Explicit SQL2019-only Spanish baseline. Never invoked by application startup.

The imported 98-table artifact is immutable. This new release adds one journal
in a separate schema and runs reviewed DDL under a narrowed, loginless actor.
Uncertain commits are reconciled only through an independent fresh connection.
"""

import hashlib
import json
import os
import re
import sys
from contextlib import suppress
from pathlib import Path
from uuid import UUID, uuid4

from app.parity_channels.catalog import metadata
from tools.cbn_foundation import acquire, target_identity
from tools.es_schema_catalog_v2 import compare, snapshot
from tools.foundation_snapshot import records, sha

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "backend/migrations/cbn_spanish_schema_v2"
VERSION = "cbn-spanish-baseline-v2"
ACTOR = "cbn_es_migrator_p1_v2"
TARGET = re.compile(r"CBN_P1ES_(BASE|TRIAL|FAULT|RECOVERY)_20261026_[0-9a-f]{8}\Z")
UNITS = ("ES-B000", "ES-B001")

MANIFEST_KEYS = {
    "academic_DML",
    "compatibility",
    "CRM_tables",
    "version",
    "journal_tables_added",
    "expected_total_tables",
    "inputs",
    "engine_major",
    "runtime_redirect",
    "units",
    "source_archive_sha256",
    "scope",
    "parent_C13_sha256",
    "academic_structure_tables",
    "package_tables",
    "automatic_startup_DDL",
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def release(approved_manifest_sha256):
    raw = (PACKAGE / "release.json").read_bytes()
    if (
        not isinstance(approved_manifest_sha256, str)
        or not re.fullmatch(r"[0-9a-f]{64}", approved_manifest_sha256)
        or hashlib.sha256(raw).hexdigest() != approved_manifest_sha256
    ):
        raise ValueError("ES_unapproved_manifest")
    if len(raw) > 65536:
        raise ValueError("ES_manifest_size")

    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("ES_duplicate_manifest_key")
            value[key] = item
        return value

    value = json.loads(raw, object_pairs_hook=unique)
    names = {
        "ES_B000_journal.sql",
        "ES_B001_schema.sql",
        "expected_catalog.json",
        "table_map.json",
        "source_creation.sql",
        "source_verify.sql",
    }
    external = {
        "backend/tools/es_schema_migrate_v2.py",
        "backend/tools/es_schema_catalog_v2.py",
        "backend/migrations/cbn_foundation/B000_journal.sql",
    }
    expected_inputs = {
        str((PACKAGE / name).relative_to(ROOT)).replace("\\", "/") for name in names
    } | external
    if (
        set(value) != MANIFEST_KEYS
        or value["version"] != VERSION
        or value["engine_major"] != 15
        or value["compatibility"] != 150
    ):
        raise ValueError("ES_release_shape_or_version")
    if (
        value["source_archive_sha256"]
        != "f6a8468291c022b85b8c953cbcf6291d384258115fc443698be0b6f35ca69b40"
        or value["expected_total_tables"] != 99
        or value["academic_DML"] is not False
        or value["automatic_startup_DDL"] is not False
        or value["runtime_redirect"] is not False
    ):
        raise ValueError("ES_release_scope")
    if (
        (
            value["package_tables"],
            value["CRM_tables"],
            value["academic_structure_tables"],
            value["journal_tables_added"],
        )
        != (98, 68, 30, 1)
        or value["scope"] != "new_explicitly_restored_SQL2019_targets_only"
        or value["parent_C13_sha256"]
        != "c55373d5c9a517f1691e9c3cb528336c8615b933253585902f0650cc8b1cfb75"
    ):
        raise ValueError("ES_release_partition_or_parent")
    if type(value["inputs"]) is not dict or set(value["inputs"]) != expected_inputs:
        raise ValueError("ES_exact_input_set")
    if type(value["units"]) is not list or len(value["units"]) != 2:
        raise ValueError("ES_release_units")
    for unit, uid, name in zip(
        value["units"],
        UNITS,
        ("ES_B000_journal.sql", "ES_B001_schema.sql"),
        strict=True,
    ):
        if (
            type(unit) is not dict
            or set(unit) != {"id", "file", "sha256", "source", "normalized_body_sha256"}
            or unit["id"] != uid
            or unit["file"] != name
        ):
            raise ValueError("ES_unit_path_or_shape")
        path = PACKAGE / name
        key = path.relative_to(ROOT).as_posix()
        if unit["sha256"] != value["inputs"][key] or unit["sha256"] != digest(path):
            raise ValueError("ES_unit_bytes_conflict")
        ddl = path.read_text(encoding="utf-8")
        marker = "-- P1_ES_DDL_BODY_BEGIN\n"
        if (
            ddl.count(marker) != 1
            or hashlib.sha256(ddl.split(marker, 1)[1].encode()).hexdigest()
            != unit["normalized_body_sha256"]
        ):
            raise ValueError("ES_DDL_body_integrity")
        source = (
            "backend/migrations/cbn_foundation/B000_journal.sql"
            if uid == "ES-B000"
            else "source_creation.sql"
        )
        if unit["source"] != source:
            raise ValueError("ES_unit_source")
    for name, expected in value["inputs"].items():
        if (
            not isinstance(expected, str)
            or not re.fullmatch(r"[0-9a-f]{64}", expected)
            or digest(ROOT / name) != expected
        ):
            raise ValueError("ES_release_input_changed")
    if (
        digest(PACKAGE / "source_creation.sql")
        != "9ea58376e0c8739188d52b78bfa22e85efc9eaa79fa917e4e143985ae09f8cb4"
    ):
        raise ValueError("ES_original_creation_changed")
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
    return sha({"model": snapshot(cursor), "catalog": metadata(cursor)})


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


WAL_BINDING = (
    "unit",
    "attempt",
    "version",
    "target",
    "manifest",
    "unit_sha256",
    "before",
)
TERMINAL = {"COMMITTED", "RECONCILED_COMMITTED", "RECONCILED_NOT_APPLIED"}


def wal_state(events):
    states = {}
    file_binding = None
    for event in events:
        if type(event) is not dict:
            raise ValueError("ES_WAL_record_shape")
        kind = event.get("event")
        allowed = set(WAL_BINDING) | {"event", "previous", "hash"}
        if kind in {"COMMITTED", "RECONCILED_COMMITTED"}:
            allowed.add("after")
        if not set(WAL_BINDING) | {"event"} <= set(event) or not set(event) <= allowed:
            raise ValueError("ES_WAL_record_shape")
        if (
            kind not in TERMINAL | {"STARTED", "FAILED_OR_UNCERTAIN"}
            or event["unit"] not in UNITS
            or event["version"] != VERSION
        ):
            raise ValueError("ES_WAL_event_kind")
        binding = tuple(event[k] for k in ("version", "target", "manifest"))
        if file_binding is not None and binding != file_binding:
            raise ValueError("ES_WAL_file_binding")
        file_binding = binding
        try:
            if str(UUID(event["attempt"])) != event["attempt"]:
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            raise ValueError("ES_WAL_attempt_id") from None
        for key in ("target", "manifest", "unit_sha256", "before") + (
            ("after",) if kind in {"COMMITTED", "RECONCILED_COMMITTED"} else ()
        ):
            if type(event.get(key)) is not str or not re.fullmatch(
                r"[0-9a-f]{64}", event[key]
            ):
                raise ValueError("ES_WAL_hash_field")
        attempt = event["attempt"]
        prior = states.get(attempt)
        if kind == "STARTED":
            if prior:
                raise ValueError("ES_WAL_duplicate_start")
            states[attempt] = {"start": event, "status": "STARTED"}
        else:
            if prior is None or prior["status"] in TERMINAL:
                raise ValueError("ES_WAL_terminal_order")
            if any(event[k] != prior["start"][k] for k in WAL_BINDING):
                raise ValueError("ES_WAL_cross_attempt_binding")
            if kind == "FAILED_OR_UNCERTAIN" and prior["status"] != "STARTED":
                raise ValueError("ES_WAL_uncertain_order")
            prior["status"] = kind
    return states


def wal_events(path):
    if not Path(path).exists():
        return []
    if Path(path).stat().st_size > 2_000_000:
        raise ValueError("ES_WAL_size")
    events = []
    previous = "0" * 64
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        recorded = event.pop("hash")
        if event["previous"] != previous or sha(event) != recorded:
            raise ValueError("ES_WAL_integrity")
        previous = recorded
        events.append({**event, "hash": recorded})
    wal_state(events)
    return events


def receipt(path, event):
    events = wal_events(path)
    wal_state([*events, event])
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
    return [
        value["start"]
        for value in wal_state(events).values()
        if value["status"] not in TERMINAL
    ]


def terminal_receipt(path, start, event, after=None):
    value = {key: start[key] for key in WAL_BINDING}
    value["event"] = event
    if after is not None:
        value["after"] = after
    receipt(path, value)


def validate_wal_bindings(events, actual, manifest, package, history):
    units = {u["id"]: u for u in package["units"]}
    states = wal_state(events)
    for attempt, state in states.items():
        start = state["start"]
        unit = units[start["unit"]]
        if (start["target"], start["manifest"], start["unit_sha256"]) != (
            sha(actual),
            manifest,
            unit["sha256"],
        ):
            raise ValueError("ES_WAL_binding_conflict")
        sql = history.get(attempt)
        if sql and (
            sql["start"]["UnitId"] != unit["id"]
            or bytes(sql["start"]["BeforeShapeSha256"]).hex() != start["before"]
        ):
            raise ValueError("ES_SQL_WAL_attempt_binding")
        if state["status"] in {"COMMITTED", "RECONCILED_COMMITTED"}:
            if not sql or sql["status"] not in {"COMMITTED", "RECONCILED_COMMITTED"}:
                raise ValueError("ES_WAL_commit_without_SQL_proof")
            terminal = next(e for e in reversed(events) if e["attempt"] == attempt)
            if terminal["after"] != bytes(sql["commit"]["AfterShapeSha256"]).hex():
                raise ValueError("ES_WAL_commit_shape")
        elif state["status"] == "RECONCILED_NOT_APPLIED":
            if sql and sql["status"] != "RECONCILED_NOT_APPLIED":
                raise ValueError("ES_WAL_not_applied_SQL_conflict")
            if sql is None and unit["id"] != "ES-B000":
                raise ValueError("ES_WAL_not_applied_without_SQL_proof")


def append(cursor, actual, unit, attempt, event, manifest, before, after=None):
    cursor.execute(
        "INSERT crm_meta.MigrationJournal(AttemptId,UnitId,EventKind,ReleaseId,ToolVersion,ManifestSha256,UnitSha256,ShapeVersion,TargetSha256,BeforeShapeSha256,AfterShapeSha256,EvidenceRef,ApprovalRef,BackupRef,PrincipalRef,SuccessKey) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        str(attempt),
        unit["id"],
        event,
        VERSION,
        "P1-ES-explicit-v2",
        bytes.fromhex(manifest),
        bytes.fromhex(unit["sha256"]),
        "p1-es-full-catalog-v2",
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
            "SELECT ManifestSha256,UnitSha256,TargetSha256,AfterShapeSha256,AttemptId,EventId,EventKind,ReleaseId,ToolVersion,ShapeVersion,BeforeShapeSha256,SuccessKey FROM crm_meta.MigrationJournal WHERE SuccessKey=?",
            unit["id"],
        ).fetchone()
        if journal_exists(cursor)
        else None
    )


def success_matches(row, manifest, unit, actual, attempt=None):
    if (
        not row
        or tuple(bytes(v).hex() for v in row[:3])
        != (manifest, unit["sha256"], sha(actual))
        or tuple(row[6:10])
        != ("COMMITTED", VERSION, "P1-ES-explicit-v2", "p1-es-full-catalog-v2")
        or row[10] is None
        or row[11] != unit["id"]
    ):
        raise ValueError("ES_committed_bytes_or_target_conflict")
    if attempt is not None and str(row[4]).lower() != attempt:
        raise ValueError("ES_committed_attempt_conflict")


def sql_history(cursor, package, manifest, actual):
    if not journal_exists(cursor):
        return {}
    events = records(cursor, "SELECT * FROM crm_meta.MigrationJournal ORDER BY EventId")
    if len(events) > 10000:
        raise ValueError("ES_history_limit")
    attempts = {}
    units = {u["id"]: u for u in package["units"]}
    for row in events:
        unit = units.get(row["UnitId"])
        attempt = str(row["AttemptId"]).lower()
        kind = row["EventKind"]
        if (
            unit is None
            or row["ReleaseId"] != VERSION
            or row["ToolVersion"] != "P1-ES-explicit-v2"
            or row["ShapeVersion"] != "p1-es-full-catalog-v2"
            or row["PrincipalRef"] != ACTOR
            or row["EvidenceRef"] != "P1-ES-SQL2019"
            or row["ApprovalRef"] != "owner-20261026"
            or row["BackupRef"] != "native-restored-before-first-apply"
            or row["ErrorCode"] is not None
        ):
            raise ValueError("ES_history_header")
        if (
            tuple(
                bytes(row[k]).hex()
                for k in ("ManifestSha256", "UnitSha256", "TargetSha256")
            )
            != (manifest, unit["sha256"], sha(actual))
            or row["BeforeShapeSha256"] is None
        ):
            raise ValueError("ES_history_binding")
        state = attempts.get(attempt)
        if state is None:
            if kind == "STARTED" and unit["id"] == "ES-B001":
                state = {"start": row, "status": "STARTED", "commit": None}
                attempts[attempt] = state
            elif kind == "COMMITTED" and unit["id"] == "ES-B000":
                state = {"start": row, "status": "STARTED", "commit": None}
                attempts[attempt] = state
            else:
                raise ValueError("ES_history_start_order")
        elif row["UnitId"] != state["start"]["UnitId"] or bytes(
            row["BeforeShapeSha256"]
        ) != bytes(state["start"]["BeforeShapeSha256"]):
            raise ValueError("ES_history_attempt_binding")
        if kind == "STARTED":
            if (
                row is not state["start"]
                or row["AfterShapeSha256"] is not None
                or row["SuccessKey"] is not None
            ):
                raise ValueError("ES_history_duplicate_start")
        elif kind == "COMMITTED":
            if (
                state["status"] != "STARTED"
                or row["SuccessKey"] != unit["id"]
                or row["AfterShapeSha256"] is None
            ):
                raise ValueError("ES_history_commit_order")
            state["status"] = "COMMITTED"
            state["commit"] = row
        elif kind == "RECONCILED_COMMITTED":
            if (
                state["status"] != "COMMITTED"
                or row["SuccessKey"] is not None
                or bytes(row["AfterShapeSha256"] or b"")
                != bytes(state["commit"]["AfterShapeSha256"])
            ):
                raise ValueError("ES_history_commit_confirmation")
            state["status"] = "RECONCILED_COMMITTED"
        elif kind == "RECONCILED_NOT_APPLIED":
            if (
                state["status"] != "STARTED"
                or row["AfterShapeSha256"] is not None
                or row["SuccessKey"] is not None
            ):
                raise ValueError("ES_history_not_applied_order")
            state["status"] = "RECONCILED_NOT_APPLIED"
        else:
            raise ValueError("ES_history_event_kind")
        state["last"] = row
    committed = [r for r in events if r["SuccessKey"] is not None]
    if [r["UnitId"] for r in committed] != list(UNITS[: len(committed)]):
        raise ValueError("ES_history_vector")
    if committed:
        first = committed[0]
        for state in attempts.values():
            if state["start"]["UnitId"] == "ES-B001" and bytes(
                state["start"]["BeforeShapeSha256"]
            ) != bytes(first["AfterShapeSha256"]):
                raise ValueError("ES_history_shape_chain")
    return attempts


def enter(connection, expected):
    if connection.autocommit is not True:
        raise ValueError("ES_durable_STARTED_requires_autocommit")
    cursor = connection.cursor()
    if cursor.execute("SELECT @@TRANCOUNT").fetchval() != 0:
        cursor.close()
        raise ValueError("ES_caller_transaction_not_owned")
    actual = guard(cursor, expected)
    owner = cursor.execute(
        "SELECT ORIGINAL_LOGIN(),SUSER_SNAME(),USER_NAME(),HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','CONTROL')"
    ).fetchone()
    if owner[0] != owner[1] or owner[2] != "dbo" or owner[3] != 1:
        cursor.close()
        raise ValueError("ES_unimpersonated_preparer_required")
    try:
        cursor.execute(
            "EXEC sys.sp_set_session_context @key=N'CBN_ES_TARGET',@value=?",
            actual["database"],
        )
        cursor.execute("EXECUTE AS USER=N'cbn_es_migrator_p1_v2'")
        if (
            cursor.execute(
                "SELECT HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','CONTROL')"
            ).fetchval()
            != 0
            or cursor.execute("SELECT IS_MEMBER('db_owner')").fetchval() != 0
        ):
            raise ValueError("ES_migrator_privilege_overlay")
        acquire(cursor, "crm.schema.migrate.v1", "Session")
        acquire(cursor, "crm.local.commit", "Session")
    except BaseException:
        leave(cursor, connection)
        raise
    return cursor, actual


def leave(cursor, connection):
    failed = False
    for resource in ("crm.local.commit", "crm.schema.migrate.v1"):
        try:
            result = cursor.execute(
                "DECLARE @r int;EXEC @r=sys.sp_releaseapplock @Resource=?,@LockOwner='Session';SELECT @r",
                resource,
            ).fetchval()
            if result < 0:
                failed = True
        except Exception:
            failed = True
    try:
        cursor.execute("REVERT")
        state = cursor.execute(
            "SELECT @@TRANCOUNT,USER_NAME(),ORIGINAL_LOGIN(),SUSER_SNAME()"
        ).fetchone()
        if state[0] != 0 or state[1] != "dbo" or state[2] != state[3]:
            failed = True
    except Exception:
        failed = True
    try:
        cursor.close()
    except Exception:
        failed = True
    if failed:
        with suppress(Exception):
            connection.close()
        if sys.exc_info()[0] is None:
            raise ValueError("ES_cleanup_connection_discarded")


def apply(
    connection,
    expected,
    wal,
    *,
    approved_manifest_sha256,
    approved_initial_shape_sha256=None,
    fault=None,
):
    package = release(approved_manifest_sha256)
    if not isinstance(approved_initial_shape_sha256, str) or not re.fullmatch(
        r"[0-9a-f]{64}", approved_initial_shape_sha256
    ):
        raise ValueError("ES_approved_initial_catalog_required")
    manifest = digest(PACKAGE / "release.json")
    cursor, actual = enter(connection, expected)
    try:
        events = wal_events(wal)
        history = sql_history(cursor, package, manifest, actual)
        validate_wal_bindings(events, actual, manifest, package, history)
        if pending_wal(events):
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
        if not journal_exists(cursor):
            if metadata(cursor)["user_types"]:
                raise ValueError("ES_unrecognized_initial_user_types")
            if shape(cursor) != approved_initial_shape_sha256:
                raise ValueError("ES_initial_catalog_not_approved")
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
                "version": VERSION,
                "target": sha(actual),
                "manifest": manifest,
                "unit_sha256": unit["sha256"],
                "before": before,
            }
            receipt(wal, start)
            if fault == unit["id"] + ":after_wal_before_SQL_started":
                raise RuntimeError("ES_controlled_WAL_to_SQL_gap")
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
                terminal_receipt(wal, start, "FAILED_OR_UNCERTAIN")
                raise
            terminal_receipt(wal, start, "COMMITTED", after)
            applied += 1
        return {
            "status": "committed" if applied else "noop",
            "applied_units": applied,
            "shape_sha256": shape(cursor),
        }
    finally:
        leave(cursor, connection)


def reconcile(connection, expected, wal, *, approved_manifest_sha256, fault=None):
    package = release(approved_manifest_sha256)
    manifest = digest(PACKAGE / "release.json")
    cursor, actual = enter(connection, expected)
    try:
        events = wal_events(wal)
        pending = pending_wal(events)
        history = sql_history(cursor, package, manifest, actual)
        results = []
        validate_wal_bindings(events, actual, manifest, package, history)
        for event in pending:
            unit = next(u for u in package["units"] if u["id"] == event["unit"])
            if (event["target"], event["manifest"], event["unit_sha256"]) != (
                sha(actual),
                manifest,
                unit["sha256"],
            ):
                raise ValueError("ES_WAL_binding_conflict")
            sql = history.get(event["attempt"])
            row = success(cursor, unit)
            current = shape(cursor)
            if sql and (
                sql["start"]["UnitId"] != unit["id"]
                or bytes(sql["start"]["BeforeShapeSha256"]).hex() != event["before"]
            ):
                raise ValueError("ES_SQL_WAL_attempt_binding")
            already_confirmed = False
            if sql and sql["status"] == "RECONCILED_NOT_APPLIED":
                status = "RECONCILED_NOT_APPLIED"
                after = None
                already_confirmed = True
            elif row:
                success_matches(row, manifest, unit, actual, event["attempt"])
                if bytes(row[3]).hex() != current:
                    raise ValueError("ES_recovery_required_after_commit")
                status = "RECONCILED_COMMITTED"
                after = current
                already_confirmed = bool(
                    sql and sql["status"] == "RECONCILED_COMMITTED"
                )
            elif current == event["before"]:
                status = "RECONCILED_NOT_APPLIED"
                after = None
            else:
                raise ValueError("ES_recovery_required_unknown_shape")
            if unit["id"] == "ES-B001" and sql is None:
                boot = success(cursor, package["units"][0])
                success_matches(boot, manifest, package["units"][0], actual)
                if bytes(boot[3]).hex() != event["before"]:
                    raise ValueError("ES_pending_schema_without_verified_bootstrap")
                append(
                    cursor,
                    actual,
                    unit,
                    event["attempt"],
                    "STARTED",
                    manifest,
                    event["before"],
                )
                if fault == "after_recovered_SQL_started":
                    raise RuntimeError("ES_controlled_recovered_STARTED_ack_lost")
            if journal_exists(cursor) and not already_confirmed:
                append(
                    cursor,
                    actual,
                    unit,
                    event["attempt"],
                    status,
                    manifest,
                    event["before"],
                    after,
                )
            terminal_receipt(wal, event, status, after)
            results.append(status)
        return {"reconciled": results}
    finally:
        leave(cursor, connection)
