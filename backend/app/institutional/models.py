"""Typed configuration and access inputs. No client supplied authority fields."""

import re
import unicodedata
from typing import Annotated, Literal
from urllib.parse import urlsplit
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)

from app.institutional.policy import ACTIONS, MODULES
from app.institutional.voice_policy import VoicePolicy
from app.modules.ai.domain.models import (
    AiSettings,
    CredentialProvider,
    MediaSettings,
    Provider,
)


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    @field_validator("full_name", "name", "display_name", check_fields=False)
    @classmethod
    def visible_name(cls, value):
        if not value.strip() or any(ord(c) < 32 for c in value):
            raise ValueError("invalid_name")
        return value.strip()


def login_key(value):
    value = unicodedata.normalize("NFC", value).strip()
    if (
        not re.fullmatch(
            r"[^\s@\x00-\x1f]{1,120}@[^\s@\x00-\x1f]{1,120}\.[^\s@\x00-\x1f]{2,30}",
            value,
        )
        or len(value) > 254
    ):
        raise ValueError("invalid_email")
    return value.casefold()


def public_url(value):
    if not value:
        return value
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.fragment
        or any(ord(c) < 32 for c in value)
    ):
        raise ValueError("invalid_https_url")
    return value


def valid_timezone(value):
    try:
        ZoneInfo(value)
    except (ValueError, ZoneInfoNotFoundError):
        raise ValueError("invalid_timezone") from None
    return value


class Profile(Strict):
    full_name: str = Field(min_length=1, max_length=180)
    phone: str = Field(default="", max_length=60)
    role_label: str = Field(default="", max_length=120)
    avatar_url: str = Field(default="", max_length=2048)
    timezone: str = "America/Bogota"
    _url = field_validator("avatar_url")(public_url)
    _timezone = field_validator("timezone")(valid_timezone)


class ProfileEdit(Strict):
    operation_id: str
    revision: int = Field(ge=1)
    email: str = Field(max_length=254)
    profile: Profile
    current_password: SecretStr | None = Field(default=None, max_length=128)
    _email = field_validator("email")(login_key)


class PublicContact(Strict):
    label: str = Field(min_length=1, max_length=80)
    number: str = Field(min_length=8, max_length=24)
    use: Literal["whatsapp", "calls", "both"]
    active: bool = True
    note: str = Field(default="", max_length=200)

    @field_validator("number")
    @classmethod
    def telephone(cls, value):
        import re
        if not re.fullmatch(r"\+?[0-9 ()-]+", value):
            raise ValueError("invalid_public_contact_number")
        digits = re.sub(r"\D", "", value)
        if len(digits) == 10:
            digits = "57" + digits
        if not 8 <= len(digits) <= 15:
            raise ValueError("invalid_public_contact_number")
        return "+" + digits


class Institution(Strict):
    name: str = Field(min_length=1, max_length=160)
    timezone: str = "America/Bogota"
    locale: Literal["es-CO", "es", "en-US"] = "es-CO"
    public_contacts: list[PublicContact] = Field(default_factory=list, max_length=12)
    _timezone = field_validator("timezone")(valid_timezone)


class MediaChoice(Strict):
    model: str = Field(default="", max_length=240, pattern=r"^[A-Za-z0-9._:/-]*$")
    voice_id: str = Field(default="", max_length=200, pattern=r"^[A-Za-z0-9._-]*$")


class InstitutionMedia(MediaSettings):
    voice_model: str = Field(default="", max_length=240, pattern=r"^[A-Za-z0-9._:/-]*$")
    audio_model: str = Field(default="", max_length=240, pattern=r"^[A-Za-z0-9._:/-]*$")
    vision_model: str = Field(
        default="", max_length=240, pattern=r"^[A-Za-z0-9._:/-]*$"
    )


