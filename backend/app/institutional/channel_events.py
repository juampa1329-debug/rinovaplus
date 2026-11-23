"""Pure provider normalization and transactional C10-to-CRM projections."""

import hashlib
import json
import math
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException

from app.institutional import postgres_queue
from app.institutional.channel_ingress import body_owner, strict_json
from app.institutional.channel_operations import configuration
from app.institutional.channel_text import sql_text
from app.institutional.crypto import canonical, unseal
from app.institutional.db import institution, key, one, rows
from app.institutional.store import transaction
from app.modules.channels.providers import whatsapp_user_id
from app.modules.crm_configuration.application.service import (
    read_configuration,
    validate_contact,
)
from app.modules.inbox.application.state import control
from app.sql_workspace import Contact
from app.institutional.sales_referrals import sanitize as sanitize_referral
from app.institutional.social_messages import text as social_text


def valid_external(value):
    return (
        isinstance(value, str)
        and 0 < len(value) <= 200
        and all(33 <= ord(char) <= 126 for char in value)
    )


def replyable_message(channel, provider):
    """Schedule inspected audio as well as text; the worker waits for download.

    This only queues Gemini input. ElevenLabs output still obeys its own pilot,
    conversation quota and human-control guards.
    """
    if channel == "whatsapp":
        if provider.get("type") == "text":
            return True
        audio = provider.get("audio")
        return provider.get("type") == "audio" and isinstance(audio, dict) and valid_external(audio.get("id"))
    text = (provider.get("message") or {}).get("text")
    return channel in {"messenger", "instagram"} and isinstance(text, str) and bool(text.strip())


def bounded_provider(value, depth=0):
    allowed = {
        "id",
        "timestamp",
        "created_time", "comment_surface",
        "is_echo", "app_id",
        "text",
        "body",
        "type",
        "from",
        "to",
        "image",
        "audio",
        "sticker",
        "document",
        "video",
        "button",
        "caption",
        "filename",
        "mime_type",
        "sha256",
        "animated",
        "voice",
        "url",
        "message",
        "reply_to", "story", "is_unsupported",
        "attachments",
        "payload",
        "sender",
        "recipient",
        "status",
        "video_id",
        "media_id",
        "comment_id",
        "parent_id",
        "parent_comment_id",
        "reply_to_comment_id",
        "self_ig_scoped_id",
        "post_id",
        "verb",
        "unique_identifier",
        "conversation_id",
        "comment_action",
        "mid",
        "username",
        "name",
        "media",
        "context",
        "referral", "source_id", "source_type", "source_url", "headline", "ctwa_clid",
    }
    if depth > 5:
        return None
    if isinstance(value, str):
        return sql_text(value, 8192)
    if type(value) is float and not math.isfinite(value):
        return None
    if value is None or type(value) in {bool, int, float}:
        return value
    if isinstance(value, list):
        return [bounded_provider(v, depth + 1) for v in value[:20]]
    if isinstance(value, dict):
        return {
            k: bounded_provider(v, depth + 1) for k, v in value.items() if k in allowed
        }
    return None


def event(channel, route, kind, external, author, text, payload):
    # Provider-controlled _crm fields never enter operational state.
    return {
        "channel": channel,
        "route": sql_text(route, 200),
        "kind": kind,
        "external": sql_text(external, 200),
        "author": author if valid_external(author) else "",
        "valid_source_ids": valid_external(route) and valid_external(external),
        "text": sql_text(text, 4000),
        "provider": bounded_provider(payload),
        "normalizer_version": 1,
    }


def whatsapp_profile_names(value, *, identifiers=False):
    contacts = value.get("contacts")
    if not isinstance(contacts, list):
        return {}
    names = {}
    for contact in contacts[:100]:
        if not isinstance(contact, dict):
            continue
        keys = [contact["wa_id"]] if valid_external(contact.get("wa_id")) else []
        if identifiers and whatsapp_user_id(contact.get("user_id")):
            keys.append(contact["user_id"])
        profile = contact.get("profile")
        if not isinstance(profile, dict):
            continue
        for field in ("name", "username"):
            text = profile.get(field)
            if isinstance(text, str) and text.strip():
                names.update((key, sql_text(" ".join(text.split()), 100)) for key in keys)
                break
    return names


