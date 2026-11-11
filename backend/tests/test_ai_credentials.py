import asyncio
import os

import httpx2 as httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.modules.ai.infrastructure.credentials import CredentialRepository, WindowsProtector
from app.modules.ai.domain.models import ModelInfo
from app.modules.ai.infrastructure.providers import AiError, ProviderGateway
from app.modules.ai.application.service import AiService, SettingsRepository
from app.main import create_app


class TestProtector:
    __test__ = False

    def transform(self, value, *, decrypt):
        # Test-only reversible boundary, never used by the application.
        if decrypt:
            if not value.startswith(b"test:"):
                raise AiError("credential_storage_unavailable", 503)
            return value[5:][::-1]
        return b"test:" + value[::-1]


@pytest.fixture
def service(tmp_path):
    return AiService(
        SettingsRepository(tmp_path / "settings.json"),
        ProviderGateway({"xai": "environment-synthetic"}),
        False,
        CredentialRepository(tmp_path / "credentials.dpapi", TestProtector()),
    )


@pytest.fixture
def client(service):
    with TestClient(
        create_app(service),
        base_url="http://127.0.0.1:8002",
        client=("127.0.0.1", 1234),
        headers={"X-CRM-Local": "1"},
    ) as client:
        yield client


def test_save_is_local_redacted_and_restores_after_restart(client, service):
    key = "synthetic-never-a-real-key"
    response = client.put(
        "/api/ai/credentials/gemini", json={"revision": 0, "api_key": key}
    )
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert key not in response.text
    assert key not in client.get("/api/ai/settings").text
    assert key.encode() not in service.credentials.path.read_bytes()
    assert not service.repository.path.exists()
    assert response.json()["outbound_enabled"] is False
    assert response.json()["providers"][0]["credential_source"] == "local"
    restored = AiService(
        service.repository, ProviderGateway({}), False, service.credentials
    )
    restored.connection_snapshot()
    assert restored.gateway.keys["gemini"] == key
    assert restored.outbound is False
    assert (
        client.post("/api/ai/models/gemini", json={}).json()["code"]
        == "outbound_disabled"
    )


def test_explicit_consent_loads_models_with_saved_key_and_persists(client, service):
    requests = []

    def handler(request):
        requests.append(request)
        assert request.headers["x-goog-api-key"] == "synthetic-key"
        return httpx.Response(
            200,
            json={
                "models": [
                    {
                        "name": "models/gemini-test",
                        "supportedGenerationMethods": ["generateContent"],
                        "outputTokenLimit": 8192,
                    }
                ]
            },
        )

    service.gateway.transport = httpx.MockTransport(handler)
    client.put(
        "/api/ai/credentials/gemini", json={"revision": 0, "api_key": "synthetic-key"}
    )
    assert requests == []
    enabled = client.put("/api/ai/outbound", json={"revision": 1, "enabled": True})
    assert enabled.status_code == 200
    assert requests == []
    response = client.post("/api/ai/models/gemini", json={})
    assert response.status_code == 200
    assert response.json()["models"][0]["id"] == "gemini-test"
    assert len(requests) == 1
    assert service.credentials.read().outbound is True
    client.put("/api/ai/outbound", json={"revision": 2, "enabled": False})
    assert client.post("/api/ai/models/gemini", json={}).status_code == 409
    assert len(requests) == 1


def test_replacement_invalidates_catalog_and_preserves_environment(client, service):
    service.connection_snapshot()
    service.catalogs["xai"] = {"old": ModelInfo(id="old", name="old")}
    response = client.put(
        "/api/ai/credentials/xai", json={"revision": 0, "api_key": "local-synthetic"}
    )
    assert response.status_code == 200
    assert service.gateway.keys["xai"] == "local-synthetic"
    assert service.environment_keys["xai"] == "environment-synthetic"
    assert service.catalogs == {}
    stale = client.put(
        "/api/ai/credentials/xai", json={"revision": 0, "api_key": "stale-synthetic"}
    )
    assert stale.status_code == 409
    assert service.gateway.keys["xai"] == "local-synthetic"


@pytest.mark.parametrize("key", ["", " ", "bad\nkey", "bad key", "é", "x" * 4097])
def test_invalid_credentials_never_echo_input(client, service, key):
    response = client.put(
        "/api/ai/credentials/gemini", json={"revision": 0, "api_key": key}
    )
    assert response.status_code == 422
    assert response.json() == {"code": "invalid_request"}
    assert not service.credentials.path.exists()


