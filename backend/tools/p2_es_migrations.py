"""Explicit additive P2 Spanish migrations in new native SQL2019 restorations."""

import hashlib
import json
import os
import re
from contextlib import suppress
from pathlib import Path
from uuid import UUID, uuid4

from app.institutional.models import (
    AI,
    Availability,
    Budgets,
    Institution,
    Models,
    Webhooks,
)
from app.institutional.policy import MODULES, ROLE_ACTIONS, ROLE_LABELS
from app.institutional.spanish_bindings import (
    PACKAGE,
    TARGET,
    Cursor,
    canonical_context,
)
from app.parity_channels.catalog import metadata
from tools.cbn_foundation import acquire
from tools.es_schema_catalog_v2 import canonical, model, snapshot
from tools.es_schema_migrate_v2 import batches, identity, leave
from tools.foundation_snapshot import records, sha

ROOT = Path(__file__).resolve().parents[2]
VERSION = "cbn-p2-es-release-v1"
ACTOR = "cbn_institutional_es_migrator"
UNITS = ("P2ES-001", "P2ES-002")
PARENT = "5457c8da43a9c303c5b7032cff625a3d7ae112c876187c61fdb31e7a8948e2d3"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def release(approved_manifest_sha256):
    raw = (PACKAGE / "release.json").read_bytes()
    if (
        not isinstance(approved_manifest_sha256, str)
        or hashlib.sha256(raw).hexdigest() != approved_manifest_sha256
    ):
        raise ValueError("P2ES_unapproved_manifest")
    if len(raw) > 65536:
        raise ValueError("P2ES_manifest_size")

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("P2ES_duplicate_manifest_key")
            result[key] = value
        return result

    value = json.loads(raw, object_pairs_hook=unique)
    expected_inputs = {
        "backend/migrations/cbn_institutional_spanish_v1/" + name
        for name in (
            "P2ES_001_channels.sql",
            "P2ES_002_access.sql",
            "table_map.json",
            "derivation.json",
            "expected-stages.json",
        )
    } | {
        "backend/tools/p2_es_migrations.py",
        "backend/app/institutional/spanish_bindings.py",
        "backend/app/institutional/models.py",
        "backend/app/institutional/policy.py",
        "backend/tools/es_schema_migrate_v2.py",
        "backend/tools/es_schema_catalog_v2.py",
        "docs/adaptation/sql/p2-channel-fields.json",
        "backend/migrations/cbn_spanish_schema_v2/table_map.json",
        "backend/app/institutional/model_settings.py",
    }
    if (
        set(value)
        != {
            "version",
            "units",
            "inputs",
            "parent_release",
            "parent_journal_sha256",
            "parent_journal_rows",
            "table_counts",
            "scope",
        }
        or value["version"] != VERSION
        or value["parent_release"] != PARENT
        or value["table_counts"] != [99, 123, 138]
        or value["scope"] != "new_SQL2019_P2ES_restorations_only"
    ):
        raise ValueError("P2ES_manifest_contract")
    if (
        set(value["inputs"]) != expected_inputs
        or value["parent_journal_rows"] != 3
        or not re.fullmatch(r"[0-9a-f]{64}", value["parent_journal_sha256"])
    ):
        raise ValueError("P2ES_input_or_parent_contract")
    if [u.get("id") for u in value["units"]] != list(UNITS):
        raise ValueError("P2ES_unit_order")
    for unit, filename in zip(
        value["units"], ("P2ES_001_channels.sql", "P2ES_002_access.sql"), strict=True
    ):
        key = "backend/migrations/cbn_institutional_spanish_v1/" + filename
        if (
            set(unit) != {"id", "file", "sha256"}
            or unit["file"] != filename
            or unit["sha256"] != value["inputs"][key]
        ):
            raise ValueError("P2ES_unit_binding")
    for relative, expected in value["inputs"].items():
        if digest(ROOT / relative) != expected:
            raise ValueError("P2ES_release_bytes_changed")
    derivation = json.loads((PACKAGE / "derivation.json").read_text())
    for relative, expected in derivation["frozen_sources"].items():
        if digest(ROOT / relative) != expected:
            raise ValueError("P2ES_frozen_source_changed")
    return value


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


