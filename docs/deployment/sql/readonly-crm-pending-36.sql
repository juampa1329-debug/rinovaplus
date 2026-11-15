-- Review and run as DBA connected to DBSIIE_2025A.
-- Create a fresh server login named rinovaplus_pg_reader separately in SSMS.
-- This script creates only its database user and grants SELECT on these CRM tables.
SET NOCOUNT ON;
SET XACT_ABORT ON;

IF DB_NAME() <> N'DBSIIE_2025A'
    THROW 51000, 'Connect to DBSIIE_2025A first', 1;
IF SUSER_ID(N'rinovaplus_pg_reader') IS NULL OR USER_ID(N'rinovaplus_pg_reader') IS NOT NULL
    THROW 51001, 'Use a new dedicated server login without an existing database user', 1;
IF ISNULL(IS_SRVROLEMEMBER(N'sysadmin', N'rinovaplus_pg_reader'), 1) <> 0
OR EXISTS (SELECT 1 FROM sys.server_role_members WHERE member_principal_id = SUSER_ID(N'rinovaplus_pg_reader'))
OR EXISTS (
    SELECT 1 FROM sys.server_permissions WHERE grantee_principal_id = SUSER_ID(N'rinovaplus_pg_reader')
      AND permission_name <> N'CONNECT SQL'
)
    THROW 51002, 'Use a reader without server roles or extra server permissions', 1;

DECLARE @scope table (name sysname PRIMARY KEY);
INSERT @scope VALUES
    (N'CRMAdmision'),
    (N'CRMAdmisionOperacion'),
    (N'CRMAdmisionSeguimiento'),
    (N'CRMAnalisisConversacionEstado'),
    (N'CRMAnalisisEvaluacionHumana'),
    (N'CRMAnalisisIntento'),
    (N'CRMAnalisisOperacion'),
    (N'CRMAnalisisPolitica'),
    (N'CRMAnalisisRecepcion'),
    (N'CRMArchivoMultimedia'),
    (N'CRMBandejaMiembro'),
    (N'CRMBandejaOperacion'),
    (N'CRMCampanaDestinatario'),
    (N'CRMCampanaPolitica'),
    (N'CRMCanalCredencial'),
    (N'CRMCanalCuenta'),
    (N'CRMCanalInstitucionalVinculoOrigen'),
    (N'CRMComentarioSocial'),
    (N'CRMContactoConsentimiento'),
    (N'CRMConversacionEvento'),
    (N'CRMCuentaCadencia'),
    (N'CRMEstrategiaOperacion'),
    (N'CRMEstrategiaPolitica'),
    (N'CRMEventoPreparacion'),
    (N'CRMEventoReintentoOperacion'),
    (N'CRMEventoWebhook'),
    (N'CRMIAAdmisionPolitica'),
    (N'CRMIAConexion'),
    (N'CRMIAConfiguracion'),
    (N'CRMIACredencial'),
    (N'CRMMensajeExterno'),
    (N'CRMMensajePlantilla'),
    (N'CRMProspectoMemoria'),
    (N'CRMRecontactoRegla'),
    (N'CRMRespuestaTrabajo'),
    (N'CRMUnificacionOperacion');

IF (SELECT COUNT(*) FROM @scope) <> 36
    THROW 51003, 'Unexpected CRM table scope', 1;
IF EXISTS (SELECT 1 FROM @scope WHERE OBJECT_ID(N'dbo.' + QUOTENAME(name), N'U') IS NULL)
    THROW 51004, 'One or more reviewed CRM tables is missing', 1;

DECLARE @objects table (qualified nvarchar(520) PRIMARY KEY, expected_read bit NOT NULL);
INSERT @objects
SELECT QUOTENAME(s.name) + N'.' + QUOTENAME(o.name),
       CASE WHEN s.name = N'dbo' AND a.name IS NOT NULL THEN 1 ELSE 0 END
FROM sys.objects o JOIN sys.schemas s ON s.schema_id = o.schema_id
LEFT JOIN @scope a ON o.name = a.name
WHERE o.is_ms_shipped = 0 AND o.parent_object_id = 0;

