"""C8 explicit local composition: configuration and reads, no provider installers."""

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.channels_contract import ticket
from app.modules.ai.api.router import LocalAiGuard
from app.modules.channels.router import (
    Channel,
    ChannelConfiguration,
    ConfigurationWrite,
)
from app.modules.channels.storage import CHANNELS, ChannelStore
from app.sql_target import validate_settings


class ChannelDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=0, strict=True)
    configuration: ChannelConfiguration


def create_channels_app(settings):
    validate_settings(settings)
    ticket(settings)
    application = FastAPI(
        title="CRM CBN channels rehearsal",
        version="SQL-C8",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    application.state.settings = settings
    store = ChannelStore(settings)
    application.state.channel_store = store
    application.add_middleware(LocalAiGuard)

    @application.middleware("http")
    async def private_response(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    @application.exception_handler(RequestValidationError)
    async def invalid_input(request: Request, exception: RequestValidationError):
        return JSONResponse({"code": "invalid_request"}, status_code=422)

    @application.get("/health/live")
    def live():
        return {"status": "alive", "mode": "local_channels"}

    @application.get("/health/ready", status_code=503)
    def ready():
        return {"status": "not_ready", "reason": "Institutional acceptance pending"}

    @application.get("/api/local/runtime")
    def runtime():
        return {
            "version": "cbn-channels-rehearsal-v1",
            "mode": "local_channels",
            "scope": "restored_rehearsal_only",
            "features": {
                "configuration": True,
                "localPersistence": True,
                "externalDelivery": False,
                "publicWebhooks": False,
                "workers": False,
                "academic": False,
            },
            "institutional_sql2019_accepted": False,
        }

    @application.get("/api/v1/channels")
    def list_channels():
        with store.transaction() as cursor:
            return {"channels": [store.get(cursor, channel) for channel in CHANNELS]}

    @application.get("/api/v1/channels/transport/status")
    def transport_status():
        with store.transaction() as cursor:
            counts = dict(
                cursor.execute(
                    "SELECT State,COUNT_BIG(*) FROM crm_channels.outbound_queue "
                    "GROUP BY State"
                ).fetchall()
            )
            receipts = cursor.execute(
                "SELECT COUNT_BIG(*) FROM crm_channels.webhook_events"
            ).fetchval()
        return {
            "states": counts,
            "receipts": receipts,
            "transportEnabled": False,
            "workersEnabled": False,
        }

    @application.get("/api/v1/channels/{channel}")
    def get_channel(channel: Channel):
        with store.transaction() as cursor:
            return store.get(cursor, channel)

    @application.put("/api/v1/channels/{channel}/draft")
    def save_channel(channel: Channel, body: ChannelDraft):
        write = ConfigurationWrite(**body.model_dump())
        with store.transaction() as cursor:
            return store.save_configuration(cursor, channel, write)

    @application.get("/api/v1/social-comments")
    def comments(
        channel: Channel | None = None,
        offset: int = Query(0, ge=0, le=100000),
        limit: int = Query(25, ge=1, le=100),
    ):
        with store.transaction() as cursor:
            rows = cursor.execute(
                "SELECT CommentId,Channel,ExternalId,Body,ReceivedAt "
                "FROM crm_channels.social_comments WHERE (? IS NULL OR Channel=?) "
                "ORDER BY ReceivedAt DESC,CommentId "
                "OFFSET ? ROWS FETCH NEXT ? ROWS ONLY",
                channel,
                channel,
                offset,
                limit,
            ).fetchall()
        return {
            "comments": [
                {
                    "id": str(r[0]),
                    "channel": r[1],
                    "externalId": r[2],
                    "body": r[3],
                    "receivedAt": r[4].isoformat() + "Z",
                }
                for r in rows
            ]
        }

    @application.api_route(
        "/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"]
    )
    def unavailable(path: str):
        raise HTTPException(503, "channels_rehearsal_capability_unavailable")

    return application
