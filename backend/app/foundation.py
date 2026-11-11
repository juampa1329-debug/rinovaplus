"""Read-only acceptance of the SQL-C3 release plus the explicit C4 runtime ACL."""

import hashlib
import json
from pathlib import Path

from tools.foundation_snapshot import metadata, records, sha

DATABASE = "CBN_C3_TRIAL_20261024_ac8505b8"
PRINCIPAL = "cbn_foundation_runtime_c4"
RELEASE_SHA = "b8de5466cd6c0e8b373490cc0987bacbf90deff95ffe45e8d84f54f6dc08827a"
PACKAGE = Path(__file__).resolve().parents[1] / "migrations/cbn_foundation"
RIGHTS = {
    "crm.Contact": ("SELECT", "INSERT", "UPDATE"),
    "crm.Conversation": ("SELECT", "INSERT", "UPDATE"),
    "crm.Message": ("SELECT", "INSERT"),
    "crm.Operation": ("SELECT", "INSERT"),
    "crm_config.Configuration": ("SELECT", "UPDATE"),
    "crm_config.Operation": ("SELECT", "INSERT"),
    "crm_meta.MigrationJournal": ("SELECT",),
}
DENIED = ("SELECT", "INSERT", "UPDATE", "DELETE", "ALTER", "REFERENCES", "EXECUTE")
GLOBAL_PERMISSIONS = {
    "SERVER": {"CONNECT SQL", "VIEW ANY DATABASE"},
    "DATABASE": {
        "CONNECT",
        "VIEW DEFINITION",
        "VIEW SECURITY DEFINITION",
        "VIEW PERFORMANCE DEFINITION",
        "VIEW ANY COLUMN ENCRYPTION KEY DEFINITION",
        "VIEW ANY COLUMN MASTER KEY DEFINITION",
    },
}
IDENTITY_SQL = """SELECT DB_NAME(),DB_ID(),
 CONVERT(nvarchar(128),SERVERPROPERTY('MachineName')),
 CONVERT(nvarchar(128),SERVERPROPERTY('ServerName')),
 CONVERT(nvarchar(128),SERVERPROPERTY('InstanceName')),
 CONVERT(int,SERVERPROPERTY('ProductMajorVersion')),
 (SELECT compatibility_level FROM sys.databases WHERE database_id=DB_ID()),
 CONVERT(nvarchar(128),DATABASEPROPERTYEX(DB_NAME(),'Collation')),
 (SELECT CONVERT(varchar(33),create_date,126) FROM sys.databases
  WHERE database_id=DB_ID())"""
IDENTITY_KEYS = (
    "database",
    "database_id",
    "machine",
    "server",
    "instance",
    "engine",
    "compatibility",
    "collation",
    "created_at",
)


def require(condition):
    if not condition:
        raise ValueError("Foundation rehearsal contract mismatch")


def assets():
    raw = (PACKAGE / "release.json").read_bytes()
    require(hashlib.sha256(raw).hexdigest() == RELEASE_SHA)
    release = json.loads(raw)
    raw = (PACKAGE / "expected-shapes.json").read_bytes()
    require(hashlib.sha256(raw).hexdigest() == release["expected_shapes_sha256"])
    reader = Path(__file__).resolve().parents[1] / "tools/foundation_snapshot.py"
    expected = next(
        r["sha256"]
        for r in release["tool_files"]
        if r["path"].endswith("/foundation_snapshot.py")
    )
    require(hashlib.sha256(reader.read_bytes()).hexdigest() == expected)
    return release, json.loads(raw)["CBN-B006"]


def ticket(settings):
    raw = Path(settings.foundation_ticket_path).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == settings.foundation_ticket_sha256)
    value = json.loads(raw)
    require(
        value["scope"] == "SQL-C4-restored-repositories-only"
        and value["release_sha256"] == RELEASE_SHA
        and value["identity"]["database"] == DATABASE
        and value["identity"]["engine"] == 16
        and value["identity"]["compatibility"] == 160
    )
    return value


def identity(cursor):
    row = cursor.execute(IDENTITY_SQL).fetchone()
    require(row is not None and len(row) == len(IDENTITY_KEYS))
    return dict(zip(IDENTITY_KEYS, row, strict=True))


def runtime_permissions(cursor):
    return records(
        cursor,
        """SELECT p.class_desc,p.permission_name,p.state_desc,
      CASE p.class WHEN 1 THEN
        OBJECT_SCHEMA_NAME(p.major_id)+'.'+OBJECT_NAME(p.major_id)
      WHEN 3 THEN SCHEMA_NAME(p.major_id) ELSE DB_NAME() END AS target,p.minor_id,
      USER_NAME(p.grantor_principal_id) AS grantor
      FROM sys.database_permissions p WHERE USER_NAME(p.grantee_principal_id)=?
      ORDER BY p.class_desc,target,p.permission_name,p.minor_id""",
        (PRINCIPAL,),
    )


