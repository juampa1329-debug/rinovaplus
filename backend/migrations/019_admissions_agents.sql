-- Explicit local extension of the single Inbox agent registry. No core writes.
SET XACT_ABORT ON;
IF @@TRANCOUNT=0 THROW 51000,'Explicit transaction required.',1;
IF DB_NAME()<>N'DBSIIE' OR ISNULL(CONVERT(nvarchar(128),SERVERPROPERTY('InstanceName')),N'')<>N'SQLEXPRESS'
 THROW 51001,'Unexpected local target.',1;
IF OBJECT_ID(N'crm_inbox.Agent') IS NULL OR OBJECT_ID(N'crm_ai.ResponseJob') IS NULL
 THROW 51002,'Existing Inbox and admissions contracts required.',1;
IF SCHEMA_ID(N'crm_agents') IS NOT NULL THROW 51003,'Agents schema exists; inspect contract before changing.',1;
DECLARE @lock int;
EXEC @lock=sys.sp_getapplock @Resource=N'crm.local.commit',@LockMode='Exclusive',@LockOwner='Transaction',@LockTimeout=5000;
IF @lock<0 THROW 51004,'Migration lock unavailable.',1;
EXEC(N'CREATE SCHEMA crm_agents AUTHORIZATION dbo');
CREATE TABLE crm_agents.Stage(
 StageId uniqueidentifier NOT NULL PRIMARY KEY, ProgramId int NOT NULL,
 Name nvarchar(100) NOT NULL, EntryRule nvarchar(1000) NOT NULL, ExitRule nvarchar(1000) NOT NULL,
 EvidenceRequired nvarchar(1000) NOT NULL, Revision bigint NOT NULL CHECK(Revision>0),
 ApprovedRevision bigint NULL, ApprovedAt datetime2(7) NULL,
 UNIQUE(ProgramId,Name), UNIQUE(StageId,ProgramId), CHECK(ApprovedRevision IS NULL OR ApprovedRevision=Revision)
);
CREATE TABLE crm_agents.Profile(
 AgentId uniqueidentifier NOT NULL PRIMARY KEY REFERENCES crm_inbox.Agent(AgentId),
 Level varchar(10) NOT NULL CHECK(Level IN('guide','program','stage')),
 ParentId uniqueidentifier NULL REFERENCES crm_agents.Profile(AgentId), ProgramId int NULL,
 StageId uniqueidentifier NULL, State varchar(10) NOT NULL DEFAULT 'draft' CHECK(State IN('draft','active','paused','archived')),
 Version bigint NOT NULL CHECK(Version>0), Revision bigint NOT NULL DEFAULT 1 CHECK(Revision>0), ApprovedVersion bigint NULL,
 Document nvarchar(max) NOT NULL CHECK(ISJSON(Document)=1),
 UpdatedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
 FOREIGN KEY(StageId,ProgramId) REFERENCES crm_agents.Stage(StageId,ProgramId),
 CHECK((Level='guide' AND ParentId IS NULL AND ProgramId IS NULL AND StageId IS NULL)
 OR (Level='program' AND ParentId IS NOT NULL AND ProgramId IS NOT NULL AND StageId IS NULL)
 OR (Level='stage' AND ParentId IS NOT NULL AND ProgramId IS NOT NULL AND StageId IS NOT NULL)),
 CHECK(ParentId IS NULL OR ParentId<>AgentId), CHECK(State<>'active' OR (ApprovedVersion IS NOT NULL AND ApprovedVersion=Version))
);
CREATE UNIQUE INDEX UX_Agents_Program ON crm_agents.Profile(ProgramId) WHERE Level='program' AND State<>'archived';
CREATE UNIQUE INDEX UX_Agents_Stage ON crm_agents.Profile(StageId) WHERE Level='stage' AND State<>'archived';
CREATE UNIQUE INDEX UX_Agents_Guide ON crm_agents.Profile(Level) WHERE Level='guide' AND State<>'archived';
CREATE TABLE crm_agents.Context(
 ContextId uniqueidentifier NOT NULL PRIMARY KEY,
 ConversationId uniqueidentifier NOT NULL REFERENCES crm.Conversation(ConversationId),
 ProgramId int NOT NULL, ApplicantId int NULL, PeriodId int NULL, StageId uniqueidentifier NULL,
 Revision bigint NOT NULL CHECK(Revision>0), StageRevision bigint NULL,
 Evidence nvarchar(1000) NOT NULL, ApprovedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
 MemoryJson nvarchar(max) NOT NULL DEFAULT '{}' CHECK(ISJSON(MemoryJson)=1), BaselineSequence bigint NOT NULL,
 FOREIGN KEY(StageId,ProgramId) REFERENCES crm_agents.Stage(StageId,ProgramId),
 UNIQUE(ContextId,ConversationId), CHECK((ApplicantId IS NULL AND PeriodId IS NULL) OR (ApplicantId IS NOT NULL AND PeriodId IS NOT NULL))
);
CREATE TABLE crm_agents.SourceScope(
 DocumentId uniqueidentifier NOT NULL PRIMARY KEY REFERENCES crm_ai.KnowledgeDocument(DocumentId),
 ProgramId int NULL, StageId uniqueidentifier NULL, Owner nvarchar(100) NOT NULL,
 ValidUntil date NOT NULL, Revision bigint NOT NULL CHECK(Revision>0), DocumentRevision bigint NOT NULL, ApprovedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
 FOREIGN KEY(StageId,ProgramId) REFERENCES crm_agents.Stage(StageId,ProgramId),
 CHECK(StageId IS NULL OR ProgramId IS NOT NULL)
);
CREATE TABLE crm_agents.Assignment(
 ConversationId uniqueidentifier NOT NULL PRIMARY KEY REFERENCES crm.Conversation(ConversationId),
 Mode varchar(10) NOT NULL CHECK(Mode IN('automatic','manual','human')),
 ContextId uniqueidentifier NULL, Revision bigint NOT NULL CHECK(Revision>0),
 Reason nvarchar(1000) NOT NULL, BaselineSequence bigint NOT NULL,
 FOREIGN KEY(ContextId,ConversationId) REFERENCES crm_agents.Context(ContextId,ConversationId)
);
CREATE TABLE crm_agents.History(
 EventId bigint IDENTITY PRIMARY KEY, OperationId uniqueidentifier NOT NULL UNIQUE,
 EntityId uniqueidentifier NOT NULL, Kind varchar(24) NOT NULL, PayloadHash char(64) NOT NULL,
 Document nvarchar(max) NOT NULL CHECK(ISJSON(Document)=1), Note nvarchar(1000) NOT NULL,
 Actor varchar(30) NOT NULL DEFAULT 'local-operator', CreatedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME()
);
CREATE INDEX IX_Agents_History_Entity ON crm_agents.History(EntityId,EventId DESC);
CREATE TABLE crm_agents.Usage(
 RequestId uniqueidentifier NOT NULL PRIMARY KEY, AgentId uniqueidentifier NOT NULL REFERENCES crm_agents.Profile(AgentId),
 ChainJson nvarchar(max) NOT NULL CHECK(ISJSON(ChainJson)=1), TokensReserved int NOT NULL CHECK(TokensReserved>0),
 TokensUsed int NULL CHECK(TokensUsed>=0), State varchar(12) NOT NULL CHECK(State IN('reserved','completed','uncertain')),
 CreatedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME()
);
EXEC sys.sp_addextendedproperty @name=N'crm_agents.contract',@value=N'admissions-agents-v1',@level0type=N'SCHEMA',@level0name=N'crm_agents';
