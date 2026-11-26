import asyncio
import json

import httpx2 as httpx
import pytest
from fastapi import HTTPException

from app.institutional import comment_ai, comment_automation, comment_private, grounded_replies, language_resilience, voice_transcripts
from app.modules.ai.domain.models import MediaSettings
from app.modules.ai.infrastructure.providers import AiError, ProviderGateway


ROUTE = {"provider": "openrouter", "model": "fixture/current", "input_usd_per_million": 3.0, "output_usd_per_million": 15.0}
DOCUMENT = {"language_resilience": {"enabled": True, "primary": ROUTE, "routes": [{**ROUTE, "model": "fixture/backup"}]},
            "provider": "gemini", "model": "old-lite"}


@pytest.mark.parametrize("old_provider", ["gemini", "openai"])
def test_social_pricing_uses_current_engine_and_keeps_approved_account_ceiling(monkeypatch, old_provider):
    queries = []
    old = {"provider": old_provider, "model": "retired", "daily_requests": 17, "input_micros_per_million": 1}
    def one(_c, query, *_):
        queries.append(query)
        return {"Summary": json.dumps(old)}
    monkeypatch.setattr(comment_ai, "one", one)
    monkeypatch.setattr(comment_ai, "institution", lambda _: "inst")
    value = comment_ai.policy(None, None, "account", DOCUMENT, engine=True)
    assert value["provider"] == "openrouter" and value["model"] == ROUTE["model"]
    assert value["daily_requests"] == 17 and value["input_micros_per_million"] == 3_000_000
    assert "ExpiresAt>" not in queries[0]
    with pytest.raises(HTTPException, match="comment_ai_pricing_review_required"):
        comment_ai.policy(None, None, "account", DOCUMENT)
    assert "ExpiresAt>" in queries[-1]  # legacy explicit model still requires its own review


@pytest.mark.parametrize("summary", [None, {}, {"daily_requests": 0}, {"daily_requests": True}, {"daily_requests": 10001}])
def test_selecting_an_engine_never_grants_an_account_traffic_limit(monkeypatch, summary):
    monkeypatch.setattr(comment_ai, "one", lambda *_: {"Summary": json.dumps(summary)} if summary is not None else None)
    monkeypatch.setattr(comment_ai, "institution", lambda _: "inst")
    with pytest.raises(HTTPException, match="comment_ai_account_limit_required"):
        comment_ai.policy(None, None, "account", DOCUMENT, engine=True)


def test_missing_primary_key_keeps_approved_fallback_without_consulting_gemini(monkeypatch):
    queried = []
    monkeypatch.setattr(language_resilience, "setting", lambda *_: {"revision": 8, "document": DOCUMENT})
    monkeypatch.setattr(language_resilience, "institution", lambda _: "inst")
    monkeypatch.setattr(language_resilience, "one", lambda _c, _q, _inst, provider: queried.append(provider))
    saved = language_resilience.snapshot(None, None)
    assert saved["primary"] == ROUTE and saved["routes"][0]["model"] == "fixture/backup"
    assert queried == ["openrouter", "openrouter"] and saved["keys"] == {}


@pytest.mark.parametrize("failure", ["provider_key_missing", "credential_rejection"])
def test_known_primary_preflight_or_auth_rejection_can_use_another_approved_provider(failure):
    posts, trace = [], {}
    def transport(request):
        if request.method == "GET":
            return httpx.Response(200, json={"data": [{"id": ROUTE["model"], "context_length": 100000,
                "architecture": {"output_modalities": ["text"]}, "supported_parameters": ["max_tokens", "response_format"],
                "pricing": {"prompt": "0.000003", "completion": "0.000015"}, "top_provider": {"max_completion_tokens": 8000}}]})
        posts.append(str(request.url))
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": '{"decision":"responder","text":"Gracias por acompañarnos 💚","crm_observations":[]}'}}]})
    async def primary():
        raise AiError("provider_key_missing", 409) if failure == "provider_key_missing" else AiError("provider_rejected_request", 502, upstream_status=401)
    body = grounded_replies.request_body({"system": "Skills y contexto intactos", "query": "Felicitaciones"}, 2000)
    result = asyncio.run(language_resilience.execute(primary, "openai", "fixture/disabled", body,
        {"routes": [ROUTE], "keys": {"openrouter": "fixture"}}, lambda: None, lambda *_: None, trace,
        gateway=ProviderGateway({"openrouter": "fixture"}, httpx.MockTransport(transport))))
    assert grounded_replies.parse(result, public=True).startswith("Gracias")
    assert len(posts) == 1 and trace["fallback_used"] and trace["provider"] == "openrouter"


