"""Institution-bound channel operations, generated callbacks and C10 credentials."""

from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import HTTPException, Request
from pydantic import Field

from app.institutional.auth import authorize
from app.institutional.channel_secrets import get, put
from app.institutional.channels import (
    FACEBOOK_LOGIN_CONFIGURATION,
    WHATSAPP_LOGIN_CONFIGURATION,
    Channels,
)
from app.institutional.crypto import token
from app.institutional.db import (
    audit,
    institution,
    one,
    record_operation,
    replay,
    rows,
    uid,
    utc,
)
from app.institutional.models import Strict, public_url
from app.institutional.store import transaction

VERSION = "cbn-institutional-channels-p4-v1"


def account(c, settings, identity):
    value = one(
        c,
        (
            "SELECT i.*,a.ClientId,a.IssuerProfile,a.State AS Application"
            "State,a.EgressProfile,a.RedirectUri,a.RowVersion AS ApplicationVersion "
            "FROM "
            "crm_channels2.Integration i JOIN crm_channels2.Application a"
            " ON a.InstitutionId=i.InstitutionId AND a.ApplicationId=i.Ap"
            "plicationId WHERE i.InstitutionId=? AND i.IntegrationId=?"
        ),
        institution(settings),
        uid(identity),
    )
    if not value:
        raise HTTPException(404, "account_not_found")
    return value


def configuration(c, settings):
    value = one(
        c,
        "SELECT * FROM crm_channels4.Configuration WHERE InstitutionId=?",
        institution(settings),
    )
    if not value:
        raise HTTPException(503, "channel_configuration_unavailable")
    from app.institutional.settings import setting

    if getattr(settings, "public_origin", None):
        value["PublicBaseUrl"] = settings.public_origin
    value["ModuleEnabled"] = setting(c, settings, "modules")["document"]["enabled"].get(
        "channels", False
    )
    return value


def base_url(value):
    public_url(value)
    parsed = urlsplit(value)
    if value and (
        parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or parsed.port not in {None, 443}
    ):
        raise HTTPException(422, "public_origin_required")
    return value.rstrip("/")


def endpoint(c, settings, item, *, create=False):
    selector = "facebook" if item["Channel"] == "messenger" else item["Channel"]
    value = one(
        c,
        (
            "SELECT * FROM crm_channels2.WebhookEndpoint WHERE Institutio"
            "nId=? AND ApplicationId=? AND ChannelSelector=?"
        ),
        institution(settings),
        item["ApplicationId"],
        selector,
    )
    issued = {}
    if not value and create:
        identity, key = str(uuid4()), "ep_" + token()
        c.execute(
            (
                "INSERT crm_channels2.WebhookEndpoint(InstitutionId,EndpointI"
                "d,ApplicationId,Provider,ChannelSelector,EndpointKey,Signatu"
                "reProfile,SignatureRequired,IsActive,CreatedAt,UpdatedAt) VA"
                "LUES(?,?,?,?,?,?,?,1,0,SYSUTCDATETIME(),SYSUTCDATETIME())"
            ),
            institution(settings),
            identity,
            item["ApplicationId"],
            item["Provider"],
            selector,
            key,
            "meta_sha256" if item["Provider"] == "meta" else "tiktok_timestamp_sha256",
        )
        verify = token()
        put(c, settings, "endpoint", identity, "webhook_verify", verify)
        issued = {"verify_token": verify}
        value = one(
            c,
            (
                "SELECT * FROM crm_channels2.WebhookEndpoint WHERE Institutio"
                "nId=? AND EndpointId=?"
            ),
            institution(settings),
            identity,
        )
    if not value:
        return None, issued
    origin = configuration(c, settings)["PublicBaseUrl"]
    path = "/hooks/channels/" + value["EndpointKey"]
    return {
        "id": uid(str(value["EndpointId"])),
        "key": value["EndpointKey"],
        "path": path,
        "callback_url": origin + path if origin else "",
        "public_origin_required": not bool(origin),
        "signature_required": True,
        "active": bool(value["IsActive"]),
        "challenge_verified_at": utc(value["ChallengeVerifiedAt"]),
        "last_seen_at": utc(value["LastSeenAt"]),
        "row_version": bytes(value["RowVersion"]).hex(),
    }, issued


