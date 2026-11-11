-- New P2 Spanish release, derived from frozen reviewed DDL; no old release edits.
SET XACT_ABORT ON;
IF @@TRANCOUNT<>1 OR USER_NAME()<>N'cbn_institutional_es_migrator'
 OR CONVERT(int,SERVERPROPERTY('ProductMajorVersion'))<>15
 OR (SELECT compatibility_level FROM sys.databases WHERE database_id=DB_ID())<>150
 OR SESSION_CONTEXT(N'CBN_P2ES_TARGET') IS NULL
 OR DB_NAME() COLLATE Latin1_General_100_BIN2<>CONVERT(nvarchar(128),SESSION_CONTEXT(N'CBN_P2ES_TARGET')) COLLATE Latin1_General_100_BIN2
 OR LEFT(DB_NAME(),9) COLLATE Latin1_General_100_BIN2<>N'CBN_P2ES_'
 THROW 51870,'Approved Spanish P2 restoration, actor and transaction required.',1;
-- P2_ES_DDL_BODY_BEGIN
CREATE TABLE [dbo].[CRMAccesoInstitucion](
 InstitutionId uniqueidentifier NOT NULL CONSTRAINT PK_P2_Institution PRIMARY KEY,
 BootstrapHash binary(32) NULL,InitializedAt datetime2(7) NULL,
 CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_P2_Institution DEFAULT SYSUTCDATETIME(),
 CONSTRAINT FK_P2_Institution FOREIGN KEY(InstitutionId) REFERENCES [dbo].[CRMCanalInstitucionalContexto](InstitutionId)
);
CREATE TABLE [dbo].[CRMAccesoRol](
 InstitutionId uniqueidentifier NOT NULL,RoleKey varchar(64) COLLATE Latin1_General_100_BIN2 NOT NULL,
 Name nvarchar(100) NOT NULL,Actions nvarchar(max) NOT NULL,Protected bit NOT NULL,
 Active bit NOT NULL,Revision bigint NOT NULL,
 CONSTRAINT PK_P2_Role PRIMARY KEY(InstitutionId,RoleKey),
 CONSTRAINT FK_P2_Role FOREIGN KEY(InstitutionId) REFERENCES [dbo].[CRMAccesoInstitucion](InstitutionId),
 CONSTRAINT CK_P2_Role CHECK(ISJSON(Actions)=1 AND LEFT(LTRIM(Actions),1)=N'[' AND Revision>0 AND LEN(Name)>0)
);
CREATE TABLE [dbo].[CRMAccesoUsuario](
 InstitutionId uniqueidentifier NOT NULL,UserId uniqueidentifier NOT NULL,
 Login nvarchar(254) NOT NULL,NormalizedLogin nvarchar(254) COLLATE Latin1_General_100_BIN2 NOT NULL,
 DisplayName nvarchar(180) NOT NULL,Profile nvarchar(max) NOT NULL,
 PasswordHash varchar(300) NULL,RoleKey varchar(64) COLLATE Latin1_General_100_BIN2 NOT NULL,
 Active bit NOT NULL,AuthVersion bigint NOT NULL,Revision bigint NOT NULL,
 CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_P2_User_Created DEFAULT SYSUTCDATETIME(),
 UpdatedAt datetime2(7) NOT NULL CONSTRAINT DF_P2_User_Updated DEFAULT SYSUTCDATETIME(),
 CONSTRAINT PK_P2_User PRIMARY KEY(InstitutionId,UserId),
 CONSTRAINT UQ_P2_User_Login UNIQUE(InstitutionId,NormalizedLogin),
 CONSTRAINT FK_P2_User_Role FOREIGN KEY(InstitutionId,RoleKey) REFERENCES [dbo].[CRMAccesoRol](InstitutionId,RoleKey),
 CONSTRAINT CK_P2_User CHECK(ISJSON(Profile)=1 AND LEFT(LTRIM(Profile),1)=N'{' AND Revision>0 AND AuthVersion>0 AND LEN(DisplayName)>0)
);
CREATE TABLE [dbo].[CRMAccesoSesion](
 InstitutionId uniqueidentifier NOT NULL,SessionId uniqueidentifier NOT NULL,UserId uniqueidentifier NOT NULL,
 TokenHash binary(32) NOT NULL,CSRFHash binary(32) NOT NULL,AuthVersion bigint NOT NULL,
 IssuedAt datetime2(7) NOT NULL,ExpiresAt datetime2(7) NOT NULL,
 RevokedAt datetime2(7) NULL,RecentAt datetime2(7) NULL,MFAAt datetime2(7) NULL,
 CONSTRAINT PK_P2_Session PRIMARY KEY(InstitutionId,SessionId),
 CONSTRAINT UQ_P2_Session_Token UNIQUE(TokenHash),
 CONSTRAINT FK_P2_Session_User FOREIGN KEY(InstitutionId,UserId) REFERENCES [dbo].[CRMAccesoUsuario](InstitutionId,UserId),
 CONSTRAINT CK_P2_Session CHECK(ExpiresAt>IssuedAt AND AuthVersion>0)
);
CREATE INDEX IX_P2_Session_User ON [dbo].[CRMAccesoSesion](InstitutionId,UserId,RevokedAt,ExpiresAt);
CREATE TABLE [dbo].[CRMAccesoAjuste](
 InstitutionId uniqueidentifier NOT NULL,Section varchar(40) COLLATE Latin1_General_100_BIN2 NOT NULL,
 Document nvarchar(max) NOT NULL,Revision bigint NOT NULL,UpdatedAt datetime2(7) NOT NULL,
 UpdatedBy uniqueidentifier NULL,
 CONSTRAINT PK_P2_Setting PRIMARY KEY(InstitutionId,Section),
 CONSTRAINT FK_P2_Setting FOREIGN KEY(InstitutionId) REFERENCES [dbo].[CRMAccesoInstitucion](InstitutionId),
 CONSTRAINT CK_P2_Setting CHECK(ISJSON(Document)=1 AND LEFT(LTRIM(Document),1)=N'{' AND Revision>0)
);
CREATE TABLE [dbo].[CRMAccesoAjusteHistorial](
 InstitutionId uniqueidentifier NOT NULL,Section varchar(40) COLLATE Latin1_General_100_BIN2 NOT NULL,
 Revision bigint NOT NULL,Document nvarchar(max) NOT NULL,RecordedAt datetime2(7) NOT NULL,
 ActorId uniqueidentifier NULL,
 CONSTRAINT PK_P2_SettingHistory PRIMARY KEY(InstitutionId,Section,Revision),
 CONSTRAINT FK_P2_SettingHistory FOREIGN KEY(InstitutionId) REFERENCES [dbo].[CRMAccesoInstitucion](InstitutionId),
 CONSTRAINT CK_P2_SettingHistory CHECK(ISJSON(Document)=1 AND Revision>0)
);
CREATE TABLE [dbo].[CRMAccesoSecreto](
 InstitutionId uniqueidentifier NOT NULL,SecretId uniqueidentifier NOT NULL,
 Scope varchar(20) NOT NULL,OwnerRef nvarchar(200) COLLATE Latin1_General_100_BIN2 NOT NULL,
 Kind varchar(40) NOT NULL,VersionNo bigint NOT NULL,KeyId varchar(32) NOT NULL,
 Nonce binary(12) NOT NULL,Ciphertext varbinary(max) NOT NULL,Hint nvarchar(20) NOT NULL,
 State varchar(12) NOT NULL,CreatedAt datetime2(7) NOT NULL,
 CONSTRAINT PK_P2_Secret PRIMARY KEY(InstitutionId,SecretId),
 CONSTRAINT UQ_P2_Secret_Version UNIQUE(InstitutionId,Scope,OwnerRef,Kind,VersionNo),
 CONSTRAINT FK_P2_Secret FOREIGN KEY(InstitutionId) REFERENCES [dbo].[CRMAccesoInstitucion](InstitutionId),
 CONSTRAINT CK_P2_Secret CHECK(Scope IN('provider','channel','webhook','totp') AND State IN('staged','retired') AND VersionNo>0 AND DATALENGTH(Ciphertext)>16)
);
CREATE TABLE [dbo].[CRMAccesoFactor](
 InstitutionId uniqueidentifier NOT NULL,UserId uniqueidentifier NOT NULL,
 SecretId uniqueidentifier NULL,PendingSecretId uniqueidentifier NULL,State varchar(12) NOT NULL,LastStep bigint NOT NULL,
 SetupId uniqueidentifier NULL,SetupSessionId uniqueidentifier NULL,SetupExpiresAt datetime2(7) NULL,
 SetupAttempts int NOT NULL CONSTRAINT DF_P2_Factor_Attempts DEFAULT 0,
 CONSTRAINT PK_P2_Factor PRIMARY KEY(InstitutionId,UserId),
 CONSTRAINT FK_P2_Factor_User FOREIGN KEY(InstitutionId,UserId) REFERENCES [dbo].[CRMAccesoUsuario](InstitutionId,UserId),
 CONSTRAINT FK_P2_Factor_Secret FOREIGN KEY(InstitutionId,SecretId) REFERENCES [dbo].[CRMAccesoSecreto](InstitutionId,SecretId),
 CONSTRAINT FK_P2_Factor_Pending FOREIGN KEY(InstitutionId,PendingSecretId) REFERENCES [dbo].[CRMAccesoSecreto](InstitutionId,SecretId),
 CONSTRAINT CK_P2_Factor CHECK(State IN('disabled','pending','enabled') AND SetupAttempts BETWEEN 0 AND 8)
);
CREATE TABLE [dbo].[CRMAccesoCodigoRecuperacion](
 InstitutionId uniqueidentifier NOT NULL,UserId uniqueidentifier NOT NULL,
 CodeHash binary(32) NOT NULL,ConsumedAt datetime2(7) NULL,
 CONSTRAINT PK_P2_Recovery PRIMARY KEY(InstitutionId,UserId,CodeHash),
 CONSTRAINT FK_P2_Recovery FOREIGN KEY(InstitutionId,UserId) REFERENCES [dbo].[CRMAccesoUsuario](InstitutionId,UserId)
);
CREATE TABLE [dbo].[CRMAccesoDesafio](
 InstitutionId uniqueidentifier NOT NULL,ChallengeId uniqueidentifier NOT NULL,
 UserId uniqueidentifier NOT NULL,TokenHash binary(32) NOT NULL,Kind varchar(20) NOT NULL,
 AuthVersion bigint NOT NULL,Attempts int NOT NULL,ExpiresAt datetime2(7) NOT NULL,ConsumedAt datetime2(7) NULL,
 CONSTRAINT PK_P2_Challenge PRIMARY KEY(InstitutionId,ChallengeId),
 CONSTRAINT UQ_P2_Challenge_Hash UNIQUE(TokenHash),
 CONSTRAINT FK_P2_Challenge_User FOREIGN KEY(InstitutionId,UserId) REFERENCES [dbo].[CRMAccesoUsuario](InstitutionId,UserId),
 CONSTRAINT CK_P2_Challenge CHECK(Kind IN('login_mfa','invite','reset') AND Attempts BETWEEN 0 AND 8)
);
CREATE TABLE [dbo].[CRMAccesoLimiteAcceso](
 InstitutionId uniqueidentifier NOT NULL,BucketHash binary(32) NOT NULL,
 WindowAt datetime2(7) NOT NULL,Attempts int NOT NULL,LockedUntil datetime2(7) NULL,
 CONSTRAINT PK_P2_Rate PRIMARY KEY(InstitutionId,BucketHash),
 CONSTRAINT FK_P2_Rate FOREIGN KEY(InstitutionId) REFERENCES [dbo].[CRMAccesoInstitucion](InstitutionId),
 CONSTRAINT CK_P2_Rate CHECK(Attempts>=0)
);
CREATE TABLE [dbo].[CRMAccesoOperacion](
 InstitutionId uniqueidentifier NOT NULL,OperationId uniqueidentifier NOT NULL,ActorId uniqueidentifier NOT NULL,
 Action varchar(80) NOT NULL,ResourceRef nvarchar(200) NOT NULL,PayloadHash binary(32) NOT NULL,
 Result nvarchar(max) NOT NULL,CreatedAt datetime2(7) NOT NULL,
 CONSTRAINT PK_P2_Operation PRIMARY KEY(InstitutionId,OperationId),
 CONSTRAINT FK_P2_Operation FOREIGN KEY(InstitutionId,ActorId) REFERENCES [dbo].[CRMAccesoUsuario](InstitutionId,UserId),
 CONSTRAINT CK_P2_Operation CHECK(ISJSON(Result)=1)
);
CREATE TABLE [dbo].[CRMAccesoAuditoria](
 EventId bigint IDENTITY(1,1) NOT NULL CONSTRAINT PK_P2_Audit PRIMARY KEY,
 InstitutionId uniqueidentifier NOT NULL,ActorId uniqueidentifier NULL,
 Action varchar(80) NOT NULL,ResourceRef nvarchar(200) NOT NULL,Outcome varchar(20) NOT NULL,
 Metadata nvarchar(max) NOT NULL,OccurredAt datetime2(7) NOT NULL CONSTRAINT DF_P2_Audit DEFAULT SYSUTCDATETIME(),
 CONSTRAINT FK_P2_Audit FOREIGN KEY(InstitutionId) REFERENCES [dbo].[CRMAccesoInstitucion](InstitutionId),
 CONSTRAINT CK_P2_Audit CHECK(ISJSON(Metadata)=1 AND Outcome IN('accepted','denied','failed'))
);
CREATE INDEX IX_P2_Audit ON [dbo].[CRMAccesoAuditoria](InstitutionId,EventId DESC);
CREATE TABLE [dbo].[CRMAccesoCanalAjuste](
 InstitutionId uniqueidentifier NOT NULL,IntegrationId uniqueidentifier NOT NULL,
 Document nvarchar(max) NOT NULL,Revision bigint NOT NULL,UpdatedAt datetime2(7) NOT NULL,UpdatedBy uniqueidentifier NULL,
 CONSTRAINT PK_P2_ChannelSetting PRIMARY KEY(InstitutionId,IntegrationId),
 CONSTRAINT FK_P2_ChannelSetting FOREIGN KEY(InstitutionId,IntegrationId) REFERENCES [dbo].[CRMCanalInstitucionalIntegracion](InstitutionId,IntegrationId),
 CONSTRAINT FK_P2_ChannelSetting_Actor FOREIGN KEY(InstitutionId,UpdatedBy) REFERENCES [dbo].[CRMAccesoUsuario](InstitutionId,UserId),
 CONSTRAINT CK_P2_ChannelSetting CHECK(ISJSON(Document)=1 AND LEFT(LTRIM(Document),1)=N'{' AND Revision>0)
);
CREATE TABLE [dbo].[CRMAccesoConsumo](
 InstitutionId uniqueidentifier NOT NULL,Kind varchar(16) NOT NULL,WindowDate date NOT NULL,
 Amount decimal(19,6) NOT NULL,
 CONSTRAINT PK_P2_BudgetUsage PRIMARY KEY(InstitutionId,Kind,WindowDate),
 CONSTRAINT FK_P2_BudgetUsage FOREIGN KEY(InstitutionId) REFERENCES [dbo].[CRMAccesoInstitucion](InstitutionId),
 CONSTRAINT CK_P2_BudgetUsage CHECK(Kind IN('tokens','messages','usd') AND Amount>=0)
);