class AI(AiSettings):
    voice: VoicePolicy = Field(default_factory=VoicePolicy)
    media: InstitutionMedia = Field(default_factory=InstitutionMedia)
    voice_models: dict[Literal["elevenlabs", "google_tts", "piper"], MediaChoice] = (
        Field(default_factory=dict, max_length=3)
    )
    model: str = Field(default="", max_length=240, pattern=r"^[A-Za-z0-9._:/-]*$")
    fallback_model: str = Field(
        default="", max_length=240, pattern=r"^[A-Za-z0-9._:/-]*$"
    )
    backup_model: str = Field(
        default="", max_length=240, pattern=r"^[A-Za-z0-9._:/-]*$"
    )
    backup_fallback_model: str = Field(
        default="", max_length=240, pattern=r"^[A-Za-z0-9._:/-]*$"
    )
    max_tokens: int = Field(default=700, ge=200, le=8000)
    output_tokens: int = Field(default=700, ge=0, le=8000)
    wait_seconds: int = Field(default=60, ge=0, le=3600)
    typing_ms: int = Field(default=2600, ge=0, le=240000)
    fragment_delay_ms: int = Field(default=9000, ge=0, le=240000)
    chars_per_message: int = Field(default=180, ge=0, le=2000)
    recent_messages: int = Field(default=16, ge=4, le=24)
    history_chars: int = Field(default=1200, ge=200, le=4000)
    system_prompt: str = Field(
        default="Responde en español claro y profesional.", max_length=20000
    )
    comment_prompt: str = Field(default="", max_length=1600)
    comment_mode: Literal["manual", "auto"] = "auto"
    comment_auto_reply: str = Field(default="", max_length=400)
    comment_private_accounts: list[str] = Field(default_factory=list, max_length=50)
    voice_name: str = Field(default="", max_length=160)
    vision_analysis_provider: Literal[
        "gemini", "openai", "anthropic", "hermes", "openrouter", "kimi"
    ] = "gemini"
    model_failover_enabled: bool = True
    human_reply_style_enabled: bool = True
    model_fallback_mode: Literal["configured_slots"] = "configured_slots"
    model_fallback_attempt_limit: int = Field(default=2, ge=1, le=2)
    model_fallbacks_json: dict[
        Provider,
        list[Annotated[str, Field(max_length=240, pattern=r"^[A-Za-z0-9._:/-]+$")]],
    ] = Field(default_factory=dict, max_length=10)
    reply_min_chunk_delay_ms: int = Field(default=9000, ge=0, le=240000)
    quote_first_reply: bool = False

    @model_validator(mode="after")
    def coherent_models(self):
        values = [
            *self.provider_models.values(),
            self.model,
            self.fallback_model,
            self.backup_model,
            self.backup_fallback_model,
            *(
                value
                for entries in self.model_fallbacks_json.values()
                for value in entries
            ),
        ]
        if any(
            not re.fullmatch(r"[A-Za-z0-9._:/-]{0,240}", value) or ".." in value
            for value in values
        ):
            raise ValueError("invalid_model_id")
        if self.enabled and not self.model:
            raise ValueError("primary_model_required")
        if self.backup_provider == self.provider:
            raise ValueError("backup_provider_must_differ")
        if not self.backup_provider and (
            self.backup_model or self.backup_fallback_model
        ):
            raise ValueError("backup_provider_required")
        if (
            self.fallback_model
            and self.fallback_model == self.model
            or self.backup_fallback_model
            and self.backup_fallback_model == self.backup_model
        ):
            raise ValueError("duplicate_fallback_model")
        return self


class ModelSelection(Strict):
    provider: CredentialProvider | Literal["piper"]
    category: Literal["text", "audio", "vision", "voice", "search"]
    selected_model: str = Field(
        default="", max_length=240, pattern=r"^[A-Za-z0-9._:/-]*$"
    )
    display_name: str = Field(min_length=1, max_length=120)
    voice_id: str = Field(default="", max_length=200, pattern=r"^[A-Za-z0-9._-]*$")

    @model_validator(mode="after")
    def bounded_identifier(self):
        if ".." in self.selected_model:
            raise ValueError("invalid_model_id")
        return self


class Models(Strict):
    selections: list[ModelSelection] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def unique(self):
        keys = [(s.provider, s.category) for s in self.selections]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate_provider_category")
        for provider, category in keys:
            if category not in PROVIDER_CATEGORIES[provider]:
                raise ValueError("unsupported_provider_category")
        return self


PROVIDER_CATEGORIES = {
    "gemini": ("text", "audio", "vision"),
    "openai": ("text", "vision"),
    "anthropic": ("text", "vision"),
    "hermes": ("text", "vision"),
    "openrouter": ("text", "vision"),
    "kimi": ("text", "vision"),
    "groq": ("text", "audio"),
    "nvidia": ("text",),
    "mistral": ("text",),
    "xai": ("text",),
    "elevenlabs": ("voice",),
    "google_tts": ("voice",),
    "piper": ("voice",),
    "tavily": ("search",),
    "brave": ("search",),
    "serpapi": ("search",),
}


class Availability(Strict):
    enabled: dict[str, bool]

    @field_validator("enabled")
    @classmethod
    def known_modules(cls, value):
        if set(value) != set(MODULES) or not value["settings"]:
            raise ValueError("invalid_module_availability")
        return value


class Budgets(Strict):
    daily_tokens: int = Field(default=0, ge=0, le=1_000_000_000)
    daily_messages: int = Field(default=0, ge=0, le=1_000_000)
    daily_usd_micros: int = Field(default=0, ge=0, le=10_000_000_000)
    requests_per_minute: int = Field(default=120, ge=10, le=10000)
    max_active_integrations: int = Field(default=20, ge=1, le=1000)


