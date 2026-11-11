"""Guarded local admissions API; settings/key vault remains the existing owner."""

import re
from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from pydantic import Field

from app.modules.ai.domain.models import StrictModel, MediaChatRequest, HistoryMessage
from app.modules.ai.infrastructure.credentials import CredentialRequest
from app.modules.ai.infrastructure.providers import AiError
from app.modules.ai.application.admissions import AdmissionsService, AdmissionsWorker, installed, policy_row
from app.modules.ai.application.admissions_prompt import AdmissionsPolicy
from app.modules.knowledge.service import add_document, extract, search


class PolicyWrite(StrictModel):
    revision: int = Field(ge=0)
    enabled: bool
    settings: AdmissionsPolicy


class StateWrite(StrictModel):
    revision: int = Field(ge=0)
    state: str = Field(pattern=r"^(published|disabled|deleted)$")
    official: bool = False


class ResetWrite(StrictModel):
    revision: int = Field(ge=0)


class ContextRequest(StrictModel):
    question: str = Field(min_length=1, max_length=4000)
    program_id: int | None = Field(default=None, ge=1)
    semester: int | None = Field(default=None, ge=1, le=12)


class PreviewRequest(MediaChatRequest):
    preview_model: str = Field(default="", max_length=200, pattern=r"^[A-Za-z0-9._:/-]*$")
    program_id: int | None = Field(default=None, ge=1)
    semester: int | None = Field(default=None, ge=1, le=12)


class PreviewSessionRequest(StrictModel):
    preview_model: str = Field(default="", max_length=200, pattern=r"^[A-Za-z0-9._:/-]*$")
    question: str = Field(default="", max_length=2000)
    program_id: int | None = Field(default=None, ge=1)
    semester: int | None = Field(default=None, ge=1, le=12)


PreviewRequest.model_rebuild(_types_namespace={"HistoryMessage": HistoryMessage})


