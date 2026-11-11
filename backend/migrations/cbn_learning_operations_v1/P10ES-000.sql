SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
SET ANSI_PADDING ON;
CREATE TABLE dbo.CRMAprendizajeMigracion (
 UnitId varchar(30) NOT NULL CONSTRAINT PK_P10Diario PRIMARY KEY,
 ManifestSha256 char(64) NOT NULL,TargetDatabase sysname NOT NULL,
 ParentHistorySha256 char(64) NOT NULL,
 Status varchar(12) NOT NULL CONSTRAINT CK_P10DiarioEstado CHECK(Status IN('STARTED','COMMITTED')),
 StartedAt datetime2(7) NOT NULL CONSTRAINT DF_P10DiarioInicio DEFAULT SYSUTCDATETIME(),
 CommittedAt datetime2(7) NULL,
 CONSTRAINT CK_P10DiarioFecha CHECK((Status='STARTED' AND CommittedAt IS NULL) OR (Status='COMMITTED' AND CommittedAt IS NOT NULL))
);
