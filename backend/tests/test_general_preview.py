"""Offline C13 bootstrap/auth/contract checks: never discover a real profile."""

import time
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.general_preview.api import create_app
from app.general_preview.store import connection_string, principal


class NoSQL:
    def transaction(self, *args, **kwargs):
        raise AssertionError("Unexpected SQL")


def client(peer="127.0.0.1", expired=False):
    settings = SimpleNamespace(
        review={"session_token": "x" * 48},
        ticket={"expires_at": 0 if expired else time.time() + 3600},
    )
    return TestClient(
        create_app(settings, NoSQL()),
        base_url="http://127.0.0.1:4176",
        client=(peer, 1),
    )


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Host": "evil.test", "X-CRM-Local": "1"},
        {"Origin": "http://127.0.0.1:4173", "X-CRM-Local": "1"},
        {"Origin": "https://evil.test", "X-CRM-Local": "1"},
    ],
)
def test_bootstrap_boundary(headers):
    with client() as c:
        assert c.post("/api/local/session", headers=headers).status_code == 403


def test_remote_bootstrap_rejected():
    with client("192.0.2.1") as c:
        assert (
            c.post("/api/local/session", headers={"X-CRM-Local": "1"}).status_code
            == 403
        )


def test_profile_expiry_rejected_before_sql():
    with client(expired=True) as c:
        assert (
            c.post("/api/local/session", headers={"X-CRM-Local": "1"}).status_code
            == 403
        )


def test_private_cookie_and_new_manifest():
    with client() as c:
        response = c.post("/api/local/session", headers={"X-CRM-Local": "1"})
        assert response.status_code == 200 and response.json() == {
            "scope": "local_owner_preview"
        }
        assert (
            "HttpOnly" in response.headers["set-cookie"]
            and "SameSite=strict" in response.headers["set-cookie"]
        )
        assert "x" * 48 not in response.text
        result = c.get("/api/local/runtime", headers={"X-CRM-Local": "1"})
        assert (
            result.status_code == 200 and result.headers["cache-control"] == "no-store"
        )
        value = result.json()
        assert (
            value["version"] == "cbn-general-preview-c13-v1"
            and len(value["sections"]) == 14
        )
        assert all(not v for v in value["features"].values())
        assert {s["path"] for s in value["sections"] if s["available"]} == {
            "overview",
            "clients",
            "inbox",
            "settings",
            "channels",
        }


@pytest.mark.parametrize(
    "path",
    [
        "/api/local/crm",
        "/api/local/channels/secrets",
        "/api/local/progress",
        "/api/local/runtime",
    ],
)
def test_session_required_before_storage(path):
    with client() as c:
        assert c.get(path, headers={"X-CRM-Local": "1"}).status_code == 403


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/webhooks/meta",
        "/api/v1/ai/chat",
        "/api/v1/agents",
        "/api/v1/broadcasts",
    ],
)
def test_pending_functions_fail_closed(path):
    with client() as c:
        c.post("/api/local/session", headers={"X-CRM-Local": "1"})
        assert c.post(path, headers={"X-CRM-Local": "1"}, json={}).status_code == 503


@pytest.mark.parametrize(
    "database",
    [
        "HORARIOSSIIE",
        "CBN_C12_TRIAL_20261025_7a309d11",
        "CBN_C13_TRIAL_20261025_1f10a824;DROP",
    ],
)
def test_own_target_contract(database):
    with pytest.raises(ValueError):
        principal(database)


@pytest.mark.parametrize(
    "change",
    [
        {"server": "localhost;Encrypt=No"},
        {"database": "HORARIOSSIIE"},
        {"username": "sa"},
        {"certificate_hostname": "other"},
        {"port": True},
    ],
)
def test_direct_construction_cannot_bypass_transport_validation(change):
    connection = {
        "server": "localhost",
        "port": 1433,
        "username": "cbn_general_c13_1f10a824",
        "password": "synthetic};Encrypt=No",
        "database": "CBN_C13_TRIAL_20261025_1f10a824",
        "certificate_hostname": "localhost",
        **change,
    }
    with pytest.raises(ValueError):
        connection_string(SimpleNamespace(connection=connection))