def normalize(provider, payload, *, whatsapp_names=True, whatsapp_identifiers=True):
    if provider == "tiktok":
        content = payload.get("content") or {}
        content = strict_json(content) if isinstance(content, str) else content
        if not isinstance(content, dict):
            return []
        name = payload.get("event")
        route = str(payload.get("user_openid", ""))
        if name == "comment.update":
            return [
                event(
                    "tiktok",
                    route,
                    "comment_deleted"
                    if content.get("comment_action") in {"delete", "remove"}
                    else "comment",
                    content.get("comment_id", ""),
                    content.get("unique_identifier", ""),
                    content.get("text", ""),
                    content,
                )
            ]
        if name in {"im_receive_msg", "im_receive_msg_eu"}:
            return [
                event(
                    "tiktok",
                    route,
                    "message",
                    content.get("message_id", ""),
                    content.get("conversation_id", ""),
                    (content.get("text") or {}).get("body", "[multimedia]"),
                    {**content, "timestamp": payload.get("create_time")},
                )
            ]
        if name in {"im_send_msg", "im_mark_read_msg"}:
            return [
                event(
                    "tiktok",
                    route,
                    "status",
                    content.get("message_id", ""),
                    "",
                    "sent" if name == "im_send_msg" else "read",
                    content,
                )
            ]
        return []
    effects = []
    for entry in payload.get("entry", [])[:100]:
        route = str(entry.get("id", ""))
        for change in entry.get("changes", [])[:100]:
            value = change.get("value") or {}
            field = change.get("field")
            if field == "messages" and value.get("messaging_product") == "whatsapp":
                phone = str((value.get("metadata") or {}).get("phone_number_id", ""))
                names = whatsapp_profile_names(value, identifiers=whatsapp_identifiers) if whatsapp_names else {}
                for message in value.get("messages", [])[:100]:
                    sender = message.get("from", "")
                    user_id = message.get("from_user_id")
                    use_user_id = whatsapp_identifiers and whatsapp_user_id(user_id)
                    text = (
                        (message.get("text") or {}).get("body")
                        or (message.get("button") or {}).get("text")
                        or "[" + str(message.get("type", "multimedia")) + "]"
                    )
                    effect = event(
                        "whatsapp", phone, "message", message.get("id", ""),
                        sender if valid_external(sender) or not use_user_id else user_id,
                        text, message,
                    )
                    if name := names.get(effect["author"]) or (names.get(user_id) if use_user_id else None):
                        effect.update(contact_name=name, normalizer_version=2)
                    if use_user_id:
                        effect.update(whatsapp_user_id=user_id, normalizer_version=3)
                    effects.append(effect)
                for status in value.get("statuses", [])[:100]:
                    effect = event(
                        "whatsapp",
                        phone,
                        "status",
                        status.get("id", ""),
                        "",
                        status.get("status", ""),
                        status,
                    )
                    if effect["text"] == "failed":
                        from app.modules.channels.providers import whatsapp_delivery_error

                        errors = status.get("errors")
                        if isinstance(errors, list):
                            effect["failure"] = next(
                                (code for error in errors[:10]
                                 if (code := whatsapp_delivery_error(error))),
                                None,
                            )
                    effects.append(effect)
            elif field in {"comments", "live_comments"}:
                effects.append(
                    event(
                        "instagram",
                        route,
                        "comment_deleted"
                        if value.get("verb") in {"remove", "delete"}
                        else "comment",
                        value.get("id", ""),
                        (value.get("from") or {}).get("id", ""),
                        value.get("text", ""),
                        {**value, "comment_surface": field},
                    )
                )
            elif field == "feed" and value.get("item") == "comment":
                effects.append(
                    event(
                        "facebook",
                        route,
                        "comment_deleted"
                        if value.get("verb") in {"remove", "delete"}
                        else "comment",
                        value.get("comment_id", ""),
                        (value.get("from") or {}).get("id", ""),
                        value.get("message", ""),
                        value,
                    )
                )
        messaging = list(entry.get("messaging", [])[:100])
        if payload.get("object") == "instagram":
            for change in entry.get("changes", [])[:100]:
                value = change.get("value") or {}
                if (
                    change.get("field") in {"messages", "messaging_seen"}
                    and isinstance(value, dict)
                    and ("message" in value or "read" in value)
                ):
                    messaging.append(value)
        for value in messaging[:200]:
            channel = (
                "instagram" if payload.get("object") == "instagram" else "messenger"
            )
            message = value.get("message") or {}
            if message:
                effects.append(
                    event(
                        channel,
                        route,
                        "message_echo" if message.get("is_echo") else "message",
                        message.get("mid", ""),
                        (value.get("recipient" if message.get("is_echo") else "sender") or {}).get("id", ""),
                        social_text(message),
                        value,
                    )
                )
            for external in (value.get("delivery") or {}).get("mids", [])[:100]:
                effects.append(
                    event(channel, route, "status", external, "", "delivered", value)
                )
            if (value.get("read") or {}).get("mid"):
                effects.append(
                    event(
                        channel,
                        route,
                        "status",
                        value["read"]["mid"],
                        "",
                        "read",
                        value,
                    )
                )
    if len(effects) > 1000:
        raise ValueError("webhook_event_limit")
    return effects


