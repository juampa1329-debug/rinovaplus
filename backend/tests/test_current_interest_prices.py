"""Campaign buttons must resolve reviewed prices without assigning enrollment."""
import json
from types import SimpleNamespace

import pytest

from app.institutional import agent_catalog, grounded_replies as replies
from app.modules.agents.skill_policy import for_turn, project_facts


@pytest.mark.parametrize("current,old,question", [
    ("INGLÉS", "", "Ver plan de pagos"),
    ("INGLÉS", "", "Diurna"),
    ("COCINA NACIONAL E INTERNACIONAL", "INGLÉS", "Ver plan de pagos"),
])
def test_campaign_button_retrieves_current_candidate_family_not_old_advertisement(monkeypatch, current, old, question):
    programs = [{"program_id": i, "name": name, "schedule": schedule}
                for i, (name, schedule) in enumerate([
                    ("INGLÉS", "DIURNA"), ("INGLÉS", "NOCTURNA"),
                    ("COCINA NACIONAL E INTERNACIONAL", "DIURNA"),
                    ("COCINA NACIONAL E INTERNACIONAL", "NOCTURNA"),
                ], 1)]
    candidates = [p for p in programs if p["name"] == current]
    monkeypatch.setattr(replies, "setting", lambda *_: {"document": {}, "revision": 1})
    monkeypatch.setattr(replies, "search", lambda *_: [])
    monkeypatch.setattr(replies, "effective", lambda *_: {"shared": [], "conversation": []})
    monkeypatch.setattr(replies, "rows", lambda *_: list(reversed([
        {"Direction": "incoming", "Body": "Información " + old},
        {"Direction": "incoming", "Body": "Ver plan de pagos"},
        {"Direction": "incoming", "Body": question},
    ])))
    seen = []
    def retrieve(cursor, query, program):
        seen.append(query)
        assert program is None  # Retrieval does not invent a jornada assignment.
        found = agent_catalog.relevant_programs(programs, {}, query)
        assert found == candidates
        return {"material": {"queried_programs": [{**p, "commercial": {
            "price_cop": 1250000, "financial_plans": [{"initial_payment_cop": 440000}],
        }} for p in found]}}
    monkeypatch.setattr(replies, "Catalog", lambda *_: SimpleNamespace(read_context=retrieve))
    result = replies.context(SimpleNamespace(), SimpleNamespace(), question, conversation="own", selection={
        "configuration": {}, "commercial_interest": {"program_id": None, "candidates": candidates},
        "campaign_reply": {"program_hint": old, "sequence": 0},
    })
    payload = json.loads(result["query"])
    assert all(p["commercial"]["financial_plans"][0]["initial_payment_cop"] == 440000
               for p in payload["catalogo"]["queried_programs"])
    if old and old != current:
        assert old not in seen[0]
        assert old in result["query"]  # Original history is retained for continuity.


@pytest.mark.parametrize("public", [False, True])
def test_unresolved_campaign_fallback_and_public_isolation(monkeypatch, public):
    monkeypatch.setattr(replies, "setting", lambda *_: {"document": {}, "revision": 1})
    monkeypatch.setattr(replies, "search", lambda *_: [])
    monkeypatch.setattr(replies, "effective", lambda *_: {"shared": [], "conversation": []})
    queries = []
    def retrieve(_cursor, query, _program):
        queries.append(query)
        return {"material": {}}
    monkeypatch.setattr(replies, "Catalog", lambda *_: SimpleNamespace(read_context=retrieve))
    replies.context(SimpleNamespace(), SimpleNamespace(), "Precio", public=public, post="PRE-ICFES" if public else "",
                    selection={"configuration": {}, "campaign_reply": {"program_hint": "INGLÉS", "sequence": 0},
                               "commercial_interest": {"candidates": [{"name": "COCINA"}]} if public else {}})
    assert ("INGLÉS" in queries[0]) is (not public)
    assert "COCINA" not in queries[0]


@pytest.mark.parametrize("answer,expected", [("Sí", True), ("Sí por favor", True), ("No", False),
                                             ("Gracias", False), ("Ahora quiero Turismo", False)])
def test_accepting_assistant_payment_offer_keeps_prices(answer, expected):
    history = [{"direction": "incoming", "text": "Conocer el programa"},
               {"direction": "outgoing", "text": "¿Quieres revisar las opciones de pago?"}]
    policy = for_turn(answer, history=history)
    assert policy["turn_plan"]["money_relevant"] is expected
    facts = project_facts({"commercial": {"financial_plans": [{"initial_payment_cop": 440000}]}}, policy)
    if expected:
        assert facts["commercial"]["financial_plans"][0]["initial_payment_cop"] == 440000
    assert for_turn(answer, history=history, public=True)["turn_plan"]["money_relevant"] is False


def test_payment_rules_reach_general_and_specialists_without_inventing_bank_details():
    from app.institutional.cbn_profile import PAYMENT_POLICY, facts_for
    from app.modules.agents.conversation_style import instructions
    from app.modules.ai.application.admissions_prompt import INSTITUTIONAL_SAFETY
    assert PAYMENT_POLICY in instructions() and PAYMENT_POLICY in INSTITUTIONAL_SAFETY
    assert any(v["topic"] == "pagos_y_tarifas_por_semestre" for v in facts_for("Addi"))
    assert "no multipliques" in PAYMENT_POLICY and "PRE-ICFES" in PAYMENT_POLICY


def test_owner_schedule_and_internships_supersede_old_counts_without_changing_english_or_pre():
    from app.institutional.cbn_profile import SCHEDULE_PRACTICE_POLICY, facts_for
    from app.modules.agents.conversation_style import instructions
    from app.modules.ai.application.admissions_prompt import INSTITUTIONAL_SAFETY
    assert SCHEDULE_PRACTICE_POLICY in instructions() and SCHEDULE_PRACTICE_POLICY in INSTITUTIONAL_SAFETY
    facts = {v["topic"]: v for v in facts_for("prácticas")}
    assert "más de 600" in facts["convenios"]["text"]
    assert "remuneradas" in facts["practicas"]["text"]
    assert "7:00 a. m. a 6:00 p. m." in SCHEDULE_PRACTICE_POLICY
    assert "No extrapoles" in SCHEDULE_PRACTICE_POLICY and "PRE-ICFES" in SCHEDULE_PRACTICE_POLICY
