-- Additive admissions AI, knowledge and memory; never create/alter core tables.
SET XACT_ABORT ON;
IF DB_NAME()<>N'DBSIIE' OR CONVERT(nvarchar(128),SERVERPROPERTY('InstanceName'))<>N'SQLEXPRESS'
 THROW 51000,'Unexpected local target.',1;
IF NOT EXISTS(SELECT 1 FROM sys.extended_properties WHERE class=3 AND major_id=SCHEMA_ID(N'crm_ai') AND name=N'crm_ai.contract' AND CONVERT(nvarchar(80),value)=N'CRM-ai-v1')
 THROW 51001,'AI configuration migration required.',1;
IF OBJECT_ID(N'crm_channels.MessageRoute') IS NULL OR OBJECT_ID(N'crm_inbox.Task') IS NULL
 THROW 51001,'Inbox migrations required.',1;
IF EXISTS(SELECT 1 FROM sys.extended_properties WHERE class=3 AND major_id=SCHEMA_ID(N'crm_ai') AND name=N'crm_ai.admissions' AND CONVERT(nvarchar(80),value)=N'admissions-ai-v1') RETURN;
IF OBJECT_ID(N'crm_ai.AdmissionsPolicy') IS NOT NULL OR OBJECT_ID(N'crm_ai.KnowledgeDocument') IS NOT NULL OR OBJECT_ID(N'crm_ai.ProspectMemory') IS NOT NULL OR OBJECT_ID(N'crm_ai.ResponseJob') IS NOT NULL
 THROW 51002,'Unrecognized existing admissions objects.',1;
CREATE TABLE crm_ai.AdmissionsPolicy(
 PolicyId tinyint NOT NULL PRIMARY KEY CHECK(PolicyId=1), Revision bigint NOT NULL DEFAULT 0,
 Enabled bit NOT NULL DEFAULT 0, ActivationSequence bigint NOT NULL DEFAULT 0,
 KnowledgeRevision bigint NOT NULL DEFAULT 0, Document nvarchar(max) NOT NULL CHECK(ISJSON(Document)=1),
 UpdatedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME()
);
INSERT crm_ai.AdmissionsPolicy(PolicyId,Document) VALUES(1,N'{"primary_model":"","fallback_model":"","temperature":0.3,"system_prompt":"Orienta sobre admisiones técnicas usando exclusivamente las fuentes institucionales publicadas. Identifícate como asistente virtual y transfiere al asesor cuando falte información.","max_tokens":700}');
CREATE TABLE crm_ai.KnowledgeDocument(
 DocumentId uniqueidentifier NOT NULL PRIMARY KEY, Title nvarchar(160) NOT NULL,
 FileName nvarchar(160) NOT NULL, ContentHash binary(32) NOT NULL, ByteLength int NOT NULL CHECK(ByteLength BETWEEN 1 AND 5000000),
 State varchar(10) NOT NULL CHECK(State IN('draft','published','disabled','deleted')),
 Revision bigint NOT NULL DEFAULT 0, CreatedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
 UpdatedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME()
);
CREATE TABLE crm_ai.KnowledgeChunk(
 ChunkId uniqueidentifier NOT NULL PRIMARY KEY, DocumentId uniqueidentifier NOT NULL REFERENCES crm_ai.KnowledgeDocument(DocumentId),
 Ordinal int NOT NULL, PageNumber int NOT NULL, Body nvarchar(1800) NOT NULL,
 UNIQUE(DocumentId,Ordinal)
);
CREATE TABLE crm_ai.KnowledgeTerm(
 Term nvarchar(64) COLLATE Latin1_General_100_CI_AI NOT NULL,
 ChunkId uniqueidentifier NOT NULL REFERENCES crm_ai.KnowledgeChunk(ChunkId), Frequency smallint NOT NULL CHECK(Frequency>0),
 PRIMARY KEY(Term,ChunkId)
);
CREATE INDEX IX_KnowledgeTerm_Chunk ON crm_ai.KnowledgeTerm(ChunkId);
CREATE TABLE crm_ai.ProspectMemory(
 ConversationId uniqueidentifier NOT NULL PRIMARY KEY REFERENCES crm.Conversation(ConversationId),
 Revision bigint NOT NULL DEFAULT 0, Generation bigint NOT NULL DEFAULT 0,
 BaselineSequence bigint NOT NULL DEFAULT 0,
 Document nvarchar(max) NOT NULL DEFAULT '{}' CHECK(ISJSON(Document)=1),
 UpdatedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME()
);
CREATE TABLE crm_ai.ResponseJob(
 MessageId uniqueidentifier NOT NULL PRIMARY KEY REFERENCES crm.Message(MessageId),
 ConversationId uniqueidentifier NOT NULL REFERENCES crm.Conversation(ConversationId),
 IdentityId uniqueidentifier NOT NULL REFERENCES crm_channels.ExternalIdentity(IdentityId),
 State varchar(12) NOT NULL DEFAULT 'queued' CHECK(State IN('queued','processing','completed','cancelled','failed','handoff')),
 Attempts int NOT NULL DEFAULT 0, LeaseId uniqueidentifier NULL,
 DueAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(), CreatedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
 ResponseMessageId uniqueidentifier NULL REFERENCES crm.Message(MessageId),
 TaskId uniqueidentifier NULL REFERENCES crm_inbox.Task(TaskId),
 Result nvarchar(max) NOT NULL DEFAULT '{}' CHECK(ISJSON(Result)=1), LastError varchar(80) NULL
);
CREATE INDEX IX_AdmissionsJob_Work ON crm_ai.ResponseJob(State,DueAt);
EXEC sys.sp_addextendedproperty @name=N'crm_ai.admissions',@value=N'admissions-ai-v1',@level0type=N'SCHEMA',@level0name=N'crm_ai';
