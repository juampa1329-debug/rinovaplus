"""Explicit institutional route authority for the reusable agent constructor."""

from uuid import UUID, NAMESPACE_URL, uuid5
from contextlib import nullcontext

from fastapi import HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import Field, model_validator

from app.institutional.agents import Agents
from app.institutional.db import institution, record_operation, replay
from app.modules.agents.domain import Mutation, JsonUUID
from app.institutional.models import Strict
from app.institutional.program_commercial import (
    CommercialProfile, ExtractedProgram, ImportUrl, import_program, read_profile, save_profile,
)
from typing import Literal
from app.modules.agents.router import install_agents
from app.modules.agents.service import load
from app.modules.ai.infrastructure.providers import AiError
from app.institutional.siie_catalog import SiieImport, preview as siie_preview
from app.institutional.siie_local import SiieSync, draft_from_source, local_source, reviewed_draft, save_source


class ProgramWrite(Mutation):
    name: str = Field(min_length=1, max_length=180)
    school: str = Field(default="", max_length=100)
    schedule: str = Field(default="", max_length=100)
    active: bool = True
    commercial: CommercialProfile | None = None
    siie_sync: SiieSync | None = None

    @model_validator(mode='after')
    def sync_profile_required(self):
        if self.siie_sync is not None and self.commercial is None:
            raise ValueError('siie_profile_required')
        return self


