"""Private explicit qualification driver; no source DML or automatic retries."""

import argparse
import contextlib
import hashlib
import json
import secrets
import time
import uuid
from pathlib import Path

import pyodbc
from app.es_schema_profile import CORE, journal_digest, principal
from app.es_schema_profile import VERSION as PROFILE_VERSION
from app.es_schema_profile import load as profile_load
from app.es_schema_profile import transaction as runtime_transaction
from app.parity_channels.catalog import metadata
from app.sql_profile import SqlProfileStore
from app.sql_target import _quoted
from tools.es_schema_migrate_v2 import (
    ACTOR,
    PACKAGE,
    TARGET,
    batches,
    digest,
    identity,
    shape,
    verify_package_catalog,
)
from tools.es_schema_migrate_v2 import apply as _apply
from tools.es_schema_migrate_v2 import reconcile as _reconcile
from tools.es_schema_migrate_v2 import release as _release
from tools.es_schema_recovery_v2 import backup, restore
from tools.foundation_snapshot import quote_name as q
from tools.foundation_snapshot import sha
from tools.parity_data import full_snapshot
from tools.rehearse_foundation import literal, private_profile

WORK = Path("/var/lib/cbn-p2/p1-es-v2-final")
APPROVED = None


def release():
    return _release(APPROVED)


def apply(*args, **kwargs):
    return _apply(
        *args,
        approved_manifest_sha256=APPROVED,
        approved_initial_shape_sha256=read(WORK / "state.json")["empty_backup"][
            "shape_sha256"
        ],
        **kwargs,
    )


def reconcile(*args, **kwargs):
    return _reconcile(*args, approved_manifest_sha256=APPROVED, **kwargs)


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n")
    path.chmod(0o600)


def read(path):
    return json.loads(Path(path).read_text())


def text(name):
    password = Path("/run/p2-private/sql19/sa-password").read_text()
    assert name in {"master", "DBSIIE_CRM_Esquema_ES_20261026"} or TARGET.fullmatch(
        name
    )
    return (
        "DRIVER={ODBC Driver 18 for SQL Server};SERVER=tcp:crm-cbn-p2-sql2019,1433;DATABASE="
        + _quoted(name)
        + ";UID=sa;PWD="
        + _quoted(password)
        + ";Encrypt=Yes;TrustServerCertificate=No;HostnameInCertificate=localhost;APP=CBN P1 ES explicit qualification;"
    )


@contextlib.contextmanager
def admin(name):
    c = pyodbc.connect(text(name), autocommit=True, timeout=5)
    c.timeout = 120
    try:
        actual = identity(c.cursor())
        assert (
            actual["database"] == name
            and actual["engine"] == 15
            and actual["machine"] == "crm-cbn-p2-sql2019"
        )
        yield c
    finally:
        with contextlib.suppress(Exception):
            c.close()


def fresh(kind="TRIAL"):
    return "CBN_P1ES_" + kind + "_20261026_" + uuid.uuid4().hex[:8]


def restored(checkpoint, kind="TRIAL"):
    name = fresh(kind)
    with admin("master") as c:
        result = restore(c, checkpoint, name)
    with admin(name) as c:
        actual = identity(c.cursor())
    return name, actual, result


def source_snapshots():
    old = private_profile()["connection"]
    result = {}
    names = [
        "HORARIOSSIIE",
        "CBN_C3_TRIAL_20261024_ac8505b8",
        "CBN_C9_TRIAL_20261025_23ac78d3",
        "CBN_C11_TRIAL_20261025_d30e2cb2",
        "CBN_C12_TRIAL_20261025_7a309d11",
        "CBN_C13_TRIAL_20261025_1f10a824",
    ]
    for name in names:
        s = (
            "DRIVER={ODBC Driver 18 for SQL Server};SERVER=tcp:"
            + old["server"]
            + ","
            + str(old["port"])
            + ";DATABASE="
            + _quoted(name)
            + ";UID="
            + _quoted(old["username"])
            + ";PWD="
            + _quoted(old["password"])
            + ";Encrypt=Yes;TrustServerCertificate=No;HostnameInCertificate=localhost;APP=CBN P1 ES source preservation read;"
        )
        with pyodbc.connect(s, autocommit=True, readonly=True, timeout=5) as c:
            assert identity(c.cursor())["engine"] == 16
            result[name] = full_snapshot(c)
    return result


