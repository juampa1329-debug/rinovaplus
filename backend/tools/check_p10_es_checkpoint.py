"""Offline P10 checkpoint: partial work, exact frozen P9 replay, no SQL IO."""

import argparse
import copy
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACCEPTED = {"P10.1", "P10.2", "P10.3", "P10.4"}
PENDING = {"P10.close.m4"}
MINIMUM = {
    "api": 16,
    "extras": 15,
    "gates": 8,
    "storage": 12,
    "recovery": 8,
    "boundaries": 6,
}


def read(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))


def sha(p):
    value = hashlib.sha256()
    with Path(p).open("rb") as source:
        while block := source.read(1024 * 1024):
            value.update(block)
    return value.hexdigest()


def require(ok):
    if not ok:
        raise ValueError("invalid_P10_partial_checkpoint")


def validate(p):
    require(
        p["unit"] == "P10-ES"
        and p["status"] == "partial_predecessor_external_gates_pending"
        and p["P10_accepted"] is False
    )
    require(
        p["primary_port"] == 4178 and p["engine"] == 15 and p["compatibility"] == 150
    )
    require(
        p["database"] == "CBN_P10ES_TRIAL_20261028_014cc86f"
        and p["tables"] == 185
        and p["foreign_keys"] == 330
        and p["bindings"] == 155
    )
    require(
        p["academic_DDL_or_DML"] is False
        and p["real_provider_calls"] == 0
        and p["actual_external_receipts"] is False
        and p["actual_Meta_catalog_approved"] is False
    )
    require(
        p["phase_percentages"]["P10"] == "95.00%"
        and p["phase_percentages"]["P4"] == "82.29%"
        and p["phase_percentages"]["P8"] == "95.00%"
        and p["phase_percentages"]["P9"] == "93.75%"
    )
    require(
        p["fixed_criteria"] == 56
        and p["fixed_milestones"] == 279
        and p["done_milestones"] == 252
        and p["accepted_criteria"] == 43
    )
    require(p["overall_technical_percent"] == "90.23%")
    required = {
        "backend/app/institutional/" + n + ".py"
        for n in [
            "learning",
            "learning_models",
            "learning_policy",
            "learning_engine",
            "learning_api",
        ]
    }
    required |= {
        "backend/tools/check_p10_es_checkpoint.py",
        "backend/tools/phase_work_progress.py",
        "frontend/src/institution/LearningWorkspace.tsx",
        "frontend/src/institution/learning.css",
        "compose.learning.yaml",
        "docker/Dockerfile.learning",
        "tasks/p10-es-progress.json",
        "docs/adaptation/phase-work-progress.json",
    }
    require(required <= set(p["source_pins"]))
    for n, h in p["source_pins"].items():
        require(sha(ROOT / n) == h)
    b = read(ROOT / "docs/adaptation/sql/p10_es_input_baseline.json")
    require(
        sha(ROOT / ".local/p10-es/public-preimages.zip") == b["source_archive_sha256"]
    )
    require(
        sha(ROOT / "docs/adaptation/sql/p9_es_validation.json")
        == b["parent_P9_proof_sha256"]
    )
    with zipfile.ZipFile(ROOT / ".local/p10-es/public-preimages.zip") as z:
        for n, t in p["changed_predecessors"].items():
            e = next(v for v in b["files"] if v["path"] == n)
            require(
                hashlib.sha256(z.read(e["archive_name"])).hexdigest()
                == e["sha256"]
                == t["before"]
                and sha(ROOT / n) == t["after"]
            )
    for n, h in p["frozen_releases"].items():
        require(sha(ROOT / n) == h)
    require(
        sha(ROOT / "backend/migrations/cbn_ads_operations_v2/release.json")
        == p["base_release_sha256"]
    )
    require(
        sha(ROOT / "backend/migrations/cbn_learning_operations_v1/release.json")
        == p["release_sha256"]
    )
    review = read(ROOT / "artifacts/p10-es/acceptance-review.json")
    require(
        review["P10_accepted"] is False
        and set(review["accepted_criteria"]) == ACCEPTED
        and set(review["pending_milestones"]) == PENDING
        and review["dependency_P8_P9_pending"]
    )
    for n, h in review["evidence"].items():
        require(sha(ROOT / n) == h)
    for n, count in MINIMUM.items():
        r = read(ROOT / ("artifacts/p10-es/" + n + "-result.json"))
        require(r["status"] == "passed" and len(r["checks"]) >= count)
    for n in [
        "compile",
        "demo",
        "preservation",
        "restart",
        "deployment",
        "media",
        "parent-replay",
    ]:
        require(
            read(ROOT / ("artifacts/p10-es/" + n + "-result.json"))["status"]
            == "passed"
        )
    require(len(read(ROOT / "artifacts/p10-es/browser/result.json")["checks"]) >= 30)
    require(
        len(read(ROOT / "artifacts/p10-es/browser/final-result.json")["checks"]) >= 12
    )
    checks = read(ROOT / "artifacts/p10-es/final-checks.json")
    require(
        checks["status"] == "passed"
        and checks["checks"]["backend"]["passed"] >= 419
        and checks["checks"]["frontend"]["passed"] >= 351
    )
    deployment = read(ROOT / "artifacts/p10-es/deployment-result.json")
    require(
        deployment["image_digest"] == p["image_digest"]
        and deployment["image_tag"] == "crm-cbn-workspace:p10es-r2"
        and deployment["old_P9_container_retained_stopped"]
        and deployment["runtime_Python_application_files_match_workspace"] == 222
    )
    require(
        read(ROOT / "artifacts/p10-es/recovery-result.json")["stable_tables"] == 171
    )
    require(
        read(ROOT / "artifacts/p10-es/recovery-result.json")["ready_blobs_copied"] == 4
    )
    require(
        read(ROOT / "artifacts/p10-es/media-result.json")["copied_ready_blobs"] == 4
    )
    require(read(ROOT / "artifacts/p10-es/restart-result.json")["stable_tables"] == 182)
    require(
        len(p["memory_transitions"]) == 13
        and all(t["before"] != t["after"] for t in p["memory_transitions"].values())
    )
    work = read(ROOT / "docs/adaptation/phase-work-progress.json")
    require(
        work["summary"]["overall_technical_percent_display"]
        == p["overall_technical_percent"]
    )
    for n in ["existing", "reference"]:
        review = read(ROOT / ("artifacts/p10-es/" + n + "-review-final.json"))
        entries = review.get("source_manifest", []) + review.get("source_pins", [])
        for entry in entries:
            name = entry.get("path", entry.get("source_file"))
            require(name is not None and sha(ROOT / name) == entry["sha256"])
    original_reader = next(
        e for e in b["files"] if e["path"] == "backend/tools/es_schema_catalog_v2.py"
    )
    require(sha(ROOT / original_reader["path"]) == original_reader["sha256"])

    return dict(
        status="passed",
        P10="95.00%",
        overall=p["overall_technical_percent"],
        accepted_P10_criteria=sorted(ACCEPTED),
        pending_dependencies=sorted(PENDING),
        source_pins=len(p["source_pins"]),
        memory_transitions=13,
        SQL_connected=False,
    )


