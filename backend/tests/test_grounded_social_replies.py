import json
from contextlib import nullcontext
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.institutional import (
    grounded_replies as grounding,
    whatsapp_gemini as messaging,
    comment_automation as comments,
)
from app.institutional.agent_catalog import relevant_programs
from app.institutional.program_commercial import agent_facts
from app.modules.agents import service as agent_service
from app.modules.ai.infrastructure.providers import AiError


def result(text, decision="responder", finish="STOP"):
    return {
        "candidates": [
            {
                "finishReason": finish,
                "content": {
                    "parts": [
                        {"text": json.dumps({"decision": decision, "text": text})},
                    ]
                },
            }
        ]
    }


def test_generated_replies_are_not_limited_to_greetings():
    answer = "El programa de Software tiene tres semestres y aborda programación. ¿Qué jornada buscas?"
    assert grounding.parse(result(answer)) == answer
    assert grounding.parse(result("", "revisar")) is None
    for invalid in [
        result(""),
        result("x" * 901),
        result("hola", finish="MAX_TOKENS"),
        result("hola", decision="inventado"),
    ]:
        with pytest.raises(ValueError):
            grounding.parse(invalid, public=True)


def test_human_control_only_allows_explicit_reviewed_drafts(monkeypatch):
    class Cursor:
        def __init__(self):
            self.answers = iter(
                [("human", "open"), ("human", None, 3, 0, None, 1), (None,)]
            )

        def execute(self, query, *_):
            assert query.lstrip().startswith("SELECT")
            return SimpleNamespace(fetchone=lambda: next(self.answers))

    monkeypatch.setattr(agent_service, "load", lambda *_: ({"agent": {}}, {}))
    monkeypatch.setattr(agent_service, "context_row", lambda *_: None)
    monkeypatch.setattr(agent_service, "preflight", lambda *_: {"ready": True})

    def resolve(_agents, _stages, assignment, _context, _channel, control):
        if control == "human":
            raise AiError("agents_human_control", 409)
        assert assignment["mode"] == "automatic"
        return {"agent_id": "agent"}

    monkeypatch.setattr(agent_service, "resolve", resolve)
    with pytest.raises(AiError, match="agents_human_control"):
        agent_service.resolve_conversation(Cursor(), "own", "instagram")
    selected = agent_service.resolve_conversation(
        Cursor(), "own", "instagram", for_draft=True
    )
    assert selected["assignment"]["mode"] == "human"
    assert selected["assignment"]["revision"] == 3


def test_program_lookup_is_informational_and_price_requires_current_evidence():
    items = [
        {"program_id": 1, "name": "Auxiliar de Enfermería"},
        {"program_id": 2, "name": "Desarrollo de Software"},
    ]
    assert relevant_programs(items, {}, "¿Cuánto dura enfermeria?") == [items[0]]
    assert relevant_programs(
        items, {2: {"aliases": "Programación, sistemas"}}, "Quiero sistemas"
    ) == [items[1]]
    assert "price_cop" not in agent_facts(
        {
            "price_cop": 100000,
            "price_concept": "Matrícula",
            "price_valid_until": "2000-01-01",
        }
    )


def test_context_uses_saved_prompts_history_and_reviewed_programs_without_private_public_memory(
    monkeypatch,
):
    settings = SimpleNamespace()
    monkeypatch.setattr(
        grounding,
        "setting",
        lambda *_: {
            "revision": 7,
            "document": {
                "system_prompt": "Usa el nombre CBN.",
                "comment_prompt": "Responde sin emojis.",
            },
        },
    )
    catalog_queries = []

    class Catalog:
        def __init__(self, *_):
            pass

        def read_context(self, _c, query, _program):
            catalog_queries.append(query)
            return {
                "material": {
                    "queried_programs": [
                        {"program_id": 2, "name": "Software", "duration": "3 semestres"}
                    ]
                }
            }

    monkeypatch.setattr(grounding, "Catalog", Catalog)
    monkeypatch.setattr(
        grounding,
        "search",
        lambda *_: [{"id": "source", "title": "Plan revisado", "text": "Programación"}],
    )
    monkeypatch.setattr(
        grounding,
        "effective",
        lambda *_: {"shared": [], "conversation": [{"secret": "privado"}]},
    )
    monkeypatch.setattr(
        grounding,
        "rows",
        lambda *_: [
            {"Direction": "incoming", "Body": "¿Y cuánto dura?"},
            {"Direction": "incoming", "Body": "Me interesa Software"},
        ],
    )
    selection = {
        "configuration": {
            "instructions": "Sé cercano.",
            "objectives": ["Orientar"],
            "rules": [],
            "tone": "Cercano",
        }
    }
    private = grounding.context(
        None,
        settings,
        "¿Y cuánto dura?",
        selection=selection,
        conversation="own",
        sequence=3,
    )
    assert (
        "Sé cercano" in private["system"] and "Usa el nombre CBN" in private["system"]
    )
    assert "Software" in catalog_queries[-1] and "3 semestres" in private["query"]
    public = grounding.context(
        None, settings, "Precio", public=True, post="Programa Software"
    )
    assert "sin emojis" in public["system"]
    assert (
        json.loads(public["query"])["historial"] == []
        and "privado" not in public["query"]
    )
    assert private["fingerprint"] != public["fingerprint"]


