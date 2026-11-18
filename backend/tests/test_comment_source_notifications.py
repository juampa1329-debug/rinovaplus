import json
from contextlib import nullcontext
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.institutional import comment_effects as effects
from app.institutional import comment_notifications as notifications
from app.modules.channels import providers


@pytest.mark.parametrize("change", ["none", "comment", "account", "authority"])
def test_source_result_applies_only_with_the_original_authority_and_versions(
    monkeypatch, change
):
    identity, integration, operation, actor_id = [str(uuid4()) for _ in range(4)]
    settings = SimpleNamespace(ticket={"context": [[1, str(uuid4())]]})
    original = {
        "CommentId": identity,
        "IntegrationId": integration,
        "RowVersion": b"version1",
        "Body": "Original",
        "Payload": '{"_crm":{"state":"new","control_mode":"human"}}',
    }
    captured, calls = [], {"comment": 0, "account": 0, "authority": 0}

    class Cursor:
        rowcount = 1

        def execute(self, sql, *params):
            captured.append((sql, params))
            return SimpleNamespace(fetchone=lambda: (1,))

    def one(_c, sql, *_params):
        if "ProviderOperation" in sql:
            return None
        calls["comment"] += 1
        return {
            **original,
            "RowVersion": b"version2"
            if change == "comment" and calls["comment"] > 1
            else b"version1",
        }

    def account(*_a):
        calls["account"] += 1
        return {
            "IntegrationId": integration,
            "ApplicationId": str(uuid4()),
            "Channel": "instagram",
            "RowVersion": b"changed!"
            if change == "account" and calls["account"] > 1
            else b"version1",
        }

    def authorize(*_a):
        calls["authority"] += 1
        if change == "authority" and calls["authority"] > 1:
            raise HTTPException(403, "permission_denied")
        return {"UserId": actor_id}

    monkeypatch.setattr(effects, "transaction", lambda *_a, **_k: nullcontext(Cursor()))
    monkeypatch.setattr(effects, "one", one)
    monkeypatch.setattr(effects, "account", account)
    monkeypatch.setattr(effects, "authorize", authorize)
    monkeypatch.setattr(effects, "configuration", lambda *_a: {"ModuleEnabled": True})
    monkeypatch.setattr(effects, "bound_hash", lambda *_a: b"digest")
    monkeypatch.setattr(effects, "provider_account", lambda *_a: ({}, 1))
    service = effects.Effects(
        settings,
        lambda *_a: {
            "source": {
                "status": "unavailable",
                "reason": "provider_permission_or_request_rejected",
            }
        },
    )
    result = service.perform(
        None,
        identity,
        "reconcile",
        effects.Effect(operation_id=operation, row_version=b"version1".hex()),
    )
    updates = [
        params
        for sql, params in captured
        if "UPDATE crm_channels2.SocialComment" in sql
    ]
    if change == "none":
        assert result["status"] == "confirmed" and len(updates) == 1
        payload = json.loads(updates[0][0])
        assert payload["_crm"]["state"] == "unavailable" and updates[0][1] == "Original"
    else:
        assert (
            result["status"] == "uncertain" and result["result"] == {} and not updates
        )


@pytest.mark.parametrize(
    "channel,field", [("facebook", "message"), ("instagram", "text")]
)
def test_reconcile_updates_only_the_exact_comment(monkeypatch, channel, field):
    def request(_adapter, method, path, params):
        assert (method, path, params) == ("GET", "123", {"fields": "id," + field})
        return {"id": "123", field: "Texto editado", "private": "not returned"}

    monkeypatch.setattr(providers, "request", request)
    result = effects.call_provider(
        {"channel": channel}, "reconcile", {"ExternalId": "123"}
    )
    assert result == {"source": {"status": "available"}, "body": "Texto editado"}
    assert effects.valid_source_result(result)
    monkeypatch.setattr(
        providers, "request", lambda *_a, **_k: {"id": "other", field: "bad"}
    )
    with pytest.raises(providers.ProviderFailure) as raised:
        effects.call_provider({"channel": channel}, "reconcile", {"ExternalId": "123"})
    assert raised.value.code == "comment_target_mismatch"


