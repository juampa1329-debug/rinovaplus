import asyncio
import json
from types import SimpleNamespace

import httpx2 as httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.institutional import provider_balances as balances
from app.institutional.api import core_permission
from app.institutional.models import SecretEdit
from app.modules.ai.infrastructure.providers import AiError


def test_model_key_reports_its_budget_not_account_balance_and_filters_identity():
    calls = []
    def reply(request):
        calls.append(request)
        return httpx.Response(200, json={"data": {"usage": 1.23, "usage_daily": 0, "limit": None,
                              "limit_remaining": None, "label": "private-key-label", "creator_user_id": "private-user"}})
    result = asyncio.run(balances.collect("openrouter", "model-key", transport=httpx.MockTransport(reply)))
    assert len(calls) == 1 and calls[0].method == "GET" and calls[0].url.path == "/api/v1/key"
    assert result["account"] is None and result["account_status"] == "management_key_required"
    assert result["key"]["usage_daily"] == 0 and result["key"]["limit"] is None
    assert "private" not in json.dumps(result) and "model-key" not in json.dumps(result)


def test_management_key_is_only_used_for_credits_and_never_substitutes_model_key():
    calls = []
    def reply(request):
        calls.append((request.url.path, request.headers["authorization"], request.method))
        return httpx.Response(200, json={"data": {"usage": 1, "limit": 0, "limit_remaining": 0}
                             if request.url.path.endswith("/key") else {"total_credits": 5, "total_usage": 6}})
    result = asyncio.run(balances.collect("openrouter", "model-key", "account-key", transport=httpx.MockTransport(reply)))
    assert calls == [("/api/v1/key", "Bearer model-key", "GET"), ("/api/v1/credits", "Bearer account-key", "GET")]
    assert result["key"]["limit_remaining"] == 0 and result["account"]["remaining"] == -1


def test_rejected_management_key_keeps_successful_key_usage_without_a_retry():
    calls = []
    def reply(request):
        calls.append(request.url.path)
        return httpx.Response(403, json={"error": "secret rejected detail"}) if request.url.path.endswith("credits") else httpx.Response(200, json={"data": {"usage": 0.5}})
    result = asyncio.run(balances.collect("openrouter", "model-key", "wrong-key", transport=httpx.MockTransport(reply)))
    assert len(calls) == 2 and result["key_status"] == "available"
    assert result["account_status"] == "management_key_rejected" and "secret" not in json.dumps(result)


def test_elevenlabs_only_reads_subscription_and_strips_invoices_and_payment_data():
    calls = []
    def reply(request):
        calls.append(request)
        return httpx.Response(200, json={"tier": "creator", "character_count": 7, "character_limit": 10,
                  "next_character_count_reset_unix": 1800000000, "voice_slots_used": 2, "voice_limit": 10,
                  "can_extend_character_limit": False, "open_invoices": [{"private": "payment-info"}]})
    result = asyncio.run(balances.collect("elevenlabs", "voice-key", transport=httpx.MockTransport(reply)))
    assert len(calls) == 1 and calls[0].method == "GET" and calls[0].url.path == "/v1/user/subscription"
    assert result["quota"]["remaining"] == 3 and result["voice_slots"]["voice_slots_used"] == 2
    assert result["overage_enabled"] is False and "payment" not in json.dumps(result)
    assert "currency" not in result and "voice-key" not in json.dumps(result)


@pytest.mark.parametrize("value", [True, -1, float("nan"), float("inf"), "1.2"])
def test_invalid_money_is_not_displayed_as_a_known_balance(value):
    with pytest.raises(AiError, match="provider_invalid_response"):
        balances.safe_credits({"data": {"total_credits": value, "total_usage": 0}})


def client(monkeypatch, key_reader):
    app = FastAPI()
    @app.middleware("http")
    async def authority(request, call_next):
        request.state.authority = "fixture-actor"
        return await call_next(request)
    monkeypatch.setattr(balances, "credential", key_reader)
    monkeypatch.setattr(balances, "management_credential", lambda *_: None)
    balances.install(app, SimpleNamespace())
    return TestClient(app)


def test_read_permission_denial_happens_before_any_provider_lookup(monkeypatch):
    def denied(*_):
        raise HTTPException(403, "permission_required")
    def no_io(*_):
        pytest.fail("Provider must not be contacted")
    monkeypatch.setattr(balances, "collect", no_io)
    c = client(monkeypatch, denied)
    assert c.get("/api/institution/provider-balance/openrouter").status_code == 403
    assert core_permission("/api/institution/provider-balance/openrouter", "GET") == ("settings.providers.read", "settings")
    assert c.post("/api/institution/provider-balance/openrouter").status_code == 405
    assert c.get("/api/institution/provider-balance/unknown").status_code == 422


def test_rotated_credential_invalidates_snapshot_and_never_returns_the_data(monkeypatch):
    keys = iter(["old", "new"])
    c = client(monkeypatch, lambda *_: next(keys))
    async def collect(*_):
        return {"balance": "must-not-return"}
    monkeypatch.setattr(balances, "collect", collect)
    result = c.get("/api/institution/provider-balance/openrouter")
    assert result.status_code == 409 and "must-not-return" not in result.text


def test_management_secret_is_only_accepted_for_openrouter_and_not_other_scopes():
    valid = {"operation_id": "fixture", "scope": "provider", "owner": "openrouter", "kind": "management_key", "value": "fixture-key"}
    assert SecretEdit(**valid).kind == "management_key"
    for patch in ({"owner": "gemini"}, {"scope": "channel"}, {"scope": "webhook"}):
        with pytest.raises(ValidationError):
            SecretEdit(**{**valid, **patch})
