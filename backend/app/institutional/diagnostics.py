"""Read-only operational timeline. No prompt, credentials, payload or customer body."""

import json
from fastapi import Request

from app.institutional.auth import authorize
from app.institutional.db import institution, rows, uid, utc
from app.institutional.store import transaction


def projection(value):
    """Only explicitly selected telemetry crosses the administrative boundary."""
    data = json.loads(value or "{}")
    trace = data.get("language_execution") or {}
    return {"provider": str(trace.get("provider") or "")[:40], "model": str(trace.get("model") or "")[:180],
            "fallback_used": trace.get("fallback_used") is True,
            "context_changes": data.get("dispatch_context_changes", [])[:30],
            "own_projection_context_refreshed": data.get("own_projection_context_refreshed") is True,
            "attempts": [{k: a.get(k) for k in ("provider", "model", "role", "state", "code")}
                         for a in trace.get("attempts", [])[:4] if isinstance(a, dict)],
            "conversation_id": str(data.get("conversation") or "")[:36]}


def read(c, settings, conversation=None):
    inst = institution(settings)
    bind = uid(conversation) if conversation else None
    sends = rows(c, "SELECT TOP(50) q.QueueId,q.State,q.LastErrorCode,q.Attempts,q.CreatedAt,"
        "m.ConversationId,i.Channel,i.DisplayName FROM crm_channels2.SendJob q "
        "JOIN crm_channels2.Integration i ON i.InstitutionId=q.InstitutionId AND i.IntegrationId=q.IntegrationId "
        "LEFT JOIN crm.Message m ON m.MessageId=q.MessageId WHERE q.InstitutionId=? "
        + ("AND m.ConversationId=? " if bind else "") + "ORDER BY q.CreatedAt DESC,q.QueueId", inst, *((bind,) if bind else ()))
    operations = rows(c, "SELECT TOP(50) p.OperationId,p.Action,p.Status,p.ResultCode,p.CreatedAt,p.ResultMetadata,"
        "i.Channel,i.DisplayName FROM crm_channels2.ProviderOperation p "
        "JOIN crm_channels2.Integration i ON i.InstitutionId=p.InstitutionId AND i.IntegrationId=p.IntegrationId "
        "WHERE p.InstitutionId=? " + ("AND JSON_VALUE(p.ResultMetadata,'$.conversation')=? " if bind else "")
        + "ORDER BY p.CreatedAt DESC,p.OperationId", inst, *((bind,) if bind else ()))
    events = [] if bind else rows(c, "SELECT TOP(50) e.EventId,e.Kind,e.Status,e.LastErrorCode,e.CreatedAt,"
        "i.Channel,i.DisplayName FROM crm_channels2.WebhookEvent e LEFT JOIN crm_channels2.Integration i "
        "ON i.InstitutionId=e.InstitutionId AND i.IntegrationId=e.IntegrationId WHERE e.InstitutionId=? "
        "ORDER BY e.CreatedAt DESC,e.EventId", inst)
    result = []
    for v in sends:
        result.append({"id": uid(str(v["QueueId"])), "section": "outbound", "action": "send", "state": v["State"],
            "code": v["LastErrorCode"], "attempt_count": v["Attempts"], "at": utc(v["CreatedAt"]),
            "channel": v["Channel"], "account": v["DisplayName"], "conversation_id": uid(str(v["ConversationId"])) if v["ConversationId"] else ""})
    for v in operations:
        result.append({"id": uid(str(v["OperationId"])), "section": "ai" if v["Action"] in {"gemini_whatsapp_reply", "gemini_comment_reply"} or "gemini" in v["Action"] else "channel",
            "action": v["Action"], "state": v["Status"], "code": v["ResultCode"], "at": utc(v["CreatedAt"]),
            "channel": v["Channel"], "account": v["DisplayName"], **projection(v["ResultMetadata"])})
    for v in events:
        result.append({"id": uid(str(v["EventId"])), "section": "webhook", "action": v["Kind"], "state": v["Status"],
            "code": v["LastErrorCode"], "at": utc(v["CreatedAt"]), "channel": v["Channel"] or "", "account": v["DisplayName"] or "Sin cuenta vinculada"})
    return {"items": sorted(result, key=lambda v: (v["at"], v["id"]), reverse=True), "limit_per_section": 50,
            "read_only": True, "contains_prompts_or_credentials": False}


def install(app, settings):
    @app.get("/api/institution/diagnostics")
    def overview(request: Request, conversation_id: str | None = None):
        with transaction(settings, anonymous=True) as c:
            authorize(c, settings, request.state.authority, "users.manage")
            return read(c, settings, conversation_id)
