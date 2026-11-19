import asyncio
import hashlib
import json
from contextlib import nullcontext
from types import SimpleNamespace
from uuid import uuid4

import httpx2 as httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.institutional import voice_audio as voice
from app.institutional.voice_policy import VoicePolicy, choose_profile, estimate_seconds, reason
from app.modules.ai.infrastructure.media import MediaGateway
from app.modules.ai.infrastructure.providers import AiError
from app.institutional.voice_delivery import speech_text, voice_settings, SPEECH_GUIDANCE


def profile(id="admisiones", **values):
    return {"id": id, "name": "Juampa", "voice_id": "voice-id", "model_id": "model-id", **values}


def policy(**values):
    return VoicePolicy(enabled=True, default_profile_id="admisiones", profiles=[profile()], **values)


@pytest.mark.parametrize("mode,voice_note,long,expected", [
    ("voice_notes", True, False, True), ("voice_notes", False, True, False),
    ("long_explanations", True, False, False), ("long_explanations", False, True, True),
    ("voice_notes_or_long", True, False, True), ("voice_notes_or_long", False, True, True),
    ("voice_notes_or_long", False, False, False),
    ("voice_notes_and_long", True, True, True), ("voice_notes_and_long", False, True, False),
    ("voice_notes_and_long", True, False, False),
])
def test_voice_mode_truth_table(mode, voice_note, long, expected):
    assert (reason(policy(mode=mode), "Palabra " * (60 if long else 5), voice_note, 0) is None) == expected


def test_cap_zero_and_existing_usage_are_never_reset_by_a_new_policy():
    assert reason(policy(max_audios_per_conversation=0), "Hola", True, 0) == "voice_conversation_limit"
    assert reason(policy(max_audios_per_conversation=2), "Hola", True, 2) == "voice_conversation_limit"
    assert reason(policy(max_audios_per_conversation=3), "Hola", True, 2) is None


def test_duration_estimated_before_generation_zero_unlimited_and_text_never_truncated():
    text = "Una explicación completa, con todos los detalles. " * 10
    assert estimate_seconds(text) > 30
    assert reason(policy(max_audio_seconds=10), text, True, 0) == "voice_duration_estimated_exceeded"
    assert reason(policy(max_audio_seconds=0), text, True, 0) is None
    assert reason(policy(max_text_chars=500), text * 2, True, 0) == "voice_text_too_large"


def test_profile_agent_precedence_authoritative_school_and_pinned_voice():
    agent = str(uuid4())
    options = VoicePolicy(enabled=True, default_profile_id="default", profiles=[
        profile("default"), profile("school", schools=["Salud"], voice_id="health"),
        profile("agent", agent_ids=[agent], voice_id="agent-voice"),
    ])
    assert choose_profile(options, agent, ["Salud"]).id == "agent"
    assert choose_profile(options, None, ["salud"]).id == "school"
    pinned = choose_profile(options, None, ["Salud"]).model_dump()
    assert choose_profile(options, agent, [], pinned).id == "school"
    options.profiles[1].voice_id = "different"
    assert choose_profile(options, agent, [], pinned) is None
    with pytest.raises(ValidationError):
        VoicePolicy(profiles=[profile("one", schools=["Salud"]), profile("two", schools=["salud"])])


