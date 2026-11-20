"""Conversation-only context boundary and attributable audio interpretation."""

import json
from uuid import UUID

from app.institutional import db


def memory_section(conversation):
    return "sm-" + UUID(str(conversation)).hex


def transcript_section(message):
    return "at-" + UUID(str(message)).hex


def cutoff(c, settings, conversation):
    row = db.one(c, "SELECT Document FROM crm_access.Setting WHERE InstitutionId=? AND Section=?",
                 db.institution(settings), memory_section(conversation))
    value = json.loads(row["Document"]).get("reset_after_sequence", 0) if row else 0
    if type(value) is not int or value < 0:
        raise ValueError("invalid_conversation_context_boundary")
    return value


def audio_history(c, settings, conversation, messages):
    candidates = [m for m in messages if m.get("Direction") == "incoming" and m.get("MessageId")]
    if not candidates:
        return messages
    records = db.rows(c, "SELECT Section,Document FROM crm_access.Setting WHERE InstitutionId=? AND Section IN("
                      + ",".join("?" for _ in candidates) + ")", db.institution(settings),
                      *[transcript_section(m["MessageId"]) for m in candidates])
    if not records:
        return messages
    assets = db.rows(c, "SELECT MessageId,MediaId,ContentHash FROM crm_channels4.MediaAsset WHERE InstitutionId=? "
                     "AND ConversationId=? AND SourceKind='provider' AND Kind='audio' AND MessageId IN("
                     + ",".join("?" for _ in candidates) + ")", db.institution(settings), conversation,
                     *[str(m["MessageId"]) for m in candidates])
    proofs = {str(a["MessageId"]).lower(): (str(a["MediaId"]).lower(), bytes(a["ContentHash"]).hex()) for a in assets if a["ContentHash"]}
    documents = {r["Section"]: json.loads(r["Document"]) for r in records}
    result = []
    for message in messages:
        document = documents.get(transcript_section(message["MessageId"])) if message.get("MessageId") else None
        proof = proofs.get(str(message.get("MessageId", "")).lower())
        if document and proof and document.get("conversation_id") == str(conversation).lower() and (
            document.get("media_id"), document.get("media_hash")
        ) == proof and isinstance(document.get("text"), str) and 0 < len(document["text"]) <= 6000:
            result.append({**message, "Body": document["text"], "body_origin": "automatic_audio_transcription"})
        else:
            result.append(message)
    return result


def configure(c, settings):
    c.context_cutoff = lambda conversation: cutoff(c, settings, conversation)
    c.audio_history = lambda conversation, messages: audio_history(c, settings, conversation, messages)
