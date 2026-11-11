-- Inbox operations: explicit local extension; no core mutations or automatic migration.
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
    IF EXISTS (SELECT 1 FROM sys.schemas WHERE LOWER(name) = N'crm_inbox'
               AND name COLLATE Latin1_General_100_BIN2 <> N'crm_inbox')
        THROW 51004, 'Schema name collision.', 1;
    IF SCHEMA_ID(N'crm') IS NULL OR OBJECT_ID(N'dbo.GEEmpleado',N'U') IS NULL
        THROW 51007, 'Required source contract absent.', 1;
    IF (SELECT COUNT(*) FROM sys.columns WHERE object_id=OBJECT_ID(N'dbo.GEEmpleado')
       AND ((name='CnsctvoEmpldo' AND TYPE_NAME(user_type_id)='int' AND is_nullable=0)
       OR (name='NmbrePrsna' AND TYPE_NAME(user_type_id)='varchar' AND max_length=20)
       OR (name='AplldosPrsna' AND TYPE_NAME(user_type_id)='varchar' AND max_length=30)
       OR (name='Actvo' AND TYPE_NAME(user_type_id)='bit' AND is_nullable=0)))<>4
       OR NOT EXISTS (SELECT 1 FROM sys.indexes i JOIN sys.index_columns ic
         ON ic.object_id=i.object_id AND ic.index_id=i.index_id
         JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
         WHERE i.object_id=OBJECT_ID(N'dbo.GEEmpleado') AND i.is_primary_key=1
         AND ic.key_ordinal=1 AND c.name='CnsctvoEmpldo')
       OR (SELECT COUNT(*) FROM sys.indexes i JOIN sys.index_columns ic
         ON ic.object_id=i.object_id AND ic.index_id=i.index_id
         WHERE i.object_id=OBJECT_ID(N'dbo.GEEmpleado') AND i.is_primary_key=1
         AND ic.key_ordinal>0)<>1
        THROW 51008, 'Employee source shape differs.', 1;
    IF SCHEMA_ID(N'crm_inbox') IS NULL
    BEGIN
        EXEC(N'CREATE SCHEMA crm_inbox AUTHORIZATION dbo;');
        SET @created = 1;
        CREATE TABLE crm_inbox.Member (
            EmployeeId int NOT NULL CONSTRAINT PK_InboxMember PRIMARY KEY,
            Enabled bit NOT NULL,
            CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_InboxMember_Created DEFAULT SYSUTCDATETIME(),
            UpdatedAt datetime2(7) NOT NULL CONSTRAINT DF_InboxMember_Updated DEFAULT SYSUTCDATETIME()
        );
        CREATE TABLE crm_inbox.Agent (
            AgentId uniqueidentifier NOT NULL CONSTRAINT PK_InboxAgent PRIMARY KEY,
            Name nvarchar(100) NOT NULL, Description nvarchar(1000) NOT NULL,
            Enabled bit NOT NULL,
            CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_InboxAgent_Created DEFAULT SYSUTCDATETIME(),
            UpdatedAt datetime2(7) NOT NULL CONSTRAINT DF_InboxAgent_Updated DEFAULT SYSUTCDATETIME(),
            CONSTRAINT CK_InboxAgent_Name CHECK(LEN(LTRIM(RTRIM(Name)))>0)
        );
        CREATE TABLE crm_inbox.Assignment (
            ConversationId uniqueidentifier NOT NULL CONSTRAINT PK_InboxAssignment PRIMARY KEY,
            HumanEmployeeId int NULL, AiAgentId uniqueidentifier NULL,
            UpdatedAt datetime2(7) NOT NULL CONSTRAINT DF_InboxAssignment_Updated DEFAULT SYSUTCDATETIME(),
            CONSTRAINT FK_InboxAssignment_Conversation FOREIGN KEY(ConversationId) REFERENCES crm.Conversation(ConversationId),
            CONSTRAINT FK_InboxAssignment_Human FOREIGN KEY(HumanEmployeeId) REFERENCES crm_inbox.Member(EmployeeId),
            CONSTRAINT FK_InboxAssignment_Agent FOREIGN KEY(AiAgentId) REFERENCES crm_inbox.Agent(AgentId)
        );
        CREATE TABLE crm_inbox.Task (
            TaskId uniqueidentifier NOT NULL CONSTRAINT PK_InboxTask PRIMARY KEY,
            ConversationId uniqueidentifier NOT NULL, Title nvarchar(120) NOT NULL,
            HumanEmployeeId int NULL, DueAt datetime2(7) NULL,
            Priority varchar(8) NOT NULL, Status varchar(12) NOT NULL,
            CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_InboxTask_Created DEFAULT SYSUTCDATETIME(),
            UpdatedAt datetime2(7) NOT NULL CONSTRAINT DF_InboxTask_Updated DEFAULT SYSUTCDATETIME(),
            CONSTRAINT FK_InboxTask_Conversation FOREIGN KEY(ConversationId) REFERENCES crm.Conversation(ConversationId),
            CONSTRAINT FK_InboxTask_Human FOREIGN KEY(HumanEmployeeId) REFERENCES crm_inbox.Member(EmployeeId),
            CONSTRAINT CK_InboxTask_Title CHECK(LEN(LTRIM(RTRIM(Title)))>0),
            CONSTRAINT CK_InboxTask_Priority CHECK(Priority IN ('low','normal','high','urgent')),
            CONSTRAINT CK_InboxTask_Status CHECK(Status IN ('pending','completed','cancelled'))
        );
        CREATE INDEX IX_InboxTask_Conversation ON crm_inbox.Task(ConversationId,CreatedAt,TaskId);
        CREATE TABLE crm_inbox.SlaPolicy (
            PolicyId tinyint NOT NULL CONSTRAINT PK_InboxSlaPolicy PRIMARY KEY,
            Enabled bit NOT NULL, ThresholdMinutes int NOT NULL,
            UpdatedAt datetime2(7) NOT NULL CONSTRAINT DF_InboxSlaPolicy_Updated DEFAULT SYSUTCDATETIME(),
            CONSTRAINT CK_InboxSlaPolicy_Single CHECK(PolicyId=1),
            CONSTRAINT CK_InboxSlaPolicy_Threshold CHECK(ThresholdMinutes BETWEEN 1 AND 525600)
        );
        CREATE TABLE crm_inbox.Operation (
            OperationId uniqueidentifier NOT NULL CONSTRAINT PK_InboxOperation PRIMARY KEY NONCLUSTERED,
            Revision bigint IDENTITY(1,1) NOT NULL CONSTRAINT UQ_InboxOperation_Revision UNIQUE CLUSTERED,
            Action varchar(20) NOT NULL, EntityKey nvarchar(100) NOT NULL,
            PayloadHash binary(32) NOT NULL, Actor varchar(32) NOT NULL,
            CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_InboxOperation_Created DEFAULT SYSUTCDATETIME(),
            CONSTRAINT CK_InboxOperation_Action CHECK(Action IN ('member','agent','assignment','task_create','task_edit','policy')),
            CONSTRAINT CK_InboxOperation_Actor CHECK(Actor='local-operator')
        );
    END;
    SET @schema = SCHEMA_ID(N'crm_inbox');
    DECLARE @version nvarchar(128), @stored binary(32), @manifest nvarchar(max), @hash binary(32);
    SELECT @version = CONVERT(nvarchar(128), value) FROM sys.extended_properties
        WHERE class = 3 AND major_id = @schema AND name = N'crm_inbox.contract';
    SELECT @stored = CONVERT(binary(32), value) FROM sys.extended_properties
        WHERE class = 3 AND major_id = @schema AND name = N'crm_inbox.shape';
    IF @created = 0 AND (@version IS NULL OR @version <> N'inbox-v1' OR @stored IS NULL)
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
        EXEC sys.sp_addextendedproperty @name=N'crm_inbox.contract', @value=N'inbox-v1',
            @level0type=N'SCHEMA', @level0name=N'crm_inbox';
        EXEC sys.sp_addextendedproperty @name=N'crm_inbox.shape', @value=@hash,
            @level0type=N'SCHEMA', @level0name=N'crm_inbox';
    END;
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
