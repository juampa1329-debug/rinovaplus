"""Explicit C11 backup/restoration/reference/rehearsal, never app startup."""

import argparse
import contextlib
import json
import uuid
from pathlib import Path, PureWindowsPath

import pyodbc

from app.sql_target import HOST, _quoted
from tools.cbn_foundation import acquire, drain, target_identity
from tools.channels_parity import guard, run
from tools.channels_parity_contract import (
    ACTOR,
    MODEL_SHA,
    PACKAGE,
    RELEASE,
    ROOT,
    SCHEMA,
    TARGET,
    VERSION,
    assets,
    compile_units,
    digest,
    model,
    qualified,
    quote,
    require,
)
from tools.channels_parity_snapshot import (
    DENIES,
    GRANTS,
    NEW_TABLES,
    canonical,
    effective_acl,
    journal_binary,
    metadata,
    preserved_data,
    protected,
    sha,
    verify_partition,
)
from tools.rehearse_crm_extension_v2 import load, save
from tools.rehearse_foundation import checkdb, execute_results, literal, private_profile

pyodbc.pooling = False
C5 = "CBN_C3_TRIAL_20261024_ac8505b8"
C9 = "CBN_C9_TRIAL_20261025_23ac78d3"


@contextlib.contextmanager
def admin(database, context, *, readonly=False):
    require(
        database in {"master", "HORARIOSSIIE", C5, C9}
        or bool(TARGET.fullmatch(database)),
        "C11_admin_destination",
    )
    cfg = private_profile()["connection"]
    require(
        cfg["certificate_hostname"] == "localhost"
        and HOST.fullmatch(cfg["server"])
        and isinstance(cfg["port"], int)
        and 1 <= cfg["port"] <= 65535,
        "C11_TLS_hostname_and_endpoint",
    )
    text = (
        "DRIVER={ODBC Driver 18 for SQL Server};SERVER=tcp:"
        + cfg["server"]
        + ","
        + str(cfg["port"])
        + ";DATABASE="
        + _quoted(database)
        + ";Encrypt=Yes;TrustServerCertificate=No;HostnameInCertificate=localhost;UID="
        + _quoted(cfg["username"])
        + ";PWD="
        + _quoted(cfg["password"])
        + ";APP=CBN SQL-C11 restored-only;"
    )
    connection = pyodbc.connect(text, timeout=5, autocommit=True, readonly=readonly)
    try:
        connection.timeout = 180
        identity = target_identity(connection.cursor())
        require(
            identity["database"] == database
            and [identity[k] for k in ("machine", "server", "instance", "engine")]
            == [context["identity"][i] for i in (1, 2, 3, 4)],
            "C11_server_identity",
        )
        require(
            connection.cursor()
            .execute("SELECT IS_SRVROLEMEMBER('sysadmin')")
            .fetchval()
            == 1,
            "C11_administrative_visibility",
        )
        require(
            not connection.cursor()
            .execute("SELECT 1 FROM sys.server_triggers")
            .fetchone(),
            "C11_server_trigger",
        )
        yield connection
    finally:
        connection.close()


def snapshot(connection, source=False):
    cursor = connection.cursor()
    cursor.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE; BEGIN TRANSACTION;")
    try:
        catalog = metadata(cursor)
        tables = [
            r["schema_name"] + "." + r["name"]
            for r in catalog["catalog"]
            if r["type"].strip() == "U"
        ]
        from tools.crm_extension_snapshot_v2 import data_signature

        rows = data_signature(cursor, sorted(tables))
        value = {"catalog_sha256": sha(catalog), "data": rows}
        if not source:
            value.update(
                preservation=preserved_data(cursor),
                journal_rows=len(journal_binary(cursor)),
            )
        cursor.execute("COMMIT; SET TRANSACTION ISOLATION LEVEL READ COMMITTED;")
        return value
    except BaseException:
        cursor.execute("IF @@TRANCOUNT>0 ROLLBACK;")
        raise
    finally:
        cursor.close()


def protected_snapshots(context):
    result = {}
    for name in ("HORARIOSSIIE", C5, C9):
        with admin(name, context, readonly=True) as connection:
            result[name] = snapshot(connection, source=name != C9)
    return result


