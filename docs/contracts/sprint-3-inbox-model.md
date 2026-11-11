# Sprint 3 — especificación de Inbox multicanal y medios privados

Fecha original: 2026-10-19, America/Bogota. **PROPUESTA HISTÓRICA; SU DDL Y ROUTERS NO SE EJECUTARON LITERALMENTE.** Los apartados siguientes conservan el diseño y estado de aquel corte, no describen íntegramente el runtime actual. [Contrato anterior](sprint-2-channel-model.md).

**Actualización del 2026-10-20:** la unidad local de Inbox/mini CRM/asignación/control humano está implementada y aceptada sobre `/api/local/crm/inbox`, la conversación padre y los dueños existentes. Usa el esquema real de canales 011/012 y tres extensiones aditivas de 015: ConversationProfile, ConversationControl y MessageRoute. No creó AccountId/ExternalThread ni otro router. [Implementación y límites](../reports/inbox-sprint3-local.md). La unidad posterior de multimedia privada usa **MediaAsset de 016**, vinculado a la conversación/mensaje/identidad existentes; se comprobaron carga y guardado locales, reproducción y descarga privada/Range, sin ejecutar el DDL MediaAsset propuesto abajo. [Aceptación multimedia y límites](../reports/inbox-media-sprint3-local.md). RBAC, grabación real por micrófono y recepción/entrega conectadas siguen pendientes; el diseño restante se conserva como referencia, no como autorización de DDL o implementación automática.

## Límite que debe revisarse primero

`crm.Conversation.ContactId` es único: no se puede crear un segundo registro por contacto para cada canal sin cambiar el contrato vigente. Se propone distinguir **hilo externo** (`thread_id`) de **conversación CRM** (`conversation_id`). `/inbox/conversations/{thread_id}` identificaría un UUID nuevo de `ExternalThread`; incluirá ambos IDs y `state_scope: "conversation"`. Cuenta + ID externo identifican el hilo del proveedor; nunca el teléfono solo. En WhatsApp, si el producto no tiene thread ID independiente, el adaptador define una clave estable documentada por cuenta + identidad externa, sin usar texto de mensajes.

Varios hilos de cuentas distintas pueden apuntar a la misma conversación CRM y contacto. **Consecuencia propuesta, pendiente de aceptación:** prioridad, etapa del contacto, asesor, tareas y takeover se comparten entre esos hilos. Tomar control desde un hilo pausa respuestas bot en todos los hilos de su conversación padre. El detalle debe exponer `affected_thread_ids`; el operador necesita permiso sobre todo ese alcance antes de mutar. No se crea una segunda autoridad de estado por canal. Si se exige control/asesor independiente por canal, este diseño no lo resuelve: primero debe aprobarse una migración de preservación del modelo de conversación, sin `ALTER` implícito ni cambios de huella.

## Qué existe y qué se reutiliza

| Dueño real y evidencia | Reutilización / diferencia propuesta |
|---|---|
| `backend/migrations/001_local_crm.sql:22–58` | Contacto, conversación y mensaje con UUID; `Conversation.ContactId` único; `Message.Body nvarchar(4000)` obligatorio y dirección `incoming/outgoing`. Sin nueva tabla `prospects`. |
| `backend/app/modules/inbox/application/service.py:45–80,202–259,262–349` | Lectura de ficha compartida, paginación e historial existentes. Ruta actual `/api/local/crm/inbox`; canal real presentado como `Local`. Nuevo namespace versionado todavía inexistente. |
| `backend/migrations/003_local_inbox.sql:39–89` | Member/Agent/Assignment/Task/SlaPolicy/Operation. Conservar membresía, asignación y tareas; no duplicarlas en tablas por hilo. |
| `backend/app/modules/inbox/application/operations.py:355–368,370–410,490–564` | Asesor elegible = miembro habilitado y empleado activo; asignación guarda referencias estables y etiqueta compatible. Replay/hash/revisión existentes no acreditan identidad autenticada. |
| `backend/app/modules/inbox/application/operations.py:35–63,131–140` | SLA local vigente: próximo pendiente, 24/7, política explícita, entrante posterior al último saliente local y conversación cerrada excluida. **No es primera respuesta externa ni envío confirmado.** |
| `backend/app/sql_workspace.py:293–451` | Unidad transaccional y diario compatibles. El escritor actual exige hilo abierto y control humano para agregar texto; no puede reutilizarse sin adaptar explícitamente el caso de uso de envío humano mientras IA conserva control. |
| `backend/migrations/007_institutional_identity.sql:20–29`; `backend/app/modules/contacts/domain/models.py:15–32` | Perfil declarado del contacto, independiente de la identidad académica. Nombre/documento/correo no autorizan unión automática con SIIE. |
| `backend/app/sql_workspace.py:29–67`; `backend/app/modules/admissions/application/service.py:197–283` | `Contact.ProgramId int NULL`, `Program nvarchar(200)` e `Interests nvarchar(300)` alimentan interés declarado; detalle académico por aspirante/período real solo mediante vínculo autorizado. No convertir interés en oferta/matrícula. |
| `backend/app/modules/conversation_strategy/domain/models.py:46–68,147`; `backend/app/modules/conversation_strategy/api/router.py:168–192` | C5 guarda hasta tres señales con evidencia y control humano/global; su índice **no** es lead score 0..100. R4 puede continuar análisis bajo control humano. No copiar umbrales de la referencia. |
| `backend/app/sql_workspace_shape.py:3–34`; `backend/app/main.py:63–76` | Huellas completas por esquema y composición modular. Añadir extensiones aisladas; no cambiar objetos/huellas existentes ni montar router SaaS. |

