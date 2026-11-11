# Multimedia del Inbox — aceptación local del 2026-10-20

Implementada en la misma aplicación `127.0.0.1:4173`, propietarios Inbox/canales y copia local DBSIIE. Imagen, documento y audio se adjuntan al mensaje existente; guardar localmente no llama proveedores ni encola envíos externos. El control, asignación, mini CRM, diario, CAS e intención de destino del Inbox se conservan. Esta unidad no modifica ajustes ni credenciales de IA.

## Persistencia y contrato efectivo

El operador aplicó la migración aditiva **016** mediante `backend/tools/migrate_inbox_media.py`, con `verify_target`, TLS y verificación de huellas antes/después. Añade únicamente `crm_channels.MediaAsset`, marcador `inbox-media-v1`; no altera core ni tablas legacy. Los archivos privados usan el volumen durable existente, en `inbox-media`, con nombres internos UUID y metadatos SQL; no se publica una carpeta de archivos ni se entrega la URL del proveedor al navegador. La receta conserva Pillow **13.0.0**, pypdf **6.21.1** y ffmpeg/ffprobe **5.1.9**; el operador instaló estas dependencias en el mismo runtime. No hay DDL al arrancar ni otro servicio.

Se mantienen los endpoints de Inbox. Bajo `/api/local/crm/inbox/conversations/{conversation_id}/media/{media_id}`, `PUT` carga bytes acotados, `GET` devuelve metadatos y `DELETE` descarta únicamente un adjunto de carga sin mensaje confirmado. `GET .../content` sirve contenido privado con Range simple 206/416, no-store y nosniff; documentos se descargan como attachment. El guard local existente sigue exigiendo las condiciones loopback/Host/Origin y cabecera local. No equivale a autenticación multiusuario ni RBAC. En navegador se obtiene contenido con cabecera mediante fetch/Blob; las URLs Blob se liberan y no contienen tokens del negocio. El guardado vincula archivo y mensaje en la misma transacción del escritor existente; un archivo ya confirmado no se elimina al cancelar otro borrador.

Política local: **un archivo por mensaje, 5 MB**, imágenes JPEG/PNG hasta 16 megapíxeles, PDF/TXT y DOCX/XLSX/PPTX sin macros ni contenido activo admitido; audio hasta **300 segundos**. La grabación por micrófono tiene controles explícitos de inicio/detención/cancelación y límite de **60 segundos**. ffmpeg normaliza audio a Ogg/Opus; no se cambia el texto del usuario por una transcripción ficticia. Se limita concurrencia de inspección, cuota global de 250 MB y por conversación de 50 MB; cargas sin confirmar caducan en una hora. Esos valores son política local, no límites atribuidos a las plataformas.

La inspección no confía en el MIME declarado. JPEG/PNG se verifican y recodifican; Office se inspecciona como contenedor y PDF se analiza estructuralmente con pypdf estricto en un proceso acotado, sin renderizar. PDF permite enlaces HTTP/HTTPS válidos sin credenciales y navegación GoTo interna; rechaza cifrado, acciones automáticas/ejecutables/desconocidas, JavaScript, archivos incrustados, XFA y RichMedia. Conserva límites de objetos/profundidad, memoria, CPU, tiempo y descompresión estructural. No decodifica imágenes ni fuentes para decidir si existe una acción. No se afirma antivirus, eliminación de malware o validación exhaustiva de cada formato.

## Recepción y envío desacoplados

La ingesta registra referencias de adjuntos junto con el mensaje, conserva captions WhatsApp y deja al worker la descarga/inspección durable. Se comprueban conversación, identidad y cuenta originales, así como la revisión vigente antes de publicar el archivo. La descarga remota valida TLS, host y direcciones públicas, sin redirecciones ni URLs arbitrarias. La restricción de un archivo por mensaje se hace explícita ante eventos con varios adjuntos; no se presenta una recepción parcial como éxito completo.

El envío externo conserva selección explícita de destino, outbox y estados reales. La subida privada precede una nueva validación de frontera: identidad/conversación exactas, cuenta/revisión, control/epoch, ventana y estado de cola se revisan antes del POST de mensaje. El trabajo bot obsoleto no se reactiva al liberar control; los mensajes humanos se distinguen. Una petición externa ya iniciada no puede retirarse. Resultados inciertos no se reenvían ciegamente. Encolar no satisface por sí solo el SLA.

- WhatsApp usa subida privada y media ID; audio no admite texto/caption adicional en esta unidad.
- Messenger usa multipart privado. Instagram lo usa exclusivamente con Facebook Login, Page ID y Page Access Token; PDF es el documento admitido y el audio se convierte al formato correspondiente. El modo Instagram Login no se presume equivalente.
- TikTok admite únicamente imagen JPEG/PNG de hasta **3 MB**: determina el tipo de conversación mediante paginación acotada, consulta IMAGE_SEND y sube/envía el media ID. No se implementa audio/PDF sin contrato. Un CDN de descarga no verificado se rechaza; no se amplía la confianza a hosts arbitrarios.

