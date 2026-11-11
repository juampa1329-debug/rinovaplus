"""Durable SQL leases for ingestion and outbound dispatch in the existing process."""

import json
import threading
import time
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException

from . import providers
from .storage import document


def meta_effects(payload, accounts):
    for entry in payload.get("entry", []):
        asset = str(entry.get("id", ""))
        for account in accounts:
            channel = account["channel"]
            config = account["configuration"]
            expected = (
                config.get("wabaId")
                if channel == "whatsapp"
                else config.get("accountId")
                if channel == "instagram"
                else config.get("pageId")
            )
            if asset != expected:
                continue
            for change in entry.get("changes", []):
                value = change.get("value", {})
                if channel == "whatsapp":
                    if str(
                        value.get("metadata", {}).get("phone_number_id", "")
                    ) != config.get("phoneNumberId"):
                        continue
                    for message in value.get("messages", []):
                        kind = message.get("type", "unknown")
                        text = (
                            message.get("text", {}).get("body")
                            or message.get("button", {}).get("text")
                            or message.get("image", {}).get("caption")
                            or message.get("document", {}).get("caption")
                            or f"[{kind}]"
                        )
                        yield (
                            account,
                            "message",
                            message["id"],
                            str(message["from"]),
                            text,
                            message,
                        )
                    for status in value.get("statuses", []):
                        yield (
                            account,
                            "status",
                            status.get("id", ""),
                            "",
                            status.get("status", ""),
                            status,
                        )
                elif channel == "instagram" and change.get("field") in (
                    "comments",
                    "live_comments",
                ):
                    yield (
                        account,
                        "comment",
                        str(value.get("id", "")),
                        str(value.get("from", {}).get("id", "")),
                        value.get("text", ""),
                        value,
                    )
                elif (
                    channel == "facebook"
                    and change.get("field") == "feed"
                    and value.get("item") == "comment"
                    and value.get("verb") == "add"
                ):
                    yield (
                        account,
                        "comment",
                        str(value.get("comment_id", "")),
                        str(value.get("from", {}).get("id", "")),
                        value.get("message", ""),
                        value,
                    )
            if channel not in ("messenger", "instagram"):
                continue
            for event in entry.get("messaging", []):
                message = event.get("message", {})
                if message and not message.get("is_echo"):
                    yield (
                        account,
                        "message",
                        str(message.get("mid", "")),
                        str(event.get("sender", {}).get("id", "")),
                        message.get("text") or "[multimedia]",
                        event,
                    )
                for external in event.get("delivery", {}).get("mids", []):
                    yield account, "status", str(external), "", "delivered", event
                if event.get("read", {}).get("mid"):
                    yield (
                        account,
                        "status",
                        str(event["read"]["mid"]),
                        "",
                        "read",
                        event,
                    )


def tiktok_effects(payload, accounts):
    for account in accounts:
        config = account["configuration"]
        if str(payload.get("client_key", "")) != config.get("appId") or str(
            payload.get("user_openid", "")
        ) != config.get("accountId"):
            continue
        content = payload.get("content", {})
        if isinstance(content, str):
            content = json.loads(content)
        event = payload.get("event")
        if event in ("im_receive_msg", "im_receive_msg_eu"):
            yield (
                account,
                "message",
                str(content.get("message_id", "")),
                str(content.get("conversation_id", "")),
                content.get("text", {}).get("body")
                or "[" + str(content.get("type", "multimedia")) + "]",
                content,
            )
        elif event == "im_mark_read_msg":
            yield (
                account,
                "status",
                str(content.get("message_id", "")),
                "",
                "read",
                content,
            )
        elif event == "im_send_msg":
            yield (
                account,
                "status",
                str(content.get("message_id", "")),
                "",
                "sent",
                content,
            )
        elif event == "comment.update":
            kind = (
                "comment"
                if content.get("comment_action") == "insert"
                else "comment_state"
            )
            yield (
                account,
                kind,
                str(content.get("comment_id", "")),
                str(content.get("unique_identifier", "")),
                str(content.get("text", "")),
                content,
            )


