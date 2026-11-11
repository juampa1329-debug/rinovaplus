"""Cross-branch composition must keep routes unique and transports isolated."""

from collections import Counter

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.modules.ai.infrastructure.providers import ProviderGateway
from app.modules.ai.application.service import AiService, SettingsRepository
from app.main import create_app


def test_no_duplicate_runtime_route_or_openapi_identity(tmp_path):
    service = AiService(
        SettingsRepository(tmp_path / "settings.json"), ProviderGateway({}), False
    )
    application = create_app(service)
    routes = [
        candidate
        for route in application.routes
        for candidate in (
            route.original_router.routes
            if hasattr(route, "original_router")
            else [route]
        )
        if isinstance(candidate, APIRoute)
    ]
    identities = Counter(
        (method, route.path) for route in routes for method in route.methods
    )
    assert all(count == 1 for count in identities.values())
    assert identities[("GET", "/api/v1/catalog/programs")] == 1
    document = application.openapi()
    operation = document["paths"]["/api/v1/catalog/programs"]["get"]
    assert operation["operationId"] == "catalog_programs"
    assert "200" in operation["responses"] and "501" not in operation["responses"]
    assert (
        document["x-local-superseded-proposals"][0]["path"]
        == "/api/v1/catalog/programs"
    )


def test_sanitized_errors_and_disabled_catalog_coexist(tmp_path):
    service = AiService(
        SettingsRepository(tmp_path / "settings.json"), ProviderGateway({}), False
    )
    with TestClient(
        create_app(service),
        base_url="http://127.0.0.1:8000",
        client=("127.0.0.1", 1234),
        headers={"X-CRM-Local": "1"},
    ) as client:
        ai = client.put("/api/ai/settings", json={"private": "SECRET_SENTINEL"})
        local = client.post("/api/v1/auth/login", json={"private": "SECRET_SENTINEL"})
        assert ai.status_code == local.status_code == 422
        assert ai.json() == {"code": "invalid_request"}
        assert local.json() == {
            "code": "invalid_local_contract_input",
            "mode": "local_demo",
        }
        assert "SECRET_SENTINEL" not in ai.text + local.text
        assert client.get("/api/v1/catalog/programs").status_code == 503
        assert client.get("/api/ai/settings").status_code == 200
