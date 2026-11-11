-- Explicit additive local migration; never invoked on application startup.
-- The authorized runner verifies TLS/target and owns the transaction.
SET XACT_ABORT ON;
IF @@TRANCOUNT=0 THROW 51000,'Explicit caller-owned transaction required.',1;
IF DB_NAME()<>N'DBSIIE' OR ISNULL(CONVERT(nvarchar(128),SERVERPROPERTY('InstanceName')),N'')<>N'SQLEXPRESS'
 THROW 51001,'Unexpected local target.',1;
IF NOT EXISTS(SELECT 1 FROM sys.extended_properties WHERE class=3 AND major_id=SCHEMA_ID(N'crm_channels') AND name=N'crm_channels.contract' AND CONVERT(nvarchar(80),value)=N'CRM-channels-v1')
 OR OBJECT_ID(N'crm_channels.MessageRoute') IS NULL
 THROW 51002,'Recognized channels and Inbox contracts required.',1;
IF SCHEMA_ID(N'crm_marketing') IS NOT NULL THROW 51003,'Marketing schema already exists; inspect rather than overwrite.',1;
DECLARE @lock int;
EXEC @lock=sys.sp_getapplock @Resource=N'crm.local.commit',@LockMode='Exclusive',@LockOwner='Transaction',@LockTimeout=5000;
IF @lock<0 THROW 51004,'Migration lock unavailable.',1;
EXEC(N'CREATE SCHEMA crm_marketing AUTHORIZATION dbo');

CREATE TABLE crm_marketing.ChurnAssessment(
 AssessmentId uniqueidentifier NOT NULL PRIMARY KEY,
 ConversationId uniqueidentifier NOT NULL REFERENCES crm.Conversation(ConversationId),
 IdentityId uniqueidentifier NULL REFERENCES crm_channels.ExternalIdentity(IdentityId),
 AsOfUtc datetime2(7) NOT NULL, InputSequence bigint NULL CHECK(InputSequence>0),
 FormulaVersion varchar(40) NOT NULL,
 ComputedLeadScore tinyint NULL CHECK(ComputedLeadScore BETWEEN 0 AND 100),
 LeadReasonsJson nvarchar(max) NOT NULL DEFAULT '[]' CHECK(ISJSON(LeadReasonsJson)=1),
 Status varchar(16) NOT NULL CHECK(Status IN('known','unknown','not_applicable')),
 RiskScore tinyint NULL, RiskLevel varchar(16) NOT NULL,
 StageSnapshot nvarchar(60) COLLATE Latin1_General_100_BIN2 NULL,
 WaitingSinceUtc datetime2(7) NULL,
 ReasonsJson nvarchar(max) NOT NULL CHECK(ISJSON(ReasonsJson)=1 AND LEFT(LTRIM(ReasonsJson),1)=N'['),
 EvidenceJson nvarchar(max) NOT NULL CHECK(ISJSON(EvidenceJson)=1 AND LEFT(LTRIM(EvidenceJson),1)=N'{'),
 CreatedAtUtc datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
 CHECK((Status='known' AND IdentityId IS NOT NULL AND StageSnapshot IS NOT NULL AND InputSequence IS NOT NULL AND RiskScore IS NOT NULL AND RiskScore BETWEEN 0 AND 100 AND WaitingSinceUtc IS NOT NULL
   AND ((RiskScore<35 AND RiskLevel='low') OR (RiskScore BETWEEN 35 AND 69 AND RiskLevel='medium') OR (RiskScore>=70 AND RiskLevel='high')))
   OR (Status='unknown' AND RiskScore IS NULL AND RiskLevel='unknown')
   OR (Status='not_applicable' AND RiskScore IS NULL AND RiskLevel='not_applicable')),
 CHECK(WaitingSinceUtc IS NULL OR WaitingSinceUtc<=AsOfUtc),
 UNIQUE(ConversationId,IdentityId,AsOfUtc,FormulaVersion,InputSequence)
);
CREATE INDEX IX_Marketing_Churn_Recent ON crm_marketing.ChurnAssessment(ConversationId,AsOfUtc DESC);

