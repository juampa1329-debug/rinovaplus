"""Provisional local shapes; never identity, core or provider credentials."""

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Text = Annotated[str, Field(max_length=1000)]
DemoReference = Annotated[str, Field(pattern=r"^DEMO-[A-Za-z0-9_-]{1,60}$")]


class LocalModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class PendingRequest(LocalModel):
    """Intentionally empty: domain/provider schema is not approved."""


class Channel(str, Enum):
    facebook = "facebook"
    messenger = "messenger"
    instagram = "instagram"
    whatsapp = "whatsapp"
    tiktok = "tiktok"


class ClientDraft(LocalModel):
    name: Text | None = None
    phone: Text | None = None
    city: Text | None = None
    program: Text | None = None
    schedule: Text | None = None
    stage: Text | None = None
    tags: Text | None = None
    notes: Text | None = None
    type: Text | None = None
    interests: Text | None = None
    customValues: dict[str, Text] | None = None


class Stage(LocalModel):
    key: Text
    label: Text
    probability: Annotated[float, Field(ge=0, le=100)]


class CustomField(LocalModel):
    key: Text
    label: Text
    type: Literal["Text", "Number", "List", "Date", "Boolean", "Email", "Phone", "URL"]
    options: list[Text]
    active: bool


class CrmDraft(LocalModel):
    stages: list[Stage] | None = None
    tags: list[Text] | None = None
    fields: list[CustomField] | None = None


class MessageDraft(LocalModel):
    body: Text | None = None


class WorkflowDraft(LocalModel):
    state: Literal["Abierta", "En espera", "Cerrada"] | None = None
    priority: Literal["Baja", "Normal", "Alta", "Urgente"] | None = None
    assignee: Text | None = None


class TaskDraft(LocalModel):
    title: Text | None = None
    due: Text | None = None
    status: Literal["Pendiente", "Completada", "Cancelada"] | None = None


class ApplicationDraft(LocalModel):
    name: Text | None = None
    email: Text | None = None
    program: Text | None = None
    schedule: Text | None = None
    consent: bool | None = None


class ReviewDraft(LocalModel):
    status: Literal["reviewed", "observed", "rejected"] | None = None
    reason: Text | None = None


class AssistantDraft(LocalModel):
    assistantName: Text | None = None
    style: Text | None = None
    instructions: Text | None = None


class ProfileDraft(LocalModel):
    profileName: Text | None = None
    position: Text | None = None
    timezone: Literal["America/Bogota", "UTC"] | None = None


class ChannelDraft(LocalModel):
    appReference: DemoReference | None = None
    assetReference: DemoReference | None = None
    portfolioReference: DemoReference | None = None
    pageReference: DemoReference | None = None
    wabaReference: DemoReference | None = None
    phoneReference: DemoReference | None = None
    accountReference: DemoReference | None = None
    usernameReference: DemoReference | None = None
    clientKeyReference: DemoReference | None = None
    openIdReference: DemoReference | None = None
    tokenReference: DemoReference | None = None
    secretReference: DemoReference | None = None
    verifyReference: DemoReference | None = None
    callbackReference: DemoReference | None = None
    webhookReference: DemoReference | None = None
    versionReference: DemoReference | None = None
    requestedScopesReference: DemoReference | None = None
    grantedScopesReference: DemoReference | None = None
    accessEvidenceReference: DemoReference | None = None


class StubUnavailable(LocalModel):
    code: Literal["local_stub_unavailable"] = "local_stub_unavailable"
    mode: Literal["local_demo"] = "local_demo"
    operation_id: str
    schema_status: Literal["provisional", "pending", "local_defined"]
    activation_gate: str


class InvalidInput(LocalModel):
    code: Literal["invalid_local_contract_input"] = "invalid_local_contract_input"
    mode: Literal["local_demo"] = "local_demo"