def seed_binding(value):
    if (
        set(value) != {"institution", "bootstrap_sha256"}
        or str(UUID(value["institution"])) != value["institution"]
        or not re.fullmatch(r"[0-9a-f]{64}", value["bootstrap_sha256"])
    ):
        raise ValueError("P2ES_seed_binding")
    return sha(value)


def target_hash(actual, seed):
    return sha({"identity": actual, "seed_sha256": seed_binding(seed)})


def shape(cursor):
    return sha({"model": snapshot(cursor), "catalog": metadata(cursor)})


def guard(cursor, expected):
    actual = identity(cursor)
    if (
        actual != expected
        or not TARGET.fullmatch(actual["database"])
        or (actual["engine"], actual["compatibility"]) != (15, 150)
    ):
        raise ValueError("P2ES_target_identity")
    if tuple(
        cursor.execute(
            "SELECT is_trustworthy_on,is_db_chaining_on FROM sys.databases WHERE database_id=DB_ID()"
        ).fetchone()
    ) != (0, 0):
        raise ValueError("P2ES_unsafe_chaining")
    return actual


def verify_model(cursor, unit):
    expected = json.loads((PACKAGE / "expected-stages.json").read_text())[unit]
    if canonical(model(snapshot(cursor))) != canonical(expected):
        raise ValueError("P2ES_catalog_model_drift")


def ddl_batches(unit):
    text = (PACKAGE / unit["file"]).read_text(encoding="utf-8")
    return batches(text.replace("-- C11_BOUNDARY", "GO\n-- C11_BOUNDARY"))


def seed_unit(cursor, unit, seed):
    c = Cursor(cursor)
    institution = seed["institution"]
    if unit == UNITS[0]:
        c.execute(
            "INSERT crm_channels2.Context(ContextId,InstitutionId,ContractVersion,CreatedAt) VALUES(1,?,'CBN-channels-parity-v1',SYSUTCDATETIME())",
            institution,
        )
    else:
        c.execute(
            "INSERT crm_access.Institution(InstitutionId,BootstrapHash) VALUES(?,?)",
            institution,
            bytes.fromhex(seed["bootstrap_sha256"]),
        )
        for role, actions in ROLE_ACTIONS.items():
            c.execute(
                "INSERT crm_access.Role(InstitutionId,RoleKey,Name,Actions,Protected,Active,Revision) VALUES(?,?,?,?,?,1,1)",
                institution,
                role,
                ROLE_LABELS[role],
                json.dumps(list(actions)),
                int(role in {"owner", "admin"}),
            )
        for section, document in defaults().items():
            text = json.dumps(document, ensure_ascii=False)
            c.execute(
                "INSERT crm_access.Setting(InstitutionId,Section,Document,Revision,UpdatedAt) VALUES(?,?,?,1,SYSUTCDATETIME())",
                institution,
                section,
                text,
            )
            c.execute(
                "INSERT crm_access.SettingHistory(InstitutionId,Section,Revision,Document,RecordedAt) VALUES(?,?,1,?,SYSUTCDATETIME())",
                institution,
                section,
                text,
            )
        # CRM configuration is an explicit new-copy seed; no academic data is copied.
        from app.modules.crm_configuration.application.service import Configuration

        document = Configuration(stages=[], tags=[], fields=[]).model_dump_json()
        c.execute(
            "INSERT crm_config.Configuration(ConfigurationId,Document,Revision) VALUES(1,?,1)",
            document,
        )