class Webhook(Strict):
    key: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    provider: Literal["meta", "whatsapp", "facebook", "instagram", "tiktok"]
    callback_url: str = Field(default="", max_length=2048)
    signature_required: bool = True
    requested_active: bool = False
    integration_ids: list[str] = Field(default_factory=list, max_length=50)
    _url = field_validator("callback_url")(public_url)

    @field_validator("integration_ids")
    @classmethod
    def ids(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("duplicate_integration")
        for item in value:
            UUID(item)
        return value

    @model_validator(mode="after")
    def signed(self):
        if self.requested_active and (
            not self.signature_required or not self.callback_url
        ):
            raise ValueError("signed_callback_required")
        return self


class Webhooks(Strict):
    endpoints: list[Webhook] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def unique(self):
        keys = [e.key for e in self.endpoints]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate_endpoint")
        return self


SECTIONS = {
    "institution": Institution,
    "ai": AI,
    "models": Models,
    "modules": Availability,
    "budgets": Budgets,
    "webhooks": Webhooks,
}


class Login(Strict):
    email: str = Field(max_length=254)
    password: SecretStr = Field(min_length=1, max_length=128)
    _email = field_validator("email")(login_key)


class MFA(Strict):
    challenge_token: SecretStr = Field(min_length=40, max_length=100)
    code: SecretStr = Field(min_length=6, max_length=40)


class Reauthenticate(Strict):
    current_password: SecretStr = Field(min_length=1, max_length=128)
    code: SecretStr | None = Field(default=None, max_length=40)


class Bootstrap(Login):
    bootstrap_token: SecretStr = Field(min_length=40, max_length=100)
    full_name: str = Field(min_length=1, max_length=180)


class UserCreate(Strict):
    operation_id: str
    email: str = Field(max_length=254)
    full_name: str = Field(min_length=1, max_length=180)
    password: SecretStr | None = Field(default=None, min_length=15, max_length=128)
    role: str = Field(max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    _email = field_validator("email")(login_key)


class UserEdit(Strict):
    operation_id: str
    revision: int = Field(ge=1)
    role: str = Field(max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    active: bool
    full_name: str = Field(min_length=1, max_length=180)


class RoleEdit(Strict):
    operation_id: str
    revision: int = Field(ge=0)
    name: str = Field(min_length=1, max_length=100)
    active: bool = True
    actions: list[str] = Field(max_length=len(ACTIONS))

    @field_validator("actions")
    @classmethod
    def known(cls, value):
        if len(value) != len(set(value)) or not set(value) <= set(ACTIONS):
            raise ValueError("invalid_actions")
        return sorted(value)

    @model_validator(mode="after")
    def readable_writes(self):
        required = {
            "crm.write": {"crm.read"},
            "inbox.read": {"crm.read"},
            "inbox.write": {"inbox.read", "crm.read"},
        }
        for action in self.actions:
            if not required.get(action, set()) <= set(self.actions):
                raise ValueError("read_permission_required")
        return self


class SettingEdit(Strict):
    operation_id: str
    revision: int = Field(ge=1)
    document: dict


class SecretEdit(Strict):
    operation_id: str
    scope: Literal["provider", "channel", "webhook"]
    owner: str = Field(min_length=1, max_length=200)
    kind: Literal[
        "api_key",
        "management_key",
        "access_token",
        "app_secret",
        "page_access_token",
        "client_secret",
        "verify_token",
        "webhook_secret",
    ]
    value: SecretStr | None = Field(default=None, min_length=0, max_length=12000)
    source_secret_id: str | None = Field(default=None, min_length=36, max_length=36)

    @model_validator(mode="after")
    def validate_saved_app_secret(self):
        if self.kind == "management_key" and (self.scope != "provider" or self.owner != "openrouter"):
            raise ValueError("management_key_openrouter_only")
        if self.source_secret_id is not None:
            if self.scope != "channel" or self.kind not in {"app_secret", "client_secret"}:
                raise ValueError("saved_app_secret_only")
            if self.value:
                raise ValueError("credential_value_and_source_conflict")
            UUID(self.source_secret_id)
        return self


class PasswordChange(Reauthenticate):
    new_password: SecretStr = Field(min_length=15, max_length=128)


class Redeem(Strict):
    token: SecretStr = Field(min_length=40, max_length=100)
    new_password: SecretStr = Field(min_length=15, max_length=128)
    code: SecretStr | None = Field(default=None, max_length=40)


class VerifyFactor(Strict):
    setup_id: str
    code: SecretStr = Field(min_length=6, max_length=6)