def test_credentials_reject_untrusted_origin_and_provider(client, service):
    assert (
        client.put(
            "/api/ai/credentials/gemini",
            headers={"Origin": "https://evil.example"},
            json={"revision": 0, "api_key": "synthetic"},
        ).status_code
        == 403
    )
    assert (
        client.put(
            "/api/ai/credentials/unknown", json={"revision": 0, "api_key": "synthetic"}
        ).status_code
        == 422
    )
    assert not service.credentials.path.exists()


def test_busy_connection_changes_cannot_swap_inflight_key(client, service):
    service.busy = True
    assert (
        client.put(
            "/api/ai/credentials/xai", json={"revision": 0, "api_key": "synthetic"}
        ).status_code
        == 429
    )
    assert (
        client.put(
            "/api/ai/outbound", json={"revision": 0, "enabled": True}
        ).status_code
        == 429
    )
    assert service.gateway.keys["xai"] == "environment-synthetic"
    assert not service.credentials.path.exists()


def test_corrupt_store_fails_closed_and_is_never_overwritten(client, service):
    service.credentials.path.write_bytes(b"broken-secret-store")
    assert client.get("/api/ai/settings").status_code == 503
    assert (
        client.put(
            "/api/ai/credentials/gemini", json={"revision": 0, "api_key": "synthetic"}
        ).status_code
        == 503
    )
    assert service.credentials.path.read_bytes() == b"broken-secret-store"
    with pytest.raises(AiError) as error:
        asyncio.run(service.load_models("xai"))
    assert error.value.code == "credential_storage_unavailable"


@pytest.mark.skipif(os.name != "nt", reason="Real DPAPI requires Windows")
def test_real_windows_dpapi_roundtrip_restart_and_tamper(tmp_path):
    path = tmp_path / "credentials.dpapi"
    repository = CredentialRepository(path)
    key = "synthetic-dpapi-roundtrip-secret"
    repository.update(0, provider="gemini", key=SecretStr(key))
    encrypted = path.read_bytes()
    assert key.encode() not in encrypted
    assert CredentialRepository(path).read().keys["gemini"].get_secret_value() == key
    path.write_bytes(encrypted[:-1] + bytes([encrypted[-1] ^ 0xFF]))
    with pytest.raises(AiError):
        CredentialRepository(path).read()


def test_unsupported_os_never_writes_plaintext(tmp_path, monkeypatch):
    monkeypatch.setattr("app.modules.ai.infrastructure.credentials.os.name", "unsupported")
    with pytest.raises(AiError) as error:
        WindowsProtector().transform(b"synthetic", decrypt=False)
    assert error.value.code == "credential_storage_unsupported"


def test_local_permission_overrides_environment_after_restart(service):
    service.credentials.update(0, outbound=False)
    restarted = AiService(
        service.repository, ProviderGateway({}), True, service.credentials
    )
    assert restarted.connection_snapshot()["outbound_enabled"] is False


def test_failed_atomic_write_keeps_previous_credential(client, service, monkeypatch):
    client.put(
        "/api/ai/credentials/gemini",
        json={"revision": 0, "api_key": "original-synthetic"},
    )
    original = service.credentials.path.read_bytes()

    def fail(*args):
        raise OSError("synthetic-sensitive-error")

    monkeypatch.setattr("app.modules.ai.infrastructure.credentials.os.replace", fail)
    response = client.put(
        "/api/ai/credentials/gemini",
        json={"revision": 1, "api_key": "replacement-synthetic"},
    )
    assert response.status_code == 503
    assert response.json() == {"code": "credential_storage_unavailable"}
    assert service.credentials.path.read_bytes() == original
    assert service.gateway.keys["gemini"] == "original-synthetic"


@pytest.mark.parametrize("provider", ["xai", "openrouter"])
def test_saved_bearer_credentials_reach_only_expected_provider(
    client, service, provider
):
    requests = []

    def handler(request):
        requests.append(request)
        assert request.headers["authorization"] == "Bearer synthetic-key"
        assert request.url.host == (
            "api.x.ai" if provider == "xai" else "openrouter.ai"
        )
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": "synthetic-model",
                        "architecture": {"output_modalities": ["text"]},
                        "supported_parameters": ["max_tokens", "temperature"],
                    }
                ]
            },
        )

    service.gateway.transport = httpx.MockTransport(handler)
    client.put(
        f"/api/ai/credentials/{provider}",
        json={"revision": 0, "api_key": "synthetic-key"},
    )
    client.put("/api/ai/outbound", json={"revision": 1, "enabled": True})
    assert (
        client.post(f"/api/ai/models/{provider}", json={}).json()["models"][0]["id"]
        == "synthetic-model"
    )
    assert len(requests) == 1
