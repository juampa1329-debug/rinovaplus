import json
import pytest
from types import SimpleNamespace
from uuid import uuid4

from app.institutional import agent_catalog
from app.modules.ai.application.admissions_prompt import AdmissionsPolicy, assemble_prompt
from app.modules.ai.infrastructure.providers import AiError


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


def test_native_trial_keeps_full_evidence_with_explicit_bound_and_model_capacity():
    from app.modules.agents.simulation_route import check_context
    source = {"id": "fixture", "title": "Condiciones completas", "text": "Dato verificado. " * 2000}
    with pytest.raises(AiError, match="admissions_context_limit"):
        assemble_prompt(AdmissionsPolicy(), "Pregunta", {}, [source], [])
    messages = assemble_prompt(AdmissionsPolicy(), "Pregunta", {}, [source], [], max_chars=60000)
    assert source["text"] in messages[1]["content"]
    check_context({"context_limit": 100000}, messages, 700)
    for route in ({"context_limit": 1000}, {"context_limit": None}):
        with pytest.raises(AiError, match="agents_model_context_limit"):
            check_context(route, messages, 700)
    with pytest.raises(AiError, match="admissions_context_limit"):
        assemble_prompt(AdmissionsPolicy(), "Pregunta", {}, [{**source, "text": "x" * 60000}], [], max_chars=60000)


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


def test_financial_focus_keeps_all_payment_conditions_and_explicit_academic_questions():
    from app.modules.agents.skill_policy import for_turn, project_facts
    profile = {"duration": "2 semestres", "certification": "Diploma con condición", "syllabus": "Todas las materias",
               "requirements": "Todos los documentos", "presentation": "Presentación", "career_outcomes": "Campo laboral",
               "financial_plans": [{"conditions": "Alcance, cargos y fechas completos", "installments": [{"due_date": "2027-03-08"}]}],
               "cost_exclusions": "Uniforme aparte", "source_note": "Nota revisada"}
    focused = project_facts(profile, for_turn("¿Con cuánto puedo empezar y cuándo pago el resto?"))
    assert focused["financial_plans"] == profile["financial_plans"]
    assert focused["cost_exclusions"] == profile["cost_exclusions"] and focused["source_note"] == profile["source_note"]
    assert "syllabus" not in focused and "presentation" not in focused
    expanded = project_facts(profile, for_turn("¿Cuánto cuesta, qué materias tiene y qué requisitos piden?"))
    assert expanded["syllabus"] == profile["syllabus"] and expanded["requirements"] == profile["requirements"]


def test_two_requested_programs_keep_prices_by_removing_derived_prompt_repetition():
    from copy import deepcopy
    from app.institutional.program_commercial import agent_facts
    programs = []
    for number, cash, initial in [(1, 800000, 220000), (2, 1860000, 490000)]:
        profile = agent_facts({
            'presentation': 'Presentación verificada. ' * 50,
            'price_cop': cash, 'price_concept': 'Concepto y alcance revisados',
            'price_valid_until': '2099-12-16', 'cost_exclusions': 'Material aparte',
            'source_note': 'Procedencia revisada sin recortar',
            'financial_plans': [{
                'external_id': str(number), 'initial_payment_cop': initial,
                'initial_payment_due_date': '2099-12-15', 'total_cost_cop': 4 * initial,
                'valid_until': '2099-12-15', 'conditions': 'Condiciones completas del plan. ' * 25,
                'installments': [{'number': i, 'amount_cop': initial, 'due_date': f'2100-0{i+1}-10'} for i in range(1, 4)],
            }],
        })
        programs.append({'program_id': number, 'commercial': profile})
    original = deepcopy(programs)
    assert sum(len(json.dumps(p, ensure_ascii=False)) for p in programs) > 12000
    _, retained = agent_catalog.bounded_commercial_context(None, programs)
    assert all('commercial' in p and not p.get('commercial_details_omitted') for p in retained)
    assert sum(len(json.dumps(p, ensure_ascii=False)) for p in retained) <= 12000
    for item, before in zip(retained, original, strict=True):
        profile, prior = item['commercial'], before['commercial']
        for key in ('financial_plans', 'price_cop', 'price_concept', 'price_valid_until', 'cost_exclusions', 'source_note', 'presentation'):
            assert profile[key] == prior[key]
        assert profile['entry_payment_offer']['initial_payment_cop'] == prior['entry_payment_offer']['initial_payment_cop']
        assert profile['entry_payment_offer']['full_details_in_financial_plan'] == profile['financial_plans'][0]['external_id']
    assert programs == original
