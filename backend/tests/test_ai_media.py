import asyncio
import base64
import json
import secrets
from unittest.mock import AsyncMock, Mock

import httpx2 as httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.modules.ai.infrastructure.media import ConversationLedger, MediaGateway, decode_attachment, safe_url
from app.modules.ai.domain.models import (
    AiSettings,
    Attachment,
    MediaChatRequest,
    MediaSettings,
    ModelInfo,
    SaveSettings,
)
from app.modules.ai.infrastructure.providers import AiError, ProviderGateway
from app.modules.ai.application.service import AiService, SettingsRepository
from app.main import create_app


def run(coroutine):
    return asyncio.run(coroutine)


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "https://localhost/a",
        "https://127.0.0.1/a",
        "https://10.0.0.1/a",
        "https://[::1]/a",
        "javascript:alert(1)",
        "https://name:secret@example.com",
        "https://host.local/a",
    ],
)
def test_safe_source_rejects_internal_and_unsafe(url):
    assert safe_url(url) == ""


def test_public_source_url():
    assert safe_url("https://example.com/a?q=b") == "https://example.com/a?q=b"


@pytest.mark.parametrize(
    "mime,data",
    [
        ("audio/wav", b"RIFF1234WAVE"),
        ("audio/mpeg", b"ID3test"),
        ("audio/ogg", b"OggSdata"),
        ("audio/flac", b"fLaCdata"),
        ("audio/webm", b"\x1aE\xdf\xa3test"),
        ("image/png", b"\x89PNG\r\n\x1a\n"),
        ("image/jpeg", b"\xff\xd8\xfftest"),
        ("image/webp", b"RIFF1234WEBP"),
    ],
)
def test_media_signatures(mime, data):
    assert (
        decode_attachment(
            Attachment(mime_type=mime, data=base64.b64encode(data).decode())
        )
        == data
    )
    with pytest.raises(AiError) as error:
        decode_attachment(
            Attachment(mime_type=mime, data=base64.b64encode(b"Not media").decode())
        )
    assert error.value.code == "invalid_media"


def test_media_size_and_invalid_base64():
    with pytest.raises(AiError) as error:
        decode_attachment(Attachment(mime_type="image/png", data="!"))
    assert error.value.code == "invalid_media"
    with pytest.raises(AiError) as error:
        decode_attachment(
            Attachment(
                mime_type="image/png", data=base64.b64encode(b"a" * 4_000_001).decode()
            )
        )
    assert error.value.code == "media_too_large"


def test_legacy_settings_default_disabled_and_strict_limits():
    assert (
        AiSettings.model_validate({"system_prompt": "Preserve"}).media
        == MediaSettings()
    )
    for value in (-1, 101, True, "3"):
        with pytest.raises(ValidationError):
            MediaSettings(voice_limit=value)


def test_durable_reservation_and_duplicate_turn(tmp_path):
    ledger = ConversationLedger(tmp_path / "ledger.json")
    identifier = ledger.create("1:2")
    turn = secrets.token_hex(16)
    ledger.start_turn(identifier, "1:2", turn)
    assert ledger.reserve_voice(identifier, "1:2", 1)
    restarted = ConversationLedger(ledger.path)
    assert not restarted.reserve_voice(identifier, "1:2", 1)
    with pytest.raises(AiError) as error:
        restarted.start_turn(identifier, "1:2", turn)
    assert error.value.code == "turn_already_started"
    with pytest.raises(AiError) as error:
        restarted.state(identifier, "3:2")
    assert error.value.code == "conversation_configuration_changed"
    assert restarted.state(identifier, "1:2")[1]["used"] == 1


@pytest.mark.parametrize(
    "bad",
    [
        {"used": 0},
        {"binding": "1:1", "used": True, "expires": 9999999999, "turns": []},
        {"binding": "1:1", "used": 0, "expires": float("nan"), "turns": []},
    ],
)
def test_corrupt_ledger_fails_closed_without_overwrite(tmp_path, bad):
    path = tmp_path / "ledger.json"
    original = json.dumps({"a" * 32: bad})
    path.write_text(original)
    ledger = ConversationLedger(path)
    with pytest.raises(AiError) as error:
        ledger.create("1:1")
    assert error.value.code == "conversation_storage_unavailable"
    assert path.read_text() == original