DECLARE @columns table (qualified nvarchar(520) NOT NULL, name sysname NOT NULL, expected_read bit NOT NULL);
INSERT @columns
SELECT o.qualified, c.name, o.expected_read
FROM @objects o JOIN sys.columns c ON c.object_id = OBJECT_ID(o.qualified)
WHERE OBJECTPROPERTY(c.object_id, 'IsUserTable') = 1 OR OBJECTPROPERTY(c.object_id, 'IsView') = 1;

DECLARE @impersonated bit = 0;
BEGIN TRY
    BEGIN TRANSACTION;
    CREATE USER [rinovaplus_pg_reader] FOR LOGIN [rinovaplus_pg_reader] WITH DEFAULT_SCHEMA = [dbo];
    GRANT CONNECT TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMAdmision] TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMAdmisionOperacion] TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMAdmisionSeguimiento] TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMAnalisisConversacionEstado] TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMAnalisisEvaluacionHumana] TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMAnalisisIntento] TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMAnalisisOperacion] TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMAnalisisPolitica] TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMAnalisisRecepcion] TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMArchivoMultimedia] TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMBandejaMiembro] TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMBandejaOperacion] TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMCampanaDestinatario] TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMCampanaPolitica] TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMCanalCredencial] TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMCanalCuenta] TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMCanalInstitucionalVinculoOrigen] TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMComentarioSocial] TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMContactoConsentimiento] TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMConversacionEvento] TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMCuentaCadencia] TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMEstrategiaOperacion] TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMEstrategiaPolitica] TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMEventoPreparacion] TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMEventoReintentoOperacion] TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMEventoWebhook] TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMIAAdmisionPolitica] TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMIAConexion] TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMIAConfiguracion] TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMIACredencial] TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMMensajeExterno] TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMMensajePlantilla] TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMProspectoMemoria] TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMRecontactoRegla] TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMRespuestaTrabajo] TO [rinovaplus_pg_reader];
    GRANT SELECT ON OBJECT::[dbo].[CRMUnificacionOperacion] TO [rinovaplus_pg_reader];

    EXECUTE AS USER = N'rinovaplus_pg_reader';
    SET @impersonated = 1;
    IF EXISTS (
        SELECT 1 FROM sys.fn_my_permissions(NULL, 'DATABASE')
        WHERE permission_name NOT IN (N'CONNECT', N'VIEW ANY COLUMN ENCRYPTION KEY DEFINITION',
                                      N'VIEW ANY COLUMN MASTER KEY DEFINITION')
    )
    OR EXISTS (
        SELECT 1 FROM @objects o
        WHERE ISNULL(HAS_PERMS_BY_NAME(o.qualified, 'OBJECT', 'SELECT'), 0) <> o.expected_read
           OR HAS_PERMS_BY_NAME(o.qualified, 'OBJECT', 'INSERT') = 1
           OR HAS_PERMS_BY_NAME(o.qualified, 'OBJECT', 'UPDATE') = 1
           OR HAS_PERMS_BY_NAME(o.qualified, 'OBJECT', 'DELETE') = 1
           OR HAS_PERMS_BY_NAME(o.qualified, 'OBJECT', 'EXECUTE') = 1
           OR HAS_PERMS_BY_NAME(o.qualified, 'OBJECT', 'ALTER') = 1
    )
    OR EXISTS (
        SELECT 1 FROM @columns c
        WHERE ISNULL(HAS_PERMS_BY_NAME(c.qualified, 'OBJECT', 'SELECT', c.name, 'COLUMN'), 0) <> c.expected_read
           OR HAS_PERMS_BY_NAME(c.qualified, 'OBJECT', 'UPDATE', c.name, 'COLUMN') = 1
    )
        THROW 51005, 'Unexpected permissions, including permissions inherited from public', 1;
    REVERT;
    SET @impersonated = 0;
    COMMIT;
END TRY
BEGIN CATCH
    IF @impersonated = 1 REVERT;
    IF XACT_STATE() <> 0 ROLLBACK;
    THROW;
END CATCH;