@pytest.mark.parametrize(
    "answer", ["Software dura tres semestres según la ficha vigente.", None]
)
def test_message_worker_sends_generated_text_or_hands_off(monkeypatch, answer):
    from app.institutional import channel_outbox

    profile = SimpleNamespace(ticket={"context": [[1, str(uuid4())]]})
    operation, integration, conversation = [str(uuid4()) for _ in range(3)]
    data = {
        "conversation": conversation,
        "identity": str(uuid4()),
        "incoming": operation,
        "epoch": 1,
    }

    class Cursor:
        rowcount = 1

        def execute(self, *_):
            return self

        def fetchone(self):
            return (1,)

    cursor = Cursor()
    monkeypatch.setattr(messaging, "transaction", lambda *_a, **_k: nullcontext(cursor))
    monkeypatch.setattr(
        messaging,
        "one",
        lambda *_: {
            "OperationId": operation,
            "IntegrationId": integration,
            "ResultMetadata": json.dumps(data),
        },
    )
    monkeypatch.setattr(
        messaging,
        "source",
        lambda *_: (
            {"IntegrationId": integration},
            {"Body": "Software", "Sequence": 3, "Epoch": 1},
            {"daily_tokens": 1000000, "daily_usd_micros": 1000000},
        ),
    )
    monkeypatch.setattr(messaging, "provider_account", lambda *_: None)
    monkeypatch.setattr(
        messaging,
        "model_config",
        lambda *_: (
            {
                "max_tokens": 1500,
                "input_usd_per_million": 0.25,
                "output_usd_per_million": 1.5,
            },
            {"VersionNo": 1, "Nonce": b"", "Ciphertext": b""},
            {"model": "gemini-test", "credential": str(uuid4())},
        ),
    )
    # Binding is stable throughout a paid attempt.
    config, secret, binding = messaging.model_config()
    monkeypatch.setattr(messaging, "model_config", lambda *_: (config, secret, binding))
    monkeypatch.setattr(
        messaging,
        "reply_context",
        lambda *_: {
            "system": "Prompt de ventas",
            "query": "Software: 3 semestres",
            "fingerprint": "reviewed",
        },
    )
    monkeypatch.setattr(messaging, "unseal", lambda *_: "test-only")
    monkeypatch.setattr(messaging, "key", lambda *_: b"test-only")
    monkeypatch.setattr(messaging, "reserve_budget", lambda *_: None)
    recorded, sent, handoffs = [], [], []
    monkeypatch.setattr(
        messaging, "finish", lambda *args: recorded.append(args[5]) or True
    )
    monkeypatch.setattr(
        channel_outbox,
        "enqueue",
        lambda *args, **_kw: sent.append(args[5]["body"]) or str(uuid4()),
    )
    from app.modules.inbox.application import state

    monkeypatch.setattr(state, "change_control", lambda *_: handoffs.append(True))

    class Gateway:
        def __init__(self, *_):
            pass

        async def gemini_generation(self, model, body, before_attempt):
            before_attempt()
            assert body["systemInstruction"]["parts"][0]["text"] == "Prompt de ventas"
            return result(answer or "", "responder" if answer else "revisar")

    assert messaging.Worker(profile, Gateway).once()
    assert sent == ([answer] if answer else [])
    assert bool(handoffs) == (answer is None)
    assert recorded[-1]["generation"] == "grounded-v1"
    assert recorded[-1]["generated_text"] == answer