def expected_permissions():
    result = [
        ("OBJECT_OR_COLUMN", permission, "GRANT", table, 0, "dbo")
        for table, permissions in RIGHTS.items()
        for permission in permissions
    ]
    result += [
        ("DATABASE", permission, "GRANT", DATABASE, 0, "dbo")
        for permission in ("CONNECT", "VIEW DEFINITION")
    ]
    result += [("SCHEMA", permission, "DENY", "dbo", 0, "dbo") for permission in DENIED]
    return sorted(result)


def verify_acl(cursor, value):
    permissions = runtime_permissions(cursor)
    require(sorted(tuple(r.values()) for r in permissions) == expected_permissions())
    row = cursor.execute("""SELECT ORIGINAL_LOGIN(),SUSER_SNAME(),USER_NAME(),
      CONVERT(varchar(170),SUSER_SID(),2),IS_SRVROLEMEMBER('sysadmin'),
      IS_MEMBER('db_owner'),IS_MEMBER('db_ddladmin'),IS_MEMBER('db_datawriter'),
      HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','CONTROL'),
      HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','CREATE TABLE'),
      HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','ALTER ANY USER'),
      HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','VIEW DEFINITION')""").fetchone()
    require(
        tuple(row[:3]) == (PRINCIPAL,) * 3
        and row[3] == value["login_sid"]
        and tuple(row[4:]) == (0,) * 7 + (1,)
    )
    require(
        not cursor.execute(
            """SELECT 1 FROM sys.database_role_members
      WHERE member_principal_id=USER_ID(?)""",
            PRINCIPAL,
        ).fetchone()
    )
    require(
        not cursor.execute(
            """SELECT 1 FROM sys.schemas
      WHERE principal_id=USER_ID(?)""",
            PRINCIPAL,
        ).fetchone()
    )
    # Check effective permissions as well as direct ACLs (public/custom roles).
    row = cursor.execute("""SELECT COUNT(DISTINCT t.object_id),
      SUM(CASE WHEN HAS_PERMS_BY_NAME(QUOTENAME(s.name)+'.'+QUOTENAME(t.name),
        'OBJECT',p.permission)=0 THEN 0 ELSE 1 END)
      FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id
      CROSS JOIN (VALUES('SELECT'),('INSERT'),('UPDATE'),('DELETE'))
        p(permission)
      WHERE t.is_ms_shipped=0
        AND s.name NOT IN ('crm','crm_config','crm_meta')""").fetchone()
    require(tuple(row) == (50, 0))
    for table, allowed in RIGHTS.items():
        for permission in ("SELECT", "INSERT", "UPDATE", "DELETE", "ALTER", "CONTROL"):
            actual = cursor.execute(
                "SELECT HAS_PERMS_BY_NAME(?,'OBJECT',?)", table, permission
            ).fetchone()[0]
            require(actual == int(permission in allowed))
    verify_global_permissions(cursor)


def verify_global_permissions(cursor):
    # SQL2022 rehearsal only. Detect elevation through public/custom server roles,
    # impersonation or database-wide permissions, beyond direct object grants.
    for scope, expected in GLOBAL_PERMISSIONS.items():
        actual = cursor.execute(
            "SELECT permission_name FROM sys.fn_my_permissions(NULL,?)", scope
        ).fetchall()
        require({row[0] for row in actual} == expected)


def project_managed(shape):
    """Remove only the separately verified runtime actor; preserve the frozen ACL."""
    return {
        **shape,
        "permissions": [p for p in shape["permissions"] if p["grantee"] != PRINCIPAL],
    }


def project_academic(shape):
    """Administrative evidence only; all preexisting principals/ACLs remain compared."""
    return {
        **shape,
        "permissions": [p for p in shape["permissions"] if p["grantee"] != PRINCIPAL],
        "principals": [p for p in shape["principals"] if p["name"] != PRINCIPAL],
        "database_permissions": [
            p for p in shape["database_permissions"] if p["grantee"] != PRINCIPAL
        ],
    }


def journal_signature(cursor, shape):
    # SQL binary values retain all datetime2(7) digits, unlike Python datetime.
    columns = [
        c["name"]
        for c in shape["columns"]
        if c["schema_name"] == "crm_meta" and c["table_name"] == "MigrationJournal"
    ]
    select = ",".join(f"CONVERT(varbinary(max),[{c}]) AS [{c}]" for c in columns)
    return sha(
        records(
            cursor,
            "SELECT " + select + " FROM crm_meta.MigrationJournal ORDER BY EventId",
        )
    )


def verify(cursor, settings):
    from app.sql_target import validate_settings

    validate_settings(settings)
    value = ticket(settings)
    require(
        value["identity"]["machine"] == settings.sql_expected_machine
        and value["identity"]["server"] == settings.sql_expected_server
    )
    require(identity(cursor) == value["identity"])
    verify_acl(cursor, value)
    _, expected = assets()
    require(sha(project_managed(metadata(cursor, managed=True))) == sha(expected))
    require(journal_signature(cursor, expected) == value["journal_sha256"])
    row = cursor.execute(
        "SELECT Document,Revision FROM crm_config.Configuration WHERE ConfigurationId=1"
    ).fetchone()
    require(row is not None and row[1] > 0)
    from app.modules.crm_configuration.application.service import Configuration

    Configuration.model_validate_json(row[0])