def replay_parent():
    from p10_parent_replay import replay_parent as replay

    result = replay()
    return {k: v for k, v in result.items() if k != "result"}


def self_test(proof):
    cases = [
        ("engine", 16),
        ("compatibility", 160),
        ("primary_port", 4173),
        ("real_provider_calls", 1),
        ("academic_DDL_or_DML", True),
        ("database", "HORARIOSSIIE"),
        ("done_milestones", 279),
        ("accepted_criteria", 56),
        ("P10_accepted", True),
        ("actual_Meta_catalog_approved", True),
        ("actual_external_receipts", True),
        ("tables", 167),
        ("overall_technical_percent", "100.00%"),
    ]
    for k, v in cases:
        bad = copy.deepcopy(proof)
        bad[k] = v
        try:
            validate(bad)
        except (ValueError, AssertionError):
            pass
        else:
            raise AssertionError("false_P10_completion_accepted")
    return len(cases)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--replay-parent", action="store_true")
    args = parser.parse_args()
    result = validate(read(ROOT / "docs/adaptation/sql/p10_es_validation.json"))
    from p10_es_graphs import check as graph_check
    from phase_work_progress import check

    result["work_progress"] = check(negatives=args.self_test)
    result["graph"] = graph_check()
    if args.self_test:
        result["negative_cases_rejected"] = self_test(
            read(ROOT / "docs/adaptation/sql/p10_es_validation.json")
        )
    if args.replay_parent:
        result["parent"] = replay_parent()
    print(json.dumps(result, ensure_ascii=False))
