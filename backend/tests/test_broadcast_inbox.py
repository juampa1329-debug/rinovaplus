"""Outbound messages and delivery receipts do not promote campaign-only chats."""

import sqlite3

from app.institutional.broadcast_inbox import BROADCAST_PENDING


def test_campaign_only_thread_enters_inbox_on_actual_customer_message():
    c = sqlite3.connect(":memory:")
    for schema in ["crm", "crm_channels2", "crm_broadcast7"]:
        c.execute(f"ATTACH DATABASE ':memory:' AS {schema}")
    c.executescript("""
        CREATE TABLE crm.Conversation(ConversationId TEXT);
        CREATE TABLE crm.Message(MessageId TEXT,ConversationId TEXT,Direction TEXT);
        CREATE TABLE crm_channels2.SendJob(
            MessageId TEXT,InstitutionId TEXT,QueueId TEXT);
        CREATE TABLE crm_broadcast7.Attempt(InstitutionId TEXT,QueueId TEXT);
        INSERT INTO crm.Conversation VALUES('campaign'),('ordinary'),('active');
        INSERT INTO crm.Message VALUES('c','campaign','outgoing'),
            ('o','ordinary','outgoing'),('a','active','outgoing'),
            ('in','active','incoming');
        INSERT INTO crm_channels2.SendJob VALUES('c','i','q'),('a','i','qa');
        INSERT INTO crm_broadcast7.Attempt VALUES('i','q'),('i','qa');
    """)

    def visible():
        return {
            r[0]
            for r in c.execute(
                "SELECT v.ConversationId FROM crm.Conversation v WHERE NOT "
                + BROADCAST_PENDING
            )
        }

    assert visible() == {"ordinary", "active"}
    # An echo, a retry, or a receipt changes no inbound evidence.
    c.execute("INSERT INTO crm.Message VALUES('echo','campaign','outgoing')")
    assert visible() == {"ordinary", "active"}
    c.execute("INSERT INTO crm.Message VALUES('reply','campaign','incoming')")
    assert visible() == {"ordinary", "active", "campaign"}


def test_campaign_pending_query_translates_to_postgresql():
    from pglast import parse_sql

    from app.institutional.operations_policy import layout
    from app.institutional.postgres_dialect import postgres_sql

    parse_sql(
        postgres_sql(
            "SELECT v.ConversationId FROM crm.Conversation v WHERE NOT "
            + BROADCAST_PENDING,
            layout()["tables"],
        )
    )