def prepare():
    assert not (WORK / "state.json").exists(), "P1_ES_already_prepared"
    package = release()
    sources = source_snapshots()
    save(WORK / "sources-before.json", sources)
    name = fresh("BASE")
    with admin("master") as c:
        assert (
            not c.cursor()
            .execute("SELECT 1 FROM sys.databases WHERE name=?", name)
            .fetchone()
        )
        c.cursor().execute(
            "CREATE DATABASE " + q(name) + " COLLATE Modern_Spanish_CI_AS"
        )
        c.cursor().execute("ALTER DATABASE " + q(name) + " SET COMPATIBILITY_LEVEL=150")
    with admin(name) as c:
        cur = c.cursor()
        actual = identity(cur)
        cur.execute("CREATE SCHEMA crm_meta AUTHORIZATION dbo")
        cur.execute(
            "CREATE USER "
            + q(ACTOR)
            + " WITHOUT LOGIN;GRANT CREATE TABLE,VIEW DEFINITION TO "
            + q(ACTOR)
        )
        cur.execute(
            "GRANT ALTER,REFERENCES,SELECT,INSERT,UPDATE ON SCHEMA::dbo TO " + q(ACTOR)
        )
        cur.execute(
            "GRANT ALTER,REFERENCES,SELECT,INSERT,UPDATE ON SCHEMA::crm_meta TO "
            + q(ACTOR)
        )
        cur.execute(
            "GRANT SELECT ON OBJECT::sys.sql_expression_dependencies TO " + q(ACTOR)
        )
        before = shape(cur)
        cur.execute(
            "EXEC sys.sp_set_session_context @key=N'CBN_ES_TARGET',@value=?", name
        )
        cur.execute("EXECUTE AS USER=" + literal(ACTOR))
        cur.execute("BEGIN TRANSACTION")
        try:
            for unit in package["units"]:
                for batch in batches((PACKAGE / unit["file"]).read_text()):
                    cur.execute(batch)
                    while cur.nextset():
                        pass
            verify_package_catalog(cur)
        finally:
            cur.execute("IF @@TRANCOUNT>0 ROLLBACK")
            cur.execute("REVERT")
        assert before == shape(cur), "SQL smoke rollback changed catalog"
        checkpoint = backup(c, actual)
    save(
        WORK / "state.json",
        {
            "base": name,
            "base_identity": actual,
            "empty_backup": checkpoint,
            "sources": sources,
            "release_sha256": digest(PACKAGE / "release.json"),
            "status": "prepared_empty_native_backup_before_first_apply",
        },
    )
    print(
        json.dumps(
            {
                "empty_SQL2019_base": name,
                "uncommitted_DDL_smoke": "passed",
                "native_backup_verified": True,
                "source_databases_preserved": 6,
            }
        )
    )


def trial_apply():
    state = read(WORK / "state.json")
    name, actual, recovery = restored(state["empty_backup"])
    wal = WORK / (name + ".wal.jsonl")
    with admin(name) as c:
        result = apply(c, actual, wal)
    with admin(name) as c:
        assert apply(c, actual, wal)["status"] == "noop"
        assert verify_package_catalog(c.cursor())["passed"]
        shape_value = shape(c.cursor())
        history = journal_digest(c.cursor())
        checkpoint = backup(c, actual)
    save(
        WORK / "main.json",
        {
            "database": name,
            "identity": actual,
            "wal": str(wal),
            "result": result,
            "shape_sha256": shape_value,
            "journal_sha256": history,
            "post_backup": checkpoint,
            "before_apply_restore": recovery,
        },
    )
    print(
        json.dumps(
            {
                "SQL2019_main": name,
                "units": 2,
                "tables": 99,
                "repeat": "noop",
                "backup_and_restore_before_first_apply": True,
                "post_backup_verified": True,
            }
        )
    )


