"""Owner-reviewed logistics apply to every agent without a fictitious employee."""

import json

from app.institutional.cbn_profile import ADMISSIONS_LOCATION, FACTS, LOCATION_POLICY
from app.modules.agents.conversation_style import instructions
from app.modules.ai.application.admissions_prompt import AdmissionsPolicy, assemble_prompt


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
        assert payload["institutional_reviewed_facts"]["facts"] == FACTS
        assert payload["history"][0]["text"] == history[0]["text"]
    assert LOCATION_POLICY in instructions({"advisor_name": "Juan"})
    assert "No prometas que encontrarán físicamente" in instructions()
    assert "Si preguntan expresamente si eres IA" in instructions()
