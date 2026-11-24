import asyncio
import json
from contextlib import nullcontext
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pglast import parse_sql

from app.institutional import grounded_replies, reply_turns, whatsapp_gemini
from app.institutional.language_resilience import generate
from app.institutional.operations_policy import layout
from app.institutional.postgres_dialect import postgres_sql


def fixture():
    inst, integration, conversation, identity, first, latest = [str(uuid4()) for _ in range(6)]
    data = {"integration": integration, "conversation": conversation, "identity": identity, "incoming": latest, "epoch": 7}
    settings = SimpleNamespace(ticket={"context": [[1, inst]]})
    messages = [
        {"MessageId": first, "Sequence": 3, "Direction": "incoming", "Body": "¿Cuánto cuesta Software?", "ExternalId": "mid.oldest"},
        {"MessageId": latest, "Sequence": 5, "Direction": "incoming", "Body": "¿Y qué jornada tiene?", "ExternalId": "mid.latest"},
    ]
    return settings, data, messages


def sql_check(sql, args):
    assert sql.count("?") == len(args)
    parse_sql(postgres_sql(sql, layout()["tables"]).replace("%s", "NULL"))


def test_pending_batch_keeps_old_question_quotes_first_and_binds_every_query_to_owner(monkeypatch):
    settings, data, messages = fixture()
    statements = []

    def one(_c, sql, *args):
        sql_check(sql, args)
        statements.append(sql)
        assert args[:2] == (settings.ticket["context"][0][1], data["integration"])
        return {"Sequence": 2}

    def rows(_c, sql, *args):
        sql_check(sql, args)
        assert args == (settings.ticket["context"][0][1], data["integration"], data["identity"], data["conversation"], 2, 5)
        return messages

    monkeypatch.setattr(reply_turns.db, "one", one)
    monkeypatch.setattr(reply_turns.db, "rows", rows)
    value = reply_turns.snapshot(None, settings, data, {"Sequence": 5})
    assert value["pending"] == [v["Body"] for v in messages]
    assert value["incoming_ids"] == [v["MessageId"] for v in messages]
    assert value["quote_incoming"] == messages[0]["MessageId"]
    assert value["quote_external"] == "mid.oldest"
    coverage = statements[0]
    assert "AND NOT EXISTS" in coverage and "j.State NOT IN('accepted','sent','delivered','read')" in coverage
    assert "reply_turn_no_response" in coverage and "op.Status='confirmed'" in coverage
    assert "COALESCE(TRY_CONVERT(uniqueidentifier,JSON_VALUE(op.ResultMetadata,'$.incoming')),op.OperationId)=m.MessageId" in coverage


@pytest.mark.parametrize("case", ["reset", "too_many", "too_long", "missing_latest"])
def test_reset_boundary_and_oversize_batches_do_not_drop_early_questions(monkeypatch, case):
    settings, data, messages = fixture()
    monkeypatch.setattr(reply_turns.db, "one", lambda *_: {"Sequence": 0})
    if case == "too_many":
        messages = [messages[0]] * 24 + [messages[-1]]
    elif case == "too_long":
        messages[0]["Body"] = "x" * 12001
    elif case == "missing_latest":
        messages = messages[:1]
    cursor = SimpleNamespace(context_cutoff=lambda _: 4)

    def rows(_c, sql, *args):
        assert args[-2] == 4
        return messages[-1:] if case == "reset" else messages

    monkeypatch.setattr(reply_turns.db, "rows", rows)
    if case == "reset":
        assert reply_turns.snapshot(cursor, settings, data, {"Sequence": 5})["pending"] == [messages[-1]["Body"]]
    else:
        with pytest.raises(HTTPException, match="reply_turn_source_changed" if case == "missing_latest" else "reply_turn_batch_review_required"):
            reply_turns.snapshot(cursor, settings, data, {"Sequence": 5})


@pytest.mark.parametrize("state", [None, "queued", "sending", "uncertain", "running"])
def test_prior_work_waits_and_uncertain_delivery_is_not_automatically_replayed(monkeypatch, state):
    settings, data, _ = fixture()
    calls = []

    def one(_c, sql, *args):
        sql_check(sql, args)
        calls.append(sql)
        if "SendJob" in sql:
            return {"State": state} if state in {"queued", "sending", "uncertain"} else None
        return {"OperationId": "older"} if state == "running" else None

    monkeypatch.setattr(reply_turns.db, "one", one)
    if state:
        with pytest.raises(HTTPException, match="reply_turn_delivery_uncertain" if state == "uncertain" else "reply_turn_waiting_previous"):
            reply_turns.require_settled(None, settings, data, {"Sequence": 5})
    else:
        reply_turns.require_settled(None, settings, data, {"Sequence": 5})
    assert all(sql.startswith("SELECT") for sql in calls)


