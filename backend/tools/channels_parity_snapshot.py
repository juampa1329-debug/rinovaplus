"""Complete C11 rehearsal catalog and exact protected-object partition."""

from tools.channels_parity_contract import ACTOR, SCHEMA, VERSION, model, require
from tools.crm_extension_snapshot_v2 import (
    PARTITION,
    data_signature,
    journal_binary,
    records,
    sha,
    table_names,
)
from tools.crm_extension_snapshot_v2 import (
    metadata as legacy_metadata,
)

OLD_TABLES = sorted(
    PARTITION["academic"] + PARTITION["foundation"] + PARTITION["extension"]
)
NEW_TABLES = [t["name"] for t in model()["tables"]]
JOURNAL = "crm_meta.MigrationJournal"
GRANTS = {
    ("DATABASE", "<database>", "CONNECT"),
    ("DATABASE", "<database>", "CREATE TABLE"),
    ("DATABASE", "<database>", "VIEW DEFINITION"),
    ("SCHEMA", SCHEMA, "ALTER"),
    ("SCHEMA", SCHEMA, "REFERENCES"),
    *(
        ("OBJECT_OR_COLUMN", name, "REFERENCES")
        for name in ("crm.Contact", "crm.Conversation", "crm.Message")
    ),
    *(("OBJECT_OR_COLUMN", JOURNAL, right) for right in ("SELECT", "INSERT")),
}
DENIES = {
    ("SCHEMA", "dbo", p)
    for p in ("SELECT", "INSERT", "UPDATE", "DELETE", "ALTER", "REFERENCES", "EXECUTE")
}


def metadata(cursor):
    result = legacy_metadata(cursor)
    result["object_owners"] = records(
        cursor,
        """SELECT s.name AS schema_name,
      o.name AS object_name,o.type,USER_NAME(o.principal_id) AS explicit_owner,
      USER_NAME(COALESCE(o.principal_id,s.principal_id)) AS effective_owner
      FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
      WHERE o.is_ms_shipped=0 ORDER BY s.name,o.name,o.type""",
    )
    return result


def verify_acl(shape, sid):
    users = [p for p in shape["principals"] if p["name"] == ACTOR]
    require(
        len(users) == 1
        and users[0]["sid"] == sid
        and users[0]["type_desc"] == "SQL_USER"
        and users[0]["authentication_type_desc"] == "NONE"
        and users[0]["default_schema_name"] == "dbo",
        "C11_actor_identity",
    )
    rights = [p for p in shape["all_permissions"] if p["grantee"] == ACTOR]
    require(len(rights) == len(GRANTS) + len(DENIES), "C11_actor_ACL_count")
    for state, expected in (("GRANT", GRANTS), ("DENY", DENIES)):
        require(
            {
                (r["class_desc"], r["target"], r["permission_name"])
                for r in rights
                if r["state_desc"] == state
            }
            == expected,
            "C11_actor_ACL",
        )
    require(
        all(r["minor_id"] == 0 and r["grantor"] == "dbo" for r in rights),
        "C11_actor_grantor",
    )
    require(
        not any(r["member_name"] == ACTOR for r in shape["role_membership"]),
        "C11_actor_roles",
    )
    require(
        not any(r["owner"] == ACTOR for r in shape["schemas"]), "C11_actor_ownership"
    )


def canonical(shape, sid):
    verify_acl(shape, sid)
    result = {
        k: [dict(row) for row in value] if k != "version" else VERSION
        for k, value in shape.items()
    }
    next(p for p in result["principals"] if p["name"] == ACTOR)["sid"] = (
        "<verified-C11-without-login>"
    )
    return {
        k: sorted(v, key=lambda r: sha(r)) if k != "version" else v
        for k, v in result.items()
    }


def protected(shape):
    result = {"version": "cbn-extension-shape-v3"}
    for key, value in shape.items():
        if key == "version":
            continue
        result[key] = [
            r
            for r in value
            if r.get("schema_name") != SCHEMA
            and not (key == "schemas" and r.get("name") == SCHEMA)
            and r.get("grantee") != ACTOR
            and r.get("member_name") != ACTOR
            and not (key == "principals" and r.get("name") == ACTOR)
        ]
    return result


def preserved_data(cursor):
    identity = records(
        cursor,
        """SELECT OBJECT_SCHEMA_NAME(object_id) AS schema_name,
      OBJECT_NAME(object_id) AS table_name,name,
      CONVERT(nvarchar(100),last_value) AS last_value
      FROM sys.identity_columns ORDER BY schema_name,table_name,name""",
    )
    return {
        "rows": data_signature(cursor, [t for t in OLD_TABLES if t != JOURNAL]),
        "identity_values": [
            r
            for r in identity
            if r["schema_name"] + "." + r["table_name"] in set(OLD_TABLES) - {JOURNAL}
        ],
        "legacy_journal": sha(journal_binary(cursor, 7)),
    }


def verify_partition(shape, prefix):
    expected = set(OLD_TABLES)
    units = model()["migration"]["units"]
    require(0 <= prefix <= len(units), "C11_prefix")
    for unit in units[:prefix]:
        expected.update(unit["tables"])
    actual = table_names(shape)
    require(
        len(actual) == len(set(actual)) and set(actual) == expected,
        "C11_exact_partition",
    )


def effective_acl(cursor):
    cursor.execute("EXECUTE AS USER=N'" + ACTOR + "';")
    try:
        row = cursor.execute(
            (
                "SELECT USER_NAME(),IS_MEMBER('db_owner'),IS_MEMBER('db_ddlad"
                "min'),HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','CONTROL')"
            )
        ).fetchone()
        require(tuple(row) == (ACTOR, 0, 0, 0), "C11_effective_roles")
        for table in OLD_TABLES:
            expected = (
                {"REFERENCES"}
                if table in {"crm.Contact", "crm.Conversation", "crm.Message"}
                else {"SELECT", "INSERT"}
                if table == JOURNAL
                else set()
            )
            for right in (
                "SELECT",
                "INSERT",
                "UPDATE",
                "DELETE",
                "ALTER",
                "REFERENCES",
                "CONTROL",
            ):
                value = cursor.execute(
                    "SELECT HAS_PERMS_BY_NAME(?,'OBJECT',?)", table, right
                ).fetchval()
                require(
                    value == int(right in expected), "C11_effective_protected_rights"
                )
        permissions = {
            r["permission_name"]
            for r in records(
                cursor,
                "SELECT permission_name FROM sys.fn_my_permissions(NULL,'DATABASE')",
            )
        }
        allowed = {
            "CONNECT",
            "CREATE TABLE",
            "VIEW DEFINITION",
            "VIEW SECURITY DEFINITION",
            "VIEW PERFORMANCE DEFINITION",
            "VIEW ANY COLUMN ENCRYPTION KEY DEFINITION",
            "VIEW ANY COLUMN MASTER KEY DEFINITION",
        }
        require(permissions == allowed, "C11_database_elevation")
    finally:
        cursor.execute("REVERT;")
