# Inventario de migraciones SQL Server

P1.1 · 2026-10-24. Inventario estático reproducible; no se consultó ni modificó ninguna base. Declaraciones del repositorio no prueban aplicación en la base institucional. Los ALTER y cambios dinámicos se conservan por separado.

## Recuento

- migration_files: 19
- maximum_ordinal: 20
- missing_ordinals: [10]
- schemas: 13
- declared_tables: 68
- declared_columns: 596
- table_constraints: 132
- foreign_keys: 92
- explicit_create_indexes: 31
- alter_table_occurrences: 12
- alter_added_columns: 1
- alter_modified_columns: 5
- alter_foreign_keys: 1
- versioned_runners: 9

**010 no existe:** no es una migración pendiente de aplicar ni se debe rellenar el ordinal por inferencia. El plan P0 decía 20 por el máximo ordinal; existen 19 archivos.

## Secuencia y dependencias

| ID | Propósito | Tablas | Dependencias por FK | Runner encontrado |
|---|---|---:|---|---|
| [001](../../../backend/migrations/001_local_crm.sql) | Persistencia CRM: contacto, conversación, mensajes y diario idempotente | 4 | — | No versionado en tools |
| [002](../../../backend/migrations/002_local_admissions.sql) | Casos de admisión y seguimiento CRM sin modificar aspirantes oficiales | 3 | — | No versionado en tools |
| [003](../../../backend/migrations/003_local_inbox.sql) | Membresía, agentes, asignación dual, tareas y SLA | 6 | 001 | No versionado en tools |
| [004](../../../backend/migrations/004_conversation_events.sql) | Eventos durables y preparación incremental recuperable | 3 | 001 | No versionado en tools |
| [005](../../../backend/migrations/005_conversation_analysis.sql) | Política de análisis, contexto, recibos, intentos y feedback | 6 | 001, 004 | No versionado en tools |
| [006](../../../backend/migrations/006_crm_configuration.sql) | Configuración compartida de etapas, etiquetas y campos derivada del CRM existente | 2 | — | No versionado en tools |
| [007](../../../backend/migrations/007_institutional_identity.sql) | Perfil institucional declarado por contacto | 1 | 001 | No versionado en tools |
| [008](../../../backend/migrations/008_contact_merge.sql) | Unificación lógica reversible y diario de operaciones | 2 | 001 | No versionado en tools |
| [009](../../../backend/migrations/009_conversation_strategy.sql) | Planes con evidencia, feedback y autonomía interna acotada | 3 | 001, 003 | No versionado en tools |
| [011](../../../backend/migrations/011_channels.sql) | Cuentas, secretos cifrados, eventos de webhook, identidades externas, outbox única, comentarios y auditoría de canales. | 8 | 001 | migrate_channels.py |
| [012](../../../backend/migrations/012_channels_identity_collation.sql) | Preservar identificadores opacos de proveedores con collation binaria y reconstruir claves dependientes. | 0 | — | migrate_channels.py |
| [013](../../../backend/migrations/013_ai_providers.sql) | Configuración IA, conexión/consentimiento de salida y credenciales cifradas por proveedor. | 3 | — | migrate_ai_providers.py |
| [014](../../../backend/migrations/014_ai_provider_catalog.sql) | Ampliar el CHECK de proveedores de credenciales IA; no añade comercio electrónico. | 0 | — | migrate_ai_provider_catalog.py |
| [015](../../../backend/migrations/015_inbox_unified.sql) | Perfil manual, epoch de control y trazabilidad mensaje-identidad-outbox del Inbox. | 3 | 001, 011 | migrate_inbox.py |
| [016](../../../backend/migrations/016_inbox_media.sql) | Metadatos privados de adjuntos de Inbox, procesamiento, hash, tamaño, estado y expiración. | 1 | 001, 011 | migrate_inbox_media.py |
| [017](../../../backend/migrations/017_ai_admissions.sql) | Política de respuestas de admisiones, documentos publicados, chunks/términos léxicos, memoria de aspirante y jobs de respuesta. | 6 | 001, 003, 011 | migrate_ai_admissions.py |
| [018](../../../backend/migrations/018_campaigns.sql) | Evaluación de abandono, plantillas Meta, consentimiento, reglas de remarketing, cadencia por cuenta, campañas/destinatarios y ejecuciones durables. | 9 | 001, 011 | migrate_campaigns.py |
| [019](../../../backend/migrations/019_admissions_agents.sql) | Jerarquía institucional/programa/etapa, perfiles sobre registro Agent, contexto, ámbitos de fuentes, asignación, historial y reservas de consumo. | 7 | 001, 003, 017 | migrate_agents.py |
| [020](../../../backend/migrations/020_agent_execution.sql) | Ledger de ejecuciones IA con ruta/modelo, variante, reservas/costo, intentos y uso confirmado o incierto. | 1 | 001, 019 | migrate_agent_execution.py |