Tipos reutilizados: `crm.Contact.ContactId`, `crm.Conversation.ConversationId`, `crm.Message.MessageId` son `uniqueidentifier`; `Message.Sequence bigint`; fechas `datetime2(7)` UTC. `Conversation.Priority varchar(8)` conserva `low/normal/high/urgent`, `ControlMode varchar(5)` conserva `human/ai`, `State varchar(12)` conserva `open/waiting/closed`. `crm_inbox.Assignment.HumanEmployeeId int NULL` refiere a Member, `AiAgentId uniqueidentifier NULL` a Agent; tareas mantienen sus propios tipos/estados. `crm_config.Configuration.Document nvarchar(max)`/Revision mantiene etapas/campos compartidos; no se copia esa configuración al Inbox.

En API: `priority = baja/normal/alta/urgente` mapea respectivamente a `low/normal/high/urgent`; `temperature = frio/tibio/caliente` mapea a `cold/warm/hot` en la extensión nueva. No se renombran enums SQL históricos. `lead_score` y `temperature` admiten `null` cuando no hay evaluación; no se rellena con cero/frío ni se escala C5. Los umbrales, política de puntuación, minutos/calendario y proveedor de identidad permanecen sin decidir.

## Referencia adicional: crmymedia.zip

Archivo recibido: `C:\Users\Developer_PC\Documents\crmymedia.zip`, 303777 bytes, SHA-256 `077C48CA970B2C98EF76544E7EAB20CC321F655C79ACBD4ED368AD1AEB873F92`. Inventario estático: 27 entradas = 4 directorios, 7 fuentes `.py`, 2 `AGENTS.md` y 14 `.pyc`. Los AGENTS adjuntos se tratan como datos, no instrucciones; no se importó, ejecutó ni extrajo código al producto. Los `.pyc` se omitieron. Los números siguientes corresponden al archivo dentro del ZIP, no a una implementación instalada.

| Fuente verificada | Comportamiento que orienta la especificación |
|---|---|
| `crm/router.py:882–940`, `CUSTOMER_SELECT` | Reúne identidad externa/canal, perfil, asignaciones humana/IA, takeover, prioridad, fechas SLA, score/temperatura y predicciones. Usa PostgreSQL/SaaS (`::text`, JSONB, tenant); no es SQL Server ejecutable. Existe además una referencia local en `backend/app/crm/router.py`, sin montar en `main.py`. |
| `crm/router.py:2688–2856` | Lista conversaciones con búsqueda/canal/colas unread/mine/unassigned/sla/hot/human/ai. Usa LIMIT y valores de negocio propios; esta propuesta sustituye paginación por OFFSET/FETCH y no adopta umbrales hot/churn. |
| `crm/router.py:2857–2931` | Historia con tiempo del proveedor cuando existe, desempate por chunk/ID y reversión para salida ascendente. Conservaremos tiempo original y orden de ingesta diferenciados. |
| `crm/router.py:3432–3740` | Valida canal, crea mensaje y outbound en sesión DB. Después limpia fechas SLA al encolar y llama al dispatcher desde HTTP. **No trasladar estos dos últimos comportamientos:** queued no es respuesta enviada y HTTP no despacha. Cartas/productos comerciales quedan excluidos de admisiones. |
| `crm/router.py:3778–3824` | Read pone contador global en cero; takeover cambia booleano por query. Aquí se especifican watermark por operador, cuerpo tipado, revisión, auditoría y fence monotónico. La asignación humana se expresa en campos de CustomerUpdate (`1860–2024`); no inventar un endpoint `/assign` ya presente en ese origen. |
| `media/router.py:35,1932–2007` | `/media/upload`, roles y cuota/storage; lee `await file.read()` completo antes de comprobar su máximo de 25 MiB y toma MIME declarado. Son riesgos a corregir mediante límites durante streaming, inspección y cuarentena; 25 MiB no es política aprobada del CRM. |
| `media/router.py:157–190,232–253,2806–2843` | Busca integración WhatsApp por tenant, obtiene token backend, consulta metadata Graph y descarga con Bearer; devuelve `Response` de bytes completos. Seleccionar última integración por tenant no basta para varias cuentas: resolver cuenta exacta del hilo, limitar/validar host y redirecciones. Estos helpers usan urllib y no implementan streaming ni Range. |
| `media/router.py:2736–2803`; `media/public_links.py:31–98` | Descarga privada por access token en query y enlaces públicos HMAC con tenant/media/exp, comparación constante y TTL propio. El secreto puede caer a claves generales SaaS/JWT. No copiar token en URL, fallback de secretos, TTL, enlaces públicos ni entrega inline sin política al Inbox privado. |

