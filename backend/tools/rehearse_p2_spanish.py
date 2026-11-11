"""Explicit local P2 qualification driver; never invoked by application startup."""

import argparse
import base64
import contextlib
import hashlib
import json
import secrets
import time
import uuid
from pathlib import Path

import pyodbc
from app.es_schema_profile import journal_digest
from app.institutional.crypto import token_hash
from app.institutional.spanish import RIGHTS, qualified_shape
from app.institutional.spanish_bindings import (
    PACKAGE,
    VERSION,
    layout,
    principal,
)
from app.parity_channels.catalog import metadata
from app.parity_channels.policy import COLUMNS
from app.sql_profile import SqlProfileStore
from app.sql_target import _quoted
from tools import p2_es_migrations as migration
from tools.es_schema_catalog_v2 import model, snapshot
from tools.es_schema_migrate_v2 import identity
from tools.foundation_snapshot import encode, sha
from tools.foundation_snapshot import quote_name as q
from tools.p2_es_recovery import backup, data_fingerprint, restore
from tools.qualify_spanish_schema import source_snapshots
from tools.rehearse_foundation import literal

WORK = Path("/var/lib/cbn-p2/p2-es-v1")
APPROVED = None


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    path.chmod(0o600)


def text(name):
    if not name or len(name) > 128 or not all(c.isalnum() or c == "_" for c in name):
        raise ValueError("P2ES_connection_database_identifier")
    password = Path("/run/p2-private/sql19/sa-password").read_text()
    return (
        "DRIVER={ODBC Driver 18 for SQL Server};SERVER=tcp:crm-cbn-p2-sql2019,1433;DATABASE="
        + _quoted(name)
        + ";UID=sa;PWD="
        + _quoted(password)
        + ";Encrypt=Yes;TrustServerCertificate=No;HostnameInCertificate=localhost;APP=CBN P2 Spanish qualification;"
    )


@contextlib.contextmanager
def admin(name, *, readonly=False):
    connection = pyodbc.connect(
        text(name), autocommit=True, timeout=5, readonly=readonly
    )
    connection.timeout = 120
    try:
        current = identity(connection.cursor())
        if (
            current["database"] != name
            or current["engine"] != 15
            or current["machine"] != "crm-cbn-p2-sql2019"
        ):
            raise ValueError("P2ES_qualification_server_identity")
        yield connection
    finally:
        with contextlib.suppress(Exception):
            connection.close()


def fresh(kind="TRIAL"):
    return "CBN_P2ES_" + kind + "_20261026_" + uuid.uuid4().hex[:8]


def restored(checkpoint, kind="TRIAL"):
    name = fresh(kind)
    with admin("master") as connection:
        result = restore(connection, checkpoint, name)
    with admin(name) as connection:
        actual = identity(connection.cursor())
    return name, actual, result


def source_2019(names=None):
    from tools.parity_data import ALLOWED

    allowed = (
        ALLOWED | set(layout()["tables"].values()) | set(layout()["academic_tables"])
    )
    if names is None:
        with admin("master", readonly=True) as connection:
            names = [
                r[0]
                for r in connection.cursor()
                .execute(
                    "SELECT name FROM sys.databases WHERE database_id>4 AND state=0 AND name NOT LIKE 'CBN_P2ES[_]%' ORDER BY name"
                )
                .fetchall()
            ]
    result = {}
    for name in names:
        with admin(name, readonly=True) as connection:
            cursor = connection.cursor()
            current = metadata(cursor)
            tables = sorted(
                r["schema_name"] + "." + r["name"]
                for r in current["catalog"]
                if r["type"].strip() == "U"
            )
            if not set(tables) <= allowed:
                raise ValueError("P2ES_source_snapshot_partition")
            values = []
            for table in tables:
                columns = [
                    r[0]
                    for r in cursor.execute(
                        "SELECT name FROM sys.columns WHERE object_id=OBJECT_ID(?) ORDER BY column_id",
                        table,
                    ).fetchall()
                ]
                projection = ",".join(
                    "CONVERT(varbinary(max)," + q(column) + ")" for column in columns
                )
                entries = []
                cursor.execute(
                    "SELECT "
                    + projection
                    + " FROM "
                    + ".".join(map(q, table.split(".")))
                )
                while batch := cursor.fetchmany(1000):
                    entries.extend(
                        hashlib.sha256(encode(list(row))).digest() for row in batch
                    )
                values.append(
                    {
                        "table": table,
                        "rows": len(entries),
                        "sha256": hashlib.sha256(b"".join(sorted(entries))).hexdigest(),
                    }
                )
            options = [
                list(r)
                for r in cursor.execute(
                    "SELECT OBJECT_SCHEMA_NAME(i.object_id),OBJECT_NAME(i.object_id),i.name,i.optimize_for_sequential_key,st.no_recompute FROM sys.indexes i LEFT JOIN sys.stats st ON st.object_id=i.object_id AND st.stats_id=i.index_id WHERE i.object_id IN(SELECT object_id FROM sys.tables WHERE is_ms_shipped=0) ORDER BY 1,2,3"
                ).fetchall()
            ]
            result[name] = {
                "catalog_sha256": sha({"raw": current, "index_options": options}),
                "data": {
                    "tables": len(tables),
                    "rows": sum(row["rows"] for row in values),
                    "sha256": sha(values),
                },
            }
    return result


