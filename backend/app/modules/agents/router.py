"""Guarded local agent administration. No institutional RBAC is claimed."""

import json
from uuid import UUID

from fastapi import APIRouter, Query

from app.modules.agents.domain import (
    AgentWrite,
    AssignmentWrite,
    Configuration,
    ContextWrite,
    ReviewWrite,
    SimulationRequest,
    SourceWrite,
    StageWrite,
    StateWrite,
    NoteWrite,
    ActionWrite,
    ActionDecision,
    ReindexWrite,
)
from app.modules.agents.generation import provider_options
from app.modules.agents.service import (
    AgentsService,
    identifier,
    load,
    preflight,
    require_schema,
)
from app.modules.ai.infrastructure.providers import AiError


def validation_fields(errors):
    models = (
        AgentWrite,
        AssignmentWrite,
        Configuration,
        ContextWrite,
        ReviewWrite,
        SimulationRequest,
        SourceWrite,
        StageWrite,
        StateWrite,
        NoteWrite,
        ActionWrite,
        ActionDecision,
        ReindexWrite,
    )
    allowed = {"entity_id", "document_id", "conversation_id", "offset"} | {
        field for model in models for field in model.model_fields
    }
    fields = []
    for error in errors[:8]:
        path = [part for part in error["loc"][1:] if isinstance(part, str)]
        if path and all(part in allowed for part in path):
            fields.append(".".join(path))
    return list(dict.fromkeys(fields))


