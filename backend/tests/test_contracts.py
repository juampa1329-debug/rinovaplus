import pytest
from fastapi.testclient import TestClient

from app.contracts import BUSINESS_ROUTES, STUB_ROUTES, contract_catalog
from app.local_registry import LOCAL_CONTRACTS
from app.main import create_app


def test_catalog_and_openapi_are_one_inventory():
    app = create_app()
    with TestClient(app) as client:
        catalog = client.get("/api/v1/contracts").json()
    assert len(catalog["routes"]) == 155
    assert catalog == contract_catalog().model_dump(mode="json")
    operations = [
        (path, method.upper())
        for path, item in app.openapi()["paths"].items()
        for method in item
        if method in {"get", "post", "put", "patch", "delete"}
        and not path.startswith(
            (
                "/api/ai/",
                "/api/local/clients",
                "/api/local/crm",
                "/api/local/admissions",
            )
        )
    ]
    assert set(operations) == {
        (route.path, route.method) for route in contract_catalog().routes
    }
    ids = [route.operation_id for route in contract_catalog().routes]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("route", STUB_ROUTES, ids=lambda route: route.operation_id)
def test_every_business_operation_is_unavailable(route):
    import re

    path = re.sub(r"\{channel\}", "whatsapp", route.path)
    path = re.sub(r"\{[^}]+\}", "DEMO-001", path)
    definition = LOCAL_CONTRACTS[(route.method, route.path.removeprefix("/api/v1"))]
    with TestClient(create_app()) as client:
        response = client.request(
            route.method,
            path,
            json=definition.body_example.model_dump(mode="json", exclude_unset=True)
            if definition.body_example
            else None,
            params=definition.query_example.model_dump(mode="json", exclude_none=True),
        )
    assert response.status_code == 501
    assert response.json() == {
        "code": "local_stub_unavailable",
        "mode": "local_demo",
        "operation_id": route.operation_id,
        "schema_status": route.schema_status,
        "activation_gate": route.activation_gate,
    }
    assert not {"set-cookie", "location"} & set(response.headers)


@pytest.mark.parametrize(
    "path,kwargs",
    [
        ("/api/v1/channels/invalid/activation", {"json": {}}),
        ("/api/v1/auth/login", {"json": {"private_unknown_name": "SECRET_SENTINEL"}}),
        ("/api/v1/auth/login", {"content": '{"private_unknown_name":SECRET_SENTINEL'}),
        (
            "/api/v1/channels/whatsapp/draft",
            {"json": {"tokenReference": "SECRET_SENTINEL"}},
        ),
    ],
)
def test_errors_never_reflect_input(path, kwargs):
    with TestClient(create_app()) as client:
        response = client.request(
            "PUT" if path.endswith("draft") else "POST", path, **kwargs
        )
    assert response.status_code == 422
    assert response.json() == {
        "code": "invalid_local_contract_input",
        "mode": "local_demo",
    }
    assert "SECRET_SENTINEL" not in response.text
    assert "private_unknown_name" not in response.text


def test_transport_query_limits_and_pending_schemas():
    with TestClient(create_app()) as client:
        assert client.get("/api/v1/clients?limit=0&offset=-1").status_code == 422
        assert client.get("/api/v1/clients?limit=101").status_code == 422
        assert client.get("/api/v1/channels/whatsapp/capabilities").status_code == 501
        assert (
            client.get(
                "/api/v1/webhooks/tiktok?hub.challenge=SECRET_SENTINEL"
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/api/v1/webhooks/tiktok", json={"secret": "SECRET_SENTINEL"}
            ).status_code
            == 422
        )


def test_no_outbound_or_database_entrypoints(monkeypatch):
    import ast
    import socket
    from pathlib import Path

    monkeypatch.setattr(
        socket, "create_connection", lambda *a, **k: pytest.fail("outbound forbidden")
    )
    for path in [
        Path("app") / name
        for name in (
            "contracts.py",
            "schemas.py",
            "local_models.py",
            "local_plans.py",
            "local_registry.py",
            "local_samples.py",
            "local_openapi.py",
        )
    ]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ]
        names = [alias.name.split(".")[0] for node in imports for alias in node.names]
        names += [
            node.module.split(".")[0]
            for node in imports
            if isinstance(node, ast.ImportFrom) and node.module
        ]
        assert not set(names) & {
            "requests",
            "httpx",
            "httpx2",
            "urllib",
            "pyodbc",
            "sqlalchemy",
            "redis",
            "subprocess",
        }
    with TestClient(create_app()) as client:
        assert client.get("/api/v1/contracts").status_code == 200
        definition = LOCAL_CONTRACTS[("POST", "/diagnostics/process")]
        assert (
            client.post(
                "/api/v1/diagnostics/process",
                json=definition.body_example.model_dump(
                    mode="json", exclude_unset=True
                ),
            ).status_code
            == 501
        )


@pytest.mark.parametrize("route", STUB_ROUTES, ids=lambda route: route.operation_id)
def test_openapi_matches_explicit_route_signature(route):
    import inspect

    from app.contracts import endpoint_for

    operation = create_app().openapi()["paths"][route.path][route.method.lower()]
    assert set(operation["responses"]) == {"501", "422"}
    assert operation["operationId"] == route.operation_id
    signature = inspect.signature(endpoint_for(route))
    assert all(
        parameter.annotation is not inspect.Parameter.empty
        for parameter in signature.parameters.values()
    )
    assert not any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )
    for parameter in operation.get("parameters", []):
        if parameter["in"] == "path":
            assert parameter["required"] is True
    if route.method in {"POST", "PUT", "PATCH"}:
        schema = operation["requestBody"]["content"]["application/json"]["schema"]
        assert schema["$ref"].endswith("/" + route.request_schema)
        assert operation["requestBody"]["required"] is True
    assert "security" not in operation


def test_pending_and_provisional_schema_are_honest():
    app = create_app()
    components = app.openapi()["components"]["schemas"]
    assert "PendingRequest" not in components
    assert components["LoginIntent"]["additionalProperties"] is False
    assert "password" not in components["LoginIntent"]["properties"]
    assert components["ClientDraft"]["additionalProperties"] is False
    assert components["Channel"]["enum"] == [
        "facebook",
        "messenger",
        "instagram",
        "whatsapp",
        "tiktok",
    ]
    assert sum(route.phase.startswith("7") for route in BUSINESS_ROUTES) == 38
    from pathlib import Path

    for route in BUSINESS_ROUTES:
        assert (Path("..") / route.source_locator).is_file()


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/clients?limit=SECRET_SENTINEL",
        "/api/v1/conversations/DEMO-001/messages?limit=0",
        "/api/v1/providers/DEMO-001/models?offset=-1",
        "/api/v1/clients/SECRET%20SENTINEL",
    ],
)
def test_invalid_query_or_path_is_constant(path):
    with TestClient(create_app()) as client:
        response = client.get(path)
    assert response.status_code == 422
    assert response.json() == {
        "code": "invalid_local_contract_input",
        "mode": "local_demo",
    }
