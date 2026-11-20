"""Declared CRM program catalog; never impersonates an official SIIE record."""

from uuid import NAMESPACE_URL, uuid5
import json
import re
import unicodedata

from app.institutional.db import institution, rows, one
from app.institutional.program_commercial import agent_facts, read_profile
from app.modules.agents.domain import digest
from app.modules.ai.infrastructure.providers import AiError


def normalized(value):
    return "".join(c for c in unicodedata.normalize("NFKD", value.lower()) if not unicodedata.combining(c))


def relevant_programs(items, profiles, question):
    words = set(re.findall(r"[a-z0-9]+", normalized(question))) - {
        "programa", "programas", "tecnico", "tecnica", "laboral", "auxiliar", "de", "en", "y", "el", "la", "del", "los",
        "a", "al", "las", "un", "una", "unos", "unas", "me", "mi", "mis", "se", "su", "sus",
        "con", "sin", "por", "para", "que", "como", "cuanto", "cuantos", "cual", "cuales",
    }
    ranked = []
    for item in items:
        profile = profiles.get(item["program_id"], {})
        names = normalized(item["name"] + " " + profile.get("aliases", ""))
        score = len(words & set(re.findall(r"[a-z0-9]+", names)))
        if score:
            ranked.append((score, item, words & set(re.findall(r"[a-z0-9]+", names))))
    # A shared word such as Diurna or Bartender must not retrieve an unrelated
    # or duplicate full profile when another match covers those words plus more.
    ranked = [entry for entry in ranked if not any(entry[2] < other[2] for other in ranked)]
    return [item for _, item, _ in sorted(ranked, key=lambda pair: (-pair[0], pair[1]["program_id"]))[:6]]


def bounded_commercial_context(selected, informational, limit=20_000):
    """Keep whole financial facts; never cut a quote or payment condition midway.

    Other matches may be catalog-only when their complete profiles do not fit.
    The selected profile has priority and is not repeated in queried_programs.
    """
    used = len(json.dumps(selected, ensure_ascii=False)) if selected else 0
    if used > limit:
        raise AiError("admissions_context_limit", 413)
    bounded = []
    for item in informational:
        if selected and item["program_id"] == selected["program_id"]:
            bounded.append({k: v for k, v in item.items() if k != "commercial"})
            bounded[-1]["commercial_in_selected"] = True
            continue
        size = len(json.dumps(item, ensure_ascii=False))
        if used + size <= limit:
            bounded.append(item)
            used += size
        else:
            compact = {k: v for k, v in item.items() if k != "commercial"}
            compact["commercial_details_omitted"] = True
            compact["context_guidance"] = (
                "El programa existe en el catálogo, pero su ficha comercial completa no cabe en esta consulta. "
                "Pide concretar ese programa para consultar sus condiciones; no inventes ni extrapoles tarifas, "
                "becas o materias de otro programa."
            )
            bounded.append(compact)
    return selected, bounded


