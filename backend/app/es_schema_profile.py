"""Own encrypted SQL2019 profile for the qualified Spanish foundation.

This module registers no HTTP routes and runs no startup DDL. Institutional
authentication remains a separate P2 gate; old preview profiles are not reused.
"""

import hashlib
import json
import time
from contextlib import contextmanager, suppress
from pathlib import Path
from types import SimpleNamespace

import pyodbc
from tools.es_schema_migrate_v2 import PACKAGE, TARGET, guard, release, shape
from tools.foundation_snapshot import sha

from app.parity_channels.catalog import metadata
from app.sql_profile import SqlProfileStore
from app.sql_target import HOST, _quoted

VERSION = "cbn-spanish-foundation-profile-v2"
CORE = (
    "crm.Contact",
    "crm.Conversation",
    "crm.Message",
    "crm.Operation",
    "crm_config.Configuration",
    "crm_config.Operation",
)
PERMISSIONS = ("SELECT", "INSERT", "UPDATE", "DELETE", "ALTER", "REFERENCES", "CONTROL")
CORE_MAP = {
    "crm.Contact": "dbo.CRMContacto",
    "crm.Conversation": "dbo.CRMConversacion",
    "crm.Message": "dbo.CRMMensaje",
    "crm.Operation": "dbo.CRMOperacion",
    "crm_config.Configuration": "dbo.CRMConfiguracion",
    "crm_config.Operation": "dbo.CRMConfiguracionOperacion",
}


def partition(ticket):
    if ticket.get("version") != VERSION or time.time() >= ticket.get("expires_at", 0):
        raise ValueError("ES_profile_version_or_expiry")
    release(ticket.get("migration_manifest_sha256"))
    layout = json.loads((PACKAGE / "table_map.json").read_text(encoding="utf-8"))
    expected_core = {key: layout["CRM_map"][key] for key in CORE}
    academic = set(layout["academic_tables"])
    tables = set(layout["CRM_map"].values()) | academic | {"crm_meta.MigrationJournal"}
    if (
        expected_core != CORE_MAP
        or len(layout["CRM_map"]) != 68
        or len(academic) != 30
        or len(tables) != 99
        or set(expected_core.values()) & academic
    ):
        raise ValueError("ES_approved_partition_invalid")
    if (
        ticket.get("core_map") != expected_core
        or len(ticket.get("tables", [])) != 99
        or set(ticket["tables"]) != tables
        or len(ticket.get("academic_tables", [])) != 30
        or set(ticket["academic_tables"]) != academic
    ):
        raise ValueError("ES_ticket_partition_mismatch")
    return expected_core, tables


def principal(database):
    if not TARGET.fullmatch(database):
        raise ValueError("ES_profile_target")
    return "cbn_es_runtime_p1_" + database.rsplit("_", 1)[1]


