import copy
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pglast import parse_sql

from app.institutional import channel_edits, channel_events, channel_workspace, reply_turns
from app.institutional.operations_policy import layout
from app.institutional.postgres_dialect import postgres_sql


def payload(text="¿El volante es por el abono?", original="wamid.original"):
    return {"entry": [{"id": "waba", "changes": [{"field": "messages", "value": {
        "messaging_product": "whatsapp", "metadata": {"phone_number_id": "account"},
        "messages": [{"id": "wamid.edit", "from": "sender", "type": "edit", "timestamp": "1795650000",
                      "edit": {"original_message_id": original, "message": {"type": "text", "text": {"body": text}}}}]}}]}]}


def test_edit_retains_exact_reference_and_new_text_without_granting_provider_control():
    raw = payload()
    raw["entry"][0]["changes"][0]["value"]["messages"][0]["edit"]["_crm"] = {"admin": True}
    value = channel_events.normalize("meta", raw)[0]
    assert channel_edits.reference(value["provider"]) == {"external": "wamid.original", "text": "¿El volante es por el abono?"}
    assert "_crm" not in json.dumps(value)
    assert channel_events.replyable_message("whatsapp", value["provider"])
    stopped = channel_events.normalize("meta", payload("No recibir mensajes"))[0]
    assert not channel_events.replyable_message("whatsapp", stopped["provider"])


@pytest.mark.parametrize("edit", [None, {}, {"original_message_id": "wrong\n", "message": {}},
    {"original_message_id": "wamid.original", "message": {"text": {"body": ""}}},
    {"original_message_id": "wamid.original", "message": {"text": {"body": "x" * 4001}}}])
def test_incomplete_edit_never_becomes_a_replyable_question(edit):
    provider = {"type": "edit", "edit": edit}
    assert channel_edits.reference(provider) is None
    assert not channel_events.replyable_message("whatsapp", provider)


def test_old_edit_recovers_only_from_matching_authenticated_receipt(monkeypatch):
    saved = channel_events.normalize("meta", payload())[0]
    legacy = copy.deepcopy(saved)
    legacy["provider"].pop("edit")
    monkeypatch.setattr(channel_edits, "key", lambda _: b"fixture")
    monkeypatch.setattr(channel_edits, "body_owner", lambda *_: {})
    monkeypatch.setattr(channel_edits, "unseal", lambda *_: json.dumps(payload()))
    receipt = {"ReceiptId": str(uuid4()), "EndpointId": str(uuid4()), "BodyCiphertext": b"cipher", "BodyNonce": b"nonce"}
    assert channel_edits.reference(channel_edits.recovered_provider(legacy, receipt, None))
    for field in ("channel", "route", "kind", "external", "author"):
        assert channel_edits.recovered_provider({**legacy, field: "other"}, receipt, None) == legacy["provider"]
    assert channel_edits.recovered_provider(legacy, {}, None) == legacy["provider"]


@pytest.mark.parametrize("matches", [0, 1, 2])
def test_edit_projection_requires_unique_same_incoming_identity_and_preserves_original(monkeypatch, matches):
    inst, conversation, message, integration, identity, original = [str(uuid4()) for _ in range(6)]
    settings = SimpleNamespace(ticket={"context": [[1, inst]]})
    source = {"MessageId": message, "IntegrationId": integration, "IdentityId": identity,
              "Payload": json.dumps(channel_events.normalize("meta", payload())[0])}
    queries = []
    def read(_c, sql, *args):
        assert sql.count("?") == len(args)
        parse_sql(postgres_sql(sql, layout()["tables"]).replace("%s", "NULL"))
        queries.append((sql, args))
        return [source] if len(queries) == 1 else [{"MessageId": original, "Body": "¿Sale completo?", "Direction": "incoming"}] * matches
    monkeypatch.setattr(channel_edits, "rows", read)
    value = channel_edits.project(None, settings, conversation, [{"id": message, "body": "[edit]", "direction": "incoming"}])[message]
    assert "w.Authentication='verified'" in queries[0][0]
    assert "r.ActorKind='external'" in queries[1][0] and "m.Direction='incoming'" in queries[1][0]
    assert queries[1][1] == (inst, integration, identity, conversation, "wamid.original")
    assert value["messageEdit"]["verified"] == (matches == 1)
    if matches == 1:
        assert value["body"] == "¿El volante es por el abono?" and value["replyTo"]["body"] == "¿Sale completo?"
    else:
        assert "replyTo" not in value and "abono" not in value["body"]


def test_edit_history_keeps_current_event_identity_and_points_quote_to_original(monkeypatch):
    message, original = str(uuid4()), str(uuid4())
    monkeypatch.setattr(channel_edits, "project", lambda *_: {message: {"body": "Prefiero G2", "messageEdit": {"verified": True},
        "replyTo": {"id": original, "body": "Prefiero G1"}, "editTargetExternal": "wamid.original"}})
    original_input = [{"MessageId": message, "Direction": "incoming", "Body": "[edit]", "ExternalId": "wamid.edit"}]
    value = channel_edits.history(None, None, "scope", original_input)[0]
    assert value["MessageId"] == message and value["edit_target_id"] == original
    assert value["ExternalId"] == "wamid.original" and "reemplaza" in value["Body"]
    assert "Prefiero G2" in value["Body"] and original_input[0]["Body"] == "[edit]"


