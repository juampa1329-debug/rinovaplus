-- SQL-C11 immutable restored-copy unit. Runner owns the transaction.
SET XACT_ABORT ON;
IF @@TRANCOUNT<>1 OR USER_NAME()<>N'cbn_channels_parity_migrator_c11' OR SESSION_CONTEXT(N'CBN_C11_TARGET') IS NULL OR DB_NAME() COLLATE Latin1_General_100_BIN2<>CONVERT(nvarchar(128),SESSION_CONTEXT(N'CBN_C11_TARGET')) COLLATE Latin1_General_100_BIN2 OR DB_NAME() NOT LIKE N'CBN_C11[_]%' THROW 51111,'Approved C11 restoration and principal required.',1;
-- C11_BOUNDARY
CREATE TABLE [crm_channels2].[OAuthSession](
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
CREATE TABLE [crm_channels2].[WebhookEndpoint](
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
CREATE TABLE [crm_channels2].[ProviderOperation](
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
CREATE INDEX [IX_ProviderOperation_Work] ON [crm_channels2].[ProviderOperation] ([InstitutionId],[Status],[LeaseUntil]);
-- C11_BOUNDARY
CREATE TABLE [crm_channels2].[ProviderAsset](
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
CREATE TABLE [crm_channels2].[SecretVersion](
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
CREATE UNIQUE INDEX [UQ_Secret_Version_ApplicationId] ON [crm_channels2].[SecretVersion] ([InstitutionId],[ApplicationId],[Kind],[VersionNo]) WHERE ApplicationId IS NOT NULL;
CREATE UNIQUE INDEX [UQ_Secret_Version_IntegrationId] ON [crm_channels2].[SecretVersion] ([InstitutionId],[IntegrationId],[Kind],[VersionNo]) WHERE IntegrationId IS NOT NULL;
CREATE UNIQUE INDEX [UQ_Secret_Version_EndpointId] ON [crm_channels2].[SecretVersion] ([InstitutionId],[EndpointId],[Kind],[VersionNo]) WHERE EndpointId IS NOT NULL;
CREATE UNIQUE INDEX [UQ_Secret_Version_OAuthSessionId] ON [crm_channels2].[SecretVersion] ([InstitutionId],[OAuthSessionId],[Kind],[VersionNo]) WHERE OAuthSessionId IS NOT NULL;
CREATE UNIQUE INDEX [UQ_Secret_Version_AssetId] ON [crm_channels2].[SecretVersion] ([InstitutionId],[AssetId],[Kind],[VersionNo]) WHERE AssetId IS NOT NULL;
CREATE UNIQUE INDEX [UQ_Secret_Active_AssetId] ON [crm_channels2].[SecretVersion] ([InstitutionId],[AssetId],[Kind]) WHERE AssetId IS NOT NULL AND State='active';
CREATE UNIQUE INDEX [UQ_Secret_Active_ApplicationId] ON [crm_channels2].[SecretVersion] ([InstitutionId],[ApplicationId],[Kind]) WHERE ApplicationId IS NOT NULL AND State='active';
CREATE UNIQUE INDEX [UQ_Secret_Active_IntegrationId] ON [crm_channels2].[SecretVersion] ([InstitutionId],[IntegrationId],[Kind]) WHERE IntegrationId IS NOT NULL AND State='active';
CREATE UNIQUE INDEX [UQ_Secret_Active_EndpointId] ON [crm_channels2].[SecretVersion] ([InstitutionId],[EndpointId],[Kind]) WHERE EndpointId IS NOT NULL AND State='active';
CREATE UNIQUE INDEX [UQ_Secret_Active_OAuthSessionId] ON [crm_channels2].[SecretVersion] ([InstitutionId],[OAuthSessionId],[Kind]) WHERE OAuthSessionId IS NOT NULL AND State='active';
-- C11_BOUNDARY
ALTER TABLE [crm_channels2].[OAuthSession] WITH CHECK ADD CONSTRAINT [FK_C11_3] FOREIGN KEY([InstitutionId]) REFERENCES [crm_channels2].[Context]([InstitutionId]);
ALTER TABLE [crm_channels2].[WebhookEndpoint] WITH CHECK ADD CONSTRAINT [FK_C11_4] FOREIGN KEY([InstitutionId]) REFERENCES [crm_channels2].[Context]([InstitutionId]);
ALTER TABLE [crm_channels2].[SecretVersion] WITH CHECK ADD CONSTRAINT [FK_C11_5] FOREIGN KEY([InstitutionId]) REFERENCES [crm_channels2].[Context]([InstitutionId]);
ALTER TABLE [crm_channels2].[ProviderAsset] WITH CHECK ADD CONSTRAINT [FK_C11_6] FOREIGN KEY([InstitutionId]) REFERENCES [crm_channels2].[Context]([InstitutionId]);
ALTER TABLE [crm_channels2].[ProviderOperation] WITH CHECK ADD CONSTRAINT [FK_C11_7] FOREIGN KEY([InstitutionId]) REFERENCES [crm_channels2].[Context]([InstitutionId]);
ALTER TABLE [crm_channels2].[OAuthSession] WITH CHECK ADD CONSTRAINT [FK_C11_25] FOREIGN KEY([InstitutionId],[ApplicationId]) REFERENCES [crm_channels2].[Application]([InstitutionId],[ApplicationId]);
ALTER TABLE [crm_channels2].[ProviderAsset] WITH CHECK ADD CONSTRAINT [FK_C11_26] FOREIGN KEY([InstitutionId],[ApplicationId]) REFERENCES [crm_channels2].[Application]([InstitutionId],[ApplicationId]);
ALTER TABLE [crm_channels2].[ProviderOperation] WITH CHECK ADD CONSTRAINT [FK_C11_27] FOREIGN KEY([InstitutionId],[ApplicationId]) REFERENCES [crm_channels2].[Application]([InstitutionId],[ApplicationId]);
ALTER TABLE [crm_channels2].[SecretVersion] WITH CHECK ADD CONSTRAINT [FK_C11_37] FOREIGN KEY([InstitutionId],[ApplicationId]) REFERENCES [crm_channels2].[Application]([InstitutionId],[ApplicationId]);
ALTER TABLE [crm_channels2].[SecretVersion] WITH CHECK ADD CONSTRAINT [FK_C11_38] FOREIGN KEY([InstitutionId],[IntegrationId]) REFERENCES [crm_channels2].[Integration]([InstitutionId],[IntegrationId]);
ALTER TABLE [crm_channels2].[SecretVersion] WITH CHECK ADD CONSTRAINT [FK_C11_39] FOREIGN KEY([InstitutionId],[EndpointId]) REFERENCES [crm_channels2].[WebhookEndpoint]([InstitutionId],[EndpointId]);
ALTER TABLE [crm_channels2].[SecretVersion] WITH CHECK ADD CONSTRAINT [FK_C11_40] FOREIGN KEY([InstitutionId],[OAuthSessionId]) REFERENCES [crm_channels2].[OAuthSession]([InstitutionId],[OAuthSessionId]);
ALTER TABLE [crm_channels2].[OAuthSession] WITH CHECK ADD CONSTRAINT [FK_C11_55] FOREIGN KEY([InstitutionId],[IntegrationId],[ApplicationId]) REFERENCES [crm_channels2].[Integration]([InstitutionId],[IntegrationId],[ApplicationId]);
ALTER TABLE [crm_channels2].[ProviderOperation] WITH CHECK ADD CONSTRAINT [FK_C11_56] FOREIGN KEY([InstitutionId],[IntegrationId],[ApplicationId]) REFERENCES [crm_channels2].[Integration]([InstitutionId],[IntegrationId],[ApplicationId]);
ALTER TABLE [crm_channels2].[ProviderOperation] WITH CHECK ADD CONSTRAINT [FK_C11_57] FOREIGN KEY([InstitutionId],[EndpointId],[ApplicationId]) REFERENCES [crm_channels2].[WebhookEndpoint]([InstitutionId],[EndpointId],[ApplicationId]);
ALTER TABLE [crm_channels2].[ProviderAsset] WITH CHECK ADD CONSTRAINT [FK_C11_58] FOREIGN KEY([InstitutionId],[OAuthSessionId],[IntegrationId],[ApplicationId]) REFERENCES [crm_channels2].[OAuthSession]([InstitutionId],[OAuthSessionId],[IntegrationId],[ApplicationId]);
ALTER TABLE [crm_channels2].[ProviderAsset] WITH CHECK ADD CONSTRAINT [FK_C11_59] FOREIGN KEY([InstitutionId],[IntegrationId],[DiscoveryOperationId],[ApplicationId]) REFERENCES [crm_channels2].[ProviderOperation]([InstitutionId],[IntegrationId],[OperationId],[ApplicationId]);
ALTER TABLE [crm_channels2].[SecretVersion] WITH CHECK ADD CONSTRAINT [FK_C11_60] FOREIGN KEY([InstitutionId],[AssetId]) REFERENCES [crm_channels2].[ProviderAsset]([InstitutionId],[AssetId]);
ALTER TABLE [crm_channels2].[OAuthSession] WITH CHECK ADD CONSTRAINT [FK_C11_61] FOREIGN KEY([InstitutionId],[ClientSecretId]) REFERENCES [crm_channels2].[SecretVersion]([InstitutionId],[SecretId]);
ALTER TABLE [crm_channels2].[WebhookEndpoint] WITH CHECK ADD CONSTRAINT [FK_C11_66] FOREIGN KEY([InstitutionId],[ApplicationId],[Provider]) REFERENCES [crm_channels2].[Application]([InstitutionId],[ApplicationId],[Provider]);
ALTER TABLE [crm_channels2].[ProviderAsset] WITH CHECK ADD CONSTRAINT [FK_C11_73] FOREIGN KEY([InstitutionId],[OAuthSessionId],[ApplicationId]) REFERENCES [crm_channels2].[OAuthSession]([InstitutionId],[OAuthSessionId],[ApplicationId]);
ALTER TABLE [crm_channels2].[ProviderAsset] WITH CHECK ADD CONSTRAINT [FK_C11_74] FOREIGN KEY([InstitutionId],[DiscoveryOperationId],[ApplicationId]) REFERENCES [crm_channels2].[ProviderOperation]([InstitutionId],[OperationId],[ApplicationId]);
