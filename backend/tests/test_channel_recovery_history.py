import json
from contextlib import nullcontext
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.institutional import channel_recovery


@pytest.mark.parametrize("can_read,module_enabled", [(True, True), (False, True), (True, False)])
def test_recovery_history_identifies_event_without_leaking_unreadable_body(
    monkeypatch, can_read, module_enabled,
):
    integration, event_id, app_id, user_id = [str(uuid4()) for _ in range(4)]
    actor = {"Actions": json.dumps(["inbox.read"] if can_read else []), "UserId": user_id}
    event = {
        "EventId": event_id, "Status": "quarantined", "LastErrorCode": None,
        "RowVersion": bytes.fromhex("0000000000000001"), "Kind": "comment",
        "CreatedAt": datetime(2026, 11, 17, 12, 0),
        "Payload": json.dumps({"text": "Texto privado de prueba", "provider": {"url": "secret-provider-url"}}),
    }
    monkeypatch.setattr(channel_recovery, "transaction", lambda *_a, **_k: nullcontext(object()))
    monkeypatch.setattr(channel_recovery, "authorize", lambda *_a, **_k: actor)
    monkeypatch.setattr(channel_recovery, "account", lambda *_: {
        "IntegrationId": integration, "ApplicationId": app_id,
        "Channel": "instagram", "ExternalAccountId": "fixture",
    })
    monkeypatch.setattr(channel_recovery, "institution", lambda _: "fixture")
    monkeypatch.setattr(channel_recovery, "rows", lambda _c, sql, *_: [event] if "e.EventId" in sql else [])
    monkeypatch.setattr(channel_recovery, "one", lambda *_: None)
    from app.institutional import settings
    monkeypatch.setattr(settings, "setting", lambda *_: {"document": {"enabled": {"inbox": module_enabled}}})

    result = channel_recovery.Recoveries(SimpleNamespace()).read(None, integration)
    visible = result["events"][0]
    assert visible["id"] == event_id and visible["kind"] == "comment"
    assert visible["created_at"] == "2026-11-17T12:00:00Z"
    assert visible["row_version"] == "0000000000000001"
    expected = "Texto privado de prueba" if can_read and module_enabled else None
    assert visible["body_preview"] == expected
    assert "secret-provider-url" not in json.dumps(result)
    if expected is None:
        assert "Texto privado de prueba" not in json.dumps(result)
