import asyncio
import copy
import json
from types import SimpleNamespace
from uuid import uuid4

import httpx2 as httpx
import pytest
from fastapi import HTTPException
from pglast import parse_sql

from app.institutional import agent_catalog, channel_reactions, diagnostics, sales_context
from app.institutional.channel_events import normalize, replyable_message
from app.institutional.operations_policy import layout
from app.institutional.postgres_dialect import postgres_sql
from app.modules.ai.infrastructure.providers import AiError, ProviderGateway
from test_language_resilience import setup, run


PROGRAMS = [{"program_id": 1, "name": "COCINA NACIONAL E INTERNACIONAL"},
            {"program_id": 2, "name": "PRE-ICFES ALTA COMPETENCIA"},
            {"program_id": 3, "name": "DESARROLLO DE SOFTWARE", "schedule": "DIURNA"}]
PROFILES = {2: {"aliases": "ICFES, Saber 11, preicfes"}}


@pytest.mark.parametrize("question", ["¿Y esto tiene que ver con mis resultados del ICFES?",
    "¿Exigen puntaje de ICFES para entrar?", "¿Es obligatorio el Saber 11?", "Mi puntaje del icfes es 227, ¿está bien?"])
def test_score_or_requirement_keeps_previous_interest_and_does_not_retrieve_preparation(question):
    messages = [{"Direction": "incoming", "Body": "Me interesa cocina", "Sequence": 1, "MessageId": str(uuid4())},
                {"Direction": "outgoing", "Body": "Información del PRE-ICFES", "Sequence": 2, "MessageId": str(uuid4())},
                {"Direction": "incoming", "Body": question, "Sequence": 3, "MessageId": str(uuid4())}]
    assert sales_context.interest(PROGRAMS, PROFILES, messages)["program_id"] == 1
    assert 2 not in [p["program_id"] for p in agent_catalog.relevant_programs(PROGRAMS, PROFILES, question)]


@pytest.mark.parametrize("question,expected", [("Ahora prefiero PRE-ICFES, ¿cómo mejoro mis resultados?", 2),
    ("Quiero información de preicfes y precios", 2), ("Ahora quiero software diurno", 3)])
def test_explicit_course_change_still_works(question, expected):
    assert sales_context.matches(PROGRAMS, PROFILES, question)[0]["program_id"] == expected


def reaction_payload(emoji="❤️"):
    return {"entry": [{"id": "waba", "changes": [{"field": "messages", "value": {
        "messaging_product": "whatsapp", "metadata": {"phone_number_id": "business"},
        "messages": [{"id": "reaction-id", "from": "sender", "type": "reaction", "timestamp": "1795550000",
                      "reaction": {"message_id": "original-id", "emoji": emoji}}]}}]}]}


@pytest.mark.parametrize("emoji", ["❤️", "👍", ""])
def test_reaction_retains_exact_target_and_never_schedules_a_language_reply(emoji):
    event = normalize("meta", reaction_payload(emoji))[0]
    ref = channel_reactions.reference(event["provider"])
    assert ref == {"external": "original-id", "emoji": emoji, "removed": emoji == ""}
    assert not replyable_message("whatsapp", event["provider"])
    target = {"MessageId": uuid4(), "Body": "El mensaje realmente señalado", "Direction": "outgoing"}
    shown = channel_reactions.presentation(ref, [target])
    assert shown["replyTo"]["body"] == target["Body"]
    assert ("Retiró" if not emoji else emoji) in shown["body"]
    assert "replyTo" not in channel_reactions.presentation(ref, [])
    assert "replyTo" not in channel_reactions.presentation(ref, [target, target])


def test_legacy_reaction_uses_only_matching_authenticated_event_without_replay(monkeypatch):
    saved = normalize("meta", reaction_payload())[0]
    legacy = copy.deepcopy(saved)
    legacy["provider"].pop("reaction")
    settings = SimpleNamespace(encryption_key=b"unused")
    monkeypatch.setattr(channel_reactions, "key", lambda _: b"test")
    monkeypatch.setattr(channel_reactions, "body_owner", lambda *_: {})
    monkeypatch.setattr(channel_reactions, "unseal", lambda *_: json.dumps(reaction_payload()))
    receipt = {"ReceiptId": str(uuid4()), "EndpointId": str(uuid4()), "BodyNonce": b"nonce", "BodyCiphertext": b"cipher"}
    assert channel_reactions.reference(channel_reactions.recovered_provider(legacy, receipt, settings))
    for field in ("author", "route", "external", "channel"):
        wrong = {**legacy, field: "different"}
        assert channel_reactions.recovered_provider(wrong, receipt, settings) == legacy["provider"]