Estos adaptadores implementados no acreditan permisos, cuentas conectadas, recepción de webhook ni entrega real. Texto adicional incompatible con el adjunto se bloquea explícitamente para evitar pérdidas silenciosas. La intención local continúa disponible sin canales vinculados.

## Aceptación manual observada

El operador utilizó archivos reales existentes y guardó únicamente mensajes locales:

- JPEG de 84 059 bytes: vista previa y guardado; recodificación a **118 201 bytes**, archivo listo y vinculado.
- PDF de **2 202 633 bytes**: carga y guardado con texto. Descarga HTTP 200 por Nginx con igual longitud y SHA-256 que SQL y el original; disposición attachment y no-store.
- MP3 de 114 145 bytes: conversión real a Ogg/Opus de **43 106 bytes**, duración **7,065 segundos**, y guardado sin texto, solamente el archivo. Play nativo confirmó `paused=false`, `readyState=4`, `error=null` y duración **7,065375 s**.
- Petición Range `bytes=0-63`: HTTP **206**, 64 bytes y Content-Range exacto; rango inválido: **416**. Sin cabecera local: **403**. Consultar el mismo archivo bajo otra conversación: **404**.
- El HTML del frontend fue rechazado como formato no admitido y descartado. Se descartaron cargas fallidas sin eliminar archivos de mensajes confirmados. No se utilizaron identidades, mensajes ni webhooks ficticios.

Una conexión SQL nueva con guard válido confirmó **2 contactos, 2 conversaciones, 7 mensajes, 0 identidades externas, 0 outbound y 0 MessageRoute**. El cierre confirmó **3 MediaAsset ready vinculados y 4 deleted**. Ningún mensaje se envió a plataformas.

La recarga real conservó los tres adjuntos. El JPEG cargó con dimensiones 940 × 915; el botón nativo de descarga PDF produjo 2 202 633 bytes y SHA-256 igual al original, además de la comprobación HTTP. Play después de recargar mostró tiempo 6,887706 s de 7,065375 s, `paused=false`, `readyState=4` y `error=null`. ffprobe del archivo guardado confirmó Ogg/Opus mono; Range del audio `bytes=0-255` respondió 206 con 256 bytes, `audio/ogg`, Content-Range `0-255/43106` y cabecera OggS. La consola reciente no mostró errores y el borrador quedó vacío. La nota sin texto conserva el marcador explícito `[audio]`; no representa una transcripción. Micrófono real no probado.

Capturas finales revisadas: [multimedia y reproducción](C:/Users/Developer_PC/.codex/visualizations/2026/10/19/01a1562a-952c-7913-a6cf-c6abf669e15e/inbox-multimedia-final.png) y [documento descargable](C:/Users/Developer_PC/.codex/visualizations/2026/10/19/01a1562a-952c-7913-a6cf-c6abf669e15e/inbox-multimedia-documento-final.png).

Durante la aceptación se corrigió un falso positivo: una regex sobre todos los bytes del PDF encontraba nombres como `/JS` en streams comprimidos. Se reemplazó por inspección estructural. El primer criterio estructural rechazaba también enlaces legítimos; se delimitó la política a acciones reales, permitiendo los cinco enlaces HTTPS del PDF utilizado. La descompresión de todos los streams agotaba presupuesto sin aportar a la detección de acciones; se limita a `/ObjStm` y `/XRef`. El mismo PDF real pasó después y conservó sus bytes. Estos hechos no acreditan aceptación de cualquier PDF.

Nginx se recargó en el mismo contenedor para activar el límite de cuerpo y tiempo de proxy necesarios; no se reinició ni recreó la aplicación. Se aplicó formato a las fuentes modificadas antes de la aceptación. No se ejecutaron pruebas automáticas, lint, typecheck, builds de comprobación, copias ni commits.

## Límites de este corte

Pendientes: grabación real con micrófono, otros documentos Office/TXT y codecs, recepción mediante eventos firmados de cuentas reales, permisos y entrega/lectura de plataformas, recuperación/concurrencia/carga y confianza explícita en CDN TikTok cuando corresponda. No se acredita streaming Range desde el reproductor nativo: se verificaron por separado reproducción privada en navegador y Range del endpoint. No se añadió RBAC, OAuth, enlaces públicos ni análisis IA del archivo. Los límites connected del [Inbox anterior](inbox-sprint3-local.md) siguen vigentes. El [modelo histórico](../contracts/sprint-3-inbox-model.md) no se aplicó literalmente: el almacenamiento real usa MediaAsset de 016 y conversación/identidad existentes.

Referencias primarias: [Meta WhatsApp](https://www.postman.com/meta/whatsapp-business-platform/folder/13382743-ecb27be5-4d27-4763-bbee-6a8002c04bf3), [Instagram attachment upload](https://developers.facebook.com/documentation/business-messaging/instagram-messaging/features/attachment-upload), [TikTok image upload](https://business-api.tiktok.com/portal/docs/upload-an-image/v1.3), [TikTok image download](https://business-api.tiktok.com/portal/docs/download-an-image-or-a-video-from-a-message/v1.3), [pypdf estricto](https://pypdf.readthedocs.io/en/stable/user/robustness.html). Describen contratos/controles, no operación conectada del CRM.