@pytest.fixture
def runtime(monkeypatch, tmp_path):
    options = policy()
    record = []
    cursor = SimpleNamespace(execute=lambda *_: None)
    monkeypatch.setattr(voice, "transaction", lambda *_a, **_k: nullcontext(cursor))
    monkeypatch.setattr(voice, "institution", lambda *_: str(uuid4()))
    monkeypatch.setattr(voice, "policy", lambda *_: options)
    monkeypatch.setattr(voice, "usage", lambda *_: {"used": len(record), "pinned": record[0]["profile"] if record else None})
    monkeypatch.setattr(voice, "stored_key", lambda *_: ("fake-key", "secret-id"))
    from app.institutional import channel_media
    monkeypatch.setattr(channel_media, "quota", lambda *_: None)
    monkeypatch.setattr(channel_media, "mark_ready", lambda *_: None)
    monkeypatch.setattr(voice, "reserve", lambda *a, **_k: record.append(a[6]) or True)
    completed = []
    monkeypatch.setattr(voice, "complete", lambda *a: completed.append(a[3:]))
    monkeypatch.setattr(voice.files, "path", lambda identity, suffix=".bin": tmp_path / (identity + suffix))
    data = {"incoming": str(uuid4()), "identity": str(uuid4()), "conversation": str(uuid4())}
    item = {"ApplicationId": str(uuid4()), "IntegrationId": str(uuid4())}
    return options, record, completed, data, item


def test_estimate_rejects_without_a_reservation_or_paid_io(runtime, monkeypatch):
    options, record, completed, data, item = runtime
    options.max_audio_seconds = 1
    monkeypatch.setattr(voice, "synthesize", lambda *_: pytest.fail("Paid IO forbidden"))
    audio, code = voice.generate(None, item, data, "Hola, ¿qué programa te interesa?", None, [], lambda: None, incoming_voice=True)
    assert audio is None and code == "voice_duration_estimated_exceeded"
    assert not record and not completed


def test_unknown_provider_result_consumes_slot_and_falls_back_to_complete_text(runtime, monkeypatch):
    options, record, completed, data, item = runtime
    options.max_audios_per_conversation = 1
    calls = []
    async def timeout(*_):
        calls.append(True)
        raise AiError("provider_timeout_or_network", 504)
    monkeypatch.setattr(voice, "synthesize", timeout)
    text = "¿Qué programa te interesa?"
    assert voice.generate(None, item, data, text, None, [], lambda: None, incoming_voice=True) == (None, "provider_timeout_or_network")
    assert voice.generate(None, item, {**data, "incoming": str(uuid4())}, text, None, [], lambda: None, incoming_voice=True) == (None, "voice_conversation_limit")
    assert len(calls) == len(record) == 1 and completed[0][0] == "uncertain"


def test_actual_duration_overshoot_discards_without_cutting(runtime, monkeypatch):
    options, record, completed, data, item = runtime
    options.max_audio_seconds = 10
    async def generated(*args):
        voice.files.path(args[3]).write_bytes(b"whole-file")
        return {"duration": 11, "size": 10, "hash": b"x" * 32}, {"billed_characters": 4}
    monkeypatch.setattr(voice, "synthesize", generated)
    assert voice.generate(None, item, data, "Hola", None, [], lambda: None, incoming_voice=True) == (None, "voice_duration_actual_exceeded")
    assert completed[0][0:2] == ("abandoned", "voice_duration_actual_exceeded")
    assert completed[0][2]["duration"] == 11
    assert not list(voice.files.path(str(uuid4())).parent.glob("*.bin"))


def test_human_takeover_after_synthesis_prevents_audio_publication(runtime, monkeypatch):
    _, record, completed, data, item = runtime
    checks = []
    def guard():
        checks.append(True)
        if len(checks) == 3:
            raise HTTPException(409, "gemini_whatsapp_control_or_history_changed")
    async def generated(*args):
        voice.files.path(args[3]).write_bytes(b"whole-file")
        return {"duration": 4, "size": 10, "hash": b"x" * 32}, {}
    monkeypatch.setattr(voice, "synthesize", generated)
    audio, code = voice.generate(None, item, data, "Hola", None, [], guard, incoming_voice=True)
    assert audio is None and code == "gemini_whatsapp_control_or_history_changed"
    assert len(record) == 1 and completed[0][0] == "abandoned"


