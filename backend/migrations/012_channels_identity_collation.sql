-- Preserve opaque provider identifiers exactly; local CRM channel schema only.
SET XACT_ABORT ON;
IF DB_NAME()<>N'DBSIIE' OR CONVERT(nvarchar(128),SERVERPROPERTY('InstanceName'))<>N'SQLEXPRESS'
 THROW 51000,'Unexpected local target.',1;
IF NOT EXISTS(SELECT 1 FROM sys.extended_properties WHERE class=3 AND major_id=SCHEMA_ID(N'crm_channels') AND name=N'crm_channels.contract' AND CONVERT(nvarchar(80),value)=N'CRM-channels-v1')
 THROW 51001,'Channels migration 011 required.',1;
IF EXISTS(SELECT 1 FROM sys.extended_properties WHERE class=3 AND major_id=SCHEMA_ID(N'crm_channels') AND name=N'crm_channels.identity_collation')
BEGIN
 IF EXISTS(SELECT 1 FROM sys.columns WHERE object_id IN(OBJECT_ID(N'crm_channels.ExternalIdentity'),OBJECT_ID(N'crm_channels.ExternalMessage'),OBJECT_ID(N'crm_channels.outbound_queue'),OBJECT_ID(N'crm_channels.social_comments')) AND name IN(N'ExternalId',N'AuthorId') AND collation_name<>N'Latin1_General_100_BIN2')
  THROW 51002,'Unexpected identifier collation.',1;
 RETURN;
END;
DECLARE @statement nvarchar(max)=N'';
SELECT @statement=@statement+N'ALTER TABLE crm_channels.'+QUOTENAME(OBJECT_NAME(parent_object_id))+N' DROP CONSTRAINT '+QUOTENAME(name)+N';'
 FROM sys.key_constraints
 WHERE (parent_object_id=OBJECT_ID(N'crm_channels.ExternalIdentity') AND type='UQ')
 OR (parent_object_id=OBJECT_ID(N'crm_channels.ExternalMessage') AND type='PK')
 OR (parent_object_id=OBJECT_ID(N'crm_channels.social_comments') AND type='UQ');
EXEC sys.sp_executesql @statement;
ALTER TABLE crm_channels.ExternalIdentity ALTER COLUMN ExternalId nvarchar(128) COLLATE Latin1_General_100_BIN2 NOT NULL;
ALTER TABLE crm_channels.ExternalMessage ALTER COLUMN ExternalId nvarchar(200) COLLATE Latin1_General_100_BIN2 NOT NULL;
ALTER TABLE crm_channels.outbound_queue ALTER COLUMN ExternalId nvarchar(200) COLLATE Latin1_General_100_BIN2 NULL;
ALTER TABLE crm_channels.social_comments ALTER COLUMN ExternalId nvarchar(200) COLLATE Latin1_General_100_BIN2 NOT NULL;
ALTER TABLE crm_channels.social_comments ALTER COLUMN AuthorId nvarchar(128) COLLATE Latin1_General_100_BIN2 NOT NULL;
ALTER TABLE crm_channels.ExternalIdentity ADD CONSTRAINT UQ_Channels_Identity UNIQUE(Channel,ExternalId);
ALTER TABLE crm_channels.ExternalMessage ADD CONSTRAINT PK_Channels_ExternalMessage PRIMARY KEY(Channel,ExternalId);
ALTER TABLE crm_channels.social_comments ADD CONSTRAINT UQ_Channels_Comment UNIQUE(Channel,ExternalId);
EXEC sys.sp_addextendedproperty @name=N'crm_channels.identity_collation',@value=N'BIN2-v1',@level0type=N'SCHEMA',@level0name=N'crm_channels';