def sync_route(c, settings, item, endpoint_id):
    c.execute(
        (
            "UPDATE crm_channels2.EndpointIntegration SET IsActive=0 WHER"
            "E InstitutionId=? AND IntegrationId=?"
        ),
        institution(settings),
        item["IntegrationId"],
    )
    external = item["ExternalAccountId"]
    route_kind = "configured_" + item["Channel"]
    if not external:
        return
    duplicate = c.execute(
        (
            "SELECT 1 FROM crm_channels2.EndpointIntegration WHERE Instit"
            "utionId=? AND EndpointId=? AND RouteKind=? AND ExternalId=? "
            "AND IntegrationId<>?"
        ),
        institution(settings),
        endpoint_id,
        route_kind,
        external,
        item["IntegrationId"],
    ).fetchone()
    if duplicate:
        raise HTTPException(409, "webhook_external_route_already_bound")
    current = c.execute(
        (
            "SELECT 1 FROM crm_channels2.EndpointIntegration WHERE Instit"
            "utionId=? AND EndpointId=? AND IntegrationId=? AND RouteKind"
            "=? AND ExternalId=?"
        ),
        institution(settings),
        endpoint_id,
        item["IntegrationId"],
        route_kind,
        external,
    ).fetchone()
    if current:
        c.execute(
            (
                "UPDATE crm_channels2.EndpointIntegration SET IsActive=1 WHER"
                "E InstitutionId=? AND EndpointId=? AND IntegrationId=? AND R"
                "outeKind=? AND ExternalId=?"
            ),
            institution(settings),
            endpoint_id,
            item["IntegrationId"],
            route_kind,
            external,
        )
    else:
        c.execute(
            (
                "INSERT crm_channels2.EndpointIntegration(InstitutionId,Endpo"
                "intId,IntegrationId,ApplicationId,RouteKind,ExternalId,IsAct"
                "ive,CreatedAt) VALUES(?,?,?,?,?,?,1,SYSUTCDATETIME())"
            ),
            institution(settings),
            endpoint_id,
            item["IntegrationId"],
            item["ApplicationId"],
            route_kind,
            external,
        )


class OperationalChannels(Channels):
    def _fields(self, data):
        return super()._fields(data) + [
            {
                "id": field_id,
                "group": group,
                "label": "ID de configuración de Facebook Login",
                "config_key": field_id.split(":", 1)[1],
                "input_type": "text",
                "field_kind": "input",
                "value_type": "string",
                "max_length": 32,
                "editable_in_p2": True,
                "p2_write_allowed": True,
                "p2_mapping": {
                    "destination": "ChannelSetting JSON",
                    "p2_flat_json_key": field_id,
                },
            }
            for group, field_id in (
                ("facebook", FACEBOOK_LOGIN_CONFIGURATION),
                ("whatsapp", WHATSAPP_LOGIN_CONFIGURATION),
            )
        ]

    def catalog(self, authority):
        return {**super().catalog(authority), "provider_operations_available": True}

    def edited(self, c, identity):
        item = account(c, self.settings, identity)
        if item["VerifiedStatus"] == "retired":
            raise HTTPException(409, "retired_account_requires_restore")
        c.execute(
            (
                "UPDATE crm_channels2.Integration SET RequestedStatus='paused"
                "',VerifiedStatus='unverified',UpdatedAt=SYSUTCDATETIME() WHE"
                "RE InstitutionId=? AND IntegrationId=?"
            ),
            institution(self.settings),
            item["IntegrationId"],
        )
        if item["Channel"] == "tiktok":
            from app.institutional.channel_tiktok import apply_policy

            apply_policy(c, self.settings, item)

    def created(self, c, identity):
        item = account(c, self.settings, identity)
        origin = configuration(c, self.settings)["PublicBaseUrl"]
        if origin and not item["RedirectUri"]:
            c.execute(
                (
                    "UPDATE crm_channels2.Application SET RedirectUri=?,UpdatedAt"
                    "=SYSUTCDATETIME() WHERE InstitutionId=? AND ApplicationId=?"
                ),
                origin + "/hooks/oauth/" + str(item["ApplicationId"]).lower(),
                institution(self.settings),
                item["ApplicationId"],
            )
        ep, issued = endpoint(c, self.settings, item, create=True)
        return {"webhook": ep, **issued}

    def _item(self, c, identity):
        item = super()._item(c, identity)
        row = account(c, self.settings, identity)
        ep, _ = endpoint(c, self.settings, row)
        return {
            **item,
            "webhook": ep,
            "provider_operations_available": True,
            "capabilities": capabilities(row),
            "oauth_ready": bool(configuration(c, self.settings)["PublicBaseUrl"]),
            "oauth_callback": (configuration(c, self.settings)["PublicBaseUrl"] or "")
            + "/hooks/oauth/"
            + str(row["ApplicationId"]).lower(),
            "requested_status": row["RequestedStatus"],
            "issuer_profile": row["IssuerProfile"],
            "initial_stage_key": row["InitialStageKey"],
            "synthetic_demo": row["EgressProfile"] == "synthetic_no_provider",
        }


