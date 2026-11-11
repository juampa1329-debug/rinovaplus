SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
SET ANSI_PADDING ON;
CREATE TABLE dbo.CRMCanalOperacionConfiguracion (
 InstitutionId uniqueidentifier NOT NULL CONSTRAINT PK_CRMCanalOperacionConfiguracion PRIMARY KEY,
 PublicBaseUrl nvarchar(2048) NOT NULL CONSTRAINT DF_CRMCanalOperacionConfiguracionUrl DEFAULT N'',
 IngressEnabled bit NOT NULL CONSTRAINT DF_CRMCanalOperacionConfiguracionEntrada DEFAULT 1,
 OutboundEnabled bit NOT NULL CONSTRAINT DF_CRMCanalOperacionConfiguracionSalida DEFAULT 0,
 ReceiptRetentionDays int NOT NULL CONSTRAINT DF_CRMCanalOperacionConfiguracionRetencion DEFAULT 14,
 Revision bigint NOT NULL CONSTRAINT DF_CRMCanalOperacionConfiguracionRevision DEFAULT 1,
 UpdatedAt datetime2(7) NOT NULL CONSTRAINT DF_CRMCanalOperacionConfiguracionActualizada DEFAULT SYSUTCDATETIME(),
 RowVersion rowversion NOT NULL,
 CONSTRAINT FK_CRMCanalOperacionConfiguracionInstitucion FOREIGN KEY(InstitutionId) REFERENCES dbo.CRMAccesoInstitucion(InstitutionId),
 CONSTRAINT CK_CRMCanalOperacionConfiguracionRetencion CHECK(ReceiptRetentionDays BETWEEN 1 AND 90),
 CONSTRAINT CK_CRMCanalOperacionConfiguracionRevision CHECK(Revision>0)
);
CREATE TABLE dbo.CRMCanalOperacionArchivo (
 MediaId uniqueidentifier NOT NULL CONSTRAINT PK_CRMCanalOperacionArchivo PRIMARY KEY,
 InstitutionId uniqueidentifier NOT NULL,
 IntegrationId uniqueidentifier NULL,
 IdentityId uniqueidentifier NULL,
 ConversationId uniqueidentifier NOT NULL,
 MessageId uniqueidentifier NULL,
 UserId uniqueidentifier NULL,
 SourceKind varchar(8) NOT NULL,
 State varchar(12) NOT NULL,
 Kind varchar(8) NULL,
 FileName nvarchar(160) NOT NULL,
 ActualMime varchar(100) NULL,
 StorageKey varchar(64) NULL,
 ByteLength bigint NULL,
 ContentHash binary(32) NULL,
 ProviderReference nvarchar(max) NOT NULL CONSTRAINT DF_CRMCanalOperacionArchivoProveedor DEFAULT N'{}',
 LastErrorCode varchar(80) NULL,
 CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_CRMCanalOperacionArchivoCreado DEFAULT SYSUTCDATETIME(),
 UpdatedAt datetime2(7) NOT NULL CONSTRAINT DF_CRMCanalOperacionArchivoActualizado DEFAULT SYSUTCDATETIME(),
 ExpiresAt datetime2(7) NULL,
 RowVersion rowversion NOT NULL,
 CONSTRAINT UQ_CRMCanalOperacionArchivoInstitucion UNIQUE(InstitutionId,MediaId),
 CONSTRAINT FK_CRMCanalOperacionArchivoInstitucion FOREIGN KEY(InstitutionId) REFERENCES dbo.CRMAccesoInstitucion(InstitutionId),
 CONSTRAINT FK_CRMCanalOperacionArchivoCuenta FOREIGN KEY(InstitutionId,IntegrationId) REFERENCES dbo.CRMCanalInstitucionalIntegracion(InstitutionId,IntegrationId),
 CONSTRAINT FK_CRMCanalOperacionArchivoIdentidad FOREIGN KEY(InstitutionId,IdentityId) REFERENCES dbo.CRMCanalInstitucionalIdentidadExterna(InstitutionId,IdentityId),
 CONSTRAINT FK_CRMCanalOperacionArchivoUsuario FOREIGN KEY(InstitutionId,UserId) REFERENCES dbo.CRMAccesoUsuario(InstitutionId,UserId),
 CONSTRAINT FK_CRMCanalOperacionArchivoConversacion FOREIGN KEY(ConversationId) REFERENCES dbo.CRMConversacion(ConversationId),
 CONSTRAINT FK_CRMCanalOperacionArchivoMensaje FOREIGN KEY(MessageId) REFERENCES dbo.CRMMensaje(MessageId),
 CONSTRAINT CK_CRMCanalOperacionArchivoFuente CHECK((SourceKind='provider' AND IntegrationId IS NOT NULL AND IdentityId IS NOT NULL) OR (SourceKind='upload' AND IdentityId IS NULL AND UserId IS NOT NULL)),
 CONSTRAINT CK_CRMCanalOperacionArchivoEstado CHECK(State IN('pending','processing','ready','rejected','failed','deleted')),
 CONSTRAINT CK_CRMCanalOperacionArchivoTipo CHECK(Kind IN('image','audio','document','video')),
 CONSTRAINT CK_CRMCanalOperacionArchivoTamano CHECK(ByteLength>0 AND ByteLength<=25000000),
 CONSTRAINT CK_CRMCanalOperacionArchivoProveedor CHECK(ISJSON(ProviderReference)=1),
 CONSTRAINT CK_CRMCanalOperacionArchivoListo CHECK(State<>'ready' OR (ActualMime IS NOT NULL AND StorageKey IS NOT NULL AND ByteLength IS NOT NULL AND ContentHash IS NOT NULL AND Kind IS NOT NULL))
);
CREATE INDEX IX_CRMCanalOperacionArchivoConversacion ON dbo.CRMCanalOperacionArchivo(ConversationId,CreatedAt,MediaId) INCLUDE(MessageId,State,Kind);
