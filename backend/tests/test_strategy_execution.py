"""Action reservations cannot block the independent analysis recovery loop."""

import asyncio
from contextlib import contextmanager
from unittest.mock import Mock
from uuid import uuid4

from fastapi import HTTPException
from test_analysis_runtime import setup_worker

from app.modules.conversation_strategy.api.router import ConversationStrategy


class Cursor:
    def __init__(self, conversations):
        self.conversations = conversations
        self.calls = []

    def execute(self, sql, *args):
        self.calls.append((sql, args))
        return self

    def fetchall(self):
        return [(i,) for i in self.conversations]

    def fetchone(self):
        return (str(uuid4()),)


def setup_repository(monkeypatch, count=1):
    cursor = Cursor([str(uuid4()) for _ in range(count)])

    @contextmanager
    def transaction(write=False):
        assert write
        yield cursor

    workspace = Mock(transaction=transaction)
    service = ConversationStrategy(workspace)
    monkeypatch.setattr("app.modules.conversation_strategy.api.router.present", lambda *args: True)
    monkeypatch.setattr(
        "app.modules.conversation_strategy.api.router.ConversationAnalysis.verify", lambda c: None
    )
    monkeypatch.setattr(
        "app.modules.conversation_strategy.api.router.InboxOperations.verify", lambda c: None
    )
    monkeypatch.setattr(
        "app.modules.contacts.application.merge.historical_ids", lambda c, contact: {contact}
    )
    service.inspect = Mock(
        return_value=({"id": str(uuid4())}, {}, {}, None, {"effective": True})
    )
    service.record = Mock()
    return service, cursor


def test_reserved_peer_skips_only_action_and_r4_recovery_is_still_reached(monkeypatch):
    service, cursor = setup_repository(monkeypatch)
    monkeypatch.setattr(
        "app.modules.contacts.application.merge.analysis_guard",
        Mock(side_effect=HTTPException(409, "analysis_attempt_reserved")),
    )
    worker, analysis, _, gateway, _, _ = setup_worker(monkeypatch)
    worker.strategy = service
    asyncio.run(worker.cycle())
    analysis.reserve.assert_called_once()
    gateway.generate.assert_awaited_once()
    assert not any("INSERT crm_inbox.Task" in sql for sql, _ in cursor.calls)


def test_reserved_peer_does_not_abort_another_eligible_conversation(monkeypatch):
    service, cursor = setup_repository(monkeypatch, 2)
    monkeypatch.setattr(
        "app.modules.contacts.application.merge.analysis_guard",
        Mock(side_effect=[HTTPException(409, "analysis_attempt_reserved"), None]),
    )
    assert service.execute("binding") == "task_created"
    assert sum("INSERT crm_inbox.Task" in sql for sql, _ in cursor.calls) == 1
    assert service.record.call_count == 1


def test_current_batch_uses_one_provider_call_and_one_guarded_completion(monkeypatch):
    import json

    from test_strategy_models import envelope

    worker, analysis, _, gateway, job, _ = setup_worker(monkeypatch)
    gateway.generate.return_value = json.dumps(envelope())
    analysis.complete.return_value = False
    asyncio.run(worker.cycle())
    gateway.generate.assert_awaited_once()
    assert len(analysis.complete.call_args.args) == 4
    assert analysis.complete.call_count == 1
    # No second, unconditional persistence or action hook follows rejected completion.
    assert worker.strategy is None