class Catalog:
    def __init__(self, settings):
        self.settings = settings

    def programs(self, c, offset=0, limit=150):
        total = c.execute(
            "SELECT COUNT(*) FROM crm_agents5.Program WHERE InstitutionId=? AND Active=1",
            institution(self.settings),
        ).fetchval()
        values = rows(
            c,
            "SELECT * FROM crm_agents5.Program WHERE InstitutionId=? AND Active=1 "
            "ORDER BY ProgramId OFFSET ? ROWS FETCH NEXT ? ROWS ONLY",
            institution(self.settings),
            offset,
            limit,
        )
        return {
            "period": {
                "id": 0,
                "name": "Catálogo CRM declarado",
                "starts_at": None,
                "ends_at": None,
            },
            "items": [
                {
                    "offering_id": v["ProgramId"],
                    "program_id": v["ProgramId"],
                    "name": v["Name"],
                    "code": str(v["ProgramId"]),
                    "semesters": None,
                    "modality": "",
                    "schedule": v["Schedule"],
                    "school": v["School"],
                    "authority": v["Authority"],
                    "revision": v["Revision"],
                }
                for v in values
            ],
            "total": total,
            "has_more": offset + len(values) < total,
            "offset": offset,
            "authority": "declared_CRM_catalog_not_verified_SIIE",
        }

    def read_context(self, c, question, program_id=None, semester=None):
        from app.modules.agents.skill_policy import for_turn, project_facts
        skill_policy = getattr(c, "agent_turn_policy", None) or for_turn(question)
        catalog = self.programs(c, 0, 300)
        if getattr(self.settings, "postgres_deployment", False):
            catalog["items"] = [v for v in catalog["items"] if v["authority"] != "synthetic_demo"]
        profiles = rows(c, "SELECT Section,Document FROM crm_access.Setting "
                        "WHERE InstitutionId=? AND Section LIKE 'program-commercial-%'", institution(self.settings))
        commercial_profiles = {
            int(v["Section"].removeprefix("program-commercial-")): json.loads(v["Document"])
            for v in profiles if v["Section"].removeprefix("program-commercial-").isdigit()
        }
        informational = []
        for value in relevant_programs(catalog["items"], commercial_profiles, question):
            if getattr(self.settings, "postgres_deployment", False) and value["authority"] == "synthetic_demo":
                continue
            informational.append({**value, "commercial": agent_facts(commercial_profiles.get(value["program_id"]))})
        selected = None
        if program_id is not None:
            row = one(
                c,
                "SELECT * FROM crm_agents5.Program WHERE InstitutionId=? AND ProgramId=? AND Active=1",
                institution(self.settings),
                program_id,
            )
            selected = (
                {
                    "program_id": row["ProgramId"],
                    "name": row["Name"],
                    "school": row["School"],
                    "schedule": row["Schedule"],
                    "revision": row["Revision"],
                    "authority": row["Authority"],
                }
                if row
                else None
            )
            if selected is None:
                raise AiError("institutional_program_not_in_active_offer", 409)
            commercial = agent_facts(read_profile(c, self.settings, program_id))
            if commercial:
                selected["commercial"] = commercial
        fingerprint = digest([catalog, selected, informational, skill_policy])
        selected = project_facts(selected, skill_policy)
        informational = project_facts(informational, skill_policy)
        selected, informational = bounded_commercial_context(selected, informational)
        # Never infer assignment/program from the question, names or phone.
        sources = []
        if selected:
            reference = str(
                uuid5(
                    NAMESPACE_URL,
                    "cbn-declared-program:"
                    + institution(self.settings)
                    + ":"
                    + str(program_id),
                )
            )
            sources.append(
                {
                    "id": reference,
                    "title": "Programa declarado en CRM: " + selected["name"],
                    "text": "Información comercial revisada en el CRM; el expediente académico corresponde a SIIE: "
                    + str(selected),
                    "source_kind": "declared_CRM_catalog",
                    "revision": selected["revision"],
                    "synthetic_demo": selected["authority"] == "synthetic_demo",
                }
            )
        for value in informational:
            if selected and value["program_id"] == selected["program_id"]:
                continue
            sources.append({
                "id": str(uuid5(NAMESPACE_URL, "cbn-declared-program:" + institution(self.settings) + ":" + str(value["program_id"]))),
                "title": "Consulta informativa de programa CRM: " + value["name"],
                "text": json.dumps(value, ensure_ascii=False),
                "source_kind": "declared_CRM_catalog", "revision": value["revision"],
                "synthetic_demo": value["authority"] == "synthetic_demo",
            })
        return {
            "material": {
                "period": None,
                "selected": selected,
                "program_catalog": catalog["items"],
                "queried_programs": informational,
                "query_does_not_confirm_assignment": True,
                "catalog_has_more": catalog["has_more"],
                "authority": catalog["authority"],
                "academic_writes_allowed": False,
            },
            "sources": sources,
            "fingerprint": fingerprint,
            "authority": catalog["authority"],
        }
