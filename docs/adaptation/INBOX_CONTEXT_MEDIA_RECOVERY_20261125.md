# Continuidad del contexto y mensajes con imágenes

25 de noviembre de 2026. Correcciones `0654df5` y `936fcd3` publicadas y saludables. Tres orientaciones nuevas entregadas; quedan pendientes expresos abajo.

## Evidencia que motivó la corrección

- Un turno de horarios de PRE-ICFES tuvo cinco borradores descartados con cero intentos. El diagnóstico de la generación conserva `dispatch_context_changes=["system"]`: cambiaron las instrucciones antes del envío. Los horarios sí existían; no fue una ausencia de información.
- Una imagen de confirmación del formulario quedó sin operación de IA. El código de recepción sólo programaba texto, botones y audio de WhatsApp, y texto de Instagram/Messenger. Las imágenes puras estaban fuera de esa ruta.
- Un intento manual nuevo de horarios quedó `uncertain/send_lease_expired`, un intento, sin aceptación acreditada. No se repitió. Otro intento manual no terminó de preparar el envío por espera de almacenamiento; no se acredita entrega. Ambos chats volvieron a IA y se retiró el borrador manual no enviado del compositor.
- El número de otro caso no apareció al buscarlo en Inbox ni CRM. Las consultas anteriores buscaban el teléfono editable de Contact, sin incluir el identificador del canal. Su localización y atención siguen pendientes de comprobación real.
- Un evento mostrado como `[unsupported]` necesita pedir el reenvío, sin fingir que el canal entregó su contenido. No se atribuye a mensaje temporal, eliminación u otra causa no acreditada.

## Comportamiento preparado

Cuando cambian el contexto, las instrucciones, el modelo aprobado o la configuración de respaldo, se crea un nuevo turno sobre la entrada autenticada vigente. Se releen mensajes, catálogo, memoria, agente, instrucciones y configuración. Se conserva la espera configurada. Una nueva entrada sigue su propia operación; el control Humano, su época, las bajas y la ventana de respuesta prevalecen.

La recuperación sólo retira partes que siguen sin intentar y sin identificador externo. Las partes explícitamente aceptadas se incorporan como historial de la misma institución, cuenta, identidad y conversación, para continuar sin repetirlas. Cualquier parte enviándose, intentada sin aceptación, incierta o incongruente bloquea esa recuperación. Tres reconstrucciones por entrada limitan un bucle de configuración cambiante; el diagnóstico distingue el turno nuevo en cola de un envío efectivamente aceptado. No hay replay de un POST incierto ni reenvío masivo de histórico.

Las imágenes entran a la cola normal y esperan al descargador existente. Sólo se adjuntan archivos inspeccionados, con hash verificado y ligados al mensaje/hilo/cuenta/identidad. Máximo tres imágenes de 4 MB, JPEG/PNG/WebP, con reserva conservadora de entrada y comprobación del catálogo de visión. Se transmiten inline, sin publicar URLs privadas. El mismo contrato JSON, las skills y las guardas de salida permanecen. Un adjunto no disponible produce orientación para reenviarlo; una captura no confirma identidad, pago, inscripción en SIIE ni matrícula.

