"""P21: guarded backups for grounded text, with a reservation per attempted route.

No audio is forwarded to a text model. A known rejection may select the next
approved route; ambiguous inference results keep the original uncertain state.
"""

import asyncio
import json
import math
from time import monotonic

from fastapi import HTTPException

from app.institutional.crypto import unseal
from app.institutional.db import institution, key, one, uid
from app.institutional.settings import setting
from app.institutional.store import transaction
from app.modules.ai.domain.resilience import LanguageResilience, can_failover
from app.modules.ai.infrastructure.providers import AiError, ProviderGateway


def snapshot(c, settings):
    value = setting(c, settings, "ai")
    policy = LanguageResilience.model_validate(value["document"].get("language_resilience", {}))
    result = {"revision": value["revision"], "routes": [], "keys": {}, "credentials": {}}
    if not policy.enabled:
        return result
    for route in policy.routes:
        secret = one(c, "SELECT * FROM crm_access.Secret WHERE InstitutionId=? AND Scope='provider' "
                     "AND OwnerRef=? AND Kind='api_key' AND State='staged'", institution(settings), route.provider)
        if not secret:
            continue
        identity = uid(str(secret["SecretId"]))
        result["keys"][route.provider] = unseal(key(settings), {
            "institution": institution(settings), "scope": "provider", "owner": route.provider,
            "kind": "api_key", "version": secret["VersionNo"], "secret_id": identity,
        }, secret["Nonce"], secret["Ciphertext"])
        result["credentials"][route.provider] = (identity, secret["VersionNo"])
        result["routes"].append(route.model_dump())
    return result


def assert_snapshot(c, settings, saved):
    if setting(c, settings, "ai")["revision"] != saved["revision"]:
        raise HTTPException(409, "language_backup_configuration_changed")
    for provider, identity in saved["credentials"].items():
        secret = one(c, "SELECT SecretId,VersionNo FROM crm_access.Secret WHERE InstitutionId=? "
                     "AND Scope='provider' AND OwnerRef=? AND Kind='api_key' AND State='staged'",
                     institution(settings), provider)
        if not secret or (uid(str(secret["SecretId"])), secret["VersionNo"]) != identity:
            raise HTTPException(409, "language_backup_configuration_changed")


def reservation(settings, saved, route, incoming, outgoing):
    from app.institutional.comment_ai import reserve_budget

    with transaction(settings, True, anonymous=True) as c:
        assert_snapshot(c, settings, saved)
        budget = setting(c, settings, "budgets")["document"]
        reserve_budget(c, settings, "tokens", incoming + outgoing, budget["daily_tokens"])
        micros = max(1, math.ceil(incoming * route["input_usd_per_million"] + outgoing * route["output_usd_per_million"]))
        reserve_budget(c, settings, "usd", micros / 1000000, budget["daily_usd_micros"] / 1000000)


async def compatible(gateway, route, body):
    models = await gateway.models(route["provider"], account_catalog=True)
    model = next((m for m in models if m.id == route["model"]), None)
    if not model:
        raise AiError("language_backup_model_unavailable", 409)
    details = gateway.catalog_details.get(route["provider"], {}).get(route["model"], {})
    incoming = len(json.dumps(body, ensure_ascii=False).encode()) + 512
    outgoing = body["generationConfig"]["maxOutputTokens"]
    context = details.get("context_length")
    if not context or incoming + outgoing > context or not model.output_limit or outgoing > model.output_limit:
        raise AiError("language_backup_context_incompatible", 409)
    if not model.temperature:
        raise AiError("language_backup_parameters_incompatible", 409)
    if route["provider"] == "openrouter":
        if "response_format" not in details.get("supported_parameters", []):
            raise AiError("language_backup_parameters_incompatible", 409)
        for field in ("input_usd_per_million", "output_usd_per_million"):
            price = details.get(field)
            if price is None or price > route[field]:
                raise AiError("language_backup_price_exceeds_limit", 409)
        if details.get("request_usd") not in (None, 0):
            raise AiError("language_backup_price_exceeds_limit", 409)
    return incoming, outgoing


