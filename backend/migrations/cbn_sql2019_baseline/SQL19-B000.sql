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
CREATE TABLE crm_meta.MigrationJournal(
 EventId bigint IDENTITY(1,1) NOT NULL CONSTRAINT PK_MigrationJournal PRIMARY KEY CLUSTERED,
 AttemptId uniqueidentifier NOT NULL, UnitId nvarchar(80) NOT NULL,
 EventKind varchar(32) NOT NULL,
 RecordedAtUtc datetime2(7) NOT NULL CONSTRAINT DF_MigrationJournal_Recorded DEFAULT SYSUTCDATETIME(),
 ReleaseId nvarchar(80) NOT NULL, ToolVersion nvarchar(40) NOT NULL,
 ManifestSha256 binary(32) NOT NULL, UnitSha256 binary(32) NOT NULL,
 ShapeVersion varchar(32) NOT NULL, TargetSha256 binary(32) NOT NULL,
 BeforeShapeSha256 binary(32) NULL, AfterShapeSha256 binary(32) NULL,
 EvidenceRef nvarchar(160) NOT NULL, ApprovalRef nvarchar(160) NOT NULL,
 BackupRef nvarchar(160) NOT NULL, PrincipalRef nvarchar(128) NOT NULL,
 ErrorCode varchar(60) NULL, SuccessKey nvarchar(80) NULL,
 RelatedAttemptId uniqueidentifier NULL, RelatedUnitId nvarchar(80) NULL,
 CONSTRAINT CK_MigrationJournal_Event CHECK(EventKind IN
 ('STARTED','COMMITTED','ADOPTED','FAILED_ROLLED_BACK','UNKNOWN',
  'RECONCILED_COMMITTED','RECONCILED_NOT_APPLIED','RECOVERY_REQUIRED','COMPENSATED','RESTORED')),
 CONSTRAINT CK_MigrationJournal_Success CHECK(
  (EventKind IN ('COMMITTED','ADOPTED') AND SuccessKey=UnitId AND SuccessKey IS NOT NULL)
  OR (EventKind NOT IN ('COMMITTED','ADOPTED') AND SuccessKey IS NULL)),
 CONSTRAINT CK_MigrationJournal_Error CHECK(EventKind<>'COMMITTED' OR ErrorCode IS NULL)
);
CREATE UNIQUE INDEX UX_MigrationJournal_Success ON crm_meta.MigrationJournal(SuccessKey)
 WHERE SuccessKey IS NOT NULL;
EXEC sys.sp_addextendedproperty @name=N'crm_meta.contract',@value=N'CBN-migrations-v1',@level0type=N'SCHEMA',@level0name=N'crm_meta';
