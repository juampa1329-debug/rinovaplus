"""Explicit recovery of inputs with no AI operation, not replay of provider IO."""

from fastapi import HTTPException, Request
from pydantic import Field

from app.institutional import db
from app.institutional.auth import authorize
from app.institutional.models import Strict
from app.institutional.store import transaction
from app.modules.agents.domain import JsonUUID


class Input(Strict):
    id: JsonUUID
    proof: str = Field(pattern=r"^[a-f0-9]{64}$")


class Recover(Strict):
    operation_id: JsonUUID
    confirmed: bool
    inputs: list[Input] = Field(min_length=1, max_length=25)


def missing(c, s, conversation=None):
    return db.rows(
        c,
        "SELECT TOP(50) m.MessageId,m.ConversationId,m.Body,m.Sequence,m.CreatedAt,"
        "r.IntegrationId,r.IdentityId,ctrl.Epoch,p.Name,a.Channel,a.DisplayName "
        "FROM crm.Message m JOIN crm.Conversation v ON v.ConversationId=m.ConversationId "
        "JOIN crm.Contact p ON p.ContactId=v.ContactId "
        "JOIN crm_channels.ConversationControl ctrl ON ctrl.ConversationId=v.ConversationId "
        "JOIN crm_channels2.MessageRoute r ON r.MessageId=m.MessageId AND r.InstitutionId=? AND r.ActorKind='external' "
        "JOIN crm_channels2.ExternalIdentity i ON i.InstitutionId=r.InstitutionId AND i.IntegrationId=r.IntegrationId "
        "AND i.IdentityId=r.IdentityId AND i.ConversationId=v.ConversationId AND i.ContactId=v.ContactId "
        "JOIN crm_channels2.Integration a ON a.InstitutionId=r.InstitutionId AND a.IntegrationId=r.IntegrationId "
        "WHERE m.Direction='incoming' AND v.ControlMode='ai' AND v.State<>'closed' "
        "AND a.Channel IN('whatsapp','messenger','instagram') AND a.RequestedStatus='connected' AND a.VerifiedStatus='verified' "
        "AND m.CreatedAt>=DATEADD(hour,-24,SYSUTCDATETIME()) AND LEN(m.Body)>0 AND LEFT(m.Body,1)<>'[' "
        "AND NOT EXISTS(SELECT 1 FROM crm.Message newer WHERE newer.ConversationId=m.ConversationId AND newer.Sequence>m.Sequence) "
        "AND NOT EXISTS(SELECT 1 FROM crm_channels2.ProviderOperation op WHERE op.InstitutionId=r.InstitutionId AND op.OperationId=m.MessageId) "
        + ("AND m.ConversationId=? " if conversation else "")
        + "ORDER BY m.CreatedAt DESC,m.Sequence DESC",
        db.institution(s),
        *((db.uid(conversation),) if conversation else ()),
    )


def proof(s, row):
    return db.bound_hash(
        s,
        {
            k: str(row[k])
            for k in (
                "MessageId",
                "ConversationId",
                "Body",
                "Sequence",
                "IntegrationId",
                "IdentityId",
                "Epoch",
            )
        },
        "reply-recovery",
    ).hex()


def install(app, s):
    @app.get("/api/institution/reply-recovery")
    def preview(request: Request, conversation_id: str | None = None):
        with transaction(s, anonymous=True) as c:
            authorize(c, s, request.state.authority, "users.manage")
            return {
                "items": [
                    {
                        "id": db.uid(str(v["MessageId"])),
                        "conversation_id": db.uid(str(v["ConversationId"])),
                        "name": v["Name"],
                        "channel": v["Channel"],
                        "account": v["DisplayName"],
                        "at": db.utc(v["CreatedAt"]),
                        "proof": proof(s, v),
                    }
                    for v in missing(c, s, conversation_id)
                ]
            }

    @app.post("/api/institution/reply-recovery")
    def recover(request: Request, body: Recover):
        if not body.confirmed or len({str(v.id) for v in body.inputs}) != len(
            body.inputs
        ):
            raise HTTPException(422, "reply_recovery_review_required")
        with transaction(s, True, anonymous=True) as c:
            actor = authorize(
                c, s, request.state.authority, "settings.channels.write", recent=True
            )
            authorize(c, s, request.state.authority, "inbox.write")
            digest, prior = db.replay(
                c,
                s,
                actor["UserId"],
                str(body.operation_id),
                "reply.recover_missing",
                "",
                body.model_dump(mode="json"),
            )
            if prior:
                return prior
            candidates = {db.uid(str(v["MessageId"])): v for v in missing(c, s)}
            from app.institutional.whatsapp_gemini import schedule, source

            for selected in body.inputs:
                row = candidates.get(str(selected.id))
                if not row or proof(s, row) != selected.proof:
                    raise HTTPException(409, "reply_recovery_source_changed")
                data = {
                    "conversation": db.uid(str(row["ConversationId"])),
                    "identity": db.uid(str(row["IdentityId"])),
                    "incoming": str(selected.id),
                    "epoch": row["Epoch"],
                    "channel": row["Channel"],
                }
                item, _, _ = source(c, s, row["IntegrationId"], data)
                schedule(c, s, item, row, str(selected.id))
                if not c.execute(
                    "SELECT 1 FROM crm_channels2.ProviderOperation WHERE InstitutionId=? AND OperationId=? AND Status='pending'",
                    db.institution(s),
                    str(selected.id),
                ).fetchone():
                    raise HTTPException(409, "reply_recovery_not_scheduled")
            result = {
                "queued": len(body.inputs),
                "provider_calls": 0,
                "messages_resent": False,
            }
            db.record_operation(
                c,
                s,
                actor["UserId"],
                str(body.operation_id),
                "reply.recover_missing",
                "",
                digest,
                result,
            )
            db.audit(
                c, s, actor["UserId"], "reply.recover_missing", str(body.operation_id)
            )
            c.execute(
                "UPDATE crm_workspace.State SET Revision=Revision+1 WHERE StateId=1"
            )
            return result
