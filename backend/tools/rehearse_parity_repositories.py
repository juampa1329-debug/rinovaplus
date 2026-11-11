"""Explicit C12 independent restored-copy preparation; no app startup."""

import argparse
import contextlib
import hashlib
import json
import secrets
import time
import uuid
from pathlib import Path, PureWindowsPath

import pyodbc

from app.parity_channels.catalog import metadata as runtime_metadata
from app.parity_channels.guard import acl
from app.parity_channels.policy import (
    COLUMNS,
    DENIED,
    IMPORTER,
    RIGHTS,
    TARGET,
    VERSION,
    principal,
    require,
)
from app.parity_channels.profile import load as runtime_settings
from app.sql_profile import SqlProfileStore
from app.sql_target import HOST, _quoted
from tools.cbn_foundation import acquire, target_identity
from tools.channels_parity import expected_shapes, guard, history
from tools.channels_parity_contract import assets, quote
from tools.channels_parity_snapshot import NEW_TABLES, OLD_TABLES
from tools.crm_extension_snapshot_v2 import journal_binary
from tools.foundation_snapshot import quote_name, sha
from tools.parity_data import ALLOWED, signature
from tools.parity_data import full_snapshot as snapshot
from tools.parity_mapping import KEYS, import_rows
from tools.rehearse_channels_parity import C5, C9
from tools.rehearse_crm_extension_v2 import load, save
from tools.rehearse_foundation import checkdb, execute_results, literal, private_profile

SOURCE = "CBN_C11_TRIAL_20261025_d30e2cb2"


@contextlib.contextmanager
def admin(database, context, readonly=False):
    require(
        database in {"master", "HORARIOSSIIE", C5, C9, SOURCE}
        or TARGET.fullmatch(database),
        "C12_admin_target",
    )
    cfg = private_profile()["connection"]
    require(
        HOST.fullmatch(cfg["server"])
        and cfg["certificate_hostname"] == "localhost"
        and type(cfg["port"]) is int
        and 1 <= cfg["port"] <= 65535,
        "C12_TLS_endpoint",
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
        + ";APP=CBN C12 rehearsal;"
    )
    c = pyodbc.connect(text, timeout=5, autocommit=True, readonly=readonly)
    try:
        c.timeout = 120
        actual = target_identity(c.cursor())
        require(
            actual["database"] == database
            and [actual[k] for k in ("machine", "server", "instance", "engine")]
            == [context["identity"][i] for i in (1, 2, 3, 4)],
            "C12_server_identity",
        )
        require(
            c.cursor().execute("SELECT IS_SRVROLEMEMBER('sysadmin')").fetchval() == 1,
            "C12_admin_visibility",
        )
        yield c
    finally:
        with contextlib.suppress(pyodbc.Error):
            c.close()


def sources(context):
    result = {}
    for name in ("HORARIOSSIIE", C5, C9, SOURCE):
        with admin(name, context, True) as c:
            result[name] = snapshot(c)
    return result


