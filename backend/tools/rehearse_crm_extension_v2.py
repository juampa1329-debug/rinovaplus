"""Explicit C7 backup/reference/trial harness. No application or worker startup."""

import argparse
import contextlib
import json
import os
import uuid
from pathlib import Path, PureWindowsPath

import pyodbc

from app import foundation
from tools.cbn_foundation import Audit, acquire, drain, target_identity
from tools.crm_extension_contract import verify_final_shape
from tools.crm_extension_snapshot_v2 import (
    VERSION,
    encode,
    extension_shape,
    journal_binary,
    metadata,
    partition_tables,
    preservation,
    protected,
    quote_name,
    require,
    sha,
    table_names,
    table_sets,
    validate_extra_catalog,
)
from tools.crm_extension_v2 import (
    ACTOR,
    DENIED_DBO,
    PACKAGE,
    PERMISSIONS,
    RELEASE,
    ROOT,
    SQL_FILE,
    TARGET,
    TOOL_VERSION,
    UNIT,
    assets,
    file_sha,
    guard,
    run,
    verify_direct_acl,
    verify_effective_acl,
    verify_legacy_actor,
)
from tools.foundation_snapshot import metadata as legacy_metadata
from tools.rehearse_foundation import (
    checkdb,
    execute_results,
    literal,
    private_profile,
)
from tools.rehearse_foundation_ui import signatures

pyodbc.pooling = False
SOURCE = foundation.DATABASE


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(encode(value) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


@contextlib.contextmanager
def admin(database, context, *, readonly=False):
    from app.sql_target import HOST, _quoted

    require(
        database in {SOURCE, "HORARIOSSIIE", "master"}
        or bool(TARGET.fullmatch(database)),
        "unapproved_database",
    )
    c = private_profile()["connection"]
    require(
        HOST.fullmatch(c["server"]) and HOST.fullmatch(c["certificate_hostname"]),
        "invalid_tls_endpoint",
    )
    text = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER=tcp:{c['server']},{c['port']};DATABASE={_quoted(database)};"
        "Encrypt=Yes;TrustServerCertificate=No;"
        f"HostnameInCertificate={c['certificate_hostname']};"
        f"UID={_quoted(c['username'])};PWD={_quoted(c['password'])};"
        "APP=CBN SQL-C7 isolated extension;"
    )
    connection = pyodbc.connect(text, timeout=5, autocommit=True, readonly=readonly)
    try:
        connection.timeout = 120
        cursor = connection.cursor()
        actual = target_identity(cursor)
        require(
            [actual[k] for k in ("machine", "server", "instance", "engine")]
            == [context["identity"][i] for i in (1, 2, 3, 4)],
            "server_identity",
        )
        require(
            actual["database"] == database and actual["engine"] == 16,
            "local_server_contract",
        )
        require(
            cursor.execute("SELECT IS_SRVROLEMEMBER('sysadmin')").fetchval() == 1,
            "administrative_evidence_connection",
        )
        require(
            not cursor.execute("SELECT 1 FROM sys.server_triggers").fetchone(),
            "server_trigger",
        )
        cursor.close()
        yield connection
    finally:
        connection.close()


def authenticate_legacy_catalog(cursor, expected):
    require(
        sha(foundation.project_academic(legacy_metadata(cursor, managed=False)))
        == expected["academic"],
        "C5_academic_catalog_changed",
    )
    require(
        sha(foundation.project_managed(legacy_metadata(cursor, managed=True)))
        == expected["managed"],
        "C5_foundation_catalog_changed",
    )


def capture(connection, legacy=None):
    cursor = connection.cursor()
    cursor.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE; BEGIN TRANSACTION;")
    try:
        if legacy is not None:
            authenticate_legacy_catalog(cursor, legacy)
        shape = metadata(cursor)
        names = table_names(shape)
        partition_tables(names, set(names) == table_sets(True))
        data = preservation(cursor)
        prefix = journal_binary(cursor, 5)
        all_journal = journal_binary(cursor)
        if legacy is not None:
            authenticate_legacy_catalog(cursor, legacy)
        cursor.execute("COMMIT; SET TRANSACTION ISOLATION LEVEL READ COMMITTED;")
        return {
            "shape": shape,
            "preservation": data,
            "legacy_journal_sha256": sha(prefix),
            "journal_sha256": sha(all_journal),
            "journal_rows": len(all_journal),
        }
    except BaseException:
        cursor.execute("IF @@TRANCOUNT>0 ROLLBACK;")
        raise
    finally:
        cursor.close()


