"""Fixed HTTPS provider adapters. No tools, redirects, cookies or environment proxy."""

import asyncio
import json
import logging
import math
import os
import random
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlencode, urlsplit

import httpx2 as httpx

from app.modules.ai.domain.models import AiSettings, ModelInfo


class AiError(Exception):
    def __init__(
        self,
        code: str,
        status: int = 400,
        transient: bool = False,
        upstream_status: int | None = None,
    ):
        self.code, self.status, self.transient = code, status, transient
        self.upstream_status = (
            upstream_status
            if type(upstream_status) is int and 100 <= upstream_status <= 599
            else None
        )


class ProviderGateway:
    def __init__(self, keys: dict[str, str], transport=None):
        self.keys = keys
        self.transport = transport
        self.last_usage = None
        self.last_response_metadata = {}
        self.last_assistant = None
        self.no_temperature = set()
        self.catalog_details = {}
        endpoint = os.environ.get("HERMES_BASE_URL", "").strip()
        try:
            parsed = urlsplit(endpoint)
            self.hermes_base = (
                endpoint.rstrip("/") + "/"
                if parsed.scheme == "https"
                and parsed.hostname
                and not parsed.username
                and not parsed.password
                and not parsed.query
                and not parsed.fragment
                and not re.search(r"[\s\\]", endpoint)
                else ""
            )
        except ValueError:
            self.hermes_base = ""

    async def request(self, provider: str, method: str, path: str, body=None):
        if provider == "hermes" and not self.hermes_base:
            raise AiError("provider_endpoint_missing", 409)
        key = self.keys.get(provider)
        if not key:
            raise AiError("provider_key_missing", 409)
        bases = {
            "gemini": "https://generativelanguage.googleapis.com/v1beta/",
            "xai": "https://api.x.ai/v1/",
            "openrouter": "https://openrouter.ai/api/v1/",
            "groq": "https://api.groq.com/openai/v1/",
            "mistral": "https://api.mistral.ai/v1/",
            "nvidia": "https://integrate.api.nvidia.com/v1/",
            "openai": "https://api.openai.com/v1/",
            "anthropic": "https://api.anthropic.com/v1/",
            "kimi": "https://api.moonshot.ai/v1/",
            "hermes": self.hermes_base,
        }
        headers = (
            {"x-goog-api-key": key}
            if provider == "gemini"
            else {"Authorization": f"Bearer {key}"}
        )
        if provider == "anthropic":
            headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
        gemini_generation = (
            provider == "gemini"
            and method == "POST"
            and path.startswith("models/")
            and path.endswith(":generateContent")
        )
        diagnostic = {"upstream_status": None, "response_bytes": 0, "content_type": "unknown"}
        retry_after = None

        def failure(code, status=502, transient=False, kind="http", error_class=None):
            error = AiError(code, status, transient, diagnostic["upstream_status"])
            error.diagnostics = {"kind": kind, **diagnostic}
            error.retry_after = retry_after
            if error_class:
                error.diagnostics["error_class"] = error_class
            logging.getLogger(__name__).warning(
                "AI_PROVIDER_FAILURE provider=%s kind=%s upstream_status=%s response_bytes=%s content_type=%s error_class=%s",
                provider if provider in bases else "unknown", kind,
                diagnostic["upstream_status"] or 0, diagnostic["response_bytes"], diagnostic["content_type"], error_class or "none",
            )
            return error
        try:
            async with asyncio.timeout(35 if gemini_generation else 12):
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(10, read=30) if gemini_generation else 10,
                    follow_redirects=False,
                    trust_env=False,
                    transport=self.transport,
                ) as client:
                    async with client.stream(
                        method, bases[provider] + path, headers=headers, json=body
                    ) as response:
                        diagnostic["upstream_status"] = response.status_code
                        retry_after = self.retry_after_seconds(response.headers.get("retry-after"))
                        content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                        diagnostic["content_type"] = content_type if re.fullmatch(r"[a-z0-9.+-]{1,40}/[a-z0-9.+-]{1,60}", content_type) else "other"
                        if response.status_code >= 300:
                            transient = response.status_code in (
                                408,
                                429,
                                500,
                                502,
                                503,
                                504,
                            )
                            code = (
                                "provider_rate_limited"
                                if response.status_code == 429
                                else "provider_temporary_failure"
                                if transient
                                else "provider_rejected_request"
                            )
                            if provider == "gemini" and response.status_code == 404:
                                code = "provider_model_unavailable"
                            raise failure(code, transient=transient)
                        data = bytearray()
                        async for chunk in response.aiter_bytes():
                            data.extend(chunk)
                            diagnostic["response_bytes"] = len(data)
                            if len(data) > 2_000_000:
                                raise AiError("provider_response_too_large", 502)
                        try:
                            return json.loads(data)
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            raise failure("provider_invalid_json", kind="invalid_json") from None
        except (httpx.ConnectTimeout, httpx.ConnectError):
            raise failure("provider_connection_failed", 504, True, "connect") from None
        except httpx.ReadTimeout:
            raise failure("provider_response_timeout", 504, True, "read_timeout") from None
        except (TimeoutError, httpx.TimeoutException, httpx.NetworkError):
            raise failure("provider_timeout_or_network", 504, True, "timeout_or_network") from None
        except httpx.HTTPError as error:
            kind = type(error).__name__
            safe_class = kind if kind in {"RemoteProtocolError", "LocalProtocolError", "DecodingError", "ProxyError", "UnsupportedProtocol"} else "HTTPError"
            raise failure("provider_protocol_failure", kind="protocol", error_class=safe_class) from None
        except ValueError:
            raise failure("provider_invalid_response", kind="invalid_response") from None

    @staticmethod
    def retry_after_seconds(value):
        if not value:
            return None
        try:
            seconds = float(value)
            return max(0, seconds) if math.isfinite(seconds) else math.inf
        except ValueError:
            try:
                parsed = parsedate_to_datetime(value)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return max(0, (parsed - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                return None

    async def gemini_generation(self, model, body, before_attempt=None):
        """Retry only explicit server rejections, under the original total budget."""
        deadline = asyncio.get_running_loop().time() + 35
        for attempt in range(3):
            if before_attempt:
                before_attempt()
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                raise AiError("provider_retry_budget_exhausted", 503)
            try:
                async with asyncio.timeout(remaining):
                    return await self.request("gemini", "POST", f"models/{model}:generateContent", body)
            except AiError as error:
                # A timeout, truncated/non-JSON body or protocol error may follow
                # accepted/billed work. Never repeat those uncertain POSTs.
                if error.upstream_status not in (429, 503) or not error.transient or attempt == 2:
                    raise
                delay = getattr(error, "retry_after", None)
                if delay is None:
                    delay = 0.5 * 2**attempt + random.uniform(0, 0.25)
                if delay >= deadline - asyncio.get_running_loop().time():
                    raise
                logging.getLogger(__name__).warning(
                    "AI_PROVIDER_RETRY provider=gemini attempt=%s upstream_status=%s delay_ms=%s",
                    attempt + 2, error.upstream_status, round(delay * 1000),
                )
                await asyncio.sleep(delay)
            except TimeoutError:
                raise AiError("provider_response_timeout", 504) from None

    async def models(self, provider: str, kind="text", *, account_catalog=False) -> list[ModelInfo]:
        self.catalog_details[provider] = {}
        items = []
        token = ""
        account_openrouter = provider == "openrouter" and account_catalog
        pages = 10 if account_openrouter else 3
        for page in range(pages):
            path = "models"
            if provider == "gemini":
                path += "?" + urlencode(
                    {"pageSize": 1000, **({"pageToken": token} if token else {})}
                )
            elif provider == "anthropic":
                path += "?" + urlencode(
                    {"limit": 1000, **({"after_id": token} if token else {})}
                )
            elif account_openrouter:
                path = "models/user?" + urlencode({"limit": 100, "offset": len(items)})
            data = await self.request(provider, "GET", path)
            if not isinstance(data, dict):
                raise AiError("provider_invalid_response", 502)
            page_items = data.get("models" if provider == "gemini" else "data")
            if not isinstance(page_items, list):
                raise AiError("provider_invalid_response", 502)
            items.extend(page_items)
            token = data.get("nextPageToken", "") if provider == "gemini" else ""
            if provider == "anthropic" and data.get("has_more"):
                token = data.get("last_id", "")
                if not token:
                    raise AiError("provider_invalid_response", 502)
            if account_openrouter:
                token = "more" if len(page_items) == 100 else ""
            if not isinstance(token, str):
                raise AiError("provider_invalid_response", 502)
            if len(items) > 3000 or len(token) > 2048 or (page == pages - 1 and token):
                raise AiError("model_catalog_too_large", 502)
            if not token:
                break
        result = []
        for item in items:
            if not isinstance(item, dict):
                continue
            model_id = (
                item.get("name", "") if provider == "gemini" else item.get("id", "")
            )
            if not isinstance(model_id, str) or not re.fullmatch(
                r"[A-Za-z0-9._:/-]{1,200}", model_id
            ):
                continue
            if provider == "gemini":
                model_id = model_id.removeprefix("models/")
            if ".." in model_id or not model_id:
                continue
            methods = item.get("supportedGenerationMethods")
            if provider == "gemini" and (
                not isinstance(methods, list) or "generateContent" not in methods
            ):
                continue
            if account_catalog and provider == "gemini":
                if any(part in model_id for part in ("-tts", "-image", "-native-audio", "-live")):
                    continue
                if kind in {"audio", "vision"} and not model_id.startswith("gemini-"):
                    continue
            if provider == "openrouter":
                # The CRM sends synchronous chat completions, never batch jobs.
                # Respect explicit endpoint capabilities without excluding older
                # catalogs that did not publish this field.
                endpoints = item.get("endpoints")
                if model_id.endswith(":batch") or endpoints is not None and (
                    not isinstance(endpoints, list)
                    or not any(path in endpoints for path in ("/api/v1/chat/completions", "/v1/chat/completions"))
                ):
                    continue
                architecture = item.get("architecture", {})
                if (
                    not isinstance(architecture, dict)
                    or not isinstance(architecture.get("output_modalities"), list)
                    or "text" not in architecture["output_modalities"]
                ):
                    continue
                params = item.get("supported_parameters", [])
                if not isinstance(params, list) or "max_tokens" not in params:
                    continue
                if account_catalog and kind == "vision" and "image" not in (
                    architecture.get("input_modalities") or []
                ):
                    continue
                top = item.get("top_provider")
                limit = (
                    top.get("max_completion_tokens") if isinstance(top, dict) else None
                )
                temperature = "temperature" in params
                from decimal import Decimal, InvalidOperation
                prices = {}
                for field, source in (("input_usd_per_million", "prompt"), ("output_usd_per_million", "completion")):
                    try:
                        raw = Decimal(str((item.get("pricing") or {}).get(source))) * 1000000
                        prices[field] = float(raw) if raw.is_finite() and 0 <= raw <= 100000 else None
                    except (InvalidOperation, TypeError, ValueError, AttributeError):
                        prices[field] = None
                try:
                    request_price = float((item.get("pricing") or {}).get("request", "0"))
                    if not math.isfinite(request_price) or request_price < 0:
                        request_price = math.inf
                except (ValueError, TypeError, AttributeError):
                    request_price = math.inf
                self.catalog_details[provider][model_id] = {**prices, "request_usd": request_price, "supported_parameters": params,
                    "context_length": item.get("context_length") if type(item.get("context_length")) is int else None}
            else:
                if provider == "gemini":
                    self.catalog_details[provider][model_id] = {
                        "context_length": item.get("inputTokenLimit") if type(item.get("inputTokenLimit")) is int else None,
                    }
                if provider == "openai" and any(
                    k in model_id.lower()
                    for k in (
                        "embedding",
                        "whisper",
                        "tts",
                        "audio",
                        "realtime",
                        "moderation",
                        "dall-e",
                        "gpt-image",
                        "sora",
                        "transcrib",
                    )
                ):
                    continue
                if provider == "groq":
                    if item.get("active") is False:
                        continue
                    if kind == "audio":
                        if model_id not in (
                            "whisper-large-v3",
                            "whisper-large-v3-turbo",
                        ):
                            continue
                    elif any(
                        k in model_id.lower()
                        for k in (
                            "whisper",
                            "tts",
                            "playai",
                            "orpheus",
                            "guard",
                            "embedding",
                            "prompt-guard",
                            "compound",
                        )
                    ):
                        continue
                if provider == "mistral":
                    capabilities = item.get("capabilities", {})
                    if (
                        not isinstance(capabilities, dict)
                        or capabilities.get("completion_chat") is not True
                        or item.get("deprecation")
                    ):
                        continue
                limit = item.get("outputTokenLimit") if provider == "gemini" else None
                temperature = provider not in ("openai", "anthropic", "kimi")
            result.append(
                ModelInfo(
                    id=model_id,
                    name=str(item.get("displayName") or item.get("name") or model_id)[
                        :200
                    ],
                    output_limit=limit
                    if isinstance(limit, int) and limit > 0
                    else None,
                    temperature=temperature,
                    max_temperature=float(item["maxTemperature"])
                    if provider == "gemini"
                    and type(item.get("maxTemperature")) in (int, float)
                    and math.isfinite(item["maxTemperature"])
                    else None,
                )
            )
        self.no_temperature = {
            item for item in self.no_temperature if item[0] != provider
        } | {(provider, item.id) for item in result if not item.temperature}
        return sorted(
            {item.id: item for item in result}.values(), key=lambda item: item.id
        )

    async def generate(
        self,
        provider: str,
        model: str,
        settings: AiSettings,
        system: str,
        messages: list[dict],
        before_attempt=None,
        response_schema=None,
    ) -> str:
        limit = min(settings.max_tokens, settings.output_tokens)
        self.last_usage = None
        self.last_response_metadata = {}
        self.last_assistant = None
        if provider == "gemini":
            body = {
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [
                    {
                        "role": "model" if item["role"] == "assistant" else "user",
                        "parts": [{"text": item["content"]}],
                    }
                    for item in messages
                ],
                "generationConfig": {
                    "maxOutputTokens": limit,
                    "temperature": settings.temperature,
                },
            }
            if response_schema is not None:
                body["generationConfig"].update({"responseMimeType": "application/json", "responseSchema": response_schema})
            elif "VOICE_DECISION_JSON" in system:
                body["generationConfig"].update(
                    {
                        "responseMimeType": "application/json",
                        "responseSchema": {
                            "type": "OBJECT",
                            "properties": {
                                "text": {"type": "STRING"},
                                "use_voice": {"type": "BOOLEAN"},
                            },
                            "required": ["text", "use_voice"],
                        },
                    }
                )
            data = await self.gemini_generation(model, body, before_attempt)
            try:
                finish_reason = data["candidates"][0].get("finishReason")
                if finish_reason in {"STOP", "MAX_TOKENS", "SAFETY", "RECITATION", "OTHER", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII", "MALFORMED_FUNCTION_CALL", "UNEXPECTED_TOOL_CALL"}:
                    self.last_response_metadata["finish_reason"] = finish_reason
                thought_tokens = data.get("usageMetadata", {}).get("thoughtsTokenCount")
                if type(thought_tokens) is int and thought_tokens >= 0:
                    self.last_response_metadata["thought_tokens"] = thought_tokens
                text = "\n".join(
                    part["text"]
                    for part in data["candidates"][0]["content"]["parts"]
                    if isinstance(part, dict)
                    and "text" in part
                    and not part.get("thought", False)
                )
            except (KeyError, IndexError, TypeError, AttributeError):
                raise AiError("provider_empty_or_blocked_response", 502) from None
        elif provider == "xai":
            body = {
                "model": model,
                "input": [{"role": "system", "content": system}, *messages],
                "max_output_tokens": limit,
                "temperature": settings.temperature,
                "store": False,
            }
            data = await self.request(provider, "POST", "responses", body)
            try:
                text = "\n".join(
                    part["text"]
                    for item in data["output"]
                    if item.get("type") == "message"
                    for part in item["content"]
                    if part.get("type") == "output_text"
                )
            except (KeyError, TypeError, AttributeError):
                raise AiError("provider_invalid_response", 502) from None
        elif provider == "anthropic":
            data = await self.request(
                provider,
                "POST",
                "messages",
                {
                    "model": model,
                    "system": system,
                    "max_tokens": limit,
                    "messages": messages,
                },
            )
            try:
                text = "\n".join(
                    part["text"]
                    for part in data["content"]
                    if isinstance(part, dict) and part.get("type") == "text"
                )
            except (KeyError, TypeError):
                raise AiError("provider_invalid_response", 502) from None
        else:
            body = {
                "model": model,
                "messages": [{"role": "system", "content": system}, *messages],
                "max_tokens": limit,
                "temperature": settings.temperature,
            }
            if provider == "openrouter":
                body["provider"] = {
                    "allow_fallbacks": False,
                    "require_parameters": True,
                }
            elif provider in ("openai", "kimi"):
                body.pop("max_tokens")
                body.pop("temperature")
                body["max_completion_tokens"] = limit
                if provider == "kimi" and "k2.6" in model.lower():
                    body["thinking"] = {"type": "disabled"}
            elif provider in ("nvidia", "hermes"):
                body.pop("temperature")
            elif provider == "groq":
                body["temperature"] = max(settings.temperature, 1e-8)
                body["n"] = 1
            if (provider, model) in self.no_temperature:
                body.pop("temperature", None)
            data = await self.request(provider, "POST", "chat/completions", body)
            try:
                text = data["choices"][0]["message"]["content"]
                if provider == "kimi":
                    assistant = data["choices"][0]["message"]
                    reasoning = assistant.get("reasoning_content")
                    if reasoning is not None and (
                        not isinstance(reasoning, str) or len(reasoning) > 200_000
                    ):
                        raise AiError("provider_response_too_large", 502)
                    self.last_assistant = {
                        "role": "assistant",
                        "content": text,
                        **({"reasoning_content": reasoning} if reasoning else {}),
                    }
                if provider == "mistral" and isinstance(text, list):
                    text = "\n".join(
                        part["text"]
                        for part in text
                        if isinstance(part, dict)
                        and part.get("type") == "text"
                        and isinstance(part.get("text"), str)
                    )
            except (KeyError, IndexError, TypeError):
                raise AiError("provider_invalid_response", 502) from None
        if not isinstance(text, str) or not text.strip():
            raise AiError("provider_empty_or_blocked_response", 502)
        if len(text) > 32000:
            raise AiError("provider_output_too_large", 502)
        usage = (
            data.get("usageMetadata" if provider == "gemini" else "usage", {})
            if isinstance(data, dict)
            else {}
        )
        if isinstance(usage, dict):
            incoming = usage.get(
                "promptTokenCount"
                if provider == "gemini"
                else "input_tokens"
                if provider in ("anthropic", "xai")
                else "prompt_tokens"
            )
            outgoing = usage.get(
                "candidatesTokenCount"
                if provider == "gemini"
                else "output_tokens"
                if provider in ("anthropic", "xai")
                else "completion_tokens"
            )
            if (
                type(incoming) is int
                and type(outgoing) is int
                and incoming >= 0
                and outgoing >= 0
            ):
                self.last_usage = {"input": incoming, "output": outgoing}
        return text.strip()

    async def transcribe(self, model, mime, data):
        if model not in ("whisper-large-v3", "whisper-large-v3-turbo"):
            raise AiError("audio_model_unsupported", 409)
        key = self.keys.get("groq")
        if not key:
            raise AiError("provider_key_missing", 409)
        extensions = {
            "audio/wav": "wav",
            "audio/mpeg": "mp3",
            "audio/ogg": "ogg",
            "audio/flac": "flac",
            "audio/webm": "webm",
        }
        if mime not in extensions:
            raise AiError("invalid_media")
        try:
            async with asyncio.timeout(35):
                async with httpx.AsyncClient(
                    timeout=30,
                    follow_redirects=False,
                    trust_env=False,
                    transport=self.transport,
                ) as client:
                    async with client.stream(
                        "POST",
                        "https://api.groq.com/openai/v1/audio/transcriptions",
                        headers={"Authorization": "Bearer " + key},
                        data={"model": model, "response_format": "json"},
                        files={"file": ("audio." + extensions[mime], data, mime)},
                    ) as response:
                        if response.status_code >= 300:
                            raise AiError("provider_rejected_request", 502)
                        body = bytearray()
                        async for chunk in response.aiter_bytes():
                            body.extend(chunk)
                            if len(body) > 64000:
                                raise AiError("provider_response_too_large", 502)
                        result = json.loads(body)
                        text = result.get("text") if isinstance(result, dict) else None
                        if (
                            not isinstance(text, str)
                            or not text.strip()
                            or len(text) > 16000
                        ):
                            raise AiError("provider_empty_or_blocked_response", 502)
                        return text.strip()[:4000]
        except (TimeoutError, httpx.TimeoutException, httpx.NetworkError):
            raise AiError("provider_timeout_or_network", 504) from None
        except (ValueError, httpx.HTTPError):
            raise AiError("provider_invalid_response", 502) from None
