"""Reviewed, atomic provisioning of the institutional program specialists."""

from uuid import NAMESPACE_URL, uuid5

from fastapi import HTTPException
from pydantic import Field

from app.institutional import db
from app.institutional.auth import authorize
from app.institutional.policy import request_authority
from app.institutional.sales_context import catalog_data
from app.modules.agents.domain import AgentWrite, Configuration, JsonUUID, Mutation, digest
from app.modules.agents.generation import provider_options
from app.modules.agents.sales_skills import IDS, VERSION, catalog, specialist_instructions
from app.modules.agents.service import load, preflight
from app.institutional.models import Strict


class Provision(Strict):
    operation_id: JsonUUID
    guide_id: JsonUUID
    preview_digest: str = Field(min_length=64, max_length=64)
    confirmed: bool


class AdLink(Strict):
    ad_id: str = Field(pattern=r"^[0-9]{1,40}$")
    program_id: int = Field(gt=0)


class AdLinksWrite(Mutation):
    items: list[AdLink] = Field(max_length=1000)


class ResetContext(Mutation):
    sequence: int = Field(ge=0)
    confirmed: bool
    action: str = Field(default="reset", pattern="^(reset|restore)$")


def preview(c, settings, guide_id):
    agents, stages = load(c)
    root = agents.get(str(guide_id))
    if not root or root["level"] != "guide" or root["state"] != "active" or not root["enabled"]:
        raise HTTPException(409, "sales_active_guide_required")
    if not preflight(c, root, agents, stages)["ready"]:
        raise HTTPException(409, "sales_guide_not_ready")
    programs, profiles = catalog_data(c, settings)
    items = []
    for p in programs:
        existing = [a for a in agents.values() if a["level"] == "program" and a["program_id"] == p["program_id"] and a["state"] != "archived"]
        if len(existing) > 1:
            raise HTTPException(409, "sales_specialist_ambiguous")
        profile = profiles.get(p["program_id"], {})
        items.append({"program_id": p["program_id"], "name": p["name"], "school": p["school"], "schedule": p["schedule"],
                      "program_revision": p["revision"], "agent_id": existing[0]["id"] if existing else str(uuid5(NAMESPACE_URL, "rinovaplus-sales:" + db.institution(settings) + ":" + str(p["program_id"]))),
                      "action": "preserve" if existing else "create", "agent_revision": existing[0]["revision"] if existing else 0,
                      "missing": [key for key in ("duration", "requirements", "syllabus", "source_url") if not profile.get(key)],
                      "price_pending": profile.get("price_cop") is None and profile.get("full_cost_cash_cop") is None,
                      "system_prompt": specialist_instructions(p)})
    value = {"guide_id": root["id"], "guide_revision": root["revision"], "guide_name": root["name"],
             "provider": root["configuration"]["provider"], "model": root["configuration"]["primary_model"],
             "items": items, "skills": catalog(), "skills_version": VERSION,
             "guide_changes": [f"{len(IDS)} skills revisadas por política central", "derivación comercial", "memoria privada por hilo", "calificación comercial automática con evidencia"],
             "academic_writes": False, "network_called": False}
    return {**value, "digest": digest(value)}


