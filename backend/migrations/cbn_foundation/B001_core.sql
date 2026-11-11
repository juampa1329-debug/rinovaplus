-- Explicit SQL-C3 restored-copy unit. Runner owns the transaction.
SET XACT_ABORT ON;
IF @@TRANCOUNT <> 1 THROW 51100, 'Runner transaction required.', 1;
IF DB_NAME() IN (N'HORARIOSSIIE',N'master',N'model',N'msdb',N'tempdb')
 OR DB_NAME() COLLATE Latin1_General_100_BIN2 <> CONVERT(nvarchar(128),SESSION_CONTEXT(N'CBN_C3_TARGET')) COLLATE Latin1_General_100_BIN2
 OR SESSION_CONTEXT(N'CBN_C3_TARGET') IS NULL
 OR USER_NAME() <> N'cbn_foundation_migrator'
 THROW 51101, 'Approved restored target and migration principal required.', 1;
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

EXEC sys.sp_addextendedproperty @name=N'crm.contract',@value=N'CBN-foundation-B001-v1',@level0type=N'SCHEMA',@level0name=N'crm';
