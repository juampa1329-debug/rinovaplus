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


@pytest.mark.parametrize("model", ["fixture/default", "anthropic/fixture"])
def test_private_comment_backup_enforces_the_dispatch_contract_without_changing_gemini_schema(model):
    import json
    from app.institutional import comment_private
    from app.institutional.language_resilience import generate

    ground = {"system": "Fuentes revisadas", "query": json.dumps({"catalogo": {"queried_programs": [{"program_id": 27}]}})}
    body = comment_private.request_body(ground, 1200, 0.3)
    calls = []

    class Gateway:
        async def request(self, provider, method, path, outgoing):
            calls.append(outgoing)
            return {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps({"decision": "responder", "intent": "information", "delivery": "private", "program_id": "27", "text": "Información vigente solicitada."})}}]}

    response = asyncio.run(generate(Gateway(), {**ROUTE,"model":model}, body, lambda: None))
    format = calls[0]["response_format"]
    assert format["type"] == "json_schema"
    schema = format["json_schema"]["schema"]
    assert format["json_schema"]["strict"] is True
    assert schema["additionalProperties"] is False
    if model.startswith("anthropic/"):
        assert "maxLength" not in schema["properties"]["text"]
        assert "900" in schema["properties"]["text"]["description"]
    else:
        assert schema["properties"]["text"]["maxLength"] == 900
    assert schema["properties"]["program_id"] == {"type": "string"}
    assert body["generationConfig"]["responseSchema"]["type"] == "OBJECT"
    assert "maxLength" not in body["generationConfig"]["responseSchema"]["properties"]["text"]
    assert comment_private.parse(response, ground)[1]["delivery"] == "private"
    assert len(calls) == 1


@pytest.mark.parametrize("model", ["anthropic/claude-sonnet-4.6", "anthropic/claude-sonnet-5.5", "fixture/default"])
def test_grounded_dm_contract_is_strict_for_primary_and_backups(model):
    import copy
    import json
    from app.institutional.language_resilience import generate

    original = copy.deepcopy(BODY)
    calls = []

    class Gateway:
        async def request(self, provider, method, path, outgoing):
            calls.append(outgoing)
            contract = outgoing["response_format"]
            assert contract["type"] == "json_schema" and contract["json_schema"]["strict"]
            schema = contract["json_schema"]["schema"]
            assert schema["additionalProperties"] is False
            assert set(schema["required"]) == {"decision", "text", "crm_observations"}
            assert schema["properties"]["decision"]["enum"] == ["responder", "revisar"]
            observations = schema["properties"]["crm_observations"]
            assert observations["items"]["additionalProperties"] is False
            assert set(observations["items"]["required"]) == {"field", "value", "quote"}
            if model.startswith("anthropic/"):
                assert "maxLength" not in schema["properties"]["text"]
                assert "maxItems" not in observations
                assert "3000" in schema["properties"]["text"]["description"]
                assert "8" in observations["description"]
            else:
                assert schema["properties"]["text"]["maxLength"] == 3000
                assert observations["maxItems"] == 8
            return {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps({
                "decision": "responder", "text": "La tarifa está por confirmar; no inventamos precios.",
                "crm_observations": []})}}]}

    result = asyncio.run(generate(Gateway(), {**ROUTE, "model": model}, BODY, lambda: None))
    assert grounded_replies.parse(result) == "La tarifa está por confirmar; no inventamos precios."
    assert len(calls) == 1 and BODY == original


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
        assert body["provider"]["max_price"] == {"prompt": 0, "completion": 0}
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
    assert not LanguageResilience().fallback_on_timeout
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


def test_first_backup_missing_from_catalog_continues_to_next_compatible_free_model():
    state = setup()
    state.saved["routes"].insert(0, {**ROUTE, "model": "missing:free"})
    response = run(state)
    assert grounded_replies.parse(response) == "Respuesta fundamentada"
    assert state.trace["attempts"][1]["code"] == "language_backup_model_unavailable"
    assert state.trace["attempts"][2]["state"] == "completed"
    assert len(state.reservations) == 1 and sum(method == "POST" for method, _ in state.calls) == 1


