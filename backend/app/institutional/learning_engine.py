"""Deterministic binary ML on reviewed numeric snapshots; no IO or rule labels."""

import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone

FEATURES = {
    "lead_scoring": [
        "response_time",
        "message_count",
        "asked_for_price",
        "engagement_score",
        "avg_reply_speed",
        "channel_source_score",
        "followup_count",
    ],
    "churn_prediction": [
        "inactivity_days",
        "negative_sentiment_ratio",
        "response_drop",
        "ticket_frequency",
        "engagement_decline",
        "message_count",
        "engagement_score",
    ],
    "smart_remarketing": [
        "open_rate",
        "click_rate",
        "best_hour",
        "best_channel_score",
        "campaign_engagement",
        "engagement_score",
        "inactivity_days",
    ],
    "operational_anomaly": [
        "webhook_errors_24h",
        "ai_failed_24h",
        "outbound_failed_24h",
        "dead_letters_open",
        "event_failure_rate",
    ],
}
ALGORITHM = "cbn_binary_logistic_gd_v1"


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()


def features(task, value):
    if (
        task not in FEATURES
        or not isinstance(value, dict)
        or set(value) != set(FEATURES[task])
    ):
        raise ValueError("learning_feature_schema")
    if any(
        type(v) not in {int, float} or not math.isfinite(v) or not 0 <= v <= 1000000
        for v in value.values()
    ):
        raise ValueError("learning_feature_range")
    return {k: float(value[k]) for k in FEATURES[task]}


def sigmoid(v):
    return 1 / (1 + math.exp(-max(-40, min(40, v))))


def score(artifact, values):
    if artifact["algorithm"] != ALGORITHM or artifact["feature_keys"] != FEATURES.get(
        artifact["task"]
    ):
        raise ValueError("learning_artifact_schema")
    v = features(artifact["task"], values)
    return sigmoid(
        artifact["bias"]
        + sum(
            w * ((v[k] - mu) / scale)
            for k, w, mu, scale in zip(
                artifact["feature_keys"],
                artifact["weights"],
                artifact["mean"],
                artifact["scale"],
                strict=True,
            )
        )
    )


def metrics(labels, scores):
    n = len(labels)
    if not n or len(scores) != n:
        raise ValueError("learning_empty_evaluation")
    tp = sum(y == 1 and p >= 0.5 for y, p in zip(labels, scores))
    fp = sum(y == 0 and p >= 0.5 for y, p in zip(labels, scores))
    fn = sum(y == 1 and p < 0.5 for y, p in zip(labels, scores))
    positives = sum(labels)
    negatives = n - positives
    # Average rank AUC; ties receive half credit, no test labels enter fitting.
    ordered = sorted(zip(scores, labels))
    rank_sum = 0.0
    i = 0
    while i < n:
        j = i + 1
        while j < n and ordered[j][0] == ordered[i][0]:
            j += 1
        rank_sum += ((i + 1 + j) / 2) * sum(y for _, y in ordered[i:j])
        i = j
    auc = (
        (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)
        if positives and negatives
        else None
    )
    return dict(
        n=n,
        positives=positives,
        negatives=negatives,
        accuracy=sum((p >= 0.5) == y for y, p in zip(labels, scores)) / n,
        precision=tp / max(1, tp + fp),
        recall=tp / max(1, tp + fn),
        f1=2 * tp / max(1, 2 * tp + fp + fn),
        brier=sum((p - y) ** 2 for y, p in zip(labels, scores)) / n,
        auc=auc,
        false_positives=fp,
        false_negatives=fn,
    )


