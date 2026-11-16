"""Paged social comments, CAS state and idempotent CRM conversion per account."""

import json
from typing import Literal
from uuid import uuid4

from fastapi import HTTPException, Query, Request
from pydantic import Field

from app.institutional.auth import authorize
from app.institutional.channel_events import create_contact
from app.institutional.channel_operations import account, capabilities
from app.institutional.channel_outbox import enqueue
from app.institutional.channel_text import sql_text
from app.institutional.db import (
    audit,
    institution,
    one,
    record_operation,
    replay,
    rows,
    uid,
    utc,
)
from app.institutional.models import Strict
from app.institutional.store import transaction
from app.modules.inbox.application.service import pattern


class CommentAction(Strict):
    operation_id: str
    row_version: str = Field(pattern=r"^[0-9a-f]{16}$")
    action: Literal["read", "archive", "reopen", "convert", "reply", "takeover", "release"]
    body: str = Field(default="", max_length=4000)
    display_name: str = Field(default="", max_length=180)


def public_comment(value):
    state = json.loads(value["Payload"]).get("_crm", {})
    synthetic = bool(state.get("synthetic_demo"))
    return {
        "id": uid(str(value["CommentId"])),
        "integration_id": uid(str(value["IntegrationId"])),
        "channel": value["Channel"],
        "account": value["DisplayName"],
        "external_id": value["ExternalId"],
        "author": value["AuthorExternalId"],
        "body": value["Body"],
        "received_at": utc(value["ReceivedAt"]),
        "row_version": bytes(value["RowVersion"]).hex(),
        "state": state.get("state", "new"),
        "control_mode": state.get("control_mode", "ai"),
        "contact_id": state.get("contact_id"),
        "conversation_id": state.get("conversation_id"),
        "last_queue_id": state.get("last_queue_id"),
        "reply_state": value.get("ReplyState"),
        "liked": bool(state.get("liked", False)),
        "preview": state.get("preview"),
        "capabilities": {
            **capabilities(value),
            **(
                {"public_comment_reply": False, "comment_like": False}
                if synthetic
                else {}
            ),
        },
        "synthetic_demo": synthetic,
    }


