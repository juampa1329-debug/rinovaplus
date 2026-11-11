"""Explicit institutional route authority for the reusable agent constructor."""

from uuid import UUID

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import Field

from app.institutional.agents import Agents
from app.institutional.db import institution, record_operation, replay
from app.modules.agents.domain import Mutation, JsonUUID
from app.institutional.models import Strict
from typing import Literal
from app.modules.agents.router import install_agents
from app.modules.agents.service import load
from app.modules.ai.infrastructure.providers import AiError


class ProgramWrite(Mutation):
    name: str = Field(min_length=1, max_length=180)
    school: str = Field(default="", max_length=100)
    schedule: str = Field(default="", max_length=100)
    active: bool = True


class Restore(Mutation):
    version: int = Field(ge=1)
    note: str = Field(min_length=1, max_length=1000)


class Draft(Strict):
    revision: int = Field(ge=0)
    request_id: JsonUUID
    question: str = Field(min_length=1, max_length=2000)
    channel: Literal["local", "whatsapp", "facebook", "instagram", "tiktok"] = "local"
    call_provider: bool = False
    acknowledge_consumption: bool = False


def install(app, settings, gateway_factory=None):
    service = Agents(app, settings, gateway_factory)
    install_agents(app, service)

    @app.exception_handler(AiError)
    async def agent_error(request: Request, error: AiError):
        return JSONResponse({"code": error.code}, status_code=error.status)

    @app.get("/api/v1/agents/selection")
    def selection():
        with service.transaction() as c:
            agents, stages = load(c)
            return {
                "installed": True,
                "agents": [
                    {
                        k: item.get(k)
                        for k in [
                            "id",
                            "name",
                            "state",
                            "enabled",
                            "version",
                            "revision",
                            "level",
                            "parent_id",
                            "program_id",
                            "stage_id",
                        ]
                    }
                    for item in agents.values()
                ],
                "stages": list(stages.values()),
                "programs": service.catalog_adapter.programs(c, 0, 300),
                "sources": [],
                "legacy_agents": [],
            }

    @app.get("/api/v1/agents/programs")
    def programs():
        with service.transaction() as c:
            return service.catalog_adapter.programs(c, 0, 300)

    @app.put("/api/v1/agents/programs/{program_id}")
    def save_program(program_id: int, body: ProgramWrite):
        if program_id <= 0:
            raise HTTPException(422, "invalid_program_id")
        if any(
            len(v.encode("utf-16-le")) > limit * 2
            for v, limit in [(body.name, 180), (body.school, 100), (body.schedule, 100)]
        ):
            raise HTTPException(422, "field_too_long")
        with service.transaction(True) as c:
            digest, prior = replay(
                c,
                settings,
                c.agent_user,
                str(body.operation_id),
                "agents.program",
                str(program_id),
                body.model_dump(mode="json"),
            )
            if prior:
                return prior
            old = c.execute(
                "SELECT Revision FROM crm_agents5.Program WHERE InstitutionId=? AND ProgramId=?",
                institution(settings),
                program_id,
            ).fetchone()
            if body.revision != (old[0] if old else 0):
                raise HTTPException(409, "revision_conflict")
            if old:
                c.execute(
                    "UPDATE crm_agents5.Program SET Name=?,School=?,Schedule=?,Active=?,Revision=Revision+1,ReviewedBy=?,UpdatedAt=SYSUTCDATETIME() "
                    "WHERE InstitutionId=? AND ProgramId=?",
                    body.name,
                    body.school,
                    body.schedule,
                    body.active,
                    c.agent_user,
                    institution(settings),
                    program_id,
                )
            else:
                c.execute(
                    "INSERT crm_agents5.Program(InstitutionId,ProgramId,Name,School,Schedule,Active,Authority,ReviewedBy) "
                    "VALUES(?,?,?,?,?,?,'declared',?)",
                    institution(settings),
                    program_id,
                    body.name,
                    body.school,
                    body.schedule,
                    body.active,
                    c.agent_user,
                )
            result = {
                "saved": True,
                "authority": "declared_CRM_catalog_not_verified_SIIE",
            }
            record_operation(
                c,
                settings,
                c.agent_user,
                str(body.operation_id),
                "agents.program",
                str(program_id),
                digest,
                result,
            )
            return result

    @app.get("/api/v1/agents/programs/{program_id}")
    def program(program_id: int):
        from app.institutional.db import one

        with service.transaction() as c:
            item = one(
                c,
                "SELECT ProgramId,Name,School,Schedule,Active,Revision,Authority FROM crm_agents5.Program WHERE InstitutionId=? AND ProgramId=?",
                institution(settings),
                program_id,
            )
            return {
                "exists": item is not None,
                "revision": item["Revision"] if item else 0,
                "program": item,
                "authority": "declared_CRM_catalog_not_verified_SIIE",
            }

    @app.post("/api/v1/agents/profiles/{agent_id}/restore-version")
    def restore(agent_id: UUID, body: Restore):
        return service.restore_version(str(agent_id), body)

    @app.post("/api/v1/agents/conversations/{conversation_id}/draft")
    async def draft(conversation_id: UUID, body: Draft):
        return await service.draft_conversation(str(conversation_id), body)
