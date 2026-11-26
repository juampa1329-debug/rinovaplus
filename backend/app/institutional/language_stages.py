"""Central model inheritance; program skills and authority remain on the agent."""

import json

from app.institutional.db import one
from app.modules.ai.domain.resilience import LanguageResilience
from app.modules.agents.domain import digest


def policy(document):
    return LanguageResilience.model_validate(document.get("language_resilience", {}))


def stage(c, conversation):
    if not conversation:
        return None
    person = one(c, "SELECT p.Stage FROM crm.Conversation v JOIN crm.Contact p ON "
                 "p.ContactId=COALESCE((SELECT TargetContactId FROM crm_workspace.Merge "
                 "WHERE SourceContactId=v.ContactId AND Active=1),v.ContactId) "
                 "WHERE v.ConversationId=?", conversation)
    config = one(c, "SELECT Document,Revision FROM crm_config.Configuration WHERE ConfigurationId=1")
    if not person or not config:
        return None
    current = next((s for s in json.loads(config["Document"]).get("stages", [])
                    if s.get("active", True) and person["Stage"] in (s["key"], s["label"])), None)
    return {"key": current["key"] if current else None, "revision": config["Revision"]}


def choose(value, turn=None, crm_stage=None):
    if not value.enabled or not value.primary:
        return None, None
    phase = (turn or {}).get("turn_plan", {}).get("phase")
    # The current question/whole pending turn overrides an early CRM stage.
    # Missing context and objections never downgrade to an opening model.
    opening = bool(value.opening and crm_stage and crm_stage.get("key") in value.opening_stage_keys
                   and phase in {"orientation", "specific_information", "value_alignment"}
                   and not {"pricing", "objection", "comparison", "decision", "decision_support", "followup", "escalation"}.intersection((turn or {}).get("reasons", [])))
    return (value.opening if opening else value.primary), {
        "source": "institutional_language_policy", "stage": (crm_stage or {}).get("key"),
        "phase": phase, "route": "opening" if opening else "commercial",
    }


def configuration(config, route, backup=None, max_tokens=None):
    result = {**config, **route.model_dump(), "primary_model": route.model,
              "fallback_model": backup.model if backup else "",
              "fallback_provider": backup.provider if backup else None,
              "fallback_input_usd_per_million": backup.input_usd_per_million if backup else None,
              "fallback_output_usd_per_million": backup.output_usd_per_million if backup else None}
    result.pop("model", None)
    if max_tokens is not None:
        result["max_tokens"] = max_tokens
    return result


def compose(c, selected, configured, conversation=None):
    # Explicit P22 trials retain their exact model and do not alter production.
    if "trial_temperature_supported" in selected:
        return
    value = policy(configured["document"])
    route, trace = choose(value, getattr(c, "agent_turn_policy", None), stage(c, conversation) if value.opening else None)
    if route:
        backup = value.primary if route != value.primary else next(iter(value.routes), None)
        selected["configuration"] = configuration(selected["configuration"], route, backup, value.reply_max_tokens)
        selected["language_routing"] = trace
        selected["binding"] = digest([selected.get("binding"), route.model_dump(), trace])
