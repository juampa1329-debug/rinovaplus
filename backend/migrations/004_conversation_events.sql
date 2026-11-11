-- Durable conversation preparation: explicit local extension; no core mutations or automatic migration.
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
    IF EXISTS (SELECT 1 FROM sys.schemas WHERE LOWER(name) = N'crm_events'
               AND name COLLATE Latin1_General_100_BIN2 <> N'crm_events')
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
    IF SCHEMA_ID(N'crm_events') IS NULL
    BEGIN
        EXEC(N'CREATE SCHEMA crm_events AUTHORIZATION dbo;');
        SET @created=1;
        CREATE TABLE crm_events.Event (
            EventId bigint IDENTITY(1,1) NOT NULL CONSTRAINT PK_Event PRIMARY KEY,
            SourceKind varchar(20) NOT NULL, SourceId uniqueidentifier NOT NULL,
            SourceRevision bigint NULL, SourceAction varchar(24) NULL,
            ConversationId uniqueidentifier NOT NULL,
            SourceOccurredAt datetime2(7) NOT NULL,
            CapturedAt datetime2(7) NOT NULL CONSTRAINT DF_Event_Captured DEFAULT SYSUTCDATETIME(),
            State varchar(12) NOT NULL CONSTRAINT DF_Event_State DEFAULT 'pending',
            Attempts int NOT NULL CONSTRAINT DF_Event_Attempts DEFAULT 0,
            TotalAttempts int NOT NULL CONSTRAINT DF_Event_Total DEFAULT 0,
            NextAttemptAt datetime2(7) NOT NULL CONSTRAINT DF_Event_Next DEFAULT SYSUTCDATETIME(),
            LeaseToken uniqueidentifier NULL, LeaseUntil datetime2(7) NULL,
            PreparedAt datetime2(7) NULL, ErrorCode varchar(40) NULL,
            CONSTRAINT UQ_Event_Source UNIQUE(SourceKind,SourceId),
            CONSTRAINT FK_Event_Conversation FOREIGN KEY(ConversationId) REFERENCES crm.Conversation(ConversationId),
            CONSTRAINT CK_Event_Source CHECK(SourceKind IN ('baseline','message','crm_operation','inbox_operation')),
            CONSTRAINT CK_Event_State CHECK(State IN ('pending','leased','prepared','failed')),
            CONSTRAINT CK_Event_Attempts CHECK(Attempts BETWEEN 0 AND 5 AND TotalAttempts>=Attempts),
            CONSTRAINT CK_Event_Lease CHECK((State='leased' AND LeaseToken IS NOT NULL AND LeaseUntil IS NOT NULL)
                OR (State<>'leased' AND LeaseToken IS NULL AND LeaseUntil IS NULL))
        );
        CREATE INDEX IX_Event_Work ON crm_events.Event(State,NextAttemptAt,EventId);
        CREATE INDEX IX_Event_Conversation ON crm_events.Event(ConversationId,EventId);
        CREATE TABLE crm_events.Preparation (
            ConversationId uniqueidentifier NOT NULL CONSTRAINT PK_Preparation PRIMARY KEY,
            LastEventId bigint NOT NULL, MessageCount bigint NOT NULL,
            LatestMessageSequence bigint NULL, SourceCrmRevision bigint NOT NULL,
            SourceInboxRevision bigint NOT NULL, PreparedAt datetime2(7) NOT NULL,
            CONSTRAINT FK_Preparation_Conversation FOREIGN KEY(ConversationId) REFERENCES crm.Conversation(ConversationId),
            CONSTRAINT FK_Preparation_Event FOREIGN KEY(LastEventId) REFERENCES crm_events.Event(EventId)
        );
        CREATE TABLE crm_events.RetryOperation (
            OperationId uniqueidentifier NOT NULL CONSTRAINT PK_EventRetry PRIMARY KEY,
            RetriedCount int NOT NULL,
            CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_EventRetry_Created DEFAULT SYSUTCDATETIME(),
            CONSTRAINT CK_EventRetry_Count CHECK(RetriedCount BETWEEN 0 AND 25)
        );
    END;
    SET @schema = SCHEMA_ID(N'crm_events');
    DECLARE @version nvarchar(128), @stored binary(32), @manifest nvarchar(max), @hash binary(32);
    SELECT @version = CONVERT(nvarchar(128), value) FROM sys.extended_properties
        WHERE class = 3 AND major_id = @schema AND name = N'crm_events.contract';
    SELECT @stored = CONVERT(binary(32), value) FROM sys.extended_properties
        WHERE class = 3 AND major_id = @schema AND name = N'crm_events.shape';
    IF @created = 0 AND (@version IS NULL OR @version <> N'events-v1' OR @stored IS NULL)
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
        EXEC sys.sp_addextendedproperty @name=N'crm_events.contract', @value=N'events-v1',
            @level0type=N'SCHEMA', @level0name=N'crm_events';
        EXEC sys.sp_addextendedproperty @name=N'crm_events.shape', @value=@hash,
            @level0type=N'SCHEMA', @level0name=N'crm_events';
    END;
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