def capabilities(item):
    channel = item["Channel"]
    return {
        "public_comment_reply": channel in {"facebook", "instagram", "tiktok"},
        "comment_like": channel in {"facebook", "instagram"},
        "private_comment_reply": False,
        "register_number": channel == "whatsapp",
        "oauth": True,
        "chat": channel in {"whatsapp", "messenger", "instagram", "tiktok"},
        "connected": item["RequestedStatus"] == "connected"
        and item["VerifiedStatus"] == "verified",
    }


class RuntimeEdit(Strict):
    operation_id: str
    revision: int = Field(ge=1)
    public_base_url: str = Field(max_length=2048)
    ingress_enabled: bool
    outbound_enabled: bool
    receipt_retention_days: int = Field(ge=1, le=90)


class EndpointAction(Strict):
    operation_id: str
    row_version: str = Field(pattern=r"^[0-9a-f]{16}$")
    active: bool = False


class EndpointIssue(Strict):
    operation_id: str
    row_version: str | None = Field(default=None, pattern=r"^[0-9a-f]{16}$")
    active: bool = False


class RoutingEdit(Strict):
    operation_id: str
    row_version: str = Field(pattern=r"^[0-9a-f]{16}$")
    initial_stage_key: str = Field(pattern=r"^[a-z][a-z0-9_]{0,39}$")
    status: str = Field(pattern=r"^(connected|paused|disconnected)$")


