"""Explicit, bounded language routes. Catalog presence is checked at execution."""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LanguageRoute(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    provider: Literal["gemini", "openrouter", "openai", "anthropic", "hermes", "groq", "kimi", "nvidia", "mistral", "xai"]
    model: str = Field(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9._:/-]+$")
    input_usd_per_million: float = Field(default=0, ge=0, le=100000)
    output_usd_per_million: float = Field(default=0, ge=0, le=100000)

    @model_validator(mode="after")
    def interactive(self):
        if ".." in self.model or self.model.endswith(":batch"):
            raise ValueError("language_backup_interactive_model_required")
        return self


class LanguageResilience(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    enabled: bool = False
    fallback_on_timeout: bool = False
    primary: LanguageRoute | None = None
    opening: LanguageRoute | None = None
    opening_stage_keys: list[str] = Field(default_factory=list, max_length=100)
    reply_max_tokens: int = Field(default=2000, ge=512, le=8000)
    routes: list[LanguageRoute] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def unique(self):
        if self.opening and (not self.primary or not self.opening_stage_keys):
            raise ValueError("language_opening_primary_and_stages_required")
        if len(set(self.opening_stage_keys)) != len(self.opening_stage_keys) or any(
            not re.fullmatch(r"[a-z][a-z0-9_]{0,39}", key)
            for key in self.opening_stage_keys
        ):
            raise ValueError("language_opening_stage_invalid")
        if self.primary and any((r.provider, r.model) == (self.primary.provider, self.primary.model) for r in self.routes):
            raise ValueError("language_backup_duplicate")
        if len({(r.provider, r.model) for r in self.routes}) != len(self.routes):
            raise ValueError("language_backup_duplicate")
        if self.enabled and not self.routes:
            raise ValueError("language_backup_required")
        return self


def can_failover(error):
    """Only a rejected/unconnected request; no replay of accepted or unknown work."""
    return error.code in {"provider_model_unavailable", "provider_rate_limited",
                          "provider_connection_failed", "agents_provider_not_configured", "provider_key_missing"} or (
        error.upstream_status in {401, 403, 404, 429, 503}
        and error.code in {"provider_rejected_request", "provider_temporary_failure", "openrouter_rejected_request", "openrouter_retry_exhausted"}
    )
