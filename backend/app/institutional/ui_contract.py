"""Typed, bounded UI metadata; no credential values or database configuration."""

from fastapi import Request

from app.institutional.auth import authorize
from app.institutional.models import (
    AI,
    PROVIDER_CATEGORIES,
    Budgets,
    Institution,
    Profile,
)
from app.institutional.policy import ACTIONS, MODULES
from app.institutional.store import transaction

MODULE_LABELS = dict(
    zip(
        MODULES,
        (
            "Resumen",
            "CRM",
            "Inbox",
            "Canales",
            "Asistente",
            "Agentes",
            "Conocimiento",
            "Memoria colectiva",
            "Mensajería masiva",
            "Campañas y remarketing",
            "Meta Ads",
            "Inteligencia",
            "Admisiones",
            "Ajustes",
        ),
        strict=True,
    )
)
LABELS = {
    "name": "Nombre de la institución",
    "timezone": "Zona horaria",
    "locale": "Formato regional",
    "full_name": "Nombre completo",
    "phone": "Teléfono",
    "role_label": "Cargo",
    "avatar_url": "URL de la imagen de perfil",
    "enabled": "Solicitar asistencia de IA",
    "provider": "Proveedor principal",
    "backup_provider": "Proveedor de respaldo",
    "system_prompt": "Instrucciones del asistente",
    "max_tokens": "Máximo de tokens",
    "temperature": "Temperatura",
    "model": "Modelo principal guardado",
    "backup_model": "Modelo de respaldo guardado",
    "fallback_model": "Modelo alternativo principal",
    "backup_fallback_model": "Modelo alternativo de respaldo",
    "model_failover_enabled": "Usar modelos alternativos si falla el principal",
    "fallback_enabled": "Permitir alternativa de modelo",
    "human_reply_style_enabled": "Estilo de respuesta natural",
    "brief_responses": "Preferir respuestas breves",
    "split_responses": "Dividir respuestas",
    "show_typing": "Mostrar indicador de escritura",
    "quote_first_reply": "Citar el mensaje del cliente sólo en la primera parte de WhatsApp",
    "wait_seconds": "Espera tras recibir mensajes (segundos)",
    "typing_ms": "Demora inicial (ms)",
    "fragment_delay_ms": "Demora entre fragmentos (ms)",
    "reply_min_chunk_delay_ms": "Demora mínima entre fragmentos (ms)",
    "chars_per_message": "Caracteres por fragmento",
    "output_tokens": "Límite de tokens de respuesta",
    "recent_messages": "Mensajes recientes de contexto",
    "history_chars": "Caracteres por mensaje de contexto",
    "model_fallback_mode": "Selección de modelos alternativos",
    "model_fallback_attempt_limit": "Intentos totales por proveedor",
    "voice_name": "Nombre de la voz",
    "vision_analysis_provider": "Proveedor de análisis de imágenes",
    "media.voice_enabled": "Habilitar configuración de voz",
    "media.prefer_voice": "Preferir voz",
    "media.reply_audio_with_voice": "Responder audios con voz",
    "media.voice_provider": "Proveedor de voz",
    "media.voice_model": "Modelo de voz guardado",
    "media.voice_id": "Identificador de voz guardado",
    "media.voice_prompt": "Instrucciones para la voz",
    "media.voice_limit_enabled": "Limitar respuestas de voz",
    "media.voice_limit": "Máximo de respuestas de voz",
    "media.audio_model": "Modelo de audio guardado",
    "media.audio_provider": "Proveedor de análisis de audio",
    "media.vision_model": "Modelo de imágenes guardado",
    "media.search_provider": "Proveedor de búsqueda",
    "daily_tokens": "Tokens al día",
    "daily_messages": "Mensajes al día",
    "daily_usd_micros": "Presupuesto diario (microunidades de USD)",
    "requests_per_minute": "Solicitudes por minuto y usuario",
    "max_active_integrations": "Máximo de cuentas configuradas",
}
READONLY = {
    "model",
    "backup_model",
    "fallback_model",
    "backup_fallback_model",
    "media.voice_model",
    "media.voice_id",
    "media.audio_model",
    "media.vision_model",
}