def append_message(
    cursor, account, external, identity, text, payload, *, foundation=False
):
    channel = account["channel"]
    if not external or not identity:
        raise HTTPException(422, "external_identity_missing")
    if cursor.execute(
        "SELECT ExternalId FROM crm_channels.ExternalMessage WHERE Channel=? AND ExternalId=?",
        channel,
        external,
    ).fetchone():
        return
    linked = cursor.execute(
        "SELECT IdentityId,ContactId,ConversationId FROM crm_channels.ExternalIdentity WHERE Channel=? AND ExternalId=?",
        channel,
        identity,
    ).fetchone()
    if not linked:
        from app.modules.crm_configuration.application.service import (
            read_configuration,
            validate_contact,
        )
        from app.sql_workspace import Contact

        stage = account["configuration"].get("initialStage", "")
        configuration, _ = read_configuration(cursor, foundation=foundation)
        if not stage or not any(
            s.label == stage and s.active for s in configuration.stages
        ):
            raise HTTPException(409, "initial_crm_stage_required")
        contact_id, conversation_id, identity_id = map(str, (uuid4(), uuid4(), uuid4()))
        phone = identity if channel == "whatsapp" else ""
        contact = Contact(
            id=contact_id,
            name=identity[:100],
            phone=phone[:40],
            city="",
            program="",
            schedule="",
            stage=stage,
            tags="",
            notes="",
            type="",
            interests="",
            customValues={},
        )
        validate_contact(cursor, contact, foundation=foundation)
        cursor.execute(
            "INSERT crm.Contact(ContactId,Name,Phone,City,ProgramId,Program,Schedule,Stage,Tags,Notes,Type,Interests,CustomValues) VALUES(?,?,?,'',NULL,'','',?,'','','','','{}')",
            contact_id,
            contact.name,
            contact.phone,
            stage,
        )
        cursor.execute(
            "INSERT crm.Conversation(ConversationId,ContactId,State,Priority,ControlMode,Unread) VALUES(?,?,'open','normal','human',1)",
            conversation_id,
            contact_id,
        )
        cursor.execute(
            "INSERT crm_channels.ExternalIdentity(IdentityId,Channel,ExternalId,ContactId,ConversationId) VALUES(?,?,?,?,?)",
            identity_id,
            channel,
            identity,
            contact_id,
            conversation_id,
        )
        linked = (identity_id, contact_id, conversation_id)
    timestamp = payload.get("timestamp")
    try:
        seconds = float(timestamp)
        if channel != "whatsapp":
            seconds /= 1000
        incoming_at = datetime.fromtimestamp(seconds, timezone.utc).replace(tzinfo=None)
        if seconds > datetime.now(timezone.utc).timestamp() + 300:
            raise ValueError()
    except (ValueError, TypeError, OverflowError, OSError):
        raise HTTPException(422, "provider_message_timestamp_invalid") from None
    message_id = str(uuid4())
    cursor.execute(
        "INSERT crm.Message(MessageId,ConversationId,Body,Direction,CreatedAt) VALUES(?,?,?,'incoming',?)",
        message_id,
        str(linked[2]),
        str(text).strip()[:4000] or "[evento]",
        incoming_at,
    )
    cursor.execute(
        "INSERT crm_channels.ExternalMessage(Channel,ExternalId,MessageId,Payload) VALUES(?,?,?,?)",
        channel,
        external,
        message_id,
        document(payload),
    )
    if not foundation and cursor.execute(
        "SELECT OBJECT_ID(N'crm_channels.MessageRoute')"
    ).fetchval():
        cursor.execute(
            "INSERT crm_channels.MessageRoute(MessageId,IdentityId,ActorKind) VALUES(?,?,'external')",
            message_id,
            str(linked[0]),
        )
        from app.modules.inbox.application.media import record_incoming

        record_incoming(
            cursor, account, str(linked[0]), str(linked[2]), message_id, payload
        )
        if cursor.execute("SELECT OBJECT_ID(N'crm_ai.AdmissionsPolicy')").fetchval():
            cursor.execute(
                "INSERT crm_ai.ResponseJob(MessageId,ConversationId,IdentityId) "
                "SELECT m.MessageId,m.ConversationId,? FROM crm.Message m "
                "JOIN crm.Conversation c WITH(UPDLOCK,HOLDLOCK) ON c.ConversationId=m.ConversationId "
                "CROSS JOIN crm_ai.AdmissionsPolicy p WHERE m.MessageId=? AND p.PolicyId=1 AND p.Enabled=1 "
                "AND c.ControlMode='ai' AND c.State<>'closed' AND m.Sequence>p.ActivationSequence",
                str(linked[0]), message_id,
            )
    cursor.execute(
        "UPDATE crm.Conversation SET Unread=1,UpdatedAt=SYSUTCDATETIME() WHERE ConversationId=?",
        str(linked[2]),
    )
    cursor.execute(
        "UPDATE crm_channels.ExternalIdentity SET LastIncomingAt=CASE WHEN LastIncomingAt IS NULL OR LastIncomingAt<? THEN ? ELSE LastIncomingAt END WHERE IdentityId=?",
        incoming_at,
        incoming_at,
        str(linked[0]),
    )
    cursor.execute(
        "INSERT crm_channels.Audit(Channel,Action,EntityId) VALUES(?,'incoming_message',?)",
        channel,
        message_id,
    )


