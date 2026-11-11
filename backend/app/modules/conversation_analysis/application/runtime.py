"""Local analysis runtime: explicit policy, fixed gateway, no channel delivery."""

import asyncio
import json
import sys
from datetime import datetime, timezone
from threading import Event, Thread
from uuid import UUID

import pyodbc
from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.modules.ai.domain.models import AiSettings
from app.modules.ai.infrastructure.providers import AiError, ProviderGateway
from app.modules.conversation_analysis.domain.models import (
    ANALYSIS_PROMPT,
    PROMPT_VERSION,
    AnalysisFeedbackWrite,
    AnalysisPolicyWrite,
)
from app.modules.catalog.domain.contracts import CatalogUnavailable
from app.modules.conversation_analysis.api.router import ConversationAnalysis
from app.modules.conversation_events.api.router import RetryRequest
from app.sql_workspace import Identifier, SqlWorkspace
from app.modules.conversation_strategy.domain.models import (
    STRATEGY_PROMPT,
    validate_result,
)


def connection(service):
    state = service.connection_snapshot()
    return {
        "outbound": state["outbound_enabled"],
        "credentialRevision": state["credential_revision"],
        "providers": [
            {"id": p["id"], "configured": p["configured"]}
            for p in state["providers"]
            if p["id"]
            in (
                "gemini",
                "nvidia",
                "openai",
                "anthropic",
                "hermes",
                "groq",
                "mistral",
                "openrouter",
                "kimi",
                "xai",
            )
        ],
        "serverCredentials": not state["credential_storage_available"],
    }


def binding(service, policy):
    if not policy:
        return None
    credentials = service.connection_snapshot()
    return ":".join(
        [
            policy["revision"],
            PROMPT_VERSION,
            str(bool(credentials["outbound_enabled"])),
            str(credentials["credential_revision"]),
        ]
    )


class AnalysisWorker:
    def __init__(self, repository, service):
        self.repository = repository
        self.service = service
        self.stop_event = Event()
        self.thread = None
        self.health = {"state": "stopped", "lastCycleAt": None}
        self.catalog_binding = None
        self.models = {}
        self.strategy = None

    def start(self):
        self.thread = Thread(
            target=self.run, name="crm-conversation-analysis", daemon=True
        )
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=15)

    def run(self):
        while not self.stop_event.is_set():
            try:
                state = asyncio.run(self.cycle())
                self.health = {
                    "state": state,
                    "lastCycleAt": datetime.now(timezone.utc).isoformat(),
                }
            except HTTPException as error:
                self.health = {
                    **self.health,
                    "state": "budget_exhausted"
                    if error.status_code == 429
                    else "storage_unavailable",
                }
            except AiError as error:
                self.health = {**self.health, "state": error.code}
            except Exception:
                self.health = {**self.health, "state": "unavailable"}
            self.stop_event.wait(5)
        self.health = {**self.health, "state": "stopped"}

    async def cycle(self):
        config = self.repository.configuration()
        policy = config["policy"]
        if not policy or not policy["enabled"]:
            return "disabled"
        self.service.require_outbound()
        if not self.service.gateway.keys.get(policy["provider"]):
            return "provider_key_missing"
        current = binding(self.service, policy)
        if self.strategy:
            self.strategy.execute(current)
        legacy_gateway = getattr(
            sys.modules.get(__name__), "ProviderGateway", ProviderGateway
        )
        gateway = legacy_gateway(
            dict(self.service.gateway.keys), self.service.gateway.transport
        )
        if self.catalog_binding != current:
            self.models = {
                item.id: item for item in await gateway.models(policy["provider"])
            }
            self.catalog_binding = current
        model = self.models.get(policy["model"])
        if not model or not model.temperature:
            return "model_unavailable"
        if model.output_limit and policy["outputTokens"] > model.output_limit:
            return "model_output_limit_exceeded"
        # Reserve before generation; uncertain calls still consume budget.
        job = self.repository.reserve(current)
        if not job:
            return "running"
        try:
            self.service.require_outbound()
            latest = self.repository.configuration()["policy"]
            if binding(self.service, latest) != current or not latest["enabled"]:
                self.repository.complete(job, {}, None)
                return "configuration_changed"
            if not self.repository.job_current(job):
                self.repository.complete(job, {}, None)
                return "input_changed"
            settings = AiSettings(
                enabled=True,
                provider=policy["provider"],
                model=policy["model"],
                max_tokens=policy["outputTokens"],
                output_tokens=policy["outputTokens"],
                temperature=0.0,
            )
            raw = await gateway.generate(
                policy["provider"],
                policy["model"],
                settings,
                ANALYSIS_PROMPT + STRATEGY_PROMPT,
                [
                    {
                        "role": "user",
                        "content": json.dumps(job["payload"], ensure_ascii=False),
                    }
                ],
            )
            result, strategy = validate_result(raw, job["references"], job["known"])
            self.service.require_outbound()
            latest = self.repository.configuration()["policy"]
            current = binding(self.service, latest)
            if strategy is None:
                self.repository.complete(job, result, current)
            else:
                self.repository.complete(job, result, current, strategy)
        except AiError as error:
            self.repository.fail(job, error.code)
        except (ValueError, TypeError, KeyError):
            self.repository.fail(job, "analysis_output_invalid")
        except Exception:
            self.repository.fail(job, "analysis_processing_unavailable")
        return "running"


