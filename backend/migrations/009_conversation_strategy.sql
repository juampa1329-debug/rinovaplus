-- Explicit local-only evidence plans and bounded internal autonomy. No seeds or core writes.
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
 IF SCHEMA_ID(N'crm_strategy') IS NULL
 BEGIN
  IF EXISTS(SELECT 1 FROM sys.schemas WHERE LOWER(name)=N'crm_strategy') THROW 51005, 'Schema collision.', 1;
  SET @created=1;
  EXEC(N'CREATE SCHEMA crm_strategy AUTHORIZATION dbo;');
  CREATE TABLE crm_strategy.Policy(
   ScopeKey varchar(36) NOT NULL CONSTRAINT PK_StrategyPolicy PRIMARY KEY,
   ConversationId uniqueidentifier NULL,Enabled bit NOT NULL,
   CONSTRAINT FK_StrategyPolicy_Conversation FOREIGN KEY(ConversationId) REFERENCES crm.Conversation(ConversationId),
   CONSTRAINT CK_StrategyPolicy CHECK((ScopeKey='global' AND ConversationId IS NULL)
    OR (ConversationId IS NOT NULL AND ScopeKey=LOWER(CONVERT(varchar(36),ConversationId))))
  );
  CREATE TABLE crm_strategy.EvaluationPlan(
   PlanId uniqueidentifier NOT NULL CONSTRAINT PK_StrategyPlan PRIMARY KEY,
   ConversationId uniqueidentifier NOT NULL,Generation bigint NOT NULL,AnalysisRevision bigint NOT NULL,
   Fingerprint char(64) NOT NULL,Binding varchar(300) NOT NULL,SemanticFingerprint char(64) NOT NULL,
   DocumentJson nvarchar(max) NOT NULL,Provider varchar(32) NOT NULL,Model varchar(200) NOT NULL,
   PromptVersion varchar(40) NOT NULL,PolicyRevision bigint NOT NULL,
   CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_StrategyPlan_Created DEFAULT SYSUTCDATETIME(),
   CONSTRAINT FK_StrategyPlan_Conversation FOREIGN KEY(ConversationId) REFERENCES crm.Conversation(ConversationId),
   CONSTRAINT UQ_StrategyPlan_Revision UNIQUE(ConversationId,Generation,AnalysisRevision),
   CONSTRAINT CK_StrategyPlan CHECK(Generation>0 AND AnalysisRevision>0 AND PolicyRevision>0
    AND ISJSON(DocumentJson)=1 AND LEFT(LTRIM(DocumentJson),1)=N'{')
  );
  CREATE TABLE crm_strategy.Operation(
   OperationId uniqueidentifier NOT NULL CONSTRAINT PK_StrategyOperation PRIMARY KEY NONCLUSTERED,
   Revision bigint IDENTITY(1,1) NOT NULL CONSTRAINT UQ_StrategyRevision UNIQUE CLUSTERED,
   Action varchar(20) NOT NULL,ConversationId uniqueidentifier NOT NULL,PlanId uniqueidentifier NULL,
   TaskId uniqueidentifier NULL,PayloadHash binary(32) NOT NULL,DocumentJson nvarchar(max) NOT NULL,
   Actor varchar(32) NOT NULL,CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_StrategyOperation_Created DEFAULT SYSUTCDATETIME(),
   CONSTRAINT FK_StrategyOperation_Conversation FOREIGN KEY(ConversationId) REFERENCES crm.Conversation(ConversationId),
   CONSTRAINT FK_StrategyOperation_Plan FOREIGN KEY(PlanId) REFERENCES crm_strategy.EvaluationPlan(PlanId),
   CONSTRAINT FK_StrategyOperation_Task FOREIGN KEY(TaskId) REFERENCES crm_inbox.Task(TaskId),
   CONSTRAINT CK_StrategyOperation CHECK(ISJSON(DocumentJson)=1 AND LEFT(LTRIM(DocumentJson),1)=N'{'
    AND ((Action='task_create' AND Actor='automation' AND PlanId IS NOT NULL AND TaskId IS NOT NULL)
     OR (Action='feedback' AND Actor='local-operator' AND PlanId IS NOT NULL AND TaskId IS NULL)
     OR (Action IN ('autonomy','pause') AND Actor='local-operator' AND PlanId IS NULL AND TaskId IS NULL)))
  );
  CREATE UNIQUE INDEX UX_StrategyTaskPlan ON crm_strategy.Operation(PlanId) WHERE Action='task_create';
 END;
    SET @schema = SCHEMA_ID(N'crm_strategy');
    DECLARE @version nvarchar(128), @stored binary(32), @manifest nvarchar(max), @hash binary(32);
    SELECT @version = CONVERT(nvarchar(128), value) FROM sys.extended_properties
        WHERE class = 3 AND major_id = @schema AND name = N'crm_strategy.contract';
    SELECT @stored = CONVERT(binary(32), value) FROM sys.extended_properties
        WHERE class = 3 AND major_id = @schema AND name = N'crm_strategy.shape';
    IF @created = 0 AND (@version IS NULL OR @version <> N'strategy-v1' OR @stored IS NULL)
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
        EXEC sys.sp_addextendedproperty @name=N'crm_strategy.contract', @value=N'strategy-v1',
            @level0type=N'SCHEMA', @level0name=N'crm_strategy';
        EXEC sys.sp_addextendedproperty @name=N'crm_strategy.shape', @value=@hash,
            @level0type=N'SCHEMA', @level0name=N'crm_strategy';
    END;
 COMMIT TRANSACTION;
END TRY
BEGIN CATCH
 IF XACT_STATE()<>0 ROLLBACK TRANSACTION;
 THROW;
END CATCH;
