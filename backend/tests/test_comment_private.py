import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.institutional import comment_private as private
from app.modules.channels import providers
from app.modules.agents.skill_library import resources, render


NOW = datetime.now(timezone.utc)


def original(channel="facebook"):
    return {"Channel": channel, "ExternalAccountId": "owned"}, {
        "ExternalId": "comment",
        "AuthorExternalId": "person",
        "Payload": '{"_crm":{"state":"new"},"provider":{}}',
    }


@pytest.mark.parametrize("channel", ["facebook", "instagram"])
def test_private_eligibility_uses_creation_not_import_time(channel):
    item, comment = original(channel)
    private.eligible(item, comment, NOW.isoformat(), now=NOW)
    for stamp in [
        NOW - timedelta(days=7),
        NOW + timedelta(minutes=5),
        None,
        "2026-11-23",
    ]:
        with pytest.raises(HTTPException):
            private.eligible(
                item,
                comment,
                stamp.isoformat() if isinstance(stamp, datetime) else stamp,
                now=NOW,
            )


@pytest.mark.parametrize(
    "payload",
    [
        {"_crm": {"synthetic_demo": True}},
        {"_crm": {"state": "deleted"}},
        {"_crm": {"state": "unavailable"}},
        {"provider": {"comment_surface": "live_comments"}},
    ],
)
def test_no_deleted_demo_or_unconfirmed_live_private(payload):
    item, comment = original()
    comment["Payload"] = json.dumps(payload)
    with pytest.raises(HTTPException):
        private.eligible(item, comment, NOW.isoformat(), now=NOW)


@pytest.mark.parametrize("author", ["", "owned"])
def test_private_requires_external_person(author):
    item, comment = original()
    comment["AuthorExternalId"] = author
    with pytest.raises(HTTPException):
        private.eligible(item, comment, NOW.isoformat(), now=NOW)


def generated(
    intent="information",
    delivery="private",
    program="27",
    decision="responder",
    text="Puedes empezar con el abono vigente.",
    finish="STOP",
):
    return {
        "candidates": [
            {
                "finishReason": finish,
                "content": {
                    "parts": [
                        {
                            "text": json.dumps(
                                {
                                    "decision": decision,
                                    "intent": intent,
                                    "delivery": delivery,
                                    "program_id": program,
                                    "text": text,
                                }
                            )
                        }
                    ]
                },
            }
        ]
    }


def grounding():
    return {
        "system": "fuentes",
        "query": json.dumps(
            {
                "catalogo": {
                    "queried_programs": [{"program_id": 27, "name": "PRE-ICFES"}]
                }
            }
        ),
        "fingerprint": "bound",
        "skill_policy": {},
    }


def test_private_only_for_information_and_actual_catalog_program():
    assert private.parse(generated(), grounding())[1]["delivery"] == "private"
    assert private.parse(generated(delivery="public"), grounding())[1]["delivery"] == "private"
    for result in [
        generated(program="invented"),
        generated(intent="support"),
        generated(intent="complaint"),
        generated(decision="revisar", text=""),
    ]:
        assert private.parse(result, grounding())[0] is None
    assert (
        private.parse(
            generated(
                intent="support", delivery="public", text="¡Gracias por acompañarnos!"
            ),
            grounding(),
        )[1]["delivery"]
        == "public"
    )


@pytest.mark.parametrize(
    "result",
    [
        generated(text="x" * 901),
        generated(finish="MAX_TOKENS"),
        generated(intent="injected"),
        generated(delivery="mass_dm"),
    ],
)
def test_private_parser_rejects_invalid_or_truncated_result(result):
    with pytest.raises(ValueError):
        private.parse(result, grounding())


def test_real_guides_are_loaded_hashed_and_bound_to_context():
    guides = resources(private.GUIDES)
    assert len(guides) == 3 and all(len(r["sha256"]) == 64 for r in guides)
    assert "SKILL CONSULTADA" in render(guides)
    value = private.context(grounding())
    assert value["fingerprint"] != "bound"
    assert value["skill_policy"]["social_resources"] == guides
    schema = private.request_body(value, 1000, 0.3)["generationConfig"][
        "responseSchema"
    ]
    assert "delivery" in schema["required"]
    assert schema["properties"]["program_id"] == {"type": "STRING"}


