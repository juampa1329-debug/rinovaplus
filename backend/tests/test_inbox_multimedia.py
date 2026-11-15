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


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="FFmpeg unavailable")
@pytest.mark.parametrize(("kind", "source", "suffix", "mime"), [
    ("audio", "sine=frequency=440:duration=1", "wav", "audio/ogg"),
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
            assert files["file"][2] == media["mime"]
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
