import asyncio
import json

import httpx2 as httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.modules.ai.domain.models import (
    AiSettings,
    HistoryMessage,
    ModelInfo,
    SaveSettings,
    model_order,
    prepare_messages,
    response_plan,
)
from app.modules.ai.domain.models import (
    TestRequest as AiTestRequest,
)
from app.modules.ai.infrastructure.providers import AiError, ProviderGateway
from app.modules.ai.application.service import AiService, SettingsRepository
from app.main import create_app


def run(coroutine):
    return asyncio.run(coroutine)


@pytest.fixture
def service(tmp_path):
    return AiService(
        SettingsRepository(tmp_path / "settings.json"), ProviderGateway({}), False
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


def test_save_reload_and_stale_revision(client, service):
    initial = client.get("/api/ai/settings").json()
    assert initial["settings"]["enabled"] is False
    draft = initial["settings"] | {"system_prompt": "Estilo de prueba"}
    response = client.put("/api/ai/settings", json={"revision": 0, "settings": draft})
    assert response.status_code == 200
    assert response.json()["revision"] == 1
    assert (
        SettingsRepository(service.repository.path).read().settings.system_prompt
        == "Estilo de prueba"
    )
    assert (
        client.put(
            "/api/ai/settings", json={"revision": 0, "settings": draft}
        ).status_code
        == 409
    )
    assert "API_KEY" not in service.repository.path.read_text()
    assert client.get("/health/ready").status_code == 503


@pytest.mark.parametrize(
    "headers",
    [
        {"Host": "evil.example:8000"},
        {"Origin": "https://evil.example"},
        {"Origin": "null"},
        {"X-CRM-Local": "0"},
    ],
)
def test_local_security_headers(client, headers):
    assert client.get("/api/ai/settings", headers=headers).status_code == 403


def test_remote_client_rejected_even_with_good_host(service):
    with TestClient(
        create_app(service),
        base_url="http://127.0.0.1:8002",
        client=("192.0.2.2", 1234),
        headers={"X-CRM-Local": "1"},
    ) as client:
        assert client.get("/api/ai/settings").status_code == 403


def test_local_browser_origin_allowed_and_body_bounded(client):
    assert (
        client.get(
            "/api/ai/settings", headers={"Origin": "http://127.0.0.1:5175"}
        ).status_code
        == 200
    )
    assert (
        client.put(
            "/api/ai/settings",
            content="x" * 64001,
            headers={"Content-Type": "application/json"},
        ).status_code
        == 413
    )
    assert client.put("/api/ai/settings", content="x").status_code == 415


def test_validation_never_echoes_submitted_text(client):
    response = client.put(
        "/api/ai/settings",
        json={"revision": 0, "settings": {"max_tokens": "sensitive-content"}},
    )
    assert response.status_code == 422
    assert response.json() == {"code": "invalid_request"}
    assert "sensitive" not in response.text
    assert client.post("/api/ai/models/unknown", json={}).status_code == 422


@pytest.mark.parametrize(
    "change",
    [
        {"temperature": float("nan")},
        {"max_tokens": True},
        {"max_tokens": 0},
        {"max_tokens": 8193},
        {"system_prompt": "x" * 8001},
        {"recent_messages": 31},
        {"wait_seconds": -1},
        {"model": "../bad?x=1"},
        {"enabled": True},
        {"backup_provider": "gemini"},
        {"backup_model": "missing-provider"},
        {"model": "same", "fallback_model": "same"},
    ],
)
def test_strict_config_validation(change):
    with pytest.raises(ValidationError):
        AiSettings(**change)


def test_outbound_opt_in_required(client):
    response = client.post("/api/ai/models/gemini", json={})
    assert response.status_code == 409
    assert response.json()["code"] == "outbound_disabled"


def test_corrupt_storage_fails_closed(client, service):
    service.repository.path.write_text("not json")
    response = client.get("/api/ai/settings")
    assert response.status_code == 503
    assert response.json()["code"] == "settings_storage_unavailable"
    assert service.repository.path.read_text() == "not json"


def test_history_and_fragment_plan_are_effective():
    settings = AiSettings(
        recent_messages=1,
        history_chars=40,
        chars_per_message=40,
        wait_seconds=2,
        typing_ms=500,
        fragment_delay_ms=1000,
    )
    request = AiTestRequest(
        revision=0,
        prompt="Pregunta ficticia",
        history=[
            HistoryMessage(role="user", content="omit"),
            HistoryMessage(role="assistant", content="x" * 90),
        ],
    )
    system, messages = prepare_messages(settings, request)
    assert "No ejecutes herramientas, SQL" in system
    assert "breves" in system
    assert len(messages) == 2 and len(messages[0]["content"]) == 40
    text = "Una respuesta ficticia para comprobar fragmentos sin enviar a nadie. " * 4
    plan = response_plan(text, settings)
    assert all(len(fragment["text"]) <= 40 for fragment in plan)
    assert " ".join(fragment["text"] for fragment in plan) == text.strip()
    assert plan[0]["after_ms"] == 2500 and plan[1]["after_ms"] == 3500
    assert (
        len(response_plan(text, settings.model_copy(update={"split_responses": False})))
        == 1
    )
    assert (
        len(
            prepare_messages(
                settings.model_copy(update={"recent_messages": 0}), request
            )[1]
        )
        == 1
    )


def catalog(service, provider, *names):
    service.catalogs[provider] = {name: ModelInfo(id=name, name=name) for name in names}


def configured_service(tmp_path, handler):
    gateway = ProviderGateway(
        {"gemini": "fake-gemini", "xai": "fake-xai", "openrouter": "fake-openrouter"},
        httpx.MockTransport(handler),
    )
    return AiService(SettingsRepository(tmp_path / "settings.json"), gateway, True)


def test_transient_fallback_four_attempts_and_no_hidden_retries(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) < 4:
            return httpx.Response(429, json={"secret": "must-not-escape"})
        return httpx.Response(
            200,
            json={
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {"type": "output_text", "text": "Respuesta ficticia"}
                        ],
                    }
                ]
            },
        )

    service = configured_service(tmp_path, handler)
    settings = AiSettings(
        enabled=True,
        model="a",
        fallback_enabled=True,
        fallback_model="b",
        backup_provider="xai",
        backup_model="c",
        backup_fallback_model="d",
    )
    catalog(service, "gemini", "a", "b")
    catalog(service, "xai", "c", "d")
    service.save(SaveSettings(revision=0, settings=settings))
    result = run(service.test(AiTestRequest(revision=1, prompt="Ficticio")))
    assert len(calls) == 4 and len(result["attempts"]) == 4
    assert (
        result["model"] == "d"
        and result["delivered"] is False
        and result["typing_available"] is False
    )
    assert (
        len(model_order(settings.model_copy(update={"fallback_enabled": False}))) == 1
    )