Las dependencias FK no sustituyen guards, contratos, orden dentro de runners ni prerrequisitos documentados. Ver revisiones [001–009](reviews/001-009.json), [011–020](reviews/011-020.json), [compatibilidad](COMPATIBILITY_SQL2019.md) y [mapa por capacidad](CAPABILITY_MAP.md). Ninguno de estos enlaces es un comando de aplicación.

## 001_local_crm.sql

Persistencia CRM: contacto, conversación, mensajes y diario idempotente

**Reejecución y drift:** Crea sólo cuando falta el esquema; cuando existe exige contract y shape almacenada, recompone metadatos y rechaza drift. No repara un esquema desconocido ni altera objetos existentes. COMMIT sólo tras validación; CATCH revierte transacción abierta.

**Escrituras iniciales:** {"persistent_initial_rows": false, "detail": "Sin INSERT inicial persistente"}

**Efectos core:** No DML/DDL explícito sobre tablas académicas core. Puede disparar auditoría DDL externa; preservar registro y verificar alcance antes de ejecución futura.

**Contratos y guards:** ver el fragmento de revisión y el SQL citado; no se ejecutaron. El mínimo operativo de la aplicación debe incluir las consultas JSON del runtime, además del DDL.

## 002_local_admissions.sql

Casos de admisión y seguimiento CRM sin modificar aspirantes oficiales

**Reejecución y drift:** Crea sólo cuando falta el esquema; cuando existe exige contract y shape almacenada, recompone metadatos y rechaza drift. No repara un esquema desconocido ni altera objetos existentes. COMMIT sólo tras validación; CATCH revierte transacción abierta.

**Escrituras iniciales:** {"persistent_initial_rows": false, "detail": "Sin INSERT inicial persistente"}

**Efectos core:** No DML/DDL explícito sobre tablas académicas core. Puede disparar auditoría DDL externa; preservar registro y verificar alcance antes de ejecución futura.

**Contratos y guards:** ver el fragmento de revisión y el SQL citado; no se ejecutaron. El mínimo operativo de la aplicación debe incluir las consultas JSON del runtime, además del DDL.

## 003_local_inbox.sql

Membresía, agentes, asignación dual, tareas y SLA

**Reejecución y drift:** Crea sólo cuando falta el esquema; cuando existe exige contract y shape almacenada, recompone metadatos y rechaza drift. No repara un esquema desconocido ni altera objetos existentes. COMMIT sólo tras validación; CATCH revierte transacción abierta.

**Escrituras iniciales:** {"persistent_initial_rows": false, "detail": "Sin INSERT inicial persistente"}

**Efectos core:** No DML/DDL explícito sobre tablas académicas core. Puede disparar auditoría DDL externa; preservar registro y verificar alcance antes de ejecución futura.

**Contratos y guards:** ver el fragmento de revisión y el SQL citado; no se ejecutaron. El mínimo operativo de la aplicación debe incluir las consultas JSON del runtime, además del DDL.

## 004_conversation_events.sql

Eventos durables y preparación incremental recuperable

**Reejecución y drift:** Crea sólo cuando falta el esquema; cuando existe exige contract y shape almacenada, recompone metadatos y rechaza drift. No repara un esquema desconocido ni altera objetos existentes. COMMIT sólo tras validación; CATCH revierte transacción abierta.

**Escrituras iniciales:** {"persistent_initial_rows": false, "detail": "No INSERT persistente inicial en estas fuentes; INSERT @sourceShape es verificación transitoria"}

**Efectos core:** No DML/DDL explícito sobre tablas académicas core. Puede disparar auditoría DDL externa; preservar registro y verificar alcance antes de ejecución futura.

**Contratos y guards:** ver el fragmento de revisión y el SQL citado; no se ejecutaron. El mínimo operativo de la aplicación debe incluir las consultas JSON del runtime, además del DDL.

