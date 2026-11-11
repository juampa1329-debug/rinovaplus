"""Offline P7 partial checkpoint, evidence boundaries and frozen P6 replay."""

import argparse
import copy
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACCEPTED = {"P7.2", "P7.3"}
PENDING = {"P7.1.m5", "P7.1.m7", "P7.4.m4", "P7.4.m5", "P7.close.m5"}
MINIMUM = {
    "api": 15,
    "runtime": 22,
    "extras": 6,
    "storage": 12,
    "recovery": 7,
    "catalog": 5,
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(value):
    if not value:
        raise ValueError("invalid_P7_partial_checkpoint")


def validate(proof):
    require(
        proof["unit"] == "P7-ES"
        and proof["P7_accepted"] is False
        and proof["status"] == "partial_external_gates_pending"
    )
    require(
        proof["primary_port"] == 4178
        and proof["engine"] == 15
        and proof["compatibility"] == 150
    )
    require(
        proof["database"] == "CBN_P7ES_TRIAL_20261027_c305e024"
        and proof["academic_DDL_or_DML"] is False
        and proof["real_provider_calls"] == 0
    )
    require(
        proof["actual_Meta_catalog_approved"] is False
        and proof["actual_external_receipts"] is False
    )
    require(
        proof["phase_percentages"]["P7"] == "82.29%"
        and proof["phase_percentages"]["P4"] == "82.29%"
        and proof["phase_percentages"]["P6"] == "100.00%"
    )
    require(
        proof["fixed_milestones"] == 279
        and proof["fixed_criteria"] == 56
        and proof["done_milestones"] == 201
        and proof["accepted_criteria"] == 33
    )
    require(
        proof["tables"] == 160
        and proof["foreign_keys"] == 266
        and proof["bindings"] == 130
    )
    required = {
        "backend/app/institutional/" + n + ".py"
        for n in [
            "broadcasts",
            "broadcast_api",
            "broadcast_models",
            "broadcast_templates",
            "broadcast_dispatch",
            "broadcast_policy",
            "channel_outbox",
            "channel_events",
            "channel_workers",
            "spanish",
        ]
    }
    required |= {
        "frontend/src/institution/BroadcastWorkspace.tsx",
        "backend/tools/foundation_snapshot.py",
        "backend/tools/qualify_p7_catalog.py",
        "backend/tools/check_p7_es_checkpoint.py",
        "compose.broadcast.yaml",
        "docker/Dockerfile.broadcast",
        "tasks/p7-es-progress.json",
        "docs/adaptation/phase-work-progress.json",
    }
    require(required <= set(proof["source_pins"]))
    for name, expected in proof["source_pins"].items():
        require(sha(ROOT / name) == expected)
    baseline = read(ROOT / "docs/adaptation/sql/p7_es_input_baseline.json")
    require(
        sha(ROOT / ".local/p7-es/public-preimages.zip")
        == baseline["source_archive_sha256"]
    )
    require(
        sha(ROOT / "docs/adaptation/sql/p6_es_validation.json")
        == baseline["parent_P6_proof_sha256"]
    )
    with zipfile.ZipFile(ROOT / ".local/p7-es/public-preimages.zip") as archive:
        for name, transition in proof["changed_predecessors"].items():
            entry = next(v for v in baseline["files"] if v["path"] == name)
            require(
                hashlib.sha256(archive.read(entry["archive_name"])).hexdigest()
                == transition["before"]
                == entry["sha256"]
            )
            require(sha(ROOT / name) == transition["after"])
    for name, expected in proof["frozen_releases"].items():
        require(sha(ROOT / name) == expected)
    require(
        sha(ROOT / ("backend/migrations/cbn_broadcast_operations_v1/release.json"))
        == proof["release_sha256"]
    )
    review = read(ROOT / "artifacts/p7-es/acceptance-review.json")
    require(
        review["P7_accepted"] is False
        and set(review["accepted_criteria"]) == ACCEPTED
        and set(review["pending_milestones"]) == PENDING
        and review["dependency_P4_pending"]
    )
    for name, expected in review["evidence"].items():
        require(sha(ROOT / name) == expected)
    for name, minimum in MINIMUM.items():
        report = read(ROOT / ("artifacts/p7-es/" + name + "-result.json"))
        require(report["status"] == "passed" and len(report["checks"]) >= minimum)
    for name in [
        "compile",
        "demo",
        "preservation",
        "restart",
        "deployment",
        "media",
        "parent-replay",
    ]:
        require(
            read(ROOT / ("artifacts/p7-es/" + name + "-result.json"))["status"]
            == "passed"
        )
    require(len(read(ROOT / "artifacts/p7-es/browser/result.json")["checks"]) >= 18)
    require(
        len(read(ROOT / "artifacts/p7-es/browser/final-result.json")["checks"]) >= 7
    )
    checks = read(ROOT / "artifacts/p7-es/final-checks.json")
    require(
        checks["status"] == "passed"
        and checks["checks"]["backend"]["passed"] >= 322
        and checks["checks"]["frontend"]["passed"] >= 323
    )
    deployment = read(ROOT / "artifacts/p7-es/deployment-result.json")
    require(
        deployment["image_digest"] == proof["image_digest"]
        and deployment["image_tag"] == "crm-cbn-workspace:p7es-r3"
        and deployment["old_P6_container_retained_stopped"]
        and deployment["runtime_Python_application_files_match_workspace"] == 202
    )
    require(
        not read(ROOT / "graphify-out/p7-es/source-manifest.json")["old_graphs_rebuilt"]
    )
    return dict(
        status="passed",
        P7="82.29%",
        accepted_P7_criteria=sorted(ACCEPTED),
        pending_real_provider_gates=sorted(PENDING),
        source_pins=len(proof["source_pins"]),
        memory_transitions=len(proof["memory_transitions"]),
        SQL_connected=False,
    )


def replay_parent():
    baseline = read(ROOT / "docs/adaptation/sql/p7_es_input_baseline.json")
    archive = ROOT / ".local/p7-es/public-preimages.zip"
    require(sha(archive) == baseline["source_archive_sha256"])
    base = ROOT / ".local/r7"
    target = base / "CRM_CBN"
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zipped:
        for entry in baseline["files"]:
            raw = zipped.read(entry["archive_name"])
            require(hashlib.sha256(raw).hexdigest() == entry["sha256"])
            p = (target / entry["path"]).resolve()
            require(p.is_relative_to(base.resolve()))
            if p.exists():
                require(p.read_bytes() == raw)
            else:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(raw)
    require(
        sha(target / "docs/adaptation/sql/p6_es_validation.json")
        == baseline["parent_P6_proof_sha256"]
    )
    result = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-B",
            "tools/check_p6_es_checkpoint.py",
            "--self-test",
            "--replay-parent",
        ],
        cwd=target / "backend",
        capture_output=True,
    )
    require(result.returncode == 0)
    return dict(
        status="passed",
        exact_preimages=len(baseline["files"]),
        parent_checker_bytes_modified=False,
        SQL_connected=False,
    )


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
        ("P7_accepted", True),
        ("actual_Meta_catalog_approved", True),
        ("actual_external_receipts", True),
        ("tables", 153),
    ]
    for key, value in cases:
        bad = copy.deepcopy(proof)
        bad[key] = value
        try:
            validate(bad)
        except (ValueError, AssertionError):
            pass
        else:
            raise AssertionError("false_P7_completion_accepted")
    return len(cases)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--replay-parent", action="store_true")
    args = parser.parse_args()
    proof = read(ROOT / "docs/adaptation/sql/p7_es_validation.json")
    result = validate(proof)
    from p7_es_graphs import check as graph_check
    from phase_work_progress import check

    result["work_progress"] = check(negatives=args.self_test)
    result["graph"] = graph_check()
    if args.self_test:
        result["negative_cases_rejected"] = self_test(proof)
    if args.replay_parent:
        result["parent"] = replay_parent()
    print(json.dumps(result, ensure_ascii=False))
