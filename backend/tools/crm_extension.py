"""C7 isolated B011 guard and runner. Importing performs no SQL or secret reads."""

import hashlib
import json
import re
import uuid
from pathlib import Path

from tools.cbn_foundation import Audit, acquire, drain, target_identity
from tools.cbn_foundation import transaction as begin_transaction
from tools.crm_extension_contract import verify_final_shape
from tools.crm_extension_snapshot import (
    ACTOR,
    PACKAGE,
    PARTITION,
    VERSION,
    canonical,
    journal_binary,
    metadata,
    partition_tables,
    preservation,
    protected,
    records,
    require,
    sha,
    table_names,
)

UNIT = "CBN-B011"
RELEASE = "CBN-channels-local-v1"
TOOL_VERSION = "SQL-C7-v1"
TARGET = re.compile(r"CBN_C7_(REF|TRIAL|FAULT)_20261025_[0-9a-f]{8}\Z")
ROOT = Path(__file__).resolve().parents[2]
SQL_FILE = "B011_channels.sql"
PERMISSIONS = {
    ("DATABASE", "<database>", "CONNECT"),
    ("DATABASE", "<database>", "CREATE TABLE"),
    ("DATABASE", "<database>", "VIEW DEFINITION"),
    ("SCHEMA", "crm_channels", "ALTER"),
    ("SCHEMA", "crm_channels", "REFERENCES"),
    ("OBJECT_OR_COLUMN", "crm.Contact", "REFERENCES"),
    ("OBJECT_OR_COLUMN", "crm.Conversation", "REFERENCES"),
    ("OBJECT_OR_COLUMN", "crm.Message", "REFERENCES"),
    ("OBJECT_OR_COLUMN", "crm_meta.MigrationJournal", "SELECT"),
    ("OBJECT_OR_COLUMN", "crm_meta.MigrationJournal", "INSERT"),
}
DENIED_DBO = {"SELECT", "INSERT", "UPDATE", "DELETE", "ALTER", "REFERENCES", "EXECUTE"}
DATABASE_RIGHTS = {
    "CONNECT",
    "CREATE TABLE",
    "VIEW DEFINITION",
    "VIEW SECURITY DEFINITION",
    "VIEW PERFORMANCE DEFINITION",
    "VIEW ANY COLUMN ENCRYPTION KEY DEFINITION",
    "VIEW ANY COLUMN MASTER KEY DEFINITION",
}


class CommitUnknown(RuntimeError):
    pass


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assets(directory=PACKAGE):
    release = json.loads((directory / "release.json").read_text(encoding="utf-8"))
    require(release["release_id"] == RELEASE and release["unit"] == UNIT, "release")
    require(release["shape_version"] == VERSION, "shape_version")
    require(release["institutional_sql2019_accepted"] is False, "institutional_claim")
    allowed = {
        "backend/migrations/cbn_channels/" + n
        for n in (SQL_FILE, "partition.json", "shape-spec.json", "expected-shapes.json")
    }
    allowed |= {
        "backend/tools/crm_extension.py",
        "backend/tools/crm_extension_snapshot.py",
        "backend/tools/crm_extension_contract.py",
        "backend/migrations/011_channels.sql",
        "backend/migrations/012_channels_identity_collation.sql",
    }
    require(
        {r["path"] for r in release["files"]} == allowed
        and len(release["files"]) == len(allowed),
        "release_file_membership",
    )
    for r in release["files"]:
        require(file_sha(ROOT / r["path"]) == r["sha256"], "artifact_changed")
    base = ROOT / "backend/migrations/cbn_foundation/release.json"
    expected_base = "b8de5466cd6c0e8b373490cc0987bacbf90deff95ffe45e8d84f54f6dc08827a"
    require(
        file_sha(base) == release["base_release_sha256"] == expected_base,
        "base_release",
    )
    for r in json.loads(base.read_text(encoding="utf-8"))["tool_files"]:
        require(file_sha(ROOT / r["path"]) == r["sha256"], "frozen_C3_tool_changed")
    shapes = json.loads(
        (directory / "expected-shapes.json").read_text(encoding="utf-8")
    )
    return release, file_sha(directory / "release.json"), shapes


