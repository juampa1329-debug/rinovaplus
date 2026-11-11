"""Explicit restored-copy foundation runner. Importing it performs no IO or SQL."""

import hashlib
import json
import re
import uuid
from pathlib import Path

from tools.foundation_snapshot import (
    PRINCIPAL,
    SHAPE_VERSION,
    core_signature,
    metadata,
    records,
    sha,
)

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "backend/migrations/cbn_foundation"
UNITS = ("CBN-B000", "CBN-B001", "CBN-B006")
SQL_FILES = ("B000_journal.sql", "B001_core.sql", "B006_configuration.sql")
TOOL_FILES = (
    "backend/tools/cbn_foundation.py",
    "backend/tools/foundation_snapshot.py",
    "backend/tools/foundation_contract.py",
)
LEGACY_FILES = (
    "backend/migrations/001_local_crm.sql",
    "backend/migrations/006_crm_configuration.sql",
    "docs/adaptation/sql/inventory.json",
)
TOOL_VERSION = "SQL-C3-v2"
TARGET_NAME = re.compile(r"CBN_C3_(REF|TRIAL)_20261024_[a-f0-9]{8}\Z")


class Blocked(RuntimeError):
    pass


class CommitUnknown(Blocked):
    pass


def require(condition, code):
    if not condition:
        raise Blocked(code)


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def drain(cursor):
    while cursor.nextset():
        pass


def target_identity(cursor):
    row = cursor.execute("""SELECT DB_NAME(),DB_ID(),
      CONVERT(nvarchar(128),SERVERPROPERTY('MachineName')),
      CONVERT(nvarchar(128),SERVERPROPERTY('ServerName')),
      CONVERT(nvarchar(128),SERVERPROPERTY('InstanceName')),
      CONVERT(int,SERVERPROPERTY('ProductMajorVersion')),
      (SELECT compatibility_level FROM sys.databases WHERE database_id=DB_ID()),
      CONVERT(nvarchar(128),DATABASEPROPERTYEX(DB_NAME(),'Collation')),
      (SELECT CONVERT(varchar(33),create_date,126)
       FROM sys.databases WHERE database_id=DB_ID())
      """).fetchone()
    return dict(
        zip(
            (
                "database",
                "database_id",
                "machine",
                "server",
                "instance",
                "engine",
                "compatibility",
                "collation",
                "created_at",
            ),
            row,
            strict=True,
        )
    )


def guard(cursor, ticket):
    require(
        bool(TARGET_NAME.fullmatch(ticket["identity"]["database"])),
        "restored_name_required",
    )
    require(ticket["scope"] == "restored_rehearsal_only", "scope_not_authorized")
    require(
        ticket["identity"]["engine"] == 16
        and ticket["identity"]["compatibility"] == 160,
        "local_engine_contract_required",
    )
    require(target_identity(cursor) == ticket["identity"], "target_identity_changed")
    row = cursor.execute("""SELECT USER_NAME(),
      CONVERT(nvarchar(128),SESSION_CONTEXT(N'CBN_C3_TARGET')),
      HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','VIEW DEFINITION'),
      IS_MEMBER('db_owner'),IS_MEMBER('db_ddladmin'),
      IS_MEMBER('db_datawriter')""").fetchone()
    require(
        tuple(row) == (PRINCIPAL, ticket["identity"]["database"], 1, 0, 0, 0),
        "restricted_principal_required",
    )
    powers = cursor.execute("""SELECT COUNT(*),COALESCE(SUM(CASE WHEN
      COALESCE(HAS_PERMS_BY_NAME(QUOTENAME(s.name)+'.'+QUOTENAME(t.name),
        'OBJECT','ALTER'),1)<>0 OR
      COALESCE(HAS_PERMS_BY_NAME(QUOTENAME(s.name)+'.'+QUOTENAME(t.name),
        'OBJECT','INSERT'),1)<>0 OR
      COALESCE(HAS_PERMS_BY_NAME(QUOTENAME(s.name)+'.'+QUOTENAME(t.name),
        'OBJECT','UPDATE'),1)<>0 OR
      COALESCE(HAS_PERMS_BY_NAME(QUOTENAME(s.name)+'.'+QUOTENAME(t.name),
        'OBJECT','DELETE'),1)<>0
      THEN 1 ELSE 0 END),0) FROM sys.tables t
      JOIN sys.schemas s ON s.schema_id=t.schema_id
      WHERE t.is_ms_shipped=0
      AND s.name NOT IN(N'crm_meta',N'crm',N'crm_config')""").fetchone()
    require(
        tuple(powers) == (ticket["academic_table_count"], 0),
        "academic_permissions_or_visibility",
    )
    require(
        core_signature(cursor, include_data=False)["metadata_sha256"]
        == ticket["core_metadata_sha256"],
        "academic_metadata_changed",
    )
    require(
        not cursor.execute(
            "SELECT 1 FROM sys.triggers WHERE parent_class=0"
        ).fetchone(),
        "database_ddl_trigger_present",
    )
    unexpected = cursor.execute("""SELECT name FROM sys.schemas WHERE
      (name=N'crm' OR name LIKE N'crm[_]%')
      AND name NOT IN(N'crm_meta',N'crm',N'crm_config')""").fetchone()
    require(unexpected is None, "unknown_managed_namespace")


