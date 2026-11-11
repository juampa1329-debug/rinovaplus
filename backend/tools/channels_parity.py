"""C11 explicit five-unit runner. No connections or secrets at import time."""

import contextlib
import json
import uuid

from tools.cbn_foundation import Audit, acquire, drain, target_identity, transaction
from tools.channels_parity_contract import (
    ACTOR,
    PACKAGE,
    RELEASE,
    TARGET,
    VERSION,
    assets,
    digest,
    model,
    require,
)
from tools.channels_parity_snapshot import (
    canonical,
    effective_acl,
    journal_binary,
    metadata,
    preserved_data,
    protected,
    records,
    sha,
    verify_partition,
)


class CommitUnknown(RuntimeError):
    pass


def cleanup(cursor, locked):
    with contextlib.suppress(Exception):
        cursor.execute("IF @@TRANCOUNT>0 ROLLBACK;")
    if locked:
        with contextlib.suppress(Exception):
            cursor.execute(
                (
                    "EXEC sys.sp_releaseapplock @Resource=N'crm.schem"
                    "a.migrate.v1',@LockOwner=N'Session';"
                )
            )
    with contextlib.suppress(Exception):
        cursor.close()


def expected_shapes():
    return json.loads((PACKAGE / "expected-shapes.json").read_text(encoding="utf-8"))


def guard(cursor, ticket, shapes):
    require(ticket["scope"] == "SQL-C11-restored-schema-only", "C11_scope")
    require(bool(TARGET.fullmatch(ticket["identity"]["database"])), "C11_target_name")
    require(target_identity(cursor) == ticket["identity"], "C11_target_identity")
    require(
        (ticket["identity"]["engine"], ticket["identity"]["compatibility"])
        in {(15, 150), (16, 160)},
        "C11_engine_profile",
    )
    require(
        tuple(
            cursor.execute(
                (
                    "SELECT is_trustworthy_on,is_db_chaining_on FROM sys.database"
                    "s WHERE database_id=DB_ID()"
                )
            ).fetchone()
        )
        == (0, 0),
        "C11_ownership_chaining",
    )
    require(
        not cursor.execute("SELECT 1 FROM sys.server_triggers").fetchone(),
        "C11_server_trigger",
    )
    raw = metadata(cursor)
    require(
        sha(protected(raw)) == ticket["protected_catalog_sha256"],
        "C11_protected_catalog",
    )
    actual = canonical(raw, ticket["actor_sid"])
    matches = [i for i, shape in enumerate(shapes) if sha(actual) == shape]
    require(len(matches) == 1, "C11_catalog_drift")
    prefix = matches[0]
    verify_partition(raw, prefix)
    effective_acl(cursor)
    require(preserved_data(cursor) == ticket["preservation"], "C11_protected_data")
    if prefix:
        rows = cursor.execute(
            (
                "SELECT ContextId,CONVERT(varchar(36),InstitutionId),Contract"
                "Version FROM crm_channels2.Context"
            )
        ).fetchall()
        require(
            len(rows) == 1
            and rows[0][0] == 1
            and str(uuid.UUID(rows[0][1])) == ticket["institution_id"]
            and rows[0][2] == model()["version"],
            "C11_context",
        )
    return prefix