@pytest.mark.parametrize("status", [400, 401, 403, 404, 302])
def test_nontransient_failure_never_falls_back(tmp_path, status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            status,
            headers={"Location": "https://evil.example"},
            json={"private": "secret"},
        )

    service = configured_service(tmp_path, handler)
    catalog(service, "gemini", "a", "b")
    service.save(
        SaveSettings(
            revision=0,
            settings=AiSettings(
                enabled=True, model="a", fallback_model="b", fallback_enabled=True
            ),
        )
    )
    with pytest.raises(AiError, match="provider_rejected_request"):
        run(service.test(AiTestRequest(revision=1, prompt="Ficticio")))
    assert len(calls) == 1
    assert not service.busy


def test_timeout_is_transient_and_busy_is_released(tmp_path):
    def handler(request):
        raise httpx.ReadTimeout("sensitive network text", request=request)

    service = configured_service(tmp_path, handler)
    catalog(service, "gemini", "a")
    service.save(SaveSettings(revision=0, settings=AiSettings(enabled=True, model="a")))
    with pytest.raises(AiError, match="all_models_unavailable"):
        run(service.test(AiTestRequest(revision=1, prompt="Ficticio")))
    assert not service.busy


@pytest.mark.parametrize("provider", ["gemini", "xai", "openrouter"])
def test_provider_wire_contract(provider):
    seen = []

    def handler(request):
        seen.append(request)
        if provider == "gemini":
            return httpx.Response(
                200,
                json={
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {"text": "private thought", "thought": True},
                                    {"text": "Respuesta"},
                                ]
                            }
                        }
                    ]
                },
            )
        if provider == "xai":
            return httpx.Response(
                200,
                json={
                    "output": [
                        {
                            "type": "message",
                            "content": [{"type": "output_text", "text": "Respuesta"}],
                        }
                    ]
                },
            )
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "Respuesta"}}]}
        )

    gateway = ProviderGateway({provider: "synthetic-key"}, httpx.MockTransport(handler))
    result = run(
        gateway.generate(
            provider,
            "fixture-model",
            AiSettings(output_tokens=100),
            "fixed system",
            [{"role": "user", "content": "fixture"}],
        )
    )
    assert result == "Respuesta"
    body = json.loads(seen[0].content)
    assert seen[0].url.scheme == "https"
    assert "tools" not in body
    if provider == "gemini":
        assert seen[0].headers["x-goog-api-key"] == "synthetic-key"
        assert body["generationConfig"]["maxOutputTokens"] == 100
        assert body["systemInstruction"]["parts"][0]["text"] == "fixed system"
    elif provider == "xai":
        assert seen[0].url.path == "/v1/responses"
        assert body["store"] is False and body["max_output_tokens"] == 100
    else:
        assert body["max_tokens"] == 100
        assert body["provider"]["allow_fallbacks"] is False


