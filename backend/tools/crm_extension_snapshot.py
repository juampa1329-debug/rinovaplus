"""Exact-object C7 catalog and binary data reader; frozen C3 readers stay intact."""

import hashlib
import json
from pathlib import Path

from tools.foundation_snapshot import encode, quote_name, records, sha
from tools.foundation_snapshot import metadata as legacy_metadata

PACKAGE = Path(__file__).resolve().parents[1] / "migrations/cbn_channels"
PARTITION = json.loads((PACKAGE / "partition.json").read_text(encoding="utf-8"))
VERSION = "cbn-extension-shape-v2"
ACTOR = "cbn_channels_migrator_c7"
JOURNAL = "crm_meta.MigrationJournal"


def require(condition, code):
    if not condition:
        raise ValueError(code)


def table_sets(extended=False):
    return (
        set(PARTITION["academic"])
        | set(PARTITION["foundation"])
        | (set(PARTITION["extension"]) if extended else set())
    )


def partition_tables(actual, extended=False):
    require(len(actual) == len(set(actual)), "duplicate_table")
    require(set(actual) == table_sets(extended), "unknown_missing_or_colliding_table")
    return {"academic": 50, "foundation": 7, "extension": 8 if extended else 0}


def metadata(cursor):
    require(
        cursor.execute(
            "SELECT HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','CONTROL')"
        ).fetchval()
        == 1,
        "complete_administrative_visibility_required",
    )
    # Reuse unchanged canonical queries over BOTH historical halves. No schema
    # complement defines C7 protection; exact objects and full catalogs do.
    left = legacy_metadata(cursor, managed=True)
    right = legacy_metadata(cursor, managed=False)
    result = {
        key: sorted(left[key] + right[key], key=encode)
        for key in left
        if key != "version"
    }
    result["version"] = VERSION
    for column in result["columns"]:
        column.pop("identity_last_value", None)
    result["catalog"] = records(
        cursor,
        """SELECT s.name AS schema_name,o.name,
      o.type,OBJECT_NAME(o.parent_object_id) AS parent_name,
      CONVERT(int,ISNULL(OBJECTPROPERTY(o.object_id,'IsEncrypted'),0)) AS encrypted
      FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
      WHERE o.is_ms_shipped=0 ORDER BY s.name,o.name,o.type""",
    )
    require(not any(o["encrypted"] for o in result["catalog"]), "encrypted_metadata")
    result["ddl_triggers"] = right["ddl_triggers"]
    # Complete security catalogs: DO NOT inherit the C3 actor exclusion.
    result["principals"] = records(
        cursor,
        """SELECT name,type_desc,
      default_schema_name,authentication_type_desc,CONVERT(varchar(170),sid,2) AS sid
      FROM sys.database_principals ORDER BY name""",
    )
    result["all_permissions"] = records(
        cursor,
        """SELECT p.class_desc,
      p.permission_name,p.state_desc,USER_NAME(p.grantee_principal_id) AS grantee,
      USER_NAME(p.grantor_principal_id) AS grantor,p.minor_id,
      CASE p.class WHEN 0 THEN N'<database>'
       WHEN 1 THEN OBJECT_SCHEMA_NAME(p.major_id)+N'.'+OBJECT_NAME(p.major_id)
       WHEN 3 THEN SCHEMA_NAME(p.major_id)
       WHEN 4 THEN USER_NAME(p.major_id)
       ELSE CONVERT(nvarchar(20),p.major_id) END AS target
      FROM sys.database_permissions p ORDER BY grantee,p.class_desc,target,
       p.minor_id,p.permission_name,p.state_desc""",
    )
    result["role_membership"] = records(
        cursor,
        """SELECT USER_NAME(role_principal_id)
      AS role_name,USER_NAME(member_principal_id) AS member_name
      FROM sys.database_role_members ORDER BY role_name,member_name""",
    )
    result["dependencies"] = records(
        cursor,
        """SELECT
      OBJECT_SCHEMA_NAME(referencing_id) AS schema_name,
      OBJECT_NAME(referencing_id) AS object_name,referencing_minor_id,
      referenced_class_desc,referenced_server_name,referenced_database_name,
      referenced_schema_name,referenced_entity_name,referenced_minor_id,
      is_schema_bound_reference,is_caller_dependent,is_ambiguous
      FROM sys.sql_expression_dependencies
      ORDER BY schema_name,object_name,referencing_minor_id,referenced_class_desc,
       referenced_server_name,referenced_database_name,referenced_schema_name,
       referenced_entity_name,referenced_minor_id""",
    )
    result["synonyms"] = records(
        cursor,
        """SELECT SCHEMA_NAME(schema_id) AS
      schema_name,name,base_object_name FROM sys.synonyms ORDER BY schema_name,name""",
    )
    result["user_types"] = records(
        cursor,
        """SELECT SCHEMA_NAME(schema_id) AS
      schema_name,name,is_table_type,is_assembly_type,max_length,precision,scale,
      is_nullable FROM sys.types WHERE is_user_defined=1 ORDER BY schema_name,name""",
    )
    return result


