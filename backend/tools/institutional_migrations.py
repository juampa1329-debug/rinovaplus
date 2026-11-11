"""Explicit P2 release application; no startup DDL or academic mutation."""

import hashlib
import json
from pathlib import Path
from uuid import UUID, uuid4

from app.institutional.crypto import token_hash
from app.institutional.models import (
    AI,
    Availability,
    Budgets,
    Institution,
    Models,
    Webhooks,
)
from app.institutional.policy import MODULES, ROLE_ACTIONS, ROLE_LABELS, TARGET
from app.parity_channels.catalog import metadata
from tools.cbn_foundation import acquire, target_identity
from tools.foundation_snapshot import sha

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "backend/migrations/cbn_institutional"
ACTOR = "cbn_access_migrator_p2"
UNIT = "CBN-P2-001"
VERSION = "cbn-access-p2-v1"
TABLES = {
    "Institution",
    "Role",
    "AccessUser",
    "Session",
    "Setting",
    "SettingHistory",
    "Secret",
    "Factor",
    "RecoveryCode",
    "Challenge",
    "RateBucket",
    "Operation",
    "Audit",
    "ChannelSetting",
    "BudgetUsage",
}


def defaults():
    return {
        "institution": Institution(name="Institución educativa").model_dump(
            mode="json"
        ),
        "ai": AI().model_dump(mode="json"),
        "models": Models().model_dump(mode="json"),
        "modules": Availability(enabled={m: True for m in MODULES}).model_dump(
            mode="json"
        ),
        "budgets": Budgets().model_dump(mode="json"),
        "webhooks": Webhooks().model_dump(mode="json"),
    }


def assets():
    return [
        "backend/migrations/cbn_institutional/P2_001_access.sql",
        "backend/tools/institutional_migrations.py",
        "backend/app/institutional/models.py",
        "backend/app/institutional/policy.py",
    ]


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def release():
    result = json.loads((PACKAGE / "release.json").read_text(encoding="utf-8"))
    if result["version"] != VERSION or result["unit"] != UNIT:
        raise ValueError("P2_release_version")
    for name, digest in result["inputs"].items():
        if file_sha(ROOT / name) != digest:
            raise ValueError("P2_release_input_changed")
    if set(result["tables"]) != TABLES:
        raise ValueError("P2_release_partition")
    return result


def structural(cursor):
    shape = metadata(cursor)
    result = {
        key: [
            r
            for r in values
            if r.get("schema_name") == "crm_access"
            or key == "schemas"
            and r.get("name") == "crm_access"
        ]
        for key, values in shape.items()
        if isinstance(values, list)
        and key
        not in {"permissions", "all_permissions", "principals", "role_membership"}
    }
    return result


def verify_shape(cursor):
    shape = structural(cursor)
    actual = {r["name"] for r in shape["catalog"] if r["type"].strip() == "U"}
    if actual != TABLES:
        raise ValueError("P2_table_partition")
    invalid = cursor.execute(
        "SELECT COUNT(*) FROM sys.foreign_keys WHERE parent_object_id IN(SELECT object_id FROM sys.tables WHERE schema_id=SCHEMA_ID('crm_access')) AND (is_disabled=1 OR is_not_trusted=1)"
    ).fetchval()
    if invalid:
        raise ValueError("P2_untrusted_foreign_key")
    return sha(shape)


def journal(cursor, attempt, kind, manifest, unit_hash, identity, before, after=None):
    cursor.execute(
        "INSERT crm_meta.MigrationJournal(AttemptId,UnitId,EventKind,ReleaseId,ToolVersion,ManifestSha256,UnitSha256,ShapeVersion,TargetSha256,BeforeShapeSha256,AfterShapeSha256,EvidenceRef,ApprovalRef,BackupRef,PrincipalRef,SuccessKey) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        str(attempt),
        UNIT,
        kind,
        VERSION,
        "P2-explicit-v1",
        bytes.fromhex(manifest),
        bytes.fromhex(unit_hash),
        VERSION,
        bytes.fromhex(sha(identity)),
        bytes.fromhex(before),
        bytes.fromhex(after) if after else None,
        "P2-restored-local",
        "owner-P2-20261026",
        identity["database"] + "-preparation",
        ACTOR,
        UNIT if kind == "COMMITTED" else None,
    )


