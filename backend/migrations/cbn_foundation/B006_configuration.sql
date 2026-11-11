-- Explicit SQL-C3 restored-copy unit. Runner owns the transaction.
SET XACT_ABORT ON;
IF @@TRANCOUNT <> 1 THROW 51100, 'Runner transaction required.', 1;
IF DB_NAME() IN (N'HORARIOSSIIE',N'master',N'model',N'msdb',N'tempdb')
 OR DB_NAME() COLLATE Latin1_General_100_BIN2 <> CONVERT(nvarchar(128),SESSION_CONTEXT(N'CBN_C3_TARGET')) COLLATE Latin1_General_100_BIN2
 OR SESSION_CONTEXT(N'CBN_C3_TARGET') IS NULL
 OR USER_NAME() <> N'cbn_foundation_migrator'
 THROW 51101, 'Approved restored target and migration principal required.', 1;
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
