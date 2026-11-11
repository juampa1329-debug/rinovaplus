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
CREATE TABLE [crm_channels2].[EndpointIntegration](
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
CREATE TABLE [crm_channels2].[WebhookReceipt](
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
CREATE UNIQUE INDEX [UQ_Receipt_BodyNonce] ON [crm_channels2].[WebhookReceipt] ([BodyKeyVersion],[BodyNonce]) WHERE BodyKeyVersion IS NOT NULL AND BodyNonce IS NOT NULL;
CREATE INDEX [IX_WebhookReceipt_Work] ON [crm_channels2].[WebhookReceipt] ([InstitutionId],[Status],[LeaseUntil]);
-- C11_BOUNDARY
CREATE TABLE [crm_channels2].[WebhookEvent](
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
CREATE UNIQUE INDEX [UQ_Event_Integration_Dedupe] ON [crm_channels2].[WebhookEvent] ([InstitutionId],[IntegrationId],[DedupeKey]) WHERE IntegrationId IS NOT NULL;
CREATE INDEX [IX_WebhookEvent_Work] ON [crm_channels2].[WebhookEvent] ([InstitutionId],[Status],[LeaseUntil]);
-- C11_BOUNDARY
CREATE TABLE [crm_channels2].[VerificationEvidence](
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
ALTER TABLE [crm_channels2].[VerificationEvidence] WITH CHECK ADD CONSTRAINT [FK_C11_9] FOREIGN KEY([InstitutionId]) REFERENCES [crm_channels2].[Context]([InstitutionId]);
ALTER TABLE [crm_channels2].[EndpointIntegration] WITH CHECK ADD CONSTRAINT [FK_C11_12] FOREIGN KEY([InstitutionId]) REFERENCES [crm_channels2].[Context]([InstitutionId]);
ALTER TABLE [crm_channels2].[WebhookReceipt] WITH CHECK ADD CONSTRAINT [FK_C11_13] FOREIGN KEY([InstitutionId]) REFERENCES [crm_channels2].[Context]([InstitutionId]);
ALTER TABLE [crm_channels2].[WebhookEvent] WITH CHECK ADD CONSTRAINT [FK_C11_14] FOREIGN KEY([InstitutionId]) REFERENCES [crm_channels2].[Context]([InstitutionId]);
ALTER TABLE [crm_channels2].[VerificationEvidence] WITH CHECK ADD CONSTRAINT [FK_C11_41] FOREIGN KEY([InstitutionId],[EndpointId]) REFERENCES [crm_channels2].[WebhookEndpoint]([InstitutionId],[EndpointId]);
ALTER TABLE [crm_channels2].[EndpointIntegration] WITH CHECK ADD CONSTRAINT [FK_C11_42] FOREIGN KEY([InstitutionId],[EndpointId],[ApplicationId]) REFERENCES [crm_channels2].[WebhookEndpoint]([InstitutionId],[EndpointId],[ApplicationId]);
ALTER TABLE [crm_channels2].[EndpointIntegration] WITH CHECK ADD CONSTRAINT [FK_C11_43] FOREIGN KEY([InstitutionId],[IntegrationId],[ApplicationId]) REFERENCES [crm_channels2].[Integration]([InstitutionId],[IntegrationId],[ApplicationId]);
ALTER TABLE [crm_channels2].[WebhookReceipt] WITH CHECK ADD CONSTRAINT [FK_C11_67] FOREIGN KEY([InstitutionId],[EndpointId],[ApplicationId]) REFERENCES [crm_channels2].[WebhookEndpoint]([InstitutionId],[EndpointId],[ApplicationId]);
ALTER TABLE [crm_channels2].[WebhookReceipt] WITH CHECK ADD CONSTRAINT [FK_C11_68] FOREIGN KEY([InstitutionId],[SignatureSecretId]) REFERENCES [crm_channels2].[SecretVersion]([InstitutionId],[SecretId]);
ALTER TABLE [crm_channels2].[WebhookEvent] WITH CHECK ADD CONSTRAINT [FK_C11_69] FOREIGN KEY([InstitutionId],[ReceiptId],[EndpointId],[ApplicationId]) REFERENCES [crm_channels2].[WebhookReceipt]([InstitutionId],[ReceiptId],[EndpointId],[ApplicationId]);
ALTER TABLE [crm_channels2].[WebhookEvent] WITH CHECK ADD CONSTRAINT [FK_C11_70] FOREIGN KEY([InstitutionId],[IntegrationId],[ApplicationId]) REFERENCES [crm_channels2].[Integration]([InstitutionId],[IntegrationId],[ApplicationId]);
ALTER TABLE [crm_channels2].[WebhookEvent] WITH CHECK ADD CONSTRAINT [FK_C11_71] FOREIGN KEY([InstitutionId],[EndpointId],[IntegrationId],[RouteKind],[RouteExternalId]) REFERENCES [crm_channels2].[EndpointIntegration]([InstitutionId],[EndpointId],[IntegrationId],[RouteKind],[ExternalId]);
ALTER TABLE [crm_channels2].[VerificationEvidence] WITH CHECK ADD CONSTRAINT [FK_C11_72] FOREIGN KEY([InstitutionId],[ReceiptId]) REFERENCES [crm_channels2].[WebhookReceipt]([InstitutionId],[ReceiptId]);
ALTER TABLE [crm_channels2].[VerificationEvidence] WITH CHECK ADD CONSTRAINT [FK_C11_75] FOREIGN KEY([InstitutionId],[IntegrationId],[ApplicationId]) REFERENCES [crm_channels2].[Integration]([InstitutionId],[IntegrationId],[ApplicationId]);
ALTER TABLE [crm_channels2].[VerificationEvidence] WITH CHECK ADD CONSTRAINT [FK_C11_76] FOREIGN KEY([InstitutionId],[IntegrationId],[OperationId],[ApplicationId]) REFERENCES [crm_channels2].[ProviderOperation]([InstitutionId],[IntegrationId],[OperationId],[ApplicationId]);
ALTER TABLE [crm_channels2].[VerificationEvidence] WITH CHECK ADD CONSTRAINT [FK_C11_77] FOREIGN KEY([InstitutionId],[EventId],[IntegrationId],[ReceiptId],[EndpointId],[ApplicationId]) REFERENCES [crm_channels2].[WebhookEvent]([InstitutionId],[EventId],[IntegrationId],[ReceiptId],[EndpointId],[ApplicationId]);
