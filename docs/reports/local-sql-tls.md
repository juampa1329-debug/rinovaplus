# Certificado y conexión SQL Server local verificados

**Fecha:** 2026-10-14, America/Bogota. **Alcance:** resolver el certificado de la instancia local `SQLEXPRESS` y comprobar acceso a `DBSIIE`, por autorización del propietario. Esta unidad no implementa integración Python ni APIs.

## Resultado comprobado

La conexión con autenticación integrada de Windows, cifrado solicitado y validación de certificado activa funcionó contra `localhost\SQLEXPRESS`, base `DBSIIE`. Una segunda comprobación independiente desde Windows PowerShell 5.1, con usuario no elevado, confirmó el resultado. Usar ese nombre local canónico: la forma `.\SQLEXPRESS` falló por discrepancia del nombre principal del certificado y no se considera validada.

| Evidencia de metadata | Resultado |
|---|---|
| Base abierta | `DBSIIE` |
| Versión SQL Server | `17.0.1000.7` |
| Edición | Express, 64 bits |
| Transporte de esta sesión | `Shared memory` |
| `encrypt_option` | `TRUE` |
| Validación de certificado | `TrustServerCertificate=False` |
| Autenticación | Windows integrada |
| Comprobación del helper, UTC | `2026-10-14T16:04:49.6872364Z` |

Las consultas se limitaron a nombre de base, propiedades del servidor y metadata de la sesión actual. No se leyeron filas de negocio ni se realizaron escrituras, DDL o inventario de tablas/datos personales.

## Configuración aplicada y reversión

Se creó un certificado local autofirmado de autenticación de servidor, RSA 2048/SHA-256, vigencia de doce meses, clave no exportable y `KeySpec=KeyExchange`. Se concedió lectura exclusivamente a la cuenta del servicio SQL sobre la clave nueva; se instaló la confianza pública en el almacén raíz del usuario actual y se configuró el vínculo del certificado de esta instancia. La confianza se limita a ese usuario y máquina.

Se reinició únicamente SQL Server y su dependiente Launchpad previamente activo; SQL Agent permaneció detenido. El certificado anterior no relacionado se conservó. `ForceEncryption=0`, TCP y Named Pipes no cambiaron; estos dos protocolos siguen deshabilitados. Los clientes comprobados solicitaron cifrado explícitamente.

Los helpers `Configure-LocalSqlTls.ps1` y `Rollback-LocalSqlTls.ps1`, el estado previo, resultados y certificado público permanecen en `.local/sql-tls/`, ignorado por Git. Identificadores de máquina, SID, huellas y ubicaciones de claves no se incorporan a este informe. Ambos scripts pasaron el parser de PowerShell. El helper de configuración se ejecutó correctamente; el rollback está preparado, **no fue ejecutado ni acreditado como probado operativamente**.

La configuración sigue las referencias de Microsoft sobre [configurar cifrado de SQL Server](https://learn.microsoft.com/en-us/sql/database-engine/configure-windows/configure-sql-server-encryption?view=sql-server-ver17) y [requisitos de certificados](https://learn.microsoft.com/en-us/sql/database-engine/configure-windows/certificate-requirements?view=sql-server-ver17).

## Límites y siguiente paso

Esta evidencia corresponde a la sesión local por memoria compartida. No acredita conexión TCP, acceso desde otras máquinas, integración Python/ODBC/API, permisos SQL mínimos, aislamiento de entornos ni anonimización de `DBSIIE`. No cambiaron fuentes de frontend/backend; no se requieren ni se reportan nuevos builds o tests de aplicación por esta unidad.

P-001 y P-006 conservan sus partes pendientes: inventario y contratos de lectura permitida, naturaleza y tratamiento de los datos de prueba, roles/permisos mínimos, separación de entornos y política de secretos. El siguiente trabajo es definir esos contratos y preparar la integración Python local con aceptación propia; el certificado no cierra la fase 1 ni autoriza escrituras core.