Dependencias del ZIP no aportadas por completo: `app_saas.db/security/secrets/storage`, billing, agentes, inteligencia, gateway y workers, además de tablas SaaS/SQLAlchemy. El ZIP no prueba sus permisos, transacciones, cifrado o conectividad. No se localiza `media/router.py` instalado en el checkout; ahora sí está disponible como fuente en este ZIP. Voz/visión/búsqueda IA y sus endpoints adicionales quedan fuera del Sprint 3. La referencia completa queda relacionada documentalmente con Sprint 2; su persistencia en el grafo se registra por separado.

## DDL propuesto — NO EJECUTAR

Solo tablas nuevas de extensión; `crm_channels` y Account/outbound_queue pertenecen al **borrador no aplicado de Sprint 2**. No hay `CREATE SCHEMA`, `ALTER`, migración ni ejecutor. La migración eventual debe preservar datos, FKs, huellas y diarios anteriores, después de autorización y ensayo. Índices únicos usan UUID y claves externas BIN2 acotadas; sin índice sobre MAX. JSON valida sintaxis y el futuro escritor validará estructura/límites.

```sql
CREATE TABLE crm_channels.ExternalThread (
    ThreadId uniqueidentifier NOT NULL PRIMARY KEY,
    AccountId uniqueidentifier NOT NULL REFERENCES crm_channels.Account(AccountId),
    ExternalThreadId nvarchar(200) COLLATE Latin1_General_100_BIN2 NOT NULL,
    ConversationId uniqueidentifier NOT NULL REFERENCES crm.Conversation(ConversationId),
    CreatedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
    UNIQUE (AccountId, ExternalThreadId)
);

CREATE TABLE crm_channels.ThreadMessage (
    ThreadId uniqueidentifier NOT NULL REFERENCES crm_channels.ExternalThread(ThreadId),
    MessageId uniqueidentifier NOT NULL UNIQUE REFERENCES crm.Message(MessageId),
    MessageKind varchar(10) NOT NULL CHECK (MessageKind IN ('text','audio','image','document')),
    BodyKind varchar(10) NOT NULL CHECK (BodyKind IN ('text','attachment')),
    ProviderOccurredAt datetime2(7) NULL,
    PRIMARY KEY (ThreadId, MessageId)
);

CREATE TABLE crm_channels.ThreadReadCursor (
    ThreadId uniqueidentifier NOT NULL REFERENCES crm_channels.ExternalThread(ThreadId),
    OperatorSubject nvarchar(128) COLLATE Latin1_General_100_BIN2 NOT NULL,
    LastSeenSequence bigint NOT NULL CHECK (LastSeenSequence>=0),
    Revision bigint NOT NULL CHECK (Revision>=0),
    UpdatedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
    PRIMARY KEY (ThreadId, OperatorSubject)
);

CREATE TABLE crm_channels.ConversationFence (
    ConversationId uniqueidentifier NOT NULL PRIMARY KEY REFERENCES crm.Conversation(ConversationId),
    ControlEpoch bigint NOT NULL CHECK (ControlEpoch>=0),
    Revision bigint NOT NULL CHECK (Revision>=0)
);

CREATE TABLE crm_channels.InboxOperation (
    OperationId uniqueidentifier NOT NULL PRIMARY KEY,
    AccountId uniqueidentifier NOT NULL REFERENCES crm_channels.Account(AccountId),
    ThreadId uniqueidentifier NOT NULL REFERENCES crm_channels.ExternalThread(ThreadId),
    ActorSubject nvarchar(128) COLLATE Latin1_General_100_BIN2 NOT NULL,
    Action varchar(16) NOT NULL CHECK (Action IN ('read','assign','takeover','send','upload')),
    PayloadHash binary(32) NOT NULL,
    RevisionScope varchar(12) NOT NULL CHECK (RevisionScope IN ('conversation','read_cursor','media')),
    ResultJson nvarchar(max) NOT NULL CHECK (ISJSON(ResultJson)=1),
    CreatedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME()
);

CREATE TABLE crm_channels.OutboundControl (
    OutboundId uniqueidentifier NOT NULL PRIMARY KEY REFERENCES crm_channels.outbound_queue(OutboundId),
    ThreadId uniqueidentifier NOT NULL REFERENCES crm_channels.ExternalThread(ThreadId),
    ActorKind varchar(5) NOT NULL CHECK (ActorKind IN ('human','bot')),
    ControlEpoch bigint NULL,
    CHECK ((ActorKind='bot' AND ControlEpoch IS NOT NULL AND ControlEpoch>=0)
        OR (ActorKind='human' AND ControlEpoch IS NULL))
);

CREATE TABLE crm_channels.ThreadSlaProjection (
    ThreadId uniqueidentifier NOT NULL PRIMARY KEY REFERENCES crm_channels.ExternalThread(ThreadId),
    PolicyKey varchar(80) NOT NULL,
    PolicyRevision bigint NOT NULL CHECK (PolicyRevision>0),
    FirstIncomingMessageId uniqueidentifier NOT NULL REFERENCES crm.Message(MessageId),
    PendingIncomingMessageId uniqueidentifier NULL REFERENCES crm.Message(MessageId),
    FirstResponseDueAt datetime2(7) NULL,
    SlaDueAt datetime2(7) NULL,
    QualifiedOutboundId uniqueidentifier NULL REFERENCES crm_channels.outbound_queue(OutboundId),
    SourceRevision bigint NOT NULL CHECK (SourceRevision>=0),
    CalculatedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME()
);

CREATE TABLE crm_channels.ContactLeadAssessment (
    ContactId uniqueidentifier NOT NULL PRIMARY KEY REFERENCES crm.Contact(ContactId),
    LeadScore tinyint NULL CHECK (LeadScore BETWEEN 0 AND 100),
    Temperature varchar(4) NULL CHECK (Temperature IN ('cold','warm','hot')),
    PolicyKey varchar(80) NOT NULL,
    PolicyRevision bigint NOT NULL CHECK (PolicyRevision>0),
    EvidenceJson nvarchar(max) NOT NULL CHECK (ISJSON(EvidenceJson)=1),
    SourceRevision bigint NOT NULL CHECK (SourceRevision>=0),
    AssessedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME()
);

CREATE TABLE crm_channels.MediaAsset (
    MediaId uniqueidentifier NOT NULL PRIMARY KEY,
    ThreadId uniqueidentifier NOT NULL REFERENCES crm_channels.ExternalThread(ThreadId),
    AccountId uniqueidentifier NOT NULL REFERENCES crm_channels.Account(AccountId),
    ProviderMediaId nvarchar(200) COLLATE Latin1_General_100_BIN2 NULL,
    StorageKey nvarchar(200) COLLATE Latin1_General_100_BIN2 NULL,
    ActualMime varchar(100) NULL,
    Codec varchar(50) NULL,
    ByteLength bigint NOT NULL CHECK (ByteLength>0),
    ContentHash binary(32) NOT NULL,
    ScanState varchar(12) NOT NULL CHECK (ScanState IN ('quarantine','ready','rejected','deleted')),
    Revision bigint NOT NULL CHECK (Revision>=0),
    SourceKind varchar(8) NOT NULL CHECK (SourceKind IN ('provider','upload')),
    CreatedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
    ExpiresAt datetime2(7) NULL,
    UNIQUE (ThreadId, MediaId),
    CHECK (ScanState<>'ready' OR (StorageKey IS NOT NULL AND ActualMime IS NOT NULL))
);
CREATE UNIQUE INDEX UX_Media_Provider ON crm_channels.MediaAsset(AccountId,ProviderMediaId)
    WHERE ProviderMediaId IS NOT NULL;
CREATE UNIQUE INDEX UX_Media_Storage ON crm_channels.MediaAsset(StorageKey)
    WHERE StorageKey IS NOT NULL;

CREATE TABLE crm_channels.MessageAttachment (
    ThreadId uniqueidentifier NOT NULL,
    MessageId uniqueidentifier NOT NULL,
    MediaId uniqueidentifier NOT NULL,
    PRIMARY KEY (ThreadId, MessageId, MediaId),
    FOREIGN KEY (ThreadId, MessageId) REFERENCES crm_channels.ThreadMessage(ThreadId, MessageId),
    FOREIGN KEY (ThreadId, MediaId) REFERENCES crm_channels.MediaAsset(ThreadId, MediaId)
);
```

