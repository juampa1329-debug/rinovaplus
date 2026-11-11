"""Audited agent notes, assisted drafts and bounded knowledge reindexing."""

import json
from collections import Counter
from uuid import UUID, NAMESPACE_URL, uuid5

from app.modules.agents.domain import (
    chain_for,
    digest,
    effective_configuration,
    validate_hierarchy,
)
from app.modules.agents.service import history, identifier, invalidate, load, replay
from app.modules.ai.infrastructure.providers import AiError
from app.modules.knowledge.service import terms


ACTION_TOOLS = {
    "recommendation": "advisor.actions",
    "summary": "advisor.summary",
    "report": "analytics.report",
    "campaign_draft": "campaigns.draft",
    "followup_task": "advisor.actions",
    "crm_note": "crm.update",
}


def profile(cursor, key, request=None):
    agents, _ = load(cursor)
    agent = agents.get(key)
    if not agent:
        raise AiError("agents_not_found", 404)
    if request and request.revision != agent["revision"]:
        raise AiError("agents_revision_conflict", 409)
    return agent


def actions(cursor, key):
    rows = cursor.execute(
        "WITH a AS(SELECT Document,ROW_NUMBER() OVER(PARTITION BY JSON_VALUE(Document,'$.action_id') ORDER BY EventId DESC) AS n FROM crm_agents.History WHERE EntityId=? AND Kind IN('action_draft','action_approve','action_reject','action_execute')) SELECT TOP(25) Document FROM a WHERE n=1",
        key,
    ).fetchall()
    return [json.loads(row[0]) for row in rows]


def permissions(cursor, agent, *, execute=False):
    agents, stages = load(cursor)
    validate_hierarchy(agent, agents, stages)
    chain = chain_for(agent, agents)
    if execute and any(a["state"] != "active" or not a["enabled"] for a in chain):
        raise AiError("agents_parent_or_agent_unavailable", 409)
    config = effective_configuration(chain)
    binding = digest([[a["id"], a["version"]] for a in chain])
    return config, binding


def conversation_scope(cursor, agent, conversation_id):
    row = cursor.execute(
        "SELECT c.State,x.ProgramId,x.StageId FROM crm.Conversation c LEFT JOIN crm_agents.Assignment a ON a.ConversationId=c.ConversationId LEFT JOIN crm_agents.Context x ON x.ContextId=a.ContextId AND x.ConversationId=c.ConversationId WHERE c.ConversationId=?",
        conversation_id,
    ).fetchone()
    if not row or row[0] == "closed":
        raise AiError("agents_conversation_unavailable", 409)
    if (
        agent["level"] == "guide"
        and row[1] is not None
        or agent["level"] != "guide"
        and row[1] != agent["program_id"]
        or agent["level"] == "stage"
        and identifier(row[2]) != agent["stage_id"]
    ):
        raise AiError("agents_assignment_conflict", 409)


def note(service, key, request):
    with service.transaction(True) as cursor:
        repeated, payload = replay(cursor, "agent_note", key, request)
        if repeated:
            return {"confirmed": True, "replayed": True}
        profile(cursor, key, request)
        if not request.note.strip():
            raise AiError("agents_note_required", 422)
        history(
            cursor, "agent_note", key, request, payload, {"note": request.note.strip()}
        )
    return {"confirmed": True}


def create_action(service, key, request):
    with service.transaction(True) as cursor:
        repeated, payload = replay(cursor, "action_draft", key, request)
        if repeated:
            return {"confirmed": True, "replayed": True}
        agent = profile(cursor, key, request)
        config, binding = permissions(cursor, agent)
        if (
            agent["state"] == "archived"
            or ACTION_TOOLS[request.kind] not in config["capabilities"]
        ):
            raise AiError("agents_action_not_allowed", 409)
        if request.conversation_id:
            conversation_scope(cursor, agent, str(request.conversation_id))
        if (
            request.kind in ("followup_task", "crm_note")
            and not request.conversation_id
        ):
            raise AiError("agents_action_conversation_required", 409)
        if not request.conversation_id and not config["global_enabled"]:
            raise AiError("agents_action_conversation_required", 409)
        document = {
            **request.model_dump(mode="json"),
            "action_id": str(request.operation_id),
            "state": "draft",
            "agent_version": agent["version"],
            "chain_binding": binding,
        }
        history(cursor, "action_draft", key, request, payload, document)
    return {"confirmed": True}


