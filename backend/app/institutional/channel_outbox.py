"""Single operational outbox, exact account ownership and uncertain-effect fencing."""

import json
import re
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException

from app.institutional import postgres_queue
from app.institutional.channel_operations import account, configuration
from app.institutional.channel_provider import provider_account
from app.institutional.db import bound_hash, institution, one, rows, uid
from app.institutional.settings import setting
from app.institutional.store import transaction
from app.modules.channels import providers


def enqueue(
    c,
    settings,
    item,
    actor,
    operation,
    payload,
    *,
    comment=None,
    identity=None,
    message=None,
):
    from app.institutional import comment_automation
    from app.institutional.whatsapp_gemini import ACTOR, ORIGIN

    actor_ref = str(actor["UserId"]).lower() if actor is not None else None
    if actor_ref is None:
        if payload.get("origin") == ORIGIN and identity and message and not comment:
            actor_ref = ACTOR
        elif payload.get("origin") == comment_automation.ORIGIN and comment and not (identity or message):
            actor_ref = comment_automation.ACTOR
        else:
            raise HTTPException(403, "outbox_actor_required")
    if not configuration(c, settings)["ModuleEnabled"]:
        raise HTTPException(403, "module_disabled")
    kind = "comment_reply" if comment else "chat"
    inst, queue = institution(settings), str(uuid4())
    digest = bound_hash(
        settings,
        {
            "integration": str(item["IntegrationId"]).lower(),
            "kind": kind,
            "payload": payload,
            "comment": comment,
            "identity": identity,
            "message": message,
        },
        "outbox-intent",
    )
    current = one(
        c,
        (
            "SELECT OperationId,RequestDigest FROM "
            "crm_channels2.ProviderOperation WHERE "
            "InstitutionId=? AND OperationId=?"
        ),
        inst,
        operation,
    )
    if current:
        if bytes(current["RequestDigest"]) != digest:
            raise HTTPException(409, "operation_conflict")
        return c.execute(
            (
                "SELECT QueueId FROM crm_channels2.Send"
                "Job WHERE InstitutionId=? AND Operatio"
                "nId=?"
            ),
            inst,
            operation,
        ).fetchval()
    if payload.get("privateReply"):
        if not comment or item["Channel"] not in {"facebook", "instagram"}:
            raise HTTPException(422, "comment_private_channel_unavailable")
        if c.execute(
            "SELECT 1 FROM crm_channels2.SendJob WITH(UPDLOCK,HOLDLOCK) WHERE InstitutionId=? AND IntegrationId=? AND CommentId=? "
            "AND JSON_VALUE(Payload,'$.privateReply')='true' AND (State<>'cancelled' OR Attempts>0 OR ExternalId IS NOT NULL)",
            inst, item["IntegrationId"], comment,
        ).fetchone():
            raise HTTPException(409, "comment_private_already_attempted")
    if item["RequestedStatus"] != "connected" or item["VerifiedStatus"] != "verified":
        raise HTTPException(409, "verified_connected_account_required")
    if identity:
        consistent = c.execute(
            (
                "SELECT 1 FROM crm_channels2.ExternalId"
                "entity i JOIN crm.Conversation v ON v."
                "ConversationId=i.ConversationId AND v."
                "ContactId=i.ContactId JOIN crm.Message"
                " m ON m.ConversationId=v.ConversationI"
                "d WHERE i.InstitutionId=? AND i.Integr"
                "ationId=? AND i.IdentityId=? AND m.Mes"
                "sageId=?"
            ),
            inst,
            item["IntegrationId"],
            identity,
            message,
        ).fetchone()
        if not consistent:
            raise HTTPException(409, "message_identity_account_mismatch")
    if (
        comment
        and not c.execute(
            (
                "SELECT 1 FROM crm_channels2.SocialComm"
                "ent WHERE InstitutionId=? AND Integrat"
                "ionId=? AND CommentId=? AND ISNULL(JSO"
                "N_VALUE(Payload,'$._crm.state'),'new')"
                " NOT IN('deleted','unavailable')"
            ),
            inst,
            item["IntegrationId"],
            comment,
        ).fetchone()
    ):
        raise HTTPException(409, "comment_account_mismatch")
    intent = dict(payload)
    if actor is not None:
        intent.update(actorSessionId=str(actor["SessionId"]).lower(), actorId=actor_ref)
    from app.institutional.agents_policy import VERSION as P5

    if identity and settings.ticket.get("version") == P5:
        intent["controlEpoch"] = c.execute(
            (
                "SELECT COALESCE(ctrl.Epoch,0) FROM crm"
                ".Conversation v LEFT JOIN crm_channels"
                ".ConversationControl ctrl ON ctrl.Conv"
                "ersationId=v.ConversationId JOIN crm_c"
                "hannels2.ExternalIdentity i ON i.Conve"
                "rsationId=v.ConversationId WHERE i.Ins"
                "titutionId=? AND i.IdentityId=?"
            ),
            inst,
            identity,
        ).fetchval()
    c.execute(
        (
            "INSERT crm_channels2.ProviderOperation"
            "(InstitutionId,OperationId,Application"
            "Id,IntegrationId,ActorRef,Action,Reque"
            "stDigest,Status,ResultMetadata,EffectK"
            "ey,CreatedAt) VALUES(?,?,?,?,?,?,?,'pe"
            "nding','{}',?,SYSUTCDATETIME())"
        ),
        inst,
        operation,
        item["ApplicationId"],
        item["IntegrationId"],
        actor_ref,
        kind,
        digest,
        digest,
    )
    c.execute(
        (
            "INSERT crm_channels2.SendJob(Instituti"
            "onId,QueueId,IntegrationId,IdentityId,"
            "MessageId,CommentId,OperationId,Kind,S"
            "tate,Payload,DueAt,CreatedAt) VALUES(?"
            ",?,?,?,?,?,?,?,'queued',?,SYSUTCDATETI"
            "ME(),SYSUTCDATETIME())"
        ),
        inst,
        queue,
        item["IntegrationId"],
        identity,
        message,
        comment,
        operation,
        kind,
        json.dumps(intent, ensure_ascii=False),
    )
    return queue


