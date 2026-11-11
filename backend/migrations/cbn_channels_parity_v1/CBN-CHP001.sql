-- SQL-C11 immutable restored-copy unit. Runner owns the transaction.
SET XACT_ABORT ON;
IF @@TRANCOUNT<>1 OR USER_NAME()<>N'cbn_channels_parity_migrator_c11' OR SESSION_CONTEXT(N'CBN_C11_TARGET') IS NULL OR DB_NAME() COLLATE Latin1_General_100_BIN2<>CONVERT(nvarchar(128),SESSION_CONTEXT(N'CBN_C11_TARGET')) COLLATE Latin1_General_100_BIN2 OR DB_NAME() NOT LIKE N'CBN_C11[_]%' THROW 51111,'Approved C11 restoration and principal required.',1;
-- C11_BOUNDARY
CREATE TABLE [crm_channels2].[Context](
 [ContextId] tinyint NOT NULL,
 [InstitutionId] uniqueidentifier NOT NULL,
 [ContractVersion] varchar(40) NOT NULL,
 [CreatedAt] datetime2(7) NOT NULL,
 CONSTRAINT [K_C11_Context_0] PRIMARY KEY ([ContextId]),
 CONSTRAINT [K_C11_Context_1] UNIQUE ([InstitutionId]),
 CONSTRAINT [CK_C11_Context_0] CHECK (ContextId=1)
);
-- C11_BOUNDARY
CREATE TABLE [crm_channels2].[Application](
 [InstitutionId] uniqueidentifier NOT NULL,
 [ApplicationId] uniqueidentifier NOT NULL,
 [Provider] varchar(12) NOT NULL,
 [ClientId] nvarchar(128) COLLATE Latin1_General_100_BIN2 NOT NULL,
 [ApiVersion] varchar(20) NOT NULL,
 [IssuerProfile] varchar(40) NOT NULL,
 [RedirectUri] nvarchar(2048) NOT NULL,
 [EgressProfile] varchar(64) NOT NULL,
 [State] varchar(16) NOT NULL CONSTRAINT [DF_C11_Application_State] DEFAULT N'draft',
 [CreatedAt] datetime2(7) NOT NULL,
 [UpdatedAt] datetime2(7) NOT NULL,
 [RowVersion] rowversion NOT NULL,
 CONSTRAINT [K_C11_Application_0] PRIMARY KEY ([InstitutionId],[ApplicationId]),
 CONSTRAINT [K_C11_Application_1] UNIQUE ([InstitutionId],[ApplicationId],[Provider]),
 CONSTRAINT [K_C11_Application_2] UNIQUE ([InstitutionId],[Provider],[ClientId],[IssuerProfile]),
 CONSTRAINT [CK_C11_Application_0] CHECK (Provider IN('meta','tiktok')),
 CONSTRAINT [CK_C11_Application_1] CHECK (State IN('draft','enabled','paused','retired')),
 CONSTRAINT [CK_C11_Application_2] CHECK ([ClientId] IS NULL OR (DATALENGTH([ClientId])>0 AND DATALENGTH([ClientId])=DATALENGTH(RTRIM([ClientId]))))
);
-- C11_BOUNDARY
CREATE TABLE [crm_channels2].[Integration](
 [InstitutionId] uniqueidentifier NOT NULL,
 [IntegrationId] uniqueidentifier NOT NULL,
 [ApplicationId] uniqueidentifier NOT NULL,
 [Provider] varchar(12) NOT NULL,
 [Channel] varchar(12) NOT NULL,
 [Environment] varchar(16) NOT NULL CONSTRAINT [DF_C11_Integration_Environment] DEFAULT N'development',
 [DisplayName] nvarchar(160) NOT NULL,
 [ExternalAccountId] nvarchar(200) COLLATE Latin1_General_100_BIN2 NULL,
 [ParentExternalId] nvarchar(200) COLLATE Latin1_General_100_BIN2 NULL,
 [PageName] nvarchar(200) NULL,
 [UserName] nvarchar(200) NULL,
 [PortfolioId] nvarchar(128) NULL,
 [BusinessAccountId] nvarchar(128) NULL,
 [AdvertiserId] nvarchar(128) NULL,
 [ApiVersion] varchar(20) NOT NULL,
 [DispatchMode] varchar(32) NOT NULL,
 [RequestedStatus] varchar(16) NOT NULL CONSTRAINT [DF_C11_Integration_RequestedStatus] DEFAULT N'disconnected',
 [VerifiedStatus] varchar(24) NOT NULL CONSTRAINT [DF_C11_Integration_VerifiedStatus] DEFAULT N'unverified',
 [InitialStageKey] varchar(64) NULL,
 [InitialStageConfigHash] binary(32) NULL,
 [TokenExpiresAt] datetime2(7) NULL,
 [RefreshExpiresAt] datetime2(7) NULL,
 [LastSyncAt] datetime2(7) NULL,
 [CreatedAt] datetime2(7) NOT NULL,
 [UpdatedAt] datetime2(7) NOT NULL,
 [RowVersion] rowversion NOT NULL,
 [ConfiguredScopes] nvarchar(max) NOT NULL CONSTRAINT [DF_C11_Integration_ConfiguredScopes] DEFAULT N'[]',
 [ApprovedScopes] nvarchar(max) NOT NULL CONSTRAINT [DF_C11_Integration_ApprovedScopes] DEFAULT N'[]',
 [AppReviewStatus] varchar(24) NOT NULL CONSTRAINT [DF_C11_Integration_AppReviewStatus] DEFAULT N'untracked',
 [ExternalNamespace] binary(32) NOT NULL,
 CONSTRAINT [K_C11_Integration_0] PRIMARY KEY ([InstitutionId],[IntegrationId]),
 CONSTRAINT [K_C11_Integration_1] UNIQUE ([InstitutionId],[IntegrationId],[ApplicationId]),
 CONSTRAINT [CK_C11_Integration_0] CHECK ((Provider='meta' AND Channel IN('whatsapp','instagram','facebook','messenger')) OR (Provider='tiktok' AND Channel='tiktok')),
 CONSTRAINT [CK_C11_Integration_1] CHECK (RequestedStatus IN('connected','paused','disconnected')),
 CONSTRAINT [CK_C11_Integration_2] CHECK ([ExternalAccountId] IS NULL OR (DATALENGTH([ExternalAccountId])>0 AND DATALENGTH([ExternalAccountId])=DATALENGTH(RTRIM([ExternalAccountId])))),
 CONSTRAINT [CK_C11_Integration_3] CHECK ([ParentExternalId] IS NULL OR (DATALENGTH([ParentExternalId])>0 AND DATALENGTH([ParentExternalId])=DATALENGTH(RTRIM([ParentExternalId])))),
 CONSTRAINT [CK_C11_Integration_4] CHECK (ISJSON([ConfiguredScopes])=1),
 CONSTRAINT [CK_C11_Integration_5] CHECK (ISJSON([ApprovedScopes])=1)
);
CREATE UNIQUE INDEX [UQ_Integration_External] ON [crm_channels2].[Integration] ([InstitutionId],[Provider],[Channel],[ExternalNamespace],[ExternalAccountId]) WHERE ExternalAccountId IS NOT NULL;
-- C11_BOUNDARY
CREATE TABLE [crm_channels2].[Audit](
 [InstitutionId] uniqueidentifier NOT NULL,
 [AuditId] uniqueidentifier NOT NULL,
 [IntegrationId] uniqueidentifier NULL,
 [ActorRef] nvarchar(128) NOT NULL,
 [Action] varchar(64) NOT NULL,
 [OperationId] uniqueidentifier NULL,
 [ResultCode] varchar(64) NOT NULL,
 [CreatedAt] datetime2(7) NOT NULL,
 CONSTRAINT [K_C11_Audit_0] PRIMARY KEY ([InstitutionId],[AuditId])
);
-- C11_BOUNDARY
ALTER TABLE [crm_channels2].[Application] WITH CHECK ADD CONSTRAINT [FK_C11_0] FOREIGN KEY([InstitutionId]) REFERENCES [crm_channels2].[Context]([InstitutionId]);
ALTER TABLE [crm_channels2].[Integration] WITH CHECK ADD CONSTRAINT [FK_C11_1] FOREIGN KEY([InstitutionId]) REFERENCES [crm_channels2].[Context]([InstitutionId]);
ALTER TABLE [crm_channels2].[Audit] WITH CHECK ADD CONSTRAINT [FK_C11_2] FOREIGN KEY([InstitutionId]) REFERENCES [crm_channels2].[Context]([InstitutionId]);
ALTER TABLE [crm_channels2].[Integration] WITH CHECK ADD CONSTRAINT [FK_C11_23] FOREIGN KEY([InstitutionId],[ApplicationId],[Provider]) REFERENCES [crm_channels2].[Application]([InstitutionId],[ApplicationId],[Provider]);
ALTER TABLE [crm_channels2].[Audit] WITH CHECK ADD CONSTRAINT [FK_C11_24] FOREIGN KEY([InstitutionId],[IntegrationId]) REFERENCES [crm_channels2].[Integration]([InstitutionId],[IntegrationId]);