def reference():
    if (WORK / "state.json").exists():
        raise ValueError("P2ES_reference_already_prepared")
    parent = read("/var/lib/cbn-p2/p1-es-v2-final/main.json")
    sources = {"Windows_SQL2022": source_snapshots(), "previous_SQL2019": source_2019()}
    save(WORK / "sources-before.json", sources)
    name, actual, recovery = restored(parent["post_backup"], "REF")
    seed_raw = secrets.token_urlsafe(32)
    seed = {
        "institution": str(uuid.uuid4()),
        "bootstrap_sha256": token_hash(seed_raw).hex(),
    }
    with admin(name) as connection:
        cursor = connection.cursor()
        cursor.execute(
            "CREATE USER "
            + q(migration.ACTOR)
            + " WITHOUT LOGIN;GRANT CREATE TABLE,VIEW DEFINITION TO "
            + q(migration.ACTOR)
        )
        cursor.execute(
            "GRANT SELECT,INSERT,UPDATE,ALTER,REFERENCES ON SCHEMA::dbo TO "
            + q(migration.ACTOR)
        )
        cursor.execute(
            "GRANT SELECT,INSERT ON OBJECT::crm_meta.MigrationJournal TO "
            + q(migration.ACTOR)
        )
        cursor.execute(
            "GRANT SELECT ON OBJECT::sys.sql_expression_dependencies TO "
            + q(migration.ACTOR)
        )
        mapping = layout()
        for table in mapping["base_tables"]:
            if table in {
                "crm_meta.MigrationJournal",
                mapping["tables"]["crm_config.Configuration"],
            }:
                continue
            cursor.execute(
                "DENY INSERT,UPDATE,DELETE,ALTER ON OBJECT::"
                + table
                + " TO "
                + q(migration.ACTOR)
            )
            if table in mapping["academic_tables"]:
                cursor.execute(
                    "DENY SELECT,REFERENCES ON OBJECT::"
                    + table
                    + " TO "
                    + q(migration.ACTOR)
                )
        cursor.execute(
            "DENY UPDATE,DELETE,ALTER ON OBJECT::"
            + mapping["tables"]["crm_config.Configuration"]
            + " TO "
            + q(migration.ACTOR)
        )
        before, initial_data = migration.shape(cursor), data_fingerprint(cursor)
        parent_digest = journal_digest(cursor)
        cursor.execute(
            "EXEC sys.sp_set_session_context @key=N'CBN_P2ES_TARGET',@value=?", name
        )
        cursor.execute("EXECUTE AS USER=" + literal(migration.ACTOR))
        cursor.execute("BEGIN TRANSACTION")
        stages = {}
        try:
            for unit, filename in zip(
                migration.UNITS,
                ("P2ES_001_channels.sql", "P2ES_002_access.sql"),
                strict=True,
            ):
                for batch in migration.ddl_batches({"file": filename}):
                    cursor.execute(batch)
                    while cursor.nextset():
                        pass
                migration.seed_unit(cursor, unit, seed)
                stages[unit] = model(snapshot(cursor))
                assert len(stages[unit]["tables"]) == (
                    123 if unit == migration.UNITS[0] else 138
                )
        finally:
            cursor.execute("IF @@TRANCOUNT>0 ROLLBACK")
            cursor.execute("REVERT")
        assert before == migration.shape(cursor) and initial_data == data_fingerprint(
            cursor
        )
        checkpoint = backup(connection, actual)
        business_data = data_fingerprint(cursor, omit_journal=True)
    save(PACKAGE / "expected-stages.json", stages)
    save(WORK / "initial-business-data.json", business_data)
    save(
        WORK / "state.json",
        {
            "reference": name,
            "identity": actual,
            "initial_backup": checkpoint,
            "parent_restore": recovery,
            "seed": seed,
            "bootstrap_token": seed_raw,
            "parent_journal_sha256": parent_digest,
            "expected_stages_sha256": migration.digest(
                PACKAGE / "expected-stages.json"
            ),
        },
    )
    print(
        json.dumps(
            {
                "reference": name,
                "uncommitted_DDL_smoke": "passed",
                "new_tables": 39,
                "academic_DML": False,
                "native_backup_before_first_apply": True,
                "previous_SQL2019_databases": len(sources["previous_SQL2019"]),
            }
        )
    )


