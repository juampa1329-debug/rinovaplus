# R3A local — eventos durables y preparación recuperable

Corte del 2026-10-16, completado y aceptado por capas, incluido navegador real. La preparación técnica automática conserva referencias SQL reales y permite recuperar trabajo pendiente tras caída o reinicio. **No ejecuta análisis IA, contexto, puntuación, entrenamiento ni envíos.** Contrato: [ADR-008](../decisions/ADR-008-conversation-events.md).

## Funcionamiento y alcance

En **Inbox → Configurar operación → Preparación de conversaciones · R3A** se consultan referencias sin registrar, eventos pendientes/en preparación/preparados/fallidos, cobertura registrada y última actividad. La vista actualiza cada diez segundos; la cobertura no significa que no existan pendientes posteriores. El reintento humano recupera hasta 25 fallos y conserva la misma operación ante una respuesta incierta, incluso al navegar.

Un worker integrado en FastAPI reconcilia hasta 100 referencias por fuente por ciclo y prepara hasta 20 eventos; espera cinco segundos después del ciclo. Fuentes: conversación inicial, mensajes originales, operaciones CRM y operaciones de tareas R2. La asignación dual conserva su operación CRM; configuración global no genera eventos de conversación ficticios. El control humano no suspende esta preparación.

La captura es eventual desde diarios durables, no una inserción atómica junto al mensaje. Una clave única y búsqueda de referencias ausentes recuperan commits tardíos sin cursor MAX. Cada lease dura treinta segundos; token/expiración impiden confirmar al propietario anterior. Cinco intentos automáticos y espera creciente preceden al fallo visible. Preparación y confirmación del evento comparten transacción; no completan otros eventos pendientes.

La proyección contiene metadatos actuales, no reconstrucciones históricas de contenido. LastEventId/PreparedAt son diagnóstico/frescura, no versión suficiente para R4: el futuro consumidor necesita su propio estado/revisión transaccional. El origen permanece en SQL, sin duplicar textos en eventos ni logs.

## Evidencia por capa

| Capa | Resultado |
|---|---|
| Migración 004 | Respaldo COPY_ONLY/CHECKSUM nuevo, restauración independiente y CHECKDB, fallo con rollback, repetición idempotente y aplicación durable comprobados. Tres tablas `crm_events` inicialmente vacías; versiones/huellas previas conservadas. |
| Preservación | Metadatos core y valores de CRM/Admisiones/R2 preservados; ocho auditorías DDL automáticas conservadas. Sin filas de negocio de prueba al finalizar. |
| SQL funcional | 19 comprobaciones aprobadas: referencia inferior omitida tras otra superior, fecha tardía, replay, fallo/reintento, confirmación aislada, claims concurrentes, lease recuperado y propietario obsoleto rechazado. 15 referencias reales preparadas y visibles desde conexión nueva. |
| Backend | Corrida combinada 345/346; único fallo del cliente de prueba corregido y R3A 12/12 final. Ruff/formato/exportación canónica aprobados; no se afirma una segunda corrida completa. |
| Frontend | 8/8 pruebas enfocadas de estado, indisponibilidad, actualización/respuesta tardía, reintento y operación R2; lint/tipos/build aprobados. |
| Runtime/HTTP | Preview privado 4173 reconstruido saludable; snapshot CRM, volumen IA y Admisiones conservados. 19 comprobaciones HTTP aprobadas: ciclo automático, UTC, recuperación tras un reinicio y ausencia de duplicados; dos miembros actuales y agentes preservados. |
| Navegador | Aceptado: estado técnico real, actualización automática, directorio vigente, borradores, filtros, scroll independiente y móvil; sin escrituras de negocio. |

Las pruebas que introdujeron mensajes técnicos y estados de fallo se ejecutaron en una transacción siempre revertida. La captura/preparación posterior **sí se confirmó** sobre referencias de fuentes reales: no se presenta rollback como prueba de durabilidad. El snapshot de negocio permaneció idéntico. Al cierre se observaron dos miembros reales ya configurados en Admisiones, preservados; el vacío inicial del informe R2 es histórico. No se añadieron integrantes ni agentes en este corte.

Evidencia saneada local: `.local/events-r3a-20261016/backup-result.json`, `backup.json`, `restore.json`, `migration-result.json`, `repository-result.json`, `docker-final.json`, `runtime-freeze.json`, `http-result.json`, `browser-result.json` y captura saneada `browser-processing.png`. Imagen reconstruida: `sha256:46e9a83e61b0ae697404ae279739ff98af50a8cc64e8f97c932f55547a2b4902`. Los resultados contienen comprobaciones/conteos; no nombres, documentos, mensajes ni credenciales.

La primera prueba del endpoint carecía del cliente loopback exigido y recibió 403; se corrigió el test. Una ejecución restringida quedó bloqueada en el socket interno de asyncio antes del lifespan; la corrida local autorizada completó normalmente. No se cambió código de producto para esos problemas del harness.

## Aceptación de navegador

La UI mostró procesador en ejecución, 15 eventos preparados y cobertura 2/2; pendientes, leases, fallos y referencias sin registrar en cero, con reintento deshabilitado. El último ciclo avanzó automáticamente de 08:47 a 08:51, sin recargar la página. Los dos miembros actuales se conservaron; el selector humano mostró tres opciones contando sin asignar.

En 1440 × 1000, lista/ficha midieron 717 px y terminaron en 975 px. El desplazamiento real de la ficha de 2000 a 1000 mantuvo lista, mensajes y documento en cero. Borradores temporales de ciudad, mensaje y tarea sobrevivieron a navegación y se descartaron después. Búsqueda inexistente mostró cero conservando detalle; limpiar restituyó las dos conversaciones. En 390 × 844, página de 375 px, ficha de 358 px y borde inferior 751,625 px; cierre/regreso y configuración R3A de 311 px fueron accesibles sin desbordamiento. No hubo escrituras de negocio ni intervención en la pestaña del usuario; se retiraron borradores/búsquedas y se restauró el viewport de la pestaña propia.

## Recuperación y límites

La [migración explícita](../../backend/migrations/004_conversation_events.sql) no se ejecuta al arrancar. Sin esquema válido se informa indisponibilidad; las funciones anteriores se conservan. Volver a la imagen anterior detiene el worker y mantiene tablas/eventos/diarios; retomar recupera ausencias. No eliminar el esquema ni restaurar encima de cambios posteriores.

La espera más el trabajo y los lotes determina la latencia; no es un SLA fijo. El bloqueo global y las consultas de ausencia son adecuados al volumen local comprobado: medir antes de escalar. Cambios directos SQL sin operación no constituyen una revisión capturable del contrato. El siguiente corte es R4 con fuentes/modelo/alcance autorizados; R3B y envíos siguen separados. Esto no acredita producción 24/7 ni acceso compartido autenticado.