def restore(cursor, backup, context, kind):
    require(kind in {"REF", "TRIAL", "FAULT"}, "restore_kind")
    name = "CBN_C7_" + kind + "_20261025_" + uuid.uuid4().hex[:8]
    require(TARGET.fullmatch(name) is not None, "restore_name")
    require(
        not cursor.execute("SELECT 1 FROM sys.databases WHERE name=?", name).fetchone(),
        "restore_database_collision",
    )
    files = execute_results(cursor, "RESTORE FILELISTONLY FROM DISK=" + literal(backup))
    require(
        len(files) == 2 and {f["Type"] for f in files} == {"D", "L"}, "backup_files"
    )
    moves = []
    for item in files:
        log = item["Type"] == "L"
        path = str(
            PureWindowsPath(context["paths"][2 if log else 1])
            / (name + ("_log.ldf" if log else ".mdf"))
        )
        require(PureWindowsPath(path).is_absolute(), "file_path")
        require(
            cursor.execute(
                "SELECT file_exists FROM sys.dm_os_file_exists(?)", path
            ).fetchval()
            == 0,
            "restore_file_collision",
        )
        moves.append("MOVE " + literal(item["LogicalName"]) + " TO " + literal(path))
    statement = (
        "RESTORE DATABASE "
        + quote_name(name)
        + " FROM DISK="
        + literal(backup)
        + " WITH "
        + ",".join(moves)
        + ",RECOVERY,CHECKSUM;"
    )
    require("REPLACE" not in statement, "replace_forbidden")
    execute_results(cursor, statement)
    checkdb(cursor, name)
    return name


def start(work, c5_before, runtime):
    require(not (work / "state.json").exists(), "already_started")
    previous = load(c5_before)
    context = previous["context"]
    current = signatures(context, runtime)
    require(
        all(
            current[k] == previous["signatures"][k]
            for k in ("source", "academic", "journal")
        ),
        "C5_accepted_context_changed",
    )
    state = {
        "scope": "SQL-C7-isolated-extension-only",
        "context": context,
        "runtime_directory": str(runtime),
        "c5_signatures": current,
        "databases": [],
    }
    backup = str(
        PureWindowsPath(context["paths"][0])
        / ("CBN_C7_POPULATED_" + uuid.uuid4().hex + ".bak")
    )
    with admin(SOURCE, context) as source:
        cursor = source.cursor()
        acquire(cursor, "crm.local.commit", "Session")
        try:
            legacy = {
                "academic": current["academic"]["metadata_sha256"],
                "managed": sha(foundation.assets()[1]),
            }
            before = capture(source, legacy)
            verify_legacy_actor(before["shape"])
            partition_tables(table_names(before["shape"]), False)
            require(
                before["journal_rows"] == 5
                and before["legacy_journal_sha256"] == current["journal"],
                "legacy_journal",
            )
            validate_extra_catalog(before["shape"])
            with admin("master", context) as master:
                m = master.cursor()
                require(
                    m.execute(
                        "SELECT file_exists FROM sys.dm_os_file_exists(?)", backup
                    ).fetchval()
                    == 0,
                    "backup_collision",
                )
                execute_results(
                    m,
                    "BACKUP DATABASE "
                    + quote_name(SOURCE)
                    + " TO DISK="
                    + literal(backup)
                    + " WITH COPY_ONLY,CHECKSUM;",
                )
                execute_results(
                    m,
                    "RESTORE VERIFYONLY FROM DISK="
                    + literal(backup)
                    + " WITH CHECKSUM;",
                )
            require(capture(source, legacy) == before, "source_changed_during_backup")
            state.update(backup=backup, source=before)
            save(work / "state.json", state)
        finally:
            cursor.execute(
                "EXEC sys.sp_releaseapplock @Resource=N'crm.local.commit',"
                "@LockOwner=N'Session';"
            )
            cursor.close()
    with admin("master", context) as master:
        for kind in ("REF", "TRIAL", "FAULT"):
            name = restore(master.cursor(), backup, context, kind)
            state["databases"].append({"kind": kind, "name": name})
            save(work / "state.json", state)
            with admin(name, context, readonly=True) as restored:
                require(
                    capture(restored) == before, "restored_populated_state_mismatch"
                )
    report(
        work,
        "backup_restores",
        databases=len(state["databases"]),
        backup_checksum_verified=True,
        restored_checkdb=True,
        academic_tables=50,
        academic_rows=before["preservation"]["academic"]["rows"],
        crm_business_rows=before["preservation"]["business"]["rows"],
        journal_rows=5,
        source_unchanged=True,
    )


