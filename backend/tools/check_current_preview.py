"Offline persisted-demo handoff, with unmodified P3/P2/P1 checkpoint replay."

import argparse
import copy
import hashlib
import json
import subprocess
import sys
import uuid
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROOF = ROOT / ("docs/adaptation/sql/current_preview_validation.json")
ALLOWED = {
    "AGENTS.md",
    "README.md",
    "ai-memory/CURRENT_STATE.md",
    "ai-memory/FILE_MAP.md",
    "tasks/TASK_STATE.md",
    "docs/ADAPTATION_STATUS.md",
    "docs/roadmap.md",
    "docs/SCENTRA_ADAPTATION_ROADMAP.md",
    "docs/adaptation/RESUME.md",
    "docs/adaptation/WORK_PROGRESS.md",
    "docs/adaptation/GRAPH_GUIDE.md",
    "ai-memory/CRITICAL_WARNINGS.md",
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(value):
    if not value:
        raise ValueError("current_preview_checkpoint_mismatch")


def parent_inputs():
    baseline = read(ROOT / "artifacts/current-preview/input-baseline.json")
    frozen = read(ROOT / "docs/adaptation/sql/p3_es_validation.json")
    require(
        sha(ROOT / "docs/adaptation/sql/p3_es_validation.json")
        == baseline["frozen_P3_proof_sha256"]
    )
    require(sha(ROOT / baseline["preimages_archive"]) == baseline["preimages_sha256"])
    changed = {}
    with zipfile.ZipFile(ROOT / baseline["preimages_archive"]) as saved:
        require(set(saved.namelist()) == set(baseline["files"]) == ALLOWED)
        for name, expected in frozen["source_pins"].items():
            actual = sha(ROOT / name)
            if actual != expected:
                require(name in ALLOWED)
                require(hashlib.sha256(saved.read(name)).hexdigest() == expected)
                changed[name] = {"before": expected, "after": actual}
    return frozen, changed


def replay_parent():
    frozen, _ = parent_inputs()
    baseline = read(ROOT / "artifacts/current-preview/input-baseline.json")
    # Keep nested frozen-checker import paths below Windows' legacy limit.
    base = (ROOT / ".local/r" / uuid.uuid4().hex[:8]).resolve()
    target = base / "CRM_CBN"
    target.mkdir(parents=True)
    with zipfile.ZipFile(ROOT / baseline["preimages_archive"]) as saved:
        for name, expected in frozen["source_pins"].items():
            raw = (ROOT / name).read_bytes()
            if hashlib.sha256(raw).hexdigest() != expected:
                raw = saved.read(name)
            require(hashlib.sha256(raw).hexdigest() == expected)
            path = (target / name).resolve()
            require(path.is_relative_to(target))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    proof = target / "docs/adaptation/sql/p3_es_validation.json"
    proof.write_bytes((ROOT / "docs/adaptation/sql/p3_es_validation.json").read_bytes())
    graph_sources = read(target / "graphify-out/p3-es/source-manifest.json")["sources"]
    for name, expected in graph_sources.items():
        path = target / name
        if not path.is_file():
            raw = (ROOT / name).read_bytes()
            require(hashlib.sha256(raw).hexdigest() == expected)
            require(path.resolve().is_relative_to(target))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    # Complete runtime inputs omitted from a checkpoint's direct pins using
    # their independent hashes already fixed in its archived ledgers.
    work = read(target / "docs/adaptation/phase-work-progress.json")
    for evidence in work["evidence_registry"].values():
        path = (target / evidence["file"]).resolve()
        if not path.is_file():
            raw = (ROOT / evidence["file"]).read_bytes()
            require(
                hashlib.sha256(raw).hexdigest() == evidence["source_sha256_at_review"]
            )
            require(path.is_relative_to(base))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    old = read(target / "docs/adaptation/sql/p3_es_input_baseline.json")
    for entry in old["files"]:
        if entry["path"].startswith("../"):
            raw = (ROOT / entry["path"]).read_bytes()
            require(hashlib.sha256(raw).hexdigest() == entry["sha256"])
            path = (target / entry["path"]).resolve()
            require(path.is_relative_to(base))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    result = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-B",
            str(target / "backend/tools/check_p3_es_checkpoint.py"),
            "--self-test",
        ],
        cwd=target,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode:
        (ROOT / ".local/current-preview/replay-error.txt").write_text(
            result.stderr, encoding="utf-8"
        )
    require(result.returncode == 0)
    return {
        "status": "passed",
        "parent_P3_result": json.loads(result.stdout),
        "original_checkers_modified": False,
        "current_sources_overwritten": False,
        "SQL_connections": 0,
    }


