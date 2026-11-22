"""P4 transport extension of the accepted P3 human workspace."""

import json
import re
from datetime import timezone
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


def followup_evidence(c, institution, conversations):
    placeholders = ",".join("?" for _ in conversations)
    items = db.rows(
        c,
        "SELECT v.ConversationId,evidence.IncomingAt,evidence.ReplyAt,SYSUTCDATETIME() AS AsOfUtc "
        "FROM crm.Conversation v OUTER APPLY("
        "SELECT TOP(1) m.CreatedAt AS IncomingAt,"
        "(SELECT TOP(1) q.CompletedAt FROM crm_channels2.SendJob q "
        "JOIN crm.Message reply ON reply.MessageId=q.MessageId "
        "WHERE q.InstitutionId=r.InstitutionId AND q.IntegrationId=r.IntegrationId "
        "AND q.IdentityId=r.IdentityId AND q.ExternalId IS NOT NULL "
        "AND q.State IN('sent','delivered','read') AND reply.Direction='outgoing' "
        "AND q.CompletedAt IS NOT NULL AND reply.ConversationId=m.ConversationId "
        "AND reply.Sequence>m.Sequence ORDER BY reply.Sequence DESC) AS ReplyAt "
        "FROM crm.Message m JOIN crm_channels2.MessageRoute r ON r.MessageId=m.MessageId "
        "JOIN crm_channels2.ExternalMessage x ON x.InstitutionId=r.InstitutionId "
        "AND x.IntegrationId=r.IntegrationId AND x.MessageId=r.MessageId "
        "WHERE r.InstitutionId=? AND m.ConversationId=v.ConversationId AND m.Direction='incoming' "
        "AND r.ActorKind='external' ORDER BY m.Sequence DESC) evidence "
        f"WHERE v.ConversationId IN ({placeholders}) AND evidence.IncomingAt IS NOT NULL",
        institution,
        *conversations,
    )
    return {str(item["ConversationId"]).lower(): item for item in items}


def followup_risk(evidence, risk):
    """Read-only fallback for a routed chat without a current assessment."""
    if not evidence:
        return risk
    at = evidence["AsOfUtc"].replace(tzinfo=timezone.utc)
    incoming = evidence["IncomingAt"].replace(tzinfo=timezone.utc)
    if not evidence["ReplyAt"]:
        return dict(
            risk, reasons=["Hay un mensaje entrante sin respuesta confirmada por el canal."],
            nextAction="Revisa el último mensaje y responde al contacto.",
        )
    reply = evidence["ReplyAt"].replace(tzinfo=timezone.utc)
    hours = max(0, (at - max(incoming, reply)).total_seconds() / 3600)
    score = 75 if hours >= 168 else 50 if hours >= 72 else 25 if hours >= 24 else 10
    level = "high" if score >= 70 else "medium" if score >= 40 else "low"
    return dict(
        risk,
        status="known", level=level, score=score, source="channel_activity",
        asOf=db.utc(at), fresh=True,
        reasons=[
            "El canal confirmó una respuesta después del último mensaje del contacto.",
            "El puntaje aumenta después de 24 horas, 72 horas y 7 días desde la última respuesta confirmada.",
        ],
        nextAction=(
            "Revisa el historial y prioriza el seguimiento."
            if level == "high" else "Revisa el siguiente paso acordado con el contacto."
        ),
    )


class Workspace(Parent):
    operational_channels = True

    def conversation_risk(self, c, contact, conversation):
        current = super().conversation_risk(c, contact, conversation)
        if current["status"] == "not_applicable":
            return current
        from app.institutional.sales_memory import read as sales_read, risk as sales_risk
        document, _ = sales_read(c, self.profile, conversation)
        sequence = c.execute("SELECT COALESCE(MAX(Sequence),0) FROM crm.Message WHERE ConversationId=? AND Direction='incoming'", conversation).fetchval()
        commercial = sales_risk(document, sequence)
        if commercial and (current.get("score") is None or commercial["score"] >= current["score"]):
            return {**current, **commercial}
        if current["status"] != "unknown":
            return current
        key = str(conversation).lower()
        evidence = followup_evidence(c, db.institution(self.profile), [key])
        return followup_risk(evidence.get(key), current)

    def populate_inbox_risk(self, c, items):
        super().populate_inbox_risk(c, items)
        from app.institutional.sales_memory import risks as sales_risks
        commercial = sales_risks(c, self.profile, [str(row["conversationId"]) for row in items if row.get("conversationId")])
        for row in items:
            found = commercial.get(str(row.get("conversationId", "")).lower())
            if found and row["risk"]["status"] != "not_applicable" and (row["risk"].get("score") is None or found["score"] >= row["risk"]["score"]):
                row["risk"] = {**row["risk"], **found}
        candidates = {
            str(row["conversationId"]).lower(): row
            for row in items if row["risk"]["status"] == "unknown" and row["channel"] != "local"
        }
        if candidates:
            evidence = followup_evidence(c, db.institution(self.profile), list(candidates))
            for key, row in candidates.items():
                row["risk"] = followup_risk(evidence.get(key), row["risk"])

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
            if channel != "messenger":
                return {"profile": None}
            try:
                threads = providers.request(
                    adapter, "GET", item["ExternalAccountId"] + "/conversations",
                    params={"fields": "participants", "user_id": sender, "limit": 1},
                )
            except providers.ProviderFailure:
                return {"profile": None}
            result = next((
                person for thread in threads.get("data", [])[:1]
                for person in (thread.get("participants") or {}).get("data", [])[:20]
                if str(person.get("id")) == sender
            ), {})
        name = result.get("name")
        if channel == "messenger":
            name = " ".join(
                result[field].strip()
                for field in ("first_name", "last_name")
                if isinstance(result.get(field), str) and result[field].strip()
            ) or name
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
                        "quoted.MessageId AS ReplyId,quoted.Body AS ReplyBody,quoted.Direction AS ReplyDirection,"
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
                        "ageId=q.MessageId LEFT JOIN crm.Message quoted ON "
                        "quoted.MessageId=TRY_CONVERT(uniqueidentifier,JSON_VALUE(q.Payload,'$.replyToInternalId')) "
                        "AND quoted.ConversationId=m.ConversationId WHERE q.InstitutionI"
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
                        if value.get("ReplyId"):
                            message["replyTo"] = {
                                "id": str(value["ReplyId"]).lower(),
                                "body": value["ReplyBody"][:600],
                                "direction": value["ReplyDirection"],
                            }
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
                from app.institutional.social_messages import presentation
                sources = db.rows(c, "SELECT x.MessageId,e.Payload FROM crm_channels2.ExternalMessage x "
                    "JOIN crm_channels2.WebhookEvent e ON e.InstitutionId=x.InstitutionId "
                    "AND e.IntegrationId=x.IntegrationId AND e.ProviderEventId=x.ExternalId "
                    "WHERE x.InstitutionId=? AND x.MessageId IN(" + ",".join("?" for _ in ids) + ") AND e.Kind='message'", db.institution(self.profile), *ids)
                social = {str(v["MessageId"]).lower(): presentation(json.loads(v["Payload"]).get("provider", {})) for v in sources}
                for message in result["items"]:
                    if social.get(message["id"]):
                        message["socialSource"] = social[message["id"]]
                        if message["body"] == "[multimedia]":
                            message["body"] = social[message["id"]]["label"]
        return result