El escritor comprobará además que hilo/cuenta/conversación/mensaje/receipt corresponden en cada operación; las FKs simples no prueban ese conjunto. No existe FK a un usuario SIIE inventado: `OperatorSubject`/`ActorSubject` será el identificador opaco del principal autenticado y solo lo fija el servidor. `InboxOperation` es auditoría/autenticación nueva, no otro estado actual de la ficha. `crm.Operation.Actor='local-operator'` y la revisión local se preservan como compatibilidad y nunca se presentan como usuario autenticado.

`MediaAsset` describe bytes ya descargados/subidos y medidos; antes de descargarlos solo se conserva referencia externa del evento de Sprint 2, no se inventa longitud/hash. La obtención posterior crea metadata en cuarentena; ningún asset es servible antes de estar listo. Índices adicionales de lectura/reclamación y políticas de retención quedan en el diseño de migración; no hay proveedor o dependencia de almacenamiento elegido.

## Routers propuestos sobre el módulo existente

```text
backend/app/modules/inbox/             (existente; sin scaffold en este corte)
  api/router.py                       composición HTTP actual y futuro /api/v1/inbox
  api/media.py                        router propuesto /api/v1/media; sin alias /inbox/media
  application/service.py              lectura paginada/ficha/historia compartida
  application/operations.py           asignación/tareas; mantener su dueño
  application/                        futuros casos de lectura/read/takeover/send/media
  domain/                             futuros contratos puros, enums y reglas
  infrastructure/                     futuros adaptadores SQL/media privados
```

