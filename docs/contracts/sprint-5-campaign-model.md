# Sprint 5 — modelos de campañas y rúbrica de abandono

**Actualización operativa local, 2026-10-20:** tras el primer corte de modelos, el propietario autorizó endpoints, workers y pantalla sin envíos reales. El coordinador aplicó explícitamente `018_campaigns.sql` sobre el destino `local_sql_copy` verificado con TLS; existen nueve tablas `crm_marketing`. Se implementaron API, evaluación/preparación durable y `/#/campaigns`. La aceptación manual de navegador/HTTP se registra en el informe de operación; la lectura de fuentes no sustituye esa evidencia. No se ejecutaron tests, builds, copias ni envíos reales.

## Reutilización e identidad

Se conservan `crm.Contact`, `crm.Conversation` y `crm.Message` con UUID/Sequence existentes; `Contact.Stage` es texto, no UUID de etapa. `ConversationProfile.LeadScore` es manual y no se sobrescribe. `ExternalIdentity` es la identidad exacta del canal: nunca se fusiona por teléfono. La única cola de salida continúa siendo `crm_channels.outbound_queue`; un destinatario enlaza su `QueueId`, no crea otra outbox.

`MessageRoute.CompletedAt` acredita final del POST local aceptado, **no entrega ni hora de envío confirmada por el proveedor**. `outbound_queue.State='sent'` puede proceder del POST y por sí solo tampoco acredita un evento `sent` recibido. La extracción futura debe comprobar el evento firmado persistido y su timestamp/identidad antes de construir `ConfirmedResponse`. No se sustituye por `CreatedAt`, `UpdatedAt` ni fecha de encolado. SLA del asesor y abandono del aspirante son conceptos distintos.

## Modelo SQL local

018 crea únicamente `crm_marketing`. El runner explícito `backend/tools/migrate_campaigns.py` exige destino local, TLS, contratos existentes y transacción; toma el bloqueo local y rechaza un esquema previo. No se aplica al arrancar la app ni incluye contactos de ejemplo. La auditoría DDL normal del destino local permanece activa conforme a ADR-006; no se escriben datos de negocio core.

| Tabla | Datos y restricciones principales |
| --- | --- |
| `ChurnAssessment` | UUID; FK conversación e identidad opcional; `AsOfUtc`, `InputSequence` nullable, `FormulaVersion`, etapa exacta, espera; `RiskScore` nullable 0–100, estado known/unknown/not_applicable y nivel coherente; razones array y evidencia objeto `NVARCHAR(MAX)` con `ISJSON`; índice conversación/fecha. Es una evaluación versionada, no probabilidad. |
| `MessageTemplate` | UUID local y ID real del proveedor; canal, cuenta externa/WABA, revisión de cuenta, nombre, idioma, versión de contenido, revisión de estado, status y fecha de sincronización; componentes JSON array. Unicidad por cuenta/ID/versión y por cuenta/nombre/idioma/versión. FK compuesta utilizada por reglas/campañas impide mezclar sus cuentas/idiomas mediante otro registro. No se declara aprobada una plantilla por estar guardada. |
| `ContactConsent` | Historial por identidad exacta/canal/cuenta/finalidad marketing o service; versión monotónica, unknown/granted/revoked/expired, evidencia JSON y fechas; revocación puede referenciar versión anterior mediante FK del mismo ámbito. Sin fila o estado unknown no habilitan marketing. Un opt-out sin grant histórico también se registra como revoked; no exige inventar un consentimiento anterior. |
| `RemarketingRule` | Etapa textual exacta con collation binaria, días de inactividad, cooldown, riesgo mínimo, cuenta y versión de plantilla; revisión y `Enabled=0` inicial. No deduce la etapa desde palabras españolas ni convierte un plan de recomendación en campaña. |
| `AccountCadence` | Una fila por canal/cuenta externa, compartida por todas las campañas: intervalo mínimo, cupo de destinatarios, ventana UTC persistida, reservas, próximo permiso, revisión y lease. No contiene cola ni mensajes. Los valores los debe configurar el propietario; no hay límites del proveedor inventados. |
| `Campaign` | UUID, bulk/remarketing, draft inicial, scheduled/running/paused/completed/cancelled; segmento JSON, cuenta/cadencia, plantilla versionada e idioma obtenido de ese registro, regla opcional coherente con kind, programación UTC, pausa, revisión y epoch de inclusión. |
| `CampaignRecipient` | Inscripción y ciclo durable en una sola tabla; UNIQUE(campaña, identidad), FK contacto/conversación/campaña, único enlace a cola existente; estado pending/blocked/leased/queued/sent/delivered/read/failed/uncertain/cancelled, evidencia y watermark, versiones de campaña/regla/consentimiento/cuenta, epoch humano e inclusión, vencimiento de lease, intentos y motivo. Estados enviados/queued requieren cola y referencia de consentimiento, sin convertir eso en aprobación de envío. |
| `EvaluationRun` | Ejecuciones durables de riesgo, reglas y preparación; UUID idempotente, origen manual/periódico, queued/processing/completed/failed, fechas, lease, máximo tres recuperaciones, resultados JSON y error saneado. |
| `Policy` | Pesos explícitos por etapa, revisión CAS, interruptor de evaluación periódica e intervalo. No contiene un interruptor de transporte. |

