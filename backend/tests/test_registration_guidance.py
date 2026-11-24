import json
from uuid import NAMESPACE_URL, uuid5
from types import SimpleNamespace

import pytest

from app.institutional.cbn_profile import (
    FACTS, REVIEWED, REGISTRATION_POLICY, REGISTRATION_URL,
    PREICFES_REGISTRATION_URL, reviewed_sources,
)
from app.modules.ai.application.admissions_prompt import AdmissionsPolicy, assemble_prompt
from app.institutional import grounded_replies as grounding
from app.institutional.registration_guidance import FACTS as HELP_FACTS, relevant


@pytest.mark.parametrize("structured", [False, True])
def test_general_and_specialist_keep_correct_registration_sources_without_program_profile(structured):
    messages = assemble_prompt(AdmissionsPolicy(system_prompt="Atiende con las fuentes revisadas."),
        "Quiero inscribirme mientras revisan mi abono inicial", {}, [], [], structured=structured)
    assert REGISTRATION_POLICY in messages[0]["content"]
    context = json.loads(messages[1]["content"].split("\n", 1)[1])
    sources = context["institutional_sources_sql_primary_documents_supplemental"]
    general = next(v for v in sources if v["title"].endswith("inscripcion_general"))
    pre = next(v for v in sources if v["title"].endswith("inscripcion_preicfes"))
    assert REGISTRATION_URL in general["text"] and PREICFES_REGISTRATION_URL not in general["text"]
    assert PREICFES_REGISTRATION_URL in pre["text"] and REGISTRATION_URL not in pre["text"]
    assert all(v["revision"] == "2026-11-24" and not v["financial_source"] for v in (general, pre))
    assert "no aprueba el plan" in messages[0]["content"]


def test_adding_registration_does_not_reidentify_prior_reviewed_facts():
    values = reviewed_sources([])
    assert reviewed_sources(values) == values
    for fact in FACTS:
        if fact.get("reviewed_at"):
            continue
        expected = str(uuid5(NAMESPACE_URL, "cbn-reviewed:" + REVIEWED + ":" + fact["topic"]))
        assert next(v for v in values if v["title"].endswith(fact["topic"]))["id"] == expected


@pytest.mark.parametrize("question", [
    "¿Cómo lleno el formulario de inscripción?", "No me carga el municipio", "¿Qué documento adjunto?",
    "¿Y el correo?", "¿Qué pongo en este campo?", "¿Cómo me matriculo?",
])
def test_help_retrieval_keeps_both_scoped_forms_and_nonfinancial_provenance(question):
    assert relevant(question)
    sources = reviewed_sources([], question)
    help_sources = [s for s in sources if "inscripcion_ayuda" in s["title"]]
    assert len(help_sources) == 3
    assert all(not s["financial_source"] and s["revision"] == "2026-11-24" for s in help_sources)
    assert reviewed_sources(sources, question) == sources
    messages = assemble_prompt(AdmissionsPolicy(), question, {}, sources, [])
    payload = json.loads(messages[1]["content"].split("\n", 1)[1])
    assert all(s in payload["institutional_sources_sql_primary_documents_supplemental"] for s in help_sources)


def test_form_help_does_not_expand_unrelated_turns_and_keeps_form_specific_limits():
    assert not relevant("Me interesa emprender con Software")
    assert not any("inscripcion_ayuda" in s["title"] for s in reviewed_sources([], "Me interesa emprender con Software"))
    general, pre, help_rules = HELP_FACTS
    assert general["source"] == REGISTRATION_URL and pre["source"] == PREICFES_REGISTRATION_URL
    assert "BARISMO y BARTENDER" in general["text"] and "confirmar con Admisiones" in general["text"]
    assert "PROEFICIENCIA EN INGLES" in general["text"]
    assert "no una nueva declaración de obligatoriedad" in general["text"]
    assert "máximo 10MB por archivo y 50MB en total" in pre["text"]
    assert "No aplicar aquí el mínimo de 16 años" in pre["text"]
    assert "ni pedir envíos repetidos" in help_rules["text"]
    assert "directamente en el formulario oficial" in help_rules["text"]


@pytest.mark.parametrize("public,structured", [(False, True), (False, False), (True, True), (True, False)])
def test_automatic_and_suggested_social_replies_receive_reviewed_help_without_private_documents(
    monkeypatch, public, structured,
):
    monkeypatch.setattr(grounding, "setting", lambda *_: {"revision": 1, "document": {}})
    monkeypatch.setattr(grounding, "Catalog", lambda *_: SimpleNamespace(read_context=lambda *_: {"material": {}}))
    monkeypatch.setattr(grounding, "search", lambda *_: [])
    monkeypatch.setattr(grounding, "effective", lambda *_: {"shared": []})
    value = grounding.context(None, SimpleNamespace(), "¿Cómo lleno el formulario de Inglés?",
                              public=public, structured=structured)
    facts = json.loads(value["query"])["institucion_revisada"]["facts"]
    assert all(f in facts for f in HELP_FACTS)
    assert "no se solicitan por este chat" in value["system"]
    assert json.loads(value["query"])["historial"] == []
