"""The pricing turn preserves approved options and conveys Treasury authority."""

from copy import deepcopy

import pytest

from app.institutional.program_commercial import agent_facts
from app.modules.agents.skill_library import read
from app.modules.agents.skill_policy import for_turn, instructions, project_facts


@pytest.mark.parametrize("public", [False, True])
@pytest.mark.parametrize("question", [
    "¿Puedo dar un abono inicial mayor para bajar las cuotas?",
    "Quiero abonar más de lo estipulado; ¿puedo adelantar mi inscripción?",
    "¿Qué otro plan de financiación tienen si pago más al inicio?",
])
def test_greater_deposit_uses_whole_pricing_guide_without_rewriting_finance(public, question):
    profile = {"price_concept": "Primer semestre", "financial_plans": [
        {"external_id": "lower-entry", "initial_payment_cop": 550000,
         "total_cost_cop": 2200000, "installments": [{"number": i, "amount_cop": 550000} for i in range(1, 4)]},
        {"external_id": "higher-entry", "initial_payment_cop": 1100000,
         "total_cost_cop": 2150000, "installments": [{"number": i, "amount_cop": 350000} for i in range(1, 4)]},
        {"external_id": "expired", "initial_payment_cop": 1500000,
         "valid_until": "2000-01-01", "installments": []},
    ]}
    original = deepcopy(profile)
    trace = for_turn(question, public=public)
    prompt = instructions(trace)
    guide = read("pricing")
    assert guide["content"] in prompt
    assert "Tesorería debe revisar y aprobar" in prompt
    assert "no recalcules ni prometas" in prompt
    assert "puede adelantar la inscripción" in prompt
    assert "enlace oficial suministrado para ese programa" in prompt
    material = project_facts({"commercial": agent_facts(profile)}, trace)["commercial"]
    assert [p["external_id"] for p in material["financial_plans"]] == ["lower-entry", "higher-entry"]
    assert material["financial_plans"] == original["financial_plans"][:2]
    assert material["entry_payment_offer"]["initial_payment_cop"] == 550000
    assert profile == original and trace["grants_permissions"] is False
