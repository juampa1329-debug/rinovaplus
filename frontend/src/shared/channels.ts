export const channelKeys = [
  "whatsapp",
  "instagram",
  "messenger",
  "facebook",
  "tiktok",
] as const;
export type ChannelKey = (typeof channelKeys)[number];
export type ChannelAccount = {
  channel: ChannelKey;
  configuration: Record<string, string>;
  state: string;
  revision: number;
  capabilities: {
    asset?: Record<string, string>;
    numbers?: Record<string, string>[];
    messages?: boolean;
    comments?: boolean;
  };
  credentials: string[];
  lastError: string | null;
  verifiedAt: string | null;
};
export const channelReferences = {
  whatsapp: {
    name: "WhatsApp",
    purpose: "Número oficial de admisiones · WhatsApp Cloud API",
  },
  instagram: {
    name: "Instagram",
    purpose: "Mensajes y comentarios de una cuenta profesional",
  },
  messenger: {
    name: "Messenger",
    purpose: "Mensajes privados de la página de Facebook",
  },
  facebook: {
    name: "Facebook",
    purpose: "Comentarios públicos de la página del Instituto",
  },
  tiktok: {
    name: "TikTok",
    purpose: "Business Messaging y comentarios de videos propios",
  },
};
export const channelStates: Record<string, string> = {
  unconfigured: "Sin configurar",
  configured: "Datos guardados",
  validated: "Acceso a API validado",
  awaiting_webhook: "Suscripción activa · esperando webhook",
  connected: "Conectado",
  paused: "Pausado",
  attention_required: "Requiere revisar permisos o credenciales",
};
const errors: Record<string, string> = {
  channels_ui_capability_unavailable:
    "Esta función todavía no está habilitada.",
  invalid_crm_stage: "Selecciona una etapa activa del CRM.",
  channels_schema_required:
    "La configuración de canales todavía requiere actualizar el esquema SQL local.",
  channels_storage_unavailable:
    "No se pudo acceder a los canales en SQL Server. Reintenta la consulta.",
  channel_configuration_incomplete:
    "Completa los identificadores, la versión API, el token de acceso, el secreto de la aplicación y el token de verificación.",
  provider_permission_or_request_rejected:
    "La plataforma rechazó la solicitud. Revisa los datos, los permisos y el acceso de la aplicación a ese recurso.",
  meta_access_token_expired:
    "El Access Token de Meta venció. Genera un token nuevo en el panel de Meta para desarrollo, actualiza el campo Access Token, guarda los datos y vuelve a pulsar Validar acceso.",
  meta_access_token_invalid:
    "Meta rechazó el Access Token. Genera un token válido para esta aplicación en el panel de Meta, actualiza Access Token, guarda los datos y vuelve a pulsar Validar acceso.",
  phone_not_in_waba: "El Phone Number ID no pertenece a la WABA indicada.",
  public_https_callback_required:
    "Ingresa el callback HTTPS público registrado en la plataforma para activar la suscripción.",
  channel_configuration_changed:
    "La configuración cambió. Actualiza el estado antes de guardar nuevamente.",
  channel_identity_has_history:
    "Este canal ya tiene historial. Puedes actualizar sus tokens y su callback; cambiar la cuenta requiere conservar y reasignar antes las conversaciones existentes.",
  provider_connection_failed:
    "No se pudo alcanzar la plataforma. Tus datos guardados se conservan.",
  provider_unavailable:
    "La plataforma no está disponible. Reintenta más tarde.",
  provider_outcome_unknown:
    "La plataforma no confirmó el resultado. Consulta su configuración antes de repetir la operación.",
  channel_encryption_key_unavailable:
    "No está disponible la clave privada de cifrado del backend. No vuelvas a guardar credenciales hasta recuperar su volumen.",
  invalid_request: "Revisa los campos: hay datos con formato no válido.",
  initial_crm_stage_required:
    "Seleccioná una etapa inicial activa para crear aspirantes desde los webhooks.",
  local_access_required:
    "Esta configuración requiere acceso desde la aplicación local.",
};
export async function channelRequest<T>(
  path: string,
  method = "GET",
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(path, {
    method,
    signal,
    cache: "no-store",
    credentials: "same-origin",
    headers: {
      "X-CRM-Local": "1",
      ...(method !== "GET" ? { "Content-Type": "application/json" } : {}),
    },
    ...(method !== "GET" ? { body: JSON.stringify(body ?? {}) } : {}),
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) {
    const code =
      typeof result.detail === "string" ? result.detail : result.code;
    throw new Error(
      errors[code] ||
        "No se pudo completar la operación. Revisa la configuración y reintenta.",
    );
  }
  return result as T;
}