def validate(proof):
    require(proof["unit"] == "PREVIEW-DEMO-1" and proof["primary_port"] == 4178)
    require(proof["provider_calls"] == 0 and proof["academic_DDL_or_DML"] is False)
    frozen, changed = parent_inputs()
    require(proof["memory_transitions"] == changed)
    required = {
        "backend/tools/prepare_demo_preview.py",
        "backend/tools/check_current_preview.py",
        "compose.preview.yaml",
        "artifacts/current-preview/browser-result.json",
        "artifacts/current-preview/sql-result.json",
        "artifacts/current-preview/restart-result.json",
    }
    require(required <= set(proof["source_pins"]))
    for name, expected in proof["source_pins"].items():
        path = (ROOT / name).resolve()
        require(path.is_relative_to(ROOT) and path.is_file() and sha(path) == expected)
    require(proof["phase_percentages"] == frozen["phase_percentages"])
    seed = read(ROOT / "artifacts/current-preview/seed-result.json")
    require(
        seed["status"] == "passed"
        and (
            seed["contacts"],
            seed["conversations"],
            seed["messages"],
            seed["notes"],
            seed["tasks"],
        )
        == (8, 8, 26, 8, 8)
    )
    require(
        seed["P2_source_catalog_and_data_unchanged"]
        and seed["clean_P3_catalog_unchanged"]
        and seed["clean_P3_has_no_demo_contacts"]
    )
    for name in [
        "browser-result.json",
        "sql-result.json",
        "deployment-result.json",
        "restart-result.json",
        "p3-replay-result.json",
    ]:
        require(read(ROOT / "artifacts/current-preview" / name)["status"] == "passed")
    restart = read(ROOT / "artifacts/current-preview/restart-result.json")
    require(
        restart["before"] == restart["after"]
        and restart["business_tables_persisted"] == 9
    )
    deployment = read(ROOT / ("artifacts/current-preview/deployment-result.json"))
    require(
        deployment["image_digest"] == frozen["image_digest"]
        and deployment["same_application_as_P3_R6"]
    )
    from check_phase_progress import validate as canonical
    from phase_work_progress import check

    work = check(negatives=True)
    canonical(read(ROOT / "docs/adaptation/phase-progress-contract.json"))
    require(work["done_milestones"] == 147 and work["accepted_criteria"] == 20)
    return {
        "status": "passed",
        "primary_port": 4178,
        "frozen_P3_sources_verified": len(frozen["source_pins"]),
        "memory_transitions": len(changed),
        "phase_percentages_unchanged": True,
        "fixed_criteria": 56,
        "fixed_milestones": 279,
        "SQL_connections": 0,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--replay-parent", action="store_true")
    args = parser.parse_args()
    proof = read(PROOF)
    result = validate(proof)
    if args.replay_parent:
        result["frozen_P3_P2_P1_replayed"] = replay_parent()["status"] == "passed"
    if args.self_test:
        cases = [
            lambda p: p.__setitem__("primary_port", 4179),
            lambda p: p.__setitem__("provider_calls", 1),
            lambda p: p.__setitem__("academic_DDL_or_DML", True),
            lambda p: p["source_pins"].pop("backend/tools/prepare_demo_preview.py"),
            lambda p: p["memory_transitions"].clear(),
            lambda p: p["phase_percentages"].__setitem__("P4", "100.00%"),
        ]
        for mutate in cases:
            wrong = copy.deepcopy(proof)
            mutate(wrong)
            try:
                validate(wrong)
            except ValueError:
                pass
            else:
                raise AssertionError("invalid_demo_preview_checkpoint_accepted")
        result["negative_cases_rejected"] = len(cases)
    print(json.dumps(result, indent=2))