def history(cursor, ticket, release, manifest):
    rows = records(
        cursor,
        """SELECT EventId,CONVERT(varchar(36),AttemptId) AS attempt,
      UnitId AS unit,EventKind AS kind,ReleaseId AS release_id,ToolVersion AS tool,
      CONVERT(varchar(64),ManifestSha256,2) AS manifest,
      CONVERT(varchar(64),UnitSha256,2) AS unit_hash,ShapeVersion AS shape_version,
      CONVERT(varchar(64),TargetSha256,2) AS target_hash,
      CONVERT(varchar(64),BeforeShapeSha256,2) AS before_hash,
      CONVERT(varchar(64),AfterShapeSha256,2) AS after_hash,PrincipalRef AS principal,
      EvidenceRef AS evidence,ApprovalRef AS approval,BackupRef AS backup_ref,
      ErrorCode AS error,SuccessKey AS success_key,
      CONVERT(varchar(36),RelatedAttemptId) AS related_attempt,
      RelatedUnitId AS related_unit
      FROM crm_meta.MigrationJournal ORDER BY EventId""",
    )
    require(
        sha(journal_binary(cursor, 7)) == ticket["preservation"]["legacy_journal"],
        "C11_journal_prefix",
    )
    units = {u["id"]: u for u in release["units"]}
    groups = {}
    successes = []
    pending_attempt = None
    recent_success = None
    for row in rows[7:]:
        require(row["unit"] in units, "C11_unknown_history_unit")
        unit = units[row["unit"]]
        row["attempt"] = str(uuid.UUID(row["attempt"]))
        require(
            (row["release_id"], row["tool"], row["shape_version"], row["principal"])
            == (RELEASE, "SQL-C11-v1", VERSION, ACTOR),
            "C11_history_identity",
        )
        require(
            row["manifest"].lower() == manifest
            and row["unit_hash"].lower() == unit["sha256"]
            and row["target_hash"].lower() == sha(ticket["identity"]),
            "C11_history_hash",
        )
        require(
            row["before_hash"].lower() == unit["before_sha256"], "C11_history_before"
        )
        require(
            (row["evidence"], row["approval"], row["backup_ref"])
            == (ticket["evidence_ref"], ticket["approval_ref"], ticket["backup_ref"]),
            "C11_history_context",
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
            "C11_history_kind",
        )
        committed = row["kind"] in {"COMMITTED", "RECONCILED_COMMITTED"}
        require(
            (row["after_hash"].lower() if row["after_hash"] else None)
            == (unit["after_sha256"] if committed else None),
            "C11_history_after",
        )
        require(
            row["success_key"] == (row["unit"] if row["kind"] == "COMMITTED" else None),
            "C11_history_success",
        )
        require(
            row["error"]
            == ("unit_rolled_back" if row["kind"] == "FAILED_ROLLED_BACK" else None),
            "C11_history_error",
        )
        related = row["kind"].startswith("RECONCILED")
        require(
            (str(uuid.UUID(row["related_attempt"])) if row["related_attempt"] else None)
            == (row["attempt"] if related else None)
            and row["related_unit"] == (row["unit"] if related else None),
            "C11_history_related",
        )
        pair = (row["attempt"], row["unit"])
        if row["kind"] == "STARTED":
            require(
                pending_attempt is None
                and len(successes) < len(units)
                and row["unit"] == list(units)[len(successes)]
                and row["attempt"] not in groups,
                "C11_history_pending_unit",
            )
            pending_attempt, recent_success = pair, None
        elif row["kind"] == "RECONCILED_COMMITTED":
            require(
                pending_attempt is None and recent_success == pair,
                "C11_history_reconcile_order",
            )
            recent_success = None
        else:
            require(pending_attempt == pair, "C11_history_interleaved_attempt")
            pending_attempt = None
            recent_success = pair if row["kind"] == "COMMITTED" else None
        groups.setdefault(row["attempt"], []).append(row)
        if row["kind"] == "COMMITTED":
            successes.append(row["unit"])
    require(successes == list(units)[: len(successes)], "C11_history_vector")
    allowed = [
        ["STARTED"],
        ["STARTED", "COMMITTED"],
        ["STARTED", "FAILED_ROLLED_BACK"],
        ["STARTED", "RECONCILED_NOT_APPLIED"],
        ["STARTED", "COMMITTED", "RECONCILED_COMMITTED"],
    ]
    for group in groups.values():
        require(
            len({r["unit"] for r in group}) == 1
            and [r["kind"] for r in group] in allowed,
            "C11_attempt_sequence",
        )
    unresolved = [g[0] for g in groups.values() if len(g) == 1]
    return rows[7:], len(successes), unresolved


