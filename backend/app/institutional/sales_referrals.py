"""Signed inbound Click-to-WhatsApp attribution; local ad-to-program bindings."""

import json
import re
from urllib.parse import urlsplit

from app.institutional import db


def sanitize(value):
    if not isinstance(value, dict) or not re.fullmatch(r"[0-9]{1,40}", str(value.get("source_id", ""))):
        return None
    result = {"source_id": str(value["source_id"]), "source_type": "ad" if value.get("source_type") == "ad" else "post"}
    for field, limit in (("headline", 300), ("body", 1200), ("ctwa_clid", 500)):
        if isinstance(value.get(field), str):
            result[field] = value[field][:limit]
    url = value.get("source_url")
    if isinstance(url, str):
        try:
            parsed = urlsplit(url)
            if parsed.scheme == "https" and not parsed.username and not parsed.password and parsed.hostname in {"www.facebook.com", "facebook.com", "fb.me", "www.instagram.com", "instagram.com"}:
                result["source_url"] = url[:1500]
        except ValueError:
            pass
    return result


def links(c, settings):
    value = db.one(c, "SELECT Document,Revision FROM crm_access.Setting WHERE InstitutionId=? AND Section='sales-ad-links'", db.institution(settings))
    return {"items": json.loads(value["Document"])["items"], "revision": value["Revision"]} if value else {"items": [], "revision": 0}


def origin(c, settings, conversation, sequence):
    row = db.one(c,
        "SELECT TOP(1) x.Payload,m.MessageId,m.Sequence FROM crm_channels2.ExternalMessage x "
        "JOIN crm.Message m ON m.MessageId=x.MessageId WHERE x.InstitutionId=? AND m.ConversationId=? "
        "AND m.Sequence<=? AND ((m.Direction='incoming' AND JSON_VALUE(x.Payload,'$.referral.source_id') IS NOT NULL) OR JSON_VALUE(x.Payload,'$.comment_source.program_id') IS NOT NULL) ORDER BY m.Sequence DESC",
        db.institution(settings), conversation, sequence)
    if not row:
        return None
    value = json.loads(row["Payload"]).get("comment_source", {})
    if value:
        if value.get("authority") != "cbn-comment-private-v1" or type(value.get("program_id")) is not int:
            return None
        return {**value, "source_message_id": str(row["MessageId"]), "sequence": row["Sequence"],
                "source_type": "comment_private_reply", "authority": "accepted_private_reply_not_academic_confirmation"}
    referral = sanitize(json.loads(row["Payload"]).get("referral"))
    if not referral:
        return None
    mapping = links(c, settings)
    selected = next((v for v in mapping["items"] if v["ad_id"] == referral["source_id"]), None)
    # Click IDs stay in storage for attribution; they are not needed in an LLM prompt.
    return {**{k: v for k, v in referral.items() if k != "ctwa_clid"},
            "program_id": selected["program_id"] if selected else None,
            "mapping_revision": mapping["revision"], "source_message_id": str(row["MessageId"]), "sequence": row["Sequence"],
            "authority": "signed_ad_referral_not_program_facts"}
