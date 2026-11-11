"""R2 boundary proof with synthetic values only; no SQL IO."""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from test_admissions import ReadCursor, Workspace

from app.modules.inbox.application.service import InboxRepository
from app.modules.inbox.application.operations import (
    AssignmentWrite,
    InboxOperations,
    PolicyWrite,
    TaskWrite,
    sla_status,
)

BASE = {"operationId": str(uuid4()), "expectedRevision": "0"}


@pytest.mark.parametrize("value", [None, 0, -1, 525601, "30", True])
def test_policy_requires_explicit_bounded_integer(value):
    with pytest.raises(ValidationError):
        PolicyWrite(**BASE, enabled=True, thresholdMinutes=value)


@pytest.mark.parametrize("date", ["2026-10-15T12:00:00", "invalid"])
def test_task_requires_timezone(date):
    with pytest.raises(ValidationError):
        TaskWrite(
            **BASE,
            title="Task",
            priority="normal",
            humanEmployeeId=None,
            dueAt=date,
            status="pending",
        )


def test_task_normalizes_bogota_utc():
    body = TaskWrite(
        **BASE,
        title=" Task ",
        priority="normal",
        humanEmployeeId=None,
        dueAt="2026-10-15T12:00:00-05:00",
        status="pending",
    )
    assert body.dueAt.hour == 17 and body.title == "Task"


@pytest.mark.parametrize(
    "enabled,state,started,seconds,expected",
    [
        (False, "open", True, 9999, "not_configured"),
        (True, "open", False, 9999, "no_incoming"),
        (True, "closed", True, 9999, "closed"),
        (True, "waiting", True, 59, "on_time"),
        (True, "waiting", True, 60, "overdue"),
        (True, "open", True, 61, "overdue"),
    ],
)
def test_sla_boundary_no_fabricated_start_or_waiting_pause(
    enabled, state, started, seconds, expected
):
    now = datetime.now(timezone.utc)
    assert (
        sla_status(
            enabled,
            1,
            state,
            now - timedelta(seconds=seconds) if started else None,
            now,
        )
        == expected
    )


def test_typed_filters_are_sql_predicates_before_paging(monkeypatch):
    monkeypatch.setattr(InboxOperations, "present", lambda _: True)
    monkeypatch.setattr(InboxOperations, "verify", staticmethod(lambda _: None))
    cursor = ReadCursor([[]])
    agent = str(uuid4())
    assert (
        InboxRepository(Workspace(cursor)).list(
            human_id=7, ai_id=agent, sla_filter="overdue", offset=5025
        )["items"]
        == []
    )
    sql, args = cursor.calls[0]
    for predicate in ["ia.HumanEmployeeId=?", "ia.AiAgentId=?", "sla.status=?"]:
        assert sql.index(predicate) < sql.index("OFFSET")
    assert args[-8:] == (7, 7, agent, agent, "overdue", "overdue", 5025, 26)
    assert "Sequence>COALESCE(replied.sequence,0)" in sql


def test_missing_schema_does_not_ignore_new_filters(monkeypatch):
    monkeypatch.setattr(InboxOperations, "present", lambda _: False)
    with pytest.raises(HTTPException) as error:
        InboxRepository(Workspace(ReadCursor([]))).list(human_id=7)
    assert error.value.status_code == 503


def test_assignment_replay_returns_original_revision_without_writing(monkeypatch):
    import hashlib
    import json

    body = AssignmentWrite(**BASE, humanEmployeeId=7, aiAgentId=str(uuid4()))
    key = str(uuid4())
    payload = body.model_dump(mode="json", exclude={"expectedRevision"})
    digest = hashlib.sha256(
        json.dumps(
            ["assignment", key, key, payload], sort_keys=True, separators=(",", ":")
        ).encode()
    ).digest()
    cursor = ReadCursor([[{"hash": digest, "revision": 9}]])
    monkeypatch.setattr(InboxOperations, "verify", staticmethod(lambda _: None))
    repo = InboxOperations(Workspace(cursor))
    repo.revision = Mock(side_effect=AssertionError("must not reread revision"))
    assert repo.mutate("assignment", key, body, key) == {"revision": "9"}
    assert len(cursor.calls) == 1
    cursor = ReadCursor([[{"hash": b"x" * 32, "revision": 9}]])
    with pytest.raises(HTTPException) as error:
        InboxOperations(Workspace(cursor)).mutate("assignment", key, body, key)
    assert error.value.status_code == 409
