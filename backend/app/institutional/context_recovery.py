"""Replan stale, unattempted replies; never replay a channel side effect."""

import json
from uuid import NAMESPACE_URL, uuid5

from fastapi import HTTPException

from app.institutional import db

MAX_REPLANS = 3
REASONS = {"gemini_reply_context_changed", "gemini_whatsapp_model_changed", "language_backup_configuration_changed"}


def replan(c, settings, operation, integration, reason):
    if reason not in REASONS:
        return False
    from app.institutional import whatsapp_gemini as replies

    inst = db.institution(settings)
    row = db.one(c,
        "SELECT ResultMetadata FROM crm_channels2.ProviderOperation "
        "WHERE InstitutionId=? AND IntegrationId=? AND OperationId=? "
        "AND Action=? AND ActorRef=? AND Status IN('confirmed','abandoned')",
        inst, integration, operation, replies.ACTION, replies.ACTOR)
    if not row:
        return False
    data = json.loads(row["ResultMetadata"])
    if data.get("recovery_operation") or data.get("context_replans", 0) >= MAX_REPLANS:
        return False
    data["integration"] = db.uid(str(integration))
    try:
        # Same authenticated input, current account, latest history and exact
        # AI control epoch. A new input has its own operation; Humano wins.
        item, _, _ = replies.source(c, settings, integration, data)
    except HTTPException:
        return False
    prior_ids = sorted({value for generation in data.get("cancelled_generations", []) for value in generation.get("reply_ids", [])})
    jobs = db.rows(c,
        "SELECT j.QueueId,j.OperationId,j.MessageId,j.State,j.Attempts,j.ExternalId "
        "FROM crm_channels2.SendJob j JOIN crm_channels2.MessageRoute r "
        "ON r.InstitutionId=j.InstitutionId AND r.QueueId=j.QueueId "
        "AND r.IntegrationId=j.IntegrationId AND r.IdentityId=j.IdentityId "
        "JOIN crm.Message m ON m.MessageId=r.MessageId "
        "WHERE j.InstitutionId=? AND j.IntegrationId=? AND j.IdentityId=? "
        "AND m.ConversationId=? AND r.ActorKind='bot' AND r.ControlEpoch=? "
        "AND (JSON_VALUE(j.Payload,'$.automationId')=?"
        + (" OR j.MessageId IN(" + ",".join("?" for _ in prior_ids) + ")" if prior_ids else "") + ")",
        inst, integration, data["identity"], data["conversation"], data["epoch"], db.uid(str(operation)), *prior_ids)
    expected = {part["id"] for part in data.get("response_parts", [])} | set(prior_ids)
    accepted = {db.uid(str(job["MessageId"])) for job in jobs
                if job["State"] in {"accepted", "sent", "delivered", "read"}
                and job["Attempts"] > 0 and job["ExternalId"]}
    if {db.uid(str(job["MessageId"])) for job in jobs} != expected or any(
        db.uid(str(job["MessageId"])) not in accepted and (
            job["Attempts"] != 0 or job["ExternalId"]
            or job["State"] not in {"queued", "cancelled"}) for job in jobs
    ) or expected and accepted == expected:
        # Explicitly accepted parts become history, never retries. Attempted,
        # sending and uncertain parts still require receipt reconciliation.
        return False
    for job in jobs:
        if job["State"] == "queued":
            c.execute(
                "UPDATE crm_channels2.SendJob SET State='cancelled',"
                "LastErrorCode='reply_context_replanned',CompletedAt=SYSUTCDATETIME() "
                "WHERE InstitutionId=? AND QueueId=? AND State='queued' "
                "AND Attempts=0 AND ExternalId IS NULL", inst, job["QueueId"])
            if c.rowcount != 1:
                raise HTTPException(409, "reply_context_recovery_changed")
            c.execute(
                "UPDATE crm_channels2.ProviderOperation SET Status='abandoned',"
                "ResultCode='reply_context_replanned',CompletedAt=SYSUTCDATETIME() "
                "WHERE InstitutionId=? AND OperationId=? AND Status='pending'",
                inst, job["OperationId"])
    attempt = data.get("context_replans", 0) + 1
    root = data.get("context_recovery_root", db.uid(str(operation)))
    recovery = str(uuid5(NAMESPACE_URL, "rinova:context-recovery:" + root + ":" + str(attempt)))
    replies.schedule(c, settings, item,
                     {"ConversationId": data["conversation"], "IdentityId": data["identity"]},
                     data["incoming"], operation_id=recovery)
    fresh = db.one(c,
        "SELECT ResultMetadata FROM crm_channels2.ProviderOperation WHERE InstitutionId=? "
        "AND IntegrationId=? AND OperationId=? AND Action=? AND Status='pending'",
        inst, integration, recovery, replies.ACTION)
    if not fresh:
        raise HTTPException(409, "reply_context_recovery_changed")
    new_data = json.loads(fresh["ResultMetadata"])
    prior = data.get("cancelled_generations", [])
    new_data.update(
        cancelled_generations=[*prior, {"reply_ids": sorted(expected)}],
        context_replans=attempt, context_recovery_root=root,
        recovery_from=db.uid(str(operation)), recovery_reason=reason,
        accepted_continuation_ids=sorted(accepted))
    if data.get("input_kind") == "unsupported":
        new_data["input_kind"] = "unsupported"
    c.execute(
        "UPDATE crm_channels2.ProviderOperation SET ResultMetadata=? WHERE InstitutionId=? "
        "AND OperationId=? AND Status='pending'",
        json.dumps(new_data), inst, recovery)
    data["recovery_operation"] = recovery
    c.execute(
        "UPDATE crm_channels2.ProviderOperation SET ResultMetadata=? WHERE InstitutionId=? "
        "AND OperationId=? AND Status IN('confirmed','abandoned')",
        json.dumps(data), inst, operation)
    c.execute("UPDATE crm_workspace.State SET Revision=Revision+1 WHERE StateId=1")
    return True
