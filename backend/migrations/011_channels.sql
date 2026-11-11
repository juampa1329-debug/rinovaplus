-- Explicit additive migration for the already-authorized local CRM database.
SET XACT_ABORT ON;
IF DB_NAME()<>N'DBSIIE' OR CONVERT(nvarchar(128),SERVERPROPERTY('InstanceName'))<>N'SQLEXPRESS'
 THROW 51000,'Unexpected local target.',1;
IF SCHEMA_ID(N'crm_channels') IS NOT NULL
BEGIN
 IF NOT EXISTS(SELECT 1 FROM sys.extended_properties WHERE class=3 AND major_id=SCHEMA_ID(N'crm_channels') AND name=N'crm_channels.contract' AND CONVERT(nvarchar(80),value)=N'CRM-channels-v1')
  THROW 51001,'Unrecognized channels schema.',1;
 RETURN;
END;
EXEC(N'CREATE SCHEMA crm_channels AUTHORIZATION dbo');
CREATE TABLE crm_channels.Account(
 Channel varchar(12) NOT NULL PRIMARY KEY,
 Configuration nvarchar(max) NOT NULL CHECK(ISJSON(Configuration)=1),
 State varchar(24) NOT NULL DEFAULT 'configured',
 Revision int NOT NULL DEFAULT 1,
 Capabilities nvarchar(max) NOT NULL DEFAULT '{}' CHECK(ISJSON(Capabilities)=1),
 LastError varchar(80) NULL,
 VerifiedAt datetime2 NULL, UpdatedAt datetime2 NOT NULL DEFAULT SYSUTCDATETIME(),
 CHECK(Channel IN('whatsapp','facebook','messenger','instagram','tiktok'))
);
CREATE TABLE crm_channels.Credential(
 Channel varchar(12) NOT NULL REFERENCES crm_channels.Account(Channel),
 Kind varchar(24) NOT NULL, KeyId varchar(32) NOT NULL,
 Nonce binary(12) NOT NULL, Ciphertext varbinary(max) NOT NULL,
 PRIMARY KEY(Channel,Kind)
);
CREATE TABLE crm_channels.webhook_events(
 EventId uniqueidentifier NOT NULL PRIMARY KEY, Provider varchar(12) NOT NULL,
 Digest binary(32) NOT NULL, Payload nvarchar(max) NOT NULL CHECK(ISJSON(Payload)=1),
 State varchar(16) NOT NULL DEFAULT 'queued', Attempts int NOT NULL DEFAULT 0,
 DueAt datetime2 NOT NULL DEFAULT SYSUTCDATETIME(), LeaseId uniqueidentifier NULL,
 LastError varchar(80) NULL, ReceivedAt datetime2 NOT NULL DEFAULT SYSUTCDATETIME(),
 UNIQUE(Provider,Digest)
);
CREATE INDEX IX_Channels_Receipt_Work ON crm_channels.webhook_events(State,DueAt);
CREATE TABLE crm_channels.ExternalIdentity(
 IdentityId uniqueidentifier NOT NULL PRIMARY KEY, Channel varchar(12) NOT NULL REFERENCES crm_channels.Account(Channel),
 ExternalId nvarchar(128) NOT NULL, ContactId uniqueidentifier NOT NULL REFERENCES crm.Contact(ContactId),
 ConversationId uniqueidentifier NOT NULL REFERENCES crm.Conversation(ConversationId),
 LastIncomingAt datetime2 NULL, UNIQUE(Channel,ExternalId)
);
CREATE TABLE crm_channels.ExternalMessage(
 Channel varchar(12) NOT NULL REFERENCES crm_channels.Account(Channel), ExternalId nvarchar(200) NOT NULL,
 MessageId uniqueidentifier NULL REFERENCES crm.Message(MessageId),
 Payload nvarchar(max) NOT NULL CHECK(ISJSON(Payload)=1), PRIMARY KEY(Channel,ExternalId)
);
CREATE TABLE crm_channels.outbound_queue(
 QueueId uniqueidentifier NOT NULL PRIMARY KEY, Channel varchar(12) NOT NULL REFERENCES crm_channels.Account(Channel),
 IdentityId uniqueidentifier NULL REFERENCES crm_channels.ExternalIdentity(IdentityId),
 MessageId uniqueidentifier NULL REFERENCES crm.Message(MessageId),
 Payload nvarchar(max) NOT NULL CHECK(ISJSON(Payload)=1), State varchar(16) NOT NULL DEFAULT 'queued',
 Attempts int NOT NULL DEFAULT 0, DueAt datetime2 NOT NULL DEFAULT SYSUTCDATETIME(),
 LeaseId uniqueidentifier NULL, ExternalId nvarchar(200) NULL, LastError varchar(80) NULL,
 CreatedAt datetime2 NOT NULL DEFAULT SYSUTCDATETIME(),
 CHECK(State IN('queued','sending','sent','delivered','read','failed','uncertain'))
);
CREATE INDEX IX_Channels_Outbound_Work ON crm_channels.outbound_queue(State,DueAt);
CREATE UNIQUE INDEX IX_Channels_Queue_Message ON crm_channels.outbound_queue(MessageId) WHERE MessageId IS NOT NULL;
CREATE TABLE crm_channels.social_comments(
 CommentId uniqueidentifier NOT NULL PRIMARY KEY, Channel varchar(12) NOT NULL REFERENCES crm_channels.Account(Channel),
 ExternalId nvarchar(200) NOT NULL, AuthorId nvarchar(128) NOT NULL, Body nvarchar(max) NOT NULL,
 Payload nvarchar(max) NOT NULL CHECK(ISJSON(Payload)=1), ReceivedAt datetime2 NOT NULL DEFAULT SYSUTCDATETIME(),
 UNIQUE(Channel,ExternalId)
);
CREATE TABLE crm_channels.Audit(
 Revision bigint IDENTITY PRIMARY KEY, Channel varchar(12) NOT NULL,
 Action varchar(40) NOT NULL, EntityId uniqueidentifier NULL,
 CreatedAt datetime2 NOT NULL DEFAULT SYSUTCDATETIME()
);
EXEC sys.sp_addextendedproperty @name=N'crm_channels.contract',@value=N'CRM-channels-v1',@level0type=N'SCHEMA',@level0name=N'crm_channels';
