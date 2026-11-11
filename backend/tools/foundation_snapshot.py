"""Canonical metadata and private row digests for the scoped SQL-C3 rehearsal."""

import datetime
import decimal
import hashlib
import json
import uuid

SCHEMAS = ("crm_meta", "crm", "crm_config")
PRINCIPAL = "cbn_foundation_migrator"
SHAPE_VERSION = "cbn-foundation-shape-v1"
MANAGED = "s.name IN (N'crm_meta',N'crm',N'crm_config')"


def encode(value):
    def special(item):
        if isinstance(item, bytes):
            return {"binary": item.hex()}
        if isinstance(item, (datetime.date, datetime.time)):
            return {"temporal": item.isoformat()}
        if isinstance(item, decimal.Decimal):
            return {"decimal": str(item)}
        if isinstance(item, uuid.UUID):
            return {"uuid": str(item)}
        raise TypeError(type(item).__name__)

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=special,
    ).encode("utf-8")


def sha(value):
    return hashlib.sha256(encode(value)).hexdigest()


def records(cursor, sql, params=()):
    cursor.execute(sql, *params)
    names = [c[0] for c in cursor.description]
    result = []
    while batch := cursor.fetchmany(1000):
        result.extend(dict(zip(names, row, strict=True)) for row in batch)
        if len(result) > 200000:
            raise ValueError("metadata_limit")
    return result