class Operations:
    def __init__(self, settings):
        self.settings = settings

    def lifecycle(self, authority, identity, action, body):
        if action not in {"retire", "restore"}:
            raise HTTPException(404, "channel_action_not_found")
        with transaction(self.settings, True, anonymous=True) as c:
            actor = authorize(
                c, self.settings, authority, "settings.channels.write", recent=True
            )
            item = account(c, self.settings, identity)
            digest, prior = replay(
                c,
                self.settings,
                actor["UserId"],
                body.operation_id,
                "channels." + action,
                identity,
                body.model_dump(),
            )
            if prior:
                return prior
            if bytes(item["RowVersion"]).hex() != body.row_version:
                raise HTTPException(409, "revision_conflict")
            if action == "restore" and item["VerifiedStatus"] != "retired":
                raise HTTPException(409, "retired_account_required")
            c.execute(
                (
                    "UPDATE crm_channels2.Integration SET RequestedStatus='discon"
                    "nected',VerifiedStatus=?,UpdatedAt=SYSUTCDATETIME() WHERE In"
                    "stitutionId=? AND IntegrationId=?"
                ),
                "retired" if action == "retire" else "unverified",
                institution(self.settings),
                item["IntegrationId"],
            )
            if action == "retire":
                c.execute(
                    (
                        "UPDATE crm_channels4.MediaAsset SET State='failed',LastError"
                        "Code='account_retired',UpdatedAt=SYSUTCDATETIME() WHERE Inst"
                        "itutionId=? AND IntegrationId=? AND SourceKind='provider' AN"
                        "D State='pending'"
                    ),
                    institution(self.settings),
                    item["IntegrationId"],
                )
                c.execute(
                    (
                        "UPDATE crm_channels2.SecretVersion SET State='revoked',Revok"
                        "edAt=SYSUTCDATETIME() WHERE InstitutionId=? AND IntegrationI"
                        "d=? AND State IN('active','staged')"
                    ),
                    institution(self.settings),
                    item["IntegrationId"],
                )
                c.execute(
                    (
                        "UPDATE crm_channels2.EndpointIntegration SET IsActive=0 WHER"
                        "E InstitutionId=? AND IntegrationId=?"
                    ),
                    institution(self.settings),
                    item["IntegrationId"],
                )
                c.execute(
                    (
                        "UPDATE p SET Status='abandoned',ResultCode='account_retired'"
                        ",CompletedAt=SYSUTCDATETIME() FROM crm_channels2.ProviderOpe"
                        "ration p JOIN crm_channels2.SendJob q ON q.InstitutionId=p.I"
                        "nstitutionId AND q.OperationId=p.OperationId WHERE q.Institu"
                        "tionId=? AND q.IntegrationId=? AND q.State='queued' AND p.St"
                        "atus='pending'"
                    ),
                    institution(self.settings),
                    item["IntegrationId"],
                )
                c.execute(
                    (
                        "UPDATE crm_channels2.SendJob SET State='cancelled',LastError"
                        "Code='account_retired',CompletedAt=SYSUTCDATETIME() WHERE In"
                        "stitutionId=? AND IntegrationId=? AND State='queued'"
                    ),
                    institution(self.settings),
                    item["IntegrationId"],
                )
                c.execute(
                    (
                        "UPDATE crm_channels2.OAuthSession SET Status='cancelled',Com"
                        "pletedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND Integrat"
                        "ionId=? AND Status IN('pending','assets_ready')"
                    ),
                    institution(self.settings),
                    item["IntegrationId"],
                )
            result = {
                "saved": True,
                "history_preserved": True,
                "credentials_require_new_authorization": True,
            }
            record_operation(
                c,
                self.settings,
                actor["UserId"],
                body.operation_id,
                "channels." + action,
                identity,
                digest,
                result,
            )
            audit(c, self.settings, actor["UserId"], "channels." + action, identity)
            return result

    def routing(self, authority, identity, body):
        import hashlib

        from app.modules.crm_configuration.application.service import read_configuration

        with transaction(self.settings, True, anonymous=True) as c:
            actor = authorize(
                c, self.settings, authority, "settings.channels.write", recent=True
            )
            item = account(c, self.settings, identity)
            digest, prior = replay(
                c,
                self.settings,
                actor["UserId"],
                body.operation_id,
                "channels.routing",
                identity,
                body.model_dump(),
            )
            if prior:
                return prior
            if bytes(item["RowVersion"]).hex() != body.row_version:
                raise HTTPException(409, "revision_conflict")
            config, _ = read_configuration(c, foundation=True)
            if not any(
                s.key == body.initial_stage_key and s.active for s in config.stages
            ):
                raise HTTPException(422, "active_initial_stage_required")
            if body.status == "connected" and item["VerifiedStatus"] != "verified":
                raise HTTPException(409, "provider_verification_required")
            config_hash = hashlib.sha256(config.model_dump_json().encode()).digest()
            c.execute(
                (
                    "UPDATE crm_channels2.Integration SET InitialStageKey=?,Initi"
                    "alStageConfigHash=?,RequestedStatus=?,UpdatedAt=SYSUTCDATETI"
                    "ME() WHERE InstitutionId=? AND IntegrationId=? AND RowVersio"
                    "n=?"
                ),
                body.initial_stage_key,
                config_hash,
                body.status,
                institution(self.settings),
                item["IntegrationId"],
                bytes.fromhex(body.row_version),
            )
            if c.rowcount != 1:
                raise HTTPException(409, "revision_conflict")
            result = {"saved": True, "status": body.status}
            record_operation(
                c,
                self.settings,
                actor["UserId"],
                body.operation_id,
                "channels.routing",
                identity,
                digest,
                result,
            )
            return result

    def runtime(self, authority, body=None):
        with transaction(self.settings, body is not None, anonymous=True) as c:
            actor = authorize(
                c,
                self.settings,
                authority,
                "settings.webhooks." + ("write" if body else "read"),
                recent=body is not None,
            )
            current = configuration(c, self.settings)
            if body:
                origin = base_url(body.public_base_url)
                if getattr(self.settings, "public_origin", None) and origin != self.settings.public_origin:
                    raise HTTPException(422, "public_origin_managed_by_deployment")
                digest, prior = replay(
                    c,
                    self.settings,
                    actor["UserId"],
                    body.operation_id,
                    "channels.runtime",
                    "institution",
                    body.model_dump(),
                )
                if prior:
                    return prior
                if current["Revision"] != body.revision:
                    raise HTTPException(409, "revision_conflict")
                c.execute(
                    (
                        "UPDATE crm_channels4.Configuration SET PublicBaseUrl=?,Ingre"
                        "ssEnabled=?,OutboundEnabled=?,ReceiptRetentionDays=?,Revisio"
                        "n=Revision+1,UpdatedAt=SYSUTCDATETIME() WHERE InstitutionId="
                        "? AND Revision=?"
                    ),
                    origin,
                    body.ingress_enabled,
                    body.outbound_enabled,
                    body.receipt_retention_days,
                    institution(self.settings),
                    body.revision,
                )
                if c.rowcount != 1:
                    raise HTTPException(409, "revision_conflict")
                # Redirects are generated, never accepted from a callback or a Host
                # header.
                c.execute(
                    (
                        "UPDATE crm_channels2.Application SET RedirectUri=CASE WHEN ?"
                        "='' THEN '' ELSE CONCAT(?,'/hooks/oauth/',CONVERT(varchar(36),"
                        "ApplicationId)) END,UpdatedAt=SYSUTCDATETIME() WHERE InstitutionId"
                        "=?"
                    ),
                    origin,
                    origin,
                    institution(self.settings),
                )
                result = {"saved": True, "revision": body.revision + 1}
                record_operation(
                    c,
                    self.settings,
                    actor["UserId"],
                    body.operation_id,
                    "channels.runtime",
                    "institution",
                    digest,
                    result,
                )
                audit(
                    c,
                    self.settings,
                    actor["UserId"],
                    "channels.runtime",
                    "institution",
                    revision=body.revision + 1,
                )
                return result
            return {
                "revision": current["Revision"],
                "public_base_url": current["PublicBaseUrl"],
                "ingress_enabled": bool(current["IngressEnabled"]),
                "outbound_enabled": bool(current["OutboundEnabled"]),
                "receipt_retention_days": current["ReceiptRetentionDays"],
            }

    def webhook(self, authority, identity, body, *, rotate=False):
        with transaction(self.settings, True, anonymous=True) as c:
            actor = authorize(
                c, self.settings, authority, "settings.webhooks.write", recent=True
            )
            item = account(c, self.settings, identity)
            ep, _ = endpoint(c, self.settings, item)
            digest, prior = replay(
                c,
                self.settings,
                actor["UserId"],
                body.operation_id,
                "channels.webhook.rotate" if rotate else "channels.webhook",
                identity,
                body.model_dump(),
            )
            if prior:
                return {**prior, "secrets_already_issued": True}
            if (ep["row_version"] if ep else None) != body.row_version:
                raise HTTPException(409, "revision_conflict")
            issued = {}
            if rotate and ep is None:
                ep, issued = endpoint(c, self.settings, item, create=True)
            elif rotate:
                verify = token()
                put(c, self.settings, "endpoint", ep["id"], "webhook_verify", verify)
                issued["verify_token"] = verify
                c.execute(
                    (
                        "UPDATE crm_channels2.WebhookEndpoint SET ChallengeVerifiedAt"
                        "=NULL,UpdatedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND E"
                        "ndpointId=? AND RowVersion=?"
                    ),
                    institution(self.settings),
                    ep["id"],
                    bytes.fromhex(ep["row_version"]),
                )
                if c.rowcount != 1:
                    raise HTTPException(409, "revision_conflict")
            else:
                if body.active:
                    if item["Provider"] == "meta":
                        get(
                            c,
                            self.settings,
                            "application",
                            str(item["ApplicationId"]),
                            app_secret_kind(item),
                        )
                    else:
                        get(
                            c,
                            self.settings,
                            "endpoint",
                            ep["id"],
                            "tiktok_webhook_secret",
                        )
                    if not item["ExternalAccountId"]:
                        raise HTTPException(409, "external_account_required")
                    sync_route(c, self.settings, item, ep["id"])
                c.execute(
                    (
                        "UPDATE crm_channels2.WebhookEndpoint SET IsActive=?,UpdatedA"
                        "t=SYSUTCDATETIME() WHERE InstitutionId=? AND EndpointId=? AN"
                        "D RowVersion=?"
                    ),
                    body.active,
                    institution(self.settings),
                    ep["id"],
                    bytes.fromhex(body.row_version),
                )
                if c.rowcount != 1:
                    raise HTTPException(409, "revision_conflict")
            result = {"webhook": endpoint(c, self.settings, item)[0]}
            record_operation(
                c,
                self.settings,
                actor["UserId"],
                body.operation_id,
                "channels.webhook.rotate" if rotate else "channels.webhook",
                identity,
                digest,
                result,
            )
            return {**result, **issued}


