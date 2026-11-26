"""Provider adapters for the canonical bounded request, not an engine selector."""

import json

from app.modules.ai.domain.models import AiSettings
from app.modules.ai.infrastructure.providers import AiError


async def generate(gateway, route, body, guard):
    provider, model = route["provider"], route["model"]
    if provider == "gemini":
        guard()
        if hasattr(gateway, "gemini_generation"):
            return await gateway.gemini_generation(model, body, before_attempt=guard)
        return await gateway.request(provider, "POST", "models/" + model + ":generateContent", body)
    if provider == "openrouter":
        from app.institutional.language_resilience import generate as openrouter_request
        return await openrouter_request(gateway, route, body, guard)
    from app.institutional.language_resilience import message_content
    system = "\n".join(p.get("text", "") for p in body.get("systemInstruction", {}).get("parts", []))
    schema = body["generationConfig"].get("responseSchema", {})
    system += "\nDevuelve sólo JSON válido con este contrato: " + json.dumps(schema, ensure_ascii=False)
    messages = []
    for content in body["contents"]:
        parts = message_content(content)
        if not isinstance(parts, str):
            raise AiError("language_backup_modality_unsupported", 409)
        messages.append({"role": "assistant" if content.get("role") == "model" else "user", "content": parts})
    limits = body["generationConfig"]
    config = AiSettings(provider=provider, model=model, max_tokens=limits["maxOutputTokens"],
                        output_tokens=limits["maxOutputTokens"], temperature=limits.get("temperature", 0.3))
    guard()
    text = await gateway.generate(provider, model, config, system, messages, before_attempt=guard)
    guard()
    reason = getattr(gateway, "last_response_metadata", {}).get("finish_reason")
    if reason in {"MAX_TOKENS", "length", "max_tokens"}:
        raise AiError("language_reply_truncated", 502)
    if reason in {"content_filter", "tool_calls"}:
        raise AiError("language_reply_incomplete", 502)
    if not isinstance(text, str) or not text.strip() or len(text) > 32000:
        raise AiError("language_backup_invalid_response", 502)
    try:
        json.loads(text)
    except ValueError:
        raise AiError("language_reply_invalid_contract", 502) from None
    usage = getattr(gateway, "last_usage", None) or {}
    result = {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": text}]}}],
              "usageMetadata": {"promptTokenCount": usage.get("input"), "candidatesTokenCount": usage.get("output")}}
    if "crm_observations" in schema.get("properties", {}):
        from app.institutional.grounded_replies import parse
        try:
            parse(result, allow_wait="esperar" in schema["properties"]["decision"].get("enum", []))
        except (ValueError, KeyError, IndexError, TypeError):
            raise AiError("language_reply_invalid_contract", 502) from None
    return result
