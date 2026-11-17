"""Session-bound, single-use OAuth. Tokens stay provisional until asset selection."""

import hmac
import json
import re
from datetime import timedelta
from urllib.parse import urlencode
from uuid import uuid4

import httpx2 as httpx
from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import Field

from app.institutional.auth import authorize, cookie_name
from app.institutional.channel_operations import account, app_secret_kind, configuration
from app.institutional.channel_secrets import get, put
from app.institutional.channel_text import sql_text
from app.institutional.channels import FACEBOOK_LOGIN_CONFIGURATION, WHATSAPP_LOGIN_CONFIGURATION
from app.institutional.crypto import token, token_hash
from app.institutional.db import bound_hash, institution, one, rows, uid
from app.institutional.models import Strict
from app.institutional.store import transaction
from app.modules.channels.providers import ProviderFailure

SCOPES = {
    "meta_whatsapp": {
        "business_management",
        "whatsapp_business_management",
        "whatsapp_business_messaging",
    },
    "facebook_login": {
        "pages_show_list",
        "pages_manage_metadata",
        "pages_read_engagement",
        "pages_manage_engagement",
        "pages_messaging",
        "instagram_basic",
        "instagram_manage_messages",
        "instagram_manage_comments",
    },
    "instagram_login": {
        "instagram_business_basic",
        "instagram_business_manage_messages",
        "instagram_business_manage_comments",
    },
    "tiktok_login_kit": {"user.info.basic", "user.info.profile", "user.info.stats"},
}
OAUTH_FAILURE_CODES = {
    "configured_waba_required",
    "meta_app_secret_rejected",
    "oauth_asset_missing",
    "oauth_assets_missing",
    "oauth_code_exchange_rejected",
    "oauth_invalid_assets",
    "oauth_provider_rejected",
    "oauth_response_too_large",
    "oauth_result_unknown",
    "oauth_token_missing",
    "token_application_mismatch_or_invalid",
}


class Start(Strict):
    operation_id: str
    scopes: list[str] = Field(min_length=1, max_length=12)


class SelectAsset(Strict):
    operation_id: str
    asset_id: str


def authorization_url(
    item, state, redirect, scopes, verifier, *, configuration_id=None
):
    issuer = item["IssuerProfile"]
    params = {
        "redirect_uri": redirect,
        "state": state,
        "response_type": "code",
        "scope": ",".join(scopes),
    }
    if issuer == "tiktok_login_kit":
        params["client_key"] = item["ClientId"]
        # Confidential web clients use state; no desktop-only PKCE encoding is assumed.
        return "https://www.tiktok.com/v2/auth/authorize/?" + urlencode(params)
    params["client_id"] = item["ClientId"]
    if issuer == "instagram_login":
        params["enable_fb_login"] = "0"
        return "https://www.instagram.com/oauth/authorize?" + urlencode(params)
    if not re.fullmatch(r"v[0-9]{1,2}\.[0-9]{1,2}", item["ApiVersion"] or ""):
        raise HTTPException(409, "api_version_required")
    if issuer in {"facebook_login", "meta_whatsapp"} and configuration_id:
        params.pop("scope")
        params["config_id"] = configuration_id
        params["override_default_response_type"] = "true"
    return (
        "https://www.facebook.com/"
        + item["ApiVersion"]
        + "/dialog/oauth?"
        + urlencode(params)
    )


def meta_exchange_failure(body):
    try:
        value = json.loads(body)
    except ValueError:
        return "oauth_code_exchange_rejected"
    error = value.get("error") if isinstance(value, dict) else None
    message = str(error.get("message", "")).lower() if isinstance(error, dict) else ""
    if re.search(r"\b(?:client|app|application) secret\b", message) and any(
        word in message for word in ("validating", "invalid", "mismatch")
    ):
        return "meta_app_secret_rejected"
    return "oauth_code_exchange_rejected"


