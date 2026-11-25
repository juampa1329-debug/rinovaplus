"""A proven local wait must not lose a response or replay uncertain effects."""
import json
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.institutional import channel_outbox as outbox
from app.institutional import channel_reservations as quota
from app.institutional import email_notifications, reply_delivery
from app.modules.channels import providers


def dispatcher(monkeypatch, failure, *, phase="guard", media=False):
    identifiers = [str(uuid4()) for _ in range(5)]
    job = dict(zip(("QueueId", "OperationId", "IntegrationId", "MessageId", "ReservationId"), identifiers))
    job.update(State="queued", LeaseId=None, ExternalId=None,
               Payload=json.dumps({"origin": "gemini_whatsapp", "kind": "chat", "target": "contact", "body": "respuesta"}))
    writes, posts = [], []
    fail_once = [True]

    class Cursor:
        rowcount = 1

        def execute(self, sql, *params):
            assert sql.count("?") == len(params)
            writes.append((sql, params))
            if sql.startswith("UPDATE crm_channels2.SendJob SET State='sending'"):
                job.update(State="sending", LeaseId=params[0])
            elif sql.startswith("UPDATE crm_channels2.SendJob SET State=?"):
                job.update(State=params[0], ExternalId=params[1], LastErrorCode=params[2], LeaseId=None)
            return self

    cursor = Cursor()

    @contextmanager
    def transaction(*args, **kwargs):
        yield cursor

    def one(c, sql, *args):
        if "SELECT TOP(1)" in sql or "SELECT State,LeaseId" in sql:
            return dict(job)
        if "SELECT * FROM crm_channels2.SendJob" in sql:
            if phase == "guard" and fail_once[0]:
                fail_once[0] = False
                raise failure
            return dict(job)
        raise AssertionError(sql)

    def send(adapter, payload, media=None, before_send=None):
        if phase == "frontier":
            before_send()
        if phase == "after_transport":
            posts.append("started")
            raise failure
        posts.append("accepted")
        return "wamid.accepted"

    monkeypatch.setattr(outbox, "transaction", transaction)
    monkeypatch.setattr(outbox, "institution", lambda _: "institution")
    monkeypatch.setattr(outbox, "rows", lambda *_: [])
    monkeypatch.setattr(outbox, "one", one)
    monkeypatch.setattr(outbox, "configuration", lambda *_: {"OutboundEnabled": True, "ModuleEnabled": True})
    adapter = {"channel": "whatsapp"}
    payload = json.loads(job["Payload"])
    if media:
        payload["mediaId"] = "audio"
        from app.institutional import channel_media
        monkeypatch.setattr(channel_media, "file_for", lambda *_: (job, {"kind": "audio"}))
    monkeypatch.setattr(outbox, "ready", lambda *_a, **_k: ({"RowVersion": b"1"}, payload, adapter, {"SecretId": "same"}))
    monkeypatch.setattr(outbox, "reserve", lambda *_: job["ReservationId"])
    monkeypatch.setattr(providers, "send", send)
    monkeypatch.setattr(email_notifications, "observe_service", lambda *_a, **_k: None)
    monkeypatch.setattr(reply_delivery, "next_typing", lambda *_: None)
    settings = SimpleNamespace(ticket={"version": "cbn-institutional-agents-p5-v1"})
    worker = outbox.Dispatcher(settings)

    def frontier(*_):
        if fail_once[0]:
            fail_once[0] = False
            raise failure

    worker.frontier = frontier
    return worker, job, writes, posts


@pytest.mark.parametrize("phase", ["guard", "frontier"])
def test_local_storage_wait_retains_job_releases_quota_then_sends_once(monkeypatch, phase):
    worker, job, writes, posts = dispatcher(monkeypatch, HTTPException(503, "storage_busy"), phase=phase)
    assert worker.once() is True
    assert job["State"] == "queued" and job["LastErrorCode"] == "outbound_storage_wait"
    assert job["LeaseId"] is None and posts == []
    assert any("DueAt=DATEADD(second,5" in sql for sql, _ in writes)
    assert any("QuotaReservation SET Status=?" in sql and params[0] == "released" for sql, params in writes)
    assert any("ProviderOperation SET Status=?" in sql and params[:2] == ("pending", "outbound_storage_wait") for sql, params in writes)
    assert worker.once() is True
    assert job["State"] == "accepted" and posts == ["accepted"]


@pytest.mark.parametrize("failure,state", [
    (HTTPException(503, "storage_busy"), "failed"),
    (providers.ProviderFailure("provider_timeout", uncertain=True), "uncertain"),
])
def test_failure_after_entering_transport_is_never_assumed_unsent(monkeypatch, failure, state):
    worker, job, writes, posts = dispatcher(monkeypatch, failure, phase="after_transport")
    worker.once()
    assert job["State"] == state and posts == ["started"]
    assert not any("DueAt=DATEADD(second,5" in sql for sql, _ in writes)


def test_media_frontier_does_not_certify_a_pre_upload_wait(monkeypatch):
    worker, job, _, posts = dispatcher(monkeypatch, HTTPException(503, "storage_busy"), phase="frontier", media=True)
    worker.once()
    assert job["State"] == "failed" and posts == []


@pytest.mark.parametrize("detail", ["send_account_changed", "gemini_whatsapp_human", "gemini_reply_context_changed"])
def test_authority_and_context_errors_remain_fenced(monkeypatch, detail):
    worker, job, _, posts = dispatcher(monkeypatch, HTTPException(409, detail))
    worker.once()
    assert job["State"] == "failed" and job["LastErrorCode"] == detail and posts == []


@pytest.mark.parametrize("channel", ["whatsapp", "instagram", "messenger"])
def test_builtin_text_contract_never_posts_when_guard_waits(monkeypatch, channel):
    request = Mock(side_effect=AssertionError("No provider message before guard"))
    monkeypatch.setattr(providers, "request", request)
    check = Mock(side_effect=HTTPException(503, "storage_busy"))
    with pytest.raises(quota.PreProviderStorageWait):
        providers.send({"channel": channel}, {"origin": "gemini_whatsapp", "kind": "chat"},
                       before_send=lambda: quota.before_text_send(check))
    request.assert_not_called()