def enqueue_message(
    cursor, conversation_id, message_id, body, identity_id, media_id=None
):
    if not cursor.execute("SELECT SCHEMA_ID(N'crm_channels')").fetchone()[0]:
        raise HTTPException(503, "channels_schema_required")
    links = cursor.execute(
        "SELECT i.IdentityId,i.Channel,i.ExternalId,a.State FROM crm_channels.ExternalIdentity i JOIN crm_channels.Account a ON a.Channel=i.Channel WHERE ConversationId=? AND i.IdentityId=?",
        conversation_id,
        identity_id,
    ).fetchall()
    if not links:
        raise HTTPException(409, "channel_identity_changed")
    identity, channel, target, state = links[0]
    if state not in ("connected", "awaiting_webhook"):
        raise HTTPException(409, "channel_not_active")
    queue_id = str(uuid4())
    cursor.execute(
        "INSERT crm_channels.outbound_queue(QueueId,Channel,IdentityId,MessageId,Payload) VALUES(?,?,?,?,?)",
        queue_id,
        channel,
        str(identity),
        message_id,
        document(
            {
                "kind": "message",
                "target": target,
                "body": body,
                "origin": "human",
                **({"mediaId": media_id} if media_id else {}),
            }
        ),
    )
    from app.modules.inbox.application.state import control

    control(cursor, conversation_id)
    cursor.execute(
        "INSERT crm_channels.MessageRoute(MessageId,IdentityId,QueueId,ActorKind) VALUES(?,?,?,'human')",
        message_id,
        str(identity),
        queue_id,
    )


def record_comment(cursor, account, external, identity, text, payload):
    channel = account["channel"]
    previous = cursor.execute(
        "SELECT Payload FROM crm_channels.social_comments WITH(UPDLOCK,HOLDLOCK) WHERE Channel=? AND ExternalId=?",
        channel,
        external,
    ).fetchone()
    if previous and channel == "tiktok":
        old = json.loads(previous[0])
        old_time = int(old.get("timestamp", 0))
        new_time = int(payload.get("timestamp", 0))
        if new_time < old_time or (
            new_time == old_time
            and old.get("comment_action") not in ("insert", "set_to_public")
            and payload.get("comment_action") == "insert"
        ):
            return
    if previous:
        cursor.execute(
            "UPDATE crm_channels.social_comments SET Payload=?,Body=?,AuthorId=? WHERE Channel=? AND ExternalId=?",
            document(payload),
            text,
            identity,
            channel,
            external,
        )
    else:
        cursor.execute(
            "INSERT crm_channels.social_comments(CommentId,Channel,ExternalId,AuthorId,Body,Payload) VALUES(?,?,?,?,?,?)",
            str(uuid4()),
            channel,
            external,
            identity,
            text,
            document(payload),
        )