def app_secret_kind(item):
    return {
        "meta_whatsapp": "meta_app_secret",
        "facebook_login": "facebook_app_secret",
        "instagram_login": "instagram_app_secret",
        "tiktok_business": "tiktok_client_secret",
        "tiktok_login_kit": "tiktok_client_secret",
    }[item["IssuerProfile"]]


def credential_owner(c, settings, body):
    prefix, _, identity = body.owner.partition(":")
    identity = uid(identity)
    if prefix == "application":
        app = one(
            c,
            (
                "SELECT * FROM crm_channels2.Application WHERE InstitutionId="
                "? AND ApplicationId=?"
            ),
            institution(settings),
            identity,
        )
        if not app or body.kind != (
            "client_secret" if app["Provider"] == "tiktok" else "app_secret"
        ):
            raise HTTPException(422, "credential_owner_mismatch")
        kind = app_secret_kind(app)
    elif prefix == "integration":
        item = account(c, settings, identity)
        if body.kind not in {"access_token", "page_access_token", "refresh_token"}:
            raise HTTPException(422, "credential_owner_mismatch")
        if body.kind == "refresh_token":
            if item["Channel"] != "tiktok":
                raise HTTPException(422, "credential_owner_mismatch")
            kind = "tiktok_refresh"
        else:
            kind = {
                "whatsapp": "meta_permanent_access",
                "instagram": "instagram_page_access"
                if body.kind == "page_access_token"
                else "instagram_user_access",
                "facebook": "facebook_page_access"
                if body.kind == "page_access_token"
                else "facebook_user_access",
                "messenger": "facebook_page_access"
                if body.kind == "page_access_token"
                else "facebook_user_access",
                "tiktok": "tiktok_access",
            }[item["Channel"]]
    elif prefix == "endpoint":
        ep = one(
            c,
            (
                "SELECT Provider FROM crm_channels2.WebhookEndpoint WHERE Ins"
                "titutionId=? AND EndpointId=?"
            ),
            institution(settings),
            identity,
        )
        if not ep or body.kind not in {"verify_token", "webhook_secret"}:
            raise HTTPException(422, "credential_owner_mismatch")
        if body.kind == "verify_token":
            raise HTTPException(422, "verify_token_server_generated")
        if ep["Provider"] != "tiktok":
            raise HTTPException(422, "meta_signature_uses_application_secret")
        kind = "tiktok_webhook_secret"
    else:
        raise HTTPException(422, "credential_owner_mismatch")
    return prefix, identity, kind


