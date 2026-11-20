import json
from types import SimpleNamespace
from uuid import uuid4

from app.institutional import agent_catalog
from app.modules.ai.application.admissions_prompt import AdmissionsPolicy, assemble_prompt


def test_pronouns_and_articles_do_not_match_program_abbreviations():
    programs = [
        {"program_id": 1, "name": "BARISMO Y BARTENDER"},
        {"program_id": 2, "name": "MANTENIMIENTO ELECTRONICO"},
        {"program_id": 3, "name": "ATENCION A LA INFANCIA"},
    ]
    profiles = {2: {"aliases": "ME"}}
    result = agent_catalog.relevant_programs(
        programs, profiles, "¿Me dan información para Barismo y Bartender, con una beca?"
    )
    assert result == [programs[0]]


def test_large_comparisons_keep_selected_financing_whole_and_mark_omissions(monkeypatch):
    programs = [
        {"program_id": i, "name": f"Especialidad{i}", "school": "Escuela",
         "schedule": "Diurna", "authority": "declared_CRM_catalog", "revision": 1}
        for i in range(1, 7)
    ]
    profiles = {
        p["program_id"]: {
            "presentation": "Presentación institucional. " * 65,
            "syllabus": "Contenido académico. " * 100,
            "requirements": "Requisito documentado. " * 60,
            "financial_plans": [{
                "external_id": f"plan-{p['program_id']}",
                "initial_payment_cop": 100,
                "total_cost_cop": 200,
                "installments": [{"number": 1, "amount_cop": 100, "due_date": None}],
                "conditions": "Condición completa sin cortar. " * 60,
                "valid_from": None, "valid_until": None,
            }],
        }
        for p in programs
    }
    catalog = agent_catalog.Catalog(SimpleNamespace(
        postgres_deployment=True, ticket={"context": [[1, str(uuid4())]]},
    ))
    monkeypatch.setattr(catalog, "programs", lambda *_: {
        "items": programs, "has_more": False, "authority": "declared_CRM_catalog",
    })
    monkeypatch.setattr(agent_catalog, "rows", lambda *_: [
        {"Section": f"program-commercial-{i}", "Document": json.dumps(p)}
        for i, p in profiles.items()
    ])
    monkeypatch.setattr(agent_catalog, "one", lambda *_: {
        "ProgramId": 1, "Name": "Especialidad1", "School": "Escuela",
        "Schedule": "Diurna", "Revision": 1, "Authority": "declared_CRM_catalog",
    })
    monkeypatch.setattr(agent_catalog, "read_profile", lambda *_: profiles[1])
    question = "Compara precios y condiciones de financiación de " + " y ".join(p["name"] for p in programs)
    context = catalog.read_context(object(), question, 1)
    material = context["material"]
    assert material["selected"]["commercial"]["financial_plans"] == profiles[1]["financial_plans"]
    own = next(p for p in material["queried_programs"] if p["program_id"] == 1)
    assert own["commercial_in_selected"] and "commercial" not in own
    omitted = [p for p in material["queried_programs"] if p.get("commercial_details_omitted")]
    assert omitted and all("commercial" not in p for p in omitted)
    for p in material["queried_programs"]:
        if "commercial" in p:
            assert p["commercial"]["financial_plans"] == profiles[p["program_id"]]["financial_plans"]
    messages = assemble_prompt(
        AdmissionsPolicy(system_prompt="Instrucciones revisadas. " * 230),
        question, {}, context["sources"], [],
    )
    assert sum(len(m["content"]) for m in messages) < 40_000
    # A change to a profile omitted from the prompt still invalidates its binding.
    before = context["fingerprint"]
    profiles[6]["financial_plans"][0]["initial_payment_cop"] = 101
    assert catalog.read_context(object(), question, 1)["fingerprint"] != before
