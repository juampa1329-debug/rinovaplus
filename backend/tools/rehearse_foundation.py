"""SQL-C3 isolated backup/restore harness; explicit commands only, no app startup."""

import argparse
import contextlib
import json
import uuid
from pathlib import Path, PureWindowsPath

import pyodbc

from tools.cbn_foundation import (
    LEGACY_FILES,
    PACKAGE,
    PRINCIPAL,
    ROOT,
    SQL_FILES,
    TARGET_NAME,
    TOOL_FILES,
    UNITS,
    append_event,
    drain,
    file_sha,
    guard,
    require,
    sha,
    target_identity,
    transaction,
)
from tools.foundation_snapshot import core_signature, metadata, quote_name

pyodbc.pooling = False
SOURCE = "HORARIOSSIIE"


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    path.chmod(0o600)


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def private_profile():
    from app.sql_profile import SqlProfileStore

    profile = SqlProfileStore(Path("/var/lib/crm-ai/database")).load()
    require(
        profile is not None and profile["connection"]["database"] == SOURCE,
        "saved_source_profile_required",
    )
    return profile


def connection_text(database):
    from app.sql_target import HOST, _quoted

    c = private_profile()["connection"]
    require(
        database in {SOURCE, "master"} or bool(TARGET_NAME.fullmatch(database)),
        "database_outside_rehearsal",
    )
    require(
        HOST.fullmatch(c["server"]) and HOST.fullmatch(c["certificate_hostname"]),
        "invalid_tls_endpoint",
    )
    return (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER=tcp:{c['server']},{c['port']};DATABASE={_quoted(database)};"
        "Encrypt=Yes;TrustServerCertificate=No;"
        f"HostnameInCertificate={c['certificate_hostname']};"
        f"UID={_quoted(c['username'])};PWD={_quoted(c['password'])};"
        "APP=CBN SQL-C3 rehearsal;"
    )


@contextlib.contextmanager
def admin(database, context, *, readonly=False):
    connection = pyodbc.connect(
        connection_text(database), timeout=5, autocommit=True, readonly=readonly
    )
    try:
        connection.timeout = 120
        cursor = connection.cursor()
        actual = target_identity(cursor)
        original = context["identity"]
        require(
            [actual[k] for k in ("machine", "server", "instance", "engine")]
            == [original[i] for i in (1, 2, 3, 4)],
            "server_identity_changed",
        )
        require(actual["database"] == database, "connection_database_changed")
        require(
            not cursor.execute("SELECT 1 FROM sys.server_triggers").fetchone(),
            "server_ddl_trigger_present",
        )
        cursor.close()
        yield connection
    finally:
        connection.close()


def capture(connection):
    cursor = connection.cursor()
    try:
        cursor.execute(
            "SET TRANSACTION ISOLATION LEVEL SERIALIZABLE; BEGIN TRANSACTION;"
        )
        result = core_signature(cursor)
        cursor.execute(
            "COMMIT TRANSACTION; SET TRANSACTION ISOLATION LEVEL READ COMMITTED;"
        )
        return result
    except BaseException:
        cursor.execute("IF @@TRANCOUNT>0 ROLLBACK TRANSACTION;")
        raise
    finally:
        cursor.close()


def literal(value):
    require(
        isinstance(value, str) and not any(ord(c) < 32 for c in value),
        "unsafe_sql_literal",
    )
    return "N'" + value.replace("'", "''") + "'"


def execute_results(cursor, sql, *params):
    cursor.execute(sql, *params)
    result = []
    while True:
        if cursor.description:
            names = [c[0] for c in cursor.description]
            result.extend(
                dict(zip(names, row, strict=True)) for row in cursor.fetchall()
            )
        if not cursor.nextset():
            break
    return result


def checkdb(cursor, database):
    errors = execute_results(
        cursor,
        "DBCC CHECKDB("
        + quote_name(database)
        + ") WITH TABLERESULTS,NO_INFOMSGS,ALL_ERRORMSGS;",
    )
    require(not errors, "restored_checkdb_failed")


