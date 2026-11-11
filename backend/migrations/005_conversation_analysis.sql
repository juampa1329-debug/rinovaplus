-- Continuous analysis consumer: explicit local extension; no core mutations or automatic migration.
SET XACT_ABORT ON;
IF @@TRANCOUNT <> 0 THROW 51000, 'Open transaction refused.', 1;
IF DB_NAME() COLLATE Latin1_General_100_BIN2 <> N'DBSIIE'
   OR ISNULL(CONVERT(nvarchar(128), SERVERPROPERTY('InstanceName')), N'') COLLATE Latin1_General_100_BIN2 <> N'SQLEXPRESS'
   THROW 51001, 'Unexpected database or instance.', 1;
IF (SELECT compatibility_level FROM sys.databases WHERE database_id = DB_ID()) < 130
   THROW 51002, 'SQL compatibility 130 or later required.', 1;
BEGIN TRY
    BEGIN TRANSACTION;
    DECLARE @lock int, @created bit = 0, @schema int;
    EXEC @lock = sys.sp_getapplock @Resource = N'crm.local.commit',
        @LockMode = 'Exclusive', @LockOwner = 'Transaction', @LockTimeout = 5000;
    IF @lock < 0 THROW 51003, 'Migration lock unavailable.', 1;
    IF EXISTS (SELECT 1 FROM sys.schemas WHERE LOWER(name) = N'crm_analysis'
               AND name COLLATE Latin1_General_100_BIN2 <> N'crm_analysis')
        THROW 51004, 'Schema name collision.', 1;
    IF SCHEMA_ID(N'crm') IS NULL OR SCHEMA_ID(N'crm_inbox') IS NULL
        THROW 51007, 'Required CRM source contracts absent.', 1;
    IF NOT EXISTS (SELECT 1 FROM sys.extended_properties WHERE class=3
        AND major_id=SCHEMA_ID(N'crm') AND name=N'crm.contract'
        AND CONVERT(nvarchar(128),value)=N'ADR-006-v1')
        OR NOT EXISTS (SELECT 1 FROM sys.extended_properties WHERE class=3
        AND major_id=SCHEMA_ID(N'crm_inbox') AND name=N'crm_inbox.contract'
        AND CONVERT(nvarchar(128),value)=N'inbox-v1')
        THROW 51008, 'Source contract versions differ.', 1;
    DECLARE @sourceShape TABLE(Valid bit);
    INSERT @sourceShape EXEC(N'
DECLARE @schema int = SCHEMA_ID(N''crm''), @manifest nvarchar(max), @hash
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
    SET @hash = HASHBYTES(''SHA2_256'', @manifest);
SELECT CASE WHEN @hash = (SELECT CONVERT(binary(32),value) FROM
sys.extended_properties WHERE class=3 AND major_id=@schema AND
name=N''crm.shape'') THEN 1 ELSE 0 END;
');
    INSERT @sourceShape EXEC(N'
DECLARE @schema int = SCHEMA_ID(N''crm_inbox''), @manifest nvarchar(max), @hash
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
    SET @hash = HASHBYTES(''SHA2_256'', @manifest);
SELECT CASE WHEN @hash = (SELECT CONVERT(binary(32),value) FROM
sys.extended_properties WHERE class=3 AND major_id=@schema AND
name=N''crm_inbox.shape'') THEN 1 ELSE 0 END;
');
    IF (SELECT COUNT(*) FROM @sourceShape WHERE Valid=1)<>2
        THROW 51009, 'Source fingerprints differ.', 1;
    IF NOT EXISTS (SELECT 1 FROM sys.extended_properties WHERE class=3 AND major_id=SCHEMA_ID(N'crm_events') AND name=N'crm_events.contract' AND CONVERT(nvarchar(128),value)=N'events-v1') THROW 51008, 'Event contract absent.', 1;
    DELETE @sourceShape; INSERT @sourceShape EXEC(N'
DECLARE @schema int = SCHEMA_ID(N''crm_events''), @manifest nvarchar(max), @hash
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
    SET @hash = HASHBYTES(''SHA2_256'', @manifest);
SELECT CASE WHEN @hash = (SELECT CONVERT(binary(32),value) FROM
sys.extended_properties WHERE class=3 AND major_id=@schema AND
name=N''crm_events.shape'') THEN 1 ELSE 0 END;
');
    IF NOT EXISTS (SELECT 1 FROM @sourceShape WHERE Valid=1) THROW 51008, 'Event shape differs.', 1;
    IF SCHEMA_ID(N'crm_analysis') IS NULL
    BEGIN
        EXEC(N'CREATE SCHEMA crm_analysis AUTHORIZATION dbo;');
        SET @created=1;
        CREATE TABLE crm_analysis.Policy (
            PolicyId tinyint NOT NULL CONSTRAINT PK_AnalysisPolicy PRIMARY KEY,
            Revision bigint NOT NULL, Enabled bit NOT NULL, Provider varchar(16) NOT NULL,
            Model varchar(200) NOT NULL, InputScope varchar(30) NOT NULL, ScopeAccepted bit NOT NULL,
            DailyRequests int NOT NULL, DailyOutputTokens int NOT NULL, OutputTokens int NOT NULL,
            UpdatedAt datetime2(7) NOT NULL,
            CONSTRAINT CK_AnalysisPolicy CHECK(PolicyId=1 AND Revision>0 AND Provider IN ('gemini','xai','openrouter')
                AND InputScope='redacted_messages' AND (Enabled=0 OR ScopeAccepted=1)
                AND DailyRequests BETWEEN 1 AND 10000 AND DailyOutputTokens BETWEEN 256 AND 10000000
                AND OutputTokens BETWEEN 256 AND 8192 AND OutputTokens<=DailyOutputTokens)
        );
        CREATE TABLE crm_analysis.ConversationState (
            ConversationId uniqueidentifier NOT NULL CONSTRAINT PK_AnalysisState PRIMARY KEY,
            Revision bigint NOT NULL, Generation bigint NOT NULL, Binding varchar(200) NOT NULL,
            ContextGeneration bigint NULL, ContextJson nvarchar(max) NULL, AnalyzedAt datetime2(7) NULL,
            ContextProvider varchar(16) NULL, ContextModel varchar(200) NULL,
            ContextPromptVersion varchar(40) NULL, ContextPolicyRevision bigint NULL,
            Fingerprint char(64) NULL, Status varchar(20) NOT NULL,
            LeaseToken uniqueidentifier NULL, LeaseUntil datetime2(7) NULL,
            Failures int NOT NULL, NextAttemptAt datetime2(7) NOT NULL, ErrorCode varchar(60) NULL,
            CONSTRAINT FK_AnalysisState_Conversation FOREIGN KEY(ConversationId) REFERENCES crm.Conversation(ConversationId),
            CONSTRAINT CK_AnalysisState CHECK(Revision>=0 AND Generation>0 AND Failures BETWEEN 0 AND 3
                AND Status IN ('pending','processing','current','failed','no_messages')
                AND (ContextJson IS NULL OR ISJSON(ContextJson)=1)
                AND ((Status='processing' AND LeaseToken IS NOT NULL AND LeaseUntil IS NOT NULL)
                    OR (Status<>'processing' AND LeaseToken IS NULL AND LeaseUntil IS NULL)))
        );
        CREATE TABLE crm_analysis.Receipt (
            ConversationId uniqueidentifier NOT NULL, Generation bigint NOT NULL, EventId bigint NOT NULL,
            CompletedAt datetime2(7) NOT NULL,
            CONSTRAINT PK_AnalysisReceipt PRIMARY KEY(ConversationId,Generation,EventId),
            CONSTRAINT FK_AnalysisReceipt_Conversation FOREIGN KEY(ConversationId) REFERENCES crm.Conversation(ConversationId),
            CONSTRAINT FK_AnalysisReceipt_Event FOREIGN KEY(EventId) REFERENCES crm_events.Event(EventId)
        );
        CREATE TABLE crm_analysis.Attempt (
            AttemptId uniqueidentifier NOT NULL CONSTRAINT PK_AnalysisAttempt PRIMARY KEY,
            ConversationId uniqueidentifier NOT NULL, Generation bigint NOT NULL, PolicyRevision bigint NOT NULL,
            ReservedOutputTokens int NOT NULL, Status varchar(16) NOT NULL, CreatedAt datetime2(7) NOT NULL,
            CompletedAt datetime2(7) NULL, ErrorCode varchar(60) NULL,
            CONSTRAINT FK_AnalysisAttempt_Conversation FOREIGN KEY(ConversationId) REFERENCES crm.Conversation(ConversationId),
            CONSTRAINT CK_AnalysisAttempt CHECK(ReservedOutputTokens BETWEEN 256 AND 8192
                AND Status IN ('reserved','succeeded','failed','stale','expired'))
        );
        CREATE INDEX IX_AnalysisAttempt_Day ON crm_analysis.Attempt(CreatedAt) INCLUDE(ReservedOutputTokens);
        CREATE TABLE crm_analysis.Feedback (
            FeedbackId uniqueidentifier NOT NULL CONSTRAINT PK_AnalysisFeedback PRIMARY KEY,
            ConversationId uniqueidentifier NOT NULL, SourceRevision bigint NOT NULL,
            Text nvarchar(1000) NOT NULL, CreatedAt datetime2(7) NOT NULL,
            ConsumedGeneration bigint NOT NULL CONSTRAINT DF_AnalysisFeedback_Generation DEFAULT 0,
            CONSTRAINT FK_AnalysisFeedback_Conversation FOREIGN KEY(ConversationId) REFERENCES crm.Conversation(ConversationId)
        );
        CREATE TABLE crm_analysis.Operation (
            OperationId uniqueidentifier NOT NULL CONSTRAINT PK_AnalysisOperation PRIMARY KEY,
            Action varchar(16) NOT NULL, RequestHash char(64) NOT NULL, ResponseJson nvarchar(max) NOT NULL,
            CreatedAt datetime2(7) NOT NULL,
            CONSTRAINT CK_AnalysisOperation CHECK(Action IN ('policy','retry','feedback') AND ISJSON(ResponseJson)=1)
        );
    END;
    SET @schema = SCHEMA_ID(N'crm_analysis');
    DECLARE @version nvarchar(128), @stored binary(32), @manifest nvarchar(max), @hash binary(32);
    SELECT @version = CONVERT(nvarchar(128), value) FROM sys.extended_properties
        WHERE class = 3 AND major_id = @schema AND name = N'crm_analysis.contract';
    SELECT @stored = CONVERT(binary(32), value) FROM sys.extended_properties
        WHERE class = 3 AND major_id = @schema AND name = N'crm_analysis.shape';
    IF @created = 0 AND (@version IS NULL OR @version <> N'analysis-v1' OR @stored IS NULL)
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
        EXEC sys.sp_addextendedproperty @name=N'crm_analysis.contract', @value=N'analysis-v1',
            @level0type=N'SCHEMA', @level0name=N'crm_analysis';
        EXEC sys.sp_addextendedproperty @name=N'crm_analysis.shape', @value=@hash,
            @level0type=N'SCHEMA', @level0name=N'crm_analysis';
    END;
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