def append(cursor, ticket, release, manifest, unit, attempt, kind):
    cursor.execute("EXECUTE AS USER=N'" + ACTOR + "';")
    try:
        cursor.execute(
            """INSERT crm_meta.MigrationJournal
          (AttemptId,UnitId,EventKind,ReleaseId,ToolVersion,ManifestSha256,UnitSha256,
           ShapeVersion,TargetSha256,BeforeShapeSha256,AfterShapeSha256,EvidenceRef,
           ApprovalRef,BackupRef,PrincipalRef,ErrorCode,SuccessKey,RelatedAttemptId,RelatedUnitId)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            attempt,
            unit["id"],
            kind,
            RELEASE,
            "SQL-C11-v1",
            bytes.fromhex(manifest),
            bytes.fromhex(unit["sha256"]),
            VERSION,
            bytes.fromhex(sha(ticket["identity"])),
            bytes.fromhex(unit["before_sha256"]),
            bytes.fromhex(unit["after_sha256"])
            if kind in {"COMMITTED", "RECONCILED_COMMITTED"}
            else None,
            ticket["evidence_ref"],
            ticket["approval_ref"],
            ticket["backup_ref"],
            ACTOR,
            "unit_rolled_back" if kind == "FAILED_ROLLED_BACK" else None,
            unit["id"] if kind == "COMMITTED" else None,
            attempt if kind.startswith("RECONCILED") else None,
            unit["id"] if kind.startswith("RECONCILED") else None,
        )
    finally:
        cursor.execute("REVERT;")


def commit(cursor, phase, fault):
    if fault == phase + "_rolled_back":
        cursor.execute("ROLLBACK;")
        raise CommitUnknown("C11_simulated_lost_response")
    cursor.execute("COMMIT;")
    if fault == phase:
        raise CommitUnknown("C11_simulated_lost_response")


def run(connection, ticket, audit_path, *, unit_id=None, fail_at=None, lose_ack=None):
    release, manifest = assets()
    require(ticket["release_sha256"] == manifest, "C11_release_ticket")
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
        "C11_fault",
    )
    require(
        not lose_ack or not lose_ack.startswith("failure") or fail_at is not None,
        "C11_failure_fault",
    )
    audit = Audit(audit_path, sha(ticket["identity"]))
    require(not audit.unresolved(), "C11_external_unknown")
    c = connection.cursor()
    if c.execute("SELECT @@TRANCOUNT").fetchval() != 0:
        c.close()
        raise ValueError("C11_open_transaction")
    locked = False
    try:
        acquire(c, "crm.schema.migrate.v1", "Session")
        locked = True
        require(not audit.unresolved(), "C11_external_unknown")
        shapes = expected_shapes()
        prefix = guard(c, ticket, shapes)
        _, completed, unresolved = history(c, ticket, release, manifest)
        require(
            not unresolved and prefix == completed, "C11_history_catalog_disagreement"
        )
        if prefix == len(release["units"]):
            return "NOOP"
        unit = release["units"][prefix]
        require(unit_id is None or unit_id == unit["id"], "C11_unit_sequence")
        attempt = str(uuid.uuid4())
        audit.add(attempt, unit["id"], "STARTED")
        transaction(c)
        append(c, ticket, release, manifest, unit, attempt, "STARTED")
        try:
            commit(c, "started", lose_ack)
        except BaseException as error:
            audit.add(attempt, unit["id"], "UNKNOWN")
            raise CommitUnknown("C11_started_commit_unknown") from error
        transaction(c)
        committing = False
        try:
            acquire(c, "crm.local.commit", "Transaction")
            require(guard(c, ticket, shapes) == prefix, "C11_prefix_changed")
            c.execute(
                "EXEC sys.sp_set_session_context @key=N'CBN_C11_TARGET',@value=?",
                ticket["identity"]["database"],
            )
            raw = (PACKAGE / (unit["id"] + ".sql")).read_bytes()
            require(
                digest(PACKAGE / (unit["id"] + ".sql")) == unit["sha256"],
                "C11_SQL_changed",
            )
            chunks = raw.decode("utf-8").split("-- C11_BOUNDARY")
            c.execute("EXECUTE AS USER=N'" + ACTOR + "';")
            try:
                for number, chunk in enumerate(chunks):
                    if fail_at == number:
                        raise RuntimeError("C11_injected_boundary_failure")
                    c.execute(chunk)
                    drain(c)
            finally:
                c.execute("REVERT;")
            if prefix == 0:
                # Only the explicit rehearsal coordinator seeds this new table.
                c.execute(
                    (
                        "INSERT crm_channels2.Context(ContextId,InstitutionId,Contrac"
                        "tVersion,CreatedAt) VALUES(1,?,?,SYSUTCDATETIME())"
                    ),
                    ticket["institution_id"],
                    model()["version"],
                )
            require(guard(c, ticket, shapes) == prefix + 1, "C11_post_shape")
            if fail_at == len(chunks):
                raise RuntimeError("C11_injected_before_success")
            append(c, ticket, release, manifest, unit, attempt, "COMMITTED")
            if fail_at == len(chunks) + 1:
                raise RuntimeError("C11_injected_after_success")
            committing = True
            commit(c, "applied", lose_ack)
            audit.add(attempt, unit["id"], "COMMITTED")
            return "APPLIED"
        except BaseException as error:
            if committing:
                audit.add(attempt, unit["id"], "UNKNOWN")
                raise CommitUnknown("C11_DDL_commit_unknown") from error
            c.execute("IF @@TRANCOUNT>0 ROLLBACK;")
            transaction(c)
            try:
                append(
                    c, ticket, release, manifest, unit, attempt, "FAILED_ROLLED_BACK"
                )
                commit(c, "failure", lose_ack)
            except BaseException as recording:
                audit.add(attempt, unit["id"], "UNKNOWN")
                raise CommitUnknown("C11_failure_commit_unknown") from recording
            audit.add(attempt, unit["id"], "FAILED_ROLLED_BACK")
            raise
    finally:
        cleanup(c, locked)


def reconcile(connection, ticket, audit_path, *, lose_ack=None):
    release, manifest = assets()
    require(ticket["release_sha256"] == manifest, "C11_release_ticket")
    require(
        lose_ack in {None, "reconciled", "reconciled_rolled_back"},
        "C11_reconcile_fault",
    )
    audit = Audit(audit_path, sha(ticket["identity"]))
    c = connection.cursor()
    if c.execute("SELECT @@TRANCOUNT").fetchval() != 0:
        c.close()
        raise ValueError("C11_open_transaction")
    locked = False
    try:
        acquire(c, "crm.schema.migrate.v1", "Session")
        locked = True
        pending = audit.unresolved()
        require(len(pending) <= 1, "C11_one_unresolved_required")
        transaction(c)
        prefix = guard(c, ticket, expected_shapes())
        rows, completed, _ = history(c, ticket, release, manifest)
        require(prefix == completed, "C11_reconcile_shape_history")
        if not pending:
            c.execute("COMMIT;")
            return "ALREADY_RECORDED"
        item = pending[0]
        matches = [u for u in release["units"] if u["id"] == item["unit"]]
        require(len(matches) == 1, "C11_audit_unit")
        unit = matches[0]
        own = [r for r in rows if r["attempt"] == item["attempt"]]
        require(
            all(r["unit"] == unit["id"] for r in own), "C11_audit_SQL_unit_mismatch"
        )
        require(
            bool(own) or completed <= release["units"].index(unit),
            "C11_empty_audit_completed_unit",
        )
        kinds = [r["kind"] for r in own]
        if kinds == ["STARTED"]:
            kind = "RECONCILED_NOT_APPLIED"
        elif kinds == ["STARTED", "COMMITTED"]:
            kind = "RECONCILED_COMMITTED"
        elif kinds in (
            [],
            ["STARTED", "FAILED_ROLLED_BACK"],
            ["STARTED", "RECONCILED_NOT_APPLIED"],
            ["STARTED", "COMMITTED", "RECONCILED_COMMITTED"],
        ):
            commit(c, "reconciled", lose_ack)
            audit.add(
                item["attempt"],
                unit["id"],
                "RECONCILED_NOT_APPLIED" if not kinds else "RECONCILED",
            )
            return "ALREADY_RECORDED" if kinds else "NO_SQL_ATTEMPT"
        else:
            raise ValueError("C11_manual_reconciliation_required")
        append(c, ticket, release, manifest, unit, item["attempt"], kind)
        try:
            commit(c, "reconciled", lose_ack)
        except BaseException as error:
            raise CommitUnknown("C11_reconcile_commit_unknown") from error
        audit.add(item["attempt"], unit["id"], "RECONCILED")
        return kind
    finally:
        cleanup(c, locked)