def metadata(cursor, *, managed):
    scope = MANAGED if managed else "NOT (" + MANAGED + ")"
    identity_last = (
        ",CONVERT(nvarchar(100),ic.last_value) AS identity_last_value"
        if not managed
        else ""
    )
    # IDs, create/modify times and usage counters do not define shape.
    queries = {
        "schemas": f"""SELECT s.name,USER_NAME(s.principal_id) AS owner
          FROM sys.schemas s WHERE {scope} ORDER BY s.name""",
        "objects": f"""SELECT s.name AS schema_name,o.name,o.type,
          COALESCE(m.definition,dc.definition,cc.definition) AS definition
          FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
          LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
          LEFT JOIN sys.default_constraints dc ON dc.object_id=o.object_id
          LEFT JOIN sys.check_constraints cc ON cc.object_id=o.object_id
          WHERE o.is_ms_shipped=0 AND {scope} ORDER BY s.name,o.name,o.type""",
        "columns": f"""SELECT s.name AS schema_name,o.name AS table_name,c.name,
          c.column_id AS ordinal,TYPE_NAME(c.user_type_id) AS type_name,
          c.max_length,c.precision,c.scale,c.is_nullable,c.is_identity,c.is_computed,
          c.collation_name,cc.definition AS computed_definition,cc.is_persisted,
          dc.name AS default_name,dc.definition AS default_definition,
          CONVERT(nvarchar(100),ic.seed_value) AS identity_seed,
          CONVERT(nvarchar(100),ic.increment_value) AS identity_increment
          {identity_last}
          FROM sys.columns c JOIN sys.objects o ON o.object_id=c.object_id
          JOIN sys.schemas s ON s.schema_id=o.schema_id
          LEFT JOIN sys.identity_columns ic ON ic.object_id=c.object_id
            AND ic.column_id=c.column_id
          LEFT JOIN sys.computed_columns cc ON cc.object_id=c.object_id
            AND cc.column_id=c.column_id
          LEFT JOIN sys.default_constraints dc ON dc.object_id=c.default_object_id
          WHERE o.is_ms_shipped=0 AND {scope} ORDER BY s.name,o.name,c.column_id""",
        "indexes": f"""SELECT s.name AS schema_name,o.name AS table_name,i.name,
          i.type_desc,i.is_unique,i.is_primary_key,i.is_unique_constraint,
          i.is_disabled,i.has_filter,i.filter_definition,i.fill_factor,i.is_padded,
          i.ignore_dup_key,i.allow_row_locks,i.allow_page_locks,
          c.name AS column_name,ic.key_ordinal,ic.is_descending_key,
          ic.is_included_column,
          ic.index_column_id
          FROM sys.indexes i JOIN sys.objects o ON o.object_id=i.object_id
          JOIN sys.schemas s ON s.schema_id=o.schema_id
          LEFT JOIN sys.index_columns ic ON ic.object_id=i.object_id
            AND ic.index_id=i.index_id
          LEFT JOIN sys.columns c ON c.object_id=ic.object_id
            AND c.column_id=ic.column_id
          WHERE o.is_ms_shipped=0 AND {scope}
          ORDER BY s.name,o.name,i.name,ic.index_column_id""",
        "checks": f"""SELECT s.name AS schema_name,
          OBJECT_NAME(c.parent_object_id) AS table_name,
          c.name,c.definition,c.is_disabled,c.is_not_trusted,c.is_not_for_replication
          FROM sys.check_constraints c JOIN sys.schemas s ON s.schema_id=c.schema_id
          WHERE {scope} ORDER BY s.name,c.name""",
        "foreign_keys": f"""SELECT s.name AS schema_name,
          OBJECT_NAME(f.parent_object_id) AS table_name,
          f.name,COL_NAME(k.parent_object_id,k.parent_column_id) AS column_name,
          OBJECT_SCHEMA_NAME(k.referenced_object_id) AS target_schema,
          OBJECT_NAME(k.referenced_object_id) AS target_table,
          COL_NAME(k.referenced_object_id,k.referenced_column_id) AS target_column,
          k.constraint_column_id AS ordinal,f.delete_referential_action,
          f.update_referential_action,f.is_disabled,f.is_not_trusted,
          f.is_not_for_replication
          FROM sys.foreign_keys f JOIN sys.foreign_key_columns k
            ON k.constraint_object_id=f.object_id
          JOIN sys.schemas s ON s.schema_id=f.schema_id
          WHERE {scope} ORDER BY s.name,f.name,k.constraint_column_id""",
        "properties": f"""SELECT s.name AS schema_name,e.class,e.name,
          CASE WHEN e.class=1 THEN OBJECT_NAME(e.major_id) ELSE NULL END AS object_name,
          e.minor_id,CONVERT(nvarchar(max),e.value) AS value
          FROM sys.extended_properties e JOIN sys.schemas s
          ON s.schema_id=CASE WHEN e.class=3 THEN e.major_id
          WHEN e.class=1 THEN
            (SELECT schema_id FROM sys.objects WHERE object_id=e.major_id) END
          WHERE e.class IN (1,3) AND {scope}
          ORDER BY s.name,e.class,object_name,e.minor_id,e.name""",
        "permissions": f"""SELECT s.name AS schema_name,
          p.class_desc,p.permission_name,p.state_desc,
          USER_NAME(p.grantee_principal_id) AS grantee,
          USER_NAME(p.grantor_principal_id) AS grantor,
          CASE WHEN p.class=3 THEN s.name
            ELSE OBJECT_NAME(p.major_id) END AS object_name,
          CASE WHEN p.class=1 THEN COL_NAME(p.major_id,p.minor_id) END AS column_name
          FROM sys.database_permissions p JOIN sys.schemas s
          ON s.schema_id=CASE WHEN p.class=3 THEN p.major_id
          WHEN p.class=1 THEN
            (SELECT schema_id FROM sys.objects WHERE object_id=p.major_id) END
          WHERE p.class IN(1,3) AND {scope}
          ORDER BY s.name,p.class_desc,object_name,column_name,
            grantee,p.permission_name,p.state_desc""",
        "triggers": f"""SELECT s.name AS schema_name,t.name,t.is_disabled,
          t.is_instead_of_trigger,t.is_not_for_replication,
          m.definition
          FROM sys.triggers t JOIN sys.objects o ON o.object_id=t.parent_id
          JOIN sys.schemas s ON s.schema_id=o.schema_id
          LEFT JOIN sys.sql_modules m ON m.object_id=t.object_id
          WHERE {scope} ORDER BY s.name,t.name""",
    }
    result = {name: records(cursor, sql) for name, sql in queries.items()}
    result["version"] = SHAPE_VERSION
    if not managed:
        result["ddl_triggers"] = records(
            cursor,
            """SELECT t.name,t.is_disabled,m.definition
          FROM sys.triggers t LEFT JOIN sys.sql_modules m ON m.object_id=t.object_id
          WHERE t.parent_class=0 ORDER BY t.name""",
        )
        result["principals"] = records(
            cursor,
            f"""SELECT name,type_desc,default_schema_name,
          authentication_type_desc FROM sys.database_principals
          WHERE name<>N'{PRINCIPAL}' ORDER BY name""",
        )
        result["database_permissions"] = records(
            cursor,
            f"""SELECT p.class_desc,p.permission_name,
          p.state_desc,USER_NAME(p.grantee_principal_id) AS grantee,
          USER_NAME(p.grantor_principal_id) AS grantor
          FROM sys.database_permissions p WHERE p.class=0
          AND USER_NAME(p.grantee_principal_id)<>N'{PRINCIPAL}'
          ORDER BY grantee,p.permission_name,p.state_desc""",
        )
        result["role_membership"] = records(
            cursor,
            f"""SELECT USER_NAME(role_principal_id) AS role_name,
          USER_NAME(member_principal_id) AS member_name FROM sys.database_role_members
          WHERE USER_NAME(member_principal_id)<>N'{PRINCIPAL}'
          ORDER BY role_name,member_name""",
        )
    return result


