SET XACT_ABORT ON;
SET NOCOUNT ON;
SET ANSI_NULLS ON;SET QUOTED_IDENTIFIER ON;SET ANSI_PADDING ON;
SET ANSI_WARNINGS ON;SET ARITHABORT ON;SET CONCAT_NULL_YIELDS_NULL ON;SET NUMERIC_ROUNDABORT OFF;
IF @@TRANCOUNT<>1 OR USER_NAME()<>N'cbn_es_migrator_p1'
 OR CONVERT(int,SERVERPROPERTY('ProductMajorVersion'))<>15
 OR (SELECT compatibility_level FROM sys.databases WHERE database_id=DB_ID())<>150
 OR SESSION_CONTEXT(N'CBN_ES_TARGET') IS NULL
 OR DB_NAME() COLLATE Latin1_General_100_BIN2<>CONVERT(nvarchar(128),SESSION_CONTEXT(N'CBN_ES_TARGET')) COLLATE Latin1_General_100_BIN2
 OR LEFT(DB_NAME(),9) COLLATE Latin1_General_100_BIN2<>N'CBN_P1ES_'
 THROW 51960,'Approved SQL2019 Spanish baseline target/actor/transaction required.',1;
GO
-- crm.Contact -> dbo.CRMContacto
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[CRMContacto](

	[ContactId] [uniqueidentifier] NOT NULL,

	[Name] [nvarchar](100) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Phone] [nvarchar](40) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[City] [nvarchar](100) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[ProgramId] [int] NULL,

	[Program] [nvarchar](200) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Schedule] [nvarchar](100) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Stage] [nvarchar](60) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Tags] [nvarchar](1000) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Notes] [nvarchar](1000) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Type] [nvarchar](100) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Interests] [nvarchar](300) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[CustomValues] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[CreatedAt] [datetime2](7) NOT NULL,

	[UpdatedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMContacto_PK_Contact] PRIMARY KEY CLUSTERED 

(

	[ContactId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
ALTER TABLE [dbo].[CRMContacto] ADD  CONSTRAINT [CRMContacto_DF_Contact_CreatedAt]  DEFAULT (sysutcdatetime()) FOR [CreatedAt]
GO
ALTER TABLE [dbo].[CRMContacto] ADD  CONSTRAINT [CRMContacto_DF_Contact_UpdatedAt]  DEFAULT (sysutcdatetime()) FOR [UpdatedAt]
GO
ALTER TABLE [dbo].[CRMContacto]  WITH CHECK ADD  CONSTRAINT [CRMContacto_CK_Contact_Custom] CHECK  ((isjson([CustomValues])=(1) AND left(ltrim([CustomValues]),(1))=N'{'))
GO
ALTER TABLE [dbo].[CRMContacto] CHECK CONSTRAINT [CRMContacto_CK_Contact_Custom]
GO
ALTER TABLE [dbo].[CRMContacto]  WITH CHECK ADD  CONSTRAINT [CRMContacto_CK_Contact_Identity] CHECK  ((len(ltrim(rtrim([Name])))>(0) OR len(ltrim(rtrim([Phone])))>(0)))
GO
ALTER TABLE [dbo].[CRMContacto] CHECK CONSTRAINT [CRMContacto_CK_Contact_Identity]
GO
ALTER TABLE [dbo].[CRMContacto]  WITH CHECK ADD  CONSTRAINT [CRMContacto_CK_Contact_Stage] CHECK  ((len(ltrim(rtrim([Stage])))>(0)))
GO
ALTER TABLE [dbo].[CRMContacto] CHECK CONSTRAINT [CRMContacto_CK_Contact_Stage]
GO
-- crm.Conversation -> dbo.CRMConversacion
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMConversacion](

	[ConversationId] [uniqueidentifier] NOT NULL,

	[ContactId] [uniqueidentifier] NOT NULL,

	[State] [varchar](12) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Priority] [varchar](8) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Assignee] [nvarchar](100) COLLATE Modern_Spanish_CI_AS NULL,

	[ControlMode] [varchar](5) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Unread] [bit] NOT NULL,

	[CreatedAt] [datetime2](7) NOT NULL,

	[UpdatedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMConversacion_PK_Conversation] PRIMARY KEY CLUSTERED 

