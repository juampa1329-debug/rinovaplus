"""Explicit C13 restored-copy preparation; no production targets or startup DDL."""

import argparse
import contextlib
import hashlib
import json
import secrets
import time
import uuid
from pathlib import Path, PureWindowsPath

import pyodbc

from app.general_preview.store import (
    COLUMNS,
    RIGHTS,
    TARGET,
    VERSION,
    principal,
    transaction,
)
from app.general_preview.store import (
    load as runtime_load,
)
from app.parity_channels.catalog import metadata
from app.parity_channels.guard import transaction as c12_transaction
from app.parity_channels.policy import DENIED
from app.parity_channels.profile import load as c12_load
from app.sql_profile import SqlProfileStore
from app.sql_target import HOST, _quoted
from tools.cbn_foundation import acquire, target_identity
from tools.channels_parity_snapshot import OLD_TABLES
from tools.crm_extension_snapshot_v2 import journal_binary
from tools.foundation_snapshot import quote_name, sha
from tools.parity_data import full_snapshot, signature
from tools.rehearse_crm_extension_v2 import load, save
from tools.rehearse_foundation import checkdb, execute_results, literal, private_profile
from tools.rehearse_parity_repositories import (
    sources as prior_sources,
)

SOURCE = "CBN_C12_TRIAL_20261025_7a309d11"


def require(value, code):
    if not value:
        raise ValueError(code)


@contextlib.contextmanager
def admin(name, context):
    require(TARGET.fullmatch(name) or name in {"master", SOURCE}, "C13_admin_target")
    c = private_profile()["connection"]
    require(
        HOST.fullmatch(c["server"]) and c["certificate_hostname"] == "localhost",
        "C13_admin_TLS",
    )
    text = (
        "DRIVER={ODBC Driver 18 for SQL Server};SERVER=tcp:"
        + c["server"]
        + ","
        + str(c["port"])
        + ";DATABASE="
        + _quoted(name)
        + ";Encrypt=Yes;TrustServerCertificate=No;HostnameInCertificate=localhost;UID="
        + _quoted(c["username"])
        + ";PWD="
        + _quoted(c["password"])
        + ";APP=CBN C13 preparation;"
    )
    connection = pyodbc.connect(text, autocommit=True, timeout=5)
    try:
        connection.timeout = 120
        actual = target_identity(connection.cursor())
        require(
            actual["database"] == name
            and [actual[k] for k in ("machine", "server", "instance", "engine")]
            == [context["identity"][i] for i in (1, 2, 3, 4)],
            "C13_admin_identity",
        )
        require(
            connection.cursor()
            .execute("SELECT IS_SRVROLEMEMBER('sysadmin')")
            .fetchval()
            == 1,
            "C13_admin_visibility",
        )
        yield connection
    finally:
        connection.close()


