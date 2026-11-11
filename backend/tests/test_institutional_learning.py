"""Learning invariants: fitted parameters, held-out labels, group/time and privacy."""

from uuid import uuid4

import pytest

from app.institutional.learning_engine import (
    FEATURES,
    digest,
    drift,
    features,
    metrics,
    score,
    split,
    train,
)
from app.institutional.learning_models import DatasetWrite, PackWrite, SampleWrite

CUTOFF = "2026-09-01T00:00:00Z"


def corpus(task="lead_scoring"):
    result = []
    for i in range(64):
        label = i % 2
        future = i >= 48
        values = {k: float((label * 80 + 10) + (i % 3)) for k in FEATURES[task]}
        result.append(
            dict(
                id=str(i),
                group=str(i),
                label=label,
                features=values,
                feature_at="2026-09-02T00:00:00Z" if future else "2026-08-01T00:00:00Z",
                outcome_at="2026-09-03T00:00:00Z" if future else "2026-08-02T00:00:00Z",
                program="p" + str((i // 2) % 2),
                stage="new",
            )
        )
    return result


@pytest.mark.parametrize("task", FEATURES)
def test_fit_improves_and_reproduces_by_task_and_segment(task):
    model, report = train(task, corpus(task), CUTOFF)
    again, second = train(task, corpus(task), CUTOFF)
    assert digest(model) == digest(again) and report == second
    assert report["eligible"] and report["candidate"]["accuracy"] == 1
    assert report["candidate"]["brier"] < report["baseline"]["brier"]
    assert len(report["segments"]) == 2 and any(abs(w) > 0.01 for w in model["weights"])


def test_holdout_features_and_labels_cannot_change_fitted_parameters():
    data = corpus()
    original, _ = train("lead_scoring", data, CUTOFF)
    for row in data[48:]:
        row["label"] = 1 - row["label"]
        row["features"] = {k: 999999.0 for k in row["features"]}
    changed, report = train("lead_scoring", data, CUTOFF)
    assert original == changed and not report["eligible"]


def test_groups_are_excluded_across_time_even_if_samples_differ():
    data = corpus()
    data[48]["group"] = data[0]["group"]
    model, report = train("lead_scoring", data, CUTOFF)
    assert "48" not in report["holdout_ids"] and report["excluded_count"] == 1


def test_observed_outcome_crossing_cutoff_cannot_enter_train():
    data = corpus()
    data[0]["outcome_at"] = "2026-09-02T00:00:00Z"
    _, report = train("lead_scoring", data, CUTOFF)
    assert "0" not in report["train_ids"] and "0" not in report["holdout_ids"]


def test_timezone_comparison_is_instant_not_iso_lexical():
    data = corpus()
    data[0]["outcome_at"] = "2026-09-01T00:00:00.000001Z"
    training, _ = split(data, CUTOFF)
    assert "0" not in {r["id"] for r in training}


@pytest.mark.parametrize(
    "mutation",
    ["duplicate", "future_label", "label_two", "too_few", "one_class", "no_holdout"],
)
def test_invalid_dataset_cannot_train(mutation):
    data = corpus()
    if mutation == "duplicate":
        data[1]["id"] = data[0]["id"]
    if mutation == "future_label":
        data[0]["feature_at"] = data[0]["outcome_at"]
    if mutation == "label_two":
        data[0]["label"] = 2
    if mutation == "too_few":
        data = data[:20]
    if mutation == "one_class":
        for row in data:
            row["label"] = 0
    if mutation == "no_holdout":
        for row in data:
            row["group"] = "same"
    with pytest.raises(ValueError):
        train("lead_scoring", data, CUTOFF)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, 1000001, True, "1"])
def test_numeric_schema_rejects_nonfinite_unbounded_or_coerced(value):
    sample = corpus()[0]["features"]
    sample["message_count"] = value
    with pytest.raises(ValueError):
        features("lead_scoring", sample)


def test_labels_or_raw_content_are_not_features():
    sample = corpus()[0]["features"]
    sample["label"] = 1
    with pytest.raises(ValueError):
        features("lead_scoring", sample)
    with pytest.raises(ValueError):
        features("lead_scoring", {"transcript": "private"})


def test_auc_ties_and_zero_denominators():
    result = metrics([0, 1, 0, 1], [0.5] * 4)
    assert result["auc"] == 0.5 and result["brier"] == 0.25 and result["recall"] == 1
    assert metrics([0, 0], [0, 0])["auc"] is None


def test_inference_uses_stored_parameters_and_detects_shift():
    model, _ = train("lead_scoring", corpus(), CUTOFF)
    assert score(model, corpus()[1]["features"]) > 0.9
    assert score(model, corpus()[0]["features"]) < 0.1
    assert drift(model, [{k: 999999 for k in FEATURES["lead_scoring"]}])[
        "review_required"
    ]
    assert not drift(model, [r["features"] for r in corpus()[:4]])["review_required"]


def test_commands_forbid_unreviewed_fields_and_naive_time():
    with pytest.raises(ValueError):
        PackWrite(
            operation_id=uuid4(),
            revision=0,
            document=dict(name="test", task="lead_scoring", tenant_id="other"),
        )
    with pytest.raises(ValueError):
        DatasetWrite(operation_id=uuid4(), cutoff="2026-09-01T00:00:00")
    with pytest.raises(ValueError):
        SampleWrite(
            operation_id=uuid4(),
            grant_id=uuid4(),
            source_kind="demo",
            stage="new",
            feature_at="2026-09-01T00:00:00Z",
            outcome_at="2026-08-01T00:00:00Z",
            features=corpus()[0]["features"],
            label=1,
        )
