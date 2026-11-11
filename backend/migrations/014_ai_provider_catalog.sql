-- Expand only the local AI credential provider constraint. No configuration writes.
SET XACT_ABORT ON;
IF DB_NAME()<>N'DBSIIE' OR CONVERT(nvarchar(128),SERVERPROPERTY('InstanceName'))<>N'SQLEXPRESS'
 THROW 51000,'Unexpected local target.',1;
IF NOT EXISTS(SELECT 1 FROM sys.extended_properties WHERE class=3 AND major_id=SCHEMA_ID(N'crm_ai') AND name=N'crm_ai.contract' AND CONVERT(nvarchar(80),value)=N'CRM-ai-v1')
 THROW 51001,'Unrecognized AI schema.',1;
DECLARE @constraint sysname;
SELECT @constraint=name FROM sys.check_constraints WHERE parent_object_id=OBJECT_ID(N'crm_ai.Credential') AND definition LIKE N'%Provider%';
IF @constraint IS NULL THROW 51002,'AI credential provider constraint missing.',1;
DECLARE @sql nvarchar(max);
SET @sql=N'ALTER TABLE crm_ai.Credential DROP CONSTRAINT '+QUOTENAME(@constraint);
EXEC sys.sp_executesql @sql;
ALTER TABLE crm_ai.Credential WITH CHECK ADD CONSTRAINT CK_crm_ai_Credential_Provider
 CHECK(Provider IN('gemini','nvidia','openai','anthropic','hermes','groq','mistral','openrouter','kimi','xai','elevenlabs','google_tts','tavily','brave','serpapi'));
