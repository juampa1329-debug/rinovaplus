SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
SET ANSI_PADDING ON;
CREATE TABLE dbo.CRMAgenteOperacionPrograma (
 InstitutionId uniqueidentifier NOT NULL,
 ProgramId int NOT NULL,
 Name nvarchar(180) NOT NULL,
 School nvarchar(100) NOT NULL CONSTRAINT DF_P5ProgramaEscuela DEFAULT N'',
 Schedule nvarchar(100) NOT NULL CONSTRAINT DF_P5ProgramaJornada DEFAULT N'',
 Authority varchar(24) NOT NULL,
 Active bit NOT NULL CONSTRAINT DF_P5ProgramaActivo DEFAULT 1,
 Revision int NOT NULL CONSTRAINT DF_P5ProgramaRevision DEFAULT 1,
 ReviewedBy uniqueidentifier NOT NULL,
 UpdatedAt datetime2(7) NOT NULL CONSTRAINT DF_P5ProgramaFecha DEFAULT SYSUTCDATETIME(),
 RowVersion rowversion NOT NULL,
 CONSTRAINT PK_P5Programa PRIMARY KEY(InstitutionId,ProgramId),
 CONSTRAINT FK_P5ProgramaInstitucion FOREIGN KEY(InstitutionId) REFERENCES dbo.CRMAccesoInstitucion(InstitutionId),
 CONSTRAINT FK_P5ProgramaRevisor FOREIGN KEY(InstitutionId,ReviewedBy) REFERENCES dbo.CRMAccesoUsuario(InstitutionId,UserId),
 CONSTRAINT CK_P5Programa CHECK(ProgramId>0 AND LEN(Name)>0 AND Revision>0 AND Authority IN('declared','synthetic_demo'))
);
CREATE TABLE dbo.CRMAgenteOperacionSolicitud (
 InstitutionId uniqueidentifier NOT NULL,
 RequestId uniqueidentifier NOT NULL,
 ActorId uniqueidentifier NOT NULL,
 SessionId uniqueidentifier NOT NULL,
 AgentId uniqueidentifier NOT NULL,
 ConversationId uniqueidentifier NULL,
 Epoch bigint NULL,
 Kind varchar(24) NOT NULL,
 PayloadHash binary(32) NOT NULL,
 BindingHash binary(32) NULL,
 State varchar(16) NOT NULL,
 Result nvarchar(max) NOT NULL CONSTRAINT DF_P5SolicitudResultado DEFAULT N'{}',
 ErrorCode varchar(80) NULL,
 LeaseId uniqueidentifier NULL,
 LeaseUntil datetime2(7) NULL,
 CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_P5SolicitudInicio DEFAULT SYSUTCDATETIME(),
 CompletedAt datetime2(7) NULL,
 RowVersion rowversion NOT NULL,
 CONSTRAINT PK_P5Solicitud PRIMARY KEY(InstitutionId,RequestId),
 CONSTRAINT FK_P5SolicitudUsuario FOREIGN KEY(InstitutionId,ActorId) REFERENCES dbo.CRMAccesoUsuario(InstitutionId,UserId),
 CONSTRAINT FK_P5SolicitudSesion FOREIGN KEY(InstitutionId,SessionId) REFERENCES dbo.CRMAccesoSesion(InstitutionId,SessionId),
 CONSTRAINT FK_P5SolicitudAgente FOREIGN KEY(AgentId) REFERENCES dbo.CRMAgentePerfil(AgentId),
 CONSTRAINT FK_P5SolicitudConversacion FOREIGN KEY(ConversationId) REFERENCES dbo.CRMConversacion(ConversationId),
 CONSTRAINT CK_P5Solicitud CHECK(State IN('running','confirmed','failed','uncertain','cancelled') AND Kind IN('simulation','conversation_draft') AND ISJSON(Result)=1)
);
