-- Private Inbox assets; additive metadata only, no existing CRM/core changes.
SET XACT_ABORT ON;
IF DB_NAME()<>N'DBSIIE' OR CONVERT(nvarchar(128),SERVERPROPERTY('InstanceName'))<>N'SQLEXPRESS'
 THROW 51000,'Unexpected local target.',1;
IF NOT EXISTS(SELECT 1 FROM sys.extended_properties WHERE class=3 AND major_id=SCHEMA_ID(N'crm_channels') AND name=N'crm_channels.inbox' AND CONVERT(nvarchar(80),value)=N'inbox-unified-v1')
 THROW 51001,'Inbox migration 015 required.',1;
IF EXISTS(SELECT 1 FROM sys.extended_properties WHERE class=3 AND major_id=SCHEMA_ID(N'crm_channels') AND name=N'crm_channels.media' AND CONVERT(nvarchar(80),value)=N'inbox-media-v1') RETURN;
IF OBJECT_ID(N'crm_channels.MediaAsset') IS NOT NULL THROW 51002,'Unrecognized existing media table.',1;
CREATE TABLE crm_channels.MediaAsset(
 MediaId uniqueidentifier NOT NULL PRIMARY KEY,
 ConversationId uniqueidentifier NOT NULL REFERENCES crm.Conversation(ConversationId),
 MessageId uniqueidentifier NULL REFERENCES crm.Message(MessageId),
 IdentityId uniqueidentifier NULL REFERENCES crm_channels.ExternalIdentity(IdentityId),
 Channel varchar(12) NULL REFERENCES crm_channels.Account(Channel),
 SourceKind varchar(8) NOT NULL CHECK(SourceKind IN('upload','provider')),
 State varchar(12) NOT NULL CHECK(State IN('uploading','pending','processing','ready','rejected','failed','deleted')),
 Kind varchar(8) NULL CHECK(Kind IN('image','audio','document')),
 FileName nvarchar(160) NOT NULL,
 ActualMime varchar(100) NULL, StorageKey varchar(40) NULL,
 ByteLength bigint NULL CHECK(ByteLength>0 AND ByteLength<=5000000),
 ContentHash binary(32) NULL, SourceHash binary(32) NULL,
 DurationSeconds decimal(9,3) NULL CHECK(DurationSeconds>0 AND DurationSeconds<=300),
 ProviderReference nvarchar(max) NOT NULL DEFAULT '{}' CHECK(ISJSON(ProviderReference)=1),
 Attempts int NOT NULL DEFAULT 0, DueAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
 LeaseId uniqueidentifier NULL, LastError varchar(80) NULL,
 CreatedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
 ExpiresAt datetime2(7) NULL,
 CHECK(State<>'ready' OR (ActualMime IS NOT NULL AND StorageKey IS NOT NULL AND ByteLength IS NOT NULL AND ContentHash IS NOT NULL AND Kind IS NOT NULL)),
 CHECK((SourceKind='upload' AND IdentityId IS NULL AND Channel IS NULL) OR (SourceKind='provider' AND IdentityId IS NOT NULL AND Channel IS NOT NULL))
);
CREATE UNIQUE INDEX IX_InboxMedia_Message ON crm_channels.MediaAsset(MessageId) WHERE MessageId IS NOT NULL;
CREATE INDEX IX_InboxMedia_Work ON crm_channels.MediaAsset(State,DueAt);
CREATE INDEX IX_InboxMedia_Conversation ON crm_channels.MediaAsset(ConversationId,CreatedAt);
EXEC sys.sp_addextendedproperty @name=N'crm_channels.media',@value=N'inbox-media-v1',@level0type=N'SCHEMA',@level0name=N'crm_channels';