def save_credential(settings, authority, body, remove):
    permission = (
        "settings." + ("channels" if body.scope == "channel" else "webhooks") + ".write"
    )
    raw = body.value.get_secret_value() if body.value else None
    with transaction(settings, True, anonymous=True) as c:
        actor = authorize(c, settings, authority, permission, recent=True)
        owner_type, identity, kind = credential_owner(c, settings, body)
        digest, prior = replay(
            c,
            settings,
            actor["UserId"],
            body.operation_id,
            permission,
            body.owner,
            {"kind": kind, "value": raw, "remove": remove},
        )
        if prior:
            return prior
        if remove:
            from app.institutional.channel_secrets import OWNERS

            c.execute(
                (
                    "UPDATE crm_channels2.SecretVersion SET State='revoked',Revok"
                    "edAt=SYSUTCDATETIME() WHERE InstitutionId=? AND "
                )
                + OWNERS[owner_type]
                + "=? AND Kind=? AND State IN('staged','active')",
                institution(settings),
                identity,
                kind,
            )
            result = {"removed": True}
        else:
            result = (
                put(c, settings, owner_type, identity, kind, raw)
                if raw
                else {"unchanged": True}
            )
        if owner_type in {"application", "integration"}:
            column = "ApplicationId" if owner_type == "application" else "IntegrationId"
            c.execute(
                (
                    "UPDATE crm_channels2.Integration SET VerifiedStatus='unverif"
                    "ied',RequestedStatus='paused',UpdatedAt=SYSUTCDATETIME() WHE"
                    "RE InstitutionId=? AND "
                )
                + column
                + "=?",
                institution(settings),
                identity,
            )
        record_operation(
            c,
            settings,
            actor["UserId"],
            body.operation_id,
            permission,
            body.owner,
            digest,
            result,
        )
        audit(c, settings, actor["UserId"], "channel.credential", body.owner, kind=kind)
        return result