def load_release(directory=PACKAGE):
    directory = Path(directory)
    path = directory / "release.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    require(manifest["scope"] == "restored_rehearsal_only", "release_scope")
    require(
        manifest["engine_major"] == 16
        and manifest["institutional_sql2019_accepted"] is False,
        "release_engine_scope",
    )
    require(manifest["shape_version"] == SHAPE_VERSION, "shape_version")
    require([u["id"] for u in manifest["units"]] == list(UNITS), "unit_vector")
    require([u["file"] for u in manifest["units"]] == list(SQL_FILES), "unit_files")
    require(
        [u["depends_on"] for u in manifest["units"]]
        == [[], [UNITS[0]], [UNITS[0], UNITS[1]]],
        "unit_dependencies",
    )
    for unit in manifest["units"]:
        require(
            file_sha(directory / unit["file"]) == unit["sha256"], "sql_artifact_changed"
        )
    require(
        [r["path"] for r in manifest["tool_files"]] == list(TOOL_FILES),
        "tool_file_vector",
    )
    require(
        [r["path"] for r in manifest["legacy_sources"]] == list(LEGACY_FILES),
        "legacy_file_vector",
    )
    for record in [*manifest["tool_files"], *manifest["legacy_sources"]]:
        require(
            file_sha(ROOT / record["path"]) == record["sha256"], "tool_artifact_changed"
        )
    require(
        file_sha(directory / "expected-shapes.json")
        == manifest["expected_shapes_sha256"],
        "expected_shape_artifact_changed",
    )
    shapes = json.loads(
        (directory / "expected-shapes.json").read_text(encoding="utf-8")
    )
    require(list(shapes) == ["prepared", *UNITS], "expected_prefixes")
    for unit, before in zip(manifest["units"], ["prepared", *UNITS[:-1]], strict=True):
        require(
            unit["before_sha256"] == sha(shapes[before])
            and unit["after_sha256"] == sha(shapes[unit["id"]]),
            "prefix_shape_hash",
        )
    return manifest, shapes, file_sha(path)


class Audit:
    """Append sanitized outcomes outside SQL; protects commit-ACK reconciliation."""

    def __init__(self, path, target_hash):
        self.path, self.target_hash = Path(path), target_hash

    def rows(self):
        if not self.path.exists():
            return []
        entries = [
            json.loads(line)
            for line in self.path.read_text(encoding="utf-8").splitlines()
        ]
        require(
            all(e["target"] == self.target_hash for e in entries),
            "audit_target_mismatch",
        )
        return entries

    def unresolved(self):
        latest = {}
        for entry in self.rows():
            latest[entry["attempt"]] = entry
        return [e for e in latest.values() if e["status"] in {"STARTED", "UNKNOWN"}]

    def add(self, attempt, unit, status):
        import os

        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        value = {
            "target": self.target_hash,
            "attempt": str(attempt),
            "unit": unit,
            "status": status,
        }
        with self.path.open("a", encoding="utf-8") as stream:
            os.chmod(self.path, 0o600)
            stream.write(json.dumps(value) + "\n")
            stream.flush()
            os.fsync(stream.fileno())