def restore(cursor, backup, context, kind):
    require(kind in {"TRIAL", "FAULT"}, "C12_restore_kind")
    name = "CBN_C12_" + kind + "_20261025_" + uuid.uuid4().hex[:8]
    require(
        TARGET.fullmatch(name)
        and not cursor.execute(
            "SELECT 1 FROM sys.databases WHERE name=?", name
        ).fetchone(),
        "C12_restore_collision",
    )
    files = execute_results(cursor, "RESTORE FILELISTONLY FROM DISK=" + literal(backup))
    require(
        len(files) == 2 and {f["Type"] for f in files} == {"D", "L"},
        "C12_backup_layout",
    )
    moves = []
    for f in files:
        log = f["Type"] == "L"
        path = str(
            PureWindowsPath(context["paths"][2 if log else 1])
            / (name + ("_log.ldf" if log else ".mdf"))
        )
        require(
            cursor.execute(
                "SELECT file_exists FROM sys.dm_os_file_exists(?)", path
            ).fetchval()
            == 0,
            "C12_file_collision",
        )
        moves.append("MOVE " + literal(f["LogicalName"]) + " TO " + literal(path))
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
    require(not (work / "state.json").exists(), "C12_work_exists")
    parent = load(Path("/tmp/cbn-c11-v1/state.json"))
    context = parent["context"]
    ticket = load(Path("/tmp/cbn-c11-v1") / (SOURCE + ".json"))
    release, manifest = assets()
    require(ticket["release_sha256"] == manifest, "C12_source_release")
    with admin(SOURCE, context, True) as c:
        cursor = c.cursor()
        require(guard(cursor, ticket, expected_shapes()) == 5, "C12_source_shape")
        _, complete, pending = history(cursor, ticket, release, manifest)
        require(complete == 5 and not pending, "C12_source_history")
        require(
            all(
                cursor.execute("SELECT COUNT(*) FROM " + t).fetchval()
                == int(t == "crm_channels2.Context")
                for t in NEW_TABLES
            ),
            "C12_source_new_tables_not_empty",
        )
    before = sources(context)
    backup = str(
        PureWindowsPath(context["paths"][0])
        / ("CBN_C12_20261025_" + uuid.uuid4().hex[:8] + ".bak")
    )
    with admin(SOURCE, context, True) as c:
        cursor = c.cursor()
        acquire(cursor, "crm.schema.migrate.v1", "Session")
        acquire(cursor, "crm.local.commit", "Session")
        try:
            require(
                guard(cursor, ticket, expected_shapes()) == 5, "C12_locked_source_shape"
            )
            _, complete, pending = history(cursor, ticket, release, manifest)
            require(complete == 5 and not pending, "C12_locked_source_history")
            require(snapshot(c) == before[SOURCE], "C12_source_changed")
            with admin("master", context) as master:
                cursor = master.cursor()
                require(
                    cursor.execute(
                        "SELECT file_exists FROM sys.dm_os_file_exists(?)", backup
                    ).fetchval()
                    == 0,
                    "C12_backup_collision",
                )
                execute_results(
                    cursor,
                    "BACKUP DATABASE "
                    + quote(SOURCE)
                    + " TO DISK="
                    + literal(backup)
                    + " WITH COPY_ONLY,CHECKSUM;",
                )
                execute_results(
                    cursor,
                    "RESTORE VERIFYONLY FROM DISK="
                    + literal(backup)
                    + " WITH CHECKSUM;",
                )
            cursor = c.cursor()
            require(
                guard(cursor, ticket, expected_shapes()) == 5, "C12_after_backup_shape"
            )
            _, complete, pending = history(cursor, ticket, release, manifest)
            require(
                complete == 5 and not pending and snapshot(c) == before[SOURCE],
                "C12_after_backup_source",
            )
        finally:
            c.cursor().execute(
                (
                    "EXEC sys.sp_releaseapplock @Resource=N'crm.local.c"
                    "ommit',@LockOwner=N'Session'; EXEC "
                    "sys.sp_releaseapplock @Resource=N'crm.schema.migra"
                    "te.v1',@LockOwner=N'Session';"
                )
            )
    with admin("master", context) as c:
        name = restore(c.cursor(), backup, context, "TRIAL")
    with admin(name, context, True) as c:
        require(snapshot(c) == before[SOURCE], "C12_restore_exact")
    require(sources(context) == before, "C12_sources_preserved")
    save(
        work / "state.json",
        {
            "context": context,
            "backup": backup,
            "database": name,
            "source": before[SOURCE],
            "sources": before,
            "source_ticket": ticket,
        },
    )
    print(
        json.dumps(
            {
                "phase": "restored",
                "database": name,
                "backup_verified": True,
                "CHECKDB": True,
                "sources_unchanged": True,
            }
        ),
        flush=True,
    )


def survey(work):
    state = load(work / "state.json")
    with admin(state["database"], state["context"], True) as c:
        out = []
        for channel, configuration in (
            c.cursor()
            .execute("SELECT Channel,Configuration FROM crm_channels.Account")
            .fetchall()
        ):
            data = json.loads(configuration)
            out.append(
                {
                    "channel": channel,
                    "nonempty_fields": sorted(k for k, v in data.items() if v),
                    "has_app_id": bool(data.get("appId")),
                    "has_callback": bool(data.get("callbackUrl")),
                }
            )
        creds = [
            {"channel": r[0], "kind": r[1]}
            for r in c.cursor()
            .execute("SELECT Channel,Kind FROM crm_channels.Credential")
            .fetchall()
        ]
    save(work / "survey.json", {"accounts": out, "credential_kinds": creds})
    print(
        json.dumps(
            {"phase": "mapping_survey", "accounts": out, "credential_kinds": creds}
        ),
        flush=True,
    )


IMPORT_TABLES = (
    "Application",
    "Integration",
    "Audit",
    "WebhookEndpoint",
    "SecretVersion",
    "ExternalIdentity",
    "ExternalMessage",
    "SocialComment",
    "WebhookReceipt",
    "ProviderOperation",
    "SendJob",
    "LegacyBinding",
)