def credentials(settings, authority, scope):
    with transaction(settings, anonymous=True) as c:
        authorize(
            c,
            settings,
            authority,
            "settings." + ("channels" if scope == "channel" else "webhooks") + ".read",
        )
        items = rows(
            c,
            (
                "SELECT SecretId,ApplicationId,IntegrationId,EndpointId,Kind,"
                "VersionNo,Hint,State,CreatedAt FROM crm_channels2.SecretVers"
                "ion WHERE InstitutionId=? AND State IN('active','staged') AN"
                "D "
            )
            + (
                "(ApplicationId IS NOT NULL OR IntegrationId IS NOT NULL)"
                if scope == "channel"
                else "EndpointId IS NOT NULL"
            )
            + " ORDER BY CreatedAt",
            institution(settings),
        )
        result = []
        for value in items:
            kind = value["Kind"]
            public_kind = (
                "app_secret"
                if kind.endswith("app_secret")
                else "client_secret"
                if kind == "tiktok_client_secret"
                else "verify_token"
                if kind == "webhook_verify"
                else "webhook_secret"
                if kind == "tiktok_webhook_secret"
                else "page_access_token"
                if "page_access" in kind
                else "refresh_token"
                if kind == "tiktok_refresh"
                else "access_token"
            )
            prefix = next(
                p
                for p, col in [
                    ("application", "ApplicationId"),
                    ("integration", "IntegrationId"),
                    ("endpoint", "EndpointId"),
                ]
                if value[col]
            )
            result.append(
                {
                    "id": uid(str(value["SecretId"])),
                    "owner": prefix
                    + ":"
                    + uid(
                        str(
                            value[
                                {
                                    "application": "ApplicationId",
                                    "integration": "IntegrationId",
                                    "endpoint": "EndpointId",
                                }[prefix]
                            ]
                        )
                    ),
                    "kind": public_kind,
                    "version": value["VersionNo"],
                    "hint": value["Hint"],
                    "state": value["State"],
                    "configured": True,
                    "verified": False,
                    "updated_at": utc(value["CreatedAt"]),
                }
            )
        return {"items": result}


def install(app, settings):
    operations = Operations(settings)

    @app.post("/api/institution/channels/{identity}/lifecycle/{action}")
    def lifecycle(request: Request, identity: str, action: str, body: EndpointAction):
        return operations.lifecycle(request.state.authority, identity, action, body)

    @app.get("/api/institution/channels/routing-options")
    def routing_options(request: Request):
        from app.modules.crm_configuration.application.service import read_configuration

        with transaction(settings, anonymous=True) as c:
            authorize(c, settings, request.state.authority, "settings.channels.read")
            config, _ = read_configuration(c, foundation=True)
            return {
                "stages": [
                    {"key": s.key, "label": s.label} for s in config.stages if s.active
                ]
            }

    @app.put("/api/institution/channels/{identity}/routing")
    def routing(request: Request, identity: str, body: RoutingEdit):
        return operations.routing(request.state.authority, identity, body)

    @app.get("/api/institution/channels/runtime")
    def runtime(request: Request):
        return operations.runtime(request.state.authority)

    @app.put("/api/institution/channels/runtime")
    def edit_runtime(request: Request, body: RuntimeEdit):
        return operations.runtime(request.state.authority, body)

    @app.post("/api/institution/channels/{identity}/webhook")
    def webhook(request: Request, identity: str, body: EndpointAction):
        return operations.webhook(request.state.authority, identity, body)

    @app.post("/api/institution/channels/{identity}/webhook/rotate")
    def rotate(request: Request, identity: str, body: EndpointIssue):
        return operations.webhook(request.state.authority, identity, body, rotate=True)