async def generate(gateway, route, body, guard):
    guard()
    if route["provider"] == "gemini":
        # Deliberately one POST per route; no hidden retry cycle.
        return await gateway.request("gemini", "POST", "models/" + route["model"] + ":generateContent", body)
    system = "\n".join(p.get("text", "") for p in body.get("systemInstruction", {}).get("parts", []))
    schema = body["generationConfig"].get("responseSchema", {})
    system += "\nDevuelve sólo JSON válido con este contrato: " + json.dumps(schema, ensure_ascii=False)
    messages = [{"role": "system", "content": system}]
    for content in body["contents"]:
        if any("text" not in p for p in content["parts"]):
            raise AiError("language_backup_text_only", 409)
        messages.append({"role": "assistant" if content.get("role") == "model" else "user",
                         "content": "\n".join(p["text"] for p in content["parts"])})
    data = await gateway.request("openrouter", "POST", "chat/completions", {
        "model": route["model"], "messages": messages, "max_tokens": body["generationConfig"]["maxOutputTokens"],
        "temperature": body["generationConfig"].get("temperature", 0.3), "response_format": {"type": "json_object"},
        "provider": {"allow_fallbacks": False, "require_parameters": True, "data_collection": "deny"},
    })
    try:
        choice, usage = data["choices"][0], data.get("usage", {})
        text = choice["message"]["content"]
        if choice["finish_reason"] != "stop" or not isinstance(text, str) or not text.strip() or len(text) > 32000:
            raise ValueError()
        return {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": text}]}}],
                "usageMetadata": {"promptTokenCount": usage.get("prompt_tokens"), "candidatesTokenCount": usage.get("completion_tokens")}}
    except (KeyError, IndexError, TypeError, ValueError):
        raise AiError("language_backup_invalid_response", 502) from None


async def execute(primary, provider, model, body, saved, guard, reserve, trace, *, gateway=None):
    """One complete answer; tracing excludes prompt, secrets and customer data."""
    gateway = gateway or ProviderGateway(saved["keys"])
    attempts = trace.setdefault("attempts", [])
    started = monotonic()
    seen = {(provider, model)}
    try:
        guard()
        result = await primary()
        attempts.append({"provider": provider, "model": model, "state": "completed", "role": "primary"})
        trace.update(provider=provider, model=model, fallback_used=False)
        trace["latency_ms"] = round((monotonic() - started) * 1000)
        return result
    except AiError as error:
        attempts.append({"provider": provider, "model": model, "state": "failed", "code": error.code, "upstream_status": error.upstream_status, "role": "primary"})
        if not can_failover(error):
            raise
        original = error
    try:
        async with asyncio.timeout(35):
            for route in saved["routes"]:
                pair = (route["provider"], route["model"])
                if pair in seen:
                    continue
                seen.add(pair)
                attempt = {"provider": pair[0], "model": pair[1], "role": "fallback"}
                attempts.append(attempt)
                try:
                    guard()
                    incoming, outgoing = await compatible(gateway, route, body)
                    guard()
                    reserve(route, incoming, outgoing)
                    result = await generate(gateway, route, body, guard)
                    guard()
                    attempt["state"] = "completed"
                    trace.update(provider=pair[0], model=pair[1], fallback_used=True)
                    return result
                except AiError as error:
                    attempt.update(state="failed", code=error.code, upstream_status=error.upstream_status)
                    # Catalog/capability checks have not performed inference.
                    if not (error.code.startswith("language_backup_") and error.status == 409) and not can_failover(error):
                        raise
                    if can_failover(error):
                        original = error  # Report the final real rejection, not only the simulated primary fault.
            raise original
    except TimeoutError:
        raise AiError("language_backup_timeout", 504) from None
    finally:
        trace["latency_ms"] = round((monotonic() - started) * 1000)
