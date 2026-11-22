import asyncio
from copy import deepcopy
from types import SimpleNamespace
from uuid import uuid4

import httpx2 as httpx
import pytest
from pydantic import ValidationError

from app.modules.agents.domain import SimulationRequest
from app.modules.agents.simulation_route import apply, prepare
from app.modules.ai.infrastructure.providers import AiError, ProviderGateway


def request(**changes):
    return SimulationRequest(agent_id=uuid4(), config_version=1, question="Hola", request_id=uuid4(),
                             provider_override="openrouter", model_override="google/gemma-fixture:free", **changes)


def runtime(*, pricing=None, parameters=None, rotate=False, reasoning=None, output_limit=500):
    calls = []
    def transport(req):
        calls.append(req)
        assert req.method == "GET" and req.url.path == "/api/v1/models/user"
        return httpx.Response(200, json={"data": [{
            "id": "google/gemma-fixture:free", "pricing": pricing if pricing is not None else {"prompt": "0", "completion": "0"},
            "architecture": {"output_modalities": ["text"]},
            "supported_parameters": parameters if parameters is not None else ["max_tokens", "temperature", "response_format"],
            "top_provider": {"max_completion_tokens": output_limit},
            **({"reasoning": reasoning} if reasoning else {}),
        }]})
    gateway = ProviderGateway({"openrouter": "fixture-key"}, httpx.MockTransport(transport))
    snapshots = []
    def snapshot():
        snapshots.append(1)
        return {"credential_revision": len(snapshots) if rotate else 2}
    return SimpleNamespace(gateway=gateway, refresh_credentials=lambda: None, connection_snapshot=snapshot), calls


def test_trial_uses_live_account_catalog_and_zero_price_without_mutating_profile():
    ai, calls = runtime()
    route = asyncio.run(prepare(ai, request()))
    saved = {"binding": "saved", "configuration": {"provider": "gemini", "primary_model": "current",
             "fallback_model": "backup", "max_tokens": 700, "capabilities": ["program.read"], "channels": ["local"],
             "monthly_token_limit": 250000, "allow_reply": False}}
    original = deepcopy(saved)
    selected = apply(saved, route)
    assert saved == original and len(calls) == 1
    assert selected["configuration"]["primary_model"] == "google/gemma-fixture:free"
    assert selected["configuration"]["input_usd_per_million"] == selected["configuration"]["output_usd_per_million"] == 0
    assert selected["configuration"]["max_tokens"] == 500
    assert selected["configuration"]["monthly_token_limit"] == 250000
    assert selected["configuration"]["capabilities"] == ["program.read"]
    assert selected["configuration"]["allow_reply"] is False
    assert selected["configuration"]["fallback_model"] == "" and selected["binding"] != saved["binding"]


@pytest.mark.parametrize("kwargs,error", [
    ({"pricing": {}}, "agents_pricing_required"),
    ({"pricing": {"prompt": "NaN", "completion": "-1"}}, "agents_pricing_required"),
    ({"parameters": ["max_tokens", "temperature"]}, "agents_model_structured_output_required"),
    ({"rotate": True}, "agents_configuration_changed"),
])
def test_trial_stops_before_generation_on_missing_capabilities_or_rotation(kwargs, error):
    ai, calls = runtime(**kwargs)
    with pytest.raises(AiError, match=error):
        asyncio.run(prepare(ai, request()))
    assert len(calls) == 1 and all(call.method == "GET" for call in calls)


def test_trial_requires_a_model_and_provider_pair_and_keeps_default_preview_offline():
    with pytest.raises(ValidationError):
        SimulationRequest(agent_id=uuid4(), config_version=1, question="Hola", request_id=uuid4(), provider_override="openrouter")
    no_override = SimulationRequest(agent_id=uuid4(), config_version=1, question="Hola", request_id=uuid4())
    assert asyncio.run(prepare(None, no_override)) is None
    value = {"configuration": {}, "binding": "unchanged"}
    assert apply(value, None) is value


def test_trial_can_omit_unsupported_temperature_without_changing_the_saved_profile():
    ai, calls = runtime(parameters=["max_tokens", "response_format", "reasoning"],
                        reasoning={"supported_efforts": ["high", "medium", "low"]}, output_limit=4096)
    route = asyncio.run(prepare(ai, request(output_tokens_override=2000)))
    saved = {"binding": "original", "configuration": {"max_tokens": 700, "allow_reply": False}}
    selected = apply(saved, route)
    assert saved == {"binding": "original", "configuration": {"max_tokens": 700, "allow_reply": False}}
    assert selected["configuration"]["max_tokens"] == 2000
    assert selected["trial_temperature_supported"] is False
    assert selected["trial_reasoning_effort"] == "low"
    assert len(calls) == 1 and calls[0].method == "GET"


def test_trial_output_override_is_bounded_and_requires_an_isolated_route():
    ai, calls = runtime()
    with pytest.raises(AiError, match="agents_model_output_limit"):
        asyncio.run(prepare(ai, request(output_tokens_override=2000)))
    assert len(calls) == 1
    with pytest.raises(ValidationError):
        request(output_tokens_override=2001)
    with pytest.raises(ValidationError):
        SimulationRequest(agent_id=uuid4(), config_version=1, question="Hola", request_id=uuid4(), output_tokens_override=2000)
