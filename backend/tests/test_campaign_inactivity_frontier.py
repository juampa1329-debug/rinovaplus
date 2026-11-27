import json
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from pglast import parse_sql

from app.institutional import campaign_runtime as runtime
from app.institutional.operations_policy import layout
from app.institutional.postgres_dialect import postgres_sql


@pytest.mark.parametrize("followup_only", [True, False])
@pytest.mark.parametrize("changed", [True, False])
def test_inactivity_discovers_readonly_and_rechecks_exact_job_under_write_lock(monkeypatch, followup_only, changed):
    settings = SimpleNamespace()
    selected_trigger, selected_queue, identity = [str(uuid4()) for _ in range(3)]
    trigger = {"RecordId": selected_trigger, "CurrentVersion": 2,
               "Document": json.dumps({"flow_id": "flow", "idle_minutes": 60})}
    job = {"QueueId": selected_queue, "IdentityId": identity,
           "ObservedAt": __import__("datetime").datetime(2026, 11, 26)}
    accesses, queries, writes = [], [], []
    @contextmanager
    def transaction(s, write=False, **kwargs):
        accesses.append(write)
        yield SimpleNamespace(write=write)
    monkeypatch.setattr(runtime, "transaction", transaction)
    monkeypatch.setattr(runtime, "institution", lambda _: "inst")
    monkeypatch.setattr(runtime, "enabled", lambda *_: True)
    monkeypatch.setattr(runtime, "authority", lambda *_: None)
    monkeypatch.setattr(runtime, "get", lambda *_: {"Document": json.dumps({"integration_id": "account", "followup_only": followup_only})})
    monkeypatch.setattr(runtime, "person", lambda *_: {"IncomingText": "Contexto vigente"})
    monkeypatch.setattr(runtime, "snapshot", lambda p: p)
    def rows(c, sql, *args):
        assert sql.count("?") == len(args)
        if "EventType" in sql:
            return [{"EventType": "inactivity"}]
        if c.write:
            assert args == ("inst", selected_trigger) and "RecordId=?" in sql
        return [trigger]
    def one(c, sql, *args):
        assert sql.count("?") == len(args)
        parse_sql(postgres_sql(sql, layout()["tables"]).replace("%s", "NULL"))
        # A new trigger version cannot replay a receipt already used by the
        # same trigger. The signal retains its original version in history.
        receipt_fence = sql.split("e.Kind='signal'", 1)[1]
        assert "inactivity_queue_id" in receipt_fence
        assert "trigger_version" not in receipt_fence
        queries.append((c.write, sql))
        if c.write:
            assert "AND q.QueueId=? " in sql and args[2] == selected_queue
            return None if changed else job
        assert "AND q.QueueId=? " not in sql
        return job
    monkeypatch.setattr(runtime, "rows", rows)
    monkeypatch.setattr(runtime, "one", one)
    monkeypatch.setattr(runtime, "event", lambda c, *args, **kwargs: writes.append(c.write))
    worker = runtime.Worker(settings)
    worker.triggers = Mock()
    worker.maintenance()
    assert queries[0][0] is False and queries[1][0] is True
    assert writes == ([] if changed else [True])
    assert accesses == [False, False, True, True]
