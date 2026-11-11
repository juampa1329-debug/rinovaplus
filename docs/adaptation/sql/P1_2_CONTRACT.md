# P1.2 — Contrato seguro de entorno y destino SQL Server 2019

Fecha: 2026-10-24. Estado: implementado y verificado offline. Autorización: contrato de configuración/destino, TLS y validaciones; **sin conectar, consultar ni modificar una base**. P1 general continúa abierto. [Inventario previo](P1_1_REVIEW.md), [roadmap](../../SCENTRA_ADAPTATION_ROADMAP.md), [ADR-012](../../decisions/ADR-012-sql-target-contract.md).

## Separación entre destino y operación

`CRM_SQL_ENVIRONMENT` admite `local_copy` (predeterminado) o `institutional`. Es un perfil de destino independiente de `CRM_APP_MODE`; no existe un nuevo modo productivo. El arranque continúa en `local_demo` por defecto, con SQL sin activar.

| Perfil / modo | Resultado |
|---|---|
| `local_copy` / `local_demo` | Configuración local, catálogo y workspace sin activar. |
| `local_copy` / `local_readonly_catalog` | Lector local existente, token/orígenes loopback y permisos mínimos intactos. |
| `local_copy` / `local_sql_copy` | Copia local existente, TCP local explícito, máquina aprobada y certificado `localhost`; conserva sus guardas. |
| `institutional` / `local_demo` | Preparación offline del contrato institucional. Sin conexión por crear/importar configuración. |
| `institutional` / `local_readonly_catalog` | Camino de catálogo preparado con transporte readonly y validaciones; requiere activación/autorización independiente para consultarlo. No se utilizó en esta entrega. |
| `institutional` / `local_sql_copy` | Rechazado. No habilita rutas de escritura ni workers. |

El constructor compartido rechaza además **todo workspace institucional**, incluso con `Settings` construido directamente o modo demo/readonly. Para workspace local exige `local_sql_copy`. Preparar un destino no acredita autenticación institucional, RBAC, readiness, migraciones ni operación productiva. Esas aceptaciones pertenecen a P1.3/P1.4/P2 y etapas siguientes.

## Variables y valores explícitos

La [plantilla pública](../../../.env.example) conserva defaults seguros. No se editó ni imprimió `.env`. Una ejecución inicial detectó que python-dotenv 1.1.0 del host ignoraba `PYTHON_DOTENV_DISABLED` y cargaba involuntariamente el entorno privado al construir la app de pruebas. Se corrigió la barrera de colección redirigiendo además la ruta antes de importar la app; las pruebas finales usan sólo configuración sintética. No hubo conexión SQL ni salida de secretos. El [Compose de desarrollo](../../../compose.yaml) transmite una lista explícita y no ejecutó contenedores; no es una receta institucional aceptada.

| Variable | Contrato |
|---|---|
| `CRM_SQL_ENVIRONMENT` | `local_copy` o `institutional`; cualquier otro valor falla. |
| `CRM_SQL_HOST` / `CRM_SQL_PORT` | Institucional: DNS/IPv4 y puerto ASCII decimal 1–65535, ambos explícitos; sin URL, instancia, coma, punto y coma ni comodines. |
| `CRM_SQL_DATABASE` | Institucional: obligatorio, sin asumir DBSIIE. Nombre de 1–128 caracteres, sin controles ni espacios exteriores; se delimita/escapa para ODBC. Local: exclusivamente DBSIIE. |
| `CRM_SQL_USER` / `CRM_SQL_PASSWORD` | Ambos o ninguno; TCP exige ambos. Sin caracteres de control. Nunca se imprimen; `}` se duplica dentro de valores ODBC delimitados. No existe fallback institucional a autenticación integrada. |
| `CRM_SQL_CERTIFICATE_HOSTNAME` | Institucional: nombre DNS/IPv4 explícito del certificado, validado sintácticamente; independiente del alias TCP. Local workspace: `localhost`. |
| `CRM_SQL_EXPECTED_MACHINE` | Institucional obligatorio: `SERVERPROPERTY('MachineName')`, valor exacto. Puede diferir del DNS usado para conectar. Obligatorio también para workspace local. |
| `CRM_SQL_EXPECTED_SERVER` | Institucional obligatorio: `SERVERPROPERTY('ServerName')`, valor exacto; no es una cadena de conexión. |
| `CRM_SQL_EXPECTED_INSTANCE` | Institucional obligatorio: nombre exacto o literal `DEFAULT`. `DEFAULT` exige `InstanceName IS NULL`; vacío no significa cualquier instancia. Local permanece SQLEXPRESS. |
| `CRM_SQL_EXPECTED_LOGIN` | Institucional obligatorio: coincide tanto con `ORIGINAL_LOGIN()` como con `SUSER_SNAME()`; rechaza suplantación de contexto. |
| `CRM_SQL_EXPECTED_DATABASE_USER` | Institucional obligatorio: `USER_NAME()` exacto. |
| `CRM_SQL_SERVER` | Guard heredado de la copia local, `localhost\SQLEXPRESS`; no selecciona el endpoint institucional. Usar HOST/PORT y EXPECTED_SERVER. |

