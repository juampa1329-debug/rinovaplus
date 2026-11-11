"""C9 UI-only guard with exact column ACLs and mutable configuration."""

import hashlib
import json
import re
from contextlib import contextmanager, suppress
from pathlib import Path

from app.channels_catalog import VERSION, metadata
from app.foundation import identity, verify_global_permissions
from tools.crm_extension_snapshot_v2 import (
    PARTITION,
    journal_binary,
    partition_tables,
    records,
    require,
    sha,
    table_names,
)
from tools.crm_extension_v2 import assets

TARGET = re.compile(r"CBN_C9_TRIAL_20261025_([0-9a-f]{8})\Z")
PREFIX = "cbn_channels_ui_c9_"
RELEASE_SHA = "49f72eb835ce46b83ec9c6267da2f73c9d7799990de6fab8ed28762565985998"
RIGHTS = {
    "crm_channels.Account": ("SELECT", "INSERT", "UPDATE"),
    "crm_channels.Audit": ("INSERT",),
    "crm_channels.ExternalIdentity": ("SELECT",),
    "crm_channels.social_comments": ("SELECT",),
    "crm_channels.outbound_queue": ("SELECT",),
    "crm_channels.webhook_events": ("SELECT",),
    "crm_config.Configuration": ("SELECT",),
    "crm_meta.MigrationJournal": ("SELECT",),
}
CREDENTIAL_COLUMNS = {"Channel": 1, "Kind": 2}
DENIED = ("SELECT", "INSERT", "UPDATE", "DELETE", "ALTER", "REFERENCES", "EXECUTE")
METADATA_RIGHTS = ("sys.sql_expression_dependencies",)


def principal(database):
    match = TARGET.fullmatch(database)
    require(match is not None, "channels_isolated_target_required")
    return PREFIX + match[1]


def ticket(settings):
    raw = Path(settings.channels_ticket_path).read_bytes()
    require(
        hashlib.sha256(raw).hexdigest() == settings.channels_ticket_sha256,
        "channels_ticket_changed",
    )
    value = json.loads(raw)
    require(
        value["scope"] == "SQL-C9-restored-channels-ui-only"
        and value["release_sha256"] == RELEASE_SHA
        and value["catalog_version"] == VERSION
        and value["identity"]["database"] == settings.sql_database
        and value["identity"]["engine"] == 16
        and value["identity"]["compatibility"] == 160
        and value["identity"]["machine"] == settings.sql_expected_machine
        and value["identity"]["server"] == settings.sql_expected_server
        and value["credential_access"] is False,
        "channels_ticket_contract",
    )
    return value


def expected_acl(user):
    result = {
        ("OBJECT_OR_COLUMN", table, permission, "GRANT", 0, "dbo")
        for table, permissions in RIGHTS.items()
        for permission in permissions
    }
    result |= {
        ("DATABASE", "<database>", p, "GRANT", 0, "dbo")
        for p in ("CONNECT", "VIEW DEFINITION")
    }
    result |= {("SCHEMA", "dbo", p, "DENY", 0, "dbo") for p in DENIED}
    result |= {
        ("OBJECT_OR_COLUMN", table, "SELECT", "GRANT", 0, "dbo")
        for table in METADATA_RIGHTS
    }
    result |= {
        ("OBJECT_OR_COLUMN", "crm_channels.Credential", "SELECT", "GRANT", minor, "dbo")
        for minor in CREDENTIAL_COLUMNS.values()
    }
    return result