def install_admissions_ai(application):
    service = AdmissionsService(application)
    application.state.admissions_ai = service
    application.state.admissions_ai_worker = AdmissionsWorker(service)
    router = APIRouter(prefix="/api/v1/ai")

    @router.get("/settings")
    def settings():
        return service.settings()

    @router.get("/institutional/programs")
    def institutional_programs(offset: int = Query(default=0, ge=0, le=100000), limit: int = Query(default=150, ge=1, le=150)):
        return service.academic_programs(offset, limit)

    @router.put("/settings")
    def save_settings(request: PolicyWrite):
        return service.save_settings(request)

    @router.put("/settings/openrouter-key")
    def key(request: CredentialRequest):
        return service.ai.configure_connection(request.revision, provider="openrouter", key=request.api_key)

    @router.get("/knowledge")
    def documents(offset: int = Query(default=0, ge=0, le=100)):
        with service.transaction() as cursor:
            policy = policy_row(cursor)
            found = cursor.execute("SELECT d.DocumentId,d.Title,d.FileName,d.State,d.Revision,d.ByteLength,(SELECT COUNT(*) FROM crm_ai.KnowledgeChunk c WHERE c.DocumentId=d.DocumentId) FROM crm_ai.KnowledgeDocument d WHERE d.State<>'deleted' ORDER BY d.CreatedAt DESC,d.DocumentId OFFSET ? ROWS FETCH NEXT 26 ROWS ONLY", offset).fetchall()
            return {"items": [{"id": str(r[0]), "title": r[1], "filename": r[2], "state": r[3], "revision": r[4], "bytes": r[5], "chunks": r[6]} for r in found[:25]], "has_more": len(found) > 25, "knowledge_revision": policy["knowledge_revision"]}

    @router.get("/knowledge/search")
    def find(q: str = Query(min_length=1, max_length=2000)):
        with service.transaction() as cursor:
            installed(cursor)
            return {"sources": search(cursor, q), "method": "sql_lexical_index", "semantic_embeddings": False}

    @router.get("/knowledge/{document_id}/chunks")
    def chunks(document_id: UUID, offset: int = Query(default=0, ge=0, le=250)):
        with service.transaction() as cursor:
            installed(cursor)
            if not cursor.execute("SELECT 1 FROM crm_ai.KnowledgeDocument WHERE DocumentId=? AND State<>'deleted'", str(document_id)).fetchone():
                raise AiError("knowledge_document_not_found", 404)
            found = cursor.execute("SELECT ChunkId,PageNumber,Body,Ordinal FROM crm_ai.KnowledgeChunk WHERE DocumentId=? ORDER BY Ordinal OFFSET ? ROWS FETCH NEXT 11 ROWS ONLY", str(document_id), offset).fetchall()
            return {"items": [{"id": str(r[0]), "page": r[1], "text": r[2], "ordinal": r[3]} for r in found[:10]], "has_more": len(found) > 10}

    @router.put("/knowledge/{document_id}/content")
    async def upload(document_id: UUID, request: Request, filename: str = Query(min_length=1, max_length=160), title: str = Query(min_length=1, max_length=160)):
        # UUID in URL is an idempotency key: same byte hash/title replays safely.
        data = bytearray()
        async for part in request.stream():
            data.extend(part)
            if len(data) > 5_000_000:
                raise AiError("knowledge_size_limit", 413)
        if re.search(r"[\x00-\x1f/\\]", filename) or not title.strip():
            raise AiError("knowledge_metadata_invalid")
        from starlette.concurrency import run_in_threadpool
        import hashlib

        pages = await run_in_threadpool(extract, bytes(data), filename)
        with service.transaction(True) as cursor:
            installed(cursor)
            prior = cursor.execute("SELECT ContentHash,Title FROM crm_ai.KnowledgeDocument WHERE DocumentId=?", str(document_id)).fetchone()
            if prior:
                if bytes(prior[0]) != hashlib.sha256(data).digest() or prior[1] != title.strip():
                    raise AiError("knowledge_upload_id_conflict", 409)
                return {"id": str(document_id), "confirmed": True}
            identifier = add_document(cursor, filename, title.strip(), bytes(data), pages, str(document_id))
        return {"id": identifier, "state": "draft", "confirmed": True}

    @router.put("/knowledge/{document_id}")
    def state(document_id: UUID, request: StateWrite):
        if request.state == "published" and not request.official:
            raise AiError("knowledge_official_confirmation_required", 409)
        with service.transaction(True) as cursor:
            installed(cursor)
            cursor.execute("UPDATE crm_ai.KnowledgeDocument SET State=?,Revision=Revision+1,UpdatedAt=SYSUTCDATETIME() WHERE DocumentId=? AND Revision=? AND State<>'deleted'", request.state, str(document_id), request.revision)
            if cursor.rowcount != 1:
                raise AiError("knowledge_revision_conflict", 409)
            cursor.execute("UPDATE crm_ai.AdmissionsPolicy SET KnowledgeRevision=KnowledgeRevision+1 WHERE PolicyId=1")
            # Invalidate unsent generated responses; in-flight delivery cannot be revoked.
            cursor.execute("UPDATE q SET State='failed',LastError='knowledge_revision_changed',LeaseId=NULL FROM crm_channels.outbound_queue q JOIN crm_ai.ResponseJob j ON j.ResponseMessageId=q.MessageId JOIN crm_channels.MessageRoute r ON r.QueueId=q.QueueId WHERE r.StartedAt IS NULL AND q.State IN('queued','sending')")
            if request.state == "deleted":
                cursor.execute("DELETE t FROM crm_ai.KnowledgeTerm t JOIN crm_ai.KnowledgeChunk c ON c.ChunkId=t.ChunkId WHERE c.DocumentId=?", str(document_id))
                cursor.execute("DELETE crm_ai.KnowledgeChunk WHERE DocumentId=?", str(document_id))
        return {"confirmed": True, "revision": request.revision + 1}

    @router.get("/conversations")
    def conversations(offset: int = Query(default=0, ge=0, le=100000)):
        with service.transaction() as cursor:
            installed(cursor)
            rows = cursor.execute("SELECT c.ConversationId,p.Name,c.ControlMode,COALESCE(m.Revision,0),COALESCE(m.Generation,0) FROM crm.Conversation c JOIN crm.Contact p ON p.ContactId=c.ContactId LEFT JOIN crm_ai.ProspectMemory m ON m.ConversationId=c.ConversationId ORDER BY c.UpdatedAt DESC,c.ConversationId OFFSET ? ROWS FETCH NEXT 26 ROWS ONLY", offset).fetchall()
            return {"items": [{"id": str(r[0]), "name": r[1], "control": r[2], "memory_revision": r[3], "generation": r[4]} for r in rows[:25]], "has_more": len(rows) > 25}

    @router.get("/conversations/{conversation_id}/memory")
    def memory(conversation_id: UUID):
        return service.memory(str(conversation_id))

    @router.delete("/conversations/{conversation_id}/memory")
    @router.post("/conversations/{conversation_id}/context-reset")
    def reset(conversation_id: UUID, request: ResetWrite):
        return service.reset(str(conversation_id), request.revision)

    @router.post("/conversations/{conversation_id}/context")
    def context(conversation_id: UUID, request: ContextRequest):
        return service.context(str(conversation_id), request.question, request.program_id, request.semester)

    @router.post("/conversations/{conversation_id}/preview")
    async def preview(conversation_id: UUID, request: PreviewRequest):
        try:
            return await service.preview(str(conversation_id), request)
        except AiError as error:
            phase = getattr(error, "phase", None)
            provider = getattr(error, "provider", None)
            diagnostics = getattr(error, "diagnostics", {})
            safe = {name: diagnostics[name] for name in ("kind", "response_bytes", "content_type", "error_class") if name in diagnostics}
            return JSONResponse({"code": error.code, "upstream_status": error.upstream_status, "phase": phase if phase in ("catalog", "generation") else None, "provider": provider if provider in ("gemini", "openrouter", "openai", "anthropic", "xai", "nvidia", "groq", "mistral", "kimi", "hermes") else None, "diagnostics": safe}, status_code=error.status, headers={"Cache-Control": "no-store"})

    @router.post("/conversations/{conversation_id}/preview-session")
    def preview_session(conversation_id: UUID, request: PreviewSessionRequest):
        return service.preview_session(str(conversation_id), request.preview_model, request.question, request.program_id, request.semester)

    @router.get("/jobs")
    def jobs():
        with service.transaction() as cursor:
            installed(cursor)
            rows = cursor.execute("SELECT TOP(25) MessageId,ConversationId,State,Attempts,LastError,ResponseMessageId,TaskId,CreatedAt,Result FROM crm_ai.ResponseJob ORDER BY CreatedAt DESC").fetchall()
            import json
            return {"items": [{"message_id": str(r[0]), "conversation_id": str(r[1]), "state": r[2], "attempts": r[3], "error": r[4], "response_message_id": str(r[5]) if r[5] else None, "task_id": str(r[6]) if r[6] else None, "created_at": r[7], "model": json.loads(r[8]).get("model")} for r in rows]}

    application.include_router(router)