| Método / ruta propuesta | Resultado y permiso mínimo por acción/recurso |
|---|---|
| `GET /api/v1/inbox/conversations` | 200 página visible al principal; filtros `channel`, `admission_stage`, `assignee_id`, `unread`, `overdue`, `offset`, `limit`, `cutoff`. |
| `GET /api/v1/inbox/conversations/{thread_id}` | 200 ficha/MiniCRM con contacto, interés, posible vínculo académico autorizado, estado/control compartidos, SLA y evaluación con procedencia. |
| `GET /api/v1/inbox/conversations/{thread_id}/messages` | 200 historial cronológico acotado por cursor `before`/`limit`; incluye IDs internos de medios y estado de entrega real. |
| `POST /api/v1/inbox/conversations/{thread_id}/read` | 200 watermark monotónico del operador actual; permiso de lectura. No envía read receipt al proveedor. |
| `POST /api/v1/inbox/conversations/{thread_id}/assign` | 200 asignación padre; permiso gestionar asignación en todos los hilos afectados y asesor elegible verificado. |
| `POST /api/v1/inbox/conversations/{thread_id}/takeover` | 200 control padre/fence; permiso control humano en alcance afectado. Cuerpo booleano estricto. |
| `POST /api/v1/inbox/conversations/{thread_id}/messages` | 202 aceptación durable `queued`, mensaje + outbox atómicos; permiso de envío humano y cuenta habilitada. Sin llamada externa en HTTP. |
| `POST /api/v1/media` | 202 multipart con `thread_id` en metadata, hacia cuarentena privada; autorización de upload y límites configurados. No permite envío hasta ready. |
| `GET /api/v1/media/{media_id}` | 200 metadata/estado privado; mismo control de cuenta e hilo. Sin URL remota, secreto o storage key. |
| `GET /api/v1/media/{media_id}/content` | 200/206 stream autorizado de contenido privado ya verificado, por ID interno. |

Todos los handlers son **propuestos**. Auth/RBAC real está pendiente; ni loopback ni `X-CRM-Local` bastan para activarlos. El servidor deriva actor y cuentas permitidas, comprueba visibilidad en cada lookup y replay, y devuelve 404 para referencias fuera del alcance sin revelar existencia. 401 sin sesión; 403 acción prohibida sobre recurso visible; 409 revisión/idempotencia/relación incompatible; 413 tamaño; 415 MIME/codec no permitido; 422 entrada inválida saneada; 423 medio en cuarentena; 410 expirado/eliminado; 416 Range inválido; 429 cuota; 502 proveedor indisponible; 503 dependencia/política no configurada. Sin rutas arbitrarias de despacho, SQL libre, URL proxy ni token en query.

### Ejemplos de contrato, no registros reales

IDs de ejemplo son UUID sintéticos; `null` indica ausencia de evidencia, no cálculo pendiente simulado.

```json
{
  "items": [{
    "thread_id": "10000000-0000-4000-8000-000000000001",
    "conversation_id": "20000000-0000-4000-8000-000000000001",
    "account_id": "30000000-0000-4000-8000-000000000001",
    "contact_id": "40000000-0000-4000-8000-000000000001",
    "channel": "whatsapp", "priority": "normal", "state_scope": "conversation",
    "assignee_id": null, "unread": true, "overdue": null,
    "lead_score": null, "temperature": null,
    "first_response_due_at": null, "sla_due_at": null,
    "takeover": true, "revision": "7"
  }],
  "offset": 0, "limit": 25, "has_more": false,
  "cutoff": "2026-10-19T22:00:00.0000000Z", "consistency": "live_with_cutoff"
}
```

```json
{
  "thread_id": "10000000-0000-4000-8000-000000000001",
  "mini_crm": {
    "applicant": {"source": "crm_declared", "contact_id": "40000000-0000-4000-8000-000000000001", "academic_record": null, "academic_link_status": "not_linked"},
    "program_interest": {"program_id": null, "label": "", "declared_interests": "", "source": "crm.Contact"},
    "admission_stage": {"key": null, "label": "", "source": "crm_config_and_contact", "status": "not_configured"},
    "priority": "normal", "lead_score": null, "temperature": null,
    "assessment_status": "not_configured", "assessment_evidence": [],
    "takeover": true, "control_epoch": "4", "state_scope": "conversation",
    "affected_thread_ids": ["10000000-0000-4000-8000-000000000001"],
    "first_response_due_at": null, "sla_due_at": null, "sla_status": "not_configured"
  },
  "revision": "7", "read_revision": "2"
}
```

