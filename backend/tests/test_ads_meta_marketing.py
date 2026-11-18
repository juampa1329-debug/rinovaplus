"""Marketing reads, honest metrics and local draft safeguards; no provider writes."""

import json
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.institutional.ads_meta_provider import (
    MetaReader,
    metrics,
    creative,
    validate_period,
)
from app.institutional.ads_marketing import Marketing, Draft, Sync, Complete, draft_issues
from app.institutional import ads_marketing as module
from app.institutional import channel_oauth


def fixture_transport(path, params):
    if path == "act_123":
        return dict(
            id="act_123", name="CBN", currency="COP", timezone_name="America/Bogota"
        )
    if path.endswith("/insights"):
        row = dict(
            date_start="2026-11-01",
            spend="120",
            clicks="12",
            impressions="1200",
            reach="700",
            actions=[
                dict(action_type="lead", value="3"),
                dict(action_type="offsite_conversion.fb_pixel_lead", value="3"),
            ],
        )
        if params.get("level") == "ad":
            row.update(ad_id="33", campaign_id="11", adset_id="22")
        return {"data": [row]}
    return {"data": []}


def test_snapshot_uses_account_reach_and_deduplicates_lead_aliases():
    calls = []

    def transport(path, params):
        calls.append((path, params))
        return fixture_transport(path, params)

    value = MetaReader("private", "v25.0", transport=transport).snapshot(
        "123", "2026-11-01", "2026-11-02"
    )
    assert value["totals"]["leads"] == 3
    assert value["totals"]["reach"] == 700
    assert value["totals"]["cpl"] == 40
    assert value["totals"]["ctr"] == 1
    assert value["provider_writes"] is False
    assert len(calls) == 7 and all(p.startswith("act_123") for p, _ in calls)
    assert "private" not in json.dumps(value)


def test_zero_activity_distinct_from_failure():
    def empty(path, params):
        return fixture_transport(path, params) if path == "act_123" else {"data": []}

    value = MetaReader("t", "v25.0", transport=empty).snapshot(
        "123", "2026-11-01", "2026-11-02"
    )
    assert value["no_delivery"] and value["totals"]["spend"] == 0
    assert value["totals"]["cpl"] is None
    with pytest.raises(HTTPException, match="ads_meta_permission_required"):
        MetaReader(
            "t",
            "v25.0",
            transport=lambda *a: {"error": {"code": 200, "message": "secret"}},
        ).accounts()


def test_reads_526_ads_in_bounded_pages_without_truncation():
    requests = []
    def transport(path, params):
        requests.append(params)
        page = int(params.get("after", "0"))
        return {"data": [{"id": str(v)} for v in range(page * 250, min(526, (page + 1) * 250))],
                "paging": {"next": "ignored", "cursors": {"after": str(page + 1)}} if page < 2 else {}}
    result = MetaReader("private", "v27.0", transport=transport).edge("act_123/ads", fields="id")
    assert len(result) == 526
    assert len({v["id"] for v in result}) == 526
    assert len(requests) == 3 and all(v["limit"] == 250 for v in requests)
    with pytest.raises(HTTPException, match="ads_meta_scope_limit"):
        MetaReader("private", "v27.0", transport=lambda *a: {"data": [{"id": "1"}] * 1001}).edge("act_123/ads")


@pytest.mark.parametrize(
    "code,status,detail",
    [
        (190, 409, "ads_meta_token_expired"),
        (4, 429, "ads_meta_rate_limited"),
        (10, 403, "ads_meta_permission_required"),
        (100, 502, "ads_meta_request_rejected"),
    ],
)
def test_provider_errors_are_actionable_without_raw_secrets(code, status, detail):
    with pytest.raises(HTTPException) as error:
        MetaReader(
            "t",
            "v25.0",
            transport=lambda *a: {"error": {"code": code, "message": "private-token"}},
        ).accounts()
    assert (error.value.status_code, error.value.detail) == (status, detail)