def load(directory):
    directory = Path(directory)
    if not directory.is_absolute():
        raise ValueError("ES_absolute_profile_required")
    value = SqlProfileStore(directory / "runtime").load()
    if value is None:
        raise ValueError("ES_profile_missing")
    raw = (directory / "ticket.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != value["review"]["ticket_sha256"]:
        raise ValueError("ES_ticket_binding")
    settings = SimpleNamespace(connection=value["connection"], ticket=json.loads(raw))
    connection_text(settings)
    if (
        settings.ticket["version"] != VERSION
        or time.time() >= settings.ticket["expires_at"]
    ):
        raise ValueError("ES_profile_version_or_expiry")
    return settings


def connection_text(settings):
    partition(settings.ticket)
    c = settings.connection
    if (
        not TARGET.fullmatch(c["database"])
        or c["username"] != principal(c["database"])
        or not HOST.fullmatch(c["server"])
        or type(c["port"]) is not int
        or not 1 <= c["port"] <= 65535
        or c["certificate_hostname"] != "localhost"
    ):
        raise ValueError("ES_profile_transport_boundary")
    return (
        "DRIVER={ODBC Driver 18 for SQL Server};SERVER=tcp:"
        + c["server"]
        + ","
        + str(c["port"])
        + ";DATABASE="
        + _quoted(c["database"])
        + ";UID="
        + _quoted(c["username"])
        + ";PWD="
        + _quoted(c["password"])
        + ";Encrypt=Yes;TrustServerCertificate=No;HostnameInCertificate=localhost;APP=CBN ES foundation;"
    )


def journal_digest(cursor):
    columns = [
        r[0]
        for r in cursor.execute(
            "SELECT name FROM sys.columns WHERE object_id=OBJECT_ID('crm_meta.MigrationJournal') ORDER BY column_id"
        ).fetchall()
    ]
    return sha(
        [
            list(r)
            for r in cursor.execute(
                "SELECT "
                + ",".join("CONVERT(varbinary(max),[" + c + "])" for c in columns)
                + " FROM crm_meta.MigrationJournal ORDER BY EventId"
            ).fetchall()
        ]
    )


def verify(cursor, settings):
    ticket = settings.ticket
    c = settings.connection
    user = principal(c["database"])
    core, tables = partition(ticket)
    if (
        ticket["version"] != VERSION
        or ticket["identity"]["database"] != c["database"]
        or time.time() >= ticket["expires_at"]
    ):
        raise ValueError("ES_profile_binding")
    guard(cursor, ticket["identity"])
    actual = cursor.execute(
        "SELECT ORIGINAL_LOGIN(),SUSER_SNAME(),USER_NAME(),CONVERT(varchar(170),SUSER_SID(),2),IS_SRVROLEMEMBER('sysadmin'),HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','CONTROL')"
    ).fetchone()
    if (
        tuple(actual[:3]) != (user, user, user)
        or actual[3] != ticket["sid"]
        or tuple(actual[4:]) != (0, 0)
    ):
        raise ValueError("ES_effective_identity")
    catalog = metadata(cursor)
    if (
        sha(catalog) != ticket["catalog_sha256"]
        or shape(cursor) != ticket["qualified_shape_sha256"]
        or journal_digest(cursor) != ticket["journal_sha256"]
    ):
        raise ValueError("ES_profile_catalog_ACL_or_journal_drift")
    allowed = {
        physical: {"SELECT", "INSERT", "UPDATE"}
        for logical, physical in core.items()
        if logical in CORE
    }
    allowed["crm_meta.MigrationJournal"] = {"SELECT"}
    for table in tables:
        for permission in PERMISSIONS:
            if cursor.execute(
                "SELECT HAS_PERMS_BY_NAME(?,'OBJECT',?)", table, permission
            ).fetchval() != int(permission in allowed.get(table, set())):
                raise ValueError("ES_effective_object_permission")
    for scope, expected in {
        "SERVER": {"CONNECT SQL", "VIEW ANY DATABASE"},
        "DATABASE": {
            "CONNECT",
            "VIEW DEFINITION",
            "VIEW ANY COLUMN ENCRYPTION KEY DEFINITION",
            "VIEW ANY COLUMN MASTER KEY DEFINITION",
        },
    }.items():
        if {
            r[0]
            for r in cursor.execute(
                "SELECT permission_name FROM sys.fn_my_permissions(NULL,?)", scope
            ).fetchall()
        } != expected:
            raise ValueError("ES_global_permission_drift")
    principals = {r["name"] for r in catalog["principals"]}
    if set(ticket["principals"]) != principals:
        raise ValueError("ES_principal_partition")
    for name in principals:
        if (
            name != user
            and cursor.execute(
                "SELECT HAS_PERMS_BY_NAME(?,'USER','IMPERSONATE')", name
            ).fetchval()
            != 0
        ):
            raise ValueError("ES_impersonation")
    if (
        "sa" not in ticket.get("protected_logins", [])
        or user in ticket["protected_logins"]
    ):
        raise ValueError("ES_protected_logins_required")
    for name in ticket["protected_logins"]:
        if (
            cursor.execute(
                "SELECT HAS_PERMS_BY_NAME(?,'LOGIN','IMPERSONATE')", name
            ).fetchval()
            != 0
        ):
            raise ValueError("ES_login_impersonation")


@contextmanager
def transaction(settings, *, write=False):
    connection = None
    try:
        connection = pyodbc.connect(
            connection_text(settings), autocommit=False, timeout=5
        )
        connection.timeout = 20
        cursor = connection.cursor()
        cursor.execute(
            "SET XACT_ABORT ON;SET LOCK_TIMEOUT 5000;SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"
        )
        for resource, mode in [
            ("crm.schema.migrate.v1", "Shared"),
            ("crm.local.commit", "Exclusive" if write else "Shared"),
        ]:
            result = cursor.execute(
                "DECLARE @r int;EXEC @r=sys.sp_getapplock @Resource=?,@LockMode=?,@LockOwner='Transaction',@LockTimeout=5000;SELECT @r",
                resource,
                mode,
            ).fetchval()
            if result < 0:
                raise ValueError("ES_runtime_lock")
        verify(cursor, settings)
        yield cursor
        connection.commit()
    except BaseException:
        if connection:
            with suppress(Exception):
                connection.rollback()
        raise
    finally:
        if connection:
            with suppress(Exception):
                connection.close()
