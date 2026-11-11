"""One-shot fictitious P10 preview data. No labels or consent inferred for people."""

import json
from uuid import uuid4

from tools.p10_demo_data import seed
from tools.p10_test_support import Harness
from tools.prepare_p10_learning import WORK, save


def main():
    assert not (WORK / "demo-result.json").exists(), "do not reseed a populated preview"
    h = Harness("final-v2")
    assert not h.call("learning/packs")["items"]
    actor = h.call("auth/me")["user"]["id"]
    catalog = h.call("learning/catalog")
    stage = catalog["stages"][0]["id"]
    programs = [str(v["id"]) for v in catalog["programs"][:2]] or ["general"]

    def command(**v):
        return dict(operation_id=str(uuid4()), **v)

    results = []
    for task, title in [
        ("lead_scoring", "Priorización de aspirantes"),
        ("churn_prediction", "Riesgo de abandono"),
        ("smart_remarketing", "Seguimiento educativo"),
        ("operational_anomaly", "Salud de operaciones"),
    ]:
        p = h.call(
            "learning/packs",
            "POST",
            command(
                revision=0,
                document=dict(
                    name=title + " · Ejemplo ficticio",
                    task=task,
                    scope="demo",
                    training_enabled=True,
                ),
            ),
        )
        base = "learning/packs/" + p["id"]
        data = seed(h, p["id"], task, actor, program=programs, stage=stage)
        dataset = h.call(
            base + "/datasets", "POST", command(cutoff="2026-09-01T00:00:00Z")
        )
        artifact = h.call(base + "/train", "POST", command(dataset_id=dataset["id"]))
        assert artifact["evaluation"]["eligible"]
        selected = h.call(
            base + "/selection",
            "POST",
            command(revision=1, action="shadow", artifact_id=artifact["id"]),
        )
        for row in data[:4]:
            h.call(
                base + "/infer",
                "POST",
                command(
                    grant_id=row["grant_id"], features=row["features"], mode="shadow"
                ),
            )
        selected = h.call(
            base + "/selection",
            "POST",
            command(
                revision=selected["revision"],
                action="promote",
                artifact_id=artifact["id"],
            ),
        )
        assert selected["active_id"] == artifact["id"]
        h.call(
            base + "/infer",
            "POST",
            command(
                grant_id=data[0]["grant_id"],
                features=data[0]["features"],
                mode="active",
            ),
        )
        results.append(
            dict(
                pack_id=p["id"],
                task=task,
                artifact_id=artifact["id"],
                artifact_hash=artifact["hash"],
                dataset_hash=dataset["hash"],
                samples=64,
                evaluation=artifact["evaluation"],
                synthetic_demo=True,
            )
        )
    assert not h.gateway.posts and not h.gateway.gets
    save(
        WORK / "demo-result.json",
        dict(
            status="passed",
            packs=results,
            total_packs=4,
            total_samples=256,
            total_predictions=20,
            synthetic_demo=True,
            real_institution_effectiveness_claimed=False,
            raw_content_used=False,
            real_provider_calls=0,
            academic_DDL_or_DML=False,
        ),
    )
    print(
        json.dumps(dict(status="passed", packs=4, samples=256, real_provider_calls=0))
    )


if __name__ == "__main__":
    main()
