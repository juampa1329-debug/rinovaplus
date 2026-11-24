"""CRM text journeys use the existing C10 queue, authority and provider adapters."""

import json
from datetime import timedelta
from uuid import NAMESPACE_URL, uuid4, uuid5

from fastapi import HTTPException

from app.institutional.campaign_models import now
from app.institutional.campaigns import authority, event, key, reference, render_crm
from app.institutional.db import institution, one, rows, uid


def capability(c, s, item, job=None):
    if item["Channel"] != "tiktok":
        return
    policy = one(
        c,
        "SELECT * FROM crm_channels2.TikTokPolicy WHERE InstitutionId=? AND IntegrationId=?",
        institution(s),
        item["IntegrationId"],
    )
    if (
        not policy
        or policy["ReviewStatus"] != "approved"
        or policy["OutboundMode"] != "live"
        or not policy["OperatorAttestedEvents"]
        or not policy["BusinessMessagingEnabled"]
        or policy["RolloutPercent"] <= 0
    ):
        raise HTTPException(409, "campaign_tiktok_live_capability_required")
    if (
        item["IssuerProfile"] != "tiktok_business"
        or "business_messaging" not in json.loads(policy["ApprovedProducts"])
        or not json.loads(policy["ApprovedScopes"])
        or not set(json.loads(policy["ApprovedScopes"]))
        <= set(json.loads(item["ApprovedScopes"]))
    ):
        raise HTTPException(409, "tiktok_granted_product_or_scope_missing")
    count = c.execute(
        "SELECT ISNULL(SUM(Reserved+Committed),0) FROM crm_channels2.QuotaBucket WHERE InstitutionId=? AND IntegrationId=? AND DayUtc=CONVERT(date,SYSUTCDATETIME()) AND Action='outbound'",
        institution(s),
        item["IntegrationId"],
    ).fetchval()
    reserved = bool(
        job
        and job.get("ReservationId")
        and c.execute(
            "SELECT 1 FROM crm_channels2.QuotaReservation WHERE InstitutionId=? AND ReservationId=? AND OperationId=? AND Status='reserved'",
            institution(s),
            job["ReservationId"],
            job["OperationId"],
        ).fetchone()
    )
    if (
        policy["DailyOutboundQuota"] <= 0
        or count - (1 if reserved else 0) >= policy["DailyOutboundQuota"]
    ):
        raise HTTPException(429, "campaign_tiktok_daily_quota")


def links(c, s, step):
    return rows(
        c,
        "SELECT q.*,e.Document AS LinkDocument FROM crm_campaign8.Event e JOIN crm_channels2.SendJob q ON q.InstitutionId=e.InstitutionId AND q.QueueId=TRY_CONVERT(uniqueidentifier,JSON_VALUE(e.Document,'$.queue_id')) WHERE e.InstitutionId=? AND e.StepId=? AND e.Kind='native_chat' ORDER BY e.CreatedAt,e.EventId",
        institution(s),
        step["StepId"],
    )


def record(c, s, queue):
    return one(
        c,
        "SELECT e.StepId,e.EnrollmentId FROM crm_campaign8.Event e WHERE e.InstitutionId=? AND e.Kind='native_chat' AND JSON_VALUE(e.Document,'$.queue_id')=?",
        institution(s),
        uid(str(queue)),
    )


def template(c, s, doc, definition, variant, *, preview=False):
    b = variant == "B" and doc["ab_test"]["enabled"]
    id = definition["variant_b_crm_template_id"] if b else definition["crm_template_id"]
    version = (
        definition["variant_b_crm_template_version"]
        if b
        else definition["crm_template_version"]
    )
    if preview:
        saved = one(
            c,
            "SELECT Document FROM crm_campaign8.Version WHERE InstitutionId=? AND RecordId=? AND VersionNo=? AND Kind='template'",
            institution(s),
            id,
            version,
        )
        if not saved:
            raise HTTPException(404, "campaign_version_not_found")
        template = json.loads(saved["Document"])
    else:
        template = reference(
            c,
            s,
            definition["variant_b_crm_template_id"]
            if b
            else definition["crm_template_id"],
            definition["variant_b_crm_template_version"]
            if b
            else definition["crm_template_version"],
            "template",
        )
    if not template or template["channel"] != doc["channel"]:
        raise HTTPException(409, "campaign_CRM_template_channel_required")
    return template