def validate_data(cursor, prefix, seed):
    """Check durable required data without replacing legitimate user edits."""
    if prefix == 0:
        return
    c = Cursor(cursor)
    context = canonical_context(
        c.execute(
            "SELECT ContextId,CONVERT(varchar(36),InstitutionId),ContractVersion FROM crm_channels2.Context"
        ).fetchall()
    )
    if context != [[1, seed["institution"], "CBN-channels-parity-v1"]]:
        raise ValueError("P2ES_context_seed_drift")
    if prefix == 1:
        return
    institutions = c.execute(
        "SELECT CONVERT(varchar(36),InstitutionId),BootstrapHash,InitializedAt FROM crm_access.Institution"
    ).fetchall()
    if len(institutions) != 1 or str(UUID(institutions[0][0])) != seed["institution"]:
        raise ValueError("P2ES_institution_seed_drift")
    initialized = institutions[0][2] is not None
    if (
        initialized
        and institutions[0][1] is not None
        or not initialized
        and bytes(institutions[0][1] or b"").hex() != seed["bootstrap_sha256"]
    ):
        raise ValueError("P2ES_bootstrap_state_drift")
    roles = records(
        c,
        "SELECT RoleKey,Name,Actions,Protected,Active,Revision FROM crm_access.Role WHERE InstitutionId=?",
        (seed["institution"],),
    )
    if not set(ROLE_ACTIONS) <= {row["RoleKey"] for row in roles}:
        raise ValueError("P2ES_missing_builtin_role")
    from app.institutional.models import RoleEdit

    for role in roles:
        actions = json.loads(role["Actions"])
        RoleEdit(
            operation_id="00000000-0000-0000-0000-000000000000",
            revision=role["Revision"],
            name=role["Name"],
            active=bool(role["Active"]),
            actions=actions,
        )
        if role["RoleKey"] in {"owner", "admin"} and (
            not role["Protected"]
            or not role["Active"]
            or set(actions) != set(ROLE_ACTIONS[role["RoleKey"]])
        ):
            raise ValueError("P2ES_protected_role_drift")
    users = c.execute(
        "SELECT COUNT(*) FROM crm_access.AccessUser WHERE InstitutionId=?",
        seed["institution"],
    ).fetchval()
    administrators = c.execute(
        "SELECT COUNT(*) FROM crm_access.AccessUser WHERE InstitutionId=? AND Active=1 AND PasswordHash IS NOT NULL AND RoleKey IN('owner','admin')",
        seed["institution"],
    ).fetchval()
    owners = c.execute(
        "SELECT COUNT(*) FROM crm_access.AccessUser WHERE InstitutionId=? AND Active=1 AND PasswordHash IS NOT NULL AND RoleKey='owner'",
        seed["institution"],
    ).fetchval()
    if initialized and (administrators < 1 or owners < 1) or not initialized and users:
        raise ValueError("P2ES_administrator_state_drift")
    from app.institutional.models import SECTIONS

    current = c.execute(
        "SELECT Section,Document,Revision FROM crm_access.Setting WHERE InstitutionId=?",
        seed["institution"],
    ).fetchall()
    documents = {row[0]: json.loads(row[1]) for row in current}
    if set(documents) != set(SECTIONS):
        raise ValueError("P2ES_missing_setting_section")
    for section, document in documents.items():
        SECTIONS[section].model_validate(document)
    for section, text, revision in current:
        historical = c.execute(
            "SELECT Document FROM crm_access.SettingHistory WHERE InstitutionId=? AND Section=? AND Revision=?",
            seed["institution"],
            section,
            revision,
        ).fetchval()
        if historical is None or sha(json.loads(historical)) != sha(json.loads(text)):
            raise ValueError("P2ES_setting_history_missing_or_conflicting")
    from app.institutional.model_settings import validate_projection

    try:
        validate_projection(documents["ai"], documents["models"])
    except Exception:
        raise ValueError("P2ES_model_selection_projection_drift") from None
    from app.modules.crm_configuration.application.service import Configuration

    configuration = c.execute(
        "SELECT ConfigurationId,Document,Revision FROM crm_config.Configuration"
    ).fetchall()
    if len(configuration) != 1 or configuration[0][0] != 1 or configuration[0][2] < 1:
        raise ValueError("P2ES_configuration_singleton_missing")
    Configuration.model_validate_json(configuration[0][1])


