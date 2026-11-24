"""Reviewed recovery of a campaign button incorrectly handed off, never an IO replay."""

import json
from uuid import UUID, uuid5

from fastapi import HTTPException, Request

from app.institutional import broadcast_conversation, db
from app.institutional.auth import authorize
from app.institutional.reply_recovery import Recover
from app.institutional.store import transaction


def eligible(row):
    prior = json.loads(row["ResultMetadata"])
    return (
        broadcast_conversation.advisor_entry(row["Body"])
        and prior.get("incoming") == db.uid(str(row["MessageId"]))
        and prior.get("identity") == db.uid(str(row["IdentityId"]))
        and prior.get("conversation") == db.uid(str(row["ConversationId"]))
        and type(prior.get("epoch")) is int
        and row["Epoch"] == prior["epoch"] + 1
        and not prior.get("reply") and not prior.get("response_parts")
        and not prior.get("generated_text")
    )


def candidates(c, s, conversation=None):
    result = []
    rows = db.rows(c,
        "SELECT TOP(100) m.MessageId,m.ConversationId,m.Body,m.Sequence,m.CreatedAt,"
        "r.IntegrationId,r.IdentityId,ctrl.Epoch,p.Name,a.Channel,a.DisplayName,op.ResultMetadata "
        "FROM crm.Message m JOIN crm.Conversation v ON v.ConversationId=m.ConversationId "
        "JOIN crm.Contact p ON p.ContactId=v.ContactId "
        "JOIN crm_channels.ConversationControl ctrl ON ctrl.ConversationId=v.ConversationId "
        "JOIN crm_channels2.MessageRoute r ON r.MessageId=m.MessageId AND r.InstitutionId=? AND r.ActorKind='external' "
        "JOIN crm_channels2.ExternalIdentity i ON i.InstitutionId=r.InstitutionId AND i.IntegrationId=r.IntegrationId "
        "AND i.IdentityId=r.IdentityId AND i.ConversationId=v.ConversationId AND i.ContactId=v.ContactId "
        "JOIN crm_channels2.Integration a ON a.InstitutionId=r.InstitutionId AND a.IntegrationId=r.IntegrationId "
        "JOIN crm_channels2.ProviderOperation op ON op.InstitutionId=r.InstitutionId AND op.OperationId=m.MessageId "
        "AND op.IntegrationId=r.IntegrationId AND op.Action='whatsapp_gemini_intro' "
        "AND op.ActorRef='system:gemini-whatsapp' AND op.Status='confirmed' AND op.ResultCode='gemini_handoff' "
        "WHERE m.Direction='incoming' AND v.ControlMode='human' AND v.State<>'closed' AND a.Channel='whatsapp' "
        "AND a.RequestedStatus='connected' AND a.VerifiedStatus='verified' "
        "AND m.CreatedAt>=DATEADD(hour,-24,SYSUTCDATETIME()) AND m.Body='Hablar con Juan Pablo' "
        "AND NOT EXISTS(SELECT 1 FROM crm.Message newer WHERE newer.ConversationId=m.ConversationId AND newer.Sequence>m.Sequence) "
        "AND NOT EXISTS(SELECT 1 FROM crm_channels2.ProviderOperation newer WHERE newer.InstitutionId=r.InstitutionId "
        "AND newer.OperationId<>op.OperationId AND JSON_VALUE(newer.ResultMetadata,'$.incoming')=LOWER(CONVERT(varchar(36),m.MessageId))) "
        + ("AND m.ConversationId=? " if conversation else "")
        + "ORDER BY m.CreatedAt DESC,m.Sequence DESC", db.institution(s), *((db.uid(conversation),) if conversation else ()))
    for row in rows:
        if not eligible(row):
            continue
        campaign = broadcast_conversation.origin(c, s, row["ConversationId"], [{**row, "Direction": "incoming"}])
        if not campaign:
            continue
        row["CampaignId"] = campaign["campaign_id"]
        row["PriorCampaignContext"] = "inicio_comercial_campana" in json.loads(row["ResultMetadata"]).get("contextComponents", {})
        result.append(row)
    return result


def proof(s, row):
    return db.bound_hash(s, {k: str(row[k]) for k in (
        "MessageId", "ConversationId", "Sequence", "IntegrationId", "IdentityId", "Epoch", "CampaignId"
    )}, "advisor-recovery").hex()


def install(app, s):
    @app.get("/api/institution/advisor-recovery")
    def preview(request: Request, conversation_id: str | None = None):
        with transaction(s, anonymous=True) as c:
            authorize(c, s, request.state.authority, "users.manage")
            return {"items": [{"id": db.uid(str(v["MessageId"])), "conversation_id": db.uid(str(v["ConversationId"])),
                "name": v["Name"], "channel": v["Channel"], "account": v["DisplayName"], "at": db.utc(v["CreatedAt"]),
                "proof": proof(s, v), "prior_campaign_context": v["PriorCampaignContext"]}
                for v in candidates(c, s, conversation_id)]}

    @app.post("/api/institution/advisor-recovery")
    def recover(request: Request, body: Recover):
        if not body.confirmed or len({str(v.id) for v in body.inputs}) != len(body.inputs):
            raise HTTPException(422, "reply_recovery_review_required")
        with transaction(s, True, anonymous=True) as c:
            actor = authorize(c, s, request.state.authority, "settings.channels.write", recent=True)
            authorize(c, s, request.state.authority, "inbox.write")
            digest, prior = db.replay(c, s, actor["UserId"], str(body.operation_id), "reply.recover_advisor", "", body.model_dump(mode="json"))
            if prior:
                return prior
            current = {db.uid(str(v["MessageId"])): v for v in candidates(c, s)}
            from app.institutional.whatsapp_gemini import schedule, source
            from app.modules.inbox.application.state import change_control
            for selected in body.inputs:
                row = current.get(str(selected.id))
                if not row or proof(s, row) != selected.proof:
                    raise HTTPException(409, "reply_recovery_source_changed")
                # Only the exact automatic handoff epoch qualifies. Any later human
                # control change, message or operation makes the signed review stale.
                change_control(c, row["ConversationId"], "human", "ai")
                c.execute("UPDATE crm.Conversation SET ControlMode='ai',UpdatedAt=SYSUTCDATETIME() WHERE ConversationId=? AND ControlMode='human'", row["ConversationId"])
                data = {"conversation": db.uid(str(row["ConversationId"])), "identity": db.uid(str(row["IdentityId"])),
                        "incoming": str(selected.id), "epoch": row["Epoch"] + 1, "channel": row["Channel"]}
                item, _, _ = source(c, s, row["IntegrationId"], data)
                operation = str(uuid5(UUID(str(body.operation_id)), str(selected.id)))
                schedule(c, s, item, row, str(selected.id), operation_id=operation)
                if not c.execute("SELECT 1 FROM crm_channels2.ProviderOperation WHERE InstitutionId=? AND OperationId=? AND Status='pending'", db.institution(s), operation).fetchone():
                    raise HTTPException(409, "reply_recovery_not_scheduled")
                db.audit(c, s, actor["UserId"], "reply.recover_advisor", operation)
            result = {"queued": len(body.inputs), "provider_calls": 0, "messages_resent": False, "restored_ai": True}
            db.record_operation(c, s, actor["UserId"], str(body.operation_id), "reply.recover_advisor", "", digest, result)
            c.execute("UPDATE crm_workspace.State SET Revision=Revision+1 WHERE StateId=1")
            return result