def report(work, phase, **fields):
    value = {"stage": "SQL-C7", "phase": phase, **fields}
    save(work / (phase + "-result.json"), value)
    print(json.dumps(value), flush=True)


def prepare_database(connection, source):
    identity = target_identity(connection.cursor())
    require(
        bool(TARGET.fullmatch(identity["database"]))
        and identity["engine"] == 16
        and identity["compatibility"] == 160,
        "isolated_restoration_required_before_preparation",
    )
    before = capture(connection)
    require(before == source, "clone_not_accepted_source")
    cursor = connection.cursor()
    require(
        not cursor.execute(
            "SELECT 1 FROM sys.schemas WHERE name=N'crm_channels'"
        ).fetchone(),
        "schema_collision",
    )
    require(
        not cursor.execute(
            "SELECT 1 FROM sys.database_principals WHERE name=?", ACTOR
        ).fetchone(),
        "principal_collision",
    )
    cursor.execute("BEGIN TRANSACTION;")
    try:
        cursor.execute("CREATE SCHEMA crm_channels AUTHORIZATION dbo;")
        cursor.execute(
            "CREATE USER "
            + quote_name(ACTOR)
            + " WITHOUT LOGIN WITH DEFAULT_SCHEMA=dbo;"
        )
        for cls, target, permission in sorted(PERMISSIONS):
            scope = (
                ""
                if cls == "DATABASE"
                else (
                    " ON SCHEMA::crm_channels"
                    if cls == "SCHEMA"
                    else " ON OBJECT::"
                    + ".".join(quote_name(p) for p in target.split("."))
                )
            )
            cursor.execute(
                "GRANT " + permission + scope + " TO " + quote_name(ACTOR) + ";"
            )
        for permission in sorted(DENIED_DBO):
            cursor.execute(
                "DENY " + permission + " ON SCHEMA::dbo TO " + quote_name(ACTOR) + ";"
            )
        raw = metadata(cursor)
        sid = next(p["sid"] for p in raw["principals"] if p["name"] == ACTOR)
        verify_direct_acl(raw, sid)
        verify_effective_acl(cursor)
        require(
            sha(protected(raw)) == sha(protected(before["shape"])),
            "preparation_changed_existing_metadata",
        )
        require(
            preservation(cursor) == before["preservation"], "preparation_changed_data"
        )
        require(
            sha(journal_binary(cursor)) == before["journal_sha256"],
            "preparation_changed_journal",
        )
        cursor.execute("COMMIT;")
    except BaseException:
        cursor.execute("IF @@TRANCOUNT>0 ROLLBACK;")
        raise
    return {
        "scope": "SQL-C7-isolated-extension-only",
        "identity": target_identity(cursor),
        "actor_sid": sid,
        "protected_metadata_sha256": sha(protected(raw)),
        "preservation": before["preservation"],
        "legacy_rows": 5,
        "legacy_journal_sha256": before["legacy_journal_sha256"],
        "evidence_ref": "SQL-C7-restored-channels",
        "approval_ref": "owner-continue-C7-20261025",
        "backup_ref": "C7-populated-copy-verified",
    }


