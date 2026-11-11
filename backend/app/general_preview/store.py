"""Own C13 authority over a restored copy, preserving all earlier profiles."""

import hashlib
import json
import re
import time
from contextlib import contextmanager, suppress
from pathlib import Path
from types import SimpleNamespace

import pyodbc
from fastapi import HTTPException

from app.foundation import GLOBAL_PERMISSIONS
from app.foundation import RIGHTS as CORE_RIGHTS
from app.parity_channels.catalog import metadata
from app.parity_channels.policy import (
    COLUMNS,
    require,
)
from app.parity_channels.policy import (
    RIGHTS as CHANNEL_RIGHTS,
)
from app.parity_channels.profile import Settings as PrivateSettings
from app.sql_profile import SqlProfileStore
from app.sql_target import HOST, _quoted
from app.sql_workspace import SqlWorkspace
from tools.cbn_foundation import target_identity
from tools.crm_extension_snapshot_v2 import journal_binary
from tools.foundation_snapshot import sha

TARGET = re.compile(r"CBN_C13_TRIAL_20261025_([0-9a-f]{8})\Z")
VERSION = "cbn-general-preview-c13-v1"
RIGHTS = {**CHANNEL_RIGHTS, **CORE_RIGHTS, "crm_channels.Audit": ("SELECT",)}
RIGHTS["crm_channels2.ProviderOperation"] = ("SELECT", "INSERT", "UPDATE")


def principal(database):
    match = TARGET.fullmatch(database)
    require(match is not None, "C13_target")
    return "cbn_general_c13_" + match[1]


def load(directory):
    directory = Path(directory)
    require(directory.is_absolute(), "C13_absolute_profile")
    value = SqlProfileStore(directory / "runtime").load()
    require(value is not None, "C13_profile_required")
    raw = (directory / "ticket.json").read_bytes()
    review = value["review"]
    c = value["connection"]
    ticket = json.loads(raw)
    require(
        hashlib.sha256(raw).hexdigest() == review["ticket_sha256"], "C13_ticket_digest"
    )
    require(
        ticket["version"] == VERSION
        and ticket["scope"] == "isolated_general_preview"
        and c["database"] == ticket["identity"]["database"]
        and c["username"] == principal(c["database"]),
        "C13_profile_binding",
    )
    require(
        HOST.fullmatch(c["server"])
        and type(c["port"]) is int
        and 1 <= c["port"] <= 65535
        and c["certificate_hostname"] == "localhost",
        "C13_TLS",
    )
    require(
        ticket["identity"]["engine"] == 16
        and ticket["identity"]["compatibility"] == 160
        and time.time() < ticket["expires_at"],
        "C13_engine_expiry",
    )
    require(
        hashlib.sha256(review["session_token"].encode()).hexdigest()
        == ticket["session_sha256"],
        "C13_session_binding",
    )
    return PrivateSettings(connection=c, review=review, ticket=ticket)


def connection_string(settings):
    c = settings.connection
    require(
        HOST.fullmatch(c["server"])
        and type(c["port"]) is int
        and 1 <= c["port"] <= 65535
        and c["username"] == principal(c["database"])
        and c["certificate_hostname"] == "localhost",
        "C13_transport_boundary",
    )
    return (
        "DRIVER={ODBC Driver 18 for SQL Server};SERVER=tcp:"
        + c["server"]
        + ","
        + str(c["port"])
        + ";DATABASE="
        + _quoted(c["database"])
        + ";Encrypt=Yes;TrustServerCertificate=No;HostnameInCertificate=localhost;UID="
        + _quoted(c["username"])
        + ";PWD="
        + _quoted(c["password"])
        + ";APP=CBN General C13;"
    )


