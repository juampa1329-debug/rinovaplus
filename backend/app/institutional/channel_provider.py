"""One C10 provider intent before network IO; ambiguous effects are never retried."""

import json
import re
from uuid import uuid4

from fastapi import HTTPException, Request
from pydantic import Field, SecretStr

from app.institutional.auth import authorize
from app.institutional.channel_operations import (
    account,
    app_secret_kind,
    configuration,
    endpoint,
    sync_route,
)
from app.institutional.channel_secrets import get, put
from app.institutional.db import bound_hash, institution, one, uid
from app.institutional.models import Strict
from app.institutional.store import transaction
from app.modules.channels import providers


class ProviderAction(Strict):
    operation_id: str
    row_version: str = Field(pattern=r"^[0-9a-f]{16}$")
    pin: SecretStr | None = None


def access_kind(item):
    return {
        "whatsapp": "meta_permanent_access",
        "instagram": "instagram_page_access"
        if item["IssuerProfile"] == "facebook_login"
        else "instagram_user_access",
        "facebook": "facebook_page_access",
        "messenger": "facebook_page_access",
        "tiktok": "tiktok_access",
    }[item["Channel"]]


def provider_account(c, settings, item, *, require_access=True, require_account=True):
    if item.get("EgressProfile") == "synthetic_no_provider":
        raise HTTPException(409, "demo_account_has_no_provider")
    if item.get("VerifiedStatus") == "retired":
        raise HTTPException(409, "account_retired")
    if item.get("Provider") == "meta" and not re.fullmatch(
        r"v[0-9]{1,2}\.[0-9]{1,2}", item["ApiVersion"] or ""
    ):
        raise HTTPException(409, "api_version_required")
    if require_account and not re.fullmatch(
        r"[A-Za-z0-9_.:-]{1,200}", item["ExternalAccountId"] or ""
    ):
        raise HTTPException(409, "external_account_required")
    if item["ParentExternalId"] and not re.fullmatch(
        r"[A-Za-z0-9_.:-]{1,200}", item["ParentExternalId"]
    ):
        raise HTTPException(422, "invalid_parent_account")
    config = {
        "phoneNumberId": item["ExternalAccountId"],
        "wabaId": item["ParentExternalId"],
        "accountId": item["ExternalAccountId"],
        "pageId": item["ExternalAccountId"],
        "appId": item["ClientId"],
        "apiVersion": item["ApiVersion"],
        "instagramLogin": "instagram"
        if item["IssuerProfile"] == "instagram_login"
        else "facebook",
    }
    secrets, version = {}, None
    if require_access:
        raw, version = get(
            c, settings, "integration", str(item["IntegrationId"]), access_kind(item)
        )
        secrets["accessToken"] = raw
    return {
        "channel": item["Channel"],
        "configuration": config,
        "secrets": secrets,
    }, version


def safe_result(action, result):
    # Never persist arbitrary provider error bodies, headers or credentials.
    if action in {"verify", "numbers", "health"}:
        return {
            key: result[key]
            for key in (
                "asset",
                "numbers",
                "apiAssetValidated",
                "supportedComments",
                "supportedMessages",
                "observedApiVersion",
                "grantedScopes",
                "identityOnly",
                "applicationValidated",
                "tokenValid",
                "expiresAtEpoch",
                "hasMoreNumbers",
            )
            if key in result
        }
    if action == "refresh":
        return {
            "confirmed": result.get("_rotated") is True,
            "expires_in": result.get("expires_in"),
        }
    return {"confirmed": result.get("success") is True}


def call_provider(adapter, action, item, pin=None):
    from app.institutional.channel_tokens import health, renew

    if action == "health":
        return health(adapter, item)
    if action == "refresh":
        return renew(adapter, item)
    if action == "numbers":
        if not item["ParentExternalId"]:
            raise providers.ProviderFailure("whatsapp_business_account_id_required")
        value = providers.request(
            adapter,
            "GET",
            item["ParentExternalId"] + "/phone_numbers",
            params={"fields": "id,display_phone_number,verified_name", "limit": 100},
        )
        return {
            "numbers": [
                {
                    k: v[k]
                    for k in ("id", "display_phone_number", "verified_name")
                    if k in v
                }
                for v in value.get("data", [])[:100]
            ],
            "hasMoreNumbers": bool((value.get("paging") or {}).get("next")),
        }
    if action in {"verify", "numbers"}:
        if item["IssuerProfile"] == "tiktok_login_kit":
            return health(adapter, item)
        value = providers.discover(adapter)
        if action == "verify" and item["Provider"] == "meta":
            value.update(health(adapter, item))
        if item["Channel"] == "tiktok":
            value["apiAssetValidated"] = True
        return value
    if action == "subscribe":
        return providers.subscribe(adapter)
    if action == "register":
        if (
            item["Channel"] != "whatsapp"
            or not pin
            or not re.fullmatch(r"[0-9]{6}", pin)
        ):
            raise HTTPException(422, "whatsapp_six_digit_pin_required")
        return providers.request(
            adapter,
            "POST",
            item["ExternalAccountId"] + "/register",
            {"messaging_product": "whatsapp", "pin": pin},
        )
    raise HTTPException(422, "unsupported_provider_action")


