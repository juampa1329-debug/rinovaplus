"""Reuse configured model catalogs and the provider gateway without discovery."""

from typing import get_args
from time import monotonic

from app.modules.ai.domain.models import ModelInfo, Provider
from app.modules.ai.infrastructure.openrouter import OpenRouterClient
from app.modules.ai.infrastructure.providers import AiError
from app.modules.ai.application.admissions_prompt import ADMISSIONS_RESPONSE_SCHEMA


def provider_options(ai):
    """Read metadata only; never call load_models or a provider endpoint."""
    connection = ai.connection_snapshot()
    settings = ai.repository.read().settings
    configured = {item["id"]: item["configured"] for item in connection["providers"]}
    result = []
    for provider in get_args(Provider):
        models = {
            key: {**model.model_dump(mode="json"), "origin": "cached_catalog"}
            for key, model in ai.catalogs.get(provider, {}).items()
        }
        saved = [settings.provider_models.get(provider, "")]
        if settings.provider == provider:
            saved.extend((settings.model, settings.fallback_model))
        for model_id in saved:
            if model_id and model_id not in models:
                models[model_id] = {
                    **ModelInfo(id=model_id, name=model_id).model_dump(),
                    "origin": "saved_configuration",
                }
        if provider == "gemini" and isinstance(
            getattr(ai, "demo_template_model", None), str
        ):
            model_id = ai.demo_template_model
            models[model_id] = {
                **ModelInfo(id=model_id, name="Ejemplo sin proveedor").model_dump(),
                "origin": "local_template_no_provider",
            }
        endpoint_ready = provider != "hermes" or bool(ai.gateway.hermes_base)
        result.append(
            {
                "id": provider,
                "configured": bool(configured.get(provider)),
                "endpoint_ready": endpoint_ready,
                "models": sorted(models.values(), key=lambda value: value["id"]),
                "catalog_loaded": bool(ai.catalogs.get(provider)),
            }
        )
    return {
        "providers": result,
        "current_provider": settings.provider,
        "credential_revision": connection["credential_revision"],
        "network_called": False,
        "defaults": {
            "provider": settings.provider,
            "primary_model": settings.model
            or settings.provider_models.get(settings.provider, ""),
            "fallback_model": settings.fallback_model
            if settings.provider == "openrouter"
            else "",
            "monthly_token_limit": 250000,
            "max_tokens": min(2000, max(128, settings.max_tokens)),
        },
    }


def validate_selection(configuration, options, previous=None):
    previous = previous or {}
    for field, provider in (
        ("primary_model", configuration["provider"]),
        (
            "fallback_model",
            configuration.get("fallback_provider") or configuration["provider"],
        ),
    ):
        selected = next(p for p in options["providers"] if p["id"] == provider)
        known = {model["id"] for model in selected["models"]}
        old_provider = (
            (
                previous.get("fallback_provider")
                or previous.get("provider", "openrouter")
            )
            if field == "fallback_model"
            else previous.get("provider", "openrouter")
        )
        model = configuration[field]
        if (
            model
            and model not in known
            and not (old_provider == provider and previous.get(field) == model)
        ):
            raise AiError("agents_provider_model_catalog_required", 409)


def require_provider(ai, configuration, provider=None):
    ai.refresh_credentials()
    provider = provider or configuration.get("provider", "openrouter")
    if not ai.repository.read().settings.enabled or not ai.outbound:
        raise AiError("agents_global_ai_gate_closed", 409)
    if not ai.gateway.keys.get(provider):
        raise AiError("agents_provider_not_configured", 409)
    if provider == "hermes" and not ai.gateway.hermes_base:
        raise AiError("provider_endpoint_missing", 409)
    return provider


async def complete(ai, selection, policy, messages, guard, *, preview=False):
    """Use explicit primary/fallback routes; uncertain POSTs are never repeated."""
    configuration = selection["configuration"]
    if ai.busy:
        raise AiError("operation_busy", 429)
    ai.busy = True
    started = monotonic()
    attempts = []
    candidates = [(configuration["provider"], policy.primary_model)]
    if policy.fallback_model:
        candidates.append(
            (
                configuration.get("fallback_provider") or configuration["provider"],
                policy.fallback_model,
            )
        )
    try:
        for index, (provider, model) in enumerate(candidates):
            attempt_start = monotonic()
            guard()
            try:
                require_provider(ai, configuration, provider)
                settings = ai.repository.read().settings.model_copy(
                    update={
                        "provider": provider,
                        "model": model,
                        "max_tokens": policy.max_tokens,
                        "output_tokens": policy.max_tokens,
                        "temperature": policy.temperature,
                        "fallback_enabled": False,
                        "backup_provider": None,
                    }
                )
                if provider == "openrouter":
                    result = await OpenRouterClient(
                        ai.gateway.keys[provider], ai.gateway.transport
                    ).complete(
                        policy.model_copy(
                            update={"primary_model": model, "fallback_model": ""}
                        ),
                        messages,
                        guard,
                    )
                else:
                    system = "\n".join(
                        m["content"] for m in messages if m["role"] == "system"
                    )
                    schema = ADMISSIONS_RESPONSE_SCHEMA
                    if preview:
                        schema = {
                            **schema,
                            "properties": {
                                **schema["properties"],
                                "memory": {
                                    **schema["properties"]["memory"],
                                    "maxItems": 0,
                                },
                            },
                        }
                    text = await ai.gateway.generate(
                        provider,
                        model,
                        settings,
                        system,
                        [m for m in messages if m["role"] != "system"],
                        before_attempt=guard,
                        response_schema=schema if provider == "gemini" else None,
                    )
                    usage = ai.gateway.last_usage
                    result = {
                        "content": text,
                        "model": model,
                        "usage": {
                            "prompt_tokens": usage["input"],
                            "completion_tokens": usage["output"],
                        }
                        if usage
                        else {},
                        "response_metadata": ai.gateway.last_response_metadata,
                    }
                guard()
                attempts.append(
                    {
                        "provider": provider,
                        "model": model,
                        "role": "fallback" if index else "primary",
                        "state": "completed",
                        "latency_ms": round((monotonic() - attempt_start) * 1000),
                        **result.get("response_metadata", {}),
                    }
                )
                return {
                    **result,
                    "provider": provider,
                    "fallback_used": bool(index),
                    "latency_ms": round((monotonic() - started) * 1000),
                    "attempts": attempts,
                }
            except AiError as error:
                attempts.append(
                    {
                        "provider": provider,
                        "model": model,
                        "role": "fallback" if index else "primary",
                        "state": "failed",
                        "code": error.code,
                        "latency_ms": round((monotonic() - attempt_start) * 1000),
                    }
                )
                error.agent_execution = {
                    "latency_ms": round((monotonic() - started) * 1000),
                    "attempts": attempts,
                    "provider": provider,
                    "model": model,
                    "fallback_used": bool(index),
                }
                # Only a known rejection before inference may use another model.
                # A timeout/5xx can already have consumed the previous route.
                recoverable = (
                    error.code
                    in {
                        "provider_model_unavailable",
                        "provider_rate_limited",
                        "provider_connection_failed",
                        "agents_provider_not_configured",
                    }
                    or error.code == "openrouter_rejected_request"
                    and error.upstream_status == 404
                )
                if index + 1 == len(candidates) or not recoverable:
                    raise
        raise AiError("all_models_unavailable", 502)
    finally:
        ai.busy = False