@pytest.mark.parametrize("provider", ["openai", "anthropic", "groq", "kimi", "nvidia", "mistral", "xai", "hermes"])
def test_canonical_text_adapters_do_not_require_gemini(provider):
    calls = []
    def transport(request):
        calls.append((str(request.url), json.loads(request.content)))
        text = '{"decision":"responder","text":"Respuesta con el contexto y las skills.","crm_observations":[]}'
        if provider == "anthropic":
            return httpx.Response(200, json={"stop_reason": "end_turn", "content": [{"type": "text", "text": text}]})
        if provider == "xai":
            return httpx.Response(200, json={"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}]})
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": text}}]})
    gateway = ProviderGateway({provider: "fixture"}, httpx.MockTransport(transport))
    gateway.hermes_base = "https://hermes.example.invalid/v1/"
    result = asyncio.run(language_resilience.generate(gateway, {**ROUTE, "provider": provider},
        grounded_replies.request_body({"system": "Skills revisadas", "query": "Consulta"}, 4000), lambda: None))
    assert grounded_replies.parse(result).startswith("Respuesta") and len(calls) == 1
    assert "googleapis" not in calls[0][0] and "Skills revisadas" in json.dumps(calls[0][1], ensure_ascii=False)


def test_selected_audio_uses_audio_catalog_and_never_text_only_fallback(monkeypatch):
    monkeypatch.setattr(language_resilience, "setting", lambda *_: {"revision": 8, "document": {
        "language_resilience": {"enabled": True, "primary": ROUTE,
            "routes": [{**ROUTE, "provider": "gemini", "model": "not-authorized-for-raw-audio"}, {**ROUTE, "model": "fixture/audio"}]}}})
    monkeypatch.setattr(language_resilience, "institution", lambda _: "inst")
    monkeypatch.setattr(language_resilience, "one", lambda *_: None)
    saved = language_resilience.snapshot(None, None, media_route={**ROUTE, "model": "fixture/asr"})
    assert all(r["provider"] == "openrouter" for r in [saved["primary"], *saved["routes"]])
    calls = []
    def transport(request):
        if request.method == "GET":
            return httpx.Response(200, json={"data": [{"id": "fixture/asr", "context_length": 100000,
                "architecture": {"input_modalities": ["audio", "text"], "output_modalities": ["text"]},
                "supported_parameters": ["max_tokens", "response_format"], "pricing": {"prompt": "0.000003", "completion": "0.000015"},
                "top_provider": {"max_completion_tokens": 8000}}]})
        body = json.loads(request.content)
        calls.append(body)
        assert body["messages"][1]["content"][-1]["type"] == "input_audio"
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": '{"intelligible":true,"text":"Quiero estudiar Software"}'}}]})
    body = voice_transcripts.request_body({"mime": "audio/ogg", "raw": b"synthetic fixture"})
    gateway = ProviderGateway({"openrouter": "fixture"}, httpx.MockTransport(transport))
    result = asyncio.run(language_resilience.execute(lambda: pytest.fail("No legacy ASR"), "openrouter", "fixture/asr", body,
        {**saved, "keys": {"openrouter": "fixture"}}, lambda: None, lambda *_: None, {}, gateway=gateway))
    assert voice_transcripts.parse(result) == "Quiero estudiar Software" and len(calls) == 1
    assert MediaSettings(audio_provider="openrouter", audio_model="google/fixture").audio_provider == "openrouter"
    with pytest.raises(AiError, match="audio_not_authorized"):
        language_resilience.message_content(body["contents"][0])


@pytest.mark.parametrize("text,expected", [("Felicidades Vale 🎉", True), ("❤️✨", True), ("Excelente, pero cuánto cuesta", False), ("Felicitaciones, ¿cómo me inscribo?", False)])
def test_support_comments_skip_optional_vision_without_turning_questions_into_thanks(text, expected):
    assert comment_private.support(text) is expected
    context = comment_private.context({"system": "fuentes", "query": json.dumps({"catalogo": {"queried_programs": []}}), "fingerprint": "old", "skill_policy": {}})
    assert "No exige identificar un programa" in context["system"]


@pytest.mark.parametrize("human", [False, True])
def test_only_zero_attempt_price_veto_can_be_reconsidered_and_current_controls_win(monkeypatch, human):
    from pglast import parse_sql
    from app.institutional.operations_policy import layout
    from app.institutional.postgres_dialect import postgres_sql
    statements = []
    class Cursor:
        rowcount = 1
        def execute(self, query, *args):
            statements.append((query, args))
            return self
    monkeypatch.setattr(comment_automation, "setting", lambda *_: {"revision": 8, "document": DOCUMENT})
    monkeypatch.setattr(comment_automation, "institution", lambda _: "inst")
    def one(_c, query, *_):
        parse_sql(postgres_sql(query, layout()["tables"]).replace("%s", "NULL"))
        assert "COALESCE(p.Attempts,0)=0" in query and "NOT EXISTS" in query and "SendJob" in query
        assert "DATEADD(hour,-24" in query and "p.Status='abandoned'" in query
        assert "JSON_VALUE" in query
        return {"OperationId": "comment", "IntegrationId": "account", "ResultMetadata": '{"comment":"comment","version":"00"}'}
    monkeypatch.setattr(comment_automation, "one", one)
    def current(*_):
        if human:
            raise HTTPException(409, "comment_auto_source_changed")
    monkeypatch.setattr(comment_automation, "current", current)
    monkeypatch.setattr(comment_automation, "policy", lambda *_, **__: {})
    result = comment_automation.recover_price_preflight(Cursor(), None)
    assert (result is None) is human
    assert len(statements) == 1
    if human:
        assert "Status='pending'" not in statements[0][0] and "not_eligible" in statements[0][1][0]
    else:
        assert "Status='pending'" in statements[0][0] and "reconsidered" in statements[0][1][0]
