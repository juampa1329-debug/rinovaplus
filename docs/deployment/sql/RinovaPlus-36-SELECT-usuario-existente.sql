-- Abrir el archivo en SSMS como DBA, elegir DBSIIE_2025A y ejecutar con F5.
-- Escribir el login de SQL Server que usa RinovaPlus y dejar OTORGAR para habilitar.
-- Tras la extracción, usar el mismo login y cambiar OTORGAR por RETIRAR abajo.
GO

IF @@TRANCOUNT <> 0
BEGIN
    RAISERROR ('Ejecute el archivo en una ventana nueva, sin transaccion activa.', 16, 1);
    RETURN;
END;

SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @LoginSql sysname = N'REEMPLAZA_POR_TU_LOGIN_SQL';
DECLARE @Accion varchar(8) = 'OTORGAR';
DECLARE @Rol sysname = N'rinovaplus_pg_select36_tmp';

IF DB_NAME() <> N'DBSIIE_2025A'
    THROW 51100, 'Selecciona DBSIIE_2025A en SSMS y ejecuta el archivo de nuevo.', 1;
IF @Accion NOT IN ('OTORGAR', 'RETIRAR')
    THROW 51101, 'Usa OTORGAR o RETIRAR en @Accion.', 1;
IF @LoginSql = N'REEMPLAZA_POR_TU_LOGIN_SQL' OR NULLIF(LTRIM(RTRIM(@LoginSql)), N'') IS NULL
    THROW 51102, 'Escribe el nombre del login SQL actual en @LoginSql.', 1;

DECLARE @Usuario sysname, @UsuarioId int;
SELECT @Usuario = u.name, @UsuarioId = u.principal_id
FROM sys.server_principals AS l
JOIN sys.database_principals AS u ON u.sid = l.sid
WHERE l.name = @LoginSql AND l.type = 'S'
  AND (l.is_disabled = 0 OR @Accion = 'RETIRAR')
  AND u.type = 'S' AND u.authentication_type = 1 AND u.principal_id > 4;
IF @UsuarioId IS NULL
    THROW 51103, 'El login SQL necesita un usuario existente en esta base. Verifica el nombre y ejecuta como DBA.', 1;

DECLARE @Tablas TABLE (nombre sysname PRIMARY KEY, objeto int NULL);
INSERT @Tablas (nombre) VALUES
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