`applicant` muestra el prospecto declarado, sin crear `prospects`. El registro `ACAspirante` solo se agrega cuando una vinculación institucional separada está autorizada y validada en el período consultado; actualmente se muestran candidatos, no una relación confirmada. No deducir vínculo por teléfono/documento. Etapa se resuelve contra la configuración compartida; etiqueta y key no se sustituyen por heurística.

```json
{"takeover": true, "operationId": "50000000-0000-4000-8000-000000000001", "expectedRevision": "7"}
```

```json
{"humanEmployeeId": 123, "operationId": "50000000-0000-4000-8000-000000000002", "expectedRevision": "8"}
```

```json
{"lastSeenSequence": "241", "operationId": "50000000-0000-4000-8000-000000000003", "expectedRevision": "2"}
```

```json
{"messageId": "60000000-0000-4000-8000-000000000001", "text": "Información de admisiones", "mediaIds": [], "operationId": "50000000-0000-4000-8000-000000000004", "expectedRevision": "8"}
```

Send responde 202 con `message_id`, `outbound_id`, `delivery_state: "queued"` y revisión confirmada; no `sent:true`. IDs/recipient/account se resuelven desde el hilo, no desde texto del operador. Misma operación/cuenta/hilo/payload devuelve resultado original, sin insertar otra vez; payload, actor o alcance diferente con OperationId reutilizado da 409, previa autorización. El hash canónico incluye acción, hilo, cuenta, IDs y cuerpo, excluye expectedRevision. Revisión conversacional para assign/takeover/send; revisión del cursor para read. Upload incluye operación + hash real de bytes/metadatos saneados y conserva el asset original ante replay.

## Paginación y orden SQL Server

Límites propuestos técnicos: `offset 0..1000000`, `limit 1..100`, default 25; historia `limit 1..100`, default 50. Son límites del contrato a revisar, no SLA institucional. Canal enum cerrado; etapa validada contra configuración; assignee int real o filtro `unassigned` separado; booleanos estrictos y sin consultas arbitrarias. Ejemplo parametrizado para **una cuenta previamente autorizada por servidor**, sin sustituir la verificación de acceso:

```sql
-- Parámetros ligados por el driver; nunca concatenar filtros del navegador.
SELECT t.ThreadId,t.ConversationId,a.Channel,c.Priority,p.Stage,
       ia.HumanEmployeeId,latest.LastActivityAt
FROM crm_channels.ExternalThread t
JOIN crm_channels.Account a ON a.AccountId=t.AccountId
JOIN crm.Conversation c ON c.ConversationId=t.ConversationId
JOIN crm.Contact p ON p.ContactId=c.ContactId
LEFT JOIN crm_inbox.Assignment ia ON ia.ConversationId=c.ConversationId
OUTER APPLY (
    SELECT MAX(m.CreatedAt) AS LastActivityAt
    FROM crm_channels.ThreadMessage tm JOIN crm.Message m ON m.MessageId=tm.MessageId
    WHERE tm.ThreadId=t.ThreadId AND m.CreatedAt<=@cutoff
) latest
WHERE t.AccountId=@authorizedAccountId AND t.CreatedAt<=@cutoff
  AND (@channel IS NULL OR a.Channel=@channel)
  AND (@stageLabel IS NULL OR p.Stage=@stageLabel)
  AND (@assigneeId IS NULL OR ia.HumanEmployeeId=@assigneeId)
  AND (@unassigned=0 OR ia.HumanEmployeeId IS NULL)
ORDER BY COALESCE(latest.LastActivityAt,t.CreatedAt) DESC,t.ThreadId DESC
OFFSET @offset ROWS FETCH NEXT @fetchPlusOne ROWS ONLY;
```

Para varias cuentas, la aplicación agrega un conjunto de IDs **autorizados** mediante parámetros/TVP soportado; no acepta una lista libre como control de acceso. `unread` agrega EXISTS de entrantes del hilo con Sequence mayor al cursor del operador; `overdue` usa la proyección externa configurada, estado padre abierto/en espera y reloj UTC servidor. Sin política: `overdue=null`; `overdue=true` excluye no configurados, `false` selecciona únicamente configurados aún no vencidos. No confundir ese filtro con el SLA local anterior.

