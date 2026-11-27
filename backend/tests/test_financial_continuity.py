import pytest

from app.institutional.grounded_replies import RULES, redact
from app.modules.agents.skill_policy import for_turn, project_facts


@pytest.mark.parametrize("question", ["Hmm", "Si", "Entiendo", "🤔"])
def test_brief_private_continuation_retains_price_evidence_and_guides(question):
    history = [
        {"direction": "incoming", "text": "¿Qué costo tiene cada semestre?"},
        {"direction": "outgoing", "text": redact("Cuesta $2.893.000 de contado")},
    ]
    trace = for_turn(question, history=history)
    assert trace["turn_plan"]["phase"] == "continue"
    assert trace["turn_plan"]["financial_continuity"]
    assert "pricing" in {v["id"] for v in trace["consulted_resources"]}
    facts = {"selected": {"commercial": {"price_cop": 2893000, "financial_plans": [{"initial_payment_cop": 770000}]}}}
    assert project_facts(facts, trace) == facts
    assert "redacción de privacidad" in RULES
    assert "[dato omitido]" in history[-1]["text"]


@pytest.mark.parametrize("question,history,public", [
    ("Hmm", [{"direction": "incoming", "text": "¿Qué materias tiene?"}], False),
    ("Hmm", [{"direction": "incoming", "text": "Precio"}, {"direction": "incoming", "text": "Quiero otro programa"}], False),
    ("Hmm", [{"direction": "outgoing", "text": "Precio"}], False),
    ("Hmm", [{"direction": "incoming", "text": "Precio"}], True),
    ("Quiero conocer las materias de Software", [{"direction": "incoming", "text": "Precio"}], False),
])
def test_continuity_does_not_override_new_topic_or_use_private_context_publicly(question, history, public):
    assert not for_turn(question, history=history, public=public)["turn_plan"].get("financial_continuity")


def test_privacy_redaction_still_hides_contact_details():
    assert "3004714060" not in redact("Llama al 3004714060")
    assert "persona@example.com" not in redact("persona@example.com")
