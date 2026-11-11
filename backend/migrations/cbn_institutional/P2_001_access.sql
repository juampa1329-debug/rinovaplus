-- Explicit P2 migration. The reviewed runner owns the transaction and target.
SET XACT_ABORT ON;
IF @@TRANCOUNT<>1 OR USER_NAME()<>N'cbn_access_migrator_p2'
 OR SESSION_CONTEXT(N'CBN_P2_TARGET') IS NULL
 OR DB_NAME() COLLATE Latin1_General_100_BIN2<>
 CONVERT(nvarchar(128),SESSION_CONTEXT(N'CBN_P2_TARGET')) COLLATE Latin1_General_100_BIN2
 OR LEFT(DB_NAME(),7) COLLATE Latin1_General_100_BIN2<>N'CBN_P2_'
 THROW 51800,'Reviewed isolated P2 target and actor required.',1;
IF EXISTS(SELECT 1 FROM sys.objects WHERE schema_id=SCHEMA_ID(N'crm_access'))
 THROW 51801,'Empty institutional schema required.',1;
CREATE TABLE crm_access.Institution(
 InstitutionId uniqueidentifier NOT NULL CONSTRAINT PK_P2_Institution PRIMARY KEY,
 BootstrapHash binary(32) NULL,InitializedAt datetime2(7) NULL,
 CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_P2_Institution DEFAULT SYSUTCDATETIME(),
 CONSTRAINT FK_P2_Institution FOREIGN KEY(InstitutionId) REFERENCES crm_channels2.Context(InstitutionId)
);
CREATE TABLE crm_access.Role(
 InstitutionId uniqueidentifier NOT NULL,RoleKey varchar(64) COLLATE Latin1_General_100_BIN2 NOT NULL,
 Name nvarchar(100) NOT NULL,Actions nvarchar(max) NOT NULL,Protected bit NOT NULL,
 Active bit NOT NULL,Revision bigint NOT NULL,
 CONSTRAINT PK_P2_Role PRIMARY KEY(InstitutionId,RoleKey),
 CONSTRAINT FK_P2_Role FOREIGN KEY(InstitutionId) REFERENCES crm_access.Institution(InstitutionId),
 CONSTRAINT CK_P2_Role CHECK(ISJSON(Actions)=1 AND LEFT(LTRIM(Actions),1)=N'[' AND Revision>0 AND LEN(Name)>0)
);
CREATE TABLE crm_access.AccessUser(
 InstitutionId uniqueidentifier NOT NULL,UserId uniqueidentifier NOT NULL,
 Login nvarchar(254) NOT NULL,NormalizedLogin nvarchar(254) COLLATE Latin1_General_100_BIN2 NOT NULL,
 DisplayName nvarchar(120) NOT NULL,Profile nvarchar(max) NOT NULL,
 PasswordHash varchar(300) NULL,RoleKey varchar(64) COLLATE Latin1_General_100_BIN2 NOT NULL,
 Active bit NOT NULL,AuthVersion bigint NOT NULL,Revision bigint NOT NULL,
 CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_P2_User_Created DEFAULT SYSUTCDATETIME(),
 UpdatedAt datetime2(7) NOT NULL CONSTRAINT DF_P2_User_Updated DEFAULT SYSUTCDATETIME(),
 CONSTRAINT PK_P2_User PRIMARY KEY(InstitutionId,UserId),
 CONSTRAINT UQ_P2_User_Login UNIQUE(InstitutionId,NormalizedLogin),
 CONSTRAINT FK_P2_User_Role FOREIGN KEY(InstitutionId,RoleKey) REFERENCES crm_access.Role(InstitutionId,RoleKey),
 CONSTRAINT CK_P2_User CHECK(ISJSON(Profile)=1 AND LEFT(LTRIM(Profile),1)=N'{' AND Revision>0 AND AuthVersion>0 AND LEN(DisplayName)>0)
);
CREATE TABLE crm_access.Session(
 InstitutionId uniqueidentifier NOT NULL,SessionId uniqueidentifier NOT NULL,UserId uniqueidentifier NOT NULL,
 TokenHash binary(32) NOT NULL,CSRFHash binary(32) NOT NULL,AuthVersion bigint NOT NULL,
 IssuedAt datetime2(7) NOT NULL,ExpiresAt datetime2(7) NOT NULL,
 RevokedAt datetime2(7) NULL,RecentAt datetime2(7) NULL,MFAAt datetime2(7) NULL,
 CONSTRAINT PK_P2_Session PRIMARY KEY(InstitutionId,SessionId),
 CONSTRAINT UQ_P2_Session_Token UNIQUE(TokenHash),
 CONSTRAINT FK_P2_Session_User FOREIGN KEY(InstitutionId,UserId) REFERENCES crm_access.AccessUser(InstitutionId,UserId),
 CONSTRAINT CK_P2_Session CHECK(ExpiresAt>IssuedAt AND AuthVersion>0)
);
CREATE INDEX IX_P2_Session_User ON crm_access.Session(InstitutionId,UserId,RevokedAt,ExpiresAt);
CREATE TABLE crm_access.Setting(
 InstitutionId uniqueidentifier NOT NULL,Section varchar(40) COLLATE Latin1_General_100_BIN2 NOT NULL,
 Document nvarchar(max) NOT NULL,Revision bigint NOT NULL,UpdatedAt datetime2(7) NOT NULL,
 UpdatedBy uniqueidentifier NULL,
 CONSTRAINT PK_P2_Setting PRIMARY KEY(InstitutionId,Section),
 CONSTRAINT FK_P2_Setting FOREIGN KEY(InstitutionId) REFERENCES crm_access.Institution(InstitutionId),
 CONSTRAINT CK_P2_Setting CHECK(ISJSON(Document)=1 AND LEFT(LTRIM(Document),1)=N'{' AND Revision>0)
);
CREATE TABLE crm_access.SettingHistory(
 InstitutionId uniqueidentifier NOT NULL,Section varchar(40) COLLATE Latin1_General_100_BIN2 NOT NULL,
 Revision bigint NOT NULL,Document nvarchar(max) NOT NULL,RecordedAt datetime2(7) NOT NULL,
 ActorId uniqueidentifier NULL,
 CONSTRAINT PK_P2_SettingHistory PRIMARY KEY(InstitutionId,Section,Revision),
 CONSTRAINT FK_P2_SettingHistory FOREIGN KEY(InstitutionId) REFERENCES crm_access.Institution(InstitutionId),
 CONSTRAINT CK_P2_SettingHistory CHECK(ISJSON(Document)=1 AND Revision>0)
);
CREATE TABLE crm_access.Secret(
 InstitutionId uniqueidentifier NOT NULL,SecretId uniqueidentifier NOT NULL,
 Scope varchar(20) NOT NULL,OwnerRef nvarchar(200) COLLATE Latin1_General_100_BIN2 NOT NULL,
 Kind varchar(40) NOT NULL,VersionNo bigint NOT NULL,KeyId varchar(32) NOT NULL,
 Nonce binary(12) NOT NULL,Ciphertext varbinary(max) NOT NULL,Hint nvarchar(20) NOT NULL,
 State varchar(12) NOT NULL,CreatedAt datetime2(7) NOT NULL,
 CONSTRAINT PK_P2_Secret PRIMARY KEY(InstitutionId,SecretId),
 CONSTRAINT UQ_P2_Secret_Version UNIQUE(InstitutionId,Scope,OwnerRef,Kind,VersionNo),
 CONSTRAINT FK_P2_Secret FOREIGN KEY(InstitutionId) REFERENCES crm_access.Institution(InstitutionId),
 CONSTRAINT CK_P2_Secret CHECK(Scope IN('provider','channel','webhook','totp') AND State IN('staged','retired') AND VersionNo>0 AND DATALENGTH(Ciphertext)>16)
);
CREATE TABLE crm_access.Factor(
 InstitutionId uniqueidentifier NOT NULL,UserId uniqueidentifier NOT NULL,
 SecretId uniqueidentifier NULL,PendingSecretId uniqueidentifier NULL,State varchar(12) NOT NULL,LastStep bigint NOT NULL,
 SetupId uniqueidentifier NULL,SetupSessionId uniqueidentifier NULL,SetupExpiresAt datetime2(7) NULL,
 SetupAttempts int NOT NULL CONSTRAINT DF_P2_Factor_Attempts DEFAULT 0,
 CONSTRAINT PK_P2_Factor PRIMARY KEY(InstitutionId,UserId),
 CONSTRAINT FK_P2_Factor_User FOREIGN KEY(InstitutionId,UserId) REFERENCES crm_access.AccessUser(InstitutionId,UserId),
 CONSTRAINT FK_P2_Factor_Secret FOREIGN KEY(InstitutionId,SecretId) REFERENCES crm_access.Secret(InstitutionId,SecretId),
 CONSTRAINT FK_P2_Factor_Pending FOREIGN KEY(InstitutionId,PendingSecretId) REFERENCES crm_access.Secret(InstitutionId,SecretId),
 CONSTRAINT CK_P2_Factor CHECK(State IN('disabled','pending','enabled') AND SetupAttempts BETWEEN 0 AND 8)
);
CREATE TABLE crm_access.RecoveryCode(
 InstitutionId uniqueidentifier NOT NULL,UserId uniqueidentifier NOT NULL,
 CodeHash binary(32) NOT NULL,ConsumedAt datetime2(7) NULL,
 CONSTRAINT PK_P2_Recovery PRIMARY KEY(InstitutionId,UserId,CodeHash),
 CONSTRAINT FK_P2_Recovery FOREIGN KEY(InstitutionId,UserId) REFERENCES crm_access.AccessUser(InstitutionId,UserId)
);
CREATE TABLE crm_access.Challenge(
 InstitutionId uniqueidentifier NOT NULL,ChallengeId uniqueidentifier NOT NULL,
 UserId uniqueidentifier NOT NULL,TokenHash binary(32) NOT NULL,Kind varchar(20) NOT NULL,
 AuthVersion bigint NOT NULL,Attempts int NOT NULL,ExpiresAt datetime2(7) NOT NULL,ConsumedAt datetime2(7) NULL,
 CONSTRAINT PK_P2_Challenge PRIMARY KEY(InstitutionId,ChallengeId),
 CONSTRAINT UQ_P2_Challenge_Hash UNIQUE(TokenHash),
 CONSTRAINT FK_P2_Challenge_User FOREIGN KEY(InstitutionId,UserId) REFERENCES crm_access.AccessUser(InstitutionId,UserId),
 CONSTRAINT CK_P2_Challenge CHECK(Kind IN('login_mfa','invite','reset') AND Attempts BETWEEN 0 AND 8)
);
CREATE TABLE crm_access.RateBucket(
 InstitutionId uniqueidentifier NOT NULL,BucketHash binary(32) NOT NULL,
 WindowAt datetime2(7) NOT NULL,Attempts int NOT NULL,LockedUntil datetime2(7) NULL,
 CONSTRAINT PK_P2_Rate PRIMARY KEY(InstitutionId,BucketHash),
 CONSTRAINT FK_P2_Rate FOREIGN KEY(InstitutionId) REFERENCES crm_access.Institution(InstitutionId),
 CONSTRAINT CK_P2_Rate CHECK(Attempts>=0)
);
CREATE TABLE crm_access.Operation(
 InstitutionId uniqueidentifier NOT NULL,OperationId uniqueidentifier NOT NULL,ActorId uniqueidentifier NOT NULL,
 Action varchar(80) NOT NULL,ResourceRef nvarchar(200) NOT NULL,PayloadHash binary(32) NOT NULL,
 Result nvarchar(max) NOT NULL,CreatedAt datetime2(7) NOT NULL,
 CONSTRAINT PK_P2_Operation PRIMARY KEY(InstitutionId,OperationId),
 CONSTRAINT FK_P2_Operation FOREIGN KEY(InstitutionId,ActorId) REFERENCES crm_access.AccessUser(InstitutionId,UserId),
 CONSTRAINT CK_P2_Operation CHECK(ISJSON(Result)=1)
);
CREATE TABLE crm_access.Audit(
 EventId bigint IDENTITY(1,1) NOT NULL CONSTRAINT PK_P2_Audit PRIMARY KEY,
 InstitutionId uniqueidentifier NOT NULL,ActorId uniqueidentifier NULL,
 Action varchar(80) NOT NULL,ResourceRef nvarchar(200) NOT NULL,Outcome varchar(20) NOT NULL,
 Metadata nvarchar(max) NOT NULL,OccurredAt datetime2(7) NOT NULL CONSTRAINT DF_P2_Audit DEFAULT SYSUTCDATETIME(),
 CONSTRAINT FK_P2_Audit FOREIGN KEY(InstitutionId) REFERENCES crm_access.Institution(InstitutionId),
 CONSTRAINT CK_P2_Audit CHECK(ISJSON(Metadata)=1 AND Outcome IN('accepted','denied','failed'))
);
CREATE INDEX IX_P2_Audit ON crm_access.Audit(InstitutionId,EventId DESC);
CREATE TABLE crm_access.ChannelSetting(
 InstitutionId uniqueidentifier NOT NULL,IntegrationId uniqueidentifier NOT NULL,
 Document nvarchar(max) NOT NULL,Revision bigint NOT NULL,UpdatedAt datetime2(7) NOT NULL,UpdatedBy uniqueidentifier NULL,
 CONSTRAINT PK_P2_ChannelSetting PRIMARY KEY(InstitutionId,IntegrationId),
 CONSTRAINT FK_P2_ChannelSetting FOREIGN KEY(InstitutionId,IntegrationId) REFERENCES crm_channels2.Integration(InstitutionId,IntegrationId),
 CONSTRAINT FK_P2_ChannelSetting_Actor FOREIGN KEY(InstitutionId,UpdatedBy) REFERENCES crm_access.AccessUser(InstitutionId,UserId),
 CONSTRAINT CK_P2_ChannelSetting CHECK(ISJSON(Document)=1 AND LEFT(LTRIM(Document),1)=N'{' AND Revision>0)
);
CREATE TABLE crm_access.BudgetUsage(
 InstitutionId uniqueidentifier NOT NULL,Kind varchar(16) NOT NULL,WindowDate date NOT NULL,
 Amount decimal(19,6) NOT NULL,
 CONSTRAINT PK_P2_BudgetUsage PRIMARY KEY(InstitutionId,Kind,WindowDate),
 CONSTRAINT FK_P2_BudgetUsage FOREIGN KEY(InstitutionId) REFERENCES crm_access.Institution(InstitutionId),
 CONSTRAINT CK_P2_BudgetUsage CHECK(Kind IN('tokens','messages','usd') AND Amount>=0)
);
