-- New SQL2019-only release. Original source files remain frozen.
SET XACT_ABORT ON;
IF @@TRANCOUNT<>1 OR USER_NAME()<>N'cbn_sql19_migrator'
 OR CONVERT(int,SERVERPROPERTY('ProductMajorVersion'))<>15
 OR (SELECT compatibility_level FROM sys.databases WHERE database_id=DB_ID())<>150
 OR SESSION_CONTEXT(N'CBN_SQL19_TARGET') IS NULL
 OR DB_NAME() COLLATE Latin1_General_100_BIN2<>
 CONVERT(nvarchar(128),SESSION_CONTEXT(N'CBN_SQL19_TARGET')) COLLATE Latin1_General_100_BIN2
 OR LEFT(DB_NAME(),7) COLLATE Latin1_General_100_BIN2<>N'CBN_P2_'
 THROW 51900,'Approved SQL2019 target, actor and transaction required.',1;
  CREATE TABLE crm_config.Configuration(
   ConfigurationId int NOT NULL CONSTRAINT PK_CrmConfiguration PRIMARY KEY,
   Document nvarchar(max) NOT NULL,Revision bigint NOT NULL,
   CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_CrmConfiguration_Created DEFAULT SYSUTCDATETIME(),
   UpdatedAt datetime2(7) NOT NULL CONSTRAINT DF_CrmConfiguration_Updated DEFAULT SYSUTCDATETIME(),
   CONSTRAINT CK_CrmConfiguration CHECK(ConfigurationId=1 AND Revision>0 AND ISJSON(Document)=1)
  );
  CREATE TABLE crm_config.Operation(
   OperationId uniqueidentifier NOT NULL CONSTRAINT PK_CrmConfigOperation PRIMARY KEY,
   PayloadHash binary(32) NOT NULL,Revision bigint NOT NULL CONSTRAINT UQ_CrmConfigRevision UNIQUE,
   CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_CrmConfigOperation_Created DEFAULT SYSUTCDATETIME(),
   CONSTRAINT CK_CrmConfigOperation CHECK(Revision>1)
  );

IF EXISTS(SELECT 1 FROM crm.Contact)
 THROW 51102, 'Empty-contact installation required for the new configuration seed.', 1;
INSERT crm_config.Configuration(ConfigurationId,Document,Revision)
 VALUES(1,N'{"stages":[],"tags":[],"inactiveTags":[],"fields":[]}',1);
EXEC sys.sp_addextendedproperty @name=N'crm_config.contract',@value=N'CBN-foundation-B006-v1',@level0type=N'SCHEMA',@level0name=N'crm_config';
