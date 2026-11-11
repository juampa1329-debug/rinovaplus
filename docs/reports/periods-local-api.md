# Primera API de períodos: corte local implementado

**Snapshot histórico P-035:** conserva la primera entrega de períodos. La frontera actual incluye también escuelas, modalidades y programas, ampliados por aprobaciones específicas a sus columnas DTO. [Estado vigente, controles y evidencia A-025/P-037](programs-local-api.md). Las afirmaciones siguientes sobre lector exclusivo de GEPeriodo y otros catálogos pendientes corresponden a aquel cierre inicial, anterior a las ampliaciones.

**Fecha:** 2026-10-14, America/Bogota. **Estado:** primer catálogo de períodos implementado y verificado con DBSIIE real, HTTP y navegador local; corte P-035 completado. El propietario autorizó primero con «Adelante» el recorrido React → FastAPI → SQL Server, y después amplió exclusivamente la seguridad del lector: **«Sí, crea crm_catalog_reader con lectura solo de dbo.GEPeriodo, bloquea los permisos heredados adicionales y continúa con la prueba real, sin modificar tablas ni datos.»** Toda la unidad corresponde al worktree SQL, rama `feat/sqlserver-python-api`; otros catálogos, IAM empresarial y fase 1 completa siguen pendientes.

## Resultado y evidencia

DTO, puerto/caso de uso paginado, entrada FastAPI protegida y adaptador de lectura estática implementados. React añade un catálogo independiente en Conocimiento con acceso manual temporal solo en memoria, selección por ID y estados explícitos. Otros módulos siguen siendo demos. [Guía de ejecución](../integration/periods-local-runbook.md), [ADR-005](../decisions/ADR-005-local-period-catalog.md).

| Capa | Evidencia |
|---|---|
| Backend | Ruff formato/check aprobados; pytest **61 pruebas** aprobadas tras la corrección acotada de la PK, siete de salud conservadas. Compatibilidad de las 25 dependencias comprobada antes de la corrección; lockfiles intactos. |
| Frontend | `npm run check` completo aprobado: formato, lint, tipos, Vitest **68 pruebas**, build Vite; ocho pruebas nuevas y 60 anteriores conservadas. |
| Negativos | Auth inválida/ausente/duplicada antes de SQL; query desconocida/duplicada/rangos/inyección; roles elevados, permisos amplios/ajenos; error/timeout/ocupado, NULL/drift, TLS fijo y cierre/parametrización. |
| React | Sin auto-fetch o almacenamiento del token; fechas/bit/IDs negativos, páginas, vacío, 503/reintento sin fallback y descarte/abort obsoleto. |
| Normalización | Trece archivos base normalizados exclusivamente CRLF→LF; comparación acreditó **13/13 diferencias solo EOL**. Copias/SHA256 previos y posteriores: `.local/periods/normalization-before/`. |
| SQL/TLS real | QA independiente Python/pyodbc con ODBC Driver 18 (`18.06.0002`), certificado validado (`TrustServerCertificate=False`), `encrypt_option=TRUE`, Shared memory. Lector restringido con flags `[0,0,0,0,1]`, sin roles amplios; matriz efectiva DML/ALTER/CONTROL/EXECUTE y permisos ajenos en cero. Adaptador devolvió **32 períodos reales** acotados, schema validado y sin persistir filas completas. |
| Guard SQL | Expresión CASE exacta comprobada en SQL Server con cinco casos sintéticos: tabla y PK propia → PERIOD; otra tabla/PK y trigger propio → OTHER. La clasificación reconoce únicamente tipo PK cuyo padre es GEPeriodo; no nombre hardcodeado ni ampliación de OTHER. Bloqueo administrativo inicial sigue comprobado sin consulta de negocio. |
| HTTP real | **Doce casos aprobados** bajo lector restringido: páginas primera/siguiente/máximo/vacía con 200, 401 sin auth, 422 límite/duplicado/desconocido, live 200/ready 503, CORS aprobado y Host ajeno 400. Envelope y campos exactos; orden estable y sin solapamiento. |
| Navegador | IAB con fuente real: **25 períodos en página 1 y 7 en página 2**; selección muestra fechas/bit originales, Siguiente deshabilitado al final y Anterior vuelve a página 1 descartando selección. Escritorio y móvil emulado 390×844 sin overflow horizontal. Negativos 503/401, clave borrada al navegar y ausencia de fallback comprobados en QA inicial. |
| Invariantes | PUBLIC de servidor/base y esquema de negocio **sin cambios**; cero mutaciones de negocio. Nueve DENY exclusivos al usuario nuevo, sin roles amplios. |
| Inmutabilidad | QA final contrastó **41 hashes fuente/prueba** con freeze de la corrección, lista `source_hash_changed` vacía. Fuente y pruebas no cambian durante este cierre documental. |

Instalaciones iniciales en sandbox fallaron por cache uv denegada y DNS npm; se completaron con cache local/escalación autorizada, sin herramientas globales. Pytest inicial sin escalación quedó sin resultado por socketpair Windows: se interrumpió y la ejecución autorizada aprobó 57/57. Primer `npm run check` se detuvo por EOL heredado; tras respaldo/normalización se ejecutó completo y aprobó. No se presentan esos intentos como pruebas aprobadas.

