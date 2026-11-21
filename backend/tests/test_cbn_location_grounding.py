"""Owner-reviewed logistics apply to every agent without a fictitious employee."""

import json

from app.institutional.cbn_profile import ADMISSIONS_LOCATION, FACTS, LOCATION_POLICY, reviewed_sources
from app.modules.agents.conversation_style import instructions
from app.modules.ai.application.admissions_prompt import AdmissionsPolicy, assemble_prompt, validate_reply
from app.modules.ai.infrastructure.providers import AiError
import pytest


def test_location_is_an_owner_reviewed_fact_not_an_invented_web_source():
    location = next(f for f in FACTS if f["topic"] == "oficina_admisiones")
    assert ADMISSIONS_LOCATION in location["text"]
    assert location["source"] == "owner_reviewed:2026-11-20:admissions-office"
    assert "horarios" in location["text"]


def test_general_and_specialist_keep_correction_over_old_assistant_history():
    history = [{"id": "old", "role": "assistant", "text": "Estamos en calle 14 número 2-24."}]
    for structured in (True, False):
        messages = assemble_prompt(AdmissionsPolicy(), "¿Puedo ir personalmente?", {}, [], history, structured=structured)
        assert LOCATION_POLICY in messages[0]["content"]
        assert "no es una fuente institucional" in messages[0]["content"]
        payload = json.loads(messages[1]["content"].split("\n", 1)[1])
        assert payload["institutional_sources_sql_primary_documents_supplemental"] == reviewed_sources([])
        assert payload["history"][0]["text"] == history[0]["text"]
    assert LOCATION_POLICY in instructions({"advisor_name": "Juan"})
    assert "No prometas que encontrarán físicamente" in instructions()
    assert "Si preguntan expresamente si eres IA" in instructions()


def test_reviewed_facts_have_valid_deduplicated_references_without_trusting_arbitrary_urls():
    sources = reviewed_sources([])
    assert reviewed_sources(sources) == sources
    office = next(s for s in sources if "oficina_admisiones" in s["title"])
    reply = {"answer": ADMISSIONS_LOCATION, "handoff": False, "references": [office["id"]]}
    assert not validate_reply(json.dumps(reply), [], [])[0].handoff
    reply["references"] = ["https://unverified.invalid"]
    with pytest.raises(AiError, match="admissions_unknown_reference"):
        validate_reply(json.dumps(reply), sources, [])
