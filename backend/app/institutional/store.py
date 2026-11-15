"Independent P2 SQL authority. Older profiles and their contracts are immutable."

import base64
import hashlib
import json
import time
from contextlib import contextmanager, suppress
from pathlib import Path
from types import SimpleNamespace

import pyodbc
from fastapi import HTTPException

from app.foundation import GLOBAL_PERMISSIONS as SQL2022_GLOBAL_PERMISSIONS
from app.foundation import RIGHTS as CORE_RIGHTS
from app.institutional.policy import VERSION, principal, request_authority
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

RIGHTS = {**CHANNEL_RIGHTS, **CORE_RIGHTS, "crm_channels.Audit": ("SELECT",)}
RIGHTS["crm_channels2.ProviderOperation"] = ("SELECT",)
for name in (
    "Role",
    "AccessUser",
    "Session",
    "Setting",
    "Secret",
    "Factor",
    "RecoveryCode",
    "Challenge",
    "Operation",
    "ChannelSetting",
    "BudgetUsage",
):
    RIGHTS["crm_access." + name] = ("SELECT", "INSERT", "UPDATE")
RIGHTS["crm_access.Institution"] = ("SELECT", "UPDATE")
RIGHTS["crm_access.Audit"] = ("SELECT", "INSERT")
RIGHTS["crm_access.SettingHistory"] = ("SELECT", "INSERT")
RIGHTS["crm_access.RateBucket"] = ("SELECT", "INSERT", "UPDATE", "DELETE")


