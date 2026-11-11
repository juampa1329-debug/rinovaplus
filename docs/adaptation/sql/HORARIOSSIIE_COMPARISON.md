# HORARIOSSIIE frente a las declaraciones CRM CBN

Generado offline por `backend/tools/compare_horariosiie.py`. SQL-C2, 2026-10-24. [Plan de creación](HORARIOSSIIE_CRM_PLAN.md). Ninguna clasificación concede permiso de ejecución o activa funciones.

## Grupos y precondiciones

| Grupo | Fuentes | Tablas | Clasificación | Depende de |
|---|---|---:|---|---|
| CBN-B000 | diario nuevo | 0 | history_design_only | — |
| CBN-B001 | 001 | 4 | conditional_structural_candidate | CBN-B000 |
| CBN-B002 | 002 | 3 | conditional_structural_candidate | CBN-B000, CBN-B001 |
| CBN-B003 | 003 | 6 | employee_contract_pending | CBN-B000, CBN-B001 |
| CBN-B004 | 004 | 3 | employee_contract_pending | CBN-B000, CBN-B001, CBN-B003 |
| CBN-B005 | 005 | 6 | employee_contract_pending | CBN-B000, CBN-B001, CBN-B003, CBN-B004 |
| CBN-B006 | 006 | 2 | conditional_structural_candidate | CBN-B000, CBN-B001 |
| CBN-B007 | 007 | 1 | conditional_structural_candidate | CBN-B000, CBN-B001 |
| CBN-B008 | 008 | 2 | conditional_structural_candidate | CBN-B000, CBN-B001 |
| CBN-B009 | 009 | 3 | employee_contract_pending | CBN-B000, CBN-B001, CBN-B003 |
| CBN-B011 | 011, 012 | 8 | conditional_structural_candidate | CBN-B000, CBN-B001 |
| CBN-B013 | 013, 014 | 3 | conditional_structural_candidate | CBN-B000, CBN-B001 |
| CBN-B015 | 015 | 3 | conditional_structural_candidate | CBN-B000, CBN-B001, CBN-B011 |
| CBN-B016 | 016 | 1 | conditional_structural_candidate | CBN-B000, CBN-B001, CBN-B011, CBN-B015 |
| CBN-B017 | 017 | 6 | employee_contract_pending | CBN-B000, CBN-B001, CBN-B003, CBN-B011, CBN-B013, CBN-B015 |
| CBN-B018 | 018 | 9 | conditional_structural_candidate | CBN-B000, CBN-B001, CBN-B011, CBN-B015 |
| CBN-B019 | 019 | 7 | employee_contract_pending | CBN-B000, CBN-B001, CBN-B003, CBN-B017 |
| CBN-B020 | 020 | 1 | employee_contract_pending | CBN-B000, CBN-B001, CBN-B019 |

## Las 68 tablas declaradas

Todas están ausentes en esta captura con visibilidad completa. Las columnas contadas son CREATE; ALTER y forma final se revisan aparte.