def test_elevenlabs_saved_voice_pagination_models_and_one_synthesis(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        assert request.headers["xi-api-key"] == "fake-key"
        if request.url.path == "/v2/voices":
            assert request.url.params["voice_type"] in {"saved", "default"}
            if request.url.params["voice_type"] == "default":
                return httpx.Response(200, json={"voices": [], "has_more": False})
            page = request.url.params.get("next_page_token")
            return httpx.Response(
                200,
                json={
                    "voices": [
                        {
                            "voice_id": "voice2" if page else "voice1",
                            "name": "Configured voice",
                            "labels": {"language": "es"},
                        }
                    ],
                    "has_more": not page,
                    "next_page_token": "next" if not page else "",
                },
            )
        if request.url.path == "/v1/models":
            return httpx.Response(
                200,
                json=[
                    {"model_id": "tts1", "name": "TTS", "can_do_text_to_speech": True},
                    {"model_id": "stt", "can_do_text_to_speech": False},
                ],
            )
        assert request.url.path == "/v1/text-to-speech/voice2"
        assert json.loads(request.content) == {"text": "Prueba", "model_id": "tts1"}
        return httpx.Response(
            200, content=b"ID3fakeaudio", headers={"Content-Type": "audio/mpeg"}
        )

    gateway = MediaGateway(
        {"elevenlabs": "fake-key"}, tmp_path, httpx.MockTransport(handler)
    )
    catalog = run(gateway.catalog("elevenlabs"))
    assert [item["id"] for item in catalog["voices"]] == ["voice1", "voice2"]
    assert [item["id"] for item in catalog["models"]] == ["tts1"]
    audio, mime = run(
        gateway.synthesize(
            MediaSettings(voice_id="voice2", voice_model="tts1"), "Prueba", catalog
        )
    )
    assert audio == b"ID3fakeaudio" and mime == "audio/mpeg"
    assert len(calls) == 5


def test_google_voice_selection_and_key_header(tmp_path):
    def handler(request):
        assert request.headers["x-goog-api-key"] == "fake-google"
        if request.url.path.endswith("voices"):
            return httpx.Response(
                200,
                json={
                    "voices": [{"name": "es-US-Standard-A", "languageCodes": ["es-US"]}]
                },
            )
        body = json.loads(request.content)
        assert body["voice"] == {"languageCode": "es-US", "name": "es-US-Standard-A"}
        assert body["audioConfig"]["audioEncoding"] == "MP3"
        return httpx.Response(
            200, json={"audioContent": base64.b64encode(b"ID3audio").decode()}
        )

    gateway = MediaGateway(
        {"google_tts": "fake-google"}, tmp_path, httpx.MockTransport(handler)
    )
    catalog = run(gateway.catalog("google_tts"))
    assert (
        run(
            gateway.synthesize(
                MediaSettings(voice_provider="google_tts", voice_id="es-US-Standard-A"),
                "Hola",
                catalog,
            )
        )[0]
        == b"ID3audio"
    )
    with pytest.raises(AiError) as error:
        run(
            gateway.synthesize(
                MediaSettings(voice_provider="google_tts", voice_id="not-catalog"),
                "Hola",
                catalog,
            )
        )
    assert error.value.code == "voice_catalog_required"


@pytest.mark.parametrize("provider", ["tavily", "brave", "serpapi"])
@pytest.mark.parametrize("kind", ["web", "images"])
def test_search_fixed_urls_redacted_and_bounded_sources(tmp_path, provider, kind):
    def handler(request):
        if provider == "tavily":
            assert request.headers["Authorization"] == "Bearer fake-key"
            body = json.loads(request.content)
            assert (
                body["include_raw_content"] is False and body["search_depth"] == "basic"
            )
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "title": "Safe",
                            "url": "https://example.com",
                            "content": "Context",
                        },
                        {"title": "Local", "url": "https://localhost"},
                    ],
                    "images": [
                        {"url": "https://example.com/image.png", "description": "Image"}
                    ],
                },
            )
        if provider == "brave":
            assert request.headers["X-Subscription-Token"] == "fake-key"
            assert request.url.params["safesearch"] == "strict"
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "title": "Safe",
                            "url": "https://example.com",
                            "properties": {"url": "https://example.com/image.png"},
                        }
                    ],
                    "web": {
                        "results": [{"title": "Safe", "url": "https://example.com"}]
                    },
                },
            )
        assert request.url.params["api_key"] == "fake-key"
        return httpx.Response(
            200,
            json={
                "search_metadata": {"status": "Success"},
                "search_parameters": {"api_key": "fake-key"},
                "images_results": [
                    {
                        "title": "Safe",
                        "link": "https://example.com",
                        "original": "https://example.com/image.png",
                    }
                ],
                "organic_results": [
                    {
                        "title": "Safe",
                        "link": "https://example.com",
                        "snippet": "Context",
                    }
                ],
            },
        )

    gateway = MediaGateway(
        {provider: "fake-key"}, tmp_path, httpx.MockTransport(handler)
    )
    result = run(gateway.search(provider, "Consulta ficticia", kind))
    assert len(result) == 1
    assert "fake-key" not in json.dumps(result)
    assert result[0]["url"].startswith("https://example.com")


