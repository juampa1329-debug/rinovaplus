-- Explicit expansion of the verified local copy; core and crm remain unchanged.
SET XACT_ABORT ON;
IF DB_NAME()<>N'DBSIIE' OR CONVERT(nvarchar(128),SERVERPROPERTY('InstanceName'))<>N'SQLEXPRESS'
 THROW 51000,'Unexpected local target.',1;
IF SCHEMA_ID(N'crm_ai') IS NOT NULL
BEGIN
 IF NOT EXISTS(SELECT 1 FROM sys.extended_properties WHERE class=3 AND major_id=SCHEMA_ID(N'crm_ai') AND name=N'crm_ai.contract' AND CONVERT(nvarchar(80),value)=N'CRM-ai-v1')
  THROW 51001,'Unrecognized AI schema.',1;
 RETURN;
END;
EXEC(N'CREATE SCHEMA crm_ai AUTHORIZATION dbo');
CREATE TABLE crm_ai.Configuration(
 ConfigurationId tinyint NOT NULL PRIMARY KEY CHECK(ConfigurationId=1),
 Revision int NOT NULL CHECK(Revision>=0),
 Document nvarchar(max) NOT NULL CHECK(ISJSON(Document)=1),
 UpdatedAt datetime2 NOT NULL DEFAULT SYSUTCDATETIME()
);
CREATE TABLE crm_ai.Connection(
 ConnectionId tinyint NOT NULL PRIMARY KEY CHECK(ConnectionId=1),
 Revision int NOT NULL DEFAULT 0 CHECK(Revision>=0),
 Outbound bit NOT NULL DEFAULT 0,
 UpdatedAt datetime2 NOT NULL DEFAULT SYSUTCDATETIME()
);
CREATE TABLE crm_ai.Credential(
 Provider varchar(24) COLLATE Latin1_General_100_BIN2 NOT NULL PRIMARY KEY,
 KeyId varchar(32) NOT NULL,Nonce binary(12) NOT NULL,Ciphertext varbinary(max) NOT NULL,
 UpdatedAt datetime2 NOT NULL DEFAULT SYSUTCDATETIME(),
 CHECK(Provider IN('gemini','groq','mistral','xai','openrouter','elevenlabs','google_tts','tavily','brave','serpapi'))
);
INSERT crm_ai.Connection(ConnectionId,Outbound) VALUES(1,0);
EXEC sys.sp_addextendedproperty @name=N'crm_ai.contract',@value=N'CRM-ai-v1',@level0type=N'SCHEMA',@level0name=N'crm_ai';
