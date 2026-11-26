"""Source-declared admissions states suppress promotions, without SIIE claims."""

import json

from app.institutional.prospect_import import normalize


def promotion_exclusion(values, document=None):
    if isinstance(values, str):
        values = json.loads(values or "{}")
    states = {normalize(v) for v in (values or {}).get("pre_estado", "").split("|")}
    if states & {"inscrito segun origen", "matriculado segun origen"}:
        return "source_enrolled_no_promotions"
    if "negociacion no aceptada" in states:
        return "source_declined_no_reactivation"
    if "interes confirmado segun origen" in states and not (document or {}).get(
        "followup_only"
    ):
        return "source_interest_no_reactivation"
    return ""