@pytest.mark.parametrize("status", [301, 401, 403, 429, 432, 433, 500])
def test_provider_failure_never_leaks_body_or_retries(tmp_path, status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, json={"error": "fake-secret"})

    gateway = MediaGateway(
        {"tavily": "fake-secret"}, tmp_path, httpx.MockTransport(handler)
    )
    with pytest.raises(AiError) as error:
        run(gateway.search("tavily", "Prueba", "web"))
    assert len(calls) == 1
    assert "fake-secret" not in error.value.code


def make_service(tmp_path, media):
    service = AiService(
        SettingsRepository(tmp_path / "settings.json"),
        ProviderGateway({"gemini": "fake"}),
        True,
    )
    settings = AiSettings(enabled=True, model="chat", media=media)
    service.repository.save(SaveSettings(revision=0, settings=settings))
    service.catalogs["gemini"] = {"chat": ModelInfo(id="chat", name="Chat")}
    service.voice_catalogs["piper"] = {
        "voices": [{"id": "test", "name": "Test", "language": "es"}],
        "models": [],
        "ready": True,
        "local": True,
    }
    return service


@pytest.mark.parametrize(
    "enabled,prefer,incoming,reply,limited,cap,decision,expected",
    [
        (False, True, False, False, False, 3, True, False),
        (True, True, False, False, True, 0, True, False),
        (True, True, False, False, True, 1, False, True),
        (True, False, True, True, False, 3, False, True),
        (True, False, False, True, False, 3, False, False),
        (True, False, False, False, False, 3, True, True),
        (True, False, False, False, False, 3, False, False),
    ],
)
def test_voice_rule_precedence_and_server_quota(
    tmp_path, enabled, prefer, incoming, reply, limited, cap, decision, expected
):
    media = MediaSettings(
        voice_enabled=enabled,
        prefer_voice=prefer,
        reply_audio_with_voice=reply,
        voice_limit_enabled=limited,
        voice_limit=cap,
        voice_provider="piper",
        voice_id="test",
        audio_model="chat",
    )
    service = make_service(tmp_path, media)
    calls = []

    async def generate(provider, model, settings, system, messages, **kwargs):
        assert "asistente virtual" in system
        return (
            json.dumps({"text": "Hola", "use_voice": decision})
            if "VOICE_DECISION_JSON" in system
            else "Hola"
        )

    async def synthesize(*args):
        calls.append(args)
        return b"RIFF1234WAVE", "audio/wav"

    async def analyze(*args):
        return {"candidates": [{"content": {"parts": [{"text": "Audio ficticio"}]}}]}

    service.gateway.generate = generate
    service.gateway.request = analyze
    service.media_gateway.synthesize = synthesize
    identifier = service.create_conversation()["conversation_id"]
    request = MediaChatRequest(
        revision=1,
        credential_revision=0,
        conversation_id=identifier,
        turn_id=secrets.token_hex(16),
        prompt="Hola",
        attachment=Attachment(
            mime_type="audio/wav", data=base64.b64encode(b"RIFF1234WAVE").decode()
        )
        if incoming
        else None,
    )
    result = run(service.media_chat(request))
    assert result["text"] == "Hola"
    assert bool(result["audio_id"]) == expected
    assert len(calls) == int(expected)
    assert result["voice_attempts"] == int(expected)
    if expected and limited:
        second = request.model_copy(update={"turn_id": secrets.token_hex(16)})
        result = run(service.media_chat(second))
        assert result["voice_status"] == "limit_reached" and len(calls) == 1