OpenRouter recibe imágenes en `chat/completions` mediante partes `image_url` con data URL, según su [guía oficial de visión](https://openrouter.ai/blog/tutorials/send-image-to-llm/). Gemini mantiene su formato inline documentado en [Image understanding](https://ai.google.dev/gemini-api/docs/image-understanding). Sólo se usan las rutas ya aprobadas que figuren disponibles para visión; no se cambian modelos activos ni se reintentan inferencias multimodales inciertas.

El receptor también programa una aclaración para un evento WhatsApp auténtico de tipo `unsupported`, sin adivinar su contenido. No convierte reacciones en preguntas. La revisión administrativa de entradas sin operación puede localizar imágenes históricas del mismo ámbito, dentro de 24 horas y sin salida posterior; no las reenvía por consultar el listado.

El claim PostgreSQL existente concede 60 segundos. Dentro de la misma transacción se alinea su concesión viva de trabajo y operación a 180 segundos para dar margen a las comprobaciones previas y al transporte acotado. Se exige la misma concesión no vencida y ambos estados vigentes. No revive un trabajo vencido, no cambia intentos/cuotas y no modifica la unidad SQL congelada ni ejecuta DDL. Esto mitiga la expiración durante comprobaciones bajo carga; no acredita que desaparezca toda contención de almacenamiento.

La búsqueda incorpora ExternalIdentity junto al teléfono CRM, con institución y contacto, y también conversación en Inbox. La pauta provisional del titular para PRE-ICFES indica envío del volante al día siguiente de diligenciar el formulario cuando preguntan por el pago. Es gestión manual hasta integrar el contrato de volante; no se inventan cuentas, vencimientos ni una generación/envío ya realizados.

## Verificación local

- Selección final: 486 pruebas backend pasan, tres omitidas explícitamente. Otra selección posterior de fuentes/inscripción/nuevas rutas: 82 pasan. Hay solapamiento; no se suman como suites disjuntas.
- Las tres pruebas de `test_commercial_risk_filter_keeps_bound_current_conversation_and_valid_sql` fallan por `unmapped_crm_table` usando el mapa de workspace anterior. Se reprodujeron con la preimagen completa de `workspace.py` del commit `25a91e4`, sin cambiar código productivo ni relajar el mapa. No se declara suite completa verde.
- Diez pruebas frontend seleccionadas pasan; TypeScript, ESLint seleccionado, Ruff seleccionado y compilación institucional aprobados. Advertencia histórica de bundle conservada.
- Casos nuevos cubren aislamiento de cuenta/identidad, contexto actualizado, Humano, baja, resultados inciertos, continuidad parcial con recibos, archivos ajenos/no disponibles, espera del descargador, contrato multimodal, reserva/catálogo de visión y concesión sin resurrección.

## Límites de este corte

### Ampliación tras comprobación nativa

`0654df5` pasó salud en Coolify: backend `wa1vobamffk3is5vysyjukji`, Success 4m19s; frontend `n55fth64okxyvzpyufd6trlx`, Success 45s. La búsqueda por el sufijo del número encontró ahora el contacto esperado, antes ausente. Su mensaje nuevo quedó en cola con cero intentos y `messaging_response_window_closed`; al restaurar IA se conservó cancelado con cero intentos. No se acredita entrega ni se conserva una salida pendiente que pueda duplicarse.

La selección manual de ExternalIdentity no tenía orden. Se elige ahora la identidad con entrada más reciente del mismo ámbito; los valores nulos van al final explícitamente en ambos dialectos. La ventana de 24 horas y el control Humano siguen obligatorios, sin mover fechas ni inventar entradas. Esto corrige la selección; la causa exacta de la ventana de ese caso se comprobará con un envío nuevo después de publicar.

Los registros siguen mostrando `55P03` al adquirir el bloqueo de institución. Las lecturas de listados tomaban ese mismo bloqueo compartido durante consultas largas, retrasando escrituras. Las transacciones PostgreSQL de sólo lectura usan ahora `REPEATABLE READ READ ONLY`: autorización, revisión y datos conservan una misma vista confirmada sin retener el bloqueo de escritura. Todas las mutaciones mantienen el bloqueo exclusivo, comprobación de institución/usuario, permisos, CSRF, revisión y guardas inmediatamente anteriores al proveedor. No hay DDL, privilegios nuevos, repetición de mutaciones ni relajación de la firma.

SIIE conserva el mismo evento sintético en reintento con HTTP 503. La interfaz recién consultada confirma recepción habilitada y secreto presente; cero eventos verificados. No se deduce del 503 que la firma esté corregida. El receptor registra ahora un motivo fijo de almacenamiento/configuración con `signature_verified=true` sólo después de verificar la firma. El cuerpo HTTP conserva `{"detail":"storage_busy"}`, `general_storage_unavailable` o `siie_webhook_disabled`, según la causa; secreto ausente conserva `siie_webhook_not_configured`. Nunca se registran cuerpo, documento, claves, firmas ni identificadores. Un fallo no devuelve acuse; el mismo evento puede reintentarse y un duplicado confirmado no vuelve a proyectarse.

Selección adicional de 329 pruebas backend aprobada (solapada con anteriores): PostgreSQL, permisos de lecturas/escrituras, HMAC, cuerpos 503, no acuse ante almacenamiento ocupado, reintento idempotente, elección de identidad, contexto y medios. Ruff de errores Python (`E9,F`) pasa. La selección completa de estilo de estos archivos encuentra advertencias históricas de longitud/importaciones; no se declara Ruff completo verde.

`936fcd3` pasó salud en Coolify: backend `oi4wjrayqborlb68fmgto8eh`, Success 4m22s; frontend `8rdxkulxgjkdxeywjnz1mfdb`, Success 25s. Se completaron tres orientaciones manuales nativas: aclaración de contenido no disponible, volante al día siguiente y acuse de captura con elección de pago. Las tres quedaron **Entregado**; los tres hilos se restauraron a IA y se verificó el control. El primer intento del caso de pago se canceló sin intento; sólo su nueva orientación tiene recibo de entrega. El número buscado corresponde al contacto esperado y la nueva selección de identidad permitió enviar dentro de la ventana sin modificar fechas.

La recuperación administrativa de imagen se puso en preparación, pero quedó detenida con `storage_busy` antes de acreditar una inferencia. La respuesta entregada fue revisada manualmente a partir de la captura; **no acredita una inferencia multimodal productiva**. No se relanzó esa operación fallida. Una futura imagen nueva debe validar el recorrido automático completo. El replanificador está cubierto en pruebas, pero no se acredita aquí una reconstrucción automática real posterior a un cambio de instrucciones.

El intento anterior de horarios sigue `uncertain/send_lease_expired`, un intento y sin recibo de aceptación. La bandeja WhatsApp de Meta Business Suite no está configurada en la superficie disponible; no fue posible corroborarlo allí. No se repitió ni se modificó su recibo. El hilo sigue IA. No se declaran todos los casos históricos atendidos.

Los registros del nuevo contenedor conservan esperas `55P03` durante el solapamiento de despliegue, hasta 00:00:54 UTC; las observaciones nativas posteriores acreditan las tres entregas y consultas sin modal, no un SLA ni carga máxima ni cero fallos perpetuos. No se cambió el timeout de bloqueo ni la firma para ocultar errores.

Rinova sigue mostrando recepción SIIE habilitada, secreto reconocido y **cero eventos verificados**. El titular aportó el mismo evento sintético con cuatro intentos/HTTP503; el cuerpo de ese rechazo aún no se recibió. Se solicitó reenviar ese evento con payload corregido estable y timestamp/firma nuevos, sin otra inscripción. El contrato único añade los códigos seguros 503 y la revisión del reloj del planificador de SIIE. No se acredita aún firma corregida en un intento nuevo ni recepción conjunta.

No se generó volante/PDF, no se escribieron datos nuevos en SIIE y no hubo DDL, seeds, servicios ni cambios de modelos. P23 mantiene 0/9 aceptados y las demás aceptaciones se conservan.

También permanecen como comprobaciones separadas las citas entrantes de mensajes antiguos (incluida imagen citada con respuesta mínima) y el caso de imagen de Instagram señalado anteriormente por el titular. Las pruebas del adaptador multimodal y la atención manual de la captura no acreditan esos dos recorridos históricos.
