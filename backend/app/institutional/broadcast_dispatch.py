"""A bounded campaign producer using the existing C10 queue and dispatcher."""

import json
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException

from app.institutional import broadcast_templates as templates
from app.institutional.broadcasts import (
    VERSION,
    audience,
    authority,
    current,
    enabled,
    same,
)
from app.institutional.channel_operations import configuration
from app.institutional.db import institution, one, uid
from app.institutional.store import transaction


def record(c, s, queue):
    return one(
        c,
        (
            "SELECT r.* FROM crm_broadcast7.Attempt"
            " a JOIN crm_broadcast7.Recipient r ON "
            "r.InstitutionId=a.InstitutionId AND r."
            "RecipientId=a.RecipientId WHERE a.Inst"
            "itutionId=? AND a.QueueId=?"
        ),
        institution(s),
        queue,
    )


def check(c, s, recipient, *, controlled=False, queue=None):
    campaign = current(c, s, str(recipient["CampaignId"]))
    if s.ticket.get("version") in {'cbn-institutional-ads-p9-v1', 'cbn-institutional-campaign-p8-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
        from app.institutional.campaign_runtime import fence

        fence(c, s, str(recipient["CampaignId"]))
    actor = authority(c, s, campaign)
    if (
        campaign["State"] not in {"running", "scheduled"}
        or campaign["ScheduledAt"]
        and campaign["ScheduledAt"] > datetime.utcnow()
    ):
        raise HTTPException(409, "broadcast_paused_or_not_due")
    if (
        campaign["Epoch"] != recipient["CampaignEpoch"]
        or campaign["Revision"] != recipient["CampaignRevision"]
    ):
        raise HTTPException(409, "broadcast_revision_changed")
    found, item = audience(c, s, campaign, controlled=controlled,
                           target_identity=recipient["IdentityId"])
    candidate = next(
        (v for v in found if same(v["identity_id"], recipient["IdentityId"])), None
    )
    if not candidate or not candidate["eligible"]:
        raise HTTPException(
            409,
            (candidate["reasons"][0] if candidate else "broadcast_recipient_excluded"),
        )
    snapshot = json.loads(recipient["Snapshot"])
    if (
        not same(candidate["contact_id"], snapshot["canonical_contact"])
        or candidate["person"]["ControlEpoch"] != recipient["ControlEpoch"]
        or not same(candidate["consent"]["ConsentId"], recipient["ConsentId"])
        or candidate["consent"]["VersionNo"] != recipient["ConsentVersion"]
        or bytes(item["RowVersion"]) != bytes(recipient["AccountVersion"])
        or candidate["template"] != snapshot["template"]
        or candidate["phone"] != snapshot["target"]
    ):
        raise HTTPException(409, "broadcast_recipient_changed_review_required")
    if queue:
        if (
            not same(recipient["CurrentQueueId"], queue["QueueId"])
            or not same(queue["IdentityId"], recipient["IdentityId"])
            or not same(queue["IntegrationId"], campaign["IntegrationId"])
        ):
            raise HTTPException(409, "broadcast_queue_identity_mismatch")
        cadence = one(
            c,
            (
                "SELECT * FROM crm_broadcast7.Cadence W"
                "HERE InstitutionId=? AND IntegrationId"
                "=?"
            ),
            institution(s),
            campaign["IntegrationId"],
        )
        if (
            not cadence
            or not cadence["Enabled"]
            or cadence["Revision"]
            != json.loads(queue["Payload"]).get("cadenceRevision")
        ):
            raise HTTPException(409, "broadcast_cadence_changed")
        if cadence["NextAt"] > datetime.utcnow():
            raise HTTPException(429, "broadcast_cadence_wait")
        route = one(
            c,
            (
                "SELECT MessageId,IdentityId,Integratio"
                "nId FROM crm_channels2.MessageRoute WH"
                "ERE InstitutionId=? AND QueueId=?"
            ),
            institution(s),
            queue["QueueId"],
        )
        if (
            not route
            or not same(route["MessageId"], queue["MessageId"])
            or not same(route["IdentityId"], recipient["IdentityId"])
            or not same(route["IntegrationId"], campaign["IntegrationId"])
        ):
            raise HTTPException(409, "broadcast_message_route_mismatch")
    return campaign, actor, candidate, item


def ready(c, s, job, *, controlled=False):
    if s.ticket.get("version") not in {VERSION, "cbn-institutional-campaign-p8-v1", 'cbn-institutional-ads-p9-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
        raise HTTPException(423, "marketing_transport_disabled")
    recipient = record(c, s, str(job["QueueId"]))
    if not recipient:
        raise HTTPException(409, "broadcast_durable_recipient_required")
    campaign, actor, candidate, item = check(
        c, s, recipient, controlled=controlled, queue=job
    )
    payload = json.loads(job["Payload"])
    template = candidate["template_record"]
    expected = {
        "name": template["Name"],
        "language": template["Language"],
        "provider_id": template["ProviderId"],
        "components_fingerprint": templates.fingerprint(
            json.loads(template["Definition"])
        ),
    }
    if (
        payload.get("template") != candidate["template"]
        or payload.get("broadcastTemplate") != expected
        or payload.get("body") != candidate["text"]
    ):
        raise HTTPException(409, "broadcast_payload_changed")
    payload["target"] = candidate["phone"]
    payload["kind"] = "chat"
    return item, payload


def actor_allowed(c, s, payload):
    try:
        campaign = current(c, s, uid(payload.get("broadcastId")))
        actor = authority(c, s, campaign)
        return same(actor["UserId"], payload.get("actorId")) and same(
            campaign["ActorSessionId"], payload.get("actorSessionId")
        )
    except HTTPException:
        return False


class Worker:
    def __init__(self, settings, *, controlled=False):
        self.settings = settings
        self.controlled = controlled

    def once(self):
        from app.institutional.channel_outbox import enqueue

        with transaction(self.settings, True, anonymous=True) as c:
            if (
                not enabled(c, self.settings)
                or not configuration(c, self.settings)["OutboundEnabled"]
            ):
                return False
            c.execute(
                (
                    "UPDATE b SET State='completed',Updated"
                    "At=SYSUTCDATETIME() FROM crm_broadcast"
                    "7.Campaign b WHERE b.InstitutionId=? A"
                    "ND b.State IN('running','scheduled') A"
                    "ND EXISTS(SELECT 1 FROM crm_broadcast7"
                    ".Recipient r WHERE r.InstitutionId=b.I"
                    "nstitutionId AND r.CampaignId=b.Campai"
                    "gnId) AND NOT EXISTS(SELECT 1 FROM crm"
                    "_broadcast7.Recipient r LEFT JOIN crm_"
                    "channels2.SendJob q ON q.InstitutionId"
                    "=r.InstitutionId AND q.QueueId=r.Curre"
                    "ntQueueId WHERE r.InstitutionId=b.Inst"
                    "itutionId AND r.CampaignId=b.CampaignI"
                    "d AND (q.ExternalId IS NULL OR q.State"
                    " IN('queued','sending','uncertain') OR"
                    " r.State='prepared'))"
                ),
                institution(self.settings),
            )
            recipient = one(
                c,
                (
                    "SELECT TOP(1) r.* FROM crm_broadcast7."
                    "Recipient r JOIN crm_broadcast7.Campai"
                    "gn b ON b.InstitutionId=r.InstitutionI"
                    "d AND b.CampaignId=r.CampaignId JOIN c"
                    "rm_broadcast7.Cadence p ON p.Instituti"
                    "onId=b.InstitutionId AND p.Integration"
                    "Id=b.IntegrationId WHERE r.Institution"
                    "Id=? AND r.State='prepared' AND b.Stat"
                    "e IN('running','scheduled') AND (b.Sch"
                    "eduledAt IS NULL OR b.ScheduledAt<=SYS"
                    "UTCDATETIME()) AND p.Enabled=1 AND p.N"
                    "extAt<=SYSUTCDATETIME() AND (p.Reserve"
                    "d<p.DailyLimit OR p.WindowAt<=DATEADD("
                    "hour,-24,SYSUTCDATETIME())) ORDER BY r"
                    ".CreatedAt,r.RecipientId"
                ),
                institution(self.settings),
            )
            if not recipient:
                return False
            try:
                campaign, actor, candidate, item = check(
                    c, self.settings, recipient, controlled=self.controlled
                )
            except HTTPException as e:
                if e.detail == "broadcast_template_refresh_required":
                    # A failed catalog GET must not discard unsent recipients.
                    # Delay this account only; all provider/authority checks remain.
                    c.execute("UPDATE crm_broadcast7.Cadence SET NextAt=DATEADD(second,60,SYSUTCDATETIME()) "
                              "WHERE InstitutionId=? AND IntegrationId=?",
                              institution(self.settings), recipient["IntegrationId"] if "IntegrationId" in recipient else current(c, self.settings, str(recipient["CampaignId"]))["IntegrationId"])
                    return False
                if e.detail == "campaign_quiet_or_not_due":
                    from app.institutional.campaign_models import now, next_allowed

                    flow = one(
                        c,
                        "SELECT f.Document FROM crm_campaign8.Record f JOIN crm_campaign8.Step st ON st.InstitutionId=f.InstitutionId JOIN crm_campaign8.Enrollment r ON r.InstitutionId=st.InstitutionId AND r.EnrollmentId=st.EnrollmentId AND r.FlowId=f.RecordId WHERE st.InstitutionId=? AND st.NativeCampaignId=?",
                        institution(self.settings),
                        recipient["CampaignId"],
                    )
                    due = next_allowed(
                        now(), json.loads(flow["Document"])["quiet_hours"]
                    )
                    c.execute(
                        "UPDATE crm_broadcast7.Campaign SET ScheduledAt=? WHERE InstitutionId=? AND CampaignId=?",
                        due,
                        institution(self.settings),
                        recipient["CampaignId"],
                    )
                    return True
                c.execute(
                    (
                        "UPDATE crm_broadcast7.Recipient SET St"
                        "ate='blocked',LastError=? WHERE Instit"
                        "utionId=? AND RecipientId=?"
                    ),
                    str(e.detail)[:80],
                    institution(self.settings),
                    recipient["RecipientId"],
                )
                return True
            cadence = one(
                c,
                (
                    "SELECT * FROM crm_broadcast7.Cadence W"
                    "HERE InstitutionId=? AND IntegrationId"
                    "=?"
                ),
                institution(self.settings),
                item["IntegrationId"],
            )
            if not cadence or not cadence["Enabled"]:
                return False
            now = datetime.utcnow()
            count = (
                cadence["Reserved"]
                if cadence["WindowAt"] > now - timedelta(hours=24)
                else 0
            )
            if count >= cadence["DailyLimit"]:
                return False
            c.execute(
                (
                    "UPDATE crm_broadcast7.Cadence SET Wind"
                    "owAt=?,Reserved=? WHERE InstitutionId="
                    "? AND IntegrationId=?"
                ),
                cadence["WindowAt"] if count else now,
                count + 1,
                institution(self.settings),
                item["IntegrationId"],
            )
            template = candidate["template_record"]
            message = str(uuid4())
            operation = str(uuid4())
            payload = {
                "origin": "broadcast",
                "broadcastId": uid(str(campaign["CampaignId"])),
                "recipientId": uid(str(recipient["RecipientId"])),
                "body": candidate["text"],
                "template": candidate["template"],
                "cadenceRevision": cadence["Revision"],
                "broadcastTemplate": {
                    "name": template["Name"],
                    "language": template["Language"],
                    "provider_id": template["ProviderId"],
                    "components_fingerprint": templates.fingerprint(
                        json.loads(template["Definition"])
                    ),
                },
            }
            c.execute(
                (
                    "INSERT crm.Message(MessageId,Conversat"
                    "ionId,Body,Direction) VALUES(?,?,?,'ou"
                    "tgoing')"
                ),
                message,
                recipient["ConversationId"],
                candidate["text"],
            )
            queue = enqueue(
                c,
                self.settings,
                item,
                actor,
                operation,
                payload,
                identity=str(recipient["IdentityId"]),
                message=message,
            )
            c.execute(
                (
                    "INSERT crm_channels2.MessageRoute(Inst"
                    "itutionId,MessageId,IntegrationId,Iden"
                    "tityId,QueueId,ActorKind) VALUES(?,?,?"
                    ",?,?,'human')"
                ),
                institution(self.settings),
                message,
                item["IntegrationId"],
                recipient["IdentityId"],
                queue,
            )
            c.execute(
                (
                    "INSERT crm_broadcast7.Attempt(Institut"
                    "ionId,RecipientId,AttemptNo,QueueId,Op"
                    "erationId) VALUES(?,?,?,?,?)"
                ),
                institution(self.settings),
                recipient["RecipientId"],
                recipient["Attempts"] + 1,
                queue,
                operation,
            )
            c.execute(
                (
                    "UPDATE crm_broadcast7.Recipient SET St"
                    "ate='queued',CurrentQueueId=?,Attempts"
                    "=Attempts+1,UpdatedAt=SYSUTCDATETIME()"
                    " WHERE InstitutionId=? AND RecipientId"
                    "=?"
                ),
                queue,
                institution(self.settings),
                recipient["RecipientId"],
            )
            c.execute(
                (
                    "UPDATE crm_broadcast7.Campaign SET Sta"
                    "te='running' WHERE InstitutionId=? AND"
                    " CampaignId=?"
                ),
                institution(self.settings),
                campaign["CampaignId"],
            )
            return True


def reconcile_receipts(c, s):
    # Quarantined authenticated input remains durable when a receipt races the
    # provider's POST response. No receipt is fabricated or silently discarded.
    c.execute(
        (
            "UPDATE e SET Status='queued',LastError"
            "Code=NULL FROM crm_channels2.WebhookEv"
            "ent e WHERE e.InstitutionId=? AND e.St"
            "atus='quarantined' AND e.LastErrorCode"
            "='delivery_unmatched' AND EXISTS(SELEC"
            "T 1 FROM crm_channels2.SendJob q WHERE"
            " q.InstitutionId=e.InstitutionId AND q"
            ".IntegrationId=e.IntegrationId AND q.E"
            "xternalId=e.ProviderEventId COLLATE Latin1_General_100_BIN2"
            ")"
        ),
        institution(s),
    )