def load(directory):
    directory = Path(directory)
    require(directory.is_absolute(), "P2_absolute_profile")
    value = SqlProfileStore(directory / "runtime").load()
    require(value is not None, "P2_profile_required")
    raw = (directory / "ticket.json").read_bytes()
    review = value["review"]
    c = value["connection"]
    ticket = json.loads(raw)
    if ticket.get("version") in {
        "cbn-institutional-spanish-p2-v1",
        "cbn-institutional-spanish-p3-v1",
        "cbn-institutional-channels-p4-v1",
        "cbn-institutional-agents-p5-v1",
        "cbn-institutional-knowledge-p6-v1",
        "cbn-institutional-broadcast-p7-v1",
        "cbn-institutional-campaign-p8-v1", 'cbn-institutional-ads-p9-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
        from app.institutional.spanish import load as load_spanish

        return load_spanish(directory)
    require(
        hashlib.sha256(raw).hexdigest() == review["ticket_sha256"], "P2_ticket_digest"
    )
    require(
        ticket["version"] == VERSION
        and ticket["scope"] == "isolated_institutional_preview"
        and c["database"] == ticket["identity"]["database"]
        and c["username"] == principal(c["database"]),
        "P2_profile_binding",
    )
    require(
        HOST.fullmatch(c["server"])
        and type(c["port"]) is int
        and 1 <= c["port"] <= 65535
        and c["certificate_hostname"] == "localhost",
        "P2_TLS",
    )
    require(
        (ticket["identity"]["engine"], ticket["identity"]["compatibility"])
        in {(16, 160), (15, 150)}
        and time.time() < ticket["expires_at"],
        "P2_engine_expiry",
    )
    require(
        hashlib.sha256(review["session_token"].encode()).hexdigest()
        == ticket["session_sha256"],
        "P2_session_binding",
    )
    key = base64.b64decode(review["secrets_key"], validate=True)
    require(
        len(key) == 32
        and hashlib.sha256(key).hexdigest() == ticket["secret_key_sha256"],
        "P2_secret_key_binding",
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
        "P2_transport_boundary",
    )
    return (
        ("DRIVER={ODBC Driver 18 for SQL Server};SERVER=tcp:")
        + c["server"]
        + ","
        + str(c["port"])
        + ";DATABASE="
        + _quoted(c["database"])
        + (
            ";Encrypt=Yes;TrustServerCertificate=No"
            ";HostnameInCertificate=localhost;UID="
        )
        + _quoted(c["username"])
        + ";PWD="
        + _quoted(c["password"])
        + ";APP=CBN Institutional P2;"
    )


def verify(cursor, settings):
    require(time.time() < settings.ticket["expires_at"], "P2_profile_expired")
    ticket = settings.ticket
    user = principal(settings.connection["database"])
    require(target_identity(cursor) == ticket["identity"], "P2_identity_drift")
    actual = cursor.execute(
        (
            "SELECT ORIGINAL_LOGIN(),SUSER_SNAME(),"
            "USER_NAME(),CONVERT(varchar(170),SUSER"
            "_SID(),2),IS_SRVROLEMEMBER('sysadmin')"
            ",HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE"
            "','CONTROL')"
        )
    ).fetchone()
    require(
        tuple(actual[:3]) == (user,) * 3
        and actual[3] == ticket["sid"]
        and tuple(actual[4:]) == (0, 0),
        "P2_effective_identity",
    )
    expected_permissions = {
        scope: rights - {"VIEW SECURITY DEFINITION", "VIEW PERFORMANCE DEFINITION"}
        if ticket["identity"]["engine"] == 15
        else rights
        for scope, rights in SQL2022_GLOBAL_PERMISSIONS.items()
    }
    for scope, expected in expected_permissions.items():
        require(
            {
                r[0]
                for r in cursor.execute(
                    ("SELECT permission_name FROM sys.fn_my_permissions(NULL,?)"), scope
                ).fetchall()
            }
            == expected,
            "P2_global_permissions",
        )
    shape = metadata(cursor)
    require(sha(shape) == ticket["catalog_sha256"], "P2_catalog_ACL_owner_drift")
    require(sha(journal_binary(cursor)) == ticket["journal_sha256"], "P2_journal_drift")
    require(
        [
            list(r)
            for r in cursor.execute(
                (
                    "SELECT ContextId,CONVERT(varchar(36),I"
                    "nstitutionId),ContractVersion FROM crm"
                    "_channels2.Context"
                )
            ).fetchall()
        ]
        == ticket["context"],
        "P2_context_drift",
    )
    require(
        tuple(
            cursor.execute(
                (
                    "SELECT is_trustworthy_on,is_db_chainin"
                    "g_on FROM sys.databases WHERE database"
                    "_id=DB_ID()"
                )
            ).fetchone()
        )
        == (0, 0),
        "P2_unsafe_chain",
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
                "P2_effective_permission",
            )
        if table in COLUMNS:
            for (column,) in cursor.execute(
                ("SELECT name FROM sys.columns WHERE object_id=OBJECT_ID(?)"), table
            ).fetchall():
                require(
                    cursor.execute(
                        ("SELECT HAS_PERMS_BY_NAME(?,'OBJECT','SELECT',?,'COLUMN')"),
                        table,
                        column,
                    ).fetchval()
                    == int(column in COLUMNS[table]),
                    "P2_column_permission",
                )
    for actor in shape["principals"]:
        if actor["name"] != user:
            require(
                cursor.execute(
                    ("SELECT HAS_PERMS_BY_NAME(?,'USER','IMPERSONATE')"), actor["name"]
                ).fetchval()
                == 0,
                "P2_impersonation",
            )
    for actor in ticket["protected_logins"]:
        require(
            cursor.execute(
                ("SELECT HAS_PERMS_BY_NAME(?,'LOGIN','IMPERSONATE')"), actor
            ).fetchval()
            == 0,
            "P2_login_impersonation",
        )


@contextmanager
def transaction(
    settings, write=False, *, permission=None, anonymous=False, recent=False
):
    if getattr(settings, "postgres_profile", False):
        from app.institutional.postgres_rehearsal import transaction as postgres_transaction

        with postgres_transaction(
            settings, write, permission=permission, anonymous=anonymous, recent=recent
        ) as cursor:
            yield cursor
        return
    if settings.ticket.get("version") in {
        "cbn-institutional-spanish-p2-v1",
        "cbn-institutional-spanish-p3-v1",
        "cbn-institutional-channels-p4-v1",
        "cbn-institutional-agents-p5-v1",
        "cbn-institutional-knowledge-p6-v1",
        "cbn-institutional-broadcast-p7-v1",
        "cbn-institutional-campaign-p8-v1", 'cbn-institutional-ads-p9-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
        from app.institutional.spanish import transaction as spanish_transaction

        with spanish_transaction(
            settings, write, permission=permission, anonymous=anonymous, recent=recent
        ) as cursor:
            yield cursor
        return
    connection = None
    try:
        connection = pyodbc.connect(
            connection_string(settings), timeout=5, autocommit=False
        )
        connection.timeout = 20
        cursor = connection.cursor()
        cursor.execute(
            (
                "SET XACT_ABORT ON;SET LOCK_TIMEOUT 500"
                "0;SET TRANSACTION ISOLATION LEVEL SERI"
                "ALIZABLE;"
            )
        )
        for resource, mode in (
            ("crm.schema.migrate.v1", "Shared"),
            ("crm.local.commit", "Exclusive" if write else "Shared"),
        ):
            require(
                cursor.execute(
                    (
                        "DECLARE @r int;EXEC @r=sys.sp_getapplo"
                        "ck @Resource=?,@LockMode=?,@LockOwner="
                        "'Transaction',@LockTimeout=5000;SELECT"
                        " @r;"
                    ),
                    resource,
                    mode,
                ).fetchval()
                >= 0,
                "P2_lock",
            )
        verify(cursor, settings)
        if not anonymous:
            from app.institutional.auth import authorize

            authority = request_authority.get()
            require(authority is not None, "P2_session_context_required")
            authorize(
                cursor,
                settings,
                authority,
                permission or authority["permission"],
                recent=recent,
            )
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

    @contextmanager
    def transaction(self, write=False):
        with transaction(self.profile, write) as cursor:
            yield cursor
            if write:
                from app.institutional.auth import authorize
                from app.institutional.db import audit

                authority = request_authority.get()
                actor = authorize(cursor, self.profile, authority)
                audit(
                    cursor,
                    self.profile,
                    actor["UserId"],
                    authority["permission"],
                    authority.get("resource", ""),
                )

    def snapshot(self, cursor):
        from app.institutional.auth import authorize

        authority = request_authority.get()
        actor = authorize(cursor, self.profile, authority)
        value = super().snapshot(cursor)
        # Contact workflows are shared CRM context; message bodies require Inbox read.
        availability = cursor.execute(
            (
                "SELECT Document FROM crm_access.Settin"
                "g WHERE InstitutionId=? AND Section='m"
                "odules'"
            ),
            settings_institution(self.profile),
        ).fetchval()
        if (
            "inbox.read" not in json.loads(actor["Actions"])
            or not json.loads(availability)["enabled"]["inbox"]
        ):
            for thread in value["threads"]:
                thread["messages"] = []
        return value


def settings_institution(settings):
    return settings.ticket["context"][0][1]
