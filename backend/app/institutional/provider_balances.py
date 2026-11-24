"""Read-only account snapshots. Never inference, top-up or subscription changes."""

import asyncio
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import HTTPException, Request
from starlette.concurrency import run_in_threadpool

from app.institutional.auth import authorize
from app.institutional.crypto import unseal
from app.institutional.db import institution, key, one, uid
from app.institutional.provider_catalog import credential
from app.institutional.store import transaction
from app.institutional.voice_audio import public_balance
from app.modules.ai.infrastructure.media import MediaGateway
from app.modules.ai.infrastructure.providers import AiError, ProviderGateway


def management_credential(settings, authority):
    with transaction(settings, anonymous=True) as c:
        authorize(c, settings, authority, "settings.providers.read")
        row = one(c, "SELECT SecretId,VersionNo,Nonce,Ciphertext FROM crm_access.Secret "
                  "WHERE InstitutionId=? AND Scope='provider' AND OwnerRef='openrouter' "
                  "AND Kind='management_key' AND State='staged'", institution(settings))
        if not row:
            return None
        return unseal(key(settings), {"institution": institution(settings), "scope": "provider",
                      "owner": "openrouter", "kind": "management_key", "version": row["VersionNo"],
                      "secret_id": uid(str(row["SecretId"]))}, row["Nonce"], row["Ciphertext"])


def number(data, name, *, required=False):
    value = data.get(name)
    if value is None and not required:
        return None
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise AiError("provider_invalid_response", 502)
    return value


def safe_key(value):
    data = value.get("data") if isinstance(value, dict) else None
    if not isinstance(data, dict):
        raise AiError("provider_invalid_response", 502)
    result = {name: number(data, name, required=name == "usage") for name in
              ("usage", "usage_daily", "usage_weekly", "usage_monthly", "limit", "limit_remaining")}
    reset = data.get("limit_reset")
    result["limit_reset"] = reset if isinstance(reset, str) and reset in {"daily", "weekly", "monthly"} else None
    return result


def safe_credits(value):
    data = value.get("data") if isinstance(value, dict) else None
    if not isinstance(data, dict):
        raise AiError("provider_invalid_response", 502)
    total, used = number(data, "total_credits", required=True), number(data, "total_usage", required=True)
    return {"total_credits": total, "total_usage": used, "remaining": total - used}


async def collect(provider, api_key, account_key=None, *, transport=None):
    if provider == "elevenlabs":
        raw = await MediaGateway({provider: api_key}, Path("."), transport=transport).request(provider, "GET", "v1/user/subscription")
        result = {"provider": provider, "quota": public_balance(raw)}
        result["quota"]["tier"] = raw["tier"][:80] if isinstance(raw.get("tier"), str) else ""
        result["voice_slots"] = {name: value if type(value := raw.get(name)) is int and value >= 0 else None
                                 for name in ("voice_slots_used", "voice_limit")}
        result["overage_enabled"] = raw.get("can_extend_character_limit") if type(raw.get("can_extend_character_limit")) is bool else None
        result["links"] = {"billing": "https://elevenlabs.io/app/subscription", "usage": "https://elevenlabs.io/app/usage"}
    else:
        result = {"provider": provider, "currency": "USD", "key": None, "account": None,
                  "account_status": "management_key_required", "key_status": "unavailable",
                  "links": {"billing": "https://openrouter.ai/settings/credits", "usage": "https://openrouter.ai/activity"}}
        try:
            result["key"] = safe_key(await ProviderGateway({provider: api_key}, transport=transport).request(provider, "GET", "key"))
            result["key_status"] = "available"
        except AiError as error:
            result["key_status"] = "key_rejected" if error.upstream_status in {401, 403} else "unavailable"
        if account_key:
            try:
                result["account"] = safe_credits(await ProviderGateway({provider: account_key}, transport=transport).request(provider, "GET", "credits"))
                result["account_status"] = "available"
            except AiError as error:
                result["account_status"] = "management_key_rejected" if error.upstream_status in {401, 403} else "unavailable"
    result["checked_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return result


def install(app, settings):
    @app.get("/api/institution/provider-balance/openrouter/alert")
    def alert_status(request: Request):
        from app.institutional.balance_alerts import public_status
        with transaction(settings, anonymous=True) as c:
            authorize(c, settings, request.state.authority, "settings.budgets.read")
            return public_status(c, settings)

    @app.get("/api/institution/provider-balance/{provider}")
    async def balance(request: Request, provider: Literal["openrouter", "elevenlabs"]):
        authority = request.state.authority
        secret = await run_in_threadpool(credential, settings, authority, provider)
        account_key = await run_in_threadpool(management_credential, settings, authority) if provider == "openrouter" else None
        try:
            async with asyncio.timeout(25):
                result = await collect(provider, secret, account_key)
        except TimeoutError:
            raise HTTPException(504, "provider_balance_timeout") from None
        except AiError as error:
            code = "provider_key_rejected" if error.upstream_status in {401, 403} else error.code
            raise HTTPException(error.status, code) from None
        if await run_in_threadpool(credential, settings, authority, provider) != secret:
            raise HTTPException(409, "provider_balance_changed")
        if provider == "openrouter" and await run_in_threadpool(management_credential, settings, authority) != account_key:
            raise HTTPException(409, "provider_balance_changed")
        return result
