# Conexión local y mapeos existentes

**Actualización SQL-C1 (2026-10-24):** acceso/TLS local resuelto. El propietario confirmó HORARIOSSIIE como fragmento; motor16Express/compat160,50tablas/437columnas/41FK. DBSIIE no visible. Selector de inspección disponible, sin migraciones ni conexiónCRM activa. Ver [evidencia actual](SQL_C1_REVIEW.md) y [captura saneada](observed-schema.json). La configuración/aceptaciones históricas de DBSIIE de este documento no certifican esa base en el equipo actual.


## Actualización SQL-R1 — 2026-10-24

El propietario autorizó posteriormente la lectura conectada. [Preflight e informe actual](SQL_R1_REVIEW.md): falló SSL/TLS08001 sin conexión autenticada ni SQL ejecutado. La configuración conservada requiere aclarar entorno Docker anterior frente a instancia Windows actual; se pidió esa precisión. No se cambiaron credenciales/certificados, permisos o destino. Los párrafos inferiores conservan la verificación previa de presencia y mapeos, no una conexión exitosa.

Verificación de configuración/fuentes: 2026-10-24. El propietario confirmó **la copia local ya configurada** como referencia para comprender tablas y recordó los mapeos existentes en CRM CBN. Esta precisión complementa P1.3; no sustituye su límite de no conectar ni modificar la base.

## Qué se comprobó

Existe conexión implementada con pyodbc/ODBC Driver 18 y constructor compartido en [sql_target.py](../../../backend/app/sql_target.py). TLS obligatorio: Encrypt=Yes y TrustServerCertificate=No. El archivo privado `.env` existe y la configuración efectiva consultada indica `local_sql_copy`, con host, puerto, usuario, contraseña, base, máquina esperada y nombre de certificado presentes. No se guardaron ni imprimieron sus valores ni se cargó la aplicación. No se intentó conexión, autenticación, consulta SQL ni ejecución de runner.

La selección de perfil SQL no está explícitamente establecida como institucional; rige la configuración local. La mera presencia de credenciales **no demuestra conectividad, identidad, versión/edición o validez actual**. No hace falta pedir al propietario que vuelva a pegar esas credenciales en el chat. La futura inspección autorizada reutilizará el mecanismo privado, con alcance de metadatos/lectura y TLS/guardas intactos; no iniciar el runtime o workers para probarla.

## Rutas y contratos que se reutilizan

| Área | Fuente existente | Autoridad de datos |
|---|---|---|
| Períodos, escuelas, modalidades y programas | [lector de catálogo](../../../backend/app/modules/catalog/infrastructure/sql_reader.py), [API](../../../backend/app/modules/catalog/api/router.py) | dbo.GEPeriodo, dbo.ACEscuela, dbo.ACModalidad y dbo.ACProgramas, con proyecciones SQL fijas/parametrizadas. |
| Admisiones y oferta académica | [servicio](../../../backend/app/modules/admissions/application/service.py), [rutas](../../../backend/app/modules/admissions/api/router.py) | Lecturas existentes de SIIE; no reemplazarlas por tablas CRM autoritativas. |
| Perfil declarado y candidatos de identidad | [rutas de identidad](../../../backend/app/modules/contacts/api/router.py) | GETipoIdentidad, GEPeriodo, ACProgramas y relaciones con ACAspirante/GEEstudiante/ACProgramaOfrecido. No unir identidades automáticamente por parecido. |
| Contrato académico de empleados | [003](../../../backend/migrations/003_local_inbox.sql) | GEEmpleado como precondición de forma/lectura; no una migración de esa tabla. |
| Inventario previo de estructura | [informe DBSIIE](../../reports/dbsiie-schema-inventory.md) | Captura histórica de catálogos; fecha 2026-10-14, sin nueva conexión en este corte. |

La captura `.local/sql-inventory/schema-snapshot.json` y el manifiesto `.local/sql-inventory/query-manifest.json` existen y sus SHA-256 coinciden con los publicados en el informe histórico. Sólo se comprobaron existencia/bytes; no se exportaron ni copiaron archivos privados al repositorio. El informe conserva 21 conjuntos de metadatos y límites de visibilidad, sin filas de negocio. Las cifras/objetos son de aquel corte y no certifican el estado del 24 de octubre.

El inventario académico anterior y el inventario de 19 migraciones CRM de P1.1 son capas diferentes. P1.3 usa ambos para delimitar precondiciones y recuperación; no infiere que la estructura institucional coincida con esta copia, que existan las 68 tablas CRM, ni que un snapshot histórico sustituya el futuro modelo completo de drift.
