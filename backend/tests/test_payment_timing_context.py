from datetime import date

import pytest

from app.institutional.program_commercial import payment_timing


def schedule():
    return {"initial_payment_due_date": "2026-12-10", "installments": [
        {"due_date": "2027-03-09"}, {"due_date": "2027-04-13"},
    ]}


def test_calendar_benefit_is_source_based_conditional_and_scoped():
    value = payment_timing(schedule(), date(2026, 11, 20))
    assert value["next_installment_due_date"] == "2027-03-09"
    assert value["next_installment_is_next_year"]
    assert "año entrante" in value["guidance"] and "si realiza el abono" in value["guidance"]
    assert value["scope"] == "financing_installments_only_not_other_charges"
    assert "otros cargos" in value["guidance"]


@pytest.mark.parametrize("change", [
    {"initial_payment_due_date": None},
    {"installments": [{"due_date": None}, {"due_date": "2027-04-13"}]},
    {"installments": []}, {"installments": [{"due_date": "2026-12-09"}]},
    {"installments": [{"due_date": "2027-02-30"}]},
])
def test_no_grace_period_is_inferred_from_partial_or_invalid_dates(change):
    assert payment_timing({**schedule(), **change}, date(2026, 11, 20)) is None


def test_calendar_words_follow_current_colombian_date_not_a_permanent_script():
    assert payment_timing(schedule(), date(2027, 1, 2)) is None
    later = {"initial_payment_due_date": "2027-02-01", "installments": [{"due_date": "2027-03-09"}]}
    value = payment_timing(later, date(2027, 1, 2))
    assert not value["next_installment_is_next_year"]
    assert "año entrante" not in value["guidance"]
