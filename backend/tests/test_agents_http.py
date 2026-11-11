"""Real HTTP contracts with synthetic persistence and no provider or SQL IO."""

import json
from contextlib import contextmanager
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.agents import service
from app.modules.agents.domain import AgentWrite, Configuration, SimulationRequest
from app.modules.agents.router import install_agents
from app.modules.ai.api.router import install_ai


@pytest.fixture
def http_client(monkeypatch):
    commands, operations = [], {}

    class Cursor:
        value = None

        def execute(self, sql, *args):
            commands.append((sql, args))
            self.value = None
            if sql.startswith("SELECT PayloadHash"):
                self.value = operations.get(args[0])
            elif "INSERT crm_agents.History" in sql:
                operations[args[0]] = (args[3],)
            return self

        def fetchone(self):
            return self.value

    @contextmanager
    def transaction(write=False):
        assert write
        yield Cursor()

    monkeypatch.setattr(service, "load", lambda _: ({}, {}))
    monkeypatch.setattr(
        service,
        "provider_options",
        lambda _: {"providers": [{"id": "gemini", "models": [{"id": "saved-model"}]}]},
    )
    app = FastAPI()
    app.state.settings = SimpleNamespace(mode="local_sql_copy")
    app.state.admissions_ai = SimpleNamespace(transaction=transaction)
    install_ai(app, SimpleNamespace())
    install_agents(app)
    with TestClient(
        app,
        base_url="http://localhost:8000",
        client=("127.0.0.1", 1),
        headers={"X-CRM-Local": "1"},
    ) as client:
        yield client, commands


def root_payload():
    return {
        "operation_id": str(uuid4()),
        "revision": 0,
        "name": "Synthetic root",
        "level": "guide",
        "parent_id": None,
        "program_id": None,
        "stage_id": None,
        "configuration": Configuration(
            provider="gemini",
            primary_model="saved-model",
            channels=["local"],
            monthly_token_limit=1000000,
            instructions="Complete institutional instruction. " * 2200,
        ).model_dump(mode="json"),
    }


def test_first_root_http_save_accepts_uuid_text_and_replays_without_duplicate(
    http_client,
):
    client, commands = http_client
    path = "/api/v1/agents/profiles/" + str(uuid4())
    payload = root_payload()
    first = client.put(path, json=payload)
    assert first.status_code == 200, first.text
    assert first.json() == {"confirmed": True, "version": 1}
    again = client.put(path, json=payload)
    assert again.status_code == 200 and again.json()["replayed"]
    conflict = client.put(path, json={**payload, "name": "Different request"})
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "agents_operation_conflict"
    profiles = [args for sql, args in commands if "INSERT crm_agents.Profile" in sql]
    assert len(profiles) == 1
    assert profiles[0][1:5] == ("guide", None, None, None)
    assert json.loads(profiles[0][-1]) == payload["configuration"]
    events = [args for sql, args in commands if "INSERT crm_agents.History" in sql]
    assert len(events) == 1
    recorded = json.loads(events[0][4])
    assert recorded["state"] == "active" and recorded["approved_version"] == 1
    assert recorded["enabled"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("operation_id", "not-a-uuid"),
        ("operation_id", 12),
        ("parent_id", "not-a-uuid"),
        ("revision", "0"),
        ("configuration.max_tokens", "700"),
        ("configuration.allow_reply", "false"),
        ("configuration.provider", "unsupported-provider"),
        ("configuration.document_ids", ["not-a-uuid"]),
    ],
)
def test_http_validation_rejects_invalid_values_and_identifies_only_safe_field(
    http_client, field, value
):
    client, commands = http_client
    payload = root_payload()
    parts = field.split(".")
    target = payload[parts[0]] if len(parts) > 1 else payload
    target[parts[-1]] = value
    response = client.put("/api/v1/agents/profiles/" + str(uuid4()), json=payload)
    assert response.status_code == 422
    assert response.json() == {"code": "invalid_request", "fields": [field]}
    assert commands == []
    assert "Complete institutional instruction" not in response.text
    assert str(value) not in response.text


def test_unrecognized_field_name_is_not_reflected_in_validation_response(http_client):
    client, commands = http_client
    payload = root_payload()
    payload["do_not_echo_unknown_input"] = "do_not_echo_value"
    response = client.put("/api/v1/agents/profiles/" + str(uuid4()), json=payload)
    assert response.status_code == 422
    assert response.json() == {"code": "invalid_request", "fields": []}
    assert commands == []


def test_json_uuid_conversion_covers_related_ids_without_changing_strict_scalars():
    payload = root_payload()
    payload.update(parent_id=str(uuid4()), stage_id=str(uuid4()))
    payload["configuration"]["document_ids"] = [str(uuid4())]
    agent = AgentWrite.model_validate(payload)
    assert all(
        isinstance(value, UUID)
        for value in (
            agent.operation_id,
            agent.parent_id,
            agent.stage_id,
            agent.configuration.document_ids[0],
        )
    )
    simulation = SimulationRequest.model_validate(
        {
            "agent_id": str(uuid4()),
            "config_version": 1,
            "question": "Synthetic question",
            "request_id": str(uuid4()),
        }
    )
    assert isinstance(simulation.agent_id, UUID) and isinstance(
        simulation.request_id, UUID
    )
