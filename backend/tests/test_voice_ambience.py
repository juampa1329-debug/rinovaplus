import hashlib
import json
import math
import shutil
import struct
import subprocess
import wave
from contextlib import nullcontext
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.institutional import voice_ambience as ambience, voice_audio as voice
from app.institutional.voice_policy import VoiceAmbience, VoiceProfile


@pytest.mark.parametrize("change", [
    {"office_volume": -1}, {"typing_volume": 1.1}, {"voice_volume": 0},
    {"voice_volume": float("nan")}, {"office_volume": float("inf")}, {"url": "https://invalid"},
])
def test_mix_rejects_nonfinite_out_of_range_or_external_assets(change):
    with pytest.raises(ValidationError):
        VoiceAmbience(**change)


def test_existing_profiles_are_dry_and_ducking_is_default():
    profile = VoiceProfile(id="juampa", name="Juampa", voice_id="voice", model_id="model")
    assert profile.ambience.enabled is False and profile.ambience.ducking is True
    graph = ambience.filter_graph(VoiceAmbience(enabled=True, office_volume=0, typing_volume=0.3), 12)
    assert "volume=0.0000[office]" in graph and "volume=0.3000[typing]" in graph
    assert "sidechaincompress" in graph and "duration=first" in graph
    assert "sidechaincompress" not in ambience.filter_graph(VoiceAmbience(ducking=False), 12)


def test_disabled_mix_is_identical_and_does_not_require_ffmpeg(tmp_path, monkeypatch):
    source, output = tmp_path / "dry", tmp_path / "mixed"
    source.write_bytes(b"OggS-original")
    monkeypatch.setattr(ambience.shutil, "which", lambda *_: pytest.fail("no encoder for disabled mix"))
    ambience.mix(source, output, {}, 2)
    assert output.read_bytes() == source.read_bytes()


def setup_route(monkeypatch, tmp_path, *, deny=False):
    app = FastAPI()
    @app.middleware("http")
    async def authority(request, call_next):
        request.state.authority = "test"
        return await call_next(request)
    monkeypatch.setattr(voice, "transaction", lambda *_a, **_k: nullcontext(None))
    actor, media = str(uuid4()), str(uuid4())
    source = tmp_path / (media + ".dry")
    source.write_bytes(b"inspected-private-audio")
    record = {"media": media, "duration": 3, "receipt": {"ambience": {"dry_hash": hashlib.sha256(source.read_bytes()).hexdigest()}}}
    def authorize(*_a, **_k):
        if deny:
            raise HTTPException(403, "action_denied")
        return {"UserId": actor}
    monkeypatch.setattr(voice, "authorize", authorize)
    monkeypatch.setattr(voice, "institution", lambda *_: "institution")
    queries = []
    def one(_c, sql, *args):
        queries.append((sql, args))
        return {"ResultMetadata": json.dumps(record)}
    monkeypatch.setattr(voice, "one", one)
    monkeypatch.setattr(voice.files, "path", lambda identifier, suffix=".bin": tmp_path / (str(identifier) + suffix))
    voice.install(app, None)
    return app, source, queries, actor


def test_private_remix_is_owner_scoped_no_provider_no_writes_and_cleans_temp(monkeypatch, tmp_path):
    app, source, queries, actor = setup_route(monkeypatch, tmp_path)
    monkeypatch.setattr(voice, "stored_key", lambda *_: pytest.fail("no paid provider for remix"))
    def render(src, dst, options, duration):
        assert src == source and options.typing_volume == 0.2 and duration == 3
        dst.write_bytes(b"OggS-mixed")
    monkeypatch.setattr(ambience, "mix", render)
    with TestClient(app) as client:
        response = client.get(f"/api/institution/voice/previews/{uuid4()}/mix?typing_volume=0.2")
    assert response.status_code == 200 and response.content == b"OggS-mixed"
    assert response.headers["cache-control"] == "private, no-store"
    assert len(queries) == 2 and all("ActorRef=?" in sql and args[-1] == actor and "hour,-24" in sql for sql, args in queries)
    assert not list(tmp_path.glob("*.mixed"))


def test_private_remix_denies_before_read_and_rejects_changed_master(monkeypatch, tmp_path):
    app, _, queries, _ = setup_route(monkeypatch, tmp_path, deny=True)
    with TestClient(app) as client:
        assert client.get(f"/api/institution/voice/previews/{uuid4()}/mix").status_code == 403
    assert not queries
    app, source, _, _ = setup_route(monkeypatch, tmp_path)
    source.write_bytes(b"changed")
    monkeypatch.setattr(ambience, "mix", lambda *_: pytest.fail("tampered source"))
    with TestClient(app) as client:
        assert client.get(f"/api/institution/voice/previews/{uuid4()}/mix").status_code == 404
        assert client.get(f"/api/institution/voice/previews/{uuid4()}/mix?office_volume=nan").status_code == 422


def wav(path, values, rate=48000):
    with wave.open(str(path), "wb") as output:
        output.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        output.writeframes(b"".join(struct.pack("<h", round(v * 32767)) for v in values))


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="Real encoder required")
def test_real_opus_mix_ducks_background_without_cutting_voice(tmp_path, monkeypatch):
    rate, duration = 48000, 4
    source = tmp_path / "source.wav"
    wav(source, [0.35 * math.sin(2 * math.pi * 1000 * n / rate) if rate <= n < 3 * rate else 0 for n in range(rate * duration)])
    wav(tmp_path / "office.wav", [0.2 * math.sin(2 * math.pi * 220 * n / rate) for n in range(rate)])
    wav(tmp_path / "typing.wav", [0 for _ in range(rate)])
    monkeypatch.setattr(ambience, "ASSETS", tmp_path)
    levels = {}
    for duck in (False, True):
        output = tmp_path / f"mix-{duck}.ogg"
        ambience.mix(source, output, VoiceAmbience(enabled=True, office_volume=1.0, typing_volume=0.0, ducking=duck), duration)
        pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(output), "-f", "f32le", "-ac", "1", "-ar", str(rate), "pipe:1"], capture_output=True, check=True).stdout
        values = struct.unpack("<" + "f" * (len(pcm) // 4), pcm)
        assert abs(len(values) / rate - duration) < 0.04
        assert max(abs(v) for v in values) < 0.99
        def amplitude(start, end):
            indices = range(int(start * rate), int(end * rate))
            return abs(sum(values[n] * math.sin(2 * math.pi * 220 * n / rate) for n in indices) / len(indices))
        levels[duck] = (amplitude(0.4, 0.8), amplitude(1.8, 2.4))
    assert levels[True][1] < levels[False][1] * 0.6
    assert levels[True][0] == pytest.approx(levels[False][0], rel=0.1)