def test_failed_synthesis_reserves_budget_and_rejects_retry(tmp_path):
    service = make_service(
        tmp_path,
        MediaSettings(
            voice_enabled=True,
            prefer_voice=True,
            voice_limit_enabled=True,
            voice_limit=1,
            voice_provider="piper",
            voice_id="test",
        ),
    )

    async def generate(*args, **kwargs):
        return "Texto conservado"

    async def fail(*args):
        raise AiError("provider_timeout_or_network", 504)

    service.gateway.generate = generate
    service.media_gateway.synthesize = fail
    identifier = service.create_conversation()["conversation_id"]
    request = MediaChatRequest(
        revision=1,
        credential_revision=0,
        conversation_id=identifier,
        turn_id=secrets.token_hex(16),
        prompt="Prueba",
    )
    result = run(service.media_chat(request))
    assert result["text"] == "Texto conservado" and result["voice_attempts"] == 1
    assert result["voice_status"] == "failed_text_preserved"
    with pytest.raises(AiError) as error:
        run(service.media_chat(request))
    assert error.value.code == "turn_already_started"
    assert (
        ConversationLedger(service.ledger.path).state(identifier, "1:0")[1]["used"] == 1
    )


def test_media_routes_keep_guards_and_old_request_limits(tmp_path):
    service = make_service(tmp_path, MediaSettings())
    with TestClient(
        create_app(service),
        base_url="http://127.0.0.1:8002",
        client=("127.0.0.1", 1234),
        headers={"X-CRM-Local": "1"},
    ) as client:
        assert client.post("/api/ai/conversation", json={}).status_code == 200
        assert (
            client.post(
                "/api/ai/conversation",
                json={},
                headers={"Origin": "https://evil.example"},
            ).status_code
            == 403
        )
        assert client.post("/api/ai/voice-catalog/unknown", json={}).status_code == 400
        assert client.get("/api/ai/media/unknown").status_code == 404
        assert (
            client.get(
                "/api/ai/media/unknown", headers={"X-CRM-Local": "0"}
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/api/ai/chat",
                content=" " * 64001,
                headers={"Content-Type": "application/json"},
            ).status_code
            == 413
        )
        assert client.post(
            "/api/ai/media-chat", json={"api_key": "DoNotEcho"}
        ).json() == {"code": "invalid_request"}


def test_attachment_context_not_lost_when_history_disabled(tmp_path):
    service = make_service(tmp_path, MediaSettings(audio_model="chat"))
    current = service.repository.read()
    current.settings.recent_messages = 0
    service.repository.save(current)
    captured = []

    async def generate(*args, **kwargs):
        captured.append(args[-1])
        return "Contexto leído"

    async def analyze(*args):
        return {"candidates": [{"content": {"parts": [{"text": "COLOR_VIOLETA"}]}}]}

    service.gateway.generate = generate
    service.gateway.request = analyze
    identifier = service.create_conversation()["conversation_id"]
    result = run(
        service.media_chat(
            MediaChatRequest(
                revision=2,
                credential_revision=0,
                conversation_id=identifier,
                turn_id=secrets.token_hex(16),
                attachment=Attachment(
                    mime_type="audio/wav",
                    data=base64.b64encode(b"RIFF1234WAVE").decode(),
                ),
            )
        )
    )
    assert "COLOR_VIOLETA" in captured[0][-1]["content"]
    assert result["attachment_text"] == "COLOR_VIOLETA"


