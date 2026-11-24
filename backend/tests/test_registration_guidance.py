import json
from uuid import NAMESPACE_URL, uuid5

import pytest

from app.institutional.cbn_profile import (
    FACTS, REVIEWED, REGISTRATION_POLICY, REGISTRATION_URL,
    PREICFES_REGISTRATION_URL, reviewed_sources,
)
from app.modules.ai.application.admissions_prompt import AdmissionsPolicy, assemble_prompt


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