def parent_history(cursor, package):
    columns = [
        r[0]
        for r in cursor.execute(
            "SELECT name FROM sys.columns WHERE object_id=OBJECT_ID('crm_meta.MigrationJournal') ORDER BY column_id"
        ).fetchall()
    ]
    rows = [
        list(r)
        for r in cursor.execute(
            "SELECT "
            + ",".join("CONVERT(varbinary(max),[" + column + "])" for column in columns)
            + " FROM crm_meta.MigrationJournal WHERE EventId<=? ORDER BY EventId",
            package["parent_journal_rows"],
        ).fetchall()
    ]
    if (
        len(rows) != package["parent_journal_rows"]
        or sha(rows) != package["parent_journal_sha256"]
    ):
        raise ValueError("P2ES_parent_history_changed")


def journal(cursor, actual, unit, attempt, kind, manifest, seed, before, after=None):
    cursor.execute(
        "INSERT crm_meta.MigrationJournal(AttemptId,UnitId,EventKind,ReleaseId,ToolVersion,ManifestSha256,UnitSha256,ShapeVersion,TargetSha256,BeforeShapeSha256,AfterShapeSha256,EvidenceRef,ApprovalRef,BackupRef,PrincipalRef,SuccessKey) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        attempt,
        unit["id"],
        kind,
        VERSION,
        VERSION,
        bytes.fromhex(manifest),
        bytes.fromhex(unit["sha256"]),
        VERSION,
        bytes.fromhex(target_hash(actual, seed)),
        bytes.fromhex(before),
        bytes.fromhex(after) if after else None,
        "P2ES/" + seed_binding(seed),
        "owner-P2-20261026",
        "native-restore-before-first-apply",
        ACTOR,
        unit["id"] if kind == "COMMITTED" else None,
    )


def history(cursor, package, manifest, actual, seed):
    parent_history(cursor, package)
    events = records(
        cursor,
        "SELECT * FROM crm_meta.MigrationJournal WHERE EventId>? ORDER BY EventId",
        (package["parent_journal_rows"],),
    )
    if len(events) > 10000:
        raise ValueError("P2ES_history_limit")
    units = {u["id"]: u for u in package["units"]}
    attempts, committed = {}, []
    for row in events:
        unit = units.get(row["UnitId"])
        if unit is None or any(
            row[key] != value
            for key, value in {
                "ReleaseId": VERSION,
                "ToolVersion": VERSION,
                "ShapeVersion": VERSION,
                "PrincipalRef": ACTOR,
                "EvidenceRef": "P2ES/" + seed_binding(seed),
                "ApprovalRef": "owner-P2-20261026",
                "BackupRef": "native-restore-before-first-apply",
                "ErrorCode": None,
            }.items()
        ):
            raise ValueError("P2ES_history_header")
        if (
            tuple(
                bytes(row[k]).hex()
                for k in ("ManifestSha256", "UnitSha256", "TargetSha256")
            )
            != (manifest, unit["sha256"], target_hash(actual, seed))
            or row["BeforeShapeSha256"] is None
        ):
            raise ValueError("P2ES_history_binding")
        attempt = str(row["AttemptId"]).lower()
        state = attempts.get(attempt)
        kind = row["EventKind"]
        if state is None:
            if kind != "STARTED":
                raise ValueError("P2ES_history_start_order")
            state = {"start": row, "status": "STARTED", "commit": None}
            attempts[attempt] = state
        elif row["UnitId"] != state["start"]["UnitId"] or bytes(
            row["BeforeShapeSha256"]
        ) != bytes(state["start"]["BeforeShapeSha256"]):
            raise ValueError("P2ES_history_attempt_binding")
        if kind == "STARTED":
            if (
                row is not state["start"]
                or row["AfterShapeSha256"] is not None
                or row["SuccessKey"] is not None
            ):
                raise ValueError("P2ES_duplicate_start")
        elif kind == "COMMITTED":
            if (
                state["status"] != "STARTED"
                or row["SuccessKey"] != unit["id"]
                or row["AfterShapeSha256"] is None
            ):
                raise ValueError("P2ES_commit_order")
            state.update(status="COMMITTED", commit=row)
            committed.append(row)
        elif kind == "RECONCILED_COMMITTED":
            if (
                state["status"] != "COMMITTED"
                or row["SuccessKey"] is not None
                or bytes(row["AfterShapeSha256"] or b"")
                != bytes(state["commit"]["AfterShapeSha256"])
            ):
                raise ValueError("P2ES_commit_confirmation")
            state["status"] = kind
        elif kind == "RECONCILED_NOT_APPLIED":
            if (
                state["status"] != "STARTED"
                or row["SuccessKey"] is not None
                or row["AfterShapeSha256"] is not None
            ):
                raise ValueError("P2ES_not_applied_order")
            state["status"] = kind
        else:
            raise ValueError("P2ES_history_event")
    if [r["UnitId"] for r in committed] != list(UNITS[: len(committed)]):
        raise ValueError("P2ES_history_prefix")
    if len(committed) > 1 and bytes(committed[1]["BeforeShapeSha256"]) != bytes(
        committed[0]["AfterShapeSha256"]
    ):
        raise ValueError("P2ES_history_shape_chain")
    return attempts, committed


