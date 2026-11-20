import json
from contextlib import nullcontext
from copy import deepcopy
from types import SimpleNamespace
from uuid import uuid4

import httpx2 as httpx
import pytest
from fastapi import HTTPException

from app.institutional import language_rehearsal as rehearsal
from app.modules.ai.infrastructure.providers import ProviderGateway


def environment(monkeypatch, *, rotate=False, uncertain=False, revoke_after_post=False, busy=False):
    state = {"operation": None, "calls": [], "reserves": [], "revision": 27}
    profile = SimpleNamespace(ticket={"context": [[1, str(uuid4())]]})
    actor = {"UserId": str(uuid4())}
    ai = {"provider": "gemini", "model": "gemini-fixture", "enabled": True}
    class Cursor:
        rowcount = 1
        def execute(self, sql, *params):
            assert sql.startswith("UPDATE crm_access.Operation SET Result=")
            state["operation"] = json.loads(params[0])
            return self
    monkeypatch.setattr(rehearsal, "transaction", lambda *_a, **_k: nullcontext(Cursor()))
    monkeypatch.setattr(rehearsal, "authorize", lambda *_a, **_k: actor)
    monkeypatch.setattr(rehearsal, "setting", lambda *_: {"revision": state["revision"], "document": ai})
    monkeypatch.setattr(rehearsal, "replay", lambda *_: (b"digest", deepcopy(state["operation"])))
    monkeypatch.setattr(rehearsal, "record_operation", lambda *args: state.update(operation=deepcopy(args[-1])))
    monkeypatch.setattr(rehearsal, "one", lambda *_: {"OperationId": "fixture"} if state["operation"]["state"] == "running" else None)
    saved = {"revision": 27, "credentials": {}, "keys": {"openrouter": "fixture"}, "routes": [{
        "provider": "openrouter", "model": "fixture:free", "input_usd_per_million": 0, "output_usd_per_million": 0}]}
    monkeypatch.setattr(rehearsal.resilience, "snapshot", lambda *_: saved)
    def check(*_):
        if state["revision"] != 27:
            raise HTTPException(409, "language_backup_configuration_changed")
    monkeypatch.setattr(rehearsal.resilience, "assert_snapshot", check)
    monkeypatch.setattr(rehearsal.resilience, "reservation", lambda *args: state["reserves"].append(args[2]))
    def handler(req):
        state["calls"].append(req.method)
        if req.url.path == "/api/v1/key":
            return httpx.Response(200, json={"data": {"label": "NEVER EXPOSE THIS LABEL", "limit_remaining": 99,
                "free_model_daily_requests": {"used": 50, "limit": 50, "remaining": 0}}})
        if req.method == "GET":
            if rotate:
                state["revision"] = 28
            return httpx.Response(200, json={"data": [{"id": "fixture:free", "context_length": 500000,
                "architecture": {"output_modalities": ["text"]}, "supported_parameters": ["max_tokens", "temperature", "response_format"],
                "top_provider": {"max_completion_tokens": 8000}, "pricing": {"prompt": "0", "completion": "0"}}]})
        wire = json.loads(req.content)
        if busy:
            return httpx.Response(429, json={"error": {"code": 429}})
        if uncertain:
            raise httpx.ReadTimeout("fixture", request=req)
        if revoke_after_post:
            state["revision"] = 28
        assert wire["provider"]["data_collection"] == "deny" and not wire["provider"]["allow_fallbacks"]
        query = json.loads(wire["messages"][1]["content"])
        prefix = "Alex, " if query["history"] else ""
        text = prefix + "Programa Demostración P21: 2 semestres en jornada nocturna."
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {
            "content": json.dumps({"decision": "responder", "text": text})}}], "usage": {"prompt_tokens": 100, "completion_tokens": 30}})
    gateway = ProviderGateway(saved["keys"], httpx.MockTransport(handler))
    return state, profile, gateway


