import asyncio
import json
from contextlib import contextmanager
from decimal import Decimal
from types import SimpleNamespace

import httpx2 as httpx
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.institutional import balance_alerts as alerts, comment_ai
from app.institutional.models import Budgets


def test_budget_defaults_preserve_disabled_zero_and_validate_threshold():
    assert not Budgets().ai_budget_unlimited
    assert Budgets().openrouter_balance_alert_threshold_usd == 5
    for threshold in (-1, float("nan"), float("inf")):
        with pytest.raises(ValidationError):
            Budgets(openrouter_balance_alert_threshold_usd=threshold)


class Ledger:
    def __init__(self, used=None):
        self.used, self.writes = used, []

    def execute(self, sql, *params):
        if not sql.startswith("SELECT"):
            self.writes.append((sql, params))
        return self

    def fetchval(self):
        return self.used


@pytest.mark.parametrize("kind", ["tokens", "usd"])
@pytest.mark.parametrize("maximum", [0, 1])
def test_unlimited_keeps_reservations_after_crossing_old_limits(monkeypatch, kind, maximum):
    monkeypatch.setattr(comment_ai, "setting", lambda *_: {"document": {"ai_budget_unlimited": True}})
    monkeypatch.setattr(comment_ai, "institution", lambda *_: "fixture")
    c = Ledger(Decimal(100))
    comment_ai.reserve_budget(c, None, kind, 10, maximum)
    assert len(c.writes) == 1 and c.writes[0][1][0] == Decimal(10)


def test_explicit_opt_in_never_removes_message_limits_or_legacy_budget(monkeypatch):
    monkeypatch.setattr(comment_ai, "institution", lambda *_: "fixture")
    for unlimited, kind, limit, expected in [(False, "tokens", 0, "disabled"), (False, "usd", 1, "exhausted"), (True, "messages", 1, "exhausted")]:
        monkeypatch.setattr(comment_ai, "setting", lambda *_: {"document": {"ai_budget_unlimited": unlimited}})
        c = Ledger(Decimal(100))
        with pytest.raises(HTTPException) as error:
            comment_ai.reserve_budget(c, None, kind, 10, limit)
        assert error.value.detail.endswith(expected) and not c.writes


def fixture_mail(monkeypatch):
    calls = []
    people = [{"UserId": str(i), "Login": f"admin{i}@example.invalid", "DisplayName": "Test", "Active": active, "Actions": json.dumps(actions)} for i, active, actions in [(1, True, ["users.manage"]), (2, True, ["users.manage"]), (3, False, ["users.manage"]), (4, True, ["inbox.read"])]]
    monkeypatch.setattr(alerts.mail, "transport", lambda *_: {"enabled": True})
    monkeypatch.setattr(alerts.mail, "users", lambda *_: people)
    monkeypatch.setattr(alerts.mail, "enqueue", lambda *args, **kw: calls.append((args, kw)))
    return calls


def test_low_balance_notifies_active_admins_once_rearms_after_recharge(monkeypatch):
    calls = fixture_mail(monkeypatch)
    s = SimpleNamespace(public_origin="https://example.invalid")
    record, status = alerts.transition(None, s, {}, 4.99, 5)
    assert status == "low_notified" and len(calls) == 2
    assert all(v[0][2] == "provider.balance_low" for v in calls)
    record, _ = alerts.transition(None, s, record, 4, 5)
    assert len(calls) == 2
    record, status = alerts.transition(None, s, record, 10, 5)
    assert not record["low"] and status == "available"
    alerts.transition(None, s, record, 5, 5)
    assert len(calls) == 4
    assert calls[0][0][3] != calls[2][0][3]


def test_changed_threshold_and_disabled_mail_do_not_lose_alert(monkeypatch):
    calls = fixture_mail(monkeypatch)
    s = SimpleNamespace(public_origin="https://example.invalid")
    record, _ = alerts.transition(None, s, {}, 4, 5)
    alerts.transition(None, s, record, 4, 6)
    assert len(calls) == 4
    monkeypatch.setattr(alerts.mail, "transport", lambda *_: {"enabled": False})
    record, status = alerts.transition(None, s, {}, 1, 5)
    assert status == "mail_disabled" and not record.get("low")


def test_credits_check_only_gets_global_credits_with_management_key():
    calls = []
    def reply(req):
        calls.append(req)
        return httpx.Response(200, json={"data": {"total_credits": 20, "total_usage": 16}})
    assert asyncio.run(alerts.credits("fixture-management", httpx.MockTransport(reply))) == 4
    assert len(calls) == 1 and calls[0].method == "GET" and calls[0].url.path == "/api/v1/credits"


def test_missing_key_and_durable_cadence_make_no_network_calls(monkeypatch):
    saved = {}
    @contextmanager
    def tx(*args, **kw):
        yield None
    monkeypatch.setattr(alerts, "transaction", tx)
    monkeypatch.setattr(alerts.mail, "enabled", lambda *_: True)
    monkeypatch.setattr(alerts, "setting", lambda *_: {"document": {"openrouter_balance_alert_enabled": True}})
    monkeypatch.setattr(alerts, "state", lambda *_: dict(saved))
    monkeypatch.setattr(alerts, "save", lambda c, s, v: saved.update(v))
    monkeypatch.setattr(alerts, "secret_row", lambda *_: None)
    async def forbidden(*_):
        raise AssertionError("network must not run")
    monitor = alerts.Monitor(None, forbidden)
    monitor.once()
    assert saved["status"] == "management_key_required" and saved["next_at"]
    first_claim = saved["claim"]
    monitor.once()
    assert saved["claim"] == first_claim


