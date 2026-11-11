"""Real file inspection, immutable library, ordered typed C10 media and delay."""

import base64, io, json, os, subprocess, time, wave
from uuid import uuid4
from unittest.mock import patch
from PIL import Image
from pypdf import PdfWriter
from app.institutional.campaign_runtime import Worker
from app.institutional.channel_outbox import Dispatcher
from tools.p8_test_support import Harness
from tools.prepare_p8_campaign import WORK, save


def main():
    os.environ["CRM_AI_STATE_DIR"] = str(WORK / "runtime-r2-media")
    h = Harness("runtime-r2")
    checks = []

    def check(n, ok=True):
        assert ok, n
        checks.append(n)
        save(
            WORK / "template-media-result.json",
            dict(status="in_progress", checks=checks),
        )

    data = io.BytesIO()
    Image.new("RGB", (8, 8), (30, 50, 90)).save(data, format="PNG")
    image = data.getvalue()
    data = io.BytesIO()
    pdf = PdfWriter()
    pdf.add_blank_page(width=72, height=72)
    pdf.write(data)
    document = data.getvalue()
    data = io.BytesIO()
    with wave.open(data, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(48000)
        f.writeframes(bytes(4800 * 2))
    audio = data.getvalue()
    video_path = WORK / ("media-fixture-" + uuid4().hex + ".mp4")
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=32x32:d=0.3",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-threads",
            "1",
            "-y",
            str(video_path),
        ],
        check=True,
        timeout=10,
    )
    video = video_path.read_bytes()
    assets = {}
    for kind, raw, filename in [
        ("image", image, "orientacion.png"),
        ("document", document, "requisitos.pdf"),
        ("audio", audio, "orientacion.wav"),
        ("video", video, "programa.mp4"),
    ]:
        body = dict(
            operation_id=str(uuid4()),
            filename=filename,
            kind=kind,
            content_base64=base64.b64encode(raw).decode(),
        )
        result = h.call("campaigns/assets", "POST", body)
        assert h.call("campaigns/assets", "POST", body) == result
        response = h.b.client.get(
            "/api/institution/campaigns/assets/" + result["id"],
            headers={"X-CRM-Local": "1"},
        )
        assert (
            response.status_code == 200
            and len(response.content) == result["size"]
            and result["kind"] == kind
        )
        assets[kind] = result
        check("inspected_" + kind + "_upload_exact_replay_and_authorized_download")
    count = h.sql(
        "SELECT COUNT(*) FROM crm_campaign8.Event WHERE Kind='template_asset'"
    )[0][0]
    h.call(
        "campaigns/assets",
        "POST",
        dict(
            operation_id=str(uuid4()),
            filename="falso.png",
            kind="image",
            content_base64=base64.b64encode(document).decode(),
        ),
        415,
    )
    check(
        "file_kind_spoof_does_not_register_an_asset",
        h.sql("SELECT COUNT(*) FROM crm_campaign8.Event WHERE Kind='template_asset'")[
            0
        ][0]
        == count,
    )
    row = h.sql(
        "SELECT IdentityId,ContactId,ConversationId,IntegrationId FROM crm_channels2.ExternalIdentity WHERE ExternalId='573100000082'"
    )[0]
    p = dict(
        id=str(row[0]).lower(),
        contact=str(row[1]).lower(),
        conversation=str(row[2]).lower(),
    )
    a = str(row[3]).lower()
    blocks = [
        dict(
            type=k,
            asset_id=v["id"],
            filename=v["name"],
            text="" if k == "audio" else "Adjunto " + k,
            delay_ms=15000 if k == "image" else 0,
        )
        for k, v in assets.items()
    ]
    t = h.template8(body="Texto de orientación", variables={}, blocks=blocks)
    f = h.flow8(a, t)
    run = h.enroll8(f, p)
    w = Worker(h.settings, h.gateway)
    calls = []

    def provider(account, method, path, body=None, **kw):
        if path.endswith("/media"):
            calls.append(("upload", bool(kw.get("files"))))
            return {"id": "media_" + uuid4().hex}
        calls.append(("message", body))
        return {"messages": [{"id": "wamid.p8media." + uuid4().hex}]}

    with patch("app.modules.channels.providers.request", side_effect=provider):
        for _ in range(35):
            h.release8(a)
            w.once()
            Dispatcher(h.settings, allow_controlled=True).once()
            w.once()
            if h.run8(run)["state"] == "completed":
                break
            time.sleep(0.25)
    messages = [v[1] for v in calls if v[0] == "message"]
    types = [v.get("type") for v in messages]
    check(
        "uploaded_text_image_document_audio_video_execute_in_order_through_C10",
        h.run8(run)["state"] == "completed"
        and types == ["text", "image", "document", "audio", "video"],
    )
    check(
        "WA_video_caption_is_preserved_for_campaign_origin",
        next(v for v in messages if v["type"] == "video")["video"]["caption"]
        == "Adjunto video",
    )
    rows = h.sql(
        "SELECT e.Document,q.DueAt,q.CompletedAt,q.State FROM crm_campaign8.Event e JOIN crm_channels2.SendJob q ON q.QueueId=TRY_CONVERT(uniqueidentifier,JSON_VALUE(e.Document,'$.queue_id')) WHERE e.EnrollmentId=? AND e.Kind='native_chat' ORDER BY e.CreatedAt",
        run,
    )
    from datetime import timedelta

    check(
        "block_delay_is_persisted_in_native_due_time_and_not_shortened",
        rows[1][1] >= rows[0][2] + timedelta(seconds=15)
        and all(v[3] == "accepted" for v in rows),
    )
    # The native channel contract must reject unsupported TikTok media before activation.
    tk = next(v for v in h.call("channels")["items"] if v["channel"] == "tiktok")["id"]
    bad = h.save8(
        "template",
        dict(
            channel="tiktok",
            body="",
            variables={},
            blocks=[
                dict(
                    type="document",
                    asset_id=assets["document"]["id"],
                    filename="requisitos.pdf",
                )
            ],
        ),
    )
    h.act8(bad["id"], "activate")
    draft = h.save8(
        "flow",
        dict(
            channel="tiktok",
            integration_id=tk,
            steps=[dict(kind="send", crm_template_id=bad["id"])],
        ),
    )
    pre = h.call(
        "campaigns/" + draft["id"] + "/preflight", "POST", h.cmd(draft["revision"])
    )
    check(
        "TikTok_unsupported_media_is_explicitly_blocked_in_preflight",
        not pre["valid"] and "campaign_tiktok_media_not_supported" in pre["issues"],
    )
    save(
        WORK / "template-media-result.json",
        dict(
            status="passed",
            checks=checks,
            uploaded_assets=4,
            accepted_parts=5,
            real_provider_calls=0,
            academic_writes=False,
        ),
    )
    print(json.dumps(dict(status="passed", checks=len(checks))))


if __name__ == "__main__":
    main()
