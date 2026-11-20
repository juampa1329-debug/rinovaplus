"""An explicit model trial never edits the published agent or grants permissions."""

from app.modules.agents.domain import digest
from app.modules.ai.infrastructure.providers import AiError


async def prepare(ai, request):
    if not request.provider_override:
        return None
    ai.refresh_credentials()
    provider = request.provider_override
    before = ai.connection_snapshot()["credential_revision"]
    if not ai.gateway.keys.get(provider):
        raise AiError("agents_provider_not_configured", 409)
    models = await ai.gateway.models(provider, account_catalog=True)
    model = next((m for m in models if m.id == request.model_override), None)
    details = ai.gateway.catalog_details.get(provider, {}).get(request.model_override, {})
    if not model:
        raise AiError("agents_provider_model_catalog_required", 409)
    if any(details.get(field) is None for field in ("input_usd_per_million", "output_usd_per_million")):
        raise AiError("agents_pricing_required", 409)
    if "response_format" not in details.get("supported_parameters", []):
        raise AiError("agents_model_structured_output_required", 409)
    if not model.temperature:
        raise AiError("agents_model_temperature_unsupported", 409)
    if ai.connection_snapshot()["credential_revision"] != before:
        raise AiError("agents_configuration_changed", 409)
    return {"provider": provider, "primary_model": model.id, "fallback_provider": None, "fallback_model": "",
            "input_usd_per_million": details["input_usd_per_million"],
            "output_usd_per_million": details["output_usd_per_million"],
            "output_limit": model.output_limit, "credential_revision": before, "context_limit": details.get("context_length")}


def apply(selection, route):
    if not route:
        return selection
    changes = {k: v for k, v in route.items() if k not in {"output_limit", "credential_revision", "context_limit"}}
    config = {**selection["configuration"], **changes}
    if route["output_limit"]:
        config["max_tokens"] = min(config["max_tokens"], route["output_limit"])
    return {**selection, "configuration": config, "binding": digest([selection["binding"], route])}


def check_context(route, messages, output_tokens):
    if not route:
        return
    limit = route.get("context_limit")
    # UTF-8 bytes bound the input conservatively; do not guess tokenization.
    required = sum(len(m["content"].encode("utf-8")) for m in messages) + output_tokens + 256
    if type(limit) is not int or limit <= 0 or required > limit:
        raise AiError("agents_model_context_limit", 409)