class SiiePageWrite(Mutation):
    source_revision: str = Field(min_length=1, max_length=120)
    cursor: str = Field(default="", max_length=128)
    period_id: str = Field(default="", pattern=r"^(?:[1-9][0-9]{0,9})?$")


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
    from app.institutional.sales_agents import install as install_sales
    install_sales(app, service, settings)
    from app.institutional.siie_api import install as install_siie
    install_siie(app, service)

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
    def programs(offset: int = Query(0, ge=0), limit: int = Query(300, ge=1, le=300), include_inactive: bool = False):
        with service.transaction() as c:
            return service.catalog_adapter.programs(c, offset, limit, include_inactive=True) if include_inactive else service.catalog_adapter.programs(c, offset, limit)

    @app.post("/api/v1/agents/programs/import")
    def extract_program(body: ImportUrl):
        with service.transaction():
            pass
        return import_program(body.url)

    @app.post("/api/v1/agents/programs/import-siie")
    def extract_siie(body: SiieImport):
        # Existing agents.manage authority and SQL checks precede outbound IO.
        with service.transaction():
            pass
        result = siie_preview(body.offer_id, program_id=body.program_id, period_id=body.period_id, cursor=body.cursor)
        with service.transaction() as c:
            source = result['source']
            if source.get('kind'):
                program_id = body.local_program_id
                matches = c.execute("SELECT p.ProgramId FROM crm_agents5.Program p JOIN crm_access.Setting s ON s.InstitutionId=p.InstitutionId AND s.Section=CONCAT('program-commercial-',p.ProgramId) WHERE p.InstitutionId=? AND JSON_VALUE(s.Document,'$.siie_program_id')=?", institution(settings), source['program_id']).fetchall()
                if len(matches) > 1:
                    raise HTTPException(409, 'siie_local_mapping_ambiguous')
                if matches and program_id is not None and matches[0][0] != program_id:
                    raise HTTPException(409, 'siie_local_mapping_ambiguous')
                if program_id is None and matches:
                    program_id = matches[0][0]
                if program_id is not None:
                    item = c.execute('SELECT Name,School,Schedule,Revision FROM crm_agents5.Program WHERE InstitutionId=? AND ProgramId=?', institution(settings), program_id).fetchone()
                    if not item:
                        raise HTTPException(404, 'invalid_program_id')
                    profile = read_profile(c, settings, program_id) or CommercialProfile().model_dump()
                    if profile.get('siie_program_id') and profile['siie_program_id'] != source['program_id']:
                        raise HTTPException(409, 'siie_program_binding_mismatch')
                    result['draft'], result['manual_fields_preserved'] = reviewed_draft({'name': item[0], 'school': item[1], 'schedule': item[2], 'commercial': profile}, local_source(c, settings, program_id, source['kind']), source)
                    result.update(local_program_id=program_id, local_revision=item[3])
        return result

    @app.post("/api/v1/agents/programs")
    def create_program(body: ProgramWrite):
        return write_program(None, body)

    @app.post("/api/v1/agents/programs/sync-siie-page")
    def sync_siie_page(body: SiiePageWrite):
        from app.institutional.siie_api import read
        with service.transaction() as c:
            digest, prior = replay(c, settings, c.agent_user, str(body.operation_id), 'agents.siie-page', 'catalog', body.model_dump(mode='json'))
            if prior:
                return prior
        page = read('programs', {'cursor': body.cursor, 'period_id': body.period_id})['data']
        if page['source_revision'] != body.source_revision:
            raise HTTPException(409, 'siie_source_changed_review_again')
        sources = [draft_from_source({**v, 'source_revision': page['source_revision']}, kind='program', request={'program_id': str(v.get('program_id')), 'cursor': body.cursor, 'period_id': body.period_id}) for v in page['items']]
        if len({v['program_id'] for v in sources}) != len(sources):
            raise HTTPException(502, 'siie_catalog_invalid_response')
        with service.transaction(True) as c:
            digest, prior = replay(c, settings, c.agent_user, str(body.operation_id), 'agents.siie-page', 'catalog', body.model_dump(mode='json'))
            if prior:
                return prior
            results = []
            for source in sources:
                matches = c.execute("SELECT p.ProgramId,p.Name,p.School,p.Schedule,p.Active,p.Revision FROM crm_agents5.Program p JOIN crm_access.Setting s ON s.InstitutionId=p.InstitutionId AND s.Section=CONCAT('program-commercial-',p.ProgramId) WHERE p.InstitutionId=? AND JSON_VALUE(s.Document,'$.siie_program_id')=?", institution(settings), source['program_id']).fetchall()
                if len(matches) > 1:
                    raise HTTPException(409, 'siie_local_mapping_ambiguous')
                old = matches[0] if matches else None
                draft = ExtractedProgram.model_validate(source['values'])
                manual = []
                if old:
                    draft, manual = reviewed_draft({'name': old[1], 'school': old[2], 'schedule': old[3], 'commercial': read_profile(c, settings, old[0]) or CommercialProfile().model_dump()}, local_source(c, settings, old[0], 'program'), source)
                command = ProgramWrite(**draft.model_dump(), active=bool(old[4]) if old else True, revision=old[5] if old else 0, operation_id=uuid5(NAMESPACE_URL, str(body.operation_id)+':'+source['program_id']))
                result = write_program(old[0] if old else None, command, source=source, connection=c)
                results.append({**result, 'manual_fields_preserved': manual})
            result = {'saved': True, 'count': len(results), 'items': results, 'siie_written': False}
            record_operation(c, settings, c.agent_user, str(body.operation_id), 'agents.siie-page', 'catalog', digest, result)
            return result

    @app.put("/api/v1/agents/programs/{program_id}")
    def save_program(program_id: int, body: ProgramWrite):
        return write_program(program_id, body)

    def write_program(program_id, body, *, source=None, connection=None):
        if program_id is not None and not 0 < program_id <= 2_147_483_647:
            raise HTTPException(422, "invalid_program_id")
        if not body.name.strip() or any(
            len(v.encode("utf-16-le")) > limit * 2
            for v, limit in [(body.name, 180), (body.school, 100), (body.schedule, 100)]
        ):
            raise HTTPException(422, "field_too_long")
        if body.siie_sync is not None and source is None:
            with service.transaction() as c:
                _, prior = replay(c, settings, c.agent_user, str(body.operation_id), 'agents.program', str(program_id) if program_id is not None else 'new', body.model_dump(mode='json', exclude_none=True))
                if prior:
                    return prior
            sync = body.siie_sync
            source = siie_preview(sync.offer_id, program_id=sync.program_id if sync.kind == 'program' else '', period_id=sync.period_id, cursor=sync.cursor)['source']
            if source['source_revision'] != sync.source_revision or source['kind'] != sync.kind:
                raise HTTPException(409, 'siie_source_changed_review_again')
        with (nullcontext(connection) if connection is not None else service.transaction(True)) as c:
            resource = str(program_id) if program_id is not None else "new"
            digest, prior = replay(
                c,
                settings,
                c.agent_user,
                str(body.operation_id),
                "agents.program",
                resource,
                body.model_dump(mode="json", exclude_none=True),
            )
            if prior:
                return prior
            if body.commercial is not None and body.commercial.siie_program_id:
                matches = c.execute("SELECT p.ProgramId FROM crm_agents5.Program p JOIN crm_access.Setting s ON s.InstitutionId=p.InstitutionId AND s.Section=CONCAT('program-commercial-',p.ProgramId) WHERE p.InstitutionId=? AND JSON_VALUE(s.Document,'$.siie_program_id')=?", institution(settings), body.commercial.siie_program_id).fetchall()
                if any(v[0] != program_id for v in matches):
                    raise HTTPException(409, 'siie_local_mapping_ambiguous')
            if program_id is None:
                program_id = c.execute(
                    "SELECT COALESCE(MAX(ProgramId),0) FROM crm_agents5.Program WHERE InstitutionId=?",
                    institution(settings),
                ).fetchval() + 1
                if program_id > 2_147_483_647:
                    raise HTTPException(409, "program_id_exhausted")
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
                    "WHERE InstitutionId=? AND ProgramId=? AND Revision=?",
                    body.name,
                    body.school,
                    body.schedule,
                    body.active,
                    c.agent_user,
                    institution(settings),
                    program_id,
                    body.revision,
                )
                if c.rowcount != 1:
                    raise HTTPException(409, "revision_conflict")
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
            if body.commercial is not None:
                profile = body.commercial
                if source is not None:
                    original = source['values']['commercial']
                    if profile.siie_program_id and profile.siie_program_id != source['program_id']:
                        raise HTTPException(409, 'siie_program_binding_mismatch')
                    fields = (('siie_program_id',) if profile.siie_offer_id else ('siie_program_id', 'siie_source_revision', 'source_checked_at')) if source['kind'] == 'program' else ('siie_program_id', 'siie_offer_id', 'siie_period_id', 'siie_campus_id', 'siie_shift_id', 'siie_source_revision', 'source_checked_at')
                    profile = profile.model_copy(update={key: original[key] for key in fields})
                    save_source(c, settings, program_id, body.revision + 1, c.agent_user, source)
                save_profile(c, settings, program_id, body.revision + 1, c.agent_user, profile)
            result = {
                "saved": True,
                "program_id": program_id,
                "revision": body.revision + 1,
                "authority": "declared_CRM_catalog_not_verified_SIIE",
            }
            record_operation(
                c,
                settings,
                c.agent_user,
                str(body.operation_id),
                "agents.program",
                resource,
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
            if item is not None:
                # PostgreSQL projects the legacy SQL bit as 0/1. Keep the HTTP
                # contract boolean so a read/edit round trip passes Strict.
                item = {**item, "Active": bool(item["Active"])}
            return {
                "exists": item is not None,
                "revision": item["Revision"] if item else 0,
                "program": item,
                "commercial": read_profile(c, settings, program_id) if item else None,
                "siie_source": (local_source(c, settings, program_id) or local_source(c, settings, program_id, 'program')) if item else None,
                "authority": "declared_CRM_catalog_not_verified_SIIE",
            }

    @app.post("/api/v1/agents/profiles/{agent_id}/restore-version")
    def restore(agent_id: UUID, body: Restore):
        return service.restore_version(str(agent_id), body)

    @app.post("/api/v1/agents/conversations/{conversation_id}/draft")
    async def draft(conversation_id: UUID, body: Draft):
        return await service.draft_conversation(str(conversation_id), body)