def test_reaction_projection_scopes_queries_to_same_conversation_account_and_identity(monkeypatch):
    inst, conversation, message, integration, identity = [str(uuid4()) for _ in range(5)]
    settings = SimpleNamespace(ticket={"context": [[1, inst]]})
    source = {"MessageId": message, "IntegrationId": integration, "IdentityId": identity,
              "Payload": json.dumps(normalize("meta", reaction_payload())[0])}
    queries = []
    def query(_c, sql, *args):
        assert sql.count("?") == len(args)
        parse_sql(postgres_sql(sql, layout()["tables"]).replace("%s", "NULL"))
        queries.append((sql, args))
        return [source] if len(queries) == 1 else []
    monkeypatch.setattr(channel_reactions, "rows", query)
    result = channel_reactions.project(None, settings, conversation,
        [{"id": message, "direction": "incoming", "body": "[reaction]"}])
    assert "mensaje original no disponible" in result[message]["body"]
    assert queries[1][1] == (inst, integration, identity, conversation, "original-id", "original-id")
    assert "w.Authentication='verified'" in queries[0][0]
    assert "replyTo" not in result[message]


def test_truncated_generation_recovers_once_without_losing_query_or_increasing_output_cap():
    state = setup()
    state.saved["fallback_on_timeout"] = True
    async def timed_out_primary():
        raise AiError("provider_timeout_or_network", 504)
    state.primary = timed_out_primary
    original = state.gateway.request
    posts = []
    async def request(provider, method, path, body=None):
        if method == "POST":
            posts.append(copy.deepcopy(body))
            if len(posts) == 1:
                return {"choices": [{"finish_reason": "length", "message": {"content": '{"text":"partial'}}]}
        return await original(provider, method, path, body)
    state.gateway.request = request
    result = run(state)
    assert result["candidates"][0]["finishReason"] == "STOP"
    assert len(posts) == len(state.reservations) == 2
    assert posts[0]["max_tokens"] == posts[1]["max_tokens"]
    assert posts[0]["messages"][1:] == posts[1]["messages"][1:]
    assert "RECUPERACIÓN" in posts[1]["messages"][0]["content"]
    assert state.trace["completion_recoveries"][0]["state"] == "completed"
    assert state.trace["attempts"][0]["state"] == "uncertain"
    assert state.trace["fallback_used"]
    projected = diagnostics.projection(json.dumps({"language_execution": state.trace}))
    assert projected["completion_recoveries"][0]["state"] == "completed"
    assert "Consulta" not in json.dumps(projected)


def test_human_change_after_truncation_prevents_a_second_generation():
    state, active, posts = setup(), [True], []
    original = state.gateway.request
    async def request(provider, method, path, body=None):
        if method == "POST":
            posts.append(1)
            active[0] = False
            return {"choices": [{"finish_reason": "length", "message": {"content": "partial"}}]}
        return await original(provider, method, path, body)
    def guard():
        if not active[0]:
            raise HTTPException(409, "human_control")
    state.gateway.request = request
    with pytest.raises(HTTPException, match="human_control"):
        run(state, guard=guard)
    assert posts == [1] and len(state.reservations) == 1


def test_generation_timeout_is_longer_than_catalog_and_does_not_retry(monkeypatch):
    seen = []
    original = httpx.AsyncClient
    def client(**kwargs):
        seen.append(kwargs["timeout"])
        return original(**kwargs)
    monkeypatch.setattr(httpx, "AsyncClient", client)
    gateway = ProviderGateway({"openrouter": "fixture"}, httpx.MockTransport(lambda _: httpx.Response(200, json={})))
    asyncio.run(gateway.request("openrouter", "POST", "chat/completions", {}))
    asyncio.run(gateway.request("openrouter", "GET", "models/user"))
    assert seen[0].read == 30 and seen[1] == 10
