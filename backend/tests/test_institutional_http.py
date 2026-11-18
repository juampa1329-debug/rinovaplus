"""Boundary tests require no SQL connection or provider service."""

import asyncio
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from app.institutional.api import create_app
from app.institutional.auth import Identity
from app.institutional.channels import contract, validate_field
from app.institutional.management import Management
from app.institutional.models import Bootstrap, Redeem
from fastapi import HTTPException
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    app = create_app(SimpleNamespace(), workspace=object())
    with TestClient(
        app, base_url="http://127.0.0.1:4177", client=("127.0.0.1", 50000)
    ) as c:
        yield c


def test_rejects_cross_origin_before_authentication(client):
    with patch("app.institutional.api.Identity.authenticate") as auth:
        assert (
            client.get(
                "/api/institution/auth/me",
                headers={"origin": "https://example.org", "x-crm-local": "1"},
            ).status_code
            == 403
        )
        auth.assert_not_called()


def test_owner_preview_bootstrap_cannot_open_institution(client):
    assert (
        client.post("/api/local/session", headers={"x-crm-local": "1"}).status_code
        == 404
    )


def test_header_and_body_limit_before_credentials(client):
    assert client.post("/api/institution/auth/login", json={}).status_code == 403
    assert (
        client.post(
            "/api/institution/auth/login",
            headers={"x-crm-local": "1", "content-length": "9999999"},
            json={},
        ).status_code
        == 413
    )


def test_unknown_routes_do_not_fall_through_to_preview(client):
    assert client.get("/api/billing", headers={"x-crm-local": "1"}).status_code == 404


def test_included_CRM_router_uses_fixed_resource_pattern(client):
    with patch("app.institutional.api.Identity.authenticate", side_effect=HTTPException(401, "session_required")) as auth, patch("app.institutional.api.transaction", side_effect=HTTPException(503, "audit_unavailable")):
        response = client.get("/api/local/crm/clients", headers={"x-crm-local": "1"})
    assert response.status_code == 503
    assert auth.call_args.args[0]["resource"] == "/api/local/crm/clients"


def test_session_secret_only_in_http_only_cookie(client):
    with patch(
        "app.institutional.api.Identity.login",
        return_value={"_token": "private-session", "user": {"id": "one"}},
    ):
        response = client.post(
            "/api/institution/auth/login",
            headers={"x-crm-local": "1"},
            json={"email": "owner@example.org", "password": "any password"},
        )
    assert response.status_code == 200
    assert response.json() == {"user": {"id": "one"}}
    cookie = response.headers["set-cookie"]
    assert (
        "HttpOnly" in cookie and "SameSite=strict" in cookie and "Path=/api" in cookie
    )
    assert response.headers["cache-control"] == "no-store"


def test_errors_never_echo_password(client):
    response = client.post(
        "/api/institution/auth/login",
        headers={"x-crm-local": "1"},
        json={"email": "bad", "password": "secret-password", "admin": True},
    )
    assert response.status_code == 422
    assert response.json() == {"detail": "invalid_request"}


def test_all_channel_contexts_and_no_display_writes():
    fields = contract()["fields"]
    assert len(fields) == 115
    assert len({f["id"] for f in fields}) == 115
    assert all(
        not f.get("p2_write_allowed") for f in fields if f["field_kind"] == "display"
    )


@pytest.mark.parametrize("bad", [True, -1, 101, 1.2, "50"])
def test_channel_rollout_rejects_invalid_types_and_bounds(bad):
    field = next(
        f for f in contract()["fields"] if f["id"] == "tiktok:tt_form_rollout_percent"
    )
    with pytest.raises(ValueError):
        validate_field(field, bad)


def test_channel_scope_lists_preserve_source_semantics():
    field = next(f for f in contract()["fields"] if f["id"] == "tiktok:tt_form_scopes")
    assert validate_field(field, ["Read", "read", "Read"]) == ["Read", "read", "Read"]
    with pytest.raises(ValueError):
        validate_field(field, ["comma,joined"])


def test_invalid_bootstrap_key_does_not_run_password_kdf():
    settings = SimpleNamespace(
        ticket={"context": [[1, "00000000-0000-0000-0000-000000000001"]]}
    )
    body = Bootstrap(
        email="owner@example.org",
        password="a sufficiently long password",
        bootstrap_token="x" * 43,
        full_name="Propietario",
    )
    with (
        patch("app.institutional.auth.transaction", return_value=nullcontext(object())),
        patch("app.institutional.auth.rate", return_value=True),
        patch("app.institutional.auth.one", return_value=None),
        patch("app.institutional.auth.audit"),
        patch("app.institutional.auth.password_hash") as kdf,
    ):
        with pytest.raises(HTTPException) as failure:
            Identity(settings).bootstrap(body)
        assert failure.value.status_code == 403
        kdf.assert_not_called()


def test_unknown_redemption_does_not_run_password_kdf():
    settings = SimpleNamespace(
        ticket={"context": [[1, "00000000-0000-0000-0000-000000000001"]]}
    )
    body = Redeem(token="x" * 43, new_password="a sufficiently long password")
    with (
        patch(
            "app.institutional.management.transaction",
            return_value=nullcontext(object()),
        ),
        patch("app.institutional.management.rate", return_value=True),
        patch("app.institutional.management.one", return_value=None),
        patch("app.institutional.management.bound_hash", return_value=b""),
        patch("app.institutional.management.audit"),
        patch("app.institutional.management.password_hash") as kdf,
    ):
        with pytest.raises(HTTPException) as failure:
            Management(settings).redeem(body)
        assert failure.value.status_code == 401
        kdf.assert_not_called()


def test_chunked_body_stops_before_reading_entire_request():
    app = create_app(SimpleNamespace(), workspace=object())
    received = []
    sent = []

    async def receive():
        received.append(1)
        return {"type": "http.request", "body": b"x" * 262144, "more_body": True}

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.4"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/institution/auth/login",
        "raw_path": b"/api/institution/auth/login",
        "query_string": b"",
        "root_path": "",
        "headers": [(b"host", b"127.0.0.1:4177"), (b"x-crm-local", b"1")],
        "client": ("127.0.0.1", 50000),
        "server": ("127.0.0.1", 4177),
    }
    asyncio.run(app(scope, receive, send))
    assert next(m["status"] for m in sent if m["type"] == "http.response.start") == 413
    assert len(received) == 3


def test_redemption_password_policy_is_a_validation_error_not_storage_failure():
    from unittest.mock import MagicMock
    settings = SimpleNamespace(ticket={"context": [[1, "00000000-0000-0000-0000-000000000001"]]})
    body = Redeem(token="x" * 43, new_password="123456789012345")
    cursor = MagicMock()
    cursor.execute.return_value.fetchval.return_value = 0
    with (
        patch("app.institutional.management.transaction", return_value=nullcontext(cursor)),
        patch("app.institutional.management.rate", return_value=True),
        patch("app.institutional.management.one", return_value={"UserId":"00000000-0000-0000-0000-000000000002", "ChallengeId":"challenge", "AuthVersion":1}),
        patch("app.institutional.management.user", return_value={"AuthVersion":1}),
        patch("app.institutional.management.bound_hash", return_value=b""),
        patch("app.institutional.management.revoke_user") as revoke,
    ):
        with pytest.raises(HTTPException) as failure:
            Management(settings).redeem(body)
        assert failure.value.status_code == 422
        assert failure.value.detail == "password_policy"
        revoke.assert_not_called()
        assert not any("PasswordHash" in str(call) for call in cursor.execute.call_args_list)