def split(samples, cutoff):
    if not 24 <= len(samples) <= 1000:
        raise ValueError("learning_samples_24_to_1000_required")

    def stamp(value):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("learning_timezone_required")
        return parsed.astimezone(timezone.utc)

    boundary = stamp(cutoff)
    if len({s["id"] for s in samples}) != len(samples) or any(
        type(s["label"]) is not int or s["label"] not in {0, 1} for s in samples
    ):
        raise ValueError("learning_sample_identity_or_label")
    ordered = sorted(samples, key=lambda s: (stamp(s["feature_at"]), s["id"]))
    if any(stamp(s["feature_at"]) >= stamp(s["outcome_at"]) for s in ordered):
        raise ValueError("learning_outcome_must_follow_features")
    training = [s for s in ordered if stamp(s["outcome_at"]) <= boundary]
    groups = {s["group"] for s in training}
    holdout = [
        s
        for s in ordered
        if stamp(s["feature_at"]) > boundary and s["group"] not in groups
    ]
    if (
        len(training) < 16
        or len(holdout) < 8
        or set(s["label"] for s in training) != {0, 1}
        or set(s["label"] for s in holdout) != {0, 1}
    ):
        raise ValueError("learning_temporal_group_split_insufficient")
    return training, holdout


def train(task, samples, cutoff):
    training, holdout = split(samples, cutoff)
    keys = FEATURES[task]
    matrix = [[features(task, s["features"])[k] for k in keys] for s in training]
    n = len(matrix)
    width = len(keys)
    means = [sum(row[j] for row in matrix) / n for j in range(width)]
    scales = [
        max(1.0, (sum((row[j] - means[j]) ** 2 for row in matrix) / n) ** 0.5)
        for j in range(width)
    ]
    x = [[(row[j] - means[j]) / scales[j] for j in range(width)] for row in matrix]
    y = [s["label"] for s in training]
    prior = sum(y) / n
    weights = [0.0] * width
    bias = math.log(prior / (1 - prior))
    for _ in range(400):
        errors = [
            sigmoid(bias + sum(a * b for a, b in zip(weights, row))) - label
            for row, label in zip(x, y)
        ]
        bias -= 0.1 * sum(errors) / n
        weights = [
            w - 0.1 * (sum(e * row[j] for e, row in zip(errors, x)) / n + 0.01 * w)
            for j, w in enumerate(weights)
        ]
    artifact = dict(
        algorithm=ALGORITHM,
        task=task,
        feature_keys=keys,
        weights=weights,
        bias=bias,
        mean=means,
        scale=scales,
        baseline=prior,
        training_count=n,
        cutoff=cutoff,
    )
    scores = [score(artifact, s["features"]) for s in holdout]
    labels = [s["label"] for s in holdout]
    candidate = metrics(labels, scores)
    baseline = metrics(labels, [prior] * len(holdout))
    grouped = defaultdict(list)
    for i, s in enumerate(holdout):
        grouped[s["program"] + ":" + s["stage"]].append(i)
    segments = {
        key: dict(
            candidate=metrics([labels[i] for i in ii], [scores[i] for i in ii]),
            baseline=metrics([labels[i] for i in ii], [prior] * len(ii)),
        )
        for key, ii in sorted(grouped.items())
    }
    eligible = (
        candidate["brier"] + 0.005 < baseline["brier"]
        and candidate["accuracy"] >= baseline["accuracy"]
        and all(
            s["candidate"]["n"] >= 4
            and s["candidate"]["positives"] >= 1
            and s["candidate"]["negatives"] >= 1
            and s["candidate"]["brier"] <= s["baseline"]["brier"]
            for s in segments.values()
        )
    )
    report = dict(
        candidate=candidate,
        baseline=baseline,
        segments=segments,
        eligible=eligible,
        train_ids=[s["id"] for s in training],
        holdout_ids=[s["id"] for s in holdout],
        excluded_count=len(samples) - n - len(holdout),
        temporal_split=True,
        group_disjoint=True,
    )
    return artifact, report


def drift(artifact, observations):
    if not observations:
        raise ValueError("learning_drift_observations_required")
    values = [features(artifact["task"], o) for o in observations]
    shifts = {
        k: abs(sum(o[k] for o in values) / len(values) - mu) / scale
        for k, mu, scale in zip(
            artifact["feature_keys"], artifact["mean"], artifact["scale"], strict=True
        )
    }
    return dict(
        method="training_standardized_mean_shift",
        n=len(values),
        features=shifts,
        max_shift=max(shifts.values()),
        review_required=max(shifts.values()) > 3,
    )