def stage(c, item):
    config, _ = read_configuration(c, foundation=True)
    selected = next(
        (s for s in config.stages if s.key == item["InitialStageKey"] and s.active),
        None,
    )
    # Routing authorizes the stage key. Unrelated CRM configuration edits
    # must not stop first contact while that stage remains active.
    if not selected or not item["InitialStageConfigHash"]:
        raise HTTPException(409, "initial_stage_review_required")
    return selected.label


def create_contact(c, settings, item, name, *, phone="", control_mode="human"):
    contact, conversation = str(uuid4()), str(uuid4())
    label = stage(c, item)
    value = Contact(
        id=contact,
        name=sql_text(name, 180),
        phone=phone[:60],
        city="",
        programId=None,
        program="",
        schedule="",
        stage=label,
        tags="",
        notes="",
        type="",
        interests="",
        customValues={},
    )
    validate_contact(c, value, foundation=True)
    c.execute(
        (
            "INSERT crm.Contact(ContactId,Name,Phon"
            "e,City,ProgramId,Program,Schedule,Stag"
            "e,Tags,Notes,Type,Interests,CustomValu"
            "es) VALUES(?,?,?,'',NULL,'','',?,'',''"
            ",'','','{}')"
        ),
        contact,
        value.name,
        value.phone,
        label,
    )
    c.execute(
        (
            "INSERT crm.Conversation(ConversationId"
            ",ContactId,State,Priority,ControlMode,"
            "Unread) VALUES(?,?,'open','normal',?,0)"
        ),
        conversation,
        contact,
        control_mode,
    )
    control(c, conversation)
    return contact, conversation