def reference(work):
    state = load(work / "state.json")
    require(
        not (work / "reference-shapes.json").exists(), "reference_already_completed"
    )
    with admin(SOURCE, state["context"]) as source:
        cursor = source.cursor()
        acquire(cursor, "crm.local.commit", "Session")
        try:
            legacy = {
                "academic": state["c5_signatures"]["academic"]["metadata_sha256"],
                "managed": sha(foundation.assets()[1]),
            }
            require(
                capture(source, legacy) == state["source"], "source_baseline_changed"
            )
        finally:
            cursor.execute(
                "EXEC sys.sp_releaseapplock @Resource=N'crm.local.commit',"
                "@LockOwner=N'Session';"
            )
            cursor.close()
    tickets = state.setdefault("tickets", {})
    for db in state["databases"]:
        with admin(db["name"], state["context"]) as connection:
            if db["kind"] in tickets:
                guard(connection.cursor(), tickets[db["kind"]])
                continue
            audit = Audit(
                work / ("prepare-" + db["kind"] + ".jsonl"),
                sha(target_identity(connection.cursor())),
            )
            require(not audit.unresolved(), "preparation_requires_inspection")
            attempt = str(uuid.uuid4())
            audit.add(attempt, "C7-PREPARE", "STARTED")
            try:
                tickets[db["kind"]] = prepare_database(connection, state["source"])
                save(work / "state.json", state)
                audit.add(attempt, "C7-PREPARE", "COMMITTED")
            except BaseException:
                audit.add(attempt, "C7-PREPARE", "UNKNOWN")
                raise
    ticket = tickets["REF"]
    with admin(ticket["identity"]["database"], state["context"]) as connection:
        cursor = connection.cursor()
        cursor.execute("BEGIN TRANSACTION;")
        acquire(cursor, "crm.local.commit", "Transaction")
        before = guard(cursor, ticket)
        cursor.execute(
            "EXEC sys.sp_set_session_context @key=N'CBN_C7_TARGET',@value=?;",
            ticket["identity"]["database"],
        )
        cursor.execute("EXECUTE AS USER=N'" + ACTOR + "';")
        try:
            cursor.execute((PACKAGE / SQL_FILE).read_text(encoding="utf-8"))
            drain(cursor)
        finally:
            cursor.execute("REVERT;")
        after = guard(cursor, ticket)
        partition_tables(table_names(after), True)
        require(
            preservation(cursor) == ticket["preservation"], "reference_data_changed"
        )
        verify_final_shape(after, ticket["identity"]["collation"])
        cursor.execute("COMMIT;")
        cursor.execute("BEGIN TRANSACTION;")
        cursor.execute(
            "INSERT crm_channels.Audit(Channel,Action) "
            "VALUES('test','canonical regression');"
        )
        cursor.execute("ROLLBACK;")
        require(
            sha(guard(cursor, ticket)) == sha(after),
            "identity_gap_changed_canonical_shape",
        )
        require(
            cursor.execute("SELECT COUNT(*) FROM crm_channels.Audit").fetchval() == 0,
            "reference_probe_left_rows",
        )
        shapes = {
            "shape_version": VERSION,
            "prepared_sha256": sha(before),
            "CBN-B011_sha256": sha(after),
            "extension": extension_shape(after),
        }
        save(work / "reference-shapes.json", shapes)
    report(
        work,
        "reference",
        tables=8,
        columns=57,
        foreign_keys=10,
        before_sha256=shapes["prepared_sha256"],
        after_sha256=shapes["CBN-B011_sha256"],
        academic_and_crm_data_unchanged=True,
        migration_journal_unchanged=True,
    )


def amend_references(work):
    """Audited draft correction. Never changes a frozen release or source."""
    require(not (PACKAGE / "release.json").exists(), "frozen_release_amendment_refused")
    state = load(work / "state.json")
    for kind, ticket in state["tickets"].items():
        with admin(ticket["identity"]["database"], state["context"]) as connection:
            cursor = connection.cursor()
            require(target_identity(cursor) == ticket["identity"], "target_identity")
            raw = metadata(cursor)
            partition_tables(table_names(raw), False)
            require(
                sha(protected(raw)) == ticket["protected_metadata_sha256"],
                "protected_metadata",
            )
            require(preservation(cursor) == ticket["preservation"], "protected_data")
            require(
                sha(journal_binary(cursor)) == ticket["legacy_journal_sha256"],
                "journal",
            )
            addition = {
                "class_desc": "SCHEMA",
                "permission_name": "REFERENCES",
                "state_desc": "GRANT",
                "grantee": ACTOR,
                "grantor": "dbo",
                "minor_id": 0,
                "target": "crm_channels",
            }
            require(addition not in raw["all_permissions"], "amendment_already_present")
            simulated = {**raw, "all_permissions": raw["all_permissions"] + [addition]}
            verify_direct_acl(simulated, ticket["actor_sid"])
            audit = Audit(
                work / ("prepare-amend-" + kind + ".jsonl"), sha(ticket["identity"])
            )
            require(not audit.unresolved(), "amendment_requires_inspection")
            attempt = str(uuid.uuid4())
            audit.add(attempt, "C7-PREPARE-REFERENCES", "STARTED")
            cursor.execute("BEGIN TRANSACTION;")
            try:
                cursor.execute(
                    "GRANT REFERENCES ON SCHEMA::crm_channels TO "
                    + quote_name(ACTOR)
                    + ";"
                )
                guard(cursor, ticket)
                require(
                    preservation(cursor) == ticket["preservation"], "amendment_data"
                )
                cursor.execute("COMMIT;")
                audit.add(attempt, "C7-PREPARE-REFERENCES", "COMMITTED")
            except BaseException:
                cursor.execute("IF @@TRANCOUNT>0 ROLLBACK;")
                audit.add(attempt, "C7-PREPARE-REFERENCES", "UNKNOWN")
                raise
    report(
        work,
        "draft_preparation_amended",
        databases=len(state["tickets"]),
        only_new_schema_references_added=True,
        source_and_C5_runtime_unchanged=True,
    )


