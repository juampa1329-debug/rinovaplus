"""Operator recovery creates new attempts only after a known failed effect."""

import json
from uuid import uuid4

from fastapi import HTTPException

from app.institutional.auth import authorize
from app.institutional.channel_operations import configuration
from app.institutional.channel_outbox import enqueue
from app.institutional.db import institution, one, uid


def recover_send(c, settings, authority, actor, item, body):
    if settings.ticket.get("version") in {
        "cbn-institutional-broadcast-p7-v1",
        "cbn-institutional-campaign-p8-v1", 'cbn-institutional-ads-p9-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
        from app.institutional.broadcast_dispatch import record

        if record(c, settings, uid(body.resource_id)):
            raise HTTPException(409, "broadcast_retry_from_campaign")
    if settings.ticket.get("version") in {'cbn-institutional-ads-p9-v1', 'cbn-institutional-campaign-p8-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
        from app.institutional.campaign_chat import record as campaign_record

        if campaign_record(c, settings, uid(body.resource_id)):
            raise HTTPException(409, "campaign_retry_from_flow")
    authorize(c, settings, authority, "inbox.write", recent=True)
    if not configuration(c, settings)["ModuleEnabled"]:
        raise HTTPException(403, "module_disabled")
    value = one(
        c,
        (
            "SELECT * FROM crm_channels2.SendJob WI"
            "TH(UPDLOCK,HOLDLOCK) WHERE Institution"
            "Id=? AND IntegrationId=? AND QueueId=?"
        ),
        institution(settings),
        item["IntegrationId"],
        uid(body.resource_id),
    )
    expected = "failed" if body.action == "retry_send" else "queued"
    if (
        not value
        or value["State"] != expected
        or bytes(value["RowVersion"]).hex() != body.row_version
    ):
        raise HTTPException(409, "send_recovery_unavailable")
    if item["RequestedStatus"] != "connected" or item["VerifiedStatus"] != "verified":
        raise HTTPException(409, "verified_connected_account_required")
    payload = json.loads(value["Payload"])
    # A restored or expired human session cannot silently authorize provider IO.
    # Preserve the original actor while recording a deliberate current approval.
    payload.setdefault("originalActorId", payload.get("actorId"))
    payload.setdefault("originalActorSessionId", payload.get("actorSessionId"))
    payload["recoveryOperationId"] = body.operation_id
    if body.action == "resume_queued":
        payload.update(actorId=actor["UserId"], actorSessionId=actor["SessionId"])
        c.execute(
            (
                "UPDATE crm_channels2.SendJob SET Paylo"
                "ad=?,DueAt=SYSUTCDATETIME(),LastErrorCode=NULL WHERE InstitutionId=? AND QueueId"
                "=? AND State='queued' AND RowVersion=?"
            ),
            json.dumps(payload),
            institution(settings),
            value["QueueId"],
            bytes.fromhex(body.row_version),
        )
        if c.rowcount != 1:
            raise HTTPException(409, "send_recovery_unavailable")
        return uid(str(value["QueueId"]))
    operation = one(
        c,
        (
            "SELECT Status FROM crm_channels2.Provi"
            "derOperation WHERE InstitutionId=? AND"
            " OperationId=?"
        ),
        institution(settings),
        value["OperationId"],
    )
    if not operation or operation["Status"] != "failed":
        raise HTTPException(409, "certain_failure_required")
    if (
        value["CommentId"]
        and c.execute(
            (
                "SELECT 1 FROM crm_channels2.SendJob WH"
                "ERE InstitutionId=? AND IntegrationId="
                "? AND CommentId=? AND QueueId<>? AND S"
                "tate IN('queued','sending','uncertain'"
                ",'accepted','sent','delivered')"
            ),
            institution(settings),
            item["IntegrationId"],
            value["CommentId"],
            value["QueueId"],
        ).fetchone()
    ):
        raise HTTPException(409, "comment_reply_already_pending")
    for field in ("actorId", "actorSessionId"):
        payload.pop(field, None)
    queue = enqueue(
        c,
        settings,
        item,
        actor,
        str(uuid4()),
        payload,
        comment=uid(str(value["CommentId"])) if value["CommentId"] else None,
        identity=uid(str(value["IdentityId"])) if value["IdentityId"] else None,
        message=uid(str(value["MessageId"])) if value["MessageId"] else None,
    )
    c.execute(
        (
            "UPDATE crm_channels2.SendJob SET State"
            "='retried' WHERE InstitutionId=? AND Q"
            "ueueId=? AND State='failed' AND RowVer"
            "sion=?"
        ),
        institution(settings),
        value["QueueId"],
        bytes.fromhex(body.row_version),
    )
    if value["MessageId"]:
        c.execute(
            (
                "UPDATE crm_channels2.MessageRoute SET "
                "QueueId=?,StartedAt=NULL,CompletedAt=N"
                "ULL WHERE InstitutionId=? AND Integrat"
                "ionId=? AND MessageId=? AND QueueId=?"
            ),
            queue,
            institution(settings),
            item["IntegrationId"],
            value["MessageId"],
            value["QueueId"],
        )
        if c.rowcount != 1:
            raise HTTPException(409, "message_identity_account_mismatch")
    return uid(str(queue))
