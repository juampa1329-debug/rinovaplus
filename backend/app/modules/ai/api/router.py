"""Loopback-only HTTP entrypoints for an explicitly enabled local AI test bench."""

import ipaddress
import os
import re
import sys
from pathlib import Path

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

from app.modules.ai.application.service import AiService, SettingsRepository
from app.modules.ai.domain.models import (
    PROVIDERS,
    ChatRequest,
    CredentialProvider,
    MediaChatRequest,
    ModelStatusRequest,
    Provider,
    SaveSettings,
    TestRequest,
)
from app.modules.ai.infrastructure.credentials import (
    CredentialDeleteRequest,
    CredentialRepository,
    CredentialRequest,
    OutboundRequest,
)
from app.modules.ai.infrastructure.providers import AiError, ProviderGateway

ALLOWED_HOSTS = {
    f"{host}:{port}"
    for host in ("127.0.0.1", "localhost", "[::1]")
    for port in (8000, 8002, 5173, 5175, 4173, 4175)
}
ALLOWED_ORIGINS = {"http://" + host for host in ALLOWED_HOSTS}


class LocalAiGuard:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        state = getattr(scope.get("app"), "state", None)
        foundation = (
            getattr(getattr(state, "settings", None), "mode", None)
            in ("local_foundation", "local_channels", "local_channels_ui")
        )
        if scope["type"] != "http" or not (
            (foundation and scope["path"].startswith("/api/"))
            or scope["path"].startswith("/api/ai")
            or scope["path"].startswith("/api/v1/ai/")
            or scope["path"].startswith("/api/v1/agents")
            or scope["path"] == "/api/local/clients"
            or scope["path"].startswith("/api/local/clients/")
            or scope["path"].startswith("/api/local/crm")
            or scope["path"].startswith("/api/local/admissions")
            or scope["path"].startswith("/api/local/database")
            or scope["path"].startswith("/api/v1/channels")
            or scope["path"].startswith("/api/v1/social-comments")
            or scope["path"].startswith("/api/v1/campaigns/")
            or scope["path"].startswith("/api/v1/broadcasts")
            or scope["path"].startswith("/api/v1/crm/predictions")
            or (
                scope["path"].startswith("/api/v1/catalog/")
                and scope["app"].state.settings.mode == "local_sql_copy"
            )
        ):
            return await self.app(scope, receive, send)
        headers = dict(scope["headers"])
        try:
            local = ipaddress.ip_address(scope.get("client", ("",))[0]).is_loopback
        except ValueError:
            local = False
        host = headers.get(b"host", b"").decode("latin-1").lower()
        origin = headers.get(b"origin", b"").decode("latin-1")
        allowed = (
            local
            and host in ALLOWED_HOSTS
            and (not origin or origin in ALLOWED_ORIGINS)
            and headers.get(b"x-crm-local") == b"1"
        )
        if not allowed:
            return await JSONResponse({"code": "local_access_required"}, 403)(
                scope, receive, send
            )
        binary_media = not foundation and scope["method"] == "PUT" and re.fullmatch(
            r"/api/local/crm/inbox/conversations/[0-9a-fA-F-]{36}/media/[0-9a-fA-F-]{36}",
            scope["path"],
        )
        binary_knowledge = (
            not foundation and scope["method"] == "PUT" and re.fullmatch(
                r"/api/v1/ai/knowledge/[0-9a-fA-F-]{36}/content", scope["path"]
            )
        )
        if binary_media or binary_knowledge:
            if (
                headers.get(b"content-type", b"").split(b";")[0].strip()
                != b"application/octet-stream"
            ):
                return await JSONResponse({"code": "binary_media_required"}, 415)(
                    scope, receive, send
                )
            # Only this exact upload consumes the stream itself under a 5 MB limit.
            return await self.app(scope, receive, send)
        if (
            scope["method"] in ("POST", "PUT")
            and headers.get(b"content-type", b"").split(b";")[0].strip()
            != b"application/json"
        ):
            return await JSONResponse({"code": "json_required"}, 415)(
                scope, receive, send
            )
        configuration_write = (
            not foundation and scope["method"] == "PUT" and re.fullmatch(
                r"/api/v1/agents/profiles/[0-9a-fA-F-]{36}", scope["path"]
            )
        )
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            # Agent configuration text has no application length ceiling.
            if not configuration_write and len(body) > (
                5_700_000 if scope["path"] == "/api/ai/media-chat" else 64000
            ):
                return await JSONResponse({"code": "request_too_large"}, 413)(
                    scope, receive, send
                )
            if not message.get("more_body", False):
                break
        delivered = False

        async def bounded_receive():
            nonlocal delivered
            if delivered:
                return await receive()
            delivered = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        async def private_send(message):
            if message["type"] == "http.response.start" and scope["path"].startswith(
                ("/api/v1/channels", "/api/v1/social-comments", "/api/v1/ai/", "/api/v1/agents")
            ):
                message["headers"] = [
                    (k, v)
                    for k, v in message.get("headers", [])
                    if k.lower() != b"cache-control"
                ] + [(b"cache-control", b"no-store")]
            await send(message)

        await self.app(scope, bounded_receive, private_send)


