import json
from contextlib import nullcontext
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.institutional import comment_threads as threads
from app.institutional.channel_comments import public_comment


@pytest.mark.parametrize("source", ["account", "instagram_scoped", "stored", "echo"])
def test_recognizes_only_evidenced_account_comments(source):
    value = {"AuthorExternalId": "cbn", "Payload": "{}"}
    account = {"ExternalAccountId": "someone-else"}
    if source == "account":
        account["ExternalAccountId"] = "cbn"
    if source == "instagram_scoped":
        value["Payload"] = json.dumps({"provider": {"self_ig_scoped_id": "cbn"}})
    if source == "stored":
        value["Payload"] = json.dumps({"_crm": {"is_self": True}})
    if source == "echo":
        value["SelfComment"] = True
    assert threads.is_account_comment(value, account)
    assert not threads.is_account_comment(
        {
            "AuthorExternalId": "a-person",
            "Payload": '{"provider":{"from":{"name":"CBN"}}}',
        },
        account,
    )


def test_thread_identity_separates_accounts_posts_and_people():
    row = {"IntegrationId": "one", "thread_post": "post", "thread_person": "juan"}
    original = threads.group_key(row)
    for key in row:
        assert threads.group_key({**row, key: "another"}) != original
    assert threads.group_key(dict(row)) == original


def test_provider_echo_and_queue_appear_once_and_failed_reply_is_retained():
    now = datetime(2026, 11, 18, 12)
    echo = {
        "CommentId": uuid4(),
        "ExternalId": "meta-reply",
        "Body": "Respuesta de CBN",
        "ReceivedAt": now,
    }
    job = {
        "QueueId": uuid4(),
        "ExternalId": "meta-reply",
        "Payload": '{"body":"Respuesta de CBN"}',
        "CreatedAt": now,
        "State": "accepted",
    }
    failed = {
        **job,
        "QueueId": uuid4(),
        "ExternalId": None,
        "State": "failed",
        "Payload": '{"body":"Otro intento"}',
    }
    history = threads.reply_history([echo], [job, failed], "CBN")
    assert len(history) == 2
    assert sum(r["body"] == "Respuesta de CBN" for r in history) == 1
    assert next(r for r in history if r["body"] == "Otro intento")["state"] == "failed"
    assert all(r["author"] == "CBN" for r in history)


def test_group_read_requires_authority_before_any_database_query(monkeypatch):
    monkeypatch.setattr(
        threads, "transaction", lambda *_a, **_kw: nullcontext(object())
    )

    def denied(*_a):
        raise HTTPException(403, "permission_denied")

    monkeypatch.setattr(threads, "authorize", denied)
    monkeypatch.setattr(
        threads, "thread_cte", lambda *_a: pytest.fail("query before permission")
    )
    with pytest.raises(HTTPException) as e:
        threads.Threads(None).read(None)
    assert e.value.status_code == 403


def test_group_search_keeps_untrusted_text_in_parameters_and_counts_groups(monkeypatch):
    queries = []

    class Cursor:
        def native(self, sql, *params):
            queries.append((sql, params))
            return self

        def fetchval(self):
            return 51

    c = Cursor()
    monkeypatch.setattr(threads, "transaction", lambda *_a, **_kw: nullcontext(c))
    monkeypatch.setattr(threads, "authorize", lambda *_a: None)
    monkeypatch.setattr(threads, "institution", lambda *_a: "institution")
    monkeypatch.setattr(threads, "thread_cte", lambda *_a: "WITH fixture AS () ")
    monkeypatch.setattr(threads, "table", lambda *_a: "jobs")

    def rows(cursor, sql, *params):
        queries.append((sql, params))
        return []

    monkeypatch.setattr(threads, "native_rows", rows)
    attack = "%' OR 1=1 --"
    result = threads.Threads(None).read(None, q=attack, channel="instagram", offset=25)
    assert result == {"items": [], "total": 51, "has_more": True, "view": "threads"}
    for sql, params in queries:
        assert attack not in sql and params[0] == "institution" and attack in params
        assert "GROUP BY m.integrationid,m.thread_post,m.thread_person" in sql


def test_account_reply_is_labeled_and_cannot_receive_another_reply():
    row = {
        "CommentId": uuid4(),
        "IntegrationId": uuid4(),
        "Channel": "instagram",
        "DisplayName": "Instagram · CBN",
        "ExternalAccountId": "cbn",
        "AuthorExternalId": "cbn",
        "ExternalId": "reply",
        "Body": "Nosotros respondimos",
        "ReceivedAt": datetime(2026, 11, 18),
        "RowVersion": b"version1",
        "Payload": "{}",
        "RequestedStatus": "connected",
        "VerifiedStatus": "verified",
    }
    result = public_comment(row)
    assert result["is_self"] and result["author"] == "Instagram · CBN"
    assert not result["capabilities"]["public_comment_reply"]


def test_account_table_names_are_validated_not_composed_from_request_values():
    settings = SimpleNamespace(
        ticket={"table_map": {"crm_channels2.SocialComment": "dbo.SafeTable"}}
    )
    assert (
        threads.table(settings, "crm_channels2.SocialComment")
        == 'rinovaplus_crm."safetable"'
    )
    settings.ticket["table_map"]["crm_channels2.SocialComment"] = "dbo.unsafe;DROP"
    with pytest.raises(ValueError):
        threads.table(settings, "crm_channels2.SocialComment")
