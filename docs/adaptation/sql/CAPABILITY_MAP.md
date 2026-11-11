# Mapa de persistencia por capacidad

P1.1 · 2026-10-24. Mapeo semántico revisado, no equivalencia de esquemas ni propuesta de crear una tabla SQL Server por cada tabla SaaS. Las tablas destino están declaradas en fuente; no se verificó su presencia en la base. La ausencia de equivalente DDL significa diseño pendiente, no permiso para crearlo.

Cobertura: 68/68 tablas destino, 31 grupos. Las columnas, claves e índices existentes se detallan en [el catálogo](SCHEMA_CATALOG.md).

## crm_core · Contacto, conversación, mensaje y diario de operaciones

**Clasificación:** reutilizar_con_adaptacion_funcional. **Etapa:** P3.

**Destino:** `crm.Contact`, `crm.Conversation`, `crm.Message`, `crm.Operation`

**Referencia Scentra:** `saas_conversations`, `saas_messages`, `saas_crm_timeline_events`

Reutilizar UUID, revisiones y diario CBN. Las entidades Scentra no se copian una a una: un contacto CBN conserva su relación educativa y la conversación de cada identidad. El mapeo no acredita paridad de campos ni migraciones aplicadas.

**Evidencia:** [../saas-version/backend/app_saas/crm/router.py:962](../../../../saas-version/backend/app_saas/crm/router.py#L962), [../saas-version/backend/app_saas/crm/router.py:1529](../../../../saas-version/backend/app_saas/crm/router.py#L1529), [../saas-version/backend/app_saas/crm/router.py:496](../../../../saas-version/backend/app_saas/crm/router.py#L496).

## admissions_native · Casos y seguimiento de admisiones sobre SIIE

**Clasificación:** preservar_nativo_educativo. **Etapa:** P3.

**Destino:** `crm_admissions.AdmissionCase`, `crm_admissions.Followup`, `crm_admissions.Operation`

**Referencia Scentra:** Función educativa nativa; conservar sin duplicar SIIE.

Capacidad educativa propia. Conservar referencias por ID a aspirante/estado/período oficiales; no crear otra población académica o matrículas a partir de tablas SaaS.

**Evidencia:** .

## inbox_operations · Equipo, registro base IA, asignación dual, tareas y SLA

**Clasificación:** reutilizar_con_adaptacion_funcional. **Etapa:** P3.

**Destino:** `crm_inbox.Member`, `crm_inbox.Agent`, `crm_inbox.Assignment`, `crm_inbox.Task`, `crm_inbox.SlaPolicy`, `crm_inbox.Operation`

**Referencia Scentra:** `saas_crm_tasks`, `saas_users`, `saas_ai_agents`

Member identifica empleados SIIE y no es usuario autenticado. Agent es el registro único que amplía crm_agents.Profile. Conservar tareas/asignación humana e IA separadas; usuarios/roles son un faltante distinto.

**Evidencia:** [../saas-version/backend/app_saas/crm/router.py:1515](../../../../saas-version/backend/app_saas/crm/router.py#L1515), [../saas-version/backend/app_saas/crm/router.py:963](../../../../saas-version/backend/app_saas/crm/router.py#L963), [../saas-version/backend/app_saas/crm/router.py:964](../../../../saas-version/backend/app_saas/crm/router.py#L964).

## event_pipeline · Eventos durables y preparación incremental

**Clasificación:** reutilizar_con_adaptacion_funcional. **Etapa:** P4.

**Destino:** `crm_events.Event`, `crm_events.Preparation`, `crm_events.RetryOperation`

**Referencia Scentra:** `saas_intelligence_events`, `saas_ai_agent_orchestration_jobs`

Preservar evento, preparación y reintento de CBN. Correspondencia por responsabilidad de procesamiento; no equivalencia exacta de columnas ni permiso para crear otra cola.

**Evidencia:** [../saas-version/backend/app_saas/intelligence/service.py:503](../../../../saas-version/backend/app_saas/intelligence/service.py#L503), [../saas-version/backend/app_saas/agents/operating_system.py:771](../../../../saas-version/backend/app_saas/agents/operating_system.py#L771).

## conversation_analysis · Análisis incremental, recibos, reservas y correcciones

**Clasificación:** reutilizar_con_adaptacion_funcional. **Etapa:** P10.

**Destino:** `crm_analysis.Policy`, `crm_analysis.ConversationState`, `crm_analysis.Receipt`, `crm_analysis.Attempt`, `crm_analysis.Feedback`, `crm_analysis.Operation`

**Referencia Scentra:** `saas_conversation_memory`, `saas_ai_agent_evals`, `saas_intelligence_prediction_feedback`

Reutilizar contexto/feedback e idempotencia ya declarados; las políticas R4 y reservas no equivalen a datasets/modelos entrenados. Su integración visual y correcciones preceden el aprendizaje evaluado.

**Evidencia:** [../saas-version/backend/app_saas/ai_agent/service.py:442](../../../../saas-version/backend/app_saas/ai_agent/service.py#L442), [../saas-version/backend/app_saas/agents/service.py:1329](../../../../saas-version/backend/app_saas/agents/service.py#L1329), [../saas-version/backend/app_saas/intelligence/service.py:694](../../../../saas-version/backend/app_saas/intelligence/service.py#L694).

## crm_configuration · Etapas, etiquetas y campos configurables compartidos

**Clasificación:** reutilizar_con_adaptacion_funcional. **Etapa:** P3.

**Destino:** `crm_config.Configuration`, `crm_config.Operation`

**Referencia Scentra:** `saas_crm_custom_fields`, `saas_crm_pipelines`, `saas_crm_pipeline_stages`, `saas_labels`, `saas_conversation_labels`

Conservar configuración singleton derivada de contactos en 006 y editor común. Normalizar organización/contratos sin crear catálogos CRM duplicados ni sobrescribir valores guardados.

**Evidencia:** [../saas-version/backend/app_saas/crm/router.py:473](../../../../saas-version/backend/app_saas/crm/router.py#L473), [../saas-version/backend/app_saas/crm/router.py:537](../../../../saas-version/backend/app_saas/crm/router.py#L537), [../saas-version/backend/app_saas/crm/router.py:567](../../../../saas-version/backend/app_saas/crm/router.py#L567), [../saas-version/backend/app_saas/crm/router.py:857](../../../../saas-version/backend/app_saas/crm/router.py#L857), [../saas-version/backend/app_saas/crm/router.py:957](../../../../saas-version/backend/app_saas/crm/router.py#L957).

## institutional_identity · Ficha institucional declarada y comparación SIIE

**Clasificación:** preservar_nativo_educativo. **Etapa:** P3.

**Destino:** `crm_identity.Profile`

**Referencia Scentra:** `saas_conversations`

El perfil estructurado educativo amplía al contacto CBN. No copiar datos oficiales ni permitir edición de SIIE como si fueran atributos locales; la referencia Scentra de conversación sólo cubre identidad CRM general.

**Evidencia:** [../saas-version/backend/app_saas/crm/router.py:962](../../../../saas-version/backend/app_saas/crm/router.py#L962).

## logical_merge · Unificación lógica y reversión con evidencia

**Clasificación:** preservar_nativo_educativo. **Etapa:** P3.

**Destino:** `crm_merge.MergeCase`, `crm_merge.Operation`

**Referencia Scentra:** `saas_crm_merge_events`

Existe referente Scentra de auditoría de merge, pero CBN conserva la semántica lógica reversible sin borrar ni reparentar los contactos ni el core académico. No sustituirla por una fusión destructiva de origen.

**Evidencia:** [../saas-version/backend/app_saas/crm/router.py:2180](../../../../saas-version/backend/app_saas/crm/router.py#L2180).

## conversation_strategy · Planes, feedback y autonomía interna limitada

**Clasificación:** reutilizar_con_adaptacion_funcional. **Etapa:** P3.

**Destino:** `crm_strategy.Policy`, `crm_strategy.EvaluationPlan`, `crm_strategy.Operation`

**Referencia Scentra:** `saas_intelligence_recommendations`, `saas_advisor_actions`

Preservar planes con evidencia y tarea interna idempotente. No confundir interpretación cualitativa o corrección de plan con probabilidad de churn o autorización de envíos.

**Evidencia:** [../saas-version/backend/app_saas/intelligence/service.py:578](../../../../saas-version/backend/app_saas/intelligence/service.py#L578), [../saas-version/backend/app_saas/agents/service.py:2278](../../../../saas-version/backend/app_saas/agents/service.py#L2278).

## channel_configuration · Cuentas, credenciales y auditoría de canales

**Clasificación:** reutilizar_con_adaptacion_funcional. **Etapa:** P4.

**Destino:** `crm_channels.Account`, `crm_channels.Credential`, `crm_channels.Audit`

**Referencia Scentra:** `saas_integrations`, `saas_api_credentials`, `saas_audit_events`

Reutilizar cifrado y configuración de canales CBN. El catálogo queda limitado a canales educativos; WooCommerce y sincronización de productos están excluidos. No copiar credenciales de Scentra.

**Evidencia:** [../saas-version/backend/app_saas/integrations/router.py:267](../../../../saas-version/backend/app_saas/integrations/router.py#L267), [../saas-version/backend/app_saas/api_credentials/router.py:225](../../../../saas-version/backend/app_saas/api_credentials/router.py#L225), [../saas-version/backend/app_saas/integrations/router.py:1143](../../../../saas-version/backend/app_saas/integrations/router.py#L1143).

## webhook_intake · Recepción y procesamiento durable de webhooks

**Clasificación:** reutilizar_con_adaptacion_funcional. **Etapa:** P4.

**Destino:** `crm_channels.webhook_events`

**Referencia Scentra:** `saas_webhook_events`, `saas_webhook_endpoints`

Conservar firma, deduplicación y recepción SQL. Endpoint/configuración puede reutilizar Account y rutas existentes; no exigir una tabla por cada objeto PostgreSQL.

**Evidencia:** [../saas-version/backend/app_saas/webhooks/router.py:935](../../../../saas-version/backend/app_saas/webhooks/router.py#L935), [../saas-version/backend/app_saas/webhooks/router.py:400](../../../../saas-version/backend/app_saas/webhooks/router.py#L400).

## message_transport · Identidades, mensajes externos, control, multimedia y outbox

**Clasificación:** reutilizar_con_adaptacion_funcional. **Etapa:** P4.

**Destino:** `crm_channels.ExternalIdentity`, `crm_channels.ExternalMessage`, `crm_channels.outbound_queue`, `crm_channels.ConversationControl`, `crm_channels.MessageRoute`, `crm_channels.MediaAsset`

**Referencia Scentra:** `saas_conversations`, `saas_messages`, `saas_outbound_messages`, `saas_message_status_events`, `saas_media_assets`

Una única cola CBN con revalidación, reconciliación y recepción durable. Conservar separación entre aceptación POST y entrega confirmada; no montar el dispatcher SaaS en paralelo.

**Evidencia:** [../saas-version/backend/app_saas/crm/router.py:962](../../../../saas-version/backend/app_saas/crm/router.py#L962), [../saas-version/backend/app_saas/crm/router.py:1529](../../../../saas-version/backend/app_saas/crm/router.py#L1529), [../saas-version/backend/app_saas/crm/router.py:3595](../../../../saas-version/backend/app_saas/crm/router.py#L3595), [../saas-version/backend/app_saas/crm/router.py:3300](../../../../saas-version/backend/app_saas/crm/router.py#L3300), [../saas-version/backend/app_saas/crm/router.py:3492](../../../../saas-version/backend/app_saas/crm/router.py#L3492).

## social_comments · Comentarios sociales y respuesta enlazada al Inbox

**Clasificación:** reutilizar_con_adaptacion_funcional. **Etapa:** P4.

**Destino:** `crm_channels.social_comments`

**Referencia Scentra:** `social_comments`, `social_posts`

Hay backend CBN para comentarios; completar UI y acciones aplicables. Scentra usa tablas sociales sin prefijo en esta ruta; no confundirlas con saas_social_comments consultada por Ads ni duplicar persistencia por el nombre.

**Evidencia:** [../saas-version/backend/app_saas/social/service.py:293](../../../../saas-version/backend/app_saas/social/service.py#L293), [../saas-version/backend/app_saas/social/service.py:267](../../../../saas-version/backend/app_saas/social/service.py#L267).

## crm_diagnostics · Score y temperatura manuales del perfil conversacional

**Clasificación:** reutilizar_con_adaptacion_funcional. **Etapa:** P3.

**Destino:** `crm_channels.ConversationProfile`

**Referencia Scentra:** `saas_conversations`, `saas_intelligence_predictions`

Unificar lectura de ficha y mini CRM, conservando el score manual. La tabla de perfil no es un modelo de abandono ni debe sobrescribirse con una estimación IA sin origen/fecha/versión.

**Evidencia:** [../saas-version/backend/app_saas/crm/router.py:962](../../../../saas-version/backend/app_saas/crm/router.py#L962), [../saas-version/backend/app_saas/crm/router.py:967](../../../../saas-version/backend/app_saas/crm/router.py#L967).

## ai_provider_configuration · Configuración, conexiones y secretos de proveedores IA

**Clasificación:** reutilizar_con_adaptacion_funcional. **Etapa:** P2.

**Destino:** `crm_ai.Configuration`, `crm_ai.Connection`, `crm_ai.Credential`

**Referencia Scentra:** `saas_ai_settings`, `saas_api_credentials`

Reutilizar configuración y credenciales de sólo escritura del destino. Completar ajustes institucionales sin dependencias de plan ni copiar claves de origen.

**Evidencia:** [../saas-version/backend/app_saas/ai_agent/service.py:424](../../../../saas-version/backend/app_saas/ai_agent/service.py#L424), [../saas-version/backend/app_saas/api_credentials/router.py:225](../../../../saas-version/backend/app_saas/api_credentials/router.py#L225).

## knowledge · Documentos publicados, fragmentos e índice léxico

**Clasificación:** reutilizar_con_adaptacion_funcional. **Etapa:** P6.

**Destino:** `crm_ai.KnowledgeDocument`, `crm_ai.KnowledgeChunk`, `crm_ai.KnowledgeTerm`

**Referencia Scentra:** `saas_knowledge_sources`, `saas_knowledge_chunks`, `saas_knowledge_retrieval_logs`, `saas_knowledge_evaluations`

Conservar extracción/recuperación léxica con separación de programa/etapa. Logs, evaluación y publicación se adaptan cuando se defina el contrato; ni SQL vectorial nativo ni pgvector son requisitos asumidos.

**Evidencia:** [../saas-version/backend/app_saas/knowledge/router.py:683](../../../../saas-version/backend/app_saas/knowledge/router.py#L683), [../saas-version/backend/app_saas/knowledge/router.py:1624](../../../../saas-version/backend/app_saas/knowledge/router.py#L1624), [../saas-version/backend/app_saas/knowledge/router.py:1670](../../../../saas-version/backend/app_saas/knowledge/router.py#L1670), [../saas-version/backend/app_saas/knowledge/router.py:1694](../../../../saas-version/backend/app_saas/knowledge/router.py#L1694).

## applicant_memory · Memoria del aspirante y contexto con evidencia

**Clasificación:** reutilizar_con_adaptacion_funcional. **Etapa:** P6.

**Destino:** `crm_ai.ProspectMemory`

**Referencia Scentra:** `saas_conversation_memory`, `saas_ai_agent_memory_archives`

Conservar hechos por aspirante/conversación y revisiones. No reutilizar memoria privada como memoria colectiva ni introducir información de otro programa por similitud.

**Evidencia:** [../saas-version/backend/app_saas/ai_agent/service.py:442](../../../../saas-version/backend/app_saas/ai_agent/service.py#L442), [../saas-version/backend/app_saas/agents/service.py:1302](../../../../saas-version/backend/app_saas/agents/service.py#L1302).

## admissions_ai_execution · Política institucional de respuesta y trabajos IA

**Clasificación:** reutilizar_con_adaptacion_funcional. **Etapa:** P5.

**Destino:** `crm_ai.AdmissionsPolicy`, `crm_ai.ResponseJob`

**Referencia Scentra:** `saas_ai_settings`, `saas_ai_pending_replies`

Conservar política, presupuesto y trabajos CBN. La disponibilidad de un perfil al guardarlo no activa automáticamente respuesta de Inbox o envío externo.

**Evidencia:** [../saas-version/backend/app_saas/ai_agent/service.py:424](../../../../saas-version/backend/app_saas/ai_agent/service.py#L424), [../saas-version/backend/app_saas/ai_agent/service.py:488](../../../../saas-version/backend/app_saas/ai_agent/service.py#L488).

## churn_assessment · Evaluación de riesgo y ejecuciones de cálculo

**Clasificación:** reutilizar_con_adaptacion_funcional. **Etapa:** P3.

**Destino:** `crm_marketing.ChurnAssessment`, `crm_marketing.EvaluationRun`, `crm_marketing.Policy`

**Referencia Scentra:** `saas_intelligence_predictions`, `saas_intelligence_recommendations`, `saas_intelligence_events`

Hay evaluación persistida y worker CBN. Integrar la superficie disponible en P3; P10 añade modelo evaluado. Distinguir regla/rúbrica, interpretación IA, score manual y predicción; sin evidencia mostrar sin evaluación.

**Evidencia:** [../saas-version/backend/app_saas/intelligence/service.py:552](../../../../saas-version/backend/app_saas/intelligence/service.py#L552), [../saas-version/backend/app_saas/intelligence/service.py:578](../../../../saas-version/backend/app_saas/intelligence/service.py#L578), [../saas-version/backend/app_saas/intelligence/service.py:503](../../../../saas-version/backend/app_saas/intelligence/service.py#L503).

## broadcast_controls · Plantillas Meta, consentimiento y cadencia

**Clasificación:** reutilizar_con_adaptacion_funcional. **Etapa:** P7.

**Destino:** `crm_marketing.MessageTemplate`, `crm_marketing.ContactConsent`, `crm_marketing.AccountCadence`

**Referencia Scentra:** `saas_meta_message_templates`, `saas_integrations`, `saas_conversations`

Conservar consentimiento versionado por identidad y cadencia compartida CBN. Los referentes aportan plantilla/cuenta/audiencia; no presumir un consentimiento por tener conversación. No confundir plantilla Meta aprobada con plantilla CRM.

**Evidencia:** [../saas-version/backend/app_saas/broadcasts/router.py:287](../../../../saas-version/backend/app_saas/broadcasts/router.py#L287), [../saas-version/backend/app_saas/broadcasts/router.py:74](../../../../saas-version/backend/app_saas/broadcasts/router.py#L74), [../saas-version/backend/app_saas/broadcasts/router.py:497](../../../../saas-version/backend/app_saas/broadcasts/router.py#L497).

## broadcasts · Campañas de envío y destinatarios

**Clasificación:** reutilizar_con_adaptacion_funcional. **Etapa:** P7.

**Destino:** `crm_marketing.Campaign`, `crm_marketing.CampaignRecipient`

**Referencia Scentra:** `saas_broadcasts`, `saas_broadcast_recipients`

Reutilizar Campaign kind bulk/remarketing y destinatarios con referencia a outbox. Transporte está bloqueado en varias capas; requiere flujo validado completo, no retirar un solo 423.

**Evidencia:** [../saas-version/backend/app_saas/broadcasts/router.py:619](../../../../saas-version/backend/app_saas/broadcasts/router.py#L619), [../saas-version/backend/app_saas/broadcasts/router.py:693](../../../../saas-version/backend/app_saas/broadcasts/router.py#L693).

## remarketing_rules · Reglas de inactividad y recuperación por etapa

**Clasificación:** reutilizar_con_adaptacion_funcional. **Etapa:** P8.

**Destino:** `crm_marketing.RemarketingRule`

**Referencia Scentra:** `saas_crm_triggers`, `saas_remarketing_flows`

La regla CBN es una base parcial por etapa/inactividad y no representa aún todos los activadores ni flujos de varios pasos de Scentra. Preservarla al diseñar el modelo faltante.

**Evidencia:** [../saas-version/backend/app_saas/campaigns/router.py:501](../../../../saas-version/backend/app_saas/campaigns/router.py#L501), [../saas-version/backend/app_saas/campaigns/router.py:638](../../../../saas-version/backend/app_saas/campaigns/router.py#L638).

## educational_agents · Jerarquía, perfiles, contexto, ámbitos, historial, uso y ejecución

**Clasificación:** reutilizar_con_adaptacion_funcional. **Etapa:** P5.

**Destino:** `crm_agents.Stage`, `crm_agents.Profile`, `crm_agents.Context`, `crm_agents.SourceScope`, `crm_agents.Assignment`, `crm_agents.History`, `crm_agents.Usage`, `crm_agents.Execution`

**Referencia Scentra:** `saas_ai_agents`, `saas_ai_agent_events`, `saas_ai_agent_prompt_versions`, `saas_ai_agent_evals`, `saas_ai_agent_tool_approvals`, `saas_ai_runs`

Conservar registro único crm_inbox.Agent y orientador→programa→etapa. Un perfil válido queda disponible al guardar según decisión vigente CBN; diagnóstico opcional y pausa explícita. No reinstalar aprobación obligatoria del perfil por copiar preflight Scentra; acciones/fuentes sensibles conservan controles propios. Usage no es billing del software.

**Evidencia:** [../saas-version/backend/app_saas/agents/service.py:1170](../../../../saas-version/backend/app_saas/agents/service.py#L1170), [../saas-version/backend/app_saas/agents/service.py:1264](../../../../saas-version/backend/app_saas/agents/service.py#L1264), [../saas-version/backend/app_saas/agents/service.py:1399](../../../../saas-version/backend/app_saas/agents/service.py#L1399), [../saas-version/backend/app_saas/agents/service.py:1329](../../../../saas-version/backend/app_saas/agents/service.py#L1329), [../saas-version/backend/app_saas/agents/service.py:1428](../../../../saas-version/backend/app_saas/agents/service.py#L1428), [../saas-version/backend/app_saas/agents/service.py:2256](../../../../saas-version/backend/app_saas/agents/service.py#L2256).

## institutional_auth · Usuarios, roles y sesiones institucionales

**Clasificación:** faltante_por_diseniar. **Etapa:** P2.

**Destino:** Sin estructura equivalente declarada; diseño pendiente.

**Referencia Scentra:** `saas_users`, `saas_memberships`, `saas_password_reset_tokens`

No se encontró DDL de usuarios/sesiones institucionales entre las 68 tablas. Member de Inbox no sustituye autenticación. Diseñar cuentas, revocación y permisos en P2 sin copiar alta multiempresa, planes o cobros del SaaS.

**Evidencia:** [../saas-version/backend/app_saas/auth/router.py:184](../../../../saas-version/backend/app_saas/auth/router.py#L184), [../saas-version/backend/app_saas/auth/router.py:139](../../../../saas-version/backend/app_saas/auth/router.py#L139), [../saas-version/backend/app_saas/auth/router.py:908](../../../../saas-version/backend/app_saas/auth/router.py#L908).

## meta_ads · Cuentas publicitarias, campañas y leads de captación

**Clasificación:** faltante_por_diseniar. **Etapa:** P9.

**Destino:** Sin estructura equivalente declarada; diseño pendiente.

**Referencia Scentra:** `saas_ad_accounts`, `saas_ad_campaigns`, `saas_ad_leads`

No se encontró DDL Meta Ads equivalente en las migraciones CBN. Diseñar sólo las funciones Ads incluidas, enlazadas a identidad/CRM y programa; ninguna lectura o sincronización autoriza gasto publicitario.

**Evidencia:** [../saas-version/backend/app_saas/ads/router.py:373](../../../../saas-version/backend/app_saas/ads/router.py#L373), [../saas-version/backend/app_saas/ads/router.py:374](../../../../saas-version/backend/app_saas/ads/router.py#L374), [../saas-version/backend/app_saas/ads/router.py:375](../../../../saas-version/backend/app_saas/ads/router.py#L375).

## crm_campaigns_segments · Campañas CRM, segmentos guardados y plantillas CRM

**Clasificación:** faltante_por_diseniar. **Etapa:** P8.

**Destino:** Sin estructura equivalente declarada; diseño pendiente.

**Referencia Scentra:** `saas_campaigns`, `saas_segments`, `saas_message_templates`, `saas_campaign_preflight_runs`, `saas_campaign_ab_events`

Campaign de crm_marketing es envío bulk/remarketing; no acredita todo el modelo de campañas CRM. Falta definir segmentos/plantillas CRM y gobierno aplicable. Evaluar ampliación de estructuras existentes antes de crear tablas nuevas.

**Evidencia:** [../saas-version/backend/app_saas/campaigns/router.py:636](../../../../saas-version/backend/app_saas/campaigns/router.py#L636), [../saas-version/backend/app_saas/campaigns/router.py:123](../../../../saas-version/backend/app_saas/campaigns/router.py#L123), [../saas-version/backend/app_saas/campaigns/router.py:177](../../../../saas-version/backend/app_saas/campaigns/router.py#L177), [../saas-version/backend/app_saas/campaigns/router.py:465](../../../../saas-version/backend/app_saas/campaigns/router.py#L465), [../saas-version/backend/app_saas/campaigns/router.py:735](../../../../saas-version/backend/app_saas/campaigns/router.py#L735).

## multi_step_flows · Activadores versionados, esperas y flujos de varios pasos

**Clasificación:** faltante_por_diseniar. **Etapa:** P8.

**Destino:** Sin estructura equivalente declarada; diseño pendiente.

**Referencia Scentra:** `saas_crm_trigger_versions`, `saas_trigger_executions`, `saas_trigger_scheduled_messages`, `saas_remarketing_flows`, `saas_campaign_quiet_hours`

No hay tablas equivalentes de versión/ejecución/pasos/espera entre las migraciones CBN. RemarketingRule no reemplaza este modelo. Diseñar cancelación por respuesta/baja/control humano, reutilizando outbox y cuentas.

**Evidencia:** [../saas-version/backend/app_saas/campaigns/router.py:432](../../../../saas-version/backend/app_saas/campaigns/router.py#L432), [../saas-version/backend/app_saas/campaigns/router.py:1227](../../../../saas-version/backend/app_saas/campaigns/router.py#L1227), [../saas-version/backend/app_saas/campaigns/router.py:1239](../../../../saas-version/backend/app_saas/campaigns/router.py#L1239), [../saas-version/backend/app_saas/campaigns/router.py:638](../../../../saas-version/backend/app_saas/campaigns/router.py#L638), [../saas-version/backend/app_saas/campaigns/router.py:265](../../../../saas-version/backend/app_saas/campaigns/router.py#L265).

## collective_memory · Gestión y gobernanza de memoria colectiva institucional

**Clasificación:** faltante_por_diseniar. **Etapa:** P6.

**Destino:** Sin estructura equivalente declarada; diseño pendiente.

**Referencia Scentra:** `saas_ai_agent_collective_memory`, `saas_ai_agent_memory_archives`

La opción collective en agentes CBN aporta políticas/fuentes, no un CRUD persistente equivalente. Diseñar vigencia, ámbito, archivo y auditoría sin compartir memorias privadas de aspirantes.

**Evidencia:** [../saas-version/backend/app_saas/agents/service.py:1360](../../../../saas-version/backend/app_saas/agents/service.py#L1360), [../saas-version/backend/app_saas/agents/service.py:1302](../../../../saas-version/backend/app_saas/agents/service.py#L1302).

## institutional_dna · ADN, perfil y evidencia institucional compartida

**Clasificación:** faltante_por_diseniar. **Etapa:** P6.

**Destino:** Sin estructura equivalente declarada; diseño pendiente.

**Referencia Scentra:** `saas_brand_profiles`, `saas_brand_evidence`, `saas_brand_governance_events`

Adaptar únicamente identidad/reglas institucionales y evidencia aplicable. No trasladar estudios de contenido, briefs publicitarios o QA de marca fuera del alcance. El ADN no sustituye catálogo, requisitos ni precios SIIE.

**Evidencia:** [../saas-version/backend/app_saas/brand_brain/router.py:212](../../../../saas-version/backend/app_saas/brand_brain/router.py#L212), [../saas-version/backend/app_saas/brand_brain/router.py:281](../../../../saas-version/backend/app_saas/brand_brain/router.py#L281), [../saas-version/backend/app_saas/brand_brain/router.py:415](../../../../saas-version/backend/app_saas/brand_brain/router.py#L415).

## training_governance · Packs, datasets de evaluación, mejoras y promociones

**Clasificación:** faltante_por_diseniar. **Etapa:** P10.

**Destino:** Sin estructura equivalente declarada; diseño pendiente.

**Referencia Scentra:** `saas_training_packs`, `saas_training_pack_events`, `saas_training_feedback_events`, `saas_training_improvement_candidates`, `saas_training_eval_cases`, `saas_training_eval_runs`, `saas_training_promotion_requests`

Feedback y notas CBN existentes no constituyen este circuito de entrenamiento/evaluación. Diseñar fuentes/revisión, criterios y reversión sin importar datasets privados de clientes Scentra.

**Evidencia:** [../saas-version/backend/app_saas/training/service.py:55](../../../../saas-version/backend/app_saas/training/service.py#L55), [../saas-version/backend/app_saas/training/service.py:84](../../../../saas-version/backend/app_saas/training/service.py#L84), [../saas-version/backend/app_saas/training/feedback_service.py:138](../../../../saas-version/backend/app_saas/training/feedback_service.py#L138), [../saas-version/backend/app_saas/training/feedback_service.py:177](../../../../saas-version/backend/app_saas/training/feedback_service.py#L177), [../saas-version/backend/app_saas/training/eval_service.py:123](../../../../saas-version/backend/app_saas/training/eval_service.py#L123), [../saas-version/backend/app_saas/training/eval_service.py:160](../../../../saas-version/backend/app_saas/training/eval_service.py#L160), [../saas-version/backend/app_saas/training/eval_service.py:199](../../../../saas-version/backend/app_saas/training/eval_service.py#L199).

## trained_ml · Features, datasets, trabajos, artefactos y registro de modelos

**Clasificación:** faltante_por_diseniar. **Etapa:** P10.

**Destino:** Sin estructura equivalente declarada; diseño pendiente.

**Referencia Scentra:** `saas_intelligence_feature_values`, `saas_intelligence_model_registry`, `saas_intelligence_model_metrics`, `saas_intelligence_model_rollout_events`, `saas_ml_training_jobs`, `saas_ml_model_artifacts`, `saas_ml_training_datasets`, `saas_ml_model_evaluations`, `saas_ml_drift_snapshots`

No hay DDL de pipeline ML entrenado equivalente entre las 68 tablas. Reutilizar eventos/riesgo como entradas revisadas, no como prueba de entrenamiento. Modelos institucionales aislados y modo sombra/promoción; federación global y memoria entre instituciones excluidas.

**Evidencia:** [../saas-version/backend/app_saas/intelligence/service.py:527](../../../../saas-version/backend/app_saas/intelligence/service.py#L527), [../saas-version/backend/app_saas/intelligence/service.py:621](../../../../saas-version/backend/app_saas/intelligence/service.py#L621), [../saas-version/backend/app_saas/intelligence/service.py:717](../../../../saas-version/backend/app_saas/intelligence/service.py#L717), [../saas-version/backend/app_saas/intelligence/service.py:657](../../../../saas-version/backend/app_saas/intelligence/service.py#L657), [../saas-version/backend/app_saas/intelligence/service.py:3626](../../../../saas-version/backend/app_saas/intelligence/service.py#L3626), [../saas-version/backend/app_saas/intelligence/service.py:3644](../../../../saas-version/backend/app_saas/intelligence/service.py#L3644), [../saas-version/backend/app_saas/intelligence/service.py:891](../../../../saas-version/backend/app_saas/intelligence/service.py#L891), [../saas-version/backend/app_saas/intelligence/service.py:921](../../../../saas-version/backend/app_saas/intelligence/service.py#L921), [../saas-version/backend/app_saas/intelligence/service.py:3683](../../../../saas-version/backend/app_saas/intelligence/service.py#L3683).