Los borradores de reglas deshabilitadas y campañas permiten plantilla/cuenta nulas. La preparación actual conserva destinatarios como `blocked`, sin crear mensajes ni QueueId. Las evaluaciones almacenan además `ComputedLeadScore` y razones independientes; no modifican `ConversationProfile.LeadScore`. Un receptor mantiene FK simple a campaña además de la compuesta por cuenta para no eludir integridad cuando el borrador aún no tiene cuenta.

Todos los JSON de este diseño son `NVARCHAR(MAX)` con `ISJSON` y forma inicial objeto/array; su contenido tipado se validará en el caso de uso futuro. `SegmentJson` admite sólo listas acotadas de `program_ids`, `stage_values`, `schedule_values` y un `period_id` explícito; sin SQL/predicados libres. Programa/período/jornada se contrastarán con oferta oficial; `Contact.Schedule` personal no confirma jornada académica ni matrícula. No se duplican precios/estudiantes como autoridad.

**Frontera de integridad que un UUID no resuelve:** la audiencia actual une identidad/contacto/conversación/cuenta exactas, verifica la última versión de consentimiento marketing, no-contacto, control humano y plantilla aprobada de la cuenta y revisión actuales. Una versión de plantilla antigua deja de ser seleccionable cuando aparece una nueva; no se cambia silenciosamente la plantilla de campañas guardadas. La audiencia permanece bloqueada por transporte. La validación completa de un envío real y su reconciliación futura sigue pendiente; ningún UUID ni consentimiento por sí solo habilita un POST.

## Función pura de abandono

`IncomingEvidence`, `ConfirmedResponse`, `CostExchange`, `ChurnInputs` y `ChurnAssessment` son dataclasses inmutables de dominio, sin SQL/FastAPI/SDK. El adaptador `campaigns/evidence.py` reconstruye evidencia acotada desde mensajes/rutas exactas y webhooks autenticados persistidos, contrasta digest y payload crudo, activo de canal y estado positivo real del proveedor. Exige referencia al último entrante respondido; los envíos humanos históricos sin esa referencia permanecen desconocidos. Una marca del navegador o LLM no acredita completitud. Límites: 100 mensajes y 50 recibos; excederlos produce abstención, no una puntuación ficticia.

Sólo conversa activa open/waiting, etapa mapeada explícitamente, entrante genuino y respuesta realmente confirmada posterior permiten puntuar. Se admite confirmación provider_sent/provider_delivered/provider_read con referencia al evento; no se equiparan entre sí ni se afirma entrega a partir de sent. Cada respuesta debe enlazar el último mensaje entrante al que responde. Duplicados, tiempos futuros/naive, cronología contradictoria, identidad diferente, watermark ausente o evidencia incompleta devuelven **score NULL / unknown**, con razón. Cerrado devuelve **NULL / not_applicable**, nunca riesgo cero. Si llegó un entrante nuevo y aún no tiene respuesta confirmada, devuelve **unknown / advisor_response_pending**: es deuda del asesor, no abandono.