def install_ai(application: FastAPI, service: AiService | None = None):
    if service is None:
        legacy_os = getattr(sys.modules.get(__name__), "os", os)
        state_directory = Path(
            legacy_os.environ.get("CRM_AI_STATE_DIR")
            or Path(__file__).resolve().parents[2] / ".local"
        )
        if not state_directory.is_absolute():
            raise ValueError("CRM_AI_STATE_DIR must be an absolute directory")
        repository = SettingsRepository(state_directory / "ai-settings.json")
        credentials = (
            CredentialRepository(repository.path.parent / "ai-credentials.dpapi")
            if legacy_os.name == "nt"
            else None
        )
        if application.state.settings.mode == "local_sql_copy":
            from app.modules.ai.infrastructure.sql_repository import (
                SqlAiStore,
                SqlCredentialRepository,
                SqlSettingsRepository,
            )

            store = SqlAiStore(application.state.settings, repository.path)
            repository = SqlSettingsRepository(store)
            credentials = SqlCredentialRepository(store)
        service = AiService(
            repository,
            ProviderGateway(
                {
                    provider: legacy_os.environ.get(variable, "")
                    for provider, variable in PROVIDERS.items()
                }
            ),
            legacy_os.environ.get("CRM_AI_OUTBOUND_ENABLED") == "true",
            credentials,
        )
    application.state.ai_service = service
    application.add_middleware(LocalAiGuard)
    router = APIRouter(prefix="/api/ai")

    @application.exception_handler(AiError)
    async def ai_error(_request: Request, error: AiError):
        return JSONResponse(
            {"code": error.code},
            status_code=error.status,
            headers={"Cache-Control": "no-store"},
        )

    @application.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, error: RequestValidationError):
        result = {"code": "invalid_request"}
        if request.url.path.startswith("/api/v1/agents"):
            from app.modules.agents.router import validation_fields

            result["fields"] = validation_fields(error.errors())
        return JSONResponse(result, status_code=422)

    @router.get("/settings")
    async def settings():
        current = service.repository.read()
        return JSONResponse(
            {
                **current.model_dump(),
                **service.connection_snapshot(),
            },
            headers={"Cache-Control": "no-store"},
        )

    @router.put("/settings")
    async def save(request: SaveSettings):
        return service.save(request)

    @router.put("/credentials/{provider}")
    async def credential(provider: CredentialProvider, request: CredentialRequest):
        return JSONResponse(
            service.configure_connection(
                request.revision, provider=provider, key=request.api_key
            ),
            headers={"Cache-Control": "no-store"},
        )

    @router.put("/outbound")
    async def outbound(request: OutboundRequest):
        return JSONResponse(
            service.configure_connection(request.revision, outbound=request.enabled),
            headers={"Cache-Control": "no-store"},
        )

    @router.delete("/credentials/{provider}")
    async def delete_credential(
        provider: CredentialProvider, request: CredentialDeleteRequest
    ):
        return JSONResponse(
            service.configure_connection(
                request.revision, provider=provider, remove=True
            ),
            headers={"Cache-Control": "no-store"},
        )

    @router.post("/models/{provider}")
    async def models(provider: Provider):
        result = await service.load_models(provider)
        return {"models": result}

    @router.post("/model-status/{provider}")
    async def model_status(provider: str, request: ModelStatusRequest):
        if (
            provider not in PROVIDERS
            and provider != "piper"
            or provider in ("tavily", "brave", "serpapi")
        ):
            raise AiError("invalid_provider")
        return JSONResponse(
            await service.model_status(provider, request),
            headers={"Cache-Control": "no-store"},
        )

    @router.post("/audio-models/groq")
    async def audio_models():
        return {"models": await service.load_audio_models()}

    @router.post("/test")
    async def test(request: TestRequest):
        return await service.test(request)

    @router.post("/chat")
    async def chat(request: ChatRequest):
        return JSONResponse(
            await service.chat(request), headers={"Cache-Control": "no-store"}
        )

    @router.post("/voice-catalog/{provider}")
    async def voice_catalog(provider: str):
        return await service.load_voice_catalog(provider)

    @router.post("/conversation")
    async def conversation():
        return service.create_conversation()

    @router.post("/media-chat")
    async def media_chat(request: MediaChatRequest):
        return JSONResponse(
            await application.state.admissions_ai.assistant_media_chat(request)
            if application.state.settings.mode == "local_sql_copy"
            else await service.media_chat(request), headers={"Cache-Control": "no-store"}
        )

    @router.get("/media/{identifier}")
    async def audio(identifier: str):
        from starlette.responses import Response

        data, mime = service.audio_media(identifier)
        return Response(
            data,
            media_type=mime,
            headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
        )

    application.include_router(router)