def actor_allowed(c, settings, payload):
    if payload.get("origin") == "broadcast" and settings.ticket.get("version") in {
        "cbn-institutional-broadcast-p7-v1",
        "cbn-institutional-campaign-p8-v1", 'cbn-institutional-ads-p9-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
        from app.institutional.broadcast_dispatch import actor_allowed as bulk_actor

        return bulk_actor(c, settings, payload)
    if (
        settings.ticket.get("version") in {'cbn-institutional-ads-p9-v1', 'cbn-institutional-campaign-p8-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}
        and payload.get("origin") == "campaign"
    ):
        from app.institutional.campaign_chat import actor_allowed as campaign_actor

        return campaign_actor(c, settings, payload)
    value = one(
        c,
        (
            "SELECT r.Actions FROM crm_access.Sessi"
            "on s JOIN crm_access.AccessUser u ON u"
            ".InstitutionId=s.InstitutionId AND u.U"
            "serId=s.UserId JOIN crm_access.Role r "
            "ON r.InstitutionId=u.InstitutionId AND"
            " r.RoleKey=u.RoleKey WHERE s.Instituti"
            "onId=? AND s.SessionId=? AND s.UserId="
            "? AND s.RevokedAt IS NULL AND s.Expire"
            "sAt>SYSUTCDATETIME() AND s.AuthVersion"
            "=u.AuthVersion AND u.Active=1 AND r.Ac"
            "tive=1"
        ),
        institution(settings),
        payload.get("actorSessionId"),
        payload.get("actorId"),
    )
    enabled = setting(c, settings, "modules")["document"]["enabled"]
    return (
        value
        and "inbox.write" in json.loads(value["Actions"])
        and enabled.get("inbox", False)
        and enabled.get("channels", False)
    )


def ready(c, settings, job, *, controlled=False):
    from app.institutional import comment_automation
    from app.institutional.whatsapp_gemini import ORIGIN, dispatch_authorized

    item = account(c, settings, str(job["IntegrationId"]))
    payload = json.loads(job["Payload"])
    config = configuration(c, settings)
    if not config["OutboundEnabled"] or not config["ModuleEnabled"]:
        raise HTTPException(409, "outbound_paused")
    if (
        item["RequestedStatus"] != "connected"
        or item["VerifiedStatus"] != "verified"
        or item["ApplicationState"] == "retired"
    ):
        raise HTTPException(409, "account_paused_or_unverified")
    automated = payload.get("origin") == ORIGIN
    if automated:
        dispatch_authorized(c, settings, job, payload)
    elif payload.get("origin") == comment_automation.ORIGIN:
        comment_automation.authorize_send(c, settings, job, payload)
    elif not actor_allowed(c, settings, payload):
        raise HTTPException(403, "queued_actor_authority_revoked")
    bulk = False
    if settings.ticket.get("version") in {
        "cbn-institutional-broadcast-p7-v1",
        "cbn-institutional-campaign-p8-v1", 'cbn-institutional-ads-p9-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
        from app.institutional.broadcast_dispatch import ready as bulk_ready
        from app.institutional.broadcast_dispatch import record

        linked = record(c, settings, str(job["QueueId"]))
        if linked:
            if payload.get("origin") != "broadcast":
                raise HTTPException(409, "broadcast_payload_changed")
            item, payload = bulk_ready(c, settings, job, controlled=controlled)
            bulk = True
    if settings.ticket.get("version") in {'cbn-institutional-ads-p9-v1', 'cbn-institutional-campaign-p8-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
        from app.institutional.campaign_chat import (
            ready as campaign_ready,
        )
        from app.institutional.campaign_chat import (
            record as campaign_record,
        )

        if campaign_record(c, settings, job["QueueId"]):
            item, payload = campaign_ready(c, settings, job)
            bulk = True
    if not bulk and (
        payload.get("origin") in {"broadcast", "campaign", "marketing", "remarketing"}
        or "broadcastId" in payload
        or "campaignId" in payload
    ):
        raise HTTPException(423, "marketing_transport_disabled")
    if bulk:
        pass
    elif job["Kind"] == "comment_reply":
        comment = one(
            c,
            (
                "SELECT * FROM crm_channels2.SocialComm"
                "ent WHERE InstitutionId=? AND Integrat"
                "ionId=? AND CommentId=?"
            ),
            institution(settings),
            item["IntegrationId"],
            job["CommentId"],
        )
        if (
            not comment
            or json.loads(comment["Payload"]).get("_crm", {}).get("state") in {"deleted", "unavailable"}
        ):
            raise HTTPException(409, "comment_deleted")
        payload["target"] = comment["ExternalId"]
        payload["kind"] = "comment"
        if payload.get("privateReply"):
            from app.institutional.comment_private import eligible
            # Manual requests can use a stored creation date; the provider adapter
            # also reads the original source time immediately before its POST.
            raw = json.loads(comment["Payload"]).get("provider", {})
            eligible(item, comment, payload.get("privateSourceTime") or raw.get("created_time") or raw.get("timestamp"))
            linked = json.loads(comment["Payload"]).get("_crm", {}).get("conversation_id")
            if payload.get("origin") and linked:
                control = c.execute("SELECT ControlMode FROM crm.Conversation WHERE ConversationId=?", linked).fetchval()
                if control != "ai":
                    raise HTTPException(409, "comment_auto_human_control")
            payload["kind"] = "private_reply"
            payload["privateOriginalText"] = comment["Body"]
        payload["videoId"] = (
            json.loads(comment["Payload"]).get("provider", {}).get("video_id", "")
        )
    else:
        identity = one(
            c,
            (
                "SELECT i.* FROM crm_channels2.External"
                "Identity i JOIN crm.Conversation v ON "
                "v.ConversationId=i.ConversationId AND "
                "v.ContactId=i.ContactId JOIN crm.Messa"
                "ge m ON m.ConversationId=v.Conversatio"
                "nId JOIN crm_channels2.MessageRoute r "
                "ON r.InstitutionId=i.InstitutionId AND"
                " r.IdentityId=i.IdentityId AND r.Integ"
                "rationId=i.IntegrationId AND r.Message"
                "Id=m.MessageId WHERE i.InstitutionId=?"
                " AND i.IntegrationId=? AND i.IdentityI"
                "d=? AND m.MessageId=? AND r.QueueId=? "
                "AND v.State<>'closed' AND v.ControlMode=?"
                + (" AND r.ActorKind='bot'" if automated else "")
            ),
            institution(settings),
            item["IntegrationId"],
            job["IdentityId"],
            job["MessageId"],
            job["QueueId"],
            "ai" if automated else "human",
        )
        if not identity:
            raise HTTPException(409, "message_identity_account_mismatch")
        from app.institutional.agents_policy import VERSION as P5

        if settings.ticket.get("version") == P5:
            epoch = c.execute(
                (
                    "SELECT COALESCE(ctrl.Epoch,0) FROM crm"
                    ".Conversation v LEFT JOIN crm_channels"
                    ".ConversationControl ctrl ON ctrl.Conv"
                    "ersationId=v.ConversationId WHERE v.Co"
                    "nversationId=?"
                ),
                identity["ConversationId"],
            ).fetchval()
            if payload.get("controlEpoch") != epoch:
                raise HTTPException(409, "control_epoch_obsolete")
        if not identity["LastIncomingAt"] or identity[
            "LastIncomingAt"
        ] < datetime.utcnow() - timedelta(hours=24):
            raise HTTPException(409, "messaging_response_window_closed")
        payload["target"], payload["kind"] = identity["ExternalId"], "chat"
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,200}", payload["target"]):
        raise HTTPException(409, "provider_target_invalid")
    if item["Channel"] == "facebook" and job["Kind"] != "comment_reply":
        raise HTTPException(409, "facebook_chat_requires_messenger_account")
    if item["Channel"] == "tiktok":
        policy = one(
            c,
            (
                "SELECT * FROM crm_channels2.TikTokPoli"
                "cy WHERE InstitutionId=? AND Integrati"
                "onId=?"
            ),
            institution(settings),
            item["IntegrationId"],
        )
        if (
            not policy
            or policy["ReviewStatus"] != "approved"
            or policy["OutboundMode"] not in {"manual", "live"}
            or not policy["OperatorAttestedEvents"]
            or not policy[
                "CommentReplyEnabled"
                if job["Kind"] == "comment_reply"
                else "BusinessMessagingEnabled"
            ]
        ):
            raise HTTPException(409, "tiktok_business_capability_not_approved")
        products = set(json.loads(policy["ApprovedProducts"]))
        required_product = (
            "organic_comments"
            if job["Kind"] == "comment_reply"
            else "business_messaging"
        )
        scopes = set(json.loads(policy["ApprovedScopes"]))
        if (
            item["IssuerProfile"] != "tiktok_business"
            or required_product not in products
            or not scopes
            or not scopes <= set(json.loads(item["ApprovedScopes"]))
        ):
            raise HTTPException(409, "tiktok_granted_product_or_scope_missing")
        rollout = (
            int.from_bytes(
                bound_hash(settings, str(job["QueueId"]), "tiktok-rollout")[:2], "big"
            )
            % 100
        )
        if rollout >= policy["RolloutPercent"]:
            raise HTTPException(409, "tiktok_rollout_not_enabled")
    adapter, secret = provider_account(c, settings, item)
    return item, payload, adapter, secret


def reserve(c, settings, job):
    inst = institution(settings)
    limit = setting(c, settings, "budgets")["document"]["daily_messages"]
    if limit <= 0:
        raise HTTPException(429, "outbound_budget_disabled")
    total = c.execute(
        (
            "SELECT ISNULL(SUM(Reserved+Committed),"
            "0) FROM crm_channels2.QuotaBucket WHER"
            "E InstitutionId=? AND DayUtc=CONVERT(d"
            "ate,SYSUTCDATETIME()) AND Action='outb"
            "ound'"
        ),
        inst,
    ).fetchval()
    if total >= limit:
        raise HTTPException(429, "outbound_budget_exhausted")
    policy = one(
        c,
        (
            "SELECT DailyOutboundQuota FROM crm_cha"
            "nnels2.TikTokPolicy WHERE InstitutionI"
            "d=? AND IntegrationId=?"
        ),
        inst,
        job["IntegrationId"],
    )
    if policy:
        own = c.execute(
            (
                "SELECT ISNULL(SUM(Reserved+Committed),"
                "0) FROM crm_channels2.QuotaBucket WHER"
                "E InstitutionId=? AND IntegrationId=? "
                "AND DayUtc=CONVERT(date,SYSUTCDATETIME"
                "()) AND Action='outbound'"
            ),
            inst,
            job["IntegrationId"],
        ).fetchval()
        if policy["DailyOutboundQuota"] <= 0 or own >= policy["DailyOutboundQuota"]:
            raise HTTPException(429, "tiktok_daily_outbound_quota")
    from app.institutional.channel_reservations import preflight_reservation, restore

    prior = preflight_reservation(c, settings, job)
    identity = prior or str(uuid4())
    if prior:
        restore(c, settings, prior)
    if getattr(settings, "postgres_profile", False):
        c.native(
            """INSERT INTO rinovaplus_crm.crmcanalinstitucionalcuota
                  AS bucket (institutionid,integrationid,dayutc,action,reserved,committed,updatedat)
               VALUES(%s,%s,(statement_timestamp() AT TIME ZONE 'UTC')::date,
                      'outbound',1,0,statement_timestamp() AT TIME ZONE 'UTC')
               ON CONFLICT (institutionid,integrationid,dayutc,action)
               DO UPDATE SET reserved=bucket.reserved+1,updatedat=excluded.updatedat""",
            inst, job["IntegrationId"],
        )
    else:
        increment_reservation(c, inst, job["IntegrationId"])
    if prior:
        return identity
    c.execute(
        (
            "INSERT crm_channels2.QuotaReservation("
            "InstitutionId,ReservationId,Integratio"
            "nId,OperationId,DayUtc,Action,Units,St"
            "atus,CreatedAt,UpdatedAt) VALUES(?,?,?"
            ",?,CONVERT(date,SYSUTCDATETIME()),'out"
            "bound',1,'reserved',SYSUTCDATETIME(),S"
            "YSUTCDATETIME())"
        ),
        inst,
        identity,
        job["IntegrationId"],
        job["OperationId"],
    )
    return identity


def increment_reservation(c, institution, integration):
    c.execute(
        (
            "IF NOT EXISTS(SELECT 1 FROM crm_channe"
            "ls2.QuotaBucket WHERE InstitutionId=? "
            "AND IntegrationId=? AND DayUtc=CONVERT"
            "(date,SYSUTCDATETIME()) AND Action='ou"
            "tbound') INSERT crm_channels2.QuotaBuc"
            "ket(InstitutionId,IntegrationId,DayUtc"
            ",Action,Reserved,Committed,UpdatedAt) "
            "VALUES(?,?,CONVERT(date,SYSUTCDATETIME"
            "()),'outbound',0,0,SYSUTCDATETIME())"
        ),
        institution,
        integration,
        institution,
        integration,
    )
    c.execute(
        (
            "UPDATE crm_channels2.QuotaBucket SET R"
            "eserved=Reserved+1,UpdatedAt=SYSUTCDAT"
            "ETIME() WHERE InstitutionId=? AND Inte"
            "grationId=? AND DayUtc=CONVERT(date,SY"
            "SUTCDATETIME()) AND Action='outbound'"
        ),
        institution,
        integration,
    )


class Dispatcher:
    def __init__(self, settings, transport=None, *, allow_controlled=False):
        self.settings = settings
        self.transport = transport or providers.send
        self.allow_controlled = allow_controlled

    def frontier(self, queue, lease):
        with transaction(self.settings, True, anonymous=True) as c:
            job = one(
                c,
                (
                    "SELECT * FROM crm_channels2.SendJob WH"
                    "ERE InstitutionId=? AND QueueId=? AND "
                    "State='sending' AND LeaseId=? AND Leas"
                    "eUntil>SYSUTCDATETIME()"
                ),
                institution(self.settings),
                queue,
                lease,
            )
            if not job:
                raise HTTPException(409, "send_lease_lost")
            ready(c, self.settings, job, controlled=self.allow_controlled)
            if self.settings.ticket.get("version") in {
                "cbn-institutional-broadcast-p7-v1",
                "cbn-institutional-campaign-p8-v1", 'cbn-institutional-ads-p9-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
                from app.institutional.broadcast_dispatch import record
                from app.institutional.campaign_chat import record as campaign_record

                if record(c, self.settings, str(queue)) or (
                    self.settings.ticket.get("version") in {'cbn-institutional-ads-p9-v1', 'cbn-institutional-campaign-p8-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}
                    and campaign_record(c, self.settings, queue)
                ):
                    c.execute(
                        (
                            "UPDATE crm_broadcast7.Cadence SET Next"
                            "At=DATEADD(second,IntervalSeconds,SYSU"
                            "TCDATETIME()) WHERE InstitutionId=? AN"
                            "D IntegrationId=?"
                        ),
                        institution(self.settings),
                        job["IntegrationId"],
                    )

    def once(self):
        inst = institution(self.settings)
        postgres = getattr(self.settings, "postgres_profile", False)
        with transaction(self.settings, True, anonymous=True) as c:
            # A crashed POST is fenced as uncertain. Never reset it to queued
            # automatically.
            if postgres:
                postgres_queue.expire(c, inst)
            expired = [] if postgres else rows(
                c,
                (
                    "SELECT QueueId,OperationId,Reservation"
                    "Id FROM crm_channels2.SendJob WHERE In"
                    "stitutionId=? AND State='sending' AND "
                    "LeaseUntil<SYSUTCDATETIME()"
                ),
                inst,
            )
            for value in expired:
                c.execute(
                    (
                        "UPDATE crm_channels2.SendJob SET State"
                        "='uncertain',LastErrorCode='send_lease"
                        "_expired',LeaseId=NULL,LeaseUntil=NULL"
                        " WHERE InstitutionId=? AND QueueId=?"
                    ),
                    inst,
                    value["QueueId"],
                )
                c.execute(
                    (
                        "UPDATE crm_channels2.ProviderOperation"
                        " SET Status='uncertain',ResultCode='se"
                        "nd_lease_expired',LeaseId=NULL,LeaseUn"
                        "til=NULL WHERE InstitutionId=? AND Ope"
                        "rationId=?"
                    ),
                    inst,
                    value["OperationId"],
                )
                c.execute(
                    (
                        "UPDATE crm_channels2.QuotaReservation "
                        "SET Status='uncertain',UpdatedAt=SYSUT"
                        "CDATETIME() WHERE InstitutionId=? AND "
                        "ReservationId=?"
                    ),
                    inst,
                    value["ReservationId"],
                )
            config = configuration(c, self.settings)
            if not config["OutboundEnabled"] or not config["ModuleEnabled"]:
                return False
            job = postgres_queue.outbound(c, inst) if postgres else one(
                c,
                (
                    "SELECT TOP(1) * FROM crm_channels2.Sen"
                    "dJob WHERE InstitutionId=? AND State='"
                    "queued' AND DueAt<=SYSUTCDATETIME() OR"
                    "DER BY DueAt,QueueId"
                ),
                inst,
            )
            if not job:
                return False
            try:
                item, payload, adapter, secret = ready(
                    c, self.settings, job, controlled=self.allow_controlled
                )
                reservation = reserve(c, self.settings, job)
            except HTTPException as error:
                origin = json.loads(job["Payload"]).get("origin")
                discarded = (
                    origin == "gemini_whatsapp" and (
                        str(error.detail).startswith(("gemini_whatsapp_", "agents_"))
                        or error.detail in {"messaging_response_window_closed", "gemini_reply_context_changed"}
                    ) or origin == "gemini_comment" and str(error.detail).startswith("comment_auto_")
                )
                if discarded:
                    c.execute(
                        "UPDATE crm_channels2.SendJob SET State='cancelled',LastErrorCode=?,"
                        "CompletedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND QueueId=? AND State='queued'",
                        str(error.detail)[:64], inst, job["QueueId"],
                    )
                    c.execute(
                        "UPDATE crm_channels2.ProviderOperation SET Status='abandoned',ResultCode=?,"
                        "CompletedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND OperationId=? AND Status='pending'",
                        str(error.detail)[:64], inst, job["OperationId"],
                    )
                    from app.institutional.context_recovery import REASONS, replan

                    if origin == "gemini_whatsapp" and error.detail in REASONS:
                        replan(c, self.settings, json.loads(job["Payload"])["automationId"],
                               job["IntegrationId"], error.detail)
                    return True
                # Pauses and budgets retain queued work, with a bounded next inspection.
                c.execute(
                    (
                        "UPDATE crm_channels2.SendJob SET LastE"
                        "rrorCode=?,DueAt=DATEADD(second,?,SYS"
                        "UTCDATETIME()) WHERE InstitutionId=? A"
                        "ND QueueId=?"
                    ),
                    str(error.detail)[:64],
                    1 if error.detail == "reply_group_waiting_previous" else 900 if error.detail == "queued_actor_authority_revoked" else 30,
                    inst,
                    job["QueueId"],
                )
                return True
            lease = str(uuid4())
            if postgres:
                if not postgres_queue.lease(c, inst, job["QueueId"], lease, reservation):
                    raise HTTPException(409, "send_lease_lost")
            else:
                mark_sending(c, inst, job, lease, reservation)
        # Recheck just before the provider effect; authority/account changes fence the
        # intent.
        transport_entered = False
        try:
            with transaction(self.settings, True, anonymous=True) as c:
                current = one(
                    c,
                    (
                        "SELECT * FROM crm_channels2.SendJob WH"
                        "ERE InstitutionId=? AND QueueId=? AND "
                        "State='sending' AND LeaseId=? AND Leas"
                        "eUntil>SYSUTCDATETIME()"
                    ),
                    inst,
                    job["QueueId"],
                    lease,
                )
                if not current:
                    raise HTTPException(409, "send_lease_lost")
                current_item, _, adapter, current_secret = ready(
                    c, self.settings, current, controlled=self.allow_controlled
                )
                if bytes(current_item["RowVersion"]) != bytes(
                    item["RowVersion"]
                ) or str(current_secret["SecretId"]) != str(secret["SecretId"]):
                    raise HTTPException(409, "send_account_changed")
                media = None
                if payload.get("mediaId"):
                    from app.institutional.channel_media import file_for

                    value, media = file_for(c, self.settings, payload["mediaId"])
                    if str(value["MessageId"]) != str(job["MessageId"]) or str(
                        value["IntegrationId"]
                    ) != str(job["IntegrationId"]):
                        raise HTTPException(409, "media_message_account_mismatch")
                    if (
                        self.settings.ticket.get("version") in {'cbn-institutional-ads-p9-v1', 'cbn-institutional-campaign-p8-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}
                        and payload.get("origin") == "campaign"
                        and adapter["channel"] == "instagram"
                        and adapter["configuration"].get("instagramLogin")
                        == "instagram"
                    ):
                        from app.institutional.campaign_delivery import delivery_url

                        media["public_url"] = delivery_url(
                            c, self.settings, job, payload["mediaId"]
                        )
            if payload.get("origin") == "gemini_whatsapp" and payload.get("showTyping"):
                from app.institutional.reply_delivery import typing
                typing(adapter, payload["target"], payload.get("typingMessageId"), before=lambda: self.frontier(job["QueueId"], lease))
            # Only the built-in text transport has the proven pre-message POST
            # callback contract. Never infer safety after media/provider IO.
            def message_frontier():
                def check():
                    return self.frontier(job["QueueId"], lease)
                if not media and self.transport is providers.send and payload.get("origin") == "gemini_whatsapp":
                    from app.institutional.channel_reservations import before_text_send
                    return before_text_send(check)
                return check()
            transport_entered = True
            external = (
                self.transport(
                    adapter,
                    payload,
                    media=media,
                    before_send=message_frontier,
                )
                if media
                or self.settings.ticket.get("version")
                in {
                    "cbn-institutional-agents-p5-v1",
                    "cbn-institutional-knowledge-p6-v1",
                    "cbn-institutional-broadcast-p7-v1",
                    "cbn-institutional-campaign-p8-v1", 'cbn-institutional-ads-p9-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}
                else self.transport(adapter, payload)
            )
            if not isinstance(external, str) or not 1 <= len(external) <= 200:
                raise providers.ProviderFailure(
                    "provider_acceptance_not_confirmed", uncertain=True
                )
            state, code = "accepted", None
        except HTTPException as error:
            from app.institutional.channel_reservations import storage_wait
            waiting_for_storage = storage_wait(error, transport_entered)
            state, code, external = (
                (
                    "queued"
                    if waiting_for_storage or error.detail
                    in {"broadcast_cadence_wait", "campaign_quiet_or_not_due"}
                    else "failed"
                ),
                "outbound_storage_wait" if waiting_for_storage else str(error.detail)[:64],
                None,
            )
        except providers.ProviderFailure as error:
            state, code, external = (
                "uncertain" if error.uncertain else "failed",
                error.code,
                None,
            )
        except Exception:
            state, code, external = "uncertain", "provider_result_unknown", None
        with transaction(self.settings, True, anonymous=True) as c:
            current = one(
                c,
                (
                    "SELECT State,LeaseId FROM crm_channels"
                    "2.SendJob WHERE InstitutionId=? AND Qu"
                    "eueId=?"
                ),
                inst,
                job["QueueId"],
            )
            if (
                not current
                or not current["LeaseId"]
                or uid(str(current["LeaseId"])) != uid(lease)
            ):
                # Durable recovery owns the result; never overwrite another lease.
                return True
            c.execute(
                (
                    "UPDATE crm_channels2.SendJob SET State"
                    "=?,ExternalId=?,LastErrorCode=?,Comple"
                    "tedAt=CASE WHEN ?='queued' THEN NULL E"
                    "LSE SYSUTCDATETIME() END,LeaseId=NULL,"
                    "LeaseUntil=NULL WHERE InstitutionId=? "
                    "AND QueueId=? AND LeaseId=?"
                ),
                state,
                external,
                code,
                state,
                inst,
                job["QueueId"],
                lease,
            )
            if state == "queued" and code == "outbound_storage_wait":
                c.execute(
                    "UPDATE crm_channels2.SendJob SET DueAt=DATEADD(second,5,SYSUTCDATETIME()) "
                    "WHERE InstitutionId=? AND QueueId=? AND State='queued' AND LastErrorCode='outbound_storage_wait'",
                    inst, job["QueueId"],
                )
            c.execute(
                (
                    "UPDATE crm_channels2.ProviderOperation"
                    " SET Status=?,ResultCode=?,ResultMetad"
                    "ata=?,CompletedAt=SYSUTCDATETIME(),Lea"
                    "seId=NULL,LeaseUntil=NULL WHERE Instit"
                    "utionId=? AND OperationId=?"
                ),
                "confirmed"
                if state == "accepted"
                else "pending"
                if state == "queued"
                else state,
                code,
                json.dumps({"accepted": state == "accepted", "external_id": external,
                            **({"recipient_id": external.recipient_id} if getattr(external, "recipient_id", None) else {})}),
                inst,
                job["OperationId"],
            )
            reservation_state = {
                "accepted": "committed",
                "failed": "released",
                "uncertain": "uncertain",
                "queued": "released",
            }[state]
            c.execute(
                (
                    "UPDATE crm_channels2.QuotaReservation "
                    "SET Status=?,UpdatedAt=SYSUTCDATETIME("
                    ") WHERE InstitutionId=? AND Reservatio"
                    "nId=? AND Status='reserved'"
                ),
                reservation_state,
                inst,
                reservation,
            )
            if state != "uncertain" and postgres:
                c.native(
                    """UPDATE rinovaplus_crm.crmcanalinstitucionalcuota b
                       SET reserved=b.reserved-1,committed=b.committed+%s,
                           updatedat=statement_timestamp() AT TIME ZONE 'UTC'
                       FROM rinovaplus_crm.crmcanalinstitucionalcuotareserva r
                       WHERE r.institutionid=b.institutionid
                         AND r.integrationid=b.integrationid AND r.dayutc=b.dayutc
                         AND r.action=b.action AND r.institutionid=%s AND r.reservationid=%s""",
                    int(state == "accepted"), inst, reservation,
                )
            elif state != "uncertain":
                c.execute(
                    (
                        "UPDATE b SET Reserved=Reserved-1,Commi"
                        "tted=Committed+?,UpdatedAt=SYSUTCDATET"
                        "IME() FROM crm_channels2.QuotaBucket b"
                        " JOIN crm_channels2.QuotaReservation r"
                        " ON r.InstitutionId=b.InstitutionId AN"
                        "D r.IntegrationId=b.IntegrationId AND "
                        "r.DayUtc=b.DayUtc AND r.Action=b.Actio"
                        "n WHERE r.InstitutionId=? AND r.Reserv"
                        "ationId=?"
                    ),
                    1 if state == "accepted" else 0,
                    inst,
                    reservation,
                )
            if job["MessageId"]:
                c.execute(
                    (
                        "UPDATE crm_channels2.MessageRoute SET "
                        "CompletedAt=SYSUTCDATETIME() WHERE Ins"
                        "titutionId=? AND MessageId=?"
                    ),
                    inst,
                    job["MessageId"],
                )
            c.execute(
                ("UPDATE crm_workspace.State SET Revision=Revision+1 WHERE StateId=1")
            )
            if state in {"accepted", "failed", "uncertain"}:
                from app.institutional.email_notifications import observe_service
                observe_service(c, self.settings, "channel-send:" + str(job["IntegrationId"]), failed=state != "accepted", module="channels", account=str(job["IntegrationId"]))
        if state == "accepted":
            if (getattr(self.settings, "postgres_deployment", False) and job.get("MessageId")
                    and "siieplus.online/" in str(payload.get("body", "")).lower()):
                # Acceptance is durable: projection failures never replay Meta.
                try:
                    from app.institutional.commercial_followup import observe
                    with transaction(self.settings, True, anonymous=True) as c:
                        contact = one(c, "SELECT COALESCE(g.TargetContactId,i.ContactId) AS ContactId "
                            "FROM crm_channels2.MessageRoute r JOIN crm_channels2.ExternalIdentity i "
                            "ON i.InstitutionId=r.InstitutionId AND i.IdentityId=r.IdentityId "
                            "LEFT JOIN crm_workspace.Merge g ON g.SourceContactId=i.ContactId AND g.Active=1 "
                            "WHERE r.InstitutionId=? AND r.MessageId=?", institution(self.settings), job["MessageId"])
                        if contact:
                            observe(c, self.settings, contact["ContactId"])
                except Exception:
                    import logging
                    logging.getLogger(__name__).warning("commercial_followup_projection_pending")
            if payload.get("privateReply"):
                # Acceptance is already durable. A failed CRM projection must
                # never cause the provider message to be sent for a second time.
                try:
                    from app.institutional.meta_history import private_accepted
                    private_accepted(self.settings, job, payload, external)
                except Exception:
                    import logging
                    logging.getLogger(__name__).warning("private_reply_inbox_projection_pending")
                try:
                    from app.institutional.comment_acknowledgement import after_acceptance
                    after_acceptance(self.settings, job, payload)
                except Exception:
                    import logging
                    logging.getLogger(__name__).warning("private_reply_public_ack_pending")
            from app.institutional.reply_delivery import next_typing
            next_typing(self.settings, job, payload)
        return True


def mark_sending(c, institution, job, lease, reservation):
    c.execute(
        "UPDATE crm_channels2.SendJob SET State='sending',LeaseId=?,"
        "LeaseUntil=DATEADD(second,60,SYSUTCDATETIME()),LeaseVersion=LeaseVersion+1,"
        "Attempts=Attempts+1,ReservationId=? WHERE InstitutionId=? AND QueueId=? AND State='queued'",
        lease, reservation, institution, job["QueueId"],
    )
    c.execute(
        "UPDATE crm_channels2.ProviderOperation SET Status='running',Attempts=Attempts+1,"
        "LeaseId=?,LeaseUntil=DATEADD(second,60,SYSUTCDATETIME()),LeaseVersion=LeaseVersion+1"
        " WHERE InstitutionId=? AND OperationId=?",
        lease, institution, job["OperationId"],
    )
    if job["MessageId"]:
        c.execute(
            "UPDATE crm_channels2.MessageRoute SET StartedAt=SYSUTCDATETIME()"
            " WHERE InstitutionId=? AND MessageId=?",
            institution, job["MessageId"],
        )