def prepare(work):
    require(not (work / "state.json").exists(), "C13_work_exists")
    parent = load(Path("/tmp/cbn-c12-final/state.json"))
    context = parent["context"]
    settings = c12_load(Path(parent["profile_directory"]))
    with c12_transaction(settings):
        pass
    with admin(SOURCE, context) as c:
        source = full_snapshot(c)
        shape = metadata(c.cursor())
    sources = prior_sources(context)
    name = "CBN_C13_TRIAL_20261025_" + uuid.uuid4().hex[:8]
    require(TARGET.fullmatch(name), "C13_trial_name")
    backup = str(PureWindowsPath(context["paths"][0]) / (name + ".bak"))
    with admin(SOURCE, context) as c:
        cursor = c.cursor()
        acquire(cursor, "crm.schema.migrate.v1", "Session")
        acquire(cursor, "crm.local.commit", "Session")
        try:
            require(full_snapshot(c) == source, "C13_source_changed")
            with admin("master", context) as m:
                cursor = m.cursor()
                require(
                    not cursor.execute(
                        "SELECT 1 FROM sys.databases WHERE name=?", name
                    ).fetchone(),
                    "C13_DB_collision",
                )
                require(
                    cursor.execute(
                        "SELECT file_exists FROM sys.dm_os_file_exists(?)", backup
                    ).fetchval()
                    == 0,
                    "C13_backup_collision",
                )
                execute_results(
                    cursor,
                    "BACKUP DATABASE "
                    + quote_name(SOURCE)
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
                files = execute_results(
                    cursor, "RESTORE FILELISTONLY FROM DISK=" + literal(backup)
                )
                require(
                    len(files) == 2 and {x["Type"] for x in files} == {"D", "L"},
                    "C13_file_layout",
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
                        "C13_file_collision",
                    )
                    moves.append(
                        "MOVE " + literal(f["LogicalName"]) + " TO " + literal(path)
                    )
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
            require(full_snapshot(c) == source, "C13_backup_source_changed")
        finally:
            c.cursor().execute(
                (
                    "EXEC sys.sp_releaseapplock @Resource=N'crm.local.c"
                    "ommit',@LockOwner=N'Session';EXEC "
                    "sys.sp_releaseapplock @Resource=N'crm.schema.migra"
                    "te.v1',@LockOwner=N'Session';"
                )
            )
    user = principal(name)
    directory = work / "profile"
    profile = {
        "revision": 1,
        "connection": {
            **private_profile()["connection"],
            "database": name,
            "username": user,
            "password": "C13!" + secrets.token_urlsafe(48),
        },
        "review": {"ticket_sha256": "", "session_token": secrets.token_urlsafe(48)},
    }
    SqlProfileStore(directory / "runtime").save(profile)
    with admin("master", context) as c:
        cursor = c.cursor()
        require(
            not cursor.execute(
                "SELECT 1 FROM sys.server_principals WHERE name=?", user
            ).fetchone(),
            "C13_login_collision",
        )
        cursor.execute(
            "CREATE LOGIN "
            + quote_name(user)
            + " WITH PASSWORD="
            + literal(profile["connection"]["password"])
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
                    "IN('S','U','G') AND name<>?"
                ),
                user,
            ).fetchall()
        ]
    with admin(name, context) as c:
        require(full_snapshot(c) == source, "C13_restore_exact")
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
            )
            for right in DENIED:
                cursor.execute("DENY " + right + " ON SCHEMA::dbo TO " + q)
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
            newshape = metadata(cursor)
            projected = {
                k: [
                    r
                    for r in v
                    if r.get("grantee") != user
                    and not (k == "principals" and r.get("name") == user)
                ]
                if k != "version"
                else v
                for k, v in newshape.items()
            }
            require(sha(projected) == sha(shape), "C13_existing_catalog_changed")
            ticket = {
                "version": VERSION,
                "scope": "isolated_general_preview",
                "identity": target_identity(cursor),
                "sid": sid,
                "catalog_sha256": sha(newshape),
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
                    for r in newshape["catalog"]
                    if r["type"].strip() == "U"
                ),
                "protected_logins": protected,
                "expires_at": int(time.time()) + 7 * 86400,
                "session_sha256": hashlib.sha256(
                    profile["review"]["session_token"].encode()
                ).hexdigest(),
            }
            academic = signature(
                cursor, [t for t in OLD_TABLES if t.startswith("dbo.")]
            )
            cursor.execute("COMMIT;")
        except BaseException:
            cursor.execute("IF @@TRANCOUNT>0 ROLLBACK;")
            raise
    save(directory / "ticket.json", ticket)
    profile["review"]["ticket_sha256"] = hashlib.sha256(
        (directory / "ticket.json").read_bytes()
    ).hexdigest()
    SqlProfileStore(directory / "runtime").save(profile)
    with transaction(runtime_load(directory)):
        pass
    require(prior_sources(context) == sources, "C13_prior_sources_changed")
    with admin(SOURCE, context) as c:
        require(full_snapshot(c) == source, "C13_C12_source_changed")
    save(
        work / "state.json",
        {
            "database": name,
            "context": context,
            "backup": backup,
            "source": source,
            "sources": sources,
            "profile_directory": str(directory),
            "academic": academic,
        },
    )
    print(
        json.dumps(
            {
                "phase": "C13_prepared",
                "database": name,
                "sources_preserved": True,
                "profile_own": True,
                "academic_signature_preserved": True,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--work", type=Path, required=True)
    try:
        prepare(p.parse_args().work)
    except pyodbc.Error as e:
        raise SystemExit("C13 SQLSTATE " + str(e.args[0])) from None