def importer(cursor):
    require(
        not cursor.execute(
            "SELECT 1 FROM sys.database_principals WHERE name=?", IMPORTER
        ).fetchone(),
        "C12_importer_exists",
    )
    q = quote_name(IMPORTER)
    cursor.execute(
        "CREATE USER " + q + " WITHOUT LOGIN;GRANT VIEW DEFINITION TO " + q + ";"
    )
    for permission in DENIED:
        cursor.execute("DENY " + permission + " ON SCHEMA::dbo TO " + q)
    for table in KEYS:
        cursor.execute(
            "GRANT SELECT ON OBJECT::crm_channels." + quote_name(table) + " TO " + q
        )
    for table in ("Context",):
        cursor.execute("GRANT SELECT ON OBJECT::crm_channels2." + table + " TO " + q)
    for table in IMPORT_TABLES:
        cursor.execute(
            "GRANT SELECT,INSERT ON OBJECT::crm_channels2." + table + " TO " + q
        )
    for table in ("Contact", "Conversation", "Message"):
        cursor.execute("GRANT SELECT ON OBJECT::crm." + table + " TO " + q)
    cursor.execute("GRANT SELECT ON OBJECT::crm_config.Configuration TO " + q)


def run_import(connection, work, fail_after=None):
    cursor = connection.cursor()
    cursor.execute(
        (
            "SET XACT_ABORT ON;SET TRANSACTION ISOLATION LEVEL "
            "SERIALIZABLE;BEGIN TRANSACTION;"
        )
    )
    impersonating = False
    try:
        acquire(cursor, "crm.schema.migrate.v1", "Transaction")
        acquire(cursor, "crm.local.commit", "Transaction")
        cursor.execute("EXECUTE AS USER=" + literal(IMPORTER) + ";")
        impersonating = True
        require(
            cursor.execute(
                "SELECT HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','CONTROL')"
            ).fetchval()
            == 0,
            "C12_importer_control",
        )
        result = import_rows(cursor, work, fail_after=fail_after)
        cursor.execute("REVERT;")
        impersonating = False
        cursor.execute("COMMIT;")
        return result
    except BaseException:
        if impersonating:
            cursor.execute("REVERT;")
        cursor.execute("IF @@TRANCOUNT>0 ROLLBACK;")
        raise


