# SQL-C10 · Contrato de Canales para SQL Server 2019

Fecha: 25 de octubre de 2026, America/Bogota. Estado: definición versionada y revisable; no es DDL implementado, compilación SQL, aceptación de proveedores o implementación visual. El alcance pedido es definir el contrato. No se conecta SQL, no se modifica SIIE/C5/C9 y no se activan rutas públicas, workers o credenciales.

## Objetivo y referencia obligatoria

Canales debe conservar **todos los campos, acciones, validaciones observadas, estados y condiciones de visibilidad de Scentra**, con el estilo CBN ya aprobado y persistencia SQL Server. Incluye tokens, secretos, contraseña de confirmación, selección/sincronización de número, PIN, registro/verificación, OAuth, activos, diagnóstico, TikTok y Webhooks. No basta una lista de proveedores o un formulario reducido de diez campos. Los controles deshabilitados del ensayo C9 no acreditan esas funciones.

La referencia vinculante es la [matriz campo por campo](SQL_C10_FIELD_MATRIX.md) y su [contrato JSON](channels-ui-parity-contract.json): conserva etiquetas, claves, tipos, opciones y condiciones HTML/JS de la fuente. Se inventariaron 115 contextos de campos/salidas y 83 instancias de acciones, incluidos controles y botones compartidos. No son 198 funciones distintas. Cada control tiene un destino SQL, un DTO, un cálculo de lectura o un uso transitorio definido; cada acción tiene ruta/DTO o comportamiento local. No se inventan inputs para salidas de lectura.

Orden: **Meta WhatsApp Cloud → Verificar número WhatsApp → Instagram Business → Facebook Messenger → TikTok → Webhooks**. Los formularios y modales de secretos se conservan. Provider/channel fijos no pasan a ser editables; PIN y contraseña usan password; los valores existentes se muestran mediante presencia/pista y no se rellenan con plaintext. Verify token es una salida generada/copiar una vez, distinta del token permanente de WhatsApp. Las cuotas técnicas TikTok se conservan; Stripe, planes, cobros y comercio siguen excluidos.

**Corrección de la inferencia C9:** la UI Scentra enumera tarjetas y números, pero `001_saas_core.sql:53` y `integrations/router.py:1006` imponen una integración por tenant/proveedor/canal. No se comprobó multicuenta Meta WhatsApp en ese backend. La petición humana SQL-C10 sí exige varias cuentas: se define como ampliación explícita CBN, sin reescribir la evidencia cerrada C9. Varios números WABA o varias Pages descubiertas tampoco equivalen por sí solos a varias integraciones.

## Modelo versionado y ámbito institucional

El [modelo estructurado](channels-parity-contract.json) propone **24 tablas nuevas en `crm_channels2`**, sin alterar las 65 existentes: 50 académicas, siete foundation y ocho B011. La partición propuesta final es exactamente 89 tablas, con nombres y catálogo completos; objetos desconocidos, colisiones o visibilidad incompleta bloquean la preparación. Es una propuesta, no un conteo observado en SQL.

| Área | Tablas propuestas | Responsabilidad |
|---|---|---|
| Identidad y configuración | Context, Application, Integration, Audit | Una institución revisada por copia; aplicaciones/perfiles OAuth y conexiones identificadas por UUID, auditoría sin secretos |
| OAuth y credenciales | OAuthSession, SecretVersion, ProviderAsset, ProviderOperation | Estados un uso; versiones cifradas; snapshots de activos por sesión/operación; diario de efectos externos |
| TikTok y límites | TikTokPolicy, VerificationEvidence, QuotaBucket, QuotaReservation | Todos los campos operativos, evidencia separada de declaraciones y reservas concurrentes |
| Recepción | WebhookEndpoint, EndpointIntegration, WebhookReceipt, WebhookEvent | Endpoint por aplicación, rutas explícitas, envelope autenticado durable y eventos por subelemento |
| Inbox/B015 y transición | ConversationProfile, ConversationControl, ExternalIdentity, ExternalMessage, SocialComment, SendJob, MessageRoute, LegacyBinding | Identidades y mensajes por cuenta; control humano/epoch; correspondencia exacta con datos heredados |

`InstitutionId` queda ligado a un único Context revisado, no a estudiantes ni a una nueva empresa SaaS. Las únicas referencias fuera del esquema nuevo son las claves CRM ya existentes de Contact, Conversation y Message; no hay FK, trigger o DML contra tablas académicas. La autoridad de estudiantes, oferta, precios y matrículas sigue SIIE.

