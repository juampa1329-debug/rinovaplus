import json
from types import SimpleNamespace
from uuid import uuid4

from pglast import parse_sql

from app.institutional import grounded_replies as replies
from app.institutional.operations_policy import layout
from app.institutional.postgres_dialect import postgres_sql


def test_rebuilt_turn_reads_only_accepted_parts_of_same_account_and_identity(monkeypatch):
    inst, integration, identity, conversation, accepted = [str(uuid4()) for _ in range(5)]
    settings = SimpleNamespace(ticket={"context": [[1, inst]]})
    monkeypatch.setattr(replies, "setting", lambda *_: {"document": {}, "revision": 1})
    monkeypatch.setattr(replies, "search", lambda *_: [])
    monkeypatch.setattr(replies, "effective", lambda *_: {"shared": [], "conversation": []})
    monkeypatch.setattr(replies, "Catalog", lambda *_: SimpleNamespace(read_context=lambda *_: {"material": {}}))
    statements = []

    def rows(_c, sql, *params):
        assert sql.count("?") == len(params)
        parse_sql(postgres_sql(sql, layout()["tables"]).replace("%s", "NULL"))
        assert params == (conversation, 5, accepted, inst, integration, identity)
        assert "acceptedRoute.InstitutionId=?" in sql and "acceptedRoute.IdentityId=?" in sql
        assert "acceptedRoute.IntegrationId=?" in sql and "acceptedRoute.ActorKind='bot'" in sql
        assert "acceptedJob.State IN('accepted','sent','delivered','read')" in sql
        statements.append(sql)
        return [{"MessageId": accepted, "Sequence": 6, "Direction": "outgoing", "Body": "Ya te expliqué el grupo del sábado por la mañana."},
                {"MessageId": str(uuid4()), "Sequence": 5, "Direction": "incoming", "Body": "¿Qué horarios tienen?"}]

    monkeypatch.setattr(replies, "rows", rows)
    result = replies.context(object(), settings, "¿Qué horarios tienen?", conversation=conversation, sequence=5,
                             accepted_continuation={"ids": [accepted], "integration": integration, "identity": identity})
    assert len(statements) == 1
    history = json.loads(result["query"])["historial"]
    assert history[-1]["direction"] == "outgoing" and "Ya te expliqué" in history[-1]["text"]
    # An accepted continuation never turns a private history into public context.
    statements.clear()
    result = replies.context(object(), settings, "Información", conversation=conversation, sequence=5, public=True,
                             accepted_continuation={"ids": [accepted], "integration": integration, "identity": identity})
    assert not statements and json.loads(result["query"])["historial"] == []