def restore(cursor, backup, context, kind):
    require(kind in {"REF", "TRIAL", "FAULT", "RECOVERY"}, "C11_restore_kind")
    name = "CBN_C11_" + kind + "_20261025_" + uuid.uuid4().hex[:8]
    require(bool(TARGET.fullmatch(name)), "C11_restore_name")
    require(
        not cursor.execute("SELECT 1 FROM sys.databases WHERE name=?", name).fetchone(),
        "C11_database_collision",
    )
    files = execute_results(cursor, "RESTORE FILELISTONLY FROM DISK=" + literal(backup))
    require(
        len(files) == 2 and {f["Type"] for f in files} == {"D", "L"},
        "C11_backup_layout",
    )
    moves = []
    for row in files:
        log = row["Type"] == "L"
        path = str(
            PureWindowsPath(context["paths"][2 if log else 1])
            / (name + ("_log.ldf" if log else ".mdf"))
        )
        require(
            cursor.execute(
                "SELECT file_exists FROM sys.dm_os_file_exists(?)", path
            ).fetchval()
            == 0,
            "C11_restore_file_collision",
        )
        moves.append("MOVE " + literal(row["LogicalName"]) + " TO " + literal(path))
    execute_results(
        cursor,
        "RESTORE DATABASE "
        + quote(name)
        + " FROM DISK="
        + literal(backup)
        + " WITH "
        + ",".join(moves)
        + ",RECOVERY,CHECKSUM;",
    )
    checkdb(cursor, name)
    return name


def start(work):
    require(not (work / "state.json").exists(), "C11_work_already_exists")
    parent = load(Path("/tmp/cbn-c9/state.json"))
    context = parent["context"]
    require(parent["database"] == C9, "C11_source_C9")
    before = protected_snapshots(context)
    require(
        before[C9]["journal_rows"] == 7,
        "C11_C9_not_accepted_source",
    )
    backup = str(
        PureWindowsPath(context["paths"][0])
        / ("CBN_C11_20261025_" + uuid.uuid4().hex[:8] + ".bak")
    )
    with admin(C9, context, readonly=True) as source:
        c = source.cursor()
        acquire(c, "crm.schema.migrate.v1", "Session")
        acquire(c, "crm.local.commit", "Session")
        try:
            from app.channels_catalog import metadata as c9_metadata

            require(
                sha(c9_metadata(c)) == parent["ticket"]["catalog_sha256"],
                "C11_C9_runtime_catalog",
            )
            require(
                target_identity(c) == parent["ticket"]["identity"],
                "C11_C9_ticket_identity",
            )
            require(
                sha(journal_binary(c)) == parent["ticket"]["journal_sha256"],
                "C11_C9_ticket_journal",
            )
            require(snapshot(source) == before[C9], "C11_source_changed")
            with admin("master", context) as master:
                c = master.cursor()
                require(
                    c.execute(
                        "SELECT file_exists FROM sys.dm_os_file_exists(?)", backup
                    ).fetchval()
                    == 0,
                    "C11_backup_collision",
                )
                execute_results(
                    c,
                    "BACKUP DATABASE "
                    + quote(C9)
                    + " TO DISK="
                    + literal(backup)
                    + " WITH COPY_ONLY,CHECKSUM;",
                )
                execute_results(
                    c,
                    "RESTORE VERIFYONLY FROM DISK="
                    + literal(backup)
                    + " WITH CHECKSUM;",
                )
        finally:
            source.cursor().execute(
                (
                    "EXEC sys.sp_releaseapplock @Resource=N'crm.local.commit',@Lo"
                    "ckOwner=N'Session'; EXEC sys.sp_releaseapplock @Resource=N'c"
                    "rm.schema.migrate.v1',@LockOwner=N'Session';"
                )
            )
    require(protected_snapshots(context) == before, "C11_preserved_sources_changed")
    state = {
        "context": context,
        "backup": backup,
        "sources": before,
        "institution_id": str(uuid.uuid4()),
        "restorations": [],
    }
    save(work / "state.json", state)
    print(
        json.dumps(
            {
                "phase": "backup",
                "copy_only_checksum_verifyonly": True,
                "protected_databases": 3,
            }
        ),
        flush=True,
    )