def install_agents(application, service=None):
    service = service or AgentsService(application)
    application.state.agents = service
    router = APIRouter(prefix="/api/v1/agents", tags=["local-admissions-agents"])

    @router.get("")
    def catalog():
        return service.catalog()

    @router.get("/providers")
    def providers():
        if application.state.settings.mode != "local_sql_copy" and not getattr(
            service, "institutional", False
        ):
            raise AiError("local_sql_copy_required", 503)
        return provider_options(service.ai)

    @router.get("/profiles/{agent_id}/console")
    def console(agent_id: UUID):
        from app.modules.agents.operations import actions, profile
        from app.modules.agents.runtime import observation

        key = str(agent_id)
        with service.transaction() as cursor:
            agent = profile(cursor, key)
            value = observation(cursor, key)
            notes = cursor.execute(
                "SELECT TOP(25) Note,CreatedAt FROM crm_agents.History WHERE EntityId=? AND Kind='agent_note' ORDER BY EventId DESC",
                key,
            ).fetchall()
            conversations = cursor.execute(
                "SELECT TOP(25) c.ConversationId,p.Name FROM crm.Conversation c JOIN crm.Contact p ON p.ContactId=c.ContactId LEFT JOIN crm_agents.Assignment a ON a.ConversationId=c.ConversationId LEFT JOIN crm_agents.Context x ON x.ContextId=a.ContextId AND x.ConversationId=c.ConversationId WHERE c.State<>'closed' AND ((? IS NULL AND x.ProgramId IS NULL) OR x.ProgramId=?) AND (? IS NULL OR x.StageId=?) ORDER BY c.UpdatedAt DESC",
                agent["program_id"],
                agent["program_id"],
                agent["stage_id"],
                agent["stage_id"],
            ).fetchall()
            return {
                **value,
                "actions": actions(cursor, key),
                "notes": [{"text": r[0], "at": str(r[1])} for r in notes],
                "conversations": [
                    {"id": str(r[0]).lower(), "label": r[1] or str(r[0])}
                    for r in conversations
                ],
            }

    @router.post("/profiles/{agent_id}/notes")
    def add_note(agent_id: UUID, request: NoteWrite):
        from app.modules.agents.operations import note

        return note(service, str(agent_id), request)

    @router.post("/profiles/{agent_id}/actions")
    def add_action(agent_id: UUID, request: ActionWrite):
        from app.modules.agents.operations import create_action

        return create_action(service, str(agent_id), request)

    @router.post("/profiles/{agent_id}/actions/decision")
    def action_decision(agent_id: UUID, request: ActionDecision):
        from app.modules.agents.operations import decide_action

        return decide_action(service, str(agent_id), request)

    @router.post("/profiles/{agent_id}/reindex")
    def rebuild(agent_id: UUID, request: ReindexWrite):
        from app.modules.agents.operations import reindex

        return reindex(service, str(agent_id), request)

    @router.put("/profiles/{agent_id}")
    def save_agent(agent_id: UUID, request: AgentWrite):
        return service.save_agent(str(agent_id), request)

    @router.get("/profiles/{agent_id}/preflight")
    def review(agent_id: UUID):
        with service.transaction() as cursor:
            agents, stages = load(cursor)
            agent = agents.get(str(agent_id))
            if not agent:
                raise AiError("agents_not_found", 404)
            return preflight(cursor, agent, agents, stages)

    @router.post("/profiles/{agent_id}/approve")
    def approve(agent_id: UUID, request: ReviewWrite):
        return service.review_agent(str(agent_id), request)

    @router.post("/profiles/{agent_id}/state")
    def change_state(agent_id: UUID, request: StateWrite):
        return service.review_agent(str(agent_id), request, request.state)

    @router.put("/stages/{stage_id}")
    def stage(stage_id: UUID, request: StageWrite):
        return service.save_stage(str(stage_id), request)

    @router.post("/stages/{stage_id}/approve")
    def approve_stage(stage_id: UUID, request: ReviewWrite):
        return service.approve_stage(str(stage_id), request)

    @router.put("/sources/{document_id}/scope")
    def source_scope(document_id: UUID, request: SourceWrite):
        return service.source_scope(str(document_id), request)

    @router.get("/history")
    def history(
        entity_id: UUID | None = None, offset: int = Query(default=0, ge=0, le=100000)
    ):
        with service.transaction() as cursor:
            require_schema(cursor)
            clause = " WHERE EntityId=?" if entity_id else ""
            args = (str(entity_id), offset) if entity_id else (offset,)
            rows = cursor.execute(
                (
                    "SELECT EventId,Kind,EntityId,Note,Actor,CreatedAt,Document FROM "
                    "crm_agents.History"
                )
                + clause
                + " ORDER BY EventId DESC OFFSET ? ROWS FETCH NEXT 26 ROWS ONLY",
                *args,
            ).fetchall()
            return {
                "items": [
                    {
                        "id": r[0],
                        "kind": r[1],
                        "entity_id": identifier(r[2]),
                        "note": r[3],
                        "actor": r[4],
                        "created_at": str(r[5]),
                        "document": json.loads(r[6]),
                    }
                    for r in rows[:25]
                ],
                "has_more": len(rows) > 25,
            }

    @router.get("/supervision")
    def supervision(offset: int = Query(default=0, ge=0, le=100000)):
        if getattr(service, "institutional", False):
            return service.supervision(offset)
        with service.transaction() as cursor:
            require_schema(cursor)
            rows = cursor.execute(
                (
                    "SELECT "
                    "j.MessageId,j.ConversationId,j.State,j.LastError,j.CreatedAt,j.R"
                    "esult FROM crm_ai.ResponseJob j ORDER BY j.CreatedAt DESC OFFSET"
                    " ? ROWS FETCH NEXT 26 ROWS ONLY"
                ),
                offset,
            ).fetchall()
            from app.modules.agents.runtime import (
                REPORTED_TOKENS_SQL,
                execution_installed,
            )

            has_execution = execution_installed(cursor)
            reported = (
                REPORTED_TOKENS_SQL if has_execution else "CONVERT(bigint,u.TokensUsed)"
            )
            ledger_join = (
                " LEFT JOIN crm_agents.Execution e ON e.RequestId=u.RequestId"
                if has_execution
                else ""
            )
            usage = cursor.execute(
                (
                    "SELECT "
                    f"COUNT(*),COALESCE(SUM(CONVERT(bigint,u.TokensReserved)),0),SUM({reported}) "
                    f"FROM crm_agents.Usage u{ledger_join} WHERE u.CreatedAt>="
                    "DATEFROMPARTS(YEAR(SYSUTCDATETIME()),MONTH(SYSUTCDATETIME()),1)"
                )
            ).fetchone()
            return {
                "items": [
                    {
                        "message_id": identifier(r[0]),
                        "conversation_id": identifier(r[1]),
                        "state": r[2],
                        "reason": r[3],
                        "created_at": str(r[4]),
                        "agent": json.loads(r[5]).get("agent_selection"),
                    }
                    for r in rows[:25]
                ],
                "has_more": len(rows) > 25,
                "usage": {
                    "requests": usage[0],
                    "tokens_reserved": usage[1],
                    "tokens_reported": usage[2],
                    "billing": "not_available",
                },
            }

    @router.get("/conversations/{conversation_id}")
    def conversation(conversation_id: UUID):
        return service.conversation(str(conversation_id))

    @router.put("/conversations/{conversation_id}/contexts/{context_id}")
    def context(conversation_id: UUID, context_id: UUID, request: ContextWrite):
        return service.save_context(str(conversation_id), str(context_id), request)

    @router.put("/conversations/{conversation_id}/assignment")
    def assign(conversation_id: UUID, request: AssignmentWrite):
        return service.assign(str(conversation_id), request)

    @router.post("/simulate")
    async def simulate(request: SimulationRequest):
        return await service.simulate(request)

    application.include_router(router)
