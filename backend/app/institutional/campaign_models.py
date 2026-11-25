"""Closed CRM campaign documents, distinct from provider template approval."""

import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pydantic import Field, model_validator
from app.institutional.models import Strict, public_url
from app.institutional.broadcast_models import Command, Filters, Variable, scheduled
from app.modules.agents.domain import JsonUUID

Kind = Literal["template", "segment", "campaign", "trigger", "flow"]


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def bounded(value):
    if isinstance(value, str):
        if "\x00" in value or len(value.encode("utf-16-le")) > 16000:
            raise ValueError("text_invalid")
    elif isinstance(value, dict):
        for k, v in value.items():
            bounded(k)
            bounded(v)
    elif isinstance(value, list):
        for v in value:
            bounded(v)


class Conditions(Filters):
    followup_states: list[Literal["interest_confirmed", "form_sent", "form_reported_complete"]] = Field(default_factory=list, max_length=3)
    keywords: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def safe_keywords(self):
        if any(not v.strip() or len(v) > 100 for v in self.keywords):
            raise ValueError("keyword_invalid")
        return self


class Block(Strict):
    type: Literal[
        "text", "heading", "image", "video", "audio", "document", "button"
    ] = "text"
    text: str = Field(default="", max_length=2000)
    url: str = Field(default="", max_length=2000)
    asset_id: JsonUUID | None = None
    filename: str = Field(default="", max_length=160)
    delay_ms: int = Field(default=0, ge=0, le=300000)

    @model_validator(mode="after")
    def safe(self):
        if self.type in {"image", "video", "audio", "document"} and bool(
            self.url
        ) == bool(self.asset_id):
            raise ValueError("select_uploaded_asset_or_public_URL")
        if self.type == "audio" and self.text:
            raise ValueError("audio_has_no_caption")
        if self.asset_id and self.type not in {"image", "video", "audio", "document"}:
            raise ValueError("media_block_required")
        if self.url:
            public_url(self.url)
        return self


class Template(Strict):
    channel: Literal["whatsapp", "instagram", "messenger", "tiktok"] = "whatsapp"
    category: str = Field(default="general", max_length=80)
    template_scope: Literal["crm"] = "crm"
    render_mode: Literal["chat", "builder"] = "chat"
    body: str = Field(default="", max_length=8000)
    variables: dict[str, Variable] = Field(default_factory=dict, max_length=50)
    blocks: list[Block] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def safe(self):
        text = "\n".join([self.body] + [b.text for b in self.blocks])
        names = set(re.findall(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]{0,40})\s*\}\}", text))
        if set(self.variables) != names:
            raise ValueError("CRM_template_variable_bindings_required")
        if "{{" in re.sub(r"\{\{[^{}]+\}\}", "", text):
            raise ValueError("template_placeholder_invalid")
        return self


class Segment(Strict):
    description: str = Field(default="", max_length=800)
    filters: Conditions = Field(default_factory=Conditions)