def apply(connection, expected, wal, fault=None):
    state = read(WORK / "state.json")
    return migration.apply(
        connection,
        expected,
        wal,
        state["seed"],
        approved_manifest_sha256=APPROVED,
        approved_initial_shape_sha256=state["initial_backup"]["shape_sha256"],
        approved_initial_data_sha256=read(WORK / "initial-business-data.json")[
            "sha256"
        ],
        fault=fault,
    )


def main():
    state = read(WORK / "state.json")
    name, actual, recovery = restored(state["initial_backup"])
    wal = WORK / (name + ".wal.jsonl")
    with admin(name) as connection:
        result = apply(connection, actual, wal)
    with admin(name) as connection:
        assert apply(connection, actual, wal)["status"] == "noop"
        checkpoint = backup(connection, actual)
        digest = journal_digest(connection.cursor())
    save(
        WORK / "main.json",
        {
            "database": name,
            "identity": actual,
            "wal": str(wal),
            "result": result,
            "post_backup": checkpoint,
            "journal_sha256": digest,
            "before_apply_restore": recovery,
        },
    )
    print(
        json.dumps(
            {
                "database": name,
                "units_committed": 2,
                "repeat": "noop",
                "tables": 138,
                "parent_journal_preserved": True,
            }
        )
    )