@pytest.mark.parametrize("code", ["provider_response_timeout", "provider_timeout_or_network", "provider_protocol_failure"])
def test_opted_in_text_timeout_uses_one_backup_and_keeps_primary_uncertainty(code):
    state = setup()
    state.saved["fallback_on_timeout"] = True
    primary_calls = []
    async def primary():
        primary_calls.append(1)
        raise AiError(code, 504)
    state.primary = primary
    assert grounded_replies.parse(run(state)) == "Respuesta fundamentada"
    assert primary_calls == [1] and len(state.reservations) == 1
    assert state.calls == [("GET", "/api/v1/models/user"), ("POST", "/api/v1/chat/completions")]
    assert state.trace["attempts"][0]["state"] == "uncertain"
    assert state.trace["attempts"][0]["reservation_retained"]
    assert state.trace["timeout_recovery"] and state.trace["fallback_used"]


@pytest.mark.parametrize("patch", [
    {"tools": [{"functionDeclarations": []}]}, {"stream": True},
    {"contents": [{"role": "user", "parts": [{"inlineData": {"data": "private-audio"}}]}]},
])
def test_timeout_recovery_does_not_forward_media_tools_or_streaming(patch):
    state = setup()
    state.saved["fallback_on_timeout"] = True
    async def primary():
        raise AiError("provider_response_timeout", 504)
    with pytest.raises(AiError, match="provider_response_timeout"):
        asyncio.run(execute(primary, "gemini", "fixture", {**BODY, **patch}, state.saved,
                            lambda: None, lambda *_: state.reservations.append(1), state.trace, gateway=state.gateway))
    assert not state.calls and not state.reservations


def test_opted_in_primary_timeout_does_not_start_another_inference_after_uncertain_backup():
    state = setup()
    state.saved["fallback_on_timeout"] = True
    state.saved["routes"].append({**ROUTE, "model": "third"})
    async def primary():
        raise AiError("provider_response_timeout", 504)
    original = state.gateway.request
    paid = []
    async def uncertain(provider, method, path, body=None):
        if method == "POST":
            paid.append(1)
            raise AiError("provider_response_timeout", 504)
        return await original(provider, method, path, body)
    state.primary = primary
    state.gateway.request = uncertain
    with pytest.raises(AiError, match="provider_response_timeout"):
        run(state)
    assert paid == [1] and len(state.reservations) == 1
    assert len(state.trace["attempts"]) == 2


def test_human_change_during_backup_discards_result_before_any_dispatch():
    state = setup()
    state.saved["fallback_on_timeout"] = True
    active = [True]
    original = state.gateway.request
    async def primary():
        raise AiError("provider_response_timeout", 504)
    async def request(provider, method, path, body=None):
        value = await original(provider, method, path, body)
        if method == "POST":
            active[0] = False
        return value
    def guard():
        if not active[0]:
            raise HTTPException(409, "human_control")
    state.primary, state.gateway.request = primary, request
    with pytest.raises(HTTPException, match="human_control"):
        run(state, guard=guard)
    assert sum(method == "POST" for method, _ in state.calls) == 1
    assert not state.trace.get("fallback_used")


def test_verified_commercial_button_keeps_response_only_schema_on_openrouter():
    import json
    from app.institutional.language_resilience import generate
    calls = []
    class Gateway:
        async def request(self, provider, method, path, outgoing):
            calls.append(outgoing)
            return {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps({"decision":"responder", "text":"Conversemos sobre tu formación.", "crm_observations":[]})}}]}
    body = grounded_replies.request_body({"system":"Botón comercial verificado", "query":"Consulta", "campaign_entry_turn":True})
    result = asyncio.run(generate(Gateway(), {**ROUTE,"model":"anthropic/fixture"}, body, lambda: None))
    assert grounded_replies.parse(result)
    schema = calls[0]["response_format"]["json_schema"]["schema"]
    assert schema["properties"]["decision"]["enum"] == ["responder"]
    assert len(calls) == 1
