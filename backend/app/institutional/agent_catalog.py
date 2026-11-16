"""Declared CRM program catalog; never impersonates an official SIIE record."""

from uuid import NAMESPACE_URL, uuid5

from app.institutional.db import institution, rows, one
from app.institutional.program_commercial import agent_facts, read_profile
from app.modules.agents.domain import digest
from app.modules.ai.infrastructure.providers import AiError


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
        catalog = self.programs(c, 0, 300)
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
        return {
            "material": {
                "period": None,
                "selected": selected,
                "program_catalog": catalog["items"],
                "authority": catalog["authority"],
                "academic_writes_allowed": False,
            },
            "sources": sources,
            "fingerprint": digest([catalog, selected]),
            "authority": catalog["authority"],
        }
