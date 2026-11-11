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
-- C11_BOUNDARY
CREATE TABLE [crm_channels2].[TikTokPolicy](
 [InstitutionId] uniqueidentifier NOT NULL,
 [IntegrationId] uniqueidentifier NOT NULL,
 [ConfiguredScopes] nvarchar(max) NOT NULL,
 [ReviewStatus] varchar(24) NOT NULL CONSTRAINT [DF_C11_TikTokPolicy_ReviewStatus] DEFAULT N'untracked',
 [ApprovedProducts] nvarchar(max) NOT NULL,
 [ApprovedScopes] nvarchar(max) NOT NULL,
 [OperatorAttestedEvents] bit NOT NULL CONSTRAINT [DF_C11_TikTokPolicy_OperatorAttestedEvents] DEFAULT 0,
 [AppReviewNotes] nvarchar(2000) NULL,
 [OutboundMode] varchar(16) NOT NULL CONSTRAINT [DF_C11_TikTokPolicy_OutboundMode] DEFAULT N'disabled',
 [RolloutPercent] tinyint NOT NULL CONSTRAINT [DF_C11_TikTokPolicy_RolloutPercent] DEFAULT 0,
 [DailyOutboundQuota] int NOT NULL CONSTRAINT [DF_C11_TikTokPolicy_DailyOutboundQuota] DEFAULT 0,
 [DailyAiQuota] int NOT NULL CONSTRAINT [DF_C11_TikTokPolicy_DailyAiQuota] DEFAULT 0,
 [BusinessMessagingEnabled] bit NOT NULL CONSTRAINT [DF_C11_TikTokPolicy_BusinessMessagingEnabled] DEFAULT 0,
 [CommentReplyEnabled] bit NOT NULL CONSTRAINT [DF_C11_TikTokPolicy_CommentReplyEnabled] DEFAULT 0,
 [AiEnabled] bit NOT NULL CONSTRAINT [DF_C11_TikTokPolicy_AiEnabled] DEFAULT 0,
 [AgentsEnabled] bit NOT NULL CONSTRAINT [DF_C11_TikTokPolicy_AgentsEnabled] DEFAULT 0,
 [TriggersEnabled] bit NOT NULL CONSTRAINT [DF_C11_TikTokPolicy_TriggersEnabled] DEFAULT 0,
 [RemarketingEnabled] bit NOT NULL CONSTRAINT [DF_C11_TikTokPolicy_RemarketingEnabled] DEFAULT 0,
 [BusinessApiBaseUrl] nvarchar(300) NOT NULL,
 [BusinessApiVersion] varchar(20) NOT NULL,
 [SendMessagePath] nvarchar(260) NULL,
 [CommentReplyPath] nvarchar(260) NULL,
 [AccessTokenAlias] varchar(120) NULL,
 [RuntimeNotes] nvarchar(1200) NULL,
 [UpdatedAt] datetime2(7) NOT NULL,
 [RowVersion] rowversion NOT NULL,
 CONSTRAINT [K_C11_TikTokPolicy_0] PRIMARY KEY ([InstitutionId],[IntegrationId]),
 CONSTRAINT [CK_C11_TikTokPolicy_0] CHECK (RolloutPercent BETWEEN 0 AND 100),
 CONSTRAINT [CK_C11_TikTokPolicy_1] CHECK (DailyOutboundQuota BETWEEN 0 AND 1000000 AND DailyAiQuota BETWEEN 0 AND 1000000),
 CONSTRAINT [CK_C11_TikTokPolicy_2] CHECK (ReviewStatus IN('untracked','pending','changes_requested','approved')),
 CONSTRAINT [CK_C11_TikTokPolicy_3] CHECK (OutboundMode IN('disabled','shadow','manual','live','stub')),
 CONSTRAINT [CK_C11_TikTokPolicy_4] CHECK (ISJSON([ConfiguredScopes])=1),
 CONSTRAINT [CK_C11_TikTokPolicy_5] CHECK (ISJSON([ApprovedProducts])=1),
 CONSTRAINT [CK_C11_TikTokPolicy_6] CHECK (ISJSON([ApprovedScopes])=1)
);
-- C11_BOUNDARY
CREATE TABLE [crm_channels2].[QuotaBucket](
 [InstitutionId] uniqueidentifier NOT NULL,
 [IntegrationId] uniqueidentifier NOT NULL,
 [DayUtc] date NOT NULL,
 [Action] varchar(24) NOT NULL,
 [Reserved] bigint NOT NULL CONSTRAINT [DF_C11_QuotaBucket_Reserved] DEFAULT 0,
 [Committed] bigint NOT NULL CONSTRAINT [DF_C11_QuotaBucket_Committed] DEFAULT 0,
 [UpdatedAt] datetime2(7) NOT NULL,
 [RowVersion] rowversion NOT NULL,
 CONSTRAINT [K_C11_QuotaBucket_0] PRIMARY KEY ([InstitutionId],[IntegrationId],[DayUtc],[Action]),
 CONSTRAINT [CK_C11_QuotaBucket_0] CHECK (Reserved>=0 AND Committed>=0),
 CONSTRAINT [CK_C11_QuotaBucket_1] CHECK (Action IN('outbound','ai'))
);
-- C11_BOUNDARY
CREATE TABLE [crm_channels2].[QuotaReservation](
 [InstitutionId] uniqueidentifier NOT NULL,
 [ReservationId] uniqueidentifier NOT NULL,
 [IntegrationId] uniqueidentifier NOT NULL,
 [DayUtc] date NOT NULL,
 [Action] varchar(24) NOT NULL,
 [OperationId] uniqueidentifier NOT NULL,
 [Units] int NOT NULL,
 [Status] varchar(16) NOT NULL,
 [CreatedAt] datetime2(7) NOT NULL,
 [UpdatedAt] datetime2(7) NOT NULL,
 [RowVersion] rowversion NOT NULL,
 CONSTRAINT [K_C11_QuotaReservation_0] PRIMARY KEY ([InstitutionId],[ReservationId]),
 CONSTRAINT [K_C11_QuotaReservation_1] UNIQUE ([InstitutionId],[IntegrationId],[OperationId],[Action]),
 CONSTRAINT [K_C11_QuotaReservation_2] UNIQUE ([InstitutionId],[IntegrationId],[ReservationId]),
 CONSTRAINT [K_C11_QuotaReservation_3] UNIQUE ([InstitutionId],[IntegrationId],[ReservationId],[OperationId]),
 CONSTRAINT [CK_C11_QuotaReservation_0] CHECK (Units>0),
 CONSTRAINT [CK_C11_QuotaReservation_1] CHECK (Status IN('reserved','committed','released','uncertain')),
 CONSTRAINT [CK_C11_QuotaReservation_2] CHECK (Action IN('outbound','ai'))
);
-- C11_BOUNDARY
ALTER TABLE [crm_channels2].[TikTokPolicy] WITH CHECK ADD CONSTRAINT [FK_C11_8] FOREIGN KEY([InstitutionId]) REFERENCES [crm_channels2].[Context]([InstitutionId]);
ALTER TABLE [crm_channels2].[QuotaBucket] WITH CHECK ADD CONSTRAINT [FK_C11_10] FOREIGN KEY([InstitutionId]) REFERENCES [crm_channels2].[Context]([InstitutionId]);
ALTER TABLE [crm_channels2].[QuotaReservation] WITH CHECK ADD CONSTRAINT [FK_C11_11] FOREIGN KEY([InstitutionId]) REFERENCES [crm_channels2].[Context]([InstitutionId]);
ALTER TABLE [crm_channels2].[TikTokPolicy] WITH CHECK ADD CONSTRAINT [FK_C11_28] FOREIGN KEY([InstitutionId],[IntegrationId]) REFERENCES [crm_channels2].[Integration]([InstitutionId],[IntegrationId]);
ALTER TABLE [crm_channels2].[QuotaBucket] WITH CHECK ADD CONSTRAINT [FK_C11_29] FOREIGN KEY([InstitutionId],[IntegrationId]) REFERENCES [crm_channels2].[Integration]([InstitutionId],[IntegrationId]);
ALTER TABLE [crm_channels2].[QuotaReservation] WITH CHECK ADD CONSTRAINT [FK_C11_30] FOREIGN KEY([InstitutionId],[IntegrationId]) REFERENCES [crm_channels2].[Integration]([InstitutionId],[IntegrationId]);
ALTER TABLE [crm_channels2].[QuotaReservation] WITH CHECK ADD CONSTRAINT [FK_C11_62] FOREIGN KEY([InstitutionId],[IntegrationId],[OperationId]) REFERENCES [crm_channels2].[ProviderOperation]([InstitutionId],[IntegrationId],[OperationId]);
ALTER TABLE [crm_channels2].[QuotaReservation] WITH CHECK ADD CONSTRAINT [FK_C11_63] FOREIGN KEY([InstitutionId],[IntegrationId],[DayUtc],[Action]) REFERENCES [crm_channels2].[QuotaBucket]([InstitutionId],[IntegrationId],[DayUtc],[Action]);
