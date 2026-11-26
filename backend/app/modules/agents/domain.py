"""Deterministic hierarchy, inherited restrictions and single-turn ownership."""

import hashlib
import json
import re
from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BeforeValidator, Field, model_validator, field_validator

from app.modules.ai.domain.models import Provider, StrictModel
from app.modules.ai.infrastructure.providers import AiError

CAPABILITIES = {
    "program.read",
    "sources.read",
    "conversation.reply",
    "human.handoff",
    "advisor.actions",
    "advisor.summary",
    "analytics.read",
    "analytics.report",
    "campaigns.draft",
    "campaigns.suggest",
    "crm.update",
    "compliance.check",
}
MEMORIES = {
    "short",
    "semantic",
    "business_summary",
    "customer_profile",
    "knowledge",
    "campaigns",
    "incidents",
    "workflows",
    "vertical",
    "regulated",
    "collective",
}


def uuid_from_json(value):
    return UUID(value) if isinstance(value, str) else value


JsonUUID = Annotated[UUID, BeforeValidator(uuid_from_json)]


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()
    ).hexdigest()


class Configuration(StrictModel):
    provider: Provider = "openrouter"
    sales_skill_ids: list[str] = Field(default_factory=list, max_length=64)
    sales_routing_enabled: bool = False
    sales_memory_enabled: bool = False
    auto_sales_crm: bool = False
    voice_profile_id: str = Field(default="", max_length=64, pattern=r"^[A-Za-z0-9_-]*$")
    description: str = ""
    operating_style: str = ""
    risk_posture: Literal["balanced", "cautious"] = "balanced"
    escalation_policy: str = ""
    instruction_template: Literal["custom", "admissions", "program"] = "custom"
    template_variables: dict[str, str] = Field(default_factory=dict)
    customized: bool = True
    route: Literal["admissions", "institutional", "followup", "analytics"] = (
        "admissions"
    )
    global_enabled: bool = False
    fallback_provider: Provider | None = None
    monthly_usd_limit: float = Field(default=0, ge=0, le=1000000)
    usage_alert_percent: int = Field(default=80, ge=1, le=100)
    hard_stop: bool = True
    input_usd_per_million: float | None = Field(default=None, ge=0, le=100000)
    output_usd_per_million: float | None = Field(default=None, ge=0, le=100000)
    fallback_input_usd_per_million: float | None = Field(default=None, ge=0, le=100000)
    fallback_output_usd_per_million: float | None = Field(default=None, ge=0, le=100000)
    ab_enabled: bool = False
    ab_variant: str = Field(default="A", min_length=1, max_length=40)
    ab_compare_version: int | None = Field(default=None, ge=1)
    ab_traffic_percent: int = Field(default=50, ge=1, le=99)
    industry_policies: list[Literal["academy", "privacy", "payments", "minors"]] = (
        Field(default_factory=lambda: ["academy", "privacy"])
    )
    memories: list[str] = Field(
        default_factory=lambda: [
            "short",
            "semantic",
            "business_summary",
            "customer_profile",
            "knowledge",
            "vertical",
            "regulated",
        ]
    )
    require_human_approval: bool = True
    allow_safe_actions: bool = False
    allow_crm_update: bool = False
    instructions: str = ""
    advisor_name: str = Field(default="", max_length=50, pattern=r"^[^\x00-\x1f\x7f]*$")
    objectives: list[str] = Field(default_factory=list)
    rules: list[str] = Field(default_factory=list)
    tone: str = ""
    channels: list[Literal["whatsapp", "instagram", "facebook", "tiktok", "local"]] = (
        Field(default_factory=list, max_length=5)
    )
    capabilities: list[str] = Field(default_factory=list, max_length=12)
    document_ids: list[JsonUUID] = Field(default_factory=list, max_length=40)
    primary_model: str = Field(
        default="", max_length=200, pattern=r"^[A-Za-z0-9._:/-]*$"
    )
    fallback_model: str = Field(
        default="", max_length=200, pattern=r"^[A-Za-z0-9._:/-]*$"
    )
    max_tokens: int = Field(default=700, ge=128, le=8000)
    monthly_token_limit: int = Field(default=0, ge=0, le=100000000)
    allow_reply: bool = False

    @field_validator("advisor_name")
    @classmethod
    def valid_advisor_name(cls, value):
        value = value.strip()
        if value and (not any(ch.isalpha() for ch in value) or any(not (ch.isalpha() or ch in " .'-’") for ch in value)):
            raise ValueError("Invalid presentation name")
        return value

    @model_validator(mode="after")
    def available(self):
        from app.modules.agents.sales_skills import IDS
        if len(self.sales_skill_ids) != len(set(self.sales_skill_ids)) or set(self.sales_skill_ids) - IDS:
            raise ValueError("Unsupported sales skill")
        if self.auto_sales_crm and not self.sales_memory_enabled:
            raise ValueError("Commercial CRM updates require conversation memory")
        if any(
            not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key)
            or key
            in {"agent_name", "agent_description", "agent_specialty", "program_id"}
            for key in self.template_variables
        ):
            raise ValueError("Invalid or reserved template variable")
        if set(self.capabilities) - CAPABILITIES:
            raise ValueError("Unsupported executable capability")
        if set(self.memories) - MEMORIES:
            raise ValueError("Unsupported memory scope")
        if (
            self.fallback_model
            and self.primary_model == self.fallback_model
            and (self.fallback_provider or self.provider) == self.provider
        ):
            raise ValueError("Fallback must differ")
        if ".." in self.primary_model or ".." in self.fallback_model:
            raise ValueError("Invalid model")
        return self


