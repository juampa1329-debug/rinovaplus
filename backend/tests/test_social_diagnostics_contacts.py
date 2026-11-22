import json
from contextlib import nullcontext
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from pglast import parse_sql

from app.institutional import channel_media, diagnostics, institution_contacts, sales_recovery
from app.institutional.channel_events import normalize, replyable_message
from app.institutional.models import Institution, PublicContact
from app.institutional.operations_policy import layout
from app.institutional.postgres_dialect import postgres_sql


def test_public_contacts_are_explicit_and_do_not_infer_calls_from_whatsapp(monkeypatch):
    number = PublicContact(label="Admisiones", number="300 471 4060", use="calls")
    assert number.number == "+573004714060"
    assert Institution(name="CBN").public_contacts == []
    monkeypatch.setattr(institution_contacts, "setting", lambda *_: {"revision": 2, "document": {"public_contacts": [number.model_dump(), {**number.model_dump(), "active": False}]}})
    value = institution_contacts.directory(None, None)
    assert len(value["items"]) == 1 and value["items"][0]["use"] == "calls"
    assert institution_contacts.sources(value)[0]["revision"] == 2
    for wrong in ("javascript:alert(1)", "123", "+57 300 llamar ya"):
        with pytest.raises(ValidationError):
            PublicContact(label="CBN", number=wrong, use="calls")


def test_story_mention_is_identified_without_scheduling_a_fake_text_reply():
    message = {"mid": "fixture-mid", "attachments": [{"type": "story_mention", "payload": {"url": "https://media.cdninstagram.com/story"}}]}
    event = normalize("meta", {"object": "instagram", "entry": [{"id": "business", "messaging": [{"sender": {"id": "sender"}, "message": message}]}]})[0]
    assert event["text"] == "Te mencionó en una historia"
    assert not replyable_message("instagram", event["provider"])
    assert event["provider"]["message"]["attachments"][0]["type"] == "story_mention"
    message.update(text="Me interesa este curso", reply_to={"story": {"id": "story", "url": "https://instagram.com/stories/test"}})
    event = normalize("meta", {"object": "instagram", "entry": [{"id": "business", "messaging": [{"sender": {"id": "sender"}, "message": message}]}]})[0]
    assert event["text"] == "Me interesa este curso" and replyable_message("instagram", event["provider"])
    assert event["provider"]["message"]["reply_to"]["story"]["id"] == "story"


def test_diagnostics_select_only_operational_metadata_and_parameterize_filters(monkeypatch):
    trace = diagnostics.projection(json.dumps({"prompt": "private", "key": "secret", "generated_text": "customer", "language_execution": {"provider": "openrouter", "model": "fixture", "fallback_used": True, "attempts": [{"model": "fixture", "key": "secret"}]}}))
    assert trace["fallback_used"] and "secret" not in json.dumps(trace) and "private" not in json.dumps(trace)
    settings = SimpleNamespace(ticket={"context": [[1, str(uuid4())]]})
    queries = []
    def capture(_c, query, *args):
        assert query.count("?") == len(args)
        parse_sql(postgres_sql(query, layout()["tables"]).replace("%s", "NULL"))
        queries.append(query)
        return []
    monkeypatch.setattr(diagnostics, "rows", capture)
    assert diagnostics.read(None, settings)["items"] == []
    assert diagnostics.read(None, settings, str(uuid4()))["read_only"]
    assert len(queries) == 5 and not any("SELECT *" in q for q in queries)
    with pytest.raises(HTTPException):
        diagnostics.read(None, settings, "' OR 1=1")


@pytest.mark.parametrize("state,attempts,external,allowed", [("cancelled",0,None,True),("cancelled",1,None,False),("cancelled",0,"sent-id",False),("uncertain",0,None,False),("accepted",1,"sent-id",False)])
def test_cancelled_generation_recovery_never_repeats_an_attempted_send(monkeypatch, state, attempts, external, allowed):
    reply = str(uuid4())
    row = {"Status":"confirmed","Attempts":1,"IntegrationId":str(uuid4()),"ResultMetadata":json.dumps({"reply":reply,"response_parts":[{"id":reply}]})}
    monkeypatch.setattr(sales_recovery.db,"rows",lambda *_:[{"MessageId":reply,"State":state,"Attempts":attempts,"ExternalId":external}])
    monkeypatch.setattr(sales_recovery,"source",lambda *_:None)
    settings=SimpleNamespace(ticket={"context":[[1,str(uuid4())]]})
    if allowed:
        assert sales_recovery.review(None,settings,row)["reply"] == reply
    else:
        with pytest.raises(HTTPException):
            sales_recovery.review(None,settings,row)


