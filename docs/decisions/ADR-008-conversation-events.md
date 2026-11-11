# ADR-008 — Preparación recuperable de conversaciones locales

Fecha: 2026-10-16. Contrato de R3A solicitado por el propietario, limitado a la copia local. No activa análisis, modelos, agentes ni canales y conserva el stack actual.

## Decisión

SQL es la fuente de verdad. Una migración explícita añade `crm_events.Event`, `Preparation` y `RetryOperation`, con versión/huella propias. No modifica las huellas ni los escritores `crm`/`crm_inbox`. Un worker integrado en el ciclo de vida FastAPI reconcilia referencias faltantes de mensajes, operaciones CRM y tareas R2, además de una referencia inicial por conversación. No copia texto ni datos personales. El diario original ya durable permite recuperar la caída entre persistencia y captura.

Captura hasta 100 referencias por fuente y vuelta, mediante ausencia de clave única, sin asumir que MAX(identity) significa cobertura completa. Cubre historial existente y commits tardíos; no reconstruye snapshots históricos a partir de un hash. El baseline identifica cobertura inicial, las operaciones conservan ID/revisión/acción y el mensaje conserva su referencia original. Cambios SQL directos sin operación quedan fuera del contrato de escritura; nuevos mensajes se reconcilian por ID aunque su fecha sea anterior.

El worker reclama un evento mediante lease con token y expiración SQL UTC. Confirma solo con propietario vigente, en transacción; un propietario obsoleto no puede completar. Una preparación verifica la fuente y registra metadatos coherentes del estado actual por conversación: número/última secuencia de mensajes, revisiones fuente y fecha. Solo completa su evento; un watermark reciente no declara cubiertos otros pendientes. No interpreta intención, no genera resumen y no cambia el control humano ni las asignaciones.

El progreso recuperable pertenece al estado de **cada evento**, no al máximo de IDs. `Preparation.LastEventId` es diagnóstico y `PreparedAt` indica frescura; ninguno es un cursor suficiente para un consumidor posterior. La tupla de conteo/secuencia/revisiones describe los metadatos leídos, no una versión de contexto. R4 debe definir su propia revisión/estado transaccional por consumidor y atender cada referencia pendiente, incluso si termina después un evento de ID inferior.

## Operación acotada

Proceso integrado sin servicio adicional; reconciliación cada cinco segundos, hasta veinte preparaciones por vuelta, lease de treinta segundos y cinco intentos automáticos por evento. Son límites técnicos locales, no SLA de negocio. Reintento con espera creciente acotada; expiración recuperable tras reinicio. Tras agotar intentos, fallo visible y reintento humano de hasta veinticinco eventos, idempotente por operationId. Se conserva TotalAttempts. Un error no expone payload ni excepción interna.

El bloqueo existente `crm.local.commit` serializa escrituras y preparación breve. Es apropiado para este preview; antes de mayor concurrencia se debe medir y separar bloqueos. No se realiza inferencia ni IO externo dentro de transacciones. El estado observable distingue referencias sin capturar, pendientes, leases, fallos y preparación técnica, con cobertura de conversaciones y última actividad del worker.

La espera de cinco segundos comienza al terminar el ciclo: la detección tarda esa espera más consultas/procesamiento y acumulación de lotes. No hay garantía fija de cinco segundos bajo carga o fallo. El diario CRM y las referencias de mensajes/tareas no deben purgarse antes de reconciliar. Se incluyen operaciones CRM vinculadas a conversación y altas/ediciones de tareas R2; las configuraciones globales de equipo/agentes/política no se atribuyen artificialmente a un hilo. La asignación dual ya deja una operación CRM compatible.

## Compatibilidad y recuperación

DDL solo mediante 004, guardado a DBSIIE/SQLEXPRESS, respaldo/restauración y ensayo previo. Sin migración, el worker informa indisponibilidad y conserva las funciones anteriores. Volver a la imagen anterior detiene el worker; esquema/eventos se conservan y los escritores previos mantienen sus diarios. Al retomar, la reconciliación recupera referencias faltantes. No se eliminan datos ni auditorías DDL.

Aceptación: duplicados/replay, captura tras caída, commits tardíos, recuperación de lease, rechazo de propietario obsoleto, fallo/reintento acotado y atomicidad preparación+confirmación; SQL/HTTP/runtime automático y UI reales. Las pruebas reversibles de negocio se diferencian del COMMIT de esquema y preparación técnica de registros reales.
