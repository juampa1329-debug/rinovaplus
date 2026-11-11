"""P6 session-scoped source and memory API, mounted only by its own profile."""

from typing import Literal

from fastapi import Request

from app.institutional.db import uid
from app.institutional.knowledge import Knowledge
from app.institutional.knowledge_models import (
    Evaluation,
    RecordWrite,
    Search,
    Transition,
    Upload,
)


def install(app, settings):
    service = Knowledge(settings)

    @app.get("/api/institution/knowledge/options")
    @app.get("/api/institution/memory/options")
    def options(request: Request):
        from app.institutional.agent_catalog import Catalog
        from app.institutional.db import rows, uid

        with service.tx(request.state.authority) as (c, _):
            programs = Catalog(settings).programs(c, 0, 300)
            stages = rows(
                c,
                (
                    "SELECT StageId,Name,ProgramId FROM crm_agents.Stage WHERE "
                    "ApprovedRevision=Revision ORDER BY ProgramId,Name"
                ),
            )
            return {
                "programs": programs["items"],
                "stages": [
                    {
                        "id": uid(str(v["StageId"])),
                        "name": v["Name"],
                        "program_id": v["ProgramId"],
                    }
                    for v in stages
                ],
                "has_more": programs["has_more"],
                "authority": "declared_CRM_not_verified_SIIE",
            }

    @app.get("/api/institution/knowledge")
    def knowledge(request: Request):
        return service.listing(request.state.authority, "document")

    @app.post("/api/institution/knowledge/upload")
    def upload(request: Request, body: Upload):
        return service.upload(request.state.authority, body)

    @app.post("/api/institution/knowledge/search")
    def search(request: Request, body: Search):
        return service.search(request.state.authority, body)

    @app.post("/api/institution/knowledge/evaluate")
    def evaluate(request: Request, body: Evaluation):
        return service.search(request.state.authority, body)

    @app.get("/api/institution/memory")
    def memories(request: Request, kind: Literal["collective", "dna"] = "collective"):
        return service.listing(request.state.authority, kind)

    # The collection selects the kind at commit too: a caller cannot move a
    # private record to a global editor or mutate another conversation by UUID.
    @app.put("/api/institution/knowledge/records/{record}")
    def save(request: Request, record: str, body: RecordWrite):
        from fastapi import HTTPException

        if body.kind != "document":
            raise HTTPException(422, "knowledge_document_required")
        return service.save(request.state.authority, uid(record), body)

    @app.put("/api/institution/memory/records/{record}")
    def save_memory(request: Request, record: str, body: RecordWrite):
        from fastapi import HTTPException

        if body.kind not in {"collective", "dna"}:
            raise HTTPException(422, "knowledge_shared_kind_required")
        return service.save(request.state.authority, uid(record), body)

    @app.get("/api/institution/knowledge/records/{record}/history")
    @app.get("/api/institution/memory/records/{record}/history")
    def history(request: Request, record: str):
        return service.history(request.state.authority, uid(record))

    @app.post("/api/institution/knowledge/records/{record}/{action}")
    @app.post("/api/institution/memory/records/{record}/{action}")
    def transition(request: Request, record: str, action: str, body: Transition):
        return service.transition(request.state.authority, uid(record), action, body)

    @app.get("/api/institution/conversation-memory/{conversation}")
    def private(request: Request, conversation: str):
        return service.listing(request.state.authority, conversation=uid(conversation))

    @app.put("/api/institution/conversation-memory/{conversation}/{record}")
    def save_private(
        request: Request, conversation: str, record: str, body: RecordWrite
    ):
        return service.save(
            request.state.authority, uid(record), body, conversation=uid(conversation)
        )

    @app.get("/api/institution/conversation-memory/{conversation}/{record}/history")
    def private_history(request: Request, conversation: str, record: str):
        return service.history(request.state.authority, uid(record), uid(conversation))

    @app.post("/api/institution/conversation-memory/{conversation}/{record}/{action}")
    def private_transition(
        request: Request, conversation: str, record: str, action: str, body: Transition
    ):
        return service.transition(
            request.state.authority, uid(record), action, body, uid(conversation)
        )
