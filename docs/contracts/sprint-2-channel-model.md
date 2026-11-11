# Sprint 2 — modelo SQL Server y verificación de webhooks

**Estado vigente, 2026-10-20:** la implementación aplicada se describe en [Canales operativos](../reports/channels-sprint-2-local.md), con ocho tablas reales, migraciones 011/012, configuración cifrada desde la UI y recepción/ingesta/despacho. Las secciones del primer corte que siguen son históricas; el diseño SQL de nueve tablas es una propuesta y no representa literalmente el esquema aplicado. Las cuentas remotas siguen pendientes de las credenciales, permisos y callback público del propietario.

Fecha histórica: 2026-10-19, America/Bogota. **Primer corte local para revisión.** En ese corte solo estaba implementado el GET de verificación Meta. El SQL siguiente sigue como propuesta histórica; no se ejecutó literalmente. WooCommerce está excluido.

## Contrato HTTP del primer corte

| Ruta | Estado y resultado |
|---|---|
| `GET /api/v1/webhooks/meta` | Implementado: `hub.mode=subscribe`, `hub.verify_token` y `hub.challenge`. Compara SHA-256 del token mediante comparación constante con `CRM_META_VERIFY_TOKEN_SHA256`. Retorna exactamente el challenge no vacío, `text/plain`, 200. |
| `POST /api/v1/webhooks/meta` | Pendiente: no devuelve ACK 200. Debe verificar `X-Hub-Signature-256` sobre bytes originales, guardar recibo durable y solo entonces confirmar. |
| `POST /api/v1/webhooks/tiktok` | Conserva contrato sintético 501 para cuerpos sintéticos válidos, 422 para cuerpos inválidos. No ingiere ni confirma eventos reales. |
| `/api/v1/channels` y configuración por canal | Conservan contratos sintéticos 501. Guardado cifrado y permisos reales pendientes; el guard local existente no equivale a RBAC. |

GET exige exactamente una aparición de cada parámetro, sin campos adicionales. Longitudes máximas: modo 20, token 4096 y challenge 4096 caracteres. Query faltante, vacía, duplicada o excesiva: 422 constante; modo/token incorrectos: 403 constante; hash backend vacío o inválido: 503 constante. Ningún error refleja las entradas. Las respuestas llevan `Cache-Control: no-store`. Solo el challenge correcto se devuelve por contrato; no se conserva.

La configuración guarda únicamente el hash hexadecimal SHA-256 de 32 bytes, sin token en claro. El operador genera un token aleatorio robusto y conserva su valor en el gestor seguro para registrarlo en Meta for Developers; el hash no vuelve seguro un token débil. La app lee la configuración al crear el proceso. Un filtro idempotente elimina toda la query de esta ruta de los registros estándar `uvicorn.access`; preserva método, path y estado. No copiar tokens, hashes reales o URLs completas de callback con query a chat, Git, logs, APM ni informes. Mantener `--no-access-log` (como en README) y redactar query en cualquier proxy/telemetría antes de exposición: el filtro de la app no controla logs externos. Este corte no publica callback HTTPS ni cambia procesos existentes.