Cada conexión tiene `IntegrationId`; cada aplicación tiene `ApplicationId` y perfil/issuer explícito. Un mismo Client ID puede tener perfiles IG/Facebook distintos, sin herencia implícita de credenciales. Una aplicación puede servir varias conexiones. WhatsApp permite una conexión por Phone Number ID y varias conexiones bajo un WABA. Todas las operaciones seleccionan el ID concreto. Una búsqueda por canal con más de un resultado devuelve ambigüedad; nunca selecciona el primero o el más reciente.

Los IDs externos usan comparación BIN2 exacta; las identidades y mensajes se deduplican por institución+integración+ID externo. Los cambios de identidad/aplicación con historia requieren una transición de correspondencias revisada y conservadora; PATCH no reasigna silenciosamente mensajes, tokens o conversaciones. La API informa el conflicto en lugar de perder historia.

## Compatibilidad SQL Server 2019

Objetivo institucional: motor 15 y compatibilidad150, con TLS validado, identidad de destino y principal específicos. El SQL2022 Express/160 usado en C9 no certifica este objetivo. El perfil de ensayo futuro debe separar explícitamente ambos casos; no se debilita el contrato institucional ni se reutiliza el ticket C9.

UUID → uniqueidentifier; JSONB → nvarchar(max) con ISJSON y DTO estricto; boolean → bit; timestamps de negocio → datetime2(7) UTC; bytes cifrados → varbinary. El control optimista usa rowversion como ETag opaco, sin tratarlo como fecha. UPDATE/INSERT parametrizado con bloqueos de clave y unicidad sustituye ON CONFLICT; OUTPUT sustituye RETURNING. No se depende de MERGE, JSON nativo/índices JSON recientes, SQLCLR o funciones posteriores a 2019.

El comprobador calcula el ancho máximo de claves y exige un techo conservador de 900 bytes. Las claves opcionales usan índices únicos filtrados; no se copia la semántica PostgreSQL de múltiples NULL sobre UNIQUE sin traducirla. Las FK deben apuntar a PK/UQ no filtradas compatibles y conservar institución/aplicación/cuenta/operación. Los campos JSON no contienen secretos.

