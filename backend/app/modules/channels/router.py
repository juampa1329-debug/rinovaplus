"""Local operator configuration, provider validation and asynchronous submissions."""

from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from . import providers
from .storage import CHANNELS, SECRET_KINDS, ChannelStore, document

Channel = Literal["whatsapp", "facebook", "messenger", "instagram", "tiktok"]


class ChannelConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    appId: str = Field(default="", max_length=128, pattern=r"^[A-Za-z0-9_-]*$")
    wabaId: str = Field(default="", max_length=128, pattern=r"^[0-9]*$")
    phoneNumberId: str = Field(default="", max_length=128, pattern=r"^[0-9]*$")
    pageId: str = Field(default="", max_length=128, pattern=r"^[0-9]*$")
    accountId: str = Field(default="", max_length=128, pattern=r"^[A-Za-z0-9_.:-]*$")
    apiVersion: str = Field(default="", max_length=12, pattern=r"^(v[0-9]{1,2}\.0)?$")
    instagramLogin: Literal["facebook", "instagram"] = "facebook"
    environment: Literal["production", "development"] = "production"
    callbackUrl: str = Field(default="", max_length=2048)
    initialStage: str = Field(default="", max_length=60)

    @model_validator(mode="after")
    def callback(self):
        if self.callbackUrl:
            url = urlsplit(self.callbackUrl)
            if (
                url.scheme != "https"
                or not url.hostname
                or url.username
                or url.password
                or url.query
                or url.fragment
            ):
                raise ValueError("HTTPS callback URL required")
        return self


class ConfigurationWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=0)
    configuration: ChannelConfiguration
    accessToken: str = Field(default="", max_length=12000)
    appSecret: str = Field(default="", max_length=4096)
    verifyToken: str = Field(default="", max_length=4096)
    refreshToken: str = Field(default="", max_length=12000)

    @model_validator(mode="after")
    def secret_characters(self):
        if any(
            any(ord(c) < 32 or ord(c) == 127 for c in getattr(self, k))
            for k in SECRET_KINDS
        ):
            raise ValueError("Invalid credential characters")
        return self


