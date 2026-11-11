SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
SET ANSI_PADDING ON;
CREATE TABLE dbo.CRMPublicidadCuenta(
 InstitutionId uniqueidentifier NOT NULL,AccountId uniqueidentifier NOT NULL,
 Provider varchar(16) NOT NULL,ExternalId nvarchar(160) COLLATE Latin1_General_100_BIN2 NOT NULL,
 IntegrationId uniqueidentifier NULL,State varchar(16) NOT NULL,Revision int NOT NULL,
 Document nvarchar(max) NOT NULL,SecretId uniqueidentifier NULL,
 CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_P9CuentaCreacion DEFAULT SYSUTCDATETIME(),
 UpdatedAt datetime2(7) NOT NULL CONSTRAINT DF_P9CuentaCambio DEFAULT SYSUTCDATETIME(),RowVersion rowversion NOT NULL,
 CONSTRAINT PK_P9Cuenta PRIMARY KEY(InstitutionId,AccountId),
 CONSTRAINT UQ_P9Cuenta UNIQUE(InstitutionId,Provider,ExternalId),
 CONSTRAINT FK_P9CuentaCanal FOREIGN KEY(InstitutionId,IntegrationId) REFERENCES dbo.CRMCanalInstitucionalIntegracion(InstitutionId,IntegrationId),
 CONSTRAINT CK_P9Cuenta CHECK(Provider IN('meta','tiktok') AND State IN('connected','paused','disconnected') AND Revision>0 AND ISJSON(Document)=1)
);
CREATE TABLE dbo.CRMPublicidadCampana(
 InstitutionId uniqueidentifier NOT NULL,CampaignId uniqueidentifier NOT NULL,AccountId uniqueidentifier NOT NULL,
 ExternalId nvarchar(160) COLLATE Latin1_General_100_BIN2 NOT NULL,Revision int NOT NULL,Document nvarchar(max) NOT NULL,
 CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_P9CampanaCreacion DEFAULT SYSUTCDATETIME(),
 UpdatedAt datetime2(7) NOT NULL CONSTRAINT DF_P9CampanaCambio DEFAULT SYSUTCDATETIME(),RowVersion rowversion NOT NULL,
 CONSTRAINT PK_P9Campana PRIMARY KEY(InstitutionId,CampaignId),
 CONSTRAINT UQ_P9CampanaCuenta UNIQUE(InstitutionId,AccountId,CampaignId),
 CONSTRAINT UQ_P9CampanaExterna UNIQUE(InstitutionId,AccountId,ExternalId),
 CONSTRAINT FK_P9CampanaCuenta FOREIGN KEY(InstitutionId,AccountId) REFERENCES dbo.CRMPublicidadCuenta(InstitutionId,AccountId),
 CONSTRAINT CK_P9Campana CHECK(Revision>0 AND ISJSON(Document)=1)
);
CREATE TABLE dbo.CRMPublicidadIdentidad(
 InstitutionId uniqueidentifier NOT NULL,IdentityId uniqueidentifier NOT NULL,AccountId uniqueidentifier NOT NULL,
 Channel varchar(16) NOT NULL,SubjectKey char(64) NOT NULL,
 ContactId uniqueidentifier NOT NULL,ConversationId uniqueidentifier NOT NULL,
 CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_P9IdentidadCreacion DEFAULT SYSUTCDATETIME(),
 CONSTRAINT PK_P9Identidad PRIMARY KEY(InstitutionId,IdentityId),
 CONSTRAINT UQ_P9IdentidadCuenta UNIQUE(InstitutionId,AccountId,IdentityId),
 CONSTRAINT UQ_P9IdentidadExterna UNIQUE(InstitutionId,AccountId,Channel,SubjectKey),
 CONSTRAINT FK_P9IdentidadCuenta FOREIGN KEY(InstitutionId,AccountId) REFERENCES dbo.CRMPublicidadCuenta(InstitutionId,AccountId),
 CONSTRAINT FK_P9IdentidadContacto FOREIGN KEY(ContactId) REFERENCES dbo.CRMContacto(ContactId),
 CONSTRAINT FK_P9IdentidadConversacion FOREIGN KEY(ConversationId) REFERENCES dbo.CRMConversacion(ConversationId),
 CONSTRAINT CK_P9Identidad CHECK(Channel IN('facebook','instagram','tiktok'))
);
CREATE TABLE dbo.CRMPublicidadCaptacion(
 InstitutionId uniqueidentifier NOT NULL,IntakeId uniqueidentifier NOT NULL,AccountId uniqueidentifier NOT NULL,
 Kind varchar(12) NOT NULL,Channel varchar(16) NOT NULL,ExternalId nvarchar(180) COLLATE Latin1_General_100_BIN2 NOT NULL,
 CampaignId uniqueidentifier NULL,IdentityId uniqueidentifier NULL,SocialCommentId uniqueidentifier NULL,
 ReceiptId uniqueidentifier NULL,Origin varchar(24) NOT NULL,State varchar(16) NOT NULL,Revision int NOT NULL,
 ProgramId int NULL,Document nvarchar(max) NOT NULL,
 CapturedAt datetime2(7) NOT NULL,ConvertedAt datetime2(7) NULL,
 CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_P9CaptacionCreacion DEFAULT SYSUTCDATETIME(),
 UpdatedAt datetime2(7) NOT NULL CONSTRAINT DF_P9CaptacionCambio DEFAULT SYSUTCDATETIME(),RowVersion rowversion NOT NULL,
 CONSTRAINT PK_P9Captacion PRIMARY KEY(InstitutionId,IntakeId),
 CONSTRAINT UQ_P9CaptacionExterna UNIQUE(InstitutionId,AccountId,Kind,Channel,ExternalId),
 CONSTRAINT FK_P9CaptacionCuenta FOREIGN KEY(InstitutionId,AccountId) REFERENCES dbo.CRMPublicidadCuenta(InstitutionId,AccountId),
 CONSTRAINT FK_P9CaptacionCampana FOREIGN KEY(InstitutionId,AccountId,CampaignId) REFERENCES dbo.CRMPublicidadCampana(InstitutionId,AccountId,CampaignId),
 CONSTRAINT FK_P9CaptacionIdentidad FOREIGN KEY(InstitutionId,AccountId,IdentityId) REFERENCES dbo.CRMPublicidadIdentidad(InstitutionId,AccountId,IdentityId),
 CONSTRAINT FK_P9CaptacionComentario FOREIGN KEY(InstitutionId,SocialCommentId) REFERENCES dbo.CRMCanalInstitucionalComentarioSocial(InstitutionId,CommentId),
 CONSTRAINT FK_P9CaptacionRecibo FOREIGN KEY(InstitutionId,ReceiptId) REFERENCES dbo.CRMCanalInstitucionalWebhookRecepcion(InstitutionId,ReceiptId),
 CONSTRAINT CK_P9Captacion CHECK(Kind IN('lead','comment') AND Channel IN('facebook','instagram','tiktok') AND Origin IN('operator','verified_receipt','synthetic_demo') AND State IN('new','review','qualified','converted','lost','resolved','hidden','deleted') AND Revision>0 AND ISJSON(Document)=1)
);
CREATE TABLE dbo.CRMPublicidadProceso(
 InstitutionId uniqueidentifier NOT NULL,RunId uniqueidentifier NOT NULL,AccountId uniqueidentifier NOT NULL,
 ReceiptId uniqueidentifier NOT NULL,State varchar(16) NOT NULL,Revision int NOT NULL,
 ActorId uniqueidentifier NOT NULL,OperationId uniqueidentifier NOT NULL,
 Document nvarchar(max) NOT NULL,ErrorCode varchar(100) NULL,
 StartedAt datetime2(7) NOT NULL CONSTRAINT DF_P9ProcesoInicio DEFAULT SYSUTCDATETIME(),
 CompletedAt datetime2(7) NOT NULL CONSTRAINT DF_P9ProcesoFin DEFAULT SYSUTCDATETIME(),
 CONSTRAINT PK_P9Proceso PRIMARY KEY(InstitutionId,RunId),
 CONSTRAINT UQ_P9ProcesoRecibo UNIQUE(InstitutionId,AccountId,ReceiptId),
 CONSTRAINT FK_P9ProcesoCuenta FOREIGN KEY(InstitutionId,AccountId) REFERENCES dbo.CRMPublicidadCuenta(InstitutionId,AccountId),
 CONSTRAINT FK_P9ProcesoRecibo FOREIGN KEY(InstitutionId,ReceiptId) REFERENCES dbo.CRMCanalInstitucionalWebhookRecepcion(InstitutionId,ReceiptId),
 CONSTRAINT FK_P9ProcesoActor FOREIGN KEY(InstitutionId,ActorId) REFERENCES dbo.CRMAccesoUsuario(InstitutionId,UserId),
 CONSTRAINT CK_P9Proceso CHECK(State IN('processed','ignored','quarantined') AND Revision>0 AND ISJSON(Document)=1)
);
CREATE TABLE dbo.CRMPublicidadEvento(
 InstitutionId uniqueidentifier NOT NULL,EventId uniqueidentifier NOT NULL,AccountId uniqueidentifier NOT NULL,
 Kind varchar(40) NOT NULL,IntakeId uniqueidentifier NULL,RunId uniqueidentifier NULL,
 ActorId uniqueidentifier NOT NULL,Document nvarchar(max) NOT NULL,
 CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_P9EventoFecha DEFAULT SYSUTCDATETIME(),
 CONSTRAINT PK_P9Evento PRIMARY KEY(InstitutionId,EventId),
 CONSTRAINT FK_P9EventoCuenta FOREIGN KEY(InstitutionId,AccountId) REFERENCES dbo.CRMPublicidadCuenta(InstitutionId,AccountId),
 CONSTRAINT FK_P9EventoCaptacion FOREIGN KEY(InstitutionId,IntakeId) REFERENCES dbo.CRMPublicidadCaptacion(InstitutionId,IntakeId),
 CONSTRAINT FK_P9EventoProceso FOREIGN KEY(InstitutionId,RunId) REFERENCES dbo.CRMPublicidadProceso(InstitutionId,RunId),
 CONSTRAINT FK_P9EventoActor FOREIGN KEY(InstitutionId,ActorId) REFERENCES dbo.CRMAccesoUsuario(InstitutionId,UserId),
 CONSTRAINT CK_P9Evento CHECK(ISJSON(Document)=1)
);
CREATE TABLE dbo.CRMPublicidadSecreto(
 InstitutionId uniqueidentifier NOT NULL,SecretId uniqueidentifier NOT NULL,AccountId uniqueidentifier NOT NULL,
 VersionNo int NOT NULL,Kind varchar(24) NOT NULL,KeyId char(32) NOT NULL,Nonce binary(12) NOT NULL,Ciphertext varbinary(max) NOT NULL,
 ActorId uniqueidentifier NOT NULL,CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_P9SecretoFecha DEFAULT SYSUTCDATETIME(),
 CONSTRAINT PK_P9Secreto PRIMARY KEY(InstitutionId,SecretId),
 CONSTRAINT UQ_P9SecretoCuenta UNIQUE(InstitutionId,AccountId,SecretId),
 CONSTRAINT UQ_P9SecretoVersion UNIQUE(InstitutionId,AccountId,Kind,VersionNo),
 CONSTRAINT FK_P9SecretoCuenta FOREIGN KEY(InstitutionId,AccountId) REFERENCES dbo.CRMPublicidadCuenta(InstitutionId,AccountId),
 CONSTRAINT FK_P9SecretoActor FOREIGN KEY(InstitutionId,ActorId) REFERENCES dbo.CRMAccesoUsuario(InstitutionId,UserId),
 CONSTRAINT CK_P9Secreto CHECK(VersionNo>0 AND Kind='access_token' AND DATALENGTH(Ciphertext)>16 AND DATALENGTH(Ciphertext)<=32784)
);
ALTER TABLE dbo.CRMPublicidadCuenta ADD CONSTRAINT FK_P9CuentaSecreto FOREIGN KEY(InstitutionId,AccountId,SecretId) REFERENCES dbo.CRMPublicidadSecreto(InstitutionId,AccountId,SecretId);
CREATE INDEX IX_P9CaptacionLista ON dbo.CRMPublicidadCaptacion(InstitutionId,AccountId,Kind,State,CapturedAt,IntakeId);
CREATE INDEX IX_P9CaptacionRecibo ON dbo.CRMPublicidadCaptacion(InstitutionId,ReceiptId);
CREATE INDEX IX_P9EventoHistorial ON dbo.CRMPublicidadEvento(InstitutionId,AccountId,CreatedAt,EventId);