def freeze(work):
    require((work / "state.json").exists(), "state_required")
    shapes = load(work / "reference-shapes.json")
    require(not (PACKAGE / "release.json").exists(), "release_already_frozen")
    require(
        sha(load(PACKAGE / "expected-shapes.json")) == sha(shapes),
        "reference_shapes_not_copied",
    )
    paths = [
        "backend/migrations/cbn_channels_v2/" + n
        for n in (SQL_FILE, "partition.json", "expected-shapes.json")
    ]
    paths += [
        "backend/tools/crm_extension_v2.py",
        "backend/tools/crm_extension_snapshot_v2.py",
        "backend/tools/crm_extension_contract.py",
        "backend/migrations/cbn_channels/shape-spec.json",
        "backend/migrations/011_channels.sql",
        "backend/migrations/012_channels_identity_collation.sql",
    ]
    release = {
        "release_id": RELEASE,
        "unit": UNIT,
        "scope": "isolated_populated_restoration_only",
        "shape_version": VERSION,
        "tool_version": TOOL_VERSION,
        "institutional_sql2019_accepted": False,
        "engine_major": 16,
        "sql_sha256": file_sha(PACKAGE / SQL_FILE),
        "before_sha256": shapes["prepared_sha256"],
        "after_sha256": shapes["CBN-B011_sha256"],
        "files": [{"path": p, "sha256": file_sha(ROOT / p)} for p in paths],
        "retired_v1_sha256": (
            "e4f76c63592b4a99f35380496d25a34afb205645a0c4f5e885cf9ece8f901ca1"
        ),
        "base_release_sha256": file_sha(
            ROOT / "backend/migrations/cbn_foundation/release.json"
        ),
    }
    save(work / "release-to-persist.json", release)
    report(
        work,
        "freeze_prepared",
        files=len(paths),
        next_action="persist release without changing its bytes",
    )


def attach_release(work):
    state = load(work / "state.json")
    _, manifest_hash, _ = assets()
    for ticket in state["tickets"].values():
        ticket["release_sha256"] = manifest_hash
    save(work / "state.json", state)
    report(work, "release_frozen", release_sha256=manifest_hash)


def trial(work):
    state = load(work / "state.json")
    ticket = state["tickets"]["TRIAL"]
    with admin(ticket["identity"]["database"], state["context"]) as connection:
        require(
            run(connection, ticket, work / "trial-audit.jsonl") == "APPLIED",
            "trial_apply",
        )
        require(
            run(connection, ticket, work / "trial-audit.jsonl") == "NOOP", "trial_noop"
        )
        actual = capture(connection)
        require(
            actual["preservation"] == state["source"]["preservation"],
            "trial_preservation",
        )
        require(
            actual["legacy_journal_sha256"] == state["source"]["legacy_journal_sha256"],
            "trial_prefix",
        )
        require(actual["journal_rows"] == 7, "trial_journal_count")
        verify_final_shape(actual["shape"], ticket["identity"]["collation"])
        save(work / "trial-after.json", actual)
    report(
        work,
        "trial",
        database=ticket["identity"]["database"],
        applied=True,
        noop=True,
        academic_tables=50,
        academic_rows=actual["preservation"]["academic"]["rows"],
        populated_crm_preserved=True,
        original_journal_rows_preserved=5,
        total_journal_rows=7,
        extension_tables=8,
        extension_rows=0,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "start",
            "reference",
            "amend-references",
            "freeze",
            "attach-release",
            "trial",
        ),
    )
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--c5-before", type=Path)
    parser.add_argument("--runtime", type=Path, default=Path("/run/crm-foundation"))
    args = parser.parse_args()
    if args.action == "start":
        require(args.c5_before is not None, "C5_private_baseline_required")
        start(args.work, args.c5_before, args.runtime)
    elif args.action == "reference":
        reference(args.work)
    elif args.action == "amend-references":
        amend_references(args.work)
    elif args.action == "freeze":
        freeze(args.work)
    elif args.action == "attach-release":
        attach_release(args.work)
    else:
        trial(args.work)


if __name__ == "__main__":
    main()
