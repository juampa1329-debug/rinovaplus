"""Offline C12 authority, validation and redaction; no SQL/profile discovery."""

import time
import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.parity_channels.api import Application, Integration, create_app
from app.parity_channels.policy import identifier, namespace, principal, secret_aad
from tools.parity_mapping import account_scope, stage_binding


class NoStorage:
    def read(self, *args, **kwargs):
        raise AssertionError("SQL must not be reached")

    def write(self, *args, **kwargs):
        raise AssertionError("SQL must not be reached")

    def operation(self, *args, **kwargs):
        raise AssertionError("SQL must not be reached")


def client(**overrides):
    settings = SimpleNamespace(
        review={"api_token": "x" * 48}, ticket={"expires_at": time.time() + 3600}
    )
    app = create_app(settings, NoStorage())
    return TestClient(
        app, base_url="http://127.0.0.1:4176", client=("127.0.0.1", 12345), **overrides
    )


HEADERS = {"Authorization": "Bearer " + "x" * 48, "X-CRM-Local": "1"}


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer " + "x" * 48},
        {"X-CRM-Local": "1"},
        {**HEADERS, "Authorization": "Bearer wrong"},
        {**HEADERS, "Host": "evil.example"},
        {**HEADERS, "Origin": "http://evil.example"},
    ],
)
def test_auth_before_storage(headers):
    with client() as c:
        assert c.get("/api/channels/secrets", headers=headers).status_code == 403


def test_remote_client_rejected():
    settings = SimpleNamespace(
        review={"api_token": "x" * 48}, ticket={"expires_at": time.time() + 3600}
    )
    with TestClient(
        create_app(settings, NoStorage()),
        base_url="http://127.0.0.1:4176",
        client=("192.0.2.1", 1),
    ) as c:
        assert c.get("/api/capabilities", headers=HEADERS).status_code == 403


def test_expired_capability():
    settings = SimpleNamespace(review={"api_token": "x" * 48}, ticket={"expires_at": 0})
    with TestClient(
        create_app(settings, NoStorage()),
        base_url="http://127.0.0.1:4176",
        client=("127.0.0.1", 1),
    ) as c:
        assert c.get("/api/capabilities", headers=HEADERS).status_code == 403


def test_distinct_capabilities():
    with client() as c:
        r = c.get("/api/capabilities", headers=HEADERS)
        assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
        body = r.json()
        assert body["mode"] == "isolated_c12" and not any(
            body[k]
            for k in (
                "oauth",
                "providers",
                "workers",
                "public_webhooks",
                "institutional_auth",
                "secret_replacement",
            )
        )


@pytest.mark.parametrize(
    "path",
    [
        "/api/channels/bad",
        "/api/channels/integrations/not-a-uuid",
        "/api/channels/secrets?limit=101",
        "/api/channels/secrets?limit=0",
        "/api/channels/receipts?after=1%27%3BDROP",
    ],
)
def test_invalid_routes_never_reach_storage(path):
    with client() as c:
        assert c.get(path, headers=HEADERS).status_code in {404, 422}


APP = {
    "Provider": "meta",
    "ClientId": "00123",
    "ApiVersion": "v23.0",
    "IssuerProfile": "meta_whatsapp",
    "RedirectUri": "https://institution.example/callback",
}


@pytest.mark.parametrize(
    "extra",
    [
        {"InstitutionId": str(uuid.uuid4())},
        {"State": "enabled"},
        {"appSecret": "sensitive-test-marker"},
        {"EgressProfile": "arbitrary"},
        {"ClientId": " 123"},
        {"RedirectUri": "http://institution.example"},
        {"RedirectUri": "https://user:password@example.test/"},
        {"RedirectUri": "https://example.test/#fragment"},
    ],
)
def test_application_validation_redacts_input(extra):
    with client() as c:
        r = c.post(
            "/api/channels/applications",
            headers={**HEADERS, "Idempotency-Key": str(uuid.uuid4())},
            json={**APP, **extra},
        )
        assert r.status_code == 422 and r.json() == {"detail": "invalid_request"}
        assert "sensitive-test-marker" not in r.text