@pytest.mark.parametrize("existing", [False, True])
def test_story_preview_registers_only_verified_incoming_media_and_never_sends(monkeypatch, existing):
    settings = SimpleNamespace(ticket={"context": [[1, str(uuid4())]]})
    body = channel_media.StoryPreview(operation_id=str(uuid4()), message_id=str(uuid4()))
    calls, queries = [], []
    cursor = SimpleNamespace(execute=lambda *_: None)
    monkeypatch.setattr(channel_media, "transaction", lambda *_a, **_k: nullcontext(cursor))
    monkeypatch.setattr(channel_media, "authorize", lambda _c, _s, _a, permission: calls.append(permission) or {"UserId": str(uuid4())})
    monkeypatch.setattr(channel_media, "replay", lambda *_: ("checksum", None))
    def source(_c, query, *args):
        assert query.count("?") == len(args)
        parse_sql(postgres_sql(query, layout()["tables"]).replace("%s", "NULL"))
        queries.append(query)
        if "WebhookEvent" in query:
            return {"IntegrationId": str(uuid4()), "ConversationId": str(uuid4()), "IdentityId": str(uuid4()),
                    "Payload": json.dumps({"provider": {"message": {"attachments": [{"type": "story_mention", "payload": {"url": "https://media.cdninstagram.com/fixture"}}]}}})}
        return {"MediaId": str(uuid4())} if existing else None
    monkeypatch.setattr(channel_media, "one", source)
    monkeypatch.setattr(channel_media, "account", lambda *_: {})
    monkeypatch.setattr(channel_media, "register_incoming", lambda *_: calls.append("register_media"))
    monkeypatch.setattr(channel_media, "record_operation", lambda *_: calls.append("record"))
    result = channel_media.Media(settings).story_preview("authority", body)
    assert result == {"saved": True, "message_sent": False}
    assert calls == ["inbox.write", "inbox.read", *([] if existing else ["register_media"]), "record"]
    assert len(queries) == 2


def test_story_preview_replay_does_not_repeat_registration(monkeypatch):
    settings = SimpleNamespace(ticket={"context": [[1, str(uuid4())]]})
    body = channel_media.StoryPreview(operation_id=str(uuid4()), message_id=str(uuid4()))
    monkeypatch.setattr(channel_media, "transaction", lambda *_a, **_k: nullcontext(None))
    monkeypatch.setattr(channel_media, "authorize", lambda *_: {"UserId": str(uuid4())})
    monkeypatch.setattr(channel_media, "replay", lambda *_: ("checksum", {"saved": True, "message_sent": False}))
    monkeypatch.setattr(channel_media, "one", lambda *_: pytest.fail("replay must not query source or register media"))
    assert channel_media.Media(settings).story_preview("authority", body)["saved"]


def test_workspace_history_projects_legacy_story_payload_without_mutating_body(monkeypatch):
    from app.institutional import channel_workspace
    message = str(uuid4())
    item = {"id": message, "body": "[multimedia]"}
    monkeypatch.setattr(channel_workspace.Parent, "messages", lambda *_: {"items": [item]})
    workspace = object.__new__(channel_workspace.Workspace)
    workspace.profile = SimpleNamespace(ticket={"context": [[1, str(uuid4())]]})
    workspace.transaction = lambda: nullcontext(None)
    def rows(_c, query, *args):
        assert query.count("?") == len(args)
        parse_sql(postgres_sql(query, layout()["tables"]).replace("%s", "NULL"))
        return [{"MessageId": message, "Payload": json.dumps({"provider": {"message": {"attachments": [{"type": "story_mention"}]}}})}] if "SELECT x.MessageId,e.Payload" in query else []
    monkeypatch.setattr(channel_workspace.db, "rows", rows)
    result = workspace.messages(str(uuid4()))
    assert result["items"][0]["body"] == "Te mencionó en una historia"
    assert result["items"][0]["socialSource"]["kind"] == "story_mention"
