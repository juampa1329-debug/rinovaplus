"""Explicit composition for the restored foundation, without workers or providers."""

import pyodbc
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.modules.ai.api.router import LocalAiGuard
from app.modules.catalog.domain.contracts import CatalogUnavailable
from app.modules.clients.api.router import install_clients
from app.modules.crm_configuration.application.service import install_crm_configuration
from app.modules.inbox.application.service import install_inbox
from app.runtime_capabilities import install_runtime_capabilities
from app.sql_target import validate_settings
from app.sql_workspace import install_sql_workspace


def create_foundation_app(settings):
    validate_settings(settings)
    application = FastAPI(
        title="CRM CBN restored foundation",
        version="SQL-C4",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    application.state.settings = settings
    install_runtime_capabilities(application)
    install_sql_workspace(application)
    install_clients(application)
    install_crm_configuration(application)
    install_inbox(application)
    application.add_middleware(LocalAiGuard)

    @application.exception_handler(RequestValidationError)
    async def invalid_input(request: Request, exception: RequestValidationError):
        return JSONResponse({"code": "invalid_request"}, status_code=422)

    @application.middleware("http")
    async def private_response(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    @application.get("/health/live")
    def live():
        return {"status": "alive", "mode": settings.mode}

    @application.get("/health/ready", status_code=503)
    def ready():
        return {
            "status": "not_ready",
            "reason": "Restored foundation only; integrations pending",
        }

    @application.get("/api/local/foundation")
    def status():
        try:
            with application.state.sql_workspace.transaction():
                pass
        except (pyodbc.Error, CatalogUnavailable):
            raise HTTPException(503, "local_sql_unavailable") from None
        return {
            "contract": "B000+B001+B006",
            "scope": "restored_rehearsal_only",
            "available": [
                "contacts",
                "conversations",
                "local_messages",
                "crm_configuration",
                "basic_inbox",
            ],
            "unavailable": [
                "academic_catalog",
                "academic_profile",
                "assignment",
                "assessment",
                "channels",
                "media",
                "agents",
                "campaigns",
                "providers",
                "workers",
            ],
            "institutional_sql2019_accepted": False,
        }

    @application.api_route(
        "/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"]
    )
    def unsupported(path: str):
        raise HTTPException(503, "foundation_capability_unavailable")

    return application
