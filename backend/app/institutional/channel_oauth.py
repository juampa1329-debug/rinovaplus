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
from app.institutional.channels import FACEBOOK_LOGIN_CONFIGURATION
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
    if issuer == "facebook_login" and configuration_id:
        params.pop("scope")
        params["config_id"] = configuration_id
        params["override_default_response_type"] = "true"
    return (
        "https://www.facebook.com/"
        + item["ApiVersion"]
        + "/dialog/oauth?"
        + urlencode(params)
    )


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
        # Discover only the operator's configured WABA; no arbitrary tenant selection.
        parent = item["ParentExternalId"]
        if not parent or not re.fullmatch(r"[0-9]+", parent):
            raise ProviderFailure("configured_waba_required")
        data = http_json(
            "GET",
            base + parent + "/phone_numbers",
            params={"fields": "id,display_phone_number", "limit": 100},
            headers={"Authorization": "Bearer " + access},
        ).get("data", [])
        assets = [
            {
                "kind": "whatsapp_phone",
                "id": str(v["id"]),
                "parent": parent,
                "name": v.get("display_phone_number", "WhatsApp"),
                "token": access,
            }
            for v in data[:100]
            if v.get("id")
        ]
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
            if item["IssuerProfile"] == "meta_whatsapp" and not re.fullmatch(
                r"[0-9]+", item["ParentExternalId"] or ""
            ):
                raise HTTPException(409, "configured_waba_required")
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
            if item["IssuerProfile"] == "facebook_login":
                document = c.execute(
                    "SELECT Document FROM crm_access.ChannelSetting "
                    "WHERE InstitutionId=? AND IntegrationId=?",
                    institution(self.settings),
                    item["IntegrationId"],
                ).fetchval()
                if document:
                    configuration_id = json.loads(document).get(
                        FACEBOOK_LOGIN_CONFIGURATION
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
        except Exception:
            status, result = "uncertain", None
        with transaction(self.settings, True, anonymous=True) as c:
            current = account(c, self.settings, str(item["IntegrationId"]))
            current_session = c.execute(
                (
                    "SELECT Status FROM crm_channels2.OAuthSession WHERE Institut"
                    "ionId=? AND OAuthSessionId=?"
                ),
                institution(self.settings),
                session["OAuthSessionId"],
            ).fetchval()
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
                or current_session != "exchanging"
                or current["VerifiedStatus"] == "retired"
            ):
                status, result = "uncertain", None
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
                operation = str(session["OperationId"])
                c.execute(
                    (
                        "INSERT crm_channels2.ProviderOperation(InstitutionId,Operati"
                        "onId,ApplicationId,IntegrationId,ActorRef,Action,RequestDige"
                        "st,Status,ResultMetadata,EffectKey,CreatedAt,CompletedAt) VA"
                        "LUES(?,?,?,?,?,'oauth_discovery',?,'confirmed','{}',?,SYSUTC"
                        "DATETIME(),SYSUTCDATETIME())"
                    ),
                    institution(self.settings),
                    operation,
                    item["ApplicationId"],
                    item["IntegrationId"],
                    session["ActorRef"],
                    session["StateHash"],
                    session["StateHash"],
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
                    "SELECT * FROM crm_channels2.OAuthSession WHERE InstitutionId"
                    "=? AND OAuthSessionId=? AND ExpiresAt>SYSUTCDATETIME()"
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
            if not body:
                values = rows(
                    c,
                    (
                        "SELECT AssetId,Kind,ExternalId,Name FROM crm_channels2.Provi"
                        "derAsset WHERE InstitutionId=? AND OAuthSessionId=?"
                    ),
                    institution(self.settings),
                    session["OAuthSessionId"],
                )
                return {
                    "status": session["Status"],
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
                    or asset["ParentExternalId"] != item["ParentExternalId"]
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
