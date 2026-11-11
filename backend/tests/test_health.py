import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_live_reports_only_local_process():
    with TestClient(create_app()) as client:
        response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive", "mode": "local_demo"}


def test_readiness_does_not_claim_integrations():
    with TestClient(create_app()) as client:
        response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["integrations"] == {
        name: "not_configured"
        for name in ("sql_server", "redis", "identity", "providers")
    }


@pytest.mark.parametrize("mode", ["production", "staging", "", "test"])
def test_remote_or_ambiguous_mode_is_rejected(monkeypatch, mode):
    monkeypatch.setenv("CRM_APP_MODE", mode)
    with pytest.raises(ValueError, match="Only CRM_APP_MODE=local_demo"):
        Settings.from_environment()


def test_unknown_route_is_not_a_business_api():
    with TestClient(create_app()) as client:
        assert client.get("/api/clients").status_code == 404
