# Continuidad del contexto y mensajes con imágenes

25 de noviembre de 2026. Estado inicial: corrección preparada, pendiente de publicación y comprobación real.

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

No se acredita aún despliegue, inferencia nueva con imagen, entrega a los contactos ni recuperación automática real por esta corrección. No se modificaron recibos anteriores, no se repitió el intento incierto, no se generó volante ni se enviaron escrituras SIIE. El webhook conjunto sigue pendiente del reenvío corregido desde SIIE. P23 mantiene 0/9 aceptados y las demás aceptaciones se conservan.
