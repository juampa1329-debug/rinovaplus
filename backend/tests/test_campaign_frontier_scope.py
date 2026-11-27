"""A single dispatch keeps full canonical-person guards without a full audience scan."""

import json
import sqlite3
from uuid import uuid4

from pglast import parse_sql

from app.institutional import broadcasts
from app.institutional.operations_policy import layout
from app.institutional.postgres_dialect import postgres_sql


def test_frontier_scope_retains_merged_sibling_identities_and_account_boundary(monkeypatch):
    con = sqlite3.connect(":memory:")
    for schema in ("crm", "crm_workspace", "crm_channels", "crm_channels2"):
        con.execute(f"ATTACH DATABASE ':memory:' AS {schema}")
    con.executescript("""
        CREATE TABLE crm_channels2.ExternalIdentity(InstitutionId TEXT,IntegrationId TEXT,IdentityId TEXT,ExternalId TEXT,ContactId TEXT,ConversationId TEXT,LastIncomingAt TEXT);
        CREATE TABLE crm.Conversation(ConversationId TEXT,ContactId TEXT,ControlMode TEXT,State TEXT);
        CREATE TABLE crm_workspace.Merge(SourceContactId TEXT,TargetContactId TEXT,Active INT);
        CREATE TABLE crm.Contact(ContactId TEXT,Tags TEXT);
        CREATE TABLE crm_channels.ConversationControl(ConversationId TEXT,Epoch INT);
    """)
    target, sibling, outsider, contact, merged = [str(uuid4()) for _ in range(5)]
    con.executemany("INSERT INTO crm.Contact VALUES(?, '')", [(contact,), (merged,)])
    for identity, owner in ((target, contact), (sibling, merged), (outsider, "other")):
        con.execute("INSERT INTO crm_channels2.ExternalIdentity VALUES('inst','account',?,'57300',?,?,'2026-11-26')", (identity, owner, identity))
        con.execute("INSERT INTO crm.Conversation VALUES(?,?,'ai','open')", (identity, owner))
    con.execute("INSERT INTO crm_workspace.Merge VALUES(?,?,1)", (merged, contact))
    calls = []
    monkeypatch.setattr(broadcasts, "institution", lambda _: "inst")

    def read(c, sql, *args):
        calls.append((sql, args))
        parse_sql(postgres_sql(sql, layout()["tables"]).replace("%s", "NULL"))
        cursor = con.execute(sql.replace("TOP(5001) ", ""), args)
        return [dict(zip([v[0] for v in cursor.description], row, strict=True)) for row in cursor.fetchall()]

    monkeypatch.setattr(broadcasts, "rows", read)
    doc = {"integration_id": "account", "filters": {}}
    result = broadcasts.candidate_rows(None, None, doc, target_identity=target)
    assert {row["IdentityId"] for row in result} == {target, sibling}
    assert all(row["ContactId"] == contact for row in result)
    assert broadcasts.candidate_rows(None, None, {**doc, "integration_id": "different"}, target_identity=target) == []
    assert calls[0][1] == ("inst", "account", "inst", "account", target)
    con.close()


def test_original_reviewed_filters_are_also_required(monkeypatch):
    captured = []
    monkeypatch.setattr(broadcasts, "institution", lambda _: "inst")
    monkeypatch.setattr(broadcasts, "rows", lambda c, sql, *args: captured.append((sql, args)) or [])
    target, contact = str(uuid4()), str(uuid4())
    broadcasts.candidate_rows(None, None, {"integration_id": "account", "filters": {
        "contact_ids": [contact], "identity_ids": [target], "stages": ["Seguimiento"]}}, target_identity=target)
    sql, args = captured[0]
    assert "p.ContactId IN" in sql and "i.IdentityId IN" in sql and "p.Stage IN" in sql
    assert args[-3:] == (json.dumps([contact]), json.dumps([target]), json.dumps(["Seguimiento"]))