DECLARE @RolId int, @Lock int, @Sql nvarchar(max), @Permisos int = 0;
BEGIN TRY
    BEGIN TRANSACTION;
    EXEC @Lock = sys.sp_getapplock
        @Resource = N'RinovaPlus-SELECT36-temporal', @LockMode = 'Exclusive',
        @LockOwner = 'Transaction', @LockTimeout = 5000;
    IF @Lock < 0
        THROW 51104, 'Otra sesion opera el rol temporal. Vuelve a ejecutar el archivo.', 1;

    SELECT @RolId = principal_id FROM sys.database_principals WHERE name = @Rol;
    IF @RolId IS NULL AND @Accion = 'RETIRAR'
    BEGIN
        COMMIT;
        SELECT N'ACCESO_YA_RETIRADO' AS estado, @LoginSql AS login_sql, @Usuario AS usuario_base;
        RETURN;
    END;

    UPDATE @Tablas SET objeto = OBJECT_ID(N'[dbo].' + QUOTENAME(nombre), N'U');
    IF @Accion = 'OTORGAR' AND EXISTS (SELECT 1 FROM @Tablas WHERE objeto IS NULL)
    BEGIN
        SELECT nombre AS tabla_faltante FROM @Tablas WHERE objeto IS NULL ORDER BY nombre;
        THROW 51105, 'Faltan tablas del alcance CRM. Se cancela el otorgamiento.', 1;
    END;

    IF @RolId IS NOT NULL
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM sys.database_principals
            WHERE principal_id = @RolId AND type = 'R'
              AND is_fixed_role = 0 AND owning_principal_id = DATABASE_PRINCIPAL_ID(N'dbo')
        )
        OR (SELECT COUNT(*) FROM sys.database_role_members WHERE role_principal_id = @RolId) <> 1
        OR NOT EXISTS (
            SELECT 1 FROM sys.database_role_members
            WHERE role_principal_id = @RolId AND member_principal_id = @UsuarioId
        )
        OR EXISTS (SELECT 1 FROM sys.database_role_members WHERE member_principal_id = @RolId)
        OR EXISTS (
            SELECT 1 FROM sys.database_permissions AS p
            WHERE p.grantee_principal_id = @RolId
              AND (p.class <> 1 OR p.minor_id <> 0 OR p.type <> 'SL' OR p.state <> 'G'
                   OR NOT EXISTS (SELECT 1 FROM @Tablas AS t WHERE t.objeto = p.major_id))
        )
            THROW 51106, 'El rol temporal existente tiene otro titular o permisos ajenos. Revisar con el DBA.', 1;
    END;

    IF @Accion = 'OTORGAR'
    BEGIN
        IF @RolId IS NULL
        BEGIN
            SET @Sql = N'CREATE ROLE ' + QUOTENAME(@Rol) + N' AUTHORIZATION [dbo];';
            EXEC sys.sp_executesql @Sql;
            SET @RolId = DATABASE_PRINCIPAL_ID(@Rol);
        END;

        SELECT @Sql = STRING_AGG(CONVERT(nvarchar(max),
            N'GRANT SELECT ON OBJECT::[dbo].' + QUOTENAME(t.nombre) + N' TO ' + QUOTENAME(@Rol) + N';'
        ), NCHAR(10))
        FROM @Tablas AS t
        WHERE NOT EXISTS (
            SELECT 1 FROM sys.database_permissions AS p
            WHERE p.grantee_principal_id = @RolId AND p.class = 1 AND p.major_id = t.objeto
              AND p.minor_id = 0 AND p.type = 'SL' AND p.state = 'G'
        );
        IF @Sql IS NOT NULL EXEC sys.sp_executesql @Sql;

        IF NOT EXISTS (
            SELECT 1 FROM sys.database_role_members
            WHERE role_principal_id = @RolId AND member_principal_id = @UsuarioId
        )
        BEGIN
            SET @Sql = N'ALTER ROLE ' + QUOTENAME(@Rol) + N' ADD MEMBER ' + QUOTENAME(@Usuario) + N';';
            EXEC sys.sp_executesql @Sql;
        END;

        SELECT @Permisos = COUNT(*) FROM sys.database_permissions
        WHERE grantee_principal_id = @RolId AND class = 1 AND minor_id = 0 AND type = 'SL' AND state = 'G';
        IF @Permisos <> 36
            THROW 51107, 'El rol temporal debe tener exactamente 36 permisos SELECT.', 1;

        -- Comprueba el acceso efectivo a todas las columnas sin consultar sus datos.
        DECLARE @Bloqueo nvarchar(2048);
        SELECT @Sql = STRING_AGG(CONVERT(nvarchar(max),
            N'IF @Bloqueo IS NULL AND ISNULL(HAS_PERMS_BY_NAME(' + QUOTENAME(N'[dbo].' + QUOTENAME(t.nombre), '''') +
            N', ''OBJECT'', ''SELECT'', ' + QUOTENAME(c.name, '''') + N', ''COLUMN''), 0) <> 1 ' +
            N'SET @Bloqueo = N' + QUOTENAME(N'Sin SELECT efectivo en ' + t.nombre, '''') + N';'
        ), NCHAR(10))
        FROM @Tablas AS t JOIN sys.columns AS c ON c.object_id = t.objeto;
        SET @Sql = N'EXECUTE AS USER = ' + QUOTENAME(@Usuario, '''') + N';
            BEGIN TRY
                ' + @Sql + N'
                REVERT;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK;
                REVERT;
                THROW;
            END CATCH;';
        EXEC sys.sp_executesql @Sql, N'@Bloqueo nvarchar(2048) OUTPUT', @Bloqueo OUTPUT;
        IF @Bloqueo IS NOT NULL
            THROW 51108, @Bloqueo, 1;
    END;
    ELSE
    BEGIN
        SET @Sql = N'ALTER ROLE ' + QUOTENAME(@Rol) + N' DROP MEMBER ' + QUOTENAME(@Usuario) + N';
            DROP ROLE ' + QUOTENAME(@Rol) + N';';
        EXEC sys.sp_executesql @Sql;
    END;

    COMMIT;
    SELECT CASE WHEN @Accion = 'OTORGAR' THEN N'ACCESO_OTORGADO' ELSE N'ACCESO_RETIRADO' END AS estado,
           @LoginSql AS login_sql, @Usuario AS usuario_base, @Permisos AS permisos_select_del_rol;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK;
    THROW;
END CATCH;
GO