def verify_direct_acl(shape, actor_sid):
    principal = [p for p in shape["principals"] if p["name"] == ACTOR]
    require(len(principal) == 1, "actor_absent")
    p = principal[0]
    require(
        p["type_desc"] == "SQL_USER"
        and p["authentication_type_desc"] == "NONE"
        and p["default_schema_name"] == "dbo"
        and p["sid"] == actor_sid,
        "actor",
    )
    rights = [r for r in shape["all_permissions"] if r["grantee"] == ACTOR]
    require(len(rights) == len(PERMISSIONS) + len(DENIED_DBO), "actor_extra_acl")
    require(
        {
            (r["class_desc"], r["target"], r["permission_name"])
            for r in rights
            if r["state_desc"] == "GRANT"
        }
        == PERMISSIONS,
        "actor_acl",
    )
    require(
        all(
            r["state_desc"] in {"GRANT", "DENY"}
            and r["grantor"] == "dbo"
            and r["minor_id"] == 0
            for r in rights
        ),
        "actor_acl_state",
    )
    require(
        {
            (r["class_desc"], r["target"], r["permission_name"])
            for r in rights
            if r["state_desc"] == "DENY"
        }
        == {("SCHEMA", "dbo", permission) for permission in DENIED_DBO},
        "actor_denials",
    )
    require(
        not any(r["member_name"] == ACTOR for r in shape["role_membership"]),
        "actor_role",
    )
    require(not any(s["owner"] == ACTOR for s in shape["schemas"]), "actor_owner")


def verify_legacy_actor(shape):
    name = "cbn_foundation_migrator"
    users = [p for p in shape["principals"] if p["name"] == name]
    require(
        len(users) == 1
        and users[0]["type_desc"] == "SQL_USER"
        and users[0]["authentication_type_desc"] == "NONE"
        and users[0]["default_schema_name"] == "dbo",
        "legacy_actor_identity",
    )
    expected = {
        ("DATABASE", "<database>", p, "GRANT")
        for p in ("CONNECT", "CREATE TABLE", "VIEW DEFINITION")
    }
    for schema, permissions in (
        ("crm", ("ALTER", "SELECT", "INSERT", "UPDATE", "DELETE", "REFERENCES")),
        ("crm_config", ("ALTER", "SELECT", "INSERT", "UPDATE", "DELETE")),
        ("crm_meta", ("ALTER", "SELECT", "INSERT")),
    ):
        expected |= {("SCHEMA", schema, p, "GRANT") for p in permissions}
    expected |= {("SCHEMA", "crm_meta", p, "DENY") for p in ("UPDATE", "DELETE")}
    rights = [r for r in shape["all_permissions"] if r["grantee"] == name]
    require(
        len(rights) == len(expected)
        and {
            (r["class_desc"], r["target"], r["permission_name"], r["state_desc"])
            for r in rights
        }
        == expected,
        "legacy_actor_acl",
    )
    require(
        all(r["grantor"] == "dbo" and r["minor_id"] == 0 for r in rights),
        "legacy_actor_grantor",
    )
    require(
        not any(r["member_name"] == name for r in shape["role_membership"])
        and not any(s["owner"] == name for s in shape["schemas"]),
        "legacy_actor_role_or_owner",
    )


