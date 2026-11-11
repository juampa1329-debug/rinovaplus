# Inbox unificado y mini CRM — aceptación local del 2026-10-20

Implementación en la misma aplicación `127.0.0.1:4173`, carpeta y copia local DBSIIE. Se reutilizan Inbox, ficha compartida, equipo, asignación y política SLA existentes. Esta unidad acredita operación local; no completa medios privados, RBAC ni aceptación conectada de plataformas.

## Contrato y persistencia

Se conservan las rutas `/api/local/crm/inbox`: listado y opciones, detalle `/contacts/{id}`, historial/envío `/conversations/{id}/messages` y actualización `PUT /conversations/{id}`. La asignación mantiene `PUT /api/local/crm/inbox/operations/conversations/{id}/assignment` y exige un miembro habilitado con empleado activo. No se duplicó el router bajo `/api/v1/inbox`.

Una conversación CRM sigue siendo la autoridad compartida de prioridad, estado, responsables y control para sus canales. El detalle agrega prospecto declarado, programa de interés, destinos vinculados, evaluación manual, takeover, asignación y fechas SLA. No une identidades por teléfono ni traslada destinos entre fichas/conversaciones de un grupo C4. Los filtros SQL incluyen etapa, canal mediante identidades vinculadas, responsable, estado, control, no leídos y SLA; listado con OFFSET/FETCH de 25 elementos e historial por secuencia de 50.

La migración explícita **015**, ejecutada por el operador mediante `backend/tools/migrate_inbox.py`, añadió solo `crm_channels.ConversationProfile`, `ConversationControl` y `MessageRoute`. Se verificaron destino local y huella legacy/core antes y después. El runner usa TLS, transacción y rollback ante error; no hay DDL al arrancar. Una conexión nueva confirmó el marcador `inbox-unified-v1`, las tres tablas vacías al aplicar y los conteos previos conservados: **2 contactos, 2 conversaciones y 2 mensajes**. No se modificaron tablas core ni huellas de `crm`/`crm_inbox`.

`delivery=local` es el valor predeterminado compatible: guardar no encola ni envía. La intención externa requiere selección explícita de `IdentityId`, validado contra la conversación exacta y una cuenta activa. Mensaje, ruta y cola se confirman en una transacción con CAS, idempotencia y diario existentes. El historial distingue local/recibido de `queued`, `sending`, `sent`, `delivered`, `read`, `failed` y `uncertain`; local nunca se presenta como entrega externa. No se invoca al proveedor desde HTTP ni se reintenta ciegamente un resultado incierto.

El control durable incrementa epoch ante cambios de modo/estado e invalida trabajo bot obsoleto. El dispatcher revalida control, epoch, relaciones, estado de cuenta y ventana antes de registrar la frontera de inicio bajo el mismo bloqueo transaccional. Los mensajes humanos se distinguen del bot. Liberar control no revive trabajo antiguo ni activa respuestas automáticas. Una petición que ya cruzó la frontera de envío no se puede retirar; el detalle informa envíos iniciados o inciertos. Los diarios R3A/R4 y los controles de autonomía interna se conservan.

La lectura avanza hasta la secuencia observada; no limpia entrantes posteriores ni emite receipts del proveedor. Es un watermark compartido del entorno local, sin atribuirlo a un asesor autenticado. Puntaje 0–100 y temperatura son manuales y nullable, con «Sin evaluar»; no convierten el índice C5 en un score. El SLA reutiliza exclusivamente la política configurada, sin inventar minutos: en conversaciones externas solo califican salientes confirmados como sent/delivered/read. Locales, queued, fallidos o inciertos no satisfacen ese SLA. Sin política o pendiente no se inventan fechas.

## Aceptación manual observada

- La UI ofrece Todos, Local y los cinco canales del registro compartido. WhatsApp mostró una bandeja vacía legítima; Todos recuperó las dos conversaciones existentes. No se crearon hilos ni cuentas ficticias.
- Tomar control persistió al recargar. Reservar para IA y volver a humano dejó ambas conversaciones en human; SQL mediante conexión nueva y guard válido confirmó **una fila de control y suma de epochs 3**, sin respuestas automáticas activadas.
- Se asignó un miembro real habilitado, se comprobó su selección después de recargar y se restauró la asignación previa vacía desde la UI. SQL conservó una fila Assignment con asignación lógicamente nula; no se registran nombres ni IDs personales en este informe.
- Puntaje y temperatura permanecieron «Sin evaluar», con límites DOM 0/100 y **cero filas Profile**. La validación y persistencia no nula se revisaron estáticamente; no se acredita un guardado real de evaluación ni una carrera de lectura sin mensajes entrantes disponibles.
- El operador guardó una nota interna real bajo control humano con destino local predeterminado. UI y recarga confirmaron persistencia y ausencia de encolado. Una conexión SQL nueva confirmó **2 contactos, 2 conversaciones, 3 mensajes, 0 identidades externas, 0 filas outbound y 0 MessageRoute**.
- Al elegir intención externa con borrador no vacío, la UI explicó que no había identidades vinculadas y mantuvo Guardar y encolar deshabilitado. El operador limpió el borrador y restauró destino local, sin enviar.
- Se corrigió un defecto React observado: claves iguales entre bloques hermanos acumulaban 14–20 formularios y avisos de duplicación durante actualizaciones. Inbox y MiniCrm usan ahora claves con prefijo por componente. Recarga completa y ciclos posteriores de control/asignación mantuvieron **un bloque operativo, un input de puntaje y un selector de temperatura**, con cero avisos de clave repetida en los últimos 60 segundos observados.

Capturas revisadas en `C:/Users/Developer_PC/.codex/visualizations/2026/10/19/01a1562a-952c-7913-a6cf-c6abf669e15e/`: `inbox-sprint3-control-local-final.jpg` e `inbox-sprint3-mini-crm-final.jpg`. Los metadatos IA conservaron revisión **26**, IA habilitada, chat `gemini-3.5-flash` y análisis audio/visión `gemini-3.1-flash-lite`; esta unidad no llamó a esos proveedores ni cambió sus credenciales.

La lectura estática independiente no encontró hallazgos P1/P2 en CAS, destino exacto, fence y SLA. No equivale a una entrega real, prueba de carrera SQL o certificación de seguridad. Se normalizaron las fuentes modificadas y se regeneraron metadatos antes de la aceptación; después se corrigieron únicamente las opciones/texto del filtro y las claves React observadas. No se ejecutaron pruebas automáticas, lint, typecheck, builds de comprobación, copias ni commits.

## Límites y siguiente alcance

No hubo envíos externos. Faltan eventos firmados y entrega/lectura autorizadas en cuentas reales, además de aceptación de concurrencia/recuperación y SLA con evidencia de proveedor. No se presume autenticación por el guard loopback ni por asignar un empleado. RBAC, lecturas por usuario autenticado, OAuth, uploads privados, descarga/streaming de medios y reproducción multimedia del Inbox siguen pendientes. El audio/visión temporal del Asistente no se reutilizó como almacenamiento de Inbox.

El [modelo Sprint 3 del 2026-10-19](../contracts/sprint-3-inbox-model.md) es una propuesta histórica y no se ejecutó literalmente: AccountId/ExternalThread y su namespace nuevo no describen esta implementación. Lo sustituyen, para este corte, la conversación padre existente, destino explícito por identidad y las tres extensiones de 015. Sus necesidades pendientes de medios y permisos conservan alcance separado.