def install_analysis(app: FastAPI):
    repository = ConversationAnalysis(SqlWorkspace(app.state.settings))
    service = app.state.ai_service
    app.state.conversation_analysis = repository
    app.state.analysis_worker = AnalysisWorker(repository, service)
    router = APIRouter(prefix="/api/local/crm/analysis", tags=["local-analysis"])

    def call(request, method, *args):
        if request.app.state.settings.mode != "local_sql_copy":
            raise HTTPException(503, "local_sql_copy_disabled")
        try:
            data = getattr(request.app.state.conversation_analysis, method)(*args)
            return data
        except (pyodbc.Error, CatalogUnavailable):
            raise HTTPException(503, "analysis_storage_unavailable") from None

    def response(value):
        return JSONResponse(value, headers={"Cache-Control": "no-store"})

    @router.get("/configuration")
    def configuration(request: Request):
        data = call(request, "configuration")
        worker = request.app.state.analysis_worker
        return response(
            {
                **data,
                "connection": connection(service),
                "worker": {
                    **worker.health,
                    "alive": bool(worker.thread and worker.thread.is_alive()),
                },
            }
        )

    @router.put("/policy")
    def policy(request: Request, body: AnalysisPolicyWrite):
        def validate():
            if not body.enabled:
                return
            service.require_outbound()
            if not service.gateway.keys.get(body.provider):
                raise HTTPException(409, "provider_key_missing")
            model = service.catalogs.get(body.provider, {}).get(body.model)
            if not model or not model.temperature:
                raise HTTPException(409, "model_catalog_required")
            if model.output_limit and body.outputTokens > model.output_limit:
                raise HTTPException(422, "model_output_limit_exceeded")

        return response(call(request, "save_policy", body, validate))

    @router.post("/retry")
    def retry(request: Request, body: RetryRequest):
        return response(call(request, "retry", str(UUID(body.operationId))))

    @router.get("/conversations/{conversation_id}")
    def conversation(request: Request, conversation_id: Identifier):
        config = call(request, "configuration")
        return response(
            call(
                request,
                "conversation",
                str(UUID(conversation_id)),
                binding(service, config["policy"]),
            )
        )

    @router.post("/conversations/{conversation_id}/feedback")
    def feedback(
        request: Request, conversation_id: Identifier, body: AnalysisFeedbackWrite
    ):
        return response(call(request, "feedback", str(UUID(conversation_id)), body))

    app.include_router(router)
