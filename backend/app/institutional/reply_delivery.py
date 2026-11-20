"""Complete, ordered reply groups over the existing outbox, with no startup DDL."""

import re
from uuid import uuid4

from fastapi import HTTPException

from app.institutional.db import institution, one
from app.modules.channels import providers

WAITING = "reply_group_waiting_previous"
ACCEPTED = {"accepted", "sent", "delivered", "read"}


def chunks(text, target=350, *, enabled=True, channel="whatsapp"):
    """Prefer paragraphs/sentences. Never drop a tail or cut a word, URL or emoji."""
    if not text.strip():
        return []
    hard_limit = (
        1000 if channel == "instagram" else 2000 if channel == "messenger" else 4096
    )
    if not enabled or target <= 0:
        if len(text.strip()) > hard_limit:
            raise HTTPException(409, "gemini_whatsapp_segment_too_long")
        return [text.strip()]
    target = max(80, min(2000, target), (len(text) + 5) // 6)
    units, start = [], 0
    abbreviation = re.compile(
        r"\b(?:sr|sra|dr|dra|av|no|art|pág|etc|[ap]|[ap]\.\s*m)\.$", re.I
    )
    for boundary in re.finditer(r"\n\s*\n|(?<=[.!?])\s+", text):
        if "\n" not in boundary.group() and abbreviation.search(
            text[: boundary.start()]
        ):
            continue
        units.append(text[start : boundary.start()])
        start = boundary.end()
    units.append(text[start:])
    result, current = [], ""
    for unit in units:
        unit = unit.strip()
        if not unit:
            continue
        if current and len(current) + len(unit) + 2 > target:
            result.append(current)
            current = ""
        current = current + "\n\n" + unit if current else unit
    if current:
        result.append(current)
    # A long complete sentence stays intact. Bound fragment count by merging,
    # rather than slicing [:N], which silently loses the end of the response.
    while len(result) > 6:
        index = min(
            range(len(result) - 1), key=lambda i: len(result[i]) + len(result[i + 1])
        )
        result[index : index + 2] = [result[index] + "\n\n" + result[index + 1]]
    if any(len(part) > hard_limit for part in result):
        raise HTTPException(409, "gemini_whatsapp_segment_too_long")
    if "".join(text.split()) != "".join("".join(result).split()):
        raise HTTPException(409, "gemini_whatsapp_segment_incomplete")
    return result


def plan(text, document, channel, *, audio=False):
    parts = chunks(
        text,
        document.get("chars_per_message", 350),
        enabled=not audio
        and document.get("split_responses", True)
        and document.get("human_reply_style_enabled", True),
        channel=channel,
    )
    gap = max(
        document.get("fragment_delay_ms", 3000),
        document.get("reply_min_chunk_delay_ms", 3000),
    )
    initial = document.get("typing_ms", 1500)
    return [
        {
            "id": str(uuid4()),
            "text": part,
            "index": index,
            "total": len(parts),
            "delay_ms": initial + index * gap,
            "gap_ms": gap,
            "typing": document.get("show_typing", True),
        }
        for index, part in enumerate(parts)
    ]


def part_for(data, message):
    return next(
        (v for v in data.get("response_parts", []) if v["id"] == str(message).lower()),
        None,
    )


def quote_reference(data, part):
    """Quote only the verified incoming message on the group's first part."""
    if (
        data.get("quote_first_reply")
        and data.get("channel", "whatsapp") == "whatsapp"
        and part["index"] == 0
        and isinstance(data.get("external_incoming"), str)
        and data["external_incoming"].startswith("wamid.")
    ):
        return {
            "replyToMessageId": data["external_incoming"],
            "replyToInternalId": data["incoming"],
        }
    return {}


def require_previous(c, settings, integration, data, part):
    if part["index"] == 0:
        return
    previous = data["response_parts"][part["index"] - 1]
    job = one(
        c,
        "SELECT State,CASE WHEN CompletedAt<=DATEADD(millisecond,?,SYSUTCDATETIME()) THEN 1 ELSE 0 END AS Spaced FROM crm_channels2.SendJob WHERE InstitutionId=? AND IntegrationId=? AND MessageId=?",
        -part["gap_ms"],
        institution(settings),
        integration,
        previous["id"],
    )
    if not job or job["State"] in {"failed", "uncertain", "cancelled"}:
        raise HTTPException(409, "gemini_whatsapp_previous_part_not_sent")
    if job["State"] not in ACCEPTED or not job["Spaced"]:
        raise HTTPException(409, WAITING)


def typing(adapter, target, incoming, *, before=None, enabled=True):
    """Best effort provider action, never a message receipt fabricated by the CRM."""
    if not enabled:
        return "disabled"
    if before:
        before()
    config, channel = adapter["configuration"], adapter["channel"]
    if channel == "whatsapp":
        if not incoming or not incoming.startswith("wamid."):
            return "provider_message_id_missing"
        path = config["phoneNumberId"] + "/messages"
        body = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": incoming,
            "typing_indicator": {"type": "text"},
        }
    elif channel in {"messenger", "instagram"}:
        asset = config.get("accountId") if channel == "instagram" else config["pageId"]
        path = asset + "/messages"
        body = {"recipient": {"id": target}, "sender_action": "typing_on"}
    else:
        return "unsupported"
    try:
        providers.request(adapter, "POST", path, body)
        return "requested"
    except providers.ProviderFailure as error:
        return error.code  # Optional indicator cannot turn a good reply into failure.


def pending_bot_history(alias="m"):
    return (
        "NOT EXISTS(SELECT 1 FROM crm_channels2.MessageRoute br JOIN crm_channels2.SendJob bj "
        "ON bj.InstitutionId=br.InstitutionId AND bj.QueueId=br.QueueId "
        f"WHERE br.MessageId={alias}.MessageId AND br.ActorKind='bot' "
        "AND bj.State NOT IN('accepted','sent','delivered','read'))"
    )


def next_typing(settings, job, payload):
    """Show processing during the actual persisted gap, after prior acceptance."""
    if payload.get("origin") != "gemini_whatsapp" or not payload.get("showTyping"):
        return
    from app.institutional.store import transaction
    from app.institutional.whatsapp_gemini import ACTION, source
    from app.institutional.channel_provider import provider_account

    try:
        with transaction(settings, anonymous=True) as c:
            operation = one(
                c,
                "SELECT ResultMetadata FROM crm_channels2.ProviderOperation WHERE InstitutionId=? AND IntegrationId=? AND OperationId=? AND Action=? AND Status='confirmed'",
                institution(settings),
                job["IntegrationId"],
                payload["automationId"],
                ACTION,
            )
            if not operation:
                return
            import json

            data = json.loads(operation["ResultMetadata"])
            part = part_for(data, job["MessageId"])
            if not part or part["index"] + 1 >= part["total"]:
                return
            item, _, _ = source(c, settings, job["IntegrationId"], data)
            adapter, _ = provider_account(c, settings, item)
        typing(adapter, payload["target"], data.get("external_incoming"))
    except Exception:
        # The accepted message cannot become uncertain because an optional
        # presentation action failed. Never retry a message from this path.
        return