@pytest.mark.parametrize(
    "payload", [None, [], {"data": None}, {"data": {}}, {"models": None}]
)
def test_invalid_catalog_sanitized(payload):
    gateway = ProviderGateway(
        {"xai": "fake"},
        httpx.MockTransport(lambda _: httpx.Response(200, json=payload)),
    )
    with pytest.raises(AiError, match="provider_invalid_response"):
        run(gateway.models("xai"))


@pytest.mark.parametrize(
    "provider,payload",
    [
        ("gemini", {"candidates": None}),
        ("xai", {"output": [None]}),
        ("openrouter", {"choices": {}}),
    ],
)
def test_invalid_generation_sanitized(provider, payload):
    gateway = ProviderGateway(
        {provider: "fake"},
        httpx.MockTransport(lambda _: httpx.Response(200, json=payload)),
    )
    with pytest.raises(AiError):
        run(gateway.generate(provider, "fixture", AiSettings(), "fixed", []))


def test_gemini_catalog_pagination_and_capabilities(tmp_path):
    paths = []

    def handler(request):
        paths.append(str(request.url))
        if len(paths) == 1:
            return httpx.Response(
                200,
                json={
                    "models": [
                        {"name": None},
                        {
                            "name": "models/embed",
                            "supportedGenerationMethods": ["embedContent"],
                        },
                    ],
                    "nextPageToken": "safe-token",
                },
            )
        return httpx.Response(
            200,
            json={
                "models": [
                    {
                        "name": "models/text",
                        "supportedGenerationMethods": ["generateContent"],
                        "outputTokenLimit": 800,
                        "maxTemperature": 1.0,
                    }
                ]
            },
        )

    service = configured_service(tmp_path, handler)
    models = run(service.load_models("gemini"))
    assert len(models) == 1 and models[0].id == "text"
    assert "pageToken=safe-token" in paths[1]
    with pytest.raises(AiError, match="model_temperature_limit_exceeded"):
        service.save(
            SaveSettings(
                revision=0,
                settings=AiSettings(enabled=True, model="text", temperature=1.5),
            )
        )
    with pytest.raises(AiError, match="model_output_limit_exceeded"):
        service.save(
            SaveSettings(
                revision=0,
                settings=AiSettings(
                    enabled=True, model="text", output_tokens=1000, max_tokens=1000
                ),
            )
        )


def test_catalog_overflow_rejected_not_truncated():
    gateway = ProviderGateway(
        {"gemini": "fake"},
        httpx.MockTransport(
            lambda _: httpx.Response(200, json={"models": [], "nextPageToken": "more"})
        ),
    )
    with pytest.raises(AiError, match="model_catalog_too_large"):
        run(gateway.models("gemini"))


def test_enabled_save_requires_catalog_and_supported_params(service):
    settings = AiSettings(enabled=True, model="test")
    with pytest.raises(AiError, match="model_catalog_required"):
        service.save(SaveSettings(revision=0, settings=settings))
    service.catalogs["gemini"] = {
        "test": ModelInfo(id="test", name="test", temperature=False)
    }
    with pytest.raises(AiError, match="model_temperature_unsupported"):
        service.save(SaveSettings(revision=0, settings=settings))


def test_busy_rejects_parallel_operations(service):
    service.outbound = True
    service.busy = True
    with pytest.raises(AiError, match="operation_busy"):
        run(service.load_models("gemini"))
