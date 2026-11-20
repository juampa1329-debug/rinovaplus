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


def test_specific_interest_does_not_retrieve_profiles_matching_only_a_shared_word():
    programs = [{"program_id": 24, "name": "BARISMO Y BARTENDER", "schedule": "DIURNA"},
                {"program_id": 25, "name": "BARTENDER", "schedule": "DIURNA"},
                {"program_id": 1, "name": "ENFERMERIA DIURNA"},
                {"program_id": 2, "name": "SOFTWARE DIURNA"}]
    assert agent_catalog.relevant_programs(programs, {}, "Hola, me interesa Barismo y Bartender") == [programs[0]]
    assert agent_catalog.relevant_programs(programs, {}, "Información de enfermería diurna") == [programs[2]]
    assert {v["program_id"] for v in agent_catalog.relevant_programs(programs, {}, "Compara Barismo y Bartender con Software diurna")} == {24, 2}


def test_opening_reserves_long_syllabus_and_requirements_for_a_specific_question():
    from app.modules.agents.skill_policy import for_turn, project_facts
    profile = {"presentation": "Beneficio revisado", "duration": "2 semestres", "certification": "Condición completa",
               "syllabus": "Materia" * 1000, "requirements": "Condiciones" * 200,
               "financial_plans": [{"conditions": "No cortar"}]}
    opening = project_facts(profile, for_turn("Me interesa ese programa"))
    assert opening["presentation"] == profile["presentation"] and opening["certification"] == profile["certification"]
    assert "syllabus" not in opening and "requirements" not in opening and "financial_plans" not in opening
    assert project_facts(profile, for_turn("¿Cuáles son las materias y requisitos?")) == profile
    assert project_facts(profile, for_turn("¿Cuánto cuesta y cuáles son las cuotas?"))["financial_plans"] == profile["financial_plans"]


def test_reviewed_dna_already_in_system_is_referenced_without_duplicating_body():
    from app.modules.agents.runtime import scoped_memory
    from app.modules.agents.domain import Configuration
    from app.modules.agents.service import policy_for
    dna = {"id": "dna", "version": 3, "content": {"dna": {"identity": "Reviewed identity"}}}
    shared = {"id": "shared", "version": 1, "content": {"body": "Independent shared guidance"}}
    selection = {"agent_id": "guide", "configuration": Configuration(memories=[]).model_dump(), "context": {"program_id": 1}, "institution_dna": [dna]}
    cursor = SimpleNamespace(agent_memory=lambda *_: {"shared": [dna, shared], "conversation": []})
    memory = scoped_memory(cursor, selection)
    assert "Reviewed identity" in policy_for(selection).system_prompt
    assert memory["reviewed_memory"]["shared"] == [shared]
    assert memory["reviewed_memory"]["dna_in_system"] == [{"id": "dna", "version": 3}]