def http_json(method, url, *, params=None, data=None, headers=None):
    # Every URL here is constructed from fixed provider hosts and validated paths.
    try:
        with httpx.Client(
            timeout=15, follow_redirects=False, trust_env=False
        ) as client:
            with client.stream(
                method, url, params=params, data=data, headers=headers
            ) as response:
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > 1_000_000:
                        raise ProviderFailure(
                            "oauth_response_too_large", uncertain=True
                        )
                if response.status_code >= 300:
                    if response.status_code in (400, 401) and re.fullmatch(
                        r"https://graph\.facebook\.com/v[0-9]{1,2}\.[0-9]{1,2}/oauth/access_token", url
                    ):
                        raise ProviderFailure(meta_exchange_failure(body))
                    raise ProviderFailure(
                        "oauth_provider_rejected", uncertain=response.status_code >= 500
                    )
                value = json.loads(body)
                error = value.get("error") if isinstance(value, dict) else None
                if (
                    not isinstance(value, dict)
                    or error
                    and not (isinstance(error, dict) and error.get("code") == "ok")
                ):
                    raise ProviderFailure("oauth_provider_rejected")
                return value
    except ProviderFailure:
        raise
    except Exception:
        raise ProviderFailure("oauth_result_unknown", uncertain=True) from None


WHATSAPP_PHONE_FIELDS = "id,display_phone_number,verified_name"


def graph_items(value, limit=100):
    data = value.get("data") if isinstance(value, dict) else None
    return [row for row in data[:limit] if isinstance(row, dict)] if isinstance(data, list) else []


def graph_id(value):
    identifier = str(value) if isinstance(value, (int, str)) else ""
    return identifier if re.fullmatch(r"[0-9]{1,32}", identifier) else ""


def whatsapp_assets(base, item, secret, access):
    headers = {"Authorization": "Bearer " + access}
    parent = item["ParentExternalId"]
    if parent:
        parent = graph_id(parent)
        if not parent:
            raise ProviderFailure("configured_waba_required")
        accounts = [{
            "id": parent,
            "phone_numbers": http_json(
                "GET", base + parent + "/phone_numbers",
                params={"fields": WHATSAPP_PHONE_FIELDS, "limit": 100},
                headers=headers,
            ),
        }]
    else:
        phone_edge = "phone_numbers.limit(25){" + WHATSAPP_PHONE_FIELDS + "}"
        account_fields = "{id,name," + phone_edge + "}"
        edges = ("owned_whatsapp_business_accounts", "client_whatsapp_business_accounts")
        fields = "id," + ",".join(edge + ".limit(25)" + account_fields for edge in edges)
        accounts = []
        try:
            businesses = graph_items(http_json(
                "GET", base + "me/businesses",
                params={"fields": fields, "limit": 25}, headers=headers,
            ), 25)
            accounts = [waba for business in businesses for edge in edges
                        for waba in graph_items(business.get(edge), 25)]
        except ProviderFailure as error:
            if error.uncertain:
                raise

        if not any(graph_items(waba.get("phone_numbers")) for waba in accounts):
            debug = http_json(
                "GET", base + "debug_token",
                params={"input_token": access},
                headers={"Authorization": f"Bearer {item['ClientId']}|{secret}"},
            ).get("data") or {}
            if debug.get("is_valid") is not True or str(debug.get("app_id")) != item["ClientId"]:
                raise ProviderFailure("token_application_mismatch_or_invalid")
            targets = dict.fromkeys(
                identifier
                for scope in debug.get("granular_scopes", [])
                if isinstance(scope, dict) and scope.get("scope") == "whatsapp_business_management"
                for target in scope.get("target_ids", [])
                if (identifier := graph_id(target))
            )
            if targets:
                selected = http_json(
                    "GET", base, params={
                        "ids": ",".join(list(targets)[:25]), "fields": "id,name," + phone_edge,
                    }, headers=headers,
                )
                accounts = [
                    value for key, value in selected.items()
                    if key in targets and isinstance(value, dict) and graph_id(value.get("id")) == key
                ]
    assets = {}
    for account in accounts:
        waba = graph_id(account.get("id"))
        if not waba:
            continue
        for phone in graph_items(account.get("phone_numbers")):
            identifier = graph_id(phone.get("id"))
            if not identifier or identifier in assets:
                continue
            label = phone.get("display_phone_number") or phone.get("verified_name") or "WhatsApp"
            assets[identifier] = {
                "kind": "whatsapp_phone", "id": identifier, "parent": waba,
                "name": f"{account['name']} · {label}" if account.get("name") else label,
                "token": access,
            }
            if len(assets) == 100:
                return list(assets.values())
    return list(assets.values())


