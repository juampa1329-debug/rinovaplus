"""P4 transport extension of the accepted P3 human workspace."""

import re
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import HTTPException

from app.institutional import db
from app.institutional.auth import authorize
from app.institutional.channel_operations import account, configuration
from app.institutional.channel_outbox import enqueue
from app.institutional.channel_provider import provider_account
from app.institutional.channel_text import sql_text
from app.institutional.policy import request_authority
from app.institutional.settings import setting
from app.institutional.workspace import Workspace as Parent
from app.modules.channels import providers


def social_avatar_url(value):
    if not isinstance(value, str) or len(value) > 2048:
        return ""
    try:
        uri = urlsplit(value)
    except ValueError:
        return ""
    if (
        uri.scheme == "https"
        and uri.netloc == uri.hostname
        and uri.hostname
        and uri.hostname.endswith((".fbcdn.net", ".cdninstagram.com", ".fbsbx.com"))
    ):
        return value
    return ""


class Workspace(Parent):
    operational_channels = True

    def social_profile(self, conversation):
        with self.transaction() as c:
            identity = db.one(
                c,
                "SELECT TOP(1) i.ExternalId,i.IntegrationId FROM crm_channels2.ExternalIdentity i "
                "JOIN crm_channels2.Integration a ON a.InstitutionId=i.InstitutionId "
                "AND a.IntegrationId=i.IntegrationId WHERE i.InstitutionId=? "
                "AND i.ConversationId=? AND a.Channel IN('facebook','messenger','instagram') "
                "AND a.VerifiedStatus='verified' ORDER BY i.LastIncomingAt DESC,i.IdentityId",
                db.institution(self.profile),
                conversation,
            )
            if not identity or not re.fullmatch(r"[0-9]{1,40}", identity["ExternalId"]):
                return {"profile": None}
            item = account(c, self.profile, str(identity["IntegrationId"]))
            try:
                adapter, _ = provider_account(c, self.profile, item)
            except HTTPException:
                return {"profile": None}
        channel, sender = item["Channel"], identity["ExternalId"]
        fields = {
            "messenger": "first_name,last_name,profile_pic",
            "facebook": "name,picture",
            "instagram": "name,username,profile_pic",
        }[channel]
        try:
            result = providers.request(adapter, "GET", sender, params={"fields": fields})
        except providers.ProviderFailure:
            return {"profile": None}
        name = result.get("name")
        if channel == "messenger":
            name = " ".join(
                result[field].strip()
                for field in ("first_name", "last_name")
                if isinstance(result.get(field), str) and result[field].strip()
            )
        photo = result.get("profile_pic")
        if channel == "facebook":
            picture = result.get("picture")
            data = picture.get("data") if isinstance(picture, dict) else None
            photo = data.get("url") if isinstance(data, dict) and not data.get("is_silhouette") else None
        username = result.get("username") if channel == "instagram" else None
        profile = {
            "name": sql_text(name.strip(), 100) if isinstance(name, str) else "",
            "username": sql_text(username.strip(), 100) if isinstance(username, str) else "",
            "avatarUrl": social_avatar_url(photo),
        }
        return {"profile": profile if any(profile.values()) else None}

    def apply(self, c, action, resource, body, actor):
        previous = self.exists(c, resource) if action in {"conversation", "control"} else None
        if action == "message":
            from app.institutional.channel_media import attach

            identity = db.one(
                c,
                (
                    "SELECT * FROM crm_channels2.ExternalId"
                    "entity WHERE InstitutionId=? AND Conve"
                    "rsationId=?"
                ),
                db.institution(self.profile),
                resource,
            )
            if identity:
                original = self.exists(c, resource)
                if (
                    original[1] == "closed"
                    or original[2] != "human"
                    or str(original[0]).lower() != str(identity["ContactId"]).lower()
                ):
                    raise HTTPException(409, "human_open_conversation_required")
                item = account(c, self.profile, str(identity["IntegrationId"]))
                current_actor = authorize(
                    c, self.profile, request_authority.get(), "inbox.write"
                )
                message = str(uuid4())
                c.execute(
                    (
                        "INSERT crm.Message(MessageId,Conversat"
                        "ionId,Body,Direction) VALUES(?,?,?,'ou"
                        "tgoing')"
                    ),
                    message,
                    resource,
                    body.body,
                )
                queue = enqueue(
                    c,
                    self.profile,
                    item,
                    current_actor,
                    str(body.operationId),
                    {
                        "body": body.body,
                        **({"mediaId": str(body.mediaId)} if body.mediaId else {}),
                    },
                    identity=str(identity["IdentityId"]).lower(),
                    message=message,
                )
                c.execute(
                    (
                        "INSERT crm_channels2.MessageRoute(Inst"
                        "itutionId,MessageId,IntegrationId,Iden"
                        "tityId,QueueId,ActorKind) VALUES(?,?,?"
                        ",?,?,'human')"
                    ),
                    db.institution(self.profile),
                    message,
                    item["IntegrationId"],
                    identity["IdentityId"],
                    queue,
                )
                if body.mediaId:
                    attach(
                        c,
                        self.profile,
                        str(body.mediaId),
                        resource,
                        message,
                        actor,
                        str(item["IntegrationId"]).lower(),
                    )
                c.execute(
                    (
                        "UPDATE crm.Conversation SET UpdatedAt="
                        "SYSUTCDATETIME() WHERE ConversationId="
                        "?"
                    ),
                    resource,
                )
                return {
                    "conversationId": resource,
                    "queueId": str(queue).lower(),
                    "deliveryState": "queued",
                }
            if body.mediaId:
                original = self.exists(c, resource)
                if (
                    original[1] == "closed"
                    or original[2] != "human"
                    or c.execute(
                        (
                            "SELECT 1 FROM crm_channels.ExternalIde"
                            "ntity WHERE ConversationId=?"
                        ),
                        resource,
                    ).fetchone()
                ):
                    raise HTTPException(409, "human_local_conversation_required")
                message = str(uuid4())
                c.execute(
                    (
                        "INSERT crm.Message(MessageId,Conversat"
                        "ionId,Body,Direction) VALUES(?,?,?,'ou"
                        "tgoing')"
                    ),
                    message,
                    resource,
                    body.body,
                )
                attach(c, self.profile, str(body.mediaId), resource, message, actor)
                c.execute(
                    (
                        "UPDATE crm.Conversation SET UpdatedAt="
                        "SYSUTCDATETIME() WHERE ConversationId="
                        "?"
                    ),
                    resource,
                )
                return {"conversationId": resource}
        result = super().apply(c, action, resource, body, actor)
        if previous and (
            previous[2] != body.mode
            or (action == "conversation" and previous[1] != "closed" and body.state == "closed")
        ):
            from app.institutional.agents_policy import VERSION as P5

            if self.profile.ticket.get("version") in {
                P5,
                "cbn-institutional-knowledge-p6-v1",
                "cbn-institutional-broadcast-p7-v1",
                "cbn-institutional-campaign-p8-v1", 'cbn-institutional-ads-p9-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
                from app.institutional.agents import invalidate

                invalidate(c, resource)
                if previous[2] == "human" and body.mode == "ai":
                    c.execute(
                        "UPDATE crm_agents.Assignment SET Mode='automatic',Revision=Revision+1,"
                        "Reason=? WHERE ConversationId=? AND Mode='human'",
                        "Se devolvió la atención a la IA desde el Inbox.",
                        resource,
                    )
            c.execute(
                (
                    "UPDATE ctrl SET Epoch=Epoch+1,UpdatedA"
                    "t=SYSUTCDATETIME() FROM crm_channels2."
                    "ConversationControl ctrl WHERE Institu"
                    "tionId=? AND ConversationId=?"
                ),
                db.institution(self.profile),
                resource,
            )
            c.execute(
                (
                    "UPDATE crm_channels2.SendJob SET State='cancelled',"
                    "LastErrorCode='human_control_changed',CompletedAt=SYSUTCDATETIME() "
                    "WHERE InstitutionId=? AND State='queued' AND QueueId IN("
                    "SELECT r.QueueId FROM crm_channels2.MessageRoute r "
                    "JOIN crm.Message m ON m.MessageId=r.MessageId "
                    "WHERE r.InstitutionId=? AND m.ConversationId=? AND r.ActorKind='human')"
                ),
                db.institution(self.profile),
                db.institution(self.profile),
                resource,
            )
        return result

    def detail(self, conversation):
        result = super().detail(conversation)
        result["mediaAvailable"] = True
        result["knowledgeOperations"] = self.profile.ticket.get("version") in {
            "cbn-institutional-knowledge-p6-v1",
            "cbn-institutional-broadcast-p7-v1",
            "cbn-institutional-campaign-p8-v1", 'cbn-institutional-ads-p9-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}
        with self.transaction() as c:
            from app.institutional.settings import setting

            result["agentOperations"] = self.profile.ticket.get("version") in {
                "cbn-institutional-agents-p5-v1",
                "cbn-institutional-knowledge-p6-v1",
                "cbn-institutional-broadcast-p7-v1",
                "cbn-institutional-campaign-p8-v1", 'cbn-institutional-ads-p9-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'} and setting(c, self.profile, "modules")["document"]["enabled"].get(
                "agents", False
            )
            links = db.rows(
                c,
                (
                    "SELECT i.IntegrationId,i.IdentityId,a."
                    "Channel,a.DisplayName,a.RequestedStatu"
                    "s,a.VerifiedStatus FROM crm_channels2."
                    "ExternalIdentity i JOIN crm_channels2."
                    "Integration a ON a.InstitutionId=i.Ins"
                    "titutionId AND a.IntegrationId=i.Integ"
                    "rationId WHERE i.InstitutionId=? AND i"
                    ".ConversationId=?"
                ),
                db.institution(self.profile),
                conversation,
            )
            result["channelAccounts"] = [
                {
                    "id": str(v["IntegrationId"]).lower(),
                    "identityId": str(v["IdentityId"]).lower(),
                    "channel": v["Channel"],
                    "name": v["DisplayName"],
                    "status": v["RequestedStatus"],
                    "verified": v["VerifiedStatus"],
                }
                for v in links
            ]
            result["inFlightOrUncertain"] += c.execute(
                (
                    "SELECT COUNT(*) FROM crm_channels2.Sen"
                    "dJob q JOIN crm.Message m ON m.Message"
                    "Id=q.MessageId WHERE q.InstitutionId=?"
                    " AND m.ConversationId=? AND q.State IN"
                    "('sending','uncertain')"
                ),
                db.institution(self.profile),
                conversation,
            ).fetchval()
        return result


    def messages(self, conversation, before=None):
        result = super().messages(conversation, before)
        with self.transaction() as c:
            if result["items"]:
                ids = [v["id"] for v in result["items"]]
                values = db.rows(
                    c,
                    (
                        "SELECT q.MessageId,q.QueueId,q.State,q.LastErrorCode,i.DisplayName,"
                        "(SELECT TOP(1) e.CreatedAt FROM crm_channels2.WebhookEvent e "
                        "WHERE q.State='read' AND e.InstitutionId=q.InstitutionId "
                        "AND e.IntegrationId=q.IntegrationId "
                        "AND e.ProviderEventId COLLATE Latin1_General_100_BIN2=q.ExternalId "
                        "AND e.Kind='status' AND e.Status='processed' "
                        "AND JSON_VALUE(e.Payload,'$.text')='read' "
                        "ORDER BY e.CreatedAt DESC,e.EventId) AS readReceiptAt FROM crm_"
                        "channels2.SendJob q JOIN crm_channels2"
                        ".Integration i ON i.InstitutionId=q.In"
                        "stitutionId AND i.IntegrationId=q.Inte"
                        "grationId JOIN crm.Message m ON m.Mess"
                        "ageId=q.MessageId WHERE q.InstitutionI"
                        "d=? AND m.ConversationId=? AND q.Messa"
                        "geId IN("
                    )
                    + ",".join("?" for _ in ids)
                    + ") AND q.State<>'retried'",
                    db.institution(self.profile),
                    conversation,
                    *ids,
                )
                by_id = {str(v["MessageId"]).lower(): v for v in values}
                paused = None
                if any(value["State"] == "queued" for value in values):
                    channel_config = configuration(c, self.profile)
                    outbound = channel_config["ModuleEnabled"] and channel_config["OutboundEnabled"]
                    budget = setting(c, self.profile, "budgets")["document"]["daily_messages"]
                    if not outbound:
                        paused = "outbound_paused" if budget else "outbound_setup_required"
                    elif not budget:
                        paused = "outbound_budget_disabled"
                for message in result["items"]:
                    value = by_id.get(message["id"])
                    if value:
                        message.update(
                            deliveryState=value["State"],
                            queueId=str(value["QueueId"]).lower(),
                            deliveryError=(paused if value["State"] == "queued" and paused else value["LastErrorCode"]),
                            channelAccount=value["DisplayName"],
                            readReceiptAt=db.utc(value["readReceiptAt"]),
                        )
                media = db.rows(
                    c,
                    (
                        "SELECT MediaId,MessageId,FileName,Kind"
                        ",State FROM crm_channels4.MediaAsset W"
                        "HERE InstitutionId=? AND ConversationI"
                        "d=? AND MessageId IS NOT NULL AND Stat"
                        "e<>'deleted'"
                    ),
                    db.institution(self.profile),
                    conversation,
                )
                for message in result["items"]:
                    message["attachments"] = [
                        {
                            "id": str(v["MediaId"]).lower(),
                            "name": v["FileName"],
                            "kind": v["Kind"],
                            "state": v["State"],
                        }
                        for v in media
                        if str(v["MessageId"]).lower() == message["id"]
                    ]
        return result
