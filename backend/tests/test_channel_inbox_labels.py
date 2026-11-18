"""Cosmetic account labels preserve the connected provider configuration."""
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.institutional import channels


def body(**extra):
    return channels.AccountEdit(operation_id=str(uuid4()), revision=1,
        row_version="0000000000000001", application_version="0000000000000002",
        values={}, **extra)


@pytest.mark.parametrize("label", ["  ", "😀" * 81])
def test_invalid_label_is_rejected(label):
    with pytest.raises(ValidationError):
        body(display_name=label)


def test_label_only_save_preserves_provider_status_and_requires_recent_authority(monkeypatch):
    cursor = Mock(rowcount=1)
    cursor.execute.return_value = cursor
    cursor.fetchval.return_value = "{}"

    @contextmanager
    def tx(*args, **kwargs):
        yield cursor

    auth = Mock(return_value={"UserId": str(uuid4())})
    monkeypatch.setattr(channels, "transaction", tx)
    monkeypatch.setattr(channels, "authorize", auth)
    monkeypatch.setattr(channels, "institution", lambda _: str(uuid4()))
    monkeypatch.setattr(channels, "replay", lambda *args: (b"digest", None))
    monkeypatch.setattr(channels, "record_operation", Mock())
    monkeypatch.setattr(channels, "audit", Mock())
    monkeypatch.setattr(channels, "contract", lambda: {"groups": [], "fields": []})
    item = {"revision": 1, "row_version": "0000000000000001",
        "application_version": "0000000000000002", "channel": "whatsapp"}
    service = channels.Channels(SimpleNamespace())
    service._item = Mock(return_value=item)
    service.edited = Mock(side_effect=AssertionError("label must not pause the channel"))
    service.save("authority", str(uuid4()), body(display_name=" CBN Admisiones "))
    assert auth.call_args.kwargs["recent"] is True
    statements = [str(call.args[0]) for call in cursor.execute.call_args_list]
    assert any("[DisplayName]=?" in sql for sql in statements)
    assert not any("RequestedStatus" in sql or "ExternalAccountId" in sql for sql in statements)
    service.edited.assert_not_called()
