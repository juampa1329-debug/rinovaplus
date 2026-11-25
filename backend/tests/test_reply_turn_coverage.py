"""Execute receipt coverage against adversarial histories, without a live DB."""
import json
import re
import sqlite3
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from pglast import parse_sql

from app.institutional import reply_turns
from app.institutional.operations_policy import layout
from app.institutional.postgres_dialect import postgres_sql


@pytest.mark.parametrize("states,expected", [
    (["accepted", "read"], 2), (["sent", "delivered"], 2),
    (["accepted", "queued"], 0), (["read", "uncertain"], 0),
    (["sent", "failed"], 0), (["accepted", "cancelled"], 0),
    ([], 0),
])
@pytest.mark.parametrize("foreign_state", ["accepted", "failed"])
def test_only_all_parts_of_same_identity_advance_pending_cursor(monkeypatch, states, expected, foreign_state):
    values = [str(uuid4()) for _ in range(7)]
    inst, integration, identity, conversation, incoming, operation, latest = values
    connection = sqlite3.connect(":memory:")
    connection.executescript("""
        ATTACH ':memory:' AS crm; ATTACH ':memory:' AS crm_channels2;
        CREATE TABLE crm.Message(MessageId TEXT,Sequence INT,ConversationId TEXT,Direction TEXT);
        CREATE TABLE crm_channels2.ProviderOperation(OperationId TEXT,InstitutionId TEXT,IntegrationId TEXT,Action TEXT,Status TEXT,ResultCode TEXT,ResultMetadata TEXT);
        CREATE TABLE crm_channels2.MessageRoute(MessageId TEXT,InstitutionId TEXT,IntegrationId TEXT,IdentityId TEXT,ActorKind TEXT,QueueId TEXT);
        CREATE TABLE crm_channels2.SendJob(InstitutionId TEXT,IntegrationId TEXT,IdentityId TEXT,Payload TEXT,State TEXT,QueueId TEXT);
    """)

    def safe_uuid(value):
        try:
            return str(UUID(value))
        except (ValueError, TypeError, AttributeError):
            return None
    connection.create_function("safe_uuid", 1, safe_uuid)
    connection.execute("INSERT INTO crm.Message VALUES(?,2,?,'incoming')", (incoming, conversation))
    connection.execute("INSERT INTO crm_channels2.MessageRoute VALUES(?,?,?,?,'external',NULL)", (incoming, inst, integration, identity))
    connection.execute("INSERT INTO crm_channels2.ProviderOperation VALUES(?,?,?,?,'confirmed',NULL,?)",
                       (operation, inst, integration, reply_turns.ACTION, json.dumps({"incoming": incoming})))
    for state in states:
        connection.execute("INSERT INTO crm_channels2.SendJob VALUES(?,?,?,?,?,?)",
                           (inst, integration, identity, json.dumps({"automationId": operation}), state, str(uuid4())))
    # A foreign identity/account/institution cannot establish or sabotage coverage.
    for changed in [(inst, integration, str(uuid4())), (inst, str(uuid4()), identity), (str(uuid4()), integration, identity)]:
        connection.execute("INSERT INTO crm_channels2.SendJob VALUES(?,?,?,?,?,?)",
                           (*changed, json.dumps({"automationId": operation}), foreign_state, str(uuid4())))
    connection.execute("INSERT INTO crm_channels2.SendJob VALUES(?,?,?,?,?,?)",
                       (inst, integration, identity, '{"automationId":"invalid"}', "uncertain", str(uuid4())))

    def one(_c, sql, *params):
        parse_sql(postgres_sql(sql, layout()["tables"]).replace("%s", "NULL"))
        sql = re.sub(r"TRY_CONVERT\(uniqueidentifier,JSON_VALUE\(([^,]+),('[^']+')\)\)",
                     r"safe_uuid(json_extract(\1,\2))", sql).replace("COUNT_BIG", "COUNT")
        row = connection.execute(sql, params).fetchone()
        return {"Sequence": row[0]}

    monkeypatch.setattr(reply_turns.db, "one", one)
    monkeypatch.setattr(reply_turns.db, "rows", lambda *_: [{"MessageId": latest, "Sequence": 5, "Body": "pregunta", "ExternalId": "new"}])
    settings = SimpleNamespace(ticket={"context": [[1, inst]]})
    data = dict(integration=integration, identity=identity, conversation=conversation, incoming=latest)
    assert reply_turns.snapshot(None, settings, data, {"Sequence": 5})["after_sequence"] == expected
    connection.execute("UPDATE crm_channels2.ProviderOperation SET ResultCode='reply_turn_no_response'")
    assert reply_turns.snapshot(None, settings, data, {"Sequence": 5})["after_sequence"] == 2
    connection.close()
