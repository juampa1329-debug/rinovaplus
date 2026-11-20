import type { AiProvider } from "../../shared/aiSettings";
import {
  coordinatedRead,
  observeReadLimit,
  readRetrySeconds,
} from "../../institution/readCoordinator";
import {
  institutionHeaders,
  institutionUnauthorized,
} from "../../shared/institutionSession";

export type Configuration = {
  provider: AiProvider;
  voice_profile_id?: string;
  advisor_name?: string;
  sales_skill_ids?: string[];
  sales_routing_enabled?: boolean;
  sales_memory_enabled?: boolean;
  auto_sales_crm?: boolean;
  description?: string;
  operating_style?: string;
  risk_posture?: "balanced" | "cautious";
  escalation_policy?: string;
  instruction_template?: "custom" | "admissions" | "program";
  template_variables?: Record<string, string>;
  customized?: boolean;
  route?: "admissions" | "institutional" | "followup" | "analytics";
  global_enabled?: boolean;
  fallback_provider?: AiProvider | null;
  monthly_usd_limit?: number;
  usage_alert_percent?: number;
  hard_stop?: boolean;
  input_usd_per_million?: number | null;
  output_usd_per_million?: number | null;
  fallback_input_usd_per_million?: number | null;
  fallback_output_usd_per_million?: number | null;
  ab_enabled?: boolean;
  ab_variant?: string;
  ab_compare_version?: number | null;
  ab_traffic_percent?: number;
  industry_policies?: string[];
  memories?: string[];
  require_human_approval?: boolean;
  allow_safe_actions?: boolean;
  allow_crm_update?: boolean;
  instructions: string;
  objectives: string[];
  rules: string[];
  tone: string;
  channels: string[];
  capabilities: string[];
  document_ids: string[];
  primary_model: string;
  fallback_model: string;
  max_tokens: number;
  monthly_token_limit: number;
  allow_reply: boolean;
};
export type Agent = {
  enabled?: boolean;
  id: string;
  name: string;
  level: string;
  parent_id: string | null;
  program_id: number | null;
  stage_id: string | null;
  state: string;
  version: number;
  revision: number;
  approved_version: number | null;
  configuration: Configuration;
};
export type Stage = {
  id: string;
  program_id: number;
  name: string;
  entry_rule: string;
  exit_rule: string;
  evidence_required: string;
  revision: number;
  approved: boolean;
};
export type Source = {
  id: string;
  title: string;
  state: string;
  revision: number;
  program_id: number | null;
  stage_id: string | null;
  owner: string | null;
  valid_until: string | null;
  scope_revision: number | null;
};
export type Catalog = {
  institutional?: boolean;
  knowledge_reindex_available?: boolean;
  knowledge_scope_editor?: boolean;
  installed: boolean;
  agents: Agent[];
  stages: Stage[];
  sources: Source[];
  counts: Record<string, number>;
  legacy_agents: { id: string; name: string }[];
  programs: {
    items: Program[];
    has_more: boolean;
    period: { id: number; label: string };
  };
};
export type Program = {
  program_id: number;
  name: string;
  schedule: string | null;
  schedule_id: number | null;
  school_id: number | null;
  school: string | null;
};
export type ProviderOptions = {
  current_provider: AiProvider;
  credential_revision: number;
  network_called: false;
  defaults?: {
    provider: AiProvider;
    primary_model: string;
    fallback_model: string;
    monthly_token_limit: number;
    max_tokens: number;
  };
  providers: {
    id: AiProvider;
    configured: boolean;
    endpoint_ready: boolean;
    catalog_loaded: boolean;
    models: { id: string; name: string; origin: string }[];
  }[];
};
export type Context = {
  id: string;
  program_id: number;
  stage_id: string | null;
  applicant_id: number | null;
  period_id: number | null;
  revision: number;
  evidence: string;
};
export type Conversation = {
  mode: string;
  context_id: string | null;
  revision: number;
  reason: string;
  contexts: Context[];
  blocked: string | null;
  selection: {
    agent_id: string;
    supervisor_id: string | null;
    reason: string;
    version: number;
  } | null;
};
export const labels: Record<string, string> = {
  guide: "Orientador institucional",
  program: "Agente de programa",
  stage: "Subagente de etapa",
  draft: "Borrador",
  active: "Activo",
  paused: "Pausado",
  archived: "Archivado",
  automatic: "Automática",
  manual: "Manual protegida",
  human: "Atención humana",
  local: "Web · aplicación",
  whatsapp: "WhatsApp",
  instagram: "Instagram",
  facebook: "Facebook",
  tiktok: "TikTok",
  "program.read": "Consultar oferta institucional",
  "sources.read": "Consultar fuentes aprobadas",
  "conversation.reply": "Responder con fuentes",
  "human.handoff": "Derivar al asesor",
  agent_config: "Configuración guardada",
  agent_review: "Revisión humana",
  agent_state: "Cambio de estado",
  stage_config: "Etapa configurada",
  stage_approval: "Etapa aprobada",
  context_approval: "Contexto aprobado",
  assignment: "Asignación",
  source_scope: "Alcance de fuente aprobado",
  agent_note: "Nota interna",
  action_draft: "Borrador de acción",
  action_approve: "Acción aprobada",
  action_reject: "Acción rechazada",
  action_execute: "Acción registrada",
  reindex: "Conocimiento reindexado",
};
const errors: Record<string, string> = {
  agents_ai_settings_invalid:
    "Los ajustes generales de IA guardados no son compatibles. Abre Ajustes → Inteligencia artificial, revisa los campos indicados y guarda la configuración antes de recargar Agentes.",
  general_storage_unavailable:
    "RinovaPlus no pudo completar la consulta del servidor. Conserva tu borrador y vuelve a cargar. Si se repite, soporte debe revisar el registro del backend; no cambies las claves de API por este aviso.",
  siie_source_changed_review_again:
    "SIIE cambió desde la revisión. Vuelve a obtener la página o preparar la ficha antes de guardarla; la copia local se conserva.",
  siie_local_mapping_ambiguous:
    "Hay más de una ficha local vinculada al mismo programa de SIIE. Revisa esa vinculación antes de sincronizar para evitar duplicados.",
  siie_program_binding_mismatch:
    "La ficha local corresponde a otro programa. Selecciona la ficha correcta antes de vincular los datos.",
  siie_local_finance_conflict:
    "Los ajustes manuales y los importes nuevos ya no coinciden con el total del plan. Revisa abono, cuotas y total en la ficha local antes de sincronizar; no se sobrescribió ningún dato.",
  siie_period_contract_required:
    "La respuesta de SIIE no identifica el período consultado. Confirma que se publicó la versión nueva de la API antes de mezclar ofertas históricas con las ofrecidas.",
  siie_offered_period_unavailable:
    "SIIE no pudo identificar el período ofrecido. Su responsable debe revisar el parámetro 38 y los períodos disponibles; no se eligió un período por suposición.",
  siie_cursor_changed:
    "El período o la paginación de SIIE cambió. Vuelve a obtener la primera página y selecciona de nuevo el registro.",
  siie_students_unavailable:
    "La consulta de estudiantes falló en SIIE. Reintenta más tarde o solicita al responsable revisar sus registros; no se modificaron matrículas.",
  siie_offer_review_required:
    "Abre SIIE en Académico y revisa la oferta recibida. La publicación de precios requiere completar su revisión y vinculación con la ficha local; no se aplican automáticamente.",
  siie_admissions_not_configured:
    "Falta configurar el acceso de SIIE. La versión actual usa una sola clave original en SIIE_API_TOKEN de Coolify; actualiza y redespliega el backend.",
  siie_invalid_parameter:
    "Revisa el período, programa, aspirante o la paginación. Usa los identificadores devueltos por SIIE y el ID completo de la oferta.",
  siie_reference_not_found:
    "SIIE no encontró esa referencia en el período consultado. Actualiza el listado y vuelve a seleccionarla.",
  siie_rate_limited:
    "SIIE alcanzó su límite de consultas. Espera al menos un minuto antes de volver a consultar; los datos ya guardados se conservan.",
  siie_source_incomplete:
    "SIIE no puede completar esta oferta. Solicita al equipo académico revisar el mapeo y sus condiciones financieras; no se publicó ningún precio.",
  siie_credential_invalid:
    "La clave de SIIE tiene un formato no válido. Guarda el token original en Coolify sin saltos de línea; no uses su hash.",
  siie_not_configured:
    "Falta configurar la conexión de SIIE. Guarda la URL HTTPS y la clave original única en SIIE_API_TOKEN de Coolify; después redespliega el backend.",
  siie_source_credential_configuration:
    "SIIE informa un problema con su configuración de claves. Su administrador debe revisar API_Key y el alias API_CRM: pueden faltar, ser inválidos o no coincidir. Cambiar datos del CRM no resuelve ese fallo.",
  siie_catalog_not_configured:
    "La API de SIIE aún no está configurada. Solicita la URL HTTPS, una credencial de consulta y el ID de la oferta. Guarda la credencial sólo en Coolify.",
  siie_catalog_endpoint_invalid:
    "La dirección de la API de SIIE no coincide con el dominio autorizado del servidor. Revisa la configuración de la integración.",
  siie_catalog_access_rejected:
    "SIIE rechazó la clave de acceso. Comprueba que la clave única original esté vigente y que la versión de clave única ya esté publicada en SIIE.",
  siie_offer_not_found:
    "No se encontró esa oferta en SIIE. Verifica programa, sede, jornada y período con el equipo académico.",
  siie_catalog_stale_or_mismatched:
    "SIIE devolvió una oferta inactiva, distinta o sin información reciente. Solicita una respuesta actualizada antes de aplicar precios.",
  siie_catalog_invalid_response:
    "La respuesta de SIIE no cumple el contrato o sus cuotas no coinciden con el costo total. Solicita revisar los datos; no se guardó nada.",
  siie_catalog_unavailable:
    "SIIE no pudo entregar esta consulta. El catálogo guardado se conserva. Reintenta más tarde o informa al equipo de SIIE.",
  program_import_not_configured:
    "Falta configurar Firecrawl y el dominio oficial en el servidor. Puedes llenar la ficha manualmente.",
  program_source_host_not_allowed:
    "Usa un enlace HTTPS directo de un dominio oficial habilitado para importar programas.",
  program_import_no_program:
    "No se identificó un programa en la página. Verifica que el enlace corresponda a la ficha del programa.",
  program_import_key_rejected:
    "Firecrawl rechazó la credencial. Revisa la clave del servidor antes de volver a extraer.",
  program_import_rate_limited:
    "Firecrawl limitó las consultas. Revisa el cupo del servicio o reintenta más tarde.",
  program_import_timeout:
    "La página tardó en responder. Reintenta o completa los campos manualmente.",
  program_import_invalid_response:
    "La página devolvió datos que no se pudieron interpretar como una ficha. Revisa el enlace.",
  program_import_failed:
    "No se pudo leer la página con Firecrawl. Revisa que esté disponible y vuelve a intentarlo.",
  agents_execution_migration_required:
    "Falta habilitar el registro de ejecuciones de los agentes. Solicite completar la actualización de la aplicación.",
  agents_ab_version_unavailable:
    "Seleccione una versión anterior guardada de este mismo agente para la comparación A/B.",
  agents_pricing_required:
    "Complete las tarifas por millón de tokens del modelo principal y del respaldo para aplicar el corte de presupuesto USD.",
  agents_cost_uncertain:
    "El consumo de una ejecución anterior no fue informado. Revise los registros antes de aplicar un corte USD al mismo período.",
  agents_note_required: "Escriba el contenido de la nota.",
  agents_action_not_allowed:
    "Esta acción no está permitida por el estado, las herramientas o los permisos del agente.",
  agents_action_conversation_required:
    "Seleccione una conversación real del mismo ámbito para crear una tarea o nota CRM.",
  agents_action_approval_required:
    "Esta acción requiere aprobación humana. Revise su contenido y pulse Aprobar en el borrador.",
  agents_archived_read_only:
    "Este agente está archivado. Restáurelo como borrador desde Revisión antes de editarlo.",
  agents_template_variable_missing:
    "Falta una variable de las instrucciones. Complete sus valores JSON o retire el marcador antes de revisar o usar el agente.",
  network_unavailable:
    "No se pudo conectar con el servidor. Revise la conexión y vuelva a intentarlo.",
  agents_migration_required:
    "La configuración de agentes aún no está disponible.",
  agents_revision_conflict: "El registro cambió. Actualice antes de guardar.",
  agents_scope_immutable:
    "La jerarquía guardada se conserva. Archive el perfil y cree otro para cambiar su ámbito.",
  agents_context_scope_immutable:
    "El programa o la solicitud de este contexto se conservan. Cree otro contexto para una postulación diferente.",
  agents_operation_conflict:
    "La operación no coincide con su confirmación anterior.",
  agents_invalid_guide: "El orientador no tiene programa, etapa ni padre.",
  agents_invalid_program_parent:
    "Seleccione un orientador como padre y un programa vigente.",
  agents_invalid_stage_parent:
    "Seleccione el agente y la etapa del mismo programa.",
  agents_hierarchy_cycle: "La jerarquía no puede contener ciclos.",
  agents_child_permission_expansion:
    "Los canales y permisos del hijo deben estar permitidos por sus padres.",
  agents_child_budget_expansion:
    "El presupuesto del hijo supera el de su padre.",
  agents_stage_approval_required:
    "La etapa o su versión necesita aprobación humana.",
  agents_active_children_require_pause: "Pause primero los subagentes activos.",
  agents_parent_or_agent_unavailable:
    "El agente o uno de sus padres no está activo y aprobado.",
  agents_review_required:
    "Apruebe explícitamente esta versión antes de activarla.",
  agents_human_confirmation_required:
    "Confirme la revisión e indique su evidencia o motivo.",
  agents_owner_unavailable_or_ambiguous:
    "Falta un responsable activo único para este contexto.",
  agents_assignment_conflict:
    "El agente protegido no coincide con el programa o etapa. Revise la asignación.",
  agents_source_not_approved_for_scope:
    "Una fuente no está publicada, vigente o aprobada para este ámbito.",
  agents_source_approval_required:
    "Confirme responsable, vigencia y aprobación de la fuente.",
  agents_source_publication_required:
    "Publique la fuente en Conocimiento antes de aprobar su alcance.",
  agents_incomplete_configuration:
    "Complete instrucciones, modelo principal, canales y presupuesto.",
  agents_guide_scope_occupied:
    "Ya existe un orientador institucional sin archivar. Su sustitución debe conservar primero los agentes de programa dependientes; no se puede restaurar un segundo orientador.",
  agents_program_scope_occupied:
    "Ya existe un agente sin archivar para este programa. Revise el responsable vigente antes de restaurar o crear otro.",
  agents_stage_scope_occupied:
    "Ya existe un agente sin archivar para esta etapa. Revise el responsable vigente antes de restaurar o crear otro.",
  agents_reply_not_allowed: "Esta configuración no permite respuestas.",
  agents_reply_capability_required:
    "La respuesta requiere la capacidad de responder con fuentes.",
  agents_budget_exhausted:
    "No hay presupuesto disponible en el agente o sus padres.",
  agents_request_already_consumed:
    "La solicitud ya se consumió. No se repetirá automáticamente.",
  agents_global_ai_gate_closed:
    "Habilite la IA y su conexión desde los ajustes existentes para probar con proveedor.",
  agents_consumption_confirmation_required:
    "Confirme el consumo de la prueba antes de llamar al proveedor.",
  agents_human_control: "La conversación está bajo atención humana.",
  agents_legacy_assignment_requires_review:
    "Revise la asignación anterior antes de adoptar los agentes de admisiones.",
  agents_configuration_changed:
    "La configuración cambió durante la prueba. El resultado quedó invalidado.",
  provider_response_timeout:
    "El proveedor de IA tardó demasiado y no confirmó una respuesta. Revisa Actividad y el consumo registrado antes de iniciar otra prueba; no se envió una respuesta al contacto desde el simulador.",
  provider_timeout_or_network:
    "No se pudo completar la conexión con el proveedor de IA. Revisa Actividad y su disponibilidad antes de repetir; tu configuración se conserva.",
  provider_temporary_failure:
    "El proveedor de IA está temporalmente indisponible. Espera unos minutos y revisa Actividad antes de probar otra vez. No necesitas cambiar el prompt ni la clave por este aviso.",
  provider_rate_limited:
    "El proveedor de IA alcanzó un límite temporal de solicitudes o de su cuenta. Revisa el cupo del proveedor en APIs y modelos y espera antes de repetir; aumentar el cupo del CRM no elimina ese límite externo.",
  admissions_invalid_structured_response:
    "El proveedor no devolvió el formato de respuesta requerido. Revise el modelo y el límite de respuesta; el consumo reportado se conserva en Actividad.",
  admissions_context_limit:
    "La consulta reúne más información de la que puede revisar el agente de una vez. Prueba con un programa concreto o reduce las fuentes e instrucciones repetidas. No se llamó al proveedor ni se envió un mensaje al contacto.",
  admissions_response_truncated:
    "El proveedor agotó el límite de respuesta antes de completar el JSON. Aumente el límite de tokens del agente o acote las instrucciones y la pregunta; el consumo informado se conserva.",
  admissions_invalid_json_response:
    "El proveedor devolvió un JSON incompleto o inválido. Revise el modelo y el límite de respuesta; el consumo informado se conserva.",
  admissions_invalid_memory_source:
    "El proveedor devolvió una referencia de memoria inválida. No se guardó esa memoria; revise las instrucciones y el modelo antes de repetir.",
  admissions_invalid_memory_response:
    "El proveedor devolvió memoria fuera del formato permitido. No se guardó esa memoria; revise las instrucciones y el modelo antes de repetir.",
  agents_usage_settlement_conflict:
    "No se pudo confirmar el registro de consumo de la respuesta. Revise Actividad antes de repetir la consulta.",
  agents_usage_settlement_initial_conflict:
    "No se confirmó la actualización inicial del consumo. La reserva se conserva; revise Actividad antes de repetir la consulta.",
  agents_usage_settlement_final_conflict:
    "La comprobación final del consumo detectó una discrepancia. La reserva se conserva; revise Actividad antes de repetir la consulta.",
  agents_stage_conditions_required:
    "Complete las condiciones y evidencia requeridas de la etapa.",
  agents_application_scope_mismatch:
    "La solicitud no corresponde al programa y período seleccionados.",
  agents_application_period_required:
    "La solicitud y su período deben seleccionarse juntos.",
  local_access_required: "El acceso requiere la aplicación local autorizada.",
  local_sql_copy_required:
    "Esta operación requiere el entorno local autorizado.",
  invalid_request: "Revise los campos y límites del formulario.",
  openrouter_key_missing: "Configure OpenRouter en Ajustes → APIs.",
  agents_name_required: "Indique el nombre del agente.",
  institutional_program_not_in_active_offer:
    "El programa ya no pertenece a la oferta vigente.",
  agents_conversation_unavailable:
    "La conversación está cerrada o ya no está disponible.",
  agents_not_found: "El agente ya no está disponible.",
  voice_profile_unavailable:
    "El perfil de voz está pausado o ya no está disponible. Actualiza las voces del agente y selecciona un perfil activo, o elige Automática.",
  sales_active_guide_required:
    "Selecciona un orientador de Admisiones activo antes de crear especialistas.",
  sales_guide_not_ready:
    "El orientador necesita un modelo, permisos de respuesta y configuración completa. Revísalo en Agentes.",
  sales_specialist_ambiguous:
    "Hay varios especialistas para un mismo programa. Revisa y conserva uno activo antes de preparar la creación.",
  sales_preview_changed:
    "Cambió el catálogo o la configuración. Prepara nuevamente la vista previa antes de guardar.",
  sales_ad_binding_invalid:
    "Revisa el ID del anuncio y el programa activo. Cada anuncio debe tener una única vinculación.",
  sales_review_required:
    "Revisa los especialistas y marca la confirmación antes de crearlos.",
  sales_memory_revision_conflict:
    "La memoria cambió durante la operación. Actualiza el hilo antes de reintentar.",
  sales_context_reset_changed:
    "Llegó información nueva o cambió la memoria. Actualiza el hilo y revisa lo último antes de reiniciar el contexto.",
  sales_context_reset_review_required:
    "Revisa qué información conservará el chat y confirma el cambio de contexto.",
  sales_context_restore_unavailable:
    "No hay un contexto anterior disponible para restaurar.",
  voice_institutional_only:
    "Los perfiles de voz se administran en el entorno institucional de RinovaPlus.",
  agents_channel_not_allowed:
    "El canal seleccionado no está permitido por esta configuración.",
  agents_input_before_assignment:
    "El mensaje es anterior a la asignación vigente.",
  agents_context_not_in_conversation:
    "El contexto no pertenece a esta conversación.",
  agents_application_scope_changed:
    "La solicitud institucional cambió. Revise el vínculo aprobado.",
  agents_provider_model_catalog_required:
    "El modelo no está en las opciones conocidas de este proveedor. Consulte su catálogo desde Ajustes → APIs.",
  agents_provider_not_configured:
    "Configure la credencial del proveedor seleccionado desde Ajustes → APIs.",
};
export const message = (code: string) =>
  errors[code] ??
  "No se pudo completar la operación. Revise la configuración y vuelva a cargar los datos.";