class Comments:
    def __init__(self, settings):
        self.settings = settings

    def read(
        self, authority, *, integration="", channel="", state="all", q="", offset=0
    ):
        with transaction(self.settings, anonymous=True) as c:
            authorize(c, self.settings, authority, "inbox.read")
            where, params = ["s.InstitutionId=?"], [institution(self.settings)]
            if integration:
                where.append("s.IntegrationId=?")
                params.append(uid(integration))
            if channel:
                where.append("i.Channel=?")
                params.append(channel)
            if state != "all":
                where.append("ISNULL(JSON_VALUE(s.Payload,'$._crm.state'),'new')=?")
                params.append(state)
            if q:
                where.append("(s.Body LIKE ? OR s.AuthorExternalId LIKE ?)")
                params.extend([pattern(q), pattern(q)])
            query = (
                " FROM crm_channels2.SocialComment s JOIN crm_channels2.Integ"
                "ration i ON i.InstitutionId=s.InstitutionId AND i.Integratio"
                "nId=s.IntegrationId WHERE "
            ) + " AND ".join(where)
            total = c.execute("SELECT COUNT(*)" + query, *params).fetchval()
            values = rows(
                c,
                (
                    "SELECT s.*,i.Channel,i.DisplayName,i.RequestedStatus,i.Verif"
                    "iedStatus,(SELECT TOP(1) q.State FROM crm_channels2.SendJob "
                    "q WHERE q.InstitutionId=s.InstitutionId AND q.IntegrationId="
                    "s.IntegrationId AND q.CommentId=s.CommentId ORDER BY q.Creat"
                    "edAt DESC,q.QueueId) AS ReplyState"
                )
                + query
                + (
                    " ORDER BY s.ReceivedAt DESC,s.CommentId OFFSET ? ROWS FETCH "
                    "NEXT 25 ROWS ONLY"
                ),
                *params,
                offset,
            )
            return {
                "items": [public_comment(value) for value in values],
                "total": total,
                "has_more": offset + len(values) < total,
            }

    def action(self, authority, identity, body):
        with transaction(self.settings, True, anonymous=True) as c:
            actor = authorize(c, self.settings, authority, "inbox.write")
            identity = uid(identity)
            digest, prior = replay(
                c,
                self.settings,
                actor["UserId"],
                body.operation_id,
                "comments." + body.action,
                identity,
                body.model_dump(),
            )
            if prior:
                return prior
            value = one(
                c,
                (
                    "SELECT s.*,i.Channel,i.DisplayName,i.RequestedStatus,i.Verif"
                    "iedStatus FROM crm_channels2.SocialComment s JOIN crm_channe"
                    "ls2.Integration i ON i.InstitutionId=s.InstitutionId AND i.I"
                    "ntegrationId=s.IntegrationId WHERE s.InstitutionId=? AND s.C"
                    "ommentId=?"
                ),
                institution(self.settings),
                identity,
            )
            if not value:
                raise HTTPException(404, "comment_not_found")
            if bytes(value["RowVersion"]).hex() != body.row_version:
                raise HTTPException(409, "revision_conflict")
            payload = json.loads(value["Payload"])
            state = payload.setdefault("_crm", {})
            if state.get("state") == "deleted":
                raise HTTPException(409, "comment_deleted")
            item = account(c, self.settings, str(value["IntegrationId"]))
            result = {}
            if body.action == "convert":
                authorize(c, self.settings, authority, "crm.write")
                if self.settings.ticket.get(
                    "version"
                ) in {'cbn-institutional-ads-p9-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'} and not state.get("contact_id"):
                    from app.institutional.ads import Ads

                    linked = Ads(self.settings).comment_link(
                        c,
                        value["IntegrationId"],
                        value["ExternalId"],
                        value["AuthorExternalId"] or "",
                    )
                    if linked:
                        state.update(linked)

                if not state.get("contact_id"):
                    if not value["AuthorExternalId"]:
                        raise HTTPException(409, "comment_author_missing")
                    # A social author is a CRM lead, never an unverified DM recipient.
                    linked = one(
                        c,
                        (
                            "SELECT TOP(1) JSON_VALUE(Payload,'$._crm.conta"
                            "ct_id') AS ContactId,JSON_VALUE(Payload,'$._cr"
                            "m.conversation_id') AS ConversationId FROM crm"
                            "_channels2.SocialComment WHERE InstitutionId=?"
                            " AND IntegrationId=? AND AuthorExternalId=? AN"
                            "D JSON_VALUE(Payload,'$._crm.contact_id') IS N"
                            "OT NULL ORDER BY ReceivedAt,CommentId"
                        ),
                        institution(self.settings),
                        value["IntegrationId"],
                        value["AuthorExternalId"],
                    )
                    if linked:
                        if not c.execute(
                            (
                                "SELECT 1 FROM crm.Conversation WHERE Conve"
                                "rsationId=? AND ContactId=?"
                            ),
                            linked["ConversationId"],
                            linked["ContactId"],
                        ).fetchone():
                            raise HTTPException(409, "comment_crm_link_invalid")
                        contact, conversation = (
                            linked["ContactId"],
                            linked["ConversationId"],
                        )
                    else:
                        contact, conversation = create_contact(
                            c,
                            self.settings,
                            item,
                            body.display_name.strip() or value["AuthorExternalId"],
                        )
                    state.update(
                        contact_id=str(contact).lower(),
                        conversation_id=str(conversation).lower(),
                    )
                    c.execute(
                        (
                            "INSERT crm_workspace.Note(NoteId,ContactId,Ins"
                            "titutionId,AuthorId,Body) VALUES(?,?,?,?,?)"
                        ),
                        str(uuid4()),
                        contact,
                        institution(self.settings),
                        actor["UserId"],
                        sql_text(
                            "Comentario de "
                            + item["DisplayName"]
                            + ": "
                            + value["Body"],
                            2000,
                        ),
                    )
                result.update(
                    contact_id=state["contact_id"],
                    conversation_id=state["conversation_id"],
                )
            elif body.action == "reply":
                if (
                    not body.body.strip()
                    or not capabilities(item)["public_comment_reply"]
                ):
                    raise HTTPException(422, "public_comment_reply_unavailable")
                existing = c.execute(
                    (
                        "SELECT 1 FROM crm_channels2.SendJob WHERE InstitutionId=? AN"
                        "D CommentId=? AND State IN('queued','sending','uncertain')"
                    ),
                    institution(self.settings),
                    identity,
                ).fetchone()
                if existing:
                    raise HTTPException(409, "comment_reply_already_pending")
                queue = enqueue(
                    c,
                    self.settings,
                    item,
                    actor,
                    uid(body.operation_id),
                    {"body": body.body.strip()},
                    comment=identity,
                )
                state["last_queue_id"] = str(queue).lower()
                result["queue_id"] = state["last_queue_id"]
                result["reply_state"] = "queued"
            elif body.action in {"takeover", "release"}:
                state["control_mode"] = "human" if body.action == "takeover" else "ai"
                result["control_mode"] = state["control_mode"]
                if body.action == "takeover":
                    from app.institutional.comment_automation import ACTOR

                    inst = institution(self.settings)
                    c.execute(
                        "UPDATE crm_channels2.ProviderOperation SET Status='abandoned',"
                        "ResultCode='comment_auto_human_control',CompletedAt=SYSUTCDATETIME() "
                        "WHERE InstitutionId=? AND ActorRef=? AND Status='pending' AND OperationId IN ("
                        "SELECT OperationId FROM crm_channels2.SendJob WHERE InstitutionId=? "
                        "AND CommentId=? AND State='queued')",
                        inst, ACTOR, inst, identity,
                    )
                    c.execute(
                        "UPDATE crm_channels2.SendJob SET State='cancelled',"
                        "LastErrorCode='comment_auto_human_control',CompletedAt=SYSUTCDATETIME() "
                        "WHERE InstitutionId=? AND CommentId=? AND State='queued' AND OperationId IN ("
                        "SELECT OperationId FROM crm_channels2.ProviderOperation WHERE InstitutionId=? "
                        "AND ActorRef=?)",
                        inst, identity, inst, ACTOR,
                    )
            else:
                state["state"] = {
                    "read": "read",
                    "archive": "archived",
                    "reopen": "new",
                }[body.action]
            c.execute(
                (
                    "UPDATE crm_channels2.SocialComment SET Payload=? WHERE Insti"
                    "tutionId=? AND CommentId=? AND RowVersion=?"
                ),
                json.dumps(payload, ensure_ascii=False),
                institution(self.settings),
                identity,
                bytes.fromhex(body.row_version),
            )
            if c.rowcount != 1:
                raise HTTPException(409, "revision_conflict")
            c.execute(
                "UPDATE crm_workspace.State SET Revision=Revision+1 WHERE StateId=1"
            )
            result["saved"] = True
            record_operation(
                c,
                self.settings,
                actor["UserId"],
                body.operation_id,
                "comments." + body.action,
                identity,
                digest,
                result,
            )
            audit(
                c, self.settings, actor["UserId"], "comments." + body.action, identity
            )
            return result


def install(app, settings):
    service = Comments(settings)

    @app.get("/api/institution/comments")
    def comments(
        request: Request,
        integration: str = "",
        channel: Literal["", "facebook", "instagram", "tiktok"] = "",
        state: Literal["all", "new", "read", "archived", "deleted"] = "all",
        q: str = Query("", max_length=200),
        offset: int = Query(0, ge=0, le=10000),
    ):
        return service.read(
            request.state.authority,
            integration=integration,
            channel=channel,
            state=state,
            q=q,
            offset=offset,
        )

    @app.post("/api/institution/comments/{identity}")
    def action(request: Request, identity: str, body: CommentAction):
        return service.action(request.state.authority, identity, body)
