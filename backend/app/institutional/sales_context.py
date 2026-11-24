"""Commercial interest routing, separate from a confirmed academic Context."""

import json
import re
from difflib import SequenceMatcher

from app.institutional.agent_catalog import Catalog, normalized
from app.institutional.db import institution, rows
from app.modules.agents.domain import digest, resolve
from app.modules.ai.infrastructure.providers import AiError

STOP = set("a al de del el la los las y en un una para por programa programas tecnico tecnica laboral auxiliar quiero interesa informacion saber conocer estudiar curso me mi mis yo tu tus se es si no lo le les nos sobre como que ofrecen tienen".split())


def matches(programs, profiles, text):
    text = normalized(text)
    # An explicit change takes precedence over a program being declined.
    text = re.split(r"\b(?:prefiero|mejor quiero|ahora quiero|sino)\b", text)[-1]
    if re.search(r"\b(?:no quiero|no me interesa)\b", text):
        return []
    words = {word for word in re.findall(r"[a-z0-9]+", text) if len(word) >= 3} - STOP
    scores = []
    for p in programs:
        names = set(re.findall(r"[a-z0-9]+", normalized(p["name"]))) - STOP
        aliases = [normalized(v.strip()) for v in re.split(r"[,;\n]", profiles.get(p["program_id"], {}).get("aliases", "")) if v.strip()]
        exact_alias = any(len(alias) >= 3 and alias not in STOP and re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", text) for alias in aliases)
        score = sum(2 for word in words if word in names)
        if not score:
            score = sum(1 for word in words if len(word) >= 6 and any(
                len(name) >= 6 and abs(len(name) - len(word)) <= 2 and SequenceMatcher(None, word, name).ratio() >= .88 for name in names
            ))
        if exact_alias:
            score += 8
        if score:
            schedule = normalized(p.get("schedule") or "")
            if re.search(r"\b(?:noche|nocturna|nocturno)\b", text) and "nocturn" not in schedule:
                continue
            if re.search(r"\b(?:dia|diurna|diurno)\b", text) and "diurn" not in schedule:
                continue
            scores.append((score, p))
    if not scores:
        return []
    maximum = max(score for score, _ in scores)
    return [p for score, p in scores if score == maximum]


def interest(programs, profiles, history):
    for message in reversed(history):
        if message["Direction"] != "incoming":
            continue
        found = matches(programs, profiles, message["Body"])
        if found:
            return {"program_id": found[0]["program_id"] if len(found) == 1 else None,
                    "candidates": [{k: v.get(k) for k in ("program_id", "name", "schedule")} for v in found],
                    "source_message_id": str(message["MessageId"]), "sequence": message["Sequence"],
                    "status": "declared_interest" if len(found) == 1 else "needs_clarification", "academic_confirmation": False}
        if re.search(r"\b(?:no quiero|no me interesa|otro programa|cambiar de programa)\b", normalized(message["Body"])):
            return {"program_id": None, "candidates": [], "status": "needs_clarification", "academic_confirmation": False,
                    "sequence": message["Sequence"], "source_message_id": str(message["MessageId"])}
    return None


def history(c, conversation, sequence=None, limit=80):
    boundary = getattr(c, "context_cutoff", lambda _: 0)(conversation)
    messages = list(reversed(rows(c,
        f"SELECT TOP({int(limit)}) MessageId,Direction,Body,Sequence,CreatedAt FROM crm.Message WHERE ConversationId=? "
        + ("AND Sequence>? " if boundary else "")
        + ("AND Sequence<=? " if sequence is not None else "") + "ORDER BY Sequence DESC",
        conversation, *((boundary,) if boundary else ()), *((sequence,) if sequence is not None else ()))))
    return getattr(c, "audio_history", lambda _, values: values)(conversation, messages)


def catalog_data(c, settings):
    programs = [p for p in Catalog(settings).programs(c, 0, 300)["items"] if p["authority"] != "synthetic_demo"]
    values = rows(c, "SELECT Section,Document FROM crm_access.Setting WHERE InstitutionId=? AND Section LIKE 'program-commercial-%'", institution(settings))
    profiles = {int(v["Section"].split("program-commercial-")[-1]): json.loads(v["Document"])
                for v in values if v["Section"].split("program-commercial-")[-1].isdigit()}
    return programs, profiles


def configure(c, settings):
    from app.institutional.institution_contacts import directory, sources
    c.public_contact_context = lambda: directory(c, settings)
    c.public_contact_sources = lambda: sources(directory(c, settings))
    from app.institutional.conversation_scope import configure as configure_scope
    configure_scope(c, settings)
    c.agent_catalog = Catalog(settings)
    from app.institutional.sales_contact import personalization
    c.contact_personalization = lambda conversation, sequence: personalization(c, settings, conversation, sequence)

    def commercial(agents, stages, assignment, channel, conversation):
        guides = [a for a in agents.values() if a["level"] == "guide" and a["state"] == "active" and a["enabled"]]
        if len(guides) != 1 or not guides[0]["configuration"].get("sales_routing_enabled"):
            return None
        programs, profiles = catalog_data(c, settings)
        # Bind only to incoming messages: our queued reply cannot change its own route.
        seq = c.execute("SELECT COALESCE(MAX(Sequence),0) FROM crm.Message WHERE ConversationId=? AND Direction='incoming'", conversation).fetchval()
        messages = history(c, conversation, seq)
        detected = interest(programs, profiles, messages)
        from app.institutional.broadcast_conversation import origin as campaign_origin
        campaign = campaign_origin(c, settings, conversation, messages)
        if campaign:
            topic = matches(programs, profiles, campaign.pop("routing_text"))
            found = matches(programs, profiles, campaign["program_hint"] + " " + campaign["schedule_hint"])
            if topic:
                overlap = [p for p in found if p in topic]
                found = overlap or topic
            if len(found) == 1 and (not detected or campaign["sequence"] > detected.get("sequence", 0)):
                detected = {"program_id": found[0]["program_id"], "candidates": found,
                            "status": "campaign_reply_context", "academic_confirmation": False,
                            "source_message_id": campaign["source_message_id"], "sequence": campaign["sequence"]}
        from app.institutional.sales_referrals import origin
        referral = origin(c, settings, conversation, seq)
        if referral and referral.get("sequence", 0) <= c.context_cutoff(conversation):
            referral = None
        if referral and referral.get("program_id") and (not detected or referral["sequence"] > detected.get("sequence", 0)):
            matched = next((p for p in programs if p["program_id"] == referral["program_id"]), None)
            if matched:
                detected = {"program_id": matched["program_id"], "candidates": [matched],
                            "status": "ad_program_mapping", "academic_confirmation": False,
                            "source_message_id": referral["source_message_id"], "sequence": referral["sequence"]}
        if not detected or not detected.get("program_id"):
            value = resolve(agents, stages, assignment, None, channel)
        else:
            try:
                value = resolve(agents, stages, assignment, {"program_id": detected["program_id"], "stage_id": None}, channel)
            except AiError as error:
                if error.code not in {"agents_owner_unavailable_or_ambiguous", "agents_parent_or_agent_unavailable", "agents_channel_not_allowed"}:
                    raise
                value = resolve(agents, stages, assignment, None, channel)
                detected = {**detected, "specialist_unavailable": True}
        value["commercial_interest"] = detected
        value["ad_referral"] = referral
        value["campaign_reply"] = campaign
        value["binding"] = digest([value["binding"], detected, referral, campaign, seq])
        value["reason"] = "commercial_interest" if detected and detected.get("program_id") and not detected.get("specialist_unavailable") else "commercial_clarification"
        return value

    c.agent_commercial_resolution = commercial