def prepare(connection, state):
    c = connection.cursor()
    require(snapshot(connection) == state["sources"][C9], "C11_restore_not_identical")
    c.execute("BEGIN TRANSACTION;")
    try:
        require(
            c.execute("SELECT SCHEMA_ID(?)", SCHEMA).fetchval() is None,
            "C11_schema_collision",
        )
        c.execute("CREATE SCHEMA " + quote(SCHEMA) + " AUTHORIZATION dbo;")
        c.execute(
            "CREATE USER " + quote(ACTOR) + " WITHOUT LOGIN WITH DEFAULT_SCHEMA=dbo;"
        )
        for class_, target, permission in sorted(GRANTS):
            scope = (
                ""
                if class_ == "DATABASE"
                else " ON SCHEMA::" + quote(target)
                if class_ == "SCHEMA"
                else " ON OBJECT::" + qualified(target)
            )
            c.execute("GRANT " + permission + scope + " TO " + quote(ACTOR) + ";")
        for _, target, permission in sorted(DENIES):
            c.execute(
                "DENY "
                + permission
                + " ON SCHEMA::"
                + quote(target)
                + " TO "
                + quote(ACTOR)
                + ";"
            )
        raw = metadata(c)
        require(
            sha(protected(raw)) == state["sources"][C9]["catalog_sha256"],
            "C11_preparation_changed_legacy",
        )
        sid = next(p["sid"] for p in raw["principals"] if p["name"] == ACTOR)
        canonical(raw, sid)
        effective_acl(c)
        require(
            preserved_data(c) == state["sources"][C9]["preservation"],
            "C11_preparation_changed_data",
        )
        c.execute("COMMIT;")
        return {
            "scope": "SQL-C11-restored-schema-only",
            "identity": target_identity(c),
            "actor_sid": sid,
            "institution_id": state["institution_id"],
            "protected_catalog_sha256": state["sources"][C9]["catalog_sha256"],
            "preservation": state["sources"][C9]["preservation"],
            "evidence_ref": "SQL-C11-local-physical-schema",
            "approval_ref": "owner-SQL-C11-20261025",
            "backup_ref": PureWindowsPath(state["backup"]).name,
        }
    except BaseException:
        c.execute("IF @@TRANCOUNT>0 ROLLBACK;")
        raise


def new_copy(work, kind):
    state = load(work / "state.json")
    with admin("master", state["context"]) as connection:
        name = restore(connection.cursor(), state["backup"], state["context"], kind)
    state["restorations"].append({"kind": kind, "database": name})
    save(work / "state.json", state)
    with admin(name, state["context"]) as connection:
        ticket = prepare(connection, state)
    save(work / (name + ".json"), ticket)
    return name, ticket, state


def reference(work):
    require(not (PACKAGE / "release.json").exists(), "C11_release_already_sealed")
    name, ticket, state = new_copy(work, "REF")
    shapes = []
    with admin(name, state["context"]) as connection:
        c = connection.cursor()
        shapes.append(sha(canonical(metadata(c), ticket["actor_sid"])))
        for number, (unit, sql) in enumerate(compile_units().items(), 1):
            require(
                preserved_data(c) == ticket["preservation"],
                "C11_reference_preservation",
            )
            c.execute("BEGIN TRANSACTION;")
            try:
                c.execute(
                    "EXEC sys.sp_set_session_context @key=N'CBN_C11_TARGET',@value=?",
                    name,
                )
                c.execute("EXECUTE AS USER=N'" + ACTOR + "';")
                try:
                    c.execute(sql)
                    drain(c)
                finally:
                    c.execute("REVERT;")
                if number == 1:
                    c.execute(
                        (
                            "INSERT crm_channels2.Context(ContextId,"
                            "InstitutionId,ContractVersion,CreatedAt) "
                            "VALUES(1,?,?,SYSUTCDATETIME())"
                        ),
                        state["institution_id"],
                        model()["version"],
                    )
                raw = metadata(c)
                verify_partition(raw, number)
                from tools.check_channels_parity import physical_shape

                physical_shape(c, number)
                require(
                    sha(protected(raw)) == ticket["protected_catalog_sha256"],
                    "C11_reference_catalog_preservation",
                )
                shapes.append(sha(canonical(raw, ticket["actor_sid"])))
                c.execute("COMMIT;")
                print(
                    json.dumps({"phase": "reference", "unit": unit, "prefix": number}),
                    flush=True,
                )
            except BaseException:
                c.execute("IF @@TRANCOUNT>0 ROLLBACK;")
                raise
        require(preserved_data(c) == ticket["preservation"], "C11_reference_final_data")
        require(len(journal_binary(c)) == 7, "C11_reference_journal")
    save(work / "reference-shapes.json", shapes)
    save(
        work / "reference-result.json",
        {
            "database": name,
            "tables": len(NEW_TABLES),
            "foreign_keys": len(model()["foreign_keys"]),
            "old_catalog_and_data_preserved": True,
        },
    )


