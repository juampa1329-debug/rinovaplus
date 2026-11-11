SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
SET ANSI_PADDING ON;
CREATE TABLE dbo.CRMFlujoDefinicion (
 InstitutionId uniqueidentifier NOT NULL,RecordId uniqueidentifier NOT NULL,
 Kind varchar(16) NOT NULL,Name nvarchar(160) NOT NULL,
 State varchar(16) NOT NULL,Revision int NOT NULL,CurrentVersion int NOT NULL,Epoch int NOT NULL,
 Document nvarchar(max) NOT NULL,
 ActorId uniqueidentifier NULL,ActorAuthVersion int NULL,ActorSessionId uniqueidentifier NULL,
 ApprovedAt datetime2(7) NULL,
 CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_P8DefCreacion DEFAULT SYSUTCDATETIME(),
 UpdatedAt datetime2(7) NOT NULL CONSTRAINT DF_P8DefCambio DEFAULT SYSUTCDATETIME(),
 RowVersion rowversion NOT NULL,
 CONSTRAINT PK_P8Def PRIMARY KEY(InstitutionId,RecordId),
 CONSTRAINT FK_P8DefActor FOREIGN KEY(InstitutionId,ActorId) REFERENCES dbo.CRMAccesoUsuario(InstitutionId,UserId),
 CONSTRAINT FK_P8DefSesion FOREIGN KEY(InstitutionId,ActorSessionId) REFERENCES dbo.CRMAccesoSesion(InstitutionId,SessionId),
 CONSTRAINT CK_P8Def CHECK(Kind IN('template','segment','campaign','trigger','flow') AND State IN('draft','active','paused','archived') AND Revision>0 AND CurrentVersion>0 AND Epoch>0 AND ISJSON(Document)=1)
);
CREATE TABLE dbo.CRMFlujoVersion (
 InstitutionId uniqueidentifier NOT NULL,RecordId uniqueidentifier NOT NULL,VersionNo int NOT NULL,
 Kind varchar(16) NOT NULL,Name nvarchar(160) NOT NULL,Document nvarchar(max) NOT NULL,
 Reason nvarchar(1000) NOT NULL,ActorId uniqueidentifier NOT NULL,OperationId uniqueidentifier NOT NULL,
 CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_P8VerFecha DEFAULT SYSUTCDATETIME(),
 CONSTRAINT PK_P8Ver PRIMARY KEY(InstitutionId,RecordId,VersionNo),
 CONSTRAINT UQ_P8VerOperacion UNIQUE(InstitutionId,OperationId),
 CONSTRAINT FK_P8VerDef FOREIGN KEY(InstitutionId,RecordId) REFERENCES dbo.CRMFlujoDefinicion(InstitutionId,RecordId),
 CONSTRAINT FK_P8VerActor FOREIGN KEY(InstitutionId,ActorId) REFERENCES dbo.CRMAccesoUsuario(InstitutionId,UserId),
 CONSTRAINT CK_P8Ver CHECK(VersionNo>0 AND ISJSON(Document)=1)
);
CREATE TABLE dbo.CRMFlujoObservacion (
 InstitutionId uniqueidentifier NOT NULL,IdentityId uniqueidentifier NOT NULL,
 CanonicalContactId uniqueidentifier NOT NULL,Stage nvarchar(60) NOT NULL,ProgramId int NULL,
 IncomingCount bigint NOT NULL,LastIncomingId uniqueidentifier NULL,
 Revision int NOT NULL,ObservedAt datetime2(7) NOT NULL,
 CONSTRAINT PK_P8Obs PRIMARY KEY(InstitutionId,IdentityId),
 CONSTRAINT FK_P8ObsId FOREIGN KEY(InstitutionId,IdentityId) REFERENCES dbo.CRMCanalInstitucionalIdentidadExterna(InstitutionId,IdentityId),
 CONSTRAINT FK_P8ObsContacto FOREIGN KEY(CanonicalContactId) REFERENCES dbo.CRMContacto(ContactId),
 CONSTRAINT CK_P8Obs CHECK(IncomingCount>=0 AND Revision>0)
);
CREATE TABLE dbo.CRMFlujoInscripcion (
 InstitutionId uniqueidentifier NOT NULL,EnrollmentId uniqueidentifier NOT NULL,
 FlowId uniqueidentifier NOT NULL,VersionNo int NOT NULL,FlowEpoch int NOT NULL,
 TriggerId uniqueidentifier NULL,TriggerVersion int NULL,
 IdentityId uniqueidentifier NOT NULL,ContactId uniqueidentifier NOT NULL,CanonicalContactId uniqueidentifier NOT NULL,
 ConversationId uniqueidentifier NOT NULL,EntryKey char(64) NOT NULL,Variant char(1) NOT NULL,
 State varchar(16) NOT NULL,StepIndex int NOT NULL,DueAt datetime2(7) NOT NULL,
 Context nvarchar(max) NOT NULL,LastReason varchar(100) NULL,
 CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_P8InsFecha DEFAULT SYSUTCDATETIME(),
 UpdatedAt datetime2(7) NOT NULL CONSTRAINT DF_P8InsCambio DEFAULT SYSUTCDATETIME(),
 CONSTRAINT PK_P8Ins PRIMARY KEY(InstitutionId,EnrollmentId),
 CONSTRAINT UQ_P8InsEntrada UNIQUE(InstitutionId,FlowId,CanonicalContactId,EntryKey),
 CONSTRAINT FK_P8InsVersion FOREIGN KEY(InstitutionId,FlowId,VersionNo) REFERENCES dbo.CRMFlujoVersion(InstitutionId,RecordId,VersionNo),
 CONSTRAINT FK_P8InsDisparador FOREIGN KEY(InstitutionId,TriggerId,TriggerVersion) REFERENCES dbo.CRMFlujoVersion(InstitutionId,RecordId,VersionNo),
 CONSTRAINT FK_P8InsId FOREIGN KEY(InstitutionId,IdentityId) REFERENCES dbo.CRMCanalInstitucionalIdentidadExterna(InstitutionId,IdentityId),
 CONSTRAINT FK_P8InsContacto FOREIGN KEY(ContactId) REFERENCES dbo.CRMContacto(ContactId),
 CONSTRAINT FK_P8InsCanonico FOREIGN KEY(CanonicalContactId) REFERENCES dbo.CRMContacto(ContactId),
 CONSTRAINT FK_P8InsConversacion FOREIGN KEY(ConversationId) REFERENCES dbo.CRMConversacion(ConversationId),
 CONSTRAINT CK_P8Ins CHECK(VersionNo>0 AND FlowEpoch>0 AND StepIndex>=0 AND StepIndex<=20 AND Variant IN('A','B') AND State IN('waiting','queued','paused','completed','cancelled','failed','uncertain') AND ISJSON(Context)=1)
);
CREATE UNIQUE INDEX UX_P8InsVigente ON dbo.CRMFlujoInscripcion(InstitutionId,FlowId,CanonicalContactId)
 WHERE State IN('waiting','queued','paused','uncertain');
