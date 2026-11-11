# Canales operativos del Sprint 2 — 2026-10-20

La pestaña **Ajustes > Canales** permite configurar WhatsApp, Instagram, Messenger, Facebook y TikTok desde el mismo frontend. Los botones Conectar abren formularios; guardar, validar acceso, suscribir y pausar utilizan el backend real y la misma copia SQL local `DBSIIE`. Se retiró de esta pantalla el inventario visual de contratos pendientes. Se conserva el diseño Glass y el desarrollo en caliente.

## Configuración y credenciales

**Ajuste de carga inicial de WhatsApp, 2026-10-20:** el operador puede guardar y validar únicamente Access Token, WABA ID y Phone Number ID. App ID, App Secret, verify token y callback HTTPS siguen siendo obligatorios para activar recepción/envíos; no se requieren para consultar los metadatos del número. El selector de entorno identifica desarrollo o producción únicamente por elección explícita del operador. Si no se indicó versión Graph, la validación realiza las dos lecturas de metadatos sin elegir una versión y solo persiste una versión `vNN.0` observada en el header `facebook-api-version` de respuestas correctas. Si Meta no informa ese dato, no se inventa una versión; la activación continúa bloqueada hasta configurarla. La validación no suscribe webhooks, no activa el despachador y no envía mensajes.

**Resultado de la carga inicial observada:** el operador guardó el perfil de desarrollo mediante la UI, con credenciales cifradas y revisión 1. La consulta real fue rechazada por Meta con HTTP 401, código 190/subcódigo 463: token vencido. Esto no acredita conexión, permisos, mensajes ni webhooks activos. La aplicación distingue este resultado con un mensaje constante que indica generar un token nuevo, reemplazarlo desde el formulario, guardar y volver a validar. Solo se inspeccionan códigos numéricos de una respuesta acotada; no se devuelve el texto del proveedor ni se documentan credenciales.

Cada canal conserva un perfil con identificadores de aplicación y recurso, versión Graph, producto de login de Instagram, callback HTTPS y etapa inicial del CRM. Access Token, App Secret y verify token son entradas de escritura: los GET solo indican cuáles están configurados. Un campo secreto vacío conserva el valor anterior. La UI permite generar y copiar el verify token antes de guardar; después no se recupera desde el servidor. El PIN de registro y el código de verificación de WhatsApp solo se transmiten a Meta cuando el operador solicita esa acción.

Las credenciales se cifran con AES-256-GCM: clave de 32 bytes en el volumen privado existente `/var/lib/crm-ai/channels-aes256.key`, nonce aleatorio de 12 bytes y AAD que vincula canal/tipo/versión. SQL contiene KeyId, nonce y ciphertext con etiqueta autenticada. Una clave ausente o distinta con registros cifrados existentes bloquea el acceso; no se reemplaza silenciosamente. La clave no se publica en Git ni en respuestas HTTP. Los endpoints administrativos conservan la protección local por loopback, Host, Origin y `X-CRM-Local`; esto todavía no constituye autenticación empresarial/RBAC.

Se utiliza conexión directa con tokens autorizados obtenidos en las plataformas. No se implementó OAuth automático: sus contratos históricos permanecen como propuestas y no aparecen como controles operativos. Tampoco se creó un túnel ni se publicó el backend local.

## SQL aplicado y compatibilidad

La migración explícita `011_channels.sql` crea ocho tablas propias de `crm_channels`: `Account`, `Credential`, `webhook_events`, `ExternalIdentity`, `ExternalMessage`, `outbound_queue`, `social_comments` y `Audit`. `012_channels_identity_collation.sql` aplica `Latin1_General_100_BIN2` a los identificadores opacos de proveedores. Ambas se aplicaron con el runner guardado `backend/tools/migrate_channels.py`, verificando destino local y contrato/huella del esquema CRM. Los documentos JSON usan `NVARCHAR(MAX)` con restricciones `ISJSON()`.

No se altera el core SIIE, el esquema `crm` ni su huella. No se crea una segunda base. Los vínculos externos se conservan en el esquema nuevo. Un perfil con historial no puede cambiar de aplicación/cuenta/página/número mediante el formulario: sus tokens y callback pueden actualizarse, pero cambiar su identidad exige una futura reasignación explícita que preserve conversaciones y colas.

La revisión lógica del workspace suma el máximo de `crm.Operation` y el número de auditorías `incoming_message` de `crm_channels.Audit`. Estas últimas se escriben junto con el mensaje entrante bajo el bloqueo transaccional vigente. Así una entrada externa invalida las revisiones antiguas sin atribuirla falsamente a `local-operator`. La ingesta no fusiona contactos por teléfono: conserva la identidad del proveedor y crea su vínculo propio. Requiere una etapa inicial activa y respeta los campos CRM obligatorios; un evento que no pueda satisfacerlos queda pendiente/fallido con posibilidad de reprocesamiento.

## Recepción, ingesta y envío