@pytest.mark.parametrize("scenario", ["unavailable", "rate_limited"])
@pytest.mark.parametrize("audience", ["message", "comment"])
def test_real_route_wire_and_synthetic_rejection_use_one_backup_and_replay_never_regenerates(monkeypatch, scenario, audience):
    state, profile, gateway = environment(monkeypatch)
    body = rehearsal.Rehearsal(operation_id=str(uuid4()), revision=27, case=scenario, audience=audience)
    first = rehearsal.run(profile, {}, body, gateway=gateway)
    assert first["state"] == "passed" and first["trace"]["fallback_used"]
    assert all(first["checks"].values()) and first["provider_calls"] == 1
    assert first["synthetic_primary"] and first["real_backup"]
    assert not first["crm_written"] and not first["delivered"] and not first["published_configuration_changed"]
    assert first["usage"]["promptTokenCount"] == 100
    second = rehearsal.run(profile, {}, body, gateway=gateway)
    assert first == second and state["calls"] == ["GET", "POST"] and len(state["reserves"]) == 1
    assert first["skill_policy"]["version"] == "cbn-sales-skills-v5"


@pytest.mark.parametrize("scenario", ["healthy", "human"])
def test_healthy_principal_and_human_control_make_zero_external_calls(monkeypatch, scenario):
    state, profile, gateway = environment(monkeypatch)
    result = rehearsal.run(profile, {}, rehearsal.Rehearsal(operation_id=str(uuid4()), revision=27, case=scenario), gateway=gateway)
    assert result["state"] == "passed" and result["provider_calls"] == 0
    assert state["calls"] == [] and state["reserves"] == []


def test_rotation_after_catalog_prevents_reservation_and_inference(monkeypatch):
    state, profile, gateway = environment(monkeypatch, rotate=True)
    result = rehearsal.run(profile, {}, rehearsal.Rehearsal(operation_id=str(uuid4()), revision=27), gateway=gateway)
    assert result["state"] == "blocked" and result["provider_calls"] == 0
    assert state["calls"] == ["GET"] and state["reserves"] == []


def test_operation_running_after_lost_response_is_returned_without_external_calls(monkeypatch):
    state, profile, gateway = environment(monkeypatch)
    state["operation"] = {"state": "running", "operation_id": str(uuid4())}
    result = rehearsal.run(profile, {}, rehearsal.Rehearsal(operation_id=str(uuid4()), revision=27), gateway=gateway)
    assert result["state"] == "running" and not state["calls"]


def test_paid_backups_and_stale_revision_are_rejected_before_claim(monkeypatch):
    state, profile, gateway = environment(monkeypatch)
    with pytest.raises(HTTPException):
        rehearsal.run(profile, {}, rehearsal.Rehearsal(operation_id=str(uuid4()), revision=26), gateway=gateway)
    assert not state["operation"] and not state["calls"]
    monkeypatch.setattr(rehearsal.resilience, "snapshot", lambda *_: {"routes": [{"provider": "gemini", "model": "paid"}]})
    with pytest.raises(HTTPException, match="language_rehearsal_free_backup_required"):
        rehearsal.run(profile, {}, rehearsal.Rehearsal(operation_id=str(uuid4()), revision=27), gateway=gateway)
    assert not state["operation"] and not state["calls"]


def test_unknown_backup_result_is_recoverable_and_never_generated_twice(monkeypatch):
    state, profile, gateway = environment(monkeypatch, uncertain=True)
    body = rehearsal.Rehearsal(operation_id=str(uuid4()), revision=27)
    first = rehearsal.run(profile, {}, body, gateway=gateway)
    assert first["state"] == "uncertain" and first["provider_calls"] == 1
    assert "text" not in first
    assert rehearsal.run(profile, {}, body, gateway=gateway) == first
    assert state["calls"] == ["GET", "POST"]


def test_revocation_after_generation_discards_response_before_any_crm_effect(monkeypatch):
    state, profile, gateway = environment(monkeypatch, revoke_after_post=True)
    result = rehearsal.run(profile, {}, rehearsal.Rehearsal(operation_id=str(uuid4()), revision=27), gateway=gateway)
    assert result["state"] == "blocked" and result["provider_calls"] == 1
    assert "text" not in result and not result["delivered"] and not result["crm_written"]


def test_backup_429_reports_free_quota_without_leaking_account_metadata_or_repeating_post(monkeypatch):
    state, profile, gateway = environment(monkeypatch, busy=True)
    result = rehearsal.run(profile, {}, rehearsal.Rehearsal(operation_id=str(uuid4()), revision=27), gateway=gateway)
    assert result["state"] == "failed" and result["code"] == "openrouter_free_daily_limit"
    assert result["free_quota"] == {"used": 50, "limit": 50, "remaining": 0}
    assert "NEVER EXPOSE" not in json.dumps(result) and "limit_remaining" not in json.dumps(result)
    assert state["calls"] == ["GET", "POST", "GET"] and result["provider_calls"] == 1
