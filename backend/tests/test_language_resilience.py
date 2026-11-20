import asyncio
from types import SimpleNamespace

import httpx2 as httpx
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.institutional import grounded_replies
from app.institutional.language_resilience import execute
from app.modules.ai.domain.resilience import LanguageResilience
from app.modules.ai.infrastructure.providers import AiError, ProviderGateway

ROUTE = {"provider": "openrouter", "model": "google/fixture:free", "input_usd_per_million": 0, "output_usd_per_million": 0}
BODY = grounded_replies.request_body({"system": "Guías y contexto revisados", "query": "Consulta"}, 700)


def setup(*, context=100000, pricing="0", finish="stop", catalog=True):
    calls, reservations, trace = [], [], {}
    def transport(req):
        calls.append((req.method, req.url.path))
        if req.method == "GET":
            return httpx.Response(200, json={"data": [{"id": ROUTE["model"], "context_length": context,
                "architecture": {"output_modalities": ["text"]}, "supported_parameters": ["temperature", "max_tokens", "response_format"],
                "pricing": {"prompt": pricing, "completion": pricing}, "top_provider": {"max_completion_tokens": 8000}}] if catalog else []})
        import json
        body = json.loads(req.content)
        assert body["provider"]["allow_fallbacks"] is False
        assert body["provider"]["data_collection"] == "deny"
        assert "Guías y contexto revisados" in body["messages"][0]["content"]
        return httpx.Response(200, json={"choices": [{"finish_reason": finish, "message": {"content": '{"decision":"responder","text":"Respuesta fundamentada"}'}}],
                                         "usage": {"prompt_tokens": 40, "completion_tokens": 15}})
    gateway = ProviderGateway({"openrouter": "test"}, httpx.MockTransport(transport))
    saved = {"keys": {"openrouter": "test"}, "routes": [ROUTE]}
    async def primary():
        raise AiError("provider_model_unavailable", 502, upstream_status=404)
    return SimpleNamespace(calls=calls, reservations=reservations, trace=trace, gateway=gateway, saved=saved, primary=primary)


def run(state, *, guard=lambda: None):
    return asyncio.run(execute(state.primary, "gemini", "gemini-fixture", BODY, state.saved, guard,
        lambda *args: state.reservations.append(args), state.trace, gateway=state.gateway))


def test_known_failure_uses_live_compatible_backup_with_one_reservation_and_preserves_contract():
    state = setup()
    result = run(state)
    assert grounded_replies.parse(result) == "Respuesta fundamentada"
    assert result["usageMetadata"]["candidatesTokenCount"] == 15
    assert state.calls == [("GET", "/api/v1/models/user"), ("POST", "/api/v1/chat/completions")]
    assert len(state.reservations) == 1
    assert state.trace["fallback_used"] and state.trace["model"] == ROUTE["model"]
    assert [v["state"] for v in state.trace["attempts"]] == ["failed", "completed"]
    assert "Consulta" not in str(state.trace) and "test" not in str(state.trace)


@pytest.mark.parametrize("kwargs,code", [({"context": 100}, "language_backup_context_incompatible"),
    ({"pricing": "0.000001"}, "language_backup_price_exceeds_limit"), ({"catalog": False}, "language_backup_model_unavailable")])
def test_unapproved_price_small_context_or_missing_model_never_infer(kwargs, code):
    state = setup(**kwargs)
    with pytest.raises(AiError, match="provider_model_unavailable"):
        run(state)
    assert state.trace["attempts"][-1]["code"] == code
    assert all(method == "GET" for method, _ in state.calls) and not state.reservations


@pytest.mark.parametrize("code,status", [("provider_response_timeout", None), ("provider_invalid_json", None),
    ("provider_rejected_request", 401), ("provider_temporary_failure", 502)])
def test_ambiguous_inference_or_auth_failure_is_not_replayed(code, status):
    state = setup()
    async def primary():
        raise AiError(code, 502, True, status)
    state.primary = primary
    with pytest.raises(AiError, match=code):
        run(state)
    assert not state.calls and not state.reservations


def test_human_or_epoch_change_after_catalog_stops_before_reservation_and_post():
    state, checks = setup(), []
    def guard():
        checks.append(1)
        if len(checks) == 3:
            raise HTTPException(409, "human_control")
    with pytest.raises(HTTPException):
        run(state, guard=guard)
    assert state.calls == [("GET", "/api/v1/models/user")] and not state.reservations


def test_budget_failure_blocks_backup_and_truncated_response_is_not_retried():
    state = setup()
    def reserve(*_):
        raise HTTPException(429, "budget_exhausted")
    with pytest.raises(HTTPException):
        asyncio.run(execute(state.primary, "gemini", "gemini-fixture", BODY, state.saved, lambda: None,
                            reserve, state.trace, gateway=state.gateway))
    assert all(method == "GET" for method, _ in state.calls)
    state = setup(finish="length")
    state.saved["routes"].append({**ROUTE, "model": "second"})
    with pytest.raises(AiError, match="language_backup_invalid_response"):
        run(state)
    assert sum(method == "POST" for method, _ in state.calls) == 1


def test_disabled_policy_and_duplicate_or_batch_models():
    assert not LanguageResilience().enabled
    for value in ({"enabled": True}, {"routes": [ROUTE, ROUTE]}, {"routes": [{**ROUTE, "model": "some:batch"}]}):
        with pytest.raises(ValidationError):
            LanguageResilience.model_validate(value)


def test_audio_is_rejected_by_the_text_backup_before_any_request():
    from app.institutional.language_resilience import generate
    state = setup()
    body = {**BODY, "contents": [{"role": "user", "parts": [{"inlineData": {"data": "not-forwarded"}}]}]}
    with pytest.raises(AiError, match="language_backup_text_only"):
        asyncio.run(generate(state.gateway, ROUTE, body, lambda: None))
    assert not state.calls
