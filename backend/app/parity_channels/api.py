"""Separate loopback-only C12 rehearsal API. No main-app mount or providers."""

import hmac
import time
from typing import Annotated, Literal
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.branding import PRODUCT_NAME
from app.parity_channels.policy import VERSION, identifier
from app.parity_channels.repository import PROJECTIONS, Repository


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)


class Application(Strict):
    Provider: Literal["meta", "tiktok"]
    ClientId: str = Field(min_length=1, max_length=128)
    ApiVersion: str = Field(max_length=20)
    IssuerProfile: Literal[
        "meta_whatsapp", "facebook_login", "instagram_login", "tiktok_business"
    ]
    RedirectUri: str = Field(max_length=2048)

    @field_validator("ClientId")
    @classmethod
    def valid_id(cls, value):
        return identifier(value, 128)

    @field_validator("RedirectUri")
    @classmethod
    def callback(cls, value):
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.fragment
        ):
            raise ValueError("invalid_callback")
        return value


class Integration(Strict):
    ApplicationId: UUID
    Channel: Literal["whatsapp", "instagram", "facebook", "messenger", "tiktok"]
    DisplayName: str = Field(min_length=1, max_length=160)
    Environment: Literal["development", "production", "test"] = "development"
    ExternalAccountId: str | None = Field(default=None, max_length=200)
    ParentExternalId: str | None = Field(default=None, max_length=200)
    ApiVersion: str = Field(max_length=20)

    @field_validator("ExternalAccountId", "ParentExternalId")
    @classmethod
    def valid_id(cls, value):
        return identifier(value) if value is not None else None


class ApplicationEdit(Strict):
    ApiVersion: str = Field(max_length=20)
    # Identity, issuer and OAuth callback cannot change through this local editor.


class IntegrationEdit(Strict):
    DisplayName: str = Field(min_length=1, max_length=160)
    ApiVersion: str = Field(max_length=20)


def create_app(settings, repository=None):
    app = FastAPI(
        title=f"{PRODUCT_NAME} · Canales locales",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    repo = repository or Repository(settings)

    @app.middleware("http")
    async def authenticate(request: Request, call_next):
        token = request.headers.get("authorization", "")
        allowed = (
            request.client is not None
            and request.client.host in {"127.0.0.1", "::1"}
            and request.headers.get("host") in {"127.0.0.1:4176", "localhost:4176"}
            and request.headers.get("origin")
            in {None, "http://127.0.0.1:4176", "http://localhost:4176"}
            and request.headers.get("x-crm-local") == "1"
            and hmac.compare_digest(
                token.encode(), ("Bearer " + settings.review["api_token"]).encode()
            )
            and time.time() < settings.ticket["expires_at"]
        )
        if not allowed:
            return JSONResponse(
                {"detail": "local_capability_required"}, status_code=403
            )
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(RequestValidationError)
    async def invalid_body(request, error):
        return JSONResponse({"detail": "invalid_request"}, status_code=422)

    @app.get("/api/capabilities")
    def capabilities():
        return {
            "version": VERSION,
            "mode": "isolated_c12",
            "configuration": "local_drafts",
            "identity": "local_owner_capability",
            "read": list(PROJECTIONS),
            "write": ["applications", "integrations"],
            "providers": False,
            "oauth": False,
            "secret_replacement": False,
            "workers": False,
            "public_webhooks": False,
            "institutional_auth": False,
        }

    @app.get("/api/channels/{kind}")
    def listing(
        kind: str,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        after: UUID | None = None,
    ):
        if kind not in PROJECTIONS:
            raise HTTPException(404, "resource_not_found")
        return repo.read(kind, limit=limit, after=after)

    @app.get("/api/channels/{kind}/{entity}")
    def entity(kind: str, entity: UUID):
        if kind not in PROJECTIONS:
            raise HTTPException(404, "resource_not_found")
        return repo.read(kind, entity=entity)

    @app.get("/api/operations/{operation}")
    def operation(operation: UUID):
        return repo.operation(operation)

    @app.post("/api/channels/applications")
    def application(
        body: Application, operation: Annotated[UUID, Header(alias="Idempotency-Key")]
    ):
        if (body.Provider == "tiktok") != (body.IssuerProfile == "tiktok_business"):
            raise HTTPException(422, "issuer_provider_mismatch")
        return repo.write("create_application", body.model_dump(mode="json"), operation)

    @app.post("/api/channels/integrations")
    def integration(
        body: Integration, operation: Annotated[UUID, Header(alias="Idempotency-Key")]
    ):
        return repo.write("create_integration", body.model_dump(mode="json"), operation)

    @app.patch("/api/channels/applications/{entity}")
    def edit_application(
        entity: UUID,
        body: ApplicationEdit,
        operation: Annotated[UUID, Header(alias="Idempotency-Key")],
        revision: Annotated[str, Header(alias="If-Match", pattern=r"^[0-9a-f]{16}$")],
    ):
        return repo.write(
            "edit_application", body.model_dump(), operation, entity, revision
        )

    @app.patch("/api/channels/integrations/{entity}")
    def edit_integration(
        entity: UUID,
        body: IntegrationEdit,
        operation: Annotated[UUID, Header(alias="Idempotency-Key")],
        revision: Annotated[str, Header(alias="If-Match", pattern=r"^[0-9a-f]{16}$")],
    ):
        return repo.write(
            "edit_integration", body.model_dump(), operation, entity, revision
        )

    return app