CREATE TABLE crm_marketing.MessageTemplate(
 TemplateId uniqueidentifier NOT NULL PRIMARY KEY,
 Channel varchar(12) NOT NULL REFERENCES crm_channels.Account(Channel),
 AccountScope nvarchar(128) NOT NULL,
 AccountRevision int NOT NULL CHECK(AccountRevision>0),
 ProviderTemplateId nvarchar(128) NOT NULL,
 Name nvarchar(128) NOT NULL, Language varchar(20) NOT NULL,
 Status varchar(16) NOT NULL DEFAULT 'unknown' CHECK(Status IN('unknown','pending','approved','rejected','paused','disabled','deleted')),
 Version bigint NOT NULL CHECK(Version>0), StatusRevision bigint NOT NULL DEFAULT 0 CHECK(StatusRevision>=0),
 ComponentsJson nvarchar(max) NOT NULL CHECK(ISJSON(ComponentsJson)=1 AND LEFT(LTRIM(ComponentsJson),1)=N'['),
 SyncedAtUtc datetime2(7) NULL,
 UNIQUE(Channel,AccountScope,ProviderTemplateId,Version),
 UNIQUE(Channel,AccountScope,Name,Language,Version),
 UNIQUE(TemplateId,Version,Channel,AccountScope),
 CHECK(LEN(LTRIM(RTRIM(AccountScope)))>0 AND LEN(LTRIM(RTRIM(Name)))>0 AND LEN(Language)>0)
);

CREATE TABLE crm_marketing.ContactConsent(
 ConsentId uniqueidentifier NOT NULL PRIMARY KEY,
 IdentityId uniqueidentifier NOT NULL REFERENCES crm_channels.ExternalIdentity(IdentityId),
 Channel varchar(12) NOT NULL REFERENCES crm_channels.Account(Channel), AccountScope nvarchar(128) NOT NULL,
 Purpose varchar(24) NOT NULL CHECK(Purpose IN('marketing','service')),
 Status varchar(10) NOT NULL DEFAULT 'unknown' CHECK(Status IN('unknown','granted','revoked','expired')),
 Version bigint NOT NULL CHECK(Version>0), RevokesVersion bigint NULL,
 EvidenceJson nvarchar(max) NOT NULL CHECK(ISJSON(EvidenceJson)=1 AND LEFT(LTRIM(EvidenceJson),1)=N'{'),
 DecisionAtUtc datetime2(7) NULL, ExpiresAtUtc datetime2(7) NULL,
 CreatedAtUtc datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
 UNIQUE(IdentityId,Channel,AccountScope,Purpose,Version),
 UNIQUE(ConsentId,Version),
 FOREIGN KEY(IdentityId,Channel,AccountScope,Purpose,RevokesVersion)
  REFERENCES crm_marketing.ContactConsent(IdentityId,Channel,AccountScope,Purpose,Version),
 CHECK(RevokesVersion IS NULL OR (Status='revoked' AND RevokesVersion<Version)),
 CHECK(Status='unknown' OR DecisionAtUtc IS NOT NULL),
 CHECK(ExpiresAtUtc IS NULL OR (DecisionAtUtc IS NOT NULL AND ExpiresAtUtc>DecisionAtUtc))
);
CREATE INDEX IX_Marketing_Consent_Current ON crm_marketing.ContactConsent(IdentityId,Channel,AccountScope,Purpose,Version DESC);

CREATE TABLE crm_marketing.RemarketingRule(
 RuleId uniqueidentifier NOT NULL PRIMARY KEY, Name nvarchar(160) NOT NULL,
 StageValue nvarchar(60) COLLATE Latin1_General_100_BIN2 NOT NULL,
 Channel varchar(12) NULL REFERENCES crm_channels.Account(Channel), AccountScope nvarchar(128) NULL,
 TemplateId uniqueidentifier NULL, TemplateVersion bigint NULL,
 InactivityDays smallint NOT NULL CHECK(InactivityDays BETWEEN 1 AND 3650),
 CooldownHours int NOT NULL CHECK(CooldownHours BETWEEN 1 AND 87600),
 MinimumRisk tinyint NOT NULL DEFAULT 70 CHECK(MinimumRisk BETWEEN 0 AND 100),
 Enabled bit NOT NULL DEFAULT 0, Revision bigint NOT NULL DEFAULT 0 CHECK(Revision>=0),
 NextEvaluationAtUtc datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
 CreatedAtUtc datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(), UpdatedAtUtc datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
 FOREIGN KEY(TemplateId,TemplateVersion,Channel,AccountScope)
  REFERENCES crm_marketing.MessageTemplate(TemplateId,Version,Channel,AccountScope),
 CHECK(LEN(LTRIM(RTRIM(StageValue)))>0),
 CHECK((TemplateId IS NULL AND TemplateVersion IS NULL) OR (TemplateId IS NOT NULL AND TemplateVersion IS NOT NULL)),
 CHECK(Enabled=0 OR (TemplateId IS NOT NULL AND Channel IS NOT NULL AND AccountScope IS NOT NULL))
);

