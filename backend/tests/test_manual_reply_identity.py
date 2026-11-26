"""A manual reply must follow the current channel identity, not a legacy row."""
import sqlite3
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.institutional import channel_workspace as workspace


@pytest.mark.parametrize("reverse", [False, True])
def test_manual_reply_selects_recent_identity_and_preserves_human_guard(monkeypatch, reverse):
    institution, conversation, contact = [str(uuid4()) for _ in range(3)]
    stale, recent, foreign = [str(uuid4()) for _ in range(3)]
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE identities(InstitutionId TEXT,ConversationId TEXT,ContactId TEXT,IdentityId TEXT,IntegrationId TEXT,LastIncomingAt TEXT)")
    rows = [
        (institution, conversation, contact, stale, "old-account", None),
        (institution, conversation, contact, recent, "current-account", "2026-11-25 22:18:00"),
        ("other-institution", conversation, contact, foreign, "foreign-account", "2026-11-25 23:18:00"),
    ]
    conn.executemany("INSERT INTO identities VALUES(?,?,?,?,?,?)", rows[::-1] if reverse else rows)
    queries = []
    def one(cursor, sql, *args):
        queries.append(sql)
        sql = sql.replace("SELECT TOP(1)", "SELECT").replace("crm_channels2.ExternalIdentity", "identities") + " LIMIT 1"
        return dict(conn.execute(sql, args).fetchone())
    monkeypatch.setattr(workspace.db, "one", one)
    monkeypatch.setattr(workspace.db, "institution", lambda _: institution)
    monkeypatch.setattr(workspace, "account", lambda c, s, account: {"IntegrationId": account})
    monkeypatch.setattr(workspace, "authorize", lambda *_: {"UserId": "actor"})
    enqueued = []
    monkeypatch.setattr(workspace, "enqueue", lambda *args, **kwargs: enqueued.append((args, kwargs)) or str(uuid4()))
    cursor = SimpleNamespace(execute=lambda *_: None)
    service = object.__new__(workspace.Workspace)
    service.profile = SimpleNamespace()
    service.exists = lambda *_: (contact, "open", "human")
    body = SimpleNamespace(body="Respuesta revisada", operationId=uuid4(), mediaId=None)
    result = service.apply(cursor, "message", conversation, body, "actor")
    assert result["deliveryState"] == "queued"
    assert enqueued[0][1]["identity"] == recent
    assert enqueued[0][0][2]["IntegrationId"] == "current-account"
    # PostgreSQL DESC puts NULLs first by default; an explicit null rank is
    # required so both SQL dialects select the same authenticated recipient.
    assert "CASE WHEN LastIncomingAt IS NULL THEN 1 ELSE 0 END" in queries[0]
    service.exists = lambda *_: (contact, "open", "ai")
    with pytest.raises(HTTPException, match="human_open_conversation_required"):
        service.apply(cursor, "message", conversation, body, "actor")
    assert len(enqueued) == 1
    conn.close()