def seal(work):
    require(not (PACKAGE / "release.json").exists(), "C11_sealed")
    shapes = load(work / "reference-shapes.json")
    require(len(shapes) == len(set(shapes)) == 6, "C11_reference_shapes")
    save(PACKAGE / "expected-shapes.json", shapes)
    files = [
        "backend/migrations/cbn_channels_parity_v1/" + n
        for n in (
            *[u + ".sql" for u in compile_units()],
            "expected-shapes.json",
            "constraint-coverage.json",
            "reviewed-checks.json",
        )
    ]
    files += [
        "backend/tools/channels_parity_contract.py",
        "backend/tools/channels_parity_snapshot.py",
        "backend/tools/channels_parity.py",
        "docs/adaptation/sql/channels-parity-contract.json",
    ]
    units = [
        {
            "id": u,
            "sha256": digest(PACKAGE / (u + ".sql")),
            "before_sha256": shapes[i],
            "after_sha256": shapes[i + 1],
        }
        for i, u in enumerate(compile_units())
    ]
    release = {
        "release_id": RELEASE,
        "tool_version": "SQL-C11-v1",
        "shape_version": VERSION,
        "contract_sha256": MODEL_SHA,
        "institutional_sql2019_accepted": False,
        "engine_profile": "local16/160_exploration_only",
        "scope": "new_restoration_schema_only",
        "reference_result_sha256": digest(work / "reference-result.json"),
        "units": units,
        "files": [{"path": p, "sha256": digest(ROOT / p)} for p in files],
    }
    save(PACKAGE / "release.json", release)
    print(json.dumps({"phase": "sealed", "release_sha256": assets()[1]}), flush=True)


def trial(work):
    name, ticket, state = new_copy(work, "TRIAL")
    ticket["release_sha256"] = assets()[1]
    save(work / (name + ".json"), ticket)
    outcomes = []
    with admin(name, state["context"]) as connection:
        for unit in assets()[0]["units"]:
            outcome = run(
                connection, ticket, work / (name + ".jsonl"), unit_id=unit["id"]
            )
            outcomes.append(outcome)
            print(
                json.dumps({"phase": "trial", "unit": unit["id"], "result": outcome}),
                flush=True,
            )
        require(run(connection, ticket, work / (name + ".jsonl")) == "NOOP", "C11_NOOP")
        require(
            guard(connection.cursor(), ticket, load(PACKAGE / "expected-shapes.json"))
            == 5,
            "C11_trial_complete",
        )
        require(len(journal_binary(connection.cursor())) == 17, "C11_trial_journal")
    require(
        protected_snapshots(state["context"]) == state["sources"],
        "C11_sources_changed_after_trial",
    )
    save(
        work / "trial-result.json",
        {
            "database": name,
            "units": outcomes,
            "NOOP": True,
            "journal_rows": 17,
            "legacy_journal_rows_unchanged": 7,
            "protected_sources_unchanged": True,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "reference", "seal", "trial"))
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    try:
        {"start": start, "reference": reference, "seal": seal, "trial": trial}[
            args.action
        ](args.work)
    except pyodbc.Error as error:
        # Full diagnostics remain private when explicitly captured by operator.
        raise SystemExit("C11 SQL error; SQLSTATE " + str(error.args[0])) from None