def verify(cursor, settings):
    require(time.time() < settings.ticket["expires_at"], "C13_profile_expired")
    ticket = settings.ticket
    user = principal(settings.connection["database"])
    require(target_identity(cursor) == ticket["identity"], "C13_identity_drift")
    actual = cursor.execute(
        (
            "SELECT ORIGINAL_LOGIN(),SUSER_SNAME(),USER_NAME(),"
            "CONVERT(varchar(170),SUSER_SID(),2),IS_SRVROLEMEMB"
            "ER('sysadmin'),HAS_PERMS_BY_NAME(DB_NAME(),'DATABA"
            "SE','CONTROL')"
        )
    ).fetchone()
    require(
        tuple(actual[:3]) == (user,) * 3
        and actual[3] == ticket["sid"]
        and tuple(actual[4:]) == (0, 0),
        "C13_effective_identity",
    )
    for scope, expected in GLOBAL_PERMISSIONS.items():
        require(
            {
                r[0]
                for r in cursor.execute(
                    "SELECT permission_name FROM sys.fn_my_permissions(NULL,?)", scope
                ).fetchall()
            }
            == expected,
            "C13_global_permissions",
        )
    shape = metadata(cursor)
    require(sha(shape) == ticket["catalog_sha256"], "C13_catalog_ACL_owner_drift")
    require(
        sha(journal_binary(cursor)) == ticket["journal_sha256"], "C13_journal_drift"
    )
    require(
        [
            list(r)
            for r in cursor.execute(
                (
                    "SELECT ContextId,CONVERT(varchar(36),InstitutionId"
                    "),ContractVersion FROM crm_channels2.Context"
                )
            ).fetchall()
        ]
        == ticket["context"],
        "C13_context_drift",
    )
    require(
        tuple(
            cursor.execute(
                (
                    "SELECT is_trustworthy_on,is_db_chaining_on FROM "
                    "sys.databases WHERE database_id=DB_ID()"
                )
            ).fetchone()
        )
        == (0, 0),
        "C13_unsafe_chain",
    )
    for table in ticket["tables"]:
        for permission in (
            "SELECT",
            "INSERT",
            "UPDATE",
            "DELETE",
            "ALTER",
            "REFERENCES",
            "CONTROL",
        ):
            if table in COLUMNS and permission == "SELECT":
                continue
            require(
                cursor.execute(
                    "SELECT HAS_PERMS_BY_NAME(?,'OBJECT',?)", table, permission
                ).fetchval()
                == int(permission in RIGHTS.get(table, ())),
                "C13_effective_permission",
            )
        if table in COLUMNS:
            for (column,) in cursor.execute(
                "SELECT name FROM sys.columns WHERE object_id=OBJECT_ID(?)", table
            ).fetchall():
                require(
                    cursor.execute(
                        "SELECT HAS_PERMS_BY_NAME(?,'OBJECT','SELECT',?,'COLUMN')",
                        table,
                        column,
                    ).fetchval()
                    == int(column in COLUMNS[table]),
                    "C13_column_permission",
                )
    for actor in shape["principals"]:
        if actor["name"] != user:
            require(
                cursor.execute(
                    "SELECT HAS_PERMS_BY_NAME(?,'USER','IMPERSONATE')", actor["name"]
                ).fetchval()
                == 0,
                "C13_impersonation",
            )
    for actor in ticket["protected_logins"]:
        require(
            cursor.execute(
                "SELECT HAS_PERMS_BY_NAME(?,'LOGIN','IMPERSONATE')", actor
            ).fetchval()
            == 0,
            "C13_login_impersonation",
        )


@contextmanager
def transaction(settings, write=False):
    connection = None
    try:
        connection = pyodbc.connect(
            connection_string(settings), timeout=5, autocommit=False
        )
        connection.timeout = 20
        cursor = connection.cursor()
        cursor.execute(
            (
                "SET XACT_ABORT ON;SET LOCK_TIMEOUT 5000;SET "
                "TRANSACTION ISOLATION LEVEL SERIALIZABLE;"
            )
        )
        for resource, mode in (
            ("crm.schema.migrate.v1", "Shared"),
            ("crm.local.commit", "Exclusive" if write else "Shared"),
        ):
            require(
                cursor.execute(
                    (
                        "DECLARE @r int;EXEC @r=sys.sp_getapplock @Resource"
                        "=?,@LockMode=?,@LockOwner='Transaction',@LockTimeo"
                        "ut=5000;SELECT @r;"
                    ),
                    resource,
                    mode,
                ).fetchval()
                >= 0,
                "C13_lock",
            )
        verify(cursor, settings)
        yield cursor
        connection.commit()
    except (pyodbc.Error, ValueError, OSError, KeyError, TypeError):
        if connection:
            with suppress(pyodbc.Error):
                connection.rollback()
        raise HTTPException(503, "general_storage_unavailable") from None
    except BaseException:
        if connection:
            with suppress(pyodbc.Error):
                connection.rollback()
        raise
    finally:
        if connection:
            with suppress(pyodbc.Error):
                connection.close()


class Workspace(SqlWorkspace):
    def __init__(self, settings):
        self.profile = settings
        super().__init__(SimpleNamespace(mode="local_foundation"))

    def transaction(self, write=False):
        return transaction(self.profile, write)