def parts(c, s, doc, definition, variant, p, name, *, preview=False):
    value = template(c, s, doc, definition, variant, preview=preview)
    output = []
    if value["body"].strip():
        output.append(
            dict(kind="text", text=render_crm(dict(value, blocks=[]), p, name))
        )
    for block in value["blocks"]:
        text = render_crm(dict(value, body=block["text"], blocks=[]), p, name)
        if block["type"] in {"image", "video", "audio", "document"}:
            if doc["channel"] == "tiktok" and block["type"] not in {"image"}:
                raise HTTPException(409, "campaign_tiktok_media_not_supported")
            if block.get("asset_id"):
                from app.institutional.campaign_assets import library_file

                asset, _ = library_file(c, s, block["asset_id"])
                if asset["kind"] != block["type"]:
                    raise HTTPException(409, "campaign_media_kind_mismatch")
            output.append(
                dict(
                    kind=block["type"],
                    url=block["url"],
                    asset_id=block.get("asset_id"),
                    filename=block.get("filename", ""),
                    delay_ms=block.get("delay_ms", 0),
                    text=text if doc["channel"] == "whatsapp" else "",
                )
            )
            if text.strip() and doc["channel"] != "whatsapp":
                output.append(dict(kind="text", text=text, delay_ms=0))
        elif (text + " " + block["url"]).strip():
            output.append(
                dict(
                    kind="text",
                    text=(text + " " + block["url"]).strip(),
                    delay_ms=block.get("delay_ms", 0),
                )
            )
    if not output or any(len(v["text"].encode("utf-16-le")) > 7000 for v in output):
        raise HTTPException(409, "campaign_CRM_text_limit")
    return output


def content(c, s, doc, definition, variant, p, name, *, preview=False):
    value = template(c, s, doc, definition, variant, preview=preview)
    rendered = parts(c, s, doc, definition, variant, p, name, preview=preview)
    text = render_crm(value, p, name)
    if not text.strip():
        text = " · ".join(
            "[" + v["kind"] + "]" for v in rendered if v["kind"] != "text"
        )
    if not text.strip() or len(text.encode("utf-16-le")) > 7000:
        raise HTTPException(409, "campaign_CRM_text_limit")
    return text


