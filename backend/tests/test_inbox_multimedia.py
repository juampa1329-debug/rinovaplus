import shutil
import subprocess
from uuid import uuid4

import pytest
from fastapi import HTTPException
from PIL import Image

from app.institutional.channel_media import inspect_attachment
from app.modules.channels import providers
from app.modules.inbox.infrastructure import media_files as files


def test_sticker_is_sanitized_and_keeps_the_private_image_schema(tmp_path, monkeypatch):
    monkeypatch.setenv("CRM_AI_STATE_DIR", str(tmp_path))
    identity = uuid4()
    Image.new("RGBA", (512, 512), (20, 52, 59, 220)).save(files.path(identity, ".part"), "WEBP")
    result = inspect_attachment(identity, "saludo.webp")
    assert result["kind"] == "image" and result["mime"] == "image/webp"
    assert result["size"] <= 100_000
    assert not files.path(identity, ".part").exists()
    with Image.open(files.path(identity)) as sticker:
        assert sticker.size == (512, 512) and sticker.n_frames == 1

    Image.new("RGB", (128, 128), "green").save(files.path(identity, ".part"), "WEBP")
    with pytest.raises(HTTPException) as error:
        inspect_attachment(identity, "saludo.webp")
    assert error.value.detail == "media_sticker_invalid"


def test_incoming_sticker_preserves_animation(tmp_path, monkeypatch):
    monkeypatch.setenv("CRM_AI_STATE_DIR", str(tmp_path))
    identity = uuid4()
    frames = [Image.new("RGB", (512, 512), color) for color in ("red", "blue")]
    frames[0].save(files.path(identity, ".part"), "WEBP", save_all=True,
                   append_images=frames[1:], duration=[100, 250], loop=0)
    raw = files.path(identity, ".part").read_bytes()
    result = inspect_attachment(identity, "sticker.webp", incoming=True)
    assert result["mime"] == "image/webp"
    assert files.path(identity).read_bytes() == raw
    with Image.open(files.path(identity)) as sticker:
        assert sticker.n_frames == 2
        sticker.seek(1)
        sticker.load()


@pytest.mark.parametrize("incoming", [False, True])
def test_animated_sticker_over_static_limit_preserves_frames(tmp_path, monkeypatch, incoming):
    monkeypatch.setenv("CRM_AI_STATE_DIR", str(tmp_path))
    identity = uuid4()
    frames = [Image.effect_noise((512, 512), 40).convert("RGBA") for _ in range(3)]
    frames[0].save(files.path(identity, ".part"), "WEBP", save_all=True,
                   append_images=frames[1:], duration=[100, 200, 300], loop=0, quality=80)
    raw = files.path(identity, ".part").read_bytes()
    assert 100_000 < len(raw) <= 500_000
    result = inspect_attachment(identity, "animado.webp", incoming=incoming)
    assert result["mime"] == "image/webp" and result["size"] == len(raw)
    assert files.path(identity).read_bytes() == raw
    with Image.open(files.path(identity)) as sticker:
        assert sticker.n_frames == 3
        durations = []
        for frame in range(sticker.n_frames):
            sticker.seek(frame)
            sticker.load()
            durations.append(sticker.info["duration"])
        assert durations == [100, 200, 300]


@pytest.mark.parametrize("durations,accepted", [([8, 8], True), ([5000, 5000], True),
                                                   ([7, 100], False), ([5001, 5000], False)])
def test_outgoing_animation_duration_bounds(tmp_path, monkeypatch, durations, accepted):
    monkeypatch.setenv("CRM_AI_STATE_DIR", str(tmp_path))
    identity = uuid4()
    frames = [Image.new("RGBA", (512, 512), color) for color in ("red", "blue")]
    frames[0].save(files.path(identity, ".part"), "WEBP", save_all=True,
                   append_images=frames[1:], duration=durations, loop=0)
    if accepted:
        assert inspect_attachment(identity, "animado.webp")["mime"] == "image/webp"
    else:
        with pytest.raises(HTTPException) as error:
            inspect_attachment(identity, "animado.webp")
        assert error.value.detail == "media_sticker_invalid"
        assert not files.path(identity).exists()
    assert not files.path(identity, ".part").exists()
    assert not files.path(identity, ".checked").exists()


