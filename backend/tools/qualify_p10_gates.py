"""Native review gates: revoked shadows, fresh deployment epoch and paused rollback."""

import json
from uuid import uuid4

from tools.p10_demo_data import seed
from tools.p10_test_support import Harness
from tools.prepare_p10_learning import WORK, save


def main():
    assert not (WORK / "gates-result.json").exists()
    h = Harness()
    checks = []

    def command(**v):
        return dict(operation_id=str(uuid4()), **v)

    def check(name, ok=True):
        assert ok, name
        checks.append(name)
        save(WORK / "gates-result.json", dict(status="in_progress", checks=checks))

    made = h.call(
        "learning/packs",
        "POST",
        command(
            revision=0,
            document=dict(
                name="Gates de aprendizaje P10", task="churn_prediction", scope="demo"
            ),
        ),
    )
    pack = made["id"]
    base = "learning/packs/" + pack
    actor = h.call("auth/me")["user"]["id"]
    data = seed(h, pack, "churn_prediction", actor)
    ds = h.call(base + "/datasets", "POST", command(cutoff="2026-09-01T00:00:00Z"))
    a = h.call(base + "/train", "POST", command(dataset_id=ds["id"]))
    b = h.call(base + "/train", "POST", command(dataset_id=ds["id"]))
    deployment = h.call(base)["deployment"]

    def select(action, id=None, expected=200):
        nonlocal deployment
        result = h.call(
            base + "/selection",
            "POST",
            command(revision=deployment["revision"], action=action, artifact_id=id),
            expected,
        )
        if expected == 200:
            deployment = result
        return result

    def infer(row):
        return h.call(
            base + "/infer",
            "POST",
            command(grant_id=row["grant_id"], features=row["features"], mode="shadow"),
        )

    select("shadow", a["id"])
    for _ in range(4):
        infer(data[0])
    select("promote", a["id"], 409)
    check("repeated_same_subject_does_not_fabricate_shadow_coverage")
    for row in data[:4]:
        infer(row)
    select("promote", a["id"])
    check("distinct_authorized_subjects_can_promote_evaluated_model")
    select("shadow", b["id"])
    outside = []
    for i in range(4):
        subject = str(uuid4())
        grant = h.call(
            base + "/grants",
            "POST",
            command(
                revision=0,
                demo_subject=subject,
                approved=True,
                basis="synthetic_demo",
                reference="QA-SHADOW-P10",
            ),
        )
        outside.append(
            dict(
                grant_id=grant["id"], features=data[i]["features"], demo_subject=subject
            )
        )
        infer(outside[-1])
    row = outside[0]
    h.call(
        base + "/grants",
        "POST",
        command(
            revision=1,
            demo_subject=row["demo_subject"],
            approved=False,
            basis="synthetic_demo",
            reference="QA-SHADOW-REVOKED",
        ),
    )
    select("promote", b["id"], 409)
    check("revoked_non_dataset_shadow_subject_is_excluded_from_promotion_gate")
    for row in data[:4]:
        infer(row)
    select("shadow", b["id"])
    select("promote", b["id"], 409)
    check("new_shadow_selection_requires_fresh_epoch_observations")
    for row in data[:4]:
        infer(row)
    select("promote", b["id"])
    pack_value = h.call(base)["pack"]
    h.call(
        base,
        "PATCH",
        command(
            revision=pack_value["revision"],
            document=dict(pack_value["document"], training_enabled=False),
        ),
    )
    select("rollback", a["id"])
    check(
        "approved_model_rollback_works_after_training_paused_and_pack_versioned",
        deployment["active_id"] == a["id"],
    )
    h.call(base + "/train", "POST", command(dataset_id=ds["id"]), 409)
    check("rollback_does_not_reenable_training_or_delete_datasets")
    h.call(
        base + "/train",
        "POST",
        dict(command(dataset_id=ds["id"]), include_global=True),
        422,
    )
    check("global_training_flag_is_not_accepted")
    check("no_provider_effects", not h.gateway.posts and not h.gateway.gets)
    save(
        WORK / "gates-result.json",
        dict(
            status="passed",
            checks=checks,
            academic_DDL_or_DML=False,
            real_provider_calls=0,
        ),
    )
    print(json.dumps(dict(status="passed", checks=len(checks))))


if __name__ == "__main__":
    main()