[Referencia oficial Meta del challenge y firma](https://whatsapp.github.io/WhatsApp-Nodejs-SDK/api-reference/webhooks/start/). La recepción validará además tamaño, producto, cuenta y pertenencia; un GET correcto no prueba permisos, suscripción activa ni conectividad real.

## Modelo aditivo propuesto

Se propone `crm_channels`: la huella vigente de `crm` cubre todos sus objetos; agregar tablas allí invalidaría `SqlWorkspace.verify_target` y sus escritores. Se preservan `crm.Contact`, `crm.Conversation` y `crm.Message`, sus UUID y las huellas existentes. No se crea otra tabla de personas `prospects`. Las identidades externas se vinculan al contacto CRM, nunca automáticamente a estudiantes/aspirantes core por teléfono.

El SQL siguiente muestra forma y restricciones para discutir el contrato. **NO ejecutar:** la migración posterior necesita guard de destino, versión/huella, colisiones, índices completos, backup/restauración/ensayo y aceptación por capas. No incluye `CREATE SCHEMA`, permisos ni ejecutor. Cada `CREATE TABLE` asume ese esquema aislado aún no creado.

```sql
CREATE TABLE crm_channels.ProviderApp (
    ProviderAppId uniqueidentifier NOT NULL PRIMARY KEY,
    Provider varchar(10) NOT NULL CHECK (Provider IN ('meta','tiktok')),
    ExternalAppId nvarchar(128) COLLATE Latin1_General_100_BIN2 NOT NULL,
    Enabled bit NOT NULL DEFAULT 0,
    UNIQUE (Provider, ExternalAppId)
);

CREATE TABLE crm_channels.Account (
    AccountId uniqueidentifier NOT NULL PRIMARY KEY,
    ProviderAppId uniqueidentifier NOT NULL REFERENCES crm_channels.ProviderApp(ProviderAppId),
    Channel varchar(12) NOT NULL CHECK (Channel IN ('whatsapp','instagram','messenger','facebook','tiktok')),
    ExternalAccountId nvarchar(128) COLLATE Latin1_General_100_BIN2 NOT NULL,
    WabaId nvarchar(128) COLLATE Latin1_General_100_BIN2 NULL,
    PhoneNumberId nvarchar(128) COLLATE Latin1_General_100_BIN2 NULL,
    ConfigurationJson nvarchar(max) NOT NULL CHECK (ISJSON(ConfigurationJson)=1),
    Enabled bit NOT NULL DEFAULT 0,
    UNIQUE (ProviderAppId, Channel, ExternalAccountId)
);

CREATE TABLE crm_channels.Credential (
    CredentialId uniqueidentifier NOT NULL PRIMARY KEY,
    ProviderAppId uniqueidentifier NOT NULL REFERENCES crm_channels.ProviderApp(ProviderAppId),
    AccountId uniqueidentifier NULL REFERENCES crm_channels.Account(AccountId),
    SecretKind varchar(32) NOT NULL,
    KeyId varchar(64) COLLATE Latin1_General_100_BIN2 NOT NULL,
    Nonce binary(12) NOT NULL,
    CiphertextAndTag varbinary(max) NOT NULL CHECK (DATALENGTH(CiphertextAndTag)>=16),
    CreatedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
    UNIQUE (KeyId, Nonce)
);

CREATE TABLE crm_channels.ExternalIdentity (
    IdentityId uniqueidentifier NOT NULL PRIMARY KEY,
    AccountId uniqueidentifier NOT NULL REFERENCES crm_channels.Account(AccountId),
    ExternalUserId nvarchar(128) COLLATE Latin1_General_100_BIN2 NOT NULL,
    ContactId uniqueidentifier NOT NULL REFERENCES crm.Contact(ContactId),
    UNIQUE (AccountId, ExternalUserId)
);

CREATE TABLE crm_channels.webhook_events (
    WebhookEventId uniqueidentifier NOT NULL PRIMARY KEY,
    ProviderAppId uniqueidentifier NOT NULL REFERENCES crm_channels.ProviderApp(ProviderAppId),
    RawPayload nvarchar(max) NOT NULL CHECK (ISJSON(RawPayload)=1),
    RawBodyHash binary(32) NOT NULL,
    ReceivedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
    State varchar(12) NOT NULL DEFAULT 'queued' CHECK (State IN ('queued','leased','processed','failed')),
    Attempts int NOT NULL DEFAULT 0 CHECK (Attempts>=0),
    NextAttemptAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
    LeaseToken uniqueidentifier NULL,
    LeaseUntil datetime2(7) NULL,
    ErrorCode varchar(64) NULL,
    CHECK ((State='leased' AND LeaseToken IS NOT NULL AND LeaseUntil IS NOT NULL)
        OR (State<>'leased' AND LeaseToken IS NULL AND LeaseUntil IS NULL))
);

CREATE TABLE crm_channels.NormalizedEvent (
    NormalizedEventId uniqueidentifier NOT NULL PRIMARY KEY,
    WebhookEventId uniqueidentifier NOT NULL REFERENCES crm_channels.webhook_events(WebhookEventId),
    AccountId uniqueidentifier NOT NULL REFERENCES crm_channels.Account(AccountId),
    EventKind varchar(32) COLLATE Latin1_General_100_BIN2 NOT NULL,
    ExternalEventKey nvarchar(200) COLLATE Latin1_General_100_BIN2 NOT NULL,
    MessageId uniqueidentifier NULL REFERENCES crm.Message(MessageId),
    OccurredAt datetime2(7) NULL,
    UNIQUE (AccountId, EventKind, ExternalEventKey)
);

CREATE TABLE crm_channels.ExternalMessage (
    AccountId uniqueidentifier NOT NULL REFERENCES crm_channels.Account(AccountId),
    ExternalMessageId nvarchar(200) COLLATE Latin1_General_100_BIN2 NOT NULL,
    MessageId uniqueidentifier NOT NULL REFERENCES crm.Message(MessageId),
    PRIMARY KEY (AccountId, ExternalMessageId)
);

CREATE TABLE crm_channels.outbound_queue (
    OutboundId uniqueidentifier NOT NULL PRIMARY KEY,
    OperationId uniqueidentifier NOT NULL UNIQUE,
    AccountId uniqueidentifier NOT NULL REFERENCES crm_channels.Account(AccountId),
    ConversationId uniqueidentifier NULL REFERENCES crm.Conversation(ConversationId),
    MessageId uniqueidentifier NULL REFERENCES crm.Message(MessageId),
    RecipientId nvarchar(128) COLLATE Latin1_General_100_BIN2 NOT NULL,
    OperationKind varchar(24) NOT NULL CHECK (OperationKind IN ('direct_message','public_reply','private_invitation')),
    Payload nvarchar(max) NOT NULL CHECK (ISJSON(Payload)=1),
    PayloadHash binary(32) NOT NULL,
    State varchar(12) NOT NULL DEFAULT 'queued'
        CHECK (State IN ('queued','leased','sent','delivered','read','failed','uncertain')),
    Attempts int NOT NULL DEFAULT 0 CHECK (Attempts>=0),
    NextAttemptAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
    LeaseToken uniqueidentifier NULL,
    LeaseUntil datetime2(7) NULL,
    ExternalMessageId nvarchar(200) COLLATE Latin1_General_100_BIN2 NULL,
    CreatedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
    ErrorCode varchar(64) NULL,
    CHECK ((State='leased' AND LeaseToken IS NOT NULL AND LeaseUntil IS NOT NULL)
        OR (State<>'leased' AND LeaseToken IS NULL AND LeaseUntil IS NULL))
);

CREATE TABLE crm_channels.social_comments (
    SocialCommentId uniqueidentifier NOT NULL PRIMARY KEY,
    AccountId uniqueidentifier NOT NULL REFERENCES crm_channels.Account(AccountId),
    ExternalCommentId nvarchar(200) COLLATE Latin1_General_100_BIN2 NOT NULL,
    ExternalPostId nvarchar(200) COLLATE Latin1_General_100_BIN2 NOT NULL,
    ExternalAuthorId nvarchar(128) COLLATE Latin1_General_100_BIN2 NULL,
    ContactId uniqueidentifier NULL REFERENCES crm.Contact(ContactId),
    Payload nvarchar(max) NOT NULL CHECK (ISJSON(Payload)=1),
    ReceivedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
    UNIQUE (AccountId, ExternalCommentId)
);
```

`ISJSON` comprueba sintaxis, no estructura ni límites: el adaptador validará esquema/tamaño, sin SQL libre. Las claves externas usan comparación binaria y límites de longitud; la mayor clave única propuesta ocupa como máximo 448 bytes, bajo el límite conservador de 900 bytes. No indexar JSON/MAX. Antes de aceptar el contrato se definen índices acotados de reclamación por estado/fecha/ID y de leases expirados, y validación de IDs vacíos/sobrelongitud. [SQL Server ISJSON](https://learn.microsoft.com/en-us/sql/t-sql/functions/isjson-transact-sql?view=sql-server-ver16).

Una app Meta puede entregar varios recursos/canales en el mismo POST: el recibo pertenece a `ProviderApp`, sin exigir prospecto, cuenta o conversación antes de normalizar. El hash sirve como integridad/diagnóstico; no elimina eventos por texto. `NormalizedEvent` deduplica efectos por cuenta, tipo e identidad real del evento; los estados sent/delivered/read del mismo mensaje deben conservar claves diferenciadas. `ExternalMessage` evita insertar otra vez el mismo mensaje externo. No inventar un ID a partir del texto si el producto carece de identificador: falta definir su clave oficial y reconciliación.

`Credential` es **solo modelo** del sobre AES-256-GCM: llave aleatoria de 32 bytes fuera de SQL/Git, nonce aleatorio de 12 bytes nuevo en cada cifrado, ciphertext con tag de 16 bytes, KeyId para rotación y AAD canónica vinculada a ProviderAppId, AccountId o marcador de app y SecretKind. La restricción evita repetir nonce por llave; no sustituye generación criptográfica. El escritor deberá verificar que cuenta y app corresponden y rechazar intercambios por AAD. App Secret de firma, access tokens y secretos TikTok se cifran; nunca entran en JSON de configuración. El verify token Meta de este corte conserva solo digest en entorno. [Contrato AESGCM](https://cryptography.io/en/stable/hazmat/primitives/aead/). `cryptography` no está declarado actualmente: no se agregó dependencia por un modelo inactivo. No existe `referencia_scentra/shared/secrets.py` extraído en este checkout; los ZIP son referencia, no código ejecutado.

## Procesamiento y aceptación pendientes

POST confirmará HTTP 200 después del commit del recibo autenticado; fallo de firma no recibe ACK y fallo SQL debe permitir reintento del proveedor, nunca simular recepción. El objetivo <1 segundo necesita medición SQL/carga/reintentos: el workspace actual espera hasta cinco segundos por su bloqueo global y no puede reutilizarse sin medir/separar ese camino. No procesar identidad, descargar media ni llamar proveedores en la petición.

Ingesta debe reservar con lease SQL, normalizar cada elemento y confirmar efecto + deduplicación + progreso atómicamente; leases obsoletos no pueden completar. Cuenta/identidad externa no fusionan personas automáticamente. El contrato actual permite un hilo local por contacto; ampliar a conversaciones por canal exige una migración de preservación independiente. Las nuevas escrituras deben conservar diarios y consumidores R3A/R4.

Despacho debe reclamar filas SQL, aplicar backoff acotado con jitter, validar cuenta/consentimiento/ventana/control humano y enviar fuera de transacción. Timeout posterior al envío o caída antes de confirmar se marca `uncertain` y se reconcilia antes de repetir; `failed` no implica que el proveedor nunca recibió el mensaje. Actualizaciones de entrega tardías no degradan read a delivered/sent. Público y DM son operaciones distintas con permisos propios, siempre en cola. Las retenciones, límites de intentos y política de reintento son contrato pendiente; no hay defaults operativos aprobados en este SQL.

[TikTok Developer: firma, timestamp y bytes originales](https://developers.tiktok.com/doc/webhooks-verification) y [webhooks/reintentos](https://developers.tiktok.com/doc/webhooks-overview) sirven solo para ese producto. **No prueban el contrato de firma, elegibilidad ni permisos de TikTok Business Messaging**. El [portal Business Messaging](https://business-api.tiktok.com/portal/docs/business-messaging-api-get-started/v1.3) no entregó contenido verificable en esta revisión; no adoptar HMAC Developer como Business por semejanza. DMs/comentarios requieren producto, grants y suscripción reales por separado.

Siguiente unidad: aceptar forma/identidad/cifrado y producto TikTok; preparar migración explícita y recibo durable probado en restauración; implementar POST firmados, después ingesta y despacho con pruebas de duplicados, caídas y recuperación. No escribir core SIIE, activar cuentas, configurar secretos reales, publicar Git o exponer callbacks por este corte.
# Implementación vigente

El modelo operativo aplicado el 2026-10-20 se documenta en [Canales del Sprint 2](../reports/channels-sprint-2-local.md): ocho tablas reales del esquema `crm_channels`, migraciones 011/012 y configuración directa desde la aplicación. El diseño de nueve tablas que sigue se conserva como propuesta de referencia; no describe literalmente el esquema aplicado ni acredita conexiones remotas.

