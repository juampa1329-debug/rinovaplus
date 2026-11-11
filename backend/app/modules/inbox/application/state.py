"""Inbox extensions to the existing conversation authority and SQL transaction."""

import json

from fastapi import HTTPException


def installed(cursor):
    return bool(
        cursor.execute(
            "SELECT OBJECT_ID(N'crm_channels.ConversationControl')"
        ).fetchval()
    )


def control(cursor, conversation_id):
    if not installed(cursor):
        raise HTTPException(503, "inbox_extension_required")
    cursor.execute(
        "IF NOT EXISTS(SELECT 1 FROM crm_channels.ConversationControl WHERE ConversationId=?) "
        "INSERT crm_channels.ConversationControl(ConversationId) VALUES(?)",
        conversation_id,
        conversation_id,
    )


def change_control(cursor, conversation_id, previous, current):
    if not installed(cursor):
        return
    control(cursor, conversation_id)
    if previous == current:
        return
    cursor.execute(
        "UPDATE crm_channels.ConversationControl SET Epoch=Epoch+1 WHERE ConversationId=?",
        conversation_id,
    )
    if getattr(cursor, "agent_invalidate", None):
        cursor.agent_invalidate(cursor, conversation_id)
        return
    cursor.execute(
        "UPDATE q SET State='failed',LastError='control_epoch_obsolete',LeaseId=NULL "
        "FROM crm_channels.outbound_queue q JOIN crm_channels.MessageRoute r ON r.QueueId=q.QueueId "
        "JOIN crm.Message m ON m.MessageId=r.MessageId WHERE m.ConversationId=? "
        "AND r.ActorKind='bot' AND r.StartedAt IS NULL AND q.State IN('queued','sending')",
        conversation_id,
    )


def mark_read(cursor, conversation_id, observed):
    control(cursor, conversation_id)
    maximum = cursor.execute(
        "SELECT COALESCE(MAX(Sequence),0) FROM crm.Message WHERE ConversationId=?",
        conversation_id,
    ).fetchval()
    observed = maximum if observed is None else int(observed)
    if observed > maximum or (
        observed
        and not cursor.execute(
            "SELECT 1 FROM crm.Message WHERE ConversationId=? AND Sequence=?",
            conversation_id,
            observed,
        ).fetchone()
    ):
        raise HTTPException(409, "read_sequence_changed")
    cursor.execute(
        "UPDATE crm_channels.ConversationControl SET ReadSequence=CASE WHEN ReadSequence<? THEN ? ELSE ReadSequence END WHERE ConversationId=?",
        observed,
        observed,
        conversation_id,
    )
    return bool(
        cursor.execute(
            "SELECT CASE WHEN EXISTS(SELECT 1 FROM crm.Message m JOIN crm_channels.ConversationControl c ON c.ConversationId=m.ConversationId "
            "WHERE m.ConversationId=? AND m.Direction='incoming' AND m.Sequence>c.ReadSequence) THEN 1 ELSE 0 END",
            conversation_id,
        ).fetchval()
    )


def save_assessment(cursor, conversation_id, score, temperature):
    control(cursor, conversation_id)
    payload = json.dumps({"score": score, "temperature": temperature})
    cursor.execute(
        "IF NOT EXISTS(SELECT 1 FROM crm_channels.ConversationProfile WHERE ConversationId=?) "
        "INSERT crm_channels.ConversationProfile(ConversationId) VALUES(?)",
        conversation_id,
        conversation_id,
    )
    cursor.execute(
        "UPDATE crm_channels.ConversationProfile SET LeadScore=TRY_CONVERT(tinyint,JSON_VALUE(?, '$.score')),"
        "Temperature=JSON_VALUE(?, '$.temperature'),UpdatedAt=SYSUTCDATETIME() WHERE ConversationId=?",
        payload,
        payload,
        conversation_id,
    )
