CREATE TABLE dbo.CRMTrabajoMigracion (
 UnitId varchar(32) NOT NULL CONSTRAINT PK_CRMTrabajoMigracion PRIMARY KEY,
 ManifestSha256 char(64) NOT NULL,
 TargetDatabase sysname NOT NULL,
 ParentJournalSha256 char(64) NOT NULL,
 Status varchar(12) NOT NULL CONSTRAINT CK_CRMTrabajoMigracionEstado CHECK(Status IN('STARTED','COMMITTED')),
 StartedAt datetime2(7) NOT NULL CONSTRAINT DF_CRMTrabajoMigracion DEFAULT SYSUTCDATETIME(),
 CommittedAt datetime2(7) NULL,
 CONSTRAINT CK_CRMTrabajoMigracionConfirmacion CHECK((Status='STARTED' AND CommittedAt IS NULL) OR (Status='COMMITTED' AND CommittedAt IS NOT NULL))
);