Se cuentan sólo respuestas confirmadas a ese último entrante. Un mismo MessageId no puede ser entrante y respuesta; MessageId, Sequence o QueueId repetidos producen unknown, sin sumar dos veces el mismo envío. Una evaluación SQL known exige identidad y etapa no nulas, igual que la función. El primer envío confirmado de ese bloque inicia el reloj; enviar más seguimientos no rejuvenece artificialmente la espera. Un entrante nuevo reinicia reloj, contador y señal de costos anterior. Máximo 100 evidencias por cálculo; si se excede, unknown en lugar de truncar silenciosamente.

La rúbrica inicial es una **propuesta transparente, no calibrada**:

1. `días = floor((as_of - primera_respuesta_confirmada)/24h)`.
2. `I = min(60, 15 × días)`.
3. `S = peso_configurado[etapa_exacta]`, entero explícito entre 0 y 25. Sin mapping: unknown. No hay defaults basados en nombres de etapas reales.
4. `U = min(15, 5 × respuestas_confirmadas_sin_nuevo_entrante)`.
5. `riesgo = clamp(I + S + U, 0, 100)`.
6. Si el **último** entrante pidió costos, existe evidencia de esa petición y de una respuesta que realmente los contesta, esa respuesta tiene confirmación positiva y pasaron **72 horas o más sin nuevo entrante**, `riesgo = max(80, riesgo)`. Las dos referencias de clasificación de costos deben existir y ser verificadas por el adaptador/revisión; un mensaje cualquiera enviado después no constituye respuesta de costos. Confirmación de esa respuesta ausente: unknown.

Niveles: **bajo 0–34; medio 35–69; alto 70–100**. El resultado incluye versión, as-of, watermark, fecha inicial, IDs de mensajes, componentes y códigos de razón. Se persiste separado del LeadScore manual. No significa «80 % de probabilidad de abandonar» ni autoriza contacto.

| Ejemplo ilustrativo de la ecuación, no registro ejecutado | Resultado esperado |
| --- | --- |
| 24 h, etapa configurada15, una respuesta confirmada | 15+15+5 = **35 / medio** |
| 72 h, etapa configurada20, una respuesta confirmada | 45+20+5 = **70 / alto** |
| 72 h tras respuesta de costos comprobada, etapa0, una respuesta | base50, mínimo especial **80 / alto** |
| Nuevo entrante después de esa respuesta, asesor aún sin responder | **NULL / unknown**, reloj anterior no reutilizable |
| Mensajes sólo locales/encolados, sin recibo proveedor | **NULL / unknown** |
| Conversación cerrada | **NULL / not_applicable** |

El endpoint devuelve `ComputedLeadScore` separado del manual: interés declarado +30, solicitud explícita de siguiente paso +30 e intención de inscripción +40, exclusivamente sobre el último entrante autenticado y con evidencia de mensaje. Sin señales devuelve NULL, no cero. Es una rúbrica `lead-observable-v1`, sin calibración ni decisiones de admisión. No usa `100-riesgo`; el `ConversationProfile.LeadScore` existente se conserva. La clasificación de costos exige intención explícita y monto ligado a una respuesta confirmada; «documentos para matrícula» y un año suelto no activan el mínimo80.

## Operación implementada y frontera de transporte

`GET/POST /api/v1/crm/predictions`, `/api/v1/campaigns/settings`, `/remarketing`, `/templates`, `/templates/sync`, `/runs` y `/api/v1/broadcasts` exponen lectura, configuración, CRUD, pausa, audiencia y preparación. Se reutiliza la guarda local de host/origen/cabecera del CRM; no se presenta como autenticación multiusuario de producción. Sin migración hay respuesta explícita de infraestructura pendiente.

