import asyncio
import json
from types import SimpleNamespace

import httpx2 as httpx
import pytest

from app.modules.ai.infrastructure.openrouter import OpenRouterClient
from app.modules.ai.infrastructure.providers import AiError


@pytest.mark.parametrize("status", [401, 402, 408, 500, 502, 504])
def test_ambiguous_or_auth_http_status_never_repeats_post(status):
    calls = []
    def respond(req):
        calls.append(req)
        return httpx.Response(status, json={"error": {"code": status}})
    with pytest.raises(AiError) as failure:
        asyncio.run(OpenRouterClient("fixture", httpx.MockTransport(respond)).complete(
            SimpleNamespace(primary_model="fixture:free", fallback_model="", temperature=0.3, max_tokens=100),
            [{"role": "user", "content": "Hola"}], lambda: None))
    assert len(calls) == 1
    assert failure.value.upstream_status == status
    if status == 402:
        assert failure.value.code == "openrouter_payment_required"


def test_explicit_busy_response_can_select_another_configured_route_without_waiting_past_retry_after():
    from app.modules.ai.domain.resilience import can_failover
    calls = []
    def respond(req):
        calls.append(req)
        return httpx.Response(503, headers={"retry-after": "120"}, json={"error": {"code": 503}})
    with pytest.raises(AiError) as failure:
        asyncio.run(OpenRouterClient("fixture", httpx.MockTransport(respond)).complete(
            SimpleNamespace(primary_model="fixture:free", fallback_model="", temperature=0.3, max_tokens=100),
            [{"role": "user", "content": "Hola"}], lambda: None))
    assert len(calls) == 1 and can_failover(failure.value)


@pytest.mark.parametrize("status", [200, 429, 503])
def test_trial_preserves_privacy_and_price_ceiling_with_one_post(status):
    calls = []
    def respond(req):
        calls.append(json.loads(req.content))
        return httpx.Response(status, json={"model": "fixture", "choices": [{"finish_reason": "stop", "message": {"content": "{}"}}], "usage": {"prompt_tokens": 10, "completion_tokens": 2}})
    work = OpenRouterClient("fixture", httpx.MockTransport(respond)).complete(
        SimpleNamespace(primary_model="fixture", fallback_model="", temperature=0.3, max_tokens=100),
        [{"role": "user", "content": "Hola"}], lambda: None,
        price_limits={"prompt": 0.4, "completion": 1.6}, max_attempts=1)
    if status == 200:
        assert asyncio.run(work)["usage"]["prompt_tokens"] == 10
    else:
        with pytest.raises(AiError, match="openrouter_retry_exhausted"):
            asyncio.run(work)
    assert len(calls) == 1
    assert calls[0]["provider"] == {"require_parameters": True, "data_collection": "deny", "max_price": {"prompt": 0.4, "completion": 1.6}}


@pytest.mark.parametrize("limits", [{"prompt": -1, "completion": 1}, {"prompt": float("inf"), "completion": 1}, {"prompt": True, "completion": 1}, {"prompt": 1}])
def test_invalid_price_limits_never_contact_provider(limits):
    with pytest.raises(AiError, match="agents_pricing_required"):
        asyncio.run(OpenRouterClient("fixture").complete(
            SimpleNamespace(primary_model="fixture", fallback_model="", temperature=0.3, max_tokens=100),
            [], lambda: None, price_limits=limits))


def test_trial_output_schema_has_no_memory_or_tool_access():
    from app.modules.agents.generation import SIMULATION_SCHEMA
    calls = []
    def respond(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json={"model": "fixture", "choices": [{"finish_reason": "stop", "message": {"content": '{"answer":"Hola","handoff":true,"references":[]}'}}], "usage": {"prompt_tokens": 10, "completion_tokens": 2}})
    asyncio.run(OpenRouterClient("fixture", httpx.MockTransport(respond)).complete(
        SimpleNamespace(primary_model="fixture", fallback_model="", temperature=0.3, max_tokens=100),
        [], lambda: None, response_schema=SIMULATION_SCHEMA, max_attempts=1))
    fmt = calls[0]["response_format"]
    assert fmt["type"] == "json_schema" and fmt["json_schema"]["strict"]
    assert set(fmt["json_schema"]["schema"]["properties"]) == {"answer", "handoff", "references"}
    assert "tools" not in calls[0]


def test_adaptive_model_trial_omits_temperature_but_preserves_json_privacy_price_and_single_post():
    from app.modules.agents.generation import SIMULATION_SCHEMA
    calls = []
    def respond(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json={"model": "fixture", "choices": [{"finish_reason": "stop", "message": {"content": '{"answer":"Hola","handoff":false,"references":[]}'}}], "usage": {"prompt_tokens": 10, "completion_tokens": 20}})
    asyncio.run(OpenRouterClient("fixture", httpx.MockTransport(respond)).complete(
        SimpleNamespace(primary_model="fixture", fallback_model="", temperature=0.3, max_tokens=2000),
        [], lambda: None, response_schema=SIMULATION_SCHEMA, max_attempts=1,
        price_limits={"prompt": 4, "completion": 20}, include_temperature=False, reasoning_effort="low"))
    assert len(calls) == 1
    body = calls[0]
    assert "temperature" not in body and body["reasoning"] == {"effort": "low", "exclude": True}
    assert body["max_tokens"] == 2000 and body["models"] == ["fixture"]
    assert body["provider"] == {"require_parameters": True, "data_collection": "deny", "max_price": {"prompt": 4, "completion": 20}}
    assert body["response_format"]["json_schema"]["strict"]


@pytest.mark.parametrize("finish,code", [("length", "admissions_response_truncated"), ("content_filter", "provider_invalid_response")])
def test_unusable_paid_completion_retains_usage_without_replaying_or_leaking_text(finish, code):
    calls = []
    def respond(request):
        calls.append(request)
        return httpx.Response(200, json={"model": "fixture", "choices": [{"finish_reason": finish, "message": {"content": "private-output", "reasoning": "private-reasoning"}}], "usage": {"prompt_tokens": 100, "completion_tokens": 700, "untrusted_extra": "private"}})
    with pytest.raises(AiError) as failure:
        asyncio.run(OpenRouterClient("fixture", httpx.MockTransport(respond)).complete(
            SimpleNamespace(primary_model="fixture", fallback_model="", temperature=0.3, max_tokens=700),
            [], lambda: None, max_attempts=1))
    assert len(calls) == 1 and failure.value.code == code
    assert failure.value.agent_usage == {"prompt_tokens": 100, "completion_tokens": 700}
    assert failure.value.response_metadata == {"finish_reason": finish}
    assert "private" not in repr(vars(failure.value))