def canonical(shape, actor_sid):
    """Only called after exact direct/effective C7 ACL and SID verification."""
    result = {**shape, "principals": [dict(p) for p in shape["principals"]]}
    actor = [p for p in result["principals"] if p["name"] == ACTOR]
    require(len(actor) == 1 and actor[0]["sid"] == actor_sid, "actor_sid_changed")
    actor[0]["sid"] = "<verified-local-C7-sid>"
    return result


def protected(shape):
    """Project only the separately verified actor and exact extension namespace."""
    result = {"version": VERSION}
    for key, value in shape.items():
        if key == "version":
            continue
        result[key] = [
            row
            for row in value
            if row.get("schema_name") != "crm_channels"
            and not (key == "schemas" and row.get("name") == "crm_channels")
            and row.get("grantee") != ACTOR
            and not (key == "principals" and row.get("name") == ACTOR)
            and row.get("member_name") != ACTOR
        ]
    return result


def extension_shape(shape):
    return {
        key: [
            row
            for row in value
            if row.get("schema_name") == "crm_channels"
            or (key == "schemas" and row.get("name") == "crm_channels")
        ]
        for key, value in shape.items()
        if key != "version"
    }


def table_names(shape):
    return [
        r["schema_name"] + "." + r["name"]
        for r in shape["catalog"]
        if r["type"].strip() == "U"
    ]


def validate_extra_catalog(shape, allowed=None):
    # Names/kinds were already verified by C5's full legacy catalog signature.
    # C7 additionally freezes the synonym target, without executing that target.
    known = {
        (o["schema_name"], o["name"])
        for o in shape["objects"]
        if o["type"].strip() == "SN"
    }
    authenticated = {
        tuple(name.split("."))
        for name in (PARTITION["protected_synonyms"] if allowed is None else allowed)
    }
    actual = {(o["schema_name"], o["name"]) for o in shape["synonyms"]}
    require(
        actual == known == authenticated and len(actual) == len(shape["synonyms"]),
        "unaccepted_synonym_catalog",
    )
    require(not shape["user_types"], "unaccepted_user_types")


def data_signature(cursor, tables):
    require(set(tables) <= table_sets(True), "data_read_outside_partition")
    signatures = []
    for table in sorted(tables):
        columns = records(
            cursor,
            """SELECT name,TYPE_NAME(user_type_id) AS type_name
          FROM sys.columns WHERE object_id=OBJECT_ID(?,'U') ORDER BY column_id""",
            (table,),
        )
        require(bool(columns), "missing_digest_columns")
        supported = {
            "bigint",
            "bit",
            "binary",
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
        require(all(c["type_name"] in supported for c in columns), "unsupported_type")
        projection = ",".join(
            "CONVERT(varbinary(max)," + quote_name(c["name"]) + ")" for c in columns
        )
        name = ".".join(quote_name(part) for part in table.split("."))
        cursor.execute("SELECT " + projection + " FROM " + name)
        hashes = []
        while batch := cursor.fetchmany(1000):
            hashes.extend(hashlib.sha256(encode(list(row))).digest() for row in batch)
            require(len(hashes) <= 1000000, "private_digest_limit")
        signatures.append(
            {
                "table": table,
                "rows": len(hashes),
                "sha256": hashlib.sha256(b"".join(sorted(hashes))).hexdigest(),
            }
        )
    return {
        "tables": len(signatures),
        "rows": sum(t["rows"] for t in signatures),
        "sha256": sha(signatures),
    }


def identity_values(cursor):
    rows = records(
        cursor,
        """SELECT OBJECT_SCHEMA_NAME(object_id) AS schema_name,
      OBJECT_NAME(object_id) AS table_name,name,
      CONVERT(nvarchar(100),last_value) AS last_value FROM sys.identity_columns
      ORDER BY schema_name,table_name,name""",
    )
    preserved = set(PARTITION["academic"] + PARTITION["foundation"]) - {JOURNAL}
    return [r for r in rows if r["schema_name"] + "." + r["table_name"] in preserved]


def preservation(cursor):
    return {
        "academic": data_signature(cursor, PARTITION["academic"]),
        "business": data_signature(
            cursor, [t for t in PARTITION["foundation"] if t != JOURNAL]
        ),
        "identity_values": identity_values(cursor),
    }


def journal_binary(cursor, limit=None):
    columns = records(
        cursor,
        """SELECT name FROM sys.columns WHERE
      object_id=OBJECT_ID(N'crm_meta.MigrationJournal') ORDER BY column_id""",
    )
    projection = ",".join(
        "CONVERT(varbinary(max),"
        + quote_name(c["name"])
        + ") AS "
        + quote_name(c["name"])
        for c in columns
    )
    top = "TOP (?) " if limit is not None else ""
    return records(
        cursor,
        "SELECT " + top + projection + " FROM crm_meta.MigrationJournal "
        "ORDER BY EventId",
        (limit,) if limit is not None else (),
    )