def enter(connection, expected):
    if connection.autocommit is not True:
        raise ValueError("P2ES_autocommit_required")
    cursor = connection.cursor()
    if cursor.execute("SELECT @@TRANCOUNT").fetchval() != 0:
        cursor.close()
        raise ValueError("P2ES_caller_transaction_not_owned")
    actual = guard(cursor, expected)
    row = cursor.execute(
        "SELECT ORIGINAL_LOGIN(),SUSER_SNAME(),USER_NAME(),HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','CONTROL')"
    ).fetchone()
    if row[0] != row[1] or row[2] != "dbo" or row[3] != 1:
        cursor.close()
        raise ValueError("P2ES_preparer_required")
    try:
        acquire(cursor, "crm.schema.migrate.v1", "Session")
        acquire(cursor, "crm.local.commit", "Session")
        initial_data = None
        if not cursor.execute(
            "SELECT 1 FROM crm_meta.MigrationJournal WHERE SuccessKey IN(?,?)", *UNITS
        ).fetchone():
            from tools.p2_es_recovery import data_fingerprint

            initial_data = data_fingerprint(cursor, omit_journal=True)
        cursor.execute(
            "EXEC sys.sp_set_session_context @key=N'CBN_P2ES_TARGET',@value=?",
            actual["database"],
        )
        cursor.execute("EXECUTE AS USER=N'cbn_institutional_es_migrator'")
        if (
            cursor.execute(
                "SELECT HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','CONTROL')"
            ).fetchval()
            != 0
            or cursor.execute("SELECT IS_MEMBER('db_owner')").fetchval() != 0
        ):
            raise ValueError("P2ES_migrator_privilege_overlay")
    except BaseException:
        leave(cursor, connection)
        raise
    return cursor, actual, initial_data


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
            raise ValueError("P2ES_WAL_record_shape")
        kind = event.get("event")
        allowed = set(WAL_BINDING) | {"event", "previous", "hash"}
        if kind in {"COMMITTED", "RECONCILED_COMMITTED"}:
            allowed.add("after")
        if not set(WAL_BINDING) | {"event"} <= set(event) or not set(event) <= allowed:
            raise ValueError("P2ES_WAL_record_shape")
        if (
            kind not in TERMINAL | {"STARTED", "FAILED_OR_UNCERTAIN"}
            or event["unit"] not in UNITS
            or event["version"] != VERSION
        ):
            raise ValueError("P2ES_WAL_event_kind")
        binding = tuple(event[k] for k in ("version", "target", "manifest"))
        if file_binding is not None and binding != file_binding:
            raise ValueError("P2ES_WAL_file_binding")
        file_binding = binding
        try:
            if str(UUID(event["attempt"])) != event["attempt"]:
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            raise ValueError("P2ES_WAL_attempt_id") from None
        for key in ("target", "manifest", "unit_sha256", "before") + (
            ("after",) if kind in {"COMMITTED", "RECONCILED_COMMITTED"} else ()
        ):
            if type(event.get(key)) is not str or not re.fullmatch(
                r"[0-9a-f]{64}", event[key]
            ):
                raise ValueError("P2ES_WAL_hash_field")
        attempt = event["attempt"]
        prior = states.get(attempt)
        if kind == "STARTED":
            if prior:
                raise ValueError("P2ES_WAL_duplicate_start")
            states[attempt] = {"start": event, "status": "STARTED"}
        else:
            if prior is None or prior["status"] in TERMINAL:
                raise ValueError("P2ES_WAL_terminal_order")
            if any(event[k] != prior["start"][k] for k in WAL_BINDING):
                raise ValueError("P2ES_WAL_cross_attempt_binding")
            if kind == "FAILED_OR_UNCERTAIN" and prior["status"] != "STARTED":
                raise ValueError("P2ES_WAL_uncertain_order")
            prior["status"] = kind
    return states


