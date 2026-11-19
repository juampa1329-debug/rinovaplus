"""Authenticated lookup of model identifiers using the institution's stored key."""

import asyncio

from fastapi import HTTPException, Request
from starlette.concurrency import run_in_threadpool

from app.institutional.auth import authorize
from app.institutional.crypto import unseal
from app.institutional.db import institution, key, one, uid
from app.institutional.models import PROVIDER_CATEGORIES
from app.institutional.store import transaction
from app.modules.ai.infrastructure.providers import AiError, ProviderGateway

CATALOG_PROVIDERS = {
    "gemini", "openrouter", "openai", "anthropic", "hermes", "kimi",
    "groq", "nvidia", "mistral", "xai",
}


def credential(settings, authority, provider):
    institution_id = institution(settings)
    with transaction(settings, anonymous=True) as c:
        authorize(c, settings, authority, "settings.providers.read")
        secret = one(
            c,
            "SELECT SecretId,VersionNo,Nonce,Ciphertext FROM crm_access.Secret "
            "WHERE InstitutionId=? AND Scope='provider' AND OwnerRef=? "
            "AND Kind='api_key' AND State='staged'",
            institution_id,
            provider,
        )
        if not secret:
            raise HTTPException(409, "provider_key_missing")
        return unseal(
            key(settings),
            {
                "institution": institution_id, "scope": "provider",
                "owner": provider, "kind": "api_key",
                "version": secret["VersionNo"], "secret_id": uid(str(secret["SecretId"])),
            },
            secret["Nonce"],
            secret["Ciphertext"],
        )


def install(app, settings):
    @app.get("/api/institution/provider-catalog/{provider}/{category}")
    async def live_models(request: Request, provider: str, category: str):
        if provider == "elevenlabs" and category == "voice":
            from app.institutional.voice_audio import catalog_for
            value = await run_in_threadpool(credential, settings, request.state.authority, provider)
            try:
                catalog = await catalog_for(value)
            except AiError as error:
                raise HTTPException(error.status, error.code) from None
            if await run_in_threadpool(credential, settings, request.state.authority, provider) != value:
                raise HTTPException(409, "voice_configuration_changed")
            return {"items": catalog["models"]}
        if provider not in CATALOG_PROVIDERS or category not in PROVIDER_CATEGORIES[provider]:
            raise HTTPException(404, "provider_catalog_unavailable")
        secret = await run_in_threadpool(credential, settings, request.state.authority, provider)
        try:
            async with asyncio.timeout(36):
                models = await ProviderGateway({provider: secret}).models(
                    provider, category, account_catalog=True
                )
        except TimeoutError:
            raise HTTPException(504, "provider_catalog_timeout") from None
        except AiError as error:
            detail = "provider_key_rejected" if error.upstream_status in {401, 403} else error.code
            raise HTTPException(error.status, detail) from None
        return {"items": [{"id": model.id, "name": model.name} for model in models]}
