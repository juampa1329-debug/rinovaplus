"""P8 controlled native step transitions, replies, rules, A/B and social channels."""

import hmac, io, json, time, os
from uuid import uuid4
from unittest.mock import patch
from PIL import Image
from app.institutional.campaign_runtime import Worker
from app.institutional.campaign_assets import refresh as images
from app.institutional.channel_outbox import Dispatcher
from app.institutional.channel_events import EventWorker
from app.institutional.channel_operations import account as owned, app_secret_kind
from app.institutional.channel_secrets import get
from app.institutional.store import transaction
from app.modules.channels import providers
from tools.p8_test_support import Harness
from tools.prepare_p8_campaign import WORK, save


def main():
    os.environ["CRM_AI_STATE_DIR"] = (
        "/var/lib/cbn-p2/p8-es-v1/"
        + os.environ.get("P8_RUNTIME_LABEL", "runtime")
        + "-media"
    )
    h = Harness(os.environ.get("P8_RUNTIME_LABEL", "runtime"))
    checks = []

    def check(n, ok=True):
        assert ok, n
        checks.append(n)
        save(WORK / "runtime-result.json", dict(status="in_progress", checks=checks))

    resume = os.environ.get("P8_RUNTIME_RESUME") in {"images", "social", "tiktok"}
    if resume:
        from tools.prepare_p8_campaign import read

        checks = read(WORK / "runtime-result.json")["checks"]
        assert len(checks) == (
            12
            if os.environ.get("P8_RUNTIME_RESUME") == "tiktok"
            else 10
            if os.environ.get("P8_RUNTIME_RESUME") == "social"
            else 9
        )
        row = h.sql(
            "SELECT IdentityId,ContactId,ConversationId,IntegrationId FROM crm_channels2.ExternalIdentity WHERE ExternalId='573100000082'"
        )[0]
        a = str(row[3]).lower()
        p = dict(
            id=str(row[0]).lower(),
            contact=str(row[1]).lower(),
            conversation=str(row[2]).lower(),
            phone="573100000082",
        )
        worker = Worker(h.settings, h.gateway)
        posts = []
        failure = None
        frontier = None
    else:
        a = h.account("82")
        p = h.incoming(a, "573100000082", "Beto Runtime")
        h.grant(a, p)
        h.cadence8(a)
        template = h.template8()
        worker = Worker(h.settings, h.gateway)
        posts = []
        failure = None
        frontier = None

    def transport(adapter, payload, **kw):
        nonlocal frontier
        if frontier:
            action = frontier
            frontier = None
            action()
        kw["before_send"]()
        if failure == "definitive":
            raise providers.ProviderFailure("controlled_rejected")
        if failure == "uncertain":
            posts.append(payload)
            raise providers.ProviderFailure("controlled_timeout", uncertain=True)
        posts.append(payload)
        return "wamid.p8runtime." + uuid4().hex

    dispatcher = Dispatcher(h.settings, transport=transport, allow_controlled=True)

    def make(**extra):
        f = h.flow8(a, template, **extra)
        r = h.enroll8(f, p)
        return f, r

    def queue():
        h.release8(a)
        worker.once()

    def complete():
        worker.once()
        worker.once()

    def live(r):
        return str(
            h.sql(
                "SELECT q.QueueId FROM crm_campaign8.Event e JOIN crm_channels2.SendJob q ON q.QueueId=TRY_CONVERT(uniqueidentifier,JSON_VALUE(e.Document,'$.queue_id')) WHERE e.EnrollmentId=? AND e.Kind='native_chat' ORDER BY e.CreatedAt DESC",
                r,
            )[0][0]
        ).lower()

    if not resume:
        f, r = make()
        queue()
        failure = "definitive"
        dispatcher.once()
        worker.once()
        check(
            "definitive_failure_is_explicit_not_automatic_retry",
            h.run8(r)["state"] == "failed",
        )
        failure = None
        h.act8(f["id"], "retry", identity_ids=[r])
        h.release8(a)
        dispatcher.once()
        complete()
        metrics = h.call("campaigns/" + f["id"] + "/metrics")["variants"][0]
        check(
            "reviewed_retry_keeps_all_failed_and_accepted_attempts",
            metrics["attempts"] == 2
            and metrics["failed"] == 1
            and metrics["accepted"] == 1,
        )
        h.act8(f["id"], "retry", 409, identity_ids=[r])
        f, r = make()
        queue()
        failure = "uncertain"
        dispatcher.once()
        worker.once()
        failure = None
        before = len(posts)
        h.act8(f["id"], "retry", 409, identity_ids=[r])
        Worker(h.settings, h.gateway).once()
        Dispatcher(h.settings, transport=transport, allow_controlled=True).once()
        check(
            "uncertain_native_effect_never_requeues_after_worker_restart",
            h.run8(r)["state"] == "uncertain" and len(posts) == before,
        )
        f, r = make()
        queue()
        before = len(posts)

        def change_stage():
            h.sql(
                "UPDATE crm.Contact SET Stage='frontera' WHERE ContactId=?",
                p["contact"],
                write=True,
            )

        oldstage = h.sql(
            "SELECT Stage FROM crm.Contact WHERE ContactId=?", p["contact"]
        )[0][0]
        frontier = change_stage
        dispatcher.once()
        worker.once()
        check(
            "stage_change_at_actual_before_send_fences_POST",
            len(posts) == before and h.run8(r)["state"] == "cancelled",
        )
        h.sql(
            "UPDATE crm.Contact SET Stage=? WHERE ContactId=?",
            oldstage,
            p["contact"],
            write=True,
        )
        # Review restore creates an immutable new draft and exact replay returns it.
        v = h.save8("segment", {"filters": {}})
        h.save8(
            "segment",
            {"filters": {"stages": ["aspirante"]}},
            id=v["id"],
            revision=v["revision"],
        )
        current = h.call("campaigns/" + v["id"])
        body = h.cmd(current["revision"], confirmed=True, version=1)
        first = h.call("campaigns/" + v["id"] + "/restore", "POST", body)
        second = h.call("campaigns/" + v["id"] + "/restore", "POST", body)
        check(
            "historical_restore_is_atomic_idempotent_new_draft_version",
            first == second and first["version"] == 3 and first["state"] == "draft",
        )
        # A/B assignment is durable; both variants are real pinned CRM templates.
        other = h.template8()
        f, r = make(
            ab_test={"enabled": True, "a_percent": 50, "label": "Admisiones"},
            steps=[
                dict(
                    kind="send",
                    crm_template_id=template["id"],
                    variant_b_crm_template_id=other["id"],
                )
            ],
        )
        variant = h.sql(
            "SELECT Variant FROM crm_campaign8.Enrollment WHERE EnrollmentId=?", r
        )[0][0]
        queue()
        h.release8(a)
        dispatcher.once()
        complete()
        check(
            "AB_assignment_is_persisted_and_measurement_uses_native_attempts",
            h.sql(
                "SELECT Variant FROM crm_campaign8.Enrollment WHERE EnrollmentId=?", r
            )[0][0]
            == variant
            and sum(
                v["accepted"]
                for v in h.call("campaigns/" + f["id"] + "/metrics")["variants"]
            )
            == 1,
        )
        # A message trigger acts on a future authenticated event, not an old observation.
        f = h.flow8(a, template)
        trigger = h.save8(
            "trigger",
            dict(
                flow_id=f["id"],
                flow_version=f["version"],
                event_type="message_in",
                conditions={"keywords": ["beca"]},
                cooldown_minutes=0,
            ),
        )
        h.act8(trigger["id"], "activate")
        worker.once()
        check(
            "activating_trigger_does_not_replay_old_incoming",
            h.sql(
                "SELECT COUNT(*) FROM crm_campaign8.Enrollment WHERE FlowId=?", f["id"]
            )[0][0]
            == 0,
        )
        h.incoming(a, p["phone"], "Beto Runtime", "Quiero una BECA")
        worker.once()
        check(
            "signed_message_keyword_trigger_enrolls_exactly_once",
            h.sql(
                "SELECT COUNT(*) FROM crm_campaign8.Enrollment WHERE FlowId=?", f["id"]
            )[0][0]
            == 1,
        )
        worker.once()
        check(
            "signal_markers_prevent_duplicate_trigger_enrollment",
            h.sql(
                "SELECT COUNT(*) FROM crm_campaign8.Enrollment WHERE FlowId=?", f["id"]
            )[0][0]
            == 1,
        )
        h.act8(trigger["id"], "pause")
        worker.once()
    if os.environ.get("P8_RUNTIME_RESUME") not in {"social", "tiktok"}:
        # Images are private inspected C10 assets; parts are separately acknowledged.
        if resume:
            f = next(
                v
                for v in h.call("campaigns")["items"]
                if v["kind"] == "flow"
                and v["document"]["steps"][0].get("crm_template_id")
                in {
                    x["id"]
                    for x in h.call("campaigns")["items"]
                    if x["kind"] == "template" and x["document"]["blocks"]
                }
            )
            r = str(
                h.sql(
                    "SELECT EnrollmentId FROM crm_campaign8.Enrollment WHERE FlowId=?",
                    f["id"],
                )[0][0]
            ).lower()
        else:
            image_template = h.template8(
                body="Texto antes",
                variables={},
                blocks=[
                    {
                        "type": "image",
                        "text": "Imagen institucional",
                        "url": "https://assets.example/imagen.png",
                    },
                    {"type": "text", "text": "Texto después"},
                ],
            )
            f = h.flow8(a, image_template)
            r = h.enroll8(f, p)
            worker.once()
        for _ in range(5):
            if h.sql("SELECT COUNT(*) FROM crm_campaign8.Step WHERE EnrollmentId=?", r)[
                0
            ][0]:
                break
            worker.once()

        def download(url, dest):
            data = io.BytesIO()
            Image.new("RGB", (3, 3), (20, 80, 120)).save(data, format="PNG")
            dest.write_bytes(data.getvalue())

        if resume:
            h.sql(
                "UPDATE crm_channels4.MediaAsset SET UpdatedAt=DATEADD(minute,-3,SYSUTCDATETIME()) WHERE State='processing'",
                write=True,
            )
        assert images(h.settings, download)
        h.sql(
            "UPDATE crm_campaign8.Enrollment SET DueAt=DATEADD(second,-1,SYSUTCDATETIME()) WHERE EnrollmentId=?",
            r,
            write=True,
        )
        worker.once()
        h.release8(a)
        dispatcher.once()
        worker.once()
        h.act8(f["id"], "pause")
        h.act8(f["id"], "activate")
        h.act8(f["id"], "resume", identity_ids=[r])
        h.release8(a)
        worker.once()
        h.release8(a)
        assert dispatcher.once()
        worker.once()
        h.release8(a)
        worker.once()
        h.release8(a)
        dispatcher.once()
        complete()
        links = h.sql(
            "SELECT q.Payload,q.State,q.Attempts FROM crm_campaign8.Event e JOIN crm_channels2.SendJob q ON q.QueueId=TRY_CONVERT(uniqueidentifier,JSON_VALUE(e.Document,'$.queue_id')) WHERE e.EnrollmentId=? AND e.Kind='native_chat'",
            r,
        )
        check(
            "ordered_CRM_image_parts_resume_after_accepted_text_without_duplicate",
            h.run8(r)["state"] == "completed"
            and len(links) in {3, 4}
            and sorted(
                json.loads(v[0])["partIndex"]
                for v in links
                if v[1] in {"accepted", "sent", "delivered", "read"}
            )
            == [0, 1, 2]
            and all(v[2] == 0 for v in links if v[1] == "cancelled"),
        )
    # Institution profile rows are the only configuration used for social sends.
    for channel in (
        ["tiktok"]
        if os.environ.get("P8_RUNTIME_RESUME") == "tiktok"
        else ["instagram", "messenger", "tiktok"]
    ):
        existing = (
            next(
                (
                    v
                    for v in h.call("channels")["items"]
                    if v["channel"] == channel
                    and v["display_name"] == "Controlado P8 " + channel
                ),
                None,
            )
            if os.environ.get("P8_RUNTIME_RESUME") == "tiktok"
            else None
        )
        if existing:
            id = existing["id"]
            item = existing
        else:
            profile = (
                "tiktok_business"
                if channel == "tiktok"
                else "instagram_login"
                if channel == "instagram"
                else "facebook_login"
            )
            created = h.call(
                "channels",
                "POST",
                dict(
                    operation_id=str(uuid4()),
                    channel=channel,
                    display_name="Controlado P8 " + channel,
                    issuer_profile=profile,
                    client_id="2782" + str(len(channel)),
                    api_version="" if channel == "tiktok" else "v24.0",
                ),
            )
            id = created["id"]
            item = next(v for v in h.call("channels")["items"] if v["id"] == id)
            for owner, kind in [
                (
                    "application:" + item["application_id"],
                    "client_secret" if channel == "tiktok" else "app_secret",
                ),
                (
                    "integration:" + id,
                    "page_access_token" if channel == "messenger" else "access_token",
                ),
            ]:
                h.call(
                    "credentials",
                    "PUT",
                    dict(
                        operation_id=str(uuid4()),
                        scope="channel",
                        owner=owner,
                        kind=kind,
                        value="controlled-" + uuid4().hex,
                    ),
                )
            reference = h.sql(
                "SELECT InitialStageKey,InitialStageConfigHash FROM crm_channels2.Integration WHERE IntegrationId=?",
                a,
            )[0]
            h.sql(
                "UPDATE crm_channels2.Integration SET ExternalAccountId=?,RequestedStatus='connected',VerifiedStatus='verified',InitialStageKey=?,InitialStageConfigHash=?,ApprovedScopes=? WHERE IntegrationId=?",
                "account_" + channel,
                reference[0],
                reference[1],
                json.dumps(["business_messaging"] if channel == "tiktok" else []),
                id,
                write=True,
            )
        if channel == "tiktok":
            h.call(
                "credentials",
                "PUT",
                dict(
                    operation_id=str(uuid4()),
                    scope="channel",
                    owner="endpoint:" + item["webhook"]["id"],
                    kind="webhook_secret",
                    value="controlled-webhook-" + uuid4().hex,
                ),
            )
            from app.institutional.channel_tiktok import apply_policy

            with transaction(h.settings, True, anonymous=True) as c:
                apply_policy(c, h.settings, owned(c, h.settings, id))
            h.sql(
                "UPDATE crm_channels2.TikTokPolicy SET ReviewStatus='approved',OutboundMode='live',OperatorAttestedEvents=1,BusinessMessagingEnabled=1,DailyOutboundQuota=1000,ApprovedProducts='[\"business_messaging\"]',ApprovedScopes='[\"business_messaging\"]',RolloutPercent=100 WHERE IntegrationId=?",
                id,
                write=True,
            )
        h.call(
            "channels/" + id + "/webhook",
            "POST",
            dict(
                operation_id=str(uuid4()),
                row_version=item["webhook"]["row_version"],
                active=True,
            ),
        )
        item = next(v for v in h.call("channels")["items"] if v["id"] == id)
        with transaction(h.settings, anonymous=True) as c:
            account = owned(c, h.settings, id)
            secret, _ = get(
                c,
                h.settings,
                "endpoint" if channel == "tiktok" else "application",
                str(
                    item["webhook"]["id"]
                    if channel == "tiktok"
                    else item["application_id"]
                ),
                "tiktok_webhook_secret"
                if channel == "tiktok"
                else app_secret_kind(account),
            )
        external = "visitor_" + channel
        payload = (
            dict(
                client_key=account["ClientId"],
                user_openid=account["ExternalAccountId"],
                event="im_receive_msg",
                create_time=int(time.time()),
                content=dict(
                    message_id="social_" + uuid4().hex,
                    conversation_id=external,
                    text={"body": "Información de admisiones"},
                ),
            )
            if channel == "tiktok"
            else dict(
                object="instagram" if channel == "instagram" else "page",
                entry=[
                    dict(
                        id=account["ExternalAccountId"],
                        messaging=[
                            dict(
                                sender={"id": external},
                                recipient={"id": account["ExternalAccountId"]},
                                timestamp=int(time.time() * 1000),
                                message={
                                    "mid": "social_" + uuid4().hex,
                                    "text": "Información de admisiones",
                                },
                            )
                        ],
                    )
                ],
            )
        )
        raw = json.dumps(payload).encode()
        stamp = str(int(time.time()))
        headers = (
            {
                "tiktok-signature": "t="
                + stamp
                + ",s="
                + hmac.digest(
                    secret.encode(), stamp.encode() + b"." + raw, "sha256"
                ).hex()
            }
            if channel == "tiktok"
            else {
                "X-Hub-Signature-256": "sha256="
                + hmac.digest(secret.encode(), raw, "sha256").hex()
            }
        )
        response = h.b.client.post(
            item["webhook"]["path"], content=raw, headers=headers
        )
        assert response.status_code == 200
        events = EventWorker(h.settings)
        events.once()
        events.project_once()
        row = h.sql(
            "SELECT IdentityId,ContactId,ConversationId FROM crm_channels2.ExternalIdentity WHERE IntegrationId=? AND ExternalId=?",
            id,
            external,
        )[0]
        person = dict(
            id=str(row[0]).lower(),
            contact=str(row[1]).lower(),
            conversation=str(row[2]).lower(),
        )
        h.sql(
            "UPDATE crm.Conversation SET ControlMode='ai' WHERE ConversationId=?",
            person["conversation"],
            write=True,
        )
        h.grant(id, person)
        h.cadence8(id)
        crm = h.template8(channel=channel)
        flow = h.flow8(id, crm, channel=channel)
        rr = h.enroll8(flow, person)
        worker.once()
        h.release8(id)
        native_calls = []

        def provider(account, method, path, body=None, **kw):
            native_calls.append((account["channel"], method, path, body))
            return (
                {
                    "code": 0,
                    "data": {"message": {"message_id": "tiktok_" + uuid4().hex}},
                }
                if account["channel"] == "tiktok"
                else {"message_id": "meta_" + uuid4().hex}
            )

        with patch("app.modules.channels.providers.request", side_effect=provider):
            Dispatcher(h.settings, allow_controlled=True).once()
        complete()
        check(
            "native_" + channel + "_CRM_template_uses_C10_account_and_real_adapter",
            h.run8(rr)["state"] == "completed"
            and len(native_calls) == 1
            and native_calls[0][0] == channel,
        )
    save(
        WORK / "runtime-result.json",
        dict(
            status="passed",
            checks=checks,
            database=h.settings.connection["database"],
            real_provider_calls=0,
            academic_writes=False,
        ),
    )
    print(json.dumps(dict(status="passed", checks=len(checks))))


if __name__ == "__main__":
    main()