def prepare(c, s, flow, doc, run, step, p, *, retry=False, next_part=False):
    from app.institutional.channel_operations import account
    from app.institutional.channel_outbox import enqueue

    old = links(c, s, step)
    if len(old) >= 420:
        raise HTTPException(409, "campaign_retry_limit")
    if old:
        job = old[-1]
        allowed = (
            job["State"] in {"accepted", "sent", "delivered", "read"}
            if next_part
            else (
                (job["State"] == "failed" and not job["ExternalId"])
                if retry
                else (job["State"] == "cancelled" and job["Attempts"] == 0)
            )
        )
        if not allowed:
            raise HTTPException(
                409, "campaign_retry_requires_definitive_unaccepted_effect"
            )
    item = account(c, s, doc["integration_id"])
    capability(c, s, item)
    if item["Channel"] != doc["channel"]:
        raise HTTPException(409, "campaign_account_mismatch")
    if not p["LastIncomingAt"] or p["LastIncomingAt"] < now() - timedelta(hours=24):
        raise HTTPException(409, "messaging_response_window_closed")
    cadence = one(
        c,
        "SELECT * FROM crm_broadcast7.Cadence WHERE InstitutionId=? AND IntegrationId=?",
        institution(s),
        item["IntegrationId"],
    )
    if not cadence or not cadence["Enabled"]:
        raise HTTPException(409, "campaign_cadence_required")
    if cadence["NextAt"] > now():
        raise HTTPException(429, "broadcast_cadence_wait")
    count = (
        cadence["Reserved"] if cadence["WindowAt"] > now() - timedelta(hours=24) else 0
    )
    if count >= cadence["DailyLimit"]:
        raise HTTPException(429, "campaign_daily_limit")
    index = (
        (
            json.loads(old[-1]["LinkDocument"]).get("part_index", 0)
            + (1 if next_part else 0)
        )
        if old
        else 0
    )
    rendered = parts(
        c, s, doc, doc["steps"][run["StepIndex"]], run["Variant"], p, flow["Name"]
    )
    if index >= len(rendered):
        raise HTTPException(409, "campaign_part_changed")
    attempts = sum(
        json.loads(v["LinkDocument"]).get("part_index", 0) == index for v in old
    )
    if attempts >= 20:
        raise HTTPException(409, "campaign_retry_limit")
    part = rendered[index]
    text = part["text"]
    from app.institutional.broadcasts import consent
    from app.institutional.campaigns import customer_window
    grant = consent(c, s, str(p["IdentityId"]))
    if not grant and not customer_window(doc, p):
        raise HTTPException(409, "marketing_consent_required")
    message = str(uuid4())
    c.execute(
        "INSERT crm.Message(MessageId,ConversationId,Body,Direction) VALUES(?,?,?,'outgoing')",
        message,
        p["ConversationId"],
        text
        or {
            "image": "[Imagen]",
            "video": "[Video]",
            "audio": "[Audio]",
            "document": "[Documento]",
        }.get(part["kind"], "[Adjunto]"),
    )
    payload = dict(
        origin="campaign",
        flowId=uid(str(flow["RecordId"])),
        stepId=uid(str(step["StepId"])),
        body=text,
        controlEpoch=p["ControlEpoch"],
        cadenceRevision=cadence["Revision"],
        accountVersion=bytes(item["RowVersion"]).hex(),
        consentVersion=grant["VersionNo"] if grant else None,
        contactBasis=doc.get("contact_basis", "marketing"),
    )
    payload["partIndex"] = index
    if part["kind"] != "text":
        from app.institutional.campaign_assets import attach_copy

        payload["mediaId"] = attach_copy(
            c,
            s,
            step,
            index,
            part,
            message,
            p,
            authority(c, s, flow),
            len(old) + 1,
        )
    previous_due = (
        old[-1]["DueAt"]
        if old and not next_part
        else (old[-1]["CompletedAt"] or now())
        + timedelta(milliseconds=part.get("delay_ms", 0))
        if old
        else run["DueAt"] + timedelta(milliseconds=part.get("delay_ms", 0))
    )
    planned = max(now(), previous_due)
    operation = str(
        uuid5(
            NAMESPACE_URL,
            "CBN-P8-chat:" + str(step["StepId"]) + ":" + str(len(old) + 1),
        )
    )
    queue = enqueue(
        c,
        s,
        item,
        authority(c, s, flow),
        operation,
        payload,
        identity=str(p["IdentityId"]),
        message=message,
    )
    c.execute(
        "UPDATE crm_channels2.SendJob SET DueAt=? WHERE InstitutionId=? AND QueueId=?",
        planned,
        institution(s),
        queue,
    )
    c.execute(
        "INSERT crm_channels2.MessageRoute(InstitutionId,MessageId,IntegrationId,IdentityId,QueueId,ActorKind) VALUES(?,?,?,?,?,'human')",
        institution(s),
        message,
        item["IntegrationId"],
        p["IdentityId"],
        queue,
    )
    c.execute(
        "UPDATE crm_broadcast7.Cadence SET WindowAt=?,Reserved=? WHERE InstitutionId=? AND IntegrationId=?",
        cadence["WindowAt"] if count else now(),
        count + 1,
        institution(s),
        item["IntegrationId"],
    )
    event(
        c,
        s,
        "native_chat",
        dict(queue_id=uid(str(queue)), attempt=len(old) + 1, part_index=index),
        record=str(flow["RecordId"]),
        enrollment=str(run["EnrollmentId"]),
        step=str(step["StepId"]),
        actor=flow["ActorId"],
        source=key("chat-attempt", step["StepId"], len(old) + 1),
    )
    c.execute(
        "UPDATE crm_campaign8.Step SET State='queued',LastReason=NULL WHERE InstitutionId=? AND StepId=?",
        institution(s),
        step["StepId"],
    )
    c.execute(
        "UPDATE crm_campaign8.Enrollment SET State='queued',LastReason=NULL WHERE InstitutionId=? AND EnrollmentId=?",
        institution(s),
        run["EnrollmentId"],
    )


