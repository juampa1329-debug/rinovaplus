"""Provider-specific token health and renewal, with no credential values in DTOs."""

from datetime import datetime, timedelta

from app.institutional.channel_oauth import http_json
from app.modules.channels import providers


def health(adapter, item):
    if item["IssuerProfile"] == "tiktok_login_kit":
        value = http_json(
            "GET",
            "https://open.tiktokapis.com/v2/user/info/",
            params={"fields": "open_id,display_name"},
            headers={"Authorization": "Bearer " + adapter["secrets"]["accessToken"]},
        )
        user = (value.get("data") or {}).get("user") or {}
        if str(user.get("open_id")) != item["ExternalAccountId"]:
            raise providers.ProviderFailure("token_identity_mismatch")
        return {
            "asset": {
                "id": str(user["open_id"]),
                "name": str(user.get("display_name", ""))[:200],
            },
            "apiAssetValidated": True,
            "identityOnly": True,
        }
    if item["Provider"] == "tiktok":
        return providers.discover(adapter)
    if item["IssuerProfile"] == "instagram_login":
        result = providers.discover(adapter)
        result["applicationValidated"] = False
        return result
    value = (
        providers.request(
            adapter,
            "GET",
            "debug_token",
            params={
                "input_token": adapter["secrets"]["accessToken"],
                "access_token": item["ClientId"]
                + "|"
                + adapter["secrets"]["appSecret"],
            },
        ).get("data")
        or {}
    )
    if (
        value.get("is_valid") is not True
        or str(value.get("app_id")) != item["ClientId"]
    ):
        raise providers.ProviderFailure("token_application_mismatch_or_invalid")
    return {
        "applicationValidated": True,
        "tokenValid": True,
        "expiresAtEpoch": value.get("expires_at"),
        "grantedScopes": value.get("scopes", []),
    }


def renew(adapter, item):
    secrets = adapter["secrets"]
    issuer = item["IssuerProfile"]
    if issuer == "tiktok_login_kit":
        value = http_json(
            "POST",
            "https://open.tiktokapis.com/v2/oauth/token/",
            data={
                "client_key": item["ClientId"],
                "client_secret": secrets["appSecret"],
                "grant_type": "refresh_token",
                "refresh_token": secrets["refreshToken"],
            },
        )
        if (
            str(value.get("open_id")) != item["ExternalAccountId"]
            or not value.get("access_token")
            or not value.get("refresh_token")
        ):
            raise providers.ProviderFailure(
                "renewed_token_account_mismatch", uncertain=True
            )
        return {
            "_tokens": {
                "tiktok_access": value["access_token"],
                "tiktok_refresh": value["refresh_token"],
            },
            "expires_in": value.get("expires_in"),
            "_rotated": True,
        }
    if issuer == "instagram_login":
        value = http_json(
            "GET",
            "https://graph.instagram.com/refresh_access_token",
            params={
                "grant_type": "ig_refresh_token",
                "access_token": secrets["accessToken"],
            },
        )
        if not value.get("access_token"):
            raise providers.ProviderFailure("renewed_token_missing", uncertain=True)
        return {
            "_tokens": {"instagram_user_access": value["access_token"]},
            "expires_in": value.get("expires_in"),
            "_rotated": True,
        }
    if issuer != "facebook_login":
        raise providers.ProviderFailure("token_renewal_requires_provider_authorization")
    base = "https://graph.facebook.com/" + item["ApiVersion"] + "/"
    value = http_json(
        "GET",
        base + "oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": item["ClientId"],
            "client_secret": secrets["appSecret"],
            "fb_exchange_token": secrets["userToken"],
        },
    )
    access = value.get("access_token")
    if not access:
        raise providers.ProviderFailure("renewed_token_missing", uncertain=True)
    pages = http_json(
        "GET",
        base + "me/accounts",
        params={
            "fields": "id,access_token,instagram_business_account{id}",
            "limit": 100,
        },
        headers={"Authorization": "Bearer " + access},
    ).get("data", [])
    page = (
        next(
            (
                v
                for v in pages
                if str((v.get("instagram_business_account") or {}).get("id"))
                == item["ExternalAccountId"]
            ),
            None,
        )
        if item["Channel"] == "instagram"
        else next(
            (v for v in pages if str(v.get("id")) == item["ExternalAccountId"]), None
        )
    )
    if not page or not page.get("access_token"):
        raise providers.ProviderFailure("renewed_asset_not_found", uncertain=True)
    return {
        "_tokens": {
            "instagram_user_access"
            if item["Channel"] == "instagram"
            else "facebook_user_access": access,
            "instagram_page_access"
            if item["Channel"] == "instagram"
            else "facebook_page_access": page["access_token"],
        },
        "expires_in": value.get("expires_in"),
        "_rotated": True,
    }


def expiry(value):
    if type(value) is not int or not 1 <= value <= 366 * 86400:
        return None
    return datetime.utcnow() + timedelta(seconds=value)
