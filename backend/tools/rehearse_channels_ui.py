"""Explicit C9 backup and UI-only principal preparation on a new restored copy."""

import argparse
import contextlib
import hashlib
import json
import secrets
import uuid
from pathlib import Path, PureWindowsPath

import pyodbc

from app import channels_ui_contract as contract
from app.channels_catalog import metadata
from app.channels_ui_profile import load_settings
from app.sql_profile import SqlProfileStore
from app.sql_target import HOST, _quoted, connection_string
from tools.cbn_foundation import target_identity
from tools.crm_extension_snapshot_v2 import (
    PARTITION,
    data_signature,
    journal_binary,
    preservation,
    quote_name,
    require,
    sha,
)
from tools.rehearse_channels import admin as source_admin
from tools.rehearse_channels import capture, load, project, save
from tools.rehearse_foundation import checkdb, execute_results, literal, private_profile
from tools.rehearse_foundation_ui import signatures

pyodbc.pooling = False


@contextlib.contextmanager
def admin(database, context, *, readonly=False):
    require(
        database == "master" or contract.TARGET.fullmatch(database), "C9_admin_target"
    )
    c = private_profile()["connection"]
    require(
        HOST.fullmatch(c["server"]) and c["certificate_hostname"] == "localhost",
        "C9_tls",
    )
    text = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER=tcp:{c['server']},{c['port']};DATABASE={_quoted(database)};"
        "Encrypt=Yes;TrustServerCertificate=No;HostnameInCertificate=localhost;"
        f"UID={_quoted(c['username'])};PWD={_quoted(c['password'])};"
        "APP=CBN C9 rehearsal;"
    )
    connection = pyodbc.connect(text, timeout=5, autocommit=True, readonly=readonly)
    try:
        connection.timeout = 120
        identity = target_identity(connection.cursor())
        require(
            [identity[k] for k in ("machine", "server", "instance", "engine")]
            == [context["identity"][i] for i in (1, 2, 3, 4)],
            "C9_admin_identity",
        )
        yield connection
    finally:
        connection.close()


def snapshot(connection):
    result = capture(connection)
    result["channels"] = data_signature(connection.cursor(), PARTITION["extension"])
    return result


def restore(cursor, backup, context, name):
    require(contract.TARGET.fullmatch(name), "C9_restore_target")
    require(
        not cursor.execute("SELECT 1 FROM sys.databases WHERE name=?", name).fetchone(),
        "C9_collision",
    )
    files = execute_results(cursor, "RESTORE FILELISTONLY FROM DISK=" + literal(backup))
    require(
        len(files) == 2 and {f["Type"] for f in files} == {"D", "L"}, "C9_backup_files"
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
            "C9_file_collision",
        )
        moves.append("MOVE " + literal(row["LogicalName"]) + " TO " + literal(path))
    execute_results(
        cursor,
        "RESTORE DATABASE "
        + quote_name(name)
        + " FROM DISK="
        + literal(backup)
        + " WITH "
        + ",".join(moves)
        + ",RECOVERY,CHECKSUM;",
    )
    checkdb(cursor, name)


def start(work, source_work):
    require(not (work / "state.json").exists(), "C9_already_started")
    old = load(source_work / "state.json")
    context = old["context"]
    baseline = signatures(context, Path(old["runtime_directory"]))
    require(baseline == old["c5_signatures"], "C9_C5_changed")
    name = "CBN_C9_TRIAL_20261025_" + uuid.uuid4().hex[:8]
    backup = str(PureWindowsPath(context["paths"][0]) / (name + ".bak"))
    with source_admin(old["database"], context, readonly=True) as connection:
        before = snapshot(connection)
        require(before["journal_rows"] == 7, "C9_source_journal")
        require(
            sha(metadata(connection.cursor())) == old["ticket"]["catalog_sha256"],
            "C9_source_not_accepted_catalog",
        )
        require(
            before["journal_sha256"] == old["ticket"]["journal_sha256"],
            "C9_source_not_accepted_journal",
        )
        with admin("master", context) as master:
            cursor = master.cursor()
            require(
                cursor.execute(
                    "SELECT file_exists FROM sys.dm_os_file_exists(?)", backup
                ).fetchval()
                == 0,
                "C9_backup_collision",
            )
            execute_results(
                cursor,
                "BACKUP DATABASE "
                + quote_name(old["database"])
                + " TO DISK="
                + literal(backup)
                + " WITH COPY_ONLY,CHECKSUM;",
            )
            execute_results(
                cursor,
                "RESTORE VERIFYONLY FROM DISK=" + literal(backup) + " WITH CHECKSUM;",
            )
        require(snapshot(connection) == before, "C9_source_changed_during_backup")
    state = {
        "context": context,
        "database": name,
        "source_database": old["database"],
        "source_work": str(source_work),
        "source": before,
        "backup": backup,
        "runtime_directory": old["runtime_directory"],
        "c5_signatures": baseline,
    }
    save(work / "state.json", state)
    with admin("master", context) as connection:
        restore(connection.cursor(), backup, context, name)
    with admin(name, context, readonly=True) as connection:
        require(snapshot(connection) == before, "C9_restore_mismatch")
    print(
        json.dumps(
            {
                "phase": "restored",
                "database": name,
                "checksum": True,
                "checkdb": True,
                "source_unchanged": True,
            }
        ),
        flush=True,
    )