class Mutation(StrictModel):
    operation_id: JsonUUID
    revision: int = Field(ge=0)

    @model_validator(mode="after")
    def sql_note_lengths(self):
        for field in (
            "note",
            "evidence",
            "entry_rule",
            "exit_rule",
            "evidence_required",
        ):
            value = getattr(self, field, None)
            if isinstance(value, str) and len(value.encode("utf-16-le")) > 2000:
                raise ValueError("SQL UTF16 length exceeded: " + field)
        return self


class AgentWrite(Mutation):
    name: str = Field(min_length=1, max_length=100)
    level: Literal["guide", "program", "stage"]
    parent_id: JsonUUID | None = None
    program_id: int | None = Field(default=None, gt=0)
    stage_id: JsonUUID | None = None
    configuration: Configuration

    @field_validator("name")
    @classmethod
    def sql_name(cls, value):
        if len(value.encode("utf-16-le")) > 200:
            raise ValueError("SQL UTF16 name length exceeded")
        return value


class StageWrite(Mutation):
    program_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=100)
    entry_rule: str = Field(min_length=1, max_length=1000)
    exit_rule: str = Field(min_length=1, max_length=1000)
    evidence_required: str = Field(min_length=1, max_length=1000)

    _sql_name = field_validator("name")(AgentWrite.sql_name.__func__)


class ReviewWrite(Mutation):
    note: str = Field(min_length=1, max_length=1000)
    confirmed: bool


class StateWrite(Mutation):
    state: Literal["active", "paused", "archived", "draft"]
    note: str = Field(default="", max_length=1000)
    confirmed: bool = True


class NoteWrite(Mutation):
    note: str = Field(min_length=1, max_length=1000)


class ActionWrite(Mutation):
    kind: Literal[
        "recommendation",
        "summary",
        "report",
        "campaign_draft",
        "followup_task",
        "crm_note",
    ]
    impact: Literal["low", "medium", "high"] = "medium"
    risk: Literal["low", "medium", "high"] = "medium"
    title: str = Field(min_length=1, max_length=120)
    context: str = Field(min_length=1, max_length=4000)
    conversation_id: JsonUUID | None = None


class ActionDecision(Mutation):
    action_id: JsonUUID
    decision: Literal["approve", "reject", "execute"]


class ReindexWrite(Mutation):
    pass


class ContextWrite(Mutation):
    program_id: int = Field(gt=0)
    applicant_id: int | None = Field(default=None, gt=0)
    period_id: int | None = Field(default=None, gt=0)
    stage_id: JsonUUID | None = None
    evidence: str = Field(min_length=1, max_length=1000)
    confirmed: bool


class AssignmentWrite(ReviewWrite):
    mode: Literal["automatic", "manual", "human"]
    agent_id: JsonUUID | None = None
    context_id: JsonUUID | None = None


class SimulationHistory(StrictModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=1600)