def provision(connection):
    """Administrative preparation, deliberately separate from the unit commits."""
    cursor = connection.cursor()
    require(
        not cursor.execute(
            "SELECT 1 FROM sys.schemas WHERE name=N'crm' OR name LIKE N'crm[_]%'"
        ).fetchone(),
        "existing_managed_namespace",
    )
    require(
        not cursor.execute(
            "SELECT 1 FROM sys.database_principals WHERE name=?", PRINCIPAL
        ).fetchone(),
        "existing_migration_principal",
    )
    transaction(cursor)
    try:
        cursor.execute(
            f"CREATE USER {quote_name(PRINCIPAL)} WITHOUT LOGIN "
            "WITH DEFAULT_SCHEMA=dbo;"
        )
        cursor.execute(
            f"GRANT CREATE TABLE,VIEW DEFINITION TO {quote_name(PRINCIPAL)};"
        )
        for schema in ("crm_meta", "crm", "crm_config"):
            cursor.execute(
                "CREATE SCHEMA " + quote_name(schema) + " AUTHORIZATION dbo;"
            )
            permissions = (
                "ALTER,SELECT,INSERT"
                if schema == "crm_meta"
                else "ALTER,SELECT,INSERT,UPDATE,DELETE"
            )
            if schema == "crm":
                permissions += ",REFERENCES"
            cursor.execute(
                f"GRANT {permissions} ON SCHEMA::{quote_name(schema)} "
                f"TO {quote_name(PRINCIPAL)};"
            )
        cursor.execute(
            f"DENY UPDATE,DELETE ON SCHEMA::crm_meta TO {quote_name(PRINCIPAL)};"
        )
        cursor.execute("COMMIT TRANSACTION;")
    except BaseException:
        cursor.execute("IF @@TRANCOUNT>0 ROLLBACK TRANSACTION;")
        raise
    finally:
        cursor.close()


def restore(master_cursor, backup, context, kind):
    require(kind in {"REF", "TRIAL"}, "restore_kind")
    name = f"CBN_C3_{kind}_20261024_{uuid.uuid4().hex[:8]}"
    require(TARGET_NAME.fullmatch(name), "restore_name")
    require(
        master_cursor.execute(
            "SELECT 1 FROM sys.databases WHERE name=?", name
        ).fetchone()
        is None,
        "restore_database_collision",
    )
    files = execute_results(
        master_cursor, "RESTORE FILELISTONLY FROM DISK=" + literal(backup)
    )
    require(
        len(files) == 2 and {f["Type"] for f in files} == {"D", "L"},
        "unsupported_backup_files",
    )
    moves = []
    destinations = []
    for record in files:
        is_log = record["Type"] == "L"
        directory = context["paths"][2 if is_log else 1]
        path = str(
            PureWindowsPath(directory) / (name + ("_log.ldf" if is_log else ".mdf"))
        )
        require(PureWindowsPath(path).is_absolute(), "restore_path_not_absolute")
        require(
            master_cursor.execute(
                "SELECT file_exists FROM sys.dm_os_file_exists(?)", path
            ).fetchval()
            == 0,
            "restore_file_collision",
        )
        moves.append("MOVE " + literal(record["LogicalName"]) + " TO " + literal(path))
        destinations.append(path)
    sql = (
        "RESTORE DATABASE "
        + quote_name(name)
        + " FROM DISK="
        + literal(backup)
        + " WITH "
        + ",".join(moves)
        + ",RECOVERY,CHECKSUM;"
    )
    require("REPLACE" not in sql, "restore_replace_forbidden")
    execute_results(master_cursor, sql)
    checkdb(master_cursor, name)
    return name, destinations


