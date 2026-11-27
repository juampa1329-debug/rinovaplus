"""Common-name retrieval regressions from the native academic audit; no live IO."""

import pytest

from app.institutional.agent_catalog import relevant_programs
from app.institutional.sales_context import matches, interest
from app.institutional.program_commercial import agent_facts
from app.modules.agents.skill_policy import for_turn, project_facts


def test_old_tourism_abbreviation_does_not_match_its_common_name():
    programs = [{"program_id": 1, "name": "SERVICIOS HOTELEROS Y AGENCIAS TURISTICAS", "schedule": "DIURNA"}]
    assert relevant_programs(programs, {1: {"aliases": "SHAT"}}, "valores de turismo") == []
    assert matches(programs, {1: {"aliases": "SHAT"}}, "valores de turismo") == []


@pytest.mark.parametrize("name,aliases,question", [
    ("SERVICIOS HOTELEROS Y AGENCIAS TURISTICAS", "SHAT; Turismo; Hotelería; Agencias Turísticas", "¿Cuánto vale Turismo?"),
    ("SERVICIOS HOTELEROS Y AGENCIAS TURISTICAS", "SHAT; Turismo; Hotelería; Agencias Turísticas", "Quiero estudiar hotelería"),
    ("AUXILIAR EN SERVICIOS FARMACEUTICOS", "ASFD; Farmacia; Servicios Farmacéuticos; Auxiliar de Farmacia", "¿Cuánto cuesta Farmacia?"),
    ("DESARROLLO DE SOFTWARE Y APLICACIONES MOVILES", "DSAM; Software; Programación; Aplicaciones Móviles", "Quiero programación"),
    ("DESARROLLO MULTIMEDIA Y COMUNICACIÓN GRAFICA", "DMC; Multimedia; Diseño Gráfico; Comunicación Gráfica", "Quiero diseño gráfico"),
    ("AUXILIAR ADMINISTRATIVO EN SALUD", "AAS; Administración en Salud; Administrativo en Salud", "Información de administración en salud"),
    ("PRE-ICFES CBN · Alta Competencia", "PRE-ICFES; PREICFES; PRE ICFES; PREIFES; PRE IFES; Precfes; Saber 11", "Preifes, ¿qué vale?"),
])
def test_reviewed_labels_find_the_same_program_for_routing_and_facts(name, aliases, question):
    programs = [{"program_id": 1, "name": name, "schedule": "DIURNA"}]
    profiles = {1: {"aliases": aliases}}
    assert relevant_programs(programs, profiles, question) == programs
    assert matches(programs, profiles, question) == programs


def test_two_schedules_stay_ambiguous_without_assigning_a_customer():
    programs = [
        {"program_id": 1, "name": "CONTABILIDAD SISTEMATIZADA Y FINANZAS", "schedule": "DIURNA"},
        {"program_id": 2, "name": "CONTABILIDAD SISTEMATIZADA Y FINANZAS", "schedule": "NOCTURNA"},
    ]
    profiles = {1: {"aliases": "Contabilidad; Finanzas"}, 2: {"aliases": "Contabilidad; Finanzas"}}
    found = interest(programs, profiles, [{"Direction": "incoming", "Body": "Quiero contabilidad", "Sequence": 1, "MessageId": "fixture"}])
    assert found["program_id"] is None and len(found["candidates"]) == 2
    assert matches(programs, profiles, "Contabilidad de noche") == [programs[1]]


def test_icfes_requirement_does_not_turn_into_a_preicfes_sales_request():
    programs = [{"program_id": 1, "name": "PRE-ICFES CBN", "schedule": "G1/G2/G3"}]
    profiles = {1: {"aliases": "PRE-ICFES; PREICFES; PRE ICFES; PREIFES; PRE IFES; Precfes; Saber 11"}}
    assert matches(programs, profiles, "¿Exigen resultados del ICFES para Cocina?") == []


def test_tourism_financial_question_keeps_reviewed_cash_and_every_installment():
    profile = {
        "price_cop": 1860000, "price_concept": "Primer semestre 2027", "price_valid_until": "2099-12-17",
        "financial_plans": [{"external_id": "fixture", "name": "Financiación", "initial_payment_cop": 490000,
                             "initial_payment_due_date": "2099-12-17", "total_cost_cop": 1960000,
                             "valid_until": "2099-12-17", "installments": [
                                 {"number": i, "amount_cop": 490000, "due_date": date}
                                 for i, date in enumerate(["2100-03-08", "2100-04-12", "2100-05-11"], 1)]}],
    }
    projected = project_facts({"commercial": agent_facts(profile)}, for_turn("¿Cuánto vale Turismo financiado y de contado?"))
    assert projected["commercial"]["price_cop"] == 1860000
    assert projected["commercial"]["entry_payment_offer"]["initial_payment_cop"] == 490000
    assert len(projected["commercial"]["financial_plans"][0]["installments"]) == 3