class Quiet(Strict):
    enabled: bool = False
    timezone: str = Field(default="America/Bogota", max_length=80)
    start_time: str = Field(default="21:00", pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")
    end_time: str = Field(default="08:00", pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")
    days: list[int] = Field(default_factory=lambda: list(range(7)), max_length=7)

    @model_validator(mode="after")
    def safe(self):
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError) as e:
            raise ValueError("timezone_invalid") from e
        if (
            self.start_time == self.end_time
            or len(set(self.days)) != len(self.days)
            or any(d not in range(7) for d in self.days)
        ):
            raise ValueError("quiet_hours_invalid")
        return self


def next_allowed(value, quiet):
    q = quiet if isinstance(quiet, Quiet) else Quiet(**quiet)
    if not q.enabled:
        return value
    candidate = value
    for _ in range(8 * 1440 + 1):
        local = candidate.replace(tzinfo=timezone.utc).astimezone(ZoneInfo(q.timezone))
        clock = local.strftime("%H:%M")
        day = local.weekday()
        blocked = (
            (day in q.days and q.start_time <= clock < q.end_time)
            if q.start_time < q.end_time
            else (
                day in q.days
                and clock >= q.start_time
                or (day - 1) % 7 in q.days
                and clock < q.end_time
            )
        )
        if not blocked:
            return candidate
        candidate = (candidate + timedelta(minutes=1)).replace(second=0, microsecond=0)
    raise ValueError("quiet_hours_no_window")


class AB(Strict):
    enabled: bool = False
    a_percent: int = Field(default=50, ge=1, le=99)
    label: str = Field(default="Experimento", max_length=100)


class Step(Strict):
    kind: Literal["wait", "condition", "send"] = "wait"
    name: str = Field(default="", max_length=160)
    wait_minutes: int = Field(default=0, ge=0, le=43200)
    conditions: Conditions = Field(default_factory=Conditions)
    on_false: Literal["stop", "skip"] = "stop"
    crm_template_id: JsonUUID | None = None
    crm_template_version: int = Field(default=1, ge=1)
    variant_b_crm_template_id: JsonUUID | None = None
    variant_b_crm_template_version: int = Field(default=1, ge=1)
    meta_template_id: JsonUUID | None = None
    meta_template_version: int = Field(default=1, ge=1)
    variables: dict[str, Variable] = Field(default_factory=dict, max_length=50)
    header_media_url: str = Field(default="", max_length=2000)
    variant_b_template_id: JsonUUID | None = None
    variant_b_template_version: int = Field(default=1, ge=1)
    variant_b_variables: dict[str, Variable] = Field(
        default_factory=dict, max_length=50
    )

    @model_validator(mode="after")
    def safe(self):
        if self.kind == "send" and bool(self.meta_template_id) == bool(
            self.crm_template_id
        ):
            raise ValueError("select_one_CRM_or_Meta_template")
        if self.variant_b_template_id and self.variant_b_crm_template_id:
            raise ValueError("select_one_variant_B_contract")
        if (
            self.crm_template_id
            and self.variant_b_template_id
            or self.meta_template_id
            and self.variant_b_crm_template_id
        ):
            raise ValueError("AB_template_contracts_must_match")
        if self.header_media_url:
            public_url(self.header_media_url)
        return self


class Flow(Strict):
    followup_only: bool = False
    contact_basis: Literal["marketing", "customer_request"] = "marketing"
    channel: Literal["whatsapp", "instagram", "messenger", "tiktok"] = "whatsapp"
    integration_id: JsonUUID
    objective: str = Field(default="", max_length=1000)
    description: str = Field(default="", max_length=1000)
    segment_id: JsonUUID | None = None
    segment_version: int = Field(default=1, ge=1)
    crm_template_id: JsonUUID | None = None
    crm_template_version: int = Field(default=1, ge=1)
    entry_conditions: Conditions = Field(default_factory=Conditions)
    scheduled_local: str | None = None
    timezone: str = Field(default="America/Bogota", max_length=80)
    quiet_hours: Quiet = Field(default_factory=Quiet)
    exit_on_response: bool = True
    steps: list[Step] = Field(min_length=1, max_length=20)
    ab_test: AB = Field(default_factory=AB)
    cooldown_minutes: int = Field(default=1440, ge=0, le=43200)

    @model_validator(mode="after")
    def safe(self):
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError) as e:
            raise ValueError("timezone_invalid") from e
        scheduled(self.scheduled_local, self.timezone)
        if self.followup_only and (not self.exit_on_response or not self.quiet_hours.enabled):
            raise ValueError("followup_requires_quiet_hours_and_exit_on_response")
        if self.contact_basis == "customer_request" and not self.followup_only:
            raise ValueError("customer_request_requires_conversation_followup")
        if self.ab_test.enabled and any(
            v.kind == "send"
            and not (v.variant_b_template_id or v.variant_b_crm_template_id)
            for v in self.steps
        ):
            raise ValueError("AB_requires_variant_B_template")
        return self


class Trigger(Strict):
    channel: Literal["whatsapp", "instagram", "messenger", "tiktok"] = "whatsapp"
    event_type: Literal[
        "message_in", "stage_changed", "program_changed", "inactivity"
    ] = "message_in"
    flow_id: JsonUUID
    flow_version: int = Field(ge=1)
    conditions: Conditions = Field(default_factory=Conditions)
    priority: int = Field(default=100, ge=1, le=10000)
    cooldown_minutes: int = Field(default=60, ge=0, le=43200)
    idle_minutes: int = Field(default=1440, ge=1, le=43200)
    stop_on_match: bool = True
    only_when_no_takeover: Literal[True] = True


def document(kind, raw):
    model = {
        "template": Template,
        "segment": Segment,
        "flow": Flow,
        "campaign": Flow,
        "trigger": Trigger,
    }[kind](**raw)
    value = model.model_dump(mode="json")
    bounded(value)
    if len(json.dumps(value).encode()) > 100000:
        raise ValueError("document_limit")
    return value


class Save(Command):
    kind: Kind
    name: str = Field(min_length=1, max_length=160)
    document: dict[str, Any]

    @model_validator(mode="after")
    def safe(self):
        if not self.name.strip() or len(self.name.encode("utf-16-le")) > 320:
            raise ValueError("name_invalid")
        bounded(self.name)
        self.document = document(self.kind, self.document)
        return self


class Review(Command):
    confirmed: bool = False
    preflight_id: JsonUUID | None = None
    identity_ids: list[JsonUUID] = Field(default_factory=list, max_length=500)
    version: int | None = Field(default=None, ge=1)
    name: str = Field(default="", max_length=160)


class Simulate(Command):
    identity_id: JsonUUID | None = None
    sample: dict[str, str] = Field(default_factory=dict, max_length=10)
    variant: Literal["A", "B"] = "A"

    @model_validator(mode="after")
    def safe(self):
        if set(self.sample) - {
            "name",
            "phone",
            "city",
            "program",
            "stage",
            "schedule",
            "message",
            "email",
        }:
            raise ValueError("simulation_field_invalid")
        bounded(self.sample)
        return self
