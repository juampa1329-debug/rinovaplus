"""Real scoped receipt aggregation on synthetic SQL data; no provider IO."""

import json
import csv
import io
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pglast import parse_sql

from app.institutional.broadcast_report import projection
from app.institutional.postgres_dialect import postgres_sql


TABLES = {
    "crm_broadcast7.Recipient": "dbo.recipients",
    "crm.Contact": "dbo.contacts",
    "crm_workspace.Merge": "dbo.merges",
    "crm_channels2.ExternalIdentity": "dbo.identities",
    "crm_channels2.SendJob": "dbo.jobs",
    "crm_channels2.WebhookEvent": "dbo.events",
}


@pytest.fixture
def database():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("ATTACH ':memory:' AS rinovaplus_crm")
    db.executescript("""
      CREATE TABLE rinovaplus_crm.recipients(InstitutionId,RecipientId,IdentityId,Attempts,CurrentQueueId,ContactId,CampaignId,State,LastError,Snapshot,CreatedAt);
      CREATE TABLE rinovaplus_crm.contacts(ContactId PRIMARY KEY,Stage,Program,CustomValues,Name);
      CREATE TABLE rinovaplus_crm.merges(SourceContactId,TargetContactId,Active);
      CREATE TABLE rinovaplus_crm.identities(InstitutionId,IdentityId,ExternalId);
      CREATE TABLE rinovaplus_crm.jobs(InstitutionId,QueueId,IntegrationId,ExternalId,State,LastErrorCode,CreatedAt,CompletedAt);
      CREATE TABLE rinovaplus_crm.events(InstitutionId,IntegrationId,Kind,Status,Payload,CreatedAt);
    """)
    calls = []

    def scalar(value, path):
        calls.append(1)
        current = json.loads(value)
        for part in path.removeprefix("$.").split("."):
            current = current.get(part) if isinstance(current, dict) else None
        return current if isinstance(current, (str, int, float)) else None

    db.create_function("JSON_VALUE", 2, scalar)
    db.create_function(
        "POSITION", 2, lambda a, b: (b.find(a) + 1) if b is not None else None
    )
    db.create_function(
        "CHARINDEX", 2, lambda a, b: (b.find(a) + 1) if b is not None else None
    )

    def recipient(
        message="msg-a",
        *,
        campaign="campaign",
        account="wa-a",
        state="read",
        body="Consulta de ensayo",
    ):
        identity, person, row, queue = (str(uuid4()) for _ in range(4))
        phone = "573000000000" + str(
            db.execute("SELECT COUNT(*) FROM rinovaplus_crm.contacts").fetchone()[0]
        )
        db.execute(
            "INSERT INTO rinovaplus_crm.contacts VALUES(?,'Seguimiento','PRE-ICFES','{}','ENSAYO')",
            (person,),
        )
        db.execute(
            "INSERT INTO rinovaplus_crm.identities VALUES('org-a',?,?)",
            (identity, phone),
        )
        db.execute(
            "INSERT INTO rinovaplus_crm.jobs VALUES('org-a',?,?,?,?,NULL,'2026-11-25T09:58:00','2026-11-25T09:59:00')",
            (queue, account, message, state),
        )
        db.execute(
            "INSERT INTO rinovaplus_crm.recipients VALUES('org-a',?,?,1,?,? ,?,'queued',NULL,?,'2026-11-25T09:57:00')",
            (row, identity, queue, person, campaign, json.dumps({"body": body})),
        )
        return row, phone

    def event(
        payload,
        *,
        kind="status",
        account="wa-a",
        org="org-a",
        state="processed",
        at="2026-11-25T10:00:00",
    ):
        db.execute(
            "INSERT INTO rinovaplus_crm.events VALUES(?,?,?,?,?,?)",
            (org, account, kind, state, json.dumps(payload), at),
        )

    def execute(query, parameters):
        sql = postgres_sql(query, TABLES)
        parse_sql(sql.replace("%s", "NULL"))
        sql = query
        for name, target in TABLES.items():
            sql = sql.replace(name, "rinovaplus_crm." + target.split(".")[1])
        sql = sql.replace("COLLATE Latin1_General_100_BIN2", "COLLATE BINARY").replace(
            "ISNULL(", "COALESCE("
        )
        sql = sql.replace(
            " OFFSET ? ROWS FETCH NEXT 100 ROWS ONLY", " LIMIT 100 OFFSET ?"
        )
        sql = sql.replace(
            " OFFSET 0 ROWS FETCH NEXT 5001 ROWS ONLY", " LIMIT 5001 OFFSET 0"
        )
        return [dict(v) for v in db.execute(sql, parameters)]

    def read(
        *,
        state="",
        search="",
        suffix="SELECT * FROM filtered ORDER BY PreparedAt,RecipientId",
        materialized=False,
    ):
        # SQLite executes the original joins/CTEs with equivalent scalar functions;
        # the production PostgreSQL form is independently parsed above.
        return execute(
            projection(materialized=materialized) + suffix,
            (
                "org-a",
                "campaign",
                state,
                state,
                state,
                search,
                search,
                search,
                search,
            ),
        )

    read.execute = execute
    yield recipient, event, read, calls
    db.close()


