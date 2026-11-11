SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
SET ANSI_PADDING ON;
CREATE TABLE dbo.CRMConocimientoRegistro (
 InstitutionId uniqueidentifier NOT NULL,
 RecordId uniqueidentifier NOT NULL,
 Kind varchar(16) NOT NULL,
 Scope varchar(16) NOT NULL,
 ProgramId int NULL,
 StageId uniqueidentifier NULL,
 ConversationId uniqueidentifier NULL,
 ContextId uniqueidentifier NULL,
 State varchar(16) NOT NULL,
 Visibility varchar(24) NOT NULL,
 CurrentVersion int NOT NULL,
 ValidUntil date NOT NULL,
 UpdatedAt datetime2(7) NOT NULL CONSTRAINT DF_P6RegistroFecha DEFAULT SYSUTCDATETIME(),
 RowVersion rowversion NOT NULL,
 CONSTRAINT PK_P6Registro PRIMARY KEY(InstitutionId,RecordId),
 CONSTRAINT FK_P6RegistroInstitucion FOREIGN KEY(InstitutionId) REFERENCES dbo.CRMAccesoInstitucion(InstitutionId),
 CONSTRAINT FK_P6RegistroPrograma FOREIGN KEY(InstitutionId,ProgramId) REFERENCES dbo.CRMAgenteOperacionPrograma(InstitutionId,ProgramId),
 CONSTRAINT FK_P6RegistroEtapa FOREIGN KEY(StageId) REFERENCES dbo.CRMAgenteEtapa(StageId),
 CONSTRAINT FK_P6RegistroConversacion FOREIGN KEY(ConversationId) REFERENCES dbo.CRMConversacion(ConversationId),
 CONSTRAINT FK_P6RegistroContexto FOREIGN KEY(ContextId) REFERENCES dbo.CRMAgenteContexto(ContextId),
 CONSTRAINT CK_P6RegistroTipo CHECK(Kind IN('document','collective','dna','private') AND CurrentVersion>0),
 CONSTRAINT CK_P6RegistroEstado CHECK(State IN('draft','published','archived')),
 CONSTRAINT CK_P6RegistroAmbito CHECK(
  (Scope='institution' AND ProgramId IS NULL AND StageId IS NULL AND ConversationId IS NULL AND ContextId IS NULL AND Kind<>'private') OR
  (Scope='program' AND ProgramId IS NOT NULL AND ConversationId IS NULL AND ContextId IS NULL AND Kind IN('document','collective')) OR
  (Scope='conversation' AND ConversationId IS NOT NULL AND Kind='private' AND StageId IS NULL AND ProgramId IS NULL)),
 CONSTRAINT CK_P6RegistroVisibilidad CHECK((Kind='private' AND Visibility='conversation_only') OR (Kind<>'private' AND Visibility IN('agent_context','staff_only'))),
 CONSTRAINT CK_P6RegistroADN CHECK(Kind<>'dna' OR Scope='institution')
);
CREATE INDEX IX_P6RegistroContexto ON dbo.CRMConocimientoRegistro(InstitutionId,Kind,State,Visibility,ProgramId,StageId,ValidUntil);
CREATE UNIQUE INDEX UX_P6ADNActivo ON dbo.CRMConocimientoRegistro(InstitutionId,Kind) WHERE Kind='dna' AND State='published';
CREATE TABLE dbo.CRMConocimientoVersion (
 InstitutionId uniqueidentifier NOT NULL,
 RecordId uniqueidentifier NOT NULL,
 VersionNo int NOT NULL,
 State varchar(16) NOT NULL,
 Snapshot nvarchar(max) NOT NULL,
 ActorId uniqueidentifier NOT NULL,
 OperationId uniqueidentifier NOT NULL,
 Reason nvarchar(1000) NOT NULL,
 CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_P6VersionFecha DEFAULT SYSUTCDATETIME(),
 CONSTRAINT PK_P6Version PRIMARY KEY(InstitutionId,RecordId,VersionNo),
 CONSTRAINT UQ_P6VersionOperacion UNIQUE(InstitutionId,OperationId),
 CONSTRAINT FK_P6VersionRegistro FOREIGN KEY(InstitutionId,RecordId) REFERENCES dbo.CRMConocimientoRegistro(InstitutionId,RecordId),
 CONSTRAINT FK_P6VersionAutor FOREIGN KEY(InstitutionId,ActorId) REFERENCES dbo.CRMAccesoUsuario(InstitutionId,UserId),
 CONSTRAINT CK_P6Version CHECK(VersionNo>0 AND ISJSON(Snapshot)=1 AND State IN('draft','published','archived') AND LEN(Reason)>0)
);
