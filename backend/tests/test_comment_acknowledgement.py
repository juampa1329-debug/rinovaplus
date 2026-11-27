import json
from contextlib import nullcontext
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.institutional import comment_acknowledgement as ack, comment_automation as auto
from app.modules.agents.domain import digest


@pytest.fixture
def fixture(monkeypatch):
    monkeypatch.setattr(ack, "institution", lambda _: "institution")
    integration, comment, queue = [str(uuid4()) for _ in range(3)]
    job = {"IntegrationId": integration, "CommentId": comment, "QueueId": str(uuid4())}
    job["OperationId"] = ack.operation(None, comment)
    payload = {"origin": auto.ORIGIN, "body": ack.TEXT, "privateAcknowledgementOf": queue}
    source = {"Payload": json.dumps({"origin": auto.ORIGIN, "privateReply": True, "body": "Información revisada"}),
              "State": "accepted", "ExternalId": "provider-receipt", "ResultMetadata": json.dumps({
                  "generated_text": "Información revisada", "source_text_digest": digest("Precio")})}
    original = {"Body": "Precio", "Payload": '{"_crm":{"state":"new","control_mode":"ai"}}'}
    def read(_c, query, *args):
        assert query.count("?") == len(args)
        return source if "SendJob q" in query else original
    monkeypatch.setattr(ack, "one", read)
    ai = {"enabled": True, "comment_mode": "auto", "comment_private_accounts": [integration]}
    monkeypatch.setattr(ack, "setting", lambda *_: {"document": ai})
    cursor = SimpleNamespace(execute=lambda query, *args: SimpleNamespace(fetchone=lambda: None, fetchval=lambda: "ai"))
    return cursor, job, payload, source, original, ai


def test_public_ack_requires_real_accepted_dm_and_unchanged_comment(fixture):
    cursor, job, payload, *_ = fixture
    ack.authorize(cursor, None, job, payload)
    auto.authorize_send(cursor, None, job, payload)  # Same guard used at dispatch.


@pytest.mark.parametrize("state", ["queued", "sending", "uncertain", "failed", "cancelled"])
def test_no_public_claim_before_durable_acceptance(fixture, state):
    cursor, job, payload, source, *_ = fixture
    source["State"] = state
    with pytest.raises(HTTPException, match="comment_auto_ack_without_acceptance"):
        ack.authorize(cursor, None, job, payload)


@pytest.mark.parametrize("change", ["edited", "human", "disabled", "unapproved_account", "no_external_id", "wrong_text", "wrong_operation", "other_public"])
def test_ack_cannot_bypass_control_identity_policy_or_deduplication(fixture, change):
    cursor, job, payload, source, original, ai = fixture
    if change == "edited": original["Body"] = "No quiero información"
    if change == "human": original["Payload"] = '{"_crm":{"control_mode":"human"}}'
    if change == "disabled": ai["enabled"] = False
    if change == "unapproved_account": ai["comment_private_accounts"] = []
    if change == "no_external_id": source["ExternalId"] = None
    if change == "wrong_text": payload["body"] = "Cualquier promoción"
    if change == "wrong_operation": job["OperationId"] = str(uuid4())
    if change == "other_public": cursor.execute = lambda *_: SimpleNamespace(fetchone=lambda: (1,))
    with pytest.raises(HTTPException): ack.authorize(cursor, None, job, payload)


def test_acceptance_hook_uses_stable_operation_and_never_replays_private(fixture, monkeypatch):
    from app.institutional import channel_operations, channel_outbox, store
    cursor, job, payload, *_ = fixture
    calls = []
    monkeypatch.setattr(store, "transaction", lambda *_a, **_k: nullcontext(cursor))
    monkeypatch.setattr(channel_operations, "account", lambda *_: {"IntegrationId": job["IntegrationId"]})
    monkeypatch.setattr(channel_outbox, "enqueue", lambda *a, **kw: calls.append((a[4], a[5], kw)))
    outgoing = {"origin": auto.ORIGIN, "privateReply": True}
    ack.after_acceptance(None, job, outgoing)
    ack.after_acceptance(None, job, outgoing)
    assert calls[0] == calls[1]  # C10 idempotency is scoped to this exact operation.
    assert calls[0][0] == job["OperationId"] and "privateReply" not in calls[0][1]
    assert calls[0][1]["privateAcknowledgementOf"] == job["QueueId"]
    ack.after_acceptance(None, job, {"origin": auto.ORIGIN})
    assert len(calls) == 2