def apply(connection, settings, *, fault=None):
    """Only a preparer-owned admin connection; actor is then narrowed explicitly."""
    profile = settings["connection"]
    database = profile["database"]
    if not TARGET.fullmatch(database):
        raise ValueError("P2_migration_target")
    cursor = connection.cursor()
    identity = target_identity(cursor)
    if identity["database"] != database or (
        identity["engine"],
        identity["compatibility"],
    ) not in {(16, 160), (15, 150)}:
        raise ValueError("P2_migration_identity")
    package = release()
    manifest = file_sha(PACKAGE / "release.json")
    unit_hash = package["inputs"][
        "backend/migrations/cbn_institutional/P2_001_access.sql"
    ]
    cursor.execute(
        "EXEC sys.sp_set_session_context @key=N'CBN_P2_TARGET',@value=?", database
    )
    cursor.execute("EXECUTE AS USER=" + "N'" + ACTOR + "';")
    try:
        acquire(cursor, "crm.schema.migrate.v1", "Session")
        acquire(cursor, "crm.local.commit", "Session")
        committed = cursor.execute(
            "SELECT ManifestSha256,UnitSha256,AfterShapeSha256 FROM crm_meta.MigrationJournal WHERE UnitId=? AND SuccessKey=?",
            UNIT,
            UNIT,
        ).fetchone()
        if committed:
            if (
                bytes(committed[0]).hex() != manifest
                or bytes(committed[1]).hex() != unit_hash
                or bytes(committed[2]).hex() != verify_shape(cursor)
            ):
                raise ValueError("P2_committed_release_or_shape_drift")
            return {"status": "noop", "unit": UNIT}
        started = cursor.execute(
            "SELECT COUNT(*) FROM crm_meta.MigrationJournal j WHERE UnitId=? AND EventKind='STARTED' AND NOT EXISTS(SELECT 1 FROM crm_meta.MigrationJournal e WHERE e.AttemptId=j.AttemptId AND e.EventKind IN('FAILED_ROLLED_BACK','RECONCILED_NOT_APPLIED','COMMITTED'))",
            UNIT,
        ).fetchval()
        if started:
            raise ValueError("P2_reconciliation_required")
        if cursor.execute(
            "SELECT COUNT(*) FROM sys.objects WHERE schema_id=SCHEMA_ID('crm_access')"
        ).fetchval():
            raise ValueError("P2_existing_schema_refused")
        before = sha(structural(cursor))
        attempt = uuid4()
        journal(cursor, attempt, "STARTED", manifest, unit_hash, identity, before)
        cursor.execute("BEGIN TRANSACTION;")
        try:
            cursor.execute((PACKAGE / "P2_001_access.sql").read_text(encoding="utf-8"))
            while cursor.nextset():
                pass
            context = cursor.execute(
                "SELECT CONVERT(varchar(36),InstitutionId) FROM crm_channels2.Context WHERE ContextId=1"
            ).fetchval()
            if str(UUID(context)) != settings["institution"]:
                raise ValueError("P2_context_drift")
            cursor.execute(
                "INSERT crm_access.Institution(InstitutionId,BootstrapHash) VALUES(?,?)",
                context,
                token_hash(settings["review"]["bootstrap_token"]),
            )
            for role, actions in ROLE_ACTIONS.items():
                cursor.execute(
                    "INSERT crm_access.Role(InstitutionId,RoleKey,Name,Actions,Protected,Active,Revision) VALUES(?,?,?,?,?,1,1)",
                    context,
                    role,
                    ROLE_LABELS[role],
                    json.dumps(list(actions)),
                    int(role in {"owner", "admin"}),
                )
            for section, document in defaults().items():
                text = json.dumps(document, ensure_ascii=False)
                cursor.execute(
                    "INSERT crm_access.Setting(InstitutionId,Section,Document,Revision,UpdatedAt) VALUES(?,?,?,1,SYSUTCDATETIME())",
                    context,
                    section,
                    text,
                )
                cursor.execute(
                    "INSERT crm_access.SettingHistory(InstitutionId,Section,Revision,Document,RecordedAt) VALUES(?,?,1,?,SYSUTCDATETIME())",
                    context,
                    section,
                    text,
                )
            after = verify_shape(cursor)
            if fault == "before_commit":
                raise RuntimeError("P2_controlled_precommit_fault")
            journal(
                cursor,
                attempt,
                "COMMITTED",
                manifest,
                unit_hash,
                identity,
                before,
                after,
            )
            cursor.execute("COMMIT;")
        except BaseException:
            cursor.execute("IF @@TRANCOUNT>0 ROLLBACK;")
            # A lost COMMIT acknowledgement must be reconciled on a new connection.
            found = cursor.execute(
                "SELECT COUNT(*) FROM crm_meta.MigrationJournal WHERE UnitId=? AND SuccessKey=?",
                UNIT,
                UNIT,
            ).fetchval()
            if not found:
                journal(
                    cursor,
                    attempt,
                    "FAILED_ROLLED_BACK",
                    manifest,
                    unit_hash,
                    identity,
                    before,
                )
            raise
        if fault == "after_commit":
            raise RuntimeError("P2_controlled_commit_ack_lost")
        return {
            "status": "committed",
            "unit": UNIT,
            "tables": len(TABLES),
            "shape_sha256": after,
        }
    finally:
        for resource in ("crm.local.commit", "crm.schema.migrate.v1"):
            cursor.execute(
                "EXEC sys.sp_releaseapplock @Resource=?,@LockOwner='Session'", resource
            )
        cursor.execute("REVERT;")
