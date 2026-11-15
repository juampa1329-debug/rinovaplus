"""C9 capability UI API: configuration and reads, without provider composition."""

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.branding import PRODUCT_NAME
from app.channels_app import ChannelDraft
from app.channels_ui_contract import ticket, transaction
from app.modules.ai.api.router import LocalAiGuard
from app.modules.channels.router import Channel, ConfigurationWrite
from app.modules.channels.storage import CHANNELS, ChannelStore
from app.modules.crm_configuration.application.service import read_configuration
from app.runtime_capabilities import FEATURES
from app.sql_target import validate_settings

CHANNEL_CAPABILITIES = {
    "configuration": True,
    "stageOptions": True,
    "status": True,
    "comments": True,
    "credentials": False,
    "providerActions": False,
    "externalDelivery": False,
    "publicWebhooks": False,
    "workers": False,
}


class ChannelUiStore(ChannelStore):
    def __init__(self, settings):
        self.settings = settings

    def transaction(self, *, write=False):
        return transaction(self.settings, write=write)

    def key(self, cursor):
        raise HTTPException(503, "channels_ui_credentials_unavailable")

    def secrets(self, cursor, channel):
        raise HTTPException(503, "channels_ui_credentials_unavailable")

    def write_secret(self, cursor, channel, kind, value):
        raise HTTPException(503, "channels_ui_credentials_unavailable")


def public_account(store, cursor, channel):
    value = store.get(cursor, channel)
    return {
        **value,
        "credentials": [],
        "state": "configured" if value["revision"] else "unconfigured",
        "capabilities": {},
        "verifiedAt": None,
        "lastError": None,
    }


def create_channels_ui_app(settings):
    validate_settings(settings)
    ticket(settings)
    application = FastAPI(
        title=f"{PRODUCT_NAME} · Interfaz de canales",
        version="SQL-C9",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    application.state.settings = settings
    store = ChannelUiStore(settings)
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
        return {"status": "alive", "mode": "local_channels_ui"}

    @application.get("/health/ready", status_code=503)
    def ready():
        return {"status": "not_ready", "reason": "Institutional acceptance pending"}

    @application.get("/api/local/runtime")
    def runtime():
        with store.transaction():
            pass
        return {
            "version": "cbn-ui-capabilities-v2",
            "profile": "channels",
            "mode": "local_channels_ui",
            "modules": ["settings"],
            "features": {key: False for key in FEATURES},
            "scope": "restored_rehearsal_only",
            "channels": CHANNEL_CAPABILITIES,
        }

    @application.get("/api/v1/channels")
    def list_channels():
        with store.transaction() as cursor:
            return {"channels": [public_account(store, cursor, c) for c in CHANNELS]}

    @application.get("/api/v1/channels/transport/status")
    def status():
        with store.transaction() as cursor:
            outbound = cursor.execute(
                "SELECT COUNT_BIG(*) FROM crm_channels.outbound_queue"
            ).fetchval()
            receipts = cursor.execute(
                "SELECT COUNT_BIG(*) FROM crm_channels.webhook_events"
            ).fetchval()
        return {
            "outboundRecords": outbound,
            "receiptRecords": receipts,
            "transportEnabled": False,
            "workersEnabled": False,
        }

    @application.get("/api/local/channels/stages")
    def stages():
        with store.transaction() as cursor:
            config, _ = read_configuration(cursor, foundation=True)
        return {"stages": [s.label for s in config.stages if s.active]}

    @application.get("/api/v1/channels/{channel}")
    def get_channel(channel: Channel):
        with store.transaction() as cursor:
            return public_account(store, cursor, channel)

    @application.put("/api/v1/channels/{channel}/draft")
    def save_channel(channel: Channel, body: ChannelDraft):
        with store.transaction(write=True) as cursor:
            if body.configuration.initialStage:
                config, _ = read_configuration(cursor, foundation=True)
                if not any(
                    s.active and s.label == body.configuration.initialStage
                    for s in config.stages
                ):
                    raise HTTPException(422, "invalid_crm_stage")
            store.save_configuration(
                cursor, channel, ConfigurationWrite(**body.model_dump())
            )
            return public_account(store, cursor, channel)

    @application.get("/api/v1/social-comments")
    def comments(
        offset: int = Query(0, ge=0, le=100000), limit: int = Query(25, ge=1, le=100)
    ):
        with store.transaction() as cursor:
            rows = cursor.execute(
                "SELECT CommentId,Channel,LEFT(Body,4000),ReceivedAt "
                "FROM crm_channels.social_comments ORDER BY ReceivedAt DESC,CommentId "
                "OFFSET ? ROWS FETCH NEXT ? ROWS ONLY",
                offset,
                limit,
            ).fetchall()
        return {
            "comments": [
                {
                    "id": str(r[0]),
                    "channel": r[1],
                    "body": r[2],
                    "receivedAt": r[3].isoformat() + "Z",
                }
                for r in rows
            ]
        }

    @application.api_route(
        "/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"]
    )
    def unavailable(path: str):
        raise HTTPException(503, "channels_ui_capability_unavailable")

    return application