def field_specs(model):
    schema = model.model_json_schema()
    properties = dict(schema["properties"])
    if "media" in properties:
        media = properties.pop("media")
        reference = media["$ref"].split("/")[-1]
        properties.update(
            {
                "media." + key: value
                for key, value in schema["$defs"][reference]["properties"].items()
            }
        )
    result = []
    for path, value in properties.items():
        if path not in LABELS:
            continue
        options = value.get("enum", [value["const"]] if "const" in value else None)
        nullable = False
        if "anyOf" in value:
            options = next(
                (part.get("enum") for part in value["anyOf"] if part.get("enum")), None
            )
            nullable = any(part.get("type") == "null" for part in value["anyOf"])
        kind = value.get("type", "string")
        group = (
            "Voz y multimedia"
            if path.startswith("media.")
            or path in {"voice_name", "vision_analysis_provider"}
            else "Mensajes y contexto"
            if path
            in {
                "wait_seconds",
                "typing_ms",
                "fragment_delay_ms",
                "reply_min_chunk_delay_ms",
                "chars_per_message",
                "output_tokens",
                "recent_messages",
                "history_chars",
                "show_typing",
                "quote_first_reply",
                "split_responses",
                "brief_responses",
                "human_reply_style_enabled",
            }
            else "Configuración general"
        )
        result.append(
            {
                "path": path,
                "label": LABELS[path],
                "type": kind,
                "group": group,
                "options": options,
                "nullable": nullable,
                "minimum": value.get("minimum"),
                "maximum": value.get("maximum"),
                "max_length": value.get("maxLength"),
                "read_only": path in READONLY,
                "multiline": path in {"system_prompt", "media.voice_prompt"},
            }
        )
    return result


def contract():
    labels = {
        "crm": "CRM",
        "inbox": "Inbox",
        "settings.crm": "Configuración del CRM",
        "settings.institution": "Institución",
        "settings.ai": "Ajustes de IA",
        "settings.providers": "Proveedores y modelos",
        "settings.channels": "Canales",
        "settings.webhooks": "Webhooks",
        "settings.modules": "Disponibilidad de módulos",
        "settings.budgets": "Límites técnicos",
        "users": "Usuarios",
        "roles": "Roles y permisos",
        "sessions": "Sesiones",
        "audit": "Auditoría",
        "agents": "Agentes",
        "sources": "Fuentes de conocimiento",
        "campaigns": "Campañas",
        "ads": "Publicidad",
    }
    actions = []
    for action in ACTIONS:
        owner, verb = action.rsplit(".", 1)
        actions.append(
            {
                "id": action,
                "group": labels[owner],
                "label": ("Consultar " if verb == "read" else "Administrar ")
                + labels[owner].lower(),
            }
        )
    return {
        "version": "cbn-institutional-ui-v1",
        "fields": {
            "institution": field_specs(Institution),
            "ai": field_specs(AI),
            "budgets": field_specs(Budgets),
            "profile": field_specs(Profile),
        },
        "provider_categories": PROVIDER_CATEGORIES,
        "actions": actions,
        "modules": [
            {"id": identity, "label": label}
            for identity, label in MODULE_LABELS.items()
        ],
        "model_selection_authority": "models",
        "provider_operations_available": False,
    }


def install(app, settings):
    @app.get("/api/institution/contracts")
    def metadata(request: Request):
        with transaction(settings, anonymous=True) as cursor:
            authorize(cursor, settings, request.state.authority)
        return {
            **contract(),
            "knowledge_operations": settings.ticket.get("version")
            in {
                "cbn-institutional-knowledge-p6-v1",
                "cbn-institutional-broadcast-p7-v1",
                "cbn-institutional-campaign-p8-v1", 'cbn-institutional-ads-p9-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'},
            "agent_operations": settings.ticket.get("version")
            in {
                "cbn-institutional-agents-p5-v1",
                "cbn-institutional-knowledge-p6-v1",
                "cbn-institutional-broadcast-p7-v1",
                "cbn-institutional-campaign-p8-v1", 'cbn-institutional-ads-p9-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'},
            "channel_operations": settings.ticket.get("version")
            in {
                "cbn-institutional-channels-p4-v1",
                "cbn-institutional-agents-p5-v1",
                "cbn-institutional-knowledge-p6-v1",
                "cbn-institutional-broadcast-p7-v1",
                "cbn-institutional-campaign-p8-v1", 'cbn-institutional-ads-p9-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'},
        }