## 005_conversation_analysis.sql

Política de análisis, contexto, recibos, intentos y feedback

**Reejecución y drift:** Crea sólo cuando falta el esquema; cuando existe exige contract y shape almacenada, recompone metadatos y rechaza drift. No repara un esquema desconocido ni altera objetos existentes. COMMIT sólo tras validación; CATCH revierte transacción abierta.

**Escrituras iniciales:** {"persistent_initial_rows": false, "detail": "No INSERT persistente inicial en estas fuentes; INSERT @sourceShape es verificación transitoria"}

**Efectos core:** No DML/DDL explícito sobre tablas académicas core. Puede disparar auditoría DDL externa; preservar registro y verificar alcance antes de ejecución futura.

**Contratos y guards:** ver el fragmento de revisión y el SQL citado; no se ejecutaron. El mínimo operativo de la aplicación debe incluir las consultas JSON del runtime, además del DDL.

## 006_crm_configuration.sql

Configuración compartida de etapas, etiquetas y campos derivada del CRM existente

**Reejecución y drift:** Crea sólo cuando falta el esquema; cuando existe exige contract y shape almacenada, recompone metadatos y rechaza drift. No repara un esquema desconocido ni altera objetos existentes. COMMIT sólo tras validación; CATCH revierte transacción abierta.

**Escrituras iniciales:** {"persistent_initial_rows": true, "detail": "Singleton crm_config.Configuration derivado de crm.Contact, no datos demo"}

**Efectos core:** No DML/DDL explícito sobre tablas académicas core. Puede disparar auditoría DDL externa; preservar registro y verificar alcance antes de ejecución futura.

**Contratos y guards:** ver el fragmento de revisión y el SQL citado; no se ejecutaron. El mínimo operativo de la aplicación debe incluir las consultas JSON del runtime, además del DDL.

## 007_institutional_identity.sql

Perfil institucional declarado por contacto

**Reejecución y drift:** Crea sólo cuando falta el esquema; cuando existe exige contract y shape almacenada, recompone metadatos y rechaza drift. No repara un esquema desconocido ni altera objetos existentes. COMMIT sólo tras validación; CATCH revierte transacción abierta.

**Escrituras iniciales:** {"persistent_initial_rows": false, "detail": "Sin INSERT inicial persistente"}

**Efectos core:** No DML/DDL explícito sobre tablas académicas core. Puede disparar auditoría DDL externa; preservar registro y verificar alcance antes de ejecución futura.

**Contratos y guards:** ver el fragmento de revisión y el SQL citado; no se ejecutaron. El mínimo operativo de la aplicación debe incluir las consultas JSON del runtime, además del DDL.

## 008_contact_merge.sql

Unificación lógica reversible y diario de operaciones

**Reejecución y drift:** Crea sólo cuando falta el esquema; cuando existe exige contract y shape almacenada, recompone metadatos y rechaza drift. No repara un esquema desconocido ni altera objetos existentes. COMMIT sólo tras validación; CATCH revierte transacción abierta.

**Escrituras iniciales:** {"persistent_initial_rows": false, "detail": "Sin INSERT inicial persistente"}

**Efectos core:** No DML/DDL explícito sobre tablas académicas core. Puede disparar auditoría DDL externa; preservar registro y verificar alcance antes de ejecución futura.

**Contratos y guards:** ver el fragmento de revisión y el SQL citado; no se ejecutaron. El mínimo operativo de la aplicación debe incluir las consultas JSON del runtime, además del DDL.

## 009_conversation_strategy.sql

Planes con evidencia, feedback y autonomía interna acotada

**Reejecución y drift:** Crea sólo cuando falta el esquema; cuando existe exige contract y shape almacenada, recompone metadatos y rechaza drift. No repara un esquema desconocido ni altera objetos existentes. COMMIT sólo tras validación; CATCH revierte transacción abierta.

**Escrituras iniciales:** {"persistent_initial_rows": false, "detail": "Sin INSERT inicial persistente"}

**Efectos core:** No DML/DDL explícito sobre tablas académicas core. Puede disparar auditoría DDL externa; preservar registro y verificar alcance antes de ejecución futura.

**Contratos y guards:** ver el fragmento de revisión y el SQL citado; no se ejecutaron. El mínimo operativo de la aplicación debe incluir las consultas JSON del runtime, además del DDL.