Ejemplo **sintético**, incompleto deliberadamente en secretos, no es una orden de activación:

```dotenv
CRM_APP_MODE=local_demo
CRM_SQL_ENVIRONMENT=institutional
CRM_SQL_HOST=sql.cbn.example.invalid
CRM_SQL_PORT=1433
CRM_SQL_DATABASE=CBN_SIIE
CRM_SQL_CERTIFICATE_HOSTNAME=sql.cbn.example.invalid
CRM_SQL_EXPECTED_MACHINE=CBN-SQL
CRM_SQL_EXPECTED_SERVER=CBN-SQL
CRM_SQL_EXPECTED_INSTANCE=DEFAULT
CRM_SQL_EXPECTED_LOGIN=cbn_catalog
CRM_SQL_EXPECTED_DATABASE_USER=cbn_catalog_user
# Inyectar USER/PASSWORD restringidos mediante el mecanismo privado acordado.
```

Los metadatos reales, la edición y los nombres esperados no se conocen todavía. Los valores de ejemplo no deben sustituir evidencia aprobada. SQL Server debe tener identidad estable; no derivar automáticamente una expectativa del mismo servidor que se está verificando.

## TLS y verificación antes de negocio

Constructor único en [sql_target.py](../../../backend/app/sql_target.py), sin IO al importar. ODBC Driver 18 con `Encrypt=Yes;TrustServerCertificate=No` fijos; no se agrega una opción para desactivar cifrado o confianza. `HostnameInCertificate` selecciona el nombre validado, sin sustituir la validación de cadena. La CA institucional deberá instalarse mediante el mecanismo revisado en P1.4; no se incorporan certificados, claves ni dependencias. [Semántica oficial ODBC/TLS](https://learn.microsoft.com/en-us/sql/connect/odbc/dsn-connection-string-attribute?view=sql-server-ver15).

La consulta fija `IDENTITY_SQL` comprueba base, instancia, máquina y servidor; motor mayor **15**, edición de motor 2/3/4 (familia SQL Server), edición textual presente, compatibilidad **130/140/150** y principal original/efectivo/usuario. Rechaza metadatos ausentes, tipo incompatible, base/instancia equivocada, versiones 2017/2022 y servicios Azure distintos. Sólo `DEFAULT` permite NULL y sólo en InstanceName. [SERVERPROPERTY y valores de edición/instancia/versión](https://learn.microsoft.com/en-us/sql/t-sql/functions/serverproperty-transact-sql?view=sql-server-ver15), [compatibilidad de base](https://learn.microsoft.com/en-us/sql/t-sql/statements/alter-database-transact-sql-compatibility-level?view=sql-server-ver15). No cambia automáticamente compatibilidad ni permisos.

El lector de catálogos ejecuta primero `verify_principal` (roles y allowlist estricta), después identidad, después la proyección parametrizada de negocio. Conserva `readonly=True`, `autocommit=True`, límites, timeout, semáforo y cierre de recursos, incluso al fallar. No exige marker CRM ni permisos adicionales sobre ese esquema; puede preparar lectura SIIE previa a nuevas migraciones.

El workspace local y los consumidores que importan su API mantienen `verify_target`: identidad compartida, marker exacto `crm.contract=ADR-006-v1` y `SHAPE_SQL`. No se sustituyó la validación de forma por sólo un marker. Conservar transacción, applock, commit/rollback y controles de cada módulo. No se alteró ningún runner ni archivo SQL histórico; los guards locales SQL y sus riesgos NULL/transacción siguen pendientes de P1.3.

## Evidencia y límites

Pruebas de contrato/catálogo/configuración/workspace/loader con cursor y transporte ficticios, bloqueo de IO real y `.env` privado redirigido antes de colección. Casos: perfiles, campos obligatorios, inyección ODBC/TLS, instancia nombrada/predeterminada, metadatos NULL/incorrectos, motor/compatibilidad/principales, validación anterior a negocio, liberación de capacidad y cierre, marker/forma y ausencia de activación por configurar destino.

Resultados exactos, huellas y comandos en [p1_2_validation.json](p1_2_validation.json). Dos fallos preexistentes en la comprobación ampliada se registran sin atribuir aprobación de toda la suite: fixture IA sin `application.state.settings` y expectativa de revisión histórica frente al comportamiento actual de replay compacto. No se cambió producto IA/replay para resolverlos.

Se consultaron grafos antes de fuentes y se actualizaron AST, brechas, inventario de declaraciones/consumidores y huellas después del cambio. El grafo no prueba conectividad ni representa un esquema aplicado. No se ejecutaron migradores, preflight, SQL real, servidores, workers, proveedor, contenedores o despliegue. Falta verificar en una copia autorizada TLS real, versión/edición/compatibilidad y metadatos/principal exactos; no se considera completada esa aceptación conectada.

Siguiente unidad seleccionable: **P1.3**, secuencia/historial/drift/reversión de migraciones, conservando las 19 históricas y el salto 010. No aplicarlas por continuación automática.