def test_pagination_never_follows_arbitrary_next_url():
    paths = []

    def transport(path, params):
        paths.append(path)
        return (
            {
                "data": [],
                "paging": {
                    "next": "https://attacker.invalid/token",
                    "cursors": {"after": "cursor"},
                },
            }
            if "after" not in params
            else {"data": []}
        )

    assert MetaReader("t", "v25.0", transport=transport).accounts() == []
    assert paths == ["me/adaccounts", "me/adaccounts"]
    with pytest.raises(HTTPException):
        MetaReader(
            "t",
            "v25.0",
            transport=lambda *a: {
                "data": [],
                "paging": {"next": "url", "cursors": "bad"},
            },
        ).accounts()


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1", "10000000000000000"])
def test_bad_metrics_are_not_presented_as_zero(value):
    with pytest.raises(HTTPException):
        metrics({"spend": value})


def test_missing_denominators_and_malformed_creative():
    assert metrics({"spend": "0", "clicks": "0", "impressions": "0"})["cpc"] is None
    assert metrics({})["spend"] is None
    assert creative({"object_story_spec": "bad"})["body"] == ""
    assert "access_token" not in creative({"access_token": "private"})


def test_invalid_period_and_daily_dates_fail_closed():
    with pytest.raises(HTTPException):
        validate_period("2026-11-02", "2026-11-01")
    with pytest.raises(HTTPException):
        validate_period("2026-01-01", "2026-11-01")

    def bad(path, params):
        return (
            {"data": [{"date_start": "wrong"}]}
            if params.get("time_increment")
            else fixture_transport(path, params)
        )

    with pytest.raises(HTTPException, match="ads_meta_invalid_response"):
        MetaReader("t", "v25.0", transport=bad).snapshot(
            "123", "2026-11-01", "2026-11-02"
        )


def test_draft_review_requires_same_account_targets_and_parent():
    snapshot = {"campaigns": [{"id": "11"}], "adsets": [], "ads": []}
    value = Draft(
        operation_id="00000000-0000-4000-8000-000000000001",
        name="Propuesta",
        entity="adset",
        parent_id="11",
    ).model_dump()
    assert len(draft_issues(value, snapshot)) == 1
    value["daily_budget_cents"] = 100
    assert draft_issues(value, snapshot) == []
    value.update(mode="edit", target_id="999", parent_id="888")
    assert len(draft_issues(value, snapshot)) == 2


def test_newer_failed_review_invalidates_prior_success(monkeypatch):
    service = Marketing(SimpleNamespace())

    @contextmanager
    def tx(*a, **kw):
        yield Mock(), {}

    service.ads.tx = tx
    monkeypatch.setattr(module, "account", lambda *a: {})
    monkeypatch.setattr(module, "institution", lambda *a: "institution")
    monkeypatch.setattr(module, "latest", lambda *a: ({}, "snapshot"))
    records = [
        [
            {
                "Document": json.dumps(
                    {"id": "draft", "revision": 1, "review_valid": False}
                )
            }
        ],
        [
            {
                "Document": json.dumps(
                    {
                        "draft_id": "draft",
                        "revision": 1,
                        "snapshot_id": "snapshot",
                        "reviewed": False,
                    }
                )
            },
            {
                "Document": json.dumps(
                    {
                        "draft_id": "draft",
                        "revision": 1,
                        "snapshot_id": "snapshot",
                        "reviewed": True,
                    }
                )
            },
        ],
    ]
    monkeypatch.setattr(module, "rows", lambda *a: records.pop(0))
    assert service.drafts({}, "account")["items"][0]["review_valid"] is False


