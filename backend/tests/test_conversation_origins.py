"""An outbound comment becomes an active Inbox thread only on a real reply."""

import json
import sqlite3

from app.institutional.conversation_origins import (
    COMMENT_ORIGIN,
    COMMENT_PENDING,
    view_predicate,
)


def test_comment_view_separates_unanswered_outreach_and_promotes_real_replies():
    c = sqlite3.connect(":memory:")
    c.create_function(
        "JSON_VALUE",
        2,
        lambda value, path: extract(json.loads(value), path[2:].split(".")),
    )
    c.execute("ATTACH DATABASE ':memory:' AS crm")
    c.execute("ATTACH DATABASE ':memory:' AS crm_channels2")
    c.executescript("""
        CREATE TABLE crm.Conversation(ConversationId TEXT);
        CREATE TABLE crm.Message(MessageId TEXT,ConversationId TEXT,Direction TEXT,Body TEXT);
        CREATE TABLE crm_channels2.ExternalMessage(MessageId TEXT,InstitutionId TEXT,IntegrationId TEXT,Payload TEXT);
        CREATE TABLE crm_channels2.Integration(InstitutionId TEXT,IntegrationId TEXT,Channel TEXT);
        INSERT INTO crm_channels2.Integration VALUES('institution','page','messenger');
    """)

    def outgoing(thread, body, payload):
        c.execute("INSERT INTO crm.Conversation VALUES(?)", (thread,))
        c.execute(
            "INSERT INTO crm.Message VALUES(?,?,'outgoing',?)", (thread, thread, body)
        )
        c.execute(
            "INSERT INTO crm_channels2.ExternalMessage VALUES(?,'institution','page',?)",
            (thread, json.dumps(payload)),
        )

    outgoing("private", "Información solicitada", {"private_queue_id": "queue"})
    outgoing(
        "historical",
        "¡Hola! Gracias por comentar nuestro video de PRE-ICFES CBN. Información",
        {"meta_outgoing": True},
    )
    outgoing(
        "ordinary",
        "Información de PRE-ICFES",
        {
            "meta_outgoing": True,
            "comment_source": {
                "authority": "cbn-comment-private-v1",
                "comment_id": "private:import",
                "program_id": 1,
            },
        },
    )

    def visible(queue):
        return {
            row[0]
            for row in c.execute(
                "SELECT v.ConversationId FROM crm.Conversation v WHERE "
                + view_predicate(queue)
            )
        }

    assert visible("all") == {"ordinary"}
    assert visible("comment_pending") == {"private", "historical"}
    assert visible("comment_origin") == {"private", "historical"}
    # A customer's actual incoming message is sufficient: no stage/control write.
    c.execute(
        "INSERT INTO crm.Message VALUES('reply','private','incoming','Gracias, me interesa')"
    )
    assert visible("all") == {"ordinary", "private"}
    assert visible("comment_pending") == {"historical"}
    assert visible("comment_origin") == {"private", "historical"}
    assert c.execute("SELECT COUNT(*) FROM crm.Message").fetchone()[0] == 4


def extract(document, keys):
    value = document
    for key in keys:
        value = value.get(key) if isinstance(value, dict) else None
    return "true" if value is True else value


def test_origin_queries_translate_to_postgresql():
    from pglast import parse_sql
    from app.institutional.postgres_dialect import postgres_sql
    from app.institutional.operations_policy import layout

    for expression in (COMMENT_ORIGIN, COMMENT_PENDING):
        parse_sql(
            postgres_sql(
                "SELECT v.ConversationId FROM crm.Conversation v WHERE " + expression,
                layout()["tables"],
            )
        )
