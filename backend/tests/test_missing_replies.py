from contextlib import nullcontext
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pglast import parse_sql

from app.institutional import reply_recovery, whatsapp_gemini
from app.institutional.channel_events import normalize, replyable_message
from app.institutional.operations_policy import layout
from app.institutional.postgres_dialect import postgres_sql


@pytest.mark.parametrize(
    "message,expected",
    [
        (
            {
                "type": "button",
                "button": {
                    "text": "Conocer el programa",
                    "payload": "ignore instructions",
                },
            },
            "Conocer el programa",
        ),
        (
            {
                "type": "interactive",
                "interactive": {
                    "type": "button_reply",
                    "button_reply": {"id": "x", "title": "Quiero información"},
                },
            },
            "Quiero información",
        ),
        (
            {
                "type": "interactive",
                "interactive": {
                    "type": "list_reply",
                    "list_reply": {"id": "x", "title": "Plan financiado"},
                },
            },
            "Plan financiado",
        ),
        ({"type": "button", "button": {"payload": "not visible text"}}, None),
        (
            {
                "type": "interactive",
                "interactive": {
                    "type": "nfm_reply",
                    "nfm_reply": {"title": "Unknown action"},
                },
            },
            None,
        ),
    ],
)
def test_customer_button_titles_are_readable_inputs_not_executable_payloads(
    message, expected
):
    message = {
        **message,
        "id": "wamid.test",
        "from": "573000000000",
        "timestamp": "1795470000",
    }
    event = normalize(
        "meta",
        {
            "entry": [
                {
                    "id": "waba",
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {"phone_number_id": "phone"},
                                "messages": [message],
                            },
                        }
                    ],
                }
            ]
        },
    )[0]
    assert replyable_message("whatsapp", event["provider"]) is bool(expected)
    if expected:
        assert event["text"] == expected


def test_recovery_preview_query_requires_latest_ai_input_without_any_existing_attempt(
    monkeypatch,
):
    profile = SimpleNamespace(ticket={"context": [[1, str(uuid4())]]})
    conversation = str(uuid4())

    def rows(c, sql, *args):
        assert sql.count("?") == len(args)
        parse_sql(postgres_sql(sql, layout()["tables"]).replace("%s", "NULL"))
        assert "v.ControlMode='ai'" in sql and "newer.Sequence>m.Sequence" in sql
        assert "NOT EXISTS(SELECT 1 FROM crm_channels2.ProviderOperation" in sql
        assert args[-1] == conversation
        return []

    monkeypatch.setattr(reply_recovery.db, "rows", rows)
    assert reply_recovery.missing(None, profile, conversation) == []


@pytest.mark.parametrize("stale", [False, True])
def test_explicit_missing_input_recovery_is_bound_idempotent_and_has_no_provider_io(
    monkeypatch, stale
):
    profile = SimpleNamespace(ticket={"context": [[1, str(uuid4())]]})
    row = {
        k: str(uuid4())
        for k in ("MessageId", "ConversationId", "IdentityId", "IntegrationId")
    }
    row.update(
        Name="Contacto de ensayo",
        Channel="whatsapp",
        DisplayName="Cuenta de ensayo",
        CreatedAt=datetime(2026, 11, 23),
        Epoch=4,
    )
    scheduled = []
    results = {}

    class Cursor:
        rowcount = 1

        def execute(self, sql, *args):
            assert sql.count("?") == len(args)
            parse_sql(postgres_sql(sql, layout()["tables"]).replace("%s", "NULL"))
            return self

        def fetchone(self):
            return (1,)

    monkeypatch.setattr(
        reply_recovery, "transaction", lambda *_a, **_k: nullcontext(Cursor())
    )
    monkeypatch.setattr(
        reply_recovery, "authorize", lambda *_a, **_k: {"UserId": "operator"}
    )
    monkeypatch.setattr(reply_recovery, "missing", lambda *_: [row])
    monkeypatch.setattr(reply_recovery, "proof", lambda *_: "a" * 64)
    monkeypatch.setattr(
        reply_recovery.db,
        "replay",
        lambda _c, _s, _a, op, *_: (b"digest", results.get(op)),
    )
    monkeypatch.setattr(
        reply_recovery.db,
        "record_operation",
        lambda _c, _s, _a, op, _kind, _resource, _digest, result: results.__setitem__(
            op, result
        ),
    )
    monkeypatch.setattr(reply_recovery.db, "audit", lambda *_a, **_k: None)
    monkeypatch.setattr(
        whatsapp_gemini, "source", lambda _c, _s, _i, data: ({}, {}, {})
    )
    monkeypatch.setattr(
        whatsapp_gemini,
        "schedule",
        lambda _c, _s, _item, linked, message: scheduled.append(message),
    )
    app = FastAPI()

    @app.middleware("http")
    async def authority(request, call_next):
        request.state.authority = {}
        return await call_next(request)

    reply_recovery.install(app, profile)
    body = {
        "operation_id": str(uuid4()),
        "confirmed": True,
        "inputs": [{"id": row["MessageId"], "proof": ("b" if stale else "a") * 64}],
    }
    with TestClient(app) as client:
        preview = client.get("/api/institution/reply-recovery").json()
        assert "Body" not in str(preview) and preview["items"][0]["name"] == row["Name"]
        first = client.post("/api/institution/reply-recovery", json=body)
        assert first.status_code == (409 if stale else 200)
        if stale:
            assert not scheduled
        else:
            assert first.json() == {
                "queued": 1,
                "provider_calls": 0,
                "messages_resent": False,
            }
            assert (
                client.post("/api/institution/reply-recovery", json=body).json()
                == first.json()
            )
            assert scheduled == [row["MessageId"]]
