-- Additive Inbox metadata. Existing CRM/core objects and rows remain authoritative.
SET XACT_ABORT ON;
IF DB_NAME()<>N'DBSIIE' OR CONVERT(nvarchar(128),SERVERPROPERTY('InstanceName'))<>N'SQLEXPRESS'
 THROW 51000,'Unexpected local target.',1;
IF NOT EXISTS(SELECT 1 FROM sys.extended_properties WHERE class=3 AND major_id=SCHEMA_ID(N'crm_channels') AND name=N'crm_channels.contract' AND CONVERT(nvarchar(80),value)=N'CRM-channels-v1')
 THROW 51001,'Channels migration required.',1;
IF EXISTS(SELECT 1 FROM sys.extended_properties WHERE class=3 AND major_id=SCHEMA_ID(N'crm_channels') AND name=N'crm_channels.inbox' AND CONVERT(nvarchar(80),value)=N'inbox-unified-v1')
 RETURN;
IF OBJECT_ID(N'crm_channels.ConversationProfile') IS NOT NULL OR OBJECT_ID(N'crm_channels.ConversationControl') IS NOT NULL OR OBJECT_ID(N'crm_channels.MessageRoute') IS NOT NULL
 THROW 51002,'Unrecognized existing Inbox extension.',1;
CREATE TABLE crm_channels.ConversationProfile(
 ConversationId uniqueidentifier NOT NULL PRIMARY KEY REFERENCES crm.Conversation(ConversationId),
 LeadScore tinyint NULL CHECK(LeadScore BETWEEN 0 AND 100),
 Temperature varchar(4) NULL CHECK(Temperature IN('cold','warm','hot')),
 UpdatedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME()
);
CREATE TABLE crm_channels.ConversationControl(
 ConversationId uniqueidentifier NOT NULL PRIMARY KEY REFERENCES crm.Conversation(ConversationId),
 Epoch bigint NOT NULL DEFAULT 0 CHECK(Epoch>=0),
 ReadSequence bigint NOT NULL DEFAULT 0 CHECK(ReadSequence>=0)
);
CREATE TABLE crm_channels.MessageRoute(
 MessageId uniqueidentifier NOT NULL PRIMARY KEY REFERENCES crm.Message(MessageId),
 IdentityId uniqueidentifier NOT NULL REFERENCES crm_channels.ExternalIdentity(IdentityId),
 QueueId uniqueidentifier NULL REFERENCES crm_channels.outbound_queue(QueueId),
 ActorKind varchar(8) NOT NULL CHECK(ActorKind IN('human','external','bot')),
 ControlEpoch bigint NULL CHECK(ControlEpoch>=0),
 StartedAt datetime2(7) NULL,
 CompletedAt datetime2(7) NULL,
 CHECK((ActorKind='bot' AND ControlEpoch IS NOT NULL) OR (ActorKind IN('human','external') AND ControlEpoch IS NULL))
);
CREATE UNIQUE INDEX IX_Inbox_MessageRoute_Queue ON crm_channels.MessageRoute(QueueId) WHERE QueueId IS NOT NULL;
CREATE INDEX IX_Inbox_MessageRoute_Identity ON crm_channels.MessageRoute(IdentityId,MessageId);
EXEC sys.sp_addextendedproperty @name=N'crm_channels.inbox',@value=N'inbox-unified-v1',@level0type=N'SCHEMA',@level0name=N'crm_channels';