@pytest.mark.parametrize("animated", [False, True])
def test_outgoing_sticker_rejects_over_its_type_limit(tmp_path, monkeypatch, animated):
    monkeypatch.setenv("CRM_AI_STATE_DIR", str(tmp_path))
    identity = uuid4()
    frames = [Image.new("RGBA", (512, 512), color) for color in ("red", "blue")]
    frames[0].save(files.path(identity, ".part"), "WEBP", save_all=animated,
                   append_images=frames[1:] if animated else [], duration=100, loop=0,
                   exif=b"x" * (500_001 if animated else 100_001))
    with pytest.raises(HTTPException) as error:
        inspect_attachment(identity, "pesado.webp")
    assert error.value.detail == "media_sticker_limit"
    assert not files.path(identity).exists()
    assert not files.path(identity, ".part").exists()


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="FFmpeg unavailable")
@pytest.mark.parametrize(("kind", "source", "suffix", "mime"), [
    ("audio", "sine=frequency=440:duration=1", "webm", "audio/ogg"),
    ("video", "color=c=green:s=320x180:d=1", "mp4", "video/mp4"),
])
def test_inbox_inspects_real_audio_and_video(tmp_path, monkeypatch, kind, source, suffix, mime):
    monkeypatch.setenv("CRM_AI_STATE_DIR", str(tmp_path))
    identity = uuid4()
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", source,
         "-f", suffix, str(files.path(identity, ".part"))],
        check=True, timeout=12,
    )
    result = inspect_attachment(identity, f"prueba.{suffix}", kind)
    assert result["kind"] == kind and result["mime"] == mime
    assert 0 < result["duration"] <= 2
    if kind == "audio":
        audio = files.audio_probe(files.path(identity))
        stream = audio["streams"][0]
        assert stream["codec_name"] == "opus" and stream["channels"] == 1
        assert float(audio["format"]["start_time"]) == 0


@pytest.mark.parametrize(("media", "payload", "expected"), [
    ({"kind": "image", "mime": "image/webp", "name": "saludo.webp"},
     {"body": "[Adjunto]"}, {"type": "sticker", "sticker": {"id": "asset"}}),
    ({"kind": "audio", "mime": "audio/ogg", "name": "nota-de-voz.ogg"},
     {"body": "[Adjunto]"}, {"type": "audio", "audio": {"id": "asset", "voice": True}}),
    ({"kind": "video", "mime": "video/mp4", "name": "recorrido.mp4"},
     {"body": "Recorrido"}, {"type": "video", "video": {"id": "asset", "caption": "Recorrido"}}),
])
def test_whatsapp_inbox_uses_native_media_payload(tmp_path, monkeypatch, media, payload, expected):
    sample = tmp_path / "sample"
    sample.write_bytes(b"fixture")
    calls = []

    def fake_request(account, method, path, body=None, *, files=None):
        calls.append((path, body))
        if files:
            expected_mime = "audio/ogg; codecs=opus" if media["mime"] == "audio/ogg" else media["mime"]
            assert files["file"][2] == expected_mime
            return {"id": "asset"}
        return {"messages": [{"id": "synthetic-message"}]}

    monkeypatch.setattr(providers, "request", fake_request)
    account = {"channel": "whatsapp", "configuration": {"phoneNumberId": "fixture"}}
    assert providers.send_media(
        account, {**payload, "target": "15551234567"}, {**media, "path": sample},
        lambda: calls.append(("confirmed", None)),
    ) == "synthetic-message"
    assert calls == [
        ("fixture/media", None),
        ("confirmed", None),
        ("fixture/messages", {"messaging_product": "whatsapp", "to": "15551234567", **expected}),
    ]


def test_delivery_error_is_allowlisted_without_raw_provider_details():
    assert providers.whatsapp_delivery_error({"code": 131042, "details": "private"}) == "whatsapp_billing_issue"
    assert providers.whatsapp_delivery_error({"code": 999999, "details": "private"}) is None
