"""Proposed transparent churn rubric; no inference, persistence or sending."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Mapping
from uuid import UUID

FORMULA_VERSION = "churn-rubric-v1"


@dataclass(frozen=True)
class IncomingEvidence:
    message_id: UUID
    identity_id: UUID
    sequence: int
    occurred_at: datetime
    source: str = "provider_inbound"


@dataclass(frozen=True)
class ConfirmedResponse:
    message_id: UUID
    identity_id: UUID
    queue_id: UUID
    reply_to_message_id: UUID
    sequence: int
    sent_at: datetime
    confirmation: str
    confirmation_evidence_id: UUID


@dataclass(frozen=True)
class CostExchange:
    request_message_id: UUID
    response_message_id: UUID
    request_evidence_id: UUID
    answer_evidence_id: UUID


@dataclass(frozen=True)
class ChurnInputs:
    conversation_id: UUID
    as_of: datetime
    state: str
    stage: str | None
    input_sequence: int | None
    latest_incoming: IncomingEvidence | None = None
    responses: tuple[ConfirmedResponse, ...] = ()
    evidence_complete: bool = False
    cost_exchange: CostExchange | None = None


@dataclass(frozen=True)
class ChurnAssessment:
    status: Literal["known", "unknown", "not_applicable"]
    score: int | None
    level: Literal["low", "medium", "high", "unknown", "not_applicable"]
    reasons: tuple[str, ...]
    as_of: datetime | None
    input_sequence: int | None
    waiting_since: datetime | None = None
    evidence_message_ids: tuple[UUID, ...] = ()
    components: tuple[tuple[str, int], ...] = ()
    formula_version: str = FORMULA_VERSION


def utc(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        return None
    return value.astimezone(timezone.utc)


def assess_churn(inputs: ChurnInputs, stage_weights: Mapping[str, int]) -> ChurnAssessment:
    """Only verified, complete input supports a score; it is not a probability.

    The future adapter must bind all evidence to this conversation/identity,
    validate provider receipts and establish chronological completeness. A POST
    acknowledgement, queued row or MessageRoute.CompletedAt is not a receipt.
    """
    as_of = utc(inputs.as_of)

    def unavailable(reason, *, closed=False):
        status = "not_applicable" if closed else "unknown"
        return ChurnAssessment(status, None, status, (reason,), as_of, inputs.input_sequence)

    if as_of is None or not isinstance(inputs.conversation_id, UUID):
        return unavailable("invalid_assessment_identity_or_time")
    if inputs.state == "closed":
        return unavailable("conversation_closed", closed=True)
    if inputs.state not in ("open", "waiting") or inputs.evidence_complete is not True:
        return unavailable("active_complete_evidence_required")
    if type(inputs.input_sequence) is not int or inputs.input_sequence < 1:
        return unavailable("input_watermark_required")
    if inputs.stage not in stage_weights:
        return unavailable("stage_mapping_required")
    stage = stage_weights[inputs.stage]
    if type(stage) is not int or not 0 <= stage <= 25:
        return unavailable("invalid_stage_weight")
    incoming = inputs.latest_incoming
    if incoming is None or incoming.source != "provider_inbound":
        return unavailable("genuine_incoming_required")
    received = utc(incoming.occurred_at)
    if (
        not isinstance(incoming.message_id, UUID)
        or not isinstance(incoming.identity_id, UUID)
        or type(incoming.sequence) is not int
        or not 0 < incoming.sequence <= inputs.input_sequence
        or received is None or received > as_of
    ):
        return unavailable("invalid_incoming_evidence")
    if len(inputs.responses) > 100:
        return unavailable("response_evidence_limit")
    seen_ids, seen_sequences, seen_queue_ids, current = set(), set(), set(), []
    for response in inputs.responses:
        sent = utc(response.sent_at)
        if (
            any(not isinstance(value, UUID) for value in (
                response.message_id, response.identity_id, response.queue_id,
                response.reply_to_message_id, response.confirmation_evidence_id,
            ))
            or response.identity_id != incoming.identity_id
            or type(response.sequence) is not int
            or not 0 < response.sequence <= inputs.input_sequence
            or response.sequence == incoming.sequence
            or response.message_id == incoming.message_id
            or response.message_id in seen_ids or response.sequence in seen_sequences
            or response.queue_id in seen_queue_ids
            or response.confirmation not in ("provider_sent", "provider_delivered", "provider_read")
            or sent is None or sent > as_of
        ):
            return unavailable("invalid_or_ambiguous_response_evidence")
        seen_ids.add(response.message_id)
        seen_sequences.add(response.sequence)
        seen_queue_ids.add(response.queue_id)
        if response.sequence > incoming.sequence:
            if sent < received:
                return unavailable("contradictory_response_chronology")
            if response.reply_to_message_id == incoming.message_id:
                current.append(response)
    # A new inbound resets the clock/count. Operator debt is a separate SLA.
    if not current:
        return unavailable("advisor_response_pending")
    current.sort(key=lambda item: item.sequence)
    if any(utc(b.sent_at) < utc(a.sent_at) for a, b in zip(current, current[1:])):
        return unavailable("contradictory_provider_chronology")
    waiting_since = utc(current[0].sent_at)
    days = int((as_of - waiting_since).total_seconds() // 86400)
    inactivity = min(60, 15 * days)
    unanswered = min(15, 5 * len(current))
    score = min(100, max(0, inactivity + stage + unanswered))
    reasons = ["waiting_for_client", "configured_stage_weight", "confirmed_unanswered_responses"]
    cost = inputs.cost_exchange
    if cost is not None:
        if any(not isinstance(value, UUID) for value in (
            cost.request_message_id, cost.response_message_id,
            cost.request_evidence_id, cost.answer_evidence_id,
        )):
            return unavailable("invalid_cost_exchange_evidence")
        reply = next((item for item in current if item.message_id == cost.response_message_id), None)
        if cost.request_message_id == incoming.message_id and reply is None:
            return unavailable("cost_answer_confirmation_missing")
        # Older cost requests cannot survive a newer inbound as an abandonment signal.
        if cost.request_message_id == incoming.message_id and reply is not None:
            if (as_of - utc(reply.sent_at)).total_seconds() >= 72 * 3600:
                score = max(80, score)
                reasons.append("cost_answer_without_new_incoming_72h")
        else:
            reasons.append("older_cost_signal_reset")
    level = "high" if score >= 70 else "medium" if score >= 35 else "low"
    return ChurnAssessment(
        "known", score, level, tuple(reasons), as_of, inputs.input_sequence,
        waiting_since, (incoming.message_id, *(item.message_id for item in current)),
        (("inactivity", inactivity), ("stage", stage), ("unanswered", unanswered)),
    )