| Tabla | Fuente | Columnas CREATE | Grupo |
|---|---|---:|---|
| crm.Contact | [001:22](../../../backend/migrations/001_local_crm.sql#L22) | 15 | CBN-B001 |
| crm.Conversation | [001:36](../../../backend/migrations/001_local_crm.sql#L36) | 9 | CBN-B001 |
| crm.Message | [001:48](../../../backend/migrations/001_local_crm.sql#L48) | 6 | CBN-B001 |
| crm.Operation | [001:59](../../../backend/migrations/001_local_crm.sql#L59) | 9 | CBN-B001 |
| crm_admissions.AdmissionCase | [002:22](../../../backend/migrations/002_local_admissions.sql#L22) | 3 | CBN-B002 |
| crm_admissions.Followup | [002:27](../../../backend/migrations/002_local_admissions.sql#L27) | 8 | CBN-B002 |
| crm_admissions.Operation | [002:39](../../../backend/migrations/002_local_admissions.sql#L39) | 6 | CBN-B002 |
| crm_inbox.Member | [003:39](../../../backend/migrations/003_local_inbox.sql#L39) | 4 | CBN-B003 |
| crm_inbox.Agent | [003:45](../../../backend/migrations/003_local_inbox.sql#L45) | 6 | CBN-B003 |
| crm_inbox.Assignment | [003:53](../../../backend/migrations/003_local_inbox.sql#L53) | 4 | CBN-B003 |
| crm_inbox.Task | [003:61](../../../backend/migrations/003_local_inbox.sql#L61) | 9 | CBN-B003 |
| crm_inbox.SlaPolicy | [003:75](../../../backend/migrations/003_local_inbox.sql#L75) | 4 | CBN-B003 |
| crm_inbox.Operation | [003:82](../../../backend/migrations/003_local_inbox.sql#L82) | 7 | CBN-B003 |
| crm_events.Event | [004:146](../../../backend/migrations/004_conversation_events.sql#L146) | 16 | CBN-B004 |
| crm_events.Preparation | [004:169](../../../backend/migrations/004_conversation_events.sql#L169) | 7 | CBN-B004 |
| crm_events.RetryOperation | [004:177](../../../backend/migrations/004_conversation_events.sql#L177) | 3 | CBN-B004 |
| crm_analysis.Policy | [005:204](../../../backend/migrations/005_conversation_analysis.sql#L204) | 11 | CBN-B005 |
| crm_analysis.ConversationState | [005:215](../../../backend/migrations/005_conversation_analysis.sql#L215) | 18 | CBN-B005 |
| crm_analysis.Receipt | [005:231](../../../backend/migrations/005_conversation_analysis.sql#L231) | 4 | CBN-B005 |
| crm_analysis.Attempt | [005:238](../../../backend/migrations/005_conversation_analysis.sql#L238) | 9 | CBN-B005 |
| crm_analysis.Feedback | [005:248](../../../backend/migrations/005_conversation_analysis.sql#L248) | 6 | CBN-B005 |
| crm_analysis.Operation | [005:255](../../../backend/migrations/005_conversation_analysis.sql#L255) | 5 | CBN-B005 |
| crm_config.Configuration | [006:21](../../../backend/migrations/006_crm_configuration.sql#L21) | 5 | CBN-B006 |
| crm_config.Operation | [006:28](../../../backend/migrations/006_crm_configuration.sql#L28) | 4 | CBN-B006 |
| crm_identity.Profile | [007:21](../../../backend/migrations/007_institutional_identity.sql#L21) | 10 | CBN-B007 |
| crm_merge.MergeCase | [008:21](../../../backend/migrations/008_contact_merge.sql#L21) | 12 | CBN-B008 |
| crm_merge.Operation | [008:41](../../../backend/migrations/008_contact_merge.sql#L41) | 10 | CBN-B008 |
| crm_strategy.Policy | [009:21](../../../backend/migrations/009_conversation_strategy.sql#L21) | 3 | CBN-B009 |
| crm_strategy.EvaluationPlan | [009:28](../../../backend/migrations/009_conversation_strategy.sql#L28) | 13 | CBN-B009 |
| crm_strategy.Operation | [009:40](../../../backend/migrations/009_conversation_strategy.sql#L40) | 10 | CBN-B009 |
| crm_channels.Account | [011:12](../../../backend/migrations/011_channels.sql#L12) | 8 | CBN-B011 |
| crm_channels.Credential | [011:22](../../../backend/migrations/011_channels.sql#L22) | 5 | CBN-B011 |
| crm_channels.webhook_events | [011:28](../../../backend/migrations/011_channels.sql#L28) | 10 | CBN-B011 |
| crm_channels.ExternalIdentity | [011:37](../../../backend/migrations/011_channels.sql#L37) | 6 | CBN-B011 |
| crm_channels.ExternalMessage | [011:43](../../../backend/migrations/011_channels.sql#L43) | 4 | CBN-B011 |
| crm_channels.outbound_queue | [011:48](../../../backend/migrations/011_channels.sql#L48) | 12 | CBN-B011 |
| crm_channels.social_comments | [011:60](../../../backend/migrations/011_channels.sql#L60) | 7 | CBN-B011 |
| crm_channels.Audit | [011:66](../../../backend/migrations/011_channels.sql#L66) | 5 | CBN-B011 |
| crm_ai.Configuration | [013:12](../../../backend/migrations/013_ai_providers.sql#L12) | 4 | CBN-B013 |
| crm_ai.Connection | [013:18](../../../backend/migrations/013_ai_providers.sql#L18) | 4 | CBN-B013 |
| crm_ai.Credential | [013:24](../../../backend/migrations/013_ai_providers.sql#L24) | 5 | CBN-B013 |
| crm_channels.ConversationProfile | [015:11](../../../backend/migrations/015_inbox_unified.sql#L11) | 4 | CBN-B015 |
| crm_channels.ConversationControl | [015:17](../../../backend/migrations/015_inbox_unified.sql#L17) | 3 | CBN-B015 |
| crm_channels.MessageRoute | [015:22](../../../backend/migrations/015_inbox_unified.sql#L22) | 7 | CBN-B015 |
| crm_channels.MediaAsset | [016:9](../../../backend/migrations/016_inbox_media.sql#L9) | 22 | CBN-B016 |
| crm_ai.AdmissionsPolicy | [017:12](../../../backend/migrations/017_ai_admissions.sql#L12) | 7 | CBN-B017 |
| crm_ai.KnowledgeDocument | [017:19](../../../backend/migrations/017_ai_admissions.sql#L19) | 9 | CBN-B017 |
| crm_ai.KnowledgeChunk | [017:26](../../../backend/migrations/017_ai_admissions.sql#L26) | 5 | CBN-B017 |
| crm_ai.KnowledgeTerm | [017:31](../../../backend/migrations/017_ai_admissions.sql#L31) | 3 | CBN-B017 |
| crm_ai.ProspectMemory | [017:37](../../../backend/migrations/017_ai_admissions.sql#L37) | 6 | CBN-B017 |
| crm_ai.ResponseJob | [017:44](../../../backend/migrations/017_ai_admissions.sql#L44) | 12 | CBN-B017 |
| crm_marketing.ChurnAssessment | [018:16](../../../backend/migrations/018_campaigns.sql#L16) | 16 | CBN-B018 |
| crm_marketing.MessageTemplate | [018:40](../../../backend/migrations/018_campaigns.sql#L40) | 12 | CBN-B018 |
| crm_marketing.ContactConsent | [018:57](../../../backend/migrations/018_campaigns.sql#L57) | 12 | CBN-B018 |
| crm_marketing.RemarketingRule | [018:77](../../../backend/migrations/018_campaigns.sql#L77) | 15 | CBN-B018 |
| crm_marketing.AccountCadence | [018:96](../../../backend/migrations/018_campaigns.sql#L96) | 10 | CBN-B018 |
| crm_marketing.Campaign | [018:107](../../../backend/migrations/018_campaigns.sql#L107) | 17 | CBN-B018 |
| crm_marketing.CampaignRecipient | [018:129](../../../backend/migrations/018_campaigns.sql#L129) | 25 | CBN-B018 |
| crm_marketing.EvaluationRun | [018:159](../../../backend/migrations/018_campaigns.sql#L159) | 15 | CBN-B018 |
| crm_marketing.Policy | [018:173](../../../backend/migrations/018_campaigns.sql#L173) | 7 | CBN-B018 |
| crm_agents.Stage | [019:13](../../../backend/migrations/019_admissions_agents.sql#L13) | 9 | CBN-B019 |
| crm_agents.Profile | [019:20](../../../backend/migrations/019_admissions_agents.sql#L20) | 11 | CBN-B019 |
| crm_agents.Context | [019:37](../../../backend/migrations/019_admissions_agents.sql#L37) | 12 | CBN-B019 |
| crm_agents.SourceScope | [019:47](../../../backend/migrations/019_admissions_agents.sql#L47) | 8 | CBN-B019 |
| crm_agents.Assignment | [019:54](../../../backend/migrations/019_admissions_agents.sql#L54) | 6 | CBN-B019 |
| crm_agents.History | [019:61](../../../backend/migrations/019_admissions_agents.sql#L61) | 9 | CBN-B019 |
| crm_agents.Usage | [019:68](../../../backend/migrations/019_admissions_agents.sql#L68) | 7 | CBN-B019 |
| crm_agents.Execution | [020:12](../../../backend/migrations/020_agent_execution.sql#L12) | 21 | CBN-B020 |

## Referencias académicas del código activo

Presencia de nombre, no aceptación de columnas/PK/permisos/datos. Las referencias anclan el inicio del literal SQL Python; se excluyen expectativas del diagnóstico y router importado no montado.

| Tabla | Presencia | Primera referencia |
|---|---|---|
| dbo.ACAsignatura | present_columns_not_fully_accepted | [backend/app/modules/catalog/infrastructure/institutional_context.py:99](../../../backend/app/modules/catalog/infrastructure/institutional_context.py#L99) |
| dbo.ACAsignaturaPlan | present_columns_not_fully_accepted | [backend/app/modules/catalog/infrastructure/institutional_context.py:99](../../../backend/app/modules/catalog/infrastructure/institutional_context.py#L99) |
| dbo.ACAspirante | absent_observed | [backend/app/modules/admissions/application/service.py:68](../../../backend/app/modules/admissions/application/service.py#L68) |
| dbo.ACDetalleJornada | absent_observed | [backend/app/modules/admissions/application/service.py:250](../../../backend/app/modules/admissions/application/service.py#L250) |
| dbo.ACEscuela | absent_observed | [backend/app/modules/agents/service.py:551](../../../backend/app/modules/agents/service.py#L551) |
| dbo.ACEstadoSeguimiento | absent_observed | [backend/app/modules/admissions/application/service.py:295](../../../backend/app/modules/admissions/application/service.py#L295) |
| dbo.ACJornada | present_columns_not_fully_accepted | [backend/app/modules/admissions/application/service.py:68](../../../backend/app/modules/admissions/application/service.py#L68) |
| dbo.ACModalidad | absent_observed | [backend/app/modules/catalog/infrastructure/institutional_context.py:11](../../../backend/app/modules/catalog/infrastructure/institutional_context.py#L11) |
| dbo.ACPlanEducativo | present_columns_not_fully_accepted | [backend/app/modules/catalog/infrastructure/institutional_context.py:99](../../../backend/app/modules/catalog/infrastructure/institutional_context.py#L99) |
| dbo.ACProgramaOfrecido | present_columns_not_fully_accepted | [backend/app/modules/admissions/application/service.py:68](../../../backend/app/modules/admissions/application/service.py#L68) |
| dbo.ACProgramas | present_columns_not_fully_accepted | [backend/app/modules/admissions/application/service.py:68](../../../backend/app/modules/admissions/application/service.py#L68) |
| dbo.ACSeguimiento | absent_observed | [backend/app/modules/admissions/application/service.py:263](../../../backend/app/modules/admissions/application/service.py#L263) |
| dbo.AFDetallePlanPago | absent_observed | [backend/app/modules/catalog/infrastructure/institutional_context.py:94](../../../backend/app/modules/catalog/infrastructure/institutional_context.py#L94) |
| dbo.AFPlanes | absent_observed | [backend/app/modules/catalog/infrastructure/institutional_context.py:86](../../../backend/app/modules/catalog/infrastructure/institutional_context.py#L86) |
| dbo.AFTarifas | absent_observed | [backend/app/modules/catalog/infrastructure/institutional_context.py:86](../../../backend/app/modules/catalog/infrastructure/institutional_context.py#L86) |
| dbo.GEEmpleado | absent_observed | [backend/app/modules/conversation_strategy/api/router.py:236](../../../backend/app/modules/conversation_strategy/api/router.py#L236) |
| dbo.GEEstudiante | present_columns_not_fully_accepted | [backend/app/modules/admissions/application/service.py:228](../../../backend/app/modules/admissions/application/service.py#L228) |
| dbo.GEImgenProg | absent_observed | [backend/app/modules/catalog/infrastructure/institutional_context.py:105](../../../backend/app/modules/catalog/infrastructure/institutional_context.py#L105) |
| dbo.GEPeriodo | present_columns_not_fully_accepted | [backend/app/modules/admissions/application/service.py:68](../../../backend/app/modules/admissions/application/service.py#L68) |
| dbo.GEPoblacion | absent_observed | [backend/app/modules/contacts/api/router.py:128](../../../backend/app/modules/contacts/api/router.py#L128) |
| dbo.GETipoIdentidad | absent_observed | [backend/app/modules/admissions/application/service.py:211](../../../backend/app/modules/admissions/application/service.py#L211) |
| dbo.GETipoImagen | absent_observed | [backend/app/modules/catalog/infrastructure/institutional_context.py:105](../../../backend/app/modules/catalog/infrastructure/institutional_context.py#L105) |
