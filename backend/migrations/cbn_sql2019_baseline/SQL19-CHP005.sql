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
CREATE TABLE [crm_channels2].[ConversationProfile](
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
CREATE TABLE [crm_channels2].[ConversationControl](
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
CREATE TABLE [crm_channels2].[ExternalIdentity](
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
CREATE TABLE [crm_channels2].[ExternalMessage](
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
CREATE TABLE [crm_channels2].[SocialComment](
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
CREATE TABLE [crm_channels2].[SendJob](
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
CREATE INDEX [IX_SendJob_Work] ON [crm_channels2].[SendJob] ([InstitutionId],[IntegrationId],[State],[DueAt]);
-- C11_BOUNDARY
CREATE TABLE [crm_channels2].[MessageRoute](
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
CREATE UNIQUE INDEX [UQ_Route_Queue] ON [crm_channels2].[MessageRoute] ([InstitutionId],[QueueId]) WHERE QueueId IS NOT NULL;
-- C11_BOUNDARY
CREATE TABLE [crm_channels2].[LegacyBinding](
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
ALTER TABLE [crm_channels2].[ConversationProfile] WITH CHECK ADD CONSTRAINT [FK_C11_15] FOREIGN KEY([InstitutionId]) REFERENCES [crm_channels2].[Context]([InstitutionId]);
ALTER TABLE [crm_channels2].[ConversationControl] WITH CHECK ADD CONSTRAINT [FK_C11_16] FOREIGN KEY([InstitutionId]) REFERENCES [crm_channels2].[Context]([InstitutionId]);
ALTER TABLE [crm_channels2].[ExternalIdentity] WITH CHECK ADD CONSTRAINT [FK_C11_17] FOREIGN KEY([InstitutionId]) REFERENCES [crm_channels2].[Context]([InstitutionId]);
ALTER TABLE [crm_channels2].[ExternalMessage] WITH CHECK ADD CONSTRAINT [FK_C11_18] FOREIGN KEY([InstitutionId]) REFERENCES [crm_channels2].[Context]([InstitutionId]);
ALTER TABLE [crm_channels2].[SocialComment] WITH CHECK ADD CONSTRAINT [FK_C11_19] FOREIGN KEY([InstitutionId]) REFERENCES [crm_channels2].[Context]([InstitutionId]);
ALTER TABLE [crm_channels2].[SendJob] WITH CHECK ADD CONSTRAINT [FK_C11_20] FOREIGN KEY([InstitutionId]) REFERENCES [crm_channels2].[Context]([InstitutionId]);
ALTER TABLE [crm_channels2].[MessageRoute] WITH CHECK ADD CONSTRAINT [FK_C11_21] FOREIGN KEY([InstitutionId]) REFERENCES [crm_channels2].[Context]([InstitutionId]);
ALTER TABLE [crm_channels2].[LegacyBinding] WITH CHECK ADD CONSTRAINT [FK_C11_22] FOREIGN KEY([InstitutionId]) REFERENCES [crm_channels2].[Context]([InstitutionId]);
ALTER TABLE [crm_channels2].[ExternalIdentity] WITH CHECK ADD CONSTRAINT [FK_C11_31] FOREIGN KEY([InstitutionId],[IntegrationId]) REFERENCES [crm_channels2].[Integration]([InstitutionId],[IntegrationId]);
ALTER TABLE [crm_channels2].[ExternalMessage] WITH CHECK ADD CONSTRAINT [FK_C11_32] FOREIGN KEY([InstitutionId],[IntegrationId]) REFERENCES [crm_channels2].[Integration]([InstitutionId],[IntegrationId]);
ALTER TABLE [crm_channels2].[SocialComment] WITH CHECK ADD CONSTRAINT [FK_C11_33] FOREIGN KEY([InstitutionId],[IntegrationId]) REFERENCES [crm_channels2].[Integration]([InstitutionId],[IntegrationId]);
ALTER TABLE [crm_channels2].[SendJob] WITH CHECK ADD CONSTRAINT [FK_C11_34] FOREIGN KEY([InstitutionId],[IntegrationId]) REFERENCES [crm_channels2].[Integration]([InstitutionId],[IntegrationId]);
ALTER TABLE [crm_channels2].[MessageRoute] WITH CHECK ADD CONSTRAINT [FK_C11_35] FOREIGN KEY([InstitutionId],[IntegrationId]) REFERENCES [crm_channels2].[Integration]([InstitutionId],[IntegrationId]);
ALTER TABLE [crm_channels2].[LegacyBinding] WITH CHECK ADD CONSTRAINT [FK_C11_36] FOREIGN KEY([InstitutionId],[IntegrationId]) REFERENCES [crm_channels2].[Integration]([InstitutionId],[IntegrationId]);
ALTER TABLE [crm_channels2].[ConversationProfile] WITH CHECK ADD CONSTRAINT [FK_C11_44] FOREIGN KEY([ConversationId]) REFERENCES [crm].[Conversation]([ConversationId]);
ALTER TABLE [crm_channels2].[ConversationControl] WITH CHECK ADD CONSTRAINT [FK_C11_45] FOREIGN KEY([ConversationId]) REFERENCES [crm].[Conversation]([ConversationId]);
ALTER TABLE [crm_channels2].[ExternalIdentity] WITH CHECK ADD CONSTRAINT [FK_C11_46] FOREIGN KEY([ConversationId]) REFERENCES [crm].[Conversation]([ConversationId]);
ALTER TABLE [crm_channels2].[ExternalIdentity] WITH CHECK ADD CONSTRAINT [FK_C11_47] FOREIGN KEY([ContactId]) REFERENCES [crm].[Contact]([ContactId]);
ALTER TABLE [crm_channels2].[ExternalMessage] WITH CHECK ADD CONSTRAINT [FK_C11_48] FOREIGN KEY([MessageId]) REFERENCES [crm].[Message]([MessageId]);
ALTER TABLE [crm_channels2].[SendJob] WITH CHECK ADD CONSTRAINT [FK_C11_49] FOREIGN KEY([MessageId]) REFERENCES [crm].[Message]([MessageId]);
ALTER TABLE [crm_channels2].[MessageRoute] WITH CHECK ADD CONSTRAINT [FK_C11_50] FOREIGN KEY([MessageId]) REFERENCES [crm].[Message]([MessageId]);
ALTER TABLE [crm_channels2].[SendJob] WITH CHECK ADD CONSTRAINT [FK_C11_51] FOREIGN KEY([InstitutionId],[IntegrationId],[IdentityId]) REFERENCES [crm_channels2].[ExternalIdentity]([InstitutionId],[IntegrationId],[IdentityId]);
ALTER TABLE [crm_channels2].[SendJob] WITH CHECK ADD CONSTRAINT [FK_C11_52] FOREIGN KEY([InstitutionId],[IntegrationId],[CommentId]) REFERENCES [crm_channels2].[SocialComment]([InstitutionId],[IntegrationId],[CommentId]);
ALTER TABLE [crm_channels2].[MessageRoute] WITH CHECK ADD CONSTRAINT [FK_C11_53] FOREIGN KEY([InstitutionId],[IntegrationId],[IdentityId]) REFERENCES [crm_channels2].[ExternalIdentity]([InstitutionId],[IntegrationId],[IdentityId]);
ALTER TABLE [crm_channels2].[MessageRoute] WITH CHECK ADD CONSTRAINT [FK_C11_54] FOREIGN KEY([InstitutionId],[IntegrationId],[QueueId],[IdentityId],[MessageId]) REFERENCES [crm_channels2].[SendJob]([InstitutionId],[IntegrationId],[QueueId],[IdentityId],[MessageId]);
ALTER TABLE [crm_channels2].[SendJob] WITH CHECK ADD CONSTRAINT [FK_C11_64] FOREIGN KEY([InstitutionId],[IntegrationId],[OperationId]) REFERENCES [crm_channels2].[ProviderOperation]([InstitutionId],[IntegrationId],[OperationId]);
ALTER TABLE [crm_channels2].[SendJob] WITH CHECK ADD CONSTRAINT [FK_C11_65] FOREIGN KEY([InstitutionId],[IntegrationId],[ReservationId],[OperationId]) REFERENCES [crm_channels2].[QuotaReservation]([InstitutionId],[IntegrationId],[ReservationId],[OperationId]);