def prepare(work):
    require(not (work / "state.json").exists(), "preparation_already_exists")
    context = load(work / "server-context.private.json")
    with admin(SOURCE, context, readonly=True) as source:
        before = capture(source)
        require(before["data"]["tables"] == 50, "source_table_count_changed")
        require(
            not source.cursor()
            .execute(
                "SELECT 1 FROM sys.schemas WHERE name=N'crm' OR name LIKE N'crm[_]%'"
            )
            .fetchone(),
            "source_namespace_changed",
        )
    save(work / "source-before.private.json", before)
    backup = str(
        PureWindowsPath(context["paths"][0])
        / ("CBN_C3_20261024_" + uuid.uuid4().hex + ".bak")
    )
    require(PureWindowsPath(backup).is_absolute(), "backup_path_not_absolute")
    state = {
        "unit": "SQL-C3",
        "source": SOURCE,
        "backup": backup,
        "targets": {},
        "source_signature": before,
        "context": context,
    }
    with admin("master", context) as master:
        cursor = master.cursor()
        require(
            cursor.execute(
                "SELECT file_exists FROM sys.dm_os_file_exists(?)", backup
            ).fetchval()
            == 0,
            "backup_file_collision",
        )
        execute_results(
            cursor,
            "BACKUP DATABASE "
            + quote_name(SOURCE)
            + " TO DISK="
            + literal(backup)
            + " WITH COPY_ONLY,CHECKSUM,NOINIT,NAME=N'CBN SQL-C3 isolated rehearsal';",
        )
        execute_results(
            cursor,
            "RESTORE VERIFYONLY FROM DISK=" + literal(backup) + " WITH CHECKSUM;",
        )
        header = execute_results(
            cursor, "RESTORE HEADERONLY FROM DISK=" + literal(backup)
        )
        require(
            len(header) == 1
            and header[0]["DatabaseName"] == SOURCE
            and header[0]["IsCopyOnly"]
            and header[0]["HasBackupChecksums"]
            and not header[0]["IsDamaged"],
            "backup_contract_failed",
        )
        state["backup_header"] = header[0]
        save(work / "state.json", state)
        for label, kind in (
            ("reference", "REF"),
            ("trial", "TRIAL"),
            ("faults", "TRIAL"),
        ):
            name, paths = restore(cursor, backup, context, kind)
            state["targets"][label] = {"database": name, "paths": paths}
            save(work / "state.json", state)
            with admin(name, context) as restored:
                restored_signature = capture(restored)
                require(
                    restored_signature == before, "restore_core_does_not_match_source"
                )
                provision(restored)
                prepared = capture(restored)
                require(prepared == before, "preparation_changed_academic_state")
                ticket = {
                    "scope": "restored_rehearsal_only",
                    "kind": kind,
                    "identity": target_identity(restored.cursor()),
                    "academic_table_count": 50,
                    "core_metadata_sha256": before["metadata_sha256"],
                    "backup_ref": "backup-" + str(header[0]["BackupSetGUID"]),
                    "evidence_ref": "SQL-C3-20261024",
                    "approval_ref": "user-SQL-C3-20261024",
                }
                save(work / (label + "-ticket.json"), ticket)
            print(
                json.dumps(
                    {"stage": "restored_and_prepared", "label": label, "database": name}
                ),
                flush=True,
            )
    with admin(SOURCE, context, readonly=True) as source:
        require(capture(source) == before, "source_changed_during_backup")
        require(
            not source.cursor()
            .execute(
                "SELECT 1 FROM sys.schemas WHERE name=N'crm' OR name LIKE N'crm[_]%'"
            )
            .fetchone(),
            "source_namespace_changed",
        )
    save(work / "state.json", state)
    return {
        "backup_checksum": True,
        "verifyonly": True,
        "restored_checkdb": 3,
        "source_unchanged": True,
        "restored_core_equal": True,
    }


@contextlib.contextmanager
def restricted(ticket, context):
    with admin(ticket["identity"]["database"], context) as connection:
        cursor = connection.cursor()
        require(
            target_identity(cursor) == ticket["identity"],
            "restore_ticket_identity_changed",
        )
        cursor.execute(
            "EXEC sys.sp_set_session_context "
            "@key=N'CBN_C3_TARGET',@value=?,@read_only=1;",
            ticket["identity"]["database"],
        )
        cursor.execute("EXECUTE AS USER=" + literal(PRINCIPAL) + ";")
        try:
            guard(cursor, ticket)
            yield connection
        finally:
            try:
                cursor.execute("IF @@TRANCOUNT>0 ROLLBACK TRANSACTION; REVERT;")
            finally:
                cursor.close()


def write_release(shapes, directory):
    import shutil

    directory.mkdir(parents=True, exist_ok=True)
    for filename in SQL_FILES:
        shutil.copyfile(PACKAGE / filename, directory / filename)
    save(directory / "expected-shapes.json", shapes)
    manifest = {
        "release_id": "CBN-foundation-local-v2",
        "scope": "restored_rehearsal_only",
        "shape_version": "cbn-foundation-shape-v1",
        "engine_major": 16,
        "institutional_sql2019_accepted": False,
        "construction": (
            "Validated reference restoration; frozen before separate trial restoration"
        ),
        "expected_shapes_sha256": file_sha(directory / "expected-shapes.json"),
        "tool_files": [{"path": p, "sha256": file_sha(ROOT / p)} for p in TOOL_FILES],
        "legacy_sources": [
            {"path": p, "sha256": file_sha(ROOT / p)} for p in LEGACY_FILES
        ],
        "units": [],
    }
    for i, (unit, filename) in enumerate(zip(UNITS, SQL_FILES, strict=True)):
        before = "prepared" if i == 0 else UNITS[i - 1]
        manifest["units"].append(
            {
                "id": unit,
                "file": filename,
                "sha256": file_sha(PACKAGE / filename),
                "depends_on": list(UNITS[:i]),
                "before_sha256": sha(shapes[before]),
                "after_sha256": sha(shapes[unit]),
            }
        )
    save(directory / "release.json", manifest)
    return manifest


