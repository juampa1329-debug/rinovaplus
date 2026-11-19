import json
from contextlib import nullcontext
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pglast import parse_sql

from app.institutional import comment_edits as edits
from app.institutional.comment_threads import reply_history
from app.institutional.operations_policy import layout
from app.institutional.postgres_dialect import postgres_sql
from app.modules.channels import providers


@pytest.mark.parametrize("problem", ["none", "owner", "changed", "post_timeout", "readback", "readback_error", "rejected"])
def test_provider_checks_owner_and_text_and_requires_exact_readback(monkeypatch, problem):
    calls = []
    def request(_adapter, method, path, body=None, params=None):
        calls.append((method, path, body, params))
        assert path == "123_456"
        if len(calls) == 1:
            return {"id": path, "message": "External edit" if problem == "changed" else "Antes", "from": {"id": "other" if problem == "owner" else "page"}}
        if method == "POST":
            if problem in {"post_timeout", "rejected"}:
                raise providers.ProviderFailure("network_or_permission", uncertain=problem == "post_timeout")
            return {"success": True}
        if problem == "readback_error":
            raise providers.ProviderFailure("provider_unavailable")
        return {"id": path, "message": "Antes" if problem == "readback" else "Después 😊"}
    monkeypatch.setattr(providers, "request", request)
    if problem == "none":
        edits.edit_provider({"external_account_id": "page"}, "123_456", "Antes", "Después 😊")
        assert calls[1] == ("POST", "123_456", {"message": "Después 😊"}, None)
    else:
        with pytest.raises(providers.ProviderFailure) as error:
            edits.edit_provider({"external_account_id": "page"}, "123_456", "Antes", "Después 😊")
        assert error.value.uncertain == (problem in {"post_timeout", "readback", "readback_error"})
        assert len(calls) == (1 if problem in {"owner", "changed"} else 2 if problem in {"post_timeout", "rejected"} else 3)


@pytest.mark.parametrize("source", ["meta", "crm"])
@pytest.mark.parametrize("outcome", ["confirmed", "uncertain", "failed"])
def test_edit_is_replay_safe_and_original_job_stays_immutable(monkeypatch, source, outcome):
    identity, integration, actor_id, inst, operation = [str(uuid4()) for _ in range(5)]
    settings = SimpleNamespace(ticket={"context": [[1, inst]]})
    social = {"CommentId": identity, "IntegrationId": integration, "RowVersion": b"version1", "ExternalId": "123_456", "Body": "Antes", "Payload": '{"_crm":{"is_self":true}}', "AuthorExternalId": "page"}
    job = {"QueueId": identity, "CommentId": str(uuid4()), "IntegrationId": integration, "RowVersion": b"version1", "ExternalId": "123_456", "Kind": "comment_reply", "State": "accepted", "Payload": '{"body":"Antes","fixed_digest":"original"}'}
    item = {"IntegrationId": integration, "ApplicationId": str(uuid4()), "Channel": "facebook", "ExternalAccountId": "page", "RequestedStatus": "connected", "VerifiedStatus": "verified", "RowVersion": b"version1"}
    intent, statements, calls = {}, [], []
    def check(sql, args):
        assert sql.count("?") == len(args)
        parse_sql(postgres_sql(sql, layout()["tables"]).replace("%s", "NULL"))
    class Cursor:
        rowcount = 1
        def execute(self, sql, *args):
            check(sql, args)
            statements.append((sql, args))
            if sql.startswith("INSERT crm_channels2.ProviderOperation"):
                intent.update(Action="comment_edit", ActorRef=actor_id, RequestDigest=b"digest", Status="running", ResultCode=None)
            if sql.startswith("UPDATE crm_channels2.ProviderOperation"):
                intent.update(Status=args[0], ResultCode=args[1])
            if sql.startswith("UPDATE crm_channels2.SocialComment"):
                social.update(Payload=args[0], Body=args[1])
            if sql.startswith("UPDATE crm_channels2.SendJob"):
                job["Payload"] = args[0]
            return self
    def one(_c, sql, *args):
        check(sql, args)
        if "ProviderOperation" in sql:
            return None if "JSON_VALUE" in sql else intent or None
        if "SocialComment" in sql:
            return social
        return job
    monkeypatch.setattr(edits, "transaction", lambda *_a, **_k: nullcontext(Cursor()))
    monkeypatch.setattr(edits, "one", one)
    monkeypatch.setattr(edits, "authorize", lambda *_a: {"UserId": actor_id})
    monkeypatch.setattr(edits, "account", lambda *_a: item)
    monkeypatch.setattr(edits, "configuration", lambda *_a: {"ModuleEnabled": True, "OutboundEnabled": True})
    monkeypatch.setattr(edits, "bound_hash", lambda *_a: b"digest")
    monkeypatch.setattr(edits, "provider_account", lambda *_a: ({}, 1))
    def transport(*args):
        calls.append(args)
        if outcome != "confirmed":
            raise providers.ProviderFailure("test_failure", uncertain=outcome == "uncertain")
    service = edits.Edits(settings, transport)
    request = edits.Edit(operation_id=operation, source=source, revision=edits.revision("Antes"), body="Después 😊")
    assert service.perform(None, identity, request)["status"] == outcome
    assert service.perform(None, identity, request)["status"] == outcome
    assert len(calls) == 1
    assert json.loads(job["Payload"])["body"] == "Antes"
    assert json.loads(job["Payload"])["fixed_digest"] == "original"
    if outcome == "confirmed":
        assert social["Body"] == "Después 😊"
        assert edits.presentation(job, "crm")[0] == "Después 😊"
        assert edits.presentation(social, "meta")[1][0]["previous"] == "Antes"
        social["ReceivedAt"] = job["CreatedAt"] = datetime(2026, 11, 19)
        result = reply_history([social], [job], "CBN", "facebook")
        assert len(result) == 1 and result[0]["edit"]["supported"]
        assert result[0]["body"] == "Después 😊"
    else:
        assert social["Body"] == "Antes" and not edits.presentation(job, "crm")[1]


