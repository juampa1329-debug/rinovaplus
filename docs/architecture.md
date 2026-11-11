# Arquitectura de referencia del CRM

**Aprobado como base del skeleton:** monolito modular; FastAPI, React, Celery/Redis; plataforma nueva; SQL Server SIIE como SSOT transaccional. Aprobación del propietario registrada en [ADR-001](decisions/ADR-001-skeleton-architecture.md), 2026-10-13. **Pendiente:** contratos detallados, tooling, diseño visual, seguridad/identidad y responsables. **Implementado en fase 0:** salud backend y diseño funcional local, sin conexiones. [Informe](reports/phase-0.md): fase 0 local cerrada, navegador y HTTP comprobados. Integración y aprobación visual humana pendientes.

## Límites y dependencias

| Capa | Responsabilidad | No permitido |
|---|---|---|
| Dominio | Estados/invariantes de prospecto, conversación, handoff y formulario. | FastAPI, SDK de proveedores, SQL/Redis o React. |
| Aplicación | Casos de uso, permisos, idempotencia y puertos. | Conocer secretos o depender del transporte HTTP. |
| Adaptadores | SQL Server, Meta, LLM/TTS, cola y almacenamiento de media. | Saltarse casos de uso o introducir reglas en SDK/ORM. |
| Entradas | API FastAPI y tareas Celery validan y llaman aplicación. | Ejecutar SQL/LLM directamente desde rutas. |
| React | Funcionalidades aisladas, contratos API y componentes compartidos. | Acceder a DB/secrets o decidir autorización. |

Límites de la arquitectura conectada **planeados**, no capas vacías creadas: `backend/app/domain`, `backend/app/application`, `backend/app/adapters`, `backend/app/entrypoints`; `frontend/src/features`, `frontend/src/shared/ui`, `frontend/src/shared/tokens`. No crear capas vacías; una nueva abstracción exige al menos una responsabilidad real. El skeleton actual usa `backend/app/config.py`, `health.py` y `main.py` con responsabilidades reales, y funcionalidades/controles/tokens React. Dominio, casos de uso y adaptadores se añaden cuando existe comportamiento autorizado. Tradeoff: el monolito modular simplifica operación y consistencia; extraer un servicio solo tras medir aislamiento/carga y aceptar ADR.

Capacidades iniciales propuestas: catálogo SIIE, admisiones/prospectos, conversaciones/handoff y formularios. Relacionamiento corporativo, retención, audio, proveedores múltiples y memoria de ventas son expansión, no condición del primer corte.

## SQL Server: integración protegida

1. Inventariar versión, esquema, vistas/procedimientos, claves y restricciones en entorno autorizado; no asumir nombres reales desde ejemplos.
2. Definir adapter/puertos de integración y DTOs mínimos; usuario de lectura de mínimo privilegio al inicio. Lecturas parametrizadas y acotadas; TLS con validación de certificado; pool/timeouts/límites acordados con DBA.
3. Preparar copia SQL Server no productiva sintética o anonimizada que conserve comportamiento relevante. Es ambiente de prueba, no una nueva autoridad productiva del CRM. SQLite no prueba dialecto, bloqueo ni transacción SQL Server.
4. Revisar diseño y migraciones `CRM_`, índices, auditoría y rollback; probar respaldo/restauración fuera de producción. No `create_all`, no inferir DDL permitido por prefijo.
5. Escribir core solo por contrato probado y autorización explícita. Separar recepción de prospecto de aceptación académica/matrícula; no crear matrícula automáticamente por llenar formulario.

