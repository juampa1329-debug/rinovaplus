"""Compose local workflows, isolated AI and opt-in read-only SQL catalogs."""

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import Settings
from app.contracts import register_contracts
from app.database_connections import install_database_connections
from app.environment import load_environment
from app.health import IntegrationReadiness, ProcessHealth, integration_readiness
from app.local_openapi import install_local_openapi
from app.modules.admissions import install_admissions
from app.modules.ai import install_ai
from app.modules.ai.application.service import AiService
from app.modules.campaigns.router import install_campaigns
from app.modules.catalog import router
from app.modules.catalog.infrastructure import SqlCatalogReader
from app.modules.channels import install_channels
from app.modules.clients import install_clients
from app.modules.contacts import install_contacts
from app.modules.conversation_analysis import install_analysis
from app.modules.conversation_events import install_events
from app.modules.conversation_strategy import install_strategy
from app.modules.crm_configuration import install_crm_configuration
from app.modules.inbox import install_inbox, install_inbox_operations
from app.modules.webhooks import install_webhooks
from app.runtime_capabilities import install_runtime_capabilities
from app.schemas import InvalidInput
from app.sql_workspace import LocalCopyCatalogReader, install_sql_workspace


def create_app(
    ai_service: AiService | None = None, *, settings: Settings | None = None
) -> FastAPI:
    if settings is None:
        load_environment()
        settings = Settings.from_environment()
    if settings.mode == "local_channels":
        from app.channels_app import create_channels_app

        return create_channels_app(settings)
    if settings.mode == "local_foundation":
        from app.foundation_app import create_foundation_app

        return create_foundation_app(settings)
    if settings.mode == "local_channels_ui":
        from app.channels_ui_app import create_channels_ui_app

        return create_channels_ui_app(settings)

    @asynccontextmanager
    async def lifespan(application):
        # Pytest sets this only around the active test call. The isolated suite
        # blocks pyodbc deliberately, so its TestClient must not start workers.
        workers_enabled = settings.mode == "local_sql_copy" and not os.environ.get(
            "PYTEST_CURRENT_TEST"
        )
        if workers_enabled:
            application.state.event_worker.start()
            application.state.analysis_worker.start()
            application.state.channel_worker.start()
            application.state.admissions_ai_worker.start()
            application.state.campaign_worker.start()
        try:
            yield
        finally:
            if workers_enabled:
                await asyncio.to_thread(application.state.admissions_ai_worker.stop)
                await asyncio.to_thread(application.state.campaign_worker.stop)
                await asyncio.to_thread(application.state.channel_worker.stop)
                await asyncio.to_thread(application.state.analysis_worker.stop)
                await asyncio.to_thread(application.state.event_worker.stop)

    application = FastAPI(
        title="CRM CBN local integration", version="0.0.1", lifespan=lifespan
    )
    application.state.settings = settings
    install_runtime_capabilities(application)
    application.state.catalog_reader = (
        LocalCopyCatalogReader(settings)
        if settings.mode == "local_sql_copy"
        else SqlCatalogReader(settings)
    )
    install_ai(application, ai_service)
    install_database_connections(application)
    install_sql_workspace(application)
    install_clients(application)
    install_crm_configuration(application)
    install_contacts(application)
    install_inbox(application)
    install_inbox_operations(application)
    install_events(application)
    install_analysis(application)
    install_strategy(application)
    install_admissions(application)
    install_channels(application)
    from app.modules.channels.workers import ChannelWorkers

    application.state.channel_worker = ChannelWorkers(application)
    from app.modules.ai.api.admissions import install_admissions_ai

    install_admissions_ai(application)
    from app.modules.agents.router import install_agents

    install_agents(application)
    install_campaigns(application)
    application.include_router(router)
    if settings.mode == "local_readonly_catalog":
        application.add_middleware(
            TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1"]
        )
        application.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.catalog_origins),
            allow_methods=["GET"],
            allow_headers=["Authorization"],
        )

    @application.exception_handler(RequestValidationError)
    async def invalid_input(
        request: Request, exception: RequestValidationError
    ) -> JSONResponse:
        # Preserve each transport envelope without reflecting submitted values.
        if request.url.path.startswith(
            (
                "/api/ai/",
                "/api/v1/ai/",
                "/api/v1/agents",
                "/api/v1/campaigns/",
                "/api/v1/broadcasts",
                "/api/v1/crm/predictions",
                "/api/local/clients",
                "/api/local/crm",
                "/api/local/admissions",
                "/api/local/database",
            )
        ):
            return JSONResponse({"code": "invalid_request"}, status_code=422)
        return JSONResponse(status_code=422, content=InvalidInput().model_dump())

    @application.get(
        "/health/live", response_model=ProcessHealth, operation_id="health_live"
    )
    def live() -> ProcessHealth:
        return ProcessHealth(mode=settings.mode)

    @application.get(
        "/health/ready",
        response_model=IntegrationReadiness,
        status_code=503,
        operation_id="health_ready",
    )
    def ready() -> IntegrationReadiness:
        return integration_readiness()

    install_webhooks(application)
    register_contracts(application)
    install_local_openapi(application)
    return application


app = create_app()