def wal_events(path):
    if not Path(path).exists():
        return []
    if Path(path).stat().st_size > 2_000_000:
        raise ValueError("P2ES_WAL_size")
    events = []
    previous = "0" * 64
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        recorded = event.pop("hash")
        if event["previous"] != previous or sha(event) != recorded:
            raise ValueError("P2ES_WAL_integrity")
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


def validate_wal(events, attempts, manifest, actual, seed, package):
    units = {u["id"]: u for u in package["units"]}
    for attempt, state in wal_state(events).items():
        start = state["start"]
        if (start["target"], start["manifest"], start["unit_sha256"]) != (
            target_hash(actual, seed),
            manifest,
            units[start["unit"]]["sha256"],
        ):
            raise ValueError("P2ES_WAL_binding")
        sql = attempts.get(attempt)
        if sql and (
            sql["start"]["UnitId"] != start["unit"]
            or bytes(sql["start"]["BeforeShapeSha256"]).hex() != start["before"]
        ):
            raise ValueError("P2ES_SQL_WAL_attempt_binding")
        if state["status"] in {"COMMITTED", "RECONCILED_COMMITTED"}:
            terminal = next(e for e in reversed(events) if e["attempt"] == attempt)
            if (
                not sql
                or sql["status"] not in {"COMMITTED", "RECONCILED_COMMITTED"}
                or terminal["after"] != bytes(sql["commit"]["AfterShapeSha256"]).hex()
            ):
                raise ValueError("P2ES_WAL_SQL_commit_proof")
        elif state["status"] == "RECONCILED_NOT_APPLIED" and (
            not sql or sql["status"] != "RECONCILED_NOT_APPLIED"
        ):
            raise ValueError("P2ES_WAL_not_applied_SQL_proof")