def reference(work):
    """Inspect REF independently and freeze for the separate trial restoration."""
    from tools.cbn_foundation import acquire
    from tools.foundation_contract import inspect_reference, integrity_checks

    state, ticket = load(work / "state.json"), load(work / "reference-ticket.json")
    require(ticket["kind"] == "REF", "reference_target_required")
    context = state["context"]
    with admin(ticket["identity"]["database"], context) as connection:
        require(
            capture(connection) == state["source_signature"],
            "reference_before_core_changed",
        )
    shapes = {}
    unit_records = [
        {"id": unit, "file": filename, "sha256": file_sha(PACKAGE / filename)}
        for unit, filename in zip(UNITS, SQL_FILES, strict=True)
    ]
    construction_hash = sha(
        {"purpose": "reference_construction_only", "units": unit_records}
    )
    with restricted(ticket, context) as connection:
        cursor = connection.cursor()
        shapes["prepared"] = metadata(cursor, managed=True)
        require(
            not shapes["prepared"]["objects"], "reference_must_start_prepared_empty"
        )
        acquire(cursor, "crm.schema.migrate.v1", "Session")
        try:
            for unit in unit_records:
                attempt = str(uuid.uuid4())
                before = sha(metadata(cursor, managed=True))
                if unit["id"] != UNITS[0]:
                    transaction(cursor)
                    append_event(
                        cursor,
                        ticket,
                        construction_hash,
                        unit,
                        attempt,
                        "STARTED",
                        before,
                        release_id="reference-construction",
                    )
                    cursor.execute("COMMIT TRANSACTION;")
                transaction(cursor)
                acquire(cursor, "crm.local.commit", "Transaction")
                guard(cursor, ticket)
                cursor.execute((PACKAGE / unit["file"]).read_text(encoding="utf-8"))
                drain(cursor)
                after = metadata(cursor, managed=True)
                guard(cursor, ticket)
                append_event(
                    cursor,
                    ticket,
                    construction_hash,
                    unit,
                    attempt,
                    "COMMITTED",
                    before,
                    sha(after),
                    release_id="reference-construction",
                )
                cursor.execute("COMMIT TRANSACTION;")
                shapes[unit["id"]] = after
            inspection = inspect_reference(connection, ticket["identity"]["collation"])
            behavior = integrity_checks(connection)
            require(
                metadata(cursor, managed=True) == shapes[UNITS[-1]],
                "reference_shape_after_checks",
            )
            row = cursor.execute(
                "SELECT ConfigurationId,Document,Revision FROM crm_config.Configuration"
            ).fetchone()
            require(
                row[0] == 1
                and row[2] == 1
                and json.loads(row[1])
                == {"stages": [], "tags": [], "inactiveTags": [], "fields": []},
                "reference_seed",
            )
        finally:
            cursor.execute("IF @@TRANCOUNT>0 ROLLBACK TRANSACTION;")
            cursor.execute(
                "EXEC sys.sp_releaseapplock "
                "@Resource=N'crm.schema.migrate.v1',@LockOwner=N'Session';"
            )
            drain(cursor)
            cursor.close()
    with admin(ticket["identity"]["database"], context) as connection:
        require(
            capture(connection) == state["source_signature"],
            "reference_after_core_changed",
        )
        checkdb(connection.cursor(), ticket["identity"]["database"])
    save(work / "reference-shapes.json", shapes)
    save(
        work / "reference-inspection.json",
        {"inspection": inspection, "behavior": behavior},
    )
    manifest = write_release(shapes, work / "release")
    proof = {
        "independent_inspection": inspection,
        "rollback_only_checks": behavior,
        "academic_shape_and_data_unchanged": True,
        "checkdb": True,
        "release_sha256": file_sha(work / "release/release.json"),
        "unit_sql_sha256": {u["id"]: u["sha256"] for u in manifest["units"]},
    }
    save(work / "reference-result.json", proof)
    return proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "reference", "rehearse"))
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    from tools.foundation_rehearsal_checks import exercise

    action = {"prepare": prepare, "reference": reference, "rehearse": exercise}[
        args.command
    ]
    print(json.dumps(action(args.work)), flush=True)


if __name__ == "__main__":
    main()