SQLAlchemy documenta el dialecto SQL Server y acceso ODBC, pero su uso/driver/versiones aún requieren decisión y prueba local: [documentación oficial](https://docs.sqlalchemy.org/en/20/dialects/mssql.html). Esto no demuestra una conexión a SIIE.

`pgvector` es una [extensión PostgreSQL](https://github.com/pgvector/pgvector), por lo que no se aplica directamente a SQL Server. No cambiar motor ni agregar una DB de negocio para resolverlo. **P-008** decide necesidad de RAG/vector, versión/capacidades del servidor, retención y solución derivada no autoritativa. Primera entrega sin memoria vectorial de ventas.

## Flujo durable propuesto

Meta → verificación firma/límites → inbox persistida con ID externo único → respuesta de recepción → tarea → caso de uso → outbox → envío/estado auditado.

- Confirmar recepción después de persistir de forma durable; si no se puede persistir, política de error/reintento según contrato verificado de Meta. Redis/Celery por sí solos no reemplazan inbox/outbox durable.
- Diseñar entrega al menos una vez; reentregas y carreras resueltas con restricciones/transacciones y claves de idempotencia. No prometer exactamente una vez en un proveedor externo.
- Reintentos acotados, backoff, timeout y recuperación de cola muerta; estados de envío distinguen pendiente, confirmado y resultado incierto. Reconciliar incertidumbre antes de reenviar para evitar duplicados.
- Demoras como trabajos programados persistidos y cancelables; no `sleep` que bloquee workers. Calendario/feriados/zona y objetivos de respuesta pendientes de aprobación.
- Política de baja y ventana/plantilla revalidadas inmediatamente antes del envío. Recordatorios de 2/24/48 horas son intenciones sujetas a consentimiento y reglas vigentes comprobadas de Meta.

La atomicidad inbox/outbox/CRM dentro de SQL Server y los contratos de envío deben probarse ante caída entre commit, encolado y envío. No escribir core SIIE y luego confiar en una tarea volátil como único registro.

## IA, formulario y control humano

- LLM recibe datos mínimos y resultados autorizados. Catálogo/precios/jornadas provienen de SIIE; no horarios exactos de clases. Respuesta sin fuente válida se deriva al asesor, no se inventa.
- Salida LLM estructurada y validada; reglas deterministas de autorización fuera del prompt. Sin SQL libre ni herramientas arbitrarias. Identidad de asistente virtual visible.
- Handoff con estado durable, propietario/versionado optimista y auditoría: tomar control invalida respuestas/tareas IA pendientes; revalidar control antes del envío. Devolución a IA explícita y concurrentemente segura.
- Token de formulario aleatorio criptográfico, corto vencimiento, uso único; almacenar hash/referencia, limitar intentos, evitar token/PII en logs y referers. Consumir atómicamente con la aceptación, validar datos y permisos en servidor.
- Audio OGG/Opus nativo y máximo 10 segundos: requisito pendiente de pruebas proveedor/API/dispositivo. Fallback LLM por LLM, TTS por TTS; no atribuir capacidad TTS a un proveedor sin documentación y prueba.

## Puertas de diseño

[ADR-003](decisions/ADR-003-local-phase-two-sequence.md) amplía el corte aislado a fase 2 por instrucción del propietario y difiere fase 1 al final del desarrollo funcional local, antes de cualquier conexión/dato real/entorno compartido. No elimina controles ni autoriza servicios. `App` es el único propietario temporal de fichas, configuración CRM, hilos y comentarios; Clientes/Inbox reutilizan esa configuración. `shared/crm.ts`, `conversationAnalysis.ts` y `comments.ts` contienen reglas puras locales; no son casos de uso conectados ni adaptadores. El mini CRM analiza evidencia sintética con reglas provisionales, no un modelo; el proveedor y su evaluación se difieren en P-029. Los cuatro canales confirmados son intención de producto, no capacidades API comprobadas (P-030). Backend de salud sin cambios.

[ADR-002](decisions/ADR-002-local-functional-skeleton.md) acepta una excepción acotada: la fase 0 local puede construir y verificar skeleton y diseño funcional con fixtures temporales, sin DB/API, auth ni proveedores. P-004 permite elegir tooling mínimo compatible. P-001, partes restantes P-002, P-003/P-015/P-018 y P-017/P-026 siguen pendientes antes de funciones conectadas en fase 1 o de su capacidad; no se cierran por el prototipo. La propuesta visual sigue provisional. [Fases](roadmap.md) y [seguridad](security-and-operations.md) mantienen los controles de integración.