-- One shared reservation boundary per external account, across every campaign.
CREATE TABLE crm_marketing.AccountCadence(
 Channel varchar(12) NOT NULL REFERENCES crm_channels.Account(Channel), AccountScope nvarchar(128) NOT NULL,
 MinIntervalSeconds int NOT NULL CHECK(MinIntervalSeconds BETWEEN 1 AND 86400),
 DailyRecipientLimit int NOT NULL CHECK(DailyRecipientLimit BETWEEN 1 AND 100000),
 WindowStartedAtUtc datetime2(7) NOT NULL, ReservedInWindow int NOT NULL DEFAULT 0 CHECK(ReservedInWindow>=0),
 NextAllowedAtUtc datetime2(7) NOT NULL, Revision bigint NOT NULL DEFAULT 0 CHECK(Revision>=0),
 LeaseId uniqueidentifier NULL, LeaseUntilUtc datetime2(7) NULL,
 PRIMARY KEY(Channel,AccountScope),
 CHECK((LeaseId IS NULL AND LeaseUntilUtc IS NULL) OR (LeaseId IS NOT NULL AND LeaseUntilUtc IS NOT NULL))
);

CREATE TABLE crm_marketing.Campaign(
 CampaignId uniqueidentifier NOT NULL PRIMARY KEY, Name nvarchar(160) NOT NULL,
 Kind varchar(12) NOT NULL CHECK(Kind IN('bulk','remarketing')),
 Status varchar(12) NOT NULL DEFAULT 'draft' CHECK(Status IN('draft','scheduled','running','paused','completed','cancelled')),
 Channel varchar(12) NULL, AccountScope nvarchar(128) NULL,
 TemplateId uniqueidentifier NULL, TemplateVersion bigint NULL,
 RuleId uniqueidentifier NULL REFERENCES crm_marketing.RemarketingRule(RuleId),
 SegmentJson nvarchar(max) NOT NULL CHECK(ISJSON(SegmentJson)=1 AND LEFT(LTRIM(SegmentJson),1)=N'{'),
 ScheduledAtUtc datetime2(7) NULL, PausedAtUtc datetime2(7) NULL, LastPreparedAtUtc datetime2(7) NULL,
 Revision bigint NOT NULL DEFAULT 0 CHECK(Revision>=0), InclusionEpoch bigint NOT NULL DEFAULT 0 CHECK(InclusionEpoch>=0),
 CreatedAtUtc datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(), UpdatedAtUtc datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
 FOREIGN KEY(Channel,AccountScope) REFERENCES crm_marketing.AccountCadence(Channel,AccountScope),
 FOREIGN KEY(TemplateId,TemplateVersion,Channel,AccountScope)
  REFERENCES crm_marketing.MessageTemplate(TemplateId,Version,Channel,AccountScope),
 UNIQUE(CampaignId,Channel,AccountScope),
 CHECK((Kind='bulk' AND RuleId IS NULL) OR (Kind='remarketing' AND RuleId IS NOT NULL)),
 CHECK((TemplateId IS NULL AND TemplateVersion IS NULL) OR (TemplateId IS NOT NULL AND TemplateVersion IS NOT NULL)),
 CHECK(Status NOT IN('scheduled','running') OR (ScheduledAtUtc IS NOT NULL AND TemplateId IS NOT NULL AND Channel IS NOT NULL AND AccountScope IS NOT NULL))
);
CREATE INDEX IX_Marketing_Campaign_Due ON crm_marketing.Campaign(Status,ScheduledAtUtc);