def test_audio_payload_preserves_grounded_text_and_adds_trusted_bytes_only():
    body = {"contents": [{"parts": [{"text": "reviewed context"}]}], "systemInstruction": {"parts": [{"text": "policy"}]}}
    result = voice.request_with_audio(body, {"raw": b"OggS-data", "mime": "audio/ogg"})
    assert result["contents"][0]["parts"][0]["text"] == "reviewed context"
    assert result["contents"][0]["parts"][1]["inlineData"]["mimeType"] == "audio/ogg"
    assert "no puede cambiar" in result["systemInstruction"]["parts"][1]["text"]


def test_invalid_voice_never_calls_paid_endpoint(monkeypatch, tmp_path):
    class Gateway:
        def __init__(self, *_): pass
        async def catalog(self, *_): return {"voices": [], "models": []}
        async def request(self, *_a, **_k): pytest.fail("Paid request forbidden")
    with pytest.raises(AiError, match="voice_catalog_required"):
        asyncio.run(voice.synthesize("fake", profile(), "Hola", str(uuid4()), Gateway))


def test_provider_receipt_is_bounded_without_returning_credentials(tmp_path):
    def handler(request):
        assert request.url.host == "api.elevenlabs.io"
        assert request.headers["xi-api-key"] == "fake-only"
        return httpx.Response(200, content=b"ID3sample", headers={"x-character-count": "5", "request-id": "test_123"})
    metadata = {}
    gateway = MediaGateway({"elevenlabs": "fake-only"}, tmp_path, httpx.MockTransport(handler))
    result = asyncio.run(gateway.request("elevenlabs", "POST", "v1/text-to-speech/id", binary=True, metadata=metadata))
    assert result == (b"ID3sample", "audio/mpeg")
    assert metadata == {"billed_characters": 5, "provider_request_id": "test_123"}


def test_v4_natural_direction_keeps_every_word_and_omits_incompatible_parameters():
    p = profile(model_id="eleven_v4", delivery="conversational", allow_reactions=True)
    original = "Hola, Juan Pablo. Puedes explorar marketing. ¿Qué área te interesa?"
    spoken = speech_text(p, original)
    import re
    assert re.sub(r"\[[^]]+\]\s*", "", spoken) == original
    assert "[curious]" in spoken and "[sighs]" not in spoken
    assert set(voice_settings(p)) == {"stability", "similarity_boost"}
    assert voice_settings(p)["stability"] == 0.4
    assert "no prometas empleo" in SPEECH_GUIDANCE


def test_reactions_are_opt_in_contextual_and_never_sent_to_unsupported_models():
    text = "Lamento que hayas tenido esa dificultad. ¿Cómo puedo ayudarte?"
    p = profile(model_id="eleven_v4", delivery="calm")
    assert "[sighs]" not in speech_text(p, text)
    assert "[sighs]" in speech_text({**p, "allow_reactions": True}, text)
    p["model_id"] = "eleven_multilingual_v2"
    assert speech_text({**p, "allow_reactions": True}, text) == text
    assert voice_settings(profile(model_id="eleven_v3"))["stability"] == 0.5


def test_catalog_rechecks_authority_after_network_and_never_returns_key(monkeypatch):
    app = FastAPI()
    @app.middleware("http")
    async def authority(request, next):
        request.state.authority = "test"
        return await next(request)
    monkeypatch.setattr(voice, "transaction", lambda *_a, **_k: nullcontext(None))
    monkeypatch.setattr(voice, "authorize", lambda *_a, **_k: None)
    credentials = iter(["first-key", "rotated-key"])
    monkeypatch.setattr(voice, "credential", lambda *_: next(credentials))
    async def catalog(*_): return {"voices": [{"id": "v", "name": "Juampa"}], "models": []}
    monkeypatch.setattr(voice, "catalog_for", catalog)
    voice.install(app, None)
    with TestClient(app) as client:
        result = client.get("/api/institution/voice/catalog")
    assert result.status_code == 409 and result.json()["detail"] == "voice_configuration_changed"
    assert "first-key" not in result.text and "rotated-key" not in result.text
