"""Activity boundaries and pagination contracts without database/provider IO."""

import base64
from datetime import date, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from test_admissions import ReadCursor, Workspace

from app.config import Settings
from app.modules.contacts.application.activity import (
    ActivityCursor,
    ContactActivity,
    activity_sql,
    date_bounds,
    scope_key,
)
from app.main import create_app


def summary():
    return {
        "calculatedAt": "2026-10-16T12:00:00.0000000Z",
        "messages": 2,
        "incoming": 0,
        "outgoing": 2,
        "lastMessageAt": "2026-10-16T11:00:00.0000001Z",
        "pendingTasks": 0,
        "completedTasks": 0,
        "cancelledTasks": 0,
        "overdueTasks": 0,
        "slaStatus": "not_configured",
        "slaStartedAt": None,
        "slaDueAt": None,
    }


def entry():
    return {
        "sourceRank": 0,
        "sourceId": str(uuid4()),
        "occurredAt": "2026-10-16T11:00:00.0000000Z",
        "kind": "contact",
        "action": "edit_contact",
        "actor": "local-operator",
        "direction": None,
    }


def repository(monkeypatch, page, optional=True):
    monkeypatch.setattr(
        "app.modules.contacts.application.activity.InboxOperations.present", lambda c: optional
    )
    monkeypatch.setattr("app.modules.contacts.application.activity.InboxOperations.verify", lambda c: None)
    cursor = ReadCursor(
        [
            [{"conversation": str(uuid4())}],
            [{"crm": 10, "inbox": 3, "message": 2}],
            page,
            [summary()],
        ]
    )
    return ContactActivity(Workspace(cursor)), cursor


def test_cursor_retains_all_seven_digits_including_zero_and_hundred_nanoseconds():
    for fraction in ["0000000", "0000001", "9999999"]:
        cursor = ActivityCursor(
            scope="a" * 64,
            crm=10,
            inbox=3,
            message=2,
            at="2026-10-16T11:00:00." + fraction + "Z",
            rank=1,
            sourceId=str(uuid4()),
        )
        assert ActivityCursor.decode(cursor.encode()) == cursor
        assert cursor.at.endswith(fraction + "Z")


@pytest.mark.parametrize(
    "token", ["!invalid", "e30", base64.urlsafe_b64encode(b'{"version":2}').decode()]
)
def test_bad_cursor_is_sanitized(token):
    with pytest.raises(HTTPException) as failure:
        ActivityCursor.decode(token)
    assert failure.value.status_code == 422


@pytest.mark.parametrize(
    "changes",
    [
        {"at": "2026-02-30T00:00:00.0000000Z"},
        {"rank": 5},
        {"crm": -1},
        {"sourceId": "bad"},
        {"at": "2026-01-01T00:00:00.000001Z"},
    ],
)
def test_cursor_fields_are_strict(changes):
    with pytest.raises(ValidationError):
        ActivityCursor(
            **(
                {
                    "scope": "a" * 64,
                    "crm": 1,
                    "inbox": 1,
                    "message": 1,
                    "at": "2026-01-01T00:00:00.0000000Z",
                    "rank": 0,
                    "sourceId": str(uuid4()),
                }
                | changes
            )
        )


def test_bogota_dates_use_inclusive_start_and_exclusive_next_day():
    start, end = date_bounds(date(2026, 10, 16), date(2026, 10, 16))
    assert start == datetime(2026, 10, 16, 5) and end == datetime(2026, 10, 17, 5)
    assert date_bounds(None, None) == (None, None)
    for dates in [(date(2026, 10, 17), date(2026, 10, 16)), (None, date.max)]:
        with pytest.raises(HTTPException):
            date_bounds(*dates)


def test_scope_bound_cursor_cannot_be_reused_for_other_contact_or_filters():
    own = str(uuid4())
    scope = scope_key(own, "all", None, None)
    cursor = ActivityCursor(
        scope=scope,
        crm=1,
        inbox=1,
        message=1,
        at="2026-01-01T00:00:00.0000000Z",
        rank=0,
        sourceId=str(uuid4()),
    ).encode()
    for contact, kind in [(str(uuid4()), "all"), (own, "message")]:
        with pytest.raises(HTTPException) as failure:
            ContactActivity(None).read(contact, kind, token=cursor)
        assert failure.value.status_code == 422