## 011_channels.sql

Cuentas, secretos cifrados, eventos de webhook, identidades externas, outbox única, comentarios y auditoría de canales.

**Reejecución y drift:** Si el esquema existe y su marcador CRM-channels-v1 coincide, RETURN; no compara la forma completa de tablas, FK o índices.

**Escrituras iniciales:** No INSERT/UPDATE de datos; defaults de estados no equivalen a cuentas activas.

**Efectos core:** No CREATE/ALTER/DML explícito sobre tablas académicas core SIIE en este archivo. Las FK a crm y otros esquemas son dependencias CRM. Triggers/auditoría DDL de la base real no inspeccionados; no se afirma ausencia de efectos implícitos.

**Contratos y guards:** ver el fragmento de revisión y el SQL citado; no se ejecutaron. El mínimo operativo de la aplicación debe incluir las consultas JSON del runtime, además del DDL.

## 012_channels_identity_collation.sql

Preservar identificadores opacos de proveedores con collation binaria y reconstruir claves dependientes.

**Reejecución y drift:** Marcador crm_channels.identity_collation presente: rechaza collation distinta en columnas encontradas y retorna; no acredita que existan todas las columnas ni claves esperadas.

**Escrituras iniciales:** Sin DML de filas; ALTER COLUMN y DROP/ADD de constraints afectan metadatos/índices de registros existentes.

**Efectos core:** No CREATE/ALTER/DML explícito sobre tablas académicas core SIIE en este archivo. Las FK a crm y otros esquemas son dependencias CRM. Triggers/auditoría DDL de la base real no inspeccionados; no se afirma ausencia de efectos implícitos.

**Contratos y guards:** ver el fragmento de revisión y el SQL citado; no se ejecutaron. El mínimo operativo de la aplicación debe incluir las consultas JSON del runtime, además del DDL.

**ALTER detectados (históricos, no aplicados por este inventario):**

- `crm_channels`, línea 14: `ALTER TABLE crm_channels.'+QUOTENAME(OBJECT_NAME(parent_object_id))+N' DROP CONSTRAINT '+QUOTENAME(name)+N'`
- `crm_channels.ExternalIdentity`, línea 20: `ALTER TABLE crm_channels.ExternalIdentity ALTER COLUMN ExternalId nvarchar(128) COLLATE Latin1_General_100_BIN2 NOT NULL`
- `crm_channels.ExternalMessage`, línea 21: `ALTER TABLE crm_channels.ExternalMessage ALTER COLUMN ExternalId nvarchar(200) COLLATE Latin1_General_100_BIN2 NOT NULL`
- `crm_channels.outbound_queue`, línea 22: `ALTER TABLE crm_channels.outbound_queue ALTER COLUMN ExternalId nvarchar(200) COLLATE Latin1_General_100_BIN2 NULL`
- `crm_channels.social_comments`, línea 23: `ALTER TABLE crm_channels.social_comments ALTER COLUMN ExternalId nvarchar(200) COLLATE Latin1_General_100_BIN2 NOT NULL`
- `crm_channels.social_comments`, línea 24: `ALTER TABLE crm_channels.social_comments ALTER COLUMN AuthorId nvarchar(128) COLLATE Latin1_General_100_BIN2 NOT NULL`
- `crm_channels.ExternalIdentity`, línea 25: `ALTER TABLE crm_channels.ExternalIdentity ADD CONSTRAINT UQ_Channels_Identity UNIQUE(Channel,ExternalId)`
- `crm_channels.ExternalMessage`, línea 26: `ALTER TABLE crm_channels.ExternalMessage ADD CONSTRAINT PK_Channels_ExternalMessage PRIMARY KEY(Channel,ExternalId)`
- `crm_channels.social_comments`, línea 27: `ALTER TABLE crm_channels.social_comments ADD CONSTRAINT UQ_Channels_Comment UNIQUE(Channel,ExternalId)`

## 013_ai_providers.sql

Configuración IA, conexión/consentimiento de salida y credenciales cifradas por proveedor.

**Reejecución y drift:** Esquema existente con CRM-ai-v1 retorna sin fingerprint completo; runner inserta Configuration sólo si no hay ConfigurationId=1.

