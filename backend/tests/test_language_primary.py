import asyncio
import json
from types import SimpleNamespace

import httpx2 as httpx
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.institutional import grounded_replies
from app.institutional.language_resilience import execute
from app.modules.ai.domain.resilience import LanguageResilience
from app.modules.ai.infrastructure.providers import ProviderGateway


@pytest.mark.parametrize("failure", [None, 429, "missing"])
def test_selected_primary_never_calls_gemini_and_fails_over_once(failure):
    calls, reserves, trace = [], [], {}
    primary = {
        "provider": "openrouter",
        "model": "fixture/primary",
        "input_usd_per_million": 1.0,
        "output_usd_per_million": 2.0,
    }
    backup = {**primary, "model": "fixture/backup"}

    def transport(request):
        if request.method == "GET":
            values = (
                ["fixture/primary", "fixture/backup"]
                if failure != "missing"
                else ["fixture/backup"]
            )
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "id": v,
                            "context_length": 100000,
                            "architecture": {"output_modalities": ["text"]},
                            "supported_parameters": ["max_tokens", "response_format"]
                            + (["temperature"] if v.endswith("primary") else []),
                            "pricing": {"prompt": "0.000001", "completion": "0.000002"},
                            "top_provider": {"max_completion_tokens": 8000},
                        }
                        for v in values
                    ]
                },
            )
        body = json.loads(request.content)
        calls.append(body)
        if body["model"].endswith("primary") and failure == 429:
            return httpx.Response(429, json={"error": {"message": "Busy"}})
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": json.dumps(
                                {
                                    "decision": "responder",
                                    "text": "Respuesta con las mismas skills y contexto.",
                                }
                            )
                        },
                    }
                ]
            },
        )

    async def forbidden():
        pytest.fail("Gemini language generation must not run with an explicit primary")

    gateway = ProviderGateway(
        {"openrouter": "fixture-key"}, httpx.MockTransport(transport)
    )
    body = grounded_replies.request_body(
        {"system": "Skills completas", "query": "Contexto revisado"}, 700
    )
    response = asyncio.run(
        execute(
            forbidden,
            "gemini",
            "legacy",
            body,
            {
                "primary": primary,
                "routes": [backup],
                "keys": {"openrouter": "fixture-key"},
            },
            lambda: None,
            lambda *args: reserves.append(args),
            trace,
            gateway=gateway,
        )
    )
    assert grounded_replies.parse(response).startswith("Respuesta")
    assert trace["provider"] == "openrouter"
    assert trace["model"] == (primary["model"] if failure is None else backup["model"])
    assert trace["fallback_used"] is (failure is not None)
    assert len(calls) == (2 if failure == 429 else 1)
    assert len(reserves) == len(calls)
    assert calls[-1]["messages"][0]["content"].startswith("Skills completas")
    assert calls[-1]["messages"][1]["content"] == "Contexto revisado"
    if failure is not None:
        assert "temperature" not in calls[-1]


def test_human_guard_blocks_catalog_and_generation_for_selected_primary():
    async def forbidden():
        pytest.fail("No generation")

    gateway = SimpleNamespace(models=lambda *_: pytest.fail("No catalog"))

    def guard():
        raise HTTPException(409, "human_control")

    with pytest.raises(HTTPException):
        asyncio.run(
            execute(
                forbidden,
                "gemini",
                "legacy",
                {},
                {
                    "primary": {"provider": "openrouter", "model": "fixture"},
                    "keys": {},
                    "routes": [],
                },
                guard,
                lambda *_: pytest.fail("No reserve"),
                {},
                gateway=gateway,
            )
        )


def test_selected_primary_cannot_also_be_its_own_backup():
    route = {"provider": "openrouter", "model": "fixture"}
    with pytest.raises(ValidationError):
        LanguageResilience.model_validate(
            {"enabled": True, "primary": route, "routes": [route]}
        )


def test_language_policy_endpoint_validates_only_routing_and_preserves_other_ai_fields(
    monkeypatch,
):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.institutional import ai_policy, language_policy

    app = FastAPI()

    @app.middleware("http")
    async def authority(request, next):
        request.state.authority = "actor"
        return await next(request)

    language_policy.install(app, "settings")
    calls = []
    monkeypatch.setattr(
        ai_policy,
        "save",
        lambda *args, **kwargs: calls.append((args, kwargs)) or {"revision": 8},
    )
    client = TestClient(app)
    body = {
        "operation_id": "operation",
        "revision": 7,
        "language_resilience": {
            "enabled": True,
            "primary": {"provider": "openrouter", "model": "fixture/primary"},
            "routes": [{"provider": "openrouter", "model": "fixture/backup"}],
        },
    }
    assert (
        client.put(
            "/api/institution/settings/ai/language-policy", json=body
        ).status_code
        == 200
    )
    assert set(calls[0][0][4]) == {"language_resilience"}
    assert calls[0][0][5] == "language.policy"
    assert (
        client.put(
            "/api/institution/settings/ai/language-policy",
            json={**body, "system_prompt": "unexpected"},
        ).status_code
        == 422
    )
    assert len(calls) == 1