def test_page_is_bounded_metrics_are_unfiltered_and_cursor_has_source_watermarks(
    monkeypatch,
):
    store, cursor = repository(monkeypatch, [entry() for _ in range(26)])
    contact = str(uuid4())
    page = store.read(contact, "contact", date(2026, 10, 16), date(2026, 10, 16))
    assert len(page["items"]) == 25 and page["hasMore"]
    decoded = ActivityCursor.decode(page["nextCursor"])
    assert (decoded.crm, decoded.inbox, decoded.message) == (10, 3, 2)
    assert decoded.at == page["items"][-1]["occurredAt"]
    assert page["metrics"]["messages"]["messages"] == 2
    assert page["metrics"]["sla"]["status"] == "not_configured"
    sql, args = cursor.calls[2]
    assert (
        args[0] == contact
        and args[5] == "contact"
        and args[6:8] == (datetime(2026, 10, 16, 5), datetime(2026, 10, 17, 5))
    )
    assert "TOP(26)" in sql and "OFFSET" not in sql
    assert "Latin1_General_100_BIN2" in sql
    assert not any(
        word in sql for word in ["Body", "PayloadHash", "ResponseJson", "CapturedAt"]
    )
    assert "@kind" not in cursor.calls[3][0]
    assert all(
        not s.lstrip().startswith(("INSERT", "UPDATE", "DELETE", "CREATE"))
        for s, _ in cursor.calls
    )


def test_next_page_binds_original_fraction_and_limits_not_current_maximum(monkeypatch):
    contact = str(uuid4())
    token = ActivityCursor(
        scope=scope_key(contact, "all", None, None),
        crm=4,
        inbox=1,
        message=1,
        at="2026-01-01T00:00:00.0000001Z",
        rank=1,
        sourceId=str(uuid4()),
    )
    store, sql = repository(monkeypatch, [])
    page = store.read(contact, token=token.encode())
    assert not page["hasMore"] and page["nextCursor"] is None
    assert sql.calls[2][1][2:5] == (4, 1, 1)
    assert sql.calls[2][1][-6:-3] == (token.at[:-1], 1, token.sourceId)


def test_future_watermark_rejected_and_missing_optional_source_is_unavailable(
    monkeypatch,
):
    contact = str(uuid4())
    store, _ = repository(monkeypatch, [])
    token = ActivityCursor(
        scope=scope_key(contact, "all", None, None),
        crm=11,
        inbox=1,
        message=1,
        at="2026-01-01T00:00:00.0000000Z",
        rank=1,
        sourceId=str(uuid4()),
    )
    with pytest.raises(HTTPException):
        store.read(contact, token=token.encode())
    store, sql = repository(monkeypatch, [], optional=False)
    page = store.read(contact)
    assert (
        page["metrics"]["tasks"] is None
        and page["metrics"]["sla"]["status"] == "unavailable"
    )
    assert not page["historyScope"]["inboxAvailable"]
    assert "crm_inbox" not in sql.calls[2][0]


def test_dedup_requires_available_primary_within_the_same_cut():
    sql = activity_sql(True)
    assert "i.OperationId=o.OperationId" in sql and "i.Revision<=@inbox" in sql
    assert "m.MessageId=o.MessageId" in sql and "m.Sequence<=@message" in sql
    assert "TRY_CONVERT(uniqueidentifier,i.EntityKey)=o.ConversationId" in sql


def test_route_validation_and_read_boundary():
    app = create_app()
    app.state.settings = Settings(mode="local_sql_copy")

    class ReadOnly:
        def read(self, *args):
            return {"items": [], "metrics": {}, "hasMore": False}

    app.state.contact_activity = ReadOnly()
    client = TestClient(app, base_url="http://127.0.0.1:8002", client=("127.0.0.1", 20))
    root = "/api/local/crm/clients/" + str(uuid4()) + "/activity"
    response = client.get(root, headers={"X-CRM-Local": "1"})
    assert (
        response.status_code == 200 and response.headers["cache-control"] == "no-store"
    )
    for query in ["?kind=bad", "?fromDate=not-a-date", "?cursor=" + "x" * 1025]:
        assert client.get(root + query, headers={"X-CRM-Local": "1"}).status_code == 422
    assert client.get(root).status_code == 403
    assert client.post(root, json={}, headers={"X-CRM-Local": "1"}).status_code == 405