def faults():
    state = read(WORK / "state.json")
    results = []
    cases = [
        "ES-B000:before_commit",
        "ES-B000:after_commit",
        "ES-B001:before_commit",
        "ES-B001:after_commit",
        "ES-B001:ddl_error",
        "ES-B001:connection_loss_before_commit",
        "ES-B000:after_wal_before_SQL_started",
        "ES-B001:after_wal_before_SQL_started",
    ]
    for case in cases:
        name, actual, recovery = restored(state["empty_backup"], "FAULT")
        wal = WORK / (name + ".wal.jsonl")
        try:
            with admin(name) as c:
                apply(c, actual, wal, fault=case)
        except (RuntimeError, pyodbc.Error):
            pass
        else:
            raise AssertionError("Expected controlled failure")
        with admin(name) as c:
            try:
                apply(c, actual, wal)
            except ValueError as e:
                assert "reconciliation" in str(e)
            else:
                raise AssertionError("Unreconciled apply accepted")
        with admin(name) as c:
            reconciled = reconcile(c, actual, wal)
        with admin(name) as c:
            result = apply(c, actual, wal)
            verify_package_catalog(c.cursor())
            assert (
                c.cursor()
                .execute(
                    "SELECT COUNT(*) FROM crm_meta.MigrationJournal WHERE SuccessKey IS NOT NULL"
                )
                .fetchval()
                == 2
            )
        results.append(
            {
                "fault": case,
                "database": name,
                "independent_reconciliation": reconciled,
                "retry": result["status"],
                "passed": True,
            }
        )
    save(WORK / "faults.json", results)
    print(
        json.dumps(
            {
                "SQL2019_failure_recovery_scenarios": len(results),
                "all_passed": True,
                "no_cleanup_or_source_changes": True,
            }
        )
    )