def delivery_state(previous, incoming):
    rank = {
        "queued": 0,
        "sending": 0,
        "uncertain": 0,
        "failed": 0,
        "sent": 1,
        "delivered": 2,
        "read": 3,
    }
    if incoming == "failed":
        return previous if previous in ("delivered", "read") else "failed"
    return incoming if rank.get(incoming, -1) > rank.get(previous, -1) else previous


def record_delivery(cursor, channel, external, status, payload):
    if status not in ("sent", "delivered", "read", "failed"):
        return
    previous = cursor.execute(
        "SELECT MessageId,Payload FROM crm_channels.ExternalMessage WITH(UPDLOCK,HOLDLOCK) WHERE Channel=? AND ExternalId=?",
        channel,
        external,
    ).fetchone()
    if previous and previous[0] is not None:
        return
    state = delivery_state(
        json.loads(previous[1]).get("state", "queued") if previous else "queued", status
    )
    receipt = document({"kind": "delivery_status", "state": state, "payload": payload})
    if previous:
        cursor.execute(
            "UPDATE crm_channels.ExternalMessage SET Payload=? WHERE Channel=? AND ExternalId=?",
            receipt,
            channel,
            external,
        )
    else:
        cursor.execute(
            "INSERT crm_channels.ExternalMessage(Channel,ExternalId,Payload) VALUES(?,?,?)",
            channel,
            external,
            receipt,
        )
    queued = cursor.execute(
        "SELECT QueueId,State FROM crm_channels.outbound_queue WHERE Channel=? AND ExternalId=?",
        channel,
        external,
    ).fetchone()
    if queued:
        cursor.execute(
            "UPDATE crm_channels.outbound_queue SET State=?,LastError=? WHERE QueueId=?",
            delivery_state(queued[1], state),
            "provider_delivery_failed" if state == "failed" else None,
            str(queued[0]),
        )


def media_frontier(application, queue_id, lease, account):
    """Revalidate after uploading bytes and immediately before sending a message."""
    with application.state.sql_workspace.transaction(write=True) as cursor:
        from app.modules.campaigns.transport import reject_marketing
        queued_payload = cursor.execute("SELECT Payload FROM crm_channels.outbound_queue WHERE QueueId=?", queue_id).fetchone()
        if queued_payload:
            reject_marketing(cursor, queue_id, json.loads(queued_payload[0]))
        current = application.state.channel_store.get(cursor, account["channel"])
        if current["revision"] != account["revision"] or current["state"] not in (
            "connected",
            "awaiting_webhook",
        ):
            raise providers.ProviderFailure("channel_paused_before_send")
        row = cursor.execute(
            "SELECT r.ActorKind,r.ControlEpoch,c.Epoch,v.ControlMode,v.State,i.LastIncomingAt "
            "FROM crm_channels.outbound_queue q WITH(UPDLOCK) JOIN crm_channels.MessageRoute r ON r.QueueId=q.QueueId AND r.IdentityId=q.IdentityId "
            "JOIN crm.Message m ON m.MessageId=q.MessageId AND r.MessageId=m.MessageId "
            "JOIN crm.Conversation v ON v.ConversationId=m.ConversationId "
            "JOIN crm_channels.ExternalIdentity i ON i.IdentityId=q.IdentityId AND i.ConversationId=v.ConversationId AND i.Channel=q.Channel "
            "LEFT JOIN crm_channels.ConversationControl c ON c.ConversationId=v.ConversationId "
            "WHERE q.QueueId=? AND q.LeaseId=? AND q.State='sending'",
            queue_id,
            lease,
        ).fetchone()
        if not row or row[4] == "closed":
            raise providers.ProviderFailure("dispatch_lease_obsolete")
        if row[0] == "bot" and (row[3] != "ai" or row[1] != row[2]):
            raise providers.ProviderFailure("control_epoch_obsolete")
        if row[0] not in ("human", "bot"):
            raise providers.ProviderFailure("outbound_origin_unverified")
        if row[0] == "bot":
            from app.modules.ai.application.admissions import validate_dispatch

            validate_dispatch(cursor, queue_id, current["revision"])
        if not row[5] or (
            datetime.now(timezone.utc).replace(tzinfo=None) - row[5]
        ).total_seconds() > (172800 if account["channel"] == "tiktok" else 86400):
            raise providers.ProviderFailure("customer_service_window_expired")
        if (
            account["channel"] == "tiktok"
            and cursor.execute(
                "SELECT COUNT(*) FROM crm_channels.outbound_queue WHERE IdentityId=(SELECT IdentityId FROM crm_channels.outbound_queue WHERE QueueId=?) AND CreatedAt>=? AND State IN('sent','delivered','read','uncertain')",
                queue_id,
                row[5],
            ).fetchval()
            >= 10
        ):
            raise providers.ProviderFailure("tiktok_reply_limit_reached")
        cursor.execute(
            "UPDATE crm_channels.MessageRoute SET StartedAt=SYSUTCDATETIME(),CompletedAt=NULL WHERE QueueId=?",
            queue_id,
        )