(

	[ConversationId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF),

 CONSTRAINT [CRMConversacion_UQ_Conversation_Contact] UNIQUE NONCLUSTERED 

(

	[ContactId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
ALTER TABLE [dbo].[CRMConversacion] ADD  CONSTRAINT [CRMConversacion_DF_Conversation_CreatedAt]  DEFAULT (sysutcdatetime()) FOR [CreatedAt]
GO
ALTER TABLE [dbo].[CRMConversacion] ADD  CONSTRAINT [CRMConversacion_DF_Conversation_UpdatedAt]  DEFAULT (sysutcdatetime()) FOR [UpdatedAt]
GO
ALTER TABLE [dbo].[CRMConversacion]  WITH CHECK ADD  CONSTRAINT [CRMConversacion_CK_Conversation_Control] CHECK  (([ControlMode]='ai' OR [ControlMode]='human'))
GO
ALTER TABLE [dbo].[CRMConversacion] CHECK CONSTRAINT [CRMConversacion_CK_Conversation_Control]
GO
ALTER TABLE [dbo].[CRMConversacion]  WITH CHECK ADD  CONSTRAINT [CRMConversacion_CK_Conversation_Priority] CHECK  (([Priority]='urgent' OR [Priority]='high' OR [Priority]='normal' OR [Priority]='low'))
GO
ALTER TABLE [dbo].[CRMConversacion] CHECK CONSTRAINT [CRMConversacion_CK_Conversation_Priority]
GO
ALTER TABLE [dbo].[CRMConversacion]  WITH CHECK ADD  CONSTRAINT [CRMConversacion_CK_Conversation_State] CHECK  (([State]='closed' OR [State]='waiting' OR [State]='open'))
GO
ALTER TABLE [dbo].[CRMConversacion] CHECK CONSTRAINT [CRMConversacion_CK_Conversation_State]
GO
-- crm.Message -> dbo.CRMMensaje
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMMensaje](

	[MessageId] [uniqueidentifier] NOT NULL,

	[ConversationId] [uniqueidentifier] NOT NULL,

	[Sequence] [bigint] IDENTITY(1,1) NOT NULL,

	[Body] [nvarchar](4000) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Direction] [varchar](8) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[CreatedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMMensaje_PK_Message] PRIMARY KEY CLUSTERED 

(

	[MessageId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
CREATE UNIQUE NONCLUSTERED INDEX [CRMMensaje_IX_Message_Conversation_Sequence] ON [dbo].[CRMMensaje]

(

	[ConversationId] ASC,

	[Sequence] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, IGNORE_DUP_KEY = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
ALTER TABLE [dbo].[CRMMensaje] ADD  CONSTRAINT [CRMMensaje_DF_Message_CreatedAt]  DEFAULT (sysutcdatetime()) FOR [CreatedAt]
GO
ALTER TABLE [dbo].[CRMMensaje]  WITH CHECK ADD  CONSTRAINT [CRMMensaje_CK_Message_Body] CHECK  ((len(ltrim(rtrim([Body])))>(0)))
GO
ALTER TABLE [dbo].[CRMMensaje] CHECK CONSTRAINT [CRMMensaje_CK_Message_Body]
GO
ALTER TABLE [dbo].[CRMMensaje]  WITH CHECK ADD  CONSTRAINT [CRMMensaje_CK_Message_Direction] CHECK  (([Direction]='outgoing' OR [Direction]='incoming'))
GO
ALTER TABLE [dbo].[CRMMensaje] CHECK CONSTRAINT [CRMMensaje_CK_Message_Direction]
GO
-- crm.Operation -> dbo.CRMOperacion
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMOperacion](

	[OperationId] [uniqueidentifier] NOT NULL,

	[Revision] [bigint] IDENTITY(1,1) NOT NULL,

	[Action] [varchar](24) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[PayloadHash] [binary](32) NOT NULL,

	[ContactId] [uniqueidentifier] NOT NULL,

	[ConversationId] [uniqueidentifier] NOT NULL,

	[MessageId] [uniqueidentifier] NULL,

	[Actor] [varchar](32) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[CreatedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMOperacion_PK_Operation] PRIMARY KEY NONCLUSTERED 

(

	[OperationId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF),

 CONSTRAINT [CRMOperacion_UQ_Operation_Revision] UNIQUE CLUSTERED 

(

	[Revision] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
ALTER TABLE [dbo].[CRMOperacion] ADD  CONSTRAINT [CRMOperacion_DF_Operation_CreatedAt]  DEFAULT (sysutcdatetime()) FOR [CreatedAt]
GO
ALTER TABLE [dbo].[CRMOperacion]  WITH CHECK ADD  CONSTRAINT [CRMOperacion_CK_Operation_Action] CHECK  (([Action]='add_message' OR [Action]='update_conversation' OR [Action]='edit_contact' OR [Action]='create_contact'))
GO
ALTER TABLE [dbo].[CRMOperacion] CHECK CONSTRAINT [CRMOperacion_CK_Operation_Action]
GO
ALTER TABLE [dbo].[CRMOperacion]  WITH CHECK ADD  CONSTRAINT [CRMOperacion_CK_Operation_Actor] CHECK  (([Actor]='local-operator'))
GO
ALTER TABLE [dbo].[CRMOperacion] CHECK CONSTRAINT [CRMOperacion_CK_Operation_Actor]
GO
ALTER TABLE [dbo].[CRMOperacion]  WITH CHECK ADD  CONSTRAINT [CRMOperacion_CK_Operation_Message] CHECK  (([Action]='add_message' AND [MessageId] IS NOT NULL OR [Action]<>'add_message' AND [MessageId] IS NULL))
GO
ALTER TABLE [dbo].[CRMOperacion] CHECK CONSTRAINT [CRMOperacion_CK_Operation_Message]
GO
-- crm_admissions.AdmissionCase -> dbo.CRMAdmision
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[CRMAdmision](

	[CaseId] [uniqueidentifier] NOT NULL,

	[AspirantId] [int] NOT NULL,

	[CreatedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMAdmision_PK_AdmissionCase] PRIMARY KEY CLUSTERED 

(

	[CaseId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF),

 CONSTRAINT [CRMAdmision_UQ_AdmissionCase_Aspirant] UNIQUE NONCLUSTERED 

(

	[AspirantId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
ALTER TABLE [dbo].[CRMAdmision] ADD  CONSTRAINT [CRMAdmision_DF_AdmissionCase_CreatedAt]  DEFAULT (sysutcdatetime()) FOR [CreatedAt]
GO
-- crm_admissions.Followup -> dbo.CRMAdmisionSeguimiento
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[CRMAdmisionSeguimiento](

	[FollowupId] [uniqueidentifier] NOT NULL,

	[CaseId] [uniqueidentifier] NOT NULL,

	[Body] [nvarchar](2000) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[StateId] [int] NOT NULL,

	[DueDate] [date] NULL,

	[Revision] [int] NOT NULL,

	[CreatedAt] [datetime2](7) NOT NULL,

	[UpdatedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMAdmisionSeguimiento_PK_Followup] PRIMARY KEY CLUSTERED 

(

	[FollowupId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
CREATE NONCLUSTERED INDEX [CRMAdmisionSeguimiento_IX_Followup_Case] ON [dbo].[CRMAdmisionSeguimiento]

(

	[CaseId] ASC,

	[CreatedAt] DESC,

	[FollowupId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
ALTER TABLE [dbo].[CRMAdmisionSeguimiento] ADD  CONSTRAINT [CRMAdmisionSeguimiento_DF_Followup_CreatedAt]  DEFAULT (sysutcdatetime()) FOR [CreatedAt]
GO
ALTER TABLE [dbo].[CRMAdmisionSeguimiento] ADD  CONSTRAINT [CRMAdmisionSeguimiento_DF_Followup_UpdatedAt]  DEFAULT (sysutcdatetime()) FOR [UpdatedAt]
GO
ALTER TABLE [dbo].[CRMAdmisionSeguimiento]  WITH CHECK ADD  CONSTRAINT [CRMAdmisionSeguimiento_CK_Followup_Body] CHECK  ((len(ltrim(rtrim([Body])))>(0)))
GO
ALTER TABLE [dbo].[CRMAdmisionSeguimiento] CHECK CONSTRAINT [CRMAdmisionSeguimiento_CK_Followup_Body]
GO
ALTER TABLE [dbo].[CRMAdmisionSeguimiento]  WITH CHECK ADD  CONSTRAINT [CRMAdmisionSeguimiento_CK_Followup_Revision] CHECK  (([Revision]>(0)))
GO
ALTER TABLE [dbo].[CRMAdmisionSeguimiento] CHECK CONSTRAINT [CRMAdmisionSeguimiento_CK_Followup_Revision]
GO
-- crm_admissions.Operation -> dbo.CRMAdmisionOperacion
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMAdmisionOperacion](

	[OperationId] [uniqueidentifier] NOT NULL,

	[FollowupId] [uniqueidentifier] NOT NULL,

	[Action] [varchar](6) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[PayloadHash] [binary](32) NOT NULL,

	[Actor] [varchar](32) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[CreatedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMAdmisionOperacion_PK_AdmissionOperation] PRIMARY KEY CLUSTERED 

(

	[OperationId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
ALTER TABLE [dbo].[CRMAdmisionOperacion] ADD  CONSTRAINT [CRMAdmisionOperacion_DF_AdmissionOperation_Actor]  DEFAULT ('local-operator') FOR [Actor]
GO
ALTER TABLE [dbo].[CRMAdmisionOperacion] ADD  CONSTRAINT [CRMAdmisionOperacion_DF_AdmissionOperation_CreatedAt]  DEFAULT (sysutcdatetime()) FOR [CreatedAt]
GO
ALTER TABLE [dbo].[CRMAdmisionOperacion]  WITH CHECK ADD  CONSTRAINT [CRMAdmisionOperacion_CK_AdmissionOperation_Action] CHECK  (([Action]='edit' OR [Action]='create'))
GO
ALTER TABLE [dbo].[CRMAdmisionOperacion] CHECK CONSTRAINT [CRMAdmisionOperacion_CK_AdmissionOperation_Action]
GO
ALTER TABLE [dbo].[CRMAdmisionOperacion]  WITH CHECK ADD  CONSTRAINT [CRMAdmisionOperacion_CK_AdmissionOperation_Actor] CHECK  (([Actor]='local-operator'))
GO
ALTER TABLE [dbo].[CRMAdmisionOperacion] CHECK CONSTRAINT [CRMAdmisionOperacion_CK_AdmissionOperation_Actor]
GO
-- crm_agents.Assignment -> dbo.CRMAgenteAsignacion
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMAgenteAsignacion](

	[ConversationId] [uniqueidentifier] NOT NULL,

	[Mode] [varchar](10) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[ContextId] [uniqueidentifier] NULL,

	[Revision] [bigint] NOT NULL,

	[Reason] [nvarchar](1000) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[BaselineSequence] [bigint] NOT NULL,

 CONSTRAINT [CRMAgenteAsignacion_PK__Assignme__C050D87792025F79] PRIMARY KEY CLUSTERED 

(

	[ConversationId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
ALTER TABLE [dbo].[CRMAgenteAsignacion]  WITH CHECK ADD  CONSTRAINT [CRMAgenteAsignacion_CK__Assignmen__Revis__3A2F0F71] CHECK  (([Revision]>(0)))
GO
ALTER TABLE [dbo].[CRMAgenteAsignacion] CHECK CONSTRAINT [CRMAgenteAsignacion_CK__Assignmen__Revis__3A2F0F71]
GO
ALTER TABLE [dbo].[CRMAgenteAsignacion]  WITH CHECK ADD  CONSTRAINT [CRMAgenteAsignacion_CK__Assignment__Mode__393AEB38] CHECK  (([Mode]='human' OR [Mode]='manual' OR [Mode]='automatic'))
GO
ALTER TABLE [dbo].[CRMAgenteAsignacion] CHECK CONSTRAINT [CRMAgenteAsignacion_CK__Assignment__Mode__393AEB38]
GO
-- crm_agents.Context -> dbo.CRMAgenteContexto
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[CRMAgenteContexto](

	[ContextId] [uniqueidentifier] NOT NULL,

	[ConversationId] [uniqueidentifier] NOT NULL,

	[ProgramId] [int] NOT NULL,

	[ApplicantId] [int] NULL,

	[PeriodId] [int] NULL,

	[StageId] [uniqueidentifier] NULL,

	[Revision] [bigint] NOT NULL,

	[StageRevision] [bigint] NULL,

	[Evidence] [nvarchar](1000) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[ApprovedAt] [datetime2](7) NOT NULL,

	[MemoryJson] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[BaselineSequence] [bigint] NOT NULL,

 CONSTRAINT [CRMAgenteContexto_PK__Context__23A2374903661005] PRIMARY KEY CLUSTERED 

(

	[ContextId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF),

 CONSTRAINT [CRMAgenteContexto_UQ__Context__4FA73ACFB4F7D899] UNIQUE NONCLUSTERED 

(

	[ContextId] ASC,

	[ConversationId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
ALTER TABLE [dbo].[CRMAgenteContexto] ADD  CONSTRAINT [CRMAgenteContexto_DF__Context__Approve__2AECCBE1]  DEFAULT (sysutcdatetime()) FOR [ApprovedAt]
GO
ALTER TABLE [dbo].[CRMAgenteContexto] ADD  CONSTRAINT [CRMAgenteContexto_DF__Context__MemoryJ__2BE0F01A]  DEFAULT ('{}') FOR [MemoryJson]
GO
ALTER TABLE [dbo].[CRMAgenteContexto]  WITH CHECK ADD  CONSTRAINT [CRMAgenteContexto_CK__Context__2EBD5CC5] CHECK  (([ApplicantId] IS NULL AND [PeriodId] IS NULL OR [ApplicantId] IS NOT NULL AND [PeriodId] IS NOT NULL))
GO
ALTER TABLE [dbo].[CRMAgenteContexto] CHECK CONSTRAINT [CRMAgenteContexto_CK__Context__2EBD5CC5]
GO
ALTER TABLE [dbo].[CRMAgenteContexto]  WITH CHECK ADD  CONSTRAINT [CRMAgenteContexto_CK__Context__MemoryJ__2CD51453] CHECK  ((isjson([MemoryJson])=(1)))
GO
ALTER TABLE [dbo].[CRMAgenteContexto] CHECK CONSTRAINT [CRMAgenteContexto_CK__Context__MemoryJ__2CD51453]
GO
ALTER TABLE [dbo].[CRMAgenteContexto]  WITH CHECK ADD  CONSTRAINT [CRMAgenteContexto_CK__Context__Revisio__29F8A7A8] CHECK  (([Revision]>(0)))
GO
ALTER TABLE [dbo].[CRMAgenteContexto] CHECK CONSTRAINT [CRMAgenteContexto_CK__Context__Revisio__29F8A7A8]
GO
-- crm_agents.Execution -> dbo.CRMAgenteEjecucion
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMAgenteEjecucion](

	[RequestId] [uniqueidentifier] NOT NULL,

	[AgentId] [uniqueidentifier] NOT NULL,

	[AgentVersion] [bigint] NOT NULL,

	[ConversationId] [uniqueidentifier] NULL,

	[Provider] [varchar](30) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[ModelId] [nvarchar](200) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Route] [varchar](30) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Variant] [nvarchar](40) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[FallbackUsed] [bit] NOT NULL,

	[PricingJson] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[AttemptsJson] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[CostReserved] [decimal](20, 8) NULL,

	[CostEstimated] [decimal](20, 8) NULL,

	[InputTokens] [bigint] NULL,

	[OutputTokens] [bigint] NULL,

	[LatencyMs] [bigint] NULL,

	[State] [varchar](12) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[ErrorCode] [varchar](80) COLLATE Modern_Spanish_CI_AS NULL,

	[SourceFingerprint] [varchar](64) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[CreatedAt] [datetime2](7) NOT NULL,

	[FinishedAt] [datetime2](7) NULL,

 CONSTRAINT [CRMAgenteEjecucion_PK__Executio__33A8517A833C0BF5] PRIMARY KEY CLUSTERED 

(

	[RequestId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
CREATE NONCLUSTERED INDEX [CRMAgenteEjecucion_IX_AgentExecution_AgentCreated] ON [dbo].[CRMAgenteEjecucion]

(

	[AgentId] ASC,

	[CreatedAt] DESC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
CREATE NONCLUSTERED INDEX [CRMAgenteEjecucion_IX_AgentExecution_Conversation] ON [dbo].[CRMAgenteEjecucion]

(

	[ConversationId] ASC,

	[CreatedAt] DESC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
ALTER TABLE [dbo].[CRMAgenteEjecucion] ADD  CONSTRAINT [CRMAgenteEjecucion_DF__Execution__Fallb__4F2A2C57]  DEFAULT ((0)) FOR [FallbackUsed]
GO
ALTER TABLE [dbo].[CRMAgenteEjecucion] ADD  CONSTRAINT [CRMAgenteEjecucion_DF__Execution__Attem__511274C9]  DEFAULT ('[]') FOR [AttemptsJson]
GO
ALTER TABLE [dbo].[CRMAgenteEjecucion] ADD  CONSTRAINT [CRMAgenteEjecucion_DF__Execution__Creat__58B39691]  DEFAULT (sysutcdatetime()) FOR [CreatedAt]
GO
ALTER TABLE [dbo].[CRMAgenteEjecucion]  WITH CHECK ADD  CONSTRAINT [CRMAgenteEjecucion_CK__Execution__Agent__4D41E3E5] CHECK  (([AgentVersion]>(0)))
GO
ALTER TABLE [dbo].[CRMAgenteEjecucion] CHECK CONSTRAINT [CRMAgenteEjecucion_CK__Execution__Agent__4D41E3E5]
GO
ALTER TABLE [dbo].[CRMAgenteEjecucion]  WITH CHECK ADD  CONSTRAINT [CRMAgenteEjecucion_CK__Execution__Attem__52069902] CHECK  ((isjson([AttemptsJson])=(1)))
GO
ALTER TABLE [dbo].[CRMAgenteEjecucion] CHECK CONSTRAINT [CRMAgenteEjecucion_CK__Execution__Attem__52069902]
GO
ALTER TABLE [dbo].[CRMAgenteEjecucion]  WITH CHECK ADD  CONSTRAINT [CRMAgenteEjecucion_CK__Execution__CostE__53EEE174] CHECK  (([CostEstimated]>=(0)))
GO
ALTER TABLE [dbo].[CRMAgenteEjecucion] CHECK CONSTRAINT [CRMAgenteEjecucion_CK__Execution__CostE__53EEE174]
GO
ALTER TABLE [dbo].[CRMAgenteEjecucion]  WITH CHECK ADD  CONSTRAINT [CRMAgenteEjecucion_CK__Execution__CostR__52FABD3B] CHECK  (([CostReserved]>=(0)))
GO
ALTER TABLE [dbo].[CRMAgenteEjecucion] CHECK CONSTRAINT [CRMAgenteEjecucion_CK__Execution__CostR__52FABD3B]
GO
ALTER TABLE [dbo].[CRMAgenteEjecucion]  WITH CHECK ADD  CONSTRAINT [CRMAgenteEjecucion_CK__Execution__Input__54E305AD] CHECK  (([InputTokens]>=(0)))
GO
ALTER TABLE [dbo].[CRMAgenteEjecucion] CHECK CONSTRAINT [CRMAgenteEjecucion_CK__Execution__Input__54E305AD]
GO
ALTER TABLE [dbo].[CRMAgenteEjecucion]  WITH CHECK ADD  CONSTRAINT [CRMAgenteEjecucion_CK__Execution__Laten__56CB4E1F] CHECK  (([LatencyMs]>=(0)))
GO
ALTER TABLE [dbo].[CRMAgenteEjecucion] CHECK CONSTRAINT [CRMAgenteEjecucion_CK__Execution__Laten__56CB4E1F]
GO
ALTER TABLE [dbo].[CRMAgenteEjecucion]  WITH CHECK ADD  CONSTRAINT [CRMAgenteEjecucion_CK__Execution__Outpu__55D729E6] CHECK  (([OutputTokens]>=(0)))
GO
ALTER TABLE [dbo].[CRMAgenteEjecucion] CHECK CONSTRAINT [CRMAgenteEjecucion_CK__Execution__Outpu__55D729E6]
GO
ALTER TABLE [dbo].[CRMAgenteEjecucion]  WITH CHECK ADD  CONSTRAINT [CRMAgenteEjecucion_CK__Execution__Prici__501E5090] CHECK  ((isjson([PricingJson])=(1)))
GO
ALTER TABLE [dbo].[CRMAgenteEjecucion] CHECK CONSTRAINT [CRMAgenteEjecucion_CK__Execution__Prici__501E5090]
GO
ALTER TABLE [dbo].[CRMAgenteEjecucion]  WITH CHECK ADD  CONSTRAINT [CRMAgenteEjecucion_CK__Execution__State__57BF7258] CHECK  (([State]='uncertain' OR [State]='failed' OR [State]='completed' OR [State]='reserved'))
GO
ALTER TABLE [dbo].[CRMAgenteEjecucion] CHECK CONSTRAINT [CRMAgenteEjecucion_CK__Execution__State__57BF7258]
GO
-- crm_agents.History -> dbo.CRMAgenteHistorial
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMAgenteHistorial](

	[EventId] [bigint] IDENTITY(1,1) NOT NULL,

	[OperationId] [uniqueidentifier] NOT NULL,

	[EntityId] [uniqueidentifier] NOT NULL,

	[Kind] [varchar](24) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[PayloadHash] [char](64) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Document] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Note] [nvarchar](1000) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Actor] [varchar](30) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[CreatedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMAgenteHistorial_PK__History__7944C810ACD212A7] PRIMARY KEY CLUSTERED 

(

	[EventId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF),

 CONSTRAINT [CRMAgenteHistorial_UQ__History__A4F5FC4561081F5C] UNIQUE NONCLUSTERED 

(

	[OperationId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
CREATE NONCLUSTERED INDEX [CRMAgenteHistorial_IX_Agents_History_Entity] ON [dbo].[CRMAgenteHistorial]

(

	[EntityId] ASC,

	[EventId] DESC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
ALTER TABLE [dbo].[CRMAgenteHistorial] ADD  CONSTRAINT [CRMAgenteHistorial_DF__History__Actor__3FE7E8C7]  DEFAULT ('local-operator') FOR [Actor]
GO
ALTER TABLE [dbo].[CRMAgenteHistorial] ADD  CONSTRAINT [CRMAgenteHistorial_DF__History__Created__40DC0D00]  DEFAULT (sysutcdatetime()) FOR [CreatedAt]
GO
ALTER TABLE [dbo].[CRMAgenteHistorial]  WITH CHECK ADD  CONSTRAINT [CRMAgenteHistorial_CK__History__Documen__3EF3C48E] CHECK  ((isjson([Document])=(1)))
GO
ALTER TABLE [dbo].[CRMAgenteHistorial] CHECK CONSTRAINT [CRMAgenteHistorial_CK__History__Documen__3EF3C48E]
GO
-- crm_agents.Profile -> dbo.CRMAgentePerfil
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMAgentePerfil](

	[AgentId] [uniqueidentifier] NOT NULL,

	[Level] [varchar](10) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[ParentId] [uniqueidentifier] NULL,

	[ProgramId] [int] NULL,

	[StageId] [uniqueidentifier] NULL,

	[State] [varchar](10) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Version] [bigint] NOT NULL,

	[Revision] [bigint] NOT NULL,

	[ApprovedVersion] [bigint] NULL,

	[Document] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[UpdatedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMAgentePerfil_PK__Profile__9AC3BFF1A1BA17BC] PRIMARY KEY CLUSTERED 

(

	[AgentId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
SET ANSI_PADDING ON
GO
CREATE UNIQUE NONCLUSTERED INDEX [CRMAgentePerfil_UX_Agents_Guide] ON [dbo].[CRMAgentePerfil]

(

	[Level] ASC

)

WHERE ([Level]='guide' AND [State]<>'archived')

WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, IGNORE_DUP_KEY = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
CREATE UNIQUE NONCLUSTERED INDEX [CRMAgentePerfil_UX_Agents_Program] ON [dbo].[CRMAgentePerfil]

(

	[ProgramId] ASC

)

WHERE ([Level]='program' AND [State]<>'archived')

WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, IGNORE_DUP_KEY = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
CREATE UNIQUE NONCLUSTERED INDEX [CRMAgentePerfil_UX_Agents_Stage] ON [dbo].[CRMAgentePerfil]

(

	[StageId] ASC

)

WHERE ([Level]='stage' AND [State]<>'archived')

WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, IGNORE_DUP_KEY = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
ALTER TABLE [dbo].[CRMAgentePerfil] ADD  CONSTRAINT [CRMAgentePerfil_DF__Profile__State__1BAA8851]  DEFAULT ('draft') FOR [State]
GO
ALTER TABLE [dbo].[CRMAgentePerfil] ADD  CONSTRAINT [CRMAgentePerfil_DF__Profile__Revisio__1E86F4FC]  DEFAULT ((1)) FOR [Revision]
GO
ALTER TABLE [dbo].[CRMAgentePerfil] ADD  CONSTRAINT [CRMAgentePerfil_DF__Profile__Updated__216361A7]  DEFAULT (sysutcdatetime()) FOR [UpdatedAt]
GO
ALTER TABLE [dbo].[CRMAgentePerfil]  WITH CHECK ADD  CONSTRAINT [CRMAgentePerfil_CK__Profile__234BAA19] CHECK  (([Level]='guide' AND [ParentId] IS NULL AND [ProgramId] IS NULL AND [StageId] IS NULL OR [Level]='program' AND [ParentId] IS NOT NULL AND [ProgramId] IS NOT NULL AND [StageId] IS NULL OR [Level]='stage' AND [ParentId] IS NOT NULL AND [ProgramId] IS NOT NULL AND [StageId] IS NOT NULL))
GO
ALTER TABLE [dbo].[CRMAgentePerfil] CHECK CONSTRAINT [CRMAgentePerfil_CK__Profile__234BAA19]
GO
ALTER TABLE [dbo].[CRMAgentePerfil]  WITH CHECK ADD  CONSTRAINT [CRMAgentePerfil_CK__Profile__243FCE52] CHECK  (([ParentId] IS NULL OR [ParentId]<>[AgentId]))
GO
ALTER TABLE [dbo].[CRMAgentePerfil] CHECK CONSTRAINT [CRMAgentePerfil_CK__Profile__243FCE52]
GO
ALTER TABLE [dbo].[CRMAgentePerfil]  WITH CHECK ADD  CONSTRAINT [CRMAgentePerfil_CK__Profile__2533F28B] CHECK  (([State]<>'active' OR [ApprovedVersion] IS NOT NULL AND [ApprovedVersion]=[Version]))
GO
ALTER TABLE [dbo].[CRMAgentePerfil] CHECK CONSTRAINT [CRMAgentePerfil_CK__Profile__2533F28B]
GO
ALTER TABLE [dbo].[CRMAgentePerfil]  WITH CHECK ADD  CONSTRAINT [CRMAgentePerfil_CK__Profile__Documen__206F3D6E] CHECK  ((isjson([Document])=(1)))
GO
ALTER TABLE [dbo].[CRMAgentePerfil] CHECK CONSTRAINT [CRMAgentePerfil_CK__Profile__Documen__206F3D6E]
GO
ALTER TABLE [dbo].[CRMAgentePerfil]  WITH CHECK ADD  CONSTRAINT [CRMAgentePerfil_CK__Profile__Level__19C23FDF] CHECK  (([Level]='stage' OR [Level]='program' OR [Level]='guide'))
GO
ALTER TABLE [dbo].[CRMAgentePerfil] CHECK CONSTRAINT [CRMAgentePerfil_CK__Profile__Level__19C23FDF]
GO
ALTER TABLE [dbo].[CRMAgentePerfil]  WITH CHECK ADD  CONSTRAINT [CRMAgentePerfil_CK__Profile__Revisio__1F7B1935] CHECK  (([Revision]>(0)))
GO
ALTER TABLE [dbo].[CRMAgentePerfil] CHECK CONSTRAINT [CRMAgentePerfil_CK__Profile__Revisio__1F7B1935]
GO
ALTER TABLE [dbo].[CRMAgentePerfil]  WITH CHECK ADD  CONSTRAINT [CRMAgentePerfil_CK__Profile__State__1C9EAC8A] CHECK  (([State]='archived' OR [State]='paused' OR [State]='active' OR [State]='draft'))
GO
ALTER TABLE [dbo].[CRMAgentePerfil] CHECK CONSTRAINT [CRMAgentePerfil_CK__Profile__State__1C9EAC8A]
GO
ALTER TABLE [dbo].[CRMAgentePerfil]  WITH CHECK ADD  CONSTRAINT [CRMAgentePerfil_CK__Profile__Version__1D92D0C3] CHECK  (([Version]>(0)))
GO
ALTER TABLE [dbo].[CRMAgentePerfil] CHECK CONSTRAINT [CRMAgentePerfil_CK__Profile__Version__1D92D0C3]
GO
-- crm_agents.SourceScope -> dbo.CRMAgenteFuenteAlcance
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[CRMAgenteFuenteAlcance](

	[DocumentId] [uniqueidentifier] NOT NULL,

	[ProgramId] [int] NULL,

	[StageId] [uniqueidentifier] NULL,

	[Owner] [nvarchar](100) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[ValidUntil] [date] NOT NULL,

	[Revision] [bigint] NOT NULL,

	[DocumentRevision] [bigint] NOT NULL,

	[ApprovedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMAgenteFuenteAlcance_PK__SourceSc__1ABEEF0F840CFBAB] PRIMARY KEY CLUSTERED 

(

	[DocumentId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
ALTER TABLE [dbo].[CRMAgenteFuenteAlcance] ADD  CONSTRAINT [CRMAgenteFuenteAlcance_DF__SourceSco__Appro__338211E2]  DEFAULT (sysutcdatetime()) FOR [ApprovedAt]
GO
ALTER TABLE [dbo].[CRMAgenteFuenteAlcance]  WITH CHECK ADD  CONSTRAINT [CRMAgenteFuenteAlcance_CK__SourceSco__Revis__328DEDA9] CHECK  (([Revision]>(0)))
GO
ALTER TABLE [dbo].[CRMAgenteFuenteAlcance] CHECK CONSTRAINT [CRMAgenteFuenteAlcance_CK__SourceSco__Revis__328DEDA9]
GO
ALTER TABLE [dbo].[CRMAgenteFuenteAlcance]  WITH CHECK ADD  CONSTRAINT [CRMAgenteFuenteAlcance_CK__SourceScope__356A5A54] CHECK  (([StageId] IS NULL OR [ProgramId] IS NOT NULL))
GO
ALTER TABLE [dbo].[CRMAgenteFuenteAlcance] CHECK CONSTRAINT [CRMAgenteFuenteAlcance_CK__SourceScope__356A5A54]
GO
-- crm_agents.Stage -> dbo.CRMAgenteEtapa
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[CRMAgenteEtapa](

	[StageId] [uniqueidentifier] NOT NULL,

	[ProgramId] [int] NOT NULL,

	[Name] [nvarchar](100) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[EntryRule] [nvarchar](1000) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[ExitRule] [nvarchar](1000) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[EvidenceRequired] [nvarchar](1000) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Revision] [bigint] NOT NULL,

	[ApprovedRevision] [bigint] NULL,

	[ApprovedAt] [datetime2](7) NULL,

 CONSTRAINT [CRMAgenteEtapa_PK__Stage__03EB7AD812D06BCA] PRIMARY KEY CLUSTERED 

(

	[StageId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF),

 CONSTRAINT [CRMAgenteEtapa_UQ__Stage__121238168FDA46A0] UNIQUE NONCLUSTERED 

(

	[ProgramId] ASC,

	[Name] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF),

 CONSTRAINT [CRMAgenteEtapa_UQ__Stage__94B92CDC50C1434D] UNIQUE NONCLUSTERED 

(

	[StageId] ASC,

	[ProgramId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
ALTER TABLE [dbo].[CRMAgenteEtapa]  WITH CHECK ADD  CONSTRAINT [CRMAgenteEtapa_CK__Stage__15F1AEFB] CHECK  (([ApprovedRevision] IS NULL OR [ApprovedRevision]=[Revision]))
GO
ALTER TABLE [dbo].[CRMAgenteEtapa] CHECK CONSTRAINT [CRMAgenteEtapa_CK__Stage__15F1AEFB]
GO
ALTER TABLE [dbo].[CRMAgenteEtapa]  WITH CHECK ADD  CONSTRAINT [CRMAgenteEtapa_CK__Stage__Revision__14FD8AC2] CHECK  (([Revision]>(0)))
GO
ALTER TABLE [dbo].[CRMAgenteEtapa] CHECK CONSTRAINT [CRMAgenteEtapa_CK__Stage__Revision__14FD8AC2]
GO
-- crm_agents.Usage -> dbo.CRMAgenteConsumo
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMAgenteConsumo](

	[RequestId] [uniqueidentifier] NOT NULL,

	[AgentId] [uniqueidentifier] NOT NULL,

	[ChainJson] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[TokensReserved] [int] NOT NULL,

	[TokensUsed] [int] NULL,

	[State] [varchar](12) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[CreatedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMAgenteConsumo_PK__Usage__33A8517A871B8B5F] PRIMARY KEY CLUSTERED 

(

	[RequestId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
ALTER TABLE [dbo].[CRMAgenteConsumo] ADD  CONSTRAINT [CRMAgenteConsumo_DF__Usage__CreatedAt__487D2EC8]  DEFAULT (sysutcdatetime()) FOR [CreatedAt]
GO
ALTER TABLE [dbo].[CRMAgenteConsumo]  WITH CHECK ADD  CONSTRAINT [CRMAgenteConsumo_CK__Usage__ChainJson__44AC9DE4] CHECK  ((isjson([ChainJson])=(1)))
GO
ALTER TABLE [dbo].[CRMAgenteConsumo] CHECK CONSTRAINT [CRMAgenteConsumo_CK__Usage__ChainJson__44AC9DE4]
GO
ALTER TABLE [dbo].[CRMAgenteConsumo]  WITH CHECK ADD  CONSTRAINT [CRMAgenteConsumo_CK__Usage__State__47890A8F] CHECK  (([State]='uncertain' OR [State]='completed' OR [State]='reserved'))
GO
ALTER TABLE [dbo].[CRMAgenteConsumo] CHECK CONSTRAINT [CRMAgenteConsumo_CK__Usage__State__47890A8F]
GO
ALTER TABLE [dbo].[CRMAgenteConsumo]  WITH CHECK ADD  CONSTRAINT [CRMAgenteConsumo_CK__Usage__TokensRes__45A0C21D] CHECK  (([TokensReserved]>(0)))
GO
ALTER TABLE [dbo].[CRMAgenteConsumo] CHECK CONSTRAINT [CRMAgenteConsumo_CK__Usage__TokensRes__45A0C21D]
GO
ALTER TABLE [dbo].[CRMAgenteConsumo]  WITH CHECK ADD  CONSTRAINT [CRMAgenteConsumo_CK__Usage__TokensUse__4694E656] CHECK  (([TokensUsed]>=(0)))
GO
ALTER TABLE [dbo].[CRMAgenteConsumo] CHECK CONSTRAINT [CRMAgenteConsumo_CK__Usage__TokensUse__4694E656]
GO
-- crm_ai.AdmissionsPolicy -> dbo.CRMIAAdmisionPolitica
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[CRMIAAdmisionPolitica](

	[PolicyId] [tinyint] NOT NULL,

	[Revision] [bigint] NOT NULL,

	[Enabled] [bit] NOT NULL,

	[ActivationSequence] [bigint] NOT NULL,

	[KnowledgeRevision] [bigint] NOT NULL,

	[Document] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[UpdatedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMIAAdmisionPolitica_PK__Admissio__2E1339A48224CDE9] PRIMARY KEY CLUSTERED 

(

	[PolicyId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
ALTER TABLE [dbo].[CRMIAAdmisionPolitica] ADD  CONSTRAINT [CRMIAAdmisionPolitica_DF__Admission__Revis__5DE26002]  DEFAULT ((0)) FOR [Revision]
GO
ALTER TABLE [dbo].[CRMIAAdmisionPolitica] ADD  CONSTRAINT [CRMIAAdmisionPolitica_DF__Admission__Enabl__5ED6843B]  DEFAULT ((0)) FOR [Enabled]
GO
ALTER TABLE [dbo].[CRMIAAdmisionPolitica] ADD  CONSTRAINT [CRMIAAdmisionPolitica_DF__Admission__Activ__5FCAA874]  DEFAULT ((0)) FOR [ActivationSequence]
GO
ALTER TABLE [dbo].[CRMIAAdmisionPolitica] ADD  CONSTRAINT [CRMIAAdmisionPolitica_DF__Admission__Knowl__60BECCAD]  DEFAULT ((0)) FOR [KnowledgeRevision]
GO
ALTER TABLE [dbo].[CRMIAAdmisionPolitica] ADD  CONSTRAINT [CRMIAAdmisionPolitica_DF__Admission__Updat__62A7151F]  DEFAULT (sysutcdatetime()) FOR [UpdatedAt]
GO
ALTER TABLE [dbo].[CRMIAAdmisionPolitica]  WITH CHECK ADD  CONSTRAINT [CRMIAAdmisionPolitica_CK__Admission__Docum__61B2F0E6] CHECK  ((isjson([Document])=(1)))
GO
ALTER TABLE [dbo].[CRMIAAdmisionPolitica] CHECK CONSTRAINT [CRMIAAdmisionPolitica_CK__Admission__Docum__61B2F0E6]
GO
ALTER TABLE [dbo].[CRMIAAdmisionPolitica]  WITH CHECK ADD  CONSTRAINT [CRMIAAdmisionPolitica_CK__Admission__Polic__5CEE3BC9] CHECK  (([PolicyId]=(1)))
GO
ALTER TABLE [dbo].[CRMIAAdmisionPolitica] CHECK CONSTRAINT [CRMIAAdmisionPolitica_CK__Admission__Polic__5CEE3BC9]
GO
-- crm_ai.Configuration -> dbo.CRMIAConfiguracion
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[CRMIAConfiguracion](

	[ConfigurationId] [tinyint] NOT NULL,

	[Revision] [int] NOT NULL,

	[Document] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[UpdatedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMIAConfiguracion_PK__Configur__95AA53BB9ABAEB46] PRIMARY KEY CLUSTERED 

(

	[ConfigurationId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
ALTER TABLE [dbo].[CRMIAConfiguracion] ADD  CONSTRAINT [CRMIAConfiguracion_DF__Configura__Updat__296E97C3]  DEFAULT (sysutcdatetime()) FOR [UpdatedAt]
GO
ALTER TABLE [dbo].[CRMIAConfiguracion]  WITH CHECK ADD  CONSTRAINT [CRMIAConfiguracion_CK__Configura__Confi__26922B18] CHECK  (([ConfigurationId]=(1)))
GO
ALTER TABLE [dbo].[CRMIAConfiguracion] CHECK CONSTRAINT [CRMIAConfiguracion_CK__Configura__Confi__26922B18]
GO
ALTER TABLE [dbo].[CRMIAConfiguracion]  WITH CHECK ADD  CONSTRAINT [CRMIAConfiguracion_CK__Configura__Docum__287A738A] CHECK  ((isjson([Document])=(1)))
GO
ALTER TABLE [dbo].[CRMIAConfiguracion] CHECK CONSTRAINT [CRMIAConfiguracion_CK__Configura__Docum__287A738A]
GO
ALTER TABLE [dbo].[CRMIAConfiguracion]  WITH CHECK ADD  CONSTRAINT [CRMIAConfiguracion_CK__Configura__Revis__27864F51] CHECK  (([Revision]>=(0)))
GO
ALTER TABLE [dbo].[CRMIAConfiguracion] CHECK CONSTRAINT [CRMIAConfiguracion_CK__Configura__Revis__27864F51]
GO
-- crm_ai.Connection -> dbo.CRMIAConexion
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[CRMIAConexion](

	[ConnectionId] [tinyint] NOT NULL,

	[Revision] [int] NOT NULL,

	[Outbound] [bit] NOT NULL,

	[UpdatedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMIAConexion_PK__Connecti__404A6493C7A90FFE] PRIMARY KEY CLUSTERED 

(

	[ConnectionId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
ALTER TABLE [dbo].[CRMIAConexion] ADD  CONSTRAINT [CRMIAConexion_DF__Connectio__Revis__2D3F28A7]  DEFAULT ((0)) FOR [Revision]
GO
ALTER TABLE [dbo].[CRMIAConexion] ADD  CONSTRAINT [CRMIAConexion_DF__Connectio__Outbo__2F277119]  DEFAULT ((0)) FOR [Outbound]
GO
ALTER TABLE [dbo].[CRMIAConexion] ADD  CONSTRAINT [CRMIAConexion_DF__Connectio__Updat__301B9552]  DEFAULT (sysutcdatetime()) FOR [UpdatedAt]
GO
ALTER TABLE [dbo].[CRMIAConexion]  WITH CHECK ADD  CONSTRAINT [CRMIAConexion_CK__Connectio__Conne__2C4B046E] CHECK  (([ConnectionId]=(1)))
GO
ALTER TABLE [dbo].[CRMIAConexion] CHECK CONSTRAINT [CRMIAConexion_CK__Connectio__Conne__2C4B046E]
GO
ALTER TABLE [dbo].[CRMIAConexion]  WITH CHECK ADD  CONSTRAINT [CRMIAConexion_CK__Connectio__Revis__2E334CE0] CHECK  (([Revision]>=(0)))
GO
ALTER TABLE [dbo].[CRMIAConexion] CHECK CONSTRAINT [CRMIAConexion_CK__Connectio__Revis__2E334CE0]
GO
-- crm_ai.Credential -> dbo.CRMIACredencial
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMIACredencial](

	[Provider] [varchar](24) COLLATE Latin1_General_100_BIN2 NOT NULL,

	[KeyId] [varchar](32) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Nonce] [binary](12) NOT NULL,

	[Ciphertext] [varbinary](max) NOT NULL,

	[UpdatedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMIACredencial_PK__Credenti__9944610AA7381B77] PRIMARY KEY CLUSTERED 

(

	[Provider] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
ALTER TABLE [dbo].[CRMIACredencial] ADD  CONSTRAINT [CRMIACredencial_DF__Credentia__Updat__32F801FD]  DEFAULT (sysutcdatetime()) FOR [UpdatedAt]
GO
ALTER TABLE [dbo].[CRMIACredencial]  WITH CHECK ADD  CONSTRAINT [CRMIACredencial_CK_crm_ai_Credential_Provider] CHECK  (([Provider]='serpapi' OR [Provider]='brave' OR [Provider]='tavily' OR [Provider]='google_tts' OR [Provider]='elevenlabs' OR [Provider]='xai' OR [Provider]='kimi' OR [Provider]='openrouter' OR [Provider]='mistral' OR [Provider]='groq' OR [Provider]='hermes' OR [Provider]='anthropic' OR [Provider]='openai' OR [Provider]='nvidia' OR [Provider]='gemini'))
GO
ALTER TABLE [dbo].[CRMIACredencial] CHECK CONSTRAINT [CRMIACredencial_CK_crm_ai_Credential_Provider]
GO
-- crm_ai.KnowledgeChunk -> dbo.CRMConocimientoFragmento
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[CRMConocimientoFragmento](

	[ChunkId] [uniqueidentifier] NOT NULL,

	[DocumentId] [uniqueidentifier] NOT NULL,

	[Ordinal] [int] NOT NULL,

	[PageNumber] [int] NOT NULL,

	[Body] [nvarchar](1800) COLLATE Modern_Spanish_CI_AS NOT NULL,

 CONSTRAINT [CRMConocimientoFragmento_PK__Knowledg__FBFF9D00B09181C3] PRIMARY KEY CLUSTERED 

(

	[ChunkId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF),

 CONSTRAINT [CRMConocimientoFragmento_UQ__Knowledg__D4BBBE878F9BDCBF] UNIQUE NONCLUSTERED 

(

	[DocumentId] ASC,

	[Ordinal] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
-- crm_ai.KnowledgeDocument -> dbo.CRMConocimientoDocumento
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMConocimientoDocumento](

	[DocumentId] [uniqueidentifier] NOT NULL,

	[Title] [nvarchar](160) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[FileName] [nvarchar](160) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[ContentHash] [binary](32) NOT NULL,

	[ByteLength] [int] NOT NULL,

	[State] [varchar](10) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Revision] [bigint] NOT NULL,

	[CreatedAt] [datetime2](7) NOT NULL,

	[UpdatedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMConocimientoDocumento_PK__Knowledg__1ABEEF0F815B1292] PRIMARY KEY CLUSTERED 

(

	[DocumentId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
ALTER TABLE [dbo].[CRMConocimientoDocumento] ADD  CONSTRAINT [CRMConocimientoDocumento_DF__Knowledge__Revis__676BCA3C]  DEFAULT ((0)) FOR [Revision]
GO
ALTER TABLE [dbo].[CRMConocimientoDocumento] ADD  CONSTRAINT [CRMConocimientoDocumento_DF__Knowledge__Creat__685FEE75]  DEFAULT (sysutcdatetime()) FOR [CreatedAt]
GO
ALTER TABLE [dbo].[CRMConocimientoDocumento] ADD  CONSTRAINT [CRMConocimientoDocumento_DF__Knowledge__Updat__695412AE]  DEFAULT (sysutcdatetime()) FOR [UpdatedAt]
GO
ALTER TABLE [dbo].[CRMConocimientoDocumento]  WITH CHECK ADD  CONSTRAINT [CRMConocimientoDocumento_CK__Knowledge__ByteL__658381CA] CHECK  (([ByteLength]>=(1) AND [ByteLength]<=(5000000)))
GO
ALTER TABLE [dbo].[CRMConocimientoDocumento] CHECK CONSTRAINT [CRMConocimientoDocumento_CK__Knowledge__ByteL__658381CA]
GO
ALTER TABLE [dbo].[CRMConocimientoDocumento]  WITH CHECK ADD  CONSTRAINT [CRMConocimientoDocumento_CK__Knowledge__State__6677A603] CHECK  (([State]='deleted' OR [State]='disabled' OR [State]='published' OR [State]='draft'))
GO
ALTER TABLE [dbo].[CRMConocimientoDocumento] CHECK CONSTRAINT [CRMConocimientoDocumento_CK__Knowledge__State__6677A603]
GO
-- crm_ai.KnowledgeTerm -> dbo.CRMConocimientoTermino
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[CRMConocimientoTermino](

	[Term] [nvarchar](64) COLLATE Latin1_General_100_CI_AI NOT NULL,

	[ChunkId] [uniqueidentifier] NOT NULL,

	[Frequency] [smallint] NOT NULL,

 CONSTRAINT [CRMConocimientoTermino_PK__Knowledg__90C604B8BF9F037D] PRIMARY KEY CLUSTERED 

(

	[Term] ASC,

	[ChunkId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
CREATE NONCLUSTERED INDEX [CRMConocimientoTermino_IX_KnowledgeTerm_Chunk] ON [dbo].[CRMConocimientoTermino]

(

	[ChunkId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
ALTER TABLE [dbo].[CRMConocimientoTermino]  WITH CHECK ADD  CONSTRAINT [CRMConocimientoTermino_CK__Knowledge__Frequ__70F53476] CHECK  (([Frequency]>(0)))
GO
ALTER TABLE [dbo].[CRMConocimientoTermino] CHECK CONSTRAINT [CRMConocimientoTermino_CK__Knowledge__Frequ__70F53476]
GO
-- crm_ai.ProspectMemory -> dbo.CRMProspectoMemoria
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[CRMProspectoMemoria](

	[ConversationId] [uniqueidentifier] NOT NULL,

	[Revision] [bigint] NOT NULL,

	[Generation] [bigint] NOT NULL,

	[BaselineSequence] [bigint] NOT NULL,

	[Document] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[UpdatedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMProspectoMemoria_PK__Prospect__C050D8775B0A3801] PRIMARY KEY CLUSTERED 

(

	[ConversationId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
ALTER TABLE [dbo].[CRMProspectoMemoria] ADD  CONSTRAINT [CRMProspectoMemoria_DF__ProspectM__Revis__74C5C55A]  DEFAULT ((0)) FOR [Revision]
GO
ALTER TABLE [dbo].[CRMProspectoMemoria] ADD  CONSTRAINT [CRMProspectoMemoria_DF__ProspectM__Gener__75B9E993]  DEFAULT ((0)) FOR [Generation]
GO
ALTER TABLE [dbo].[CRMProspectoMemoria] ADD  CONSTRAINT [CRMProspectoMemoria_DF__ProspectM__Basel__76AE0DCC]  DEFAULT ((0)) FOR [BaselineSequence]
GO
ALTER TABLE [dbo].[CRMProspectoMemoria] ADD  CONSTRAINT [CRMProspectoMemoria_DF__ProspectM__Docum__77A23205]  DEFAULT ('{}') FOR [Document]
GO
ALTER TABLE [dbo].[CRMProspectoMemoria] ADD  CONSTRAINT [CRMProspectoMemoria_DF__ProspectM__Updat__798A7A77]  DEFAULT (sysutcdatetime()) FOR [UpdatedAt]
GO
ALTER TABLE [dbo].[CRMProspectoMemoria]  WITH CHECK ADD  CONSTRAINT [CRMProspectoMemoria_CK__ProspectM__Docum__7896563E] CHECK  ((isjson([Document])=(1)))
GO
ALTER TABLE [dbo].[CRMProspectoMemoria] CHECK CONSTRAINT [CRMProspectoMemoria_CK__ProspectM__Docum__7896563E]
GO
-- crm_ai.ResponseJob -> dbo.CRMRespuestaTrabajo
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMRespuestaTrabajo](

	[MessageId] [uniqueidentifier] NOT NULL,

	[ConversationId] [uniqueidentifier] NOT NULL,

	[IdentityId] [uniqueidentifier] NOT NULL,

	[State] [varchar](12) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Attempts] [int] NOT NULL,

	[LeaseId] [uniqueidentifier] NULL,

	[DueAt] [datetime2](7) NOT NULL,

	[CreatedAt] [datetime2](7) NOT NULL,

	[ResponseMessageId] [uniqueidentifier] NULL,

	[TaskId] [uniqueidentifier] NULL,

	[Result] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[LastError] [varchar](80) COLLATE Modern_Spanish_CI_AS NULL,

 CONSTRAINT [CRMRespuestaTrabajo_PK__Response__C87C0C9C5CE74287] PRIMARY KEY CLUSTERED 

(

	[MessageId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
SET ANSI_PADDING ON
GO
CREATE NONCLUSTERED INDEX [CRMRespuestaTrabajo_IX_AdmissionsJob_Work] ON [dbo].[CRMRespuestaTrabajo]

(

	[State] ASC,

	[DueAt] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
ALTER TABLE [dbo].[CRMRespuestaTrabajo] ADD  CONSTRAINT [CRMRespuestaTrabajo_DF__ResponseJ__State__7F4353CD]  DEFAULT ('queued') FOR [State]
GO
ALTER TABLE [dbo].[CRMRespuestaTrabajo] ADD  CONSTRAINT [CRMRespuestaTrabajo_DF__ResponseJ__Attem__012B9C3F]  DEFAULT ((0)) FOR [Attempts]
GO
ALTER TABLE [dbo].[CRMRespuestaTrabajo] ADD  CONSTRAINT [CRMRespuestaTrabajo_DF__ResponseJ__DueAt__021FC078]  DEFAULT (sysutcdatetime()) FOR [DueAt]
GO
ALTER TABLE [dbo].[CRMRespuestaTrabajo] ADD  CONSTRAINT [CRMRespuestaTrabajo_DF__ResponseJ__Creat__0313E4B1]  DEFAULT (sysutcdatetime()) FOR [CreatedAt]
GO
ALTER TABLE [dbo].[CRMRespuestaTrabajo] ADD  CONSTRAINT [CRMRespuestaTrabajo_DF__ResponseJ__Resul__05F0515C]  DEFAULT ('{}') FOR [Result]
GO
ALTER TABLE [dbo].[CRMRespuestaTrabajo]  WITH CHECK ADD  CONSTRAINT [CRMRespuestaTrabajo_CK__ResponseJ__Resul__06E47595] CHECK  ((isjson([Result])=(1)))
GO
ALTER TABLE [dbo].[CRMRespuestaTrabajo] CHECK CONSTRAINT [CRMRespuestaTrabajo_CK__ResponseJ__Resul__06E47595]
GO
ALTER TABLE [dbo].[CRMRespuestaTrabajo]  WITH CHECK ADD  CONSTRAINT [CRMRespuestaTrabajo_CK__ResponseJ__State__00377806] CHECK  (([State]='handoff' OR [State]='failed' OR [State]='cancelled' OR [State]='completed' OR [State]='processing' OR [State]='queued'))
GO
ALTER TABLE [dbo].[CRMRespuestaTrabajo] CHECK CONSTRAINT [CRMRespuestaTrabajo_CK__ResponseJ__State__00377806]
GO
-- crm_analysis.Attempt -> dbo.CRMAnalisisIntento
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMAnalisisIntento](

	[AttemptId] [uniqueidentifier] NOT NULL,

	[ConversationId] [uniqueidentifier] NOT NULL,

	[Generation] [bigint] NOT NULL,

	[PolicyRevision] [bigint] NOT NULL,

	[ReservedOutputTokens] [int] NOT NULL,

	[Status] [varchar](16) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[CreatedAt] [datetime2](7) NOT NULL,

	[CompletedAt] [datetime2](7) NULL,

	[ErrorCode] [varchar](60) COLLATE Modern_Spanish_CI_AS NULL,

 CONSTRAINT [CRMAnalisisIntento_PK_AnalysisAttempt] PRIMARY KEY CLUSTERED 

(

	[AttemptId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
CREATE NONCLUSTERED INDEX [CRMAnalisisIntento_IX_AnalysisAttempt_Day] ON [dbo].[CRMAnalisisIntento]

(

	[CreatedAt] ASC

)

INCLUDE([ReservedOutputTokens]) WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
ALTER TABLE [dbo].[CRMAnalisisIntento]  WITH CHECK ADD  CONSTRAINT [CRMAnalisisIntento_CK_AnalysisAttempt] CHECK  (([ReservedOutputTokens]>=(256) AND [ReservedOutputTokens]<=(8192) AND ([Status]='expired' OR [Status]='stale' OR [Status]='failed' OR [Status]='succeeded' OR [Status]='reserved')))
GO
ALTER TABLE [dbo].[CRMAnalisisIntento] CHECK CONSTRAINT [CRMAnalisisIntento_CK_AnalysisAttempt]
GO
-- crm_analysis.ConversationState -> dbo.CRMAnalisisConversacionEstado
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMAnalisisConversacionEstado](

	[ConversationId] [uniqueidentifier] NOT NULL,

	[Revision] [bigint] NOT NULL,

	[Generation] [bigint] NOT NULL,

	[Binding] [varchar](200) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[ContextGeneration] [bigint] NULL,

	[ContextJson] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NULL,

	[AnalyzedAt] [datetime2](7) NULL,

	[ContextProvider] [varchar](16) COLLATE Modern_Spanish_CI_AS NULL,

	[ContextModel] [varchar](200) COLLATE Modern_Spanish_CI_AS NULL,

	[ContextPromptVersion] [varchar](40) COLLATE Modern_Spanish_CI_AS NULL,

	[ContextPolicyRevision] [bigint] NULL,

	[Fingerprint] [char](64) COLLATE Modern_Spanish_CI_AS NULL,

	[Status] [varchar](20) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[LeaseToken] [uniqueidentifier] NULL,

	[LeaseUntil] [datetime2](7) NULL,

	[Failures] [int] NOT NULL,

	[NextAttemptAt] [datetime2](7) NOT NULL,

	[ErrorCode] [varchar](60) COLLATE Modern_Spanish_CI_AS NULL,

 CONSTRAINT [CRMAnalisisConversacionEstado_PK_AnalysisState] PRIMARY KEY CLUSTERED 

(

	[ConversationId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
ALTER TABLE [dbo].[CRMAnalisisConversacionEstado]  WITH CHECK ADD  CONSTRAINT [CRMAnalisisConversacionEstado_CK_AnalysisState] CHECK  (([Revision]>=(0) AND [Generation]>(0) AND ([Failures]>=(0) AND [Failures]<=(3)) AND ([Status]='no_messages' OR [Status]='failed' OR [Status]='current' OR [Status]='processing' OR [Status]='pending') AND ([ContextJson] IS NULL OR isjson([ContextJson])=(1)) AND ([Status]='processing' AND [LeaseToken] IS NOT NULL AND [LeaseUntil] IS NOT NULL OR [Status]<>'processing' AND [LeaseToken] IS NULL AND [LeaseUntil] IS NULL)))
GO
ALTER TABLE [dbo].[CRMAnalisisConversacionEstado] CHECK CONSTRAINT [CRMAnalisisConversacionEstado_CK_AnalysisState]
GO
-- crm_analysis.Feedback -> dbo.CRMAnalisisEvaluacionHumana
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[CRMAnalisisEvaluacionHumana](

	[FeedbackId] [uniqueidentifier] NOT NULL,

	[ConversationId] [uniqueidentifier] NOT NULL,

	[SourceRevision] [bigint] NOT NULL,

	[Text] [nvarchar](1000) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[CreatedAt] [datetime2](7) NOT NULL,

	[ConsumedGeneration] [bigint] NOT NULL,

 CONSTRAINT [CRMAnalisisEvaluacionHumana_PK_AnalysisFeedback] PRIMARY KEY CLUSTERED 

(

	[FeedbackId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
ALTER TABLE [dbo].[CRMAnalisisEvaluacionHumana] ADD  CONSTRAINT [CRMAnalisisEvaluacionHumana_DF_AnalysisFeedback_Generation]  DEFAULT ((0)) FOR [ConsumedGeneration]
GO
-- crm_analysis.Operation -> dbo.CRMAnalisisOperacion
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMAnalisisOperacion](

	[OperationId] [uniqueidentifier] NOT NULL,

	[Action] [varchar](16) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[RequestHash] [char](64) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[ResponseJson] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[CreatedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMAnalisisOperacion_PK_AnalysisOperation] PRIMARY KEY CLUSTERED 

(

	[OperationId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
ALTER TABLE [dbo].[CRMAnalisisOperacion]  WITH CHECK ADD  CONSTRAINT [CRMAnalisisOperacion_CK_AnalysisOperation] CHECK  ((([Action]='feedback' OR [Action]='retry' OR [Action]='policy') AND isjson([ResponseJson])=(1)))
GO
ALTER TABLE [dbo].[CRMAnalisisOperacion] CHECK CONSTRAINT [CRMAnalisisOperacion_CK_AnalysisOperation]
GO
-- crm_analysis.Policy -> dbo.CRMAnalisisPolitica
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMAnalisisPolitica](

	[PolicyId] [tinyint] NOT NULL,

	[Revision] [bigint] NOT NULL,

	[Enabled] [bit] NOT NULL,

	[Provider] [varchar](16) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Model] [varchar](200) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[InputScope] [varchar](30) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[ScopeAccepted] [bit] NOT NULL,

	[DailyRequests] [int] NOT NULL,

	[DailyOutputTokens] [int] NOT NULL,

	[OutputTokens] [int] NOT NULL,

	[UpdatedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMAnalisisPolitica_PK_AnalysisPolicy] PRIMARY KEY CLUSTERED 

(

	[PolicyId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
ALTER TABLE [dbo].[CRMAnalisisPolitica]  WITH CHECK ADD  CONSTRAINT [CRMAnalisisPolitica_CK_AnalysisPolicy] CHECK  (([PolicyId]=(1) AND [Revision]>(0) AND ([Provider]='openrouter' OR [Provider]='xai' OR [Provider]='gemini') AND [InputScope]='redacted_messages' AND ([Enabled]=(0) OR [ScopeAccepted]=(1)) AND ([DailyRequests]>=(1) AND [DailyRequests]<=(10000)) AND ([DailyOutputTokens]>=(256) AND [DailyOutputTokens]<=(10000000)) AND ([OutputTokens]>=(256) AND [OutputTokens]<=(8192)) AND [OutputTokens]<=[DailyOutputTokens]))
GO
ALTER TABLE [dbo].[CRMAnalisisPolitica] CHECK CONSTRAINT [CRMAnalisisPolitica_CK_AnalysisPolicy]
GO
-- crm_analysis.Receipt -> dbo.CRMAnalisisRecepcion
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[CRMAnalisisRecepcion](

	[ConversationId] [uniqueidentifier] NOT NULL,

	[Generation] [bigint] NOT NULL,

	[EventId] [bigint] NOT NULL,

	[CompletedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMAnalisisRecepcion_PK_AnalysisReceipt] PRIMARY KEY CLUSTERED 

(

	[ConversationId] ASC,

	[Generation] ASC,

	[EventId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
-- crm_channels.Account -> dbo.CRMCanalCuenta
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMCanalCuenta](

	[Channel] [varchar](12) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Configuration] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[State] [varchar](24) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Revision] [int] NOT NULL,

	[Capabilities] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[LastError] [varchar](80) COLLATE Modern_Spanish_CI_AS NULL,

	[VerifiedAt] [datetime2](7) NULL,

	[UpdatedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMCanalCuenta_PK__Account__CFDCDBF831A2C340] PRIMARY KEY CLUSTERED 

(

	[Channel] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
ALTER TABLE [dbo].[CRMCanalCuenta] ADD  CONSTRAINT [CRMCanalCuenta_DF__Account__State__7406AB4B]  DEFAULT ('configured') FOR [State]
GO
ALTER TABLE [dbo].[CRMCanalCuenta] ADD  CONSTRAINT [CRMCanalCuenta_DF__Account__Revisio__74FACF84]  DEFAULT ((1)) FOR [Revision]
GO
ALTER TABLE [dbo].[CRMCanalCuenta] ADD  CONSTRAINT [CRMCanalCuenta_DF__Account__Capabil__75EEF3BD]  DEFAULT ('{}') FOR [Capabilities]
GO
ALTER TABLE [dbo].[CRMCanalCuenta] ADD  CONSTRAINT [CRMCanalCuenta_DF__Account__Updated__77D73C2F]  DEFAULT (sysutcdatetime()) FOR [UpdatedAt]
GO
ALTER TABLE [dbo].[CRMCanalCuenta]  WITH CHECK ADD  CONSTRAINT [CRMCanalCuenta_CK__Account__Capabil__76E317F6] CHECK  ((isjson([Capabilities])=(1)))
GO
ALTER TABLE [dbo].[CRMCanalCuenta] CHECK CONSTRAINT [CRMCanalCuenta_CK__Account__Capabil__76E317F6]
GO
ALTER TABLE [dbo].[CRMCanalCuenta]  WITH CHECK ADD  CONSTRAINT [CRMCanalCuenta_CK__Account__Channel__78CB6068] CHECK  (([Channel]='tiktok' OR [Channel]='instagram' OR [Channel]='messenger' OR [Channel]='facebook' OR [Channel]='whatsapp'))
GO
ALTER TABLE [dbo].[CRMCanalCuenta] CHECK CONSTRAINT [CRMCanalCuenta_CK__Account__Channel__78CB6068]
GO
ALTER TABLE [dbo].[CRMCanalCuenta]  WITH CHECK ADD  CONSTRAINT [CRMCanalCuenta_CK__Account__Configu__73128712] CHECK  ((isjson([Configuration])=(1)))
GO
ALTER TABLE [dbo].[CRMCanalCuenta] CHECK CONSTRAINT [CRMCanalCuenta_CK__Account__Configu__73128712]
GO
-- crm_channels.Audit -> dbo.CRMCanalAuditoria
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMCanalAuditoria](

	[Revision] [bigint] IDENTITY(1,1) NOT NULL,

	[Channel] [varchar](12) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Action] [varchar](40) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[EntityId] [uniqueidentifier] NULL,

	[CreatedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMCanalAuditoria_PK__Audit__E83095CD4DEE2541] PRIMARY KEY CLUSTERED 

(

	[Revision] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
ALTER TABLE [dbo].[CRMCanalAuditoria] ADD  CONSTRAINT [CRMCanalAuditoria_DF__Audit__CreatedAt__20D951C2]  DEFAULT (sysutcdatetime()) FOR [CreatedAt]
GO
-- crm_channels.ConversationControl -> dbo.CRMConversacionControl
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[CRMConversacionControl](

	[ConversationId] [uniqueidentifier] NOT NULL,

	[Epoch] [bigint] NOT NULL,

	[ReadSequence] [bigint] NOT NULL,

 CONSTRAINT [CRMConversacionControl_PK__Conversa__C050D87732D83A5B] PRIMARY KEY CLUSTERED 

(

	[ConversationId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
ALTER TABLE [dbo].[CRMConversacionControl] ADD  CONSTRAINT [CRMConversacionControl_DF__Conversat__Epoch__3E69B4A9]  DEFAULT ((0)) FOR [Epoch]
GO
ALTER TABLE [dbo].[CRMConversacionControl] ADD  CONSTRAINT [CRMConversacionControl_DF__Conversat__ReadS__4051FD1B]  DEFAULT ((0)) FOR [ReadSequence]
GO
ALTER TABLE [dbo].[CRMConversacionControl]  WITH CHECK ADD  CONSTRAINT [CRMConversacionControl_CK__Conversat__Epoch__3F5DD8E2] CHECK  (([Epoch]>=(0)))
GO
ALTER TABLE [dbo].[CRMConversacionControl] CHECK CONSTRAINT [CRMConversacionControl_CK__Conversat__Epoch__3F5DD8E2]
GO
ALTER TABLE [dbo].[CRMConversacionControl]  WITH CHECK ADD  CONSTRAINT [CRMConversacionControl_CK__Conversat__ReadS__41462154] CHECK  (([ReadSequence]>=(0)))
GO
ALTER TABLE [dbo].[CRMConversacionControl] CHECK CONSTRAINT [CRMConversacionControl_CK__Conversat__ReadS__41462154]
GO
-- crm_channels.ConversationProfile -> dbo.CRMConversacionPerfil
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMConversacionPerfil](

	[ConversationId] [uniqueidentifier] NOT NULL,

	[LeadScore] [tinyint] NULL,

	[Temperature] [varchar](4) COLLATE Modern_Spanish_CI_AS NULL,

	[UpdatedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMConversacionPerfil_PK__Conversa__C050D8776909C21F] PRIMARY KEY CLUSTERED 

(

	[ConversationId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
ALTER TABLE [dbo].[CRMConversacionPerfil] ADD  CONSTRAINT [CRMConversacionPerfil_DF__Conversat__Updat__3A9923C5]  DEFAULT (sysutcdatetime()) FOR [UpdatedAt]
GO
ALTER TABLE [dbo].[CRMConversacionPerfil]  WITH CHECK ADD  CONSTRAINT [CRMConversacionPerfil_CK__Conversat__LeadS__38B0DB53] CHECK  (([LeadScore]>=(0) AND [LeadScore]<=(100)))
GO
ALTER TABLE [dbo].[CRMConversacionPerfil] CHECK CONSTRAINT [CRMConversacionPerfil_CK__Conversat__LeadS__38B0DB53]
GO
ALTER TABLE [dbo].[CRMConversacionPerfil]  WITH CHECK ADD  CONSTRAINT [CRMConversacionPerfil_CK__Conversat__Tempe__39A4FF8C] CHECK  (([Temperature]='hot' OR [Temperature]='warm' OR [Temperature]='cold'))
GO
ALTER TABLE [dbo].[CRMConversacionPerfil] CHECK CONSTRAINT [CRMConversacionPerfil_CK__Conversat__Tempe__39A4FF8C]
GO
-- crm_channels.Credential -> dbo.CRMCanalCredencial
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMCanalCredencial](

	[Channel] [varchar](12) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Kind] [varchar](24) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[KeyId] [varchar](32) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Nonce] [binary](12) NOT NULL,

	[Ciphertext] [varbinary](max) NOT NULL,

 CONSTRAINT [CRMCanalCredencial_PK__Credenti__58A3D1DD317D7F30] PRIMARY KEY CLUSTERED 

(

	[Channel] ASC,

	[Kind] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
-- crm_channels.ExternalIdentity -> dbo.CRMIdentidadExterna
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMIdentidadExterna](

	[IdentityId] [uniqueidentifier] NOT NULL,

	[Channel] [varchar](12) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[ExternalId] [nvarchar](128) COLLATE Latin1_General_100_BIN2 NOT NULL,

	[ContactId] [uniqueidentifier] NOT NULL,

	[ConversationId] [uniqueidentifier] NOT NULL,

	[LastIncomingAt] [datetime2](7) NULL,

 CONSTRAINT [CRMIdentidadExterna_PK__External__30667A4549D0CA75] PRIMARY KEY CLUSTERED 

(

	[IdentityId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF),

 CONSTRAINT [CRMIdentidadExterna_UQ_Channels_Identity] UNIQUE NONCLUSTERED 

(

	[Channel] ASC,

	[ExternalId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
-- crm_channels.ExternalMessage -> dbo.CRMMensajeExterno
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMMensajeExterno](

	[Channel] [varchar](12) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[ExternalId] [nvarchar](200) COLLATE Latin1_General_100_BIN2 NOT NULL,

	[MessageId] [uniqueidentifier] NULL,

	[Payload] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

 CONSTRAINT [CRMMensajeExterno_PK_Channels_ExternalMessage] PRIMARY KEY CLUSTERED 

(

	[Channel] ASC,

	[ExternalId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
ALTER TABLE [dbo].[CRMMensajeExterno]  WITH CHECK ADD  CONSTRAINT [CRMMensajeExterno_CK__ExternalM__Paylo__0DC67D4E] CHECK  ((isjson([Payload])=(1)))
GO
ALTER TABLE [dbo].[CRMMensajeExterno] CHECK CONSTRAINT [CRMMensajeExterno_CK__ExternalM__Paylo__0DC67D4E]
GO
-- crm_channels.MediaAsset -> dbo.CRMArchivoMultimedia
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMArchivoMultimedia](

	[MediaId] [uniqueidentifier] NOT NULL,

	[ConversationId] [uniqueidentifier] NOT NULL,

	[MessageId] [uniqueidentifier] NULL,

	[IdentityId] [uniqueidentifier] NULL,

	[Channel] [varchar](12) COLLATE Modern_Spanish_CI_AS NULL,

	[SourceKind] [varchar](8) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[State] [varchar](12) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Kind] [varchar](8) COLLATE Modern_Spanish_CI_AS NULL,

	[FileName] [nvarchar](160) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[ActualMime] [varchar](100) COLLATE Modern_Spanish_CI_AS NULL,

	[StorageKey] [varchar](40) COLLATE Modern_Spanish_CI_AS NULL,

	[ByteLength] [bigint] NULL,

	[ContentHash] [binary](32) NULL,

	[SourceHash] [binary](32) NULL,

	[DurationSeconds] [decimal](9, 3) NULL,

	[ProviderReference] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Attempts] [int] NOT NULL,

	[DueAt] [datetime2](7) NOT NULL,

	[LeaseId] [uniqueidentifier] NULL,

	[LastError] [varchar](80) COLLATE Modern_Spanish_CI_AS NULL,

	[CreatedAt] [datetime2](7) NOT NULL,

	[ExpiresAt] [datetime2](7) NULL,

 CONSTRAINT [CRMArchivoMultimedia_PK__MediaAss__B2C2B5CF552CDC30] PRIMARY KEY CLUSTERED 

(

	[MediaId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
CREATE NONCLUSTERED INDEX [CRMArchivoMultimedia_IX_InboxMedia_Conversation] ON [dbo].[CRMArchivoMultimedia]

(

	[ConversationId] ASC,

	[CreatedAt] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
CREATE UNIQUE NONCLUSTERED INDEX [CRMArchivoMultimedia_IX_InboxMedia_Message] ON [dbo].[CRMArchivoMultimedia]

(

	[MessageId] ASC

)

WHERE ([MessageId] IS NOT NULL)

WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, IGNORE_DUP_KEY = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
SET ANSI_PADDING ON
GO
CREATE NONCLUSTERED INDEX [CRMArchivoMultimedia_IX_InboxMedia_Work] ON [dbo].[CRMArchivoMultimedia]

(

	[State] ASC,

	[DueAt] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
ALTER TABLE [dbo].[CRMArchivoMultimedia] ADD  CONSTRAINT [CRMArchivoMultimedia_DF__MediaAsse__Provi__5458F5C8]  DEFAULT ('{}') FOR [ProviderReference]
GO
ALTER TABLE [dbo].[CRMArchivoMultimedia] ADD  CONSTRAINT [CRMArchivoMultimedia_DF__MediaAsse__Attem__56413E3A]  DEFAULT ((0)) FOR [Attempts]
GO
ALTER TABLE [dbo].[CRMArchivoMultimedia] ADD  CONSTRAINT [CRMArchivoMultimedia_DF__MediaAsse__DueAt__57356273]  DEFAULT (sysutcdatetime()) FOR [DueAt]
GO
ALTER TABLE [dbo].[CRMArchivoMultimedia] ADD  CONSTRAINT [CRMArchivoMultimedia_DF__MediaAsse__Creat__582986AC]  DEFAULT (sysutcdatetime()) FOR [CreatedAt]
GO
ALTER TABLE [dbo].[CRMArchivoMultimedia]  WITH CHECK ADD  CONSTRAINT [CRMArchivoMultimedia_CK__MediaAsse__ByteL__5270AD56] CHECK  (([ByteLength]>(0) AND [ByteLength]<=(5000000)))
GO
ALTER TABLE [dbo].[CRMArchivoMultimedia] CHECK CONSTRAINT [CRMArchivoMultimedia_CK__MediaAsse__ByteL__5270AD56]
GO
ALTER TABLE [dbo].[CRMArchivoMultimedia]  WITH CHECK ADD  CONSTRAINT [CRMArchivoMultimedia_CK__MediaAsse__Durat__5364D18F] CHECK  (([DurationSeconds]>(0) AND [DurationSeconds]<=(300)))
GO
ALTER TABLE [dbo].[CRMArchivoMultimedia] CHECK CONSTRAINT [CRMArchivoMultimedia_CK__MediaAsse__Durat__5364D18F]
GO
ALTER TABLE [dbo].[CRMArchivoMultimedia]  WITH CHECK ADD  CONSTRAINT [CRMArchivoMultimedia_CK__MediaAsse__Provi__554D1A01] CHECK  ((isjson([ProviderReference])=(1)))
GO
ALTER TABLE [dbo].[CRMArchivoMultimedia] CHECK CONSTRAINT [CRMArchivoMultimedia_CK__MediaAsse__Provi__554D1A01]
GO
ALTER TABLE [dbo].[CRMArchivoMultimedia]  WITH CHECK ADD  CONSTRAINT [CRMArchivoMultimedia_CK__MediaAsse__Sourc__4F9440AB] CHECK  (([SourceKind]='provider' OR [SourceKind]='upload'))
GO
ALTER TABLE [dbo].[CRMArchivoMultimedia] CHECK CONSTRAINT [CRMArchivoMultimedia_CK__MediaAsse__Sourc__4F9440AB]
GO
ALTER TABLE [dbo].[CRMArchivoMultimedia]  WITH CHECK ADD  CONSTRAINT [CRMArchivoMultimedia_CK__MediaAsse__State__508864E4] CHECK  (([State]='deleted' OR [State]='failed' OR [State]='rejected' OR [State]='ready' OR [State]='processing' OR [State]='pending' OR [State]='uploading'))
GO
ALTER TABLE [dbo].[CRMArchivoMultimedia] CHECK CONSTRAINT [CRMArchivoMultimedia_CK__MediaAsse__State__508864E4]
GO
ALTER TABLE [dbo].[CRMArchivoMultimedia]  WITH CHECK ADD  CONSTRAINT [CRMArchivoMultimedia_CK__MediaAsset__591DAAE5] CHECK  (([State]<>'ready' OR [ActualMime] IS NOT NULL AND [StorageKey] IS NOT NULL AND [ByteLength] IS NOT NULL AND [ContentHash] IS NOT NULL AND [Kind] IS NOT NULL))
GO
ALTER TABLE [dbo].[CRMArchivoMultimedia] CHECK CONSTRAINT [CRMArchivoMultimedia_CK__MediaAsset__591DAAE5]
GO
ALTER TABLE [dbo].[CRMArchivoMultimedia]  WITH CHECK ADD  CONSTRAINT [CRMArchivoMultimedia_CK__MediaAsset__5A11CF1E] CHECK  (([SourceKind]='upload' AND [IdentityId] IS NULL AND [Channel] IS NULL OR [SourceKind]='provider' AND [IdentityId] IS NOT NULL AND [Channel] IS NOT NULL))
GO
ALTER TABLE [dbo].[CRMArchivoMultimedia] CHECK CONSTRAINT [CRMArchivoMultimedia_CK__MediaAsset__5A11CF1E]
GO
ALTER TABLE [dbo].[CRMArchivoMultimedia]  WITH CHECK ADD  CONSTRAINT [CRMArchivoMultimedia_CK__MediaAsset__Kind__517C891D] CHECK  (([Kind]='document' OR [Kind]='audio' OR [Kind]='image'))
GO
ALTER TABLE [dbo].[CRMArchivoMultimedia] CHECK CONSTRAINT [CRMArchivoMultimedia_CK__MediaAsset__Kind__517C891D]
GO
-- crm_channels.MessageRoute -> dbo.CRMMensajeRuta
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMMensajeRuta](

	[MessageId] [uniqueidentifier] NOT NULL,

	[IdentityId] [uniqueidentifier] NOT NULL,

	[QueueId] [uniqueidentifier] NULL,

	[ActorKind] [varchar](8) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[ControlEpoch] [bigint] NULL,

	[StartedAt] [datetime2](7) NULL,

	[CompletedAt] [datetime2](7) NULL,

 CONSTRAINT [CRMMensajeRuta_PK__MessageR__C87C0C9CEDDF466A] PRIMARY KEY CLUSTERED 

(

	[MessageId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
CREATE NONCLUSTERED INDEX [CRMMensajeRuta_IX_Inbox_MessageRoute_Identity] ON [dbo].[CRMMensajeRuta]

(

	[IdentityId] ASC,

	[MessageId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
CREATE UNIQUE NONCLUSTERED INDEX [CRMMensajeRuta_IX_Inbox_MessageRoute_Queue] ON [dbo].[CRMMensajeRuta]

(

	[QueueId] ASC

)

WHERE ([QueueId] IS NOT NULL)

WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, IGNORE_DUP_KEY = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
ALTER TABLE [dbo].[CRMMensajeRuta]  WITH CHECK ADD  CONSTRAINT [CRMMensajeRuta_CK__MessageRo__Actor__46FEFAAA] CHECK  (([ActorKind]='bot' OR [ActorKind]='external' OR [ActorKind]='human'))
GO
ALTER TABLE [dbo].[CRMMensajeRuta] CHECK CONSTRAINT [CRMMensajeRuta_CK__MessageRo__Actor__46FEFAAA]
GO
ALTER TABLE [dbo].[CRMMensajeRuta]  WITH CHECK ADD  CONSTRAINT [CRMMensajeRuta_CK__MessageRo__Contr__47F31EE3] CHECK  (([ControlEpoch]>=(0)))
GO
ALTER TABLE [dbo].[CRMMensajeRuta] CHECK CONSTRAINT [CRMMensajeRuta_CK__MessageRo__Contr__47F31EE3]
GO
ALTER TABLE [dbo].[CRMMensajeRuta]  WITH CHECK ADD  CONSTRAINT [CRMMensajeRuta_CK__MessageRoute__48E7431C] CHECK  (([ActorKind]='bot' AND [ControlEpoch] IS NOT NULL OR ([ActorKind]='external' OR [ActorKind]='human') AND [ControlEpoch] IS NULL))
GO
ALTER TABLE [dbo].[CRMMensajeRuta] CHECK CONSTRAINT [CRMMensajeRuta_CK__MessageRoute__48E7431C]
GO
-- crm_channels.outbound_queue -> dbo.CRMColaSalida
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMColaSalida](

	[QueueId] [uniqueidentifier] NOT NULL,

	[Channel] [varchar](12) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[IdentityId] [uniqueidentifier] NULL,

	[MessageId] [uniqueidentifier] NULL,

	[Payload] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[State] [varchar](16) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Attempts] [int] NOT NULL,

	[DueAt] [datetime2](7) NOT NULL,

	[LeaseId] [uniqueidentifier] NULL,

	[ExternalId] [nvarchar](200) COLLATE Latin1_General_100_BIN2 NULL,

	[LastError] [varchar](80) COLLATE Modern_Spanish_CI_AS NULL,

	[CreatedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMColaSalida_PK__outbound__8324E715E2E8FE07] PRIMARY KEY CLUSTERED 

(

	[QueueId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
SET ANSI_PADDING ON
GO
CREATE NONCLUSTERED INDEX [CRMColaSalida_IX_Channels_Outbound_Work] ON [dbo].[CRMColaSalida]

(

	[State] ASC,

	[DueAt] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
CREATE UNIQUE NONCLUSTERED INDEX [CRMColaSalida_IX_Channels_Queue_Message] ON [dbo].[CRMColaSalida]

(

	[MessageId] ASC

)

WHERE ([MessageId] IS NOT NULL)

WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, IGNORE_DUP_KEY = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
ALTER TABLE [dbo].[CRMColaSalida] ADD  CONSTRAINT [CRMColaSalida_DF__outbound___State__14737ADD]  DEFAULT ('queued') FOR [State]
GO
ALTER TABLE [dbo].[CRMColaSalida] ADD  CONSTRAINT [CRMColaSalida_DF__outbound___Attem__15679F16]  DEFAULT ((0)) FOR [Attempts]
GO
ALTER TABLE [dbo].[CRMColaSalida] ADD  CONSTRAINT [CRMColaSalida_DF__outbound___DueAt__165BC34F]  DEFAULT (sysutcdatetime()) FOR [DueAt]
GO
ALTER TABLE [dbo].[CRMColaSalida] ADD  CONSTRAINT [CRMColaSalida_DF__outbound___Creat__174FE788]  DEFAULT (sysutcdatetime()) FOR [CreatedAt]
GO
ALTER TABLE [dbo].[CRMColaSalida]  WITH CHECK ADD  CONSTRAINT [CRMColaSalida_CK__outbound___Paylo__137F56A4] CHECK  ((isjson([Payload])=(1)))
GO
ALTER TABLE [dbo].[CRMColaSalida] CHECK CONSTRAINT [CRMColaSalida_CK__outbound___Paylo__137F56A4]
GO
ALTER TABLE [dbo].[CRMColaSalida]  WITH CHECK ADD  CONSTRAINT [CRMColaSalida_CK__outbound___State__18440BC1] CHECK  (([State]='uncertain' OR [State]='failed' OR [State]='read' OR [State]='delivered' OR [State]='sent' OR [State]='sending' OR [State]='queued'))
GO
ALTER TABLE [dbo].[CRMColaSalida] CHECK CONSTRAINT [CRMColaSalida_CK__outbound___State__18440BC1]
GO
-- crm_channels.social_comments -> dbo.CRMComentarioSocial
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMComentarioSocial](

	[CommentId] [uniqueidentifier] NOT NULL,

	[Channel] [varchar](12) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[ExternalId] [nvarchar](200) COLLATE Latin1_General_100_BIN2 NOT NULL,

	[AuthorId] [nvarchar](128) COLLATE Latin1_General_100_BIN2 NOT NULL,

	[Body] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Payload] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[ReceivedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMComentarioSocial_PK__social_c__C3B4DFCA67819603] PRIMARY KEY CLUSTERED 

(

	[CommentId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF),

 CONSTRAINT [CRMComentarioSocial_UQ_Channels_Comment] UNIQUE NONCLUSTERED 

(

	[Channel] ASC,

	[ExternalId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
ALTER TABLE [dbo].[CRMComentarioSocial] ADD  CONSTRAINT [CRMComentarioSocial_DF__social_co__Recei__1DFCE517]  DEFAULT (sysutcdatetime()) FOR [ReceivedAt]
GO
ALTER TABLE [dbo].[CRMComentarioSocial]  WITH CHECK ADD  CONSTRAINT [CRMComentarioSocial_CK__social_co__Paylo__1D08C0DE] CHECK  ((isjson([Payload])=(1)))
GO
ALTER TABLE [dbo].[CRMComentarioSocial] CHECK CONSTRAINT [CRMComentarioSocial_CK__social_co__Paylo__1D08C0DE]
GO
-- crm_channels.webhook_events -> dbo.CRMEventoWebhook
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMEventoWebhook](

	[EventId] [uniqueidentifier] NOT NULL,

	[Provider] [varchar](12) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Digest] [binary](32) NOT NULL,

	[Payload] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[State] [varchar](16) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Attempts] [int] NOT NULL,

	[DueAt] [datetime2](7) NOT NULL,

	[LeaseId] [uniqueidentifier] NULL,

	[LastError] [varchar](80) COLLATE Modern_Spanish_CI_AS NULL,

	[ReceivedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMEventoWebhook_PK__webhook___7944C810D973FF18] PRIMARY KEY CLUSTERED 

(

	[EventId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF),

 CONSTRAINT [CRMEventoWebhook_UQ__webhook___BE17DFE180291ABA] UNIQUE NONCLUSTERED 

(

	[Provider] ASC,

	[Digest] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
SET ANSI_PADDING ON
GO
CREATE NONCLUSTERED INDEX [CRMEventoWebhook_IX_Channels_Receipt_Work] ON [dbo].[CRMEventoWebhook]

(

	[State] ASC,

	[DueAt] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
ALTER TABLE [dbo].[CRMEventoWebhook] ADD  CONSTRAINT [CRMEventoWebhook_DF__webhook_e__State__006C8230]  DEFAULT ('queued') FOR [State]
GO
ALTER TABLE [dbo].[CRMEventoWebhook] ADD  CONSTRAINT [CRMEventoWebhook_DF__webhook_e__Attem__0160A669]  DEFAULT ((0)) FOR [Attempts]
GO
ALTER TABLE [dbo].[CRMEventoWebhook] ADD  CONSTRAINT [CRMEventoWebhook_DF__webhook_e__DueAt__0254CAA2]  DEFAULT (sysutcdatetime()) FOR [DueAt]
GO
ALTER TABLE [dbo].[CRMEventoWebhook] ADD  CONSTRAINT [CRMEventoWebhook_DF__webhook_e__Recei__0348EEDB]  DEFAULT (sysutcdatetime()) FOR [ReceivedAt]
GO
ALTER TABLE [dbo].[CRMEventoWebhook]  WITH CHECK ADD  CONSTRAINT [CRMEventoWebhook_CK__webhook_e__Paylo__7F785DF7] CHECK  ((isjson([Payload])=(1)))
GO
ALTER TABLE [dbo].[CRMEventoWebhook] CHECK CONSTRAINT [CRMEventoWebhook_CK__webhook_e__Paylo__7F785DF7]
GO
-- crm_config.Configuration -> dbo.CRMConfiguracion
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[CRMConfiguracion](

	[ConfigurationId] [int] NOT NULL,

	[Document] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Revision] [bigint] NOT NULL,

	[CreatedAt] [datetime2](7) NOT NULL,

	[UpdatedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMConfiguracion_PK_CrmConfiguration] PRIMARY KEY CLUSTERED 

(

	[ConfigurationId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
ALTER TABLE [dbo].[CRMConfiguracion] ADD  CONSTRAINT [CRMConfiguracion_DF_CrmConfiguration_Created]  DEFAULT (sysutcdatetime()) FOR [CreatedAt]
GO
ALTER TABLE [dbo].[CRMConfiguracion] ADD  CONSTRAINT [CRMConfiguracion_DF_CrmConfiguration_Updated]  DEFAULT (sysutcdatetime()) FOR [UpdatedAt]
GO
ALTER TABLE [dbo].[CRMConfiguracion]  WITH CHECK ADD  CONSTRAINT [CRMConfiguracion_CK_CrmConfiguration] CHECK  (([ConfigurationId]=(1) AND [Revision]>(0) AND isjson([Document])=(1)))
GO
ALTER TABLE [dbo].[CRMConfiguracion] CHECK CONSTRAINT [CRMConfiguracion_CK_CrmConfiguration]
GO
-- crm_config.Operation -> dbo.CRMConfiguracionOperacion
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMConfiguracionOperacion](

	[OperationId] [uniqueidentifier] NOT NULL,

	[PayloadHash] [binary](32) NOT NULL,

	[Revision] [bigint] NOT NULL,

	[CreatedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMConfiguracionOperacion_PK_CrmConfigOperation] PRIMARY KEY CLUSTERED 

(

	[OperationId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF),

 CONSTRAINT [CRMConfiguracionOperacion_UQ_CrmConfigRevision] UNIQUE NONCLUSTERED 

(

	[Revision] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
ALTER TABLE [dbo].[CRMConfiguracionOperacion] ADD  CONSTRAINT [CRMConfiguracionOperacion_DF_CrmConfigOperation_Created]  DEFAULT (sysutcdatetime()) FOR [CreatedAt]
GO
ALTER TABLE [dbo].[CRMConfiguracionOperacion]  WITH CHECK ADD  CONSTRAINT [CRMConfiguracionOperacion_CK_CrmConfigOperation] CHECK  (([Revision]>(1)))
GO
ALTER TABLE [dbo].[CRMConfiguracionOperacion] CHECK CONSTRAINT [CRMConfiguracionOperacion_CK_CrmConfigOperation]
GO
-- crm_events.Event -> dbo.CRMConversacionEvento
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMConversacionEvento](

	[EventId] [bigint] IDENTITY(1,1) NOT NULL,

	[SourceKind] [varchar](20) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[SourceId] [uniqueidentifier] NOT NULL,

	[SourceRevision] [bigint] NULL,

	[SourceAction] [varchar](24) COLLATE Modern_Spanish_CI_AS NULL,

	[ConversationId] [uniqueidentifier] NOT NULL,

	[SourceOccurredAt] [datetime2](7) NOT NULL,

	[CapturedAt] [datetime2](7) NOT NULL,

	[State] [varchar](12) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Attempts] [int] NOT NULL,

	[TotalAttempts] [int] NOT NULL,

	[NextAttemptAt] [datetime2](7) NOT NULL,

	[LeaseToken] [uniqueidentifier] NULL,

	[LeaseUntil] [datetime2](7) NULL,

	[PreparedAt] [datetime2](7) NULL,

	[ErrorCode] [varchar](40) COLLATE Modern_Spanish_CI_AS NULL,

 CONSTRAINT [CRMConversacionEvento_PK_Event] PRIMARY KEY CLUSTERED 

(

	[EventId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF),

 CONSTRAINT [CRMConversacionEvento_UQ_Event_Source] UNIQUE NONCLUSTERED 

(

	[SourceKind] ASC,

	[SourceId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
CREATE NONCLUSTERED INDEX [CRMConversacionEvento_IX_Event_Conversation] ON [dbo].[CRMConversacionEvento]

(

	[ConversationId] ASC,

	[EventId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
SET ANSI_PADDING ON
GO
CREATE NONCLUSTERED INDEX [CRMConversacionEvento_IX_Event_Work] ON [dbo].[CRMConversacionEvento]

(

	[State] ASC,

	[NextAttemptAt] ASC,

	[EventId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
ALTER TABLE [dbo].[CRMConversacionEvento] ADD  CONSTRAINT [CRMConversacionEvento_DF_Event_Captured]  DEFAULT (sysutcdatetime()) FOR [CapturedAt]
GO
ALTER TABLE [dbo].[CRMConversacionEvento] ADD  CONSTRAINT [CRMConversacionEvento_DF_Event_State]  DEFAULT ('pending') FOR [State]
GO
ALTER TABLE [dbo].[CRMConversacionEvento] ADD  CONSTRAINT [CRMConversacionEvento_DF_Event_Attempts]  DEFAULT ((0)) FOR [Attempts]
GO
ALTER TABLE [dbo].[CRMConversacionEvento] ADD  CONSTRAINT [CRMConversacionEvento_DF_Event_Total]  DEFAULT ((0)) FOR [TotalAttempts]
GO
ALTER TABLE [dbo].[CRMConversacionEvento] ADD  CONSTRAINT [CRMConversacionEvento_DF_Event_Next]  DEFAULT (sysutcdatetime()) FOR [NextAttemptAt]
GO
ALTER TABLE [dbo].[CRMConversacionEvento]  WITH CHECK ADD  CONSTRAINT [CRMConversacionEvento_CK_Event_Attempts] CHECK  (([Attempts]>=(0) AND [Attempts]<=(5) AND [TotalAttempts]>=[Attempts]))
GO
ALTER TABLE [dbo].[CRMConversacionEvento] CHECK CONSTRAINT [CRMConversacionEvento_CK_Event_Attempts]
GO
ALTER TABLE [dbo].[CRMConversacionEvento]  WITH CHECK ADD  CONSTRAINT [CRMConversacionEvento_CK_Event_Lease] CHECK  (([State]='leased' AND [LeaseToken] IS NOT NULL AND [LeaseUntil] IS NOT NULL OR [State]<>'leased' AND [LeaseToken] IS NULL AND [LeaseUntil] IS NULL))
GO
ALTER TABLE [dbo].[CRMConversacionEvento] CHECK CONSTRAINT [CRMConversacionEvento_CK_Event_Lease]
GO
ALTER TABLE [dbo].[CRMConversacionEvento]  WITH CHECK ADD  CONSTRAINT [CRMConversacionEvento_CK_Event_Source] CHECK  (([SourceKind]='inbox_operation' OR [SourceKind]='crm_operation' OR [SourceKind]='message' OR [SourceKind]='baseline'))
GO
ALTER TABLE [dbo].[CRMConversacionEvento] CHECK CONSTRAINT [CRMConversacionEvento_CK_Event_Source]
GO
ALTER TABLE [dbo].[CRMConversacionEvento]  WITH CHECK ADD  CONSTRAINT [CRMConversacionEvento_CK_Event_State] CHECK  (([State]='failed' OR [State]='prepared' OR [State]='leased' OR [State]='pending'))
GO
ALTER TABLE [dbo].[CRMConversacionEvento] CHECK CONSTRAINT [CRMConversacionEvento_CK_Event_State]
GO
-- crm_events.Preparation -> dbo.CRMEventoPreparacion
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[CRMEventoPreparacion](

	[ConversationId] [uniqueidentifier] NOT NULL,

	[LastEventId] [bigint] NOT NULL,

	[MessageCount] [bigint] NOT NULL,

	[LatestMessageSequence] [bigint] NULL,

	[SourceCrmRevision] [bigint] NOT NULL,

	[SourceInboxRevision] [bigint] NOT NULL,

	[PreparedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMEventoPreparacion_PK_Preparation] PRIMARY KEY CLUSTERED 

(

	[ConversationId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
-- crm_events.RetryOperation -> dbo.CRMEventoReintentoOperacion
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[CRMEventoReintentoOperacion](

	[OperationId] [uniqueidentifier] NOT NULL,

	[RetriedCount] [int] NOT NULL,

	[CreatedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMEventoReintentoOperacion_PK_EventRetry] PRIMARY KEY CLUSTERED 

(

	[OperationId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
ALTER TABLE [dbo].[CRMEventoReintentoOperacion] ADD  CONSTRAINT [CRMEventoReintentoOperacion_DF_EventRetry_Created]  DEFAULT (sysutcdatetime()) FOR [CreatedAt]
GO
ALTER TABLE [dbo].[CRMEventoReintentoOperacion]  WITH CHECK ADD  CONSTRAINT [CRMEventoReintentoOperacion_CK_EventRetry_Count] CHECK  (([RetriedCount]>=(0) AND [RetriedCount]<=(25)))
GO
ALTER TABLE [dbo].[CRMEventoReintentoOperacion] CHECK CONSTRAINT [CRMEventoReintentoOperacion_CK_EventRetry_Count]
GO
-- crm_identity.Profile -> dbo.CRMContactoPerfilInstitucional
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[CRMContactoPerfilInstitucional](

	[ContactId] [uniqueidentifier] NOT NULL,

	[GivenNames] [nvarchar](100) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[FirstSurname] [nvarchar](30) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[SecondSurname] [nvarchar](30) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[DocumentTypeId] [tinyint] NULL,

	[Document] [nvarchar](16) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Email] [nvarchar](160) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[AspirationPeriodId] [int] NULL,

	[CreatedAt] [datetime2](7) NOT NULL,

	[UpdatedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMContactoPerfilInstitucional_PK_IdentityProfile] PRIMARY KEY CLUSTERED 

(

	[ContactId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
ALTER TABLE [dbo].[CRMContactoPerfilInstitucional] ADD  CONSTRAINT [CRMContactoPerfilInstitucional_DF_IdentityProfile_Created]  DEFAULT (sysutcdatetime()) FOR [CreatedAt]
GO
ALTER TABLE [dbo].[CRMContactoPerfilInstitucional] ADD  CONSTRAINT [CRMContactoPerfilInstitucional_DF_IdentityProfile_Updated]  DEFAULT (sysutcdatetime()) FOR [UpdatedAt]
GO
ALTER TABLE [dbo].[CRMContactoPerfilInstitucional]  WITH CHECK ADD  CONSTRAINT [CRMContactoPerfilInstitucional_CK_IdentityProfile_Document] CHECK  (([DocumentTypeId] IS NULL AND [Document]=N'' OR [DocumentTypeId] IS NOT NULL AND len(ltrim(rtrim([Document])))>(0)))
GO
ALTER TABLE [dbo].[CRMContactoPerfilInstitucional] CHECK CONSTRAINT [CRMContactoPerfilInstitucional_CK_IdentityProfile_Document]
GO
-- crm_inbox.Agent -> dbo.CRMBandejaAgente
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[CRMBandejaAgente](

	[AgentId] [uniqueidentifier] NOT NULL,

	[Name] [nvarchar](100) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Description] [nvarchar](1000) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Enabled] [bit] NOT NULL,

	[CreatedAt] [datetime2](7) NOT NULL,

	[UpdatedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMBandejaAgente_PK_InboxAgent] PRIMARY KEY CLUSTERED 

(

	[AgentId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
ALTER TABLE [dbo].[CRMBandejaAgente] ADD  CONSTRAINT [CRMBandejaAgente_DF_InboxAgent_Created]  DEFAULT (sysutcdatetime()) FOR [CreatedAt]
GO
ALTER TABLE [dbo].[CRMBandejaAgente] ADD  CONSTRAINT [CRMBandejaAgente_DF_InboxAgent_Updated]  DEFAULT (sysutcdatetime()) FOR [UpdatedAt]
GO
ALTER TABLE [dbo].[CRMBandejaAgente]  WITH CHECK ADD  CONSTRAINT [CRMBandejaAgente_CK_InboxAgent_Name] CHECK  ((len(ltrim(rtrim([Name])))>(0)))
GO
ALTER TABLE [dbo].[CRMBandejaAgente] CHECK CONSTRAINT [CRMBandejaAgente_CK_InboxAgent_Name]
GO
-- crm_inbox.Assignment -> dbo.CRMBandejaAsignacion
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[CRMBandejaAsignacion](

	[ConversationId] [uniqueidentifier] NOT NULL,

	[HumanEmployeeId] [int] NULL,

	[AiAgentId] [uniqueidentifier] NULL,

	[UpdatedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMBandejaAsignacion_PK_InboxAssignment] PRIMARY KEY CLUSTERED 

(

	[ConversationId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
ALTER TABLE [dbo].[CRMBandejaAsignacion] ADD  CONSTRAINT [CRMBandejaAsignacion_DF_InboxAssignment_Updated]  DEFAULT (sysutcdatetime()) FOR [UpdatedAt]
GO
-- crm_inbox.Member -> dbo.CRMBandejaMiembro
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[CRMBandejaMiembro](

	[EmployeeId] [int] NOT NULL,

	[Enabled] [bit] NOT NULL,

	[CreatedAt] [datetime2](7) NOT NULL,

	[UpdatedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMBandejaMiembro_PK_InboxMember] PRIMARY KEY CLUSTERED 

(

	[EmployeeId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
ALTER TABLE [dbo].[CRMBandejaMiembro] ADD  CONSTRAINT [CRMBandejaMiembro_DF_InboxMember_Created]  DEFAULT (sysutcdatetime()) FOR [CreatedAt]
GO
ALTER TABLE [dbo].[CRMBandejaMiembro] ADD  CONSTRAINT [CRMBandejaMiembro_DF_InboxMember_Updated]  DEFAULT (sysutcdatetime()) FOR [UpdatedAt]
GO
-- crm_inbox.Operation -> dbo.CRMBandejaOperacion
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMBandejaOperacion](

	[OperationId] [uniqueidentifier] NOT NULL,

	[Revision] [bigint] IDENTITY(1,1) NOT NULL,

	[Action] [varchar](20) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[EntityKey] [nvarchar](100) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[PayloadHash] [binary](32) NOT NULL,

	[Actor] [varchar](32) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[CreatedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMBandejaOperacion_PK_InboxOperation] PRIMARY KEY NONCLUSTERED 

(

	[OperationId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF),

 CONSTRAINT [CRMBandejaOperacion_UQ_InboxOperation_Revision] UNIQUE CLUSTERED 

(

	[Revision] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
ALTER TABLE [dbo].[CRMBandejaOperacion] ADD  CONSTRAINT [CRMBandejaOperacion_DF_InboxOperation_Created]  DEFAULT (sysutcdatetime()) FOR [CreatedAt]
GO
ALTER TABLE [dbo].[CRMBandejaOperacion]  WITH CHECK ADD  CONSTRAINT [CRMBandejaOperacion_CK_InboxOperation_Action] CHECK  (([Action]='policy' OR [Action]='task_edit' OR [Action]='task_create' OR [Action]='assignment' OR [Action]='agent' OR [Action]='member'))
GO
ALTER TABLE [dbo].[CRMBandejaOperacion] CHECK CONSTRAINT [CRMBandejaOperacion_CK_InboxOperation_Action]
GO
ALTER TABLE [dbo].[CRMBandejaOperacion]  WITH CHECK ADD  CONSTRAINT [CRMBandejaOperacion_CK_InboxOperation_Actor] CHECK  (([Actor]='local-operator'))
GO
ALTER TABLE [dbo].[CRMBandejaOperacion] CHECK CONSTRAINT [CRMBandejaOperacion_CK_InboxOperation_Actor]
GO
-- crm_inbox.SlaPolicy -> dbo.CRMBandejaPoliticaSLA
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[CRMBandejaPoliticaSLA](

	[PolicyId] [tinyint] NOT NULL,

	[Enabled] [bit] NOT NULL,

	[ThresholdMinutes] [int] NOT NULL,

	[UpdatedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMBandejaPoliticaSLA_PK_InboxSlaPolicy] PRIMARY KEY CLUSTERED 

(

	[PolicyId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
ALTER TABLE [dbo].[CRMBandejaPoliticaSLA] ADD  CONSTRAINT [CRMBandejaPoliticaSLA_DF_InboxSlaPolicy_Updated]  DEFAULT (sysutcdatetime()) FOR [UpdatedAt]
GO
ALTER TABLE [dbo].[CRMBandejaPoliticaSLA]  WITH CHECK ADD  CONSTRAINT [CRMBandejaPoliticaSLA_CK_InboxSlaPolicy_Single] CHECK  (([PolicyId]=(1)))
GO
ALTER TABLE [dbo].[CRMBandejaPoliticaSLA] CHECK CONSTRAINT [CRMBandejaPoliticaSLA_CK_InboxSlaPolicy_Single]
GO
ALTER TABLE [dbo].[CRMBandejaPoliticaSLA]  WITH CHECK ADD  CONSTRAINT [CRMBandejaPoliticaSLA_CK_InboxSlaPolicy_Threshold] CHECK  (([ThresholdMinutes]>=(1) AND [ThresholdMinutes]<=(525600)))
GO
ALTER TABLE [dbo].[CRMBandejaPoliticaSLA] CHECK CONSTRAINT [CRMBandejaPoliticaSLA_CK_InboxSlaPolicy_Threshold]
GO
-- crm_inbox.Task -> dbo.CRMBandejaTarea
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMBandejaTarea](

	[TaskId] [uniqueidentifier] NOT NULL,

	[ConversationId] [uniqueidentifier] NOT NULL,

	[Title] [nvarchar](120) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[HumanEmployeeId] [int] NULL,

	[DueAt] [datetime2](7) NULL,

	[Priority] [varchar](8) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Status] [varchar](12) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[CreatedAt] [datetime2](7) NOT NULL,

	[UpdatedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMBandejaTarea_PK_InboxTask] PRIMARY KEY CLUSTERED 

(

	[TaskId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
CREATE NONCLUSTERED INDEX [CRMBandejaTarea_IX_InboxTask_Conversation] ON [dbo].[CRMBandejaTarea]

(

	[ConversationId] ASC,

	[CreatedAt] ASC,

	[TaskId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
ALTER TABLE [dbo].[CRMBandejaTarea] ADD  CONSTRAINT [CRMBandejaTarea_DF_InboxTask_Created]  DEFAULT (sysutcdatetime()) FOR [CreatedAt]
GO
ALTER TABLE [dbo].[CRMBandejaTarea] ADD  CONSTRAINT [CRMBandejaTarea_DF_InboxTask_Updated]  DEFAULT (sysutcdatetime()) FOR [UpdatedAt]
GO
ALTER TABLE [dbo].[CRMBandejaTarea]  WITH CHECK ADD  CONSTRAINT [CRMBandejaTarea_CK_InboxTask_Priority] CHECK  (([Priority]='urgent' OR [Priority]='high' OR [Priority]='normal' OR [Priority]='low'))
GO
ALTER TABLE [dbo].[CRMBandejaTarea] CHECK CONSTRAINT [CRMBandejaTarea_CK_InboxTask_Priority]
GO
ALTER TABLE [dbo].[CRMBandejaTarea]  WITH CHECK ADD  CONSTRAINT [CRMBandejaTarea_CK_InboxTask_Status] CHECK  (([Status]='cancelled' OR [Status]='completed' OR [Status]='pending'))
GO
ALTER TABLE [dbo].[CRMBandejaTarea] CHECK CONSTRAINT [CRMBandejaTarea_CK_InboxTask_Status]
GO
ALTER TABLE [dbo].[CRMBandejaTarea]  WITH CHECK ADD  CONSTRAINT [CRMBandejaTarea_CK_InboxTask_Title] CHECK  ((len(ltrim(rtrim([Title])))>(0)))
GO
ALTER TABLE [dbo].[CRMBandejaTarea] CHECK CONSTRAINT [CRMBandejaTarea_CK_InboxTask_Title]
GO
-- crm_marketing.AccountCadence -> dbo.CRMCuentaCadencia
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMCuentaCadencia](

	[Channel] [varchar](12) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[AccountScope] [nvarchar](128) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[MinIntervalSeconds] [int] NOT NULL,

	[DailyRecipientLimit] [int] NOT NULL,

	[WindowStartedAtUtc] [datetime2](7) NOT NULL,

	[ReservedInWindow] [int] NOT NULL,

	[NextAllowedAtUtc] [datetime2](7) NOT NULL,

	[Revision] [bigint] NOT NULL,

	[LeaseId] [uniqueidentifier] NULL,

	[LeaseUntilUtc] [datetime2](7) NULL,

 CONSTRAINT [CRMCuentaCadencia_PK__AccountC__03683E41815DF26A] PRIMARY KEY CLUSTERED 

(

	[Channel] ASC,

	[AccountScope] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
ALTER TABLE [dbo].[CRMCuentaCadencia] ADD  CONSTRAINT [CRMCuentaCadencia_DF__AccountCa__Reser__47BE14B9]  DEFAULT ((0)) FOR [ReservedInWindow]
GO
ALTER TABLE [dbo].[CRMCuentaCadencia] ADD  CONSTRAINT [CRMCuentaCadencia_DF__AccountCa__Revis__49A65D2B]  DEFAULT ((0)) FOR [Revision]
GO
ALTER TABLE [dbo].[CRMCuentaCadencia]  WITH CHECK ADD  CONSTRAINT [CRMCuentaCadencia_CK__AccountCa__Daily__46C9F080] CHECK  (([DailyRecipientLimit]>=(1) AND [DailyRecipientLimit]<=(100000)))
GO
ALTER TABLE [dbo].[CRMCuentaCadencia] CHECK CONSTRAINT [CRMCuentaCadencia_CK__AccountCa__Daily__46C9F080]
GO
ALTER TABLE [dbo].[CRMCuentaCadencia]  WITH CHECK ADD  CONSTRAINT [CRMCuentaCadencia_CK__AccountCa__MinIn__45D5CC47] CHECK  (([MinIntervalSeconds]>=(1) AND [MinIntervalSeconds]<=(86400)))
GO
ALTER TABLE [dbo].[CRMCuentaCadencia] CHECK CONSTRAINT [CRMCuentaCadencia_CK__AccountCa__MinIn__45D5CC47]
GO
ALTER TABLE [dbo].[CRMCuentaCadencia]  WITH CHECK ADD  CONSTRAINT [CRMCuentaCadencia_CK__AccountCa__Reser__48B238F2] CHECK  (([ReservedInWindow]>=(0)))
GO
ALTER TABLE [dbo].[CRMCuentaCadencia] CHECK CONSTRAINT [CRMCuentaCadencia_CK__AccountCa__Reser__48B238F2]
GO
ALTER TABLE [dbo].[CRMCuentaCadencia]  WITH CHECK ADD  CONSTRAINT [CRMCuentaCadencia_CK__AccountCa__Revis__4A9A8164] CHECK  (([Revision]>=(0)))
GO
ALTER TABLE [dbo].[CRMCuentaCadencia] CHECK CONSTRAINT [CRMCuentaCadencia_CK__AccountCa__Revis__4A9A8164]
GO
ALTER TABLE [dbo].[CRMCuentaCadencia]  WITH CHECK ADD  CONSTRAINT [CRMCuentaCadencia_CK__AccountCadence__4B8EA59D] CHECK  (([LeaseId] IS NULL AND [LeaseUntilUtc] IS NULL OR [LeaseId] IS NOT NULL AND [LeaseUntilUtc] IS NOT NULL))
GO
ALTER TABLE [dbo].[CRMCuentaCadencia] CHECK CONSTRAINT [CRMCuentaCadencia_CK__AccountCadence__4B8EA59D]
GO
-- crm_marketing.Campaign -> dbo.CRMCampana
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMCampana](

	[CampaignId] [uniqueidentifier] NOT NULL,

	[Name] [nvarchar](160) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Kind] [varchar](12) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Status] [varchar](12) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Channel] [varchar](12) COLLATE Modern_Spanish_CI_AS NULL,

	[AccountScope] [nvarchar](128) COLLATE Modern_Spanish_CI_AS NULL,

	[TemplateId] [uniqueidentifier] NULL,

	[TemplateVersion] [bigint] NULL,

	[RuleId] [uniqueidentifier] NULL,

	[SegmentJson] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[ScheduledAtUtc] [datetime2](7) NULL,

	[PausedAtUtc] [datetime2](7) NULL,

	[LastPreparedAtUtc] [datetime2](7) NULL,

	[Revision] [bigint] NOT NULL,

	[InclusionEpoch] [bigint] NOT NULL,

	[CreatedAtUtc] [datetime2](7) NOT NULL,

	[UpdatedAtUtc] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMCampana_PK__Campaign__3F5E8A998EDCEC9A] PRIMARY KEY CLUSTERED 

(

	[CampaignId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF),

 CONSTRAINT [CRMCampana_UQ__Campaign__3F68097C1E811B98] UNIQUE NONCLUSTERED 

(

	[CampaignId] ASC,

	[Channel] ASC,

	[AccountScope] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
SET ANSI_PADDING ON
GO
CREATE NONCLUSTERED INDEX [CRMCampana_IX_Marketing_Campaign_Due] ON [dbo].[CRMCampana]

(

	[Status] ASC,

	[ScheduledAtUtc] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
ALTER TABLE [dbo].[CRMCampana] ADD  CONSTRAINT [CRMCampana_DF__Campaign__Status__50535ABA]  DEFAULT ('draft') FOR [Status]
GO
ALTER TABLE [dbo].[CRMCampana] ADD  CONSTRAINT [CRMCampana_DF__Campaign__Revisi__5423EB9E]  DEFAULT ((0)) FOR [Revision]
GO
ALTER TABLE [dbo].[CRMCampana] ADD  CONSTRAINT [CRMCampana_DF__Campaign__Inclus__560C3410]  DEFAULT ((0)) FOR [InclusionEpoch]
GO
ALTER TABLE [dbo].[CRMCampana] ADD  CONSTRAINT [CRMCampana_DF__Campaign__Create__57F47C82]  DEFAULT (sysutcdatetime()) FOR [CreatedAtUtc]
GO
ALTER TABLE [dbo].[CRMCampana] ADD  CONSTRAINT [CRMCampana_DF__Campaign__Update__58E8A0BB]  DEFAULT (sysutcdatetime()) FOR [UpdatedAtUtc]
GO
ALTER TABLE [dbo].[CRMCampana]  WITH CHECK ADD  CONSTRAINT [CRMCampana_CK__Campaign__5BC50D66] CHECK  (([Kind]='bulk' AND [RuleId] IS NULL OR [Kind]='remarketing' AND [RuleId] IS NOT NULL))
GO
ALTER TABLE [dbo].[CRMCampana] CHECK CONSTRAINT [CRMCampana_CK__Campaign__5BC50D66]
GO
ALTER TABLE [dbo].[CRMCampana]  WITH CHECK ADD  CONSTRAINT [CRMCampana_CK__Campaign__5CB9319F] CHECK  (([TemplateId] IS NULL AND [TemplateVersion] IS NULL OR [TemplateId] IS NOT NULL AND [TemplateVersion] IS NOT NULL))
GO
ALTER TABLE [dbo].[CRMCampana] CHECK CONSTRAINT [CRMCampana_CK__Campaign__5CB9319F]
GO
ALTER TABLE [dbo].[CRMCampana]  WITH CHECK ADD  CONSTRAINT [CRMCampana_CK__Campaign__5DAD55D8] CHECK  ((NOT ([Status]='running' OR [Status]='scheduled') OR [ScheduledAtUtc] IS NOT NULL AND [TemplateId] IS NOT NULL AND [Channel] IS NOT NULL AND [AccountScope] IS NOT NULL))
GO
ALTER TABLE [dbo].[CRMCampana] CHECK CONSTRAINT [CRMCampana_CK__Campaign__5DAD55D8]
GO
ALTER TABLE [dbo].[CRMCampana]  WITH CHECK ADD  CONSTRAINT [CRMCampana_CK__Campaign__Inclus__57005849] CHECK  (([InclusionEpoch]>=(0)))
GO
ALTER TABLE [dbo].[CRMCampana] CHECK CONSTRAINT [CRMCampana_CK__Campaign__Inclus__57005849]
GO
ALTER TABLE [dbo].[CRMCampana]  WITH CHECK ADD  CONSTRAINT [CRMCampana_CK__Campaign__Kind__4F5F3681] CHECK  (([Kind]='remarketing' OR [Kind]='bulk'))
GO
ALTER TABLE [dbo].[CRMCampana] CHECK CONSTRAINT [CRMCampana_CK__Campaign__Kind__4F5F3681]
GO
ALTER TABLE [dbo].[CRMCampana]  WITH CHECK ADD  CONSTRAINT [CRMCampana_CK__Campaign__Revisi__55180FD7] CHECK  (([Revision]>=(0)))
GO
ALTER TABLE [dbo].[CRMCampana] CHECK CONSTRAINT [CRMCampana_CK__Campaign__Revisi__55180FD7]
GO
ALTER TABLE [dbo].[CRMCampana]  WITH CHECK ADD  CONSTRAINT [CRMCampana_CK__Campaign__Segmen__532FC765] CHECK  ((isjson([SegmentJson])=(1) AND left(ltrim([SegmentJson]),(1))=N'{'))
GO
ALTER TABLE [dbo].[CRMCampana] CHECK CONSTRAINT [CRMCampana_CK__Campaign__Segmen__532FC765]
GO
ALTER TABLE [dbo].[CRMCampana]  WITH CHECK ADD  CONSTRAINT [CRMCampana_CK__Campaign__Status__51477EF3] CHECK  (([Status]='cancelled' OR [Status]='completed' OR [Status]='paused' OR [Status]='running' OR [Status]='scheduled' OR [Status]='draft'))
GO
ALTER TABLE [dbo].[CRMCampana] CHECK CONSTRAINT [CRMCampana_CK__Campaign__Status__51477EF3]
GO
-- crm_marketing.CampaignRecipient -> dbo.CRMCampanaDestinatario
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMCampanaDestinatario](

	[RecipientId] [uniqueidentifier] NOT NULL,

	[CampaignId] [uniqueidentifier] NOT NULL,

	[Channel] [varchar](12) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[AccountScope] [nvarchar](128) COLLATE Modern_Spanish_CI_AS NULL,

	[IdentityId] [uniqueidentifier] NOT NULL,

	[ContactId] [uniqueidentifier] NOT NULL,

	[ConversationId] [uniqueidentifier] NOT NULL,

	[Status] [varchar](12) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[QueueId] [uniqueidentifier] NULL,

	[ConsentId] [uniqueidentifier] NULL,

	[ConsentVersion] [bigint] NULL,

	[CampaignRevision] [bigint] NOT NULL,

	[RuleRevision] [bigint] NULL,

	[AccountRevision] [int] NOT NULL,

	[ControlEpoch] [bigint] NOT NULL,

	[InclusionEpoch] [bigint] NOT NULL,

	[InputSequence] [bigint] NOT NULL,

	[EvidenceJson] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[DueAtUtc] [datetime2](7) NOT NULL,

	[Attempts] [int] NOT NULL,

	[LeaseId] [uniqueidentifier] NULL,

	[LeaseUntilUtc] [datetime2](7) NULL,

	[LastError] [varchar](80) COLLATE Modern_Spanish_CI_AS NULL,

	[CreatedAtUtc] [datetime2](7) NOT NULL,

	[UpdatedAtUtc] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMCampanaDestinatario_PK__Campaign__F0A6024DD40B6B06] PRIMARY KEY CLUSTERED 

(

	[RecipientId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF),

 CONSTRAINT [CRMCampanaDestinatario_UQ__Campaign__7C58ED3CEF738438] UNIQUE NONCLUSTERED 

(

	[CampaignId] ASC,

	[IdentityId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
SET ANSI_PADDING ON
GO
CREATE NONCLUSTERED INDEX [CRMCampanaDestinatario_IX_Marketing_Recipient_Due] ON [dbo].[CRMCampanaDestinatario]

(

	[Status] ASC,

	[DueAtUtc] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
CREATE NONCLUSTERED INDEX [CRMCampanaDestinatario_IX_Marketing_Recipient_Identity] ON [dbo].[CRMCampanaDestinatario]

(

	[IdentityId] ASC,

	[UpdatedAtUtc] DESC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
CREATE UNIQUE NONCLUSTERED INDEX [CRMCampanaDestinatario_IX_Marketing_Recipient_Queue] ON [dbo].[CRMCampanaDestinatario]

(

	[QueueId] ASC

)

WHERE ([QueueId] IS NOT NULL)

WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, IGNORE_DUP_KEY = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
ALTER TABLE [dbo].[CRMCampanaDestinatario] ADD  CONSTRAINT [CRMCampanaDestinatario_DF__CampaignR__Statu__645A5367]  DEFAULT ('pending') FOR [Status]
GO
ALTER TABLE [dbo].[CRMCampanaDestinatario] ADD  CONSTRAINT [CRMCampanaDestinatario_DF__CampaignR__Attem__6DE3BDA1]  DEFAULT ((0)) FOR [Attempts]
GO
ALTER TABLE [dbo].[CRMCampanaDestinatario] ADD  CONSTRAINT [CRMCampanaDestinatario_DF__CampaignR__Creat__6FCC0613]  DEFAULT (sysutcdatetime()) FOR [CreatedAtUtc]
GO
ALTER TABLE [dbo].[CRMCampanaDestinatario] ADD  CONSTRAINT [CRMCampanaDestinatario_DF__CampaignR__Updat__70C02A4C]  DEFAULT (sysutcdatetime()) FOR [UpdatedAtUtc]
GO
ALTER TABLE [dbo].[CRMCampanaDestinatario]  WITH CHECK ADD  CONSTRAINT [CRMCampanaDestinatario_CK__CampaignR__Accou__691F0884] CHECK  (([AccountRevision]>(0)))
GO
ALTER TABLE [dbo].[CRMCampanaDestinatario] CHECK CONSTRAINT [CRMCampanaDestinatario_CK__CampaignR__Accou__691F0884]
GO
ALTER TABLE [dbo].[CRMCampanaDestinatario]  WITH CHECK ADD  CONSTRAINT [CRMCampanaDestinatario_CK__CampaignR__Attem__6ED7E1DA] CHECK  (([Attempts]>=(0) AND [Attempts]<=(20)))
GO
ALTER TABLE [dbo].[CRMCampanaDestinatario] CHECK CONSTRAINT [CRMCampanaDestinatario_CK__CampaignR__Attem__6ED7E1DA]
GO
ALTER TABLE [dbo].[CRMCampanaDestinatario]  WITH CHECK ADD  CONSTRAINT [CRMCampanaDestinatario_CK__CampaignR__Campa__6736C012] CHECK  (([CampaignRevision]>=(0)))
GO
ALTER TABLE [dbo].[CRMCampanaDestinatario] CHECK CONSTRAINT [CRMCampanaDestinatario_CK__CampaignR__Campa__6736C012]
GO
ALTER TABLE [dbo].[CRMCampanaDestinatario]  WITH CHECK ADD  CONSTRAINT [CRMCampanaDestinatario_CK__CampaignR__Contr__6A132CBD] CHECK  (([ControlEpoch]>=(0)))
GO
ALTER TABLE [dbo].[CRMCampanaDestinatario] CHECK CONSTRAINT [CRMCampanaDestinatario_CK__CampaignR__Contr__6A132CBD]
GO
ALTER TABLE [dbo].[CRMCampanaDestinatario]  WITH CHECK ADD  CONSTRAINT [CRMCampanaDestinatario_CK__CampaignR__Evide__6CEF9968] CHECK  ((isjson([EvidenceJson])=(1) AND left(ltrim([EvidenceJson]),(1))=N'{'))
GO
ALTER TABLE [dbo].[CRMCampanaDestinatario] CHECK CONSTRAINT [CRMCampanaDestinatario_CK__CampaignR__Evide__6CEF9968]
GO
ALTER TABLE [dbo].[CRMCampanaDestinatario]  WITH CHECK ADD  CONSTRAINT [CRMCampanaDestinatario_CK__CampaignR__Inclu__6B0750F6] CHECK  (([InclusionEpoch]>=(0)))
GO
ALTER TABLE [dbo].[CRMCampanaDestinatario] CHECK CONSTRAINT [CRMCampanaDestinatario_CK__CampaignR__Inclu__6B0750F6]
GO
ALTER TABLE [dbo].[CRMCampanaDestinatario]  WITH CHECK ADD  CONSTRAINT [CRMCampanaDestinatario_CK__CampaignR__Input__6BFB752F] CHECK  (([InputSequence]>=(0)))
GO
ALTER TABLE [dbo].[CRMCampanaDestinatario] CHECK CONSTRAINT [CRMCampanaDestinatario_CK__CampaignR__Input__6BFB752F]
GO
ALTER TABLE [dbo].[CRMCampanaDestinatario]  WITH CHECK ADD  CONSTRAINT [CRMCampanaDestinatario_CK__CampaignR__RuleR__682AE44B] CHECK  (([RuleRevision]>=(0)))
GO
ALTER TABLE [dbo].[CRMCampanaDestinatario] CHECK CONSTRAINT [CRMCampanaDestinatario_CK__CampaignR__RuleR__682AE44B]
GO
ALTER TABLE [dbo].[CRMCampanaDestinatario]  WITH CHECK ADD  CONSTRAINT [CRMCampanaDestinatario_CK__CampaignR__Statu__654E77A0] CHECK  (([Status]='cancelled' OR [Status]='uncertain' OR [Status]='failed' OR [Status]='read' OR [Status]='delivered' OR [Status]='sent' OR [Status]='queued' OR [Status]='leased' OR [Status]='blocked' OR [Status]='prepared' OR [Status]='pending'))
GO
ALTER TABLE [dbo].[CRMCampanaDestinatario] CHECK CONSTRAINT [CRMCampanaDestinatario_CK__CampaignR__Statu__654E77A0]
GO
ALTER TABLE [dbo].[CRMCampanaDestinatario]  WITH CHECK ADD  CONSTRAINT [CRMCampanaDestinatario_CK__CampaignRecipien__7490BB30] CHECK  (([ConsentId] IS NULL AND [ConsentVersion] IS NULL OR [ConsentId] IS NOT NULL AND [ConsentVersion] IS NOT NULL))
GO
ALTER TABLE [dbo].[CRMCampanaDestinatario] CHECK CONSTRAINT [CRMCampanaDestinatario_CK__CampaignRecipien__7490BB30]
GO
ALTER TABLE [dbo].[CRMCampanaDestinatario]  WITH CHECK ADD  CONSTRAINT [CRMCampanaDestinatario_CK__CampaignRecipien__7584DF69] CHECK  ((NOT ([Status]='uncertain' OR [Status]='read' OR [Status]='delivered' OR [Status]='sent' OR [Status]='queued') OR [QueueId] IS NOT NULL AND [ConsentId] IS NOT NULL))
GO
ALTER TABLE [dbo].[CRMCampanaDestinatario] CHECK CONSTRAINT [CRMCampanaDestinatario_CK__CampaignRecipien__7584DF69]
GO
ALTER TABLE [dbo].[CRMCampanaDestinatario]  WITH CHECK ADD  CONSTRAINT [CRMCampanaDestinatario_CK__CampaignRecipien__767903A2] CHECK  (([Status]='leased' AND [LeaseId] IS NOT NULL AND [LeaseUntilUtc] IS NOT NULL OR [Status]<>'leased' AND [LeaseId] IS NULL AND [LeaseUntilUtc] IS NULL))
GO
ALTER TABLE [dbo].[CRMCampanaDestinatario] CHECK CONSTRAINT [CRMCampanaDestinatario_CK__CampaignRecipien__767903A2]
GO
-- crm_marketing.ChurnAssessment -> dbo.CRMAbandonoEvaluacion
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMAbandonoEvaluacion](

	[AssessmentId] [uniqueidentifier] NOT NULL,

	[ConversationId] [uniqueidentifier] NOT NULL,

	[IdentityId] [uniqueidentifier] NULL,

	[AsOfUtc] [datetime2](7) NOT NULL,

	[InputSequence] [bigint] NULL,

	[FormulaVersion] [varchar](40) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[ComputedLeadScore] [tinyint] NULL,

	[LeadReasonsJson] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Status] [varchar](16) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[RiskScore] [tinyint] NULL,

	[RiskLevel] [varchar](16) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[StageSnapshot] [nvarchar](60) COLLATE Latin1_General_100_BIN2 NULL,

	[WaitingSinceUtc] [datetime2](7) NULL,

	[ReasonsJson] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[EvidenceJson] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[CreatedAtUtc] [datetime2](7) NOT NULL,

	[RunId] [uniqueidentifier] NULL,

 CONSTRAINT [CRMAbandonoEvaluacion_PK__ChurnAss__3D2BF81EE89A0E33] PRIMARY KEY CLUSTERED 

(

	[AssessmentId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF),

 CONSTRAINT [CRMAbandonoEvaluacion_UQ__ChurnAss__6995BABE4A1A1B8C] UNIQUE NONCLUSTERED 

(

	[ConversationId] ASC,

	[IdentityId] ASC,

	[AsOfUtc] ASC,

	[FormulaVersion] ASC,

	[InputSequence] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
CREATE NONCLUSTERED INDEX [CRMAbandonoEvaluacion_IX_Marketing_Churn_Recent] ON [dbo].[CRMAbandonoEvaluacion]

(

	[ConversationId] ASC,

	[AsOfUtc] DESC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
ALTER TABLE [dbo].[CRMAbandonoEvaluacion] ADD  CONSTRAINT [CRMAbandonoEvaluacion_DF__ChurnAsse__LeadR__0E85975D]  DEFAULT ('[]') FOR [LeadReasonsJson]
GO
ALTER TABLE [dbo].[CRMAbandonoEvaluacion] ADD  CONSTRAINT [CRMAbandonoEvaluacion_DF__ChurnAsse__Creat__134A4C7A]  DEFAULT (sysutcdatetime()) FOR [CreatedAtUtc]
GO
ALTER TABLE [dbo].[CRMAbandonoEvaluacion]  WITH CHECK ADD  CONSTRAINT [CRMAbandonoEvaluacion_CK__ChurnAsse__Compu__0D917324] CHECK  (([ComputedLeadScore]>=(0) AND [ComputedLeadScore]<=(100)))
GO
ALTER TABLE [dbo].[CRMAbandonoEvaluacion] CHECK CONSTRAINT [CRMAbandonoEvaluacion_CK__ChurnAsse__Compu__0D917324]
GO
ALTER TABLE [dbo].[CRMAbandonoEvaluacion]  WITH CHECK ADD  CONSTRAINT [CRMAbandonoEvaluacion_CK__ChurnAsse__Evide__12562841] CHECK  ((isjson([EvidenceJson])=(1) AND left(ltrim([EvidenceJson]),(1))=N'{'))
GO
ALTER TABLE [dbo].[CRMAbandonoEvaluacion] CHECK CONSTRAINT [CRMAbandonoEvaluacion_CK__ChurnAsse__Evide__12562841]
GO
ALTER TABLE [dbo].[CRMAbandonoEvaluacion]  WITH CHECK ADD  CONSTRAINT [CRMAbandonoEvaluacion_CK__ChurnAsse__Input__0C9D4EEB] CHECK  (([InputSequence]>(0)))
GO
ALTER TABLE [dbo].[CRMAbandonoEvaluacion] CHECK CONSTRAINT [CRMAbandonoEvaluacion_CK__ChurnAsse__Input__0C9D4EEB]
GO
ALTER TABLE [dbo].[CRMAbandonoEvaluacion]  WITH CHECK ADD  CONSTRAINT [CRMAbandonoEvaluacion_CK__ChurnAsse__LeadR__0F79BB96] CHECK  ((isjson([LeadReasonsJson])=(1)))
GO
ALTER TABLE [dbo].[CRMAbandonoEvaluacion] CHECK CONSTRAINT [CRMAbandonoEvaluacion_CK__ChurnAsse__LeadR__0F79BB96]
GO
ALTER TABLE [dbo].[CRMAbandonoEvaluacion]  WITH CHECK ADD  CONSTRAINT [CRMAbandonoEvaluacion_CK__ChurnAsse__Reaso__11620408] CHECK  ((isjson([ReasonsJson])=(1) AND left(ltrim([ReasonsJson]),(1))=N'['))
GO
ALTER TABLE [dbo].[CRMAbandonoEvaluacion] CHECK CONSTRAINT [CRMAbandonoEvaluacion_CK__ChurnAsse__Reaso__11620408]
GO
ALTER TABLE [dbo].[CRMAbandonoEvaluacion]  WITH CHECK ADD  CONSTRAINT [CRMAbandonoEvaluacion_CK__ChurnAsse__Statu__106DDFCF] CHECK  (([Status]='not_applicable' OR [Status]='unknown' OR [Status]='known'))
GO
ALTER TABLE [dbo].[CRMAbandonoEvaluacion] CHECK CONSTRAINT [CRMAbandonoEvaluacion_CK__ChurnAsse__Statu__106DDFCF]
GO
ALTER TABLE [dbo].[CRMAbandonoEvaluacion]  WITH CHECK ADD  CONSTRAINT [CRMAbandonoEvaluacion_CK__ChurnAssessment__143E70B3] CHECK  (([Status]='known' AND [IdentityId] IS NOT NULL AND [StageSnapshot] IS NOT NULL AND [InputSequence] IS NOT NULL AND [RiskScore] IS NOT NULL AND ([RiskScore]>=(0) AND [RiskScore]<=(100)) AND [WaitingSinceUtc] IS NOT NULL AND ([RiskScore]<(35) AND [RiskLevel]='low' OR [RiskScore]>=(35) AND [RiskScore]<=(69) AND [RiskLevel]='medium' OR [RiskScore]>=(70) AND [RiskLevel]='high') OR [Status]='unknown' AND [RiskScore] IS NULL AND [RiskLevel]='unknown' OR [Status]='not_applicable' AND [RiskScore] IS NULL AND [RiskLevel]='not_applicable'))
GO
ALTER TABLE [dbo].[CRMAbandonoEvaluacion] CHECK CONSTRAINT [CRMAbandonoEvaluacion_CK__ChurnAssessment__143E70B3]
GO
ALTER TABLE [dbo].[CRMAbandonoEvaluacion]  WITH CHECK ADD  CONSTRAINT [CRMAbandonoEvaluacion_CK__ChurnAssessment__153294EC] CHECK  (([WaitingSinceUtc] IS NULL OR [WaitingSinceUtc]<=[AsOfUtc]))
GO
ALTER TABLE [dbo].[CRMAbandonoEvaluacion] CHECK CONSTRAINT [CRMAbandonoEvaluacion_CK__ChurnAssessment__153294EC]
GO
-- crm_marketing.ContactConsent -> dbo.CRMContactoConsentimiento
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMContactoConsentimiento](

	[ConsentId] [uniqueidentifier] NOT NULL,

	[IdentityId] [uniqueidentifier] NOT NULL,

	[Channel] [varchar](12) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[AccountScope] [nvarchar](128) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Purpose] [varchar](24) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Status] [varchar](10) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Version] [bigint] NOT NULL,

	[RevokesVersion] [bigint] NULL,

	[EvidenceJson] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[DecisionAtUtc] [datetime2](7) NULL,

	[ExpiresAtUtc] [datetime2](7) NULL,

	[CreatedAtUtc] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMContactoConsentimiento_PK__ContactC__374AB086B18C5978] PRIMARY KEY CLUSTERED 

(

	[ConsentId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF),

 CONSTRAINT [CRMContactoConsentimiento_UQ__ContactC__77BFF094EC086E6E] UNIQUE NONCLUSTERED 

(

	[ConsentId] ASC,

	[Version] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF),

 CONSTRAINT [CRMContactoConsentimiento_UQ__ContactC__9FE21C7325EC1DEA] UNIQUE NONCLUSTERED 

(

	[IdentityId] ASC,

	[Channel] ASC,

	[AccountScope] ASC,

	[Purpose] ASC,

	[Version] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
SET ANSI_PADDING ON
GO
CREATE NONCLUSTERED INDEX [CRMContactoConsentimiento_IX_Marketing_Consent_Current] ON [dbo].[CRMContactoConsentimiento]

(

	[IdentityId] ASC,

	[Channel] ASC,

	[AccountScope] ASC,

	[Purpose] ASC,

	[Version] DESC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
ALTER TABLE [dbo].[CRMContactoConsentimiento] ADD  CONSTRAINT [CRMContactoConsentimiento_DF__ContactCo__Statu__2A2DB1D2]  DEFAULT ('unknown') FOR [Status]
GO
ALTER TABLE [dbo].[CRMContactoConsentimiento] ADD  CONSTRAINT [CRMContactoConsentimiento_DF__ContactCo__Creat__2DFE42B6]  DEFAULT (sysutcdatetime()) FOR [CreatedAtUtc]
GO
ALTER TABLE [dbo].[CRMContactoConsentimiento]  WITH CHECK ADD  CONSTRAINT [CRMContactoConsentimiento_CK__ContactCo__Evide__2D0A1E7D] CHECK  ((isjson([EvidenceJson])=(1) AND left(ltrim([EvidenceJson]),(1))=N'{'))
GO
ALTER TABLE [dbo].[CRMContactoConsentimiento] CHECK CONSTRAINT [CRMContactoConsentimiento_CK__ContactCo__Evide__2D0A1E7D]
GO
ALTER TABLE [dbo].[CRMContactoConsentimiento]  WITH CHECK ADD  CONSTRAINT [CRMContactoConsentimiento_CK__ContactCo__Purpo__29398D99] CHECK  (([Purpose]='service' OR [Purpose]='marketing'))
GO
ALTER TABLE [dbo].[CRMContactoConsentimiento] CHECK CONSTRAINT [CRMContactoConsentimiento_CK__ContactCo__Purpo__29398D99]
GO
ALTER TABLE [dbo].[CRMContactoConsentimiento]  WITH CHECK ADD  CONSTRAINT [CRMContactoConsentimiento_CK__ContactCo__Statu__2B21D60B] CHECK  (([Status]='expired' OR [Status]='revoked' OR [Status]='granted' OR [Status]='unknown'))
GO
ALTER TABLE [dbo].[CRMContactoConsentimiento] CHECK CONSTRAINT [CRMContactoConsentimiento_CK__ContactCo__Statu__2B21D60B]
GO
ALTER TABLE [dbo].[CRMContactoConsentimiento]  WITH CHECK ADD  CONSTRAINT [CRMContactoConsentimiento_CK__ContactCo__Versi__2C15FA44] CHECK  (([Version]>(0)))
GO
ALTER TABLE [dbo].[CRMContactoConsentimiento] CHECK CONSTRAINT [CRMContactoConsentimiento_CK__ContactCo__Versi__2C15FA44]
GO
ALTER TABLE [dbo].[CRMContactoConsentimiento]  WITH CHECK ADD  CONSTRAINT [CRMContactoConsentimiento_CK__ContactConsent__2FE68B28] CHECK  (([RevokesVersion] IS NULL OR [Status]='revoked' AND [RevokesVersion]<[Version]))
GO
ALTER TABLE [dbo].[CRMContactoConsentimiento] CHECK CONSTRAINT [CRMContactoConsentimiento_CK__ContactConsent__2FE68B28]
GO
ALTER TABLE [dbo].[CRMContactoConsentimiento]  WITH CHECK ADD  CONSTRAINT [CRMContactoConsentimiento_CK__ContactConsent__30DAAF61] CHECK  (([Status]='unknown' OR [DecisionAtUtc] IS NOT NULL))
GO
ALTER TABLE [dbo].[CRMContactoConsentimiento] CHECK CONSTRAINT [CRMContactoConsentimiento_CK__ContactConsent__30DAAF61]
GO
ALTER TABLE [dbo].[CRMContactoConsentimiento]  WITH CHECK ADD  CONSTRAINT [CRMContactoConsentimiento_CK__ContactConsent__31CED39A] CHECK  (([ExpiresAtUtc] IS NULL OR [DecisionAtUtc] IS NOT NULL AND [ExpiresAtUtc]>[DecisionAtUtc]))
GO
ALTER TABLE [dbo].[CRMContactoConsentimiento] CHECK CONSTRAINT [CRMContactoConsentimiento_CK__ContactConsent__31CED39A]
GO
-- crm_marketing.EvaluationRun -> dbo.CRMCampanaEvaluacionEjecucion
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMCampanaEvaluacionEjecucion](

	[RunId] [uniqueidentifier] NOT NULL,

	[Kind] [varchar](16) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[TriggerKind] [varchar](8) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[RuleId] [uniqueidentifier] NULL,

	[CampaignId] [uniqueidentifier] NULL,

	[State] [varchar](12) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[DueAtUtc] [datetime2](7) NOT NULL,

	[RequestedAtUtc] [datetime2](7) NOT NULL,

	[StartedAtUtc] [datetime2](7) NULL,

	[CompletedAtUtc] [datetime2](7) NULL,

	[LeaseId] [uniqueidentifier] NULL,

	[LeaseUntilUtc] [datetime2](7) NULL,

	[Attempts] [int] NOT NULL,

	[CountsJson] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[LastError] [varchar](80) COLLATE Modern_Spanish_CI_AS NULL,

 CONSTRAINT [CRMCampanaEvaluacionEjecucion_PK__Evaluati__A259D4DD98C18B6D] PRIMARY KEY CLUSTERED 

(

	[RunId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
SET ANSI_PADDING ON
GO
CREATE NONCLUSTERED INDEX [CRMCampanaEvaluacionEjecucion_IX_Marketing_Run_Due] ON [dbo].[CRMCampanaEvaluacionEjecucion]

(

	[State] ASC,

	[DueAtUtc] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
ALTER TABLE [dbo].[CRMCampanaEvaluacionEjecucion] ADD  CONSTRAINT [CRMCampanaEvaluacionEjecucion_DF__Evaluatio__State__7D260131]  DEFAULT ('queued') FOR [State]
GO
ALTER TABLE [dbo].[CRMCampanaEvaluacionEjecucion] ADD  CONSTRAINT [CRMCampanaEvaluacionEjecucion_DF__Evaluatio__DueAt__7F0E49A3]  DEFAULT (sysutcdatetime()) FOR [DueAtUtc]
GO
ALTER TABLE [dbo].[CRMCampanaEvaluacionEjecucion] ADD  CONSTRAINT [CRMCampanaEvaluacionEjecucion_DF__Evaluatio__Reque__00026DDC]  DEFAULT (sysutcdatetime()) FOR [RequestedAtUtc]
GO
ALTER TABLE [dbo].[CRMCampanaEvaluacionEjecucion] ADD  CONSTRAINT [CRMCampanaEvaluacionEjecucion_DF__Evaluatio__Attem__00F69215]  DEFAULT ((0)) FOR [Attempts]
GO
ALTER TABLE [dbo].[CRMCampanaEvaluacionEjecucion] ADD  CONSTRAINT [CRMCampanaEvaluacionEjecucion_DF__Evaluatio__Count__02DEDA87]  DEFAULT ('{}') FOR [CountsJson]
GO
ALTER TABLE [dbo].[CRMCampanaEvaluacionEjecucion]  WITH CHECK ADD  CONSTRAINT [CRMCampanaEvaluacionEjecucion_CK__Evaluatio__Attem__01EAB64E] CHECK  (([Attempts]>=(0) AND [Attempts]<=(3)))
GO
ALTER TABLE [dbo].[CRMCampanaEvaluacionEjecucion] CHECK CONSTRAINT [CRMCampanaEvaluacionEjecucion_CK__Evaluatio__Attem__01EAB64E]
GO
ALTER TABLE [dbo].[CRMCampanaEvaluacionEjecucion]  WITH CHECK ADD  CONSTRAINT [CRMCampanaEvaluacionEjecucion_CK__Evaluatio__Count__03D2FEC0] CHECK  ((isjson([CountsJson])=(1)))
GO
ALTER TABLE [dbo].[CRMCampanaEvaluacionEjecucion] CHECK CONSTRAINT [CRMCampanaEvaluacionEjecucion_CK__Evaluatio__Count__03D2FEC0]
GO
ALTER TABLE [dbo].[CRMCampanaEvaluacionEjecucion]  WITH CHECK ADD  CONSTRAINT [CRMCampanaEvaluacionEjecucion_CK__Evaluatio__State__7E1A256A] CHECK  (([State]='failed' OR [State]='completed' OR [State]='processing' OR [State]='queued'))
GO
ALTER TABLE [dbo].[CRMCampanaEvaluacionEjecucion] CHECK CONSTRAINT [CRMCampanaEvaluacionEjecucion_CK__Evaluatio__State__7E1A256A]
GO
ALTER TABLE [dbo].[CRMCampanaEvaluacionEjecucion]  WITH CHECK ADD  CONSTRAINT [CRMCampanaEvaluacionEjecucion_CK__Evaluatio__Trigg__7A499486] CHECK  (([TriggerKind]='worker' OR [TriggerKind]='manual'))
GO
ALTER TABLE [dbo].[CRMCampanaEvaluacionEjecucion] CHECK CONSTRAINT [CRMCampanaEvaluacionEjecucion_CK__Evaluatio__Trigg__7A499486]
GO
ALTER TABLE [dbo].[CRMCampanaEvaluacionEjecucion]  WITH CHECK ADD  CONSTRAINT [CRMCampanaEvaluacionEjecucion_CK__Evaluation__Kind__7955704D] CHECK  (([Kind]='preparation' OR [Kind]='remarketing' OR [Kind]='predictions'))
GO
ALTER TABLE [dbo].[CRMCampanaEvaluacionEjecucion] CHECK CONSTRAINT [CRMCampanaEvaluacionEjecucion_CK__Evaluation__Kind__7955704D]
GO
-- crm_marketing.MessageTemplate -> dbo.CRMMensajePlantilla
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMMensajePlantilla](

	[TemplateId] [uniqueidentifier] NOT NULL,

	[Channel] [varchar](12) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[AccountScope] [nvarchar](128) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[AccountRevision] [int] NOT NULL,

	[ProviderTemplateId] [nvarchar](128) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Name] [nvarchar](128) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Language] [varchar](20) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Status] [varchar](16) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Version] [bigint] NOT NULL,

	[StatusRevision] [bigint] NOT NULL,

	[ComponentsJson] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[SyncedAtUtc] [datetime2](7) NULL,

 CONSTRAINT [CRMMensajePlantilla_PK__MessageT__F87ADD27C3B31EEE] PRIMARY KEY CLUSTERED 

(

	[TemplateId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF),

 CONSTRAINT [CRMMensajePlantilla_UQ__MessageT__A51DA6BED7FA26BC] UNIQUE NONCLUSTERED 

(

	[Channel] ASC,

	[AccountScope] ASC,

	[ProviderTemplateId] ASC,

	[Version] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF),

 CONSTRAINT [CRMMensajePlantilla_UQ__MessageT__D12379C94BE420CB] UNIQUE NONCLUSTERED 

(

	[Channel] ASC,

	[AccountScope] ASC,

	[Name] ASC,

	[Language] ASC,

	[Version] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF),

 CONSTRAINT [CRMMensajePlantilla_UQ__MessageT__F88CF50B639CE7A5] UNIQUE NONCLUSTERED 

(

	[TemplateId] ASC,

	[Version] ASC,

	[Channel] ASC,

	[AccountScope] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
ALTER TABLE [dbo].[CRMMensajePlantilla] ADD  CONSTRAINT [CRMMensajePlantilla_DF__MessageTe__Statu__1CD3B6B4]  DEFAULT ('unknown') FOR [Status]
GO
ALTER TABLE [dbo].[CRMMensajePlantilla] ADD  CONSTRAINT [CRMMensajePlantilla_DF__MessageTe__Statu__1FB0235F]  DEFAULT ((0)) FOR [StatusRevision]
GO
ALTER TABLE [dbo].[CRMMensajePlantilla]  WITH CHECK ADD  CONSTRAINT [CRMMensajePlantilla_CK__MessageTe__Accou__1BDF927B] CHECK  (([AccountRevision]>(0)))
GO
ALTER TABLE [dbo].[CRMMensajePlantilla] CHECK CONSTRAINT [CRMMensajePlantilla_CK__MessageTe__Accou__1BDF927B]
GO
ALTER TABLE [dbo].[CRMMensajePlantilla]  WITH CHECK ADD  CONSTRAINT [CRMMensajePlantilla_CK__MessageTe__Compo__21986BD1] CHECK  ((isjson([ComponentsJson])=(1) AND left(ltrim([ComponentsJson]),(1))=N'['))
GO
ALTER TABLE [dbo].[CRMMensajePlantilla] CHECK CONSTRAINT [CRMMensajePlantilla_CK__MessageTe__Compo__21986BD1]
GO
ALTER TABLE [dbo].[CRMMensajePlantilla]  WITH CHECK ADD  CONSTRAINT [CRMMensajePlantilla_CK__MessageTe__Statu__1DC7DAED] CHECK  (([Status]='deleted' OR [Status]='disabled' OR [Status]='paused' OR [Status]='rejected' OR [Status]='approved' OR [Status]='pending' OR [Status]='unknown'))
GO
ALTER TABLE [dbo].[CRMMensajePlantilla] CHECK CONSTRAINT [CRMMensajePlantilla_CK__MessageTe__Statu__1DC7DAED]
GO
ALTER TABLE [dbo].[CRMMensajePlantilla]  WITH CHECK ADD  CONSTRAINT [CRMMensajePlantilla_CK__MessageTe__Statu__20A44798] CHECK  (([StatusRevision]>=(0)))
GO
ALTER TABLE [dbo].[CRMMensajePlantilla] CHECK CONSTRAINT [CRMMensajePlantilla_CK__MessageTe__Statu__20A44798]
GO
ALTER TABLE [dbo].[CRMMensajePlantilla]  WITH CHECK ADD  CONSTRAINT [CRMMensajePlantilla_CK__MessageTe__Versi__1EBBFF26] CHECK  (([Version]>(0)))
GO
ALTER TABLE [dbo].[CRMMensajePlantilla] CHECK CONSTRAINT [CRMMensajePlantilla_CK__MessageTe__Versi__1EBBFF26]
GO
ALTER TABLE [dbo].[CRMMensajePlantilla]  WITH CHECK ADD  CONSTRAINT [CRMMensajePlantilla_CK__MessageTemplate__228C900A] CHECK  ((len(ltrim(rtrim([AccountScope])))>(0) AND len(ltrim(rtrim([Name])))>(0) AND len([Language])>(0)))
GO
ALTER TABLE [dbo].[CRMMensajePlantilla] CHECK CONSTRAINT [CRMMensajePlantilla_CK__MessageTemplate__228C900A]
GO
-- crm_marketing.Policy -> dbo.CRMCampanaPolitica
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[CRMCampanaPolitica](

	[PolicyId] [tinyint] NOT NULL,

	[Revision] [bigint] NOT NULL,

	[StageWeightsJson] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[EvaluationEnabled] [bit] NOT NULL,

	[IntervalMinutes] [int] NOT NULL,

	[NextRunAtUtc] [datetime2](7) NOT NULL,

	[UpdatedAtUtc] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMCampanaPolitica_PK__Policy__2E1339A4F7698235] PRIMARY KEY CLUSTERED 

(

	[PolicyId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
ALTER TABLE [dbo].[CRMCampanaPolitica] ADD  CONSTRAINT [CRMCampanaPolitica_DF__Policy__Revision__0897B3DD]  DEFAULT ((0)) FOR [Revision]
GO
ALTER TABLE [dbo].[CRMCampanaPolitica] ADD  CONSTRAINT [CRMCampanaPolitica_DF__Policy__StageWei__0A7FFC4F]  DEFAULT ('{}') FOR [StageWeightsJson]
GO
ALTER TABLE [dbo].[CRMCampanaPolitica] ADD  CONSTRAINT [CRMCampanaPolitica_DF__Policy__Evaluati__0C6844C1]  DEFAULT ((1)) FOR [EvaluationEnabled]
GO
ALTER TABLE [dbo].[CRMCampanaPolitica] ADD  CONSTRAINT [CRMCampanaPolitica_DF__Policy__Interval__0D5C68FA]  DEFAULT ((60)) FOR [IntervalMinutes]
GO
ALTER TABLE [dbo].[CRMCampanaPolitica] ADD  CONSTRAINT [CRMCampanaPolitica_DF__Policy__NextRunA__0F44B16C]  DEFAULT (dateadd(minute,(60),sysutcdatetime())) FOR [NextRunAtUtc]
GO
ALTER TABLE [dbo].[CRMCampanaPolitica] ADD  CONSTRAINT [CRMCampanaPolitica_DF__Policy__UpdatedA__1038D5A5]  DEFAULT (sysutcdatetime()) FOR [UpdatedAtUtc]
GO
ALTER TABLE [dbo].[CRMCampanaPolitica]  WITH CHECK ADD  CONSTRAINT [CRMCampanaPolitica_CK__Policy__Interval__0E508D33] CHECK  (([IntervalMinutes]>=(1) AND [IntervalMinutes]<=(1440)))
GO
ALTER TABLE [dbo].[CRMCampanaPolitica] CHECK CONSTRAINT [CRMCampanaPolitica_CK__Policy__Interval__0E508D33]
GO
ALTER TABLE [dbo].[CRMCampanaPolitica]  WITH CHECK ADD  CONSTRAINT [CRMCampanaPolitica_CK__Policy__PolicyId__07A38FA4] CHECK  (([PolicyId]=(1)))
GO
ALTER TABLE [dbo].[CRMCampanaPolitica] CHECK CONSTRAINT [CRMCampanaPolitica_CK__Policy__PolicyId__07A38FA4]
GO
ALTER TABLE [dbo].[CRMCampanaPolitica]  WITH CHECK ADD  CONSTRAINT [CRMCampanaPolitica_CK__Policy__Revision__098BD816] CHECK  (([Revision]>=(0)))
GO
ALTER TABLE [dbo].[CRMCampanaPolitica] CHECK CONSTRAINT [CRMCampanaPolitica_CK__Policy__Revision__098BD816]
GO
ALTER TABLE [dbo].[CRMCampanaPolitica]  WITH CHECK ADD  CONSTRAINT [CRMCampanaPolitica_CK__Policy__StageWei__0B742088] CHECK  ((isjson([StageWeightsJson])=(1)))
GO
ALTER TABLE [dbo].[CRMCampanaPolitica] CHECK CONSTRAINT [CRMCampanaPolitica_CK__Policy__StageWei__0B742088]
GO
-- crm_marketing.RemarketingRule -> dbo.CRMRecontactoRegla
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMRecontactoRegla](

	[RuleId] [uniqueidentifier] NOT NULL,

	[Name] [nvarchar](160) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[StageValue] [nvarchar](60) COLLATE Latin1_General_100_BIN2 NOT NULL,

	[Channel] [varchar](12) COLLATE Modern_Spanish_CI_AS NULL,

	[AccountScope] [nvarchar](128) COLLATE Modern_Spanish_CI_AS NULL,

	[TemplateId] [uniqueidentifier] NULL,

	[TemplateVersion] [bigint] NULL,

	[InactivityDays] [smallint] NOT NULL,

	[CooldownHours] [int] NOT NULL,

	[MinimumRisk] [tinyint] NOT NULL,

	[Enabled] [bit] NOT NULL,

	[Revision] [bigint] NOT NULL,

	[NextEvaluationAtUtc] [datetime2](7) NOT NULL,

	[CreatedAtUtc] [datetime2](7) NOT NULL,

	[UpdatedAtUtc] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMRecontactoRegla_PK__Remarket__110458E28E416B94] PRIMARY KEY CLUSTERED 

(

	[RuleId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
ALTER TABLE [dbo].[CRMRecontactoRegla] ADD  CONSTRAINT [CRMRecontactoRegla_DF__Remarketi__Minim__3787ACF0]  DEFAULT ((70)) FOR [MinimumRisk]
GO
ALTER TABLE [dbo].[CRMRecontactoRegla] ADD  CONSTRAINT [CRMRecontactoRegla_DF__Remarketi__Enabl__396FF562]  DEFAULT ((0)) FOR [Enabled]
GO
ALTER TABLE [dbo].[CRMRecontactoRegla] ADD  CONSTRAINT [CRMRecontactoRegla_DF__Remarketi__Revis__3A64199B]  DEFAULT ((0)) FOR [Revision]
GO
ALTER TABLE [dbo].[CRMRecontactoRegla] ADD  CONSTRAINT [CRMRecontactoRegla_DF__Remarketi__NextE__3C4C620D]  DEFAULT (sysutcdatetime()) FOR [NextEvaluationAtUtc]
GO
ALTER TABLE [dbo].[CRMRecontactoRegla] ADD  CONSTRAINT [CRMRecontactoRegla_DF__Remarketi__Creat__3D408646]  DEFAULT (sysutcdatetime()) FOR [CreatedAtUtc]
GO
ALTER TABLE [dbo].[CRMRecontactoRegla] ADD  CONSTRAINT [CRMRecontactoRegla_DF__Remarketi__Updat__3E34AA7F]  DEFAULT (sysutcdatetime()) FOR [UpdatedAtUtc]
GO
ALTER TABLE [dbo].[CRMRecontactoRegla]  WITH CHECK ADD  CONSTRAINT [CRMRecontactoRegla_CK__Remarketi__Coold__369388B7] CHECK  (([CooldownHours]>=(1) AND [CooldownHours]<=(87600)))
GO
ALTER TABLE [dbo].[CRMRecontactoRegla] CHECK CONSTRAINT [CRMRecontactoRegla_CK__Remarketi__Coold__369388B7]
GO
ALTER TABLE [dbo].[CRMRecontactoRegla]  WITH CHECK ADD  CONSTRAINT [CRMRecontactoRegla_CK__Remarketi__Inact__359F647E] CHECK  (([InactivityDays]>=(1) AND [InactivityDays]<=(3650)))
GO
ALTER TABLE [dbo].[CRMRecontactoRegla] CHECK CONSTRAINT [CRMRecontactoRegla_CK__Remarketi__Inact__359F647E]
GO
ALTER TABLE [dbo].[CRMRecontactoRegla]  WITH CHECK ADD  CONSTRAINT [CRMRecontactoRegla_CK__Remarketi__Minim__387BD129] CHECK  (([MinimumRisk]>=(0) AND [MinimumRisk]<=(100)))
GO
ALTER TABLE [dbo].[CRMRecontactoRegla] CHECK CONSTRAINT [CRMRecontactoRegla_CK__Remarketi__Minim__387BD129]
GO
ALTER TABLE [dbo].[CRMRecontactoRegla]  WITH CHECK ADD  CONSTRAINT [CRMRecontactoRegla_CK__Remarketi__Revis__3B583DD4] CHECK  (([Revision]>=(0)))
GO
ALTER TABLE [dbo].[CRMRecontactoRegla] CHECK CONSTRAINT [CRMRecontactoRegla_CK__Remarketi__Revis__3B583DD4]
GO
ALTER TABLE [dbo].[CRMRecontactoRegla]  WITH CHECK ADD  CONSTRAINT [CRMRecontactoRegla_CK__Remarketi__Stage__401CF2F1] CHECK  ((len(ltrim(rtrim([StageValue])))>(0)))
GO
ALTER TABLE [dbo].[CRMRecontactoRegla] CHECK CONSTRAINT [CRMRecontactoRegla_CK__Remarketi__Stage__401CF2F1]
GO
ALTER TABLE [dbo].[CRMRecontactoRegla]  WITH CHECK ADD  CONSTRAINT [CRMRecontactoRegla_CK__RemarketingRule__4111172A] CHECK  (([TemplateId] IS NULL AND [TemplateVersion] IS NULL OR [TemplateId] IS NOT NULL AND [TemplateVersion] IS NOT NULL))
GO
ALTER TABLE [dbo].[CRMRecontactoRegla] CHECK CONSTRAINT [CRMRecontactoRegla_CK__RemarketingRule__4111172A]
GO
ALTER TABLE [dbo].[CRMRecontactoRegla]  WITH CHECK ADD  CONSTRAINT [CRMRecontactoRegla_CK__RemarketingRule__42053B63] CHECK  (([Enabled]=(0) OR [TemplateId] IS NOT NULL AND [Channel] IS NOT NULL AND [AccountScope] IS NOT NULL))
GO
ALTER TABLE [dbo].[CRMRecontactoRegla] CHECK CONSTRAINT [CRMRecontactoRegla_CK__RemarketingRule__42053B63]
GO
-- crm_merge.MergeCase -> dbo.CRMContactoUnificacion
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[CRMContactoUnificacion](

	[MergeId] [uniqueidentifier] NOT NULL,

	[SourceContactId] [uniqueidentifier] NOT NULL,

	[TargetContactId] [uniqueidentifier] NOT NULL,

	[Active] [bit] NOT NULL,

	[BeforeJson] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[AppliedJson] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[ChoicesJson] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[AppliedCrmRevision] [bigint] NOT NULL,

	[UndoBeforeJson] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NULL,

	[UndoAppliedJson] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NULL,

	[CreatedAt] [datetime2](7) NOT NULL,

	[UndoneAt] [datetime2](7) NULL,

 CONSTRAINT [CRMContactoUnificacion_PK_MergeCase] PRIMARY KEY CLUSTERED 

(

	[MergeId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
CREATE UNIQUE NONCLUSTERED INDEX [CRMContactoUnificacion_UX_MergeCase_ActiveSource] ON [dbo].[CRMContactoUnificacion]

(

	[SourceContactId] ASC

)

WHERE ([Active]=(1))

WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, IGNORE_DUP_KEY = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
ALTER TABLE [dbo].[CRMContactoUnificacion] ADD  CONSTRAINT [CRMContactoUnificacion_DF_MergeCase_Created]  DEFAULT (sysutcdatetime()) FOR [CreatedAt]
GO
ALTER TABLE [dbo].[CRMContactoUnificacion]  WITH CHECK ADD  CONSTRAINT [CRMContactoUnificacion_CK_MergeCase] CHECK  (([SourceContactId]<>[TargetContactId] AND [AppliedCrmRevision]>(0) AND isjson([BeforeJson])=(1) AND left(ltrim([BeforeJson]),(1))=N'{' AND isjson([AppliedJson])=(1) AND left(ltrim([AppliedJson]),(1))=N'{' AND isjson([ChoicesJson])=(1) AND left(ltrim([ChoicesJson]),(1))=N'{' AND ([Active]=(1) AND [UndoneAt] IS NULL AND [UndoBeforeJson] IS NULL AND [UndoAppliedJson] IS NULL OR [Active]=(0) AND [UndoneAt] IS NOT NULL AND [UndoBeforeJson] IS NOT NULL AND [UndoAppliedJson] IS NOT NULL AND isjson([UndoBeforeJson])=(1) AND left(ltrim([UndoBeforeJson]),(1))=N'{' AND isjson([UndoAppliedJson])=(1) AND left(ltrim([UndoAppliedJson]),(1))=N'{')))
GO
ALTER TABLE [dbo].[CRMContactoUnificacion] CHECK CONSTRAINT [CRMContactoUnificacion_CK_MergeCase]
GO
-- crm_merge.Operation -> dbo.CRMUnificacionOperacion
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMUnificacionOperacion](

	[OperationId] [uniqueidentifier] NOT NULL,

	[Revision] [bigint] IDENTITY(1,1) NOT NULL,

	[Action] [varchar](16) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[MergeId] [uniqueidentifier] NULL,

	[SourceContactId] [uniqueidentifier] NOT NULL,

	[TargetContactId] [uniqueidentifier] NOT NULL,

	[PayloadHash] [binary](32) NOT NULL,

	[IdentifiersJson] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Actor] [varchar](32) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[CreatedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMUnificacionOperacion_PK_MergeOperation] PRIMARY KEY NONCLUSTERED 

(

	[OperationId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF),

 CONSTRAINT [CRMUnificacionOperacion_UQ_MergeRevision] UNIQUE CLUSTERED 

(

	[Revision] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
ALTER TABLE [dbo].[CRMUnificacionOperacion] ADD  CONSTRAINT [CRMUnificacionOperacion_DF_MergeOperation_Created]  DEFAULT (sysutcdatetime()) FOR [CreatedAt]
GO
ALTER TABLE [dbo].[CRMUnificacionOperacion]  WITH CHECK ADD  CONSTRAINT [CRMUnificacionOperacion_CK_MergeOperation] CHECK  ((([Action]='identifiers' OR [Action]='undo' OR [Action]='merge') AND [Actor]='local-operator' AND isjson([IdentifiersJson])=(1) AND left(ltrim([IdentifiersJson]),(1))=N'[' AND ([Action]='identifiers' AND [MergeId] IS NULL OR [Action]<>'identifiers' AND [MergeId] IS NOT NULL)))
GO
ALTER TABLE [dbo].[CRMUnificacionOperacion] CHECK CONSTRAINT [CRMUnificacionOperacion_CK_MergeOperation]
GO
-- crm_strategy.EvaluationPlan -> dbo.CRMEstrategiaPlanEvaluacion
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMEstrategiaPlanEvaluacion](

	[PlanId] [uniqueidentifier] NOT NULL,

	[ConversationId] [uniqueidentifier] NOT NULL,

	[Generation] [bigint] NOT NULL,

	[AnalysisRevision] [bigint] NOT NULL,

	[Fingerprint] [char](64) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Binding] [varchar](300) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[SemanticFingerprint] [char](64) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[DocumentJson] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Provider] [varchar](32) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Model] [varchar](200) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[PromptVersion] [varchar](40) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[PolicyRevision] [bigint] NOT NULL,

	[CreatedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMEstrategiaPlanEvaluacion_PK_StrategyPlan] PRIMARY KEY CLUSTERED 

(

	[PlanId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF),

 CONSTRAINT [CRMEstrategiaPlanEvaluacion_UQ_StrategyPlan_Revision] UNIQUE NONCLUSTERED 

(

	[ConversationId] ASC,

	[Generation] ASC,

	[AnalysisRevision] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
ALTER TABLE [dbo].[CRMEstrategiaPlanEvaluacion] ADD  CONSTRAINT [CRMEstrategiaPlanEvaluacion_DF_StrategyPlan_Created]  DEFAULT (sysutcdatetime()) FOR [CreatedAt]
GO
ALTER TABLE [dbo].[CRMEstrategiaPlanEvaluacion]  WITH CHECK ADD  CONSTRAINT [CRMEstrategiaPlanEvaluacion_CK_StrategyPlan] CHECK  (([Generation]>(0) AND [AnalysisRevision]>(0) AND [PolicyRevision]>(0) AND isjson([DocumentJson])=(1) AND left(ltrim([DocumentJson]),(1))=N'{'))
GO
ALTER TABLE [dbo].[CRMEstrategiaPlanEvaluacion] CHECK CONSTRAINT [CRMEstrategiaPlanEvaluacion_CK_StrategyPlan]
GO
-- crm_strategy.Operation -> dbo.CRMEstrategiaOperacion
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMEstrategiaOperacion](

	[OperationId] [uniqueidentifier] NOT NULL,

	[Revision] [bigint] IDENTITY(1,1) NOT NULL,

	[Action] [varchar](20) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[ConversationId] [uniqueidentifier] NOT NULL,

	[PlanId] [uniqueidentifier] NULL,

	[TaskId] [uniqueidentifier] NULL,

	[PayloadHash] [binary](32) NOT NULL,

	[DocumentJson] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Actor] [varchar](32) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[CreatedAt] [datetime2](7) NOT NULL,

 CONSTRAINT [CRMEstrategiaOperacion_PK_StrategyOperation] PRIMARY KEY NONCLUSTERED 

(

	[OperationId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF),

 CONSTRAINT [CRMEstrategiaOperacion_UQ_StrategyRevision] UNIQUE CLUSTERED 

(

	[Revision] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
CREATE UNIQUE NONCLUSTERED INDEX [CRMEstrategiaOperacion_UX_StrategyTaskPlan] ON [dbo].[CRMEstrategiaOperacion]

(

	[PlanId] ASC

)

WHERE ([Action]='task_create')

WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, IGNORE_DUP_KEY = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
ALTER TABLE [dbo].[CRMEstrategiaOperacion] ADD  CONSTRAINT [CRMEstrategiaOperacion_DF_StrategyOperation_Created]  DEFAULT (sysutcdatetime()) FOR [CreatedAt]
GO
ALTER TABLE [dbo].[CRMEstrategiaOperacion]  WITH CHECK ADD  CONSTRAINT [CRMEstrategiaOperacion_CK_StrategyOperation] CHECK  ((isjson([DocumentJson])=(1) AND left(ltrim([DocumentJson]),(1))=N'{' AND ([Action]='task_create' AND [Actor]='automation' AND [PlanId] IS NOT NULL AND [TaskId] IS NOT NULL OR [Action]='feedback' AND [Actor]='local-operator' AND [PlanId] IS NOT NULL AND [TaskId] IS NULL OR ([Action]='pause' OR [Action]='autonomy') AND [Actor]='local-operator' AND [PlanId] IS NULL AND [TaskId] IS NULL)))
GO
ALTER TABLE [dbo].[CRMEstrategiaOperacion] CHECK CONSTRAINT [CRMEstrategiaOperacion_CK_StrategyOperation]
GO
-- crm_strategy.Policy -> dbo.CRMEstrategiaPolitica
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[CRMEstrategiaPolitica](

	[ScopeKey] [varchar](36) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[ConversationId] [uniqueidentifier] NULL,

	[Enabled] [bit] NOT NULL,

 CONSTRAINT [CRMEstrategiaPolitica_PK_StrategyPolicy] PRIMARY KEY CLUSTERED 

(

	[ScopeKey] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
ALTER TABLE [dbo].[CRMEstrategiaPolitica]  WITH CHECK ADD  CONSTRAINT [CRMEstrategiaPolitica_CK_StrategyPolicy] CHECK  (([ScopeKey]='global' AND [ConversationId] IS NULL OR [ConversationId] IS NOT NULL AND [ScopeKey]=lower(CONVERT([varchar](36),[ConversationId]))))
GO
ALTER TABLE [dbo].[CRMEstrategiaPolitica] CHECK CONSTRAINT [CRMEstrategiaPolitica_CK_StrategyPolicy]
GO
-- dbo.ACAcudiente -> dbo.ACAcudiente
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[ACAcudiente](

	[Id_Acudiente] [int] NOT NULL,

	[NombreAcudiente] [varchar](40) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[ApellidosAcudiente] [varchar](30) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Telefono] [varchar](23) COLLATE Modern_Spanish_CI_AS NULL,

	[Celular] [varchar](23) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Mail] [varchar](50) COLLATE Modern_Spanish_CI_AS NULL,

	[Ocupacion] [varchar](50) COLLATE Modern_Spanish_CI_AS NULL,

	[DocumentoA] [varchar](16) COLLATE Modern_Spanish_CI_AS NULL,

 CONSTRAINT [PK_ACAcudiente_1] PRIMARY KEY CLUSTERED 

(

	[Id_Acudiente] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
-- dbo.ACAsignatura -> dbo.ACAsignatura
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[ACAsignatura](

	[Id_Asignatura] [int] NOT NULL,

	[NombreAsignatura] [varchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

 CONSTRAINT [PK_ACAsignatura] PRIMARY KEY CLUSTERED 

(

	[Id_Asignatura] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
-- dbo.ACAsignaturaPlan -> dbo.ACAsignaturaPlan
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[ACAsignaturaPlan](

	[Id_AsignaturaPlan] [int] NOT NULL,

	[Id_Asignatura] [int] NOT NULL,

	[Id_PlanEducativo] [int] NOT NULL,

	[Creditos] [int] NOT NULL,

	[Intensidad] [int] NOT NULL,

	[Nivel] [int] NOT NULL,

	[Id_PlanEvaluativo] [int] NOT NULL,

	[ValorAprobacion] [int] NOT NULL,

	[Inactiva] [bit] NULL,

	[Id_TipoAlternancia] [int] NULL,

 CONSTRAINT [PK_ACAsignaturaPlan] PRIMARY KEY CLUSTERED 

(

	[Id_AsignaturaPlan] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
CREATE UNIQUE NONCLUSTERED INDEX [IX_ACAsignaturaPlan] ON [dbo].[ACAsignaturaPlan]

(

	[Id_PlanEducativo] ASC,

	[Id_Asignatura] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, IGNORE_DUP_KEY = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
-- dbo.ACAspirante -> dbo.ACAspirante
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[ACAspirante](

	[Id_Aspirante] [int] NOT NULL,

	[Id_DocAspirante] [varchar](16) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[TipoId] [tinyint] NOT NULL,

	[NombreAspirante] [varchar](100) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[PrimerApellido] [varchar](30) COLLATE Modern_Spanish_CI_AS NULL,

	[SegundoApellido] [varchar](30) COLLATE Modern_Spanish_CI_AS NULL,

	[Telefono] [varchar](50) COLLATE Modern_Spanish_CI_AS NULL,

	[Celular] [varchar](50) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Mail] [varchar](50) COLLATE Modern_Spanish_CI_AS NULL,

	[Id_PrgOfrecido] [int] NULL,

	[Cnfrmdo] [bit] NOT NULL,

	[FechaRegistro] [smalldatetime] NOT NULL,

	[Id_Periodo] [int] NULL,

	[Interna] [bit] NULL,

 CONSTRAINT [PK_ACAspirante] PRIMARY KEY CLUSTERED 

(

	[Id_Aspirante] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
SET ANSI_PADDING ON
GO
CREATE UNIQUE NONCLUSTERED INDEX [NoDuplicate] ON [dbo].[ACAspirante]

(

	[Id_DocAspirante] ASC,

	[Id_PrgOfrecido] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, IGNORE_DUP_KEY = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
ALTER TABLE [dbo].[ACAspirante] ADD  CONSTRAINT [DF_ACAspirante_FechaRegistro]  DEFAULT (getdate()) FOR [FechaRegistro]
GO
-- dbo.ACDetalleJornada -> dbo.ACDetalleJornada
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[ACDetalleJornada](

	[Id_DetalleJornada] [int] NOT NULL,

	[Id_Jornada] [int] NOT NULL,

	[Id_PrgOfrecido] [int] NOT NULL,

 CONSTRAINT [PK_ACDetalleJornada] PRIMARY KEY NONCLUSTERED 

(

	[Id_DetalleJornada] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF),

 CONSTRAINT [ControlDJ] UNIQUE CLUSTERED 

(

	[Id_DetalleJornada] ASC,

	[Id_Jornada] ASC,

	[Id_PrgOfrecido] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
-- dbo.ACEscuela -> dbo.ACEscuela
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[ACEscuela](

	[Id_Escuela] [int] NOT NULL,

	[NomEsla] [varchar](100) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Id_CstvoEmpld] [int] NULL,

	[Correo] [nvarchar](max) COLLATE Modern_Spanish_CI_AS NULL,

	[UrlEscuela] [nvarchar](100) COLLATE Modern_Spanish_CI_AS NULL,

 CONSTRAINT [PK_ACEscuela] PRIMARY KEY CLUSTERED 

(

	[Id_Escuela] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
-- dbo.ACEstadoSeguimiento -> dbo.ACEstadoSeguimiento
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[ACEstadoSeguimiento](

	[Id_EstadoSeguimiento] [int] NOT NULL,

	[Estado] [varchar](50) COLLATE Modern_Spanish_CI_AS NOT NULL,

 CONSTRAINT [PK_ACEstadoSeguimiento] PRIMARY KEY CLUSTERED 

(

	[Id_EstadoSeguimiento] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
-- dbo.ACJornada -> dbo.ACJornada
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[ACJornada](

	[Id_Jornada] [int] NOT NULL,

	[DetalleJornada] [varchar](15) COLLATE Modern_Spanish_CI_AS NOT NULL,

 CONSTRAINT [PK_ACJornada] PRIMARY KEY CLUSTERED 

(

	[Id_Jornada] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
-- dbo.ACModalidad -> dbo.ACModalidad
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[ACModalidad](

	[Id_Modalidad] [int] NOT NULL,

	[Modalidad] [varchar](20) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[DescripcionMod] [varchar](80) COLLATE Modern_Spanish_CI_AS NULL,

 CONSTRAINT [PK_ACModalidad] PRIMARY KEY CLUSTERED 

(

	[Id_Modalidad] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
-- dbo.ACPlanEducativo -> dbo.ACPlanEducativo
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[ACPlanEducativo](

	[Id_PlanEducativo] [int] NOT NULL,

	[NombrePLan] [varchar](80) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Id_Programa] [int] NOT NULL,

	[Id_Periodo] [int] NOT NULL,

	[Vigente] [bit] NOT NULL,

 CONSTRAINT [PK_ACPlanEducativo] PRIMARY KEY CLUSTERED 

(

	[Id_PlanEducativo] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
-- dbo.ACPlanEvaluativo -> dbo.ACPlanEvaluativo
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[ACPlanEvaluativo](

	[Id_PlanEvaluativo] [int] NOT NULL,

	[NombrePlanEvl] [varchar](18) COLLATE Modern_Spanish_CI_AS NOT NULL,

 CONSTRAINT [PK_ACPlanEvaluativo] PRIMARY KEY CLUSTERED 

(

	[Id_PlanEvaluativo] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
-- dbo.ACProgramaOfrecido -> dbo.ACProgramaOfrecido
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[ACProgramaOfrecido](

	[Id_PrgOfrecido] [int] NOT NULL,

	[Id_Programa] [int] NOT NULL,

	[Id_Periodo] [int] NOT NULL,

	[Id_Plan] [int] NULL,

 CONSTRAINT [PK_ACProgramaOfrecido] PRIMARY KEY CLUSTERED 

(

	[Id_PrgOfrecido] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF),

 CONSTRAINT [IX_ACProgramaOfrecido_1] UNIQUE NONCLUSTERED 

(

	[Id_Periodo] ASC,

	[Id_Programa] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
-- dbo.ACProgramas -> dbo.ACProgramas
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[ACProgramas](

	[Id_Programa] [int] NOT NULL,

	[CodigoPrograma] [varchar](10) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[NombrePrograma] [varchar](200) COLLATE Modern_Spanish_CI_AS NULL,

	[Id_Escuela] [int] NOT NULL,

	[Id_Modalidad] [int] NOT NULL,

	[fecha] [date] NULL,

	[Semestres] [int] NULL,

	[Id_Jornada] [int] NULL,

 CONSTRAINT [PK_ACProgramas] PRIMARY KEY CLUSTERED 

(

	[Id_Programa] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
-- dbo.ACSeguimiento -> dbo.ACSeguimiento
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[ACSeguimiento](

	[Id_Seguimiento] [int] NOT NULL,

	[Id_Aspirante] [int] NOT NULL,

	[Observacion] [varchar](max) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[FechaSeguimiento] [date] NULL,

	[FechaProxSeguimiento] [date] NULL,

	[Estado] [int] NOT NULL,

	[Usuario] [varchar](max) COLLATE Modern_Spanish_CI_AS NULL,

	[Hora] [varchar](10) COLLATE Modern_Spanish_CI_AS NULL,

	[Agenda] [bit] NULL,

 CONSTRAINT [PK_ACSeguimiento] PRIMARY KEY CLUSTERED 

(

	[Id_Seguimiento] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
-- dbo.ACTipoAlternancia -> dbo.ACTipoAlternancia
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[ACTipoAlternancia](

	[Id_TipoAlternancia] [int] NOT NULL,

	[Tipo] [varchar](100) COLLATE Modern_Spanish_CI_AS NULL,

	[Descripcion] [varchar](200) COLLATE Modern_Spanish_CI_AS NULL,

 CONSTRAINT [PK_ACTipoAlternancia] PRIMARY KEY CLUSTERED 

(

	[Id_TipoAlternancia] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
-- dbo.AFDetallePlanPago -> dbo.AFDetallePlanPago
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[AFDetallePlanPago](

	[Id_DetallePLan] [int] NOT NULL,

	[Id_Plan] [int] NOT NULL,

	[Concepto] [varchar](15) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Porcentaje] [float] NULL,

	[Valor] [int] NULL,

	[ValorExtr] [int] NULL,

	[FechaPago] [date] NOT NULL,

 CONSTRAINT [PK_AFDetallePlanPago] PRIMARY KEY CLUSTERED 

(

	[Id_DetallePLan] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
-- dbo.AFPlanes -> dbo.AFPlanes
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[AFPlanes](

	[Id_Plan] [int] NOT NULL,

	[NombrePlan] [varchar](80) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[TipoPlan] [varchar](80) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[ValorOrdinaria] [int] NULL,

	[ValorExtradinaria] [int] NULL,

	[ValorDescuento] [int] NULL,

	[Id_Periodo] [int] NULL,

 CONSTRAINT [PK_AFPlanes] PRIMARY KEY NONCLUSTERED 

(

	[Id_Plan] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF),

 CONSTRAINT [PlanesControl] UNIQUE CLUSTERED 

(

	[Id_Plan] ASC,

	[NombrePlan] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
-- dbo.AFTarifas -> dbo.AFTarifas
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[AFTarifas](

	[Id_Tarifa] [int] NOT NULL,

	[ValorSmtrOr] [int] NOT NULL,

	[ValorSmtrEx] [int] NOT NULL,

	[Semestre] [int] NOT NULL,

	[Id_Programa] [int] NOT NULL,

	[Id_Periodo] [int] NOT NULL,

	[Id_Plan] [int] NULL,

 CONSTRAINT [PK_AFTarifas] PRIMARY KEY CLUSTERED 

(

	[Id_Tarifa] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
CREATE UNIQUE NONCLUSTERED INDEX [AFTarifasControl] ON [dbo].[AFTarifas]

(

	[Semestre] ASC,

	[Id_Programa] ASC,

	[Id_Periodo] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, IGNORE_DUP_KEY = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
-- dbo.GECargoEmpresa -> dbo.GECargoEmpresa
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[GECargoEmpresa](

	[CdgoCrgo] [smallint] NOT NULL,

	[NmbreCrgo] [varchar](55) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Intrno] [bit] NULL,

 CONSTRAINT [PK_GECargoEmpresa] PRIMARY KEY CLUSTERED 

(

	[CdgoCrgo] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
-- dbo.GEEmpleado -> dbo.GEEmpleado
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[GEEmpleado](

	[CnsctvoEmpldo] [int] NOT NULL,

	[Idntfccion] [varchar](50) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[CdgoTpoIdntdad] [tinyint] NOT NULL,

	[NmbrePrsna] [varchar](20) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[AplldosPrsna] [varchar](30) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[CdgoArea] [smallint] NOT NULL,

	[CdgoCrgo] [smallint] NOT NULL,

	[UsrioSstma] [varchar](15) COLLATE Modern_Spanish_CI_AS NULL,

	[Extnsion] [smallint] NULL,

	[IPComun] [varchar](15) COLLATE Modern_Spanish_CI_AS NULL,

	[FchaIngrso] [smalldatetime] NULL,

	[FchaSlda] [smalldatetime] NULL,

	[Actvo] [bit] NOT NULL,

	[CdgoEmprsaLbra] [tinyint] NOT NULL,

	[FchaActlzcionPwd] [smalldatetime] NULL,

	[PwdNncaCdca] [bit] NOT NULL,

	[FchaVncmntoPwd] [smalldatetime] NULL,

	[FchaVgnciaDsde] [smalldatetime] NULL,

	[FchaVgnciaHsta] [smalldatetime] NULL,

	[CrreoEmpldo] [varchar](50) COLLATE Modern_Spanish_CI_AS NULL,

	[FchaDsctvcion] [smalldatetime] NULL,

	[Fto] [image] NULL,

	[ImgenFndo] [int] NULL,

	[Estadocivil] [varchar](50) COLLATE Modern_Spanish_CI_AS NULL,

	[Nomconyuge] [varchar](50) COLLATE Modern_Spanish_CI_AS NULL,

	[ApConyuge] [varchar](50) COLLATE Modern_Spanish_CI_AS NULL,

 CONSTRAINT [PK_GEEmpleado2] PRIMARY KEY CLUSTERED 

(

	[CnsctvoEmpldo] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
-- dbo.GEEmpresa -> dbo.GEEmpresa
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[GEEmpresa](

	[CdgoEmprsa] [tinyint] NOT NULL,

	[NmbreEmprsa] [varchar](35) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[NIT] [decimal](19, 0) NOT NULL,

	[CdgoPblcion] [int] NOT NULL,

	[MnmoVlorFctra] [money] NOT NULL,

	[CdgoTpoMndaLcal] [smallint] NOT NULL,

	[Logo] [image] NULL,

	[ClrMnuFndo] [int] NULL,

	[ClrMnuTxto] [int] NULL,

	[DireccionEmpresa] [varchar](40) COLLATE Modern_Spanish_CI_AS NULL,

	[TelefonosEmpresa] [varchar](40) COLLATE Modern_Spanish_CI_AS NULL,

	[HttpEmpresa] [varchar](40) COLLATE Modern_Spanish_CI_AS NULL,

	[NmbreCrto] [varchar](10) COLLATE Modern_Spanish_CI_AS NULL,

	[Prncpal] [bit] NULL,

	[LogoDocumento] [image] NULL,

	[CrtfcdoIso] [bit] NULL,

	[AlcnceIso] [varchar](255) COLLATE Modern_Spanish_CI_AS NULL,

	[TpoImprsion] [varchar](3) COLLATE Modern_Spanish_CI_AS NULL,

	[URLPgnaWeb] [varchar](50) COLLATE Modern_Spanish_CI_AS NULL,

	[Dmnio] [varchar](50) COLLATE Modern_Spanish_CI_AS NULL,

 CONSTRAINT [PK_PAControl] PRIMARY KEY CLUSTERED 

(

	[CdgoEmprsa] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
-- dbo.GEEstados -> dbo.GEEstados
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[GEEstados](

	[Id_Estado] [int] NOT NULL,

	[NmbreEstdo] [varchar](20) COLLATE Modern_Spanish_CI_AS NOT NULL,

 CONSTRAINT [PK_GEEstados] PRIMARY KEY CLUSTERED 

(

	[Id_Estado] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
-- dbo.GEEstudiante -> dbo.GEEstudiante
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[GEEstudiante](

	[Id_Estudiante] [int] NOT NULL,

	[Id_DocEstudiante] [varchar](16) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[TipoId] [tinyint] NOT NULL,

	[Expedida] [int] NULL,

	[Nombres] [varchar](40) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[PrimerApellido] [varchar](30) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[SegundoApellido] [varchar](30) COLLATE Modern_Spanish_CI_AS NULL,

	[Id_Genero] [int] NOT NULL,

	[EstadoCivil] [varchar](14) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Direccion] [varchar](80) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Id_Poblacion] [int] NULL,

	[Telefono] [varchar](23) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Celular] [varchar](23) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Mail] [varchar](50) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[FechaNacimento] [date] NOT NULL,

	[CiudadNacimiento] [varchar](50) COLLATE Modern_Spanish_CI_AS NULL,

	[EstadoMtla] [int] NULL,

	[GrupoSanguineo] [varchar](2) COLLATE Modern_Spanish_CI_AS NULL,

	[FactorRh] [varchar](1) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Id_Acudiente] [int] NULL,

	[Id_PrgOfrecido] [int] NOT NULL,

	[Estrato] [int] NULL,

	[Articulacion] [varchar](80) COLLATE Modern_Spanish_CI_AS NULL,

 CONSTRAINT [PK_GEEstudiante] PRIMARY KEY CLUSTERED 

(

	[Id_Estudiante] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
SET ANSI_PADDING ON
GO
CREATE UNIQUE NONCLUSTERED INDEX [DobleMat] ON [dbo].[GEEstudiante]

(

	[Id_DocEstudiante] ASC,

	[Id_PrgOfrecido] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, IGNORE_DUP_KEY = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
-- dbo.GEGenero -> dbo.GEGenero
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[GEGenero](

	[Id_Genero] [int] IDENTITY(1,1) NOT NULL,

	[Genero] [varchar](20) COLLATE Modern_Spanish_CI_AS NULL,

 CONSTRAINT [PK_GEGenero] PRIMARY KEY CLUSTERED 

(

	[Id_Genero] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
-- dbo.GEImgenProg -> dbo.GEImgenProg
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[GEImgenProg](

	[Id_ImgenPrograma] [int] NOT NULL,

	[Id_TipoImagen] [int] NOT NULL,

	[Id_Programa] [int] NOT NULL,

 CONSTRAINT [PK_GEImgenProg] PRIMARY KEY CLUSTERED 

(

	[Id_ImgenPrograma] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
CREATE NONCLUSTERED INDEX [id_control] ON [dbo].[GEImgenProg]

(

	[Id_TipoImagen] ASC,

	[Id_Programa] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)
GO
-- dbo.GEPais -> dbo.GEPais
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[GEPais](

	[Id_Pais] [int] NOT NULL,

	[NmbrePais] [varchar](50) COLLATE Modern_Spanish_CI_AS NOT NULL,

 CONSTRAINT [PK_Pais] PRIMARY KEY CLUSTERED 

(

	[Id_Pais] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
-- dbo.GEPeriodo -> dbo.GEPeriodo
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[GEPeriodo](

	[Id_Periodo] [int] NOT NULL,

	[Periodo] [varchar](20) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[FechaInicio] [date] NOT NULL,

	[FechaFinal] [date] NOT NULL,

	[EstadoPeriodo] [bit] NOT NULL,

 CONSTRAINT [PK_GEPeriodo] PRIMARY KEY CLUSTERED 

(

	[Id_Periodo] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
-- dbo.GEPoblacion -> dbo.GEPoblacion
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[GEPoblacion](

	[Id_Poblacion] [int] NOT NULL,

	[Nmbre] [varchar](40) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Id_Estado] [int] NOT NULL,

	[Id_Pais] [int] NULL,

 CONSTRAINT [PK_GEPoblacion] PRIMARY KEY CLUSTERED 

(

	[Id_Poblacion] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
-- dbo.GETipoIdentidad -> dbo.GETipoIdentidad
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[GETipoIdentidad](

	[TipoId] [tinyint] NOT NULL,

	[NmbreTpoIdntdad] [varchar](25) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Abrvtra] [varchar](5) COLLATE Modern_Spanish_CI_AS NOT NULL,

 CONSTRAINT [PK_GETipoIdentidad] PRIMARY KEY CLUSTERED 

(

	[TipoId] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
-- dbo.GETipoImagen -> dbo.GETipoImagen
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[GETipoImagen](

	[Id_TipoImagen] [int] NOT NULL,

	[TipoImagen] [varchar](40) COLLATE Modern_Spanish_CI_AS NOT NULL,

	[Descripcion] [varchar](150) COLLATE Modern_Spanish_CI_AS NULL,

	[Estado] [bit] NULL,

 CONSTRAINT [PK_GETipoImagen] PRIMARY KEY CLUSTERED 

(

	[Id_TipoImagen] ASC

)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF)

)
GO
SET ANSI_PADDING ON
GO
-- Foreign keys are emitted after every referenced table exists.
-- crm.Conversation: FK_Conversation_Contact
ALTER TABLE [dbo].[CRMConversacion]  WITH CHECK ADD  CONSTRAINT [CRMConversacion_FK_Conversation_Contact] FOREIGN KEY([ContactId])

REFERENCES [dbo].[CRMContacto] ([ContactId])
GO
ALTER TABLE [dbo].[CRMConversacion] CHECK CONSTRAINT [CRMConversacion_FK_Conversation_Contact]
GO
-- crm.Message: FK_Message_Conversation
ALTER TABLE [dbo].[CRMMensaje]  WITH CHECK ADD  CONSTRAINT [CRMMensaje_FK_Message_Conversation] FOREIGN KEY([ConversationId])

REFERENCES [dbo].[CRMConversacion] ([ConversationId])
GO
ALTER TABLE [dbo].[CRMMensaje] CHECK CONSTRAINT [CRMMensaje_FK_Message_Conversation]
GO
-- crm.Operation: FK_Operation_Contact
ALTER TABLE [dbo].[CRMOperacion]  WITH CHECK ADD  CONSTRAINT [CRMOperacion_FK_Operation_Contact] FOREIGN KEY([ContactId])

REFERENCES [dbo].[CRMContacto] ([ContactId])
GO
ALTER TABLE [dbo].[CRMOperacion] CHECK CONSTRAINT [CRMOperacion_FK_Operation_Contact]
GO
-- crm.Operation: FK_Operation_Conversation
ALTER TABLE [dbo].[CRMOperacion]  WITH CHECK ADD  CONSTRAINT [CRMOperacion_FK_Operation_Conversation] FOREIGN KEY([ConversationId])

REFERENCES [dbo].[CRMConversacion] ([ConversationId])
GO
ALTER TABLE [dbo].[CRMOperacion] CHECK CONSTRAINT [CRMOperacion_FK_Operation_Conversation]
GO
-- crm.Operation: FK_Operation_Message
ALTER TABLE [dbo].[CRMOperacion]  WITH CHECK ADD  CONSTRAINT [CRMOperacion_FK_Operation_Message] FOREIGN KEY([MessageId])

REFERENCES [dbo].[CRMMensaje] ([MessageId])
GO
ALTER TABLE [dbo].[CRMOperacion] CHECK CONSTRAINT [CRMOperacion_FK_Operation_Message]
GO
-- crm_admissions.Followup: FK_Followup_Case
ALTER TABLE [dbo].[CRMAdmisionSeguimiento]  WITH CHECK ADD  CONSTRAINT [CRMAdmisionSeguimiento_FK_Followup_Case] FOREIGN KEY([CaseId])

REFERENCES [dbo].[CRMAdmision] ([CaseId])
GO
ALTER TABLE [dbo].[CRMAdmisionSeguimiento] CHECK CONSTRAINT [CRMAdmisionSeguimiento_FK_Followup_Case]
GO
-- crm_admissions.Operation: FK_AdmissionOperation_Followup
ALTER TABLE [dbo].[CRMAdmisionOperacion]  WITH CHECK ADD  CONSTRAINT [CRMAdmisionOperacion_FK_AdmissionOperation_Followup] FOREIGN KEY([FollowupId])

REFERENCES [dbo].[CRMAdmisionSeguimiento] ([FollowupId])
GO
ALTER TABLE [dbo].[CRMAdmisionOperacion] CHECK CONSTRAINT [CRMAdmisionOperacion_FK_AdmissionOperation_Followup]
GO
-- crm_agents.Assignment: FK__Assignmen__Conve__3846C6FF
ALTER TABLE [dbo].[CRMAgenteAsignacion]  WITH CHECK ADD  CONSTRAINT [CRMAgenteAsignacion_FK__Assignmen__Conve__3846C6FF] FOREIGN KEY([ConversationId])

REFERENCES [dbo].[CRMConversacion] ([ConversationId])
GO
ALTER TABLE [dbo].[CRMAgenteAsignacion] CHECK CONSTRAINT [CRMAgenteAsignacion_FK__Assignmen__Conve__3846C6FF]
GO
-- crm_agents.Assignment: FK__Assignment__3B2333AA
ALTER TABLE [dbo].[CRMAgenteAsignacion]  WITH CHECK ADD  CONSTRAINT [CRMAgenteAsignacion_FK__Assignment__3B2333AA] FOREIGN KEY([ContextId], [ConversationId])

REFERENCES [dbo].[CRMAgenteContexto] ([ContextId], [ConversationId])
GO
ALTER TABLE [dbo].[CRMAgenteAsignacion] CHECK CONSTRAINT [CRMAgenteAsignacion_FK__Assignment__3B2333AA]
GO
-- crm_agents.Context: FK__Context__2DC9388C
ALTER TABLE [dbo].[CRMAgenteContexto]  WITH CHECK ADD  CONSTRAINT [CRMAgenteContexto_FK__Context__2DC9388C] FOREIGN KEY([StageId], [ProgramId])

REFERENCES [dbo].[CRMAgenteEtapa] ([StageId], [ProgramId])
GO
ALTER TABLE [dbo].[CRMAgenteContexto] CHECK CONSTRAINT [CRMAgenteContexto_FK__Context__2DC9388C]
GO
-- crm_agents.Context: FK__Context__Convers__2904836F
ALTER TABLE [dbo].[CRMAgenteContexto]  WITH CHECK ADD  CONSTRAINT [CRMAgenteContexto_FK__Context__Convers__2904836F] FOREIGN KEY([ConversationId])

REFERENCES [dbo].[CRMConversacion] ([ConversationId])
GO
ALTER TABLE [dbo].[CRMAgenteContexto] CHECK CONSTRAINT [CRMAgenteContexto_FK__Context__Convers__2904836F]
GO
-- crm_agents.Execution: FK__Execution__Agent__4C4DBFAC
ALTER TABLE [dbo].[CRMAgenteEjecucion]  WITH CHECK ADD  CONSTRAINT [CRMAgenteEjecucion_FK__Execution__Agent__4C4DBFAC] FOREIGN KEY([AgentId])

REFERENCES [dbo].[CRMAgentePerfil] ([AgentId])
GO
ALTER TABLE [dbo].[CRMAgenteEjecucion] CHECK CONSTRAINT [CRMAgenteEjecucion_FK__Execution__Agent__4C4DBFAC]
GO
-- crm_agents.Execution: FK__Execution__Conve__4E36081E
ALTER TABLE [dbo].[CRMAgenteEjecucion]  WITH CHECK ADD  CONSTRAINT [CRMAgenteEjecucion_FK__Execution__Conve__4E36081E] FOREIGN KEY([ConversationId])

REFERENCES [dbo].[CRMConversacion] ([ConversationId])
GO
ALTER TABLE [dbo].[CRMAgenteEjecucion] CHECK CONSTRAINT [CRMAgenteEjecucion_FK__Execution__Conve__4E36081E]
GO
-- crm_agents.Execution: FK__Execution__Reque__4B599B73
ALTER TABLE [dbo].[CRMAgenteEjecucion]  WITH CHECK ADD  CONSTRAINT [CRMAgenteEjecucion_FK__Execution__Reque__4B599B73] FOREIGN KEY([RequestId])

REFERENCES [dbo].[CRMAgenteConsumo] ([RequestId])
GO
ALTER TABLE [dbo].[CRMAgenteEjecucion] CHECK CONSTRAINT [CRMAgenteEjecucion_FK__Execution__Reque__4B599B73]
GO
-- crm_agents.Profile: FK__Profile__225785E0
ALTER TABLE [dbo].[CRMAgentePerfil]  WITH CHECK ADD  CONSTRAINT [CRMAgentePerfil_FK__Profile__225785E0] FOREIGN KEY([StageId], [ProgramId])

REFERENCES [dbo].[CRMAgenteEtapa] ([StageId], [ProgramId])
GO
ALTER TABLE [dbo].[CRMAgentePerfil] CHECK CONSTRAINT [CRMAgentePerfil_FK__Profile__225785E0]
GO
-- crm_agents.Profile: FK__Profile__AgentId__18CE1BA6
ALTER TABLE [dbo].[CRMAgentePerfil]  WITH CHECK ADD  CONSTRAINT [CRMAgentePerfil_FK__Profile__AgentId__18CE1BA6] FOREIGN KEY([AgentId])

REFERENCES [dbo].[CRMBandejaAgente] ([AgentId])
GO
ALTER TABLE [dbo].[CRMAgentePerfil] CHECK CONSTRAINT [CRMAgentePerfil_FK__Profile__AgentId__18CE1BA6]
GO
-- crm_agents.Profile: FK__Profile__ParentI__1AB66418
ALTER TABLE [dbo].[CRMAgentePerfil]  WITH CHECK ADD  CONSTRAINT [CRMAgentePerfil_FK__Profile__ParentI__1AB66418] FOREIGN KEY([ParentId])

REFERENCES [dbo].[CRMAgentePerfil] ([AgentId])
GO
ALTER TABLE [dbo].[CRMAgentePerfil] CHECK CONSTRAINT [CRMAgentePerfil_FK__Profile__ParentI__1AB66418]
GO
-- crm_agents.SourceScope: FK__SourceSco__Docum__3199C970
ALTER TABLE [dbo].[CRMAgenteFuenteAlcance]  WITH CHECK ADD  CONSTRAINT [CRMAgenteFuenteAlcance_FK__SourceSco__Docum__3199C970] FOREIGN KEY([DocumentId])

REFERENCES [dbo].[CRMConocimientoDocumento] ([DocumentId])
GO
ALTER TABLE [dbo].[CRMAgenteFuenteAlcance] CHECK CONSTRAINT [CRMAgenteFuenteAlcance_FK__SourceSco__Docum__3199C970]
GO
-- crm_agents.SourceScope: FK__SourceScope__3476361B
ALTER TABLE [dbo].[CRMAgenteFuenteAlcance]  WITH CHECK ADD  CONSTRAINT [CRMAgenteFuenteAlcance_FK__SourceScope__3476361B] FOREIGN KEY([StageId], [ProgramId])

REFERENCES [dbo].[CRMAgenteEtapa] ([StageId], [ProgramId])
GO
ALTER TABLE [dbo].[CRMAgenteFuenteAlcance] CHECK CONSTRAINT [CRMAgenteFuenteAlcance_FK__SourceScope__3476361B]
GO
-- crm_agents.Usage: FK__Usage__AgentId__43B879AB
ALTER TABLE [dbo].[CRMAgenteConsumo]  WITH CHECK ADD  CONSTRAINT [CRMAgenteConsumo_FK__Usage__AgentId__43B879AB] FOREIGN KEY([AgentId])

REFERENCES [dbo].[CRMAgentePerfil] ([AgentId])
GO
ALTER TABLE [dbo].[CRMAgenteConsumo] CHECK CONSTRAINT [CRMAgenteConsumo_FK__Usage__AgentId__43B879AB]
GO
-- crm_ai.KnowledgeChunk: FK__Knowledge__Docum__6D24A392
ALTER TABLE [dbo].[CRMConocimientoFragmento]  WITH CHECK ADD  CONSTRAINT [CRMConocimientoFragmento_FK__Knowledge__Docum__6D24A392] FOREIGN KEY([DocumentId])

REFERENCES [dbo].[CRMConocimientoDocumento] ([DocumentId])
GO
ALTER TABLE [dbo].[CRMConocimientoFragmento] CHECK CONSTRAINT [CRMConocimientoFragmento_FK__Knowledge__Docum__6D24A392]
GO
-- crm_ai.KnowledgeTerm: FK__Knowledge__Chunk__7001103D
ALTER TABLE [dbo].[CRMConocimientoTermino]  WITH CHECK ADD  CONSTRAINT [CRMConocimientoTermino_FK__Knowledge__Chunk__7001103D] FOREIGN KEY([ChunkId])

REFERENCES [dbo].[CRMConocimientoFragmento] ([ChunkId])
GO
ALTER TABLE [dbo].[CRMConocimientoTermino] CHECK CONSTRAINT [CRMConocimientoTermino_FK__Knowledge__Chunk__7001103D]
GO
-- crm_ai.ProspectMemory: FK__ProspectM__Conve__73D1A121
ALTER TABLE [dbo].[CRMProspectoMemoria]  WITH CHECK ADD  CONSTRAINT [CRMProspectoMemoria_FK__ProspectM__Conve__73D1A121] FOREIGN KEY([ConversationId])

REFERENCES [dbo].[CRMConversacion] ([ConversationId])
GO
ALTER TABLE [dbo].[CRMProspectoMemoria] CHECK CONSTRAINT [CRMProspectoMemoria_FK__ProspectM__Conve__73D1A121]
GO
-- crm_ai.ResponseJob: FK__ResponseJ__Conve__7D5B0B5B
ALTER TABLE [dbo].[CRMRespuestaTrabajo]  WITH CHECK ADD  CONSTRAINT [CRMRespuestaTrabajo_FK__ResponseJ__Conve__7D5B0B5B] FOREIGN KEY([ConversationId])

REFERENCES [dbo].[CRMConversacion] ([ConversationId])
GO
ALTER TABLE [dbo].[CRMRespuestaTrabajo] CHECK CONSTRAINT [CRMRespuestaTrabajo_FK__ResponseJ__Conve__7D5B0B5B]
GO
-- crm_ai.ResponseJob: FK__ResponseJ__Ident__7E4F2F94
ALTER TABLE [dbo].[CRMRespuestaTrabajo]  WITH CHECK ADD  CONSTRAINT [CRMRespuestaTrabajo_FK__ResponseJ__Ident__7E4F2F94] FOREIGN KEY([IdentityId])

REFERENCES [dbo].[CRMIdentidadExterna] ([IdentityId])
GO
ALTER TABLE [dbo].[CRMRespuestaTrabajo] CHECK CONSTRAINT [CRMRespuestaTrabajo_FK__ResponseJ__Ident__7E4F2F94]
GO
-- crm_ai.ResponseJob: FK__ResponseJ__Messa__7C66E722
ALTER TABLE [dbo].[CRMRespuestaTrabajo]  WITH CHECK ADD  CONSTRAINT [CRMRespuestaTrabajo_FK__ResponseJ__Messa__7C66E722] FOREIGN KEY([MessageId])

REFERENCES [dbo].[CRMMensaje] ([MessageId])
GO
ALTER TABLE [dbo].[CRMRespuestaTrabajo] CHECK CONSTRAINT [CRMRespuestaTrabajo_FK__ResponseJ__Messa__7C66E722]
GO
-- crm_ai.ResponseJob: FK__ResponseJ__Respo__040808EA
ALTER TABLE [dbo].[CRMRespuestaTrabajo]  WITH CHECK ADD  CONSTRAINT [CRMRespuestaTrabajo_FK__ResponseJ__Respo__040808EA] FOREIGN KEY([ResponseMessageId])

REFERENCES [dbo].[CRMMensaje] ([MessageId])
GO
ALTER TABLE [dbo].[CRMRespuestaTrabajo] CHECK CONSTRAINT [CRMRespuestaTrabajo_FK__ResponseJ__Respo__040808EA]
GO
-- crm_ai.ResponseJob: FK__ResponseJ__TaskI__04FC2D23
ALTER TABLE [dbo].[CRMRespuestaTrabajo]  WITH CHECK ADD  CONSTRAINT [CRMRespuestaTrabajo_FK__ResponseJ__TaskI__04FC2D23] FOREIGN KEY([TaskId])

REFERENCES [dbo].[CRMBandejaTarea] ([TaskId])
GO
ALTER TABLE [dbo].[CRMRespuestaTrabajo] CHECK CONSTRAINT [CRMRespuestaTrabajo_FK__ResponseJ__TaskI__04FC2D23]
GO
-- crm_analysis.Attempt: FK_AnalysisAttempt_Conversation
ALTER TABLE [dbo].[CRMAnalisisIntento]  WITH CHECK ADD  CONSTRAINT [CRMAnalisisIntento_FK_AnalysisAttempt_Conversation] FOREIGN KEY([ConversationId])

REFERENCES [dbo].[CRMConversacion] ([ConversationId])
GO
ALTER TABLE [dbo].[CRMAnalisisIntento] CHECK CONSTRAINT [CRMAnalisisIntento_FK_AnalysisAttempt_Conversation]
GO
-- crm_analysis.ConversationState: FK_AnalysisState_Conversation
ALTER TABLE [dbo].[CRMAnalisisConversacionEstado]  WITH CHECK ADD  CONSTRAINT [CRMAnalisisConversacionEstado_FK_AnalysisState_Conversation] FOREIGN KEY([ConversationId])

REFERENCES [dbo].[CRMConversacion] ([ConversationId])
GO
ALTER TABLE [dbo].[CRMAnalisisConversacionEstado] CHECK CONSTRAINT [CRMAnalisisConversacionEstado_FK_AnalysisState_Conversation]
GO
-- crm_analysis.Feedback: FK_AnalysisFeedback_Conversation
ALTER TABLE [dbo].[CRMAnalisisEvaluacionHumana]  WITH CHECK ADD  CONSTRAINT [CRMAnalisisEvaluacionHumana_FK_AnalysisFeedback_Conversation] FOREIGN KEY([ConversationId])

REFERENCES [dbo].[CRMConversacion] ([ConversationId])
GO
ALTER TABLE [dbo].[CRMAnalisisEvaluacionHumana] CHECK CONSTRAINT [CRMAnalisisEvaluacionHumana_FK_AnalysisFeedback_Conversation]
GO
-- crm_analysis.Receipt: FK_AnalysisReceipt_Conversation
ALTER TABLE [dbo].[CRMAnalisisRecepcion]  WITH CHECK ADD  CONSTRAINT [CRMAnalisisRecepcion_FK_AnalysisReceipt_Conversation] FOREIGN KEY([ConversationId])

REFERENCES [dbo].[CRMConversacion] ([ConversationId])
GO
ALTER TABLE [dbo].[CRMAnalisisRecepcion] CHECK CONSTRAINT [CRMAnalisisRecepcion_FK_AnalysisReceipt_Conversation]
GO
-- crm_analysis.Receipt: FK_AnalysisReceipt_Event
ALTER TABLE [dbo].[CRMAnalisisRecepcion]  WITH CHECK ADD  CONSTRAINT [CRMAnalisisRecepcion_FK_AnalysisReceipt_Event] FOREIGN KEY([EventId])

REFERENCES [dbo].[CRMConversacionEvento] ([EventId])
GO
ALTER TABLE [dbo].[CRMAnalisisRecepcion] CHECK CONSTRAINT [CRMAnalisisRecepcion_FK_AnalysisReceipt_Event]
GO
-- crm_channels.ConversationControl: FK__Conversat__Conve__3D759070
ALTER TABLE [dbo].[CRMConversacionControl]  WITH CHECK ADD  CONSTRAINT [CRMConversacionControl_FK__Conversat__Conve__3D759070] FOREIGN KEY([ConversationId])

REFERENCES [dbo].[CRMConversacion] ([ConversationId])
GO
ALTER TABLE [dbo].[CRMConversacionControl] CHECK CONSTRAINT [CRMConversacionControl_FK__Conversat__Conve__3D759070]
GO
-- crm_channels.ConversationProfile: FK__Conversat__Conve__37BCB71A
ALTER TABLE [dbo].[CRMConversacionPerfil]  WITH CHECK ADD  CONSTRAINT [CRMConversacionPerfil_FK__Conversat__Conve__37BCB71A] FOREIGN KEY([ConversationId])

REFERENCES [dbo].[CRMConversacion] ([ConversationId])
GO
ALTER TABLE [dbo].[CRMConversacionPerfil] CHECK CONSTRAINT [CRMConversacionPerfil_FK__Conversat__Conve__37BCB71A]
GO
-- crm_channels.Credential: FK__Credentia__Chann__7BA7CD13
ALTER TABLE [dbo].[CRMCanalCredencial]  WITH CHECK ADD  CONSTRAINT [CRMCanalCredencial_FK__Credentia__Chann__7BA7CD13] FOREIGN KEY([Channel])

REFERENCES [dbo].[CRMCanalCuenta] ([Channel])
GO
ALTER TABLE [dbo].[CRMCanalCredencial] CHECK CONSTRAINT [CRMCanalCredencial_FK__Credentia__Chann__7BA7CD13]
GO
-- crm_channels.ExternalIdentity: FK__ExternalI__Chann__07197FBF
ALTER TABLE [dbo].[CRMIdentidadExterna]  WITH CHECK ADD  CONSTRAINT [CRMIdentidadExterna_FK__ExternalI__Chann__07197FBF] FOREIGN KEY([Channel])

REFERENCES [dbo].[CRMCanalCuenta] ([Channel])
GO
ALTER TABLE [dbo].[CRMIdentidadExterna] CHECK CONSTRAINT [CRMIdentidadExterna_FK__ExternalI__Chann__07197FBF]
GO
-- crm_channels.ExternalIdentity: FK__ExternalI__Conta__080DA3F8
ALTER TABLE [dbo].[CRMIdentidadExterna]  WITH CHECK ADD  CONSTRAINT [CRMIdentidadExterna_FK__ExternalI__Conta__080DA3F8] FOREIGN KEY([ContactId])

REFERENCES [dbo].[CRMContacto] ([ContactId])
GO
ALTER TABLE [dbo].[CRMIdentidadExterna] CHECK CONSTRAINT [CRMIdentidadExterna_FK__ExternalI__Conta__080DA3F8]
GO
-- crm_channels.ExternalIdentity: FK__ExternalI__Conve__0901C831
ALTER TABLE [dbo].[CRMIdentidadExterna]  WITH CHECK ADD  CONSTRAINT [CRMIdentidadExterna_FK__ExternalI__Conve__0901C831] FOREIGN KEY([ConversationId])

REFERENCES [dbo].[CRMConversacion] ([ConversationId])
GO
ALTER TABLE [dbo].[CRMIdentidadExterna] CHECK CONSTRAINT [CRMIdentidadExterna_FK__ExternalI__Conve__0901C831]
GO
-- crm_channels.ExternalMessage: FK__ExternalM__Chann__0BDE34DC
ALTER TABLE [dbo].[CRMMensajeExterno]  WITH CHECK ADD  CONSTRAINT [CRMMensajeExterno_FK__ExternalM__Chann__0BDE34DC] FOREIGN KEY([Channel])

REFERENCES [dbo].[CRMCanalCuenta] ([Channel])
GO
ALTER TABLE [dbo].[CRMMensajeExterno] CHECK CONSTRAINT [CRMMensajeExterno_FK__ExternalM__Chann__0BDE34DC]
GO
-- crm_channels.ExternalMessage: FK__ExternalM__Messa__0CD25915
ALTER TABLE [dbo].[CRMMensajeExterno]  WITH CHECK ADD  CONSTRAINT [CRMMensajeExterno_FK__ExternalM__Messa__0CD25915] FOREIGN KEY([MessageId])

REFERENCES [dbo].[CRMMensaje] ([MessageId])
GO
ALTER TABLE [dbo].[CRMMensajeExterno] CHECK CONSTRAINT [CRMMensajeExterno_FK__ExternalM__Messa__0CD25915]
GO
-- crm_channels.MediaAsset: FK__MediaAsse__Chann__4EA01C72
ALTER TABLE [dbo].[CRMArchivoMultimedia]  WITH CHECK ADD  CONSTRAINT [CRMArchivoMultimedia_FK__MediaAsse__Chann__4EA01C72] FOREIGN KEY([Channel])

REFERENCES [dbo].[CRMCanalCuenta] ([Channel])
GO
ALTER TABLE [dbo].[CRMArchivoMultimedia] CHECK CONSTRAINT [CRMArchivoMultimedia_FK__MediaAsse__Chann__4EA01C72]
GO
-- crm_channels.MediaAsset: FK__MediaAsse__Conve__4BC3AFC7
ALTER TABLE [dbo].[CRMArchivoMultimedia]  WITH CHECK ADD  CONSTRAINT [CRMArchivoMultimedia_FK__MediaAsse__Conve__4BC3AFC7] FOREIGN KEY([ConversationId])

REFERENCES [dbo].[CRMConversacion] ([ConversationId])
GO
ALTER TABLE [dbo].[CRMArchivoMultimedia] CHECK CONSTRAINT [CRMArchivoMultimedia_FK__MediaAsse__Conve__4BC3AFC7]
GO
-- crm_channels.MediaAsset: FK__MediaAsse__Ident__4DABF839
ALTER TABLE [dbo].[CRMArchivoMultimedia]  WITH CHECK ADD  CONSTRAINT [CRMArchivoMultimedia_FK__MediaAsse__Ident__4DABF839] FOREIGN KEY([IdentityId])

REFERENCES [dbo].[CRMIdentidadExterna] ([IdentityId])
GO
ALTER TABLE [dbo].[CRMArchivoMultimedia] CHECK CONSTRAINT [CRMArchivoMultimedia_FK__MediaAsse__Ident__4DABF839]
GO
-- crm_channels.MediaAsset: FK__MediaAsse__Messa__4CB7D400
ALTER TABLE [dbo].[CRMArchivoMultimedia]  WITH CHECK ADD  CONSTRAINT [CRMArchivoMultimedia_FK__MediaAsse__Messa__4CB7D400] FOREIGN KEY([MessageId])

REFERENCES [dbo].[CRMMensaje] ([MessageId])
GO
ALTER TABLE [dbo].[CRMArchivoMultimedia] CHECK CONSTRAINT [CRMArchivoMultimedia_FK__MediaAsse__Messa__4CB7D400]
GO
-- crm_channels.MessageRoute: FK__MessageRo__Ident__4516B238
ALTER TABLE [dbo].[CRMMensajeRuta]  WITH CHECK ADD  CONSTRAINT [CRMMensajeRuta_FK__MessageRo__Ident__4516B238] FOREIGN KEY([IdentityId])

REFERENCES [dbo].[CRMIdentidadExterna] ([IdentityId])
GO
ALTER TABLE [dbo].[CRMMensajeRuta] CHECK CONSTRAINT [CRMMensajeRuta_FK__MessageRo__Ident__4516B238]
GO
-- crm_channels.MessageRoute: FK__MessageRo__Messa__44228DFF
ALTER TABLE [dbo].[CRMMensajeRuta]  WITH CHECK ADD  CONSTRAINT [CRMMensajeRuta_FK__MessageRo__Messa__44228DFF] FOREIGN KEY([MessageId])

REFERENCES [dbo].[CRMMensaje] ([MessageId])
GO
ALTER TABLE [dbo].[CRMMensajeRuta] CHECK CONSTRAINT [CRMMensajeRuta_FK__MessageRo__Messa__44228DFF]
GO
-- crm_channels.MessageRoute: FK__MessageRo__Queue__460AD671
ALTER TABLE [dbo].[CRMMensajeRuta]  WITH CHECK ADD  CONSTRAINT [CRMMensajeRuta_FK__MessageRo__Queue__460AD671] FOREIGN KEY([QueueId])

REFERENCES [dbo].[CRMColaSalida] ([QueueId])
GO
ALTER TABLE [dbo].[CRMMensajeRuta] CHECK CONSTRAINT [CRMMensajeRuta_FK__MessageRo__Queue__460AD671]
GO
-- crm_channels.outbound_queue: FK__outbound___Chann__10A2E9F9
ALTER TABLE [dbo].[CRMColaSalida]  WITH CHECK ADD  CONSTRAINT [CRMColaSalida_FK__outbound___Chann__10A2E9F9] FOREIGN KEY([Channel])

REFERENCES [dbo].[CRMCanalCuenta] ([Channel])
GO
ALTER TABLE [dbo].[CRMColaSalida] CHECK CONSTRAINT [CRMColaSalida_FK__outbound___Chann__10A2E9F9]
GO
-- crm_channels.outbound_queue: FK__outbound___Ident__11970E32
ALTER TABLE [dbo].[CRMColaSalida]  WITH CHECK ADD  CONSTRAINT [CRMColaSalida_FK__outbound___Ident__11970E32] FOREIGN KEY([IdentityId])

REFERENCES [dbo].[CRMIdentidadExterna] ([IdentityId])
GO
ALTER TABLE [dbo].[CRMColaSalida] CHECK CONSTRAINT [CRMColaSalida_FK__outbound___Ident__11970E32]
GO
-- crm_channels.outbound_queue: FK__outbound___Messa__128B326B
ALTER TABLE [dbo].[CRMColaSalida]  WITH CHECK ADD  CONSTRAINT [CRMColaSalida_FK__outbound___Messa__128B326B] FOREIGN KEY([MessageId])

REFERENCES [dbo].[CRMMensaje] ([MessageId])
GO
ALTER TABLE [dbo].[CRMColaSalida] CHECK CONSTRAINT [CRMColaSalida_FK__outbound___Messa__128B326B]
GO
-- crm_channels.social_comments: FK__social_co__Chann__1C149CA5
ALTER TABLE [dbo].[CRMComentarioSocial]  WITH CHECK ADD  CONSTRAINT [CRMComentarioSocial_FK__social_co__Chann__1C149CA5] FOREIGN KEY([Channel])

REFERENCES [dbo].[CRMCanalCuenta] ([Channel])
GO
ALTER TABLE [dbo].[CRMComentarioSocial] CHECK CONSTRAINT [CRMComentarioSocial_FK__social_co__Chann__1C149CA5]
GO
-- crm_events.Event: FK_Event_Conversation
ALTER TABLE [dbo].[CRMConversacionEvento]  WITH CHECK ADD  CONSTRAINT [CRMConversacionEvento_FK_Event_Conversation] FOREIGN KEY([ConversationId])

REFERENCES [dbo].[CRMConversacion] ([ConversationId])
GO
ALTER TABLE [dbo].[CRMConversacionEvento] CHECK CONSTRAINT [CRMConversacionEvento_FK_Event_Conversation]
GO
-- crm_events.Preparation: FK_Preparation_Conversation
ALTER TABLE [dbo].[CRMEventoPreparacion]  WITH CHECK ADD  CONSTRAINT [CRMEventoPreparacion_FK_Preparation_Conversation] FOREIGN KEY([ConversationId])

REFERENCES [dbo].[CRMConversacion] ([ConversationId])
GO
ALTER TABLE [dbo].[CRMEventoPreparacion] CHECK CONSTRAINT [CRMEventoPreparacion_FK_Preparation_Conversation]
GO
-- crm_events.Preparation: FK_Preparation_Event
ALTER TABLE [dbo].[CRMEventoPreparacion]  WITH CHECK ADD  CONSTRAINT [CRMEventoPreparacion_FK_Preparation_Event] FOREIGN KEY([LastEventId])

REFERENCES [dbo].[CRMConversacionEvento] ([EventId])
GO
ALTER TABLE [dbo].[CRMEventoPreparacion] CHECK CONSTRAINT [CRMEventoPreparacion_FK_Preparation_Event]
GO
-- crm_identity.Profile: FK_IdentityProfile_Contact
ALTER TABLE [dbo].[CRMContactoPerfilInstitucional]  WITH CHECK ADD  CONSTRAINT [CRMContactoPerfilInstitucional_FK_IdentityProfile_Contact] FOREIGN KEY([ContactId])

REFERENCES [dbo].[CRMContacto] ([ContactId])
GO
ALTER TABLE [dbo].[CRMContactoPerfilInstitucional] CHECK CONSTRAINT [CRMContactoPerfilInstitucional_FK_IdentityProfile_Contact]
GO
-- crm_inbox.Assignment: FK_InboxAssignment_Agent
ALTER TABLE [dbo].[CRMBandejaAsignacion]  WITH CHECK ADD  CONSTRAINT [CRMBandejaAsignacion_FK_InboxAssignment_Agent] FOREIGN KEY([AiAgentId])

REFERENCES [dbo].[CRMBandejaAgente] ([AgentId])
GO
ALTER TABLE [dbo].[CRMBandejaAsignacion] CHECK CONSTRAINT [CRMBandejaAsignacion_FK_InboxAssignment_Agent]
GO
-- crm_inbox.Assignment: FK_InboxAssignment_Conversation
ALTER TABLE [dbo].[CRMBandejaAsignacion]  WITH CHECK ADD  CONSTRAINT [CRMBandejaAsignacion_FK_InboxAssignment_Conversation] FOREIGN KEY([ConversationId])

REFERENCES [dbo].[CRMConversacion] ([ConversationId])
GO
ALTER TABLE [dbo].[CRMBandejaAsignacion] CHECK CONSTRAINT [CRMBandejaAsignacion_FK_InboxAssignment_Conversation]
GO
-- crm_inbox.Assignment: FK_InboxAssignment_Human
ALTER TABLE [dbo].[CRMBandejaAsignacion]  WITH CHECK ADD  CONSTRAINT [CRMBandejaAsignacion_FK_InboxAssignment_Human] FOREIGN KEY([HumanEmployeeId])

REFERENCES [dbo].[CRMBandejaMiembro] ([EmployeeId])
GO
ALTER TABLE [dbo].[CRMBandejaAsignacion] CHECK CONSTRAINT [CRMBandejaAsignacion_FK_InboxAssignment_Human]
GO
-- crm_inbox.Task: FK_InboxTask_Conversation
ALTER TABLE [dbo].[CRMBandejaTarea]  WITH CHECK ADD  CONSTRAINT [CRMBandejaTarea_FK_InboxTask_Conversation] FOREIGN KEY([ConversationId])

REFERENCES [dbo].[CRMConversacion] ([ConversationId])
GO
ALTER TABLE [dbo].[CRMBandejaTarea] CHECK CONSTRAINT [CRMBandejaTarea_FK_InboxTask_Conversation]
GO
-- crm_inbox.Task: FK_InboxTask_Human
ALTER TABLE [dbo].[CRMBandejaTarea]  WITH CHECK ADD  CONSTRAINT [CRMBandejaTarea_FK_InboxTask_Human] FOREIGN KEY([HumanEmployeeId])

REFERENCES [dbo].[CRMBandejaMiembro] ([EmployeeId])
GO
ALTER TABLE [dbo].[CRMBandejaTarea] CHECK CONSTRAINT [CRMBandejaTarea_FK_InboxTask_Human]
GO
-- crm_marketing.AccountCadence: FK__AccountCa__Chann__44E1A80E
ALTER TABLE [dbo].[CRMCuentaCadencia]  WITH CHECK ADD  CONSTRAINT [CRMCuentaCadencia_FK__AccountCa__Chann__44E1A80E] FOREIGN KEY([Channel])

REFERENCES [dbo].[CRMCanalCuenta] ([Channel])
GO
ALTER TABLE [dbo].[CRMCuentaCadencia] CHECK CONSTRAINT [CRMCuentaCadencia_FK__AccountCa__Chann__44E1A80E]
GO
-- crm_marketing.Campaign: FK__Campaign__59DCC4F4
ALTER TABLE [dbo].[CRMCampana]  WITH CHECK ADD  CONSTRAINT [CRMCampana_FK__Campaign__59DCC4F4] FOREIGN KEY([Channel], [AccountScope])

REFERENCES [dbo].[CRMCuentaCadencia] ([Channel], [AccountScope])
GO
ALTER TABLE [dbo].[CRMCampana] CHECK CONSTRAINT [CRMCampana_FK__Campaign__59DCC4F4]
GO
-- crm_marketing.Campaign: FK__Campaign__5AD0E92D
ALTER TABLE [dbo].[CRMCampana]  WITH CHECK ADD  CONSTRAINT [CRMCampana_FK__Campaign__5AD0E92D] FOREIGN KEY([TemplateId], [TemplateVersion], [Channel], [AccountScope])

REFERENCES [dbo].[CRMMensajePlantilla] ([TemplateId], [Version], [Channel], [AccountScope])
GO
ALTER TABLE [dbo].[CRMCampana] CHECK CONSTRAINT [CRMCampana_FK__Campaign__5AD0E92D]
GO
-- crm_marketing.Campaign: FK__Campaign__RuleId__523BA32C
ALTER TABLE [dbo].[CRMCampana]  WITH CHECK ADD  CONSTRAINT [CRMCampana_FK__Campaign__RuleId__523BA32C] FOREIGN KEY([RuleId])

REFERENCES [dbo].[CRMRecontactoRegla] ([RuleId])
GO
ALTER TABLE [dbo].[CRMCampana] CHECK CONSTRAINT [CRMCampana_FK__Campaign__RuleId__523BA32C]
GO
-- crm_marketing.CampaignRecipient: FK__CampaignR__Campa__71B44E85
ALTER TABLE [dbo].[CRMCampanaDestinatario]  WITH CHECK ADD  CONSTRAINT [CRMCampanaDestinatario_FK__CampaignR__Campa__71B44E85] FOREIGN KEY([CampaignId])

REFERENCES [dbo].[CRMCampana] ([CampaignId])
GO
ALTER TABLE [dbo].[CRMCampanaDestinatario] CHECK CONSTRAINT [CRMCampanaDestinatario_FK__CampaignR__Campa__71B44E85]
GO
-- crm_marketing.CampaignRecipient: FK__CampaignR__Conta__62720AF5
ALTER TABLE [dbo].[CRMCampanaDestinatario]  WITH CHECK ADD  CONSTRAINT [CRMCampanaDestinatario_FK__CampaignR__Conta__62720AF5] FOREIGN KEY([ContactId])

REFERENCES [dbo].[CRMContacto] ([ContactId])
GO
ALTER TABLE [dbo].[CRMCampanaDestinatario] CHECK CONSTRAINT [CRMCampanaDestinatario_FK__CampaignR__Conta__62720AF5]
GO
-- crm_marketing.CampaignRecipient: FK__CampaignR__Conve__63662F2E
ALTER TABLE [dbo].[CRMCampanaDestinatario]  WITH CHECK ADD  CONSTRAINT [CRMCampanaDestinatario_FK__CampaignR__Conve__63662F2E] FOREIGN KEY([ConversationId])

REFERENCES [dbo].[CRMConversacion] ([ConversationId])
GO
ALTER TABLE [dbo].[CRMCampanaDestinatario] CHECK CONSTRAINT [CRMCampanaDestinatario_FK__CampaignR__Conve__63662F2E]
GO
-- crm_marketing.CampaignRecipient: FK__CampaignR__Ident__617DE6BC
ALTER TABLE [dbo].[CRMCampanaDestinatario]  WITH CHECK ADD  CONSTRAINT [CRMCampanaDestinatario_FK__CampaignR__Ident__617DE6BC] FOREIGN KEY([IdentityId])

REFERENCES [dbo].[CRMIdentidadExterna] ([IdentityId])
GO
ALTER TABLE [dbo].[CRMCampanaDestinatario] CHECK CONSTRAINT [CRMCampanaDestinatario_FK__CampaignR__Ident__617DE6BC]
GO
-- crm_marketing.CampaignRecipient: FK__CampaignR__Queue__66429BD9
ALTER TABLE [dbo].[CRMCampanaDestinatario]  WITH CHECK ADD  CONSTRAINT [CRMCampanaDestinatario_FK__CampaignR__Queue__66429BD9] FOREIGN KEY([QueueId])

REFERENCES [dbo].[CRMColaSalida] ([QueueId])
GO
ALTER TABLE [dbo].[CRMCampanaDestinatario] CHECK CONSTRAINT [CRMCampanaDestinatario_FK__CampaignR__Queue__66429BD9]
GO
-- crm_marketing.CampaignRecipient: FK__CampaignRecipien__72A872BE
ALTER TABLE [dbo].[CRMCampanaDestinatario]  WITH CHECK ADD  CONSTRAINT [CRMCampanaDestinatario_FK__CampaignRecipien__72A872BE] FOREIGN KEY([CampaignId], [Channel], [AccountScope])

REFERENCES [dbo].[CRMCampana] ([CampaignId], [Channel], [AccountScope])
GO
ALTER TABLE [dbo].[CRMCampanaDestinatario] CHECK CONSTRAINT [CRMCampanaDestinatario_FK__CampaignRecipien__72A872BE]
GO
-- crm_marketing.CampaignRecipient: FK__CampaignRecipien__739C96F7
ALTER TABLE [dbo].[CRMCampanaDestinatario]  WITH CHECK ADD  CONSTRAINT [CRMCampanaDestinatario_FK__CampaignRecipien__739C96F7] FOREIGN KEY([ConsentId], [ConsentVersion])

REFERENCES [dbo].[CRMContactoConsentimiento] ([ConsentId], [Version])
GO
ALTER TABLE [dbo].[CRMCampanaDestinatario] CHECK CONSTRAINT [CRMCampanaDestinatario_FK__CampaignRecipien__739C96F7]
GO
-- crm_marketing.ChurnAssessment: FK__ChurnAsse__Conve__0AB50679
ALTER TABLE [dbo].[CRMAbandonoEvaluacion]  WITH CHECK ADD  CONSTRAINT [CRMAbandonoEvaluacion_FK__ChurnAsse__Conve__0AB50679] FOREIGN KEY([ConversationId])

REFERENCES [dbo].[CRMConversacion] ([ConversationId])
GO
ALTER TABLE [dbo].[CRMAbandonoEvaluacion] CHECK CONSTRAINT [CRMAbandonoEvaluacion_FK__ChurnAsse__Conve__0AB50679]
GO
-- crm_marketing.ChurnAssessment: FK__ChurnAsse__Ident__0BA92AB2
ALTER TABLE [dbo].[CRMAbandonoEvaluacion]  WITH CHECK ADD  CONSTRAINT [CRMAbandonoEvaluacion_FK__ChurnAsse__Ident__0BA92AB2] FOREIGN KEY([IdentityId])

REFERENCES [dbo].[CRMIdentidadExterna] ([IdentityId])
GO
ALTER TABLE [dbo].[CRMAbandonoEvaluacion] CHECK CONSTRAINT [CRMAbandonoEvaluacion_FK__ChurnAsse__Ident__0BA92AB2]
GO
-- crm_marketing.ChurnAssessment: FK__ChurnAsse__RunId__04C722F9
ALTER TABLE [dbo].[CRMAbandonoEvaluacion]  WITH CHECK ADD  CONSTRAINT [CRMAbandonoEvaluacion_FK__ChurnAsse__RunId__04C722F9] FOREIGN KEY([RunId])

REFERENCES [dbo].[CRMCampanaEvaluacionEjecucion] ([RunId])
GO
ALTER TABLE [dbo].[CRMAbandonoEvaluacion] CHECK CONSTRAINT [CRMAbandonoEvaluacion_FK__ChurnAsse__RunId__04C722F9]
GO
-- crm_marketing.ContactConsent: FK__ContactCo__Chann__28456960
ALTER TABLE [dbo].[CRMContactoConsentimiento]  WITH CHECK ADD  CONSTRAINT [CRMContactoConsentimiento_FK__ContactCo__Chann__28456960] FOREIGN KEY([Channel])

REFERENCES [dbo].[CRMCanalCuenta] ([Channel])
GO
ALTER TABLE [dbo].[CRMContactoConsentimiento] CHECK CONSTRAINT [CRMContactoConsentimiento_FK__ContactCo__Chann__28456960]
GO
-- crm_marketing.ContactConsent: FK__ContactCo__Ident__27514527
ALTER TABLE [dbo].[CRMContactoConsentimiento]  WITH CHECK ADD  CONSTRAINT [CRMContactoConsentimiento_FK__ContactCo__Ident__27514527] FOREIGN KEY([IdentityId])

REFERENCES [dbo].[CRMIdentidadExterna] ([IdentityId])
GO
ALTER TABLE [dbo].[CRMContactoConsentimiento] CHECK CONSTRAINT [CRMContactoConsentimiento_FK__ContactCo__Ident__27514527]
GO
-- crm_marketing.ContactConsent: FK__ContactConsent__2EF266EF
ALTER TABLE [dbo].[CRMContactoConsentimiento]  WITH CHECK ADD  CONSTRAINT [CRMContactoConsentimiento_FK__ContactConsent__2EF266EF] FOREIGN KEY([IdentityId], [Channel], [AccountScope], [Purpose], [RevokesVersion])

REFERENCES [dbo].[CRMContactoConsentimiento] ([IdentityId], [Channel], [AccountScope], [Purpose], [Version])
GO
ALTER TABLE [dbo].[CRMContactoConsentimiento] CHECK CONSTRAINT [CRMContactoConsentimiento_FK__ContactConsent__2EF266EF]
GO
-- crm_marketing.EvaluationRun: FK__Evaluatio__Campa__7C31DCF8
ALTER TABLE [dbo].[CRMCampanaEvaluacionEjecucion]  WITH CHECK ADD  CONSTRAINT [CRMCampanaEvaluacionEjecucion_FK__Evaluatio__Campa__7C31DCF8] FOREIGN KEY([CampaignId])

REFERENCES [dbo].[CRMCampana] ([CampaignId])
GO
ALTER TABLE [dbo].[CRMCampanaEvaluacionEjecucion] CHECK CONSTRAINT [CRMCampanaEvaluacionEjecucion_FK__Evaluatio__Campa__7C31DCF8]
GO
-- crm_marketing.EvaluationRun: FK__Evaluatio__RuleI__7B3DB8BF
ALTER TABLE [dbo].[CRMCampanaEvaluacionEjecucion]  WITH CHECK ADD  CONSTRAINT [CRMCampanaEvaluacionEjecucion_FK__Evaluatio__RuleI__7B3DB8BF] FOREIGN KEY([RuleId])

REFERENCES [dbo].[CRMRecontactoRegla] ([RuleId])
GO
ALTER TABLE [dbo].[CRMCampanaEvaluacionEjecucion] CHECK CONSTRAINT [CRMCampanaEvaluacionEjecucion_FK__Evaluatio__RuleI__7B3DB8BF]
GO
-- crm_marketing.MessageTemplate: FK__MessageTe__Chann__1AEB6E42
ALTER TABLE [dbo].[CRMMensajePlantilla]  WITH CHECK ADD  CONSTRAINT [CRMMensajePlantilla_FK__MessageTe__Chann__1AEB6E42] FOREIGN KEY([Channel])

REFERENCES [dbo].[CRMCanalCuenta] ([Channel])
GO
ALTER TABLE [dbo].[CRMMensajePlantilla] CHECK CONSTRAINT [CRMMensajePlantilla_FK__MessageTe__Chann__1AEB6E42]
GO
-- crm_marketing.RemarketingRule: FK__Remarketi__Chann__34AB4045
ALTER TABLE [dbo].[CRMRecontactoRegla]  WITH CHECK ADD  CONSTRAINT [CRMRecontactoRegla_FK__Remarketi__Chann__34AB4045] FOREIGN KEY([Channel])

REFERENCES [dbo].[CRMCanalCuenta] ([Channel])
GO
ALTER TABLE [dbo].[CRMRecontactoRegla] CHECK CONSTRAINT [CRMRecontactoRegla_FK__Remarketi__Chann__34AB4045]
GO
-- crm_marketing.RemarketingRule: FK__RemarketingRule__3F28CEB8
ALTER TABLE [dbo].[CRMRecontactoRegla]  WITH CHECK ADD  CONSTRAINT [CRMRecontactoRegla_FK__RemarketingRule__3F28CEB8] FOREIGN KEY([TemplateId], [TemplateVersion], [Channel], [AccountScope])

REFERENCES [dbo].[CRMMensajePlantilla] ([TemplateId], [Version], [Channel], [AccountScope])
GO
ALTER TABLE [dbo].[CRMRecontactoRegla] CHECK CONSTRAINT [CRMRecontactoRegla_FK__RemarketingRule__3F28CEB8]
GO
-- crm_merge.MergeCase: FK_MergeCase_Source
ALTER TABLE [dbo].[CRMContactoUnificacion]  WITH CHECK ADD  CONSTRAINT [CRMContactoUnificacion_FK_MergeCase_Source] FOREIGN KEY([SourceContactId])

REFERENCES [dbo].[CRMContacto] ([ContactId])
GO
ALTER TABLE [dbo].[CRMContactoUnificacion] CHECK CONSTRAINT [CRMContactoUnificacion_FK_MergeCase_Source]
GO
-- crm_merge.MergeCase: FK_MergeCase_Target
ALTER TABLE [dbo].[CRMContactoUnificacion]  WITH CHECK ADD  CONSTRAINT [CRMContactoUnificacion_FK_MergeCase_Target] FOREIGN KEY([TargetContactId])

REFERENCES [dbo].[CRMContacto] ([ContactId])
GO
ALTER TABLE [dbo].[CRMContactoUnificacion] CHECK CONSTRAINT [CRMContactoUnificacion_FK_MergeCase_Target]
GO
-- crm_merge.Operation: FK_MergeOperation_Case
ALTER TABLE [dbo].[CRMUnificacionOperacion]  WITH CHECK ADD  CONSTRAINT [CRMUnificacionOperacion_FK_MergeOperation_Case] FOREIGN KEY([MergeId])

REFERENCES [dbo].[CRMContactoUnificacion] ([MergeId])
GO
ALTER TABLE [dbo].[CRMUnificacionOperacion] CHECK CONSTRAINT [CRMUnificacionOperacion_FK_MergeOperation_Case]
GO
-- crm_merge.Operation: FK_MergeOperation_Source
ALTER TABLE [dbo].[CRMUnificacionOperacion]  WITH CHECK ADD  CONSTRAINT [CRMUnificacionOperacion_FK_MergeOperation_Source] FOREIGN KEY([SourceContactId])

REFERENCES [dbo].[CRMContacto] ([ContactId])
GO
ALTER TABLE [dbo].[CRMUnificacionOperacion] CHECK CONSTRAINT [CRMUnificacionOperacion_FK_MergeOperation_Source]
GO
-- crm_merge.Operation: FK_MergeOperation_Target
ALTER TABLE [dbo].[CRMUnificacionOperacion]  WITH CHECK ADD  CONSTRAINT [CRMUnificacionOperacion_FK_MergeOperation_Target] FOREIGN KEY([TargetContactId])

REFERENCES [dbo].[CRMContacto] ([ContactId])
GO
ALTER TABLE [dbo].[CRMUnificacionOperacion] CHECK CONSTRAINT [CRMUnificacionOperacion_FK_MergeOperation_Target]
GO
-- crm_strategy.EvaluationPlan: FK_StrategyPlan_Conversation
ALTER TABLE [dbo].[CRMEstrategiaPlanEvaluacion]  WITH CHECK ADD  CONSTRAINT [CRMEstrategiaPlanEvaluacion_FK_StrategyPlan_Conversation] FOREIGN KEY([ConversationId])

REFERENCES [dbo].[CRMConversacion] ([ConversationId])
GO
ALTER TABLE [dbo].[CRMEstrategiaPlanEvaluacion] CHECK CONSTRAINT [CRMEstrategiaPlanEvaluacion_FK_StrategyPlan_Conversation]
GO
-- crm_strategy.Operation: FK_StrategyOperation_Conversation
ALTER TABLE [dbo].[CRMEstrategiaOperacion]  WITH CHECK ADD  CONSTRAINT [CRMEstrategiaOperacion_FK_StrategyOperation_Conversation] FOREIGN KEY([ConversationId])

REFERENCES [dbo].[CRMConversacion] ([ConversationId])
GO
ALTER TABLE [dbo].[CRMEstrategiaOperacion] CHECK CONSTRAINT [CRMEstrategiaOperacion_FK_StrategyOperation_Conversation]
GO
-- crm_strategy.Operation: FK_StrategyOperation_Plan
ALTER TABLE [dbo].[CRMEstrategiaOperacion]  WITH CHECK ADD  CONSTRAINT [CRMEstrategiaOperacion_FK_StrategyOperation_Plan] FOREIGN KEY([PlanId])

REFERENCES [dbo].[CRMEstrategiaPlanEvaluacion] ([PlanId])
GO
ALTER TABLE [dbo].[CRMEstrategiaOperacion] CHECK CONSTRAINT [CRMEstrategiaOperacion_FK_StrategyOperation_Plan]
GO
-- crm_strategy.Operation: FK_StrategyOperation_Task
ALTER TABLE [dbo].[CRMEstrategiaOperacion]  WITH CHECK ADD  CONSTRAINT [CRMEstrategiaOperacion_FK_StrategyOperation_Task] FOREIGN KEY([TaskId])

REFERENCES [dbo].[CRMBandejaTarea] ([TaskId])
GO
ALTER TABLE [dbo].[CRMEstrategiaOperacion] CHECK CONSTRAINT [CRMEstrategiaOperacion_FK_StrategyOperation_Task]
GO
-- crm_strategy.Policy: FK_StrategyPolicy_Conversation
ALTER TABLE [dbo].[CRMEstrategiaPolitica]  WITH CHECK ADD  CONSTRAINT [CRMEstrategiaPolitica_FK_StrategyPolicy_Conversation] FOREIGN KEY([ConversationId])

REFERENCES [dbo].[CRMConversacion] ([ConversationId])
GO
ALTER TABLE [dbo].[CRMEstrategiaPolitica] CHECK CONSTRAINT [CRMEstrategiaPolitica_FK_StrategyPolicy_Conversation]
GO
-- dbo.ACAsignaturaPlan: FK_ACAsignaturaPlan_ACAsignatura
ALTER TABLE [dbo].[ACAsignaturaPlan]  WITH CHECK ADD  CONSTRAINT [FK_ACAsignaturaPlan_ACAsignatura] FOREIGN KEY([Id_Asignatura])

REFERENCES [dbo].[ACAsignatura] ([Id_Asignatura])
GO
ALTER TABLE [dbo].[ACAsignaturaPlan] CHECK CONSTRAINT [FK_ACAsignaturaPlan_ACAsignatura]
GO
-- dbo.ACAsignaturaPlan: FK_ACAsignaturaPlan_ACPlanEducativo
ALTER TABLE [dbo].[ACAsignaturaPlan]  WITH CHECK ADD  CONSTRAINT [FK_ACAsignaturaPlan_ACPlanEducativo] FOREIGN KEY([Id_PlanEducativo])

REFERENCES [dbo].[ACPlanEducativo] ([Id_PlanEducativo])
GO
ALTER TABLE [dbo].[ACAsignaturaPlan] CHECK CONSTRAINT [FK_ACAsignaturaPlan_ACPlanEducativo]
GO
-- dbo.ACAsignaturaPlan: FK_ACAsignaturaPlan_ACPlanEvaluativo1
ALTER TABLE [dbo].[ACAsignaturaPlan]  WITH CHECK ADD  CONSTRAINT [FK_ACAsignaturaPlan_ACPlanEvaluativo1] FOREIGN KEY([Id_PlanEvaluativo])

REFERENCES [dbo].[ACPlanEvaluativo] ([Id_PlanEvaluativo])
GO
ALTER TABLE [dbo].[ACAsignaturaPlan] CHECK CONSTRAINT [FK_ACAsignaturaPlan_ACPlanEvaluativo1]
GO
-- dbo.ACAsignaturaPlan: FK_ACAsignaturaPlan_ACTipoAlternancia
ALTER TABLE [dbo].[ACAsignaturaPlan]  WITH CHECK ADD  CONSTRAINT [FK_ACAsignaturaPlan_ACTipoAlternancia] FOREIGN KEY([Id_TipoAlternancia])

REFERENCES [dbo].[ACTipoAlternancia] ([Id_TipoAlternancia])
GO
ALTER TABLE [dbo].[ACAsignaturaPlan] CHECK CONSTRAINT [FK_ACAsignaturaPlan_ACTipoAlternancia]
GO
-- dbo.ACAspirante: FK_ACAspirante_ACProgramaOfrecido
ALTER TABLE [dbo].[ACAspirante]  WITH CHECK ADD  CONSTRAINT [FK_ACAspirante_ACProgramaOfrecido] FOREIGN KEY([Id_PrgOfrecido])

REFERENCES [dbo].[ACProgramaOfrecido] ([Id_PrgOfrecido])
GO
ALTER TABLE [dbo].[ACAspirante] CHECK CONSTRAINT [FK_ACAspirante_ACProgramaOfrecido]
GO
-- dbo.ACAspirante: FK_ACAspirante_GEPeriodo
ALTER TABLE [dbo].[ACAspirante]  WITH CHECK ADD  CONSTRAINT [FK_ACAspirante_GEPeriodo] FOREIGN KEY([Id_Periodo])

REFERENCES [dbo].[GEPeriodo] ([Id_Periodo])
GO
ALTER TABLE [dbo].[ACAspirante] CHECK CONSTRAINT [FK_ACAspirante_GEPeriodo]
GO
-- dbo.ACAspirante: FK_ACAspirante_GETipoIdentidad
ALTER TABLE [dbo].[ACAspirante]  WITH CHECK ADD  CONSTRAINT [FK_ACAspirante_GETipoIdentidad] FOREIGN KEY([TipoId])

REFERENCES [dbo].[GETipoIdentidad] ([TipoId])
GO
ALTER TABLE [dbo].[ACAspirante] CHECK CONSTRAINT [FK_ACAspirante_GETipoIdentidad]
GO
-- dbo.ACDetalleJornada: FK_ACJornadaOfrecida_ACJornada
ALTER TABLE [dbo].[ACDetalleJornada]  WITH CHECK ADD  CONSTRAINT [FK_ACJornadaOfrecida_ACJornada] FOREIGN KEY([Id_Jornada])

REFERENCES [dbo].[ACJornada] ([Id_Jornada])
GO
ALTER TABLE [dbo].[ACDetalleJornada] CHECK CONSTRAINT [FK_ACJornadaOfrecida_ACJornada]
GO
-- dbo.ACDetalleJornada: FK_ACJornadaOfrecida_ACProgramaOfrecido
ALTER TABLE [dbo].[ACDetalleJornada]  WITH CHECK ADD  CONSTRAINT [FK_ACJornadaOfrecida_ACProgramaOfrecido] FOREIGN KEY([Id_PrgOfrecido])

REFERENCES [dbo].[ACProgramaOfrecido] ([Id_PrgOfrecido])
GO
ALTER TABLE [dbo].[ACDetalleJornada] CHECK CONSTRAINT [FK_ACJornadaOfrecida_ACProgramaOfrecido]
GO
-- dbo.ACPlanEducativo: FK_ACPlanEducativo_GEPeriodo
ALTER TABLE [dbo].[ACPlanEducativo]  WITH CHECK ADD  CONSTRAINT [FK_ACPlanEducativo_GEPeriodo] FOREIGN KEY([Id_Periodo])

REFERENCES [dbo].[GEPeriodo] ([Id_Periodo])
GO
ALTER TABLE [dbo].[ACPlanEducativo] CHECK CONSTRAINT [FK_ACPlanEducativo_GEPeriodo]
GO
-- dbo.ACProgramaOfrecido: FK_ACProgramaOfrecido_ACProgramas
ALTER TABLE [dbo].[ACProgramaOfrecido]  WITH CHECK ADD  CONSTRAINT [FK_ACProgramaOfrecido_ACProgramas] FOREIGN KEY([Id_Programa])

REFERENCES [dbo].[ACProgramas] ([Id_Programa])
GO
ALTER TABLE [dbo].[ACProgramaOfrecido] CHECK CONSTRAINT [FK_ACProgramaOfrecido_ACProgramas]
GO
-- dbo.ACProgramaOfrecido: FK_ACProgramaOfrecido_GEPeriodo
ALTER TABLE [dbo].[ACProgramaOfrecido]  WITH CHECK ADD  CONSTRAINT [FK_ACProgramaOfrecido_GEPeriodo] FOREIGN KEY([Id_Periodo])

REFERENCES [dbo].[GEPeriodo] ([Id_Periodo])
GO
ALTER TABLE [dbo].[ACProgramaOfrecido] CHECK CONSTRAINT [FK_ACProgramaOfrecido_GEPeriodo]
GO
-- dbo.ACProgramas: FK_ACProgramas_ACEscuela
ALTER TABLE [dbo].[ACProgramas]  WITH CHECK ADD  CONSTRAINT [FK_ACProgramas_ACEscuela] FOREIGN KEY([Id_Escuela])

REFERENCES [dbo].[ACEscuela] ([Id_Escuela])
GO
ALTER TABLE [dbo].[ACProgramas] CHECK CONSTRAINT [FK_ACProgramas_ACEscuela]
GO
-- dbo.ACProgramas: FK_ACProgramas_ACJornada
ALTER TABLE [dbo].[ACProgramas]  WITH CHECK ADD  CONSTRAINT [FK_ACProgramas_ACJornada] FOREIGN KEY([Id_Jornada])

REFERENCES [dbo].[ACJornada] ([Id_Jornada])
GO
ALTER TABLE [dbo].[ACProgramas] CHECK CONSTRAINT [FK_ACProgramas_ACJornada]
GO
-- dbo.ACProgramas: FK_ACProgramas_ACModalidad
ALTER TABLE [dbo].[ACProgramas]  WITH CHECK ADD  CONSTRAINT [FK_ACProgramas_ACModalidad] FOREIGN KEY([Id_Modalidad])

REFERENCES [dbo].[ACModalidad] ([Id_Modalidad])
GO
ALTER TABLE [dbo].[ACProgramas] CHECK CONSTRAINT [FK_ACProgramas_ACModalidad]
GO
-- dbo.ACSeguimiento: FK_ACSeguimiento_ACAspirante
ALTER TABLE [dbo].[ACSeguimiento]  WITH CHECK ADD  CONSTRAINT [FK_ACSeguimiento_ACAspirante] FOREIGN KEY([Id_Aspirante])

REFERENCES [dbo].[ACAspirante] ([Id_Aspirante])
GO
ALTER TABLE [dbo].[ACSeguimiento] CHECK CONSTRAINT [FK_ACSeguimiento_ACAspirante]
GO
-- dbo.ACSeguimiento: FK_ACSeguimiento_ACEstadoSeguimiento
ALTER TABLE [dbo].[ACSeguimiento]  WITH CHECK ADD  CONSTRAINT [FK_ACSeguimiento_ACEstadoSeguimiento] FOREIGN KEY([Estado])

REFERENCES [dbo].[ACEstadoSeguimiento] ([Id_EstadoSeguimiento])
GO
ALTER TABLE [dbo].[ACSeguimiento] CHECK CONSTRAINT [FK_ACSeguimiento_ACEstadoSeguimiento]
GO
-- dbo.AFDetallePlanPago: FK_AFDetallePlanPago_AFPlanes
ALTER TABLE [dbo].[AFDetallePlanPago]  WITH CHECK ADD  CONSTRAINT [FK_AFDetallePlanPago_AFPlanes] FOREIGN KEY([Id_Plan])

REFERENCES [dbo].[AFPlanes] ([Id_Plan])
GO
ALTER TABLE [dbo].[AFDetallePlanPago] CHECK CONSTRAINT [FK_AFDetallePlanPago_AFPlanes]
GO
-- dbo.AFTarifas: FK_AFTarifas_ACProgramas
ALTER TABLE [dbo].[AFTarifas]  WITH CHECK ADD  CONSTRAINT [FK_AFTarifas_ACProgramas] FOREIGN KEY([Id_Programa])

REFERENCES [dbo].[ACProgramas] ([Id_Programa])
GO
ALTER TABLE [dbo].[AFTarifas] CHECK CONSTRAINT [FK_AFTarifas_ACProgramas]
GO
-- dbo.AFTarifas: FK_AFTarifas_AFPlanes
ALTER TABLE [dbo].[AFTarifas]  WITH CHECK ADD  CONSTRAINT [FK_AFTarifas_AFPlanes] FOREIGN KEY([Id_Plan])

REFERENCES [dbo].[AFPlanes] ([Id_Plan])
GO
ALTER TABLE [dbo].[AFTarifas] CHECK CONSTRAINT [FK_AFTarifas_AFPlanes]
GO
-- dbo.AFTarifas: FK_AFTarifas_GEPeriodo
ALTER TABLE [dbo].[AFTarifas]  WITH CHECK ADD  CONSTRAINT [FK_AFTarifas_GEPeriodo] FOREIGN KEY([Id_Periodo])

REFERENCES [dbo].[GEPeriodo] ([Id_Periodo])
GO
ALTER TABLE [dbo].[AFTarifas] CHECK CONSTRAINT [FK_AFTarifas_GEPeriodo]
GO
-- dbo.GEEmpleado: FK_GEEmpleado_GECargoEmpresa
ALTER TABLE [dbo].[GEEmpleado]  WITH CHECK ADD  CONSTRAINT [FK_GEEmpleado_GECargoEmpresa] FOREIGN KEY([CdgoCrgo])

REFERENCES [dbo].[GECargoEmpresa] ([CdgoCrgo])
GO
ALTER TABLE [dbo].[GEEmpleado] CHECK CONSTRAINT [FK_GEEmpleado_GECargoEmpresa]
GO
-- dbo.GEEmpleado: FK_GEEmpleado_GEEmpresa
ALTER TABLE [dbo].[GEEmpleado]  WITH CHECK ADD  CONSTRAINT [FK_GEEmpleado_GEEmpresa] FOREIGN KEY([CdgoEmprsaLbra])

REFERENCES [dbo].[GEEmpresa] ([CdgoEmprsa])
GO
ALTER TABLE [dbo].[GEEmpleado] CHECK CONSTRAINT [FK_GEEmpleado_GEEmpresa]
GO
-- dbo.GEEstudiante: FK_GEEstudiante_ACAcudiente
ALTER TABLE [dbo].[GEEstudiante]  WITH CHECK ADD  CONSTRAINT [FK_GEEstudiante_ACAcudiente] FOREIGN KEY([Id_Acudiente])

REFERENCES [dbo].[ACAcudiente] ([Id_Acudiente])
GO
ALTER TABLE [dbo].[GEEstudiante] CHECK CONSTRAINT [FK_GEEstudiante_ACAcudiente]
GO
-- dbo.GEEstudiante: FK_GEEstudiante_ACProgramaOfrecido
ALTER TABLE [dbo].[GEEstudiante]  WITH CHECK ADD  CONSTRAINT [FK_GEEstudiante_ACProgramaOfrecido] FOREIGN KEY([Id_PrgOfrecido])

REFERENCES [dbo].[ACProgramaOfrecido] ([Id_PrgOfrecido])
GO
ALTER TABLE [dbo].[GEEstudiante] CHECK CONSTRAINT [FK_GEEstudiante_ACProgramaOfrecido]
GO
-- dbo.GEEstudiante: FK_GEEstudiante_GEGenero
ALTER TABLE [dbo].[GEEstudiante]  WITH CHECK ADD  CONSTRAINT [FK_GEEstudiante_GEGenero] FOREIGN KEY([Id_Genero])

REFERENCES [dbo].[GEGenero] ([Id_Genero])
GO
ALTER TABLE [dbo].[GEEstudiante] CHECK CONSTRAINT [FK_GEEstudiante_GEGenero]
GO
-- dbo.GEEstudiante: FK_GEEstudiante_GEPoblacion
ALTER TABLE [dbo].[GEEstudiante]  WITH CHECK ADD  CONSTRAINT [FK_GEEstudiante_GEPoblacion] FOREIGN KEY([Id_Poblacion])

REFERENCES [dbo].[GEPoblacion] ([Id_Poblacion])
GO
ALTER TABLE [dbo].[GEEstudiante] CHECK CONSTRAINT [FK_GEEstudiante_GEPoblacion]
GO
-- dbo.GEEstudiante: FK_GEEstudiante_GETipoIdentidad
ALTER TABLE [dbo].[GEEstudiante]  WITH CHECK ADD  CONSTRAINT [FK_GEEstudiante_GETipoIdentidad] FOREIGN KEY([TipoId])

REFERENCES [dbo].[GETipoIdentidad] ([TipoId])
GO
ALTER TABLE [dbo].[GEEstudiante] CHECK CONSTRAINT [FK_GEEstudiante_GETipoIdentidad]
GO
-- dbo.GEImgenProg: FK_GEImgenProg_ACProgramas
ALTER TABLE [dbo].[GEImgenProg]  WITH CHECK ADD  CONSTRAINT [FK_GEImgenProg_ACProgramas] FOREIGN KEY([Id_Programa])

REFERENCES [dbo].[ACProgramas] ([Id_Programa])
GO
ALTER TABLE [dbo].[GEImgenProg] CHECK CONSTRAINT [FK_GEImgenProg_ACProgramas]
GO
-- dbo.GEImgenProg: FK_GEImgenProg_GETipoImagen
ALTER TABLE [dbo].[GEImgenProg]  WITH CHECK ADD  CONSTRAINT [FK_GEImgenProg_GETipoImagen] FOREIGN KEY([Id_TipoImagen])

REFERENCES [dbo].[GETipoImagen] ([Id_TipoImagen])
GO
ALTER TABLE [dbo].[GEImgenProg] CHECK CONSTRAINT [FK_GEImgenProg_GETipoImagen]
GO
-- dbo.GEPoblacion: FK_GEPoblacion_GEEstados
ALTER TABLE [dbo].[GEPoblacion]  WITH CHECK ADD  CONSTRAINT [FK_GEPoblacion_GEEstados] FOREIGN KEY([Id_Estado])

REFERENCES [dbo].[GEEstados] ([Id_Estado])
GO
ALTER TABLE [dbo].[GEPoblacion] CHECK CONSTRAINT [FK_GEPoblacion_GEEstados]
GO
-- dbo.GEPoblacion: FK_GEPoblacion_GEPais
ALTER TABLE [dbo].[GEPoblacion]  WITH CHECK ADD  CONSTRAINT [FK_GEPoblacion_GEPais] FOREIGN KEY([Id_Pais])

REFERENCES [dbo].[GEPais] ([Id_Pais])
GO
ALTER TABLE [dbo].[GEPoblacion] CHECK CONSTRAINT [FK_GEPoblacion_GEPais]
GO
-- Restore catalog states exactly; an empty copy does not prove historical trust.
ALTER TABLE [dbo].[CRMContacto] WITH CHECK CHECK CONSTRAINT [CRMContacto_CK_Contact_Custom];
ALTER TABLE [dbo].[CRMContacto] WITH CHECK CHECK CONSTRAINT [CRMContacto_CK_Contact_Identity];
ALTER TABLE [dbo].[CRMContacto] WITH CHECK CHECK CONSTRAINT [CRMContacto_CK_Contact_Stage];
ALTER TABLE [dbo].[CRMConversacion] WITH CHECK CHECK CONSTRAINT [CRMConversacion_CK_Conversation_Control];
ALTER TABLE [dbo].[CRMConversacion] WITH CHECK CHECK CONSTRAINT [CRMConversacion_CK_Conversation_Priority];
ALTER TABLE [dbo].[CRMConversacion] WITH CHECK CHECK CONSTRAINT [CRMConversacion_CK_Conversation_State];
ALTER TABLE [dbo].[CRMMensaje] WITH CHECK CHECK CONSTRAINT [CRMMensaje_CK_Message_Body];
ALTER TABLE [dbo].[CRMMensaje] WITH CHECK CHECK CONSTRAINT [CRMMensaje_CK_Message_Direction];
ALTER TABLE [dbo].[CRMOperacion] WITH CHECK CHECK CONSTRAINT [CRMOperacion_CK_Operation_Action];
ALTER TABLE [dbo].[CRMOperacion] WITH CHECK CHECK CONSTRAINT [CRMOperacion_CK_Operation_Actor];
ALTER TABLE [dbo].[CRMOperacion] WITH CHECK CHECK CONSTRAINT [CRMOperacion_CK_Operation_Message];
ALTER TABLE [dbo].[CRMAdmisionSeguimiento] WITH CHECK CHECK CONSTRAINT [CRMAdmisionSeguimiento_CK_Followup_Body];
ALTER TABLE [dbo].[CRMAdmisionSeguimiento] WITH CHECK CHECK CONSTRAINT [CRMAdmisionSeguimiento_CK_Followup_Revision];
ALTER TABLE [dbo].[CRMAdmisionOperacion] WITH CHECK CHECK CONSTRAINT [CRMAdmisionOperacion_CK_AdmissionOperation_Action];
ALTER TABLE [dbo].[CRMAdmisionOperacion] WITH CHECK CHECK CONSTRAINT [CRMAdmisionOperacion_CK_AdmissionOperation_Actor];
ALTER TABLE [dbo].[CRMAgenteAsignacion] WITH CHECK CHECK CONSTRAINT [CRMAgenteAsignacion_CK__Assignmen__Revis__3A2F0F71];
ALTER TABLE [dbo].[CRMAgenteAsignacion] WITH CHECK CHECK CONSTRAINT [CRMAgenteAsignacion_CK__Assignment__Mode__393AEB38];
ALTER TABLE [dbo].[CRMAgenteContexto] WITH CHECK CHECK CONSTRAINT [CRMAgenteContexto_CK__Context__2EBD5CC5];
ALTER TABLE [dbo].[CRMAgenteContexto] WITH CHECK CHECK CONSTRAINT [CRMAgenteContexto_CK__Context__MemoryJ__2CD51453];
ALTER TABLE [dbo].[CRMAgenteContexto] WITH CHECK CHECK CONSTRAINT [CRMAgenteContexto_CK__Context__Revisio__29F8A7A8];
ALTER TABLE [dbo].[CRMAgenteEjecucion] WITH CHECK CHECK CONSTRAINT [CRMAgenteEjecucion_CK__Execution__Agent__4D41E3E5];
ALTER TABLE [dbo].[CRMAgenteEjecucion] WITH CHECK CHECK CONSTRAINT [CRMAgenteEjecucion_CK__Execution__Attem__52069902];
ALTER TABLE [dbo].[CRMAgenteEjecucion] WITH CHECK CHECK CONSTRAINT [CRMAgenteEjecucion_CK__Execution__CostE__53EEE174];
ALTER TABLE [dbo].[CRMAgenteEjecucion] WITH CHECK CHECK CONSTRAINT [CRMAgenteEjecucion_CK__Execution__CostR__52FABD3B];
ALTER TABLE [dbo].[CRMAgenteEjecucion] WITH CHECK CHECK CONSTRAINT [CRMAgenteEjecucion_CK__Execution__Input__54E305AD];
ALTER TABLE [dbo].[CRMAgenteEjecucion] WITH CHECK CHECK CONSTRAINT [CRMAgenteEjecucion_CK__Execution__Laten__56CB4E1F];
ALTER TABLE [dbo].[CRMAgenteEjecucion] WITH CHECK CHECK CONSTRAINT [CRMAgenteEjecucion_CK__Execution__Outpu__55D729E6];
ALTER TABLE [dbo].[CRMAgenteEjecucion] WITH CHECK CHECK CONSTRAINT [CRMAgenteEjecucion_CK__Execution__Prici__501E5090];
ALTER TABLE [dbo].[CRMAgenteEjecucion] WITH CHECK CHECK CONSTRAINT [CRMAgenteEjecucion_CK__Execution__State__57BF7258];
ALTER TABLE [dbo].[CRMAgenteHistorial] WITH CHECK CHECK CONSTRAINT [CRMAgenteHistorial_CK__History__Documen__3EF3C48E];
ALTER TABLE [dbo].[CRMAgentePerfil] WITH CHECK CHECK CONSTRAINT [CRMAgentePerfil_CK__Profile__234BAA19];
ALTER TABLE [dbo].[CRMAgentePerfil] WITH CHECK CHECK CONSTRAINT [CRMAgentePerfil_CK__Profile__243FCE52];
ALTER TABLE [dbo].[CRMAgentePerfil] WITH CHECK CHECK CONSTRAINT [CRMAgentePerfil_CK__Profile__2533F28B];
ALTER TABLE [dbo].[CRMAgentePerfil] WITH CHECK CHECK CONSTRAINT [CRMAgentePerfil_CK__Profile__Documen__206F3D6E];
ALTER TABLE [dbo].[CRMAgentePerfil] WITH CHECK CHECK CONSTRAINT [CRMAgentePerfil_CK__Profile__Level__19C23FDF];
ALTER TABLE [dbo].[CRMAgentePerfil] WITH CHECK CHECK CONSTRAINT [CRMAgentePerfil_CK__Profile__Revisio__1F7B1935];
ALTER TABLE [dbo].[CRMAgentePerfil] WITH CHECK CHECK CONSTRAINT [CRMAgentePerfil_CK__Profile__State__1C9EAC8A];
ALTER TABLE [dbo].[CRMAgentePerfil] WITH CHECK CHECK CONSTRAINT [CRMAgentePerfil_CK__Profile__Version__1D92D0C3];
ALTER TABLE [dbo].[CRMAgenteFuenteAlcance] WITH CHECK CHECK CONSTRAINT [CRMAgenteFuenteAlcance_CK__SourceSco__Revis__328DEDA9];
ALTER TABLE [dbo].[CRMAgenteFuenteAlcance] WITH CHECK CHECK CONSTRAINT [CRMAgenteFuenteAlcance_CK__SourceScope__356A5A54];
ALTER TABLE [dbo].[CRMAgenteEtapa] WITH CHECK CHECK CONSTRAINT [CRMAgenteEtapa_CK__Stage__15F1AEFB];
ALTER TABLE [dbo].[CRMAgenteEtapa] WITH CHECK CHECK CONSTRAINT [CRMAgenteEtapa_CK__Stage__Revision__14FD8AC2];
ALTER TABLE [dbo].[CRMAgenteConsumo] WITH CHECK CHECK CONSTRAINT [CRMAgenteConsumo_CK__Usage__ChainJson__44AC9DE4];
ALTER TABLE [dbo].[CRMAgenteConsumo] WITH CHECK CHECK CONSTRAINT [CRMAgenteConsumo_CK__Usage__State__47890A8F];
ALTER TABLE [dbo].[CRMAgenteConsumo] WITH CHECK CHECK CONSTRAINT [CRMAgenteConsumo_CK__Usage__TokensRes__45A0C21D];
ALTER TABLE [dbo].[CRMAgenteConsumo] WITH CHECK CHECK CONSTRAINT [CRMAgenteConsumo_CK__Usage__TokensUse__4694E656];
ALTER TABLE [dbo].[CRMIAAdmisionPolitica] WITH CHECK CHECK CONSTRAINT [CRMIAAdmisionPolitica_CK__Admission__Docum__61B2F0E6];
ALTER TABLE [dbo].[CRMIAAdmisionPolitica] WITH CHECK CHECK CONSTRAINT [CRMIAAdmisionPolitica_CK__Admission__Polic__5CEE3BC9];
ALTER TABLE [dbo].[CRMIAConfiguracion] WITH CHECK CHECK CONSTRAINT [CRMIAConfiguracion_CK__Configura__Confi__26922B18];
ALTER TABLE [dbo].[CRMIAConfiguracion] WITH CHECK CHECK CONSTRAINT [CRMIAConfiguracion_CK__Configura__Docum__287A738A];
ALTER TABLE [dbo].[CRMIAConfiguracion] WITH CHECK CHECK CONSTRAINT [CRMIAConfiguracion_CK__Configura__Revis__27864F51];
ALTER TABLE [dbo].[CRMIAConexion] WITH CHECK CHECK CONSTRAINT [CRMIAConexion_CK__Connectio__Conne__2C4B046E];
ALTER TABLE [dbo].[CRMIAConexion] WITH CHECK CHECK CONSTRAINT [CRMIAConexion_CK__Connectio__Revis__2E334CE0];
ALTER TABLE [dbo].[CRMIACredencial] WITH CHECK CHECK CONSTRAINT [CRMIACredencial_CK_crm_ai_Credential_Provider];
ALTER TABLE [dbo].[CRMConocimientoDocumento] WITH CHECK CHECK CONSTRAINT [CRMConocimientoDocumento_CK__Knowledge__ByteL__658381CA];
ALTER TABLE [dbo].[CRMConocimientoDocumento] WITH CHECK CHECK CONSTRAINT [CRMConocimientoDocumento_CK__Knowledge__State__6677A603];
ALTER TABLE [dbo].[CRMConocimientoTermino] WITH CHECK CHECK CONSTRAINT [CRMConocimientoTermino_CK__Knowledge__Frequ__70F53476];
ALTER TABLE [dbo].[CRMProspectoMemoria] WITH CHECK CHECK CONSTRAINT [CRMProspectoMemoria_CK__ProspectM__Docum__7896563E];
ALTER TABLE [dbo].[CRMRespuestaTrabajo] WITH CHECK CHECK CONSTRAINT [CRMRespuestaTrabajo_CK__ResponseJ__Resul__06E47595];
ALTER TABLE [dbo].[CRMRespuestaTrabajo] WITH CHECK CHECK CONSTRAINT [CRMRespuestaTrabajo_CK__ResponseJ__State__00377806];
ALTER TABLE [dbo].[CRMAnalisisIntento] WITH CHECK CHECK CONSTRAINT [CRMAnalisisIntento_CK_AnalysisAttempt];
ALTER TABLE [dbo].[CRMAnalisisConversacionEstado] WITH CHECK CHECK CONSTRAINT [CRMAnalisisConversacionEstado_CK_AnalysisState];
ALTER TABLE [dbo].[CRMAnalisisOperacion] WITH CHECK CHECK CONSTRAINT [CRMAnalisisOperacion_CK_AnalysisOperation];
ALTER TABLE [dbo].[CRMAnalisisPolitica] WITH CHECK CHECK CONSTRAINT [CRMAnalisisPolitica_CK_AnalysisPolicy];
ALTER TABLE [dbo].[CRMCanalCuenta] WITH CHECK CHECK CONSTRAINT [CRMCanalCuenta_CK__Account__Capabil__76E317F6];
ALTER TABLE [dbo].[CRMCanalCuenta] WITH CHECK CHECK CONSTRAINT [CRMCanalCuenta_CK__Account__Channel__78CB6068];
ALTER TABLE [dbo].[CRMCanalCuenta] WITH CHECK CHECK CONSTRAINT [CRMCanalCuenta_CK__Account__Configu__73128712];
ALTER TABLE [dbo].[CRMConversacionControl] WITH CHECK CHECK CONSTRAINT [CRMConversacionControl_CK__Conversat__Epoch__3F5DD8E2];
ALTER TABLE [dbo].[CRMConversacionControl] WITH CHECK CHECK CONSTRAINT [CRMConversacionControl_CK__Conversat__ReadS__41462154];
ALTER TABLE [dbo].[CRMConversacionPerfil] WITH CHECK CHECK CONSTRAINT [CRMConversacionPerfil_CK__Conversat__LeadS__38B0DB53];
ALTER TABLE [dbo].[CRMConversacionPerfil] WITH CHECK CHECK CONSTRAINT [CRMConversacionPerfil_CK__Conversat__Tempe__39A4FF8C];
ALTER TABLE [dbo].[CRMMensajeExterno] WITH CHECK CHECK CONSTRAINT [CRMMensajeExterno_CK__ExternalM__Paylo__0DC67D4E];
ALTER TABLE [dbo].[CRMArchivoMultimedia] WITH CHECK CHECK CONSTRAINT [CRMArchivoMultimedia_CK__MediaAsse__ByteL__5270AD56];
ALTER TABLE [dbo].[CRMArchivoMultimedia] WITH CHECK CHECK CONSTRAINT [CRMArchivoMultimedia_CK__MediaAsse__Durat__5364D18F];
ALTER TABLE [dbo].[CRMArchivoMultimedia] WITH CHECK CHECK CONSTRAINT [CRMArchivoMultimedia_CK__MediaAsse__Provi__554D1A01];
ALTER TABLE [dbo].[CRMArchivoMultimedia] WITH CHECK CHECK CONSTRAINT [CRMArchivoMultimedia_CK__MediaAsse__Sourc__4F9440AB];
ALTER TABLE [dbo].[CRMArchivoMultimedia] WITH CHECK CHECK CONSTRAINT [CRMArchivoMultimedia_CK__MediaAsse__State__508864E4];
ALTER TABLE [dbo].[CRMArchivoMultimedia] WITH CHECK CHECK CONSTRAINT [CRMArchivoMultimedia_CK__MediaAsset__591DAAE5];
ALTER TABLE [dbo].[CRMArchivoMultimedia] WITH CHECK CHECK CONSTRAINT [CRMArchivoMultimedia_CK__MediaAsset__5A11CF1E];
ALTER TABLE [dbo].[CRMArchivoMultimedia] WITH CHECK CHECK CONSTRAINT [CRMArchivoMultimedia_CK__MediaAsset__Kind__517C891D];
ALTER TABLE [dbo].[CRMMensajeRuta] WITH CHECK CHECK CONSTRAINT [CRMMensajeRuta_CK__MessageRo__Actor__46FEFAAA];
ALTER TABLE [dbo].[CRMMensajeRuta] WITH CHECK CHECK CONSTRAINT [CRMMensajeRuta_CK__MessageRo__Contr__47F31EE3];
ALTER TABLE [dbo].[CRMMensajeRuta] WITH CHECK CHECK CONSTRAINT [CRMMensajeRuta_CK__MessageRoute__48E7431C];
ALTER TABLE [dbo].[CRMColaSalida] WITH CHECK CHECK CONSTRAINT [CRMColaSalida_CK__outbound___Paylo__137F56A4];
ALTER TABLE [dbo].[CRMColaSalida] WITH CHECK CHECK CONSTRAINT [CRMColaSalida_CK__outbound___State__18440BC1];
ALTER TABLE [dbo].[CRMComentarioSocial] WITH CHECK CHECK CONSTRAINT [CRMComentarioSocial_CK__social_co__Paylo__1D08C0DE];
ALTER TABLE [dbo].[CRMEventoWebhook] WITH CHECK CHECK CONSTRAINT [CRMEventoWebhook_CK__webhook_e__Paylo__7F785DF7];
ALTER TABLE [dbo].[CRMConfiguracion] WITH CHECK CHECK CONSTRAINT [CRMConfiguracion_CK_CrmConfiguration];
ALTER TABLE [dbo].[CRMConfiguracionOperacion] WITH CHECK CHECK CONSTRAINT [CRMConfiguracionOperacion_CK_CrmConfigOperation];
ALTER TABLE [dbo].[CRMConversacionEvento] WITH CHECK CHECK CONSTRAINT [CRMConversacionEvento_CK_Event_Attempts];
ALTER TABLE [dbo].[CRMConversacionEvento] WITH CHECK CHECK CONSTRAINT [CRMConversacionEvento_CK_Event_Lease];
ALTER TABLE [dbo].[CRMConversacionEvento] WITH CHECK CHECK CONSTRAINT [CRMConversacionEvento_CK_Event_Source];
ALTER TABLE [dbo].[CRMConversacionEvento] WITH CHECK CHECK CONSTRAINT [CRMConversacionEvento_CK_Event_State];
ALTER TABLE [dbo].[CRMEventoReintentoOperacion] WITH CHECK CHECK CONSTRAINT [CRMEventoReintentoOperacion_CK_EventRetry_Count];
ALTER TABLE [dbo].[CRMContactoPerfilInstitucional] WITH CHECK CHECK CONSTRAINT [CRMContactoPerfilInstitucional_CK_IdentityProfile_Document];
ALTER TABLE [dbo].[CRMBandejaAgente] WITH CHECK CHECK CONSTRAINT [CRMBandejaAgente_CK_InboxAgent_Name];
ALTER TABLE [dbo].[CRMBandejaOperacion] WITH CHECK CHECK CONSTRAINT [CRMBandejaOperacion_CK_InboxOperation_Action];
ALTER TABLE [dbo].[CRMBandejaOperacion] WITH CHECK CHECK CONSTRAINT [CRMBandejaOperacion_CK_InboxOperation_Actor];
ALTER TABLE [dbo].[CRMBandejaPoliticaSLA] WITH CHECK CHECK CONSTRAINT [CRMBandejaPoliticaSLA_CK_InboxSlaPolicy_Single];
ALTER TABLE [dbo].[CRMBandejaPoliticaSLA] WITH CHECK CHECK CONSTRAINT [CRMBandejaPoliticaSLA_CK_InboxSlaPolicy_Threshold];
ALTER TABLE [dbo].[CRMBandejaTarea] WITH CHECK CHECK CONSTRAINT [CRMBandejaTarea_CK_InboxTask_Priority];
ALTER TABLE [dbo].[CRMBandejaTarea] WITH CHECK CHECK CONSTRAINT [CRMBandejaTarea_CK_InboxTask_Status];
ALTER TABLE [dbo].[CRMBandejaTarea] WITH CHECK CHECK CONSTRAINT [CRMBandejaTarea_CK_InboxTask_Title];
ALTER TABLE [dbo].[CRMCuentaCadencia] WITH CHECK CHECK CONSTRAINT [CRMCuentaCadencia_CK__AccountCa__Daily__46C9F080];
ALTER TABLE [dbo].[CRMCuentaCadencia] WITH CHECK CHECK CONSTRAINT [CRMCuentaCadencia_CK__AccountCa__MinIn__45D5CC47];
ALTER TABLE [dbo].[CRMCuentaCadencia] WITH CHECK CHECK CONSTRAINT [CRMCuentaCadencia_CK__AccountCa__Reser__48B238F2];
ALTER TABLE [dbo].[CRMCuentaCadencia] WITH CHECK CHECK CONSTRAINT [CRMCuentaCadencia_CK__AccountCa__Revis__4A9A8164];
ALTER TABLE [dbo].[CRMCuentaCadencia] WITH CHECK CHECK CONSTRAINT [CRMCuentaCadencia_CK__AccountCadence__4B8EA59D];
ALTER TABLE [dbo].[CRMCampana] WITH CHECK CHECK CONSTRAINT [CRMCampana_CK__Campaign__5BC50D66];
ALTER TABLE [dbo].[CRMCampana] WITH CHECK CHECK CONSTRAINT [CRMCampana_CK__Campaign__5CB9319F];
ALTER TABLE [dbo].[CRMCampana] WITH CHECK CHECK CONSTRAINT [CRMCampana_CK__Campaign__5DAD55D8];
ALTER TABLE [dbo].[CRMCampana] WITH CHECK CHECK CONSTRAINT [CRMCampana_CK__Campaign__Inclus__57005849];
ALTER TABLE [dbo].[CRMCampana] WITH CHECK CHECK CONSTRAINT [CRMCampana_CK__Campaign__Kind__4F5F3681];
ALTER TABLE [dbo].[CRMCampana] WITH CHECK CHECK CONSTRAINT [CRMCampana_CK__Campaign__Revisi__55180FD7];
ALTER TABLE [dbo].[CRMCampana] WITH CHECK CHECK CONSTRAINT [CRMCampana_CK__Campaign__Segmen__532FC765];
ALTER TABLE [dbo].[CRMCampana] WITH CHECK CHECK CONSTRAINT [CRMCampana_CK__Campaign__Status__51477EF3];
ALTER TABLE [dbo].[CRMCampanaDestinatario] WITH CHECK CHECK CONSTRAINT [CRMCampanaDestinatario_CK__CampaignR__Accou__691F0884];
ALTER TABLE [dbo].[CRMCampanaDestinatario] WITH CHECK CHECK CONSTRAINT [CRMCampanaDestinatario_CK__CampaignR__Attem__6ED7E1DA];
ALTER TABLE [dbo].[CRMCampanaDestinatario] WITH CHECK CHECK CONSTRAINT [CRMCampanaDestinatario_CK__CampaignR__Campa__6736C012];
ALTER TABLE [dbo].[CRMCampanaDestinatario] WITH CHECK CHECK CONSTRAINT [CRMCampanaDestinatario_CK__CampaignR__Contr__6A132CBD];
ALTER TABLE [dbo].[CRMCampanaDestinatario] WITH CHECK CHECK CONSTRAINT [CRMCampanaDestinatario_CK__CampaignR__Evide__6CEF9968];
ALTER TABLE [dbo].[CRMCampanaDestinatario] WITH CHECK CHECK CONSTRAINT [CRMCampanaDestinatario_CK__CampaignR__Inclu__6B0750F6];
ALTER TABLE [dbo].[CRMCampanaDestinatario] WITH CHECK CHECK CONSTRAINT [CRMCampanaDestinatario_CK__CampaignR__Input__6BFB752F];
ALTER TABLE [dbo].[CRMCampanaDestinatario] WITH CHECK CHECK CONSTRAINT [CRMCampanaDestinatario_CK__CampaignR__RuleR__682AE44B];
ALTER TABLE [dbo].[CRMCampanaDestinatario] WITH CHECK CHECK CONSTRAINT [CRMCampanaDestinatario_CK__CampaignR__Statu__654E77A0];
ALTER TABLE [dbo].[CRMCampanaDestinatario] WITH CHECK CHECK CONSTRAINT [CRMCampanaDestinatario_CK__CampaignRecipien__7490BB30];
ALTER TABLE [dbo].[CRMCampanaDestinatario] WITH CHECK CHECK CONSTRAINT [CRMCampanaDestinatario_CK__CampaignRecipien__7584DF69];
ALTER TABLE [dbo].[CRMCampanaDestinatario] WITH CHECK CHECK CONSTRAINT [CRMCampanaDestinatario_CK__CampaignRecipien__767903A2];
ALTER TABLE [dbo].[CRMAbandonoEvaluacion] WITH CHECK CHECK CONSTRAINT [CRMAbandonoEvaluacion_CK__ChurnAsse__Compu__0D917324];
ALTER TABLE [dbo].[CRMAbandonoEvaluacion] WITH CHECK CHECK CONSTRAINT [CRMAbandonoEvaluacion_CK__ChurnAsse__Evide__12562841];
ALTER TABLE [dbo].[CRMAbandonoEvaluacion] WITH CHECK CHECK CONSTRAINT [CRMAbandonoEvaluacion_CK__ChurnAsse__Input__0C9D4EEB];
ALTER TABLE [dbo].[CRMAbandonoEvaluacion] WITH CHECK CHECK CONSTRAINT [CRMAbandonoEvaluacion_CK__ChurnAsse__LeadR__0F79BB96];
ALTER TABLE [dbo].[CRMAbandonoEvaluacion] WITH CHECK CHECK CONSTRAINT [CRMAbandonoEvaluacion_CK__ChurnAsse__Reaso__11620408];
ALTER TABLE [dbo].[CRMAbandonoEvaluacion] WITH CHECK CHECK CONSTRAINT [CRMAbandonoEvaluacion_CK__ChurnAsse__Statu__106DDFCF];
ALTER TABLE [dbo].[CRMAbandonoEvaluacion] WITH CHECK CHECK CONSTRAINT [CRMAbandonoEvaluacion_CK__ChurnAssessment__143E70B3];
ALTER TABLE [dbo].[CRMAbandonoEvaluacion] WITH CHECK CHECK CONSTRAINT [CRMAbandonoEvaluacion_CK__ChurnAssessment__153294EC];
ALTER TABLE [dbo].[CRMContactoConsentimiento] WITH CHECK CHECK CONSTRAINT [CRMContactoConsentimiento_CK__ContactCo__Evide__2D0A1E7D];
ALTER TABLE [dbo].[CRMContactoConsentimiento] WITH CHECK CHECK CONSTRAINT [CRMContactoConsentimiento_CK__ContactCo__Purpo__29398D99];
ALTER TABLE [dbo].[CRMContactoConsentimiento] WITH CHECK CHECK CONSTRAINT [CRMContactoConsentimiento_CK__ContactCo__Statu__2B21D60B];
ALTER TABLE [dbo].[CRMContactoConsentimiento] WITH CHECK CHECK CONSTRAINT [CRMContactoConsentimiento_CK__ContactCo__Versi__2C15FA44];
ALTER TABLE [dbo].[CRMContactoConsentimiento] WITH CHECK CHECK CONSTRAINT [CRMContactoConsentimiento_CK__ContactConsent__2FE68B28];
ALTER TABLE [dbo].[CRMContactoConsentimiento] WITH CHECK CHECK CONSTRAINT [CRMContactoConsentimiento_CK__ContactConsent__30DAAF61];
ALTER TABLE [dbo].[CRMContactoConsentimiento] WITH CHECK CHECK CONSTRAINT [CRMContactoConsentimiento_CK__ContactConsent__31CED39A];
ALTER TABLE [dbo].[CRMCampanaEvaluacionEjecucion] WITH CHECK CHECK CONSTRAINT [CRMCampanaEvaluacionEjecucion_CK__Evaluatio__Attem__01EAB64E];
ALTER TABLE [dbo].[CRMCampanaEvaluacionEjecucion] WITH CHECK CHECK CONSTRAINT [CRMCampanaEvaluacionEjecucion_CK__Evaluatio__Count__03D2FEC0];
ALTER TABLE [dbo].[CRMCampanaEvaluacionEjecucion] WITH CHECK CHECK CONSTRAINT [CRMCampanaEvaluacionEjecucion_CK__Evaluatio__State__7E1A256A];
ALTER TABLE [dbo].[CRMCampanaEvaluacionEjecucion] WITH CHECK CHECK CONSTRAINT [CRMCampanaEvaluacionEjecucion_CK__Evaluatio__Trigg__7A499486];
ALTER TABLE [dbo].[CRMCampanaEvaluacionEjecucion] WITH CHECK CHECK CONSTRAINT [CRMCampanaEvaluacionEjecucion_CK__Evaluation__Kind__7955704D];
ALTER TABLE [dbo].[CRMMensajePlantilla] WITH CHECK CHECK CONSTRAINT [CRMMensajePlantilla_CK__MessageTe__Accou__1BDF927B];
ALTER TABLE [dbo].[CRMMensajePlantilla] WITH CHECK CHECK CONSTRAINT [CRMMensajePlantilla_CK__MessageTe__Compo__21986BD1];
ALTER TABLE [dbo].[CRMMensajePlantilla] WITH CHECK CHECK CONSTRAINT [CRMMensajePlantilla_CK__MessageTe__Statu__1DC7DAED];
ALTER TABLE [dbo].[CRMMensajePlantilla] WITH CHECK CHECK CONSTRAINT [CRMMensajePlantilla_CK__MessageTe__Statu__20A44798];
ALTER TABLE [dbo].[CRMMensajePlantilla] WITH CHECK CHECK CONSTRAINT [CRMMensajePlantilla_CK__MessageTe__Versi__1EBBFF26];
ALTER TABLE [dbo].[CRMMensajePlantilla] WITH CHECK CHECK CONSTRAINT [CRMMensajePlantilla_CK__MessageTemplate__228C900A];
ALTER TABLE [dbo].[CRMCampanaPolitica] WITH CHECK CHECK CONSTRAINT [CRMCampanaPolitica_CK__Policy__Interval__0E508D33];
ALTER TABLE [dbo].[CRMCampanaPolitica] WITH CHECK CHECK CONSTRAINT [CRMCampanaPolitica_CK__Policy__PolicyId__07A38FA4];
ALTER TABLE [dbo].[CRMCampanaPolitica] WITH CHECK CHECK CONSTRAINT [CRMCampanaPolitica_CK__Policy__Revision__098BD816];
ALTER TABLE [dbo].[CRMCampanaPolitica] WITH CHECK CHECK CONSTRAINT [CRMCampanaPolitica_CK__Policy__StageWei__0B742088];
ALTER TABLE [dbo].[CRMRecontactoRegla] WITH CHECK CHECK CONSTRAINT [CRMRecontactoRegla_CK__Remarketi__Coold__369388B7];
ALTER TABLE [dbo].[CRMRecontactoRegla] WITH CHECK CHECK CONSTRAINT [CRMRecontactoRegla_CK__Remarketi__Inact__359F647E];
ALTER TABLE [dbo].[CRMRecontactoRegla] WITH CHECK CHECK CONSTRAINT [CRMRecontactoRegla_CK__Remarketi__Minim__387BD129];
ALTER TABLE [dbo].[CRMRecontactoRegla] WITH CHECK CHECK CONSTRAINT [CRMRecontactoRegla_CK__Remarketi__Revis__3B583DD4];
ALTER TABLE [dbo].[CRMRecontactoRegla] WITH CHECK CHECK CONSTRAINT [CRMRecontactoRegla_CK__Remarketi__Stage__401CF2F1];
ALTER TABLE [dbo].[CRMRecontactoRegla] WITH CHECK CHECK CONSTRAINT [CRMRecontactoRegla_CK__RemarketingRule__4111172A];
ALTER TABLE [dbo].[CRMRecontactoRegla] WITH CHECK CHECK CONSTRAINT [CRMRecontactoRegla_CK__RemarketingRule__42053B63];
ALTER TABLE [dbo].[CRMContactoUnificacion] WITH CHECK CHECK CONSTRAINT [CRMContactoUnificacion_CK_MergeCase];
ALTER TABLE [dbo].[CRMUnificacionOperacion] WITH CHECK CHECK CONSTRAINT [CRMUnificacionOperacion_CK_MergeOperation];
ALTER TABLE [dbo].[CRMEstrategiaPlanEvaluacion] WITH CHECK CHECK CONSTRAINT [CRMEstrategiaPlanEvaluacion_CK_StrategyPlan];
ALTER TABLE [dbo].[CRMEstrategiaOperacion] WITH CHECK CHECK CONSTRAINT [CRMEstrategiaOperacion_CK_StrategyOperation];
ALTER TABLE [dbo].[CRMEstrategiaPolitica] WITH CHECK CHECK CONSTRAINT [CRMEstrategiaPolitica_CK_StrategyPolicy];
ALTER TABLE [dbo].[CRMConversacion] WITH CHECK CHECK CONSTRAINT [CRMConversacion_FK_Conversation_Contact];
ALTER TABLE [dbo].[CRMMensaje] WITH CHECK CHECK CONSTRAINT [CRMMensaje_FK_Message_Conversation];
ALTER TABLE [dbo].[CRMOperacion] WITH CHECK CHECK CONSTRAINT [CRMOperacion_FK_Operation_Contact];
ALTER TABLE [dbo].[CRMOperacion] WITH CHECK CHECK CONSTRAINT [CRMOperacion_FK_Operation_Conversation];
ALTER TABLE [dbo].[CRMOperacion] WITH CHECK CHECK CONSTRAINT [CRMOperacion_FK_Operation_Message];
ALTER TABLE [dbo].[CRMAdmisionSeguimiento] WITH CHECK CHECK CONSTRAINT [CRMAdmisionSeguimiento_FK_Followup_Case];
ALTER TABLE [dbo].[CRMAdmisionOperacion] WITH CHECK CHECK CONSTRAINT [CRMAdmisionOperacion_FK_AdmissionOperation_Followup];
ALTER TABLE [dbo].[CRMAgenteAsignacion] WITH CHECK CHECK CONSTRAINT [CRMAgenteAsignacion_FK__Assignmen__Conve__3846C6FF];
ALTER TABLE [dbo].[CRMAgenteAsignacion] WITH CHECK CHECK CONSTRAINT [CRMAgenteAsignacion_FK__Assignment__3B2333AA];
ALTER TABLE [dbo].[CRMAgenteContexto] WITH CHECK CHECK CONSTRAINT [CRMAgenteContexto_FK__Context__2DC9388C];
ALTER TABLE [dbo].[CRMAgenteContexto] WITH CHECK CHECK CONSTRAINT [CRMAgenteContexto_FK__Context__Convers__2904836F];
ALTER TABLE [dbo].[CRMAgenteEjecucion] WITH CHECK CHECK CONSTRAINT [CRMAgenteEjecucion_FK__Execution__Agent__4C4DBFAC];
ALTER TABLE [dbo].[CRMAgenteEjecucion] WITH CHECK CHECK CONSTRAINT [CRMAgenteEjecucion_FK__Execution__Conve__4E36081E];
ALTER TABLE [dbo].[CRMAgenteEjecucion] WITH CHECK CHECK CONSTRAINT [CRMAgenteEjecucion_FK__Execution__Reque__4B599B73];
ALTER TABLE [dbo].[CRMAgentePerfil] WITH CHECK CHECK CONSTRAINT [CRMAgentePerfil_FK__Profile__225785E0];
ALTER TABLE [dbo].[CRMAgentePerfil] WITH CHECK CHECK CONSTRAINT [CRMAgentePerfil_FK__Profile__AgentId__18CE1BA6];
ALTER TABLE [dbo].[CRMAgentePerfil] WITH CHECK CHECK CONSTRAINT [CRMAgentePerfil_FK__Profile__ParentI__1AB66418];
ALTER TABLE [dbo].[CRMAgenteFuenteAlcance] WITH CHECK CHECK CONSTRAINT [CRMAgenteFuenteAlcance_FK__SourceSco__Docum__3199C970];
ALTER TABLE [dbo].[CRMAgenteFuenteAlcance] WITH CHECK CHECK CONSTRAINT [CRMAgenteFuenteAlcance_FK__SourceScope__3476361B];
ALTER TABLE [dbo].[CRMAgenteConsumo] WITH CHECK CHECK CONSTRAINT [CRMAgenteConsumo_FK__Usage__AgentId__43B879AB];
ALTER TABLE [dbo].[CRMConocimientoFragmento] WITH CHECK CHECK CONSTRAINT [CRMConocimientoFragmento_FK__Knowledge__Docum__6D24A392];
ALTER TABLE [dbo].[CRMConocimientoTermino] WITH CHECK CHECK CONSTRAINT [CRMConocimientoTermino_FK__Knowledge__Chunk__7001103D];
ALTER TABLE [dbo].[CRMProspectoMemoria] WITH CHECK CHECK CONSTRAINT [CRMProspectoMemoria_FK__ProspectM__Conve__73D1A121];
ALTER TABLE [dbo].[CRMRespuestaTrabajo] WITH CHECK CHECK CONSTRAINT [CRMRespuestaTrabajo_FK__ResponseJ__Conve__7D5B0B5B];
ALTER TABLE [dbo].[CRMRespuestaTrabajo] WITH CHECK CHECK CONSTRAINT [CRMRespuestaTrabajo_FK__ResponseJ__Ident__7E4F2F94];
ALTER TABLE [dbo].[CRMRespuestaTrabajo] WITH CHECK CHECK CONSTRAINT [CRMRespuestaTrabajo_FK__ResponseJ__Messa__7C66E722];
ALTER TABLE [dbo].[CRMRespuestaTrabajo] WITH CHECK CHECK CONSTRAINT [CRMRespuestaTrabajo_FK__ResponseJ__Respo__040808EA];
ALTER TABLE [dbo].[CRMRespuestaTrabajo] WITH CHECK CHECK CONSTRAINT [CRMRespuestaTrabajo_FK__ResponseJ__TaskI__04FC2D23];
ALTER TABLE [dbo].[CRMAnalisisIntento] WITH CHECK CHECK CONSTRAINT [CRMAnalisisIntento_FK_AnalysisAttempt_Conversation];
ALTER TABLE [dbo].[CRMAnalisisConversacionEstado] WITH CHECK CHECK CONSTRAINT [CRMAnalisisConversacionEstado_FK_AnalysisState_Conversation];
ALTER TABLE [dbo].[CRMAnalisisEvaluacionHumana] WITH CHECK CHECK CONSTRAINT [CRMAnalisisEvaluacionHumana_FK_AnalysisFeedback_Conversation];
ALTER TABLE [dbo].[CRMAnalisisRecepcion] WITH CHECK CHECK CONSTRAINT [CRMAnalisisRecepcion_FK_AnalysisReceipt_Conversation];
ALTER TABLE [dbo].[CRMAnalisisRecepcion] WITH CHECK CHECK CONSTRAINT [CRMAnalisisRecepcion_FK_AnalysisReceipt_Event];
ALTER TABLE [dbo].[CRMConversacionControl] WITH CHECK CHECK CONSTRAINT [CRMConversacionControl_FK__Conversat__Conve__3D759070];
ALTER TABLE [dbo].[CRMConversacionPerfil] WITH CHECK CHECK CONSTRAINT [CRMConversacionPerfil_FK__Conversat__Conve__37BCB71A];
ALTER TABLE [dbo].[CRMCanalCredencial] WITH CHECK CHECK CONSTRAINT [CRMCanalCredencial_FK__Credentia__Chann__7BA7CD13];
ALTER TABLE [dbo].[CRMIdentidadExterna] WITH CHECK CHECK CONSTRAINT [CRMIdentidadExterna_FK__ExternalI__Chann__07197FBF];
ALTER TABLE [dbo].[CRMIdentidadExterna] WITH CHECK CHECK CONSTRAINT [CRMIdentidadExterna_FK__ExternalI__Conta__080DA3F8];
ALTER TABLE [dbo].[CRMIdentidadExterna] WITH CHECK CHECK CONSTRAINT [CRMIdentidadExterna_FK__ExternalI__Conve__0901C831];
ALTER TABLE [dbo].[CRMMensajeExterno] WITH CHECK CHECK CONSTRAINT [CRMMensajeExterno_FK__ExternalM__Chann__0BDE34DC];
ALTER TABLE [dbo].[CRMMensajeExterno] WITH CHECK CHECK CONSTRAINT [CRMMensajeExterno_FK__ExternalM__Messa__0CD25915];
ALTER TABLE [dbo].[CRMArchivoMultimedia] WITH CHECK CHECK CONSTRAINT [CRMArchivoMultimedia_FK__MediaAsse__Chann__4EA01C72];
ALTER TABLE [dbo].[CRMArchivoMultimedia] WITH CHECK CHECK CONSTRAINT [CRMArchivoMultimedia_FK__MediaAsse__Conve__4BC3AFC7];
ALTER TABLE [dbo].[CRMArchivoMultimedia] WITH CHECK CHECK CONSTRAINT [CRMArchivoMultimedia_FK__MediaAsse__Ident__4DABF839];
ALTER TABLE [dbo].[CRMArchivoMultimedia] WITH CHECK CHECK CONSTRAINT [CRMArchivoMultimedia_FK__MediaAsse__Messa__4CB7D400];
ALTER TABLE [dbo].[CRMMensajeRuta] WITH CHECK CHECK CONSTRAINT [CRMMensajeRuta_FK__MessageRo__Ident__4516B238];
ALTER TABLE [dbo].[CRMMensajeRuta] WITH CHECK CHECK CONSTRAINT [CRMMensajeRuta_FK__MessageRo__Messa__44228DFF];
ALTER TABLE [dbo].[CRMMensajeRuta] WITH CHECK CHECK CONSTRAINT [CRMMensajeRuta_FK__MessageRo__Queue__460AD671];
ALTER TABLE [dbo].[CRMColaSalida] WITH CHECK CHECK CONSTRAINT [CRMColaSalida_FK__outbound___Chann__10A2E9F9];
ALTER TABLE [dbo].[CRMColaSalida] WITH CHECK CHECK CONSTRAINT [CRMColaSalida_FK__outbound___Ident__11970E32];
ALTER TABLE [dbo].[CRMColaSalida] WITH CHECK CHECK CONSTRAINT [CRMColaSalida_FK__outbound___Messa__128B326B];
ALTER TABLE [dbo].[CRMComentarioSocial] WITH CHECK CHECK CONSTRAINT [CRMComentarioSocial_FK__social_co__Chann__1C149CA5];
ALTER TABLE [dbo].[CRMConversacionEvento] WITH CHECK CHECK CONSTRAINT [CRMConversacionEvento_FK_Event_Conversation];
ALTER TABLE [dbo].[CRMEventoPreparacion] WITH CHECK CHECK CONSTRAINT [CRMEventoPreparacion_FK_Preparation_Conversation];
ALTER TABLE [dbo].[CRMEventoPreparacion] WITH CHECK CHECK CONSTRAINT [CRMEventoPreparacion_FK_Preparation_Event];
ALTER TABLE [dbo].[CRMContactoPerfilInstitucional] WITH CHECK CHECK CONSTRAINT [CRMContactoPerfilInstitucional_FK_IdentityProfile_Contact];
ALTER TABLE [dbo].[CRMBandejaAsignacion] WITH CHECK CHECK CONSTRAINT [CRMBandejaAsignacion_FK_InboxAssignment_Agent];
ALTER TABLE [dbo].[CRMBandejaAsignacion] WITH CHECK CHECK CONSTRAINT [CRMBandejaAsignacion_FK_InboxAssignment_Conversation];
ALTER TABLE [dbo].[CRMBandejaAsignacion] WITH CHECK CHECK CONSTRAINT [CRMBandejaAsignacion_FK_InboxAssignment_Human];
ALTER TABLE [dbo].[CRMBandejaTarea] WITH CHECK CHECK CONSTRAINT [CRMBandejaTarea_FK_InboxTask_Conversation];
ALTER TABLE [dbo].[CRMBandejaTarea] WITH CHECK CHECK CONSTRAINT [CRMBandejaTarea_FK_InboxTask_Human];
ALTER TABLE [dbo].[CRMCuentaCadencia] WITH CHECK CHECK CONSTRAINT [CRMCuentaCadencia_FK__AccountCa__Chann__44E1A80E];
ALTER TABLE [dbo].[CRMCampana] WITH CHECK CHECK CONSTRAINT [CRMCampana_FK__Campaign__59DCC4F4];
ALTER TABLE [dbo].[CRMCampana] WITH CHECK CHECK CONSTRAINT [CRMCampana_FK__Campaign__5AD0E92D];
ALTER TABLE [dbo].[CRMCampana] WITH CHECK CHECK CONSTRAINT [CRMCampana_FK__Campaign__RuleId__523BA32C];
ALTER TABLE [dbo].[CRMCampanaDestinatario] WITH CHECK CHECK CONSTRAINT [CRMCampanaDestinatario_FK__CampaignR__Campa__71B44E85];
ALTER TABLE [dbo].[CRMCampanaDestinatario] WITH CHECK CHECK CONSTRAINT [CRMCampanaDestinatario_FK__CampaignR__Conta__62720AF5];
ALTER TABLE [dbo].[CRMCampanaDestinatario] WITH CHECK CHECK CONSTRAINT [CRMCampanaDestinatario_FK__CampaignR__Conve__63662F2E];
ALTER TABLE [dbo].[CRMCampanaDestinatario] WITH CHECK CHECK CONSTRAINT [CRMCampanaDestinatario_FK__CampaignR__Ident__617DE6BC];
ALTER TABLE [dbo].[CRMCampanaDestinatario] WITH CHECK CHECK CONSTRAINT [CRMCampanaDestinatario_FK__CampaignR__Queue__66429BD9];
ALTER TABLE [dbo].[CRMCampanaDestinatario] WITH CHECK CHECK CONSTRAINT [CRMCampanaDestinatario_FK__CampaignRecipien__72A872BE];
ALTER TABLE [dbo].[CRMCampanaDestinatario] WITH CHECK CHECK CONSTRAINT [CRMCampanaDestinatario_FK__CampaignRecipien__739C96F7];
ALTER TABLE [dbo].[CRMAbandonoEvaluacion] WITH CHECK CHECK CONSTRAINT [CRMAbandonoEvaluacion_FK__ChurnAsse__Conve__0AB50679];
ALTER TABLE [dbo].[CRMAbandonoEvaluacion] WITH CHECK CHECK CONSTRAINT [CRMAbandonoEvaluacion_FK__ChurnAsse__Ident__0BA92AB2];
ALTER TABLE [dbo].[CRMAbandonoEvaluacion] WITH CHECK CHECK CONSTRAINT [CRMAbandonoEvaluacion_FK__ChurnAsse__RunId__04C722F9];
ALTER TABLE [dbo].[CRMContactoConsentimiento] WITH CHECK CHECK CONSTRAINT [CRMContactoConsentimiento_FK__ContactCo__Chann__28456960];
ALTER TABLE [dbo].[CRMContactoConsentimiento] WITH CHECK CHECK CONSTRAINT [CRMContactoConsentimiento_FK__ContactCo__Ident__27514527];
ALTER TABLE [dbo].[CRMContactoConsentimiento] WITH CHECK CHECK CONSTRAINT [CRMContactoConsentimiento_FK__ContactConsent__2EF266EF];
ALTER TABLE [dbo].[CRMCampanaEvaluacionEjecucion] WITH CHECK CHECK CONSTRAINT [CRMCampanaEvaluacionEjecucion_FK__Evaluatio__Campa__7C31DCF8];
ALTER TABLE [dbo].[CRMCampanaEvaluacionEjecucion] WITH CHECK CHECK CONSTRAINT [CRMCampanaEvaluacionEjecucion_FK__Evaluatio__RuleI__7B3DB8BF];
ALTER TABLE [dbo].[CRMMensajePlantilla] WITH CHECK CHECK CONSTRAINT [CRMMensajePlantilla_FK__MessageTe__Chann__1AEB6E42];
ALTER TABLE [dbo].[CRMRecontactoRegla] WITH CHECK CHECK CONSTRAINT [CRMRecontactoRegla_FK__Remarketi__Chann__34AB4045];
ALTER TABLE [dbo].[CRMRecontactoRegla] WITH CHECK CHECK CONSTRAINT [CRMRecontactoRegla_FK__RemarketingRule__3F28CEB8];
ALTER TABLE [dbo].[CRMContactoUnificacion] WITH CHECK CHECK CONSTRAINT [CRMContactoUnificacion_FK_MergeCase_Source];
ALTER TABLE [dbo].[CRMContactoUnificacion] WITH CHECK CHECK CONSTRAINT [CRMContactoUnificacion_FK_MergeCase_Target];
ALTER TABLE [dbo].[CRMUnificacionOperacion] WITH CHECK CHECK CONSTRAINT [CRMUnificacionOperacion_FK_MergeOperation_Case];
ALTER TABLE [dbo].[CRMUnificacionOperacion] WITH CHECK CHECK CONSTRAINT [CRMUnificacionOperacion_FK_MergeOperation_Source];
ALTER TABLE [dbo].[CRMUnificacionOperacion] WITH CHECK CHECK CONSTRAINT [CRMUnificacionOperacion_FK_MergeOperation_Target];
ALTER TABLE [dbo].[CRMEstrategiaPlanEvaluacion] WITH CHECK CHECK CONSTRAINT [CRMEstrategiaPlanEvaluacion_FK_StrategyPlan_Conversation];
ALTER TABLE [dbo].[CRMEstrategiaOperacion] WITH CHECK CHECK CONSTRAINT [CRMEstrategiaOperacion_FK_StrategyOperation_Conversation];
ALTER TABLE [dbo].[CRMEstrategiaOperacion] WITH CHECK CHECK CONSTRAINT [CRMEstrategiaOperacion_FK_StrategyOperation_Plan];
ALTER TABLE [dbo].[CRMEstrategiaOperacion] WITH CHECK CHECK CONSTRAINT [CRMEstrategiaOperacion_FK_StrategyOperation_Task];
ALTER TABLE [dbo].[CRMEstrategiaPolitica] WITH CHECK CHECK CONSTRAINT [CRMEstrategiaPolitica_FK_StrategyPolicy_Conversation];
ALTER TABLE [dbo].[ACAsignaturaPlan] WITH CHECK CHECK CONSTRAINT [FK_ACAsignaturaPlan_ACAsignatura];
ALTER TABLE [dbo].[ACAsignaturaPlan] WITH CHECK CHECK CONSTRAINT [FK_ACAsignaturaPlan_ACPlanEducativo];
ALTER TABLE [dbo].[ACAsignaturaPlan] WITH CHECK CHECK CONSTRAINT [FK_ACAsignaturaPlan_ACPlanEvaluativo1];
ALTER TABLE [dbo].[ACAsignaturaPlan] WITH CHECK CHECK CONSTRAINT [FK_ACAsignaturaPlan_ACTipoAlternancia];
ALTER TABLE [dbo].[ACAspirante] WITH CHECK CHECK CONSTRAINT [FK_ACAspirante_ACProgramaOfrecido];
ALTER TABLE [dbo].[ACAspirante] WITH CHECK CHECK CONSTRAINT [FK_ACAspirante_GEPeriodo];
ALTER TABLE [dbo].[ACAspirante] WITH CHECK CHECK CONSTRAINT [FK_ACAspirante_GETipoIdentidad];
ALTER TABLE [dbo].[ACDetalleJornada] WITH CHECK CHECK CONSTRAINT [FK_ACJornadaOfrecida_ACJornada];
ALTER TABLE [dbo].[ACDetalleJornada] WITH CHECK CHECK CONSTRAINT [FK_ACJornadaOfrecida_ACProgramaOfrecido];
ALTER TABLE [dbo].[ACPlanEducativo] WITH CHECK CHECK CONSTRAINT [FK_ACPlanEducativo_GEPeriodo];
ALTER TABLE [dbo].[ACProgramaOfrecido] WITH CHECK CHECK CONSTRAINT [FK_ACProgramaOfrecido_ACProgramas];
ALTER TABLE [dbo].[ACProgramaOfrecido] WITH CHECK CHECK CONSTRAINT [FK_ACProgramaOfrecido_GEPeriodo];
ALTER TABLE [dbo].[ACProgramas] WITH CHECK CHECK CONSTRAINT [FK_ACProgramas_ACEscuela];
ALTER TABLE [dbo].[ACProgramas] WITH CHECK CHECK CONSTRAINT [FK_ACProgramas_ACJornada];
ALTER TABLE [dbo].[ACProgramas] WITH CHECK CHECK CONSTRAINT [FK_ACProgramas_ACModalidad];
ALTER TABLE [dbo].[ACSeguimiento] WITH CHECK CHECK CONSTRAINT [FK_ACSeguimiento_ACAspirante];
ALTER TABLE [dbo].[ACSeguimiento] WITH CHECK CHECK CONSTRAINT [FK_ACSeguimiento_ACEstadoSeguimiento];
ALTER TABLE [dbo].[AFDetallePlanPago] WITH CHECK CHECK CONSTRAINT [FK_AFDetallePlanPago_AFPlanes];
ALTER TABLE [dbo].[AFTarifas] WITH CHECK CHECK CONSTRAINT [FK_AFTarifas_ACProgramas];
ALTER TABLE [dbo].[AFTarifas] WITH CHECK CHECK CONSTRAINT [FK_AFTarifas_AFPlanes];
ALTER TABLE [dbo].[AFTarifas] WITH CHECK CHECK CONSTRAINT [FK_AFTarifas_GEPeriodo];
ALTER TABLE [dbo].[GEEmpleado] WITH CHECK CHECK CONSTRAINT [FK_GEEmpleado_GECargoEmpresa];
ALTER TABLE [dbo].[GEEmpleado] WITH CHECK CHECK CONSTRAINT [FK_GEEmpleado_GEEmpresa];
ALTER TABLE [dbo].[GEEstudiante] WITH CHECK CHECK CONSTRAINT [FK_GEEstudiante_ACAcudiente];
ALTER TABLE [dbo].[GEEstudiante] WITH CHECK CHECK CONSTRAINT [FK_GEEstudiante_ACProgramaOfrecido];
ALTER TABLE [dbo].[GEEstudiante] WITH CHECK CHECK CONSTRAINT [FK_GEEstudiante_GEGenero];
ALTER TABLE [dbo].[GEEstudiante] WITH CHECK CHECK CONSTRAINT [FK_GEEstudiante_GEPoblacion];
ALTER TABLE [dbo].[GEEstudiante] WITH CHECK CHECK CONSTRAINT [FK_GEEstudiante_GETipoIdentidad];
ALTER TABLE [dbo].[GEImgenProg] WITH CHECK CHECK CONSTRAINT [FK_GEImgenProg_ACProgramas];
ALTER TABLE [dbo].[GEImgenProg] WITH CHECK CHECK CONSTRAINT [FK_GEImgenProg_GETipoImagen];
ALTER TABLE [dbo].[GEPoblacion] WITH CHECK CHECK CONSTRAINT [FK_GEPoblacion_GEEstados];
ALTER TABLE [dbo].[GEPoblacion] WITH CHECK CHECK CONSTRAINT [FK_GEPoblacion_GEPais];
GO
