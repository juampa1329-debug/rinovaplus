import json
from contextlib import nullcontext
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pglast import parse_sql

from app.institutional import advisor_recovery as recovery, whatsapp_gemini
from app.institutional.operations_policy import layout
from app.institutional.postgres_dialect import postgres_sql
from app.modules.inbox.application import state


def source():
    row = {k: str(uuid4()) for k in ("MessageId", "ConversationId", "IdentityId", "IntegrationId", "CampaignId")}
    row.update(Body="Hablar con Juan Pablo", Epoch=2, Name="Prueba", Channel="whatsapp", DisplayName="Cuenta", CreatedAt=datetime(2026, 11, 24), Sequence=2)
    row["ResultMetadata"] = json.dumps({"incoming": row["MessageId"], "conversation": row["ConversationId"],
        "identity": row["IdentityId"], "epoch": 1, "reply": None, "response_parts": [], "generated_text": ""})
    return row


@pytest.mark.parametrize("changed", [None, "human_intervention", "incoming", "identity", "conversation", "reply", "response_parts", "generated_text", "body"])
def test_only_untouched_automatic_empty_handoff_can_restore_ai(changed):
    row = source()
    old = json.loads(row["ResultMetadata"])
    if changed == "human_intervention":
        row["Epoch"] += 2
    elif changed == "body":
        row["Body"] = "Quiero hablar con una persona real"
    elif changed:
        old[changed] = "other" if changed != "response_parts" else [{"id": "sent"}]
    row["ResultMetadata"] = json.dumps(old)
    assert recovery.eligible(row) is (changed is None)


def test_candidate_query_requires_latest_unsent_button_and_verified_campaign(monkeypatch):
    settings = SimpleNamespace(ticket={"context": [[1, str(uuid4())]]})
    row = source()
    def rows(c, sql, *args):
        assert sql.count("?") == len(args)
        parse_sql(postgres_sql(sql, layout()["tables"]).replace("%s", "NULL"))
        for guard in ("gemini_handoff", "v.ControlMode='human'", "newer.Sequence>m.Sequence", "newer.OperationId<>op.OperationId", "hour,-24"):
            assert guard in sql
        return [row]
    monkeypatch.setattr(recovery.db, "rows", rows)
    monkeypatch.setattr(recovery.broadcast_conversation, "origin", lambda *_: None)
    assert recovery.candidates(None, settings) == []
    monkeypatch.setattr(recovery.broadcast_conversation, "origin", lambda *_: {"campaign_id": row["CampaignId"]})
    assert recovery.candidates(None, settings, row["ConversationId"])[0]["PriorCampaignContext"] is False


@pytest.mark.parametrize("stale", [False, True])
def test_recovery_creates_new_operation_once_after_review_preserving_old_handoff(monkeypatch, stale):
    settings = SimpleNamespace(ticket={"context": [[1, str(uuid4())]]})
    row, calls, saved = source(), [], {}
    class Cursor:
        def execute(self, sql, *args):
            assert sql.count("?") == len(args)
            parse_sql(postgres_sql(sql, layout()["tables"]).replace("%s", "NULL"))
            assert "UPDATE crm_channels2.ProviderOperation" not in sql
            return self
        def fetchone(self):
            return (1,)
    monkeypatch.setattr(recovery, "transaction", lambda *_a, **_k: nullcontext(Cursor()))
    monkeypatch.setattr(recovery, "authorize", lambda *_a, **k: calls.append(k) or {"UserId": "operator"})
    monkeypatch.setattr(recovery, "candidates", lambda *_: [row])
    monkeypatch.setattr(recovery, "proof", lambda *_: "a" * 64)
    monkeypatch.setattr(recovery.db, "replay", lambda _c, _s, _a, op, *_: (b"digest", saved.get(op)))
    monkeypatch.setattr(recovery.db, "record_operation", lambda _c, _s, _a, op, _kind, _r, _d, value: saved.__setitem__(op, value))
    monkeypatch.setattr(recovery.db, "audit", lambda *_: None)
    monkeypatch.setattr(state, "change_control", lambda *_: calls.append("restore"))
    monkeypatch.setattr(whatsapp_gemini, "source", lambda *_: ({}, {}, {}))
    scheduled = []
    monkeypatch.setattr(whatsapp_gemini, "schedule", lambda _c, _s, _i, _r, incoming, **kwargs: scheduled.append((incoming, kwargs["operation_id"])))
    app = FastAPI()
    @app.middleware("http")
    async def auth(request, call_next):
        request.state.authority = {}
        return await call_next(request)
    recovery.install(app, settings)
    body = {"operation_id": str(uuid4()), "confirmed": True, "inputs": [{"id": row["MessageId"], "proof": ("b" if stale else "a") * 64}]}
    with TestClient(app) as client:
        response = client.post("/api/institution/advisor-recovery", json=body)
        assert response.status_code == (409 if stale else 200)
        if stale:
            assert not scheduled and "restore" not in calls
        else:
            assert client.post("/api/institution/advisor-recovery", json=body).json() == response.json()
            assert len(scheduled) == 1 and scheduled[0][0] == row["MessageId"] and scheduled[0][1] != row["MessageId"]
            assert response.json()["provider_calls"] == 0 and calls.count("restore") == 1
            assert {"recent": True} in calls