def apply(
    connection,
    expected,
    wal,
    seed,
    *,
    approved_manifest_sha256,
    approved_initial_shape_sha256,
    approved_initial_data_sha256,
    fault=None,
):
    package = release(approved_manifest_sha256)
    seed_binding(seed)
    if not re.fullmatch(r"[0-9a-f]{64}", approved_initial_shape_sha256):
        raise ValueError("P2ES_initial_shape_approval_required")
    if not re.fullmatch(r"[0-9a-f]{64}", approved_initial_data_sha256):
        raise ValueError("P2ES_initial_data_approval_required")
    cursor, actual, initial_data = enter(connection, expected)
    try:
        attempts, committed = history(
            cursor, package, approved_manifest_sha256, actual, seed
        )
        events = wal_events(wal)
        validate_wal(events, attempts, approved_manifest_sha256, actual, seed, package)
        if pending_wal(events) or any(
            a["status"] == "STARTED" for a in attempts.values()
        ):
            raise ValueError("P2ES_independent_reconciliation_required")
        before = shape(cursor)
        if before != (
            bytes(committed[-1]["AfterShapeSha256"]).hex()
            if committed
            else approved_initial_shape_sha256
        ):
            raise ValueError("P2ES_catalog_or_initial_drift")
        validate_data(cursor, len(committed), seed)
        if not committed:
            if initial_data["sha256"] != approved_initial_data_sha256:
                raise ValueError("P2ES_unapproved_initial_data")
        applied = 0
        for unit in package["units"][len(committed) :]:
            before = shape(cursor)
            attempt = str(uuid4())
            start = {
                "event": "STARTED",
                "unit": unit["id"],
                "attempt": attempt,
                "version": VERSION,
                "target": target_hash(actual, seed),
                "manifest": approved_manifest_sha256,
                "unit_sha256": unit["sha256"],
                "before": before,
            }
            receipt(wal, start)
            if fault == unit["id"] + ":after_wal_before_SQL_started":
                raise RuntimeError("P2ES_controlled_WAL_gap")
            journal(
                cursor,
                actual,
                unit,
                attempt,
                "STARTED",
                approved_manifest_sha256,
                seed,
                before,
            )
            cursor.execute("BEGIN TRANSACTION")
            try:
                for batch in ddl_batches(unit):
                    cursor.execute(batch)
                    while cursor.nextset():
                        pass
                seed_unit(cursor, unit["id"], seed)
                validate_data(cursor, UNITS.index(unit["id"]) + 1, seed)
                verify_model(cursor, unit["id"])
                if fault == unit["id"] + ":ddl_error":
                    cursor.execute("CREATE TABLE dbo.P2ControlledSyntaxError(")
                after = shape(cursor)
                if fault == unit["id"] + ":connection_loss_before_commit":
                    connection.close()
                    raise RuntimeError("P2ES_controlled_connection_loss")
                if fault == unit["id"] + ":before_commit":
                    raise RuntimeError("P2ES_controlled_precommit")
                journal(
                    cursor,
                    actual,
                    unit,
                    attempt,
                    "COMMITTED",
                    approved_manifest_sha256,
                    seed,
                    before,
                    after,
                )
                cursor.execute("COMMIT")
                if fault == unit["id"] + ":after_commit":
                    raise RuntimeError("P2ES_controlled_commit_ACK_loss")
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


def reconcile(connection, expected, wal, seed, *, approved_manifest_sha256, fault=None):
    package = release(approved_manifest_sha256)
    seed_binding(seed)
    cursor, actual, _ = enter(connection, expected)
    try:
        attempts, committed = history(
            cursor, package, approved_manifest_sha256, actual, seed
        )
        validate_data(cursor, len(committed), seed)
        events = wal_events(wal)
        validate_wal(events, attempts, approved_manifest_sha256, actual, seed, package)
        result = []
        for event in pending_wal(events):
            unit = next(u for u in package["units"] if u["id"] == event["unit"])
            sql = attempts.get(event["attempt"])
            success = next((r for r in committed if r["UnitId"] == unit["id"]), None)
            current = shape(cursor)
            if sql and sql["status"] == "RECONCILED_NOT_APPLIED":
                status, after, confirmed = "RECONCILED_NOT_APPLIED", None, True
            elif success:
                if (
                    str(success["AttemptId"]).lower() != event["attempt"]
                    or bytes(success["AfterShapeSha256"]).hex() != current
                ):
                    raise ValueError("P2ES_recovery_commit_attempt_or_shape")
                status, after, confirmed = (
                    "RECONCILED_COMMITTED",
                    current,
                    sql["status"] == "RECONCILED_COMMITTED",
                )
            elif current == event["before"]:
                status, after, confirmed = "RECONCILED_NOT_APPLIED", None, False
            else:
                raise ValueError("P2ES_recovery_unknown_shape")
            if sql is None:
                journal(
                    cursor,
                    actual,
                    unit,
                    event["attempt"],
                    "STARTED",
                    approved_manifest_sha256,
                    seed,
                    event["before"],
                )
                if fault == "after_recovered_SQL_started":
                    raise RuntimeError("P2ES_controlled_recovered_STARTED_ACK")
            if not confirmed:
                journal(
                    cursor,
                    actual,
                    unit,
                    event["attempt"],
                    status,
                    approved_manifest_sha256,
                    seed,
                    event["before"],
                    after,
                )
            terminal_receipt(wal, event, status, after)
            result.append(status)
        return {"reconciled": result}
    finally:
        leave(cursor, connection)
