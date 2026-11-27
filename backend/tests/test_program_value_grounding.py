import json
from uuid import uuid4

from app.institutional.cbn_profile import PROGRAM_VALUE_POLICY, reviewed_sources
from app.modules.agents.conversation_style import instructions
from app.modules.ai.application.admissions_prompt import AdmissionsPolicy, assemble_prompt, validate_reply


def test_live_style_and_admissions_share_single_authoritative_value_policy():
    style = instructions({"advisor_name": "Juan Pablo"})
    assert PROGRAM_VALUE_POLICY in style
    messages = assemble_prompt(
        AdmissionsPolicy(system_prompt=PROGRAM_VALUE_POLICY + "\nConserva el interés de Cocina."),
        "¿Qué ventajas tengo al estudiar Cocina?", [], [], [],
    )
    assert messages[0]["content"].count(PROGRAM_VALUE_POLICY) == 1
    assert "Conserva el interés de Cocina." in messages[0]["content"]
    assert sum(len(v["content"]) for v in messages) <= 40000
    context = json.loads(messages[1]["content"].split("\n", 1)[1])
    facts = context["institutional_sources_sql_primary_documents_supplemental"]
    source = next(v for v in facts if "optional-scholarship-program-value" in v["provenance"])
    assert "opcionales según ficha" in source["text"]
    assert "rechazarla no impide estudiar" in messages[0]["content"]
    assert "doble titulación obligatoria" in source["text"]
    assert "No extiendas prácticas laborales" in messages[0]["content"]
    assert "No implica todas las universidades" in source["text"]
    assert "Sí es posible homologar" in source["text"]
    assert "cada universidad fija" in source["text"]
    assert "tres meses de prácticas para carreras excepto Cocina" in source["text"]
    assert "faltan costo completo e ingreso" in source["text"]
    assert "no un resultado garantizado" in messages[0]["content"]


def test_value_source_is_citable_and_unknown_evidence_is_rejected():
    from app.modules.ai.infrastructure.providers import AiError
    import pytest

    sources = reviewed_sources([])
    value = next(v for v in sources if "optional-scholarship-program-value" in v["provenance"])
    reply = {"answer": "La beca complementaria es opcional cuando aplica al programa.",
             "handoff": False, "references": [value["id"]], "memory": []}
    validate_reply(json.dumps(reply), sources, [])
    reply["references"] = [str(uuid4())]
    with pytest.raises(AiError, match="admissions_unknown_reference"):
        validate_reply(json.dumps(reply), sources, [])


def test_general_program_facts_do_not_invent_a_scholarship_or_financial_projection():
    from app.institutional.program_commercial import agent_facts

    # Generic program without scholarship/partnership data remains generic.
    facts = agent_facts({"presentation": "Programa de ejemplo"})
    assert "opcional donde corresponda" in facts["program_presentation_guidance"]
    assert not any(k in facts for k in ("scholarship", "roi_months", "monthly_income", "university_partner"))