def test_private_routing_context_removes_the_unconditional_public_delivery_instruction():
    source = grounding()
    source["system"] += " Esta respuesta será PÚBLICA. No incluyas datos personales ni memoria privada. "
    value = private.context(source)
    assert "Esta respuesta será PÚBLICA" not in value["system"]
    assert "No incluyas datos personales ni memoria privada" in value["system"]
    assert "Nunca superes 900" in value["system"]


@pytest.mark.parametrize("channel,asset", [("facebook", "page"), ("instagram", "ig")])
def test_private_uses_comment_id_and_verifies_time_before_post(
    monkeypatch, channel, asset
):
    calls = []

    def request(account, method, target, body):
        calls.append((method, target, body))
        if method == "GET":
            return {
                "id": "comment",
                "timestamp": NOW.isoformat(),
                "created_time": NOW.isoformat(),
            }
        return {"message_id": "accepted-id", "recipient_id": "actual-dm-recipient"}

    monkeypatch.setattr(providers, "request", request)
    frontier = []
    result = providers.send(
        {"channel": channel, "configuration": {"pageId": "page", "accountId": "ig"}},
        {"kind": "private_reply", "target": "comment", "body": "Información pedida"},
        before_send=lambda: frontier.append(True),
    )
    assert result == "accepted-id" and result.recipient_id == "actual-dm-recipient"
    assert len(frontier) == 1 and len(calls) == 2
    assert calls[1][1] == asset + "/messages"
    assert calls[1][2]["recipient"] == {"comment_id": "comment"}
    assert "messaging_type" not in calls[1][2]


def test_expired_private_and_human_frontier_never_post(monkeypatch):
    calls = []

    def request(_a, method, *_):
        calls.append(method)
        return {"id": "comment", "created_time": (NOW - timedelta(days=8)).isoformat()}

    monkeypatch.setattr(providers, "request", request)
    adapter = {"channel": "facebook", "configuration": {"pageId": "page"}}
    payload = {"kind": "private_reply", "target": "comment", "body": "Información"}
    with pytest.raises(
        providers.ProviderFailure, match="comment_private_window_closed"
    ):
        providers.send(adapter, payload, before_send=lambda: None)
    assert calls == ["GET"]
    monkeypatch.setattr(
        providers,
        "request",
        lambda *_: {"id": "comment", "created_time": NOW.isoformat()},
    )

    def human():
        raise HTTPException(409, "comment_auto_human_control")

    with pytest.raises(HTTPException):
        providers.send(adapter, payload, before_send=human)


def test_private_unknown_post_result_is_not_retried(monkeypatch):
    calls = []

    def request(_a, method, *_):
        calls.append(method)
        return (
            {"id": "comment", "created_time": NOW.isoformat()}
            if method == "GET"
            else {}
        )

    monkeypatch.setattr(providers, "request", request)
    with pytest.raises(providers.ProviderFailure) as exc:
        providers.send(
            {"channel": "facebook", "configuration": {"pageId": "page"}},
            {"kind": "private_reply", "target": "comment", "body": "Información"},
            before_send=lambda: None,
        )
    assert exc.value.uncertain and calls == ["GET", "POST"]


def test_visual_context_never_fetches_arbitrary_or_video_url():
    assert (
        private.image_part(
            {"media": [{"type": "image", "url": "https://localhost/secret"}]}
        )
        is None
    )
    assert (
        private.image_part(
            {"media": [{"type": "video", "url": "https://video.fbcdn.net/file.mp4"}]}
        )
        is None
    )