def test_read_oauth_does_not_discover_or_select_pages(monkeypatch):
    urls = []

    def http(method, url, **kwargs):
        urls.append(url)
        if url.endswith("oauth/access_token"):
            return {"access_token": "private"}
        if url.endswith("me/permissions"):
            return {"data": [{"permission": "ads_read", "status": "granted"}]}
        return {"id": "123", "name": "CBN"}

    monkeypatch.setattr(channel_oauth, "http_json", http)
    value = channel_oauth.exchange(
        {
            "Provider": "meta",
            "IssuerProfile": "facebook_login",
            "ApiVersion": "v25.0",
            "ClientId": "123",
            "MarketingOnly": True,
        },
        "secret",
        "code",
        "https://app.rinovaplus.com/callback",
        "verifier",
    )
    assert value["scopes"] == ["ads_read"]
    assert value["assets"][0]["kind"] == "login_identity"
    assert len(urls) == 3 and not any("accounts" in v for v in urls)


def test_sync_rechecks_credentials_after_network_and_rejects_rotation(monkeypatch):
    service = Marketing(SimpleNamespace(), reader=Mock())
    @contextmanager
    def tx(*a, **kw): yield Mock(), {"UserId": "actor"}
    service.ads.tx = tx
    monkeypatch.setattr(module, "authorize", Mock())
    monkeypatch.setattr(module, "account", lambda *a: {"State": "connected", "Provider": "meta", "Revision": 1, "ExternalId": "123"})
    monkeypatch.setattr(module, "replay", lambda *a: ("digest", None))
    credentials = [({"ApiVersion": "v25.0"}, "secret", ["v1"]), ({"ApiVersion": "v25.0"}, "secret2", ["v2"])]
    monkeypatch.setattr(module, "credential", lambda *a: credentials.pop(0))
    writes = Mock()
    monkeypatch.setattr(module, "event", writes)
    service.reader.return_value.snapshot.return_value = {"provider_writes": False}
    body = Sync(operation_id="00000000-0000-4000-8000-000000000001", revision=1, start="2026-11-01", end="2026-11-02")
    with pytest.raises(HTTPException, match="ads_meta_context_changed"):
        service.sync({}, "account", body)
    service.reader.return_value.snapshot.assert_called_once()
    writes.assert_not_called()


def test_stale_draft_revision_is_rejected_before_journal_write(monkeypatch):
    service = Marketing(SimpleNamespace())
    @contextmanager
    def tx(*a, **kw): yield Mock(), {"UserId": "actor"}
    service.ads.tx = tx
    monkeypatch.setattr(module, "account", lambda *a: {"State": "connected", "Provider": "meta"})
    monkeypatch.setattr(module, "replay", lambda *a: ("digest", None))
    monkeypatch.setattr(module, "latest", lambda *a: ({"campaigns": [], "adsets": [], "ads": []}, "snapshot"))
    monkeypatch.setattr(module, "one", lambda *a: {"Document": json.dumps({"revision": 2})})
    monkeypatch.setattr(module, "institution", lambda *a: "institution")
    writes = Mock(); monkeypatch.setattr(module, "event", writes)
    body = Draft(operation_id="00000000-0000-4000-8000-000000000001", draft_id="00000000-0000-4000-8000-000000000002", draft_revision=1, name="Old version")
    with pytest.raises(HTTPException, match="revision_conflict"):
        service.save_draft({}, "account", body)
    writes.assert_not_called()


def test_oauth_completion_cannot_be_taken_from_another_user(monkeypatch):
    service = Marketing(SimpleNamespace())
    @contextmanager
    def tx(*a, **kw): yield Mock(), {"UserId": "this-user"}
    service.ads.tx = tx
    monkeypatch.setattr(module, "authorize", Mock())
    monkeypatch.setattr(module, "institution", lambda *a: "institution")
    monkeypatch.setattr(module, "one", lambda *a: {"ActorRef": "another-user"})
    writes = Mock(); monkeypatch.setattr(module, "secret_put", writes)
    body = Complete(operation_id="00000000-0000-4000-8000-000000000001", integration_id="00000000-0000-4000-8000-000000000002", oauth_session_id="00000000-0000-4000-8000-000000000003")
    with pytest.raises(HTTPException, match="oauth_session_not_found"):
        service.complete({"token": "session-private"}, body)
    writes.assert_not_called()