def exchange(item, secret, code, redirect, verifier):
    issuer = item["IssuerProfile"]
    if issuer == "tiktok_login_kit":
        value = http_json(
            "POST",
            "https://open.tiktokapis.com/v2/oauth/token/",
            data={
                "client_key": item["ClientId"],
                "client_secret": secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect,
            },
        )
        access = value.get("access_token")
        if not access or not value.get("open_id"):
            raise ProviderFailure("oauth_token_missing")
        return {
            "access": access,
            "expires_in": value.get("expires_in"),
            "refresh": value.get("refresh_token"),
            "scopes": str(value.get("scope", "")).split(","),
            "assets": [
                {
                    "kind": "login_identity",
                    "id": str(value["open_id"]),
                    "name": "Cuenta TikTok",
                    "token": access,
                }
            ],
        }
    if issuer == "instagram_login":
        value = http_json(
            "POST",
            "https://api.instagram.com/oauth/access_token",
            data={
                "client_id": item["ClientId"],
                "client_secret": secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect,
            },
        )
        access = value.get("access_token")
        if not access:
            raise ProviderFailure("oauth_token_missing")
        who = http_json(
            "GET",
            "https://graph.instagram.com/" + item["ApiVersion"] + "/me",
            params={"fields": "id,user_id,username", "access_token": access},
        )
        identity = str(who.get("user_id") or who.get("id") or "")
        if not identity:
            raise ProviderFailure("oauth_asset_missing")
        return {
            "access": access,
            "expires_in": value.get("expires_in"),
            "scopes": [],
            "assets": [
                {
                    "kind": "instagram_account",
                    "id": identity,
                    "name": who.get("username", "Instagram"),
                    "token": access,
                }
            ],
        }
    base = "https://graph.facebook.com/" + item["ApiVersion"] + "/"
    value = http_json(
        "GET",
        base + "oauth/access_token",
        params={
            "client_id": item["ClientId"],
            "client_secret": secret,
            "code": code,
            "redirect_uri": redirect,
        },
    )
    access = value.get("access_token")
    if not access:
        raise ProviderFailure("oauth_token_missing")
    assets = []
    if issuer == "meta_whatsapp":
        assets = whatsapp_assets(base, item, secret, access)
    else:
        data = http_json(
            "GET",
            base + "me/accounts",
            params={
                "fields": "id,name,access_token,instagram_business_account{id,username}"
                if item["Channel"] == "instagram"
                else "id,name,access_token",
                "limit": 100,
            },
            headers={"Authorization": "Bearer " + access},
        ).get("data", [])
        for page in data:
            if item["Channel"] == "instagram":
                ig = page.get("instagram_business_account") or {}
                if ig.get("id") and page.get("access_token"):
                    assets.append(
                        {
                            "kind": "instagram_account",
                            "id": str(ig["id"]),
                            "parent": str(page["id"]),
                            "name": ig.get("username", "Instagram"),
                            "token": page["access_token"],
                        }
                    )
            elif page.get("id") and page.get("access_token"):
                assets.append(
                    {
                        "kind": "facebook_page",
                        "id": str(page["id"]),
                        "name": page.get("name", "Facebook"),
                        "token": page["access_token"],
                    }
                )
    if not assets:
        raise ProviderFailure("oauth_assets_missing")
    # Pagination requires a fresh explicit discovery; provider-supplied next URLs are
    # never fetched.
    return {
        "access": access,
        "expires_in": value.get("expires_in"),
        "scopes": [],
        "assets": assets[:100],
    }


