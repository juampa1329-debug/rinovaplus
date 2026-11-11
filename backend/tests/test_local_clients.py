"""Exercise the local client lifecycle without SQL, provider or operator state."""

import pytest
from fastapi.testclient import TestClient

from app.modules.ai.infrastructure.providers import ProviderGateway
from app.modules.ai.application.service import AiService, SettingsRepository
from app.main import create_app

ROOT = "/api/local/clients"


@pytest.fixture
def local_client(tmp_path):
    app = create_app(
        AiService(SettingsRepository(tmp_path / "ai.json"), ProviderGateway({}), False)
    )
    with TestClient(
        app,
        base_url="http://127.0.0.1:8000",
        client=("127.0.0.1", 1234),
        headers={"X-CRM-Local": "1"},
    ) as client:
        yield client


def test_lifecycle_search_reset_and_application_isolation(local_client, tmp_path):
    first = local_client.get(ROOT).json()
    assert first["clients"][0]["stage"] == "Interés"
    assert [c["id"] for c in first["clients"]] == [
        "demo-1",
        "demo-2",
        "demo-3",
        "demo-4",
    ]
    draft = {
        **first["clients"][0],
        "id": "demo-created",
        "name": "  Synthetic client  ",
        "stage": "Custom stage",
        "customValues": {
            "amount": "2.5",
            "day": "2026-10-15",
            "approved": "false",
            "extra": "preserved",
        },
    }
    created = local_client.post(
        ROOT, json={"client": draft, "revision": first["revision"]}
    )
    assert created.status_code == 201
    saved = created.json()
    assert saved["client"]["name"] == "Synthetic client"
    assert saved["client"]["customValues"] == draft["customValues"]
    assert local_client.get(ROOT + "/demo-created").json() == saved
    # An uncertain create can be retried without creating another record.
    assert (
        local_client.post(
            ROOT, json={"client": draft, "revision": first["revision"]}
        ).status_code
        == 200
    )
    result = local_client.get(
        ROOT, params={"q": "synthetic", "stage": "Custom stage", "tag": draft["tags"]}
    ).json()
    assert [c["id"] for c in result["clients"]] == ["demo-created"]
    assert len(local_client.get(ROOT).json()["clients"]) == 5
    assert local_client.get(ROOT, params={"q": "missing"}).json()["clients"] == []
    changed = {**saved["client"], "notes": "Changed only this synthetic client"}
    updated = local_client.put(
        ROOT + "/demo-created", json={"client": changed, "revision": saved["revision"]}
    ).json()
    assert updated["client"]["notes"] == changed["notes"]
    assert local_client.get(ROOT + "/demo-1").json()["client"] == first["clients"][0]
    stale = local_client.put(
        ROOT + "/demo-created", json={"client": draft, "revision": saved["revision"]}
    )
    assert stale.status_code == 409
    reset = local_client.post(ROOT + "/reset", json={"revision": updated["revision"]})
    assert reset.status_code == 200
    assert reset.json()["clients"] == first["clients"]
    assert reset.json()["revision"] != first["revision"]
    assert local_client.get(ROOT + "/demo-created").status_code == 404
    assert (
        local_client.post(
            ROOT, json={"client": draft, "revision": updated["revision"]}
        ).status_code
        == 409
    )
    second = create_app(
        AiService(
            SettingsRepository(tmp_path / "other.json"), ProviderGateway({}), False
        )
    )
    assert len(second.state.local_clients.clients) == 4
    assert second.state.local_clients.revision != reset.json()["revision"]
    assert local_client.get("/api/v1/clients").status_code == 501


@pytest.mark.parametrize(
    "change",
    [
        {"name": "", "phone": " "},
        {"name": "S" * 101},
        {"phone": "S" * 41},
        {"customValues": {"constructor": "SECRET_SENTINEL"}},
        {"customValues": {"number": 42}},
        {"customValues": {"long": "S" * 501}},
        {"id": "real-person"},
        {"secret": "SECRET_SENTINEL"},
    ],
)
def test_server_validation_never_mutates_or_reflects_values(local_client, change):
    before = local_client.get(ROOT).json()
    result = local_client.post(
        ROOT,
        json={
            "client": {**before["clients"][0], **change},
            "revision": before["revision"],
        },
    )
    assert result.status_code == 422
    assert result.json() == {"code": "invalid_request"}
    assert "SECRET_SENTINEL" not in result.text
    assert local_client.get(ROOT).json() == before


@pytest.mark.parametrize(
    "headers",
    [
        {"Host": "evil.invalid"},
        {"Host": "localhost.evil.invalid:8000"},
        {"Origin": "https://evil.invalid"},
        {"Origin": "null"},
        {"X-CRM-Local": ""},
    ],
)
def test_same_isolation_as_existing_local_bench(local_client, headers):
    assert local_client.get(ROOT, headers=headers).status_code == 403


def test_body_limits_errors_and_remote_peer(local_client):
    assert local_client.post(ROOT, content="{}").status_code == 415
    assert (
        local_client.post(
            ROOT, content="x" * 64001, headers={"Content-Type": "application/json"}
        ).status_code
        == 413
    )
    assert local_client.post(
        ROOT,
        content="not-json SECRET_SENTINEL",
        headers={"Content-Type": "application/json"},
    ).json() == {"code": "invalid_request"}
    assert local_client.get(ROOT, params={"q": "x" * 201}).status_code == 422
    assert local_client.get(ROOT).headers["cache-control"] == "no-store"
    with TestClient(
        local_client.app,
        base_url="http://127.0.0.1:8000",
        client=("10.0.0.1", 1234),
        headers={"X-CRM-Local": "1"},
    ) as remote:
        assert remote.get(ROOT).status_code == 403
