"""Native SQL C10 social caption parts, variable rendering and document names."""

import json
import os
from unittest.mock import patch
from uuid import uuid4

from app.institutional.campaign_runtime import Worker
from app.institutional.channel_outbox import Dispatcher
from tools.p8_test_support import Harness
from tools.prepare_p8_campaign import WORK, save


def main():
    os.environ["CRM_AI_STATE_DIR"] = str(WORK / "runtime-r2-media")
    h = Harness("runtime-r2")
    checks = []
    for channel, kind in [("messenger", "image"), ("whatsapp", "document")]:
        row = h.sql(
            "SELECT TOP(1) IdentityId,ContactId,ConversationId,IntegrationId FROM crm_channels2.ExternalIdentity WHERE ExternalId=?",
            "visitor_messenger" if channel == "messenger" else "573100000082",
        )[0]
        p = dict(
            id=str(row[0]).lower(),
            contact=str(row[1]).lower(),
            conversation=str(row[2]).lower(),
        )
        account = str(row[3]).lower()
        asset = str(
            h.sql(
                "SELECT TOP(1) EventId FROM crm_campaign8.Event WHERE Kind='template_asset' AND JSON_VALUE(Document,'$.kind')=? ORDER BY CreatedAt",
                kind,
            )[0][0]
        ).lower()
        t = h.template8(
            channel=channel,
            body="",
            blocks=[
                dict(
                    type=kind,
                    asset_id=asset,
                    filename="Requisitos CBN.pdf" if kind == "document" else "",
                    text="Hola {{nombre}}",
                ),
                dict(type="text", text="Consulta {{nombre}}"),
            ],
        )
        f = h.flow8(account, t, channel=channel)
        run = h.enroll8(f, p)
        w = Worker(h.settings, h.gateway)
        calls = []

        def provider(a, method, path, body=None, **kw):
            if path.endswith("/media"):
                return {"id": "media_" + uuid4().hex}
            calls.append((body, kw))
            return {
                "message_id": "social_" + uuid4().hex,
                "messages": [{"id": "wamid_" + uuid4().hex}],
            }

        with patch("app.modules.channels.providers.request", side_effect=provider):
            for _ in range(20):
                h.release8(account)
                w.once()
                Dispatcher(h.settings, allow_controlled=True).once()
                w.once()
                if h.run8(run)["state"] == "completed":
                    break
        assert h.run8(run)["state"] == "completed", h.run8(run)
        jobs = h.sql(
            "SELECT q.Payload,q.State FROM crm_campaign8.Event e JOIN crm_channels2.SendJob q ON q.QueueId=TRY_CONVERT(uniqueidentifier,JSON_VALUE(e.Document,'$.queue_id')) WHERE e.EnrollmentId=? AND e.Kind='native_chat' ORDER BY e.CreatedAt",
            run,
        )
        assert all(v[1] == "accepted" for v in jobs)
        parts = [json.loads(v[0]) for v in jobs]
        if channel == "messenger":
            assert (
                len(calls) == len(parts) == 3
                and parts[0]["body"] == ""
                and parts[1]["body"].startswith("Hola ")
                and "{{" not in parts[-1]["body"]
            )
            assert (
                calls[0][1]["files"]["filedata"]
                and calls[1][0]["message"]["text"] == parts[1]["body"]
            )
            checks.append(
                "Messenger_attachment_caption_and_following_variable_text_are_three_native_accepted_parts"
            )
        else:
            assert (
                len(calls) == len(parts) == 2
                and calls[0][0]["document"]["filename"] == "Requisitos CBN.pdf"
                and calls[0][0]["document"]["caption"].startswith("Hola ")
            )
            checks.append(
                "WA_document_edited_filename_and_caption_reach_native_adapter"
            )
        assert sorted(v["partIndex"] for v in parts) == list(range(len(parts)))
        checks.append(channel + "_accepted_part_indices_are_unique_and_fully_rendered")
    save(
        WORK / "captions-result.json",
        dict(
            status="passed", checks=checks, real_provider_calls=0, academic_writes=False
        ),
    )
    print(json.dumps(dict(status="passed", checks=len(checks))))


if __name__ == "__main__":
    main()