**Escrituras iniciales:** SQL INSERT crm_ai.Connection(ConnectionId=1,Outbound=0). Runner puede importar ajustes no secretos del archivo local ai-settings.json (o valores por defecto) a Configuration con UPDLOCK/HOLDLOCK. No exporta/importa Credential.

**Efectos core:** No CREATE/ALTER/DML explícito sobre tablas académicas core SIIE en este archivo. Las FK a crm y otros esquemas son dependencias CRM. Triggers/auditoría DDL de la base real no inspeccionados; no se afirma ausencia de efectos implícitos.

**Contratos y guards:** ver el fragmento de revisión y el SQL citado; no se ejecutaron. El mínimo operativo de la aplicación debe incluir las consultas JSON del runtime, además del DDL.

## 014_ai_provider_catalog.sql

Ampliar el CHECK de proveedores de credenciales IA; no añade comercio electrónico.

**Reejecución y drift:** Cada ejecución busca, elimina y vuelve a crear un CHECK; no tiene RETURN ni marcador propio de versión. Repetir no duplica datos, pero sí vuelve a ejecutar DDL.

**Escrituras iniciales:** Sin DML; reemplaza restricción de Provider con lista ampliada. Conserva claves/secretos existentes.

**Efectos core:** No CREATE/ALTER/DML explícito sobre tablas académicas core SIIE en este archivo. Las FK a crm y otros esquemas son dependencias CRM. Triggers/auditoría DDL de la base real no inspeccionados; no se afirma ausencia de efectos implícitos.

**Contratos y guards:** ver el fragmento de revisión y el SQL citado; no se ejecutaron. El mínimo operativo de la aplicación debe incluir las consultas JSON del runtime, además del DDL.

**ALTER detectados (históricos, no aplicados por este inventario):**

- `crm_ai.Credential`, línea 11: `ALTER TABLE crm_ai.Credential DROP CONSTRAINT '+QUOTENAME(@constraint)`
- `crm_ai.Credential`, línea 13: `ALTER TABLE crm_ai.Credential WITH CHECK ADD CONSTRAINT CK_crm_ai_Credential_Provider CHECK(Provider IN('gemini','nvidia','openai','anthropic','hermes','groq','mistral','openrouter','kimi','xai','elevenlabs','google_tts','tavily','brave','serpapi'))`

## 015_inbox_unified.sql

Perfil manual, epoch de control y trazabilidad mensaje-identidad-outbox del Inbox.

**Reejecución y drift:** Marcador inbox-unified-v1 retorna sin comprobar forma; si no está, rechaza tres objetos ya existentes antes de crear.

**Escrituras iniciales:** No semillas ni edición de conversaciones existentes; defaults de epoch/lectura son para filas futuras.

**Efectos core:** No CREATE/ALTER/DML explícito sobre tablas académicas core SIIE en este archivo. Las FK a crm y otros esquemas son dependencias CRM. Triggers/auditoría DDL de la base real no inspeccionados; no se afirma ausencia de efectos implícitos.

**Contratos y guards:** ver el fragmento de revisión y el SQL citado; no se ejecutaron. El mínimo operativo de la aplicación debe incluir las consultas JSON del runtime, además del DDL.

## 016_inbox_media.sql

Metadatos privados de adjuntos de Inbox, procesamiento, hash, tamaño, estado y expiración.

**Reejecución y drift:** Marcador inbox-media-v1 retorna; tabla previa sin marcador se rechaza. No compara el fingerprint completo si el marcador existe.

**Escrituras iniciales:** No filas iniciales; metadatos sólo. Los archivos binarios/media no son creados por esta migración.

**Efectos core:** No CREATE/ALTER/DML explícito sobre tablas académicas core SIIE en este archivo. Las FK a crm y otros esquemas son dependencias CRM. Triggers/auditoría DDL de la base real no inspeccionados; no se afirma ausencia de efectos implícitos.

**Contratos y guards:** ver el fragmento de revisión y el SQL citado; no se ejecutaron. El mínimo operativo de la aplicación debe incluir las consultas JSON del runtime, además del DDL.

## 017_ai_admissions.sql

Política de respuestas de admisiones, documentos publicados, chunks/términos léxicos, memoria de aspirante y jobs de respuesta.

**Reejecución y drift:** Marcador admissions-ai-v1 retorna. Antes de crear comprueba cuatro de los seis objetos; colisión en KnowledgeChunk/KnowledgeTerm queda para el motor y rollback del runner.