def ready(c, s, job):
    from app.institutional.broadcasts import consent
    from app.institutional.campaign_runtime import guard
    from app.institutional.channel_operations import account

    linked = record(c, s, job["QueueId"])
    if not linked:
        raise HTTPException(409, "campaign_durable_chat_required")
    step = one(
        c,
        "SELECT * FROM crm_campaign8.Step WHERE InstitutionId=? AND StepId=?",
        institution(s),
        linked["StepId"],
    )
    run = one(
        c,
        "SELECT * FROM crm_campaign8.Enrollment WHERE InstitutionId=? AND EnrollmentId=?",
        institution(s),
        linked["EnrollmentId"],
    )
    attempts = links(c, s, step)
    if (
        step["State"] != "queued"
        or run["StepIndex"] != step["StepIndex"]
        or uid(str(attempts[-1]["QueueId"])) != uid(str(job["QueueId"]))
    ):
        raise HTTPException(409, "campaign_step_changed")
    flow, doc, p = guard(c, s, run, for_send=True)
    item = account(c, s, doc["integration_id"])
    capability(c, s, item, job)
    payload = json.loads(job["Payload"])
    if job["DueAt"] > now():
        raise HTTPException(409, "campaign_quiet_or_not_due")
    actor = authority(c, s, flow)
    index = json.loads(attempts[-1]["LinkDocument"]).get("part_index", 0)
    rendered = parts(
        c, s, doc, doc["steps"][run["StepIndex"]], run["Variant"], p, flow["Name"]
    )
    if index >= len(rendered) or payload.get("partIndex") != index:
        raise HTTPException(409, "campaign_part_changed")
    part = rendered[index]
    grant = consent(c, s, str(p["IdentityId"]))
    if (
        payload.get("origin") != "campaign"
        or payload.get("flowId") != uid(str(flow["RecordId"]))
        or payload.get("stepId") != uid(str(step["StepId"]))
        or payload.get("actorId") != actor["UserId"]
        or payload.get("actorSessionId") != actor["SessionId"]
        or uid(str(job["IdentityId"])) != uid(str(run["IdentityId"]))
        or uid(str(job["IntegrationId"])) != doc["integration_id"]
        or payload.get("accountVersion") != bytes(item["RowVersion"]).hex()
        or payload.get("consentVersion")
        != (grant["VersionNo"] if grant else None)
        or payload.get("contactBasis", "marketing") != doc.get("contact_basis", "marketing")
        or payload.get("body") != part["text"]
    ):
        raise HTTPException(409, "campaign_chat_changed")
    if not p["LastIncomingAt"] or p["LastIncomingAt"] < now() - timedelta(hours=24):
        raise HTTPException(409, "messaging_response_window_closed")
    route = one(
        c,
        "SELECT * FROM crm_channels2.MessageRoute WHERE InstitutionId=? AND QueueId=?",
        institution(s),
        job["QueueId"],
    )
    if (
        not route
        or str(route["MessageId"]) != str(job["MessageId"])
        or str(route["IdentityId"]) != str(run["IdentityId"])
    ):
        raise HTTPException(409, "campaign_route_changed")
    cadence = one(
        c,
        "SELECT * FROM crm_broadcast7.Cadence WHERE InstitutionId=? AND IntegrationId=?",
        institution(s),
        item["IntegrationId"],
    )
    if (
        not cadence
        or not cadence["Enabled"]
        or cadence["Revision"] != payload.get("cadenceRevision")
    ):
        raise HTTPException(409, "broadcast_cadence_changed")
    if cadence["NextAt"] > now():
        raise HTTPException(429, "broadcast_cadence_wait")
    if part["kind"] != "text":
        from app.institutional.channel_media import file_for

        if not payload.get("mediaId"):
            raise HTTPException(409, "campaign_image_required")
        value, info = file_for(
            c, s, payload["mediaId"], conversation=str(p["ConversationId"])
        )
        if (
            str(value["MessageId"]) != str(job["MessageId"])
            or info["kind"] != part["kind"]
        ):
            raise HTTPException(409, "campaign_image_context_changed")
    elif payload.get("mediaId"):
        raise HTTPException(409, "campaign_image_context_changed")
    payload.update(target=p["ExternalId"], kind="chat")
    return item, payload


def actor_allowed(c, s, payload):
    from app.institutional.campaigns import get

    try:
        flow = get(c, s, uid(payload.get("flowId")))
        actor = authority(c, s, flow)
        return (
            payload.get("actorId") == actor["UserId"]
            and payload.get("actorSessionId") == actor["SessionId"]
        )
    except HTTPException:
        return False
