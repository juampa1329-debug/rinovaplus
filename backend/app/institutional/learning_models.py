"""Closed institutional learning commands. No arbitrary SQL or executable models."""

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.institutional.learning_engine import FEATURES, features

Task = Literal[
    "lead_scoring", "churn_prediction", "smart_remarketing", "operational_anomaly"
]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Command(Strict):
    operation_id: UUID


class PackDocument(Strict):
    name: str = Field(min_length=3, max_length=100)
    task: Task
    scope: Literal["demo", "native"] = "native"
    training_enabled: bool = True


class PackWrite(Command):
    revision: int = Field(ge=0, le=2147483647)
    document: PackDocument


class GrantWrite(Command):
    revision: int = Field(ge=0, le=2147483647)
    subject_id: UUID | None = None
    demo_subject: UUID | None = None
    approved: bool
    basis: Literal["consent", "institutional_authorization", "synthetic_demo"]
    reference: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_.:/-]+$")


class SampleWrite(Command):
    grant_id: UUID
    source_kind: Literal["conversation", "campaign", "admissions", "demo"]
    source_id: UUID | None = None
    program_id: int | None = Field(default=None, ge=1, le=2147483647)
    stage: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    feature_at: datetime
    outcome_at: datetime
    features: dict[str, float] = Field(min_length=1, max_length=16)
    label: Literal[0, 1]
    supersedes: UUID | None = None

    @field_validator("features", mode="before")
    @classmethod
    def numeric_only(cls, v):
        if not isinstance(v, dict) or any(
            type(n) not in {int, float} for n in v.values()
        ):
            raise ValueError("numeric_observations_required")
        return v

    @field_validator("label", mode="before")
    @classmethod
    def binary_label(cls, v):
        if type(v) is not int or v not in {0, 1}:
            raise ValueError("reviewed_binary_label_required")
        return v

    @field_validator("feature_at", "outcome_at")
    @classmethod
    def aware(cls, v):
        if v.tzinfo is None or v.utcoffset() is None:
            raise ValueError("timezone_required")
        return v.astimezone(timezone.utc)

    @model_validator(mode="after")
    def order(self):
        if not self.feature_at < self.outcome_at <= datetime.now(timezone.utc):
            raise ValueError("learning_temporal_order")
        return self


class DatasetWrite(Command):
    cutoff: datetime

    @field_validator("cutoff")
    @classmethod
    def aware(cls, v):
        if v.tzinfo is None or v.utcoffset() is None or v >= datetime.now(timezone.utc):
            raise ValueError("past_aware_cutoff_required")
        return v.astimezone(timezone.utc)


class TrainWrite(Command):
    dataset_id: UUID


class Selection(Command):
    revision: int = Field(ge=1, le=2147483647)
    artifact_id: UUID | None = None
    action: Literal["shadow", "promote", "rollback", "pause", "resume"]


class Inference(Command):
    grant_id: UUID
    features: dict[str, float] = Field(min_length=1, max_length=16)
    mode: Literal["shadow", "active"] = "shadow"

    @field_validator("features", mode="before")
    @classmethod
    def numeric_only(cls, v):
        return SampleWrite.numeric_only(v)


def validate_features(task, value):
    return features(task, value)


PURPOSE = {task: "educational_" + task for task in FEATURES}
