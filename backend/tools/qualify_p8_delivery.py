"""Instagram Login uses an expiring queue-bound URL, not a permanent public file."""

import json
import os
import time
from unittest.mock import patch
from urllib.parse import parse_qs, urlencode, urlsplit
from uuid import uuid4

from app.institutional.campaign_delivery import signature
from app.institutional.campaign_runtime import Worker
from app.institutional.channel_outbox import Dispatcher
from tools.p8_test_support import Harness
from tools.prepare_p8_campaign import WORK, save


def main():
    os.environ["CRM_AI_STATE_DIR"] = str(WORK / "runtime-r2-media")
    h = Harness("runtime-r2")
    from fastapi.testclient import TestClient

    public = TestClient(h.app)
    h.sql(
        "UPDATE crm_channels4.Configuration SET PublicBaseUrl='https://controlled.example'",
        write=True,
    )
    row = h.sql(
        "SELECT IdentityId,ContactId,ConversationId,IntegrationId FROM crm_channels2.ExternalIdentity WHERE ExternalId='visitor_instagram'"
    )[0]
    p = dict(
        id=str(row[0]).lower(),
        contact=str(row[1]).lower(),
        conversation=str(row[2]).lower(),
    )
    account = str(row[3]).lower()
    asset = str(
        h.sql(
            "SELECT TOP(1) EventId FROM crm_campaign8.Event WHERE Kind='template_asset' AND JSON_VALUE(Document,'$.kind')='image' ORDER BY CreatedAt"
        )[0][0]
    ).lower()
    t = h.template8(
        channel="instagram", body="", variables={}, blocks=[dict(type="image", asset_id=asset)]
    )
    f = h.flow8(account, t, channel="instagram")
    run = h.enroll8(f, p)
    w = Worker(h.settings, h.gateway)
    urls = []
    checks = []

    def provider(a, method, path, body=None, **kw):
        url = body["message"]["attachment"]["payload"]["url"]
        split = urlsplit(url)
        local = split.path + "?" + split.query
        response = public.get(local)
        assert (
            response.status_code == 200
            and response.headers["content-type"] == "image/png"
        )
        assert (
            response.headers["cache-control"] == "no-store"
            and len(response.content) > 0
        )
        urls.append(local)
        return {"message_id": "ig_" + uuid4().hex}

    with patch("app.modules.channels.providers.request", side_effect=provider):
        for _ in range(15):
            h.release8(account)
            w.once()
            Dispatcher(h.settings, allow_controlled=True).once()
            w.once()
            if h.run8(run)["state"] == "completed":
                break
    assert h.run8(run)["state"] == "completed" and len(urls) == 1, h.run8(run)
    checks.append(
        "media_only_template_preflight_and_Instagram_Login_send_use_native_adapter"
    )
    checks.append("provider_fetches_inspected_queue_bound_file_without_human_cookie")
    url = urls[0]
    split = urlsplit(url)
    q = parse_qs(split.query)
    assert (
        public.get(
            split.path + "?" + urlencode(dict(expires=q["expires"][0], sig="0" * 64))
        ).status_code
        == 404
    )
    checks.append("tampered_signature_rejected_before_file_access")
    media, queue = split.path.split("/")[-2:]
    expired = int(time.time()) - 1
    assert (
        public.get(
            split.path
            + "?"
            + urlencode(
                dict(expires=expired, sig=signature(h.settings, media, queue, expired))
            )
        ).status_code
        == 404
    )
    checks.append("expired_valid_signature_rejected")
    other = str(uuid4())
    assert (
        public.get(split.path.replace(media, other) + "?" + split.query).status_code
        == 404
    )
    checks.append("signature_cannot_be_rebound_to_another_media_identity")
    h.act8(f["id"], "pause")
    assert public.get(url).status_code == 404
    checks.append("pausing_flow_retires_previously_issued_delivery_URL")
    save(
        WORK / "delivery-result.json",
        dict(
            status="passed",
            checks=checks,
            lifetime_seconds=600,
            real_provider_calls=0,
            academic_writes=False,
        ),
    )
    print(json.dumps(dict(status="passed", checks=len(checks))))


if __name__ == "__main__":
    main()