Evidencia final privada saneada: `.local/periods/reader-live-qa.json`, `reader-acl-qa.json`, `reader-qa-freeze.json` y `browser/reader-qa.json`; capturas `browser/reader-desktop.png` y `browser/reader-mobile.png`. La evidencia inicial de bloqueo se conserva separada en `live-qa.json`, `metadata-qa.json` y `browser/qa.json`. No guardar filas completas, secretos o stacks en informes. Procesos propios siguen activos en `http://127.0.0.1:5193/#/knowledge` y `http://127.0.0.1:8013`; tab de entrega conservada. Verificar identidad del PID propio antes de detener/reiniciar; nunca reutilizar procesos de otra carpeta.

La primera prueba real del lector restringido se detuvo por un falso positivo: SQL Server reportó SELECT heredado sobre la PK de GEPeriodo y el guard la clasificó OTHER. No se leyeron filas en ese intento. La reversión inicial del login falló por conexión propia activa; se cerró esa conexión y se completó limpieza verificando identidad/SID y ausencia previa, sin eliminar principals ajenos. El segundo intento conservó la cuenta correcta; se corrigió únicamente el CASE por tipo/parent y se verificó la lectura. No se relajaron permisos ni se añadió GRANT para que el test pasara.

La comprobación final acredita catálogo real 200, TLS, permisos efectivos y el recorrido React → FastAPI → DBSIIE. **No acredita teléfono físico, producción, IAM/RBAC empresarial, semántica de inscripción o fase 1 íntegra.**

## Identidad mínima autorizada y verificada

La metadata confirmó autenticación SQL mixta ya habilitada e identidad ausente antes de la creación autorizada. Se creó `crm_catalog_reader` con el alcance literal aprobado. **No se cambió autenticación del servidor, reinició SQL ni modificó PUBLIC globalmente.**

| Ámbito | Cambio autorizado y comprobado |
|---|---|
| Instancia local | Login `crm_catalog_reader` creado, sin roles de servidor. Secreto generado/suministrado privadamente, sin exposición en scripts versionables, argumentos o logs. |
| DBSIIE | Usuario `crm_catalog_reader` asociado al login, sin roles amplios; `GRANT SELECT ON OBJECT::dbo.GEPeriodo TO crm_catalog_reader` comprobado. |
| DBSIIE: SELECT heredado | `DENY SELECT ON OBJECT::dbo.RWConsultas TO crm_catalog_reader`, para bloquear el permiso heredado de PUBLIC sobre este objeto de usuario ajeno. |
| DBSIIE: EXECUTE heredado | `DENY EXECUTE ON OBJECT::<objeto> TO crm_catalog_reader` para los ocho objetos de la lista siguiente; no alterar PUBLIC. |
| Verificación | Metadata nueva, guard, TLS, consulta de 32 períodos, doce casos HTTP y navegador aprobados; esquema/PUBLIC intactos. Si aparece otro permiso efectivo en el futuro, detener y revisar. |
| Secreto local | Windows DPAPI CurrentUser; blob y carpeta ignorados con herencia ACL deshabilitada y único acceso del usuario actual. Verificación ACL aprobada, sin secreto en texto plano persistido. Recuperación solo en memoria mediante helper privado documentado en la guía. |
| Reversión disponible | Tras autorizarla, comprobar propiedad/uso y cerrar sesiones propias: retirar solo el usuario nuevo de DBSIIE (`DROP USER crm_catalog_reader`) y luego login nuevo (`DROP LOGIN crm_catalog_reader`). No eliminar identidades preexistentes u objetos de negocio. La cuenta verificada se conserva activa. |

Ocho EXECUTE heredados denegados **solo al usuario nuevo**: `dbo.CAEncuestaEsquema`, `dbo.fn_diagramobjects`, `dbo.sp_alterdiagram`, `dbo.sp_creatediagram`, `dbo.sp_dropdiagram`, `dbo.sp_helpdiagramdefinition`, `dbo.sp_helpdiagrams`, `dbo.sp_renamediagram`. Junto al DENY SELECT de RWConsultas suman nueve DENY. Los cuerpos no se leyeron ni ejecutaron; el guard mantiene el rechazo de esos permisos.

Permisos públicos de metadata `CONNECT`, `VIEW ANY COLUMN ENCRYPTION KEY DEFINITION` y `VIEW ANY COLUMN MASTER KEY DEFINITION`, junto a `CONNECT SQL`/`VIEW ANY DATABASE`, se permiten sin conceder claves privadas. La cuenta administrativa nunca será fallback; `readonly=True` no sustituye permisos efectivos.

## Límites

Token local no equivale a IAM/RBAC empresarial. Solo se modificó seguridad SQL del nuevo lector por aprobación específica: **tablas, datos y PUBLIC permanecen intactos**. No otros catálogos, endpoints personales, POST/PATCH, DDL de negocio/DML/EXECUTE, migraciones, sincronización, pagos, IA, publicación Git o despliegue. Fase 1 y naturaleza/aislamiento de datos de prueba conservan partes pendientes antes de ampliar acceso.
