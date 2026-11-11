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
-- C11_BOUNDARY
CREATE TABLE [dbo].[CRMCanalInstitucionalContexto](
 [ContextId] tinyint NOT NULL,
 [InstitutionId] uniqueidentifier NOT NULL,
 [ContractVersion] varchar(40) NOT NULL,
 [CreatedAt] datetime2(7) NOT NULL,
 CONSTRAINT [K_C11_Context_0] PRIMARY KEY ([ContextId]),
 CONSTRAINT [K_C11_Context_1] UNIQUE ([InstitutionId]),
 CONSTRAINT [CK_C11_Context_0] CHECK (ContextId=1)
);
-- C11_BOUNDARY
CREATE TABLE [dbo].[CRMCanalInstitucionalAplicacion](
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
CREATE TABLE [dbo].[CRMCanalInstitucionalIntegracion](
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
CREATE UNIQUE INDEX [UQ_Integration_External] ON [dbo].[CRMCanalInstitucionalIntegracion] ([InstitutionId],[Provider],[Channel],[ExternalNamespace],[ExternalAccountId]) WHERE ExternalAccountId IS NOT NULL;
-- C11_BOUNDARY
CREATE TABLE [dbo].[CRMCanalInstitucionalAuditoria](
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
ALTER TABLE [dbo].[CRMCanalInstitucionalAplicacion] WITH CHECK ADD CONSTRAINT [FK_C11_0] FOREIGN KEY([InstitutionId]) REFERENCES [dbo].[CRMCanalInstitucionalContexto]([InstitutionId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalIntegracion] WITH CHECK ADD CONSTRAINT [FK_C11_1] FOREIGN KEY([InstitutionId]) REFERENCES [dbo].[CRMCanalInstitucionalContexto]([InstitutionId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalAuditoria] WITH CHECK ADD CONSTRAINT [FK_C11_2] FOREIGN KEY([InstitutionId]) REFERENCES [dbo].[CRMCanalInstitucionalContexto]([InstitutionId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalIntegracion] WITH CHECK ADD CONSTRAINT [FK_C11_23] FOREIGN KEY([InstitutionId],[ApplicationId],[Provider]) REFERENCES [dbo].[CRMCanalInstitucionalAplicacion]([InstitutionId],[ApplicationId],[Provider]);
ALTER TABLE [dbo].[CRMCanalInstitucionalAuditoria] WITH CHECK ADD CONSTRAINT [FK_C11_24] FOREIGN KEY([InstitutionId],[IntegrationId]) REFERENCES [dbo].[CRMCanalInstitucionalIntegracion]([InstitutionId],[IntegrationId]);

-- C11_BOUNDARY
CREATE TABLE [dbo].[CRMCanalInstitucionalSesionOAuth](
 [InstitutionId] uniqueidentifier NOT NULL,
 [OAuthSessionId] uniqueidentifier NOT NULL,
 [ApplicationId] uniqueidentifier NOT NULL,
 [IntegrationId] uniqueidentifier NULL,
 [ActorRef] nvarchar(128) NOT NULL,
 [AuthSessionHash] binary(32) NOT NULL,
 [StateHash] binary(32) NOT NULL,
 [IssuerProfile] varchar(40) NOT NULL,
 [RedirectUri] nvarchar(2048) NOT NULL,
 [RequestedScopes] nvarchar(max) NOT NULL,
 [PkceMethod] varchar(8) NULL,
 [Status] varchar(16) NOT NULL CONSTRAINT [DF_C11_OAuthSession_Status] DEFAULT N'pending',
 [ExpiresAt] datetime2(7) NOT NULL,
 [ClaimId] uniqueidentifier NULL,
 [ClaimUntil] datetime2(7) NULL,
 [ClaimVersion] bigint NOT NULL CONSTRAINT [DF_C11_OAuthSession_ClaimVersion] DEFAULT 0,
 [OperationId] uniqueidentifier NOT NULL,
 [ApplicationVersion] binary(8) NOT NULL,
 [CreatedAt] datetime2(7) NOT NULL,
 [CompletedAt] datetime2(7) NULL,
 [RowVersion] rowversion NOT NULL,
 [ClientSecretId] uniqueidentifier NOT NULL,
 [ClientSecretVersionNo] int NOT NULL,
 [GrantScope] varchar(24) NOT NULL,
 CONSTRAINT [K_C11_OAuthSession_0] PRIMARY KEY ([InstitutionId],[OAuthSessionId]),
 CONSTRAINT [K_C11_OAuthSession_1] UNIQUE ([StateHash]),
 CONSTRAINT [K_C11_OAuthSession_2] UNIQUE ([InstitutionId],[OperationId]),
 CONSTRAINT [K_C11_OAuthSession_3] UNIQUE ([InstitutionId],[OAuthSessionId],[IntegrationId],[ApplicationId]),
 CONSTRAINT [K_C11_OAuthSession_4] UNIQUE ([InstitutionId],[OAuthSessionId],[ApplicationId]),
 CONSTRAINT [CK_C11_OAuthSession_0] CHECK (ExpiresAt>CreatedAt AND ExpiresAt<=DATEADD(minute,30,CreatedAt)),
 CONSTRAINT [CK_C11_OAuthSession_1] CHECK ((GrantScope='create_connections' AND IntegrationId IS NULL) OR (GrantScope='bound_connection' AND IntegrationId IS NOT NULL)),
 CONSTRAINT [CK_C11_OAuthSession_2] CHECK (Status IN('pending','exchanging','assets_ready','completed','failed','expired','cancelled','uncertain','reconciled','abandoned')),
 CONSTRAINT [CK_C11_OAuthSession_3] CHECK (ClaimVersion>=0),
 CONSTRAINT [CK_C11_OAuthSession_4] CHECK (ClientSecretVersionNo>=1),
 CONSTRAINT [CK_C11_OAuthSession_5] CHECK (PkceMethod IS NULL OR PkceMethod='S256'),
 CONSTRAINT [CK_C11_OAuthSession_6] CHECK ((ClaimId IS NULL AND ClaimUntil IS NULL) OR (ClaimId IS NOT NULL AND ClaimUntil IS NOT NULL)),
 CONSTRAINT [CK_C11_OAuthSession_7] CHECK (ISJSON([RequestedScopes])=1)
);
-- C11_BOUNDARY
CREATE TABLE [dbo].[CRMCanalInstitucionalWebhook](
 [InstitutionId] uniqueidentifier NOT NULL,
 [EndpointId] uniqueidentifier NOT NULL,
 [ApplicationId] uniqueidentifier NOT NULL,
 [Provider] varchar(12) NOT NULL,
 [ChannelSelector] varchar(12) NOT NULL,
 [EndpointKey] varchar(96) COLLATE Latin1_General_100_BIN2 NOT NULL,
 [SignatureProfile] varchar(64) NOT NULL,
 [SignatureRequired] bit NOT NULL CONSTRAINT [DF_C11_WebhookEndpoint_SignatureRequired] DEFAULT 1,
 [IsActive] bit NOT NULL CONSTRAINT [DF_C11_WebhookEndpoint_IsActive] DEFAULT 0,
 [ChallengeVerifiedAt] datetime2(7) NULL,
 [LastSeenAt] datetime2(7) NULL,
 [CreatedAt] datetime2(7) NOT NULL,
 [UpdatedAt] datetime2(7) NOT NULL,
 [RowVersion] rowversion NOT NULL,
 CONSTRAINT [K_C11_WebhookEndpoint_0] PRIMARY KEY ([InstitutionId],[EndpointId]),
 CONSTRAINT [K_C11_WebhookEndpoint_1] UNIQUE ([EndpointKey]),
 CONSTRAINT [K_C11_WebhookEndpoint_2] UNIQUE ([InstitutionId],[EndpointId],[ApplicationId]),
 CONSTRAINT [K_C11_WebhookEndpoint_3] UNIQUE ([InstitutionId],[ApplicationId],[ChannelSelector]),
 CONSTRAINT [CK_C11_WebhookEndpoint_0] CHECK (SignatureRequired=1),
 CONSTRAINT [CK_C11_WebhookEndpoint_1] CHECK (Provider IN('meta','tiktok')),
 CONSTRAINT [CK_C11_WebhookEndpoint_2] CHECK (ChannelSelector IN('meta','whatsapp','instagram','facebook','tiktok')),
 CONSTRAINT [CK_C11_WebhookEndpoint_3] CHECK ([EndpointKey] IS NULL OR (DATALENGTH([EndpointKey])>0 AND DATALENGTH([EndpointKey])=DATALENGTH(RTRIM([EndpointKey]))))
);
-- C11_BOUNDARY
CREATE TABLE [dbo].[CRMCanalInstitucionalOperacionProveedor](
 [InstitutionId] uniqueidentifier NOT NULL,
 [OperationId] uniqueidentifier NOT NULL,
 [ApplicationId] uniqueidentifier NOT NULL,
 [IntegrationId] uniqueidentifier NULL,
 [EndpointId] uniqueidentifier NULL,
 [ActorRef] nvarchar(128) NOT NULL,
 [Action] varchar(48) NOT NULL,
 [RequestDigest] binary(32) NOT NULL,
 [Status] varchar(16) NOT NULL CONSTRAINT [DF_C11_ProviderOperation_Status] DEFAULT N'pending',
 [LeaseId] uniqueidentifier NULL,
 [LeaseUntil] datetime2(7) NULL,
 [LeaseVersion] bigint NOT NULL CONSTRAINT [DF_C11_ProviderOperation_LeaseVersion] DEFAULT 0,
 [Attempts] int NOT NULL CONSTRAINT [DF_C11_ProviderOperation_Attempts] DEFAULT 0,
 [ResultCode] varchar(64) NULL,
 [ResultMetadata] nvarchar(max) NOT NULL,
 [CreatedAt] datetime2(7) NOT NULL,
 [CompletedAt] datetime2(7) NULL,
 [RowVersion] rowversion NOT NULL,
 [EffectKey] binary(32) NOT NULL,
 CONSTRAINT [K_C11_ProviderOperation_0] PRIMARY KEY ([InstitutionId],[OperationId]),
 CONSTRAINT [K_C11_ProviderOperation_1] UNIQUE ([InstitutionId],[IntegrationId],[OperationId]),
 CONSTRAINT [K_C11_ProviderOperation_2] UNIQUE ([InstitutionId],[IntegrationId],[OperationId],[ApplicationId]),
 CONSTRAINT [K_C11_ProviderOperation_3] UNIQUE ([InstitutionId],[ApplicationId],[Action],[EffectKey]),
 CONSTRAINT [K_C11_ProviderOperation_4] UNIQUE ([InstitutionId],[OperationId],[ApplicationId]),
 CONSTRAINT [CK_C11_ProviderOperation_0] CHECK (Status IN('pending','running','confirmed','failed','uncertain','reconciled','abandoned')),
 CONSTRAINT [CK_C11_ProviderOperation_1] CHECK (LeaseVersion>=0 AND Attempts>=0),
 CONSTRAINT [CK_C11_ProviderOperation_2] CHECK (ISJSON([ResultMetadata])=1)
);
CREATE INDEX [IX_ProviderOperation_Work] ON [dbo].[CRMCanalInstitucionalOperacionProveedor] ([InstitutionId],[Status],[LeaseUntil]);
-- C11_BOUNDARY
CREATE TABLE [dbo].[CRMCanalInstitucionalActivoProveedor](
 [InstitutionId] uniqueidentifier NOT NULL,
 [AssetId] uniqueidentifier NOT NULL,
 [ApplicationId] uniqueidentifier NOT NULL,
 [OAuthSessionId] uniqueidentifier NULL,
 [Kind] varchar(24) NOT NULL,
 [ExternalId] nvarchar(200) COLLATE Latin1_General_100_BIN2 NOT NULL,
 [ParentExternalId] nvarchar(200) COLLATE Latin1_General_100_BIN2 NULL,
 [Name] nvarchar(200) NULL,
 [UserName] nvarchar(200) NULL,
 [ObservedScopes] nvarchar(max) NOT NULL,
 [Metadata] nvarchar(max) NOT NULL,
 [ObservedAt] datetime2(7) NOT NULL,
 [ExpiresAt] datetime2(7) NULL,
 [DiscoveryOperationId] uniqueidentifier NOT NULL,
 [IntegrationId] uniqueidentifier NULL,
 CONSTRAINT [K_C11_ProviderAsset_0] PRIMARY KEY ([InstitutionId],[AssetId]),
 CONSTRAINT [K_C11_ProviderAsset_1] UNIQUE ([InstitutionId],[DiscoveryOperationId],[Kind],[ExternalId]),
 CONSTRAINT [CK_C11_ProviderAsset_0] CHECK ([ExternalId] IS NULL OR (DATALENGTH([ExternalId])>0 AND DATALENGTH([ExternalId])=DATALENGTH(RTRIM([ExternalId])))),
 CONSTRAINT [CK_C11_ProviderAsset_1] CHECK ([ParentExternalId] IS NULL OR (DATALENGTH([ParentExternalId])>0 AND DATALENGTH([ParentExternalId])=DATALENGTH(RTRIM([ParentExternalId])))),
 CONSTRAINT [CK_C11_ProviderAsset_2] CHECK (ISJSON([ObservedScopes])=1),
 CONSTRAINT [CK_C11_ProviderAsset_3] CHECK (ISJSON([Metadata])=1)
);
-- C11_BOUNDARY
CREATE TABLE [dbo].[CRMCanalInstitucionalSecretoVersion](
 [InstitutionId] uniqueidentifier NOT NULL,
 [SecretId] uniqueidentifier NOT NULL,
 [ApplicationId] uniqueidentifier NULL,
 [IntegrationId] uniqueidentifier NULL,
 [EndpointId] uniqueidentifier NULL,
 [OAuthSessionId] uniqueidentifier NULL,
 [Kind] varchar(32) NOT NULL,
 [VersionNo] int NOT NULL,
 [State] varchar(12) NOT NULL CONSTRAINT [DF_C11_SecretVersion_State] DEFAULT N'staged',
 [KeyVersion] varchar(64) NOT NULL,
 [Nonce] binary(12) NOT NULL,
 [Ciphertext] varbinary(max) NOT NULL,
 [Hint] nvarchar(4) NULL,
 [Fingerprint] binary(32) NOT NULL,
 [ExpiresAt] datetime2(7) NULL,
 [GraceUntil] datetime2(7) NULL,
 [CreatedAt] datetime2(7) NOT NULL,
 [RevokedAt] datetime2(7) NULL,
 [RowVersion] rowversion NOT NULL,
 [AssetId] uniqueidentifier NULL,
 CONSTRAINT [K_C11_SecretVersion_0] PRIMARY KEY ([InstitutionId],[SecretId]),
 CONSTRAINT [K_C11_SecretVersion_1] UNIQUE ([KeyVersion],[Nonce]),
 CONSTRAINT [CK_C11_SecretVersion_0] CHECK (VersionNo>=1),
 CONSTRAINT [CK_C11_SecretVersion_1] CHECK (State IN('staged','active','grace','retired','revoked')),
 CONSTRAINT [CK_C11_SecretVersion_2] CHECK (DATALENGTH(Ciphertext)>16 AND DATALENGTH(Ciphertext)<=32784),
 CONSTRAINT [CK_C11_SecretVersion_3] CHECK (CASE WHEN ApplicationId IS NULL THEN 0 ELSE 1 END+CASE WHEN IntegrationId IS NULL THEN 0 ELSE 1 END+CASE WHEN EndpointId IS NULL THEN 0 ELSE 1 END+CASE WHEN OAuthSessionId IS NULL THEN 0 ELSE 1 END+CASE WHEN AssetId IS NULL THEN 0 ELSE 1 END=1),
 CONSTRAINT [CK_C11_SecretVersion_4] CHECK (State<>'grace' OR (EndpointId IS NOT NULL AND Kind IN('tiktok_webhook_secret','endpoint_hmac') AND GraceUntil IS NOT NULL)),
 CONSTRAINT [CK_C11_SecretVersion_5] CHECK ((ApplicationId IS NOT NULL AND Kind IN(N'meta_app_secret',N'instagram_app_secret',N'facebook_app_secret',N'tiktok_client_secret')) OR (IntegrationId IS NOT NULL AND Kind IN(N'meta_permanent_access',N'instagram_user_access',N'instagram_page_access',N'facebook_user_access',N'facebook_page_access',N'tiktok_access',N'tiktok_refresh')) OR (EndpointId IS NOT NULL AND Kind IN(N'webhook_verify',N'tiktok_webhook_secret',N'endpoint_hmac')) OR (OAuthSessionId IS NOT NULL AND Kind IN(N'oauth_pkce_verifier',N'oauth_provisional_access',N'oauth_provisional_refresh')) OR (AssetId IS NOT NULL AND Kind IN(N'oauth_asset_access')))
);
CREATE UNIQUE INDEX [UQ_Secret_Version_ApplicationId] ON [dbo].[CRMCanalInstitucionalSecretoVersion] ([InstitutionId],[ApplicationId],[Kind],[VersionNo]) WHERE ApplicationId IS NOT NULL;
CREATE UNIQUE INDEX [UQ_Secret_Version_IntegrationId] ON [dbo].[CRMCanalInstitucionalSecretoVersion] ([InstitutionId],[IntegrationId],[Kind],[VersionNo]) WHERE IntegrationId IS NOT NULL;
CREATE UNIQUE INDEX [UQ_Secret_Version_EndpointId] ON [dbo].[CRMCanalInstitucionalSecretoVersion] ([InstitutionId],[EndpointId],[Kind],[VersionNo]) WHERE EndpointId IS NOT NULL;
CREATE UNIQUE INDEX [UQ_Secret_Version_OAuthSessionId] ON [dbo].[CRMCanalInstitucionalSecretoVersion] ([InstitutionId],[OAuthSessionId],[Kind],[VersionNo]) WHERE OAuthSessionId IS NOT NULL;
CREATE UNIQUE INDEX [UQ_Secret_Version_AssetId] ON [dbo].[CRMCanalInstitucionalSecretoVersion] ([InstitutionId],[AssetId],[Kind],[VersionNo]) WHERE AssetId IS NOT NULL;
CREATE UNIQUE INDEX [UQ_Secret_Active_AssetId] ON [dbo].[CRMCanalInstitucionalSecretoVersion] ([InstitutionId],[AssetId],[Kind]) WHERE AssetId IS NOT NULL AND State='active';
CREATE UNIQUE INDEX [UQ_Secret_Active_ApplicationId] ON [dbo].[CRMCanalInstitucionalSecretoVersion] ([InstitutionId],[ApplicationId],[Kind]) WHERE ApplicationId IS NOT NULL AND State='active';
CREATE UNIQUE INDEX [UQ_Secret_Active_IntegrationId] ON [dbo].[CRMCanalInstitucionalSecretoVersion] ([InstitutionId],[IntegrationId],[Kind]) WHERE IntegrationId IS NOT NULL AND State='active';
CREATE UNIQUE INDEX [UQ_Secret_Active_EndpointId] ON [dbo].[CRMCanalInstitucionalSecretoVersion] ([InstitutionId],[EndpointId],[Kind]) WHERE EndpointId IS NOT NULL AND State='active';
CREATE UNIQUE INDEX [UQ_Secret_Active_OAuthSessionId] ON [dbo].[CRMCanalInstitucionalSecretoVersion] ([InstitutionId],[OAuthSessionId],[Kind]) WHERE OAuthSessionId IS NOT NULL AND State='active';
-- C11_BOUNDARY
ALTER TABLE [dbo].[CRMCanalInstitucionalSesionOAuth] WITH CHECK ADD CONSTRAINT [FK_C11_3] FOREIGN KEY([InstitutionId]) REFERENCES [dbo].[CRMCanalInstitucionalContexto]([InstitutionId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalWebhook] WITH CHECK ADD CONSTRAINT [FK_C11_4] FOREIGN KEY([InstitutionId]) REFERENCES [dbo].[CRMCanalInstitucionalContexto]([InstitutionId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalSecretoVersion] WITH CHECK ADD CONSTRAINT [FK_C11_5] FOREIGN KEY([InstitutionId]) REFERENCES [dbo].[CRMCanalInstitucionalContexto]([InstitutionId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalActivoProveedor] WITH CHECK ADD CONSTRAINT [FK_C11_6] FOREIGN KEY([InstitutionId]) REFERENCES [dbo].[CRMCanalInstitucionalContexto]([InstitutionId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalOperacionProveedor] WITH CHECK ADD CONSTRAINT [FK_C11_7] FOREIGN KEY([InstitutionId]) REFERENCES [dbo].[CRMCanalInstitucionalContexto]([InstitutionId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalSesionOAuth] WITH CHECK ADD CONSTRAINT [FK_C11_25] FOREIGN KEY([InstitutionId],[ApplicationId]) REFERENCES [dbo].[CRMCanalInstitucionalAplicacion]([InstitutionId],[ApplicationId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalActivoProveedor] WITH CHECK ADD CONSTRAINT [FK_C11_26] FOREIGN KEY([InstitutionId],[ApplicationId]) REFERENCES [dbo].[CRMCanalInstitucionalAplicacion]([InstitutionId],[ApplicationId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalOperacionProveedor] WITH CHECK ADD CONSTRAINT [FK_C11_27] FOREIGN KEY([InstitutionId],[ApplicationId]) REFERENCES [dbo].[CRMCanalInstitucionalAplicacion]([InstitutionId],[ApplicationId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalSecretoVersion] WITH CHECK ADD CONSTRAINT [FK_C11_37] FOREIGN KEY([InstitutionId],[ApplicationId]) REFERENCES [dbo].[CRMCanalInstitucionalAplicacion]([InstitutionId],[ApplicationId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalSecretoVersion] WITH CHECK ADD CONSTRAINT [FK_C11_38] FOREIGN KEY([InstitutionId],[IntegrationId]) REFERENCES [dbo].[CRMCanalInstitucionalIntegracion]([InstitutionId],[IntegrationId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalSecretoVersion] WITH CHECK ADD CONSTRAINT [FK_C11_39] FOREIGN KEY([InstitutionId],[EndpointId]) REFERENCES [dbo].[CRMCanalInstitucionalWebhook]([InstitutionId],[EndpointId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalSecretoVersion] WITH CHECK ADD CONSTRAINT [FK_C11_40] FOREIGN KEY([InstitutionId],[OAuthSessionId]) REFERENCES [dbo].[CRMCanalInstitucionalSesionOAuth]([InstitutionId],[OAuthSessionId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalSesionOAuth] WITH CHECK ADD CONSTRAINT [FK_C11_55] FOREIGN KEY([InstitutionId],[IntegrationId],[ApplicationId]) REFERENCES [dbo].[CRMCanalInstitucionalIntegracion]([InstitutionId],[IntegrationId],[ApplicationId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalOperacionProveedor] WITH CHECK ADD CONSTRAINT [FK_C11_56] FOREIGN KEY([InstitutionId],[IntegrationId],[ApplicationId]) REFERENCES [dbo].[CRMCanalInstitucionalIntegracion]([InstitutionId],[IntegrationId],[ApplicationId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalOperacionProveedor] WITH CHECK ADD CONSTRAINT [FK_C11_57] FOREIGN KEY([InstitutionId],[EndpointId],[ApplicationId]) REFERENCES [dbo].[CRMCanalInstitucionalWebhook]([InstitutionId],[EndpointId],[ApplicationId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalActivoProveedor] WITH CHECK ADD CONSTRAINT [FK_C11_58] FOREIGN KEY([InstitutionId],[OAuthSessionId],[IntegrationId],[ApplicationId]) REFERENCES [dbo].[CRMCanalInstitucionalSesionOAuth]([InstitutionId],[OAuthSessionId],[IntegrationId],[ApplicationId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalActivoProveedor] WITH CHECK ADD CONSTRAINT [FK_C11_59] FOREIGN KEY([InstitutionId],[IntegrationId],[DiscoveryOperationId],[ApplicationId]) REFERENCES [dbo].[CRMCanalInstitucionalOperacionProveedor]([InstitutionId],[IntegrationId],[OperationId],[ApplicationId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalSecretoVersion] WITH CHECK ADD CONSTRAINT [FK_C11_60] FOREIGN KEY([InstitutionId],[AssetId]) REFERENCES [dbo].[CRMCanalInstitucionalActivoProveedor]([InstitutionId],[AssetId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalSesionOAuth] WITH CHECK ADD CONSTRAINT [FK_C11_61] FOREIGN KEY([InstitutionId],[ClientSecretId]) REFERENCES [dbo].[CRMCanalInstitucionalSecretoVersion]([InstitutionId],[SecretId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalWebhook] WITH CHECK ADD CONSTRAINT [FK_C11_66] FOREIGN KEY([InstitutionId],[ApplicationId],[Provider]) REFERENCES [dbo].[CRMCanalInstitucionalAplicacion]([InstitutionId],[ApplicationId],[Provider]);
ALTER TABLE [dbo].[CRMCanalInstitucionalActivoProveedor] WITH CHECK ADD CONSTRAINT [FK_C11_73] FOREIGN KEY([InstitutionId],[OAuthSessionId],[ApplicationId]) REFERENCES [dbo].[CRMCanalInstitucionalSesionOAuth]([InstitutionId],[OAuthSessionId],[ApplicationId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalActivoProveedor] WITH CHECK ADD CONSTRAINT [FK_C11_74] FOREIGN KEY([InstitutionId],[DiscoveryOperationId],[ApplicationId]) REFERENCES [dbo].[CRMCanalInstitucionalOperacionProveedor]([InstitutionId],[OperationId],[ApplicationId]);

-- C11_BOUNDARY
CREATE TABLE [dbo].[CRMCanalInstitucionalPoliticaTikTok](
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
CREATE TABLE [dbo].[CRMCanalInstitucionalCuota](
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
CREATE TABLE [dbo].[CRMCanalInstitucionalCuotaReserva](
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
ALTER TABLE [dbo].[CRMCanalInstitucionalPoliticaTikTok] WITH CHECK ADD CONSTRAINT [FK_C11_8] FOREIGN KEY([InstitutionId]) REFERENCES [dbo].[CRMCanalInstitucionalContexto]([InstitutionId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalCuota] WITH CHECK ADD CONSTRAINT [FK_C11_10] FOREIGN KEY([InstitutionId]) REFERENCES [dbo].[CRMCanalInstitucionalContexto]([InstitutionId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalCuotaReserva] WITH CHECK ADD CONSTRAINT [FK_C11_11] FOREIGN KEY([InstitutionId]) REFERENCES [dbo].[CRMCanalInstitucionalContexto]([InstitutionId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalPoliticaTikTok] WITH CHECK ADD CONSTRAINT [FK_C11_28] FOREIGN KEY([InstitutionId],[IntegrationId]) REFERENCES [dbo].[CRMCanalInstitucionalIntegracion]([InstitutionId],[IntegrationId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalCuota] WITH CHECK ADD CONSTRAINT [FK_C11_29] FOREIGN KEY([InstitutionId],[IntegrationId]) REFERENCES [dbo].[CRMCanalInstitucionalIntegracion]([InstitutionId],[IntegrationId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalCuotaReserva] WITH CHECK ADD CONSTRAINT [FK_C11_30] FOREIGN KEY([InstitutionId],[IntegrationId]) REFERENCES [dbo].[CRMCanalInstitucionalIntegracion]([InstitutionId],[IntegrationId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalCuotaReserva] WITH CHECK ADD CONSTRAINT [FK_C11_62] FOREIGN KEY([InstitutionId],[IntegrationId],[OperationId]) REFERENCES [dbo].[CRMCanalInstitucionalOperacionProveedor]([InstitutionId],[IntegrationId],[OperationId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalCuotaReserva] WITH CHECK ADD CONSTRAINT [FK_C11_63] FOREIGN KEY([InstitutionId],[IntegrationId],[DayUtc],[Action]) REFERENCES [dbo].[CRMCanalInstitucionalCuota]([InstitutionId],[IntegrationId],[DayUtc],[Action]);

-- C11_BOUNDARY
CREATE TABLE [dbo].[CRMCanalInstitucionalWebhookIntegracion](
 [InstitutionId] uniqueidentifier NOT NULL,
 [EndpointId] uniqueidentifier NOT NULL,
 [IntegrationId] uniqueidentifier NOT NULL,
 [ApplicationId] uniqueidentifier NOT NULL,
 [RouteKind] varchar(24) NOT NULL,
 [ExternalId] nvarchar(200) COLLATE Latin1_General_100_BIN2 NOT NULL,
 [IsActive] bit NOT NULL CONSTRAINT [DF_C11_EndpointIntegration_IsActive] DEFAULT 0,
 [CreatedAt] datetime2(7) NOT NULL,
 [RowVersion] rowversion NOT NULL,
 CONSTRAINT [K_C11_EndpointIntegration_0] PRIMARY KEY ([InstitutionId],[EndpointId],[IntegrationId],[RouteKind],[ExternalId]),
 CONSTRAINT [K_C11_EndpointIntegration_1] UNIQUE ([InstitutionId],[EndpointId],[RouteKind],[ExternalId]),
 CONSTRAINT [CK_C11_EndpointIntegration_0] CHECK ([ExternalId] IS NULL OR (DATALENGTH([ExternalId])>0 AND DATALENGTH([ExternalId])=DATALENGTH(RTRIM([ExternalId]))))
);
-- C11_BOUNDARY
CREATE TABLE [dbo].[CRMCanalInstitucionalWebhookRecepcion](
 [InstitutionId] uniqueidentifier NOT NULL,
 [ReceiptId] uniqueidentifier NOT NULL,
 [EndpointId] uniqueidentifier NOT NULL,
 [Digest] binary(32) NOT NULL,
 [BodyKeyVersion] varchar(64) NULL,
 [BodyNonce] binary(12) NULL,
 [BodyCiphertext] varbinary(max) NULL,
 [SignatureKeyVersion] varchar(64) NOT NULL,
 [SignatureProfile] varchar(64) NOT NULL,
 [Authentication] varchar(20) NOT NULL,
 [Status] varchar(16) NOT NULL CONSTRAINT [DF_C11_WebhookReceipt_Status] DEFAULT N'queued',
 [ReceivedAt] datetime2(7) NOT NULL,
 [ExpiresAt] datetime2(7) NOT NULL,
 [LeaseId] uniqueidentifier NULL,
 [LeaseUntil] datetime2(7) NULL,
 [LeaseVersion] bigint NOT NULL CONSTRAINT [DF_C11_WebhookReceipt_LeaseVersion] DEFAULT 0,
 [Attempts] int NOT NULL CONSTRAINT [DF_C11_WebhookReceipt_Attempts] DEFAULT 0,
 [LastErrorCode] varchar(64) NULL,
 [RowVersion] rowversion NOT NULL,
 [ApplicationId] uniqueidentifier NOT NULL,
 [EndpointVersion] binary(8) NOT NULL,
 [SignatureSecretId] uniqueidentifier NULL,
 [SignatureVerifiedAt] datetime2(7) NULL,
 [BodyPurgedAt] datetime2(7) NULL,
 CONSTRAINT [K_C11_WebhookReceipt_0] PRIMARY KEY ([InstitutionId],[ReceiptId]),
 CONSTRAINT [K_C11_WebhookReceipt_1] UNIQUE ([InstitutionId],[EndpointId],[Digest]),
 CONSTRAINT [K_C11_WebhookReceipt_2] UNIQUE ([InstitutionId],[ReceiptId],[EndpointId],[ApplicationId]),
 CONSTRAINT [CK_C11_WebhookReceipt_0] CHECK (Authentication IN('verified','legacy_unverified')),
 CONSTRAINT [CK_C11_WebhookReceipt_1] CHECK ((Authentication='verified' AND SignatureSecretId IS NOT NULL AND SignatureVerifiedAt IS NOT NULL) OR (Authentication='legacy_unverified' AND SignatureVerifiedAt IS NULL)),
 CONSTRAINT [CK_C11_WebhookReceipt_2] CHECK ((BodyPurgedAt IS NULL AND BodyKeyVersion IS NOT NULL AND BodyNonce IS NOT NULL AND BodyCiphertext IS NOT NULL) OR (BodyPurgedAt IS NOT NULL AND BodyKeyVersion IS NULL AND BodyNonce IS NULL AND BodyCiphertext IS NULL)),
 CONSTRAINT [CK_C11_WebhookReceipt_3] CHECK (BodyCiphertext IS NULL OR DATALENGTH(BodyCiphertext)<=1000016),
 CONSTRAINT [CK_C11_WebhookReceipt_4] CHECK (BodyPurgedAt IS NULL OR (Status IN('processed','quarantined','failed') AND LeaseId IS NULL AND LeaseUntil IS NULL)),
 CONSTRAINT [CK_C11_WebhookReceipt_5] CHECK (Authentication<>'legacy_unverified' OR Status='quarantined'),
 CONSTRAINT [CK_C11_WebhookReceipt_6] CHECK (LeaseVersion>=0 AND Attempts>=0)
);
CREATE UNIQUE INDEX [UQ_Receipt_BodyNonce] ON [dbo].[CRMCanalInstitucionalWebhookRecepcion] ([BodyKeyVersion],[BodyNonce]) WHERE BodyKeyVersion IS NOT NULL AND BodyNonce IS NOT NULL;
CREATE INDEX [IX_WebhookReceipt_Work] ON [dbo].[CRMCanalInstitucionalWebhookRecepcion] ([InstitutionId],[Status],[LeaseUntil]);
-- C11_BOUNDARY
CREATE TABLE [dbo].[CRMCanalInstitucionalWebhookEvento](
 [InstitutionId] uniqueidentifier NOT NULL,
 [EventId] uniqueidentifier NOT NULL,
 [ReceiptId] uniqueidentifier NOT NULL,
 [IntegrationId] uniqueidentifier NULL,
 [SubeventPath] nvarchar(200) NOT NULL,
 [Kind] varchar(32) NOT NULL,
 [ProviderEventId] nvarchar(200) NULL,
 [DedupeKey] binary(32) NOT NULL,
 [IdentityStrength] varchar(16) NOT NULL,
 [Status] varchar(16) NOT NULL CONSTRAINT [DF_C11_WebhookEvent_Status] DEFAULT N'quarantined',
 [Payload] nvarchar(max) NOT NULL,
 [ProviderOccurredAt] datetime2(7) NULL,
 [CreatedAt] datetime2(7) NOT NULL,
 [LeaseId] uniqueidentifier NULL,
 [LeaseUntil] datetime2(7) NULL,
 [LeaseVersion] bigint NOT NULL CONSTRAINT [DF_C11_WebhookEvent_LeaseVersion] DEFAULT 0,
 [Attempts] int NOT NULL CONSTRAINT [DF_C11_WebhookEvent_Attempts] DEFAULT 0,
 [LastErrorCode] varchar(64) NULL,
 [RowVersion] rowversion NOT NULL,
 [ApplicationId] uniqueidentifier NOT NULL,
 [EndpointId] uniqueidentifier NOT NULL,
 [RouteKind] varchar(24) NOT NULL,
 [RouteExternalId] nvarchar(200) COLLATE Latin1_General_100_BIN2 NOT NULL,
 CONSTRAINT [K_C11_WebhookEvent_0] PRIMARY KEY ([InstitutionId],[EventId]),
 CONSTRAINT [K_C11_WebhookEvent_1] UNIQUE ([InstitutionId],[ReceiptId],[SubeventPath]),
 CONSTRAINT [K_C11_WebhookEvent_2] UNIQUE ([InstitutionId],[EventId],[IntegrationId]),
 CONSTRAINT [K_C11_WebhookEvent_3] UNIQUE ([InstitutionId],[EventId],[IntegrationId],[ReceiptId],[EndpointId],[ApplicationId]),
 CONSTRAINT [CK_C11_WebhookEvent_0] CHECK (IntegrationId IS NOT NULL OR Status='quarantined'),
 CONSTRAINT [CK_C11_WebhookEvent_1] CHECK (LeaseVersion>=0 AND Attempts>=0),
 CONSTRAINT [CK_C11_WebhookEvent_2] CHECK (ISJSON([Payload])=1),
 CONSTRAINT [CK_C11_WebhookEvent_3] CHECK ([RouteExternalId] IS NULL OR (DATALENGTH([RouteExternalId])>0 AND DATALENGTH([RouteExternalId])=DATALENGTH(RTRIM([RouteExternalId]))))
);
CREATE UNIQUE INDEX [UQ_Event_Integration_Dedupe] ON [dbo].[CRMCanalInstitucionalWebhookEvento] ([InstitutionId],[IntegrationId],[DedupeKey]) WHERE IntegrationId IS NOT NULL;
CREATE INDEX [IX_WebhookEvent_Work] ON [dbo].[CRMCanalInstitucionalWebhookEvento] ([InstitutionId],[Status],[LeaseUntil]);
-- C11_BOUNDARY
CREATE TABLE [dbo].[CRMCanalInstitucionalEvidenciaVerificacion](
 [InstitutionId] uniqueidentifier NOT NULL,
 [EvidenceId] uniqueidentifier NOT NULL,
 [IntegrationId] uniqueidentifier NOT NULL,
 [EndpointId] uniqueidentifier NULL,
 [OperationId] uniqueidentifier NULL,
 [Kind] varchar(32) NOT NULL,
 [Origin] varchar(16) NOT NULL,
 [Result] varchar(16) NOT NULL,
 [SubjectVersion] binary(8) NOT NULL,
 [EvidenceDigest] binary(32) NOT NULL,
 [ObservedAt] datetime2(7) NOT NULL,
 [ExpiresAt] datetime2(7) NOT NULL,
 [Summary] nvarchar(max) NOT NULL,
 [ReceiptId] uniqueidentifier NULL,
 [EventId] uniqueidentifier NULL,
 [ApplicationId] uniqueidentifier NOT NULL,
 CONSTRAINT [K_C11_VerificationEvidence_0] PRIMARY KEY ([InstitutionId],[EvidenceId]),
 CONSTRAINT [CK_C11_VerificationEvidence_0] CHECK (EventId IS NULL OR (ReceiptId IS NOT NULL AND EndpointId IS NOT NULL)),
 CONSTRAINT [CK_C11_VerificationEvidence_1] CHECK (ISJSON([Summary])=1)
);
-- C11_BOUNDARY
ALTER TABLE [dbo].[CRMCanalInstitucionalEvidenciaVerificacion] WITH CHECK ADD CONSTRAINT [FK_C11_9] FOREIGN KEY([InstitutionId]) REFERENCES [dbo].[CRMCanalInstitucionalContexto]([InstitutionId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalWebhookIntegracion] WITH CHECK ADD CONSTRAINT [FK_C11_12] FOREIGN KEY([InstitutionId]) REFERENCES [dbo].[CRMCanalInstitucionalContexto]([InstitutionId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalWebhookRecepcion] WITH CHECK ADD CONSTRAINT [FK_C11_13] FOREIGN KEY([InstitutionId]) REFERENCES [dbo].[CRMCanalInstitucionalContexto]([InstitutionId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalWebhookEvento] WITH CHECK ADD CONSTRAINT [FK_C11_14] FOREIGN KEY([InstitutionId]) REFERENCES [dbo].[CRMCanalInstitucionalContexto]([InstitutionId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalEvidenciaVerificacion] WITH CHECK ADD CONSTRAINT [FK_C11_41] FOREIGN KEY([InstitutionId],[EndpointId]) REFERENCES [dbo].[CRMCanalInstitucionalWebhook]([InstitutionId],[EndpointId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalWebhookIntegracion] WITH CHECK ADD CONSTRAINT [FK_C11_42] FOREIGN KEY([InstitutionId],[EndpointId],[ApplicationId]) REFERENCES [dbo].[CRMCanalInstitucionalWebhook]([InstitutionId],[EndpointId],[ApplicationId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalWebhookIntegracion] WITH CHECK ADD CONSTRAINT [FK_C11_43] FOREIGN KEY([InstitutionId],[IntegrationId],[ApplicationId]) REFERENCES [dbo].[CRMCanalInstitucionalIntegracion]([InstitutionId],[IntegrationId],[ApplicationId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalWebhookRecepcion] WITH CHECK ADD CONSTRAINT [FK_C11_67] FOREIGN KEY([InstitutionId],[EndpointId],[ApplicationId]) REFERENCES [dbo].[CRMCanalInstitucionalWebhook]([InstitutionId],[EndpointId],[ApplicationId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalWebhookRecepcion] WITH CHECK ADD CONSTRAINT [FK_C11_68] FOREIGN KEY([InstitutionId],[SignatureSecretId]) REFERENCES [dbo].[CRMCanalInstitucionalSecretoVersion]([InstitutionId],[SecretId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalWebhookEvento] WITH CHECK ADD CONSTRAINT [FK_C11_69] FOREIGN KEY([InstitutionId],[ReceiptId],[EndpointId],[ApplicationId]) REFERENCES [dbo].[CRMCanalInstitucionalWebhookRecepcion]([InstitutionId],[ReceiptId],[EndpointId],[ApplicationId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalWebhookEvento] WITH CHECK ADD CONSTRAINT [FK_C11_70] FOREIGN KEY([InstitutionId],[IntegrationId],[ApplicationId]) REFERENCES [dbo].[CRMCanalInstitucionalIntegracion]([InstitutionId],[IntegrationId],[ApplicationId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalWebhookEvento] WITH CHECK ADD CONSTRAINT [FK_C11_71] FOREIGN KEY([InstitutionId],[EndpointId],[IntegrationId],[RouteKind],[RouteExternalId]) REFERENCES [dbo].[CRMCanalInstitucionalWebhookIntegracion]([InstitutionId],[EndpointId],[IntegrationId],[RouteKind],[ExternalId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalEvidenciaVerificacion] WITH CHECK ADD CONSTRAINT [FK_C11_72] FOREIGN KEY([InstitutionId],[ReceiptId]) REFERENCES [dbo].[CRMCanalInstitucionalWebhookRecepcion]([InstitutionId],[ReceiptId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalEvidenciaVerificacion] WITH CHECK ADD CONSTRAINT [FK_C11_75] FOREIGN KEY([InstitutionId],[IntegrationId],[ApplicationId]) REFERENCES [dbo].[CRMCanalInstitucionalIntegracion]([InstitutionId],[IntegrationId],[ApplicationId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalEvidenciaVerificacion] WITH CHECK ADD CONSTRAINT [FK_C11_76] FOREIGN KEY([InstitutionId],[IntegrationId],[OperationId],[ApplicationId]) REFERENCES [dbo].[CRMCanalInstitucionalOperacionProveedor]([InstitutionId],[IntegrationId],[OperationId],[ApplicationId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalEvidenciaVerificacion] WITH CHECK ADD CONSTRAINT [FK_C11_77] FOREIGN KEY([InstitutionId],[EventId],[IntegrationId],[ReceiptId],[EndpointId],[ApplicationId]) REFERENCES [dbo].[CRMCanalInstitucionalWebhookEvento]([InstitutionId],[EventId],[IntegrationId],[ReceiptId],[EndpointId],[ApplicationId]);

-- C11_BOUNDARY
CREATE TABLE [dbo].[CRMCanalInstitucionalPerfilConversacion](
 [InstitutionId] uniqueidentifier NOT NULL,
 [ConversationId] uniqueidentifier NOT NULL,
 [LeadScore] tinyint NULL,
 [Temperature] varchar(4) NULL,
 [UpdatedAt] datetime2(7) NOT NULL,
 [RowVersion] rowversion NOT NULL,
 CONSTRAINT [K_C11_ConversationProfile_0] PRIMARY KEY ([InstitutionId],[ConversationId]),
 CONSTRAINT [CK_C11_ConversationProfile_0] CHECK (LeadScore IS NULL OR LeadScore BETWEEN 0 AND 100),
 CONSTRAINT [CK_C11_ConversationProfile_1] CHECK (Temperature IS NULL OR Temperature IN('cold','warm','hot'))
);
-- C11_BOUNDARY
CREATE TABLE [dbo].[CRMCanalInstitucionalControlConversacion](
 [InstitutionId] uniqueidentifier NOT NULL,
 [ConversationId] uniqueidentifier NOT NULL,
 [Epoch] bigint NOT NULL CONSTRAINT [DF_C11_ConversationControl_Epoch] DEFAULT 0,
 [ReadSequence] bigint NOT NULL CONSTRAINT [DF_C11_ConversationControl_ReadSequence] DEFAULT 0,
 [UpdatedAt] datetime2(7) NOT NULL,
 [RowVersion] rowversion NOT NULL,
 CONSTRAINT [K_C11_ConversationControl_0] PRIMARY KEY ([InstitutionId],[ConversationId]),
 CONSTRAINT [CK_C11_ConversationControl_0] CHECK (Epoch>=0 AND ReadSequence>=0)
);
-- C11_BOUNDARY
CREATE TABLE [dbo].[CRMCanalInstitucionalIdentidadExterna](
 [InstitutionId] uniqueidentifier NOT NULL,
 [IdentityId] uniqueidentifier NOT NULL,
 [IntegrationId] uniqueidentifier NOT NULL,
 [ExternalId] nvarchar(200) COLLATE Latin1_General_100_BIN2 NOT NULL,
 [ContactId] uniqueidentifier NOT NULL,
 [ConversationId] uniqueidentifier NOT NULL,
 [LastIncomingAt] datetime2(7) NULL,
 [CreatedAt] datetime2(7) NOT NULL,
 [RowVersion] rowversion NOT NULL,
 CONSTRAINT [K_C11_ExternalIdentity_0] PRIMARY KEY ([InstitutionId],[IdentityId]),
 CONSTRAINT [K_C11_ExternalIdentity_1] UNIQUE ([InstitutionId],[IntegrationId],[ExternalId]),
 CONSTRAINT [K_C11_ExternalIdentity_2] UNIQUE ([InstitutionId],[IntegrationId],[IdentityId]),
 CONSTRAINT [CK_C11_ExternalIdentity_0] CHECK ([ExternalId] IS NULL OR (DATALENGTH([ExternalId])>0 AND DATALENGTH([ExternalId])=DATALENGTH(RTRIM([ExternalId]))))
);
-- C11_BOUNDARY
CREATE TABLE [dbo].[CRMCanalInstitucionalMensajeExterno](
 [InstitutionId] uniqueidentifier NOT NULL,
 [ExternalMessageId] uniqueidentifier NOT NULL,
 [IntegrationId] uniqueidentifier NOT NULL,
 [ExternalId] nvarchar(200) COLLATE Latin1_General_100_BIN2 NOT NULL,
 [MessageId] uniqueidentifier NULL,
 [Payload] nvarchar(max) NOT NULL,
 [CreatedAt] datetime2(7) NOT NULL,
 [RowVersion] rowversion NOT NULL,
 CONSTRAINT [K_C11_ExternalMessage_0] PRIMARY KEY ([InstitutionId],[ExternalMessageId]),
 CONSTRAINT [K_C11_ExternalMessage_1] UNIQUE ([InstitutionId],[IntegrationId],[ExternalId]),
 CONSTRAINT [CK_C11_ExternalMessage_0] CHECK ([ExternalId] IS NULL OR (DATALENGTH([ExternalId])>0 AND DATALENGTH([ExternalId])=DATALENGTH(RTRIM([ExternalId])))),
 CONSTRAINT [CK_C11_ExternalMessage_1] CHECK (ISJSON([Payload])=1)
);
-- C11_BOUNDARY
CREATE TABLE [dbo].[CRMCanalInstitucionalComentarioSocial](
 [InstitutionId] uniqueidentifier NOT NULL,
 [CommentId] uniqueidentifier NOT NULL,
 [IntegrationId] uniqueidentifier NOT NULL,
 [ExternalId] nvarchar(200) COLLATE Latin1_General_100_BIN2 NOT NULL,
 [AuthorExternalId] nvarchar(200) COLLATE Latin1_General_100_BIN2 NOT NULL,
 [Body] nvarchar(max) NOT NULL,
 [Payload] nvarchar(max) NOT NULL,
 [ReceivedAt] datetime2(7) NOT NULL,
 [RowVersion] rowversion NOT NULL,
 CONSTRAINT [K_C11_SocialComment_0] PRIMARY KEY ([InstitutionId],[CommentId]),
 CONSTRAINT [K_C11_SocialComment_1] UNIQUE ([InstitutionId],[IntegrationId],[ExternalId]),
 CONSTRAINT [K_C11_SocialComment_2] UNIQUE ([InstitutionId],[IntegrationId],[CommentId]),
 CONSTRAINT [CK_C11_SocialComment_0] CHECK ([ExternalId] IS NULL OR (DATALENGTH([ExternalId])>0 AND DATALENGTH([ExternalId])=DATALENGTH(RTRIM([ExternalId])))),
 CONSTRAINT [CK_C11_SocialComment_1] CHECK ([AuthorExternalId] IS NULL OR (DATALENGTH([AuthorExternalId])>0 AND DATALENGTH([AuthorExternalId])=DATALENGTH(RTRIM([AuthorExternalId])))),
 CONSTRAINT [CK_C11_SocialComment_2] CHECK (ISJSON([Payload])=1)
);
-- C11_BOUNDARY
CREATE TABLE [dbo].[CRMCanalInstitucionalEnvioTrabajo](
 [InstitutionId] uniqueidentifier NOT NULL,
 [QueueId] uniqueidentifier NOT NULL,
 [IntegrationId] uniqueidentifier NOT NULL,
 [IdentityId] uniqueidentifier NULL,
 [MessageId] uniqueidentifier NULL,
 [CommentId] uniqueidentifier NULL,
 [OperationId] uniqueidentifier NOT NULL,
 [ReservationId] uniqueidentifier NULL,
 [Kind] varchar(16) NOT NULL,
 [State] varchar(16) NOT NULL CONSTRAINT [DF_C11_SendJob_State] DEFAULT N'queued',
 [Payload] nvarchar(max) NOT NULL,
 [ExternalId] nvarchar(200) COLLATE Latin1_General_100_BIN2 NULL,
 [LeaseId] uniqueidentifier NULL,
 [LeaseUntil] datetime2(7) NULL,
 [LeaseVersion] bigint NOT NULL CONSTRAINT [DF_C11_SendJob_LeaseVersion] DEFAULT 0,
 [DueAt] datetime2(7) NOT NULL,
 [Attempts] int NOT NULL CONSTRAINT [DF_C11_SendJob_Attempts] DEFAULT 0,
 [LastErrorCode] varchar(64) NULL,
 [CreatedAt] datetime2(7) NOT NULL,
 [CompletedAt] datetime2(7) NULL,
 [RowVersion] rowversion NOT NULL,
 CONSTRAINT [K_C11_SendJob_0] PRIMARY KEY ([InstitutionId],[QueueId]),
 CONSTRAINT [K_C11_SendJob_1] UNIQUE ([InstitutionId],[IntegrationId],[OperationId]),
 CONSTRAINT [K_C11_SendJob_2] UNIQUE ([InstitutionId],[IntegrationId],[QueueId],[IdentityId],[MessageId]),
 CONSTRAINT [CK_C11_SendJob_0] CHECK ((Kind='chat' AND IdentityId IS NOT NULL AND MessageId IS NOT NULL AND CommentId IS NULL) OR (Kind='comment_reply' AND CommentId IS NOT NULL AND IdentityId IS NULL AND MessageId IS NULL)),
 CONSTRAINT [CK_C11_SendJob_1] CHECK (LeaseVersion>=0 AND Attempts>=0),
 CONSTRAINT [CK_C11_SendJob_2] CHECK (ISJSON([Payload])=1),
 CONSTRAINT [CK_C11_SendJob_3] CHECK ([ExternalId] IS NULL OR (DATALENGTH([ExternalId])>0 AND DATALENGTH([ExternalId])=DATALENGTH(RTRIM([ExternalId]))))
);
CREATE INDEX [IX_SendJob_Work] ON [dbo].[CRMCanalInstitucionalEnvioTrabajo] ([InstitutionId],[IntegrationId],[State],[DueAt]);
-- C11_BOUNDARY
CREATE TABLE [dbo].[CRMCanalInstitucionalRutaMensaje](
 [InstitutionId] uniqueidentifier NOT NULL,
 [MessageId] uniqueidentifier NOT NULL,
 [IntegrationId] uniqueidentifier NOT NULL,
 [IdentityId] uniqueidentifier NOT NULL,
 [QueueId] uniqueidentifier NULL,
 [ActorKind] varchar(8) NOT NULL,
 [ControlEpoch] bigint NULL,
 [StartedAt] datetime2(7) NULL,
 [CompletedAt] datetime2(7) NULL,
 [RowVersion] rowversion NOT NULL,
 CONSTRAINT [K_C11_MessageRoute_0] PRIMARY KEY ([InstitutionId],[MessageId]),
 CONSTRAINT [CK_C11_MessageRoute_0] CHECK ((ActorKind='bot' AND ControlEpoch IS NOT NULL AND ControlEpoch>=0) OR (ActorKind IN('human','external') AND ControlEpoch IS NULL)),
 CONSTRAINT [CK_C11_MessageRoute_1] CHECK ((ActorKind='external' AND QueueId IS NULL) OR (ActorKind IN('human','bot') AND QueueId IS NOT NULL))
);
CREATE UNIQUE INDEX [UQ_Route_Queue] ON [dbo].[CRMCanalInstitucionalRutaMensaje] ([InstitutionId],[QueueId]) WHERE QueueId IS NOT NULL;
-- C11_BOUNDARY
CREATE TABLE [dbo].[CRMCanalInstitucionalVinculoOrigen](
 [InstitutionId] uniqueidentifier NOT NULL,
 [BindingId] uniqueidentifier NOT NULL,
 [LegacyTable] varchar(64) NOT NULL,
 [LegacyKeyHash] binary(32) NOT NULL,
 [LegacyKeyJson] nvarchar(max) NOT NULL,
 [SourceRowSha256] binary(32) NOT NULL,
 [IntegrationId] uniqueidentifier NOT NULL,
 [TargetKeyJson] nvarchar(max) NOT NULL,
 [TargetRowSha256] binary(32) NOT NULL,
 [MigrationUnit] varchar(32) NOT NULL,
 [CreatedAt] datetime2(7) NOT NULL,
 CONSTRAINT [K_C11_LegacyBinding_0] PRIMARY KEY ([InstitutionId],[BindingId]),
 CONSTRAINT [K_C11_LegacyBinding_1] UNIQUE ([InstitutionId],[LegacyTable],[LegacyKeyHash]),
 CONSTRAINT [CK_C11_LegacyBinding_0] CHECK (LegacyTable IN('crm_channels.Account','crm_channels.Credential','crm_channels.webhook_events','crm_channels.Audit','crm_channels.ExternalIdentity','crm_channels.ExternalMessage','crm_channels.outbound_queue','crm_channels.social_comments')),
 CONSTRAINT [CK_C11_LegacyBinding_1] CHECK (ISJSON([LegacyKeyJson])=1),
 CONSTRAINT [CK_C11_LegacyBinding_2] CHECK (ISJSON([TargetKeyJson])=1)
);
-- C11_BOUNDARY
ALTER TABLE [dbo].[CRMCanalInstitucionalPerfilConversacion] WITH CHECK ADD CONSTRAINT [FK_C11_15] FOREIGN KEY([InstitutionId]) REFERENCES [dbo].[CRMCanalInstitucionalContexto]([InstitutionId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalControlConversacion] WITH CHECK ADD CONSTRAINT [FK_C11_16] FOREIGN KEY([InstitutionId]) REFERENCES [dbo].[CRMCanalInstitucionalContexto]([InstitutionId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalIdentidadExterna] WITH CHECK ADD CONSTRAINT [FK_C11_17] FOREIGN KEY([InstitutionId]) REFERENCES [dbo].[CRMCanalInstitucionalContexto]([InstitutionId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalMensajeExterno] WITH CHECK ADD CONSTRAINT [FK_C11_18] FOREIGN KEY([InstitutionId]) REFERENCES [dbo].[CRMCanalInstitucionalContexto]([InstitutionId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalComentarioSocial] WITH CHECK ADD CONSTRAINT [FK_C11_19] FOREIGN KEY([InstitutionId]) REFERENCES [dbo].[CRMCanalInstitucionalContexto]([InstitutionId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalEnvioTrabajo] WITH CHECK ADD CONSTRAINT [FK_C11_20] FOREIGN KEY([InstitutionId]) REFERENCES [dbo].[CRMCanalInstitucionalContexto]([InstitutionId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalRutaMensaje] WITH CHECK ADD CONSTRAINT [FK_C11_21] FOREIGN KEY([InstitutionId]) REFERENCES [dbo].[CRMCanalInstitucionalContexto]([InstitutionId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalVinculoOrigen] WITH CHECK ADD CONSTRAINT [FK_C11_22] FOREIGN KEY([InstitutionId]) REFERENCES [dbo].[CRMCanalInstitucionalContexto]([InstitutionId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalIdentidadExterna] WITH CHECK ADD CONSTRAINT [FK_C11_31] FOREIGN KEY([InstitutionId],[IntegrationId]) REFERENCES [dbo].[CRMCanalInstitucionalIntegracion]([InstitutionId],[IntegrationId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalMensajeExterno] WITH CHECK ADD CONSTRAINT [FK_C11_32] FOREIGN KEY([InstitutionId],[IntegrationId]) REFERENCES [dbo].[CRMCanalInstitucionalIntegracion]([InstitutionId],[IntegrationId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalComentarioSocial] WITH CHECK ADD CONSTRAINT [FK_C11_33] FOREIGN KEY([InstitutionId],[IntegrationId]) REFERENCES [dbo].[CRMCanalInstitucionalIntegracion]([InstitutionId],[IntegrationId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalEnvioTrabajo] WITH CHECK ADD CONSTRAINT [FK_C11_34] FOREIGN KEY([InstitutionId],[IntegrationId]) REFERENCES [dbo].[CRMCanalInstitucionalIntegracion]([InstitutionId],[IntegrationId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalRutaMensaje] WITH CHECK ADD CONSTRAINT [FK_C11_35] FOREIGN KEY([InstitutionId],[IntegrationId]) REFERENCES [dbo].[CRMCanalInstitucionalIntegracion]([InstitutionId],[IntegrationId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalVinculoOrigen] WITH CHECK ADD CONSTRAINT [FK_C11_36] FOREIGN KEY([InstitutionId],[IntegrationId]) REFERENCES [dbo].[CRMCanalInstitucionalIntegracion]([InstitutionId],[IntegrationId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalPerfilConversacion] WITH CHECK ADD CONSTRAINT [FK_C11_44] FOREIGN KEY([ConversationId]) REFERENCES [dbo].[CRMConversacion]([ConversationId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalControlConversacion] WITH CHECK ADD CONSTRAINT [FK_C11_45] FOREIGN KEY([ConversationId]) REFERENCES [dbo].[CRMConversacion]([ConversationId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalIdentidadExterna] WITH CHECK ADD CONSTRAINT [FK_C11_46] FOREIGN KEY([ConversationId]) REFERENCES [dbo].[CRMConversacion]([ConversationId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalIdentidadExterna] WITH CHECK ADD CONSTRAINT [FK_C11_47] FOREIGN KEY([ContactId]) REFERENCES [dbo].[CRMContacto]([ContactId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalMensajeExterno] WITH CHECK ADD CONSTRAINT [FK_C11_48] FOREIGN KEY([MessageId]) REFERENCES [dbo].[CRMMensaje]([MessageId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalEnvioTrabajo] WITH CHECK ADD CONSTRAINT [FK_C11_49] FOREIGN KEY([MessageId]) REFERENCES [dbo].[CRMMensaje]([MessageId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalRutaMensaje] WITH CHECK ADD CONSTRAINT [FK_C11_50] FOREIGN KEY([MessageId]) REFERENCES [dbo].[CRMMensaje]([MessageId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalEnvioTrabajo] WITH CHECK ADD CONSTRAINT [FK_C11_51] FOREIGN KEY([InstitutionId],[IntegrationId],[IdentityId]) REFERENCES [dbo].[CRMCanalInstitucionalIdentidadExterna]([InstitutionId],[IntegrationId],[IdentityId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalEnvioTrabajo] WITH CHECK ADD CONSTRAINT [FK_C11_52] FOREIGN KEY([InstitutionId],[IntegrationId],[CommentId]) REFERENCES [dbo].[CRMCanalInstitucionalComentarioSocial]([InstitutionId],[IntegrationId],[CommentId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalRutaMensaje] WITH CHECK ADD CONSTRAINT [FK_C11_53] FOREIGN KEY([InstitutionId],[IntegrationId],[IdentityId]) REFERENCES [dbo].[CRMCanalInstitucionalIdentidadExterna]([InstitutionId],[IntegrationId],[IdentityId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalRutaMensaje] WITH CHECK ADD CONSTRAINT [FK_C11_54] FOREIGN KEY([InstitutionId],[IntegrationId],[QueueId],[IdentityId],[MessageId]) REFERENCES [dbo].[CRMCanalInstitucionalEnvioTrabajo]([InstitutionId],[IntegrationId],[QueueId],[IdentityId],[MessageId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalEnvioTrabajo] WITH CHECK ADD CONSTRAINT [FK_C11_64] FOREIGN KEY([InstitutionId],[IntegrationId],[OperationId]) REFERENCES [dbo].[CRMCanalInstitucionalOperacionProveedor]([InstitutionId],[IntegrationId],[OperationId]);
ALTER TABLE [dbo].[CRMCanalInstitucionalEnvioTrabajo] WITH CHECK ADD CONSTRAINT [FK_C11_65] FOREIGN KEY([InstitutionId],[IntegrationId],[ReservationId],[OperationId]) REFERENCES [dbo].[CRMCanalInstitucionalCuotaReserva]([InstitutionId],[IntegrationId],[ReservationId],[OperationId]);
