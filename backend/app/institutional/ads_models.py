"""Closed, account-scoped Ads records; recorded budgets never authorize spending."""

from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, field_validator, model_validator

from app.institutional.broadcast_models import Command as BaseCommand
from app.institutional.models import Strict, public_url
from app.modules.agents.domain import JsonUUID


class Command(BaseCommand):
    reason: str = Field(
        default="Actualización local de Publicidad", min_length=1, max_length=1000
    )


class Account(Strict):
    provider: Literal["meta", "tiktok"] = "meta"
    external_account_id: str = Field(min_length=1, max_length=160)
    name: str = Field(min_length=1, max_length=180)
    status: Literal["connected", "paused", "disconnected"] = "connected"
    currency: str = Field(default="COP", pattern="^[A-Z]{3}$")
    timezone: str = Field(default="America/Bogota", max_length=80)
    integration_id: JsonUUID | None = None
    program_id: int | None = Field(default=None, ge=-2147483648, le=2147483647)
    initial_stage_key: str = Field(default="", max_length=60)
    form_ids: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def check(self):
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("invalid_timezone") from None
        if self.provider == "meta":
            self.external_account_id = self.external_account_id.removeprefix("act_")
        for v in [self.external_account_id, *self.form_ids]:
            external(v, 180)
        if len(set(self.form_ids)) != len(self.form_ids):
            raise ValueError("duplicate_form")
        safe_text(self.name, 180)
        return self


def external(v, limit=180):
    if not v or len(v) > limit or not all(33 <= ord(c) <= 126 for c in v):
        raise ValueError("invalid_external_id")
    return v


def safe_text(v, limit):
    if len(v.encode("utf-16-le")) > limit * 2 or any(
        ord(c) < 32 and c not in "\n\r\t" for c in v
    ):
        raise ValueError("invalid_text")
    return v


class Metrics(Strict):
    ctr: float = Field(default=0, ge=0, le=100, allow_inf_nan=False)
    cpc: float = Field(default=0, ge=0, le=1000000000, allow_inf_nan=False)
    leads: int = Field(default=0, ge=0, le=100000000)


class Campaign(Strict):
    account_id: JsonUUID
    channel: Literal["facebook", "instagram", "tiktok"] = "facebook"
    external_campaign_id: str = Field(min_length=1, max_length=160)
    name: str = Field(min_length=1, max_length=180)
    objective: str = Field(default="messages", max_length=120)
    status: Literal["unknown", "draft", "active", "paused", "completed", "archived"] = (
        "unknown"
    )
    daily_budget_cents: int = Field(default=0, ge=0, le=1000000000000)
    lifetime_budget_cents: int = Field(default=0, ge=0, le=1000000000000)
    currency: str = Field(default="COP", pattern="^[A-Z]{3}$")
    metrics_json: Metrics | None = None
    period_start: str | None = Field(
        default=None, pattern="^[0-9]{4}-[0-9]{2}-[0-9]{2}$"
    )
    period_end: str | None = Field(default=None, pattern="^[0-9]{4}-[0-9]{2}-[0-9]{2}$")

    @model_validator(mode="after")
    def check(self):
        from datetime import date

        external(self.external_campaign_id, 160)
        safe_text(self.name, 180)
        if bool(self.period_start) != bool(self.period_end):
            raise ValueError("metric_period_required")
        if self.period_start and date.fromisoformat(
            self.period_start
        ) > date.fromisoformat(self.period_end):
            raise ValueError("invalid_metric_period")
        if self.metrics_json is not None and not self.period_start:
            raise ValueError("metric_period_required")
        return self


class Intake(Strict):
    account_id: JsonUUID
    channel: Literal["facebook", "instagram", "tiktok"] = "facebook"
    external_id: str = Field(min_length=1, max_length=180)
    external_form_id: str = Field(default="", max_length=180)
    external_ad_id: str = Field(default="", max_length=180)
    external_campaign_id: str = Field(default="", max_length=160)
    author_id: str = Field(default="", max_length=180)
    contact_name: str = Field(default="", max_length=180)
    email: str = Field(default="", max_length=180)
    phone: str = Field(default="", max_length=40)
    message: str = Field(default="", max_length=4000)
    external_post_id: str = Field(default="", max_length=180)
    external_parent_id: str = Field(default="", max_length=180)
    permalink_url: str = Field(default="", max_length=1000)
    status: Literal[
        "new",
        "review",
        "qualified",
        "converted",
        "lost",
        "resolved",
        "ignored",
        "hidden",
        "deleted",
    ] = "new"
    program_id: int | None = Field(default=None, ge=-2147483648, le=2147483647)
    captured_at: datetime | None = None

    @field_validator("captured_at", mode="before")
    @classmethod
    def iso_time(cls, value):
        if isinstance(value, str):
            if len(value) > 64:
                raise ValueError("invalid_capture_time")
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value

    @model_validator(mode="after")
    def check(self):
        external(self.external_id)
        for v in [
            self.external_form_id,
            self.external_ad_id,
            self.external_campaign_id,
            self.author_id,
            self.external_post_id,
            self.external_parent_id,
        ]:
            if v:
                external(v)
        for field, limit in [
            (self.contact_name, 180),
            (self.email, 180),
            (self.message, 4000),
        ]:
            safe_text(field, limit)
        if self.permalink_url:
            public_url(self.permalink_url)
        if self.captured_at is not None:
            if self.captured_at.tzinfo is None:
                raise ValueError("captured_at_requires_timezone")
            from datetime import timedelta, timezone

            if self.captured_at > datetime.now(timezone.utc) + timedelta(minutes=5):
                raise ValueError("captured_at_in_future")
        return self


class SaveAccount(Command):
    document: Account


class SaveCampaign(Command):
    document: Campaign


class SaveIntake(Command):
    document: Intake
    create_conversation: bool = False


class Process(Command):
    create_conversation: bool = True


class Credential(Command):
    value: SecretStr | None = None

    @model_validator(mode="after")
    def check(self):
        if self.value and not 1 <= len(self.value.get_secret_value()) <= 16000:
            raise ValueError("invalid_credential")
        return self