**Escrituras iniciales:** INSERT AdmissionsPolicy(PolicyId=1), Enabled=0 por default, modelos vacíos y prompt institucional. No documentos, conocimiento de aspirantes ni jobs iniciales.

**Efectos core:** No CREATE/ALTER/DML explícito sobre tablas académicas core SIIE en este archivo. Las FK a crm y otros esquemas son dependencias CRM. Triggers/auditoría DDL de la base real no inspeccionados; no se afirma ausencia de efectos implícitos.

**Contratos y guards:** ver el fragmento de revisión y el SQL citado; no se ejecutaron. El mínimo operativo de la aplicación debe incluir las consultas JSON del runtime, además del DDL.

## 018_campaigns.sql

Evaluación de abandono, plantillas Meta, consentimiento, reglas de remarketing, cadencia por cuenta, campañas/destinatarios y ejecuciones durables.

**Reejecución y drift:** SQL rechaza cualquier esquema crm_marketing previo. Runner --preflight informa existencia sin aplicar; ejecución repetida normal rechaza y requiere inspección, no es no-op.

**Escrituras iniciales:** INSERT PolicyId=1; EvaluationEnabled DEFAULT 1, intervalo 60 minutos y NextRunAtUtc futuro. Habilita la política de evaluación interna, no el transporte. Campañas/reglas/destinatarios/consentimientos quedan sin semillas.

**Efectos core:** No CREATE/ALTER/DML explícito sobre tablas académicas core SIIE en este archivo. Las FK a crm y otros esquemas son dependencias CRM. Triggers/auditoría DDL de la base real no inspeccionados; no se afirma ausencia de efectos implícitos.

**Contratos y guards:** ver el fragmento de revisión y el SQL citado; no se ejecutaron. El mínimo operativo de la aplicación debe incluir las consultas JSON del runtime, además del DDL.

**ALTER detectados (históricos, no aplicados por este inventario):**

- `crm_marketing.ChurnAssessment`, línea 172: `ALTER TABLE crm_marketing.ChurnAssessment ADD RunId uniqueidentifier NULL REFERENCES crm_marketing.EvaluationRun(RunId)`

## 019_admissions_agents.sql

Jerarquía institucional/programa/etapa, perfiles sobre registro Agent, contexto, ámbitos de fuentes, asignación, historial y reservas de consumo.

**Reejecución y drift:** SQL rechaza esquema previo. Runner acepta como no-op contrato admissions-agents-v1 y comprueba presencia de columnas seleccionadas mediante COL_LENGTH; no valida todas las definiciones/FK/índices.

**Escrituras iniciales:** No agentes, etapas, fuentes, contextos ni consumo iniciales. CHECK de ApprovedVersion conserva compatibilidad con guardado directo: servicio guarda versión aprobada igual a Version al activar, sin puerta humana adicional.

**Efectos core:** No CREATE/ALTER/DML explícito sobre tablas académicas core SIIE en este archivo. Las FK a crm y otros esquemas son dependencias CRM. Triggers/auditoría DDL de la base real no inspeccionados; no se afirma ausencia de efectos implícitos.

**Contratos y guards:** ver el fragmento de revisión y el SQL citado; no se ejecutaron. El mínimo operativo de la aplicación debe incluir las consultas JSON del runtime, además del DDL.

## 020_agent_execution.sql

Ledger de ejecuciones IA con ruta/modelo, variante, reservas/costo, intentos y uso confirmado o incierto.

**Reejecución y drift:** SQL rechaza tabla Execution previa. Runner --preflight/existencia valida contrato, columnas/tipos/longitudes/nulabilidad, precisión decimal, tres FK y dos índices, luego rollback/no-op.

**Escrituras iniciales:** No INSERT de ejecuciones ni modificación de consumos/secretos. No habilita proveedor ni transporte.

**Efectos core:** No CREATE/ALTER/DML explícito sobre tablas académicas core SIIE en este archivo. Las FK a crm y otros esquemas son dependencias CRM. Triggers/auditoría DDL de la base real no inspeccionados; no se afirma ausencia de efectos implícitos.

**Contratos y guards:** ver el fragmento de revisión y el SQL citado; no se ejecutaron. El mínimo operativo de la aplicación debe incluir las consultas JSON del runtime, además del DDL.
