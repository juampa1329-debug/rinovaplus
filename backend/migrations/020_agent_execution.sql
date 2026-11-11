-- Explicit extension of the existing local agent registry and usage ledger.
SET XACT_ABORT ON;
IF @@TRANCOUNT=0 THROW 51000,'Explicit transaction required.',1;
IF DB_NAME()<>N'DBSIIE' OR ISNULL(CONVERT(nvarchar(128),SERVERPROPERTY('InstanceName')),N'')<>N'SQLEXPRESS'
 THROW 51001,'Unexpected local target.',1;
IF OBJECT_ID(N'crm_agents.Usage') IS NULL OR OBJECT_ID(N'crm_agents.History') IS NULL
 THROW 51002,'Existing agents contract required.',1;
IF OBJECT_ID(N'crm_agents.Execution') IS NOT NULL THROW 51003,'Execution ledger already exists; inspect contract.',1;
DECLARE @lock int;
EXEC @lock=sys.sp_getapplock @Resource=N'crm.local.commit',@LockMode='Exclusive',@LockOwner='Transaction',@LockTimeout=5000;
IF @lock<0 THROW 51004,'Migration lock unavailable.',1;
CREATE TABLE crm_agents.Execution(
 RequestId uniqueidentifier NOT NULL PRIMARY KEY REFERENCES crm_agents.Usage(RequestId),
 AgentId uniqueidentifier NOT NULL REFERENCES crm_agents.Profile(AgentId),
 AgentVersion bigint NOT NULL CHECK(AgentVersion>0),
 ConversationId uniqueidentifier NULL REFERENCES crm.Conversation(ConversationId),
 Provider varchar(30) NOT NULL, ModelId nvarchar(200) NOT NULL,
 Route varchar(30) NOT NULL, Variant nvarchar(40) NOT NULL,
 FallbackUsed bit NOT NULL DEFAULT 0,
 PricingJson nvarchar(max) NOT NULL CHECK(ISJSON(PricingJson)=1),
 AttemptsJson nvarchar(max) NOT NULL DEFAULT '[]' CHECK(ISJSON(AttemptsJson)=1),
 CostReserved decimal(20,8) NULL CHECK(CostReserved>=0),
 CostEstimated decimal(20,8) NULL CHECK(CostEstimated>=0),
 InputTokens bigint NULL CHECK(InputTokens>=0), OutputTokens bigint NULL CHECK(OutputTokens>=0),
 LatencyMs bigint NULL CHECK(LatencyMs>=0),
 State varchar(12) NOT NULL CHECK(State IN('reserved','completed','failed','uncertain')),
 ErrorCode varchar(80) NULL, SourceFingerprint varchar(64) NOT NULL,
 CreatedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(), FinishedAt datetime2(7) NULL
);
CREATE INDEX IX_AgentExecution_AgentCreated ON crm_agents.Execution(AgentId,CreatedAt DESC);
CREATE INDEX IX_AgentExecution_Conversation ON crm_agents.Execution(ConversationId,CreatedAt DESC);
EXEC sys.sp_addextendedproperty @name=N'crm_agents.execution_contract',@value=N'agent-execution-v1',@level0type=N'SCHEMA',@level0name=N'crm_agents';