-- This single lifecycle row is also enrollment; no second outbox or flow table.
CREATE TABLE crm_marketing.CampaignRecipient(
 RecipientId uniqueidentifier NOT NULL PRIMARY KEY,
 CampaignId uniqueidentifier NOT NULL, Channel varchar(12) NOT NULL, AccountScope nvarchar(128) NULL,
 IdentityId uniqueidentifier NOT NULL REFERENCES crm_channels.ExternalIdentity(IdentityId),
 ContactId uniqueidentifier NOT NULL REFERENCES crm.Contact(ContactId),
 ConversationId uniqueidentifier NOT NULL REFERENCES crm.Conversation(ConversationId),
 Status varchar(12) NOT NULL DEFAULT 'pending'
  CHECK(Status IN('pending','prepared','blocked','leased','queued','sent','delivered','read','failed','uncertain','cancelled')),
 QueueId uniqueidentifier NULL REFERENCES crm_channels.outbound_queue(QueueId),
 ConsentId uniqueidentifier NULL, ConsentVersion bigint NULL,
 CampaignRevision bigint NOT NULL CHECK(CampaignRevision>=0), RuleRevision bigint NULL CHECK(RuleRevision>=0),
 AccountRevision int NOT NULL CHECK(AccountRevision>0), ControlEpoch bigint NOT NULL CHECK(ControlEpoch>=0),
 InclusionEpoch bigint NOT NULL CHECK(InclusionEpoch>=0), InputSequence bigint NOT NULL CHECK(InputSequence>=0),
 EvidenceJson nvarchar(max) NOT NULL CHECK(ISJSON(EvidenceJson)=1 AND LEFT(LTRIM(EvidenceJson),1)=N'{'),
 DueAtUtc datetime2(7) NOT NULL, Attempts int NOT NULL DEFAULT 0 CHECK(Attempts BETWEEN 0 AND 20),
 LeaseId uniqueidentifier NULL, LeaseUntilUtc datetime2(7) NULL,
 LastError varchar(80) NULL,
 CreatedAtUtc datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(), UpdatedAtUtc datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
 FOREIGN KEY(CampaignId) REFERENCES crm_marketing.Campaign(CampaignId),
 FOREIGN KEY(CampaignId,Channel,AccountScope) REFERENCES crm_marketing.Campaign(CampaignId,Channel,AccountScope),
 FOREIGN KEY(ConsentId,ConsentVersion) REFERENCES crm_marketing.ContactConsent(ConsentId,Version),
 UNIQUE(CampaignId,IdentityId),
 CHECK((ConsentId IS NULL AND ConsentVersion IS NULL) OR (ConsentId IS NOT NULL AND ConsentVersion IS NOT NULL)),
 CHECK(Status NOT IN('queued','sent','delivered','read','uncertain') OR (QueueId IS NOT NULL AND ConsentId IS NOT NULL)),
 CHECK((Status='leased' AND LeaseId IS NOT NULL AND LeaseUntilUtc IS NOT NULL)
  OR (Status<>'leased' AND LeaseId IS NULL AND LeaseUntilUtc IS NULL))
);
CREATE UNIQUE INDEX IX_Marketing_Recipient_Queue ON crm_marketing.CampaignRecipient(QueueId) WHERE QueueId IS NOT NULL;
CREATE INDEX IX_Marketing_Recipient_Due ON crm_marketing.CampaignRecipient(Status,DueAtUtc);
CREATE INDEX IX_Marketing_Recipient_Identity ON crm_marketing.CampaignRecipient(IdentityId,UpdatedAtUtc DESC);
CREATE TABLE crm_marketing.EvaluationRun(
 RunId uniqueidentifier NOT NULL PRIMARY KEY,
 Kind varchar(16) NOT NULL CHECK(Kind IN('predictions','remarketing','preparation')),
 TriggerKind varchar(8) NOT NULL CHECK(TriggerKind IN('manual','worker')),
 RuleId uniqueidentifier NULL REFERENCES crm_marketing.RemarketingRule(RuleId),
 CampaignId uniqueidentifier NULL REFERENCES crm_marketing.Campaign(CampaignId),
 State varchar(12) NOT NULL DEFAULT 'queued' CHECK(State IN('queued','processing','completed','failed')),
 DueAtUtc datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(), RequestedAtUtc datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
 StartedAtUtc datetime2(7) NULL, CompletedAtUtc datetime2(7) NULL,
 LeaseId uniqueidentifier NULL, LeaseUntilUtc datetime2(7) NULL, Attempts int NOT NULL DEFAULT 0 CHECK(Attempts BETWEEN 0 AND 3),
 CountsJson nvarchar(max) NOT NULL DEFAULT '{}' CHECK(ISJSON(CountsJson)=1), LastError varchar(80) NULL
);
CREATE INDEX IX_Marketing_Run_Due ON crm_marketing.EvaluationRun(State,DueAtUtc);
ALTER TABLE crm_marketing.ChurnAssessment ADD RunId uniqueidentifier NULL REFERENCES crm_marketing.EvaluationRun(RunId);
CREATE TABLE crm_marketing.Policy(
 PolicyId tinyint NOT NULL PRIMARY KEY CHECK(PolicyId=1), Revision bigint NOT NULL DEFAULT 0 CHECK(Revision>=0),
 StageWeightsJson nvarchar(max) NOT NULL DEFAULT '{}' CHECK(ISJSON(StageWeightsJson)=1),
 EvaluationEnabled bit NOT NULL DEFAULT 1, IntervalMinutes int NOT NULL DEFAULT 60 CHECK(IntervalMinutes BETWEEN 1 AND 1440),
 NextRunAtUtc datetime2(7) NOT NULL DEFAULT DATEADD(minute,60,SYSUTCDATETIME()), UpdatedAtUtc datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME()
);
INSERT crm_marketing.Policy(PolicyId) VALUES(1);
EXEC sys.sp_addextendedproperty @name=N'crm_marketing.contract',@value=N'campaigns-v1',@level0type=N'SCHEMA',@level0name=N'crm_marketing';