CREATE INDEX IX_P8InsVencida ON dbo.CRMFlujoInscripcion(InstitutionId,State,DueAt);
CREATE TABLE dbo.CRMFlujoPaso (
 InstitutionId uniqueidentifier NOT NULL,StepId uniqueidentifier NOT NULL,EnrollmentId uniqueidentifier NOT NULL,
 StepIndex int NOT NULL,Kind varchar(16) NOT NULL,State varchar(16) NOT NULL,
 DueAt datetime2(7) NOT NULL,NativeCampaignId uniqueidentifier NULL,LastReason varchar(100) NULL,
 CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_P8PasoFecha DEFAULT SYSUTCDATETIME(),
 CompletedAt datetime2(7) NULL,
 CONSTRAINT PK_P8Paso PRIMARY KEY(InstitutionId,StepId),
 CONSTRAINT UQ_P8PasoOrden UNIQUE(InstitutionId,EnrollmentId,StepIndex),
 CONSTRAINT FK_P8PasoIns FOREIGN KEY(InstitutionId,EnrollmentId) REFERENCES dbo.CRMFlujoInscripcion(InstitutionId,EnrollmentId),
 CONSTRAINT FK_P8PasoCampana FOREIGN KEY(InstitutionId,NativeCampaignId) REFERENCES dbo.CRMMasivoCampana(InstitutionId,CampaignId),
 CONSTRAINT CK_P8Paso CHECK(StepIndex>=0 AND StepIndex<20 AND Kind IN('wait','condition','send') AND State IN('waiting','queued','completed','skipped','failed','cancelled','uncertain'))
);
CREATE UNIQUE INDEX UX_P8PasoCampana ON dbo.CRMFlujoPaso(InstitutionId,NativeCampaignId) WHERE NativeCampaignId IS NOT NULL;
CREATE TABLE dbo.CRMFlujoEvento (
 InstitutionId uniqueidentifier NOT NULL,EventId uniqueidentifier NOT NULL,
 RecordId uniqueidentifier NULL,EnrollmentId uniqueidentifier NULL,StepId uniqueidentifier NULL,
 Kind varchar(40) NOT NULL,SourceKey char(64) NOT NULL,Document nvarchar(max) NOT NULL,
 ActorId uniqueidentifier NULL,CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_P8EvtFecha DEFAULT SYSUTCDATETIME(),
 CONSTRAINT PK_P8Evt PRIMARY KEY(InstitutionId,EventId),
 CONSTRAINT UQ_P8EvtFuente UNIQUE(InstitutionId,SourceKey),
 CONSTRAINT FK_P8EvtDef FOREIGN KEY(InstitutionId,RecordId) REFERENCES dbo.CRMFlujoDefinicion(InstitutionId,RecordId),
 CONSTRAINT FK_P8EvtIns FOREIGN KEY(InstitutionId,EnrollmentId) REFERENCES dbo.CRMFlujoInscripcion(InstitutionId,EnrollmentId),
 CONSTRAINT FK_P8EvtPaso FOREIGN KEY(InstitutionId,StepId) REFERENCES dbo.CRMFlujoPaso(InstitutionId,StepId),
 CONSTRAINT FK_P8EvtActor FOREIGN KEY(InstitutionId,ActorId) REFERENCES dbo.CRMAccesoUsuario(InstitutionId,UserId),
 CONSTRAINT CK_P8Evt CHECK(ISJSON(Document)=1)
);
