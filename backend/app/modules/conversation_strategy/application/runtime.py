"""Local strategy endpoints; no channel delivery or provider activation."""

from uuid import UUID

import pyodbc
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.modules.conversation_analysis.application.runtime import binding
from app.modules.catalog.domain.contracts import CatalogUnavailable
from app.modules.conversation_strategy.api.router import ConversationStrategy
from app.sql_workspace import Identifier
from app.modules.conversation_strategy.domain.models import AutonomyWrite, PauseWrite, StrategyFeedbackWrite


def install_strategy(app):
    repository = ConversationStrategy(app.state.sql_workspace)
    app.state.conversation_strategy = repository
    app.state.analysis_worker.strategy = repository
    router = APIRouter(prefix="/api/local/crm/strategy", tags=["local-strategy"])

    def call(request, conversation, method, *args):
        if request.app.state.settings.mode != "local_sql_copy":
            raise HTTPException(503, "local_sql_copy_disabled")
        try:
            policy = request.app.state.conversation_analysis.configuration()["policy"]
            current = binding(request.app.state.ai_service, policy)
            value = getattr(repository, method)(str(UUID(conversation)), *args, current)
            return JSONResponse(value, headers={"Cache-Control": "no-store"})
        except (pyodbc.Error, CatalogUnavailable):
            raise HTTPException(503, "strategy_storage_unavailable") from None

    @router.get("/conversations/{conversation_id}")
    def read(request: Request, conversation_id: Identifier):
        return call(request, conversation_id, "read")

    @router.post("/conversations/{conversation_id}/autonomy")
    def autonomy(request: Request, conversation_id: Identifier, body: AutonomyWrite):
        return call(request, conversation_id, "mutate", "autonomy", body)

    @router.post("/conversations/{conversation_id}/pause")
    def pause(request: Request, conversation_id: Identifier, body: PauseWrite):
        return call(request, conversation_id, "mutate", "pause", body)

    @router.post("/conversations/{conversation_id}/feedback")
    def feedback(
        request: Request, conversation_id: Identifier, body: StrategyFeedbackWrite
    ):
        return call(request, conversation_id, "mutate", "feedback", body)

    app.include_router(router)