def verify_effective_acl(cursor):
    aliases = records(
        cursor, "SELECT SCHEMA_NAME(schema_id)+'.'+name AS name FROM sys.synonyms"
    )
    users = records(
        cursor,
        """SELECT name FROM sys.database_principals
      WHERE type IN('S','U','G','E','X')
        AND name NOT IN(?,N'sys',N'INFORMATION_SCHEMA')""",
        (ACTOR,),
    )
    cursor.execute("EXECUTE AS USER=N'" + ACTOR + "';")
    try:
        require(
            tuple(
                cursor.execute(
                    "SELECT USER_NAME(),IS_MEMBER('db_owner'),"
                    "IS_MEMBER('db_ddladmin'),IS_MEMBER('db_datawriter')"
                ).fetchone()
            )
            == (ACTOR, 0, 0, 0),
            "actor_effective_roles",
        )
        actual = records(
            cursor, "SELECT permission_name FROM sys.fn_my_permissions(NULL,'DATABASE')"
        )
        require(
            {r["permission_name"] for r in actual} == DATABASE_RIGHTS,
            "actor_database_elevation",
        )
        allowed = {
            "crm.Contact": {"REFERENCES"},
            "crm.Conversation": {"REFERENCES"},
            "crm.Message": {"REFERENCES"},
            "crm_meta.MigrationJournal": {"SELECT", "INSERT"},
        }
        names = PARTITION["academic"] + PARTITION["foundation"]
        permissions = (
            "SELECT",
            "INSERT",
            "UPDATE",
            "DELETE",
            "ALTER",
            "REFERENCES",
            "CONTROL",
        )
        powers = records(
            cursor,
            """SELECT s.name+'.'+t.name AS table_name,
          p.permission_name,HAS_PERMS_BY_NAME(QUOTENAME(s.name)+'.'+QUOTENAME(t.name),
            'OBJECT',p.permission_name) AS value FROM sys.tables t
          JOIN sys.schemas s ON s.schema_id=t.schema_id
          CROSS JOIN (VALUES('SELECT'),('INSERT'),('UPDATE'),('DELETE'),('ALTER'),
           ('REFERENCES'),('CONTROL')) p(permission_name)
          WHERE s.name+'.'+t.name IN ("""
            + ",".join("?" for _ in names)
            + ")",
            tuple(names),
        )
        require(
            len(powers) == len(names) * len(permissions)
            and {(r["table_name"], r["permission_name"]) for r in powers}
            == {(table, permission) for table in names for permission in permissions},
            "effective_visibility_incomplete",
        )
        for row in powers:
            require(
                row["value"]
                == int(row["permission_name"] in allowed.get(row["table_name"], set())),
                "actor_protected_object_rights",
            )
        require(
            not cursor.execute(
                "SELECT 1 FROM sys.schemas WHERE principal_id=USER_ID()"
            ).fetchone(),
            "actor_schema_owner",
        )
        for user in users:
            require(
                cursor.execute(
                    "SELECT HAS_PERMS_BY_NAME(?,'USER','IMPERSONATE')", user["name"]
                ).fetchval()
                == 0,
                "actor_impersonation",
            )
        for alias in aliases:
            for permission in ("SELECT", "INSERT", "UPDATE", "DELETE", "EXECUTE"):
                require(
                    cursor.execute(
                        "SELECT HAS_PERMS_BY_NAME(?,'OBJECT',?)",
                        alias["name"],
                        permission,
                    ).fetchval()
                    == 0,
                    "actor_synonym_access",
                )
    finally:
        cursor.execute("REVERT;")


def guard(cursor, ticket):
    require(ticket["scope"] == "SQL-C7-isolated-extension-only", "scope")
    require(bool(TARGET.fullmatch(ticket["identity"]["database"])), "target_name")
    require(
        ticket["identity"]["engine"] == 16
        and ticket["identity"]["compatibility"] == 160,
        "local_engine",
    )
    require(target_identity(cursor) == ticket["identity"], "target_identity")
    require(
        tuple(
            cursor.execute(
                "SELECT is_trustworthy_on,is_db_chaining_on "
                "FROM sys.databases WHERE database_id=DB_ID()"
            ).fetchone()
        )
        == (0, 0),
        "unsafe_database_ownership_chain",
    )
    require(
        not cursor.execute("SELECT 1 FROM sys.server_triggers").fetchone(),
        "server_trigger",
    )
    shape = metadata(cursor)
    verify_direct_acl(shape, ticket["actor_sid"])
    verify_effective_acl(cursor)
    require(
        sha(protected(shape)) == ticket["protected_metadata_sha256"],
        "protected_metadata_changed",
    )
    prefix = journal_binary(cursor, ticket["legacy_rows"])
    require(
        len(prefix) == ticket["legacy_rows"] == 5
        and sha(prefix) == ticket["legacy_journal_sha256"],
        "legacy_prefix_changed",
    )
    return canonical(shape, ticket["actor_sid"])