`GET /api/v1/webhooks/meta` acepta el token configurado desde la UI y conserva compatibilidad con el digest privado anterior. `POST /api/v1/webhooks/meta` autentica `X-Hub-Signature-256` sobre los bytes originales. TikTok Business autentica `TikTok-Signature` con HMAC-SHA256 sobre `timestamp + '.' + cuerpo` y una tolerancia de cinco minutos. No se usa un bypass si falta el secreto. La firma determina los perfiles elegibles y la ingesta exige que el recurso corresponda al perfil.

El recibo guarda el texto JSON crudo, su payload interpretado, los perfiles elegibles y un digest único. Confirma HTTP 200 después del commit y antes de normalizar o llamar a plataformas. El trabajo SQL del recibo se ejecuta fuera del event loop; no toma el bloqueo global de cinco segundos del workspace. La latencia menor de un segundo sigue siendo un objetivo sin medición de carga en este corte.

Dos threads del proceso FastAPI existente se inician únicamente en `local_sql_copy` mediante lifespan y se detienen con ese proceso. No se agregó un segundo servicio ni un broker. El ingestor usa leases SQL recuperables y procesa mensajes, estados y comentarios; el despachador consume exclusivamente `outbound_queue`. El envío del Inbox con identidad externa inserta mensaje y cola en la misma transacción, sin llamar al proveedor desde la petición del operador. Las conversaciones locales siguen siendo locales; no se convierte automáticamente un teléfono en permiso de envío.

Los estados de salida incluyen `queued`, `sending`, `sent`, `delivered`, `read`, `failed` y `uncertain`. Solo una respuesta del proveedor con ID real permite `sent`; las confirmaciones recibidas se conservan incluso cuando llegan antes de persistir ese ID y se reconcilian al confirmar el despacho. Los estados de entrega avanzan sin degradar `read`/`delivered`. Fallos de conexión previos al envío y rechazos 429 pueden reintentarse con espera exponencial; una respuesta ambigua después de enviar, timeout de lectura, 5xx o interrupción del despachador queda `uncertain`, sin repetición automática.

El despachador vuelve a comprobar perfil, pausa, revisión, control humano, conversación abierta y ventana de servicio antes del envío. TikTok comprueba también su límite de respuestas y ventana de 48 horas. Estos controles no retiran una petición que ya salió a la plataforma. Las notas multimedia solo se conservan como payload y referencia textual; no se implementa aquí el proxy/streaming del Sprint 3.

## Comentarios y estados de conexión

Los comentarios entrantes se presentan en Canales y admiten respuestas públicas encoladas. Instagram permite además una respuesta privada al comentario, sujeta a los permisos y reglas del proveedor. TikTok conserva los eventos `comment.update`, incluyendo tombstones y orden por timestamp para borrados/ocultamientos; vuelve a comprobar visibilidad antes de despachar una respuesta. Un registro existente no se convierte en comentario público por recibir tardíamente una inserción antigua.

Guardar no declara conexión. Validar confirma acceso al recurso, la suscripción confirmada deja `awaiting_webhook`, y un evento firmado del recurso confirma `connected`. Las capacidades registran evidencias por separado; una identidad consultable o una suscripción no acreditan envío ni entrega. El flujo Meta requiere registrar también el callback y sus campos en Meta for Developers. TikTok requiere su producto Business Messaging autorizado; Login Kit no concede este acceso.

## Evidencia y límites

El runtime existente se actualizó con la dependencia criptográfica y mantuvo el proyecto Compose, puerto `127.0.0.1:4173`, montajes del mismo código, certificado SQL y volumen IA. La lectura SQL posterior a las migraciones confirmó las ocho tablas, las cinco columnas con BIN2 y la huella core conservada. La consulta HTTP real devolvió los cinco perfiles sin configurar y colas vacías. El navegador real mostró los cinco botones habilitados y los formularios, sin el acordeón de contratos. El catálogo/OpenAPI se regeneró desde las fuentes.

Por instrucción del propietario no se escribieron ni ejecutaron tests, lint, typecheck, comprobaciones de build o pruebas de carga. El formateo solo normalizó fuentes. No se introdujeron credenciales ficticias, contactos de prueba ni mensajes de demostración. No se enviaron mensajes ni se conectaron cuentas remotas: faltan los datos reales ingresados por el propietario, permisos/revisión de cada plataforma y un callback HTTPS público accesible. No se acredita operación con proveedores ni entrega real hasta completar esos pasos desde la aplicación.

## Referencias oficiales utilizadas

- [WhatsApp Cloud API, colección oficial de Meta](https://www.postman.com/meta/whatsapp-business-platform/documentation/wlk6lh4/whatsapp-cloud-api).
- [Messenger Platform, colección oficial de Meta](https://www.postman.com/meta/messenger-platform-api/documentation/iyp204x/messenger-platform-api).
- [Instagram API, colección oficial de Meta](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api).
- [TikTok Business: firma de webhooks](https://business-api.tiktok.com/portal/docs/webhook-verification/v1.3), [envío a conversaciones](https://business-api.tiktok.com/portal/docs/send-a-message-to-a-conversation/v1.3) y [eventos de comentarios](https://business-api.tiktok.com/portal/docs/comment-update-event/v1.3).