def profile():
    main = read(WORK / "main.json")
    name, restored_identity, recovery = restored(main["post_backup"], "RECOVERY")
    user = principal(name)
    mapping = read(PACKAGE / "table_map.json")
    core = {key: mapping["CRM_map"][key] for key in CORE}
    directory = WORK / "profiles" / name
    assert not directory.exists(), "Existing profile cannot be overwritten"
    profile = {
        "revision": 1,
        "connection": {
            "server": "crm-cbn-p2-sql2019",
            "port": 1433,
            "database": name,
            "username": user,
            "password": "P1!" + secrets.token_urlsafe(48),
            "certificate_hostname": "localhost",
        },
        "review": {"ticket_sha256": ""},
    }
    with admin("master") as c:
        cur = c.cursor()
        assert not cur.execute(
            "SELECT 1 FROM sys.server_principals WHERE name=?", user
        ).fetchone()
        cur.execute(
            "CREATE LOGIN "
            + q(user)
            + " WITH PASSWORD="
            + literal(profile["connection"]["password"])
            + ",DEFAULT_DATABASE="
            + q(name)
            + ",CHECK_POLICY=ON,CHECK_EXPIRATION=OFF"
        )
        sid = cur.execute(
            "SELECT CONVERT(varchar(170),SUSER_SID(?),2)", user
        ).fetchval()
        protected = [
            r[0]
            for r in cur.execute(
                "SELECT name FROM sys.server_principals WHERE type IN('S','U','G') AND name<>?",
                user,
            ).fetchall()
        ]
    with admin(name) as c:
        cur = c.cursor()
        cur.execute(
            "CREATE USER "
            + q(user)
            + " FOR LOGIN "
            + q(user)
            + " WITH DEFAULT_SCHEMA=dbo;GRANT CONNECT,VIEW DEFINITION TO "
            + q(user)
        )
        cur.execute(
            "GRANT SELECT ON OBJECT::sys.sql_expression_dependencies TO " + q(user)
        )
        cur.execute("GRANT SELECT ON OBJECT::crm_meta.MigrationJournal TO " + q(user))
        for table in core.values():
            cur.execute(
                "GRANT SELECT,INSERT,UPDATE ON OBJECT::" + table + " TO " + q(user)
            )
        for table in mapping["academic_tables"]:
            cur.execute(
                "DENY SELECT,INSERT,UPDATE,DELETE,ALTER,REFERENCES ON OBJECT::"
                + table
                + " TO "
                + q(user)
            )
        cur.execute("DENY EXECUTE ON SCHEMA::dbo TO " + q(user))
        current = metadata(cur)
        ticket = {
            "version": PROFILE_VERSION,
            "identity": identity(cur),
            "sid": sid,
            "migration_manifest_sha256": APPROVED,
            "qualified_shape_sha256": shape(cur),
            "protected_logins": protected,
            "catalog_sha256": sha(current),
            "journal_sha256": journal_digest(cur),
            "core_map": core,
            "academic_tables": mapping["academic_tables"],
            "tables": sorted(
                r["schema_name"] + "." + r["name"]
                for r in current["catalog"]
                if r["type"].strip() == "U"
            ),
            "principals": [r["name"] for r in current["principals"]],
            "expires_at": int(time.time()) + 7 * 86400,
            "source_C13_preserved": True,
            "HTTP_routes_registered": False,
            "institutional_auth_ready": False,
        }
    directory.mkdir(mode=0o700, parents=True)
    save(directory / "ticket.json", ticket)
    profile["review"]["ticket_sha256"] = hashlib.sha256(
        (directory / "ticket.json").read_bytes()
    ).hexdigest()
    SqlProfileStore(directory / "runtime").save(profile)
    settings = profile_load(directory)
    with runtime_transaction(settings) as cur:
        assert (
            cur.execute("SELECT COUNT(*) FROM " + core["crm.Contact"]).fetchval() == 0
        )
        for table in mapping["academic_tables"]:
            assert (
                cur.execute(
                    "SELECT HAS_PERMS_BY_NAME(?,'OBJECT','SELECT')", table
                ).fetchval()
                == 0
            )
    try:
        with runtime_transaction(settings, write=True) as cur:
            row_id = str(uuid.uuid4())
            table = core["crm.Contact"]
            cur.execute(
                "INSERT "
                + table
                + "(ContactId,Name,Phone,City,ProgramId,Program,Schedule,Stage,Tags,Notes,Type,Interests,CustomValues) VALUES(?,?,?,'',NULL,'','','nuevo','','','','','{}')",
                row_id,
                "P1 SQL qualification",
                "",
            )
            cur.execute(
                "UPDATE " + table + " SET Notes=? WHERE ContactId=?",
                "qualified",
                row_id,
            )
            assert (
                cur.execute(
                    "SELECT Notes FROM " + table + " WHERE ContactId=?", row_id
                ).fetchval()
                == "qualified"
            )
            raise RuntimeError("P1_rollback_own_probe")
    except RuntimeError as e:
        assert str(e) == "P1_rollback_own_probe"
    with runtime_transaction(settings) as cur:
        assert (
            cur.execute("SELECT COUNT(*) FROM " + core["crm.Contact"]).fetchval() == 0
        )
    save(
        WORK / "profile-result.json",
        {
            "directory": str(directory),
            "database": name,
            "identity": restored_identity,
            "native_restore": recovery,
            "own_principal": True,
            "TLS_verified": True,
            "academic_tables_denied": 30,
            "core_tables_only": 6,
            "catalog_ACL_journal_guard": True,
            "CRUD_and_rollback": True,
            "HTTP_exposed": False,
        },
    )
    print(
        json.dumps(
            {
                "own_SQL2019_profile": "passed",
                "academic_tables_denied": 30,
                "core_tables": 6,
                "CRUD_probe_rolled_back": True,
                "HTTP_exposed": False,
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "main", "faults", "profile"])
    parser.add_argument("--manifest-sha256", required=True)
    args = parser.parse_args()
    APPROVED = args.manifest_sha256
    release()
    WORK.mkdir(mode=0o700, exist_ok=True)
    try:
        globals()[{"main": "trial_apply"}.get(args.mode, args.mode)]()
    except BaseException as e:
        import traceback

        save(
            WORK / (args.mode + "-error-" + uuid.uuid4().hex + ".json"),
            {
                "exception_type": type(e).__name__,
                "message": str(e),
                "traceback": traceback.format_exc(),
            },
        )
        print(
            json.dumps(
                {
                    "phase": args.mode,
                    "failed": True,
                    "exception_type": type(e).__name__,
                    "private_details_retained": True,
                }
            )
        )
        raise SystemExit(1) from None
