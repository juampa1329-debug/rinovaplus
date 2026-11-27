> Tokens del host/subagentes no medidos; los ceros siguientes son placeholders.

# Graph Report - .  (2026-11-27)

## Corpus Check
- 88 files · ~42,177 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 887 nodes · 1512 edges · 51 communities (49 shown, 2 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 71 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Gestión de campañas
- workspace.py
- Diagnóstico de listas
- Eventos y recibos entrantes
- Seguimiento por tiempo y lista
- Seguimiento comercial
- Avance comercial y exclusiones
- Formularios, orientación de pago y
- Panel de campañas y seguimiento
- Becas opcionales y valor de
- Guardado concurrente y baja expresa
- Panel de mensajería masiva
- program commercial.py
- Importación de prospectos
- Baja global y negociación con
- Tres seguimientos por avance activados
- Precios recuperados, comentarios y escala
- Seguimiento y preferencias
- Memoria comercial
- Contrato y límites SIIE
- Continuidad del Inbox, voces y
- Evidencia agregada de baja global
- skill policy.py
- Información pendiente por programa —
- Auditoría integral de fichas y
- Importación del lote 2026
- Duraciones, jornadas y herencia de
- Políticas de campañas
- admissions prompt.py
- Motores por etapa
- Campaña PRE-ICFES y destinos
- Piloto y recepción SIIE
- cbn profile.py
- Informe y consultas agregadas
- Horarios y costes
- voice transcripts.py
- Panel de mensajería masiva
- Respuesta y entrada al Inbox
- Ediciones y remitentes
- Prospectos y promoción PRE-ICFES
- Campañas por programa
- Preferencias y exclusiones
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
3. `Baja global y negociación con beneficios verificados — 27Nov2026` - 28 edges
4. `Workspace` - 23 edges
5. `event()` - 21 edges
6. `key()` - 20 edges
7. `Campaigns` - 19 edges
8. `Guardado concurrente y baja expresa —27Nov2026` - 19 edges
9. `Evidencia posterior de seguimiento —27Nov2026` - 18 edges
10. `Becas opcionales y valor de la formación en mensajería —27Nov2026` - 18 edges

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

## Communities (51 total, 2 thin omitted)

### Community 0 - "Gestión de campañas"
Cohesion: 0.06
Nodes (68): Immediate canonical suppression from attributable customer input, without LLM…, receive(), supported(), configuration(), check(), install(), Institutional P8 routes; no legacy campaign router or second sender., Shorten the general silence closure without replaying completed steps. (+60 more)

### Community 1 - "workspace.py"
Cohesion: 0.07
Nodes (29): merge_contact_edit(), Three-way CRM edits: only the operator's changed fields, under writer lock., Unrelated activity is harmless; concurrent edits to the same value conflict.…, active_user(), Command, ContactWrite, ControlWrite, ConversationRead (+21 more)

### Community 2 - "Diagnóstico de listas"
Cohesion: 0.06
Nodes (47): P24 diagnóstico de listas: implementación0%, aceptación0/6, P24 — Diagnóstico de listas de conversaciones, mensajes y contactos, Propuestas de listado, historial y adjuntos pendientes, Optimizar conserva autorización, límites e idempotencia, Diagnóstico de voz: cupo y duración son causas separadas, Espera configurada60s distinta de cola y generación, P24 — Inicio, carga del Inbox y capacidad de atención, Línea base representativa y carga institucional pendientes (+39 more)

### Community 3 - "Eventos y recibos entrantes"
Cohesion: 0.06
Nodes (32): Drain old authenticated opt-outs one at a time; one idle scan per minute., Reconciler, advisor_entry(), contextual_entry(), enrich(), entry_turn(), origin(), A signed reply to accepted campaign outreach can start a commercial AI turn. (+24 more)

### Community 4 - "Seguimiento por tiempo y lista"
Cohesion: 0.06
Nodes (46): Sustitución temporal acotada al estado avanzado anterior, Rechazo automático de activación adicional conservado, Tres recorridos avanzados en borrador versión dos, Estado de biblioteca de las tres plantillas de avance, Borradores evitan duplicar espera de ocho horas, Cierre de veintiún días aprobado por Meta, Sin nuevas aceptaciones, autorizaciones artificiales o replay, Pruebas focalizadas pasan con ocho fallos heredados (+38 more)

### Community 5 - "Seguimiento comercial"
Cohesion: 0.11
Nodes (30): analytics(), contact_details(), details(), gender(), incoming_bucket(), matches(), normalized(), Declared CRM segmentation and preparation-time campaign statistics. No… (+22 more)

### Community 6 - "Avance comercial y exclusiones"
Cohesion: 0.08
Nodes (32): campaign-launch-2026-20261126, Evidencia26Nov:55activas y2461números únicos, Evidencia26Nov:36recibosentrega,1lectura,10fallos, Evidencia25Nov:61clasificados y61tareas, Evidencia25Nov:3flujos por caso siguenBorradorv1, commercial-progress-followup-20261125, Evidencia25Nov:no transición automática nueva acreditada, Cadencia autorizada 3000 por24horas y30segundos (+24 more)

### Community 7 - "Formularios, orientación de pago y"
Cohesion: 0.11
Nodes (25): Límites públicos del ajuste y clasificación, Clasificación autenticada distingue pago concreto y pregunta general, Despliegue final bc2dade comprobado antes de la acción, Evidencia agregada de formularios, pago y cierre de siete días, Detalle humano final y crecimiento posterior separados de la migración, Configuración y muestra productiva posteriores al ajuste, Validación focalizada sin afirmar suite completa verde, Acción nativa acotada con autorización reciente, revisión y CAS (+17 more)

### Community 8 - "Panel de campañas y seguimiento"
Cohesion: 0.10
Nodes (23): Binding, blank(), CampaignWorkspace(), Doc, Editor(), emptyFilters(), Executions(), FilterEditor() (+15 more)

### Community 9 - "Becas opcionales y valor de"
Cohesion: 0.13
Nodes (22): Evidencia agregada de valor de programas y borradores —27Nov2026, Tres registros CRM persisten como borradores sin envíos, Límites declarados por el titular para ROI e investigación, Estilo central versión ocho y hechos citables publicados, Referencias de seguimientos activos conservadas, Cero resultados institucionales no prueba inexistencia de convenios, Validación y despliegue final sin efecto generativo nuevo, Sin nuevas operaciones comerciales o aceptaciones (+14 more)

### Community 10 - "Guardado concurrente y baja expresa"
Cohesion: 0.12
Nodes (22): 75 comprobaciones backend focalizadas pasan, Publicación preserva contribuciones de seguimiento, Backend saludable y frontend publicado, Borrador y base sobreviven lecturas y navegación, Evidencia: concurrency, Evidencia: deployments, Evidencia agregada del guardado y baja —27Nov2026, Evidencia: limitations (+14 more)

### Community 11 - "Panel de mensajería masiva"
Cohesion: 0.09
Nodes (15): Binding, Cadence, Campaign, Component, Document, Identity, Options, Preview (+7 more)

### Community 12 - "program commercial.py"
Cohesion: 0.14
Nodes (17): agent_facts(), approved_url(), CommercialProfile, ExtractedProgram, FinancialInstallment, FinancialPlan, import_program(), ImportUrl (+9 more)

### Community 13 - "Importación de prospectos"
Cohesion: 0.14
Nodes (15): ConsentRestore, Audited correction of an initial clerical revocation; never grants sending., restore(), link(), prior_opt_out(), ProspectSetup, model_validator, Explicit outbound WhatsApp onboarding for reviewed imported CRM prospects. (+7 more)

### Community 14 - "Baja global y negociación con"
Cohesion: 0.10
Nodes (20): Baja entrante y exclusiones · Las solicitudes automáticas llevan prueba de origen y no inventan un operador, Baja entrante y exclusiones · backend/app/institutional/voice_transcripts.py aplica la misma regla después de guardar una transcri, Baja entrante y exclusiones · La recuperación histórica recorre sólo eventos opt_out de entrada autenticada atribuibles a un mensa, Baja entrante y exclusiones · Cuando no quedan esos eventos, la misma recuperación busca una conversación abierta de una persona q, Baja entrante y exclusiones · El alcance entre canales requiere identidades vinculadas a la misma ficha, Becas y conversación comercial · Lectura nativa de siete ofertas pertinentes: Cocina nocturna, Repostería, Barismo/Bartender, Turismo, Becas y conversación comercial · Se identificó otra omisión: la proyección de hechos para financiación/objeciones retiraba presentati, Becas y conversación comercial · La política común obliga a conectar la beca pertinente con la meta, presentar el plazo real entre ab (+12 more)

### Community 15 - "Tres seguimientos por avance activados"
Cohesion: 0.16
Nodes (18): Evidencia agregada de activación de tres seguimientos —27Nov2026, Sin inscripción manual, reintento incierto o entrega nueva acreditada, Flujos nativos: tres activos con un paso y espera interna cero, Exclusión No contactar en alcance canónico y ventana real, Estados activos y lista de bajas observados sin alerta, Plantillas nativas: tres activas y dos activaciones nuevas, Activadores nativos: tres activos con prioridad por avance, Operación de configuración sin código ni nuevas aceptaciones (+10 more)

### Community 16 - "Precios recuperados, comentarios y escala"
Cohesion: 0.12
Nodes (17): Aceptación canónica e iniciales conservadas, Acuse público automático con privado aceptado durable, Precios recuperados, comentarios y escala del Dashboard — 26Nov2026, Recuperación acotada de lectura del Inbox, Grafo de desarrollo separado de memoria privada, Publicación comprobada con límites y fallos heredados, Ensayo real de Cocina validado sin envío ni CRM, Ensayo institucional y contrato manual acotados (+9 more)

### Community 17 - "Seguimiento y preferencias"
Cohesion: 0.17
Nodes (16): crm-followups-20261124, Evidencia24Nov:flujoyactivador activosv2, Evidencia24Nov:NoContactcanónico verificado, Evidencia24Nov:22de24hilos conrecibos, Flujo y activador Activo v2 al24Nov, Recorrido8h,36h,60h y21d desde salida de referencia, CRM FOLLOWUPS 20261124, Sólo seguimiento de personas que ya conversaron (+8 more)

### Community 18 - "Memoria comercial"
Cohesion: 0.27
Nodes (15): concrete_goal(), context(), current_facts(), graph(), qualification(), Durable, conversation-bound commercial observations with quoted provenance., A reference to a remembered goal is not a new statement of that goal., Model labels are inferences; the stored value is always an exact incoming quote. (+7 more)

### Community 19 - "Contrato y límites SIIE"
Cohesion: 0.14
Nodes (16): Continuidad parcial sólo con aceptación acreditada, Identidad más reciente y ventana real del canal, Imágenes entrantes inspeccionadas y ligadas al hilo, Continuidad del contexto y mensajes con imágenes, Lecturas PostgreSQL REPEATABLE READ READ ONLY, Reconstrucción de turno sobre entrada autenticada vigente, Cambios reales de contexto siguen invalidando salida, Inbox · Descarte tras guardar el interés del cliente (+8 more)

### Community 20 - "Continuidad del Inbox, voces y"
Cohesion: 0.13
Nodes (15): Gráfica fija con escala adaptativa publicada, Tres adquisiciones acotadas sin repetir cuerpo, Destinatario e inactividad con revalidación exacta, Contención y envíos inciertos conservados, Continuidad del Inbox, voces y gráfica — 26 de noviembre de 2026, Publicación final sin respuesta automática posterior acreditada, Checkpoint humano permite continuar entradas posteriores, Supervisor cada treinta minutos sólo propuesto (+7 more)

### Community 21 - "Evidencia agregada de baja global"
Cohesion: 0.14
Nodes (14): Evidencia: academic_audit, Evidencia: automatic_optout, Evidencia: commits, Evidencia: date, Evidencia: deployments, Evidencia agregada de baja global y negociación, Evidencia: institution_dna, Evidencia: native_verification (+6 more)

### Community 22 - "skill policy.py"
Cohesion: 0.23
Nodes (12): for_turn(), from_messages(), instructions(), project_facts(), prompt_trace(), Server-owned turn policy for customer-facing AI, independent of the provider.…, Transmit guide IDs and one fingerprint; retain full provenance in the audit., Trace from the server-built evidence envelope, never an LLM claim. (+4 more)

### Community 23 - "Información pendiente por programa —"
Cohesion: 0.15
Nodes (13): Veinticuatro ofertas activas y tres pausadas, Fechas y alcance semestral o curso completo, Precios actuales completos; recuperación es otro problema, Calendarios, prácticas y cinco mallas por completar, Títulos y reconocimiento específico pendientes, Información pendiente por programa — 26 de noviembre de 2026, Niveles superiores e idiomas no vigentes por confirmar, Franjas y prácticas conocidas con límites (+5 more)

### Community 24 - "Auditoría integral de fichas y"
Cohesion: 0.18
Nodes (13): Horarios parciales y contenidos conservados, Alias revisados sin asignar jornada ni matrícula, Descarte autorizado de borrador sin eludir revisión, Nueve abonos mayores corregidos y releídos, Auditoría integral de fichas y nombres de búsqueda — 26Nov2026, Editor con diagnóstico seguro y normalización booleana, Tarifas de Salud, Gastronomía y PRE, Veintisiete fichas nativas auditadas (+5 more)

### Community 25 - "Importación del lote 2026"
Cohesion: 0.17
Nodes (12): Evidenciainicial26Nov:55borradores yMeta5/14, crm-import-2026-20261126, Evidenciainicial26Nov:2620fichasnuevas, CRM IMPORT 2026 20261126, 55campañasBorradorv2 antes del lanzamiento, 2026xls:2620fichas nuevas de3992filas, 550posibles coincidencias CRM, Corte inicial Meta5aprobadas14en revisión (+4 more)

### Community 26 - "Duraciones, jornadas y herencia de"
Cohesion: 0.17
Nodes (12): Duraciones y jornadas académicas confirmadas, Disponibilidad preservada y páginas vigentes preparadas, Folletos y aclaraciones expresas del titular, Duraciones, jornadas y herencia de modelos — 26Nov2026, Herencia del motor y necesidad comercial, A1 y A2 juntos; idiomas adicionales y TIC sin completar, Pendientes reales y presentación de Multimedia rechazada, Veinte fichas actualizadas con importes conservados (+4 more)

### Community 27 - "Políticas de campañas"
Cohesion: 0.27
Nodes (7): history_digest(), layout(), parent_digest(), partition(), Closed P8 authority on a native copy; historical profiles stay unchanged., release(), verify()

### Community 28 - "admissions prompt.py"
Cohesion: 0.29
Nodes (8): Same approved facts in context, returned metadata and citation validation., reviewed_sources(), AdmissionsPolicy, AdmissionsReply, MemoryFact, Bounded admission prompt and evidence-validated structured response., validate_reply(), StrictModel

### Community 29 - "Motores por etapa"
Cohesion: 0.22
Nodes (10): Atención social y cupos por cuenta, Motores activos y atención de comentarios, Motores de IA activos · corte 25Nov, Piloto nota de voz e imagen · tres partes Leídas, Recuperación social sin replay, P22 sin aceptación comercial nueva · corte 25Nov, Herencia de agentes conservando memoria y permisos, Motor de agentes por etapa y margen de salida (+2 more)

### Community 30 - "Campaña PRE-ICFES y destinos"
Cohesion: 0.22
Nodes (9): preicfes-campaign-launch-20261125, Evidencia25Nov:PREICFES100fichas,102destinos, EvidenciainicialPREICFESsinentregatotal, Rutas alternas exactas con consentimiento por identidad, CadenciaPREICFES1000por24h30s en corte25Nov, PREICFEScorteinicial:1entrega y97preparados principales, PREICFES CAMPAIGN LAUNCH 20261125, PREICFES100principales+2alternativos activados25Nov (+1 more)

### Community 31 - "Piloto y recepción SIIE"
Cohesion: 0.22
Nodes (9): Catálogos resueltos no acreditan emisor ni pagos, Catálogos nativos R7 consultados · corte25Nov, Valores e IDs nativos sin inventar ni fusionar, P23 · Catálogos R7 de inscripción, Firma válida con reloj emisor adelantado, sin ampliar300s, Ensayo público PRE-ICFES y recepción firmada, Piloto parcial no acepta P23 ni acredita volante, Primera recepción SIIE real confirmada ·25Nov19:17Bogotá (+1 more)

### Community 32 - "cbn profile.py"
Cohesion: 0.25
Nodes (3): facts_for(), Small editorial review of public institutional sources; never a financial…, A presentation name and concise Colombian Spanish, without a false human…

### Community 33 - "Informe y consultas agregadas"
Cohesion: 0.25
Nodes (8): Diseño de acceso integrado sin perder contratos, Revisión de logos y acceso institucional, Comprobación de acceso local y productiva, Respuesta atribuida exige context.id exacto, Informe de campañas: consulta agotada y revisión de diseño, Informe de campañas con agregación por cuenta, Consulta agregada419–435ms · muestra 25Nov, Recepción SIIE habilitada sin eventos · corte previo

### Community 34 - "Horarios y costes"
Cohesion: 0.25
Nodes (8): Aclarar plan de estudios versus costo deestudiar, 27fichas y51planes auditados, Botón nativoverificado recupera interés de campaña, PROGRAM HOURS AND COST SCOPE 20261124, InglésA1+A2enunsolo semestre, 24fichas con jornada definidarecargada, Horariospendientes yfallos noresueltos universalmente, PREICFESG1sábado7–12,G2sábado13–18,G3domingo7–12

### Community 35 - "voice transcripts.py"
Cohesion: 0.29
Nodes (4): pending_input(), A bounded transcription step before program routing; original audio stays…, Oldest unread voice in the unanswered group, bound to the latest intent. A…, save()

### Community 36 - "Panel de mensajería masiva"
Cohesion: 0.29
Nodes (7): blank(), CampaignEditor(), CampaignReport(), label(), RecipientDeliveryDialog(), variableKeys(), StepEditor()

### Community 37 - "Respuesta y entrada al Inbox"
Cohesion: 0.33
Nodes (6): Botón comercial Hablar con Juan Pablo, Ficha vigente prevalece sobre precio histórico de campaña, CAMPAIGN ADVISOR ENTRY 20261124, Contexto autenticado de campaña, Entrada real incorpora conversación al Inbox, Inicio comercial publicado b3e68e2

### Community 38 - "Ediciones y remitentes"
Cohesion: 0.33
Nodes (6): Vista previa usa autor real de salida, INBOX EDITS SENDERS PREICFES 20261125, Ediciones verificadas conservan original inmutable, Nueva edición automática endtoend pendiente, Especialista PREICFESv2 con37skills ymemoria, Duración de voz120s ycuota5porhilo

### Community 39 - "Prospectos y promoción PRE-ICFES"
Cohesion: 0.33
Nodes (6): Fechas de solicitud ausentes conservadas vacías, PREICFES PROSPECTS 20261125, PREICFESBorradorv1 yMetaenrevisión en corte previo, SolicitudesPREICFES:100fichas y1revisión, 5grupos ambiguos iniciales, Promoción PREICFES también con financiación

### Community 40 - "Campañas por programa"
Cohesion: 0.33
Nodes (6): Corte17campañas:57entregas incluidas6lecturas, PROGRAM CAMPAIGNS 20261124, Refresco decatálogo GETpara campañas largas, 17campañasactivadas con704números únicos24Nov, Detallehumano deenvío conserva mensaje yestadoactual, 18borradoresNoenviar para213casos

### Community 41 - "Preferencias y exclusiones"
Cohesion: 0.50
Nodes (3): NoContactWrite, field_validator, Strict

### Community 42 - "Espera interna y continuidad"
Cohesion: 0.50
Nodes (5): Cobertura de turnos exige todas las partes aceptadas, Diagnóstico SQL sin parámetros ni cuerpos privados, Espera de almacenamiento previa al efecto externo, Inbox: espera interna, continuidad y fechas confirmadas — 25Nov2026, PRE-ICFES revisión7 · corte 25Nov

### Community 43 - "Recuperación de respuestas"
Cohesion: 0.40
Nodes (5): Recuperación de atención y contexto del Inbox — 25 de noviembre de 2026, LímiteHTTP600 por minuto y usuario, Orientaciones nuevas y controles IA restaurados, Reacciones citadas y transcripción ya guardada, Recuperación breve por truncamiento y respaldos aprobados

### Community 44 - "Política de abono inicial"
Cohesion: 0.50
Nodes (4): HIGHER INITIAL PAYMENT POLICY 20261124, Menor abono vigente para presentación inicial, Puede adelantar inscripción mientras revisan financiación, Abono distinto exige revisión de Tesorería

### Community 45 - "Contención de almacenamiento"
Cohesion: 0.50
Nodes (4): Cinco cargas nativas satisfactorias · corte24Nov, GET agrupado recuperable, sin repetir mutaciones, Inbox: contención de almacenamiento · 24 de noviembre de 2026, Seguimientos liberan bloqueo entre contactos y etapas

### Community 46 - "Intereses en clases abiertas"
Cohesion: 0.50
Nodes (4): MASTERCLASS INTERESTS 20261124, Elección explícita del contacto prevalece, Propuesta de programas relacionados con masterclasses, Revisión por grupos y lotesde10

### Community 47 - "Preparación del receptor SIIE"
Cohesion: 0.67
Nodes (4): P23 · Preparación de RinovaPlus para el webhook SIIE, P23 preparación no acepta fase ni emite pagos, P23 preparación y configuración guardada separada, Vínculo SIIE exige revisión de snapshot vigente

### Community 48 - "BroadcastProspectSetup.tsx"
Cohesion: 0.50
Nodes (3): BroadcastProspectSetup(), Bundle, Route

## Knowledge Gaps
- **273 isolated node(s):** `Component`, `Template`, `Binding`, `Document`, `Campaign` (+268 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `reasons()` connect `Gestión de campañas` to `Importación de prospectos`, `Seguimiento comercial`?**
  _High betweenness centrality (0.001) - this node is a cross-community bridge._
- **What connects `Component`, `Template`, `Binding` to the rest of the system?**
  _273 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Gestión de campañas` be split into smaller, more focused modules?**
  _Cohesion score 0.06329350261389097 - nodes in this community are weakly interconnected._
- **Should `workspace.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07199032062915911 - nodes in this community are weakly interconnected._
- **Should `Diagnóstico de listas` be split into smaller, more focused modules?**
  _Cohesion score 0.059932659932659935 - nodes in this community are weakly interconnected._
- **Should `Eventos y recibos entrantes` be split into smaller, more focused modules?**
  _Cohesion score 0.06259426847662142 - nodes in this community are weakly interconnected._
- **Should `Seguimiento por tiempo y lista` be split into smaller, more focused modules?**
  _Cohesion score 0.06382978723404255 - nodes in this community are weakly interconnected._