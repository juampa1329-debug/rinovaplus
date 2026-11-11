-- SQL-C7: final 011+012 shape, empty extension, runner-owned transaction.
SET XACT_ABORT ON;
IF @@TRANCOUNT<>1 OR USER_NAME()<>N'cbn_channels_migrator_c7'
 OR SESSION_CONTEXT(N'CBN_C7_TARGET') IS NULL
 OR DB_NAME() COLLATE Latin1_General_100_BIN2 <>
 CONVERT(nvarchar(128),SESSION_CONTEXT(N'CBN_C7_TARGET')) COLLATE Latin1_General_100_BIN2
 OR LEFT(DB_NAME(),7) COLLATE Latin1_General_100_BIN2 <> N'CBN_C7_'
 THROW 51700,'Approved isolated C7 target, actor and transaction required.',1;
IF SCHEMA_ID(N'crm_channels') IS NULL
 OR EXISTS(SELECT 1 FROM sys.objects WHERE schema_id=SCHEMA_ID(N'crm_channels'))
 THROW 51701,'Prepared empty extension required.',1;
-- C7_BOUNDARY
CREATE TABLE crm_channels.Account(
 Channel varchar(12) NOT NULL CONSTRAINT PK_Channels_Account PRIMARY KEY,
 Configuration nvarchar(max) NOT NULL CONSTRAINT CK_Channels_Account_Json CHECK(ISJSON(Configuration)=1),
 State varchar(24) NOT NULL CONSTRAINT DF_Channels_Account_State DEFAULT 'configured',
 Revision int NOT NULL CONSTRAINT DF_Channels_Account_Revision DEFAULT 1,
 Capabilities nvarchar(max) NOT NULL CONSTRAINT DF_Channels_Account_Capabilities DEFAULT '{}' CONSTRAINT CK_Channels_Capabilities_Json CHECK(ISJSON(Capabilities)=1),
 LastError varchar(80) NULL, VerifiedAt datetime2(7) NULL,
 UpdatedAt datetime2(7) NOT NULL CONSTRAINT DF_Channels_Account_Updated DEFAULT SYSUTCDATETIME(),
 CONSTRAINT CK_Channels_Account_Channel CHECK(Channel IN('whatsapp','facebook','messenger','instagram','tiktok'))
);
-- C7_BOUNDARY
CREATE TABLE crm_channels.Credential(
 Channel varchar(12) NOT NULL CONSTRAINT FK_Channels_Credential_Account REFERENCES crm_channels.Account(Channel),
 Kind varchar(24) NOT NULL, KeyId varchar(32) NOT NULL,
 Nonce binary(12) NOT NULL, Ciphertext varbinary(max) NOT NULL,
 CONSTRAINT PK_Channels_Credential PRIMARY KEY(Channel,Kind)
);
-- C7_BOUNDARY
CREATE TABLE crm_channels.webhook_events(
 EventId uniqueidentifier NOT NULL CONSTRAINT PK_Channels_Webhook PRIMARY KEY,
 Provider varchar(12) NOT NULL, Digest binary(32) NOT NULL,
 Payload nvarchar(max) NOT NULL CONSTRAINT CK_Channels_Webhook_Json CHECK(ISJSON(Payload)=1),
 State varchar(16) NOT NULL CONSTRAINT DF_Channels_Webhook_State DEFAULT 'queued',
 Attempts int NOT NULL CONSTRAINT DF_Channels_Webhook_Attempts DEFAULT 0,
 DueAt datetime2(7) NOT NULL CONSTRAINT DF_Channels_Webhook_Due DEFAULT SYSUTCDATETIME(),
 LeaseId uniqueidentifier NULL, LastError varchar(80) NULL,
 ReceivedAt datetime2(7) NOT NULL CONSTRAINT DF_Channels_Webhook_Received DEFAULT SYSUTCDATETIME(),
 CONSTRAINT UQ_Channels_Webhook_Digest UNIQUE(Provider,Digest)
);
-- C7_BOUNDARY
CREATE TABLE crm_channels.ExternalIdentity(
 IdentityId uniqueidentifier NOT NULL CONSTRAINT PK_Channels_Identity PRIMARY KEY,
 Channel varchar(12) NOT NULL CONSTRAINT FK_Channels_Identity_Account REFERENCES crm_channels.Account(Channel),
 ExternalId nvarchar(128) COLLATE Latin1_General_100_BIN2 NOT NULL,
 ContactId uniqueidentifier NOT NULL CONSTRAINT FK_Channels_Identity_Contact REFERENCES crm.Contact(ContactId),
 ConversationId uniqueidentifier NOT NULL CONSTRAINT FK_Channels_Identity_Conversation REFERENCES crm.Conversation(ConversationId),
 LastIncomingAt datetime2(7) NULL,
 CONSTRAINT UQ_Channels_Identity UNIQUE(Channel,ExternalId)
);
-- C7_BOUNDARY
CREATE TABLE crm_channels.ExternalMessage(
 Channel varchar(12) NOT NULL CONSTRAINT FK_Channels_Message_Account REFERENCES crm_channels.Account(Channel),
 ExternalId nvarchar(200) COLLATE Latin1_General_100_BIN2 NOT NULL,
 MessageId uniqueidentifier NULL CONSTRAINT FK_Channels_Message_Message REFERENCES crm.Message(MessageId),
 Payload nvarchar(max) NOT NULL CONSTRAINT CK_Channels_Message_Json CHECK(ISJSON(Payload)=1),
 CONSTRAINT PK_Channels_ExternalMessage PRIMARY KEY(Channel,ExternalId)
);
-- C7_BOUNDARY
CREATE TABLE crm_channels.outbound_queue(
 QueueId uniqueidentifier NOT NULL CONSTRAINT PK_Channels_Queue PRIMARY KEY,
 Channel varchar(12) NOT NULL CONSTRAINT FK_Channels_Queue_Account REFERENCES crm_channels.Account(Channel),
 IdentityId uniqueidentifier NULL CONSTRAINT FK_Channels_Queue_Identity REFERENCES crm_channels.ExternalIdentity(IdentityId),
 MessageId uniqueidentifier NULL CONSTRAINT FK_Channels_Queue_Message REFERENCES crm.Message(MessageId),
 Payload nvarchar(max) NOT NULL CONSTRAINT CK_Channels_Queue_Json CHECK(ISJSON(Payload)=1),
 State varchar(16) NOT NULL CONSTRAINT DF_Channels_Queue_State DEFAULT 'queued',
 Attempts int NOT NULL CONSTRAINT DF_Channels_Queue_Attempts DEFAULT 0,
 DueAt datetime2(7) NOT NULL CONSTRAINT DF_Channels_Queue_Due DEFAULT SYSUTCDATETIME(),
 LeaseId uniqueidentifier NULL,
 ExternalId nvarchar(200) COLLATE Latin1_General_100_BIN2 NULL,
 LastError varchar(80) NULL,
 CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_Channels_Queue_Created DEFAULT SYSUTCDATETIME(),
 CONSTRAINT CK_Channels_Queue_State CHECK(State IN('queued','sending','sent','delivered','read','failed','uncertain'))
);
-- C7_BOUNDARY
CREATE TABLE crm_channels.social_comments(
 CommentId uniqueidentifier NOT NULL CONSTRAINT PK_Channels_Comment PRIMARY KEY,
 Channel varchar(12) NOT NULL CONSTRAINT FK_Channels_Comment_Account REFERENCES crm_channels.Account(Channel),
 ExternalId nvarchar(200) COLLATE Latin1_General_100_BIN2 NOT NULL,
 AuthorId nvarchar(128) COLLATE Latin1_General_100_BIN2 NOT NULL,
 Body nvarchar(max) NOT NULL,
 Payload nvarchar(max) NOT NULL CONSTRAINT CK_Channels_Comment_Json CHECK(ISJSON(Payload)=1),
 ReceivedAt datetime2(7) NOT NULL CONSTRAINT DF_Channels_Comment_Received DEFAULT SYSUTCDATETIME(),
 CONSTRAINT UQ_Channels_Comment UNIQUE(Channel,ExternalId)
);
-- C7_BOUNDARY
CREATE TABLE crm_channels.Audit(
 Revision bigint IDENTITY(1,1) NOT NULL CONSTRAINT PK_Channels_Audit PRIMARY KEY,
 Channel varchar(12) NOT NULL, Action varchar(40) NOT NULL, EntityId uniqueidentifier NULL,
 CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_Channels_Audit_Created DEFAULT SYSUTCDATETIME()
);
-- C7_BOUNDARY
CREATE INDEX IX_Channels_Receipt_Work ON crm_channels.webhook_events(State,DueAt);
-- C7_BOUNDARY
CREATE INDEX IX_Channels_Outbound_Work ON crm_channels.outbound_queue(State,DueAt);
-- C7_BOUNDARY
CREATE UNIQUE INDEX IX_Channels_Queue_Message ON crm_channels.outbound_queue(MessageId) WHERE MessageId IS NOT NULL;
-- C7_BOUNDARY
EXEC sys.sp_addextendedproperty @name=N'crm_channels.contract',@value=N'CRM-channels-v1',@level0type=N'SCHEMA',@level0name=N'crm_channels';
-- C7_BOUNDARY
EXEC sys.sp_addextendedproperty @name=N'crm_channels.identity_collation',@value=N'BIN2-v1',@level0type=N'SCHEMA',@level0name=N'crm_channels';