def test_private_recipient_attribution_is_account_scoped_and_applied_only_once(
    monkeypatch,
):
    from types import SimpleNamespace
    from uuid import uuid4
    from pglast import parse_sql
    from app.institutional.postgres_dialect import postgres_sql
    from app.institutional.operations_policy import layout
    from app.institutional import db

    settings = SimpleNamespace(
        postgres_deployment=True, ticket={"context": [[1, str(uuid4())]]}
    )

    def one(_c, sql, *params):
        assert sql.count("?") == len(params)
        assert "NOT EXISTS" in sql and "o.Status='confirmed'" in sql
        assert params[-2:] == ("facebook", "dm-recipient")
        parse_sql(postgres_sql(sql, layout()["tables"]).replace("%s", "NULL"))
        return {
            "CommentId": str(uuid4()),
            "ResultMetadata": json.dumps(
                {"social_decision": {"delivery": "private", "program_id": "27"}}
            ),
        }

    monkeypatch.setattr(db, "one", one)
    value = private.incoming_source(
        None,
        settings,
        {
            "Channel": "messenger",
            "ApplicationId": str(uuid4()),
            "ExternalAccountId": "page",
        },
        "dm-recipient",
    )
    assert value["program_id"] == 27 and value["authority"] == private.POLICY


def test_comment_origin_retains_program_but_does_not_claim_academic_confirmation(
    monkeypatch,
):
    from app.institutional import sales_referrals

    def one(*args):
        assert (
            "comment_source.program_id" in args[1]
            and "ORDER BY m.Sequence DESC" in args[1]
        )
        return {
            "Payload": json.dumps(
                {
                    "comment_source": {
                        "authority": private.POLICY,
                        "program_id": 27,
                        "comment_id": "original",
                    }
                }
            ),
            "MessageId": "incoming",
            "Sequence": 5,
        }

    monkeypatch.setattr(sales_referrals.db, "one", one)
    monkeypatch.setattr(sales_referrals.db, "institution", lambda _: "institution")
    value = sales_referrals.origin(None, None, "conversation", 8)
    assert value["program_id"] == 27 and value["sequence"] == 5
    assert value["authority"] == "accepted_private_reply_not_academic_confirmation"


@pytest.mark.parametrize(
    "delivery,intent,expected",
    [
        ("private", "information", True),
        ("public", "support", False),
        ("review", "complaint", None),
    ],
)
def test_worker_enqueues_one_routed_reply_without_public_dm_claim(
    monkeypatch, delivery, intent, expected
):
    from contextlib import nullcontext
    from types import SimpleNamespace
    from uuid import uuid4
    from app.institutional import (
        comment_automation as worker,
        channel_outbox,
        comment_effects,
    )

    operation, integration = str(uuid4()), str(uuid4())
    settings = SimpleNamespace(
        postgres_deployment=True, ticket={"context": [[1, str(uuid4())]]}
    )
    item, source = original()
    item["IntegrationId"] = integration
    ai = {
        "revision": 1,
        "document": {
            "provider": "gemini",
            "model": "gemini-test",
            "max_tokens": 1000,
            "comment_private_accounts": [integration],
        },
    }
    data = {"comment": operation, "version": "00"}
    statements = []

    class Cursor:
        rowcount = 1

        def execute(self, sql, *params):
            statements.append((sql, params))
            return self

        def fetchval(self):
            return 0

        def fetchone(self):
            return (1,)

    c = Cursor()
    monkeypatch.setattr(worker, "transaction", lambda *_a, **_k: nullcontext(c))

    def one(_c, sql, *_):
        if "SELECT TOP(1) OperationId" in sql:
            return {
                "OperationId": operation,
                "IntegrationId": integration,
                "ResultMetadata": json.dumps(data),
            }
        if "crm_access.Secret" in sql:
            return {
                "VersionNo": 1,
                "SecretId": str(uuid4()),
                "Nonce": b"",
                "Ciphertext": b"",
            }
        return source

    monkeypatch.setattr(worker, "one", one)
    monkeypatch.setattr(
        worker, "current", lambda *_a, **_k: (item, ai, "Información", "")
    )
    monkeypatch.setattr(worker, "comment_context", lambda *_: grounding())
    monkeypatch.setattr(worker, "provider_account", lambda *_: ({}, {}))
    monkeypatch.setattr(
        worker,
        "policy",
        lambda *_, **__: {
            "daily_requests": 20,
            "model": "gemini-test",
            "input_micros_per_million": 1,
            "output_micros_per_million": 1,
        },
    )
    monkeypatch.setattr(
        worker,
        "setting",
        lambda *_: {
            "document": {
                "daily_messages": 10,
                "daily_tokens": 100000,
                "daily_usd_micros": 100000,
            }
        },
    )
    monkeypatch.setattr(worker, "unseal", lambda *_: "fixture")
    monkeypatch.setattr(worker, "key", lambda *_: b"fixture")
    monkeypatch.setattr(worker, "reserve_budget", lambda *_: None)
    monkeypatch.setattr(
        worker.language_resilience, "snapshot", lambda *_: {"routes": [], "keys": {}}
    )
    monkeypatch.setattr(
        comment_effects,
        "call_provider",
        lambda *_: {"preview": {"caption": "PRE-ICFES"}},
    )
    monkeypatch.setattr(private, "source_time", lambda *_: NOW.isoformat())
    recorded, queued = [], []
    monkeypatch.setattr(worker, "finish", lambda *args: recorded.append(args) or True)
    monkeypatch.setattr(
        channel_outbox, "enqueue", lambda *args, **kw: queued.append((args[5], kw))
    )

    class Gateway:
        def __init__(self, *_):
            pass

        async def gemini_generation(self, _model, body, before_attempt):
            before_attempt()
            assert "delivery" in body["generationConfig"]["responseSchema"]["required"]
            return generated(intent=intent, delivery=delivery)

    assert worker.Worker(settings, Gateway).once()
    if expected is None:
        assert not queued and recorded[-1][4] == "comment_auto_review_required"
    else:
        assert len(queued) == 1
        assert bool(queued[0][0].get("privateReply")) == expected
        assert queued[0][1]["comment"] == operation


