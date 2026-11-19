"""Bounded voice/search adapters and durable local conversation budgets."""

import asyncio
import base64
import ipaddress
import json
import os
import re
import secrets
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlsplit

import httpx2 as httpx

from app.modules.ai.domain.models import Attachment, AssistantAdmissionsContext
from app.modules.ai.infrastructure.providers import AiError


def safe_url(value):
    if not isinstance(value, str) or len(value) > 2000:
        return ""
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ""
        if (
            host.lower() == "localhost"
            or "." not in host
            or host.endswith((".local", ".localhost"))
        ):
            return ""
        try:
            if not ipaddress.ip_address(host).is_global:
                return ""
        except ValueError:
            pass
        return (
            value
            if parsed.scheme == "https"
            and parsed.hostname
            and not parsed.username
            and not parsed.password
            else ""
        )
    except ValueError:
        return ""


def decode_attachment(attachment: Attachment):
    try:
        data = base64.b64decode(attachment.data, validate=True)
    except ValueError:
        raise AiError("invalid_media") from None
    if not data or len(data) > 4_000_000:
        raise AiError("media_too_large", 413)
    mime = attachment.mime_type
    matches = {
        "image/png": data.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/jpeg": data.startswith(b"\xff\xd8\xff"),
        "image/webp": data.startswith(b"RIFF") and data[8:12] == b"WEBP",
        "audio/wav": data.startswith(b"RIFF") and data[8:12] == b"WAVE",
        "audio/ogg": data.startswith(b"OggS"),
        "audio/flac": data.startswith(b"fLaC"),
        "audio/webm": data.startswith(b"\x1aE\xdf\xa3"),
        "audio/mpeg": data.startswith(b"ID3")
        or len(data) > 2
        and data[0] == 255
        and data[1] & 224 == 224,
    }
    if not matches[mime]:
        raise AiError("invalid_media")
    return data


class ConversationLedger:
    """One-worker local ledger. Reservations survive timeout, reload and restart."""

    def __init__(self, path: Path):
        self.path = path

    def read(self):
        try:
            if not self.path.exists():
                return {}
            if self.path.stat().st_size > 4_000_000:
                raise ValueError()
            data = json.loads(self.path.read_text("utf-8"))
            if not isinstance(data, dict):
                raise ValueError()
            if len(data) > 500:
                raise ValueError()
            for identifier, item in data.items():
                if (
                    not re.fullmatch(r"[a-f0-9]{32}", identifier)
                    or not isinstance(item, dict)
                    or not {"binding", "used", "expires", "turns"} <= set(item)
                    or set(item) - {"binding", "used", "expires", "turns", "admissions"}
                ):
                    raise ValueError()
                AssistantAdmissionsContext.model_validate(item.get("admissions", {}))
                if not isinstance(item["binding"], str) or not re.fullmatch(
                    r"\d{1,12}:\d{1,12}(?::admissions:[a-f0-9]{64})?", item["binding"]
                ):
                    raise ValueError()
                if (
                    type(item["used"]) is not int
                    or not 0 <= item["used"] <= 200
                    or type(item["expires"]) not in (int, float)
                    or not 0 <= item["expires"] <= 10_000_000_000
                ):
                    raise ValueError()
                if (
                    not isinstance(item["turns"], list)
                    or len(item["turns"]) > 200
                    or any(
                        not isinstance(turn, str)
                        or not re.fullmatch(r"[a-f0-9]{32}", turn)
                        for turn in item["turns"]
                    )
                    or len(set(item["turns"])) != len(item["turns"])
                ):
                    raise ValueError()
            return data
        except (OSError, ValueError):
            raise AiError("conversation_storage_unavailable", 503) from None

    def write(self, data):
        temporary = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.path.parent, delete=False
            ) as file:
                temporary = file.name
                json.dump(data, file)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary, self.path)
        except OSError:
            raise AiError("conversation_storage_unavailable", 503) from None
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)

    def create(self, binding):
        data = self.read()
        now = time.time()
        data = {key: item for key, item in data.items() if item["expires"] > now}
        if len(data) >= 500:
            raise AiError("conversation_capacity", 429)
        identifier = secrets.token_hex(16)
        data[identifier] = {
            "binding": binding,
            "used": 0,
            "expires": now + 86400,
            "turns": [],
        }
        self.write(data)
        return identifier

    def state(self, identifier, binding):
        data = self.read()
        item = data.get(identifier)
        if not item or item["expires"] <= time.time():
            raise AiError("conversation_expired", 409)
        if item["binding"] != binding:
            raise AiError("conversation_configuration_changed", 409)
        return data, item

    def start_turn(self, identifier, binding, turn_id):
        data, item = self.state(identifier, binding)
        if turn_id in item["turns"]:
            raise AiError("turn_already_started", 409)
        if len(item["turns"]) >= 200:
            raise AiError("conversation_capacity", 429)
        item["turns"].append(turn_id)
        self.write(data)

    def admissions_context(self, identifier, binding):
        _, item = self.state(identifier, binding)
        return AssistantAdmissionsContext.model_validate(item.get("admissions", {})).model_dump()

    def save_admissions_context(self, identifier, binding, expected, context):
        data, item = self.state(identifier, binding)
        current = AssistantAdmissionsContext.model_validate(item.get("admissions", {})).model_dump()
        if current != expected:
            raise AiError("conversation_context_changed", 409)
        item["admissions"] = AssistantAdmissionsContext.model_validate(context).model_dump()
        self.write(data)

    def reserve_voice(self, identifier, binding, limit):
        data, item = self.state(identifier, binding)
        if limit is not None and item["used"] >= limit:
            return False
        item["used"] += 1
        self.write(data)
        return True