@pytest.mark.parametrize(
    "code",
    [
        "provider_permission_or_request_rejected",
        "meta_access_token_invalid",
        "provider_connection_failed",
    ],
)
def test_missing_source_is_not_a_deleted_comment_or_a_global_token_failure(
    monkeypatch, code
):
    def rejected(*_a, **_k):
        raise providers.ProviderFailure(code)

    monkeypatch.setattr(providers, "request", rejected)
    if code != "provider_permission_or_request_rejected":
        with pytest.raises(providers.ProviderFailure):
            effects.call_provider(
                {"channel": "instagram"}, "reconcile", {"ExternalId": "123"}
            )
        return
    result = effects.call_provider(
        {"channel": "instagram"}, "reconcile", {"ExternalId": "123"}
    )
    payload = {
        "_crm": {
            "state": "archived",
            "control_mode": "human",
            "last_queue_id": "accepted-send",
        }
    }
    effects.apply_source_result(payload, result)
    state = payload["_crm"]
    assert (
        state["state"] == "unavailable"
        and state["state_before_unavailable"] == "archived"
    )
    assert (
        state["last_queue_id"] == "accepted-send" and state["control_mode"] == "human"
    )
    effects.apply_source_result(payload, result)
    effects.apply_source_result(
        payload, {"source": {"status": "available"}, "body": "restored"}
    )
    assert state["state"] == "archived" and "state_before_unavailable" not in state


def test_notification_ack_is_per_user_idempotent_and_does_not_change_comment_or_ai(
    monkeypatch,
):
    statements, journal, audits = [], [], []
    now = datetime(2026, 11, 18, 13)

    class Cursor:
        def execute(self, sql, *params):
            statements.append((sql, params))
            assert sql == "SELECT SYSUTCDATETIME()"
            return SimpleNamespace(fetchval=lambda: now)

    monkeypatch.setattr(
        notifications, "transaction", lambda *_a, **_k: nullcontext(Cursor())
    )
    monkeypatch.setattr(
        notifications, "authorize", lambda *_a, **_k: {"UserId": "own-user"}
    )
    monkeypatch.setattr(notifications, "replay", lambda *_a: (b"digest", None))
    monkeypatch.setattr(
        notifications, "record_operation", lambda *args: journal.append(args)
    )
    monkeypatch.setattr(notifications, "audit", lambda *args: audits.append(args))
    body = notifications.Acknowledge(
        operation_id="fixture", read_through="2026-11-18T12:00:00Z"
    )
    service = notifications.Notifications(None)
    result = service.acknowledge(None, body)
    assert journal[0][2] == "own-user" and journal[0][4] == notifications.ACTION
    assert result["read_through"] == "2026-11-18T12:00:00.000000Z"
    assert audits and all("SocialComment" not in sql for sql, _ in statements)
    monkeypatch.setattr(notifications, "replay", lambda *_a: (b"digest", result))
    assert service.acknowledge(None, body) == result and len(journal) == 1
    monkeypatch.setattr(notifications, "replay", lambda *_a: (b"digest", None))
    with pytest.raises(HTTPException) as raised:
        service.acknowledge(
            None, body.model_copy(update={"read_through": "2030-01-01T00:00:00Z"})
        )
    assert raised.value.status_code == 422 and len(journal) == 1


def test_notification_list_uses_actor_watermark_and_keeps_newer_comments(monkeypatch):
    now = datetime(2026, 11, 18, 13)
    after = "2026-11-18T12:00:00.000000Z"

    class Cursor:
        def execute(self, sql, *params):
            if "MAX(ResourceRef)" in sql:
                assert params == ("institution", "own-user", notifications.ACTION)
                value = after
            elif "COUNT(*)" in sql:
                assert "ReceivedAt>? AND s.ReceivedAt<=?" in sql
                assert params == ("institution", datetime(2026, 11, 18, 12), now)
                value = 1
            else:
                assert sql == "SELECT SYSUTCDATETIME()"
                value = now
            return SimpleNamespace(fetchval=lambda: value)

    monkeypatch.setattr(
        notifications, "transaction", lambda *_a, **_k: nullcontext(Cursor())
    )
    monkeypatch.setattr(notifications, "institution", lambda _: "institution")
    monkeypatch.setattr(notifications, "authorize", lambda *_a: {"UserId": "own-user"})
    monkeypatch.setattr(
        notifications,
        "rows",
        lambda *_a: [
            {
                "CommentId": "new-comment",
                "Body": "new",
                "AuthorExternalId": "author",
                "ReceivedAt": now,
                "Channel": "instagram",
            }
        ],
    )
    result = notifications.Notifications(None).read(None)
    assert result["total"] == 1 and result["items"][0]["id"] == "new-comment"
    assert "own-user" not in json.dumps(result)
