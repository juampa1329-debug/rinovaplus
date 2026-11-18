# P4-Meta · matriz operativa de aceptación

Corte: 17 de noviembre de 2026, America/Bogota. Alcance vigente autorizado: WhatsApp, Facebook/Messenger e Instagram. Todo TikTok pasa al [plan P16](P16_TIKTOK_PLAN.md). Los checkpoints y denominadores históricos se conservan; esta matriz no fabrica cierre canónico ni pruebas externas.

| Recorrido | Evidencia verificada | Pendiente real |
|---|---|---|
| WhatsApp OAuth | Descubrimiento de números CBN y cuenta gratuita separada autorizada por OAuth. | La cuenta «WhatsApp · CBN» aún figura pendiente de verificar; aceptar el número institucional antes de retirar el anterior. |
| WhatsApp recepción | Callback de prueba verificado por el propietario, texto entrante y Gemini en IA. Imagen y sticker animado entrantes comprobados previamente. | Consolidar recorrido institucional con su propia ruta. |
| WhatsApp salida y recibos | Voz confirmada por propietario; imagen anterior recibida; hello_world desde broadcasting con pendiente/aceptado/enviado/entregado/leído y respuesta citada atribuida. | Video y sticker salientes, comprobación en teléfono. |
| WhatsApp fallo y recuperación | Cabecera deliberadamente inválida en número gratuito: Meta aceptó y notificó fallo real; un intento, ID conservado y reintento automático bloqueado. Consentimiento temporal revocado y cadencia apagada. | Consolidar reversión y revisión de colas con cuenta institucional. |
| Messenger | OAuth, cuenta/webhook, nombre, mensaje entrante, Gemini y entrega; seguimiento en Humano con cero inferencias/respuestas bot. | Prueba revisada de recuperación y revocación sin afectar las otras cuentas. |
| Instagram DM | OAuth, entrada real, Gemini y silencio en Humano. `messaging_seen` activado y sincronizado. Nueva prueba manual recibida y leída: un intento; recibo firmado verificado y evento procesado `read`. | Consolidar recuperación/reversión; no convertir otros mensajes aceptados en leídos sin sus propios eventos. |
| Instagram comentarios | Comentario real y respuesta personalizada publicada; ID observado de vuelta por webhook. Guarda Humano rechaza sin proveedor. | Consolidar recuperación, borrado/edición y reversión con fuente vigente. |
| Facebook comentarios | Llegó «Necesito orientación» a las 20:34:33 Bogotá; Gemini confirmado, un envío aceptado y su ID observado de vuelta por webhook. Vista previa de publicación real. Comentario pasado a Humano; guarda con versión vigente rechaza sin proveedor. | Ensayo real de edición/borrado, recuperación y reversión; la guarda Humano no equivale a una nueva carrera durante inferencia. |

Fuentes: [pruebas sociales](../../artifacts/live/social-ai-20261117.json), [catálogo](../../artifacts/live/p7-catalog-20261117.json), [broadcasting](../../artifacts/live/p7-broadcasting-20261117.json) y [respuesta/fallo real](../../artifacts/live/p7-replies-failure-20261117.json).

## Consolidación de límites y reversión

Preparar no envía. Pausar impide trabajos no iniciados; los aceptados o inciertos conservan identificador e historial y se concilian antes de repetir. Revocar consentimiento no borra evidencia. Humano invalida respuestas automáticas pendientes. Rotar/revocar credenciales de una app compartida puede afectar varias cuentas: esa prueba debe hacerse sobre recursos de test, preservando los institucionales. No se revocaron credenciales productivas para simular fallos.

Se consolidaron [40 regresiones de recuperación Meta](../../artifacts/live/p4-meta-recovery-20261117.json), diez por canal: WhatsApp, Facebook, Messenger e Instagram. Recorren el normalizador real y descifran un recibo sintético AES-GCM; la transacción SQL y la autoridad son dobles controlados. Comprueban reencolado del evento original; rechazo sin escritura de digest, fuente, cuenta pausada, ruta inactiva, duplicado y versión cambiada; bloqueo de reenvío cuando el proveedor sigue incierto, ejecutándose o confirmado. La suite conjunta termina en **186 pruebas correctas**, con cuatro avisos de deprecación existentes; Ruff F correcto.