def profile():
    state, current = read(WORK / "state.json"), read(WORK / "main.json")
    name, actual, recovery = restored(current["post_backup"])
    user, mapping = principal(name), layout()
    directory = WORK / "profiles" / name
    if directory.exists():
        raise ValueError("P2ES_profile_already_exists")
    session_key, secret_key = secrets.token_urlsafe(48), secrets.token_bytes(32)
    value = {
        "revision": 1,
        "connection": {
            "server": "crm-cbn-p2-sql2019",
            "port": 1433,
            "database": name,
            "username": user,
            "password": "P2!" + secrets.token_urlsafe(48),
            "certificate_hostname": "localhost",
        },
        "review": {
            "session_token": session_key,
            "secrets_key": base64.b64encode(secret_key).decode(),
        },
    }
    with admin("master") as connection:
        cursor = connection.cursor()
        cursor.execute(
            "CREATE LOGIN "
            + q(user)
            + " WITH PASSWORD="
            + literal(value["connection"]["password"])
            + ",DEFAULT_DATABASE="
            + q(name)
            + ",CHECK_POLICY=ON,CHECK_EXPIRATION=OFF"
        )
        sid = cursor.execute(
            "SELECT CONVERT(varchar(170),SUSER_SID(?),2)", user
        ).fetchval()
        protected = [
            r[0]
            for r in cursor.execute(
                "SELECT name FROM sys.server_principals WHERE type IN('S','U','G') AND name<>?",
                user,
            ).fetchall()
        ]
    with admin(name) as connection:
        cursor = connection.cursor()
        cursor.execute(
            "CREATE USER "
            + q(user)
            + " FOR LOGIN "
            + q(user)
            + " WITH DEFAULT_SCHEMA=dbo;GRANT CONNECT,VIEW DEFINITION TO "
            + q(user)
        )
        for logical, rights in RIGHTS.items():
            physical = mapping["tables"].get(logical, logical)
            cursor.execute(
                "GRANT "
                + ",".join(rights)
                + " ON OBJECT::"
                + physical
                + " TO "
                + q(user)
            )
        for logical, columns in COLUMNS.items():
            cursor.execute(
                "GRANT SELECT ON OBJECT::"
                + mapping["tables"][logical]
                + "("
                + ",".join(map(q, columns))
                + ") TO "
                + q(user)
            )
        for table in mapping["academic_tables"]:
            cursor.execute(
                "DENY SELECT,INSERT,UPDATE,DELETE,ALTER,REFERENCES ON OBJECT::"
                + table
                + " TO "
                + q(user)
            )
        cursor.execute("DENY EXECUTE ON SCHEMA::dbo TO " + q(user))
        catalog = metadata(cursor)
        migration.history(
            cursor,
            migration.release(APPROVED),
            APPROVED,
            current["identity"],
            state["seed"],
        )
        ticket = {
            "version": VERSION,
            "scope": "isolated_institutional_spanish",
            "migration_manifest_sha256": APPROVED,
            "identity": actual,
            "sid": sid,
            "table_map": mapping["tables"],
            "academic_tables": mapping["academic_tables"],
            "tables": sorted(
                set(mapping["tables"].values()) | set(mapping["academic_tables"])
            ),
            "catalog_sha256": sha(catalog),
            "qualified_shape_sha256": qualified_shape(cursor),
            "journal_sha256": journal_digest(cursor),
            "context": [[1, state["seed"]["institution"], "CBN-channels-parity-v1"]],
            "seed": state["seed"],
            "secret_key_sha256": hashlib.sha256(secret_key).hexdigest(),
            "session_sha256": hashlib.sha256(session_key.encode()).hexdigest(),
            "protected_logins": protected,
            "principals": sorted(r["name"] for r in catalog["principals"]),
            "expires_at": int(time.time()) + 365 * 86400,
            "restored_from": {
                "source_database": current["database"],
                "backup_uuid": current["post_backup"]["backup_uuid"],
            },
        }
    directory.mkdir(mode=0o700, parents=True)
    save(directory / "ticket.json", ticket)
    value["review"]["ticket_sha256"] = migration.digest(directory / "ticket.json")
    SqlProfileStore(directory / "runtime").save(value)
    from app.institutional.spanish import load, transaction

    with transaction(load(directory), anonymous=True) as cursor:
        assert (
            cursor.execute("SELECT COUNT(*) FROM crm_access.AccessUser").fetchval() == 0
        )
    save(
        WORK / "profile.json",
        {
            "database": name,
            "directory": str(directory),
            "identity": actual,
            "native_restore": recovery,
            "manifest_sha256": APPROVED,
        },
    )
    print(
        json.dumps(
            {
                "own_profile": "passed",
                "database": name,
                "TLS": "verified",
                "tables_partition": 138,
                "academic_tables_denied": 30,
                "bootstrap_initialized": False,
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["reference", "main", "profile"])
    parser.add_argument("--manifest-sha256")
    arguments = parser.parse_args()
    APPROVED = arguments.manifest_sha256
    if arguments.mode != "reference":
        migration.release(APPROVED)
    WORK.mkdir(mode=0o700, exist_ok=True)
    try:
        globals()[arguments.mode]()
    except BaseException as error:
        import traceback

        save(
            WORK / ("error-" + uuid.uuid4().hex + ".json"),
            {
                "type": type(error).__name__,
                "message": str(error),
                "traceback": traceback.format_exc(),
            },
        )
        print(
            json.dumps(
                {
                    "failed": type(error).__name__,
                    "mode": arguments.mode,
                    "private_diagnostic_saved": True,
                }
            )
        )
        raise SystemExit(1)