class OAuth:
    def __init__(self, settings, transport=None):
        self.settings = settings
        self.transport = transport or exchange

    def start(self, authority, identity, body):
        with transaction(self.settings, True, anonymous=True) as c:
            actor = authorize(
                c, self.settings, authority, "settings.channels.write", recent=True
            )
            item = account(c, self.settings, identity)
            if item["VerifiedStatus"] == "retired":
                raise HTTPException(409, "account_retired")
            if item["EgressProfile"] == "synthetic_no_provider":
                raise HTTPException(409, "demo_account_has_no_provider")
            config = configuration(c, self.settings)
            if not config["ModuleEnabled"]:
                raise HTTPException(403, "module_disabled")
            origin = config["PublicBaseUrl"]
            if not origin:
                raise HTTPException(409, "public_https_origin_required")
            if item["IssuerProfile"] not in SCOPES:
                raise HTTPException(
                    409, "tiktok_accounts_authorization_profile_required"
                )
            if (
                len(set(body.scopes)) != len(body.scopes)
                or not set(body.scopes) <= SCOPES[item["IssuerProfile"]]
            ):
                raise HTTPException(422, "unsupported_oauth_scope")
            secret, secret_row = get(
                c,
                self.settings,
                "application",
                str(item["ApplicationId"]),
                app_secret_kind(item),
            )
            operation = uid(body.operation_id)
            if c.execute(
                (
                    "SELECT 1 FROM crm_channels2.OAuthSession WHERE InstitutionId"
                    "=? AND OperationId=?"
                ),
                institution(self.settings),
                operation,
            ).fetchone():
                raise HTTPException(409, "oauth_start_already_issued")
            if c.execute(
                (
                    "SELECT 1 FROM crm_channels2.OAuthSession WHERE InstitutionId"
                    "=? AND IntegrationId=? AND Status='exchanging'"
                ),
                institution(self.settings),
                item["IntegrationId"],
            ).fetchone():
                raise HTTPException(409, "oauth_exchange_in_progress")
            c.execute(
                (
                    "UPDATE crm_channels2.OAuthSession SET Status='cancelled',Com"
                    "pletedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND Integrat"
                    "ionId=? AND Status IN('pending','assets_ready')"
                ),
                institution(self.settings),
                item["IntegrationId"],
            )
            redirect = origin + "/hooks/oauth/" + str(item["ApplicationId"]).lower()
            state, oauth_id = token(), str(uuid4())
            configuration_id = None
            if item["IssuerProfile"] in {"facebook_login", "meta_whatsapp"}:
                document = c.execute(
                    "SELECT Document FROM crm_access.ChannelSetting "
                    "WHERE InstitutionId=? AND IntegrationId=?",
                    institution(self.settings),
                    item["IntegrationId"],
                ).fetchval()
                if document:
                    configuration_id = json.loads(document).get(
                        FACEBOOK_LOGIN_CONFIGURATION if item["IssuerProfile"] == "facebook_login"
                        else WHATSAPP_LOGIN_CONFIGURATION
                    )
            url = authorization_url(
                item, state, redirect, body.scopes, None, configuration_id=configuration_id
            )
            # Exact application version, session and secret version survive the browser
            # redirect.
            c.execute(
                (
                    "INSERT crm_channels2.OAuthSession(InstitutionId,OAuthSession"
                    "Id,ApplicationId,IntegrationId,ActorRef,AuthSessionHash,Stat"
                    "eHash,IssuerProfile,RedirectUri,RequestedScopes,Status,Expir"
                    "esAt,OperationId,ApplicationVersion,CreatedAt,ClientSecretId"
                    ",ClientSecretVersionNo,GrantScope) VALUES(?,?,?,?,?,?,?,?,?,"
                    "?,'pending',DATEADD(minute,10,SYSUTCDATETIME()),?,?,SYSUTCDA"
                    "TETIME(),?,?,'bound_connection')"
                ),
                institution(self.settings),
                oauth_id,
                item["ApplicationId"],
                item["IntegrationId"],
                str(actor["UserId"]).lower(),
                bound_hash(self.settings, authority["token"], "oauth-session"),
                token_hash(state),
                item["IssuerProfile"],
                redirect,
                json.dumps(body.scopes),
                operation,
                item["ApplicationVersion"],
                secret_row["SecretId"],
                secret_row["VersionNo"],
            )
            return {
                "oauth_session_id": oauth_id,
                "authorization_url": url,
                "callback_url": redirect,
                "expires_in": 600,
            }

    def callback(self, application, state, code, raw_session, *, denied=False):
        if not state or len(state) > 256 or len(code) > 4096:
            raise HTTPException(403, "oauth_state_rejected")
        authority = {
            "token": raw_session,
            "method": "GET",
            "permission": "settings.channels.write",
            "module": "settings",
            "resource": "/hooks/oauth/{application}",
        }
        with transaction(self.settings, True, anonymous=True) as c:
            actor = authorize(
                c, self.settings, authority, "settings.channels.write", recent=True
            )
            if not configuration(c, self.settings)["ModuleEnabled"]:
                raise HTTPException(403, "module_disabled")
            session = one(
                c,
                (
                    "SELECT * FROM crm_channels2.OAuthSession WITH(UPDLOCK,HOLDLO"
                    "CK) WHERE InstitutionId=? AND ApplicationId=? AND StateHash="
                    "? AND ExpiresAt>SYSUTCDATETIME()"
                ),
                institution(self.settings),
                uid(application),
                token_hash(state),
            )
            if (
                not session
                or session["Status"] != "pending"
                or session["ActorRef"] != str(actor["UserId"]).lower()
                or not hmac.compare_digest(
                    bytes(session["AuthSessionHash"]),
                    bound_hash(self.settings, raw_session, "oauth-session"),
                )
            ):
                raise HTTPException(403, "oauth_state_rejected")
            item = account(c, self.settings, str(session["IntegrationId"]))
            expected_redirect = (
                configuration(c, self.settings)["PublicBaseUrl"]
                + "/hooks/oauth/"
                + uid(application)
            )
            if (
                bytes(session["ApplicationVersion"])
                != bytes(item["ApplicationVersion"])
                or session["IssuerProfile"] != item["IssuerProfile"]
                or expected_redirect != session["RedirectUri"]
            ):
                raise HTTPException(409, "oauth_application_changed")
            secret, secret_row = get(
                c, self.settings, "application", application, app_secret_kind(item)
            )
            if (
                str(secret_row["SecretId"]) != str(session["ClientSecretId"])
                or secret_row["VersionNo"] != session["ClientSecretVersionNo"]
            ):
                raise HTTPException(409, "oauth_credential_changed")
            return_context = {
                "integration_id": uid(str(item["IntegrationId"])),
                "oauth_session_id": uid(str(session["OAuthSessionId"])),
            }
            if not code or denied:
                c.execute(
                    (
                        "UPDATE crm_channels2.OAuthSession SET Status='cancelled',Com"
                        "pletedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND OAuthSes"
                        "sionId=?"
                    ),
                    institution(self.settings),
                    session["OAuthSessionId"],
                )
                return {"status": "cancelled", **return_context}
            c.execute(
                (
                    "UPDATE crm_channels2.OAuthSession SET Status='exchanging',Cl"
                    "aimId=?,ClaimUntil=DATEADD(second,60,SYSUTCDATETIME()),Claim"
                    "Version=ClaimVersion+1 WHERE InstitutionId=? AND OAuthSessio"
                    "nId=? AND Status='pending'"
                ),
                str(uuid4()),
                institution(self.settings),
                session["OAuthSessionId"],
            )
        failure = None
        try:
            result = self.transport(item, secret, code, session["RedirectUri"], None)
            if (
                not isinstance(result, dict)
                or not result.get("access")
                or not 1 <= len(result.get("assets", [])) <= 100
            ):
                raise ProviderFailure("oauth_invalid_assets", uncertain=True)
            status = "assets_ready"
        except ProviderFailure as error:
            status, result = "uncertain" if error.uncertain else "failed", None
            failure = error.code if error.code in OAUTH_FAILURE_CODES else "oauth_result_unknown"
        except Exception:
            status, result = "uncertain", None
            failure = "oauth_result_unknown"
        with transaction(self.settings, True, anonymous=True) as c:
            current = account(c, self.settings, str(item["IntegrationId"]))
            current_session = c.execute(
                (
                    "SELECT Status FROM crm_channels2.OAuthSession WITH(UPDLOCK,HOLDLOCK) WHERE Institut"
                    "ionId=? AND OAuthSessionId=?"
                ),
                institution(self.settings),
                session["OAuthSessionId"],
            ).fetchval()
            if current_session != "exchanging":
                return {"status": current_session or "uncertain", **return_context}
            try:
                authorize(
                    c, self.settings, authority, "settings.channels.write", recent=True
                )
                _, active_secret = get(
                    c,
                    self.settings,
                    "application",
                    application,
                    app_secret_kind(current),
                )
                unchanged = bytes(current["ApplicationVersion"]) == bytes(
                    item["ApplicationVersion"]
                ) and str(active_secret["SecretId"]) == str(secret_row["SecretId"])
            except HTTPException:
                unchanged = False
            if (
                not unchanged
                or current["VerifiedStatus"] == "retired"
            ):
                status, result = "uncertain", None
                failure = "oauth_authority_or_configuration_changed"
            operation = str(session["OperationId"])
            c.execute(
                (
                    "INSERT crm_channels2.ProviderOperation(InstitutionId,OperationId,"
                    "ApplicationId,IntegrationId,ActorRef,Action,RequestDigest,Status,"
                    "ResultCode,ResultMetadata,EffectKey,CreatedAt,CompletedAt) "
                    "VALUES(?,?,?,?,?,'oauth_discovery',?,?,?,'{}',?,SYSUTCDATETIME(),SYSUTCDATETIME())"
                ),
                institution(self.settings),
                operation,
                item["ApplicationId"],
                item["IntegrationId"],
                session["ActorRef"],
                session["StateHash"],
                "confirmed" if result else status,
                failure,
                session["StateHash"],
            )
            if result:
                oauth_id = str(session["OAuthSessionId"])
                put(
                    c,
                    self.settings,
                    "oauth",
                    oauth_id,
                    "oauth_provisional_access",
                    result["access"],
                    state="staged",
                    expires=session["ExpiresAt"],
                )
                if result.get("refresh"):
                    put(
                        c,
                        self.settings,
                        "oauth",
                        oauth_id,
                        "oauth_provisional_refresh",
                        result["refresh"],
                        state="staged",
                        expires=session["ExpiresAt"],
                    )
                for asset in result["assets"]:
                    external = str(asset.get("id", ""))
                    if not re.fullmatch(
                        r"[A-Za-z0-9_.:-]{1,200}", external
                    ) or asset.get("kind") not in {
                        "whatsapp_phone",
                        "facebook_page",
                        "instagram_account",
                        "login_identity",
                    }:
                        raise HTTPException(502, "oauth_invalid_asset")
                    asset_id = str(uuid4())
                    c.execute(
                        (
                            "INSERT crm_channels2.ProviderAsset(Institution"
                            "Id,AssetId,ApplicationId,OAuthSessionId,Kind,E"
                            "xternalId,ParentExternalId,Name,ObservedScopes"
                            ",Metadata,ObservedAt,ExpiresAt,DiscoveryOperat"
                            "ionId,IntegrationId) VALUES(?,?,?,?,?,?,?,?,?,"
                            "?,SYSUTCDATETIME(),?,?,?)"
                        ),
                        institution(self.settings),
                        asset_id,
                        item["ApplicationId"],
                        session["OAuthSessionId"],
                        asset["kind"],
                        external,
                        asset.get("parent"),
                        sql_text(asset.get("name", ""), 200),
                        json.dumps(result.get("scopes", [])),
                        json.dumps(
                            {
                                "expires_in": result.get("expires_in")
                                if type(result.get("expires_in")) is int
                                else None
                            }
                        ),
                        session["ExpiresAt"],
                        operation,
                        item["IntegrationId"],
                    )
                    put(
                        c,
                        self.settings,
                        "asset",
                        asset_id,
                        "oauth_asset_access",
                        asset.get("token") or result["access"],
                        state="staged",
                        expires=session["ExpiresAt"],
                    )
            c.execute(
                (
                    "UPDATE crm_channels2.OAuthSession SET Status=?,ClaimId=NULL,"
                    "ClaimUntil=NULL,CompletedAt=CASE WHEN ?='assets_ready' THEN "
                    "NULL ELSE SYSUTCDATETIME() END WHERE InstitutionId=? AND OAu"
                    "thSessionId=? AND Status='exchanging'"
                ),
                status,
                status,
                institution(self.settings),
                session["OAuthSessionId"],
            )
        return {"status": status, **return_context}

    def assets(self, authority, session_id, body=None):
        with transaction(self.settings, body is not None, anonymous=True) as c:
            actor = authorize(
                c,
                self.settings,
                authority,
                "settings.channels.write",
                recent=body is not None,
            )
            session = one(
                c,
                (
                    "SELECT *,CASE WHEN ExpiresAt<=SYSUTCDATETIME() "
                    "THEN 1 ELSE 0 END AS Expired FROM crm_channels2.OAuthSession "
                    "WHERE InstitutionId=? AND OAuthSessionId=?"
                ),
                institution(self.settings),
                uid(session_id),
            )
            if (
                not session
                or session["ActorRef"] != str(actor["UserId"]).lower()
                or not hmac.compare_digest(
                    bytes(session["AuthSessionHash"]),
                    bound_hash(self.settings, authority["token"], "oauth-session"),
                )
            ):
                raise HTTPException(404, "oauth_session_not_found")
            if session["Expired"]:
                if body is not None:
                    raise HTTPException(409, "oauth_session_expired")
                if session["Status"] in {"pending", "exchanging", "assets_ready"}:
                    return {"status": "expired", "code": None, "items": []}
            if body is None:
                values = []
                if session["Status"] == "assets_ready":
                    values = rows(
                        c,
                        "SELECT AssetId,Kind,ExternalId,Name FROM crm_channels2.ProviderAsset "
                        "WHERE InstitutionId=? AND OAuthSessionId=?",
                        institution(self.settings),
                        session["OAuthSessionId"],
                    )
                return {
                    "status": session["Status"],
                    "code": c.execute(
                        "SELECT ResultCode FROM crm_channels2.ProviderOperation "
                        "WHERE InstitutionId=? AND OperationId=? AND IntegrationId=? "
                        "AND Action='oauth_discovery'",
                        institution(self.settings), session["OperationId"], session["IntegrationId"],
                    ).fetchval(),
                    "items": [
                        {
                            "id": uid(str(v["AssetId"])),
                            "kind": v["Kind"],
                            "external_id": v["ExternalId"],
                            "name": v["Name"],
                        }
                        for v in values
                    ],
                }
            if session["Status"] != "assets_ready":
                raise HTTPException(409, "oauth_selection_unavailable")
            item = account(c, self.settings, str(session["IntegrationId"]))
            if item["VerifiedStatus"] == "retired":
                raise HTTPException(409, "account_retired")
            if bytes(item["ApplicationVersion"]) != bytes(
                session["ApplicationVersion"]
            ):
                raise HTTPException(409, "oauth_application_changed")
            asset = one(
                c,
                (
                    "SELECT * FROM crm_channels2.ProviderAsset WHERE InstitutionI"
                    "d=? AND AssetId=? AND OAuthSessionId=? AND ApplicationId=? A"
                    "ND IntegrationId=?"
                ),
                institution(self.settings),
                uid(body.asset_id),
                session["OAuthSessionId"],
                item["ApplicationId"],
                item["IntegrationId"],
            )
            if (
                not asset
                or item["ExternalAccountId"]
                and item["ExternalAccountId"] != asset["ExternalId"]
                or item["IssuerProfile"] == "meta_whatsapp"
                and (
                    asset["Kind"] != "whatsapp_phone"
                    or not graph_id(asset["ParentExternalId"])
                    or item["ParentExternalId"]
                    and asset["ParentExternalId"] != item["ParentExternalId"]
                )
            ):
                raise HTTPException(409, "oauth_account_mismatch")
            from app.institutional.channel_provider import access_kind

            access, _ = get(
                c, self.settings, "asset", body.asset_id, "oauth_asset_access"
            )
            lifetime = json.loads(asset["Metadata"]).get("expires_in")
            expires = (
                asset["ObservedAt"] + timedelta(seconds=max(0, lifetime - 60))
                if type(lifetime) is int and 1 <= lifetime <= 366 * 86400
                else None
            )
            put(
                c,
                self.settings,
                "integration",
                str(item["IntegrationId"]),
                access_kind(item),
                access,
                expires=expires
                if access_kind(item)
                not in {"facebook_page_access", "instagram_page_access"}
                else None,
            )
            if item["IssuerProfile"] == "facebook_login":
                user_access, _ = get(
                    c,
                    self.settings,
                    "oauth",
                    str(session["OAuthSessionId"]),
                    "oauth_provisional_access",
                )
                put(
                    c,
                    self.settings,
                    "integration",
                    str(item["IntegrationId"]),
                    "instagram_user_access"
                    if item["Channel"] == "instagram"
                    else "facebook_user_access",
                    user_access,
                    expires=expires,
                )
            elif asset["Kind"] == "login_identity":
                try:
                    refresh, _ = get(
                        c,
                        self.settings,
                        "oauth",
                        str(session["OAuthSessionId"]),
                        "oauth_provisional_refresh",
                    )
                except HTTPException:
                    refresh = None
                if refresh:
                    put(
                        c,
                        self.settings,
                        "integration",
                        str(item["IntegrationId"]),
                        "tiktok_refresh",
                        refresh,
                    )
            c.execute(
                (
                    "UPDATE crm_channels2.Integration SET ExternalAccountId=?,Par"
                    "entExternalId=?,RequestedStatus='paused',VerifiedStatus='unv"
                    "erified',UpdatedAt=SYSUTCDATETIME() WHERE InstitutionId=? AN"
                    "D IntegrationId=?"
                ),
                asset["ExternalId"],
                asset["ParentExternalId"],
                institution(self.settings),
                item["IntegrationId"],
            )
            c.execute(
                (
                    "UPDATE crm_channels2.OAuthSession SET Status='completed',Com"
                    "pletedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND OAuthSes"
                    "sionId=?"
                ),
                institution(self.settings),
                session["OAuthSessionId"],
            )
            return {
                "status": "completed",
                "integration_id": str(item["IntegrationId"]).lower(),
                "verification_required": True,
            }