Referencias verificadas: [JSON en SQL Server](https://learn.microsoft.com/en-us/sql/relational-databases/json/json-data-sql-server?view=sql-server-ver15), [rowversion](https://learn.microsoft.com/en-us/sql/t-sql/data-types/rowversion-transact-sql?view=sql-server-ver15), [CREATE INDEX](https://learn.microsoft.com/en-us/sql/t-sql/statements/create-index-transact-sql?view=sql-server-ver15). Son criterios de diseño; no se ha compilado ni ejecutado el DDL en 2019.

## Campos, DTO y permisos de edición

La API futura v2 mantiene las claves de formulario Scentra mediante la matriz, con DTO de entrada estricto, operación UUID y versión esperada. Se separan configuración solicitada y estado verificado: elegir Connected no demuestra conexión, firma o entrega. Campos derivados como diagnóstico, last_seen, scopes observados, hints y evidencia no se convierten en propiedades editables de masa.

Los formularios preservan Phone Number ID, WABA ID, App ID, Graph API, secretos/tokens, Pages/Business IDs/nombres/portfolio, Client Key/Open ID/Advertiser ID/scopes y todos los campos TikTok. Configured scopes, approved scopes y app review Meta también se conservan como datos distintos de los scopes observados en activos. La API no descarta campos desconocidos silenciosamente: los rechaza y conserva el borrador.

GET sólo consulta. La fuente normaliza/cifra al listar y suscribe WABA al sincronizar números mediante GET; esas escrituras se separan en acciones POST explícitas. Se mantienen Refrescar, Guardar, OAuth/Conectar, cargar activos, diagnósticos, Renovar token, registrar/verificar, rotar y procesar; sus efectos dejan de esconderse en lecturas.

El actor procede de la autoridad de autenticación/roles P2, con ámbito institucional y autorización por objeto. La confirmación mediante contraseña para sustituir secretos existentes conserva su flujo Scentra. PIN, OTP, contraseña y authorization code son request-only: ni SQL, caché, logs ni respuesta los conservan. Hasta aceptar P2, las capacidades operativas permanecen bloqueadas.

## OAuth, páginas y renovación

Inicio autenticado: fijar institución, aplicación/issuer, actor y sesión de navegador, redirect URI exacta, versión de aplicación y versión exacta del secreto cliente. El ámbito se fija en servidor: crear conexiones con rol institucional, o una integración existente concreta. Guardar únicamente hash de state aleatorio de 32 bytes; TTL por defecto diez minutos y máximo treinta. Callback comprueba expiración, binding y estado antes de reclamarlo atómicamente. El claim y la intención de canje se confirman antes del HTTP; no se mantiene una transacción SQL durante el proveedor.

PKCE S256 se exige cuando el perfil verificado del proveedor lo soporta. No se supone soporte por tener un parámetro, ni se degrada en silencio: un cliente confidencial sin PKCE exige el perfil/secret/state/binding revisado antes de activarse. Issuer y callback se ligan explícitamente; no hay redirect abierto. Se adoptan las medidas aplicables de [RFC 9700](https://www.rfc-editor.org/rfc/rfc9700.html), con aceptación específica del proveedor todavía pendiente.

Los activos descubiertos son snapshots inmutables por operación/sesión y actor. Cada Page puede tener un token provisional distinto, cifrado con owner AssetId y ligado a esa sesión; no se guarda en Metadata ni se comparte un catálogo mutable de permisos entre usuarios. Connect sólo admite el activo del grant y ámbito correctos, revalida permisos y promueve la credencial seleccionada al owner definitivo con nuevo AAD. El canje de state/code es de un uso; el grant expirable puede conectar explícitamente varios activos mediante operaciones idempotentes separadas, conservando las acciones Usar Instagram/Usar Facebook de la fuente. Un grant ligado a una cuenta existente no puede ampliarse para crear otras.

Un callback no reemplaza todo el JSON de política: mezcla sólo resultados autorizados y conserva cuotas, flags, scopes declarados y notas. La renovación tiene endpoint/operación propios, exclusión por cuenta y versión pinneada; una respuesta sin refresh token nuevo conserva el anterior. Se audita la rotación sin registrar valores. Un canje/refresh con resultado desconocido pasa a uncertain: no se vuelve a usar ciegamente el código o refresh token anterior.

Rotar un secreto de aplicación incrementa su versión e invalida atómicamente sesiones pendientes que lo pinneaban; una operación ya en vuelo exige reconciliación. Las etiquetas Meta/Instagram/Facebook App Secret pueden apuntar al secreto canónico de una misma aplicación/perfil explícitamente elegido; eso no autoriza fallback entre aplicaciones/issuers, plaintext legacy, clave JWT o clave de desarrollo.

## Secretos y verificación del número

SecretVersion contiene exactamente un owner: aplicación, integración, endpoint, sesión OAuth o asset provisional. Cada owner+kind+VersionNo es único y sólo hay una versión activa por owner+kind. AES-256-GCM usa nonce12 y tag16, clave externa versionada y AAD con institución, tipo/UUID del owner, kind y versiones. Faltan clave/etiqueta/versión: se bloquea, sin regenerar una clave para datos existentes.

La interfaz muestra password vacío para escribir, presencia/hint al editar y opciones explícitas de reemplazar/revocar. Omitir o enviar vacío conserva. Crear/rotar endpoint devuelve el valor nuevo una sola vez con no-store; si se pierde la respuesta se consulta metadata y se rota explícitamente, sin redisplay del secreto almacenado. El Verify token generado nunca sustituye el token permanente ni autentica un POST Meta.

El secreto HMAC generado para un endpoint/bridge no es un Meta App Secret ni un TikTok Client Secret generado localmente. El perfil directo del proveedor usa su secreto pinneado; un bridge requiere perfil explícito y no se presenta como evidencia directa del proveedor.

Sincronizar números guarda activos observados de WABA y cuenta seleccionados. Registrar/verificar valida un PIN decimal de seis dígitos, deja intención durable, llama al proveedor sin bloqueo SQL y confirma/declara incertidumbre por operación. El PIN no se transforma en una credencial persistida. Se conservan selector, PIN, botones, resultado y errores del flujo original.

## TikTok, modos y cuotas

Se conservan todos los campos y siete casillas de la fuente: revisión/productos/scopes, eventos validados declarados, Business Messaging, comentarios, IA, agentes, activadores y remarketing; además modo, rollout, cuotas, base/version/rutas API, alias de token y notas. App review notes admite2000 caracteres y runtime notes1200, conforme a la normalización observada. La casilla de eventos expresa una declaración del operador; no fabrica evidencia firmada.

| Modo | Efecto permitido |
|---|---|
| disabled | Ningún envío externo |
| shadow | Evaluar sin enviar |
| stub | Datos sintéticos, sin acreditar proveedor |
| manual | Acción humana explícita más todas las validaciones de cuenta, revisión, permisos, evidencia, cuota y epoch |
| live | Lo anterior, rollout estable y flags concretos; revalidación justo antes de enviar |

Defaults: disabled, rollout0 y flagsfalse. La cuota0 conserva el significado Scentra de sin límite, pero no habilita un modo. Se reserva de forma atómica por integración+día UTC+acción: mensajes y respuestas a comentarios comparten presupuesto outbound; IA tiene presupuesto adicional. Reserved+Committed decide admisión. La misma operación no consume dos veces. Estado uncertain retiene la reserva hasta reconciliar; no se libera porque expire un lease.

La base API, rutas y alias env conservan sus campos visibles, con destinos operativos de una allowlist revisada en servidor. Se rechazan hosts arbitrarios, redirecciones, credenciales incrustadas y lectura libre de variables de entorno. Diagnóstico OK, last_seen, checkbox o evento stub no equivalen a firma, permisos ni entrega real.

Las salidas de identidad/modo y los recursos configurados leen Integration/Application; las pistas y el modal leen la versión activa del secreto con su propietario/kind exactos. Los recursos inferidos conservan la etiqueta de observación sin verificar. «Eventos reales» conserva la ventana fuente de doce recibos crudos, sin contar subeventos como recibos adicionales ni usar el conteo como prueba de firma. Los contadores de prospectos B013 y de errores abiertos con triage/cierre conservan su campo visual, pero devuelven disponibilidad ausente hasta sus contratos específicos; no se inventa cero ni se equipara cualquier fallo con un dead letter abierto.

## Webhooks, rutas y procedencia

Un endpoint pertenece a una aplicación y puede enrutar varias integraciones mediante EndpointIntegration. El selector educativo conserva WhatsApp/Meta/Instagram/Facebook/TikTok; se traduce a familia de proveedor y ChannelSelector. No se presupone endpoint→única cuenta. El secreto se resuelve por el perfil/versión pinneados, sin recorrer las primeras integraciones recientes.

Recepción: limitar raw body a1MB → verificar firma sobre bytes originales → persistir envelope cifrado y metadata de autenticación → COMMIT → ACK. No hay CRM, IA o envío antes del commit. Reintentar el ACK reconcilia endpoint+digest. Se normalizan todos los subeventos de cada lote con ReceiptId, ruta, aplicación e integración; IDs ambiguos/desconocidos quedan en cuarentena.

Se deduplica la recepción por institución+endpoint+digest y el evento por institución+integración+clave de normalización. Estados de entrega del mismo MessageId son eventos distintos por su estado/tiempo, y progresan sin retroceder. Identidad débil por falta de ID estable no habilita efectos irreversibles. Las FK compuestas y las comprobaciones de servidor ligan Event→Receipt→Endpoint→Application→binding/Integration; una fila válida de otra cuenta no basta.

Un endpoint público real nace inactivo y exige firma. Se conserva la casilla HMAC y las acciones originales, pero una transición que permita recepción unsigned se rechaza explícitamente. Meta usa raw HMAC del app secret; TikTok usa el perfil timestamp+raw revisado y ventana300s. No se copian tolerancias unsigned o raw-only de la fuente. La disponibilidad real de cada perfil, scopes y versiones se comprobará con documentación primaria y fixtures reales en su etapa; no se certifica en C10.

No se guardan Authorization, cookies, tokens ni headers de firma en headers_json. El recibo identifica el SecretId/version exactos que autenticaron, versión de endpoint y timestamp; la versión AES por sí sola no identifica el secreto de firma. El raw cifrado usa otro dominio de clave/AAD. La purga propuesta sólo elimina el cuerpo de recibos terminales sin lease, marca BodyPurgedAt y conserva tombstone/dedupe; no se ejecuta limpieza en esta unidad.

SignatureVerifiedAt admite NULL para importaciones legacy sin firma; los CHECK exigen secreto/fecha cuando Authentication sea verificada y fecha NULL cuando sea legacy_unverified. La unicidad de clave/nonce del cuerpo usa un índice filtrado por ambos valores no NULL: SQL Server permite conservar varios tombstones purgados sin colisión de UNIQUE(NULL,NULL). Las columnas de rutas externas en ambos extremos de la FK declaran BIN2 idéntico.

Eliminar endpoint es desactivar lógicamente; no borra recibos, rutas o auditoría en cascada. Rotar token/firma es distinto de actualizar metadata y requiere revisión/idempotencia. Last seen y challenge verificado son señales separadas de autenticación POST y entrega real.

## B015, efectos externos y permisos

CBN-CHP005 define equivalentes versionados de ConversationProfile, ConversationControl y MessageRoute, además de identidades/jobs. No se ejecuta el 015 histórico. MessageRoute conserva IntegrationId, IdentityId, MessageId, QueueId y epoch; las FK impiden usar queue/comment/reserva/operación de otra cuenta. Se verifica Message.ConversationId=Identity.ConversationId y el contacto canónico bajo bloqueo. El control de conversación debe existir; no se inventa epoch0. El bot revalida el epoch actual inmediatamente antes del envío.

ProviderOperation registra intención, target, actor, digest y EffectKey semántica antes del HTTP. Un nuevo UUID, otro worker o un lease vencido no eluden un efecto pendiente/desconocido sobre el mismo target/generación. Las finalizaciones exigen fencing. Fallos o éxitos desconocidos se guardan saneados en una transacción de resultado; no se supone que un UPDATE seguido de excepción dentro de rollback dejó diagnóstico durable.

Se definen principales independientes para migrador, UI, broker de secretos, ingress y transporte. Ninguno recibe CONTROL/db_owner ni permisos académicos. UI sólo ve metadata segura; ingress no escribe CRM; transporte sólo obtiene el DML canónico imprescindible después de su aceptación. La matriz exacta de GRANT/DENY, permisos efectivos y visibilidad completa de catálogo debe implementarse y ensayarse antes de montar perfiles. No se conceden derechos por definir este documento.

## Secuencia, drift, reversión y aceptación

Cinco unidades nuevas, IDs y hashes nuevos; no se reutiliza CBN-B011 ya confirmado. Cada unidad crea primero sus tablas y después sus FK dentro de una transacción; el ciclo deliberado OAuthSession↔SecretVersion se resuelve en ese segundo pase, no debilitando referencias.

1. CBN-CHP001: contexto, aplicaciones, integraciones y auditoría.
2. CBN-CHP002: sesiones, endpoints, operaciones, activos y versiones de secretos.
3. CBN-CHP003: política TikTok, buckets y reservas.
4. CBN-CHP004: bindings, recibos, subeventos y evidencia.
5. CBN-CHP005: metadata Inbox/B015, identidades/mensajes/comentarios/jobs/rutas y correspondencias heredadas.

Ensayo futuro: backup COPY_ONLY/CHECKSUM, VERIFYONLY, copia independiente sin REPLACE, CHECKDB, captura completa de catálogo/datos y perfiles/tickets nuevos. Se conservan las siete entradas originales del diario byte por byte; STARTED durable, COMMITTED con DDL y reconciliación de COMMIT incierto preceden a cualquier repetición. Drift incluye tablas, columnas, tipos, constraints, índices/filtros, FK, propietarios, ACL/roles/permisos efectivos, metadatos/journal y keyring revisado; desconocidos o visibilidad parcial bloquean.

Cada fila de las ocho tablas B011 requiere correspondencia explícita y hashes de origen/destino. La credencial v1 debe descifrarse con la clave verificada y recifrarse con owner/integración/AAD nuevos; no se copia el ciphertext como si el AAD fuera compatible. Clave ausente o identidad ambigua bloquean promoción. Los recibos históricos sin firma reproducible se conservan como legacy_unverified/cuarentena, sin fabricar evidencia real. No se alteran Contact/Conversation/Message ni datos académicos para facilitar el mapeo.

Reversión: detener sólo la composición nueva y sus leases/recepción; conservar auditoría/recibos/mappings; mantener C5 y C9 sobre sus bases/perfiles intactos. Si hace falta, recuperar la copia independiente del backup previo. No se ejecuta DROP/reset/reasignación contra SIIE, foundation o B011. Un éxito remoto no se deshace mediante rollback SQL.

La definición se acepta con comprobador offline positivo/negativo, inventario completo de controles, revisión semántica independiente, huellas y enlaces/grafos consistentes. **No acredita SQL2019 compilado, pantallas implementadas, OAuth real, números registrados ni mensajes entregados.** SQL-C11 propuesto implementará y ensayará el release en otra restauración; autenticación P2, UI completa y activación de proveedores mantienen sus puertas de aceptación.

Evidencia: [modelo](channels-parity-contract.json), [matriz](SQL_C10_FIELD_MATRIX.md), [validación](sql_c10_validation.json), [revisión](SQL_C10_REVIEW.md), [progreso por fases](../../../tasks/sql-c10-progress.json), [ADR-022](../../decisions/ADR-022-channels-parity-contract.md).
