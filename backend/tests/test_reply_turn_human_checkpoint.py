"""A known human answer closes old uncertainty without rewriting its receipt."""
import sqlite3
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pglast import parse_sql

from app.institutional import reply_turns
from app.institutional.operations_policy import layout
from app.institutional.postgres_dialect import postgres_sql


@pytest.mark.parametrize("change", [None, "queued_human", "uncertain_human", "foreign_institution", "foreign_account", "foreign_identity", "foreign_thread", "future_human", "older_human", "bot_answer"])
def test_old_uncertainty_only_yields_to_same_scope_accepted_human_checkpoint(monkeypatch, change):
    con = sqlite3.connect(":memory:")
    con.executescript("""
        ATTACH ':memory:' AS crm; ATTACH ':memory:' AS crm_channels2;
        CREATE TABLE crm.Message(MessageId TEXT,ConversationId TEXT,Sequence INT,Direction TEXT);
        CREATE TABLE crm_channels2.MessageRoute(MessageId TEXT,InstitutionId TEXT,IntegrationId TEXT,IdentityId TEXT,ActorKind TEXT,QueueId TEXT);
        CREATE TABLE crm_channels2.SendJob(InstitutionId TEXT,IntegrationId TEXT,QueueId TEXT,State TEXT);
        INSERT INTO crm.Message VALUES('old','thread',4,'outgoing'),('human','thread',8,'outgoing');
        INSERT INTO crm_channels2.MessageRoute VALUES('old','inst','account','identity','bot','q1'),('human','inst','account','identity','human','q2');
        INSERT INTO crm_channels2.SendJob VALUES('inst','account','q1','uncertain'),('inst','account','q2','delivered');
    """)
    if change in {"queued_human", "uncertain_human"}:
        con.execute("UPDATE crm_channels2.SendJob SET State=? WHERE QueueId='q2'", (change.split('_')[0],))
    elif change in {"foreign_institution", "foreign_account", "foreign_identity"}:
        column = {"foreign_institution": "InstitutionId", "foreign_account": "IntegrationId", "foreign_identity": "IdentityId"}[change]
        con.execute(f"UPDATE crm_channels2.MessageRoute SET {column}='other' WHERE MessageId='human'")
    elif change == "foreign_thread":
        con.execute("UPDATE crm.Message SET ConversationId='other' WHERE MessageId='human'")
    elif change in {"future_human", "older_human"}:
        con.execute("UPDATE crm.Message SET Sequence=? WHERE MessageId='human'", (12 if change == "future_human" else 2,))
    elif change == "bot_answer":
        con.execute("UPDATE crm_channels2.MessageRoute SET ActorKind='bot' WHERE MessageId='human'")
    def one(c, sql, *args):
        assert sql.count('?') == len(args)
        parse_sql(postgres_sql(sql, layout()["tables"]).replace('%s', 'NULL'))
        if 'ProviderOperation' in sql:
            return None
        row = con.execute(sql.replace('TOP(1) ', '') + ' LIMIT 1', args).fetchone()
        return {'State': row[0]} if row else None
    monkeypatch.setattr(reply_turns.db, 'one', one)
    monkeypatch.setattr(reply_turns.db, 'institution', lambda _: 'inst')
    data = dict(integration='account', identity='identity', conversation='thread')
    if change:
        with pytest.raises(HTTPException, match='reply_turn_delivery_uncertain'):
            reply_turns.require_settled(None, SimpleNamespace(), data, {'Sequence': 10})
    else:
        reply_turns.require_settled(None, SimpleNamespace(), data, {'Sequence': 10})
    assert con.execute("SELECT State FROM crm_channels2.SendJob WHERE QueueId='q1'").fetchone()[0] == 'uncertain'
    con.close()
