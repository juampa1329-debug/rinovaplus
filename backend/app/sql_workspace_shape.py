"""Read-only ADR-006 fingerprint from the approved migration."""

SHAPE_SQL = """
DECLARE @schema int = SCHEMA_ID(N'crm'), @manifest nvarchar(max), @hash
binary(32);
    SET @manifest = (
        SELECT USER_NAME(s.principal_id) AS schema_owner,
          (SELECT o.name, o.type, OBJECT_DEFINITION(o.object_id) AS definition,
                  cc.is_disabled, cc.is_not_trusted
           FROM sys.objects o LEFT JOIN sys.check_constraints cc ON cc.object_id
= o.object_id
           WHERE o.schema_id = @schema ORDER BY o.name FOR JSON PATH) AS
objects,
          (SELECT OBJECT_NAME(c.object_id) AS object_name, c.name, c.column_id,
                  TYPE_NAME(c.user_type_id) AS type_name, c.max_length,
c.precision, c.scale,
                  c.is_nullable, c.is_identity, c.collation_name,
                  CONVERT(nvarchar(128), ic.seed_value) AS identity_seed,
                  CONVERT(nvarchar(128), ic.increment_value) AS
identity_increment
           FROM sys.columns c JOIN sys.objects o ON o.object_id = c.object_id
           LEFT JOIN sys.identity_columns ic ON ic.object_id = c.object_id AND
ic.column_id = c.column_id
           WHERE o.schema_id = @schema ORDER BY o.name, c.column_id FOR JSON
PATH) AS columns,
          (SELECT o.name AS object_name, i.name, i.type, i.is_unique,
i.is_primary_key,
                  i.is_unique_constraint, i.is_disabled, i.filter_definition,
                  c.name AS column_name, ic.key_ordinal, ic.is_descending_key,
ic.is_included_column
           FROM sys.indexes i JOIN sys.objects o ON o.object_id = i.object_id
           LEFT JOIN sys.index_columns ic ON ic.object_id = i.object_id AND
ic.index_id = i.index_id
           LEFT JOIN sys.columns c ON c.object_id = ic.object_id AND c.column_id
= ic.column_id
           WHERE o.schema_id = @schema ORDER BY o.name, i.name,
ic.index_column_id FOR JSON PATH) AS indexes,
          (SELECT fk.name, OBJECT_NAME(fk.parent_object_id) AS source_table,
                  COL_NAME(fc.parent_object_id, fc.parent_column_id) AS
source_column,
                  OBJECT_SCHEMA_NAME(fc.referenced_object_id) AS target_schema,
                  OBJECT_NAME(fc.referenced_object_id) AS target_table,
                  COL_NAME(fc.referenced_object_id, fc.referenced_column_id) AS
target_column,
                  fk.delete_referential_action, fk.update_referential_action,
fk.is_disabled, fk.is_not_trusted
           FROM sys.foreign_keys fk JOIN sys.foreign_key_columns fc ON
fc.constraint_object_id = fk.object_id
           WHERE fk.schema_id = @schema ORDER BY fk.name,
fc.constraint_column_id FOR JSON PATH) AS relations
        FROM sys.schemas s WHERE s.schema_id = @schema FOR JSON PATH,
WITHOUT_ARRAY_WRAPPER
    );
    SET @hash = HASHBYTES('SHA2_256', @manifest);
SELECT CASE WHEN @hash = (SELECT CONVERT(binary(32),value) FROM
sys.extended_properties WHERE class=3 AND major_id=@schema AND
name=N'crm.shape') THEN 1 ELSE 0 END;
"""