@pytest.mark.parametrize("stale", [False, True])
def test_comment_policy_saves_only_comment_fields_with_recent_authority_and_revision(
    monkeypatch, stale
):
    from contextlib import nullcontext
    from types import SimpleNamespace
    from uuid import uuid4
    from pglast import parse_sql
    from app.institutional import auth, db, settings as settings_module, store
    from app.institutional.channel_comments import CommentPolicy
    from app.institutional.operations_policy import layout
    from app.institutional.postgres_dialect import postgres_sql

    settings = SimpleNamespace(ticket={"context": [[1, str(uuid4())]]})
    body = CommentPolicy(
        operation_id=str(uuid4()),
        revision=3,
        comment_prompt="Consulta la ficha",
        comment_mode="auto",
        comment_auto_reply="",
        comment_private_accounts=[str(uuid4())],
    )
    statements, authorized = [], []

    class Cursor:
        rowcount = 1

        def execute(self, sql, *params):
            assert sql.count("?") == len(params)
            parse_sql(postgres_sql(sql, layout()["tables"]).replace("%s", "NULL"))
            statements.append((sql, params))
            return self

    monkeypatch.setattr(store, "transaction", lambda *_a, **_k: nullcontext(Cursor()))
    monkeypatch.setattr(
        auth,
        "authorize",
        lambda *_a, **kw: authorized.append(kw) or {"UserId": str(uuid4())},
    )
    monkeypatch.setattr(db, "replay", lambda *_: (b"digest", None))
    monkeypatch.setattr(db, "record_operation", lambda *_: None)
    monkeypatch.setattr(db, "audit", lambda *_a, **_k: None)
    original = {
        "model": "existing",
        "voice": {"owner_configuration": "preserved"},
        "system_prompt": "Existing instructions",
    }
    monkeypatch.setattr(
        settings_module,
        "setting",
        lambda *_: {"revision": 4 if stale else 3, "document": original},
    )
    monkeypatch.setattr(settings_module, "validate_links", lambda *_: None)
    if stale:
        with pytest.raises(HTTPException, match="revision_conflict"):
            private.save_policy(settings, {}, body)
        assert not statements
    else:
        result = private.save_policy(settings, {}, body)
        assert (
            result["revision"] == 4 and result["document"]["voice"] == original["voice"]
        )
        assert (
            result["document"]["model"] == original["model"]
            and result["document"]["system_prompt"] == original["system_prompt"]
        )
        assert len(statements) == 2
    assert authorized == [{"recent": True}]