`cutoff` conserva el límite temporal de la primera página y el desempate UUID es único, pero **no congela** estado, lecturas ni commits tardíos entre peticiones. Un nuevo entrante/reclasificación puede reordenar páginas o desplazar elementos según contrato; el cliente deduplica por thread_id y ofrece refresco. Un snapshot real requiere materialización de IDs o misma transacción/aislamiento entre consultas, decisión fuera de este corte; no mantener una transacción SQL abierta durante navegación. [Condiciones oficiales de OFFSET/FETCH estable](https://learn.microsoft.com/en-us/sql/t-sql/queries/select-order-by-clause-transact-sql?view=sql-server-ver16).

Historia: la tupla `COALESCE(ProviderOccurredAt,CreatedAt), Sequence, MessageId` define orden único; buscar página anterior por esa misma tupla y devolverla ascendente. Cursor `before` opaco y acotado, validado contra hilo/cuenta autorizados, conserva tupla y cutoff; no mezclar seek solo por Sequence con orden distinto por fecha del proveedor. Conservar `ingest_sequence` string y `provider_occurred_at` nullable; llegada tardía puede insertarse cronológicamente antes de lo mostrado, identificable por MessageId y recuperable al refrescar. Read watermark avanza por secuencia de ingesta del hilo que el cliente confirma, no por fecha externa; validar que el límite existe en ese hilo y no supera su secuencia publicada por servidor. Es una confirmación de interfaz, no prueba de que una persona leyó cada palabra. Entradas tardías con nueva Sequence permanecen no leídas. No actualizar `crm.Conversation.Unread` global al leer una pestaña; es otra semántica histórica.

## Control humano, envío y SLA

Takeover deriva su único estado de `crm.Conversation.ControlMode`: true→human, false→ai. En una transacción debe comparar la revisión del padre, registrar operación/actor, cambiar control y aumentar ControlEpoch/Revision sin retroceder. Todos los hilos vinculados quedan afectados. No escribir otro takeover boolean en la extensión; Fence solo guarda generación/concurrencia. El análisis R4 sigue ejecutándose si está habilitado; el fence aplica a generación/despacho de respuestas bot, no al análisis. Tareas/autonomía C5 conservan sus controles propios y no se activan al liberar takeover.

Jobs y respuestas bot capturan el epoch al crearse y lo verifican al confirmar y justo antes de la llamada de envío. Epoch viejo queda terminalmente invalidado y no revive al volver a AI; puede representarse en la cola propuesta como failed con código saneado `control_epoch_obsolete`, sin fingir un intento externo. Generar una respuesta nueva exige estado/política/consentimiento vigentes. Envío humano autorizado permanece permitido aunque bot esté pausado, sujeto a cuenta, ventana y conversación abierta; no hace falta liberar takeover ni reactivar IA.

El último control SQL previo a llamar al proveedor reduce la carrera, **no permite retirar una solicitud ya en vuelo**. Debe registrarse frontera de envío/reserva y evidencia temporal: si takeover gana antes de esa frontera, no se inicia la llamada; si la llamada ya inició, takeover informa `in_flight` posible y bloquea las siguientes. No prometer atomicidad SQL+red ni rollback de una entrega externa. Un resultado incierto se reconcilia antes de repetir.

El caso send comparte una única transacción SQL: autenticación/autorización→replay→revisión/relaciones/medio ready→INSERT Message + ThreadMessage + Attachment + outbound_queue + OutboundControl + diarios/revisión→COMMIT; cualquier fallo revierte todos esos efectos. Sin dispatcher en HTTP. El estado externo sigue queued hasta confirmación del dispatcher; los diarios existentes deben preservar R3A/R4. `Body` no vacío exige que un envío solo-media registre un marcador explícito como `[audio]` con `BodyKind=attachment`; no se presenta como transcripción, texto del usuario o evidencia de contenido.

`first_response_due_at` es la fecha derivada del primer entrante pendiente del hilo y política explícita; solo se satisface cuando un outbound calificable tiene confirmación real del proveedor según contrato elegido, nunca al insertar outgoing/queued. `sla_due_at` representa la siguiente respuesta pendiente bajo esa política; entrantes posteriores no reinician artificialmente el primer pendiente. Un rechazo no satisface SLA; timeout incierto no se da por respondido. Public reply, aviso interno y receipt técnico no cuentan como respuesta DM salvo política explícita. No decidir aquí si califica aceptación sent, entrega delivered o intervención humana: esa semántica, horas/calendario y límites requieren aprobación y versión. Sin política o evidencia: fechas null/not_configured. El SLA local 24/7 sigue con su comportamiento y nombre separado.

**Condición de activación:** los escritores locales actuales no conocen ConversationFence ni OutboundControl. No se habilita el nuevo API junto a esos escritores sin integrar previamente una unidad transaccional que mantenga fences, diarios y revisiones en ambos caminos. La especificación no afirma que ese problema de concurrencia esté resuelto ni modifica sus tablas/huellas.

## Medios: contrato privado y acotado

Audio OGG/MP4, imágenes y PDF son necesidades funcionales; extensión/nombre/MIME declarado no prueban contenedor ni codec. Configuración aprobada debe limitar bytes durante lectura y descompresión/inspección, MIME efectivo, codecs/duración, concurrencia, cuotas y tiempo. Cuarentena privada, hash, inspección/escaneo y estado visible; no dar por seguro un archivo porque File/UploadFile acepte multipart. Ante política/escáner indisponible, no servir/enviar y devolver indisponibilidad, no ready. Nunca usar un adjunto como aprobación de pago/matrícula.

Almacenamiento se especifica como interfaz de objetos privados por StorageKey, sin elegir vendor/dependencia ni guardar bytes libres en columnas JSON. Acceso por MediaId interno y relación cuenta→hilo→mensaje autorizada cada vez; el cliente no proporciona ruta, token, host o URL externa. Descargar Meta obtiene referencia de medio de un evento auténtico, resuelve credencial AES backend de **esa cuenta** y valida pertenencia antes de solicitar metadata. Esto depende de Sprint 2 aún no implementado.

La referencia remota recibida permanece pendiente en el evento hasta completar una descarga de fondo acotada. El fetch/proxy autenticado es una etapa de obtención: mide longitud/hash, coloca bytes en cuarentena y los inspecciona/escanea antes de marcar `ready`. El chat transmite únicamente ese contenido privado verificado; no pasa bytes remotos sin inspección al reproductor como si estuvieran listos. Una nueva descarga por expiración de URL o cambio de contenido vuelve por validación y cuarentena antes de servirse; no omite ese ciclo. El upload propuesto usa exclusivamente `POST /api/v1/media` con `thread_id` multipart y los mismos controles, sin alias bajo `/inbox`.

Proxy: HTTPS con certificado validado y hosts aprobados para el producto; bloquear destinos privados/loopback, DNS rebinding y redirects no aprobados. Nunca reenviar Bearer a otro host por redirección; cada salto necesita política explícita o se rechaza. No devolver credencial ni URL firmada upstream al navegador, logs o mensajes de error. Si la URL expira, una sola renovación de metadata por operación tras error clasificable; no bucle infinito ni reintento ante 401/403 por secreto inválido. Límites/expiración exactos Meta aún requieren contrato oficial verificable: [documentación de medios](https://developers.facebook.com/documentation/business-messaging/whatsapp/business-phone-numbers/media).

Content streaming debe limitar bytes reales aunque falte Content-Length, cancelar y cerrar upstream/archivo al desconectar cliente, con timeout y cuota. Soportar **un solo** byte Range válido (`start-end`, `start-` o sufijo acotado), comprobar tamaño y devolver 206/Content-Range/Content-Length correctos; 416 con tamaño conocido si es inválido/no satisfacible; rechazar multi-range. No reenviar encabezados arbitrarios ni anunciar Accept-Ranges sin capacidad real. Entregar Content-Type inspeccionado, `nosniff`, nombre Content-Disposition saneado y Cache-Control privado/no-store según política; no inline activo para PDF/HTML no permitido. [FastAPI StreamingResponse](https://fastapi.tiangolo.com/advanced/custom-response/) y [UploadFile](https://fastapi.tiangolo.com/tutorial/request-files/) son primitivas, no prueba de estos controles.

## Aceptación futura y bloqueos

- Una misma persona con dos cuentas/hilos conserva un contacto/conversación; mensaje, medio y operación de otra cuenta se rechazan. El efecto compartido de takeover/asignación debe ser aprobado y visible.
- Páginas con empate/entrantes tardíos tienen orden documentado, sin duplicar identidad; historia y watermark no pierden entrantes concurrentes. Read de A no marca leído a B ni manda receipt del proveedor.
- Asignación solo a miembro habilitado/empleado activo, con revisión, replay y auditoría real. No inventar usuario autenticado a partir del employee ID.
- Dos takeovers/send concurrentes, lease/epoch obsoleto y liberación posterior no reactivan bot antiguo; caso in-flight demuestra el límite de no-revocación. El envío humano no requiere reactivar bot.
- Caída entre insert Message/outbox/commit, replay y timeout no deja mensaje sin cola ni duplica efectos. queued/uncertain no cierran SLA; delivered/read no retroceden.
- Audio/PDF/imágenes falsos, exceso de tamaño durante stream, medios cruzados, traversal/SSRF/redirect, token expirado, Range y cancelación se cubren antes de aceptar proveedor/storage. En cuarentena no se entrega contenido.

Bloqueos: aceptación de estos modelos y efecto padre; contrato de identidad/RBAC; Sprint 2 durable/cifrado/dispatcher/productos; política score/SLA/media y almacenamiento privado; transición de escritores/revisiones; SQL Server/restauración/transacciones y prueba real por capa. Esta unidad solo entrega especificación y comprobación estructural/enlaces: no acredita implementación, tests, UI, SQL, medios, proveedor o producción. No autoriza DDL, publicación, despliegue ni envío.
