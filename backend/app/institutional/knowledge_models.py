"""Closed source/memory commands; no client actor or publication state."""

from datetime import date
from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.institutional.models import Strict
from app.modules.agents.domain import JsonUUID


class DNA(Strict):
    mission: str = Field(default="", max_length=2000)
    voice: str = Field(default="", max_length=1000)
    principles: str = Field(default="", max_length=2000)
    boundaries: str = Field(default="", max_length=2000)
    escalation: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def safe_text(self):
        for name, limit in [
            ("mission", 2000),
            ("voice", 1000),
            ("principles", 2000),
            ("boundaries", 2000),
            ("escalation", 1000),
        ]:
            value = getattr(self, name)
            if "\x00" in value or len(value.encode("utf-16-le")) > 2 * limit:
                raise ValueError("DNA_text_invalid")
        return self


class Command(Strict):
    operation_id: JsonUUID
    revision: int = Field(ge=0)
    reason: str = Field(min_length=1, max_length=1000)

    @field_validator("reason")
    @classmethod
    def reason_required(cls, value):
        if not value.strip() or len(value.encode("utf-16-le")) > 2000:
            raise ValueError("reason_required")
        return value.strip()


class RecordWrite(Command):
    kind: Literal["document", "collective", "dna", "private"]
    title: str = Field(min_length=1, max_length=160)
    body: str = Field(default="", max_length=300000)
    owner: str = Field(min_length=1, max_length=160)
    origin: str = Field(min_length=1, max_length=1000)
    valid_until: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    confidence: int = Field(default=80, ge=0, le=100)
    visibility: Literal["agent_context", "staff_only", "conversation_only"] = (
        "agent_context"
    )
    program_id: int | None = Field(default=None, gt=0)
    stage_id: JsonUUID | None = None
    dna: DNA | None = None
    source_message_id: JsonUUID | None = None
    quote: str = Field(default="", max_length=2000)
    fact_type: Literal[
        "program_interest",
        "schedule_availability",
        "registration_reported",
        "contact_preference",
        "followup_note",
    ] = "followup_note"

    @model_validator(mode="after")
    def bounded(self):
        date.fromisoformat(self.valid_until)
        for name, limit in [
            ("title", 160),
            ("owner", 100 if self.kind == "document" else 160),
            ("origin", 1000),
            ("body", 300000 if self.kind == "document" else 10000),
            ("quote", 2000),
        ]:
            text = getattr(self, name)
            if "\x00" in text or len(text.encode("utf-16-le")) > 2 * limit:
                raise ValueError("field_too_long_or_invalid")
        if not self.title.strip() or not self.owner.strip() or not self.origin.strip():
            raise ValueError("metadata_required")
        if self.kind == "dna":
            if (
                not self.dna
                or not self.dna.mission.strip()
                or self.program_id
                or self.stage_id
                or self.body
            ):
                raise ValueError("institutional_DNA_required")
        elif self.dna is not None or not self.body.strip():
            raise ValueError("body_required")
        if self.kind == "private":
            if (
                self.visibility != "conversation_only"
                or self.program_id
                or self.stage_id
                or not self.source_message_id
                or not self.quote.strip()
            ):
                raise ValueError("conversation_evidence_required")
        elif (
            self.visibility == "conversation_only"
            or self.source_message_id
            or self.quote
        ):
            raise ValueError("private_fields_forbidden")
        if self.stage_id and not self.program_id:
            raise ValueError("stage_requires_program")
        return self


class Upload(Command):
    title: str = Field(min_length=1, max_length=160)
    filename: str = Field(min_length=1, max_length=160)
    content_base64: str = Field(min_length=1, max_length=6_666_668)
    owner: str = Field(min_length=1, max_length=100)
    confidence: int = Field(default=80, ge=0, le=100)
    origin: str = Field(min_length=1, max_length=1000)
    valid_until: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    visibility: Literal["agent_context", "staff_only"] = "agent_context"
    program_id: int | None = Field(default=None, gt=0)
    stage_id: JsonUUID | None = None
    record_id: JsonUUID


class Transition(Command):
    confirmed: bool = False
    version: int | None = Field(default=None, ge=1)


class Search(Strict):
    query: str = Field(min_length=1, max_length=1000)
    program_id: int | None = Field(default=None, gt=0)
    stage_id: JsonUUID | None = None


class Evaluation(Search):
    expected_document_id: JsonUUID