def prepare(work):
    state = load(work / "state.json")
    name = state["database"]
    directory = work / "profile"
    require(not directory.exists(), "C12_profile_already_exists")
    with admin(name, state["context"]) as c:
        require(snapshot(c) == state["source"], "C12_restore_changed_before_prepare")
        cursor = c.cursor()
        base_shape = runtime_metadata(cursor)
        old = signature(cursor, OLD_TABLES)
        cursor.execute("BEGIN TRANSACTION;")
        try:
            importer(cursor)
            cursor.execute("COMMIT;")
        except BaseException:
            cursor.execute("IF @@TRANCOUNT>0 ROLLBACK;")
            raise
        # Atomicity is proved before the successful import on this isolated copy.
        before = signature(cursor, sorted(ALLOWED))
        rejected = 0
        for point in ("accounts", "complete"):
            try:
                run_import(c, work, point)
            except ValueError as error:
                require(
                    str(error).startswith("C12_injected_"),
                    "C12_unexpected_import_failure",
                )
                rejected += 1
            else:
                raise ValueError("C12_fault_not_raised")
            require(
                signature(c.cursor(), sorted(ALLOWED)) == before,
                "C12_import_not_atomic",
            )
        result = run_import(c, work)
        repeat = run_import(c, work)
        require(repeat["status"] == "noop", "C12_import_replay")
        require(signature(c.cursor(), OLD_TABLES) == old, "C12_legacy_data_changed")
    user = principal(name)
    password = "C12!" + secrets.token_urlsafe(48)
    profile = {
        "revision": 1,
        "connection": {
            **private_profile()["connection"],
            "database": name,
            "username": user,
            "password": password,
        },
        "review": {
            "ticket_sha256": "",
            "api_token": secrets.token_urlsafe(48),
            "operation_key": secrets.token_hex(32),
        },
    }
    SqlProfileStore(directory / "runtime").save(profile)
    with admin("master", state["context"]) as c:
        cursor = c.cursor()
        require(
            not cursor.execute(
                "SELECT 1 FROM sys.server_principals WHERE name=?", user
            ).fetchone(),
            "C12_login_collision",
        )
        cursor.execute(
            "CREATE LOGIN "
            + quote_name(user)
            + " WITH PASSWORD="
            + literal(password)
            + ",DEFAULT_DATABASE="
            + quote_name(name)
            + ",CHECK_POLICY=ON,CHECK_EXPIRATION=OFF;"
        )
        sid = cursor.execute(
            "SELECT CONVERT(varchar(170),SUSER_SID(?),2)", user
        ).fetchval()
        protected = [
            r[0]
            for r in cursor.execute(
                (
                    "SELECT name FROM sys.server_principals WHERE type "
                    "IN('S','U','G') AND name<>? ORDER BY name"
                ),
                user,
            ).fetchall()
        ]
    with admin(name, state["context"]) as c:
        cursor = c.cursor()
        cursor.execute("BEGIN TRANSACTION;")
        try:
            q = quote_name(user)
            cursor.execute(
                "CREATE USER "
                + q
                + " FOR LOGIN "
                + q
                + " WITH DEFAULT_SCHEMA=crm_channels2;GRANT CONNECT,VIEW DEFINITION TO "
                + q
                + ";"
            )
            for permission in DENIED:
                cursor.execute("DENY " + permission + " ON SCHEMA::dbo TO " + q)
            for table, rights in RIGHTS.items():
                cursor.execute(
                    "GRANT " + ",".join(rights) + " ON OBJECT::" + table + " TO " + q
                )
            for table, columns in COLUMNS.items():
                cursor.execute(
                    "GRANT SELECT ON OBJECT::"
                    + table
                    + " ("
                    + ",".join(map(quote_name, columns))
                    + ") TO "
                    + q
                )
            shape = runtime_metadata(cursor)
            acl(cursor, shape, user, sid)
            projected = {
                k: [
                    r
                    for r in v
                    if r.get("grantee") not in {user, IMPORTER}
                    and r.get("member_name") not in {user, IMPORTER}
                    and not (k == "principals" and r.get("name") in {user, IMPORTER})
                ]
                if k != "version"
                else v
                for k, v in shape.items()
            }
            require(
                sha(projected) == sha(base_shape), "C12_preexisting_catalog_changed"
            )
            require(
                signature(cursor, OLD_TABLES) == old, "C12_preexisting_rows_changed"
            )
            ticket = {
                "scope": "SQL-C12-repositories-rehearsal-only",
                "version": VERSION,
                "identity": target_identity(cursor),
                "login_sid": sid,
                "catalog_sha256": sha(shape),
                "journal_sha256": sha(journal_binary(cursor)),
                "context": [
                    list(r)
                    for r in cursor.execute(
                        (
                            "SELECT ContextId,CONVERT(varchar(36),InstitutionId"
                            "),ContractVersion FROM crm_channels2.Context"
                        )
                    ).fetchall()
                ],
                "tables": sorted(
                    r["schema_name"] + "." + r["name"]
                    for r in shape["catalog"]
                    if r["type"].strip() == "U"
                ),
                "protected_logins": protected,
                "expires_at": int(time.time()) + 7 * 86400,
                "api_token_sha256": hashlib.sha256(
                    profile["review"]["api_token"].encode()
                ).hexdigest(),
            }
            cursor.execute("COMMIT;")
        except BaseException:
            cursor.execute("IF @@TRANCOUNT>0 ROLLBACK;")
            raise
    save(directory / "runtime-ticket.json", ticket)
    profile["review"]["ticket_sha256"] = hashlib.sha256(
        (directory / "runtime-ticket.json").read_bytes()
    ).hexdigest()
    SqlProfileStore(directory / "runtime").save(profile)
    state.update(
        profile_directory=str(directory),
        old_data=old,
        preparation={"mapping": result, "replay": repeat, "rollback_faults": rejected},
    )
    save(work / "state.json", state)
    from app.parity_channels.guard import transaction

    with transaction(runtime_settings(directory)):
        pass
    require(sources(state["context"]) == state["sources"], "C12_sources_changed")
    print(
        json.dumps(
            {
                "phase": "prepared",
                "database": name,
                **state["preparation"],
                "own_runtime_guard": True,
                "sources_unchanged": True,
            }
        ),
        flush=True,
    )


def fresh(work):
    """Keep the failed copy intact, restore another exact trial from the backup."""
    state = load(work / "state.json")
    require(not (work / "profile").exists(), "C12_no_automatic_profile_replacement")
    with admin(state["database"], state["context"], True) as c:
        require(
            c.cursor()
            .execute("SELECT COUNT(*) FROM crm_channels2.LegacyBinding")
            .fetchval()
            == 0,
            "C12_completed_copy_requires_explicit_new_work",
        )
    previous = state["database"]
    with admin("master", state["context"]) as c:
        name = restore(c.cursor(), state["backup"], state["context"], "TRIAL")
    with admin(name, state["context"], True) as c:
        require(snapshot(c) == state["source"], "C12_fresh_exact_restore")
    state["database"] = name
    state.setdefault("preserved_attempts", []).append(previous)
    save(work / "state.json", state)
    print(
        json.dumps(
            {
                "phase": "fresh_exact_restoration",
                "database": name,
                "previous_preserved": previous,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("start", "survey", "prepare", "fresh"))
    p.add_argument("--work", type=Path, required=True)
    args = p.parse_args()
    try:
        {"start": start, "survey": survey, "prepare": prepare, "fresh": fresh}[
            args.action
        ](args.work)
    except pyodbc.Error as error:
        import traceback

        frames = [
            (Path(f.filename).name, f.name, f.lineno)
            for f in traceback.extract_tb(error.__traceback__)
        ]
        raise SystemExit(
            "C12 SQLSTATE " + str(error.args[0]) + " frames=" + json.dumps(frames)
        ) from None