def install(app, settings):
    service = OAuth(settings)

    @app.post("/api/institution/channels/{identity}/oauth")
    def start(request: Request, identity: str, body: Start):
        return service.start(request.state.authority, identity, body)

    @app.get("/api/institution/channels/oauth/{session_id}/assets")
    def assets(request: Request, session_id: str):
        return service.assets(request.state.authority, session_id)

    @app.post("/api/institution/channels/oauth/{session_id}/select")
    def select(request: Request, session_id: str, body: SelectAsset):
        return service.assets(request.state.authority, session_id, body)

    @app.get("/hooks/oauth/{application}", include_in_schema=False)
    def callback(request: Request, application: str):
        q = request.query_params
        if len(q.getlist("state")) != 1 or len(q.getlist("code")) > 1:
            raise HTTPException(403, "oauth_state_rejected")
        try:
            result = service.callback(
                application,
                q.get("state", ""),
                q.get("code", ""),
                request.cookies.get(cookie_name(settings), ""),
                denied=bool(q.get("error")),
            )
            path = f"/#/channels/oauth/{result['integration_id']}/{result['oauth_session_id']}"
        except HTTPException as error:
            if error.detail != "password_confirmation_required":
                raise
            path = "/#/channels/oauth/confirm"
        return RedirectResponse(
            path,
            status_code=303,
            headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"},
        )
