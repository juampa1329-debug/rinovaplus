"""Synthetic evidence boundaries; no operator or institutional records."""

import json
from copy import deepcopy
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.conversation_analysis.domain.models import AnalysisContext
from app.modules.conversation_strategy.domain.models import (
    AutonomyWrite,
    PauseWrite,
    StrategyFeedbackWrite,
    validate_result,
)


def envelope():
    return {
        "context": {key: [] for key in AnalysisContext.model_fields},
        "strategy": {
            "signals": [],
            "churn": {"level": "unknown", "text": "", "evidenceIds": []},
            "noContact": False,
            "noContactEvidenceIds": [],
            "recommendations": [],
            "objections": [],
            "remarketing": [],
            "drafts": [],
        },
    }


def signal(criterion="interest"):
    return {
        "criterion": criterion,
        "text": "Solicitud comprobable",
        "evidenceIds": ["m1"],
    }


def test_legacy_and_empty_results_do_not_invent_score_or_plan():
    value = envelope()
    assert validate_result(json.dumps(value["context"]), {}) == (value["context"], None)
    _, plan = validate_result(json.dumps(value), {})
    assert plan["index"] is None and not plan["followupSupported"]
    assert plan["churn"]["level"] == "unknown"


@pytest.mark.parametrize("direction", ["outgoing", "human_feedback"])
@pytest.mark.parametrize("field", ["signal", "churn", "noContact"])
def test_operator_and_outgoing_cannot_establish_contact_intent(direction, field):
    value = envelope()
    if field == "signal":
        value["strategy"]["signals"] = [signal()]
    elif field == "churn":
        value["strategy"]["churn"] = {
            "level": "concern",
            "text": "Preocupación",
            "evidenceIds": ["m1"],
        }
    else:
        value["strategy"].update(noContact=True, noContactEvidenceIds=["m1"])
    with pytest.raises(ValueError):
        validate_result(json.dumps(value), {"m1": (str(uuid4()), direction)})


@pytest.mark.parametrize(
    "criterion,index,executable",
    [("interest", 1, False), ("next_step", 1, True), ("commitment", 1, True)],
)
def test_count_has_no_weights_and_followup_requires_next_step(
    criterion, index, executable
):
    value = envelope()
    value["strategy"]["signals"] = [signal(criterion)]
    message = str(uuid4())
    _, plan = validate_result(json.dumps(value), {"m1": (message, "incoming")})
    assert plan["index"] == index and plan["followupSupported"] is executable
    assert plan["signals"][0]["evidenceIds"] == [message]


@pytest.mark.parametrize("withdrawal", [False, True])
def test_no_contact_or_withdrawal_blocks_positive_commitment(withdrawal):
    value = envelope()
    value["strategy"]["signals"] = [signal("commitment")]
    if withdrawal:
        value["strategy"]["churn"] = {
            "level": "withdrawal",
            "text": "Retirada",
            "evidenceIds": ["m1"],
        }
    else:
        value["strategy"].update(noContact=True, noContactEvidenceIds=["m1"])
    _, plan = validate_result(json.dumps(value), {"m1": (str(uuid4()), "incoming")})
    assert not plan["followupSupported"]


def test_malformed_duplicate_and_unknown_evidence_rejected():
    value = envelope()
    value["strategy"]["signals"] = [signal(), signal()]
    with pytest.raises(ValueError):
        validate_result(json.dumps(value), {"m1": (str(uuid4()), "incoming")})
    value["strategy"]["signals"] = [signal()]
    with pytest.raises(ValueError):
        validate_result(json.dumps(value), {})
    value["strategy"]["probability"] = 0.9
    with pytest.raises(ValueError):
        validate_result(json.dumps(value), {"m1": (str(uuid4()), "incoming")})


def test_every_generated_text_is_redacted_but_evidence_ids_are_preserved():
    value = envelope()
    item = {
        "text": "Synthetic Private Person necesita información",
        "evidenceIds": ["m1"],
    }
    for field in ["recommendations", "objections", "remarketing", "drafts"]:
        value["strategy"][field] = [deepcopy(item)]
    value["strategy"]["signals"] = [{**item, "criterion": "interest"}]
    value["strategy"]["churn"] = {**item, "level": "concern"}
    message = str(uuid4())
    _, plan = validate_result(
        json.dumps(value), {"m1": (message, "incoming")}, ["Synthetic Private Person"]
    )
    assert "Synthetic Private Person" not in json.dumps(plan)
    assert plan["signals"][0]["evidenceIds"] == [message]


@pytest.mark.parametrize("value", [1, 0, "true", "false", None])
@pytest.mark.parametrize(
    "model,field", [(AutonomyWrite, "enabled"), (PauseWrite, "paused")]
)
def test_permission_flags_require_real_boolean(model, field, value):
    with pytest.raises(ValidationError):
        model(operationId=str(uuid4()), expectedRevision="0", **{field: value})


def test_feedback_requires_correction_and_bound_plan():
    with pytest.raises(ValidationError):
        StrategyFeedbackWrite(
            operationId=str(uuid4()),
            expectedRevision="0",
            planId=str(uuid4()),
            planRevision=1,
            usefulness="correction",
            outcome="not_observed",
            correction="  ",
        )


@pytest.mark.parametrize(
    "level,text", [("unknown", "Sin evidencia"), ("concern", "   "), ("withdrawal", "")]
)
def test_churn_explanations_require_meaningful_incoming_evidence(level, text):
    value = envelope()
    value["strategy"]["churn"] = {
        "level": level,
        "text": text,
        "evidenceIds": [] if level == "unknown" else ["m1"],
    }
    with pytest.raises(ValueError):
        validate_result(json.dumps(value), {"m1": (str(uuid4()), "incoming")})