def test_report_requires_processed_receipt_exact_account_message_and_reply_author(
    database,
):
    recipient, event, read, _ = database
    row, phone = recipient()
    recipient("another", campaign="other-campaign")
    event({"external": "msg-a", "text": "sent"})
    event({"external": "msg-a", "text": "delivered"}, at="2026-11-25T10:01:00")
    event({"external": "msg-a", "text": "delivered"}, at="2026-11-25T10:03:00")
    for invalid in ({"account": "wa-b"}, {"org": "org-b"}, {"state": "quarantined"}):
        event({"external": "msg-a", "text": "read"}, **invalid)
    event({"external": "MSG-A", "text": "read"})
    event({"provider": {"context": {"id": "msg-a"}}, "author": "other"}, kind="message")
    event({"provider": {"context": {"id": "other"}}, "author": phone}, kind="message")
    event({"text": "I replied to msg-a", "author": phone}, kind="message")
    found = read()
    assert len(found) == 1 and found[0]["RecipientId"] == row
    assert found[0]["SentAt"] == "2026-11-25T10:00:00"
    assert found[0]["DeliveredAt"] == "2026-11-25T10:01:00"
    assert found[0]["ReadAt"] is None and found[0]["RepliedAt"] is None
    assert read(state="replied") == []
    event(
        {"provider": {"context": {"id": "msg-a"}}, "author": phone},
        kind="message",
        at="2026-11-25T10:04:00",
    )
    assert read(state="replied")[0]["RepliedAt"] == "2026-11-25T10:04:00"


def test_report_keeps_acceptance_distinct_from_delivery_and_filter_counts(database):
    recipient, event, read, _ = database
    recipient("accepted", state="accepted", body="Mensaje sobre Inglés")
    recipient(None, state="queued", body="Otra consulta")
    event({"external": "other", "text": "delivered"})
    found = read()
    accepted = next(v for v in found if v["Status"] == "accepted")
    queued = next(v for v in found if v["Status"] == "queued")
    assert accepted["AcceptedAt"] is not None and accepted["DeliveredAt"] is None
    assert queued["AcceptedAt"] is None and queued["ReadAt"] is None
    assert len(read(search="Inglés")) == 1
    assert len(read(state="queued")) == 1
    counts = read(
        suffix="SELECT Status,COUNT(*) AS Total,SUM(CASE WHEN RepliedAt IS NOT NULL THEN 1 ELSE 0 END) AS Replied FROM filtered GROUP BY Status"
    )
    assert sum(v["Total"] for v in counts) == 2
    assert sum(v["Replied"] for v in counts) == 0


def test_report_json_work_scales_with_events_not_recipients_times_events(database):
    recipient, event, read, calls = database
    for number in range(100):
        recipient(f"m-{number}")
        event({"external": f"m-{number}", "text": "delivered"})
    for number in range(500):
        event({"external": f"unrelated-{number}", "text": "sent"})
    calls.clear()
    found = read(materialized=True)
    assert len(found) == 100 and all(v["DeliveredAt"] for v in found)
    # A per-recipient scan would perform at least 100*600 JSON reads.
    assert len(calls) < 600 * 8 + 100 * 5


def test_service_preserves_pagination_graphs_and_complete_csv(database, monkeypatch):
    from app.institutional import broadcasts

    recipient, event, read, _ = database
    for number in range(101):
        _, phone = recipient(
            f"m-{number}", state="delivered" if number == 0 else "accepted"
        )
        if number == 0:
            event({"external": "m-0", "text": "delivered"})
            event(
                {"provider": {"context": {"id": "m-0"}}, "author": phone},
                kind="message",
            )

    @contextmanager
    def tx(*args, **kwargs):
        yield SimpleNamespace(dialect="postgresql"), {}

    campaign = dict(
        CampaignId=str(uuid4()),
        Name="ENSAYO",
        State="completed",
        Revision=1,
        Epoch=1,
        IntegrationId=str(uuid4()),
        TemplateId=str(uuid4()),
        TemplateVersion=1,
        Document="{}",
        ScheduledAt=None,
        Timezone="America/Bogota",
    )

    def rows(_, query, *parameters):
        found = read.execute(query, parameters)
        return [
            {
                k: datetime.fromisoformat(v)
                if k.endswith("At") and isinstance(v, str)
                else v
                for k, v in row.items()
            }
            for row in found
        ]

    monkeypatch.setattr(broadcasts.Broadcasts, "tx", tx)
    monkeypatch.setattr(broadcasts, "current", lambda *a: campaign)
    monkeypatch.setattr(broadcasts, "institution", lambda *a: "org-a")
    monkeypatch.setattr(broadcasts, "rows", rows)
    monkeypatch.setattr(broadcasts.templates, "latest", lambda *a: {"Definition": "[]"})
    service = broadcasts.Broadcasts(SimpleNamespace())
    report = service.report(None, "campaign", include_analytics=True)
    assert report["total"] == 101 and len(report["items"]) == 100 and report["has_more"]
    assert (
        report["metrics"]["replied"] == 1
        and report["analytics"]["totals"]["delivered"] == 1
    )
    last_page = service.report(None, "campaign", offset=100)
    assert len(last_page["items"]) == 1 and not last_page["has_more"]
    assert len(list(csv.reader(io.StringIO(service.export(None, "campaign"))))) == 102
