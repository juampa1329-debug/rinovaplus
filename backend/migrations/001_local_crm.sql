-- ADR-006: explicit migration for the authorized local copy only.
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
    IF EXISTS (SELECT 1 FROM sys.schemas WHERE LOWER(name) = N'crm'
               AND name COLLATE Latin1_General_100_BIN2 <> N'crm')
        THROW 51004, 'Schema name collision.', 1;
    IF SCHEMA_ID(N'crm') IS NULL
    BEGIN
        EXEC(N'CREATE SCHEMA crm AUTHORIZATION dbo;');
        SET @created = 1;
        CREATE TABLE crm.Contact (
            ContactId uniqueidentifier NOT NULL CONSTRAINT PK_Contact PRIMARY KEY,
            Name nvarchar(100) NOT NULL, Phone nvarchar(40) NOT NULL,
            City nvarchar(100) NOT NULL, ProgramId int NULL,
            Program nvarchar(200) NOT NULL, Schedule nvarchar(100) NOT NULL,
            Stage nvarchar(60) NOT NULL, Tags nvarchar(1000) NOT NULL,
            Notes nvarchar(1000) NOT NULL, Type nvarchar(100) NOT NULL,
            Interests nvarchar(300) NOT NULL, CustomValues nvarchar(max) NOT NULL,
            CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_Contact_CreatedAt DEFAULT SYSUTCDATETIME(),
            UpdatedAt datetime2(7) NOT NULL CONSTRAINT DF_Contact_UpdatedAt DEFAULT SYSUTCDATETIME(),
            CONSTRAINT CK_Contact_Identity CHECK (LEN(LTRIM(RTRIM(Name))) > 0 OR LEN(LTRIM(RTRIM(Phone))) > 0),
            CONSTRAINT CK_Contact_Stage CHECK (LEN(LTRIM(RTRIM(Stage))) > 0),
            CONSTRAINT CK_Contact_Custom CHECK (ISJSON(CustomValues) = 1 AND LEFT(LTRIM(CustomValues), 1) = N'{')
        );
        CREATE TABLE crm.Conversation (
            ConversationId uniqueidentifier NOT NULL CONSTRAINT PK_Conversation PRIMARY KEY,
            ContactId uniqueidentifier NOT NULL CONSTRAINT UQ_Conversation_Contact UNIQUE,
            State varchar(12) NOT NULL, Priority varchar(8) NOT NULL,
            Assignee nvarchar(100) NULL, ControlMode varchar(5) NOT NULL, Unread bit NOT NULL,
            CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_Conversation_CreatedAt DEFAULT SYSUTCDATETIME(),
            UpdatedAt datetime2(7) NOT NULL CONSTRAINT DF_Conversation_UpdatedAt DEFAULT SYSUTCDATETIME(),
            CONSTRAINT FK_Conversation_Contact FOREIGN KEY (ContactId) REFERENCES crm.Contact(ContactId),
            CONSTRAINT CK_Conversation_State CHECK (State IN ('open', 'waiting', 'closed')),
            CONSTRAINT CK_Conversation_Priority CHECK (Priority IN ('low', 'normal', 'high', 'urgent')),
            CONSTRAINT CK_Conversation_Control CHECK (ControlMode IN ('human', 'ai'))
        );
        CREATE TABLE crm.Message (
            MessageId uniqueidentifier NOT NULL CONSTRAINT PK_Message PRIMARY KEY,
            ConversationId uniqueidentifier NOT NULL,
            Sequence bigint IDENTITY(1,1) NOT NULL, Body nvarchar(4000) NOT NULL,
            Direction varchar(8) NOT NULL,
            CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_Message_CreatedAt DEFAULT SYSUTCDATETIME(),
            CONSTRAINT FK_Message_Conversation FOREIGN KEY (ConversationId) REFERENCES crm.Conversation(ConversationId),
            CONSTRAINT CK_Message_Body CHECK (LEN(LTRIM(RTRIM(Body))) > 0),
            CONSTRAINT CK_Message_Direction CHECK (Direction IN ('incoming', 'outgoing'))
        );
        CREATE UNIQUE INDEX IX_Message_Conversation_Sequence ON crm.Message(ConversationId, Sequence);
        CREATE TABLE crm.Operation (
            OperationId uniqueidentifier NOT NULL CONSTRAINT PK_Operation PRIMARY KEY NONCLUSTERED,
            Revision bigint IDENTITY(1,1) NOT NULL CONSTRAINT UQ_Operation_Revision UNIQUE CLUSTERED,
            Action varchar(24) NOT NULL, PayloadHash binary(32) NOT NULL,
            ContactId uniqueidentifier NOT NULL, ConversationId uniqueidentifier NOT NULL,
            MessageId uniqueidentifier NULL, Actor varchar(32) NOT NULL,
            CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_Operation_CreatedAt DEFAULT SYSUTCDATETIME(),
            CONSTRAINT FK_Operation_Contact FOREIGN KEY (ContactId) REFERENCES crm.Contact(ContactId),
            CONSTRAINT FK_Operation_Conversation FOREIGN KEY (ConversationId) REFERENCES crm.Conversation(ConversationId),
            CONSTRAINT FK_Operation_Message FOREIGN KEY (MessageId) REFERENCES crm.Message(MessageId),
            CONSTRAINT CK_Operation_Action CHECK (Action IN ('create_contact', 'edit_contact', 'update_conversation', 'add_message')),
            CONSTRAINT CK_Operation_Message CHECK ((Action = 'add_message' AND MessageId IS NOT NULL) OR (Action <> 'add_message' AND MessageId IS NULL)),
            CONSTRAINT CK_Operation_Actor CHECK (Actor = 'local-operator')
        );
    END;
    SET @schema = SCHEMA_ID(N'crm');
    DECLARE @version nvarchar(128), @stored binary(32), @manifest nvarchar(max), @hash binary(32);
    SELECT @version = CONVERT(nvarchar(128), value) FROM sys.extended_properties
        WHERE class = 3 AND major_id = @schema AND name = N'crm.contract';
    SELECT @stored = CONVERT(binary(32), value) FROM sys.extended_properties
        WHERE class = 3 AND major_id = @schema AND name = N'crm.shape';
    IF @created = 0 AND (@version IS NULL OR @version <> N'ADR-006-v1' OR @stored IS NULL)
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
        EXEC sys.sp_addextendedproperty @name=N'crm.contract', @value=N'ADR-006-v1',
            @level0type=N'SCHEMA', @level0name=N'crm';
        EXEC sys.sp_addextendedproperty @name=N'crm.shape', @value=@hash,
            @level0type=N'SCHEMA', @level0name=N'crm';
    END;
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
