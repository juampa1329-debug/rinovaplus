"""Closed institutional broadcast commands; provider approval is never client input."""

import re
from datetime import datetime, timezone
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator, model_validator

from app.institutional.models import Strict, public_url
from app.modules.agents.domain import JsonUUID


class Command(Strict):
    operation_id: JsonUUID
    revision: int = Field(default=0, ge=0)
    reason: str = Field(min_length=1, max_length=1000)

    @field_validator("reason")
    @classmethod
    def text(cls, v):
        if not v.strip() or "\x00" in v or len(v.encode("utf-16-le")) > 2000:
            raise ValueError("reason_required")
        return v.strip()


class Review(Command):
    confirmed: bool = False
    recipient_ids: list[JsonUUID] = Field(default_factory=list, max_length=500)


class Button(Strict):
    type: Literal["QUICK_REPLY", "URL", "PHONE_NUMBER"] = "QUICK_REPLY"
    text: str = Field(min_length=1, max_length=25)
    url: str = Field(default="", max_length=2000)
    phone_number: str = Field(default="", max_length=30, pattern=r"^$|^\+[0-9]{7,15}$")


class TemplateWrite(Command):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,127}$")
    language: str = Field(default="es", pattern=r"^[a-zA-Z_]{2,20}$")
    category: Literal["MARKETING", "UTILITY", "AUTHENTICATION"] = "MARKETING"
    body_text: str = Field(min_length=1, max_length=1024)
    header_type: Literal["", "TEXT", "IMAGE", "VIDEO", "DOCUMENT"] = ""
    header_text: str = Field(default="", max_length=60)
    header_media_handle: str = Field(default="", max_length=500)
    footer_text: str = Field(default="", max_length=60)
    buttons: list[Button] = Field(default_factory=list, max_length=3)
    allow_category_change: bool = True
    examples: dict[str, str] = Field(default_factory=dict, max_length=50)

    @field_validator("examples")
    @classmethod
    def sample_values(cls, value):
        if any(
            not re.fullmatch(r"(?:body|header)\.[1-9][0-9]*", key)
            or not sample.strip() or "\x00" in sample
            or len(sample.encode("utf-16-le")) > 2000
            for key, sample in value.items()
        ):
            raise ValueError("template_example_invalid")
        return value


class TemplatePause(Command):
    paused: bool


class Variable(Strict):
    source: Literal[
        "literal",
        "customer_name",
        "customer_first_name",
        "customer_email",
        "customer_city",
        "customer_phone",
        "program",
        "stage",
        "schedule",
        "campaign_name",
        "custom_field",
    ] = "literal"
    value: str = Field(default="", max_length=1000)
    field_key: str = Field(default="", pattern=r"^$|^[a-z][a-z0-9_]{0,39}$")

    @model_validator(mode="after")
    def custom_binding(self):
        if (self.source == "custom_field") != bool(self.field_key):
            raise ValueError("broadcast_custom_field_required")
        return self


class CustomFilter(Strict):
    field_key: str = Field(pattern=r"^[a-z][a-z0-9_]{0,39}$")
    values: list[str] = Field(min_length=1, max_length=100)


class Filters(Strict):
    audience_mode: Literal["segment", "contacts"] = "segment"
    contact_ids: list[JsonUUID] = Field(default_factory=list, max_length=5000)
    program_ids: list[int] = Field(default_factory=list, max_length=100)
    stages: list[str] = Field(default_factory=list, max_length=100)
    cities: list[str] = Field(default_factory=list, max_length=100)
    tags: list[str] = Field(default_factory=list, max_length=100)
    tag_match: Literal["all", "any"] = "all"
    schedules: list[str] = Field(default_factory=list, max_length=100)
    contact_types: list[str] = Field(default_factory=list, max_length=100)
    genders: list[str] = Field(default_factory=list, max_length=30)
    regions: list[str] = Field(default_factory=list, max_length=100)
    countries: list[str] = Field(default_factory=list, max_length=100)
    age_min: int | None = Field(default=None, ge=0, le=120)
    age_max: int | None = Field(default=None, ge=0, le=120)
    custom_fields: list[CustomFilter] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def safe(self):
        if any(v <= 0 for v in self.program_ids):
            raise ValueError("program_id_invalid")
        if self.age_min is not None and self.age_max is not None and self.age_min > self.age_max:
            raise ValueError("age_range_invalid")
        for values in [self.stages, self.cities, self.tags, self.schedules, self.contact_types, self.genders, self.regions, self.countries, *(f.values for f in self.custom_fields)]:
            if any(
                not v.strip() or "\x00" in v or len(v.encode("utf-16-le")) > 1000
                for v in values
            ):
                raise ValueError("filter_invalid")
        return self