@pytest.mark.parametrize("unlimited", [False, True])
def test_agent_monthly_usd_stop_is_overridden_only_by_server_policy(monkeypatch, unlimited):
    from app.modules.agents import runtime
    from app.modules.ai.infrastructure.providers import AiError
    config = {"provider": "openrouter", "primary_model": "fixture", "fallback_model": "", "monthly_usd_limit": 1, "hard_stop": True, "input_usd_per_million": 1, "output_usd_per_million": 1, "route": "default", "ab_variant": "A"}
    monkeypatch.setattr(runtime, "require_execution", lambda *_: None)
    monkeypatch.setattr(runtime.Configuration, "model_validate_json", lambda *_: SimpleNamespace(model_dump=lambda **_: config))
    class Cursor:
        agent_budget_unlimited = unlimited
        writes = []
        def execute(self, sql, *args):
            self.sql = sql
            if sql.startswith("INSERT"):
                self.writes.append(sql)
            return self
        def fetchone(self):
            return ["{}"] if self.sql.startswith("SELECT Document") else [100, 0]
    cursor = Cursor()
    selection = {"configuration": config, "chain_ids": ["fixture"], "agent_id": "fixture", "version": 1, "binding": "fixture"}
    if unlimited:
        runtime.reserve_execution(cursor, "request", selection, 1000)
        assert len(cursor.writes) == 1
    else:
        with pytest.raises(AiError, match="agents_budget_exhausted"):
            runtime.reserve_execution(cursor, "request", selection, 1000)
        assert not cursor.writes


@pytest.mark.parametrize("changed", [False, True])
def test_unavailable_balance_never_enqueues_mail_or_overwrites_changed_credentials(monkeypatch, changed):
    from app.modules.ai.infrastructure.providers import AiError
    saved, calls = {}, []
    policy = {"openrouter_balance_alert_enabled": True}
    row = {"SecretId": "fef8c4b2-810e-4855-8721-bff85619a2c5", "VersionNo": 1, "Nonce": b"", "Ciphertext": b""}
    @contextmanager
    def tx(*_, **kw):
        yield None
    monkeypatch.setattr(alerts, "transaction", tx)
    monkeypatch.setattr(alerts.mail, "enabled", lambda *_: True)
    monkeypatch.setattr(alerts, "setting", lambda *_: {"document": policy})
    monkeypatch.setattr(alerts, "state", lambda *_: dict(saved))
    monkeypatch.setattr(alerts, "save", lambda c, s, v: saved.update(v))
    monkeypatch.setattr(alerts, "secret_row", lambda *_: dict(row))
    monkeypatch.setattr(alerts, "institution", lambda *_: "fixture")
    monkeypatch.setattr(alerts, "key", lambda *_: b"")
    monkeypatch.setattr(alerts, "unseal", lambda *_: "fixture-secret")
    monkeypatch.setattr(alerts.mail, "enqueue", lambda *a, **k: calls.append(a))
    async def fetch(token):
        assert token == "fixture-secret"
        if changed:
            row["VersionNo"] = 2
            return 1
        raise AiError("provider_response_timeout", 504)
    alerts.Monitor(None, fetch).once()
    assert not calls and "remaining_usd" not in saved
    assert saved["status"] == ("checking" if changed else "unavailable")


@pytest.mark.parametrize("unlimited", [False, True])
@pytest.mark.parametrize("old_cap", [0, 1])
def test_agent_monthly_tokens_keep_the_ledger_without_internal_stop(monkeypatch, unlimited, old_cap):
    from app.modules.agents import service, runtime
    from app.modules.ai.infrastructure.providers import AiError
    monkeypatch.setattr(runtime, "require_execution", lambda *_: None)
    monkeypatch.setattr(runtime, "reserve_execution", lambda *_: None)
    config = {"monthly_token_limit": old_cap, "hard_stop": True, "fallback_model": "", "max_tokens": 200}
    monkeypatch.setattr(service, "load", lambda *_: ({"agent": {"configuration": config}}, {}))
    class Cursor:
        agent_budget_unlimited = unlimited
        def __init__(self):
            self.writes = []
        def execute(self, sql, *args):
            if sql.startswith("INSERT"):
                self.writes.append((sql, args))
            return self
        def fetchone(self):
            return None
        def fetchval(self):
            return 100000
    c = Cursor()
    selected = {"configuration": config, "agent_id": "agent", "chain_ids": ["agent"]}
    if unlimited:
        service.AgentsService.reserve(None, c, "request", selected, [{"content": "source"}])
        assert len(c.writes) == 1 and c.writes[0][1][-1] > 0
    else:
        with pytest.raises(AiError, match="agents_budget_exhausted"):
            service.AgentsService.reserve(None, c, "request", selected, [{"content": "source"}])
        assert not c.writes
