"""Bounded, sanitized Meta verification independent of SQL and outbound IO."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel

from app.modules.webhooks.domain.verification import (
    verification_configured,
    verify_subscription,
)

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])
PARAMETERS = {"hub.mode": 20, "hub.verify_token": 4096, "hub.challenge": 4096}


class MetaWebhookStatus(BaseModel):
    verificationImplemented: bool = True
    verificationConfigured: bool
    callbackPath: str = "/api/v1/webhooks/meta"
    receiptImplemented: bool = False
    dispatchImplemented: bool = False
    channelsConnected: bool = False


@router.get(
    "/meta/status",
    operation_id="webhooks_meta_status",
    response_model=MetaWebhookStatus,
)
def meta_status(request: Request) -> JSONResponse:
    configured = False
    connected = False
    try:
        with request.app.state.channel_store.transaction() as cursor:
            configured = bool(
                cursor.execute(
                    "SELECT TOP(1) Channel FROM crm_channels.Credential WHERE Kind='verifyToken' AND Channel<>'tiktok'"
                ).fetchone()
            )
            connected = bool(
                cursor.execute(
                    "SELECT TOP(1) Channel FROM crm_channels.Account WHERE State='connected'"
                ).fetchone()
            )
    except Exception:
        pass
    return JSONResponse(
        MetaWebhookStatus(
            verificationConfigured=configured
            or verification_configured(
                request.app.state.settings.meta_verify_token_sha256
            ),
            receiptImplemented=True,
            dispatchImplemented=True,
            channelsConnected=connected,
        ).model_dump(),
        headers={"Cache-Control": "no-store"},
    )


@router.get(
    "/meta",
    operation_id="webhooks_meta_verification",
    response_class=PlainTextResponse,
    responses={
        403: {"description": "Subscription verification rejected"},
        422: {"description": "Invalid verification query; submitted values omitted"},
        503: {"description": "Verification digest unavailable"},
    },
    openapi_extra={
        "parameters": [
            {
                "name": name,
                "in": "query",
                "required": True,
                "schema": {"type": "string", "minLength": 1, "maxLength": maximum},
                "description": "Do not log query values or retain them in traces",
            }
            for name, maximum in PARAMETERS.items()
        ]
    },
)
def verify_meta(request: Request):
    # Manual validation avoids FastAPI error payloads reflecting secret inputs.
    query = request.query_params
    if set(query) != set(PARAMETERS) or any(
        len(query.getlist(name)) != 1 or not 1 <= len(query[name]) <= maximum
        for name, maximum in PARAMETERS.items()
    ):
        return JSONResponse(
            {"code": "invalid_webhook_verification"},
            status_code=422,
            headers={"Cache-Control": "no-store"},
        )
    verdict = verify_subscription(
        query["hub.mode"],
        query["hub.verify_token"],
        request.app.state.settings.meta_verify_token_sha256,
    )
    if verdict is not True and query["hub.mode"] == "subscribe":
        import hashlib
        import hmac
        from fastapi import HTTPException

        store = request.app.state.channel_store
        try:
            with store.transaction() as cursor:
                configured = [
                    store.get(cursor, channel, True)
                    for channel in ("whatsapp", "facebook", "messenger", "instagram")
                ]
            for account in configured:
                token = account["secrets"].get("verifyToken")
                if token and hmac.compare_digest(
                    hashlib.sha256(token.encode()).digest(),
                    hashlib.sha256(query["hub.verify_token"].encode()).digest(),
                ):
                    verdict = True
                    break
        except HTTPException:
            pass
    if verdict is not True:
        return JSONResponse(
            {
                "code": "webhook_verification_unavailable"
                if verdict is None
                else "webhook_verification_rejected"
            },
            status_code=503 if verdict is None else 403,
            headers={"Cache-Control": "no-store"},
        )
    return PlainTextResponse(
        query["hub.challenge"], headers={"Cache-Control": "no-store"}
    )


@router.post("/meta", operation_id="webhooks_meta_receipt")
async def receive_meta(request: Request):
    from app.modules.channels.receipts import receive

    return await receive(request, "meta")


@router.post("/tiktok", operation_id="webhooks_tiktok_receipt")
async def receive_tiktok(request: Request):
    from app.modules.channels.receipts import receive

    return await receive(request, "tiktok")