El worker reclama un `EvaluationRun` mediante la transacción/bloqueo local, confirma lease vigente antes de procesar y recupera trabajos interrumpidos con límite de intentos. Procesa como máximo 200 conversaciones o 500 identidades por operación, sin truncar silenciosamente. La política pausa evaluaciones periódicas; las operaciones manuales siguen explícitas. Las reglas filtran etapa actual e inactividad desde respuesta confirmada, **no antigüedad real en etapa**: esa fecha no existe en el historial y se informa desconocida. Cooldown limita preparaciones locales, sin acreditarlo como hora de envío.

El transporte marketing está bloqueado por código, sin ajuste API/UI/entorno que lo active. Los endpoints activate/start/send responden423. Ningún camino de este módulo inserta `crm.Message` ni `outbound_queue`; existe defensa adicional del dispatcher al reclamar y antes del POST para QueueId asociado a campaña o payload de marketing. El transporte humano/IA existente conserva sus propias guardas.

La sincronización de plantillas es un GET acotado de Meta con credencial cifrada ya existente, iniciado sólo por acción explícita. Se pagina por cursor validado en el host fijo; no se sigue una URL arbitraria devuelta por el proveedor. Un token vencido no produce plantillas ficticias. El módulo no crea grants de consentimiento ni identidades para poblar una audiencia vacía.

## Contrato pendiente antes de envíos reales

La futura selección no ejecuta envíos. Debe deduplicar destinatarios y revalidar inclusión exacta, período/oferta, campaña/rule/epochs, consentimiento marketing vigente, no-contacto por todos los contactos históricos y control humano antes de encolar **en la outbox existente**. `noContact=false` no es opt-in. Una baja gana y cancela pendientes; pausa de campaña incrementa epoch y bloquea nuevos POST. Un control humano no se elude con otra clasificación de actor.

Antes de **cada POST**, el dispatcher deberá repetir las comprobaciones y validar plantilla aprobada/no pausada en la cuenta, nombre/idioma/version/componentes, ventana y permisos actuales. Así se invalida un destinatario que era elegible al inscribirse pero dejó de serlo. No se mantienen locks durante red. Un POST de resultado incierto conserva estado uncertain y requiere reconciliación; no crear otra cola ni duplicar destinatario para repetirlo. Attempts del destinatario cubre selección/preparación; el transporte sigue siendo del dispatcher existente, sin un segundo bucle de reintentos externos.

La reserva de `AccountCadence` se hará atómicamente por cuenta y entre campañas, con ventana UTC de 24 horas, cupo y `NextAllowedAtUtc` persistidos; una reserva ya usada/resultado incierto no se libera para gastar otra vez el mismo cupo. Los límites operativos son adicionales a los impuestos por Meta y no garantizan ausencia de penalizaciones. No hay scheduler ni reservas reales en este corte.

Fuentes primarias suministradas por el coordinador para la futura integración: la [política de WhatsApp Business](https://whatsappbusiness.com/policy/) establece opt-in, respeto al opt-out y plantillas aprobadas fuera de la ventana de atención; referencia con revisión del 23 de septiembre de 2026. El [ejemplo oficial de Meta](https://github.com/fbsamples/whatsapp-api-examples/blob/main/send-messages-flight-app-python/message_helper.py) muestra estructura de envío de plantilla, no prueba permisos, aprobación ni cumplimiento de esta aplicación. No se reutiliza la categoría histórica `TRANSACTIONAL` como contrato vigente. Esta unidad no hizo llamadas a Meta ni verificó cuentas, plantillas o envíos reales.

**Pendiente conectado:** aceptación/calibración de rúbricas con evidencia suficiente, gestión operativa de opt-in/opt-out real, plantillas/credenciales vigentes comprobadas, reserva efectiva de cadencia, reconciliación de envíos inciertos y revalidación completa de transporte. Las capacidades locales implementadas no acreditan envíos, cumplimiento global ni un Sprint5 conectado completo.