class ChannelWorkers:
    def __init__(self, application):
        self.application = application
        self.store = application.state.channel_store
        self.stop_event = threading.Event()
        self.threads = []
        self.last_media_cleanup = 0

    def start(self):
        for kind in ("ingest", "dispatch", "media"):
            thread = threading.Thread(
                target=self.run, args=(kind,), daemon=True, name="channels-" + kind
            )
            self.threads.append(thread)
            thread.start()

    def stop(self):
        self.stop_event.set()
        for thread in self.threads:
            thread.join(timeout=14)

    def run(self, kind):
        while not self.stop_event.is_set():
            try:
                worked = getattr(self, kind)()
            except Exception:
                # SQL durable states retain diagnostics; never log payloads/credentials.
                worked = False
            self.stop_event.wait(0.2 if worked else 2)

    def media(self):
        from app.modules.inbox.application.media import cleanup, retrieve_one

        if time.monotonic() - self.last_media_cleanup > 60:
            cleanup(self.application.state.sql_workspace)
            self.last_media_cleanup = time.monotonic()
        return retrieve_one(self.application)

    def ingest(self):
        lease = str(uuid4())
        with self.store.transaction() as cursor:
            cursor.execute(
                "UPDATE crm_channels.webhook_events SET State='queued',LeaseId=NULL WHERE State='processing' AND DueAt<SYSUTCDATETIME()"
            )
            row = cursor.execute(
                ";WITH candidate AS(SELECT TOP(1) * FROM crm_channels.webhook_events WITH(UPDLOCK,READPAST,ROWLOCK) WHERE State='queued' AND DueAt<=SYSUTCDATETIME() ORDER BY ReceivedAt) UPDATE candidate SET State='processing',LeaseId=?,Attempts=Attempts+1,DueAt=DATEADD(second,60,SYSUTCDATETIME()) OUTPUT inserted.EventId,inserted.Provider,inserted.Payload,inserted.Attempts",
                lease,
            ).fetchone()
        if not row:
            return False
        event_id, provider, raw, attempt = row
        try:
            envelope = json.loads(raw)
            with self.application.state.sql_workspace.transaction(write=True) as cursor:
                owned = cursor.execute(
                    "SELECT State FROM crm_channels.webhook_events WITH(UPDLOCK) WHERE EventId=? AND LeaseId=?",
                    str(event_id),
                    lease,
                ).fetchone()
                if not owned or owned[0] != "processing":
                    return True
                accounts = [self.store.get(cursor, c) for c in envelope["channels"]]
                effects = (
                    meta_effects(envelope["payload"], accounts)
                    if provider == "meta"
                    else tiktok_effects(envelope["payload"], accounts)
                )
                for account, kind, external, identity, text, payload in effects:
                    if not external:
                        continue
                    channel = account["channel"]
                    if kind == "message":
                        append_message(
                            cursor, account, external, identity, text, payload
                        )
                    elif kind in ("comment", "comment_state"):
                        record_comment(
                            cursor, account, external, identity, text, payload
                        )
                    elif kind == "status":
                        record_delivery(cursor, channel, external, text, payload)
                    cursor.execute(
                        "UPDATE crm_channels.Account SET State='connected' WHERE Channel=? AND State='awaiting_webhook'",
                        channel,
                    )
                    if kind in ("message", "comment"):
                        evidence_path = (
                            "$.receiveMessagesConfirmed"
                            if kind == "message"
                            else "$.receiveCommentsConfirmed"
                        )
                        cursor.execute(
                            "UPDATE crm_channels.Account SET Capabilities=JSON_MODIFY(Capabilities,?,CAST(1 AS bit)) WHERE Channel=?",
                            evidence_path,
                            channel,
                        )
                cursor.execute(
                    "UPDATE crm_channels.webhook_events SET State='processed',LeaseId=NULL,LastError=NULL WHERE EventId=? AND LeaseId=?",
                    str(event_id),
                    lease,
                )
        except Exception as error:
            code = (
                error.detail
                if isinstance(error, HTTPException) and isinstance(error.detail, str)
                else "ingestion_failed"
            )
            with self.store.transaction() as cursor:
                cursor.execute(
                    "UPDATE crm_channels.webhook_events SET State=?,LeaseId=NULL,LastError=?,DueAt=DATEADD(second,?,SYSUTCDATETIME()) WHERE EventId=? AND LeaseId=?",
                    "failed" if attempt >= 6 else "queued",
                    code[:80],
                    min(300, 2**attempt),
                    str(event_id),
                    lease,
                )
        return True

    def dispatch(self):
        lease = str(uuid4())
        with self.store.transaction() as cursor:
            cursor.execute(
                "UPDATE crm_channels.outbound_queue SET State='uncertain',LastError='dispatch_interrupted',LeaseId=NULL WHERE State='sending' AND DueAt<SYSUTCDATETIME()"
            )
            row = cursor.execute(
                ";WITH candidate AS(SELECT TOP(1) q.* FROM crm_channels.outbound_queue q WITH(UPDLOCK,READPAST,ROWLOCK) JOIN crm_channels.Account a ON a.Channel=q.Channel WHERE q.State='queued' AND q.DueAt<=SYSUTCDATETIME() AND a.State IN('connected','awaiting_webhook') ORDER BY q.CreatedAt) UPDATE candidate SET State='sending',LeaseId=?,Attempts=Attempts+1,DueAt=DATEADD(second,CASE WHEN JSON_VALUE(Payload,'$.mediaId') IS NOT NULL THEN 180 ELSE 60 END,SYSUTCDATETIME()) OUTPUT inserted.QueueId,inserted.Channel,inserted.Payload,inserted.Attempts,inserted.IdentityId",
                lease,
            ).fetchone()
            if not row:
                return False
            queue_id, channel, raw, attempt, identity = row
            account = self.store.get(cursor, channel, True)
        try:
            payload = json.loads(raw)
            media = None
            with self.application.state.sql_workspace.transaction(write=True) as cursor:
                from app.modules.campaigns.transport import reject_marketing
                reject_marketing(cursor, str(queue_id), payload)
                current = self.store.get(cursor, channel)
                if current["revision"] != account["revision"] or current[
                    "state"
                ] not in ("connected", "awaiting_webhook"):
                    raise providers.ProviderFailure(
                        "channel_paused_before_send", retry=True
                    )
                if channel == "tiktok" and payload.get("kind") == "comment":
                    comment = cursor.execute(
                        "SELECT Payload FROM crm_channels.social_comments WHERE Channel=? AND ExternalId=?",
                        channel,
                        payload["target"],
                    ).fetchone()
                    if not comment or json.loads(comment[0]).get(
                        "comment_action"
                    ) not in ("insert", "set_to_public"):
                        raise providers.ProviderFailure("comment_no_longer_public")
                if identity:
                    fence = cursor.execute(
                        "SELECT i.LastIncomingAt,c.ControlMode,c.State FROM crm_channels.ExternalIdentity i JOIN crm.Conversation c ON c.ConversationId=i.ConversationId WHERE IdentityId=?",
                        str(identity),
                    ).fetchone()
                    if not fence or fence[2] == "closed":
                        raise providers.ProviderFailure(
                            "human_open_conversation_required"
                        )
                    if (
                        cursor.execute(
                            "SELECT OBJECT_ID(N'crm_channels.MessageRoute')"
                        ).fetchval()
                        and payload.get("origin") == "human"
                    ):
                        cursor.execute(
                            "INSERT crm_channels.MessageRoute(MessageId,IdentityId,QueueId,ActorKind) "
                            "SELECT q.MessageId,q.IdentityId,q.QueueId,'human' FROM crm_channels.outbound_queue q "
                            "JOIN crm.Message m ON m.MessageId=q.MessageId JOIN crm_channels.ExternalIdentity i ON i.IdentityId=q.IdentityId "
                            "AND i.ConversationId=m.ConversationId WHERE q.QueueId=? AND NOT EXISTS(SELECT 1 FROM crm_channels.MessageRoute r WHERE r.MessageId=q.MessageId)",
                            str(queue_id),
                        )
                    route = None
                    if cursor.execute(
                        "SELECT OBJECT_ID(N'crm_channels.MessageRoute')"
                    ).fetchval():
                        route = cursor.execute(
                            "SELECT r.ActorKind,r.ControlEpoch,c.Epoch FROM crm_channels.MessageRoute r "
                            "JOIN crm.Message m ON m.MessageId=r.MessageId "
                            "JOIN crm_channels.ExternalIdentity i ON i.IdentityId=r.IdentityId AND i.ConversationId=m.ConversationId "
                            "LEFT JOIN crm_channels.ConversationControl c ON c.ConversationId=m.ConversationId WHERE r.QueueId=? AND r.IdentityId=?",
                            str(queue_id),
                            str(identity),
                        ).fetchone()
                    origin = route[0] if route else payload.get("origin")
                    if origin == "bot":
                        if not route or fence[1] != "ai" or route[1] != route[2]:
                            raise providers.ProviderFailure("control_epoch_obsolete")
                    elif origin != "human" or not route:
                        raise providers.ProviderFailure("outbound_origin_unverified")
                    if channel in ("whatsapp", "instagram", "messenger") and (
                        not fence[0]
                        or (
                            datetime.now(timezone.utc).replace(tzinfo=None) - fence[0]
                        ).total_seconds()
                        > 86400
                    ):
                        raise providers.ProviderFailure(
                            "customer_service_window_expired"
                        )
                    if channel == "tiktok":
                        if (
                            not fence[0]
                            or (
                                datetime.now(timezone.utc).replace(tzinfo=None)
                                - fence[0]
                            ).total_seconds()
                            > 172800
                        ):
                            raise providers.ProviderFailure(
                                "customer_service_window_expired"
                            )
                        sent = cursor.execute(
                            "SELECT COUNT(*) FROM crm_channels.outbound_queue WHERE IdentityId=? AND CreatedAt>=? AND State IN('sent','delivered','read','uncertain')",
                            str(identity),
                            fence[0],
                        ).fetchone()[0]
                        if sent >= 10:
                            raise providers.ProviderFailure(
                                "tiktok_reply_limit_reached"
                            )
                    owned = cursor.execute(
                        "SELECT State FROM crm_channels.outbound_queue WITH(UPDLOCK) WHERE QueueId=? AND LeaseId=?",
                        str(queue_id),
                        lease,
                    ).fetchone()
                    if not owned or owned[0] != "sending":
                        raise providers.ProviderFailure("dispatch_lease_obsolete")
                    if payload.get("mediaId"):
                        from app.modules.inbox.infrastructure import media_files

                        asset = cursor.execute(
                            "SELECT a.Kind,a.ActualMime,a.FileName,a.ByteLength FROM crm_channels.MediaAsset a "
                            "JOIN crm_channels.outbound_queue q ON q.MessageId=a.MessageId "
                            "JOIN crm.Message m ON m.MessageId=q.MessageId JOIN crm_channels.ExternalIdentity i ON i.IdentityId=q.IdentityId "
                            "AND i.ConversationId=m.ConversationId AND a.ConversationId=m.ConversationId "
                            "WHERE q.QueueId=? AND a.MediaId=? AND a.State='ready'",
                            str(queue_id),
                            payload["mediaId"],
                        ).fetchone()
                        source = media_files.path(payload["mediaId"])
                        if (
                            not asset
                            or not source.is_file()
                            or source.is_symlink()
                            or source.stat().st_size != asset[3]
                        ):
                            raise providers.ProviderFailure("media_content_unavailable")
                        media = {
                            "path": source,
                            "kind": asset[0],
                            "mime": asset[1],
                            "name": asset[2],
                        }
                    else:
                        cursor.execute(
                            "UPDATE crm_channels.MessageRoute SET StartedAt=SYSUTCDATETIME(),CompletedAt=NULL WHERE QueueId=?",
                            str(queue_id),
                        )
            external = providers.send(
                account,
                payload,
                media,
                lambda: media_frontier(self.application, str(queue_id), lease, account),
            )
            with self.store.transaction() as cursor:
                pending = cursor.execute(
                    "SELECT Payload FROM crm_channels.ExternalMessage WITH(UPDLOCK,HOLDLOCK) WHERE Channel=? AND ExternalId=? AND MessageId IS NULL",
                    channel,
                    external,
                ).fetchone()
                state = (
                    delivery_state("sent", json.loads(pending[0]).get("state", "sent"))
                    if pending
                    else "sent"
                )
                cursor.execute(
                    "UPDATE crm_channels.outbound_queue SET State=?,ExternalId=?,LeaseId=NULL,LastError=? WHERE QueueId=? AND LeaseId=?",
                    state,
                    external,
                    "provider_delivery_failed" if state == "failed" else None,
                    str(queue_id),
                    lease,
                )
                cursor.execute(
                    "IF OBJECT_ID(N'crm_channels.MessageRoute') IS NOT NULL "
                    "UPDATE crm_channels.MessageRoute SET CompletedAt=SYSUTCDATETIME() WHERE QueueId=?",
                    str(queue_id),
                )
                evidence_path = (
                    "$.commentReplyConfirmed"
                    if payload["kind"] == "comment"
                    else "$.sendMessagesConfirmed"
                )
                cursor.execute(
                    "UPDATE crm_channels.Account SET Capabilities=JSON_MODIFY(Capabilities,?,CAST(1 AS bit)) WHERE Channel=? AND Revision=?",
                    evidence_path,
                    channel,
                    account["revision"],
                )
        except providers.ProviderFailure as error:
            state = (
                "uncertain"
                if error.uncertain
                else "queued"
                if error.retry and attempt < 6
                else "failed"
            )
            with self.store.transaction() as cursor:
                cursor.execute(
                    "UPDATE crm_channels.outbound_queue SET State=?,LastError=?,LeaseId=NULL,DueAt=DATEADD(second,?,SYSUTCDATETIME()) WHERE QueueId=? AND LeaseId=?",
                    state,
                    error.code,
                    min(900, 2**attempt),
                    str(queue_id),
                    lease,
                )
                if not error.uncertain:
                    cursor.execute(
                        "IF OBJECT_ID(N'crm_channels.MessageRoute') IS NOT NULL "
                        "UPDATE crm_channels.MessageRoute SET CompletedAt=SYSUTCDATETIME() WHERE QueueId=?",
                        str(queue_id),
                    )
                if error.code == "provider_permission_or_request_rejected":
                    cursor.execute(
                        "UPDATE crm_channels.Account SET State='attention_required',LastError=? WHERE Channel=? AND Revision=?",
                        error.code,
                        channel,
                        account["revision"],
                    )
        return True