@pytest.mark.parametrize("value", ["", " 001", "001 ", "a\n", "x" * 201])
def test_external_ids_reject_lossy_normalization(value):
    with pytest.raises(ValueError):
        identifier(value)


def test_binary_namespaces_and_ids():
    assert identifier("001Ab") == "001Ab"
    assert namespace("meta", "app-a", "meta_whatsapp") == namespace(
        "meta", "app-b", "facebook_login"
    )
    assert namespace("tiktok", "app-a", "tiktok_business") != namespace(
        "tiktok", "app-b", "tiktok_business"
    )


def test_webhook_endpoint_secret_uses_canonical_owner():
    ids = [str(uuid.uuid4()) for _ in range(2)]
    value = secret_aad(ids[0], "WebhookEndpoint", ids[1], "webhook_verify", 1, "c12-v1")
    assert b'"WebhookEndpoint"' in value
    with pytest.raises(ValueError):
        secret_aad(ids[0], "Endpoint", ids[1], "webhook_verify", 1, "c12-v1")


def test_no_cross_owner_ciphertext_reuse():
    ids = [str(uuid.uuid4()) for _ in range(3)]
    first = secret_aad(
        ids[0], "Integration", ids[1], "meta_permanent_access", 1, "c12-v1"
    )
    assert first != secret_aad(
        ids[0], "Integration", ids[2], "meta_permanent_access", 1, "c12-v1"
    )
    assert first != secret_aad(
        ids[0], "Integration", ids[1], "meta_permanent_access", 2, "c12-v1"
    )


@pytest.mark.parametrize(
    "database",
    [
        "HORARIOSSIIE",
        "CBN_C9_TRIAL_20261025_23ac78d3",
        "CBN_C12_TRIAL_20261025_f421674d;DROP",
        "CBN_C12_TRIAL_20261025_F421674D",
    ],
)
def test_strict_c12_target(database):
    with pytest.raises(ValueError):
        principal(database)


def test_application_ids_preserved():
    assert Application(**APP).ClientId == "00123"
    with pytest.raises(ValidationError):
        Integration(
            ApplicationId=uuid.uuid4(),
            Channel="whatsapp",
            DisplayName="test",
            ApiVersion="",
            ExternalAccountId="id ",
        )


def test_identity_and_verification_not_patchable():
    with client() as c:
        r = c.patch(
            "/api/channels/integrations/" + str(uuid.uuid4()),
            headers={
                **HEADERS,
                "Idempotency-Key": str(uuid.uuid4()),
                "If-Match": "0" * 16,
            },
            json={
                "DisplayName": "test",
                "ApiVersion": "v23.0",
                "VerifiedStatus": "verified",
                "ExternalAccountId": "changed",
            },
        )
        assert r.status_code == 422


def test_stage_label_maps_to_active_key_with_configuration_hash():
    document = (
        '{"stages":[{"key":"admission","label":"Admisiones"'
        ',"active":true}],"tags":[],"fields":[]}'
    )
    first = stage_binding(document, 4, "Admisiones")
    assert first[0] == "admission" and len(first[1]) == 32
    assert first[1] != stage_binding(document, 5, "Admisiones")[1]
    assert stage_binding(document, 4, "") == (None, None)
    with pytest.raises(ValueError):
        stage_binding(document, 4, "Unknown")


@pytest.mark.parametrize(
    "channel,mode,expected",
    [
        ("whatsapp", "facebook", "meta_whatsapp"),
        ("instagram", "facebook", "facebook_login"),
        ("instagram", "instagram", "instagram_login"),
        ("tiktok", "facebook", "tiktok_business"),
        ("facebook", "facebook", "facebook_login"),
    ],
)
def test_issuer_is_product_scoped(channel, mode, expected):
    assert (
        account_scope(channel, {"appId": "001", "instagramLogin": mode})[2] == expected
    )
