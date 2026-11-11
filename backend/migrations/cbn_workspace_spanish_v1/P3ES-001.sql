-- Additive workspace contract. Applied only by the reviewed isolated-copy runner.
CREATE TABLE dbo.CRMTrabajoEstado (
 StateId tinyint NOT NULL CONSTRAINT PK_CRMTrabajoEstado PRIMARY KEY,
 Revision bigint NOT NULL CONSTRAINT CK_CRMTrabajoRevision CHECK(Revision>=0),
 CONSTRAINT CK_CRMTrabajoEstado CHECK(StateId=1)
);
INSERT dbo.CRMTrabajoEstado(StateId,Revision) VALUES(1,0);
CREATE TABLE dbo.CRMTrabajoAsignacion (
 ConversationId uniqueidentifier NOT NULL CONSTRAINT PK_CRMTrabajoAsignacion PRIMARY KEY,
 InstitutionId uniqueidentifier NOT NULL,
 UserId uniqueidentifier NULL,
 UpdatedAt datetime2(7) NOT NULL CONSTRAINT DF_CRMTrabajoAsignacion DEFAULT SYSUTCDATETIME(),
 CONSTRAINT FK_CRMTrabajoAsignacionConversacion FOREIGN KEY(ConversationId) REFERENCES dbo.CRMConversacion(ConversationId),
 CONSTRAINT FK_CRMTrabajoAsignacionUsuario FOREIGN KEY(InstitutionId,UserId) REFERENCES dbo.CRMAccesoUsuario(InstitutionId,UserId)
);
CREATE TABLE dbo.CRMTrabajoTarea (
 TaskId uniqueidentifier NOT NULL CONSTRAINT PK_CRMTrabajoTarea PRIMARY KEY,
 InstitutionId uniqueidentifier NOT NULL,
 ConversationId uniqueidentifier NOT NULL,
 UserId uniqueidentifier NULL,
 Title nvarchar(120) NOT NULL,
 Status varchar(12) NOT NULL CONSTRAINT CK_CRMTrabajoTareaEstado CHECK(Status IN('pending','completed','cancelled')),
 Priority varchar(8) NOT NULL CONSTRAINT CK_CRMTrabajoTareaPrioridad CHECK(Priority IN('low','normal','high','urgent')),
 DueAt datetime2(7) NULL,
 CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_CRMTrabajoTareaCreada DEFAULT SYSUTCDATETIME(),
 UpdatedAt datetime2(7) NOT NULL CONSTRAINT DF_CRMTrabajoTareaActualizada DEFAULT SYSUTCDATETIME(),
 CONSTRAINT FK_CRMTrabajoTareaConversacion FOREIGN KEY(ConversationId) REFERENCES dbo.CRMConversacion(ConversationId),
 CONSTRAINT FK_CRMTrabajoTareaUsuario FOREIGN KEY(InstitutionId,UserId) REFERENCES dbo.CRMAccesoUsuario(InstitutionId,UserId),
 CONSTRAINT CK_CRMTrabajoTareaTitulo CHECK(LEN(LTRIM(RTRIM(Title)))>0)
);
CREATE INDEX IX_CRMTrabajoTareaPagina ON dbo.CRMTrabajoTarea(Status,UpdatedAt,TaskId) INCLUDE(ConversationId,UserId,DueAt);
CREATE TABLE dbo.CRMTrabajoNota (
 NoteId uniqueidentifier NOT NULL CONSTRAINT PK_CRMTrabajoNota PRIMARY KEY,
 ContactId uniqueidentifier NOT NULL,
 InstitutionId uniqueidentifier NOT NULL,
 AuthorId uniqueidentifier NOT NULL,
 Body nvarchar(2000) NOT NULL,
 CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_CRMTrabajoNota DEFAULT SYSUTCDATETIME(),
 CONSTRAINT FK_CRMTrabajoNotaContacto FOREIGN KEY(ContactId) REFERENCES dbo.CRMContacto(ContactId),
 CONSTRAINT FK_CRMTrabajoNotaAutor FOREIGN KEY(InstitutionId,AuthorId) REFERENCES dbo.CRMAccesoUsuario(InstitutionId,UserId),
 CONSTRAINT CK_CRMTrabajoNotaTexto CHECK(LEN(LTRIM(RTRIM(Body)))>0)
);
CREATE INDEX IX_CRMTrabajoNotaContacto ON dbo.CRMTrabajoNota(ContactId,CreatedAt,NoteId);
CREATE TABLE dbo.CRMTrabajoUnificacion (
 MergeId uniqueidentifier NOT NULL CONSTRAINT PK_CRMTrabajoUnificacion PRIMARY KEY,
 SourceContactId uniqueidentifier NOT NULL,
 TargetContactId uniqueidentifier NOT NULL,
 Active bit NOT NULL,
 CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_CRMTrabajoUnificacion DEFAULT SYSUTCDATETIME(),
 ReversedAt datetime2(7) NULL,
 CONSTRAINT FK_CRMTrabajoUnificacionOrigen FOREIGN KEY(SourceContactId) REFERENCES dbo.CRMContacto(ContactId),
 CONSTRAINT FK_CRMTrabajoUnificacionDestino FOREIGN KEY(TargetContactId) REFERENCES dbo.CRMContacto(ContactId),
 CONSTRAINT CK_CRMTrabajoUnificacionDistinta CHECK(SourceContactId<>TargetContactId),
 CONSTRAINT CK_CRMTrabajoUnificacionReversion CHECK((Active=1 AND ReversedAt IS NULL) OR (Active=0 AND ReversedAt IS NOT NULL))
);
CREATE UNIQUE INDEX UX_CRMTrabajoUnificacionActiva ON dbo.CRMTrabajoUnificacion(SourceContactId) WHERE Active=1;