def decide_action(service, key, request):
    task = None
    with service.transaction(True) as cursor:
        repeated, payload = replay(cursor, "action_" + request.decision, key, request)
        if repeated:
            return {"confirmed": True, "replayed": True}
        agent = profile(cursor, key, request)
        config, binding = permissions(
            cursor, agent, execute=request.decision == "execute"
        )
        action = next(
            (
                a
                for a in actions(cursor, key)
                if a["action_id"] == str(request.action_id)
            ),
            None,
        )
        if (
            not action
            or action["agent_version"] != agent["version"]
            or action.get("chain_binding") != binding
        ):
            raise AiError("agents_configuration_changed", 409)
        if (
            agent["state"] == "archived"
            or ACTION_TOOLS[action["kind"]] not in config["capabilities"]
        ):
            raise AiError("agents_action_not_allowed", 409)
        if request.decision == "execute":
            if action["state"] == "executed":
                return {"confirmed": True, "replayed": True}
            if action["state"] not in ("draft", "approved"):
                raise AiError("agents_action_not_allowed", 409)
            safe = (
                action["risk"] == "low"
                and action["impact"] == "low"
                and config["allow_safe_actions"]
                and not config["require_human_approval"]
            )
            if action["state"] != "approved" and not safe:
                raise AiError("agents_action_approval_required", 409)
            if action["kind"] in ("followup_task", "crm_note"):
                if (
                    not config["allow_safe_actions"]
                    or action["kind"] == "crm_note"
                    and not config["allow_crm_update"]
                ):
                    raise AiError("agents_action_not_allowed", 409)
                conversation_scope(cursor, agent, action["conversation_id"])
                if getattr(service, "institutional", False):
                    service.execute_action(cursor, action)
                    action["state"] = "executed"
                    history(cursor, "action_execute", key, request, payload, action)
                    return {"confirmed": True}
                from app.modules.inbox.application.operations import TaskWrite

                ops = service.application.state.inbox_operations
                operation_id = str(
                    uuid5(
                        NAMESPACE_URL, "agent-action-operation:" + action["action_id"]
                    )
                )
                task_id = str(
                    uuid5(NAMESPACE_URL, "agent-action-task:" + action["action_id"])
                )
                body = TaskWrite(
                    operationId=operation_id,
                    expectedRevision=ops.revision(cursor),
                    title=action["title"],
                    priority="high" if action["impact"] == "high" else "normal",
                    humanEmployeeId=None,
                    dueAt=None,
                    status="pending",
                )
                ops.mutate(
                    "task_create",
                    task_id,
                    body,
                    action["conversation_id"],
                    transaction_cursor=cursor,
                )
                action["task_id"] = task_id
        elif action["state"] not in ("draft", "approved"):
            raise AiError("agents_action_not_allowed", 409)
        if task is None:
            action["state"] = {
                "approve": "approved",
                "reject": "rejected",
                "execute": "executed",
            }[request.decision]
            history(cursor, "action_" + request.decision, key, request, payload, action)
            return {"confirmed": True}


def reindex(service, key, request):
    with service.transaction(True) as cursor:
        repeated, payload = replay(cursor, "reindex", key, request)
        if repeated:
            return {"confirmed": True, "replayed": True}
        agent = profile(cursor, key, request)
        if agent["state"] == "archived":
            raise AiError("agents_archived_read_only", 409)
        ids = agent["configuration"].get("document_ids", [])
        count = 0
        for doc in ids:
            rows = cursor.execute(
                "SELECT c.ChunkId,c.Body FROM crm_ai.KnowledgeChunk c JOIN crm_ai.KnowledgeDocument d ON d.DocumentId=c.DocumentId JOIN crm_agents.SourceScope s ON s.DocumentId=d.DocumentId WHERE d.DocumentId=? AND d.State='published' AND s.DocumentRevision=d.Revision AND s.ValidUntil>=CONVERT(date,SYSUTCDATETIME()) AND (s.ProgramId IS NULL OR s.ProgramId=?) AND (s.StageId IS NULL OR s.StageId=?)",
                doc,
                agent["program_id"],
                agent["stage_id"],
            ).fetchall()
            if not rows:
                raise AiError("agents_source_not_approved_for_scope", 409)
            for chunk, text in rows:
                cursor.execute("DELETE crm_ai.KnowledgeTerm WHERE ChunkId=?", chunk)
                for term, frequency in Counter(terms(text)).items():
                    cursor.execute(
                        "INSERT crm_ai.KnowledgeTerm(Term,ChunkId,Frequency) VALUES(?,?,?)",
                        term,
                        chunk,
                        min(32767, frequency),
                    )
                count += 1
        history(
            cursor,
            "reindex",
            key,
            request,
            payload,
            {
                "documents": len(ids),
                "chunks": count,
                "institutional_source": "SQL vigente, sin índice documental duplicado",
            },
        )
        invalidate(cursor)
    return {"confirmed": True, "documents": len(ids), "chunks": count}