def prepare(work):
    state = load(work / "state.json")
    directory = work / "profile"
    directory.mkdir(mode=0o700, exist_ok=False)
    name = state["database"]
    user = contract.principal(name)
    password = "C9!" + secrets.token_urlsafe(48)
    profile = {
        "revision": 1,
        "connection": {
            **private_profile()["connection"],
            "database": name,
            "username": user,
            "password": password,
        },
        "review": {
            "machine": state["context"]["identity"][1],
            "server": state["context"]["identity"][2],
            "ticket_sha256": "",
        },
    }
    SqlProfileStore(directory / "runtime").save(profile)
    with admin(name, state["context"], readonly=True) as connection:
        require(snapshot(connection) == state["source"], "C9_not_original_restoration")
    q = quote_name(user)
    with admin("master", state["context"]) as connection:
        cursor = connection.cursor()
        require(
            not cursor.execute(
                "SELECT 1 FROM sys.server_principals WHERE name=?", user
            ).fetchone(),
            "C9_login_collision",
        )
        cursor.execute(
            "CREATE LOGIN "
            + q
            + " WITH PASSWORD="
            + literal(password)
            + ",DEFAULT_DATABASE="
            + quote_name(name)
            + ",CHECK_POLICY=ON,CHECK_EXPIRATION=OFF;"
        )
        protected = [
            r[0]
            for r in cursor.execute(
                "SELECT name FROM sys.server_principals WHERE type IN('S','U','G') "
                "AND name<>? ORDER BY name",
                user,
            ).fetchall()
        ]
        sid = cursor.execute(
            "SELECT CONVERT(varchar(170),SUSER_SID(?),2)", user
        ).fetchval()
    with admin(name, state["context"]) as connection:
        cursor = connection.cursor()
        cursor.execute("BEGIN TRANSACTION;")
        try:
            cursor.execute(
                "CREATE USER "
                + q
                + " FOR LOGIN "
                + q
                + " WITH DEFAULT_SCHEMA=crm_channels;"
            )
            cursor.execute("GRANT CONNECT,VIEW DEFINITION TO " + q)
            cursor.execute(
                "DENY " + ",".join(contract.DENIED) + " ON SCHEMA::dbo TO " + q
            )
            for table, rights in contract.RIGHTS.items():
                cursor.execute(
                    "GRANT " + ",".join(rights) + " ON OBJECT::" + table + " TO " + q
                )
            for table in contract.METADATA_RIGHTS:
                cursor.execute("GRANT SELECT ON OBJECT::" + table + " TO " + q)
            cursor.execute(
                "GRANT SELECT ON OBJECT::crm_channels.Credential (Channel,Kind) TO " + q
            )
            shape = metadata(cursor)
            require(
                sha(project(shape, user)) == sha(state["source"]["shape"]),
                "C9_existing_catalog_changed",
            )
            require(
                preservation(cursor) == state["source"]["preservation"],
                "C9_data_changed",
            )
            value = {
                "scope": "SQL-C9-restored-channels-ui-only",
                "release_sha256": contract.RELEASE_SHA,
                "catalog_version": shape["version"],
                "identity": target_identity(cursor),
                "login_sid": sid,
                "catalog_sha256": sha(shape),
                "journal_sha256": sha(journal_binary(cursor)),
                "credential_access": False,
                "protected_logins": protected,
            }
            require(
                value["journal_sha256"] == state["source"]["journal_sha256"],
                "C9_journal_changed",
            )
            cursor.execute("COMMIT;")
        except BaseException:
            cursor.execute("IF @@TRANCOUNT>0 ROLLBACK;")
            raise
    save(directory / "runtime-ticket.json", value)
    profile["review"]["ticket_sha256"] = hashlib.sha256(
        (directory / "runtime-ticket.json").read_bytes()
    ).hexdigest()
    SqlProfileStore(directory / "runtime").save(profile)
    state["profile_directory"] = str(directory)
    state["ticket"] = value
    save(work / "state.json", state)
    settings = load_settings(directory)
    with pyodbc.connect(
        connection_string(settings), timeout=5, autocommit=True
    ) as connection:
        require(metadata(connection.cursor()) == shape, "C9_runtime_catalog_incomplete")
        contract.verify(connection.cursor(), settings)
    print(
        json.dumps(
            {
                "phase": "prepared",
                "grant_count": len(contract.expected_acl(user)) - 7,
                "dbo_denies": 7,
                "metadata_admin_runtime_identical": True,
                "credential_cipher_access": False,
                "provider_key_created": False,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "prepare"))
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--source-work", type=Path, default=Path("/tmp/cbn-c8-ready"))
    args = parser.parse_args()
    try:
        if args.action == "start":
            start(args.work, args.source_work)
        else:
            prepare(args.work)
    except pyodbc.Error as error:
        raise SystemExit("C9 SQL error; SQLSTATE " + str(error.args[0])) from None