class SimulationRequest(StrictModel):
    agent_id: JsonUUID
    config_version: int = Field(ge=1)
    program_id: int | None = Field(default=None, gt=0)
    stage_id: JsonUUID | None = None
    question: str = Field(min_length=1, max_length=2000)
    history: list[SimulationHistory] = Field(default_factory=list, max_length=12)
    call_provider: bool = False
    acknowledge_consumption: bool = False
    request_id: JsonUUID
    channel: Literal["local", "whatsapp", "instagram", "facebook", "tiktok"] = "local"
    variant: Literal["current", "comparison"] = "current"
    provider_override: Literal["openrouter"] | None = None
    model_override: str | None = Field(default=None, max_length=200, pattern=r"^[A-Za-z0-9._:/-]+$")
    output_tokens_override: int | None = Field(default=None, ge=128, le=2000)
    skill_focus: Literal["opening", "discovery", "value", "negotiation", "closing", "review", "advertisement"] | None = None

    @model_validator(mode="after")
    def paired_simulation_route(self):
        if bool(self.provider_override) != bool(self.model_override):
            raise ValueError("simulation_route_incomplete")
        if self.output_tokens_override is not None and not self.provider_override:
            raise ValueError("simulation_route_required")
        return self


class SourceWrite(ReviewWrite):
    program_id: int | None = Field(default=None, gt=0)
    stage_id: JsonUUID | None = None
    owner: str = Field(min_length=1, max_length=100)
    valid_until: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")

    _sql_owner = field_validator("owner")(AgentWrite.sql_name.__func__)

    @model_validator(mode="after")
    def valid_date(self):
        date.fromisoformat(self.valid_until)
        return self


def validate_hierarchy(agent, agents, stages):
    parent = agents.get(agent.get("parent_id"))
    level = agent["level"]
    if level == "guide":
        if agent.get("parent_id") or agent.get("program_id") or agent.get("stage_id"):
            raise AiError("agents_invalid_guide")
    elif level == "program":
        if (
            not parent
            or parent["level"] != "guide"
            or not agent.get("program_id")
            or agent.get("stage_id")
        ):
            raise AiError("agents_invalid_program_parent")
    else:
        stage = stages.get(agent.get("stage_id"))
        if (
            not parent
            or parent["level"] != "program"
            or parent["program_id"] != agent.get("program_id")
            or not stage
            or stage["program_id"] != agent.get("program_id")
        ):
            raise AiError("agents_invalid_stage_parent")
    seen = {agent["id"]}
    while parent:
        if parent["id"] in seen:
            raise AiError("agents_hierarchy_cycle")
        seen.add(parent["id"])
        parent = agents.get(parent.get("parent_id"))


def chain_for(agent, agents):
    chain, seen = [], set()
    while agent:
        if agent["id"] in seen:
            raise AiError("agents_hierarchy_cycle")
        seen.add(agent["id"])
        chain.insert(0, agent)
        agent = agents.get(agent.get("parent_id"))
    return chain


def effective_configuration(chain, *, validate_variables=True):
    result = None
    for agent in chain:
        current = Configuration.model_validate_json(
            json.dumps(agent["configuration"])
        ).model_dump(mode="json")
        current["instructions"] = (
            render_instructions(agent, current, validate_variables)
            if current["customized"]
            else "Usa el nombre de atención configurado sin repetir presentaciones. Si preguntan si eres IA, responde con transparencia. Usa sólo las fuentes vigentes y deriva dudas sin evidencia o solicitudes humanas al equipo."
        )
        if result is not None:
            if (
                set(current["capabilities"]) - set(result["capabilities"])
                or set(current["channels"]) - set(result["channels"])
                or current["allow_reply"]
                and not result["allow_reply"]
                or current["allow_safe_actions"]
                and not result["allow_safe_actions"]
                or current["allow_crm_update"]
                and not result["allow_crm_update"]
                or not current["require_human_approval"]
                and result["require_human_approval"]
                or current["global_enabled"]
                and not result["global_enabled"]
            ):
                raise AiError("agents_child_permission_expansion", 409)
            if (
                result["monthly_token_limit"]
                and current["monthly_token_limit"] > result["monthly_token_limit"]
            ):
                raise AiError("agents_child_budget_expansion", 409)
            current["instructions"] = (
                result["instructions"] + "\n" + current["instructions"]
            )
            current["advisor_name"] = current["advisor_name"] or result["advisor_name"]
            current["sales_memory_enabled"] = current["sales_memory_enabled"] and result["sales_memory_enabled"]
            current["auto_sales_crm"] = current["auto_sales_crm"] and result["auto_sales_crm"]
            current["rules"] = [*result["rules"], *current["rules"]]
            current["objectives"] = [*result["objectives"], *current["objectives"]]
            current["max_tokens"] = min(result["max_tokens"], current["max_tokens"])
            current["document_ids"] = list(
                dict.fromkeys([*result["document_ids"], *current["document_ids"]])
            )
            current["memories"] = list(
                set(current["memories"]) & set(result["memories"])
            )
            current["industry_policies"] = list(
                dict.fromkeys(
                    [*result["industry_policies"], *current["industry_policies"]]
                )
            )
        result = current
    return result


