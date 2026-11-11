"""Bounded reconstruction from authenticated persisted receipts, never queue age."""

import hashlib
import json
import re
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.modules.channels.workers import meta_effects, tiktok_effects
from .domain.scoring import ChurnInputs, IncomingEvidence, ConfirmedResponse, CostExchange, assess_churn


def timestamp(raw):
    try:
        value = raw.get("timestamp", raw.get("create_time"))
        if isinstance(value, bool):
            return None
        value = float(value)
        if value > 100000000000:
            value /= 1000
        return datetime.fromtimestamp(value, timezone.utc)
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def assess(cursor, store, row, weights, now):
    conversation, state, stage = str(row[0]), row[1], row[2]
    watermark = cursor.execute("SELECT COALESCE(MAX(Sequence),0) FROM crm.Message WHERE ConversationId=?", conversation).fetchval()
    base = ChurnInputs(UUID(conversation), now, state, stage, watermark)
    identities = cursor.execute("SELECT IdentityId,Channel,ExternalId FROM crm_channels.ExternalIdentity WHERE ConversationId=?", conversation).fetchall()
    if len(identities) != 1:
        result = assess_churn(base, weights)
        return replace(result, reasons=("exact_external_identity_required",)), None, None, []
    identity, channel, external = identities[0]
    messages = cursor.execute(
        "SELECT TOP(101) m.MessageId,m.Sequence,m.Direction,m.Body,m.CreatedAt,r.ActorKind,x.ExternalId,q.QueueId,q.ExternalId,q.Payload,j.MessageId "
        "FROM crm.Message m JOIN crm_channels.MessageRoute r ON r.MessageId=m.MessageId AND r.IdentityId=? "
        "LEFT JOIN crm_channels.ExternalMessage x ON x.MessageId=m.MessageId AND x.Channel=? "
        "LEFT JOIN crm_channels.outbound_queue q ON q.MessageId=m.MessageId AND q.IdentityId=r.IdentityId AND q.Channel=? AND q.QueueId=r.QueueId "
        "LEFT JOIN crm_ai.ResponseJob j ON j.ResponseMessageId=m.MessageId "
        "WHERE m.ConversationId=? ORDER BY m.Sequence DESC", str(identity), channel, channel, conversation,
    ).fetchall()
    incoming = next((m for m in messages if m[2] == "incoming" and m[5] == "external" and m[6]), None)
    if incoming is None or len(messages) > 100:
        return replace(assess_churn(base, weights), reasons=("genuine_incoming_required" if incoming is None else "message_evidence_limit",)), str(identity), None, []
    account = store.get(cursor, channel)
    receipts = cursor.execute(
        "SELECT TOP(51) EventId,Provider,Digest,Payload FROM crm_channels.webhook_events "
        "WHERE State='processed' AND ReceivedAt>=? ORDER BY ReceivedAt DESC", incoming[4] - timedelta(minutes=5),
    ).fetchall()
    effects = {}
    for receipt in receipts[:50]:
        try:
            envelope = json.loads(receipt[3])
            raw = envelope.get("raw", "")
            if channel not in envelope.get("channels", []) or hashlib.sha256(raw.encode()).digest() != bytes(receipt[2]) or json.loads(raw) != envelope.get("payload"):
                continue
            normalize = tiktok_effects if receipt[1] == "tiktok" else meta_effects
            for _, kind, message, sender, text, payload in normalize(envelope["payload"], [account]):
                at = timestamp(payload)
                if at and at <= now and (kind == "status" and text in ("sent", "delivered", "read") or kind == "message" and sender == external):
                    if kind == "status" and channel == "whatsapp" and str(payload.get("recipient_id", "")) != external:
                        continue
                    key = (kind, str(message))
                    previous = effects.get(key)
                    if previous is None or at < previous[1]:
                        effects[key] = (UUID(str(receipt[0])), at, text)
        except (ValueError, TypeError, KeyError):
            continue
    genuine = effects.get(("message", str(incoming[6])))
    if genuine is None:
        return replace(assess_churn(base, weights), reasons=("authenticated_incoming_receipt_required",)), str(identity), None, []
    incoming_evidence = IncomingEvidence(UUID(str(incoming[0])), UUID(str(identity)), incoming[1], genuine[1])
    responses, response_bodies = [], {}
    for message in messages:
        if message[2] != "outgoing" or message[1] <= incoming[1] or not message[7] or not message[8]:
            continue
        confirmation = effects.get(("status", str(message[8])))
        payload = json.loads(message[9])
        reply_to = str(message[10] or payload.get("replyToMessageId", ""))
        if confirmation is None or reply_to.lower() != str(incoming[0]).lower():
            continue
        responses.append(ConfirmedResponse(UUID(str(message[0])), UUID(str(identity)), UUID(str(message[7])), UUID(reply_to), message[1], confirmation[1], "provider_" + confirmation[2], confirmation[0]))
        response_bodies[UUID(str(message[0]))] = message[3]
    cost, cost_requested = None, bool(re.search(r"\b(precio|costo|costos|valor|tarifa)\b|cu[aá]nto.*(?:cuesta|vale)", incoming[3], re.I))
    if cost_requested:
        def monetary_answer(text):
            # A year, document count or enrollment reference is not a quoted fee.
            quoted = re.search(r"\b(?:precio|costo|valor|tarifa)\b[^\d]{0,80}(\$?\s*\d[\d.,]*)(?:\s*(COP|pesos))?", text, re.I)
            if not quoted:
                return False
            digits = re.sub(r"\D", "", quoted[1])
            return bool(digits and ("$" in quoted[1] or quoted[2] or int(digits) >= 10000))
        answered = next((r for r in sorted(responses, key=lambda item: item.sequence) if monetary_answer(response_bodies[r.message_id])), None)
        if answered:
            cost = CostExchange(incoming_evidence.message_id, answered.message_id, incoming_evidence.message_id, answered.message_id)
    inputs = replace(base, latest_incoming=incoming_evidence, responses=tuple(responses), evidence_complete=len(receipts) <= 50, cost_exchange=cost)
    result = assess_churn(inputs, weights)
    if cost_requested and cost is None:
        result = replace(result, status="unknown", score=None, level="unknown", reasons=("cost_answer_confirmation_missing",))
    signals = []
    for code, pattern, points in (
        ("explicit_interest", r"\b(?:me interesa|quiero estudiar|deseo estudiar)\b", 30),
        ("requested_next_step", r"\b(?:c[oó]mo (?:me inscribo|puedo inscribirme)|quiero (?:informaci[oó]n|una cita))\b", 30),
        ("declared_commitment", r"\b(?:quiero inscribirme|deseo matricularme|voy a inscribirme)\b", 40),
    ):
        if re.search(pattern, incoming[3], re.I) and not re.search(r"\b(?:no quiero|no me interesa|no deseo)\b", incoming[3], re.I):
            signals.append({"code": code, "points": points, "message_id": str(incoming[0]), "version": "lead-observable-v1"})
    lead = sum(s["points"] for s in signals) if signals else None
    return result, str(identity), lead, signals