class ProviderOperations:
    def __init__(self, settings, transport=None):
        self.settings = settings
        # Dependency injection is code-owned; no operator-selected provider base URL.
        self.transport = transport or call_provider

    def perform(self, authority, identity, action, body):
        if action not in {
            "verify",
            "numbers",
            "subscribe",
            "register",
            "health",
            "refresh",
        }:
            raise HTTPException(404, "provider_action_not_found")
        operation = uid(body.operation_id)
        raw_pin = body.pin.get_secret_value() if body.pin else None
        if action == "register" and (
            not raw_pin or not re.fullmatch(r"[0-9]{6}", raw_pin)
        ):
            raise HTTPException(422, "whatsapp_six_digit_pin_required")
        digest = bound_hash(
            self.settings,
            {
                "identity": identity,
                "action": action,
                "pin": raw_pin,
                "row_version": body.row_version,
            },
            "provider-intent",
        )
        effect_key = (
            bound_hash(self.settings, operation, "provider-diagnostic")
            if action in {"verify", "numbers", "health"}
            else digest
        )
        with transaction(self.settings, True, anonymous=True) as c:
            actor = authorize(
                c, self.settings, authority, "settings.channels.write", recent=True
            )
            if not configuration(c, self.settings)["ModuleEnabled"]:
                raise HTTPException(403, "module_disabled")
            item = account(c, self.settings, identity)
            existing = one(
                c,
                (
                    "SELECT * FROM crm_channels2.ProviderOperation WHERE Institut"
                    "ionId=? AND OperationId=?"
                ),
                institution(self.settings),
                operation,
            )
            if existing:
                if (
                    str(existing["IntegrationId"]).lower(),
                    existing["Action"],
                    bytes(existing["RequestDigest"]),
                ) != (uid(identity), action, digest) or existing["ActorRef"] != str(
                    actor["UserId"]
                ).lower():
                    raise HTTPException(409, "operation_conflict")
                return {
                    "operation_id": operation,
                    "status": existing["Status"],
                    "code": existing["ResultCode"],
                    "result": json.loads(existing["ResultMetadata"]),
                }
            if bytes(item["RowVersion"]).hex() != body.row_version:
                raise HTTPException(409, "revision_conflict")
            if action in {"numbers", "register"} and item["Channel"] != "whatsapp":
                raise HTTPException(422, "unsupported_channel_action")
            if item["ApplicationState"] == "retired":
                raise HTTPException(409, "application_retired")
            adapter, secret_version = provider_account(
                c, self.settings, item, require_account=action != "numbers"
            )
            if (
                action in {"verify", "health", "refresh"}
                and item["Provider"] == "meta"
                or action == "refresh"
                and item["Provider"] == "tiktok"
            ):
                adapter["secrets"]["appSecret"] = get(
                    c,
                    self.settings,
                    "application",
                    str(item["ApplicationId"]),
                    app_secret_kind(item),
                )[0]
            if action == "refresh":
                if item["IssuerProfile"] == "facebook_login":
                    adapter["secrets"]["userToken"] = get(
                        c,
                        self.settings,
                        "integration",
                        identity,
                        "instagram_user_access"
                        if item["Channel"] == "instagram"
                        else "facebook_user_access",
                    )[0]
                elif item["IssuerProfile"] == "tiktok_login_kit":
                    adapter["secrets"]["refreshToken"] = get(
                        c, self.settings, "integration", identity, "tiktok_refresh"
                    )[0]
                elif item["IssuerProfile"] != "instagram_login":
                    raise HTTPException(
                        409, "token_renewal_requires_provider_authorization"
                    )
            c.execute(
                (
                    "INSERT crm_channels2.ProviderOperation(InstitutionId,Operati"
                    "onId,ApplicationId,IntegrationId,ActorRef,Action,RequestDige"
                    "st,Status,ResultMetadata,EffectKey,CreatedAt,LeaseId,LeaseUn"
                    "til,LeaseVersion,Attempts) VALUES(?,?,?,?,?,?,?,'running','{"
                    "}',?,SYSUTCDATETIME(),?,DATEADD(second,60,SYSUTCDATETIME()),"
                    "1,1)"
                ),
                institution(self.settings),
                operation,
                item["ApplicationId"],
                item["IntegrationId"],
                str(actor["UserId"]).lower(),
                action,
                digest,
                effect_key,
                str(uuid4()),
            )
        try:
            result = self.transport(adapter, action, item, raw_pin)
            safe = safe_result(action, result)
            if action == "verify" and (
                not safe.get("apiAssetValidated")
                or str(safe.get("asset", {}).get("id")) != item["ExternalAccountId"]
            ):
                raise providers.ProviderFailure("provider_asset_mismatch")
            if action in {"subscribe", "register", "refresh"} and not safe.get(
                "confirmed"
            ):
                raise providers.ProviderFailure(
                    "provider_effect_not_confirmed", uncertain=True
                )
            state, code = "confirmed", None
        except providers.ProviderFailure as error:
            state, code, safe = (
                "uncertain" if error.uncertain else "failed",
                error.code,
                {},
            )
        except Exception:
            # IO may have succeeded. No second POST after a timeout or a process
            # interruption.
            state, code, safe = "uncertain", "provider_result_unknown", {}
        with transaction(self.settings, True, anonymous=True) as c:
            current = account(c, self.settings, identity)
            changed = bytes(current["RowVersion"]) != bytes(
                item["RowVersion"]
            ) or bytes(current["ApplicationVersion"]) != bytes(
                item["ApplicationVersion"]
            )
            try:
                _, current_secret = get(
                    c, self.settings, "integration", identity, access_kind(current)
                )
                changed = changed or str(current_secret["SecretId"]) != str(
                    secret_version["SecretId"]
                )
                authorize(
                    c, self.settings, authority, "settings.channels.write", recent=True
                )
            except HTTPException:
                changed = True
            if changed:
                state, code = "uncertain", "authority_or_account_changed"
            if state == "confirmed" and action == "refresh":
                from app.institutional.channel_tokens import expiry

                tokens = result.get("_tokens") or {}
                if not tokens:
                    state, code = "uncertain", "renewed_tokens_missing"
                else:
                    for kind, raw in tokens.items():
                        put(
                            c,
                            self.settings,
                            "integration",
                            identity,
                            kind,
                            raw,
                            expires=expiry(result.get("expires_in"))
                            if kind
                            not in {
                                "facebook_page_access",
                                "instagram_page_access",
                                "tiktok_refresh",
                            }
                            else None,
                        )
                    c.execute(
                        (
                            "UPDATE crm_channels2.Integration SET Requested"
                            "Status='paused',VerifiedStatus='unverified',To"
                            "kenExpiresAt=?,UpdatedAt=SYSUTCDATETIME() WHER"
                            "E InstitutionId=? AND IntegrationId=?"
                        ),
                        expiry(result.get("expires_in")),
                        institution(self.settings),
                        identity,
                    )
            c.execute(
                (
                    "UPDATE crm_channels2.ProviderOperation SET Status=?,ResultCo"
                    "de=?,ResultMetadata=?,CompletedAt=SYSUTCDATETIME(),LeaseId=N"
                    "ULL,LeaseUntil=NULL WHERE InstitutionId=? AND OperationId=? "
                    "AND Status='running'"
                ),
                state,
                code,
                json.dumps(safe),
                institution(self.settings),
                operation,
            )
            if state == "confirmed" and action == "verify":
                c.execute(
                    (
                        "UPDATE crm_channels2.Integration SET VerifiedStatus=?,LastSy"
                        "ncAt=SYSUTCDATETIME(),UpdatedAt=SYSUTCDATETIME() WHERE Insti"
                        "tutionId=? AND IntegrationId=?"
                    ),
                    "identity_only" if safe.get("identityOnly") else "verified",
                    institution(self.settings),
                    identity,
                )
                if item["Channel"] == "tiktok":
                    scopes = safe.get("grantedScopes") or []
                    scopes = scopes.split(",") if isinstance(scopes, str) else scopes
                    c.execute(
                        (
                            "UPDATE crm_channels2.Integration SET ApprovedS"
                            "copes=? WHERE InstitutionId=? AND IntegrationI"
                            "d=?"
                        ),
                        json.dumps([str(v).strip() for v in scopes if str(v).strip()]),
                        institution(self.settings),
                        identity,
                    )
                ep, _ = endpoint(c, self.settings, current, create=True)
                sync_route(c, self.settings, current, ep["id"])
        return {
            "operation_id": operation,
            "status": state,
            "code": code,
            "result": safe,
        }


def install(app, settings):
    service = ProviderOperations(settings)

    @app.post("/api/institution/channels/{identity}/actions/{action}")
    def perform(request: Request, identity: str, action: str, body: ProviderAction):
        return service.perform(request.state.authority, identity, action, body)