class CampaignWrite(Command):
    name: str = Field(min_length=1, max_length=160)
    integration_id: JsonUUID
    template_id: JsonUUID
    template_version: int = Field(ge=1)
    filters: Filters = Field(default_factory=Filters)
    demographic_fields: dict[Literal["gender", "birth_date", "region", "country"], str] = Field(default_factory=dict, max_length=4)
    variables: dict[str, Variable] = Field(default_factory=dict, max_length=50)
    header_media_url: str = Field(default="", max_length=2000)
    scheduled_local: str | None = None
    timezone: str = Field(default="America/Bogota", max_length=80)

    @model_validator(mode="after")
    def safe(self):
        if (
            not self.name.strip()
            or "\x00" in self.name
            or len(self.name.encode("utf-16-le")) > 320
        ):
            raise ValueError("name_invalid")
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError) as e:
            raise ValueError("timezone_invalid") from e
        if self.header_media_url:
            public_url(self.header_media_url)
        if self.filters.audience_mode == "contacts" and not self.filters.contact_ids:
            raise ValueError("audience_contacts_required")
        if any(not re.fullmatch(r"[a-z][a-z0-9_]{0,39}", v) for v in self.demographic_fields.values()):
            raise ValueError("demographic_field_invalid")
        for filter_key, mapping_key in [("genders", "gender"), ("regions", "region"), ("countries", "country")]:
            if getattr(self.filters, filter_key) and mapping_key not in self.demographic_fields:
                raise ValueError("demographic_mapping_required")
        if (self.filters.age_min is not None or self.filters.age_max is not None) and "birth_date" not in self.demographic_fields:
            raise ValueError("birth_date_mapping_required")
        scheduled(self.scheduled_local, self.timezone)
        return self


def scheduled(value, zone):
    if not value:
        return None
    selected = ZoneInfo(zone)
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    first = dt.replace(tzinfo=selected, fold=0)
    other = dt.replace(tzinfo=selected, fold=1)
    if (
        first.utcoffset() != other.utcoffset()
        or first.astimezone(timezone.utc).astimezone(selected).replace(tzinfo=None)
        != dt
    ):
        raise ValueError("schedule_ambiguous_or_nonexistent")
    return first.astimezone(timezone.utc).replace(tzinfo=None)


class ConsentWrite(Review):
    state: Literal["granted", "revoked"]
    evidence: str = Field(min_length=1, max_length=1000)
    origin: str = Field(min_length=1, max_length=200)
    expires_at: str | None = None

    @model_validator(mode="after")
    def safe(self):
        if not self.confirmed or not self.evidence.strip() or not self.origin.strip():
            raise ValueError("consent_evidence_required")
        for name, limit in [("evidence", 1000), ("origin", 200)]:
            if (
                "\x00" in getattr(self, name)
                or len(getattr(self, name).encode("utf-16-le")) > 2 * limit
            ):
                raise ValueError("text_limit")
        if self.expires_at:
            dt = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
            if not dt.tzinfo:
                raise ValueError("consent_expiry_invalid")
        if self.state == "granted":
            if not self.expires_at:
                raise ValueError("consent_expiry_required")
            dt = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
            if not dt.tzinfo or dt <= datetime.now(timezone.utc):
                raise ValueError("consent_expiry_invalid")
        return self


class CadenceWrite(Command):
    enabled: bool = False
    daily_limit: int = Field(default=100, ge=1, le=100000)
    interval_seconds: int = Field(default=30, ge=1, le=86400)
