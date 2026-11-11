"""Protected local campaign operations; no route enables external transport."""

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import Field, model_validator

from app.modules.ai.domain.models import StrictModel
from .service import CampaignService, transport_disabled
from .workers import CampaignWorker

PublicId = Annotated[UUID, Field(strict=False)]


class Operation(StrictModel):
    operation_id: PublicId


class Revision(StrictModel):
    revision: int = Field(ge=0)


class PolicyWrite(Revision):
    stage_weights: dict[str, int] = Field(max_length=200)
    evaluation_enabled: bool
    interval_minutes: int = Field(ge=1, le=1440)

    @model_validator(mode="after")
    def weights(self):
        if any(not 0 <= value <= 25 for value in self.stage_weights.values()):
            raise ValueError("Invalid stage weight")
        return self


class RuleWrite(Revision):
    name: str = Field(min_length=1, max_length=160)
    stage: str = Field(min_length=1, max_length=60)
    inactivity_days: int = Field(ge=1, le=3650)
    cooldown_hours: int = Field(ge=1, le=87600)
    minimum_risk: int = Field(default=70, ge=0, le=100)
    template_id: PublicId | None = None
    enabled: bool = False


class Segment(StrictModel):
    program_ids: list[int] = Field(default_factory=list, max_length=200)
    period_id: int | None = None
    stage_values: list[str] = Field(default_factory=list, max_length=200)
    schedule_values: list[str] = Field(default_factory=list, max_length=50)


class BroadcastWrite(Revision):
    name: str = Field(min_length=1, max_length=160)
    template_id: PublicId | None = None
    segment: Segment
    scheduled_at: Annotated[datetime, Field(strict=False)] | None = None
    interval_seconds: int = Field(default=15, ge=1, le=86400)
    daily_limit: int = Field(default=100, ge=1, le=100000)

    @model_validator(mode="after")
    def schedule(self):
        if self.scheduled_at is not None:
            if self.scheduled_at.tzinfo is None:
                raise ValueError("UTC offset required")
            self.scheduled_at = self.scheduled_at.astimezone(timezone.utc).replace(tzinfo=None)
        return self


class Sync(StrictModel):
    after: str = Field(default="", max_length=1000)


def install_campaigns(application):
    service = CampaignService(application)
    application.state.campaign_service = service
    application.state.campaign_worker = CampaignWorker(service)
    router = APIRouter()
    router.add_api_route("/api/v1/campaigns/overview", service.overview, methods=["GET"])
    router.add_api_route("/api/v1/campaigns/settings", service.configuration, methods=["GET"])
    router.add_api_route("/api/v1/crm/predictions", service.predictions, methods=["GET"])
    router.add_api_route("/api/v1/campaigns/runs", service.runs, methods=["GET"])
    router.add_api_route("/api/v1/campaigns/templates", service.templates, methods=["GET"])
    router.add_api_route("/api/v1/campaigns/remarketing", service.rules, methods=["GET"])
    router.add_api_route("/api/v1/broadcasts", service.broadcasts, methods=["GET"])

    @router.put("/api/v1/campaigns/settings")
    def settings(request: PolicyWrite):
        return service.save_configuration(request)

    @router.post("/api/v1/crm/predictions/recalculate")
    @router.post("/api/v1/crm/predictions")
    def recalculate(request: Operation):
        return service.submit_run(request.operation_id, "predictions")

    @router.post("/api/v1/campaigns/templates/sync")
    def sync(request: Sync):
        return service.sync_templates(request.after)

    @router.post("/api/v1/campaigns/remarketing")
    def rule(request: RuleWrite):
        return service.save_rule(request)

    @router.put("/api/v1/campaigns/remarketing/{rule_id}")
    def edit_rule(rule_id: UUID, request: RuleWrite):
        return service.save_rule(request, rule_id)

    @router.delete("/api/v1/campaigns/remarketing/{rule_id}")
    def delete_rule(rule_id: UUID, revision: int = Query(ge=0)):
        return service.delete_rule(rule_id, revision)

    @router.post("/api/v1/campaigns/remarketing/{rule_id}/evaluate")
    def evaluate(rule_id: UUID, request: Operation):
        return service.submit_run(request.operation_id, "remarketing", rule_id=rule_id)

    @router.post("/api/v1/broadcasts")
    def broadcast(request: BroadcastWrite):
        return service.save_broadcast(request)

    @router.get("/api/v1/broadcasts/{campaign_id}")
    def detail(campaign_id: UUID):
        return service.broadcast(campaign_id)

    @router.put("/api/v1/broadcasts/{campaign_id}")
    def edit(campaign_id: UUID, request: BroadcastWrite):
        return service.save_broadcast(request, campaign_id)

    @router.post("/api/v1/broadcasts/{campaign_id}/pause")
    def pause(campaign_id: UUID, request: Revision):
        return service.pause(campaign_id, request.revision)

    @router.get("/api/v1/broadcasts/{campaign_id}/preview")
    def preview(campaign_id: UUID):
        return service.preview(campaign_id)

    @router.post("/api/v1/broadcasts/{campaign_id}/prepare")
    def prepare(campaign_id: UUID, request: Operation):
        return service.submit_run(request.operation_id, "preparation", campaign_id=campaign_id)

    @router.post("/api/v1/broadcasts/{campaign_id}/activate")
    @router.post("/api/v1/broadcasts/{campaign_id}/start")
    @router.post("/api/v1/broadcasts/{campaign_id}/send")
    def activate(campaign_id: UUID):
        return transport_disabled()

    application.include_router(router)