def quote_name(name):
    return "[" + name.replace("]", "]]") + "]"


def data_signature(cursor):
    tables = records(
        cursor,
        """SELECT s.name AS schema_name,t.name,t.object_id FROM sys.tables t
      JOIN sys.schemas s ON s.schema_id=t.schema_id WHERE t.is_ms_shipped=0
      AND s.name NOT IN(N'crm_meta',N'crm',N'crm_config') ORDER BY s.name,t.name""",
    )
    signatures = []
    for table in tables:
        qualified = quote_name(table["schema_name"]) + "." + quote_name(table["name"])
        columns = records(
            cursor,
            """SELECT name,TYPE_NAME(user_type_id) AS type_name
          FROM sys.columns WHERE object_id=? ORDER BY column_id""",
            (table["object_id"],),
        )
        supported = {
            "bigint",
            "bit",
            "char",
            "date",
            "datetime",
            "datetime2",
            "decimal",
            "int",
            "nvarchar",
            "sysname",
            "time",
            "timestamp",
            "tinyint",
            "uniqueidentifier",
            "varbinary",
            "varchar",
        }
        if any(c["type_name"] not in supported for c in columns):
            raise ValueError("unsupported_private_digest_type")
        # SQL binary representations retain the seventh datetime fractional digit.
        projection = ",".join(
            "CONVERT(varbinary(max)," + quote_name(c["name"]) + ")" for c in columns
        )
        cursor.execute("SELECT " + projection + " FROM " + qualified)
        digests = []
        while rows := cursor.fetchmany(1000):
            digests.extend(hashlib.sha256(encode(list(row))).digest() for row in rows)
            if len(digests) > 1000000:
                raise ValueError("private_row_digest_limit")
        signatures.append(
            {
                "table": qualified,
                "rows": len(digests),
                "sha256": hashlib.sha256(b"".join(sorted(digests))).hexdigest(),
            }
        )
    # Return only an aggregate: never publish a per-row or individual-table digest.
    return {
        "tables": len(tables),
        "rows": sum(t["rows"] for t in signatures),
        "sha256": sha(signatures),
    }


def core_signature(cursor, *, include_data=True):
    result = {"metadata_sha256": sha(metadata(cursor, managed=False))}
    if include_data:
        result["data"] = data_signature(cursor)
    return result
