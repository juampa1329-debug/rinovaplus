"""Reviewed replacement of generated prompts; customized specialists are retained."""

from fastapi import HTTPException

from app.institutional import db
from app.institutional.cbn_profile import general_instructions, recommended_delivery
from app.institutional.sales_context import catalog_data
from app.modules.agents.conversation_style import VERSION
from app.modules.agents.domain import AgentWrite, Configuration, digest
from app.modules.agents.generation import provider_options
from app.modules.agents.sales_skills import (
    specialist_instructions,
    legacy_specialist_instructions,
)
from app.modules.agents.service import load
from uuid import uuid5


def preview(c, settings, guide_id):
    agents, _ = load(c)
    root = agents.get(str(guide_id))
    if not root or root["level"] != "guide" or root["state"] == "archived":
        raise HTTPException(409, "sales_active_guide_required")
    programs, _ = catalog_data(c, settings)
    programs = {p["program_id"]: p for p in programs}
    family = {root["id"]}
    while True:
        found = {a["id"] for a in agents.values() if a.get("parent_id") in family}
        if found <= family:
            break
        family |= found
    items = []
    for agent in sorted(
        (a for a in agents.values() if a["id"] in family and a["state"] != "archived"),
        key=lambda a: (a["level"] != "guide", a["name"]),
    ):
        config = agent["configuration"]
        old = config.get("instructions", "")
        program = programs.get(agent.get("program_id"))
        name = config.get("advisor_name") or "Juan"
        owned = agent["id"] == root["id"] or bool(
            program
            and old
            in {
                legacy_specialist_instructions(program),
                specialist_instructions(program),
                specialist_instructions(program).replace(
                    "Eres Juan,", "Eres " + name + ",", 1
                ),
            }
        )
        prompt = (
            (
                general_instructions()
                if agent["id"] == root["id"]
                else specialist_instructions(program)
            )
            if owned
            else old
        )
        prompt = (
            prompt.replace("Eres Juan,", "Eres " + name + ",", 1) if owned else prompt
        )
        items.append(
            {
                "agent_id": agent["id"],
                "agent_revision": agent["revision"],
                "program_id": agent.get("program_id"),
                "name": agent["name"],
                "school": program["school"] if program else "Institucional",
                "schedule": program["schedule"] if program else "",
                "system_prompt": prompt,
                "advisor_name": name,
                "action": "update"
                if owned and (old != prompt or config.get("advisor_name") != name)
                else "preserve",
                "custom_prompt_preserved": not owned,
                "missing": [],
                "price_pending": True,
                "configuration_digest": digest(config),
            }
        )
    result = {
        "mode": "style",
        "guide_id": root["id"],
        "guide_name": root["name"],
        "provider": root["configuration"]["provider"],
        "model": root["configuration"]["primary_model"],
        "guide_changes": [
            "nombre de atención editable",
            "tono colombiano profesional",
            "prompts completos sin bienvenida repetida",
            "transparencia si preguntan por IA",
        ],
        "items": items,
        "global_system_prompt": general_instructions(),
        "recommended_delivery": recommended_delivery(),
        "style_version": VERSION,
    }
    return {**result, "digest": digest(result)}


def install(app, service, settings, mutation_type):
    @app.get("/api/v1/agents/sales/style-preview")
    def prepare(guide_id: str):
        with service.transaction() as c:
            return preview(c, settings, db.uid(guide_id))

    @app.post("/api/v1/agents/sales/style")
    def apply(body: mutation_type):
        if not body.confirmed:
            raise HTTPException(422, "sales_review_required")
        options = provider_options(service.ai)
        with service.transaction(True) as c:
            checksum, prior = db.replay(
                c,
                settings,
                c.agent_user,
                str(body.operation_id),
                "agents.sales-style",
                str(body.guide_id),
                body.model_dump(mode="json"),
            )
            if prior:
                return prior
            plan = preview(c, settings, str(body.guide_id))
            if plan["digest"] != body.preview_digest:
                raise HTTPException(409, "sales_preview_changed")
            agents, _ = load(c)
            updated = []
            for item in plan["items"]:
                if item["action"] != "update":
                    continue
                agent = agents[item["agent_id"]]
                config = Configuration.model_validate(
                    {
                        **agent["configuration"],
                        "instructions": item["system_prompt"],
                        "advisor_name": item["advisor_name"],
                        "tone": "Colombiano, cercano y profesional; ideas breves completas, emojis discretos.",
                    }
                )
                service.save_agent(
                    agent["id"],
                    AgentWrite(
                        operation_id=uuid5(body.operation_id, agent["id"]),
                        revision=agent["revision"],
                        name=agent["name"],
                        level=agent["level"],
                        parent_id=agent.get("parent_id"),
                        program_id=agent.get("program_id"),
                        stage_id=agent.get("stage_id"),
                        configuration=config,
                    ),
                    _cursor=c,
                    _options=options,
                )
                updated.append(agent["id"])
            result = {
                "saved": True,
                "updated": len(updated),
                "preserved": len(plan["items"]) - len(updated),
                "style_version": VERSION,
                "settings_ai_changed": False,
            }
            db.record_operation(
                c,
                settings,
                c.agent_user,
                str(body.operation_id),
                "agents.sales-style",
                str(body.guide_id),
                checksum,
                result,
            )
            db.audit(
                c,
                settings,
                c.agent_user,
                "agents.sales-style",
                str(body.guide_id),
                count=len(updated),
                version=VERSION,
            )
            return result