def render_instructions(agent, configuration, validate_variables=True):
    """Render one profile once; descendants cannot rewrite ancestor variables."""
    variables = {
        **configuration["template_variables"],
        "agent_name": agent.get("name", ""),
        "agent_description": configuration["description"],
        "agent_specialty": {
            "guide": "orientación institucional",
            "program": "admisiones del programa confirmado",
            "stage": "atención de la etapa confirmada",
        }[agent["level"]],
        "program_id": str(agent.get("program_id") or "sin programa confirmado"),
    }

    def replace(match):
        key = match.group(1)
        if key not in variables:
            if validate_variables:
                raise AiError("agents_template_variable_missing", 409)
            return match.group(0)
        return variables[key]

    instructions = configuration["instructions"]
    if any(
        field in agent["configuration"]
        for field in ("instruction_template", "template_variables")
    ):
        instructions = re.sub(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", replace, instructions)
    if (
        not any(
            configuration[key]
            for key in ("description", "operating_style", "escalation_policy")
        )
        and configuration["risk_posture"] == "balanced"
    ):
        return instructions
    behavior = (
        "\nDescripción operativa: "
        + configuration["description"]
        + "\nEstilo operativo: "
        + configuration["operating_style"]
        + "\nPostura de riesgo: "
        + (
            "cautelosa; pide aclaración antes de recomendar cuando haya ambigüedad"
            if configuration["risk_posture"] == "cautious"
            else "equilibrada; orienta sólo con evidencia institucional suficiente"
        )
        + "\nCriterios adicionales de derivación humana: "
        + configuration["escalation_policy"]
    )
    return instructions + behavior


def resolve(
    agents,
    stages,
    assignment,
    context,
    channel,
    control="ai",
    simulation_id=None,
    require_active=False,
):
    """No keyword routing, state transitions or silent manual reassignment."""
    if control == "human" or assignment.get("mode") == "human":
        raise AiError("agents_human_control", 409)
    program_id = context.get("program_id") if context else None
    stage_id = context.get("stage_id") if context else None
    if stage_id and (
        stage_id not in stages
        or (not simulation_id or require_active)
        and not stages[stage_id]["approved"]
        or stages[stage_id]["program_id"] != program_id
    ):
        raise AiError("agents_stage_approval_required", 409)
    candidates = list(agents.values())
    if simulation_id:
        selected = agents.get(simulation_id)
        reason = "simulation_selected"
    elif assignment.get("mode") == "manual":
        selected = agents.get(assignment.get("agent_id"))
        reason = "manual_protected"
    else:
        level = "stage" if stage_id else "program" if program_id else "guide"
        found = [
            a
            for a in candidates
            if a["level"] == level
            and a.get("program_id") == program_id
            and a.get("stage_id") == stage_id
            and a["state"] == "active"
        ]
        if not found and level == "stage":
            found = [
                a
                for a in candidates
                if a["level"] == "program"
                and a.get("program_id") == program_id
                and a["state"] == "active"
            ]
        if len(found) != 1:
            raise AiError("agents_owner_unavailable_or_ambiguous", 409)
        selected, reason = (
            found[0],
            "confirmed_context" if program_id else "program_unconfirmed",
        )
    if not selected:
        raise AiError("agents_assignment_conflict", 409)
    validate_hierarchy(selected, agents, stages)
    if (
        selected["program_id"] != program_id
        and selected["level"] != "guide"
        or selected["level"] == "guide"
        and program_id
        or selected["level"] == "stage"
        and selected["stage_id"] != stage_id
    ):
        raise AiError("agents_assignment_conflict", 409)
    chain = chain_for(selected, agents)
    if (not simulation_id or require_active) and any(
        a["state"] != "active" or not a["enabled"] for a in chain
    ):
        raise AiError("agents_parent_or_agent_unavailable", 409)
    config = effective_configuration(chain)
    if channel not in config["channels"]:
        raise AiError("agents_channel_not_allowed", 409)
    supervisor = next((a["id"] for a in chain if a["level"] == "program"), None)
    binding = {
        "chain": [
            [a["id"], a["version"], a["state"], a["approved_version"], a["enabled"]]
            for a in chain
        ],
        "assignment": assignment,
        "context": context,
    }
    return {
        "agent_id": selected["id"],
        "version": selected["version"],
        "supervisor_id": supervisor,
        "reason": reason,
        "configuration": config,
        "binding": digest(binding),
        "chain_ids": [a["id"] for a in chain],
    }
