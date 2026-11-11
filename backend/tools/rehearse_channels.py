"""Explicit C8 backup, independent profile and repository rehearsal."""

import argparse
import contextlib
import hashlib
import json
import os
import secrets
import uuid
from pathlib import Path, PureWindowsPath

import pyodbc
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app import channels_contract as contract
from app.channels_catalog import metadata
from app.channels_profile import load_settings
from app.sql_profile import SqlProfileStore
from app.sql_target import HOST, _quoted
from tools.cbn_foundation import Audit, acquire, target_identity
from tools.crm_extension_snapshot_v2 import (
    journal_binary,
    preservation,
    quote_name,
    require,
    sha,
)
from tools.crm_extension_v2 import assets, verified_state
from tools.rehearse_crm_extension_v2 import admin as c7_admin
from tools.rehearse_crm_extension_v2 import capture, load, save
from tools.rehearse_foundation import checkdb, execute_results, literal, private_profile
from tools.rehearse_foundation_ui import signatures

pyodbc.pooling = False


def report(work, phase, **fields):
    value = {"stage": "SQL-C8", "phase": phase, **fields}
    save(work / (phase + "-result.json"), value)
    print(json.dumps(value), flush=True)


@contextlib.contextmanager
def admin(database, context, *, readonly=False):
    require(
        database == "master" or contract.TARGET.fullmatch(database),
        "C8_admin_destination",
    )
    c = private_profile()["connection"]
    require(
        HOST.fullmatch(c["server"]) and c["certificate_hostname"] == "localhost",
        "C8_admin_tls_endpoint",
    )
    text = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER=tcp:{c['server']},{c['port']};DATABASE={_quoted(database)};"
        "Encrypt=Yes;TrustServerCertificate=No;HostnameInCertificate=localhost;"
        f"UID={_quoted(c['username'])};PWD={_quoted(c['password'])};"
        "APP=CBN C8 rehearsal;"
    )
    connection = pyodbc.connect(text, timeout=5, autocommit=True, readonly=readonly)
    try:
        connection.timeout = 120
        identity = target_identity(connection.cursor())
        require(
            [identity[k] for k in ("machine", "server", "instance", "engine")]
            == [context["identity"][i] for i in (1, 2, 3, 4)],
            "C8_admin_identity",
        )
        yield connection
    finally:
        connection.close()