def test_meta_native_reply_does_not_silence_gemini_but_crm_send_does(monkeypatch):
    profile = SimpleNamespace(ticket={"context": [[1, str(uuid4())]]})
    monkeypatch.setattr(comments, "available", lambda *_: True)
    monkeypatch.setattr(
        comments,
        "configuration",
        lambda *_: {"OutboundEnabled": True, "ModuleEnabled": True},
    )
    monkeypatch.setattr(
        comments,
        "setting",
        lambda *_: {
            "document": {
                "enabled": True,
                "provider": "gemini",
                "model": "gemini-test",
                "comment_mode": "auto",
            }
        },
    )
    monkeypatch.setattr(
        comments,
        "account",
        lambda *_: {
            "RequestedStatus": "connected",
            "VerifiedStatus": "verified",
            "ApplicationState": "active",
        },
    )
    monkeypatch.setattr(
        comments,
        "one",
        lambda *_: {
            "Body": "Software",
            "RowVersion": b"version",
            "Payload": '{"_crm":{"state":"new"}}',
            "ExternalId": "comment",
        },
    )

    class Cursor:
        queued = False

        def execute(self, query, *_):
            assert "SendJob" in query and "SocialComment response" not in query
            return SimpleNamespace(fetchone=lambda: (1,) if self.queued else None)

    cursor = Cursor()
    data = {"comment": str(uuid4()), "version": b"version".hex()}
    assert comments.current(cursor, profile, str(uuid4()), data)[2] == "Software"
    cursor.queued = True
    with pytest.raises(HTTPException, match="comment_auto_already_answered"):
        comments.current(cursor, profile, str(uuid4()), data)


def test_generated_dm_cannot_dispatch_with_changed_text_or_changed_context(monkeypatch):
    operation, reply, identity = [str(uuid4()) for _ in range(3)]
    data = {
        "reply": reply,
        "identity": identity,
        "generation": "grounded-v1",
        "generated_text": "Software dura tres semestres.",
        "modelBinding": {"model": "gemini-test"},
        "contextBinding": "current",
    }
    monkeypatch.setattr(
        messaging, "one", lambda *_: {"ResultMetadata": json.dumps(data)}
    )
    monkeypatch.setattr(messaging, "source", lambda *_: ({}, {}, {}))
    monkeypatch.setattr(
        messaging, "model_config", lambda *_: ({}, {}, data["modelBinding"])
    )
    monkeypatch.setattr(
        messaging, "reply_context", lambda *_: {"fingerprint": "current"}
    )
    settings = SimpleNamespace(ticket={"context": [[1, str(uuid4())]]})
    job = {"MessageId": reply, "IdentityId": identity, "IntegrationId": str(uuid4())}
    payload = {"automationId": operation, "body": data["generated_text"]}
    messaging.dispatch_authorized(None, settings, job, payload)
    with pytest.raises(HTTPException, match="gemini_whatsapp_intent_mismatch"):
        messaging.dispatch_authorized(
            None, settings, job, {**payload, "body": "Texto alterado"}
        )
    monkeypatch.setattr(
        messaging, "reply_context", lambda *_: {"fingerprint": "new-program-price"}
    )
    with pytest.raises(HTTPException, match="gemini_reply_context_changed"):
        messaging.dispatch_authorized(None, settings, job, payload)


def test_generated_public_reply_must_match_the_confirmed_operation(monkeypatch):
    operation = str(uuid4())
    data = {
        "comment": str(uuid4()),
        "operation": operation,
        "revision": 4,
        "generation": "grounded-v1",
        "generated_text": "Contamos con Software. ¿Qué te gustaría conocer?",
        "contextBinding": "current",
    }
    monkeypatch.setattr(
        comments, "one", lambda *_: {"ResultMetadata": json.dumps(data)}
    )
    monkeypatch.setattr(
        comments,
        "current",
        lambda *_: ({}, {"revision": 4}, "Software", "old-greeting"),
    )
    monkeypatch.setattr(
        comments, "comment_context", lambda *_: {"fingerprint": "current"}
    )
    settings = SimpleNamespace(ticket={"context": [[1, str(uuid4())]]})
    job = {
        "OperationId": operation,
        "CommentId": data["comment"],
        "IntegrationId": str(uuid4()),
        "QueueId": str(uuid4()),
    }
    comments.authorize_send(None, settings, job, {"body": data["generated_text"]})
    with pytest.raises(HTTPException, match="comment_auto_policy_changed"):
        comments.authorize_send(None, settings, job, {"body": "old-greeting"})
