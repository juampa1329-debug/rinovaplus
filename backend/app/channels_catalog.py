"""C8 metadata only: canonical queries, complete visibility, no row snapshots."""

from tools.crm_extension_snapshot_v2 import require
from tools.foundation_snapshot import encode, records
from tools.foundation_snapshot import metadata as legacy_metadata

VERSION = "cbn-channels-runtime-catalog-v1"


def metadata(cursor):
    require(
        cursor.execute(
            "SELECT HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','VIEW DEFINITION')"
        ).fetchval()
        == 1,
        "complete_runtime_visibility_required",
    )
    # Reuse unchanged canonical queries over BOTH historical halves. No schema
    # complement defines C7 protection; exact objects and full catalogs do.
    left = legacy_metadata(cursor, managed=True)
    right = legacy_metadata(cursor, managed=False)
    result = {key: left[key] + right[key] for key in left if key != "version"}
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
    return {
        key: sorted(value, key=encode) if key != "version" else value
        for key, value in result.items()
    }
