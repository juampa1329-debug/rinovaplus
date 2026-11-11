"""Own SQL identity, complete catalog, effective ACL and immutable history."""

from contextlib import contextmanager, suppress

from app.foundation import verify_global_permissions
from app.parity_channels.catalog import metadata
from app.parity_channels.policy import COLUMNS, DENIED, RIGHTS, principal, require
from app.parity_channels.profile import connection_string
from tools.cbn_foundation import target_identity
from tools.crm_extension_snapshot_v2 import journal_binary
from tools.foundation_snapshot import sha


def acl(cursor, shape, user, sid):
    actor = [p for p in shape["principals"] if p["name"] == user]
    require(
        len(actor) == 1
        and actor[0]["sid"] == sid
        and actor[0]["authentication_type_desc"] == "INSTANCE"
        and actor[0]["default_schema_name"] == "crm_channels2",
        "C12_actor",
    )
    expected = {
        ("DATABASE", "<database>", p, "GRANT", 0, "dbo")
        for p in ("CONNECT", "VIEW DEFINITION")
    }
    expected |= {("SCHEMA", "dbo", p, "DENY", 0, "dbo") for p in DENIED}
    expected |= {
        ("OBJECT_OR_COLUMN", t, p, "GRANT", 0, "dbo")
        for t, ps in RIGHTS.items()
        for p in ps
    }
    for table, columns in COLUMNS.items():
        ids = dict(
            cursor.execute(
                "SELECT name,column_id FROM sys.columns WHERE object_id=OBJECT_ID(?)",
                table,
            ).fetchall()
        )
        expected |= {
            ("OBJECT_OR_COLUMN", table, "SELECT", "GRANT", ids[c], "dbo")
            for c in columns
        }
    actual = [
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
        for r in shape["all_permissions"]
        if r["grantee"] == user
    ]
    require(len(actual) == len(expected) and set(actual) == expected, "C12_direct_ACL")
    require(
        not any(r["member_name"] == user for r in shape["role_membership"])
        and not any(r["owner"] == user for r in shape["schemas"])
        and not any(
            r["explicit_owner"] == user or r["effective_owner"] == user
            for r in shape["object_owners"]
        ),
        "C12_owner_or_role",
    )


def verify(cursor, settings):
    ticket = settings.ticket
    user = principal(settings.connection["database"])
    require(target_identity(cursor) == ticket["identity"], "C12_identity_drift")
    row = cursor.execute(
        (
            "SELECT ORIGINAL_LOGIN(),SUSER_SNAME(),USER_NAME(),"
            "CONVERT(varchar(170),SUSER_SID(),2),IS_SRVROLEMEMB"
            "ER('sysadmin'),HAS_PERMS_BY_NAME(DB_NAME(),'DATABA"
            "SE','CONTROL'),HAS_PERMS_BY_NAME(DB_NAME(),'DATABA"
            "SE','CREATE TABLE')"
        )
    ).fetchone()
    require(
        tuple(row[:3]) == (user,) * 3
        and row[3] == ticket["login_sid"]
        and tuple(row[4:]) == (0, 0, 0),
        "C12_effective_identity",
    )
    verify_global_permissions(cursor)
    shape = metadata(cursor)
    acl(cursor, shape, user, ticket["login_sid"])
    require(sha(shape) == ticket["catalog_sha256"], "C12_catalog_drift")
    require(
        sha(journal_binary(cursor)) == ticket["journal_sha256"], "C12_history_drift"
    )
    rows = cursor.execute(
        (
            "SELECT ContextId,CONVERT(varchar(36),InstitutionId"
            "),ContractVersion FROM crm_channels2.Context"
        )
    ).fetchall()
    require([list(r) for r in rows] == ticket["context"], "C12_institution_drift")
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
        "C12_ownership_chain",
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
                continue  # The exact column matrix below is authoritative.
            value = cursor.execute(
                "SELECT HAS_PERMS_BY_NAME(?,'OBJECT',?)", table, permission
            ).fetchval()
            require(
                value == int(permission in RIGHTS.get(table, ())),
                "C12_effective_object_permission",
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
                    "C12_effective_column_permission",
                )
    for p in shape["principals"]:
        if p["name"] != user:
            require(
                cursor.execute(
                    "SELECT HAS_PERMS_BY_NAME(?,'USER','IMPERSONATE')", p["name"]
                ).fetchval()
                == 0,
                "C12_impersonation",
            )
    for login in ticket["protected_logins"]:
        require(
            cursor.execute(
                "SELECT HAS_PERMS_BY_NAME(?,'LOGIN','IMPERSONATE')", login
            ).fetchval()
            == 0,
            "C12_login_impersonation",
        )


@contextmanager
def transaction(settings, write=False):
    import pyodbc
    from fastapi import HTTPException

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
            result = cursor.execute(
                (
                    "DECLARE @r int;EXEC @r=sys.sp_getapplock @Resource"
                    "=?,@LockMode=?,@LockOwner='Transaction',@LockTimeo"
                    "ut=5000;SELECT @r;"
                ),
                resource,
                mode,
            ).fetchval()
            require(result is not None and result >= 0, "C12_lock_unavailable")
        verify(cursor, settings)
        yield cursor
        connection.commit()
    except (pyodbc.Error, ValueError, OSError, KeyError, TypeError):
        if connection:
            with suppress(pyodbc.Error):
                connection.rollback()
        raise HTTPException(503, "parity_storage_unavailable") from None
    except BaseException:
        if connection:
            with suppress(pyodbc.Error):
                connection.rollback()
        raise
    finally:
        if connection:
            with suppress(pyodbc.Error):
                connection.close()
