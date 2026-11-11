export type AiProvider =
  | "gemini"
  | "nvidia"
  | "openai"
  | "anthropic"
  | "hermes"
  | "groq"
  | "mistral"
  | "openrouter"
  | "kimi"
  | "xai";
export const providerNames: Record<AiProvider, string> = {
  gemini: "Google / Gemini",
  nvidia: "NVIDIA NIM",
  openai: "OpenAI",
  anthropic: "Claude / Anthropic",
  hermes: "Hermes Agent",
  groq: "Groq",
  mistral: "Mistral",
  openrouter: "OpenRouter",
  kimi: "Kimi / Moonshot AI",
  xai: "xAI / Grok",
};
export const credentialNames = {
  ...providerNames,
  elevenlabs: "ElevenLabs",
  google_tts: "Google Cloud TTS",
  tavily: "Tavily Search",
  brave: "Brave Search API",
  serpapi: "SerpAPI",
};
export type CredentialProvider = keyof typeof credentialNames;
export type MediaConfig = {
  voice_enabled: boolean;
  prefer_voice: boolean;
  reply_audio_with_voice: boolean;
  voice_provider: "elevenlabs" | "google_tts" | "piper";
  voice_model: string;
  voice_id: string;
  voice_prompt: string;
  voice_limit_enabled: boolean;
  voice_limit: number;
  audio_model: string;
  audio_provider: "gemini" | "groq";
  vision_model: string;
  search_provider: "tavily" | "brave" | "serpapi";
};
export const defaultMedia: MediaConfig = {
  voice_enabled: false,
  prefer_voice: false,
  reply_audio_with_voice: false,
  voice_provider: "elevenlabs",
  voice_model: "",
  voice_id: "",
  voice_prompt: "",
  voice_limit_enabled: false,
  voice_limit: 3,
  audio_model: "",
  audio_provider: "gemini",
  vision_model: "",
  search_provider: "tavily",
};
export type VoiceCatalog = {
  voices: { id: string; name: string; language: string }[];
  models: { id: string; name: string }[];
  ready: boolean;
  local: boolean;
};
export type AiConfig = {
  provider_models?: Partial<Record<AiProvider, string>>;
  voice_models?: Partial<
    Record<MediaConfig["voice_provider"], { model: string; voice_id: string }>
  >;
  media?: MediaConfig;
  enabled: boolean;
  provider: AiProvider;
  model: string;
  fallback_enabled: boolean;
  fallback_model: string;
  backup_provider: AiProvider | null;
  backup_model: string;
  backup_fallback_model: string;
  system_prompt: string;
  max_tokens: number;
  temperature: number;
  brief_responses: boolean;
  split_responses: boolean;
  wait_seconds: number;
  typing_ms: number;
  chars_per_message: number;
  fragment_delay_ms: number;
  output_tokens: number;
  recent_messages: number;
  history_chars: number;
  show_typing: boolean;
};
export type AiSnapshot = {
  revision: number;
  settings: AiConfig;
  outbound_enabled: boolean;
  credential_revision: number;
  credential_storage_available: boolean;
  storage_backend?: string;
  providers: {
    id: CredentialProvider;
    configured: boolean;
    environment_variable: string;
    credential_source: "local" | "environment" | "none";
  }[];
};
export type AiModel = {
  id: string;
  name: string;
  output_limit: number | null;
  temperature: boolean;
  max_temperature: number | null;
};
export type AiTestResult = {
  revision: number;
  provider: AiProvider;
  model: string;
  text: string;
  attempts: { provider: AiProvider; model: string; status: string }[];
  plan: { text: string; after_ms: number }[];
  history_messages_used: number;
  effective_output_tokens: number;
  typing_requested: boolean;
  typing_available: boolean;
  delivered: boolean;
};
const messages: Record<string, string> = {
  provider_context_required:
    "Inicie una conversación nueva para continuar con el contexto del modelo.",
  provider_context_expired:
    "El contexto del modelo venció. Inicie una conversación nueva.",
  provider_context_full:
    "El contexto del modelo alcanzó su límite seguro. Inicie una conversación nueva.",
  provider_endpoint_missing:
    "Falta completar la configuración del proveedor.",
  provider_history_unsupported:
    "Este modelo requiere un contrato de historial que no está habilitado. No se envió la conversación.",
  model_selection_not_saved:
    "Guarde el modelo seleccionado antes de revisar su estado.",
  model_selection_required:
    "Seleccione y guarde un modelo antes de revisar su estado.",
  ai_sql_schema_required:
    "Falta completar la configuración de proveedores IA.",
  audio_catalog_required:
    "Carga el catálogo de transcripción Groq y selecciona un modelo de audio disponible.",
  audio_model_unsupported:
    "El modelo seleccionado no admite transcripción Groq.",
  invalid_media: "El archivo no coincide con un audio o imagen admitidos.",
  media_too_large: "El adjunto supera el máximo de 4 MB.",
  analysis_model_required:
    "Seleccione el modelo de análisis de audio o visión en Ajustes > IA.",
  analysis_incomplete:
    "El análisis del adjunto no se completó o superó su límite seguro. No se utilizó contenido incompleto ni se generó una respuesta. Revise el modelo de análisis en Ajustes > IA antes de iniciar un nuevo intento.",
  voice_catalog_required:
    "Cargue las voces y seleccione una voz existente de su cuenta en Ajustes > APIs.",
  voice_model_required:
    "Seleccione un modelo de voz disponible en Ajustes > APIs.",
  piper_unavailable:
    "Piper no está disponible. Revise la configuración.",
  conversation_expired:
    "La conversación venció. Inicie una conversación nueva.",
  conversation_configuration_changed:
    "La configuración cambió. Inicie una conversación nueva.",
  conversation_context_changed:
    "El contexto de esta sesión cambió durante la respuesta. Inicie una conversación nueva antes de continuar.",
  turn_already_started:
    "Este envío ya empezó. No se reintenta para evitar duplicar costes.",
  conversation_storage_unavailable:
    "No se pudo guardar el límite de voz. Inténtelo de nuevo.",
  media_provider_rejected:
    "El proveedor rechazó la solicitud. Revise su clave, permisos y saldo.",
  search_failed: "La búsqueda no devolvió un resultado válido.",
  search_query_invalid:
    "La búsqueda admite hasta 400 caracteres y 50 palabras.",

  local_access_required:
    "No tiene acceso a esta configuración.",
  invalid_request:
    "Revise los campos: hay un valor vacío, incompatible o fuera de rango.",
  settings_revision_conflict:
    "La configuración cambió en otra pestaña. Recargue los ajustes antes de guardar.",
  settings_storage_unavailable:
    "No se pudieron guardar los ajustes. Revise sus permisos.",
  outbound_disabled:
    "Autorice las consultas externas en Ajustes > APIs antes de cargar modelos o probar IA.",
  provider_key_missing:
    "Guarde la API key de este proveedor en Ajustes > APIs.",
  credential_storage_unsupported:
    "No se pudo guardar la credencial.",
  credential_storage_unavailable:
    "No se pudo acceder al almacén de credenciales. Revise sus permisos.",
  credential_revision_conflict:
    "Las credenciales o el permiso cambiaron en otra pestaña. Recargue los ajustes antes de continuar.",
  model_catalog_required:
    "Cargue los modelos de cada proveedor elegido antes de habilitar o probar IA.",
  model_temperature_unsupported:
    "El modelo no admite temperatura. Seleccione otro modelo compatible.",
  model_temperature_limit_exceeded:
    "La temperatura supera el máximo informado por el modelo.",
  model_output_limit_exceeded:
    "El límite de tokens supera la capacidad informada por el modelo.",
  ai_disabled: "Habilite y guarde IA antes de continuar.",
  operation_busy: "Ya hay una operación IA en curso. Espere a que termine.",
  provider_rejected_request:
    "El proveedor rechazó la solicitud. Revise credencial, modelo y parámetros; no se ejecutó fallback.",
  provider_temporary_failure: "El proveedor no está disponible temporalmente.",
  provider_rate_limited:
    "El proveedor indicó un límite de solicitudes o cuota (HTTP 429). Revise el panel del proveedor antes de reintentar.",
  provider_timeout_or_network:
    "El proveedor agotó el tiempo de espera o no pudo conectarse.",
  provider_connection_failed:
    "No se pudo establecer la conexión con el proveedor. Revise la red y la configuración.",
  provider_response_timeout:
    "El proveedor no respondió dentro del tiempo de lectura permitido. Revise su disponibilidad antes de reintentar.",
  provider_protocol_failure:
    "El proveedor interrumpió la respuesta. Inténtelo de nuevo.",
  provider_invalid_json:
    "El proveedor devolvió un formato de respuesta inválido.",
  all_models_unavailable: "No se obtuvo respuesta de los modelos configurados.",
  test_deadline_exceeded: "La solicitud alcanzó su límite de tiempo.",
  provider_empty_or_blocked_response:
    "El proveedor no devolvió texto utilizable o bloqueó la respuesta.",
  provider_invalid_response: "El proveedor devolvió una respuesta inválida.",
  provider_response_too_large:
    "La respuesta del proveedor excedió el límite seguro.",
  provider_output_too_large: "El texto recibido excedió el límite permitido.",
  model_catalog_too_large:
    "El catálogo excedió el límite seguro. No se cargó un catálogo parcial.",
};
export async function aiRequest<T>(
  path: string,
  method = "GET",
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  try {
    const response = await fetch(`/api/ai/${path}`, {
      method,
      headers: { "Content-Type": "application/json", "X-CRM-Local": "1" },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: signal
        ? AbortSignal.any([
            signal,
            AbortSignal.timeout(path === "media-chat" ? 110000 : 55000),
          ])
        : AbortSignal.timeout(path === "media-chat" ? 110000 : 55000),
      cache: "no-store",
    });
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      const code =
        typeof data?.code === "string" && Object.hasOwn(messages, data.code)
          ? data.code
          : undefined;
      throw Object.assign(
        new Error(code ? messages[code] : `No se pudo completar la operación IA (HTTP ${response.status}).`),
        { code: code ?? "ai_request_failed", httpStatus: response.status },
      );
    }
    if (data === null) {
      throw Object.assign(new Error("El backend devolvió una respuesta no válida."), { httpStatus: response.status });
    }
    return data as T;
  } catch (error) {
    if (
      error instanceof Error &&
      (Object.values(messages).includes(error.message) || Number.isInteger((error as Error & { httpStatus?: number }).httpStatus))
    )
      throw error;
    throw new Error(
      "No se pudo acceder al servicio. Inténtelo de nuevo.",
      { cause: error },
    );
  }
}
