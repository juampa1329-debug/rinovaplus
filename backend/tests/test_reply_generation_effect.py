"""Exercise scheduling against the real provider-operation uniqueness contract."""

import hashlib
import json
import sqlite3
from uuid import uuid4

from app.institutional import whatsapp_gemini as replies


def test_guarded_generations_have_distinct_effects_and_stable_operation_dedupe(
    monkeypatch,
):
    inst, app, integration, conversation, identity, incoming = [
        str(uuid4()) for _ in range(6)
    ]
    connection = sqlite3.connect(":memory:")
    connection.execute("ATTACH DATABASE ':memory:' AS crm_channels2")
    connection.execute("""CREATE TABLE crm_channels2.ProviderOperation(
        InstitutionId,OperationId,ApplicationId,IntegrationId,ActorRef,Action,
        RequestDigest,EffectKey,Status,ResultMetadata,CreatedAt,
        PRIMARY KEY(InstitutionId,OperationId),
        UNIQUE(InstitutionId,ApplicationId,Action,EffectKey))""")

    class Cursor:
        def execute(self, sql, *params):
            return connection.execute(
                sql.replace("INSERT crm_channels2.", "INSERT INTO crm_channels2.")
                .replace(" WITH(UPDLOCK,HOLDLOCK)", "")
                .replace("SYSUTCDATETIME()", "'2026-11-26'"),
                params,
            )

    monkeypatch.setattr(replies, "available", lambda *args: True)
    monkeypatch.setattr(
        replies,
        "configuration",
        lambda *args: {
            "OutboundEnabled": True,
            "ModuleEnabled": True,
        },
    )
    monkeypatch.setattr(
        replies,
        "setting",
        lambda *args: {
            "document": {"daily_messages": 1000, "enabled": True},
        },
    )
    monkeypatch.setattr(replies, "institution", lambda *args: inst)
    monkeypatch.setattr(replies, "one", lambda *args: {"Epoch": 7})
    monkeypatch.setattr(
        replies,
        "bound_hash",
        lambda _s, data, purpose: hashlib.sha256(
            (purpose + json.dumps(data, sort_keys=True)).encode()
        ).digest(),
    )
    item = {"ApplicationId": app, "IntegrationId": integration, "Channel": "whatsapp"}
    linked = {"ConversationId": conversation, "IdentityId": identity}
    try:
        operations = [None, str(uuid4()), str(uuid4())]
        for operation in operations:
            for _ in range(2):
                replies.schedule(
                    Cursor(), None, item, linked, incoming, operation_id=operation
                )
        records = connection.execute(
            "SELECT OperationId,RequestDigest,EffectKey,ResultMetadata "
            "FROM crm_channels2.ProviderOperation"
        ).fetchall()
        assert len(records) == 3
        assert len({r[1] for r in records}) == 1
        assert len({r[2] for r in records}) == 3
        assert records[0][1] == records[0][2]  # Original effect key stays historical.
        assert {json.loads(r[3])["incoming"] for r in records} == {incoming}
        # A human takeover still prevents another operation before any insert.
        monkeypatch.setattr(replies, "one", lambda *args: None)
        replies.schedule(
            Cursor(), None, item, linked, incoming, operation_id=str(uuid4())
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM crm_channels2.ProviderOperation"
            ).fetchone()[0]
            == 3
        )
    finally:
        connection.close()