Estas comprobaciones locales complementan la aceptación externa registrada por canal. No equivalen a una restauración institucional de base/archivos ni a pruebas de carga. La reversión productiva completa sigue pendiente de ensayo revisado: no se revocaron secretos compartidos ni se redirigieron cuentas institucionales para simularla.

La revisión productiva detectó que una sincronización repetida chocaba con una clave única anterior (`23505`) antes de llegar a Meta. Se corrigió la clave del intento explícito de suscripción sólo para Meta, manteniendo replay por ID y el historial. La sincronización de Instagram terminó **Confirmado por el proveedor**. Después llegó el recibo real de lectura de una prueba nueva: `Authentication=verified`, evento `processed`, estado `read`, un intento. El conjunto relacionado posterior, incluyendo adjuntos de plantillas, pasa 209 pruebas backend.

## Procedimiento por canal para completar la aceptación externa

| Canal | Recuperación revisada | Fallo controlado | Reversión que debe conservar evidencia |
|---|---|---|---|
| WhatsApp | Recuperar el evento original desde Actividad y recuperación sólo si su cuenta/ruta/firma siguen vigentes. Repetir la proyección no debe crear otro contacto/mensaje. | El recurso gratuito ya notificó fallo real de adjunto; hay un intento y su ID, sin entrega inventada. Falta ensayar el recorrido institucional sin sustituir aún el número anterior. | Pausar salida de esa cuenta y conservar intentos/recibos. Volver a una ruta anterior exige confirmar antes cuál sigue activa en Meta; nunca reenviar efectos aceptados o inciertos. |
| Messenger | Pausar únicamente la cuenta de prueba, verificar el recibo pendiente, reanudar y reprocesar ese evento por ID. Comprobar una sola conversación y mensaje. | Validación de token/permisos sólo en recursos de prueba; una credencial compartida no se revoca para ensayar. La guarda local ya rechaza resultados inciertos. | Volver al estado de cuenta revisado y conservar `messages`, `message_reads`, `message_deliveries` y `feed` de la Página compartida. No sobrescribir sus campos al operar Facebook. |
| Instagram DM | Mismo recibo original y cuenta propia; comprobar que IA/Humano y la versión vigente siguen autorizando la respuesta. | Lectura real ya comprobada después de suscribir `messaging_seen`. La ausencia de otros recibos no se convierte en entrega; permisos caducados se ensayan en recursos de prueba. | Pausar la cuenta sin retirar las otras de la app. Conservar el modo de login, callback y suscripción; revalidarlos al volver. |
| Facebook/Instagram comentarios | Reprocesar el comentario original y verificar su publicación de origen. Un comentario editado o borrado debe invalidar la respuesta anterior pendiente. | Publicación y respuesta real comprobadas en ambos canales; falta ensayo de edición/borrado y recuperación externos. La guarda de fuente vigente está probada. | Dejar el comentario en Humano y cancelar sólo lo aún pendiente; conservar el ID de cualquier respuesta publicada. El borrado de una respuesta pública requiere una acción explícita independiente. |

Antes de cualquier ensayo: anotar cuenta/app, estado de control, callback y operaciones pendientes, sin copiar secretos al informe. Después: comprobar la cola por ID, ausencia de segundos intentos, recepción firmada y estado final elegido. Si el proveedor ya aceptó o el efecto es incierto, conciliar primero; un error de red no autoriza repetir un POST. El cambio de imagen de Coolify conserva base y medios; restaurar datos es otro ensayo, con sus propios recibos.

## Documentación oficial contrastada

[Campos y permisos de Instagram](https://developers.facebook.com/documentation/instagram-platform/webhooks/fields) y [ejemplos de notificaciones](https://developers.facebook.com/documentation/instagram-platform/webhooks/examples), consultados el 17 de noviembre: `messaging_seen` usa `instagram_manage_messages` en la API de mensajería compatible; informa `read.mid`. La suscripción por app y la habilitación por cuenta deben probarse juntas. El adaptador incorpora la suscripción y ambos formatos documentados, `entry.messaging` y el envoltorio `entry.changes`.