@pytest.mark.parametrize("wait", [0, 60, 120, 3600])
def test_worker_observes_configured_quiet_window_before_any_model_or_typing(monkeypatch, wait):
    settings, _, _ = fixture()
    monkeypatch.setattr(whatsapp_gemini, "transaction", lambda *_a, **_k: nullcontext(None))
    monkeypatch.setattr(whatsapp_gemini, "setting", lambda *_: {"document": {"wait_seconds": wait}})
    def one(_c, sql, *args):
        sql_check(sql, args)
        assert "CreatedAt<=DATEADD(second,?,SYSUTCDATETIME())" in sql
        assert args[-1] == -wait
        return None
    monkeypatch.setattr(whatsapp_gemini, "one", one)
    assert whatsapp_gemini.Worker(settings, gateway_factory=lambda *_: pytest.fail("No model before wait")).once() is False


def response(decision, text="", **extra):
    return {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": json.dumps({"decision": decision, "text": text, **extra})}]}}]}


def test_wait_is_only_allowed_for_bound_private_turns_and_cannot_hide_a_text_or_crm_write():
    assert grounded_replies.parse(response("esperar"), allow_wait=True) is None
    for kwargs in [{}, {"allow_wait": True, "public": True}]:
        with pytest.raises(ValueError):
            grounded_replies.parse(response("esperar"), **kwargs)
    for value in [response("esperar", "Hidden answer"), response("esperar", crm_observations=[{"field": "name"}])]:
        with pytest.raises(ValueError):
            grounded_replies.parse(value, allow_wait=True)


@pytest.mark.parametrize("pending,expected", [
    (["Gracias 😊"], True), (["Muchas gracias por la información"], True),
    (["¿Cuánto vale?", "Gracias"], False), (["Gracias, ¿qué horario tiene?"], False),
    (["Me parece caro"], False), (["Sí"], False), (["ok"], False),
    (["Quiero una persona, gracias"], False),
])
def test_repeated_questions_or_new_information_cannot_be_silenced(pending, expected):
    history = [{"direction": "outgoing", "text": "Información ya enviada"}]
    assert reply_turns.can_wait(pending, history) is expected
    assert not reply_turns.can_wait(pending, [])


def test_superseding_only_updates_same_epoch_unattempted_older_bot_jobs(monkeypatch):
    settings, data, _ = fixture()
    queue, operation = [str(uuid4()) for _ in range(2)]
    statements = []
    class Cursor:
        rowcount = 1
        def execute(self, sql, *args):
            sql_check(sql, args)
            statements.append((sql, args))
    def rows(_c, sql, *args):
        sql_check(sql, args)
        assert "j.Attempts=0 AND j.ExternalId IS NULL" in sql
        assert "r.ControlEpoch=?" in sql and "r.ActorKind='bot'" in sql
        assert args == (settings.ticket["context"][0][1], data["integration"], data["identity"], 7, data["conversation"], 5)
        return [{"QueueId": queue, "OperationId": operation}]
    monkeypatch.setattr(reply_turns.db, "rows", rows)
    assert reply_turns.supersede_queued(Cursor(), settings, data, {"Sequence": 5})
    assert len(statements) == 3
    assert "State='queued' AND Attempts=0 AND ExternalId IS NULL" in statements[0][0]
    assert statements[0][1][-1] == queue and statements[1][1][-1] == operation
    assert all("INSERT" not in sql for sql, _ in statements)


@pytest.mark.parametrize("model", ["anthropic/claude-sonnet-4.6", "fixture/model"])
def test_openrouter_keeps_strict_turn_decisions_including_wait_in_one_request(model):
    body = grounded_replies.request_body({"system": reply_turns.RULES, "query": "Gracias", "reply_turn": {"pending": ["Gracias"], "can_wait": True}})
    calls = []
    class Gateway:
        async def request(self, _provider, _method, _path, request):
            calls.append(request)
            schema = request["response_format"]["json_schema"]
            assert schema["strict"]
            assert schema["schema"]["properties"]["decision"]["enum"] == ["responder", "revisar", "esperar"]
            return {"choices": [{"finish_reason": "stop", "message": {"content": '{"decision":"esperar","text":"","crm_observations":[]}'}}]}
    result = asyncio.run(generate(Gateway(), {"provider": "openrouter", "model": model, "input_usd_per_million": 3, "output_usd_per_million": 15}, body, lambda: None))
    assert grounded_replies.parse(result, allow_wait=True) is None
    assert len(calls) == 1
