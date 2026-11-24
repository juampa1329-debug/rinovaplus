# Inbox: espera, consultas pendientes y cita del turno

## Alcance solicitado

Reunir los mensajes del cliente antes de responder, con espera editable cercana a un minuto. Revisar todas las consultas pendientes y las respuestas realmente aceptadas por Meta. Si el cliente cambia un dato o programa durante la generación, replantear el turno, sin enviar versiones antiguas ni repetir partes ya recibidas. Citar una consulta pendiente en la primera parte y conservar las siguientes sin repetir la cita. El modo Humano sigue deteniendo toda automatización.

## Implementación

- Se reutiliza `wait_seconds`, entre 0 y 3600 segundos. La selección de la operación exige que haya transcurrido esa espera desde su recepción; sólo la entrada vigente puede generar. Cada mensaje nuevo tiene su propio reloj, por lo que un mensaje que llega durante la espera vuelve a posponer la respuesta. El valor recomendado y predeterminado nuevo es 60. Los valores ya guardados no se migran automáticamente.
- Una fotografía del turno identifica hasta 24 entradas pendientes, con máximo 12000 caracteres y ventana vigente de 24 horas. El cursor sólo avanza por un grupo completo aceptado/enviado/entregado/leído, una decisión explícita y validada de no responder o una intervención humana aceptada. No se consideran enviados los borradores fallidos, inciertos o cancelados. El reinicio explícito de memoria conserva su límite.
- El modelo recibe todas las consultas pendientes ordenadas además del historial real, las mismas skills, las fuentes y la memoria institucional. Las correcciones recientes prevalecen. Una pregunta repetida exige aclaración, no descarte por semejanza. No hay un segundo modelo evaluador ni inferencia adicional para preparar el turno.
- Antes de generar se retiran únicamente partes anteriores de IA en `queued`, con cero intentos, sin ID de proveedor y en el mismo ámbito y época. Se conserva el historial. El siguiente ciclo prepara el turno vigente. Un trabajo enviándose o una generación anterior con lease activo pospone sólo este turno tres segundos, sin bloquear el procesamiento de otros contactos. Un envío incierto exige revisión; no se repite automáticamente.
- Se mantienen las guardas de entrada más reciente, control IA/época, fuente, modelo, credencial, presupuesto, lease y contexto antes de cada IO y al confirmar. Si cambia el contexto durante la generación no se publica esa respuesta; la operación de la entrada nueva esperará su plazo y volverá a reunir las preguntas pendientes. Una solicitud adicional de generación puede tener coste, aunque el borrador anterior nunca se enviara.
- La cita usa el ID de proveedor verificado de la primera entrada pendiente. La entrada más reciente continúa siendo la guarda del turno. Sólo la primera parte lleva cita. WhatsApp usa `context.message_id`; Messenger e Instagram con Facebook Login usan `reply_to.mid`. Instagram con acceso directo conserva la respuesta normal: la documentación consultada sólo acredita la cita con Facebook Login. No se realiza un segundo envío sin cita si Meta rechaza el primero.
- `decision=esperar` sólo está disponible en turnos privados con agradecimientos de una lista conservadora y al menos una salida real en el historial. Texto u observaciones CRM no vacíos invalidan esa decisión. Preguntas, objeciones, «sí», «ok» aislado, nuevos datos y solicitudes humanas no habilitan silencio. La decisión válida queda confirmada como `reply_turn_no_response`, sin mensaje nuevo ni cambio a Humano. El modelo puede optar por una respuesta breve en lugar de silencio.
- El grupo de notas de voz usa el mismo cursor de recibos para no perder un audio detrás de un borrador descartado. Se conserva la protección contra repetir una transcripción anterior incierta.

No se promete deduplicación semántica perfecta: se dan instrucciones con evidencia real y se restringe localmente el silencio. Los lotes que exceden los límites requieren revisión, sin truncar silenciosamente las primeras consultas. Las citas de mensajes antiguos pueden ser rechazadas por las condiciones del proveedor; no se falsifican recibos.

## Validación local y publicación

285 pruebas backend aprobadas y 2 omitidas de la selección; 61 frontend aprobadas antes del último ajuste de texto del preset. Incluyen espera 0/60/120/3600, ámbito del turno, orden, reinicio, lote excesivo, silencio acotado, esquema estricto de OpenRouter, citas sólo en primera parte, invalidación antes de confirmar tras una generación, voz pendiente y guardas de control. Ruff E4/E7/E9/F aprobado; tipos y ESLint sin errores, con advertencia previa sobre dependencia `dirty`; compilación institucional aprobada con advertencia histórica de bundle. La comprobación final y el despliegue se registrarán al observar sus resultados.

No DDL, seeds, servicios nuevos ni escrituras SIIE. No se reenvían conversaciones históricas ni se alteran recibos. Las aceptaciones iniciales P4/P13/P21 se conservan. P22 mantiene 3/5 hitos técnicos y 0/5 aceptaciones comerciales.

## Referencias oficiales

- [Meta Page Messages: reply_to.mid](https://developers.facebook.com/docs/graph-api/reference/page/messages)
- [Instagram Messaging: soporte de respuestas citadas con Facebook Login](https://developers.facebook.com/documentation/business-messaging/instagram-messaging/changelog/)
