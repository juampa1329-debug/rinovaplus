"""Long agent configuration survives validation, HTTP and persistence boundaries."""

import asyncio
import json
from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.modules.agents import service
from app.modules.agents.domain import AgentWrite, Configuration
from app.modules.ai.api.router import LocalAiGuard
from app.modules.ai.application.admissions_prompt import (
    AdmissionsPolicy,
    assemble_prompt,
)
from app.modules.ai.infrastructure.providers import AiError


def long_configuration():
    return {
        "instructions": "Institutional instruction. " * 3000,
        "tone": "Respectful and clear. " * 100,
        "objectives": [
            f"{index}: " + "Detailed objective. " * 40 for index in range(21)
        ],
        "rules": [f"{index}: " + "Detailed rule. " * 50 for index in range(41)],
        "primary_model": "saved-model",
        "channels": ["local"],
        "monthly_token_limit": 1000000,
    }


def test_valid_long_configuration_is_saved_whole_and_available(monkeypatch):
    configuration = Configuration(**long_configuration())
    request = AgentWrite(
        operation_id=uuid4(),
        revision=0,
        name="Synthetic guide",
        level="guide",
        configuration=configuration,
    )
    commands = []

    class Cursor:
        def execute(self, sql, *args):
            commands.append((sql, args))
            return self

        def fetchone(self):
            return None

    @contextmanager
    def transaction(write=False):
        assert write
        yield Cursor()

    monkeypatch.setattr(service, "load", lambda _: ({}, {}))
    monkeypatch.setattr(service, "provider_options", lambda _: {})
    monkeypatch.setattr(service, "validate_selection", lambda *args: None)
    monkeypatch.setattr(service, "invalidate", lambda _: None)
    target = SimpleNamespace(ai=None, transaction=transaction)
    result = service.AgentsService.save_agent(target, str(uuid4()), request)
    assert result == {"confirmed": True, "version": 1}
    profile_document = next(
        args[-1] for sql, args in commands if "INSERT crm_agents.Profile" in sql
    )
    assert json.loads(profile_document) == configuration.model_dump(mode="json")
    audit_document = next(
        args[4] for sql, args in commands if "INSERT crm_agents.History" in sql
    )
    recorded = json.loads(audit_document)
    assert recorded["configuration"] == json.loads(profile_document)
    assert recorded["state"] == "active" and recorded["approved_version"] == 1


def test_long_policy_is_preserved_without_relaxing_execution_context_limit(monkeypatch):
    config = Configuration(**long_configuration()).model_dump(mode="json")
    guide = {
        "id": "guide",
        "level": "guide",
        "parent_id": None,
        "program_id": None,
        "stage_id": None,
        "version": 1,
        "configuration": config,
    }
    monkeypatch.setattr(service, "source_rows", lambda _: [])
    check = service.preflight(None, guide, {"guide": guide}, {})
    assert check["ready"] and check["effective"] == config
    policy = service.policy_for({"configuration": config})
    for value in [
        config["instructions"],
        config["tone"],
        *config["objectives"],
        *config["rules"],
    ]:
        assert value in policy.system_prompt
    assert policy.max_tokens == config["max_tokens"]
    with pytest.raises(AiError, match="admissions_context_limit"):
        assemble_prompt(policy, "Question", {}, [], [])
    with pytest.raises(ValueError):
        AdmissionsPolicy(system_prompt=config["instructions"])


@pytest.mark.parametrize(
    "method,path,authorized,status",
    [
        ("PUT", "/api/v1/agents/profiles/" + str(uuid4()), True, 204),
        ("PUT", "/api/v1/agents/profiles/" + str(uuid4()), False, 403),
        ("POST", "/api/v1/agents/profiles/" + str(uuid4()) + "/approve", True, 413),
        ("PUT", "/api/ai/settings", True, 413),
    ],
)
def test_only_authorized_profile_configuration_accepts_large_stream(
    method, path, authorized, status
):
    body = json.dumps(long_configuration()).encode()
    assert len(body) > 64000
    chunks = [body[:40000], body[40000:]]
    responses = []
    received = bytearray()

    async def receive():
        return {
            "type": "http.request",
            "body": chunks.pop(0),
            "more_body": bool(chunks),
        }

    async def send(message):
        responses.append(message)

    async def app(scope, receive, send):
        received.extend((await receive())["body"])
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    headers = [(b"host", b"localhost:4173"), (b"content-type", b"application/json")]
    if authorized:
        headers.append((b"x-crm-local", b"1"))
    scope = {
        "type": "http",
        "path": path,
        "method": method,
        "headers": headers,
        "client": ("127.0.0.1", 1),
    }
    asyncio.run(LocalAiGuard(app)(scope, receive, send))
    assert responses[0]["status"] == status
    assert received == (body if status == 204 else b"")
    if status == 204:
        assert (b"cache-control", b"no-store") in responses[0]["headers"]
