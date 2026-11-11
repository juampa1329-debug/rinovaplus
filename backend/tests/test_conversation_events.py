"""R3A queue invariants without database or network IO."""

from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from test_admissions import ReadCursor, Workspace

from app.modules.conversation_events.api.router import (
    SOURCES,
    ConversationEvents,
    EventWorker,
    RetryRequest,
)
from app.main import create_app


@pytest.fixture
def repository(monkeypatch):
    monkeypatch.setattr(ConversationEvents, "verify", staticmethod(lambda _: None))
    return lambda sets: ConversationEvents(Workspace(ReadCursor(sets)))


def test_expired_or_stale_owner_cannot_prepare(repository):
    repo = repository([[]])
    with pytest.raises(HTTPException) as failure:
        repo.prepare(7, str(uuid4()))
    assert failure.value.status_code == 409
    sql = repo.workspace.cursor.calls[0][0]
    assert "LeaseToken=?" in sql and "LeaseUntil>SYSUTCDATETIME()" in sql
    assert repo.workspace.rollbacks == 1


def test_missing_source_does_not_confirm_event(repository):
    convo = str(uuid4())
    source = str(uuid4())
    repo = repository(
        [[{"kind": "message", "source": source, "conversation": convo}], []]
    )
    with pytest.raises(HTTPException) as failure:
        repo.prepare(7, str(uuid4()))
    assert failure.value.detail == "event_source_missing"
    assert not any("UPDATE" in s for s, _ in repo.workspace.cursor.calls)
    assert repo.workspace.rollbacks == 1


def test_retry_replay_returns_original_count_without_new_reset(repository):
    repo = repository([[{"count": 3}]])
    assert repo.retry_failed(str(uuid4())) == {"retried": 3}
    assert len(repo.workspace.cursor.calls) == 1


@pytest.mark.parametrize("value", ["bad", "", 3])
def test_retry_identifier_is_validated(value):
    with pytest.raises(ValidationError):
        RetryRequest(operationId=value)


def test_worker_prepares_during_any_control_without_provider_call():
    repo = Mock()
    repo.claim.side_effect = [(7, "token"), None]
    EventWorker(repo).cycle()
    repo.capture.assert_called_once()
    repo.prepare.assert_called_once_with(7, "token")
    repo.fail.assert_not_called()


def test_worker_does_not_fail_a_reclaimed_event():
    repo = Mock()
    repo.claim.side_effect = [(7, "old-token"), None]
    repo.prepare.side_effect = HTTPException(409, "event_lease_lost")
    EventWorker(repo).cycle()
    repo.fail.assert_not_called()


def test_worker_records_processing_failure_and_keeps_polling():
    repo = Mock()
    repo.claim.side_effect = [(7, "token"), (8, "other"), None]
    repo.prepare.side_effect = [RuntimeError("synthetic"), None]
    EventWorker(repo).cycle()
    repo.fail.assert_called_once_with(7, "token")
    assert repo.prepare.call_count == 2


def test_worker_bounds_each_preparation_batch():
    repo = Mock()
    repo.claim.return_value = (7, "token")
    EventWorker(repo).cycle()
    assert repo.prepare.call_count == 20


def test_catchup_uses_missing_references_not_maximum_cursor(repository):
    repo = repository([[], [], [], []])
    repo.workspace.cursor.rowcount = 1
    assert repo.capture() == 4
    for sql, args in repo.workspace.cursor.calls:
        assert "TOP (100)" in sql and "NOT EXISTS" in sql
        assert "MAX(" not in sql and len(args) == 2
    assert "ControlMode" not in "".join(SOURCES.values())
    assert "task_create" in SOURCES["inbox_operation"]
    assert "add_message" in SOURCES["crm_operation"]


def test_events_endpoints_fail_closed_outside_local_copy():
    with TestClient(
        create_app(),
        base_url="http://127.0.0.1:5173",
        client=("127.0.0.1", 10),
        headers={"X-CRM-Local": "1", "Origin": "http://127.0.0.1:5173"},
    ) as client:
        assert client.get("/api/local/crm/events/status").status_code == 503
        assert (
            client.post(
                "/api/local/crm/events/retry", json={"operationId": str(uuid4())}
            ).status_code
            == 503
        )
