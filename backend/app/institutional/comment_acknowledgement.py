"""One public acknowledgement, only after a durable accepted automatic DM."""
import json
from uuid import NAMESPACE_URL, uuid5

from fastapi import HTTPException

from app.institutional.db import institution, one, uid
from app.institutional.settings import setting
from app.modules.agents.domain import digest

TEXT = "Te enviamos la información por mensaje privado 😊 Si no la ves, revisa también tus solicitudes."


def operation(settings, comment):
    return str(uuid5(NAMESPACE_URL, "rinova:comment-private-ack:v1:" + str(institution(settings)) + ":" + str(comment).lower()))


def authorize(c, settings, job, payload):
    from app.institutional.comment_automation import ACTOR, ACTION, ORIGIN
    from app.institutional.comment_private import enabled
    if payload.get("privateReply") or payload.get("body") != TEXT or uid(str(job["OperationId"])) != operation(settings, job["CommentId"]):
        raise HTTPException(409, "comment_auto_ack_invalid")
    source = one(c,
        "SELECT q.Payload,q.State,q.ExternalId,p.ResultMetadata FROM crm_channels2.SendJob q "
        "JOIN crm_channels2.ProviderOperation p ON p.InstitutionId=q.InstitutionId "
        "AND p.IntegrationId=q.IntegrationId AND p.OperationId=q.CommentId "
        "AND p.ActorRef=? AND p.Action=? AND p.Status='confirmed' "
        "WHERE q.InstitutionId=? AND q.IntegrationId=? AND q.CommentId=? AND q.QueueId=?",
        ACTOR, ACTION, institution(settings), job["IntegrationId"], job["CommentId"], payload.get("privateAcknowledgementOf"))
    if not source or source["State"] not in {"accepted", "sent", "delivered", "read"} or not source["ExternalId"]:
        raise HTTPException(409, "comment_auto_ack_without_acceptance")
    original, intent = json.loads(source["Payload"]), json.loads(source["ResultMetadata"])
    if not original.get("privateReply") or original.get("origin") != ORIGIN or original.get("body") != intent.get("generated_text"):
        raise HTTPException(409, "comment_auto_ack_invalid")
    ai = setting(c, settings, "ai")["document"]
    if not ai.get("enabled") or ai.get("comment_mode", "auto") != "auto" or not enabled(ai, job["IntegrationId"]):
        raise HTTPException(409, "comment_auto_disabled")
    comment = one(c, "SELECT Body,Payload FROM crm_channels2.SocialComment WHERE InstitutionId=? AND IntegrationId=? AND CommentId=?",
                  institution(settings), job["IntegrationId"], job["CommentId"])
    state = json.loads(comment["Payload"]).get("_crm", {}) if comment else {}
    if not comment or state.get("state") in {"deleted", "unavailable", "archived"} or state.get("control_mode", "ai") != "ai" or intent.get("source_text_digest") != digest(comment["Body"]):
        raise HTTPException(409, "comment_auto_source_changed")
    linked = state.get("conversation_id")
    if linked and c.execute("SELECT ControlMode FROM crm.Conversation WHERE ConversationId=?", linked).fetchval() != "ai":
        raise HTTPException(409, "comment_auto_human_control")
    if c.execute("SELECT 1 FROM crm_channels2.SendJob WHERE InstitutionId=? AND IntegrationId=? AND CommentId=? "
                 "AND QueueId<>? AND QueueId<>? AND JSON_VALUE(Payload,'$.privateReply') IS NULL "
                 "AND (State NOT IN('failed','cancelled','retried') OR Attempts>0 OR ExternalId IS NOT NULL)",
                 institution(settings), job["IntegrationId"], job["CommentId"], payload["privateAcknowledgementOf"], job["QueueId"]).fetchone():
        raise HTTPException(409, "comment_auto_already_answered")


def after_acceptance(settings, job, payload):
    from app.institutional.comment_automation import ORIGIN
    if payload.get("origin") != ORIGIN or not payload.get("privateReply"):
        return
    from app.institutional.store import transaction
    from app.institutional.channel_outbox import enqueue
    from app.institutional.channel_operations import account
    outgoing = {"origin": ORIGIN, "body": TEXT, "privateAcknowledgementOf": str(job["QueueId"])}
    synthetic = {**job, "OperationId": operation(settings, job["CommentId"]), "QueueId": "00000000-0000-0000-0000-000000000000"}
    with transaction(settings, True, anonymous=True) as c:
        try:
            authorize(c, settings, synthetic, outgoing)
        except HTTPException as error:
            if error.status_code == 409:
                return  # No DM replay; preserve control, edits and prior public replies.
            raise
        enqueue(c, settings, account(c, settings, job["IntegrationId"]), None,
                synthetic["OperationId"], outgoing, comment=job["CommentId"])
