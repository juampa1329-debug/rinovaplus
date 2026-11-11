"""Native SQL2019 lifecycle acceptance on the P10 fixture only."""

import json
from uuid import uuid4

from tools.p10_demo_data import seed
from tools.p10_test_support import Harness
from tools.prepare_p10_learning import WORK, save


def main():
    assert not (WORK / "api-result.json").exists(), "fresh qualification only"
    h = Harness()
    checks = []

    def check(name, ok=True):
        assert ok, name
        checks.append(name)
        save(WORK / "api-result.json", dict(status="in_progress", checks=checks))

    def command(**v):
        return dict(operation_id=str(uuid4()), **v)

    catalog = h.call("learning/catalog")
    check(
        "four_source_tasks_closed_features_and_numeric_minimization",
        len(catalog["tasks"]) == 4 and not catalog["raw_content_used"],
    )
    module = next(m for m in h.call("runtime")["modules"] if m["id"] == "intelligence")
    check("own_P10_profile_capability_and_module", module["implemented"])
    body = command(
        revision=0,
        document=dict(
            name="SQL aprendizaje · ejemplo",
            task="lead_scoring",
            scope="demo",
            training_enabled=True,
        ),
    )
    p = h.call("learning/packs", "POST", body)
    pack = p["id"]
    base = "learning/packs/" + pack
    check("pack_exact_replay_one_version", h.call("learning/packs", "POST", body) == p)
    h.call(
        "learning/packs",
        "POST",
        dict(body, document=dict(body["document"], name="Conflict")),
        409,
    )
    check("operation_payload_conflict_rejected")
    h.call(base, "PATCH", command(revision=0, document=body["document"]), 409)
    check("pack_CAS_rejects_stale_revision")
    actor = h.call("auth/me")["user"]["id"]
    data = seed(h, pack, "lead_scoring", actor)
    dataset = h.call(base + "/datasets", "POST", command(cutoff="2026-09-01T00:00:00Z"))
    check(
        "dataset_48_training_16_disjoint_future_validation",
        dataset["training_count"] == 48 and dataset["holdout_count"] == 16,
    )
    trained = h.call(base + "/train", "POST", command(dataset_id=dataset["id"]))
    second = h.call(base + "/train", "POST", command(dataset_id=dataset["id"]))
    check(
        "SQL_artifacts_reproduce_parameters_and_evaluation",
        trained["hash"] == second["hash"] and trained["evaluation"]["eligible"],
    )
    selected = h.call(
        base + "/selection",
        "POST",
        command(revision=1, action="shadow", artifact_id=trained["id"]),
    )
    h.call(
        base + "/selection",
        "POST",
        command(
            revision=selected["revision"], action="promote", artifact_id=trained["id"]
        ),
        409,
    )
    check("human_promotion_requires_shadow_observations")
    for row in data[:4]:
        h.call(
            base + "/infer",
            "POST",
            command(grant_id=row["grant_id"], features=row["features"], mode="shadow"),
        )
    selected = h.call(
        base + "/selection",
        "POST",
        command(
            revision=selected["revision"], action="promote", artifact_id=trained["id"]
        ),
    )
    check(
        "human_promotion_of_evaluated_demo_version",
        selected["active_id"] == trained["id"],
    )
    prediction = h.call(
        base + "/infer",
        "POST",
        command(
            grant_id=data[0]["grant_id"], features=data[0]["features"], mode="active"
        ),
    )
    check(
        "versioned_inference_has_baseline_drift_and_no_actions",
        prediction["source"] == "trained_model"
        and not prediction["automatic_action"]
        and prediction["synthetic_demo"],
    )
    selected = h.call(
        base + "/selection",
        "POST",
        command(
            revision=selected["revision"], action="shadow", artifact_id=second["id"]
        ),
    )
    for row in data[:4]:
        h.call(
            base + "/infer",
            "POST",
            command(grant_id=row["grant_id"], features=row["features"], mode="shadow"),
        )
    selected = h.call(
        base + "/selection",
        "POST",
        command(
            revision=selected["revision"], action="promote", artifact_id=second["id"]
        ),
    )
    selected = h.call(
        base + "/selection",
        "POST",
        command(
            revision=selected["revision"], action="rollback", artifact_id=trained["id"]
        ),
    )
    check(
        "approved_version_rollback_preserves_artifacts",
        selected["active_id"] == trained["id"]
        and len(h.call(base + "/artifacts")["items"]) == 2,
    )
    selected = h.call(
        base + "/selection",
        "POST",
        command(revision=selected["revision"], action="pause"),
    )
    h.call(
        base + "/infer",
        "POST",
        command(
            grant_id=data[0]["grant_id"], features=data[0]["features"], mode="active"
        ),
        409,
    )
    check("inference_pause_preserves_samples_and_models")
    selected = h.call(
        base + "/selection",
        "POST",
        command(revision=selected["revision"], action="resume"),
    )
    h.b.request(
        base + "/infer",
        "POST",
        command(grant_id=data[0]["grant_id"], features=data[0]["features"]),
        403,
        csrf=False,
    )
    check("CSRF_required_for_inference_and_changes")
    h.call(
        base + "/grants",
        "POST",
        command(
            revision=1,
            demo_subject=data[0]["demo_subject"],
            approved=False,
            basis="synthetic_demo",
            reference="CBN-DEMO-P10",
        ),
    )
    h.call(
        base + "/infer",
        "POST",
        command(
            grant_id=data[1]["grant_id"], features=data[1]["features"], mode="active"
        ),
        409,
    )
    check("purpose_revocation_invalidates_affected_model_even_for_other_subject")
    check(
        "datasets_samples_artifacts_and_audit_remain_after_revocation",
        len(h.call(base + "/datasets")["items"]) == 1
        and len(h.call(base + "/events")["items"]) >= 5,
    )
    check("zero_provider_effects", not h.gateway.gets and not h.gateway.posts)
    save(
        WORK / "api-result.json",
        dict(
            status="passed",
            checks=checks,
            database=h.settings.connection["database"],
            pack_id=pack,
            real_provider_calls=0,
            academic_DDL_or_DML=False,
        ),
    )
    print(json.dumps({"status": "passed", "checks": len(checks)}))


if __name__ == "__main__":
    main()
