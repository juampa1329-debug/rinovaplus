"""Meta challenge verification without operator secrets, network or SQL."""

import hashlib
import logging

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

TOKEN = "synthetic-verification-token"
DIGEST = hashlib.sha256(TOKEN.encode()).hexdigest()
QUERY = {
    "hub.mode": "subscribe",
    "hub.verify_token": TOKEN,
    "hub.challenge": "001 exact challenge + / ñ",
}


def client_for(monkeypatch, digest=DIGEST):
    monkeypatch.setenv("CRM_META_VERIFY_TOKEN_SHA256", digest)
    return TestClient(create_app())


def test_challenge_is_exact_plain_text_and_has_no_io(monkeypatch):
    # The suite autouse guard fails immediately on SQL/network access.
    with client_for(monkeypatch) as client:
        response = client.get("/api/v1/webhooks/meta", params=QUERY)
    assert response.status_code == 200
    assert response.text == QUERY["hub.challenge"]
    assert response.headers["content-type"].startswith("text/plain")
    assert response.headers["cache-control"] == "no-store"
    assert TOKEN not in response.text


@pytest.mark.parametrize("digest", ["", "not-a-hash", "0" * 63, "g" * 64])
def test_missing_or_invalid_backend_digest_fails_closed(monkeypatch, digest):
    with client_for(monkeypatch, digest) as client:
        response = client.get("/api/v1/webhooks/meta", params=QUERY)
    assert response.status_code == 503
    assert response.json() == {"code": "webhook_verification_unavailable"}


@pytest.mark.parametrize(
    "field,value",
    [("hub.verify_token", "PRIVATE_SENTINEL"), ("hub.mode", "unsubscribe")],
)
def test_wrong_token_or_mode_is_rejected(monkeypatch, field, value):
    with client_for(monkeypatch) as client:
        response = client.get("/api/v1/webhooks/meta", params={**QUERY, field: value})
    assert response.status_code == 403
    assert response.json() == {"code": "webhook_verification_rejected"}
    assert value not in response.text


@pytest.mark.parametrize("field", QUERY)
@pytest.mark.parametrize("kind", ["missing", "empty", "oversized", "duplicate"])
def test_malformed_queries_are_sanitized(monkeypatch, field, kind):
    query = dict(QUERY)
    if kind == "missing":
        query.pop(field)
    elif kind == "empty":
        query[field] = ""
    elif kind == "oversized":
        query[field] = "PRIVATE_SENTINEL" * 400
    params = list(query.items())
    if kind == "duplicate":
        params.append((field, "PRIVATE_SENTINEL"))
    with client_for(monkeypatch) as client:
        response = client.get("/api/v1/webhooks/meta", params=params)
    assert response.status_code == 422
    assert response.json() == {"code": "invalid_webhook_verification"}
    assert TOKEN not in response.text
    assert "PRIVATE_SENTINEL" not in response.text


def test_unknown_query_is_sanitized_and_environment_is_not_reflected(monkeypatch):
    with client_for(monkeypatch) as client:
        response = client.get(
            "/api/v1/webhooks/meta", params={**QUERY, "secret": "PRIVATE_SENTINEL"}
        )
        assert response.status_code == 422
        assert "PRIVATE_SENTINEL" not in response.text
        assert DIGEST not in repr(client.app.state.settings)


def test_post_does_not_acknowledge_events(monkeypatch):
    with client_for(monkeypatch) as client:
        meta = client.post("/api/v1/webhooks/meta", json={"entry": []})
        tiktok = client.post("/api/v1/webhooks/tiktok", json={"event": "test"})
    assert meta.status_code != 200
    assert tiktok.status_code != 200


def test_settings_default_has_no_verification_secret():
    assert Settings().meta_verify_token_sha256 == ""


def test_uvicorn_access_record_redacts_only_meta_query(monkeypatch):
    from app.modules.webhooks.api.access_log import VerificationQueryFilter

    create_app()
    create_app()
    logger = logging.getLogger("uvicorn.access")
    filters = [
        item for item in logger.filters if isinstance(item, VerificationQueryFilter)
    ]
    assert len(filters) == 1
    for path, expected, status in [
        (
            "/api/v1/webhooks/meta?hub.verify_token=PRIVATE_SENTINEL&hub.challenge=123",
            "/api/v1/webhooks/meta",
            200,
        ),
        (
            "/api/v1/webhooks/meta/?hub.verify_token=PRIVATE_SENTINEL",
            "/api/v1/webhooks/meta/",
            307,
        ),
        (
            "/prefix/api/v1/webhooks/meta/?hub.verify_token=PRIVATE_SENTINEL",
            "/prefix/api/v1/webhooks/meta/",
            307,
        ),
        ("/health/live?other=value", "/health/live?other=value", 200),
    ]:
        record = logging.LogRecord(
            "uvicorn.access",
            logging.INFO,
            "",
            0,
            '%s - "%s %s HTTP/%s" %d',
            ("127.0.0.1", "GET", path, "1.1", status),
            None,
        )
        assert filters[0].filter(record)
        assert record.args[2] == expected
        assert "PRIVATE_SENTINEL" not in record.getMessage()
