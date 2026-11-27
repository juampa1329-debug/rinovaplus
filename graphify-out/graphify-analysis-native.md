> Tokens del host/subagentes no medidos; los ceros siguientes son placeholders.

# Graph Report - .  (2026-11-27)

## Corpus Check
- 81 files · ~40,559 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 802 nodes · 1360 edges · 44 communities (42 shown, 2 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 62 edges (avg confidence: 0.82)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- workspace.py
- Gestión de campañas
- Seguimiento por tiempo y lista
- Espacio institucional
- Auditoría integral de fichas y
- Seguimiento comercial
- Avance comercial y exclusiones
- Precios recuperados, comentarios y escala
- Eventos y recibos entrantes
- Formularios, orientación de pago y
- Panel de campañas y seguimiento
- Panel de mensajería masiva
- Becas opcionales y valor de
- program commercial.py
- Guardado concurrente y baja expresa
- Importación de prospectos
- broadcast dispatch.py
- admissions prompt.py
- Tres seguimientos por avance activados
- Seguimiento y preferencias
- Memoria comercial
- Contrato y límites SIIE
- Importación del lote 2026
- Políticas de campañas
- Motores por etapa
- Campaña PRE-ICFES y destinos
- Piloto y recepción SIIE
- Diagnóstico de listas
- Informe y consultas agregadas
- Horarios y costes
- Panel de mensajería masiva
- Respuesta y entrada al Inbox
- Ediciones y remitentes
- Prospectos y promoción PRE-ICFES
- Campañas por programa
- Espera interna y continuidad
- Recuperación de respuestas
- Política de abono inicial
- Contención de almacenamiento
- Intereses en clases abiertas
- Preparación del receptor SIIE
- BroadcastProspectSetup.tsx
- Métricas de campañas
- Promoción y bandeja entrante

## God Nodes (most connected - your core abstractions)
1. `Seguimiento por tiempo y lista No contactar —27Nov2026` - 29 edges
2. `rows()` - 28 edges
3. `Workspace` - 23 edges
4. `Campaigns` - 19 edges
5. `Guardado concurrente y baja expresa —27Nov2026` - 19 edges
6. `event()` - 18 edges
7. `Evidencia posterior de seguimiento —27Nov2026` - 18 edges
8. `Becas opcionales y valor de la formación en mensajería —27Nov2026` - 18 edges
9. `key()` - 17 edges
10. `Precios recuperados, comentarios y escala del Dashboard — 26Nov2026` - 17 edges

## Surprising Connections (you probably didn't know these)
- `CRM FOLLOWUPS 20261124` --conceptually_related_to--> `crm-followups-20261124`  [INFERRED]
  docs/adaptation/CRM_FOLLOWUPS_20261124.md → artifacts/live/crm-followups-20261124.json
- `Tres seguimientos por avance activados —27Nov2026` --conceptually_related_to--> `Evidencia agregada de activación de tres seguimientos —27Nov2026`  [INFERRED]
  docs/adaptation/ADVANCED_FOLLOWUP_ACTIVATION_20261127.md → artifacts/live/advanced-followup-activation-20261127.json
- `Formularios, orientación de pago y cierre a siete días —27Nov2026` --conceptually_related_to--> `Evidencia agregada de formularios, pago y cierre de siete días`  [INFERRED]
  docs/adaptation/FORM_PAYMENT_CLOSURE_FOLLOWUP_20261127.md → artifacts/live/form-payment-closure-followup-20261127.json
- `Cierre vigente de siete días sustituye duración final anterior` --references--> `Cierre a siete días conserva los pasos de ocho, treinta y seis y sesenta horas`  [EXTRACTED]
  artifacts/live/form-payment-closure-followup-20261127.json → docs/adaptation/FORM_PAYMENT_CLOSURE_FOLLOWUP_20261127.md
- `Becas opcionales y valor de la formación en mensajería —27Nov2026` --conceptually_related_to--> `Evidencia agregada de valor de programas y borradores —27Nov2026`  [INFERRED]
  docs/adaptation/PROGRAM_VALUE_MESSAGING_20261127.md → artifacts/live/program-value-messaging-20261127.json

## Import Cycles
- None detected.

## Communities (44 total, 2 thin omitted)

### Community 0 - "workspace.py"
Cohesion: 0.06
Nodes (37): merge_contact_edit(), Three-way CRM edits: only the operator's changed fields, under writer lock., Unrelated activity is harmless; concurrent edits to the same value conflict.…, no_contact_list(), NoContactWrite, field_validator, Strict, Canonical no-contact status and explicit operator-confirmed opt-out. (+29 more)

### Community 1 - "Gestión de campañas"
Cohesion: 0.11
Nodes (40): install(), Institutional P8 routes; no legacy campaign router or second sender., Shorten the general silence closure without replaying completed steps., shorten(), target(), version(), waiting_due(), install() (+32 more)

### Community 2 - "Seguimiento por tiempo y lista"
Cohesion: 0.06
Nodes (46): Sustitución temporal acotada al estado avanzado anterior, Rechazo automático de activación adicional conservado, Tres recorridos avanzados en borrador versión dos, Estado de biblioteca de las tres plantillas de avance, Borradores evitan duplicar espera de ocho horas, Cierre de veintiún días aprobado por Meta, Sin nuevas aceptaciones, autorizaciones artificiales o replay, Pruebas focalizadas pasan con ocho fallos heredados (+38 more)

### Community 3 - "Espacio institucional"
Cohesion: 0.08
Nodes (38): contactConflicts(), fields, rebaseReviewedContact(), ContactPreference(), NoContactList(), Activity(), AssigneePicker(), ContactEditor() (+30 more)

### Community 4 - "Auditoría integral de fichas y"
Cohesion: 0.06
Nodes (38): Duraciones y jornadas académicas confirmadas, Disponibilidad preservada y páginas vigentes preparadas, Folletos y aclaraciones expresas del titular, Duraciones, jornadas y herencia de modelos — 26Nov2026, Herencia del motor y necesidad comercial, A1 y A2 juntos; idiomas adicionales y TIC sin completar, Pendientes reales y presentación de Multimedia rechazada, Veinte fichas actualizadas con importes conservados (+30 more)

### Community 5 - "Seguimiento comercial"
Cohesion: 0.11
Nodes (31): analytics(), contact_details(), details(), gender(), incoming_bucket(), matches(), normalized(), Declared CRM segmentation and preparation-time campaign statistics. No… (+23 more)

### Community 6 - "Avance comercial y exclusiones"
Cohesion: 0.08
Nodes (32): campaign-launch-2026-20261126, Evidencia26Nov:55activas y2461números únicos, Evidencia26Nov:36recibosentrega,1lectura,10fallos, Evidencia25Nov:61clasificados y61tareas, Evidencia25Nov:3flujos por caso siguenBorradorv1, commercial-progress-followup-20261125, Evidencia25Nov:no transición automática nueva acreditada, Cadencia autorizada 3000 por24horas y30segundos (+24 more)

### Community 7 - "Precios recuperados, comentarios y escala"
Cohesion: 0.06
Nodes (32): Gráfica fija con escala adaptativa publicada, Aceptación canónica e iniciales conservadas, Acuse público automático con privado aceptado durable, Precios recuperados, comentarios y escala del Dashboard — 26Nov2026, Recuperación acotada de lectura del Inbox, Grafo de desarrollo separado de memoria privada, Publicación comprobada con límites y fallos heredados, Ensayo real de Cocina validado sin envío ni CRM (+24 more)

### Community 8 - "Eventos y recibos entrantes"
Cohesion: 0.13
Nodes (25): advisor_entry(), contextual_entry(), enrich(), entry_turn(), origin(), A signed reply to accepted campaign outreach can start a commercial AI turn., The verified button also applies to confirmed or manually assigned agents., observe() (+17 more)

### Community 9 - "Formularios, orientación de pago y"
Cohesion: 0.11
Nodes (25): Límites públicos del ajuste y clasificación, Clasificación autenticada distingue pago concreto y pregunta general, Despliegue final bc2dade comprobado antes de la acción, Evidencia agregada de formularios, pago y cierre de siete días, Detalle humano final y crecimiento posterior separados de la migración, Configuración y muestra productiva posteriores al ajuste, Validación focalizada sin afirmar suite completa verde, Acción nativa acotada con autorización reciente, revisión y CAS (+17 more)

### Community 10 - "Panel de campañas y seguimiento"
Cohesion: 0.10
Nodes (23): Binding, blank(), CampaignWorkspace(), Doc, Editor(), emptyFilters(), Executions(), FilterEditor() (+15 more)

### Community 11 - "Panel de mensajería masiva"
Cohesion: 0.09
Nodes (15): Binding, Cadence, Campaign, Component, Document, Identity, Options, Preview (+7 more)

### Community 12 - "Becas opcionales y valor de"
Cohesion: 0.14
Nodes (21): Evidencia agregada de valor de programas y borradores —27Nov2026, Tres registros CRM persisten como borradores sin envíos, Límites declarados por el titular para ROI e investigación, Estilo central versión ocho y hechos citables publicados, Referencias de seguimientos activos conservadas, Cero resultados institucionales no prueba inexistencia de convenios, Validación y despliegue final sin efecto generativo nuevo, Sin nuevas operaciones comerciales o aceptaciones (+13 more)

### Community 13 - "program commercial.py"
Cohesion: 0.14
Nodes (17): agent_facts(), approved_url(), CommercialProfile, ExtractedProgram, FinancialInstallment, FinancialPlan, import_program(), ImportUrl (+9 more)

### Community 14 - "Guardado concurrente y baja expresa"
Cohesion: 0.13
Nodes (21): 75 comprobaciones backend focalizadas pasan, Publicación preserva contribuciones de seguimiento, Backend saludable y frontend publicado, Borrador y base sobreviven lecturas y navegación, Evidencia: concurrency, Evidencia: deployments, Evidencia agregada del guardado y baja —27Nov2026, Evidencia: limitations (+13 more)

### Community 15 - "Importación de prospectos"
Cohesion: 0.14
Nodes (15): ConsentRestore, Audited correction of an initial clerical revocation; never grants sending., restore(), link(), prior_opt_out(), ProspectSetup, model_validator, Explicit outbound WhatsApp onboarding for reviewed imported CRM prospects. (+7 more)

### Community 16 - "broadcast dispatch.py"
Cohesion: 0.14
Nodes (13): configuration(), actor_allowed(), check(), A bounded campaign producer using the existing C10 queue and dispatcher., ready(), record(), Worker, Move CRM stage only after a real Meta sent/delivered/read receipt. (+5 more)

### Community 17 - "admissions prompt.py"
Cohesion: 0.15
Nodes (12): facts_for(), Small editorial review of public institutional sources; never a financial…, Same approved facts in context, returned metadata and citation validation., reviewed_sources(), A presentation name and concise Colombian Spanish, without a false human…, AdmissionsPolicy, AdmissionsReply, assemble_prompt() (+4 more)

### Community 18 - "Tres seguimientos por avance activados"
Cohesion: 0.16
Nodes (18): Evidencia agregada de activación de tres seguimientos —27Nov2026, Sin inscripción manual, reintento incierto o entrega nueva acreditada, Flujos nativos: tres activos con un paso y espera interna cero, Exclusión No contactar en alcance canónico y ventana real, Estados activos y lista de bajas observados sin alerta, Plantillas nativas: tres activas y dos activaciones nuevas, Activadores nativos: tres activos con prioridad por avance, Operación de configuración sin código ni nuevas aceptaciones (+10 more)

### Community 19 - "Seguimiento y preferencias"
Cohesion: 0.17
Nodes (16): crm-followups-20261124, Evidencia24Nov:flujoyactivador activosv2, Evidencia24Nov:NoContactcanónico verificado, Evidencia24Nov:22de24hilos conrecibos, Flujo y activador Activo v2 al24Nov, Recorrido8h,36h,60h y21d desde salida de referencia, CRM FOLLOWUPS 20261124, Sólo seguimiento de personas que ya conversaron (+8 more)

### Community 20 - "Memoria comercial"
Cohesion: 0.27
Nodes (15): concrete_goal(), context(), current_facts(), graph(), qualification(), Durable, conversation-bound commercial observations with quoted provenance., A reference to a remembered goal is not a new statement of that goal., Model labels are inferences; the stored value is always an exact incoming quote. (+7 more)

### Community 21 - "Contrato y límites SIIE"
Cohesion: 0.14
Nodes (16): Continuidad parcial sólo con aceptación acreditada, Identidad más reciente y ventana real del canal, Imágenes entrantes inspeccionadas y ligadas al hilo, Continuidad del contexto y mensajes con imágenes, Lecturas PostgreSQL REPEATABLE READ READ ONLY, Reconstrucción de turno sobre entrada autenticada vigente, Cambios reales de contexto siguen invalidando salida, Inbox · Descarte tras guardar el interés del cliente (+8 more)

### Community 22 - "Importación del lote 2026"
Cohesion: 0.17
Nodes (12): Evidenciainicial26Nov:55borradores yMeta5/14, crm-import-2026-20261126, Evidenciainicial26Nov:2620fichasnuevas, CRM IMPORT 2026 20261126, 55campañasBorradorv2 antes del lanzamiento, 2026xls:2620fichas nuevas de3992filas, 550posibles coincidencias CRM, Corte inicial Meta5aprobadas14en revisión (+4 more)

### Community 23 - "Políticas de campañas"
Cohesion: 0.27
Nodes (7): history_digest(), layout(), parent_digest(), partition(), Closed P8 authority on a native copy; historical profiles stay unchanged., release(), verify()

### Community 24 - "Motores por etapa"
Cohesion: 0.22
Nodes (10): Atención social y cupos por cuenta, Motores activos y atención de comentarios, Motores de IA activos · corte 25Nov, Piloto nota de voz e imagen · tres partes Leídas, Recuperación social sin replay, P22 sin aceptación comercial nueva · corte 25Nov, Herencia de agentes conservando memoria y permisos, Motor de agentes por etapa y margen de salida (+2 more)

### Community 25 - "Campaña PRE-ICFES y destinos"
Cohesion: 0.22
Nodes (9): preicfes-campaign-launch-20261125, Evidencia25Nov:PREICFES100fichas,102destinos, EvidenciainicialPREICFESsinentregatotal, Rutas alternas exactas con consentimiento por identidad, CadenciaPREICFES1000por24h30s en corte25Nov, PREICFEScorteinicial:1entrega y97preparados principales, PREICFES CAMPAIGN LAUNCH 20261125, PREICFES100principales+2alternativos activados25Nov (+1 more)

### Community 26 - "Piloto y recepción SIIE"
Cohesion: 0.22
Nodes (9): Catálogos resueltos no acreditan emisor ni pagos, Catálogos nativos R7 consultados · corte25Nov, Valores e IDs nativos sin inventar ni fusionar, P23 · Catálogos R7 de inscripción, Firma válida con reloj emisor adelantado, sin ampliar300s, Ensayo público PRE-ICFES y recepción firmada, Piloto parcial no acepta P23 ni acredita volante, Primera recepción SIIE real confirmada ·25Nov19:17Bogotá (+1 more)

### Community 27 - "Diagnóstico de listas"
Cohesion: 0.22
Nodes (9): P24 diagnóstico de listas: implementación0%, aceptación0/6, P24 — Diagnóstico de listas de conversaciones, mensajes y contactos, Propuestas de listado, historial y adjuntos pendientes, Optimizar conserva autorización, límites e idempotencia, Diagnóstico de voz: cupo y duración son causas separadas, Espera configurada60s distinta de cola y generación, P24 — Inicio, carga del Inbox y capacidad de atención, Línea base representativa y carga institucional pendientes (+1 more)

### Community 28 - "Informe y consultas agregadas"
Cohesion: 0.25
Nodes (8): Diseño de acceso integrado sin perder contratos, Revisión de logos y acceso institucional, Comprobación de acceso local y productiva, Respuesta atribuida exige context.id exacto, Informe de campañas: consulta agotada y revisión de diseño, Informe de campañas con agregación por cuenta, Consulta agregada419–435ms · muestra 25Nov, Recepción SIIE habilitada sin eventos · corte previo

### Community 29 - "Horarios y costes"
Cohesion: 0.25
Nodes (8): Aclarar plan de estudios versus costo deestudiar, 27fichas y51planes auditados, Botón nativoverificado recupera interés de campaña, PROGRAM HOURS AND COST SCOPE 20261124, InglésA1+A2enunsolo semestre, 24fichas con jornada definidarecargada, Horariospendientes yfallos noresueltos universalmente, PREICFESG1sábado7–12,G2sábado13–18,G3domingo7–12

### Community 30 - "Panel de mensajería masiva"
Cohesion: 0.29
Nodes (7): blank(), CampaignEditor(), CampaignReport(), label(), RecipientDeliveryDialog(), variableKeys(), StepEditor()

### Community 31 - "Respuesta y entrada al Inbox"
Cohesion: 0.33
Nodes (6): Botón comercial Hablar con Juan Pablo, Ficha vigente prevalece sobre precio histórico de campaña, CAMPAIGN ADVISOR ENTRY 20261124, Contexto autenticado de campaña, Entrada real incorpora conversación al Inbox, Inicio comercial publicado b3e68e2

### Community 32 - "Ediciones y remitentes"
Cohesion: 0.33
Nodes (6): Vista previa usa autor real de salida, INBOX EDITS SENDERS PREICFES 20261125, Ediciones verificadas conservan original inmutable, Nueva edición automática endtoend pendiente, Especialista PREICFESv2 con37skills ymemoria, Duración de voz120s ycuota5porhilo

### Community 33 - "Prospectos y promoción PRE-ICFES"
Cohesion: 0.33
Nodes (6): Fechas de solicitud ausentes conservadas vacías, PREICFES PROSPECTS 20261125, PREICFESBorradorv1 yMetaenrevisión en corte previo, SolicitudesPREICFES:100fichas y1revisión, 5grupos ambiguos iniciales, Promoción PREICFES también con financiación

### Community 34 - "Campañas por programa"
Cohesion: 0.33
Nodes (6): Corte17campañas:57entregas incluidas6lecturas, PROGRAM CAMPAIGNS 20261124, Refresco decatálogo GETpara campañas largas, 17campañasactivadas con704números únicos24Nov, Detallehumano deenvío conserva mensaje yestadoactual, 18borradoresNoenviar para213casos

### Community 35 - "Espera interna y continuidad"
Cohesion: 0.50
Nodes (5): Cobertura de turnos exige todas las partes aceptadas, Diagnóstico SQL sin parámetros ni cuerpos privados, Espera de almacenamiento previa al efecto externo, Inbox: espera interna, continuidad y fechas confirmadas — 25Nov2026, PRE-ICFES revisión7 · corte 25Nov

### Community 36 - "Recuperación de respuestas"
Cohesion: 0.40
Nodes (5): Recuperación de atención y contexto del Inbox — 25 de noviembre de 2026, LímiteHTTP600 por minuto y usuario, Orientaciones nuevas y controles IA restaurados, Reacciones citadas y transcripción ya guardada, Recuperación breve por truncamiento y respaldos aprobados

### Community 37 - "Política de abono inicial"
Cohesion: 0.50
Nodes (4): HIGHER INITIAL PAYMENT POLICY 20261124, Menor abono vigente para presentación inicial, Puede adelantar inscripción mientras revisan financiación, Abono distinto exige revisión de Tesorería

### Community 38 - "Contención de almacenamiento"
Cohesion: 0.50
Nodes (4): Cinco cargas nativas satisfactorias · corte24Nov, GET agrupado recuperable, sin repetir mutaciones, Inbox: contención de almacenamiento · 24 de noviembre de 2026, Seguimientos liberan bloqueo entre contactos y etapas

### Community 39 - "Intereses en clases abiertas"
Cohesion: 0.50
Nodes (4): MASTERCLASS INTERESTS 20261124, Elección explícita del contacto prevalece, Propuesta de programas relacionados con masterclasses, Revisión por grupos y lotesde10

### Community 40 - "Preparación del receptor SIIE"
Cohesion: 0.67
Nodes (4): P23 · Preparación de RinovaPlus para el webhook SIIE, P23 preparación no acepta fase ni emite pagos, P23 preparación y configuración guardada separada, Vínculo SIIE exige revisión de snapshot vigente

### Community 41 - "BroadcastProspectSetup.tsx"
Cohesion: 0.50
Nodes (3): BroadcastProspectSetup(), Bundle, Route

## Knowledge Gaps
- **241 isolated node(s):** `Component`, `Template`, `Binding`, `Document`, `Campaign` (+236 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `reasons()` connect `Gestión de campañas` to `Seguimiento comercial`, `Importación de prospectos`?**
  _High betweenness centrality (0.001) - this node is a cross-community bridge._
- **Why does `promotion_exclusion()` connect `Importación de prospectos` to `Eventos y recibos entrantes`?**
  _High betweenness centrality (0.000) - this node is a cross-community bridge._
- **What connects `Component`, `Template`, `Binding` to the rest of the system?**
  _241 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `workspace.py` be split into smaller, more focused modules?**
  _Cohesion score 0.058385093167701865 - nodes in this community are weakly interconnected._
- **Should `Gestión de campañas` be split into smaller, more focused modules?**
  _Cohesion score 0.10912190963341858 - nodes in this community are weakly interconnected._
- **Should `Seguimiento por tiempo y lista` be split into smaller, more focused modules?**
  _Cohesion score 0.06382978723404255 - nodes in this community are weakly interconnected._
- **Should `Espacio institucional` be split into smaller, more focused modules?**
  _Cohesion score 0.07729468599033816 - nodes in this community are weakly interconnected._