function validationMessage(fields: unknown) {
  const names: Record<string, string> = {
    operation_id: "Identificador de operación",
    revision: "Revisión",
    name: "Nombre",
    level: "Responsabilidad",
    parent_id: "Agente supervisor",
    program_id: "Programa",
    stage_id: "Etapa",
    configuration: "Configuración",
    provider: "Proveedor de IA",
    primary_model: "Modelo principal",
    fallback_model: "Modelo alternativo",
    max_tokens: "Máximo de tokens de salida",
    voice_profile_id: "Perfil de voz del agente",
    monthly_token_limit: "Límite mensual de tokens",
    allow_reply: "Permiso de respuesta",
    instructions: "Instrucciones",
    description: "Descripción operativa",
    operating_style: "Estilo operativo",
    risk_posture: "Postura de riesgo",
    escalation_policy: "Política de derivación humana",
    instruction_template: "Plantilla base",
    template_variables: "Variables JSON",
    tone: "Tono y personalidad",
    objectives: "Objetivos",
    rules: "Reglas",
    channels: "Canales",
    capabilities: "Capacidades",
    document_ids: "Fuentes",
    entry_rule: "Condición de entrada",
    exit_rule: "Condición de salida",
    evidence_required: "Evidencia requerida",
    note: "Motivo",
    confirmed: "Confirmación",
    state: "Estado",
    applicant_id: "Solicitud",
    period_id: "Período",
    mode: "Modo de asignación",
    agent_id: "Agente",
    context_id: "Contexto",
    config_version: "Versión de configuración",
    question: "Pregunta",
    call_provider: "Llamada al proveedor",
    acknowledge_consumption: "Confirmación de consumo",
    request_id: "Identificador de prueba",
    channel: "Canal",
    owner: "Responsable",
    valid_until: "Vigencia",
    entity_id: "Entidad",
    document_id: "Documento",
    conversation_id: "Conversación",
    offset: "Página",
  };
  const labels = Array.isArray(fields)
    ? [
        ...new Set(
          fields
            .filter((field): field is string => typeof field === "string")
            .map((field) => names[field.split(".").at(-1) ?? ""])
            .filter((label) => typeof label === "string"),
        ),
      ]
    : [];
  return labels.length
    ? `Revise estos campos: ${labels.join(", ")}.`
    : message("invalid_request");
}
const pendingMutations = new Map<string, string>();
export async function api<T>(
  path = "",
  method = "GET",
  body?: unknown,
): Promise<T> {
  if (method === "GET") {
    const seconds = readRetrySeconds();
    if (seconds)
      throw new Error(
        `Las consultas están en pausa durante ${seconds} segundos para respetar el límite temporal. Tu borrador se conserva.`,
      );
    return coordinatedRead(
      `agents:${institutionHeaders()["X-CSRF-Token"] ?? ""}:${path}`,
      () => request<T>(path, method, body),
    );
  }
  return request<T>(path, method, body);
}
async function request<T>(
  path: string,
  method: string,
  body?: unknown,
): Promise<T> {
  let signature = "";
  if (body && typeof body === "object" && "operation_id" in body) {
    const { operation_id, ...fields } = body as Record<string, unknown>;
    signature = JSON.stringify([path, method, fields]);
    const retained = pendingMutations.get(signature) ?? String(operation_id);
    pendingMutations.set(signature, retained);
    body = { ...fields, operation_id: retained };
  }
  const response = await fetch("/api/v1/agents" + path, {
    method,
    headers: {
      "X-CRM-Local": "1",
      ...institutionHeaders(),
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  }).catch((failure: unknown) => {
    if (failure instanceof TypeError)
      throw new Error(message("network_unavailable"));
    throw failure;
  });
  const result = await response.json().catch(() => null);
  if (response.status === 429)
    observeReadLimit(response.headers?.get("Retry-After") ?? null);
  institutionUnauthorized(response.status);
  if (signature && response.status < 500) pendingMutations.delete(signature);
  if (!response.ok) {
    // Log only bounded machine codes/status, never payloads, credentials or CRM text.
    const code = result?.code ?? result?.detail;
    const safeReason =
      typeof code === "string" && /^[a-z][a-z0-9_]{0,99}$/.test(code)
        ? code
        : "unclassified";
    console.warn(
      `RinovaPlus: Agentes HTTP ${response.status}; motivo ${safeReason}`,
    );
    const failure = new Error(
      response.status === 422 && result?.code === "invalid_request"
        ? validationMessage(result.fields)
        : message(result?.code ?? result?.detail),
    );
    const reference = response.headers?.get("X-SIIE-Correlation-ID");
    if (reference && /^[A-Za-z0-9_-]{1,100}$/.test(reference)) {
      Object.assign(failure, { correlationId: reference });
      failure.message += ` Referencia SIIE: ${reference}.`;
    }
    throw failure;
  }
  return result as T;
}
export const mutation = (revision: number) => ({
  revision,
  operation_id: crypto.randomUUID(),
});
export const blankConfiguration = (): Configuration => ({
  provider: "openrouter",
  description: "",
  operating_style: "",
  risk_posture: "balanced",
  escalation_policy: "",
  instruction_template: "custom",
  template_variables: {},
  customized: true,
  route: "admissions",
  global_enabled: false,
  fallback_provider: null,
  monthly_usd_limit: 0,
  usage_alert_percent: 80,
  hard_stop: true,
  input_usd_per_million: null,
  output_usd_per_million: null,
  fallback_input_usd_per_million: null,
  fallback_output_usd_per_million: null,
  ab_enabled: false,
  ab_variant: "A",
  ab_compare_version: null,
  ab_traffic_percent: 50,
  industry_policies: ["academy", "privacy"],
  memories: [
    "short",
    "semantic",
    "business_summary",
    "customer_profile",
    "knowledge",
    "vertical",
    "regulated",
  ],
  require_human_approval: true,
  allow_safe_actions: false,
  allow_crm_update: false,
  instructions: "",
  objectives: [],
  rules: [],
  tone: "",
  channels: ["local"],
  capabilities: [],
  document_ids: [],
  primary_model: "",
  fallback_model: "",
  max_tokens: 700,
  monthly_token_limit: 0,
  allow_reply: false,
});

export const memoryChoices = [
  [
    "short",
    "Memoria corta",
    "Usar el historial reciente de esta conversación.",
  ],
  [
    "semantic",
    "Memoria semántica",
    "Recuperar fragmentos relevantes mediante el índice léxico disponible.",
  ],
  [
    "business_summary",
    "Resumen institucional",
    "Usar el ámbito y el programa institucional confirmados.",
  ],
  [
    "customer_profile",
    "Perfil del aspirante",
    "Usar sus preferencias declaradas y su ficha CRM; no confirma matrícula.",
  ],
  [
    "knowledge",
    "Basado en conocimiento",
    "Consultar documentos publicados y aprobados para este ámbito.",
  ],
  [
    "campaigns",
    "Historial de campañas",
    "Consultar estado y fechas de campañas del programa, sin destinatarios personales.",
  ],
  [
    "incidents",
    "Historial de incidentes",
    "Consultar las tareas de esta misma conversación.",
  ],
  [
    "workflows",
    "Historial de flujos",
    "Consultar actividad operativa de este agente.",
  ],
  [
    "vertical",
    "Contexto del programa",
    "Incluir oferta, tarifas, asignaturas y requisitos de las fuentes institucionales vigentes.",
  ],
  [
    "regulated",
    "Contexto regulado",
    "Incluir recordatorios adicionales de privacidad y límites académicos.",
  ],
  [
    "collective",
    "Memoria colectiva",
    "Compartir sólo políticas y fuentes públicas autorizadas; nunca datos de otro aspirante.",
  ],
] as const;

export const toolGroups = [
  {
    name: "Orientación e Inbox",
    items: [
      ["program.read", "Consultar oferta institucional"],
      ["sources.read", "Consultar fuentes aprobadas"],
      ["conversation.reply", "Responder conversaciones"],
      ["human.handoff", "Derivar al asesor"],
    ],
  },
  {
    name: "Asesor y CRM",
    items: [
      ["advisor.actions", "Crear acciones asistidas"],
      ["advisor.summary", "Preparar resúmenes"],
      ["crm.update", "Registrar notas y tareas CRM"],
    ],
  },
  {
    name: "Analítica y seguimiento",
    items: [
      ["analytics.read", "Leer indicadores agregados"],
      ["analytics.report", "Preparar reportes"],
      ["campaigns.draft", "Crear borradores de campañas"],
      ["campaigns.suggest", "Sugerir campañas"],
      ["compliance.check", "Revisar cumplimiento institucional"],
    ],
  },
] as const;

export type AgentConsole = {
  installed: boolean;
  versions?: number[];
  metrics: null | {
    runs_7d: number;
    successes_7d: number;
    errors_7d: number;
    fallbacks_7d: number;
    latency_ms: number | null;
    health: number | null;
    tokens_reserved: number;
    tokens_reported: number | null;
    tokens_budget_used: number;
    usd_estimate: number | null;
    usd_reserved: number | null;
    unknown_cost_runs: number;
  };
  runs: {
    request_id: string;
    version: number;
    provider: string;
    model: string;
    variant: string;
    state: string;
    error: string | null;
    input_tokens: number | null;
    output_tokens: number | null;
    latency_ms: number | null;
    cost_usd_estimate: number | null;
    created_at: string;
    attempts_json: string;
  }[];
  notes: { text: string; at: string }[];
  actions: {
    action_id: string;
    kind: string;
    title: string;
    context: string;
    impact: string;
    risk: string;
    state: string;
    conversation_id: string | null;
    agent_version: number;
    task_id?: string;
  }[];
  conversations: { id: string; label: string }[];
};

export const instructionTemplates = {
  admissions:
    "Atiendes Admisiones de CBN con el nombre de atención configurado. Tu especialidad es {agent_specialty}.\n{agent_description}\nOrienta sobre la oferta vigente usando las fuentes institucionales suministradas. Si el aspirante no ha confirmado su programa, ayúdalo a identificarlo sin elegir por él. Conserva sus preferencias ya declaradas y deriva al equipo ante solicitudes humanas, información insuficiente, pagos o decisiones de matrícula. Habla en español colombiano cercano y profesional, con ideas breves completas y emojis discretos. Si preguntan si eres IA, responde con transparencia.",
  program:
    "Atiendes el programa con identificador {program_id} de CBN con el nombre de atención configurado.\n{agent_description}\nAtiende el programa y la jornada confirmados en el contexto institucional, o aclara el interés comercial recibido. Explica tarifas, asignaturas y requisitos con sus fuentes vigentes. No inventes información ni asumas que otro programa tiene las mismas condiciones. Conserva las preferencias declaradas y deriva al equipo cuando soliciten una persona o falte evidencia. Usa ideas breves completas y español colombiano profesional. Si preguntan si eres IA, responde con transparencia.",
};
