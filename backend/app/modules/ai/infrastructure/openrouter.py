"""Bounded OpenRouter chat adapter; no tools, redirects or implicit activation."""

import asyncio
import json
import math
import random
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx2 as httpx

from app.branding import PRODUCT_NAME

from .providers import AiError

# Only explicit rejection responses can safely repeat inference.
TRANSIENT = {429, 503}


def retry_delay(value, attempt):
    if value:
        try:
            parsed = float(value)
            return max(0, parsed) if math.isfinite(parsed) else float("inf")
        except ValueError:
            try:
                return max(0, (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds())
            except (ValueError, TypeError, OverflowError):
                pass
    return 0.5 * 2**attempt + random.uniform(0, 0.25)


class OpenRouterClient:
    def __init__(self, key, transport=None):
        self.key, self.transport = key, transport

    async def complete(self, policy, messages, guard):
        if not self.key:
            raise AiError("openrouter_key_missing", 409)
        models = list(dict.fromkeys(m for m in (policy.primary_model, policy.fallback_model) if m))
        if not models:
            raise AiError("admissions_model_required", 409)
        body = {"models": models, "route": "fallback", "messages": messages,
                "temperature": policy.temperature, "max_tokens": policy.max_tokens,
                "response_format": {"type": "json_object"},
                "provider": {"require_parameters": True, "data_collection": "deny"}}
        title = f"{PRODUCT_NAME} Admisiones"
        headers = {
            "Authorization": "Bearer " + self.key,
            "HTTP-Referer": "http://localhost:4173",
            "X-Title": title,
            "X-OpenRouter-Title": title,
        }
        deadline = time.monotonic() + 40
        async with httpx.AsyncClient(transport=self.transport, follow_redirects=False, trust_env=False) as client:
            for attempt in range(3):
                status = None
                guard()
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise AiError("openrouter_deadline", 504)
                delay = None
                try:
                    async with asyncio.timeout(remaining):
                        async with client.stream("POST", "https://openrouter.ai/api/v1/chat/completions", headers=headers, json=body, timeout=min(remaining, 25)) as response:
                            data = bytearray()
                            async for part in response.aiter_bytes():
                                data.extend(part)
                                if len(data) > 200000:
                                    raise AiError("provider_response_too_large", 502)
                            status = response.status_code
                            try:
                                result = json.loads(data)
                            except (ValueError, UnicodeError):
                                result = None
                            if status == 200 and isinstance(result, dict) and isinstance(result.get("error"), dict):
                                embedded = result["error"].get("code")
                                status = embedded if type(embedded) is int else 502
                            if status >= 300:
                                if status == 402:
                                    raise AiError("openrouter_payment_required", 502, upstream_status=status)
                                if status not in TRANSIENT:
                                    raise AiError("openrouter_rejected_request", 502, upstream_status=status)
                                delay = retry_delay(response.headers.get("retry-after"), attempt)
                            else:
                                try:
                                    text = result["choices"][0]["message"]["content"]
                                    if result["choices"][0].get("finish_reason") != "stop" or result["choices"][0]["message"].get("refusal"):
                                        raise ValueError()
                                    model = result["model"]
                                    usage = result.get("usage", {})
                                    if not isinstance(text, str) or not text.strip() or len(text) > 16000 or not isinstance(model, str):
                                        raise ValueError()
                                except (KeyError, TypeError, IndexError, ValueError):
                                    raise AiError("provider_invalid_response", 502) from None
                                guard()
                                return {"content": text, "model": model[:200], "usage": {k: usage[k] for k in ("prompt_tokens", "completion_tokens") if isinstance(usage, dict) and type(usage.get(k)) is int and 0 <= usage[k] <= 10000000}}
                except (httpx.ConnectTimeout, httpx.ConnectError):
                    delay = retry_delay(None, attempt)
                except (httpx.TimeoutException, httpx.NetworkError, TimeoutError, httpx.RemoteProtocolError):
                    # Inference may already have been billed; do not retry uncertain POSTs.
                    raise AiError("openrouter_result_uncertain", 504) from None
                except httpx.HTTPError:
                    raise AiError("openrouter_transport_failure", 502) from None
                if attempt == 2 or delay is None or delay >= deadline - time.monotonic():
                    raise AiError("openrouter_retry_exhausted", 503, True, upstream_status=status)
                await asyncio.sleep(delay)
                guard()