def incoming(c, settings, item, effect):
    if not valid_external(effect["author"]):
        raise HTTPException(422, "provider_author_missing")
    inst, integration = institution(settings), item["IntegrationId"]
    if c.execute(
        (
            "SELECT 1 FROM crm_channels2.ExternalMe"
            "ssage WHERE InstitutionId=? AND Integr"
            "ationId=? AND ExternalId=?"
        ),
        inst,
        integration,
        effect["external"],
    ).fetchone():
        return
    linked = one(
        c,
        (
            "SELECT * FROM crm_channels2.ExternalId"
            "entity WHERE InstitutionId=? AND Integ"
            "rationId=? AND ExternalId=?"
        ),
        inst,
        integration,
        effect["author"],
    )
    user_id = effect.get("whatsapp_user_id")
    author = effect["author"]
    phone = author if item["Channel"] == "whatsapp" and author.isascii() and author.isdigit() else ""
    if user_id:
        aliases = rows(
            c,
            "SELECT TOP(2) i.* FROM crm_channels2.ExternalIdentity i "
            "WHERE i.InstitutionId=? AND i.IntegrationId=? AND "
            "(i.ExternalId IN(?,?) OR EXISTS(SELECT 1 FROM crm_channels2.MessageRoute r "
            "JOIN crm_channels2.ExternalMessage x ON x.InstitutionId=r.InstitutionId "
            "AND x.IntegrationId=r.IntegrationId AND x.MessageId=r.MessageId "
            "WHERE r.InstitutionId=i.InstitutionId AND r.IntegrationId=i.IntegrationId "
            "AND r.IdentityId=i.IdentityId AND "
            "(JSON_VALUE(x.Payload,'$.whatsappUserId')=? "
            "OR JSON_VALUE(x.Payload,'$.whatsappPhone')=?)))",
            inst, integration, author, user_id, user_id, phone or None,
        )
        if len(aliases) > 1:
            raise HTTPException(409, "provider_whatsapp_identity_conflict")
        if aliases:
            linked = aliases[0]
    first_contact = linked is None
    contact_name = effect.get("contact_name") if item["Channel"] == "whatsapp" else None
    if first_contact:
        contact, conversation = create_contact(
            c,
            settings,
            item,
            contact_name or effect["author"],
            phone=phone,
            control_mode="ai",
        )
        linked = {
            "IdentityId": str(uuid4()),
            "ContactId": contact,
            "ConversationId": conversation,
        }
        c.execute(
            (
                "INSERT crm_channels2.ExternalIdentity("
                "InstitutionId,IdentityId,IntegrationId"
                ",ExternalId,ContactId,ConversationId,C"
                "reatedAt) VALUES(?,?,?,?,?,?,SYSUTCDAT"
                "ETIME())"
            ),
            inst,
            linked["IdentityId"],
            integration,
            effect["author"],
            contact,
            conversation,
        )
    valid = c.execute(
        ("SELECT 1 FROM crm.Conversation WHERE ConversationId=? AND ContactId=?"),
        linked["ConversationId"],
        linked["ContactId"],
    ).fetchone()
    if not valid:
        raise HTTPException(409, "identity_conversation_mismatch")
    if contact_name and not first_contact:
        c.execute(
            "UPDATE crm.Contact SET Name=?,UpdatedAt=SYSUTCDATETIME() WHERE ContactId=? "
            "AND (Name='' OR Name=?)",
            contact_name, linked["ContactId"], linked["ExternalId"],
        )
    raw_time = effect["provider"].get("timestamp")
    try:
        seconds = float(raw_time)
        if item["Channel"] in {"messenger", "instagram"}:
            seconds /= 1000
        if seconds < 0 or seconds > datetime.now(timezone.utc).timestamp() + 300:
            raise ValueError()
        observed = datetime.fromtimestamp(seconds, timezone.utc).replace(tzinfo=None)
    except (ValueError, TypeError, OSError, OverflowError):
        raise HTTPException(422, "provider_timestamp_invalid") from None
    message = str(uuid4())
    from app.institutional.comment_private import incoming_source
    comment_source = incoming_source(c, settings, item, effect["author"])
    c.execute(
        (
            "INSERT crm.Message(MessageId,Conversat"
            "ionId,Body,Direction,CreatedAt) VALUES"
            "(?,?,?,'incoming',?)"
        ),
        message,
        linked["ConversationId"],
        effect["text"] or "[evento]",
        observed,
    )
    c.execute(
        (
            "INSERT crm_channels2.ExternalMessage(I"
            "nstitutionId,ExternalMessageId,Integra"
            "tionId,ExternalId,MessageId,Payload,Cr"
            "eatedAt) VALUES(?,?,?,?,?,?,SYSUTCD"
            "ATETIME())"
        ),
        inst,
        str(uuid4()),
        integration,
        effect["external"],
        message,
        json.dumps({**({"whatsappUserId": user_id, "whatsappPhone": phone or None} if user_id else {}),
                    **({"comment_source": comment_source} if comment_source else {}),
                    **({"referral": referral} if item["Channel"] == "whatsapp" and (referral := sanitize_referral(effect["provider"].get("referral"))) else {})}),
    )
    c.execute(
        (
            "INSERT crm_channels2.MessageRoute(Inst"
            "itutionId,MessageId,IntegrationId,Iden"
            "tityId,ActorKind,CompletedAt) VALUES(?"
            ",?,?,?,'external',SYSUTCDATETIME())"
        ),
        inst,
        message,
        integration,
        linked["IdentityId"],
    )
    c.execute(
        (
            "UPDATE crm_channels2.ExternalIdentity "
            "SET LastIncomingAt=CASE WHEN LastIncom"
            "ingAt IS NULL OR LastIncomingAt<? THEN"
            " ? ELSE LastIncomingAt END WHERE Insti"
            "tutionId=? AND IdentityId=?"
        ),
        observed,
        observed,
        inst,
        linked["IdentityId"],
    )
    c.execute(
        (
            "UPDATE crm.Conversation SET Unread=1,U"
            "pdatedAt=SYSUTCDATETIME() WHERE Conver"
            "sationId=?"
        ),
        linked["ConversationId"],
    )
    from app.institutional.channel_media import register_incoming

    register_incoming(c, settings, item, effect, linked, message)
    if replyable_message(item["Channel"], effect["provider"]):
        from app.institutional.whatsapp_gemini import schedule

        schedule(c, settings, item, linked, message)
    if settings.ticket.get("version") in {'cbn-institutional-ads-p9-v1', 'cbn-institutional-campaign-p8-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
        from app.institutional.campaign_runtime import observe_identity

        observe_identity(
            c,
            settings,
            str(linked["IdentityId"]).lower(),
            incoming=True,
            incoming_text=effect.get("text", ""),
            incoming_id=message,
        )


def delivery(previous, incoming):
    order = {
        "queued": 0,
        "sending": 1,
        "uncertain": 1,
        "accepted": 2,
        "sent": 3,
        "delivered": 4,
        "read": 5,
    }
    if incoming == "failed":
        return previous if previous in {"delivered", "read"} else "failed"
    return (
        incoming
        if incoming in order and order[incoming] > order.get(previous, 0)
        else previous
    )


def project(c, settings, item, effect):
    inst = institution(settings)
    if effect["kind"] == "message_echo":
        from app.institutional.meta_history import echo
        echo(c, settings, item, effect)
    elif effect["kind"] == "message":
        incoming(c, settings, item, effect)
    elif effect["kind"].startswith("comment"):
        comment = one(
            c,
            (
                "SELECT * FROM crm_channels2.SocialComm"
                "ent WHERE InstitutionId=? AND Integrat"
                "ionId=? AND ExternalId=?"
            ),
            inst,
            item["IntegrationId"],
            effect["external"],
        )
        previous = json.loads(comment["Payload"]) if comment else {}
        state = previous.get("_crm", {})
        provider = {**previous.get("provider", {}), **effect["provider"]}
        own_ids = {str(item.get("ExternalAccountId") or ""), str(effect.get("route") or ""), str(provider.get("self_ig_scoped_id") or "")} - {""}
        author = effect.get("author") or (comment.get("AuthorExternalId") if comment else "")
        state["is_self"] = bool(state.get("is_self") or author and str(author) in own_ids)
        if effect["kind"] == "comment_deleted":
            state["state"] = "deleted"
        else:
            state.setdefault("state", "new")
        value = json.dumps(
            {"provider": provider, "_crm": state}, ensure_ascii=False
        )
        if comment:
            c.execute(
                (
                    "UPDATE crm_channels2.SocialComment SET"
                    " Body=?,Payload=? WHERE InstitutionId="
                    "? AND CommentId=?"
                ),
                effect["text"],
                value,
                inst,
                comment["CommentId"],
            )
        else:
            if not valid_external(effect["author"]):
                raise HTTPException(422, "provider_author_missing")
            comment_id = str(uuid4())
            c.execute(
                (
                    "INSERT crm_channels2.SocialComment(Ins"
                    "titutionId,CommentId,IntegrationId,Ext"
                    "ernalId,AuthorExternalId,Body,Payload,"
                    "ReceivedAt) VALUES(?,?,?,?,?,?,?,SYSUT"
                    "CDATETIME())"
                ),
                inst,
                comment_id,
                item["IntegrationId"],
                effect["external"],
                effect["author"] or None,
                effect["text"],
                value,
            )
            from app.institutional.comment_automation import schedule

            schedule(c, settings, item, effect, comment_id)
        if state["state"] == "deleted":
            c.execute(
                (
                    "UPDATE q SET State='cancelled',LastErr"
                    "orCode='comment_deleted',CompletedAt=S"
                    "YSUTCDATETIME() FROM crm_channels2.Sen"
                    "dJob q JOIN crm_channels2.SocialCommen"
                    "t s ON s.InstitutionId=q.InstitutionId"
                    " AND s.CommentId=q.CommentId AND s.Int"
                    "egrationId=q.IntegrationId WHERE s.Ins"
                    "titutionId=? AND s.IntegrationId=? AND"
                    " s.ExternalId=? AND q.State='queued'"
                ),
                inst,
                item["IntegrationId"],
                effect["external"],
            )
    elif effect["kind"] == "status":
        jobs = rows(
            c,
            (
                "SELECT QueueId,State FROM crm_channels"
                "2.SendJob WHERE InstitutionId=? AND In"
                "tegrationId=? AND ExternalId=?"
            ),
            inst,
            item["IntegrationId"],
            effect["external"],
        )
        for job in jobs:
            state = delivery(job["State"], effect["text"])
            reason = None
            if state == "failed" and effect["text"] == "failed":
                reason = effect.get("failure")
                if not reason and job["State"] != "failed":
                    reason = "provider_delivery_failed"
            c.execute(
                (
                    "UPDATE crm_channels2.SendJob SET State"
                    "=?,LastErrorCode=COALESCE(?,LastErrorCode)"
                    " WHERE InstitutionId=? AND QueueId=?"
                ),
                state,
                reason,
                inst,
                job["QueueId"],
            )
            if item["Channel"] == "whatsapp" and effect["text"] in {
                "sent", "delivered", "read",
            }:
                from app.institutional.broadcast_followup import observe

                observe(c, settings, job["QueueId"], effect["text"])
        if not jobs and item["Channel"] == "messenger" and getattr(settings, "postgres_deployment", False):
            jobs = rows(c, "SELECT q.QueueId,q.State FROM crm_channels2.SendJob q JOIN crm_channels2.Integration i ON i.InstitutionId=q.InstitutionId AND i.IntegrationId=q.IntegrationId "
                        "WHERE q.InstitutionId=? AND i.ApplicationId=? AND i.ExternalAccountId=? AND i.Channel='facebook' AND JSON_VALUE(q.Payload,'$.privateReply')='true' AND q.ExternalId=?",
                        inst, item["ApplicationId"], item["ExternalAccountId"], effect["external"])
            for job in jobs:
                state = delivery(job["State"], effect["text"])
                c.execute("UPDATE crm_channels2.SendJob SET State=? WHERE InstitutionId=? AND QueueId=?", state, inst, job["QueueId"])
        if not jobs and settings.ticket.get("version") in {
            "cbn-institutional-broadcast-p7-v1",
            "cbn-institutional-campaign-p8-v1", 'cbn-institutional-ads-p9-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
            raise HTTPException(409, "delivery_unmatched")


class EventWorker:
    def __init__(self, settings):
        self.settings = settings

    def once(self):
        with transaction(self.settings, True, anonymous=True) as c:
            inst = institution(self.settings)
            receipt = postgres_queue.receipt(c, inst) if getattr(self.settings, "postgres_profile", False) else one(
                c,
                (
                    "SELECT TOP(1) r.*,e.Provider FROM crm_"
                    "channels2.WebhookReceipt r JOIN crm_ch"
                    "annels2.WebhookEndpoint e ON e.Institu"
                    "tionId=r.InstitutionId AND e.EndpointI"
                    "d=r.EndpointId WHERE r.InstitutionId=?"
                    " AND r.Status='queued' AND r.Authentic"
                    "ation='verified' ORDER BY r.ReceivedAt"
                    ",r.ReceiptId"
                ),
                inst,
            )
            if not receipt:
                return False
            raw = unseal(
                key(self.settings),
                body_owner(self.settings, receipt["ReceiptId"], receipt["EndpointId"]),
                receipt["BodyNonce"],
                receipt["BodyCiphertext"],
            )
            try:
                effects = normalize(receipt["Provider"], strict_json(raw))
            except (ValueError, TypeError, AttributeError, KeyError, RecursionError):
                c.execute(
                    (
                        "UPDATE crm_channels2.WebhookReceipt SE"
                        "T Status='quarantined',LastErrorCode='"
                        "normalization_rejected' WHERE Institut"
                        "ionId=? AND ReceiptId=?"
                    ),
                    institution(self.settings),
                    receipt["ReceiptId"],
                )
                return True
            quarantined = not effects
            for index, effect in enumerate(effects):
                valid = (
                    effect["valid_source_ids"]
                    and valid_external(effect["external"])
                    and valid_external(effect["route"])
                )
                route_kind = "configured_" + effect["channel"]
                item = (
                    one(
                        c,
                        (
                            "SELECT i.* FROM crm_channels2.Endpoint"
                            "Integration r JOIN crm_channels2.Integ"
                            "ration i ON i.InstitutionId=r.Institut"
                            "ionId AND i.IntegrationId=r.Integratio"
                            "nId AND i.ApplicationId=r.ApplicationI"
                            "d WHERE r.InstitutionId=? AND r.Endpoi"
                            "ntId=? AND r.ApplicationId=? AND r.Rou"
                            "teKind=? AND r.ExternalId=? AND r.IsAc"
                            "tive=1"
                        ),
                        institution(self.settings),
                        receipt["EndpointId"],
                        receipt["ApplicationId"],
                        route_kind,
                        effect["route"],
                    )
                    if valid
                    else None
                )
                digest = hashlib.sha256(
                    canonical(
                        {
                            k: effect[k]
                            for k in [
                                "channel",
                                "route",
                                "kind",
                                "external",
                                "provider",
                            ]
                        }
                    )
                ).digest()
                if (
                    item
                    and c.execute(
                        (
                            "SELECT 1 FROM crm_channels2.WebhookEve"
                            "nt WHERE InstitutionId=? AND Integrati"
                            "onId=? AND DedupeKey=?"
                        ),
                        institution(self.settings),
                        item["IntegrationId"],
                        digest,
                    ).fetchone()
                ):
                    continue
                status = (
                    "queued"
                    if item
                    and item["RequestedStatus"] == "connected"
                    and item["VerifiedStatus"] == "verified"
                    else "quarantined"
                )
                c.execute(
                    (
                        "INSERT crm_channels2.WebhookEvent(Inst"
                        "itutionId,EventId,ReceiptId,Integratio"
                        "nId,SubeventPath,Kind,ProviderEventId,"
                        "DedupeKey,IdentityStrength,Status,Payl"
                        "oad,CreatedAt,ApplicationId,EndpointId"
                        ",RouteKind,RouteExternalId) VALUES(?,?"
                        ",?,?,?,?,?,?,?,?,?,SYSUTCDATETIME(),?,"
                        "?,?,?)"
                    ),
                    institution(self.settings),
                    str(uuid4()),
                    receipt["ReceiptId"],
                    item["IntegrationId"] if item else None,
                    str(index),
                    effect["kind"],
                    effect["external"] if valid_external(effect["external"]) else None,
                    digest,
                    "provider" if item else "unresolved",
                    status,
                    json.dumps(effect, ensure_ascii=False),
                    receipt["ApplicationId"],
                    receipt["EndpointId"],
                    route_kind,
                    effect["route"] if valid_external(effect["route"]) else "unknown",
                )
                quarantined = quarantined or status == "quarantined"
            c.execute(
                (
                    "UPDATE crm_channels2.WebhookReceipt SE"
                    "T Status=?,Attempts=Attempts+1 WHERE I"
                    "nstitutionId=? AND ReceiptId=?"
                ),
                "quarantined" if quarantined else "processed",
                institution(self.settings),
                receipt["ReceiptId"],
            )
            return True

    def project_once(self):
        with transaction(self.settings, True, anonymous=True) as c:
            config = configuration(c, self.settings)
            if not config["IngressEnabled"] or not config["ModuleEnabled"]:
                return False
            inst = institution(self.settings)
            value = postgres_queue.event(c, inst) if getattr(self.settings, "postgres_profile", False) else one(
                c,
                (
                    "SELECT TOP(1) ev.* FROM crm_channels2."
                    "WebhookEvent ev JOIN crm_channels2.Int"
                    "egration i ON i.InstitutionId=ev.Insti"
                    "tutionId AND i.IntegrationId=ev.Integr"
                    "ationId JOIN crm_channels2.WebhookEndp"
                    "oint ep ON ep.InstitutionId=ev.Institu"
                    "tionId AND ep.EndpointId=ev.EndpointId"
                    " WHERE ev.InstitutionId=? AND ev.Statu"
                    "s='queued' AND i.RequestedStatus='conn"
                    "ected' AND i.VerifiedStatus='verified'"
                    " AND ep.IsActive=1 ORDER BY ev.Created"
                    "At,ev.EventId"
                ),
                inst,
            )
            if not value:
                return False
            item = one(
                c,
                (
                    "SELECT * FROM crm_channels2.Integratio"
                    "n WHERE InstitutionId=? AND Integratio"
                    "nId=?"
                ),
                institution(self.settings),
                value["IntegrationId"],
            )
            # Savepoint keeps durable input when a local prerequisite is missing.
            c.execute("SAVE TRANSACTION event_projection")
            try:
                project(c, self.settings, item, json.loads(value["Payload"]))
                c.execute(
                    (
                        "UPDATE crm_workspace.State SET Revisio"
                        "n=Revision+1 WHERE StateId=1"
                    )
                )
                status, error = "processed", None
            except HTTPException as error_value:
                c.execute("ROLLBACK TRANSACTION event_projection")
                status, error = "quarantined", str(error_value.detail)[:64]
            c.execute(
                (
                    "UPDATE crm_channels2.WebhookEvent SET "
                    "Status=?,LastErrorCode=?,Attempts=Atte"
                    "mpts+1 WHERE InstitutionId=? AND Event"
                    "Id=?"
                ),
                status,
                error,
                institution(self.settings),
                value["EventId"],
            )
            from app.institutional.email_notifications import observe_service
            observe_service(c, self.settings, "webhook-projection:" + str(value["IntegrationId"]), failed=status == "quarantined", module="webhooks", channel=(item or {}).get("Channel", ""), account=str(value["IntegrationId"]))
            return True