def verify_acl(cursor, settings, value, shape):
    user = principal(settings.sql_database)
    actor = [p for p in shape["principals"] if p["name"] == user]
    require(
        len(actor) == 1
        and actor[0]["sid"] == value["login_sid"]
        and actor[0]["type_desc"] == "SQL_USER"
        and actor[0]["authentication_type_desc"] == "INSTANCE"
        and actor[0]["default_schema_name"] == "crm_channels",
        "channels_actor",
    )
    actual = [r for r in shape["all_permissions"] if r["grantee"] == user]
    require(
        {
            tuple(
                r[k]
                for k in (
                    "class_desc",
                    "target",
                    "permission_name",
                    "state_desc",
                    "minor_id",
                    "grantor",
                )
            )
            for r in actual
        }
        == expected_acl(user)
        and len(actual) == len(expected_acl(user)),
        "channels_direct_acl",
    )
    require(
        not any(r["member_name"] == user for r in shape["role_membership"])
        and not any(r["owner"] == user for r in shape["schemas"]),
        "channels_actor_role_or_owner",
    )
    row = cursor.execute("""SELECT ORIGINAL_LOGIN(),SUSER_SNAME(),USER_NAME(),
      CONVERT(varchar(170),SUSER_SID(),2),IS_SRVROLEMEMBER('sysadmin'),
      HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','CONTROL'),
      HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','CREATE TABLE'),
      HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','VIEW DEFINITION')""").fetchone()
    require(
        tuple(row[:3]) == (user,) * 3
        and row[3] == value["login_sid"]
        and tuple(row[4:]) == (0, 0, 0, 1),
        "channels_effective_identity",
    )
    verify_global_permissions(cursor)
    powers = records(
        cursor,
        """SELECT s.name+'.'+t.name AS table_name,
      p.permission_name,HAS_PERMS_BY_NAME(QUOTENAME(s.name)+'.'+QUOTENAME(t.name),
      'OBJECT',p.permission_name) AS value FROM sys.tables t
      JOIN sys.schemas s ON s.schema_id=t.schema_id
      CROSS JOIN (VALUES('SELECT'),('INSERT'),('UPDATE'),('DELETE'),('ALTER'),
      ('REFERENCES'),('CONTROL')) p(permission_name) WHERE t.is_ms_shipped=0""",
    )
    tables = set(
        PARTITION["academic"] + PARTITION["foundation"] + PARTITION["extension"]
    )
    require(
        {r["table_name"] for r in powers} == tables and len(powers) == len(tables) * 7,
        "channels_effective_visibility",
    )
    for row in powers:
        if (
            row["table_name"] == "crm_channels.Credential"
            and row["permission_name"] == "SELECT"
        ):
            continue  # Column ACL below is authoritative; no table SELECT is granted.
        require(
            row["value"]
            == int(row["permission_name"] in RIGHTS.get(row["table_name"], ())),
            "channels_effective_object_permission",
        )
    columns = records(
        cursor,
        """SELECT c.name,c.column_id,
      HAS_PERMS_BY_NAME(N'crm_channels.Credential','OBJECT','SELECT',
        c.name,'COLUMN') AS allowed
      FROM sys.columns c WHERE c.object_id=OBJECT_ID(N'crm_channels.Credential')""",
    )
    require(
        len(columns) == 5
        and {c["name"] for c in columns}
        == {"Channel", "Kind", "KeyId", "Nonce", "Ciphertext"},
        "channels_ui_column_visibility",
    )
    for column in columns:
        require(
            column["allowed"] == int(column["name"] in CREDENTIAL_COLUMNS),
            "channels_ui_credential_column_access",
        )
    for actor in shape["principals"]:
        if actor["name"] != user:
            require(
                cursor.execute(
                    "SELECT HAS_PERMS_BY_NAME(?,'USER','IMPERSONATE')", actor["name"]
                ).fetchval()
                == 0,
                "channels_impersonation",
            )
    for name in value["protected_logins"]:
        require(
            cursor.execute(
                "SELECT HAS_PERMS_BY_NAME(?,'LOGIN','IMPERSONATE')", name
            ).fetchval()
            == 0,
            "channels_login_impersonation",
        )


def verify(cursor, settings):
    from app.sql_target import validate_settings

    validate_settings(settings)
    value = ticket(settings)
    require(identity(cursor) == value["identity"], "channels_target_identity")
    require(assets()[1] == RELEASE_SHA, "channels_source_release")
    shape = metadata(cursor)
    partition_tables(table_names(shape), True)
    verify_acl(cursor, settings, value, shape)
    require(sha(shape) == value["catalog_sha256"], "channels_catalog_drift")
    require(
        sha(journal_binary(cursor)) == value["journal_sha256"], "channels_journal_drift"
    )
    row = cursor.execute(
        "SELECT is_trustworthy_on,is_db_chaining_on FROM sys.databases "
        "WHERE database_id=DB_ID()"
    ).fetchone()
    require(tuple(row) == (0, 0), "channels_unsafe_ownership_chain")


@contextmanager
def transaction(settings, *, write=False):
    import pyodbc
    from fastapi import HTTPException

    from app.sql_target import connection_string

    connection = None
    cursor = None
    try:
        connection = pyodbc.connect(
            connection_string(settings), timeout=5, autocommit=False
        )
        connection.timeout = 10
        cursor = connection.cursor()
        cursor.execute(
            "SET XACT_ABORT ON; SET LOCK_TIMEOUT 5000; "
            "SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;"
        )
        # ODBC owns this transaction. The shared schema lock excludes migration;
        # ponytail: one writer lock for this low-volume restored-copy rehearsal.
        for resource, mode in (
            ("crm.schema.migrate.v1", "Shared"),
            ("crm.local.commit", "Exclusive" if write else "Shared"),
        ):
            row = cursor.execute(
                """DECLARE @r int;
              EXEC @r=sys.sp_getapplock @Resource=?,@LockMode=?,
              @LockOwner='Transaction',@LockTimeout=5000; SELECT @r;""",
                resource,
                mode,
            ).fetchone()
            require(row is not None and row[0] >= 0, "channels_lock_unavailable")
        verify(cursor, settings)
        yield cursor
        connection.commit()
    except (pyodbc.Error, ValueError, OSError, KeyError, TypeError):
        if connection is not None:
            with suppress(pyodbc.Error):
                connection.rollback()
        raise HTTPException(503, "channels_storage_unavailable") from None
    except BaseException:
        if connection is not None:
            with suppress(pyodbc.Error):
                connection.rollback()
        raise
    finally:
        if cursor is not None:
            with suppress(pyodbc.Error):
                cursor.close()
        if connection is not None:
            with suppress(pyodbc.Error):
                connection.close()
