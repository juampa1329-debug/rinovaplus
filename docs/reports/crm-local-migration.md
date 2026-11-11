# Recuperación comprobada; creación local detenida por auditoría DDL

**Aplicación local completada, 2026-10-15:** el propietario autorizó los INSERT automáticos de auditoría. La migración creó `crm.Contact`, `crm.Conversation`, `crm.Message` y `crm.Operation` vacías en DBSIIE; contrato `ADR-006-v1`, repetición no-op y cero transacciones abiertas. Solo hubo ocho auditorías automáticas; SIlogAuditoria permanece habilitado e idéntico. Metadatos y restantes conteos de las 722 tablas core y checksums de catálogos permanecen iguales. Backup y restauración siguen retenidos. Evidencia: `.local/sql-crm-migration-20261015/apply.json`. API/UI persistentes pendientes; no hubo publicación.

**Los registros siguientes describen el ensayo y los estados anteriores a esta aplicación.**

El propietario aceptó ADR-006 el 2026-10-15 y autorizó cuatro tablas `crm` solo en DBSIIE local. **La recuperación y el ensayo de la migración pasaron; la preservación total del core falló en la restauración por auditorías automáticas. DBSIIE original no recibió DDL y permanece intacta.**

| Comprobación | Resultado |
|---|---|
| Destino | SQLEXPRESS local y listener propio contrastados; TLS estricto, sin exponer credenciales. |
| Espacio | 3.62 GiB asignados; 292.74 GiB libres; reserva conservadora de 8.24 GiB. |
| Backup | Completo COPY_ONLY/CHECKSUM, medio nuevo, 3,527,599,104 bytes; VERIFYONLY correcto. Permanece en el directorio protegido de SQL. |
| Restauración real | Base nueva y dos archivos nuevos, guardias de colisión, sin REPLACE; CHECKDB cero errores. Backup y restauración retenidos. |
| Recuperación del core | Huella de metadatos y conteos exactos de 722 tablas, más checksums acotados de cuatro catálogos, coincidieron antes del ensayo. |
| Migración en restauración | Creación de cuatro tablas vacías, repetición no-op, rechazo de drift y rollback de fallo parcial comprobados. Sin FK hacia core; contrato ADR-006-v1. |
| Preservación tras ensayo | Metadatos intactos; solo `dbo.SIAuditoriaCambios` pasó de 51,447 a 51,457 filas. El trigger DDL habilitado `SIlogAuditoria` maneja `DDL_DATABASE_LEVEL_EVENTS`, usa EVENTDATA y ejecuta INSERT en esa tabla. |
| DBSIIE original | Baseline completo conservado; sin aplicación de la migración ni escrituras de negocio. |

Las diez auditorías corresponden al ensayo completo, incluidos los cambios de prueba del constraint; no se presentan como el número de filas que generaría únicamente la creación. No se leyeron filas de auditoría ni registros personales, no se deshabilitó el trigger ni se eliminaron datos. Los checksums de catálogos son una comprobación acotada, no una garantía criptográfica sobre todos los valores de las 722 tablas.

La primera inspección Windows del directorio protegido falló con `PermissionError` antes de iniciar el backup. Se conservó su ACL y se comprobó la existencia mediante metadata SQL y el espacio desde la raíz de volumen. La recuperación posterior pasó. El ensayo DDL terminó con una aserción de preservación fallida, no con un error de sintaxis; el diagnóstico identificó la auditoría existente como efecto real.

Fuente explícita: [001_local_crm.sql](../../backend/migrations/001_local_crm.sql), extraída del SQL aprobado sin cambiar tablas/columnas/constraints. El harness ensayó la restauración sustituyendo únicamente el guard de nombre de base en memoria. No hay migración al arrancar la aplicación. No ejecutar este SQL en DBSIIE hasta resolver la excepción de auditoría.

Evidencia local saneada: `.local/sql-crm-migration-20261015/`, con `preflight.json`, `backup.json`, `restore.json`, `core-before.json`, `core-restored.json` y `core-preservation-blocker.json`. `state.json` y `private-locations.json` identifican los artefactos locales retenidos; sus rutas físicas no se publican. Harness: `.local/sql-real-20261015/prepare_crm.py`. Documentos previos respaldados en `source-before/`; `.env` nunca se copió.

**Siguiente decisión:** permitir o no los INSERT automáticos de auditoría durante la creación local, conservando el trigger. La aprobación de las cuatro tablas ya existe; no se vuelve a solicitar. Implementación API/UI, activación TLS del producto y retirada de semillas quedan pendientes. Sin publicación ni despliegue.