def install(app, service, settings):
    from app.institutional.sales_style import install as install_style
    install_style(app, service, settings, Provision)
    from app.institutional.sales_recovery import install as install_recovery
    install_recovery(app, service, settings)
    @app.get("/api/v1/agents/sales/ad-links")
    def ad_links():
        from app.institutional.sales_referrals import links
        with service.transaction() as c:
            return links(c, settings)

    @app.put("/api/v1/agents/sales/ad-links")
    def save_ad_links(body: AdLinksWrite):
        from app.institutional.sales_referrals import links
        with service.transaction(True) as c:
            checksum, prior = db.replay(c, settings, c.agent_user, str(body.operation_id), "agents.sales-ad-links", "catalog", body.model_dump(mode="json"))
            if prior:
                return prior
            current = links(c, settings)
            if body.revision != current["revision"]:
                raise HTTPException(409, "sales_preview_changed")
            programs, _ = catalog_data(c, settings)
            if len({v.ad_id for v in body.items}) != len(body.items) or any(v.program_id not in {p["program_id"] for p in programs} for v in body.items):
                raise HTTPException(422, "sales_ad_binding_invalid")
            import json
            payload = json.dumps({"items": [v.model_dump() for v in body.items]})
            if current["revision"]:
                c.execute("UPDATE crm_access.Setting SET Document=?,Revision=Revision+1,UpdatedAt=SYSUTCDATETIME(),UpdatedBy=? WHERE InstitutionId=? AND Section='sales-ad-links' AND Revision=?", payload, c.agent_user, db.institution(settings), body.revision)
            else:
                c.execute("INSERT crm_access.Setting(InstitutionId,Section,Document,Revision,UpdatedAt,UpdatedBy) VALUES(?,'sales-ad-links',?,1,SYSUTCDATETIME(),?)", db.institution(settings), payload, c.agent_user)
            c.execute("INSERT crm_access.SettingHistory(InstitutionId,Section,Revision,Document,RecordedAt,ActorId) VALUES(?,'sales-ad-links',?,?,SYSUTCDATETIME(),?)", db.institution(settings), body.revision + 1, payload, c.agent_user)
            result = {"saved": True, "revision": body.revision + 1, "meta_written": False}
            db.record_operation(c, settings, c.agent_user, str(body.operation_id), "agents.sales-ad-links", "catalog", checksum, result)
            return result

    @app.get("/api/v1/agents/sales/skills")
    def skills():
        with service.transaction():
            return {"version": VERSION, "items": catalog(), "authority": "backend_required", "selection": "per_turn_relevance"}

    @app.get("/api/v1/agents/sales/preview")
    def prepare(guide_id: str):
        with service.transaction() as c:
            return preview(c, settings, db.uid(guide_id))

    @app.post("/api/v1/agents/sales/provision")
    def provision(body: Provision):
        if not body.confirmed:
            raise HTTPException(422, "sales_review_required")
        options = provider_options(service.ai)
        with service.transaction(True) as c:
            authority = request_authority.get()
            actor = authorize(c, settings, authority, "crm.write")
            authorize(c, settings, authority, "inbox.write")
            checksum, prior = db.replay(c, settings, actor["UserId"], str(body.operation_id), "agents.sales-provision", str(body.guide_id), body.model_dump(mode="json"))
            if prior:
                return prior
            plan = preview(c, settings, str(body.guide_id))
            if plan["digest"] != body.preview_digest:
                raise HTTPException(409, "sales_preview_changed")
            agents, _ = load(c)
            root = agents[str(body.guide_id)]
            config = Configuration.model_validate({**root["configuration"], "sales_skill_ids": sorted(IDS), "sales_routing_enabled": True, "sales_memory_enabled": True, "auto_sales_crm": True})
            service.save_agent(root["id"], AgentWrite(operation_id=uuid5(body.operation_id, "guide"), revision=root["revision"],
                               name=root["name"], level="guide", configuration=config), _cursor=c, _options=options)
            created = []
            for item in plan["items"]:
                if item["action"] != "create":
                    continue
                child = config.model_copy(update={"instructions": item["system_prompt"], "description": "Asesor especializado del catálogo institucional",
                    "voice_profile_id": "", "global_enabled": False, "instruction_template": "custom", "template_variables": {},
                    "ab_enabled": False, "ab_compare_version": None})
                label = (item["name"][:70] + (" · " + item["schedule"][:15] if item["schedule"] else "") + " · " + str(item["program_id"]))[:100]
                service.save_agent(item["agent_id"], AgentWrite(operation_id=uuid5(body.operation_id, str(item["program_id"])), revision=0,
                                   name=label, level="program", parent_id=body.guide_id, program_id=item["program_id"], configuration=child), _cursor=c, _options=options)
                created.append(item["agent_id"])
            result = {"saved": True, "created": len(created), "preserved": len(plan["items"]) - len(created), "agent_ids": created,
                      "academic_writes": False, "network_called": False, "skills_version": VERSION}
            db.record_operation(c, settings, actor["UserId"], str(body.operation_id), "agents.sales-provision", str(body.guide_id), checksum, result)
            db.audit(c, settings, actor["UserId"], "agents.sales-provision", str(body.guide_id), count=len(created), version=VERSION)
            return result

    @app.get("/api/v1/agents/conversations/{conversation}/sales-memory")
    def memory(conversation: str):
        from app.institutional.sales_memory import graph
        key = db.uid(conversation)
        with service.transaction() as c:
            if not c.execute("SELECT 1 FROM crm.Conversation WHERE ConversationId=?", key).fetchone():
                raise HTTPException(404, "conversation_not_found")
            return graph(c, settings, key)

    @app.post("/api/institution/conversation-memory/{conversation}/reset")
    @app.post("/api/v1/agents/conversations/{conversation}/sales-memory/reset")
    def reset_memory(conversation: str, body: ResetContext):
        from app.institutional.sales_memory import read, save
        key = db.uid(conversation)
        if not body.confirmed:
            raise HTTPException(422, "sales_context_reset_review_required")
        with service.transaction(True) as c:
            actor = authorize(c, settings, request_authority.get(), "inbox.write", recent=True)
            checksum, prior = db.replay(c, settings, actor["UserId"], str(body.operation_id), "sales.context-reset", key, body.model_dump(mode="json"))
            if prior:
                return prior
            control = db.one(c, "SELECT v.ControlMode,ctrl.Epoch FROM crm.Conversation v JOIN crm_channels.ConversationControl ctrl ON ctrl.ConversationId=v.ConversationId WHERE v.ConversationId=?", key)
            if not control:
                raise HTTPException(404, "conversation_not_found")
            latest = c.execute("SELECT COALESCE(MAX(Sequence),0) FROM crm.Message WHERE ConversationId=?", key).fetchval()
            previous, revision = read(c, settings, key)
            if revision != body.revision or latest != body.sequence:
                raise HTTPException(409, "sales_context_reset_changed")
            if body.action == "restore":
                document = previous.get("previous_context")
                if not isinstance(document, dict):
                    raise HTTPException(409, "sales_context_restore_unavailable")
            else:
                document = {"conversation_id": key, "observations": [], "turns": [],
                            "source_sequence": latest, "reset_after_sequence": latest,
                            "previous_context": {k: v for k, v in previous.items() if k != "previous_context"}}
                # Operational provenance is not conversational memory. Keep it
                # so a prior automatic CRM score does not become a manual one.
                if previous.get("last_auto_assessment"):
                    document["last_auto_assessment"] = previous["last_auto_assessment"]
            save(c, settings, key, document, revision)
            c.execute("UPDATE crm_channels.ConversationControl SET Epoch=Epoch+1 WHERE ConversationId=? AND Epoch=?", key, control["Epoch"])
            if c.rowcount != 1:
                raise HTTPException(409, "sales_context_reset_changed")
            c.execute("UPDATE crm_workspace.State SET Revision=Revision+1 WHERE StateId=1")
            result = {"saved": True, "revision": revision + 1, "action": body.action,
                      "messages_deleted": False, "voice_usage_reset": False,
                      "control_mode": control["ControlMode"]}
            db.record_operation(c, settings, actor["UserId"], str(body.operation_id), "sales.context-reset", key, checksum, result)
            db.audit(c, settings, actor["UserId"], "sales.context-reset", key, reason=body.action)
            return result