class MediaGateway:
    def __init__(self, keys, root: Path, transport=None):
        self.keys, self.root, self.transport = keys, root, transport

    async def request(
        self, provider, method, path, body=None, params=None, binary=False, metadata=None
    ):
        key = self.keys.get(provider)
        if not key:
            raise AiError("provider_key_missing", 409)
        bases = {
            "elevenlabs": "https://api.elevenlabs.io/",
            "google_tts": "https://texttospeech.googleapis.com/",
            "tavily": "https://api.tavily.com/",
            "brave": "https://api.search.brave.com/",
            "serpapi": "https://serpapi.com/",
        }
        headers = {
            "elevenlabs": {"xi-api-key": key},
            "google_tts": {"x-goog-api-key": key},
            "tavily": {"Authorization": f"Bearer {key}"},
            "brave": {"X-Subscription-Token": key},
            "serpapi": {},
        }[provider]
        if provider == "serpapi":
            params = (params or {}) | {"api_key": key}
        try:
            async with asyncio.timeout(20):
                async with httpx.AsyncClient(
                    timeout=18,
                    follow_redirects=False,
                    trust_env=False,
                    transport=self.transport,
                ) as client:
                    async with client.stream(
                        method,
                        bases[provider] + path,
                        headers=headers,
                        json=body,
                        params=params,
                    ) as response:
                        if response.status_code >= 300:
                            if provider == "elevenlabs":
                                error_data = bytearray()
                                async for chunk in response.aiter_bytes():
                                    if len(error_data) + len(chunk) > 16_384:
                                        break
                                    error_data.extend(chunk)
                                remote_code = None
                                try:
                                    error_document = json.loads(error_data)
                                    detail = (
                                        error_document.get("detail", {})
                                        if isinstance(error_document, dict)
                                        else {}
                                    )
                                    if isinstance(detail, dict):
                                        remote_code = detail.get("code") or detail.get("status")
                                except (ValueError, TypeError):
                                    pass
                                safe_codes = {
                                    "quota_exceeded": "voice_insufficient_credits",
                                    "voice_not_found": "voice_catalog_required",
                                    "max_character_limit_exceeded": "voice_text_too_large",
                                    "subscription_required": "voice_payment_required",
                                    "feature_not_available": "voice_model_access_denied",
                                    "detected_unusual_activity": "voice_account_restricted",
                                    "insufficient_credits": "voice_insufficient_credits",
                                    "payment_required": "voice_payment_required",
                                    "insufficient_permissions": "voice_insufficient_permissions",
                                    "voice_access_denied": "voice_access_denied",
                                    "model_access_denied": "voice_model_access_denied",
                                    "invalid_api_key": "voice_invalid_key",
                                    "invalid_parameters": "voice_invalid_parameters",
                                }
                                code = (
                                    safe_codes.get(remote_code)
                                    if isinstance(remote_code, str)
                                    else None
                                )
                                if code is None:
                                    code = {
                                        402: "voice_payment_required",
                                        403: "voice_forbidden",
                                    }.get(response.status_code)
                                if code:
                                    raise AiError(code, 502)
                            raise AiError(
                                "media_provider_rejected"
                                if response.status_code < 500
                                else "media_provider_unavailable",
                                502,
                            )
                        data = bytearray()
                        async for chunk in response.aiter_bytes():
                            data.extend(chunk)
                            if len(data) > 8_000_000:
                                raise AiError("provider_response_too_large", 502)
                        if binary:
                            if not data or not (
                                data.startswith(b"ID3") or data[0] == 255
                            ):
                                raise AiError("provider_invalid_audio", 502)
                            if metadata is not None:
                                count = response.headers.get("x-character-count", "")
                                request_id = response.headers.get("request-id", "")
                                if count.isdigit() and len(count) <= 10:
                                    metadata["billed_characters"] = int(count)
                                if re.fullmatch(r"[A-Za-z0-9_-]{1,160}", request_id):
                                    metadata["provider_request_id"] = request_id
                            return bytes(data), "audio/mpeg"
                        result = json.loads(data)
                        if not isinstance(result, dict) and not (
                            provider == "elevenlabs"
                            and path == "v1/models"
                            and isinstance(result, list)
                        ):
                            raise ValueError()
                        return result
        except (TimeoutError, httpx.TimeoutException, httpx.NetworkError):
            raise AiError("provider_timeout_or_network", 504) from None
        except (ValueError, httpx.HTTPError):
            raise AiError("provider_invalid_response", 502) from None

    def piper_runtime(self):
        directory = self.root / "piper" / ".venv"
        legacy_os = getattr(sys.modules.get(__name__), "os", os)
        return directory / (
            "Scripts/python.exe" if legacy_os.name == "nt" else "bin/python"
        )

    def piper_voices(self):
        directory = self.root / "piper" / "voices"
        voices = []
        if directory.exists():
            for path in sorted(directory.glob("*.onnx"))[:100]:
                if path.is_symlink() or path.resolve().parent != directory.resolve():
                    continue
                config = path.with_suffix(".onnx.json")
                if (
                    config.is_symlink()
                    or not config.is_file()
                    or not re.fullmatch(r"[A-Za-z0-9._-]{1,200}", path.stem)
                ):
                    continue
                voices.append({"id": path.stem, "name": path.stem, "language": "es"})
        runtime = self.piper_runtime()
        return {
            "voices": voices,
            "models": [],
            "ready": runtime.is_file(),
            "local": True,
        }

    async def catalog(self, provider):
        if provider == "piper":
            return self.piper_voices()
        voices, models = [], []
        if provider == "elevenlabs":
            seen = set()
            for voice_type in ("saved", "default"):
                token = ""
                for page in range(5):
                    data = await self.request(
                        provider,
                        "GET",
                        "v2/voices",
                        params={
                            "page_size": 100,
                            "voice_type": voice_type,
                            **({"next_page_token": token} if token else {}),
                        },
                    )
                    values = data.get("voices")
                    if not isinstance(values, list):
                        raise AiError("provider_invalid_response", 502)
                    for item in values:
                        if (
                            isinstance(item, dict)
                            and re.fullmatch(
                                r"[A-Za-z0-9_-]{1,200}",
                                str(item.get("voice_id", "")),
                            )
                            and item["voice_id"] not in seen
                        ):
                            seen.add(item["voice_id"])
                            name = str(item.get("name", item["voice_id"]))[:200]
                            voices.append(
                                {
                                    "id": item["voice_id"],
                                    "name": name[:180] + " · Predeterminada"
                                    if voice_type == "default"
                                    else name,
                                    "language": str(
                                        (
                                            item.get("labels")
                                            if isinstance(item.get("labels"), dict)
                                            else {}
                                        ).get("language", "")
                                    )[:40],
                                }
                            )
                    if not data.get("has_more"):
                        break
                    token = data.get("next_page_token")
                    if (
                        not isinstance(token, str)
                        or not token
                        or len(token) > 2048
                        or page == 4
                    ):
                        raise AiError("model_catalog_too_large", 502)
            data = await self.request(provider, "GET", "v1/models")
            if not isinstance(data, list) or len(data) > 1000:
                raise AiError("provider_invalid_response", 502)
            # ElevenLabs model responses are top-level lists.
            models = [
                {
                    "id": item["model_id"],
                    "name": str(item.get("name", item["model_id"]))[:200],
                    "languages": [{"id": lang["language_id"], "name": str(lang.get("name", lang["language_id"]))[:80]} for lang in (item.get("languages") or [])[:200] if isinstance(lang, dict) and isinstance(lang.get("language_id"), str) and re.fullmatch(r"[a-z]{2}", lang["language_id"])],
                }
                for item in data
                if isinstance(item, dict)
                and item.get("can_do_text_to_speech")
                and re.fullmatch(
                    r"[A-Za-z0-9._-]{1,200}", str(item.get("model_id", ""))
                )
            ]
        else:
            data = await self.request(provider, "GET", "v1/voices")
            items = data.get("voices")
            if not isinstance(items, list) or len(items) > 2000:
                raise AiError("provider_invalid_response", 502)
            for item in items:
                if not isinstance(item, dict):
                    continue
                languages = item.get("languageCodes", [])
                name = item.get("name", "")
                if (
                    isinstance(name, str)
                    and re.fullmatch(r"[A-Za-z0-9._-]{1,200}", name)
                    and isinstance(languages, list)
                    and languages
                    and isinstance(languages[0], str)
                    and re.fullmatch(r"[A-Za-z0-9-]{1,40}", languages[0])
                ):
                    voices.append({"id": name, "name": name, "language": languages[0]})
        return {"voices": voices, "models": models, "ready": True, "local": False}

    async def synthesize(self, settings, text, catalog):
        provider = settings.voice_provider
        voice = next(
            (item for item in catalog["voices"] if item["id"] == settings.voice_id),
            None,
        )
        if not voice:
            # Manual IDs must also exist in the fetched account catalog.
            raise AiError("voice_catalog_required", 409)
        if len(text.encode("utf-8")) > 5000:
            raise AiError("voice_text_too_large", 409)
        if provider == "elevenlabs":
            if settings.voice_model not in {item["id"] for item in catalog["models"]}:
                raise AiError("voice_model_required", 409)
            return await self.request(
                provider,
                "POST",
                "v1/text-to-speech/"
                + settings.voice_id
                + "?output_format=mp3_44100_128",
                {"text": text, "model_id": settings.voice_model},
                binary=True,
            )
        if provider == "google_tts":
            data = await self.request(
                provider,
                "POST",
                "v1/text:synthesize",
                {
                    "input": {"text": text},
                    "voice": {"languageCode": voice["language"], "name": voice["id"]},
                    "audioConfig": {"audioEncoding": "MP3"},
                },
            )
            try:
                audio = base64.b64decode(data["audioContent"], validate=True)
                if (
                    not audio
                    or len(audio) > 6_000_000
                    or not (audio.startswith(b"ID3") or audio[0] == 255)
                ):
                    raise ValueError()
                return audio, "audio/mpeg"
            except (KeyError, ValueError, TypeError):
                raise AiError("provider_invalid_audio", 502) from None
        if not catalog["ready"]:
            raise AiError("piper_unavailable", 409)
        runtime = self.piper_runtime()
        model = self.root / "piper" / "voices" / (settings.voice_id + ".onnx")
        directory = self.root / "piper" / "voices"
        if model.is_symlink() or model.resolve().parent != directory.resolve():
            raise AiError("voice_catalog_required", 409)
        # Fixed module/paths and stdin; neither prompt nor model IDs become shell code.
        temporary = self.root / "piper" / (secrets.token_hex(16) + ".wav")
        process = await asyncio.create_subprocess_exec(
            str(runtime),
            "-m",
            "piper",
            "-m",
            str(model),
            "-f",
            str(temporary),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            creationflags=0x08000000 if os.name == "nt" else 0,
        )
        try:
            await asyncio.wait_for(process.communicate(text.encode("utf-8")), 25)
            if (
                process.returncode
                or not temporary.is_file()
                or temporary.stat().st_size > 6_000_000
            ):
                raise AiError("piper_synthesis_failed", 502)
            audio = temporary.read_bytes()
            if not audio.startswith(b"RIFF") or audio[8:12] != b"WAVE":
                raise AiError("provider_invalid_audio", 502)
            return audio, "audio/wav"
        except TimeoutError:
            process.kill()
            await process.wait()
            raise AiError("piper_synthesis_failed", 504) from None
        finally:
            if process.returncode is None:
                process.kill()
                await asyncio.shield(process.wait())
            temporary.unlink(missing_ok=True)

    async def search(self, provider, query, kind):
        if not query.strip() or len(query) > 400 or len(query.split()) > 50:
            raise AiError("search_query_invalid")
        if provider == "tavily":
            data = await self.request(
                provider,
                "POST",
                "search",
                {
                    "query": query,
                    "search_depth": "basic",
                    "max_results": 5,
                    "include_images": kind == "images",
                    "include_image_descriptions": kind == "images",
                    "include_answer": False,
                    "include_raw_content": False,
                    "auto_parameters": False,
                    "safe_search": True,
                },
            )
            values = data.get("images" if kind == "images" else "results", [])
        elif provider == "brave":
            data = await self.request(
                provider,
                "GET",
                "res/v1/" + ("images" if kind == "images" else "web") + "/search",
                params={
                    "q": query,
                    "count": 5,
                    "safesearch": "strict",
                    "search_lang": "es",
                    "country": "ALL",
                },
            )
            values = (
                data.get("results", [])
                if kind == "images"
                else (data.get("web") if isinstance(data.get("web"), dict) else {}).get(
                    "results", []
                )
            )
        else:
            data = await self.request(
                provider,
                "GET",
                "search.json",
                params={
                    "engine": "google_images" if kind == "images" else "google",
                    "q": query,
                    "hl": "es",
                    "safe": "active",
                    "async": "false",
                },
            )
            if (
                data.get("error")
                or not isinstance(data.get("search_metadata"), dict)
                or data["search_metadata"].get("status") != "Success"
            ):
                raise AiError("search_failed", 502)
            values = data.get(
                "images_results" if kind == "images" else "organic_results", []
            )
        if not isinstance(values, list):
            raise AiError("provider_invalid_response", 502)
        results = []
        for item in values[:5]:
            if isinstance(item, str):
                item = {"url": item}
            if not isinstance(item, dict):
                continue
            url = safe_url(item.get("link") or item.get("url"))
            properties = (
                item.get("properties")
                if isinstance(item.get("properties"), dict)
                else {}
            )
            image = safe_url(
                item.get("original")
                or properties.get("url")
                or (
                    item.get("url") if provider == "tavily" and kind == "images" else ""
                )
            )
            if url or image:
                results.append(
                    {
                        "title": str(
                            item.get("title")
                            or item.get("description")
                            or "Fuente externa"
                        )[:200],
                        "url": url or image,
                        "image_url": image,
                        "content": str(
                            item.get("content")
                            or item.get("snippet")
                            or item.get("description")
                            or ""
                        )[:1200],
                    }
                )
        return results