@pytest.mark.parametrize("text,matches,scheduled", [("Prefiero G2", 1, True), ("No recibir mensajes", 1, False), ("Prefiero G2", 0, False)])
def test_new_edit_creates_separate_attributable_input_without_overwriting_original(monkeypatch, text, matches, scheduled):
    from app.institutional import channel_media, comment_private, whatsapp_gemini
    inst, integration, conversation, identity, contact = [str(uuid4()) for _ in range(5)]
    settings = SimpleNamespace(ticket={"context": [[1, inst]], "version": "fixture"})
    item = {"Channel": "whatsapp", "IntegrationId": integration}
    linked = {"IdentityId": identity, "ContactId": contact, "ConversationId": conversation}
    statements = []
    class Cursor:
        def execute(self, sql, *args):
            statements.append((sql, args))
            self.duplicate = sql.startswith("SELECT 1 FROM crm_channels2.ExternalMessage")
            return self
        def fetchone(self):
            return None if self.duplicate else (1,)
    monkeypatch.setattr(channel_events, "one", lambda *_: linked)
    monkeypatch.setattr(channel_edits, "targets", lambda *_: ["verified"] * matches)
    monkeypatch.setattr(channel_media, "register_incoming", lambda *_: None)
    monkeypatch.setattr(comment_private, "incoming_source", lambda *_: None)
    calls = []
    monkeypatch.setattr(whatsapp_gemini, "schedule", lambda *args, **kwargs: calls.append((args, kwargs)))
    channel_events.incoming(Cursor(), settings, item, channel_events.normalize("meta", payload(text))[0])
    inserted = next(args for sql, args in statements if sql.startswith("INSERT crm.Message"))
    assert inserted[2] == (text if matches == 1 else "[edit]")
    assert bool(calls) == scheduled
    assert not any(sql.startswith("UPDATE crm.Message") for sql, _ in statements)


def test_pending_edit_quotes_verified_original_but_fences_the_current_event(monkeypatch):
    inst, integration, conversation, identity, message, original = [str(uuid4()) for _ in range(6)]
    settings = SimpleNamespace(ticket={"context": [[1, inst]]})
    data = {"integration": integration, "conversation": conversation, "identity": identity, "incoming": message}
    incoming = [{"MessageId": message, "Direction": "incoming", "Body": "Prefiero G2", "Sequence": 5, "ExternalId": "wamid.edit"}]
    monkeypatch.setattr(reply_turns.db, "one", lambda *_: {"Sequence": 0})
    monkeypatch.setattr(reply_turns.db, "rows", lambda *_: incoming)
    cursor = SimpleNamespace(audio_history=lambda _, values: [{**values[0], "edit_target_id": original, "ExternalId": "wamid.original"}])
    value = reply_turns.snapshot(cursor, settings, data, {"Sequence": 5})
    assert value["incoming_ids"] == [message]
    assert value["quote_incoming"] == original and value["quote_external"] == "wamid.original"


def test_list_sender_uses_actual_operation_actor_not_current_assignee(monkeypatch):
    inst = str(uuid4())
    conversations = [str(uuid4()) for _ in range(5)]
    settings = SimpleNamespace(ticket={"context": [[1, inst]]})
    rows = [
        {"ConversationId": conversations[0], "Direction": "outgoing", "ActorKind": "bot", "DisplayName": None, "Origin": "gemini_whatsapp"},
        {"ConversationId": conversations[1], "Direction": "outgoing", "ActorKind": "human", "DisplayName": "Juan Pablo Mora", "Origin": None},
        {"ConversationId": conversations[2], "Direction": "incoming", "ActorKind": "external", "DisplayName": None, "Origin": None},
        {"ConversationId": conversations[3], "Direction": "outgoing", "ActorKind": "external", "DisplayName": None, "Origin": None},
        {"ConversationId": conversations[4], "Direction": "outgoing", "ActorKind": "bot", "DisplayName": None, "Origin": "campaign"},
    ]
    def read(_c, sql, *args):
        assert sql.count("?") == len(args) and args == (inst, *conversations)
        translated = postgres_sql(sql, layout()["tables"])
        parse_sql(translated.replace("%s", "NULL"))
        # ActorRef also contains system actors, so compare text without casting
        # arbitrary actor strings or leaving a SQL Server type name in PostgreSQL.
        assert "TRY_CONVERT" not in translated and "uniqueidentifier" not in translated
        assert "LOWER((u.UserId)::text)=LOWER(op.ActorRef)" in translated
        assert "u.InstitutionId=op.InstitutionId" in sql and "ORDER BY CreatedAt DESC,Sequence DESC" in sql
        return rows
    monkeypatch.setattr(channel_workspace.db, "rows", read)
    items = [{"conversationId": v, "assignee": "Otro asesor"} for v in conversations]
    channel_workspace.Workspace(settings).populate_preview_senders(None, items)
    assert items[0]["previewSender"] == "ai"
    assert items[1]["previewSenderName"] == "Juan Pablo Mora"
    assert "previewSender" not in items[2]
    assert items[3]["previewSender"] == "channel"
    assert items[4]["previewSender"] == "automation"
