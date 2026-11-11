"""Bounded Inbox reads and compact writes without a database connection."""

from datetime import datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from test_admissions import ReadCursor, Workspace

from app.config import Settings
from app.main import create_app
from app.modules.inbox.application.service import InboxRepository


class InboxCursor(ReadCursor):
    def execute(self, sql, *args):
        if sql == "SELECT OBJECT_ID(N'crm_channels.ExternalIdentity')":
            self.result = [{"object_id": 1}]
            self.description = [("object_id",)]
            return self
        return super().execute(sql, *args)


@pytest.fixture(autouse=True)
def no_optional_operations(monkeypatch):
    monkeypatch.setattr(
        "app.modules.inbox.application.operations.InboxOperations.present",
        lambda cursor: False,
    )


def summary():
    return {
        "id": str(uuid4()).upper(),
        "clientId": str(uuid4()).upper(),
        "state": "open",
        "priority": "normal",
        "assignee": None,
        "createdAt": datetime(2026, 10, 15, 12),
    }


def test_server_filters_precede_page_and_snapshot_is_never_read():
    cursor = InboxCursor([[summary() for _ in range(26)]])
    workspace = Workspace(cursor)
    workspace.snapshot = Mock(side_effect=AssertionError("snapshot limit exceeded"))
    result = InboxRepository(workspace).list(
        "[%_' OR 1=1", "unknown", "open", "human", "assigned", "Operator", True, 5025
    )
    sql, args = cursor.calls[0]
    assert "WHERE" in sql and sql.index("c.State=?") < sql.index("OFFSET")
    assert "c.ControlMode=?" in sql and "LTRIM(RTRIM(c.Assignee))=?" in sql
    assert "c.Unread=1" in sql and "?='Local'" in sql
    assert "[%_' OR 1=1" not in sql and args[-2:] == (5025, 26)
    assert args[1] == "%[[][%][_]' OR 1=1%"
    assert len(result["items"]) == 25 and result["hasMore"]
    assert result["items"][0]["createdAt"] == "2026-10-15T12:00:00Z"
    assert result["items"][0]["id"] == result["items"][0]["id"].lower()
    workspace.snapshot.assert_not_called()


def test_empty_page_does_not_fall_back_to_any_population():
    assert InboxRepository(Workspace(InboxCursor([[]]))).list("absent")["items"] == []


def test_messages_have_thread_predicate_bigint_cursor_and_stable_ascending_order():
    identifier = str(uuid4())
    cursor = ReadCursor(
        [
            [{"id": identifier}],
            [
                {
                    "id": str(uuid4()),
                    "sequence": n,
                    "createdAt": datetime(2026, 10, 15),
                    "body": "test",
                    "direction": "incoming",
                    "mediaId": None,
                }
                for n in range(9007199254741090, 9007199254741039, -1)
            ],
        ]
    )
    result = InboxRepository(Workspace(cursor)).messages(identifier, 9007199254741091)
    sql, args = cursor.calls[-1]
    assert (
        "TOP(51)" in sql
        and "WHERE m.ConversationId=?" in sql
        and "ORDER BY m.Sequence DESC" in sql
    )
    assert args == (identifier, 9007199254741091, 9007199254741091)
    assert len(result["items"]) == 50 and result["hasMore"]
    assert result["before"] == "9007199254741041"
    assert [int(row["sequence"]) for row in result["items"]] == list(
        range(9007199254741041, 9007199254741091)
    )


def test_options_are_complete_persisted_assignments_not_page_membership():
    cursor = ReadCursor(
        [
            [{"id": str(uuid4())}],
            [{"label": f"Operator {n}"} for n in range(600)],
            [{"label": "Local"}],
        ]
    )
    result = InboxRepository(Workspace(cursor)).options()
    assert len(result["assignees"]) == 600 and result["channels"] == ["Local"]
    assert "OFFSET" not in cursor.calls[-1][0]


@pytest.mark.parametrize(
    "query",
    [
        "offset=-1",
        "offset=1000001",
        "state=invalid",
        "mode=invalid",
        "assignment=invalid",
        "q=" + "x" * 201,
    ],
)
def test_invalid_filters_fail_before_repository(query):
    app = create_app()
    app.state.settings = Settings(mode="local_sql_copy")
    app.state.inbox = Mock()
    with TestClient(
        app, base_url="http://127.0.0.1:8002", client=("127.0.0.1", 10)
    ) as client:
        response = client.get(
            "/api/local/crm/inbox?" + query, headers={"X-CRM-Local": "1"}
        )
    assert response.status_code == 422
    app.state.inbox.list.assert_not_called()