@pytest.mark.parametrize("problem,code", [("other_author", "comment_edit_own_only"), ("instagram", "comment_edit_unsupported_by_provider"), ("queued", "comment_edit_published_required"), ("deleted", "comment_source_unavailable"), ("missing_id", "comment_edit_published_required")])
def test_only_own_published_facebook_content_can_be_edited(monkeypatch, problem, code):
    row = {"IntegrationId": str(uuid4()), "ExternalId": None if problem == "missing_id" else "123", "Payload": json.dumps({"_crm": {"state": "deleted" if problem == "deleted" else "new"}}), "AuthorExternalId": "other" if problem == "other_author" else "page", "Kind": "comment_reply", "CommentId": str(uuid4()), "State": "queued"}
    monkeypatch.setattr(edits, "one", lambda _c, sql, *_a: None if "TOP(1)" in sql else row)
    monkeypatch.setattr(edits, "account", lambda *_a: {"Channel": "instagram" if problem == "instagram" else "facebook", "ExternalAccountId": "page", "IntegrationId": row["IntegrationId"]})
    settings = SimpleNamespace(ticket={"context": [[1, str(uuid4())]]})
    with pytest.raises(HTTPException) as error:
        edits.load(None, settings, str(uuid4()), "crm" if problem == "queued" else "meta")
    assert error.value.detail == code


@pytest.mark.parametrize("observed", ["Antes", "Después", "Cambio desde Facebook"])
def test_uncertain_result_can_be_reconciled_without_another_provider_post(monkeypatch, observed):
    inst, integration, identity, operation, actor = [str(uuid4()) for _ in range(5)]
    settings = SimpleNamespace(ticket={"context": [[1, inst]]})
    row = {"CommentId": identity, "Body": "Antes", "Payload": "{}", "RowVersion": b"version1", "ExternalId": "123"}
    item = {"IntegrationId": integration, "ExternalAccountId": "page", "RowVersion": b"version1"}
    intent = {"Action": "comment_edit", "IntegrationId": integration, "Status": "uncertain", "ResultMetadata": '{"external_id":"123","previous":"Antes","body":"Después"}'}
    writes, calls = [], []
    class Cursor:
        def execute(self, sql, *args):
            assert sql.count("?") == len(args)
            parse_sql(postgres_sql(sql, layout()["tables"]).replace("%s", "NULL"))
            writes.append((sql, args))
    monkeypatch.setattr(edits, "transaction", lambda *_a, **_k: nullcontext(Cursor()))
    monkeypatch.setattr(edits, "authorize", lambda *_a: {"UserId": actor})
    monkeypatch.setattr(edits, "load", lambda *_a: (row, item))
    monkeypatch.setattr(edits, "one", lambda *_a: intent)
    monkeypatch.setattr(edits, "provider_account", lambda *_a: ({}, 1))
    monkeypatch.setattr(edits, "write_projection", lambda *args: calls.append(args))
    def get(_adapter, method, target, params):
        assert method == "GET" and target == "123"
        return {"id": target, "message": observed, "from": {"id": "page"}}
    monkeypatch.setattr(providers, "request", get)
    result = edits.Edits(settings).reconcile(None, identity, edits.Review(operation_id=operation, source="meta"))
    assert result["status"] == ("confirmed" if observed == "Después" else "failed")
    assert calls[0][4] == observed
    assert len(writes) == 1 and "ProviderOperation" in writes[0][0]


def test_another_accounts_operation_cannot_be_reconciled(monkeypatch):
    settings = SimpleNamespace(ticket={"context": [[1, str(uuid4())]]})
    monkeypatch.setattr(edits, "transaction", lambda *_a, **_k: nullcontext(None))
    monkeypatch.setattr(edits, "authorize", lambda *_a: {"UserId": str(uuid4())})
    monkeypatch.setattr(edits, "load", lambda *_a: ({"ExternalId": "123"}, {"IntegrationId": str(uuid4())}))
    monkeypatch.setattr(edits, "one", lambda *_a: {"Action": "comment_edit", "IntegrationId": str(uuid4()), "ResultMetadata": '{"external_id":"123"}'})
    monkeypatch.setattr(providers, "request", lambda *_a, **_k: pytest.fail("No provider call for a foreign operation"))
    with pytest.raises(HTTPException) as error:
        edits.Edits(settings).reconcile(None, str(uuid4()), edits.Review(operation_id=str(uuid4()), source="meta"))
    assert error.value.status_code == 404