def append_event(
    cursor,
    ticket,
    manifest_hash,
    unit,
    attempt,
    kind,
    before,
    after=None,
    *,
    related=None,
    error=None,
    release_id="CBN-foundation-local-v2",
):
    cursor.execute(
        """INSERT crm_meta.MigrationJournal
      (AttemptId,UnitId,EventKind,ReleaseId,ToolVersion,ManifestSha256,UnitSha256,
       ShapeVersion,TargetSha256,BeforeShapeSha256,AfterShapeSha256,EvidenceRef,
       ApprovalRef,BackupRef,PrincipalRef,ErrorCode,SuccessKey,
       RelatedAttemptId,RelatedUnitId)
      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        str(attempt),
        unit["id"],
        kind,
        release_id,
        TOOL_VERSION,
        bytes.fromhex(manifest_hash),
        bytes.fromhex(unit["sha256"]),
        SHAPE_VERSION,
        bytes.fromhex(sha(ticket["identity"])),
        bytes.fromhex(before),
        bytes.fromhex(after) if after else None,
        ticket["evidence_ref"],
        ticket["approval_ref"],
        ticket["backup_ref"],
        PRINCIPAL,
        error,
        unit["id"] if kind == "COMMITTED" else None,
        str(related) if related else None,
        unit["id"] if related else None,
    )


def current_history(cursor, ticket, manifest, manifest_hash):
    if (
        cursor.execute("SELECT OBJECT_ID(N'crm_meta.MigrationJournal',N'U')").fetchval()
        is None
    ):
        return []
    rows = records(
        cursor,
        """SELECT CONVERT(varchar(36),AttemptId) AS attempt,
      UnitId AS unit,EventKind AS kind,
      CONVERT(varchar(64),ManifestSha256,2) AS manifest_hash,
      CONVERT(varchar(64),UnitSha256,2) AS unit_hash,
      CONVERT(varchar(64),TargetSha256,2) AS target_hash,
      CONVERT(varchar(64),AfterShapeSha256,2) AS after_hash,
      CONVERT(varchar(64),BeforeShapeSha256,2) AS before_hash,
      ShapeVersion AS shape_version,PrincipalRef AS principal,
      ReleaseId AS release_id,ToolVersion AS tool_version,SuccessKey AS success_key,
      ErrorCode AS error_code,CONVERT(varchar(36),RelatedAttemptId) AS related_attempt,
      RelatedUnitId AS related_unit,EvidenceRef AS evidence_ref,
      ApprovalRef AS approval_ref,BackupRef AS backup_ref
      FROM crm_meta.MigrationJournal ORDER BY EventId""",
    )
    by_id = {u["id"]: u for u in manifest["units"]}
    for row in rows:
        require(row["unit"] in by_id, "unknown_history_unit")
        require(
            row["manifest_hash"].lower() == manifest_hash
            and row["unit_hash"].lower() == by_id[row["unit"]]["sha256"]
            and row["target_hash"].lower() == sha(ticket["identity"])
            and row["shape_version"] == SHAPE_VERSION
            and row["principal"] == PRINCIPAL,
            "history_artifact_or_target_changed",
        )
        require(
            row["before_hash"] is not None
            and row["before_hash"].lower() == by_id[row["unit"]]["before_sha256"]
            and row["release_id"] == manifest["release_id"]
            and row["tool_version"] == TOOL_VERSION,
            "history_before_or_tool_changed",
        )
        require(
            all(
                row[k] == ticket[k]
                for k in ("evidence_ref", "approval_ref", "backup_ref")
            ),
            "history_evidence_changed",
        )
        require(
            row["kind"]
            in {
                "STARTED",
                "COMMITTED",
                "FAILED_ROLLED_BACK",
                "RECONCILED_COMMITTED",
                "RECONCILED_NOT_APPLIED",
            },
            "history_requires_reconciliation",
        )
        if row["kind"] == "COMMITTED":
            require(
                isinstance(row["after_hash"], str)
                and row["after_hash"].lower() == by_id[row["unit"]]["after_sha256"],
                "history_shape_changed",
            )
            require(
                row["success_key"] == row["unit"] and row["error_code"] is None,
                "history_success_fields_changed",
            )
        else:
            require(row["success_key"] is None, "unexpected_history_success")
        if row["kind"] in {"STARTED", "FAILED_ROLLED_BACK"}:
            require(row["after_hash"] is None, "unexpected_history_after_shape")
            require(
                row["error_code"]
                == (
                    "unit_failed_rolled_back"
                    if row["kind"] == "FAILED_ROLLED_BACK"
                    else None
                ),
                "history_error_code_changed",
            )
        if not row["kind"].startswith("RECONCILED_"):
            require(
                row["related_attempt"] is None and row["related_unit"] is None,
                "unexpected_related_history",
            )
        if row["kind"].startswith("RECONCILED_"):
            expected_hash = by_id[row["unit"]][
                "after_sha256"
                if row["kind"] == "RECONCILED_COMMITTED"
                else "before_sha256"
            ]
            require(
                isinstance(row["after_hash"], str)
                and row["after_hash"].lower() == expected_hash
                and row["related_attempt"] == row["attempt"]
                and row["related_unit"] == row["unit"],
                "history_reconciliation_fields",
            )
    attempts = {}
    for row in rows:
        attempts.setdefault(row["attempt"], []).append(row)
    for attempt_rows in attempts.values():
        require(len({r["unit"] for r in attempt_rows}) == 1, "attempt_unit_changed")
        kinds = tuple(r["kind"] for r in attempt_rows)
        allowed = {
            ("STARTED",),
            ("STARTED", "COMMITTED"),
            ("STARTED", "FAILED_ROLLED_BACK"),
            ("STARTED", "RECONCILED_NOT_APPLIED"),
            ("STARTED", "FAILED_ROLLED_BACK", "RECONCILED_NOT_APPLIED"),
            ("STARTED", "COMMITTED", "RECONCILED_COMMITTED"),
            ("RECONCILED_NOT_APPLIED",),
        }
        if attempt_rows[0]["unit"] == UNITS[0]:
            allowed = {("COMMITTED",), ("COMMITTED", "RECONCILED_COMMITTED")}
        require(kinds in allowed, "invalid_attempt_event_sequence")
    return rows


def validate_data(cursor, prefix):
    if prefix != UNITS[2]:
        return
    rows = cursor.execute(
        "SELECT ConfigurationId,Document,Revision FROM crm_config.Configuration"
    ).fetchmany(2)
    require(
        len(rows) == 1 and rows[0][0] == 1 and rows[0][2] > 0,
        "configuration_singleton_missing",
    )
    try:
        document = json.loads(rows[0][1])
    except (TypeError, ValueError) as error:
        raise Blocked("configuration_document_invalid") from error
    require(
        isinstance(document, dict)
        and set(document) == {"stages", "tags", "inactiveTags", "fields"}
        and all(isinstance(v, list) for v in document.values()),
        "configuration_document_invalid",
    )


def successful_prefix(rows):
    successes = [r["unit"] for r in rows if r["kind"] == "COMMITTED"]
    require(successes == list(UNITS[: len(successes)]), "invalid_history_vector")
    for attempt in {r["attempt"] for r in rows if r["kind"] == "STARTED"}:
        require(
            any(
                r["attempt"] == attempt
                and r["kind"]
                in {"COMMITTED", "FAILED_ROLLED_BACK", "RECONCILED_NOT_APPLIED"}
                for r in rows
            ),
            "incomplete_attempt_requires_reconciliation",
        )
    return successes


def acquire(cursor, resource, owner):
    row = cursor.execute(
        """DECLARE @r int; EXEC @r=sys.sp_getapplock
      @Resource=?,@LockMode='Exclusive',@LockOwner=?,@LockTimeout=5000; SELECT @r""",
        resource,
        owner,
    ).fetchone()
    require(row is not None and row[0] >= 0, "migration_lock_unavailable")


def transaction(cursor):
    cursor.execute("SET XACT_ABORT ON; SET LOCK_TIMEOUT 5000; BEGIN TRANSACTION;")


def rollback(cursor):
    cursor.execute("IF @@TRANCOUNT>0 ROLLBACK TRANSACTION;")


def apply(connection, ticket, audit, *, directory=PACKAGE):
    """Only preapproved restored targets, immutable package and known exact prefixes."""
    manifest, shapes, manifest_hash = load_release(directory)
    require(ticket["kind"] == "TRIAL", "release_trial_target_required")
    require(not audit.unresolved(), "external_unknown_requires_reconciliation")
    cursor = connection.cursor()
    locked = False
    try:
        guard(cursor, ticket)
        require(
            cursor.execute("SELECT @@TRANCOUNT").fetchval() == 0,
            "existing_transaction_refused",
        )
        acquire(cursor, "crm.schema.migrate.v1", "Session")
        locked = True
        require(not audit.unresolved(), "external_unknown_requires_reconciliation")
        guard(cursor, ticket)
        current = metadata(cursor, managed=True)
        require(
            any(current == expected for expected in shapes.values()),
            "entry_shape_drift",
        )
        history = current_history(cursor, ticket, manifest, manifest_hash)
        successes = successful_prefix(history)
        prefix = successes[-1] if successes else "prepared"
        require(current == shapes[prefix], "entry_shape_drift")
        validate_data(cursor, prefix)
        outcomes = []
        for unit in manifest["units"][len(successes) :]:
            attempt = str(uuid.uuid4())
            before = unit["before_sha256"]
            audit.add(attempt, unit["id"], "STARTED")
            if unit["id"] != UNITS[0]:
                transaction(cursor)
                append_event(
                    cursor, ticket, manifest_hash, unit, attempt, "STARTED", before
                )
                try:
                    cursor.execute("COMMIT TRANSACTION;")
                except Exception as error:
                    audit.add(attempt, unit["id"], "UNKNOWN")
                    raise CommitUnknown("audit_commit_outcome_unknown") from error
            transaction(cursor)
            committing = False
            try:
                acquire(cursor, "crm.local.commit", "Transaction")
                guard(cursor, ticket)
                require(
                    sha(metadata(cursor, managed=True)) == before,
                    "unit_entry_shape_drift",
                )
                require(
                    all(dep in successes for dep in unit["depends_on"]),
                    "dependency_missing",
                )
                if unit["id"] == UNITS[2]:
                    require(
                        cursor.execute("SELECT COUNT(*) FROM crm.Contact").fetchval()
                        == 0,
                        "empty_configuration_installation_required",
                    )
                cursor.execute(
                    (Path(directory) / unit["file"]).read_text(encoding="utf-8")
                )
                drain(cursor)
                after = metadata(cursor, managed=True)
                require(after == shapes[unit["id"]], "unit_exit_shape_drift")
                guard(cursor, ticket)
                if unit["id"] == UNITS[2]:
                    row = cursor.execute(
                        "SELECT ConfigurationId,Document,Revision "
                        "FROM crm_config.Configuration"
                    ).fetchone()
                    require(
                        tuple(row)[::2] == (1, 1)
                        and json.loads(row[1])
                        == {"stages": [], "tags": [], "inactiveTags": [], "fields": []},
                        "initial_configuration_mismatch",
                    )
                append_event(
                    cursor,
                    ticket,
                    manifest_hash,
                    unit,
                    attempt,
                    "COMMITTED",
                    before,
                    unit["after_sha256"],
                    release_id=manifest["release_id"],
                )
                committing = True
                cursor.execute("COMMIT TRANSACTION;")
                audit.add(attempt, unit["id"], "COMMITTED")
                successes.append(unit["id"])
                outcomes.append(unit["id"])
            except Exception as error:
                if committing:
                    audit.add(attempt, unit["id"], "UNKNOWN")
                    raise CommitUnknown("unit_commit_outcome_unknown") from error
                rollback(cursor)
                if unit["id"] != UNITS[0]:
                    transaction(cursor)
                    append_event(
                        cursor,
                        ticket,
                        manifest_hash,
                        unit,
                        attempt,
                        "FAILED_ROLLED_BACK",
                        before,
                        error="unit_failed_rolled_back",
                    )
                    try:
                        cursor.execute("COMMIT TRANSACTION;")
                    except Exception as audit_error:
                        audit.add(attempt, unit["id"], "UNKNOWN")
                        raise CommitUnknown(
                            "failure_audit_commit_unknown"
                        ) from audit_error
                audit.add(attempt, unit["id"], "FAILED_ROLLED_BACK")
                raise
        return {"applied": outcomes, "noop": not outcomes, "active_units": successes}
    finally:
        if locked:
            try:
                cursor.execute(
                    "EXEC sys.sp_releaseapplock "
                    "@Resource=N'crm.schema.migrate.v1',@LockOwner=N'Session';"
                )
                drain(cursor)
            except Exception:
                pass  # closing the physical connection releases a lost session lock
        cursor.close()


def reconcile(connection, ticket, audit, *, directory=PACKAGE):
    """Explicit reconciliation appends evidence; never reapplies DDL."""
    manifest, shapes, manifest_hash = load_release(directory)
    cursor = connection.cursor()
    guard(cursor, ticket)
    require(
        cursor.execute("SELECT @@TRANCOUNT").fetchval() == 0,
        "existing_transaction_refused",
    )
    acquire(cursor, "crm.schema.migrate.v1", "Session")
    try:
        require(
            any(
                metadata(cursor, managed=True) == expected
                for expected in shapes.values()
            ),
            "reconcile_shape_inconclusive",
        )
        history = current_history(cursor, ticket, manifest, manifest_hash)
        current = metadata(cursor, managed=True)
        successes = [r["unit"] for r in history if r["kind"] == "COMMITTED"]
        require(successes == list(UNITS[: len(successes)]), "reconcile_invalid_vector")
        prefix = successes[-1] if successes else "prepared"
        require(current == shapes[prefix], "reconcile_shape_inconclusive")
        validate_data(cursor, prefix)
        units = {u["id"]: u for u in manifest["units"]}
        for entry in audit.unresolved():
            committed = any(
                uuid.UUID(r["attempt"]) == uuid.UUID(entry["attempt"])
                and r["kind"] == "COMMITTED"
                for r in history
            )
            kind = "RECONCILED_COMMITTED" if committed else "RECONCILED_NOT_APPLIED"
            if entry["unit"] == UNITS[0] and not successes:
                audit.add(entry["attempt"], entry["unit"], kind)
                continue  # no SQL journal exists after a rolled-back bootstrap
            unit = units[entry["unit"]]
            transaction(cursor)
            append_event(
                cursor,
                ticket,
                manifest_hash,
                unit,
                entry["attempt"],
                kind,
                unit["before_sha256"],
                sha(current),
                related=entry["attempt"],
                release_id=manifest["release_id"],
            )
            cursor.execute("COMMIT TRANSACTION;")
            audit.add(entry["attempt"], entry["unit"], kind)
        return {"unresolved": len(audit.unresolved())}
    finally:
        cursor.execute(
            "EXEC sys.sp_releaseapplock "
            "@Resource=N'crm.schema.migrate.v1',@LockOwner=N'Session';"
        )
        drain(cursor)
        cursor.close()