class Reply(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operationId: UUID
    body: str = Field(min_length=1, max_length=4000)
    mode: Literal["public", "private"] = "public"


class NumberAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pin: str = Field(pattern=r"^[0-9]{6}$")


class ChannelNumberVerification(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["request", "verify"]
    method: Literal["SMS", "VOICE"] = "SMS"
    locale: str = Field(default="es_CO", pattern=r"^[a-z]{2}_[A-Z]{2}$")
    code: str = Field(default="", pattern=r"^[0-9]{0,16}$")


def install_channels(application):
    store = ChannelStore(application.state.settings)
    application.state.channel_store = store
    router = APIRouter(prefix="/api/v1/channels", tags=["channels"])

    @router.get("")
    def list_channels():
        with store.transaction() as cursor:
            return {"channels": [store.get(cursor, c) for c in CHANNELS]}

    @router.get("/whatsapp/numbers")
    def numbers():
        with store.transaction() as cursor:
            account = store.get(cursor, "whatsapp", True)
        try:
            return {"numbers": providers.discover(account).get("numbers", [])}
        except providers.ProviderFailure as error:
            raise HTTPException(409, error.code) from None

    @router.get("/transport/status")
    def transport_status():
        with store.transaction() as cursor:
            rows = cursor.execute(
                "SELECT State,COUNT_BIG(*) FROM crm_channels.outbound_queue GROUP BY State"
            ).fetchall()
            counts = dict(rows)
            failed = cursor.execute(
                "SELECT COUNT_BIG(*) FROM crm_channels.webhook_events WHERE LastError IS NOT NULL"
            ).fetchone()[0]
            error = cursor.execute(
                "SELECT TOP(1) LastError FROM crm_channels.webhook_events WHERE LastError IS NOT NULL ORDER BY ReceivedAt DESC"
            ).fetchone()
        return {
            "queued": counts.get("queued", 0) + counts.get("sending", 0),
            "failed": counts.get("failed", 0),
            "uncertain": counts.get("uncertain", 0),
            "receiptsFailed": failed,
            "lastError": error[0] if error else None,
        }

    @router.post("/transport/retry-receipts")
    def retry_receipts():
        with store.transaction() as cursor:
            cursor.execute(
                "UPDATE crm_channels.webhook_events SET State='queued',Attempts=0,LeaseId=NULL,LastError=NULL,DueAt=SYSUTCDATETIME() WHERE LastError IS NOT NULL AND State IN('queued','failed')"
            )
            return {"requeued": cursor.rowcount}

    @router.post("/whatsapp/number-registration")
    def register_number(body: NumberAction):
        with store.transaction() as cursor:
            account = store.get(cursor, "whatsapp", True)
        try:
            result = providers.request(
                account,
                "POST",
                account["configuration"]["phoneNumberId"] + "/register",
                {"messaging_product": "whatsapp", "pin": body.pin},
            )
            return {"registered": result.get("success") is True}
        except (providers.ProviderFailure, KeyError) as error:
            raise HTTPException(
                409, getattr(error, "code", "phone_number_configuration_required")
            ) from None

    @router.post("/whatsapp/number-verification")
    def verify_number(body: ChannelNumberVerification):
        with store.transaction() as cursor:
            account = store.get(cursor, "whatsapp", True)
        try:
            phone = account["configuration"]["phoneNumberId"]
            if body.action == "request":
                result = providers.request(
                    account,
                    "POST",
                    phone + "/request_code",
                    {"code_method": body.method, "locale": body.locale},
                )
            else:
                if not body.code:
                    raise HTTPException(422, "verification_code_required")
                result = providers.request(
                    account, "POST", phone + "/verify_code", {"code": body.code}
                )
            return {"success": result.get("success") is True}
        except (providers.ProviderFailure, KeyError) as error:
            raise HTTPException(
                409, getattr(error, "code", "phone_number_configuration_required")
            ) from None

    @router.get("/{channel}")
    def get_channel(channel: Channel):
        with store.transaction() as cursor:
            return store.get(cursor, channel)

    @router.put("/{channel}/draft")
    def save_channel(channel: Channel, body: ConfigurationWrite):
        with store.transaction() as cursor:
            return store.save_configuration(cursor, channel, body)

    def operate(channel, activation=False):
        with store.transaction() as cursor:
            account = store.get(cursor, channel, True)
        config = account["configuration"]
        required = (
            ["appId", "accountId"]
            if channel == "tiktok"
            else ["appId", "apiVersion", "wabaId", "phoneNumberId"]
            if channel == "whatsapp"
            else ["appId", "apiVersion", "accountId"]
            if channel == "instagram"
            else ["appId", "apiVersion", "pageId"]
        )
        secrets_required = (
            ("accessToken", "appSecret")
            if channel == "tiktok"
            else ("accessToken", "appSecret", "verifyToken")
        )
        if channel == "whatsapp" and not activation:
            required = ["wabaId", "phoneNumberId"]
            secrets_required = ("accessToken",)
        if any(not config.get(k) for k in required) or not all(
            account["secrets"].get(k) for k in secrets_required
        ):
            raise HTTPException(409, "channel_configuration_incomplete")
        try:
            capabilities = providers.discover(account)
            if activation:
                if not config.get("callbackUrl"):
                    raise providers.ProviderFailure("public_https_callback_required")
                providers.subscribe(account)
                capabilities["subscriptionConfirmed"] = True
        except providers.ProviderFailure as error:
            with store.transaction() as cursor:
                cursor.execute(
                    "UPDATE crm_channels.Account SET LastError=? WHERE Channel=? AND Revision=?",
                    error.code,
                    channel,
                    account["revision"],
                )
            raise HTTPException(409, error.code) from None
        with store.transaction() as cursor:
            discovered_version = capabilities.pop("discoveredApiVersion", None)
            if discovered_version and not config.get("apiVersion"):
                config["apiVersion"] = discovered_version
                cursor.execute(
                    "UPDATE crm_channels.Account SET Configuration=?,Revision=Revision+1 WHERE Channel=? AND Revision=?",
                    document(config),
                    channel,
                    account["revision"],
                )
                if cursor.rowcount != 1:
                    raise HTTPException(409, "channel_configuration_changed")
                account["revision"] += 1
            cursor.execute(
                "UPDATE crm_channels.Account SET Capabilities=?,State=?,LastError=NULL,VerifiedAt=SYSUTCDATETIME() WHERE Channel=? AND Revision=?",
                document(capabilities),
                "awaiting_webhook" if activation else "validated",
                channel,
                account["revision"],
            )
            if cursor.rowcount != 1:
                raise HTTPException(409, "channel_configuration_changed")
            return store.get(cursor, channel)

    @router.post("/{channel}/discovery")
    def discovery(channel: Channel):
        return operate(channel)

    @router.post("/{channel}/connection-tests")
    def connection_test(channel: Channel):
        return operate(channel)

    @router.post("/{channel}/activation")
    def activate(channel: Channel):
        return operate(channel, True)

    @router.post("/{channel}/pause")
    def pause(channel: Channel):
        with store.transaction() as cursor:
            cursor.execute(
                "UPDATE crm_channels.Account SET State='paused',Revision=Revision+1 WHERE Channel=?",
                channel,
            )
            return store.get(cursor, channel)

    @router.get("/{channel}/capabilities")
    def capabilities(channel: Channel):
        with store.transaction() as cursor:
            return store.get(cursor, channel)["capabilities"]

    @router.get("/{channel}/webhook-reference")
    def reference(channel: Channel):
        with store.transaction() as cursor:
            account = store.get(cursor, channel)
        path = "/api/v1/webhooks/" + ("tiktok" if channel == "tiktok" else "meta")
        return {
            "path": path,
            "callbackUrl": account["configuration"].get("callbackUrl", ""),
            "verifyTokenConfigured": "verifyToken" in account["credentials"],
            "state": account["state"],
        }

    from app.contracts import CHANNEL_ROUTES

    identities = {(r.method, r.path): r.operation_id for r in CHANNEL_ROUTES}
    for route in router.routes:
        for method in route.methods or ():
            if (method, route.path) in identities:
                route.operation_id = identities[(method, route.path)]
    application.include_router(router)
    social = APIRouter(prefix="/api/v1/social-comments", tags=["social_comments"])

    @social.get("")
    def comments(channel: Channel | None = None, offset: int = 0, limit: int = 25):
        if not 0 <= offset <= 100000 or not 1 <= limit <= 100:
            raise HTTPException(422, "invalid_pagination")
        with store.transaction() as cursor:
            rows = cursor.execute(
                "SELECT CommentId,Channel,ExternalId,Body,ReceivedAt FROM crm_channels.social_comments WHERE (? IS NULL OR Channel=?) ORDER BY ReceivedAt DESC,CommentId OFFSET ? ROWS FETCH NEXT ? ROWS ONLY",
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

    @social.post("/{comment_id}/reply", status_code=202)
    def reply(comment_id: UUID, body: Reply):
        with store.transaction() as cursor:
            row = cursor.execute(
                "SELECT Channel,ExternalId,AuthorId,Payload FROM crm_channels.social_comments WHERE CommentId=?",
                str(comment_id),
            ).fetchone()
            if not row:
                raise HTTPException(404, "comment_not_found")
            if body.mode == "private" and row[0] not in ("instagram", "messenger"):
                raise HTTPException(409, "private_reply_not_available")
            account = store.get(cursor, row[0])
            if account["state"] not in ("connected", "awaiting_webhook"):
                raise HTTPException(409, "channel_not_active")
            payload = {
                "kind": "comment" if body.mode == "public" else "private_reply",
                "target": row[1],
                "body": body.body.strip(),
            }
            if row[0] == "tiktok":
                import json

                source = json.loads(row[3])
                if source.get("comment_action") not in ("insert", "set_to_public"):
                    raise HTTPException(409, "comment_no_longer_public")
                payload["videoId"] = str(source.get("video_id", ""))
                if not payload["videoId"] or len(payload["body"]) > 1200:
                    raise HTTPException(422, "tiktok_comment_video_or_length_invalid")
            if not payload["body"]:
                raise HTTPException(422, "message_empty")
            previous = cursor.execute(
                "SELECT Payload,State,Channel FROM crm_channels.outbound_queue WITH(UPDLOCK,HOLDLOCK) WHERE QueueId=?",
                str(body.operationId),
            ).fetchone()
            if previous:
                if previous[0] != document(payload) or previous[2] != row[0]:
                    raise HTTPException(409, "operation_changed")
                return {"id": str(body.operationId), "state": previous[1]}
            cursor.execute(
                "INSERT crm_channels.outbound_queue(QueueId,Channel,Payload) VALUES(?,?,?)",
                str(body.operationId),
                row[0],
                document(payload),
            )
            return {"id": str(body.operationId), "state": "queued"}

    application.include_router(social)
