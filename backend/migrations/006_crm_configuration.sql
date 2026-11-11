-- Explicit local-only definitions adopted from saved CRM values. No business seeds.
SET XACT_ABORT ON;
IF @@TRANCOUNT <> 0 THROW 51000, 'Open transaction refused.', 1;
IF DB_NAME() COLLATE Latin1_General_100_BIN2 <> N'DBSIIE'
 OR ISNULL(CONVERT(nvarchar(128),SERVERPROPERTY('InstanceName')),N'') COLLATE Latin1_General_100_BIN2 <> N'SQLEXPRESS'
 THROW 51001, 'Unexpected database or instance.', 1;
IF (SELECT compatibility_level FROM sys.databases WHERE database_id=DB_ID())<130
 THROW 51002, 'SQL compatibility 130 required.', 1;
BEGIN TRY
 BEGIN TRANSACTION;
 DECLARE @lock int, @created bit=0, @schema int;
 EXEC @lock=sys.sp_getapplock @Resource=N'crm.local.commit',@LockMode='Exclusive',@LockOwner='Transaction',@LockTimeout=5000;
 IF @lock<0 THROW 51003, 'Migration lock unavailable.', 1;
 IF NOT EXISTS(SELECT 1 FROM sys.extended_properties WHERE class=3 AND major_id=SCHEMA_ID(N'crm') AND name=N'crm.contract' AND CONVERT(nvarchar(80),value)=N'ADR-006-v1')
  THROW 51004, 'CRM source contract unavailable.', 1;
 IF SCHEMA_ID(N'crm_config') IS NULL
 BEGIN
  IF EXISTS(SELECT 1 FROM sys.schemas WHERE LOWER(name)=N'crm_config') THROW 51005, 'Schema collision.', 1;
  SET @created=1;
  EXEC(N'CREATE SCHEMA crm_config AUTHORIZATION dbo;');
  CREATE TABLE crm_config.Configuration(
   ConfigurationId int NOT NULL CONSTRAINT PK_CrmConfiguration PRIMARY KEY,
   Document nvarchar(max) NOT NULL,Revision bigint NOT NULL,
   CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_CrmConfiguration_Created DEFAULT SYSUTCDATETIME(),
   UpdatedAt datetime2(7) NOT NULL CONSTRAINT DF_CrmConfiguration_Updated DEFAULT SYSUTCDATETIME(),
   CONSTRAINT CK_CrmConfiguration CHECK(ConfigurationId=1 AND Revision>0 AND ISJSON(Document)=1)
  );
  CREATE TABLE crm_config.Operation(
   OperationId uniqueidentifier NOT NULL CONSTRAINT PK_CrmConfigOperation PRIMARY KEY,
   PayloadHash binary(32) NOT NULL,Revision bigint NOT NULL CONSTRAINT UQ_CrmConfigRevision UNIQUE,
   CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_CrmConfigOperation_Created DEFAULT SYSUTCDATETIME(),
   CONSTRAINT CK_CrmConfigOperation CHECK(Revision>1)
  );
  DECLARE @stages nvarchar(max),@tags nvarchar(max),@fields nvarchar(max),@document nvarchar(max);
  SELECT @stages=(SELECT N'used_'+LOWER(CONVERT(varchar(32),HASHBYTES('MD5',CONVERT(varbinary(max),Stage)),2)) AS [key],Stage AS label,CONVERT(int,NULL) AS probability,CONVERT(bit,1) AS active
   FROM (SELECT DISTINCT Stage COLLATE Latin1_General_100_BIN2 AS Stage FROM crm.Contact) s ORDER BY Stage FOR JSON PATH,INCLUDE_NULL_VALUES);
  SELECT @tags=N'['+COALESCE(STRING_AGG(CONVERT(nvarchar(max),N'"'+STRING_ESCAPE(value,'json')+N'"'),N','),N'')+N']'
   FROM (SELECT DISTINCT LTRIM(RTRIM(value)) COLLATE Latin1_General_100_BIN2 AS value FROM crm.Contact CROSS APPLY STRING_SPLIT(Tags,N',') WHERE LEN(LTRIM(RTRIM(value)))>0) t;
  SELECT @fields=(SELECT [key],[key] AS label,N'Text' AS [type],JSON_QUERY(N'[]') AS options,CONVERT(bit,1) AS active,CONVERT(bit,0) AS required
   FROM (SELECT DISTINCT j.[key] COLLATE Latin1_General_100_BIN2 AS [key] FROM crm.Contact c CROSS APPLY OPENJSON(c.CustomValues) j) f ORDER BY [key] FOR JSON PATH);
  SELECT @document=(SELECT JSON_QUERY(@stages) AS stages,JSON_QUERY(@tags) AS tags,JSON_QUERY(N'[]') AS inactiveTags,JSON_QUERY(@fields) AS fields FOR JSON PATH,WITHOUT_ARRAY_WRAPPER);
  INSERT crm_config.Configuration(ConfigurationId,Document,Revision) VALUES(1,@document,1);
 END;
    SET @schema = SCHEMA_ID(N'crm_config');
    DECLARE @version nvarchar(128), @stored binary(32), @manifest nvarchar(max), @hash binary(32);
    SELECT @version = CONVERT(nvarchar(128), value) FROM sys.extended_properties
        WHERE class = 3 AND major_id = @schema AND name = N'crm_config.contract';
    SELECT @stored = CONVERT(binary(32), value) FROM sys.extended_properties
        WHERE class = 3 AND major_id = @schema AND name = N'crm_config.shape';
    IF @created = 0 AND (@version IS NULL OR @version <> N'CRM-config-v1' OR @stored IS NULL)
        THROW 51005, 'Unrecognized existing schema.', 1;
    SET @manifest = (
        SELECT USER_NAME(s.principal_id) AS schema_owner,
          (SELECT o.name, o.type, OBJECT_DEFINITION(o.object_id) AS definition,
                  cc.is_disabled, cc.is_not_trusted
           FROM sys.objects o LEFT JOIN sys.check_constraints cc ON cc.object_id = o.object_id
           WHERE o.schema_id = @schema ORDER BY o.name FOR JSON PATH) AS objects,
          (SELECT OBJECT_NAME(c.object_id) AS object_name, c.name, c.column_id,
                  TYPE_NAME(c.user_type_id) AS type_name, c.max_length, c.precision, c.scale,
                  c.is_nullable, c.is_identity, c.collation_name,
                  CONVERT(nvarchar(128), ic.seed_value) AS identity_seed,
                  CONVERT(nvarchar(128), ic.increment_value) AS identity_increment
           FROM sys.columns c JOIN sys.objects o ON o.object_id = c.object_id
           LEFT JOIN sys.identity_columns ic ON ic.object_id = c.object_id AND ic.column_id = c.column_id
           WHERE o.schema_id = @schema ORDER BY o.name, c.column_id FOR JSON PATH) AS columns,
          (SELECT o.name AS object_name, i.name, i.type, i.is_unique, i.is_primary_key,
                  i.is_unique_constraint, i.is_disabled, i.filter_definition,
                  c.name AS column_name, ic.key_ordinal, ic.is_descending_key, ic.is_included_column
           FROM sys.indexes i JOIN sys.objects o ON o.object_id = i.object_id
           LEFT JOIN sys.index_columns ic ON ic.object_id = i.object_id AND ic.index_id = i.index_id
           LEFT JOIN sys.columns c ON c.object_id = ic.object_id AND c.column_id = ic.column_id
           WHERE o.schema_id = @schema ORDER BY o.name, i.name, ic.index_column_id FOR JSON PATH) AS indexes,
          (SELECT fk.name, OBJECT_NAME(fk.parent_object_id) AS source_table,
                  COL_NAME(fc.parent_object_id, fc.parent_column_id) AS source_column,
                  OBJECT_SCHEMA_NAME(fc.referenced_object_id) AS target_schema,
                  OBJECT_NAME(fc.referenced_object_id) AS target_table,
                  COL_NAME(fc.referenced_object_id, fc.referenced_column_id) AS target_column,
                  fk.delete_referential_action, fk.update_referential_action, fk.is_disabled, fk.is_not_trusted
           FROM sys.foreign_keys fk JOIN sys.foreign_key_columns fc ON fc.constraint_object_id = fk.object_id
           WHERE fk.schema_id = @schema ORDER BY fk.name, fc.constraint_column_id FOR JSON PATH) AS relations
        FROM sys.schemas s WHERE s.schema_id = @schema FOR JSON PATH, WITHOUT_ARRAY_WRAPPER
    );
    SET @hash = HASHBYTES('SHA2_256', @manifest);
    IF @created = 0 AND @stored <> @hash THROW 51006, 'Existing schema shape differs.', 1;
    IF @created = 1
    BEGIN
        EXEC sys.sp_addextendedproperty @name=N'crm_config.contract', @value=N'CRM-config-v1',
            @level0type=N'SCHEMA', @level0name=N'crm_config';
        EXEC sys.sp_addextendedproperty @name=N'crm_config.shape', @value=@hash,
            @level0type=N'SCHEMA', @level0name=N'crm_config';
    END;
 COMMIT TRANSACTION;
END TRY
BEGIN CATCH
 IF XACT_STATE()<>0 ROLLBACK TRANSACTION;
 THROW;
END CATCH;