def history(cursor, ticket, release, manifest_hash):
    rows = records(
        cursor,
        """SELECT EventId,CONVERT(varchar(36),AttemptId) AS attempt,
      UnitId AS unit,EventKind AS kind,ReleaseId AS release_id,ToolVersion AS tool,
      CONVERT(varchar(64),ManifestSha256,2) AS manifest,
      CONVERT(varchar(64),UnitSha256,2) AS unit_hash,ShapeVersion AS shape_version,
      CONVERT(varchar(64),TargetSha256,2) AS target_hash,
      CONVERT(varchar(64),BeforeShapeSha256,2) AS before_hash,
      CONVERT(varchar(64),AfterShapeSha256,2) AS after_hash,PrincipalRef AS principal,
      EvidenceRef AS evidence,ApprovalRef AS approval,BackupRef AS [backup],
      ErrorCode AS [error],SuccessKey AS success_key,
      CONVERT(varchar(36),RelatedAttemptId) AS related_attempt,
      RelatedUnitId AS related_unit
      FROM crm_meta.MigrationJournal ORDER BY EventId""",
    )
    # Prefix bytes were verified against ORIGINAL C5, never rebound to this copy.
    tail = rows[ticket["legacy_rows"] :]
    groups = {}
    committed = False
    for row in tail:
        row["attempt"] = str(uuid.UUID(row["attempt"]))
        require(
            row["unit"] == UNIT
            and row["release_id"] == RELEASE
            and row["tool"] == TOOL_VERSION
            and row["shape_version"] == VERSION
            and row["principal"] == ACTOR,
            "unknown_history",
        )
        require(
            row["manifest"].lower() == manifest_hash
            and row["unit_hash"].lower() == release["sql_sha256"]
            and row["target_hash"].lower() == sha(ticket["identity"])
            and row["before_hash"].lower() == release["before_sha256"],
            "history_hash",
        )
        require(
            row["evidence"] == ticket["evidence_ref"]
            and row["approval"] == ticket["approval_ref"]
            and row["backup"] == ticket["backup_ref"],
            "history_context",
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
        if row["kind"] in {"COMMITTED", "RECONCILED_COMMITTED"}:
            require(
                row["after_hash"] is not None
                and row["after_hash"].lower() == release["after_sha256"]
                and row["error"] is None,
                "committed_shape",
            )
        else:
            require(row["after_hash"] is None, "unexpected_after_shape")
        require(
            row["success_key"] == (UNIT if row["kind"] == "COMMITTED" else None),
            "history_success_key",
        )
        require(
            row["error"]
            == ("unit_rolled_back" if row["kind"] == "FAILED_ROLLED_BACK" else None),
            "history_error",
        )
        related = row["kind"].startswith("RECONCILED")
        require(
            (
                str(uuid.UUID(row["related_attempt"]))
                if row.get("related_attempt")
                else None
            )
            == (row["attempt"] if related else None)
            and row.get("related_unit") == (UNIT if related else None),
            "history_reconciliation_link",
        )
        groups.setdefault(row["attempt"], []).append(row["kind"])
        committed |= row["kind"] == "COMMITTED"
    allowed = [
        ["STARTED"],
        ["STARTED", "COMMITTED"],
        ["STARTED", "FAILED_ROLLED_BACK"],
        ["STARTED", "RECONCILED_NOT_APPLIED"],
        ["STARTED", "COMMITTED", "RECONCILED_COMMITTED"],
    ]
    require(all(kinds in allowed for kinds in groups.values()), "history_sequence")
    require(sum(r["kind"] == "COMMITTED" for r in tail) <= 1, "duplicate_success")
    return tail, committed


def append(cursor, ticket, release, manifest_hash, attempt, kind, *, error=None):
    cursor.execute("EXECUTE AS USER=N'" + ACTOR + "';")
    try:
        cursor.execute(
            """INSERT crm_meta.MigrationJournal
          (AttemptId,UnitId,EventKind,ReleaseId,ToolVersion,ManifestSha256,UnitSha256,
           ShapeVersion,TargetSha256,BeforeShapeSha256,AfterShapeSha256,EvidenceRef,
           ApprovalRef,BackupRef,PrincipalRef,ErrorCode,SuccessKey,
           RelatedAttemptId,RelatedUnitId)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            str(attempt),
            UNIT,
            kind,
            RELEASE,
            TOOL_VERSION,
            bytes.fromhex(manifest_hash),
            bytes.fromhex(release["sql_sha256"]),
            VERSION,
            bytes.fromhex(sha(ticket["identity"])),
            bytes.fromhex(release["before_sha256"]),
            bytes.fromhex(release["after_sha256"])
            if kind in {"COMMITTED", "RECONCILED_COMMITTED"}
            else None,
            ticket["evidence_ref"],
            ticket["approval_ref"],
            ticket["backup_ref"],
            ACTOR,
            error,
            UNIT if kind == "COMMITTED" else None,
            str(attempt) if kind.startswith("RECONCILED") else None,
            UNIT if kind.startswith("RECONCILED") else None,
        )
    finally:
        cursor.execute("REVERT;")


def verified_state(cursor, ticket, release):
    shape = guard(cursor, ticket)
    value = sha(shape)
    extended = value == release["after_sha256"]
    require(value in {release["before_sha256"], release["after_sha256"]}, "shape_drift")
    partition_tables(table_names(shape), extended)
    require(preservation(cursor) == ticket["preservation"], "protected_data_changed")
    if extended:
        verify_final_shape(shape, ticket["identity"]["collation"])
        for table in PARTITION["extension"]:
            require(
                cursor.execute("SELECT COUNT(*) FROM " + table).fetchval() == 0,
                "extension_not_empty",
            )
    return extended


def migration_cursor(connection):
    cursor = connection.cursor()
    if cursor.execute("SELECT @@TRANCOUNT").fetchval() != 0:
        cursor.close()
        raise ValueError("open_transaction")
    return cursor


def commit(cursor, phase, fault=None):
    """Explicit test-only ACK outcomes; no application imports or uses this tool."""
    if fault == phase + "_rolled_back":
        cursor.execute("ROLLBACK;")
        raise OSError("simulated_commit_response_loss")
    cursor.execute("COMMIT;")
    if fault == phase:
        raise OSError("simulated_commit_response_loss")


def migration_audit(path, ticket):
    audit = Audit(path, sha(ticket["identity"]))
    require(all(r["unit"] == UNIT for r in audit.rows()), "audit_unit_mismatch")
    return audit


def transaction(cursor):
    cursor.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;")
    begin_transaction(cursor)


def run(connection, ticket, audit_path, *, fail_at=None, lose_ack=None):
    release, manifest_hash, _ = assets()
    require(ticket["release_sha256"] == manifest_hash, "release_ticket_changed")
    require(
        lose_ack
        in {
            None,
            "started",
            "started_rolled_back",
            "applied",
            "applied_rolled_back",
            "failure",
            "failure_rolled_back",
        },
        "ack_fault",
    )
    require(
        not lose_ack or not lose_ack.startswith("failure") or fail_at is not None,
        "failure_injection_required",
    )
    audit = migration_audit(audit_path, ticket)
    cursor = migration_cursor(connection)
    locked = False
    try:
        acquire(cursor, "crm.schema.migrate.v1", "Session")
        locked = True
        require(not audit.unresolved(), "audit_requires_reconciliation")
        transaction(cursor)
        try:
            acquire(cursor, "crm.local.commit", "Transaction")
            extended = verified_state(cursor, ticket, release)
            tail, committed = history(cursor, ticket, release, manifest_hash)
            require(
                not any(
                    r["kind"] == "STARTED"
                    and not any(
                        s["attempt"] == r["attempt"] and s["kind"] != "STARTED"
                        for s in tail
                    )
                    for r in tail
                ),
                "history_unresolved",
            )
            require(extended == committed, "history_shape_disagreement")
            cursor.execute("COMMIT;")
        except BaseException:
            cursor.execute("IF @@TRANCOUNT>0 ROLLBACK;")
            raise
        if committed:
            return "NOOP"
        attempt = str(uuid.uuid4())
        audit.add(attempt, UNIT, "STARTED")
        transaction(cursor)
        append(cursor, ticket, release, manifest_hash, attempt, "STARTED")
        try:
            commit(cursor, "started", lose_ack)
        except BaseException as exc:
            audit.add(attempt, UNIT, "UNKNOWN")
            raise CommitUnknown("started_commit_unknown") from exc
        transaction(cursor)
        committing = False
        try:
            acquire(cursor, "crm.local.commit", "Transaction")
            require(not verified_state(cursor, ticket, release), "already_applied")
            cursor.execute(
                "EXEC sys.sp_set_session_context @key=N'CBN_C7_TARGET',@value=?;",
                ticket["identity"]["database"],
            )
            raw = (PACKAGE / SQL_FILE).read_bytes()
            require(
                hashlib.sha256(raw).hexdigest() == release["sql_sha256"],
                "sql_changed_before_execution",
            )
            chunks = raw.decode("utf-8").split("-- C7_BOUNDARY")
            cursor.execute("EXECUTE AS USER=N'" + ACTOR + "';")
            try:
                for index, chunk in enumerate(chunks):
                    if fail_at == index:
                        raise RuntimeError("injected_boundary_failure")
                    cursor.execute(chunk)
                    drain(cursor)
            finally:
                cursor.execute("REVERT;")
            require(verified_state(cursor, ticket, release), "post_shape")
            if fail_at == len(chunks):
                raise RuntimeError("injected_before_success")
            append(cursor, ticket, release, manifest_hash, attempt, "COMMITTED")
            if fail_at == len(chunks) + 1:
                raise RuntimeError("injected_after_success_before_commit")
            committing = True
            commit(cursor, "applied", lose_ack)
            audit.add(attempt, UNIT, "COMMITTED")
            return "APPLIED"
        except BaseException as exc:
            if committing:
                audit.add(attempt, UNIT, "UNKNOWN")
                raise CommitUnknown("ddl_commit_unknown") from exc
            cursor.execute("IF @@TRANCOUNT>0 ROLLBACK;")
            transaction(cursor)
            try:
                append(
                    cursor,
                    ticket,
                    release,
                    manifest_hash,
                    attempt,
                    "FAILED_ROLLED_BACK",
                    error="unit_rolled_back",
                )
                commit(cursor, "failure", lose_ack)
            except BaseException as recording:
                audit.add(attempt, UNIT, "UNKNOWN")
                raise CommitUnknown("failure_record_commit_unknown") from recording
            audit.add(attempt, UNIT, "FAILED_ROLLED_BACK")
            raise
    finally:
        cursor.execute("IF @@TRANCOUNT>0 ROLLBACK;")
        if locked:
            cursor.execute(
                "EXEC sys.sp_releaseapplock @Resource=N'crm.schema.migrate.v1',"
                "@LockOwner=N'Session';"
            )
        cursor.close()


def reconcile(connection, ticket, audit_path, *, lose_ack=None):
    release, manifest_hash, _ = assets()
    require(ticket["release_sha256"] == manifest_hash, "release_ticket_changed")
    require(lose_ack in {None, "reconciled", "reconciled_rolled_back"}, "ack_fault")
    audit = migration_audit(audit_path, ticket)
    cursor = migration_cursor(connection)
    locked = False
    try:
        acquire(cursor, "crm.schema.migrate.v1", "Session")
        locked = True
        pending = audit.unresolved()
        require(len(pending) == 1, "one_unresolved_attempt_required")
        attempt = pending[0]["attempt"]
        transaction(cursor)
        acquire(cursor, "crm.local.commit", "Transaction")
        extended = verified_state(cursor, ticket, release)
        tail, committed = history(cursor, ticket, release, manifest_hash)
        require(extended == committed, "history_shape_disagreement")
        own = [r for r in tail if r["attempt"].lower() == attempt.lower()]
        kinds = [r["kind"] for r in own]
        if kinds == ["STARTED", "COMMITTED"] and extended:
            kind = "RECONCILED_COMMITTED"
        elif kinds == ["STARTED"] and not extended:
            kind = "RECONCILED_NOT_APPLIED"
        elif kinds in (
            ["STARTED", "FAILED_ROLLED_BACK"],
            ["STARTED", "RECONCILED_NOT_APPLIED"],
            ["STARTED", "COMMITTED", "RECONCILED_COMMITTED"],
        ):
            require(
                extended == ("COMMITTED" in kinds), "resolved_history_shape_mismatch"
            )
            cursor.execute("COMMIT;")
            audit.add(attempt, UNIT, "RECONCILED")
            return "ALREADY_RECORDED"
        elif not kinds and not extended:
            cursor.execute("COMMIT;")
            audit.add(attempt, UNIT, "RECONCILED_NOT_APPLIED")
            return "NO_SQL_ATTEMPT"
        else:
            raise ValueError("reconciliation_requires_manual_inspection")
        append(cursor, ticket, release, manifest_hash, attempt, kind)
        try:
            commit(cursor, "reconciled", lose_ack)
        except BaseException as exc:
            raise CommitUnknown("reconciliation_commit_unknown") from exc
        audit.add(attempt, UNIT, "RECONCILED")
        return kind
    finally:
        cursor.execute("IF @@TRANCOUNT>0 ROLLBACK;")
        if locked:
            cursor.execute(
                "EXEC sys.sp_releaseapplock @Resource=N'crm.schema.migrate.v1',"
                "@LockOwner=N'Session';"
            )
        cursor.close()
