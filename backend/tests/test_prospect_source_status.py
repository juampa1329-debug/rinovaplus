import json

import pytest
from fastapi import HTTPException

from app.institutional.broadcast_prospects import reviewed_contact
from app.institutional.prospect_source_status import promotion_exclusion


@pytest.mark.parametrize("state,reason", [
    ("Inscrito según origen", "source_enrolled_no_promotions"),
    ("Matriculado según origen", "source_enrolled_no_promotions"),
    ("Negociación no aceptada", "source_declined_no_reactivation"),
    ("Interés confirmado según origen", "source_interest_no_reactivation"),
])
def test_source_progress_blocks_generic_campaign_and_bulk_onboarding(state, reason):
    values = {
        "pre_estado": state,
        "pre_programas": "COCINA",
        "pre_import_ref": "PRE-1234567890abcdef",
    }
    assert promotion_exclusion(json.dumps(values)) == reason
    with pytest.raises(HTTPException) as error:
        reviewed_contact({"Type": "Preinscrito", "Phone": "+573001234567",
                          "CustomValues": json.dumps(values)}, "all")
    assert error.value.detail == "prospect_source_status_excluded"


def test_source_interest_allows_case_followup_but_never_enrolled_or_declined():
    doc = {"followup_only": True}
    assert not promotion_exclusion({"pre_estado": "Interés confirmado según origen"}, doc)
    for state in ["Matriculado según origen", "Inscrito según origen", "Negociación no aceptada"]:
        assert promotion_exclusion({"pre_estado": state}, doc)
    assert promotion_exclusion({"pre_estado": "En negociación | Inscrito según origen"}, doc)


@pytest.mark.parametrize("values", [None, "{}", {}, {"pre_estado": "Próximo semestre según origen"}, {"pre_estado": "En negociación"}])
def test_historical_prospect_and_missing_source_state_keep_other_delivery_guards(values):
    assert not promotion_exclusion(values)