def restore(cursor, backup, context, name):
    require(contract.TARGET.fullmatch(name), "C8_restore_name")
    require(
        not cursor.execute("SELECT 1 FROM sys.databases WHERE name=?", name).fetchone(),
        "C8_restore_collision",
    )
    files = execute_results(cursor, "RESTORE FILELISTONLY FROM DISK=" + literal(backup))
    require(
        len(files) == 2 and {f["Type"] for f in files} == {"D", "L"}, "C8_backup_files"
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
            "C8_restore_file_collision",
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


def start(work, c7_work):
    require(not (work / "state.json").exists(), "C8_already_started")
    old = load(c7_work / "state.json")
    context = old["context"]
    source = old["tickets"]["TRIAL"]
    require(assets()[1] == contract.RELEASE_SHA, "C7_release_changed")
    current = signatures(context, Path(old["runtime_directory"]))
    require(
        all(
            current[k] == old["c5_signatures"][k]
            for k in ("source", "academic", "journal", "crm_counts")
        ),
        "C5_changed",
    )
    name = "CBN_C8_TRIAL_20261025_" + uuid.uuid4().hex[:8]
    backup = str(PureWindowsPath(context["paths"][0]) / (name + ".bak"))
    state = {
        "context": context,
        "database": name,
        "source_ticket": source,
        "c7_work": str(c7_work),
        "runtime_directory": old["runtime_directory"],
        "c5_signatures": current,
        "backup": backup,
    }
    with c7_admin(source["identity"]["database"], context) as connection:
        cursor = connection.cursor()
        acquire(cursor, "crm.schema.migrate.v1", "Session")
        acquire(cursor, "crm.local.commit", "Session")
        try:
            require(
                verified_state(cursor, source, assets()[0]), "C7_source_not_accepted"
            )
            before = capture(connection)
            require(before["journal_rows"] == 7, "C7_journal_not_seven")
            with admin("master", context) as master:
                m = master.cursor()
                require(
                    m.execute(
                        "SELECT file_exists FROM sys.dm_os_file_exists(?)", backup
                    ).fetchval()
                    == 0,
                    "C8_backup_collision",
                )
                execute_results(
                    m,
                    "BACKUP DATABASE "
                    + quote_name(source["identity"]["database"])
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
            require(capture(connection) == before, "C7_source_changed_during_backup")
            state["source"] = before
            save(work / "state.json", state)
        finally:
            for resource in ("crm.local.commit", "crm.schema.migrate.v1"):
                cursor.execute(
                    "EXEC sys.sp_releaseapplock @Resource=?,@LockOwner='Session';",
                    resource,
                )
    with admin("master", context) as connection:
        restore(connection.cursor(), backup, context, name)
    with admin(name, context, readonly=True) as connection:
        require(capture(connection) == before, "C8_restored_state_mismatch")
    report(
        work,
        "restored",
        database=name,
        backup_checksum_verified=True,
        checkdb=True,
        academic_rows=before["preservation"]["academic"]["rows"],
        original_business_rows=before["preservation"]["business"]["rows"],
        journal_rows=7,
        source_C7_and_C5_unchanged=True,
        no_migrations=True,
    )


def project(shape, user):
    result = {}
    for key, value in shape.items():
        if key == "version":
            result[key] = "cbn-extension-shape-v3"
        else:
            result[key] = [
                r
                for r in value
                if r.get("grantee") != user
                and not (key == "principals" and r.get("name") == user)
            ]
    return result


def prepare(work):
    state = load(work / "state.json")
    require(not (work / "profile/runtime-ticket.json").exists(), "C8_already_prepared")
    name = state["database"]
    user = contract.principal(name)
    directory = work / "profile"
    directory.mkdir(mode=0o700, exist_ok=False)
    password = "C8!" + secrets.token_urlsafe(48)
    key = AESGCM.generate_key(bit_length=256)
    key_hash = hashlib.sha256(key).hexdigest()
    descriptor = os.open(
        directory / "channels-aes256.key", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
    )
    with os.fdopen(descriptor, "wb") as file:
        file.write(key)
        file.flush()
        os.fsync(file.fileno())
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
            "credential_key_sha256": key_hash,
        },
    }
    # Persist the encrypted recovery material before CREATE LOGIN; SQL rollback
    # cannot undo filesystem writes or a separately committed server login.
    SqlProfileStore(directory / "runtime").save(profile)
    with admin(name, state["context"], readonly=True) as connection:
        require(capture(connection) == state["source"], "C8_not_original_restoration")
    audit = Audit(work / "preparation.jsonl", sha(name))
    attempt = str(uuid.uuid4())
    audit.add(attempt, "C8-PREPARE", "STARTED")
    q = quote_name(user)
    with admin("master", state["context"]) as connection:
        cursor = connection.cursor()
        require(
            not cursor.execute(
                "SELECT 1 FROM sys.server_principals WHERE name=?", user
            ).fetchone(),
            "C8_login_collision",
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
            shape = metadata(cursor)
            require(
                sha(project(shape, user)) == sha(state["source"]["shape"]),
                "C8_existing_catalog_changed",
            )
            require(
                preservation(cursor) == state["source"]["preservation"],
                "C8_preparation_data_changed",
            )
            journal = sha(journal_binary(cursor))
            require(journal == state["source"]["journal_sha256"], "C8_journal_changed")
            value = {
                "scope": "SQL-C8-restored-channels-only",
                "release_sha256": contract.RELEASE_SHA,
                "catalog_version": shape["version"],
                "identity": target_identity(cursor),
                "login_sid": sid,
                "catalog_sha256": sha(shape),
                "journal_sha256": journal,
                "credential_key_sha256": key_hash,
                "protected_logins": protected,
            }
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
    from app.sql_target import connection_string

    with pyodbc.connect(
        connection_string(settings), timeout=5, autocommit=True
    ) as connection:
        actual = metadata(connection.cursor())
        require(actual == shape, "C8_runtime_metadata_incomplete")
        contract.verify(connection.cursor(), settings)
    audit.add(attempt, "C8-PREPARE", "COMMITTED")
    report(
        work,
        "prepared",
        independent_profile=True,
        independent_login=True,
        grant_count=sum(len(v) for v in contract.RIGHTS.values())
        + 2
        + len(contract.METADATA_RIGHTS),
        dbo_denies=len(contract.DENIED),
        metadata_admin_runtime_identical=True,
        control_granted=False,
        academic_permissions=False,
        queue_insert=False,
        journal_rows_preserved=7,
        tls_validated=True,
        no_migrations=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "prepare"))
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--c7-work", type=Path, default=Path("/tmp/cbn-c7-v2"))
    args = parser.parse_args()
    try:
        if args.action == "start":
            start(args.work, args.c7_work)
        else:
            prepare(args.work)
    except pyodbc.Error as error:
        raise SystemExit("C8 SQL error; SQLSTATE " + str(error.args[0])) from None