def test_invalid_decision_never_spends_voice(tmp_path):
    service = make_service(
        tmp_path,
        MediaSettings(voice_enabled=True, voice_provider="piper", voice_id="test"),
    )

    async def generate(*args, **kwargs):
        return '{"text":"Hola","use_voice":"yes"}'

    service.gateway.generate = generate
    identifier = service.create_conversation()["conversation_id"]
    result = run(
        service.media_chat(
            MediaChatRequest(
                revision=1,
                credential_revision=0,
                conversation_id=identifier,
                turn_id=secrets.token_hex(16),
                prompt="Prueba",
            )
        )
    )
    assert result["audio_id"] is None and result["voice_attempts"] == 0


def test_piper_cancellation_kills_child_and_cleans_output(tmp_path, monkeypatch):
    async def scenario():
        entered = asyncio.Event()
        process = Mock(returncode=None)

        async def communicate(_text):
            entered.set()
            await asyncio.Event().wait()

        process.communicate = communicate
        process.wait = AsyncMock(return_value=-9)
        monkeypatch.setattr(
            asyncio, "create_subprocess_exec", AsyncMock(return_value=process)
        )
        directory = tmp_path / "piper" / "voices"
        directory.mkdir(parents=True)
        (directory / "test.onnx").write_bytes(b"fixture")
        gateway = MediaGateway({}, tmp_path)
        task = asyncio.create_task(
            gateway.synthesize(
                MediaSettings(voice_provider="piper", voice_id="test"),
                "Texto",
                {"voices": [{"id": "test", "language": "es"}], "ready": True},
            )
        )
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        process.kill.assert_called_once()
        process.wait.assert_awaited_once()
        assert not list((tmp_path / "piper").glob("*.wav"))

    run(scenario())


def test_singleflight_and_reservation_precede_paid_attempt(tmp_path):
    async def scenario():
        service = make_service(
            tmp_path,
            MediaSettings(
                voice_enabled=True,
                prefer_voice=True,
                voice_limit_enabled=True,
                voice_limit=1,
                voice_provider="piper",
                voice_id="test",
            ),
        )
        started, finish = asyncio.Event(), asyncio.Event()

        async def generate(*args, **kwargs):
            started.set()
            await finish.wait()
            return "Hola"

        identifier = service.create_conversation()["conversation_id"]

        async def synthesize(*args):
            assert service.ledger.state(identifier, "1:0")[1]["used"] == 1
            return b"RIFF1234WAVE", "audio/wav"

        service.gateway.generate, service.media_gateway.synthesize = (
            generate,
            synthesize,
        )
        request = MediaChatRequest(
            revision=1,
            credential_revision=0,
            conversation_id=identifier,
            turn_id=secrets.token_hex(16),
            prompt="Prueba",
        )
        task = asyncio.create_task(service.media_chat(request))
        await started.wait()
        with pytest.raises(AiError) as error:
            await service.media_chat(
                request.model_copy(update={"turn_id": secrets.token_hex(16)})
            )
        assert error.value.code == "operation_busy"
        assert len(service.ledger.state(identifier, "1:0")[1]["turns"]) == 1
        finish.set()
        result = await task
        assert result["voice_status"] == "generated"
        assert service.audio_media(result["audio_id"])[1] == "audio/wav"

    run(scenario())


@pytest.mark.parametrize(
    "payload",
    [
        {"voices": None},
        {"voices": [None]},
        {"voices": [{"name": "test", "languageCodes": 1}]},
    ],
)
def test_invalid_google_catalog_shapes_are_bounded(tmp_path, payload):
    gateway = MediaGateway(
        {"google_tts": "fake"},
        tmp_path,
        httpx.MockTransport(lambda _: httpx.Response(200, json=payload)),
    )
    if payload["voices"] is None:
        with pytest.raises(AiError) as error:
            run(gateway.catalog("google_tts"))
        assert error.value.code == "provider_invalid_response"
    else:
        assert run(gateway.catalog("google_tts"))["voices"] == []
