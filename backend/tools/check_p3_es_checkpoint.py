"Offline P3 checkpoint and frozen P2/P1 replay; no database connections."

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
PROOF = ROOT / "docs/adaptation/sql/p3_es_validation.json"
RELEASE = "7d4c3f55654d8d683246c2cd2547d29da5274825170f304b2c6b069e914d379b"
PARENT = "1a7ba0dc7435e1e5dd61b431cca7f2164d698d4b4b6df9dd53cd66e8b40b10b4"
ARCHIVE = "artifacts/p3-es/history/p2-public-preimages.zip"
ALLOWED = {
    "AGENTS.md",
    "README.md",
    "docs/roadmap.md",
    "docs/ADAPTATION_STATUS.md",
    "docs/SCENTRA_ADAPTATION_ROADMAP.md",
    "docs/adaptation/GRAPH_GUIDE.md",
    "docs/adaptation/WORK_PROGRESS.md",
    "docs/adaptation/RESUME.md",
    "ai-memory/CURRENT_STATE.md",
    "ai-memory/FILE_MAP.md",
    "ai-memory/CRITICAL_WARNINGS.md",
    "tasks/TASK_STATE.md",
    "docs/adaptation/phase-progress-contract.json",
    "docs/adaptation/phase-work-progress.json",
    "backend/tools/p2_es_recovery.py",
    "frontend/src/institution/InstitutionApp.tsx",
    "frontend/src/shared/workspaceSession.tsx",
    *[
        "backend/app/institutional/" + name + ".py"
        for name in ["api", "auth", "spanish", "store"]
    ],
}
MANDATORY = {
    "backend/tools/check_p3_es_checkpoint.py",
    "backend/tools/p3_es_graphs.py",
    "backend/app/institutional/workspace.py",
    "backend/app/institutional/workspace_policy.py",
    "frontend/src/institution/Workspace.tsx",
    "frontend/src/shared/workspaceSession.tsx",
    "docs/adaptation/phase-work-progress.json",
    "docs/adaptation/phase-progress-contract.json",
    "docs/adaptation/sql/p3_es_input_baseline.json",
    "artifacts/p3-es/acceptance-review.json",
    "graphify-out/p3-es/source-manifest.json",
    "artifacts/p3-es/p2-replay-result.json",
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(value):
    if not value:
        raise ValueError("P3ES_checkpoint_mismatch")


def replay_parent():
    baseline = read(ROOT / "docs/adaptation/sql/p3_es_input_baseline.json")
    require(digest(ROOT / ARCHIVE) == baseline["source_archive_sha256"])
    base = (ROOT / ".local/p3-es" / ("checkpoint-replay-" + uuid.uuid4().hex)).resolve()
    target = base / "CRM_CBN"
    target.mkdir(parents=True)
    with zipfile.ZipFile(ROOT / ARCHIVE) as saved:
        require(
            set(saved.namelist())
            == {entry["archive_name"] for entry in baseline["files"]}
        )
        for entry in baseline["files"]:
            raw = saved.read(entry["archive_name"])
            require(hashlib.sha256(raw).hexdigest() == entry["sha256"])
            path = (target / entry["path"]).resolve()
            require(path.is_relative_to(base))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    # P2 did not include its own input registry among its source pins.
    # Supply that public registry separately and verify every entry against
    # the immutable archive hash already pinned by the frozen P2 proof.
    support = ROOT / ("artifacts/p3-es/history/p2-es-input-baseline.json")
    parent_proof = read(target / "docs/adaptation/sql/p2_es_validation.json")
    registry = read(support)
    require(len(registry["files"]) == 872)
    parent_archive = target / "artifacts/p2-es/history/p1-public-preimages.zip"
    require(
        digest(parent_archive)
        == registry["source_archive_sha256"]
        == parent_proof["preimages_sha256"]
    )
    with zipfile.ZipFile(parent_archive) as saved:
        require(set(saved.namelist()) == {e["archive_name"] for e in registry["files"]})
        for entry in registry["files"]:
            require(
                hashlib.sha256(saved.read(entry["archive_name"])).hexdigest()
                == entry["sha256"]
            )
    (target / "docs/adaptation/sql/p2_es_input_baseline.json").write_bytes(
        support.read_bytes()
    )
    ledger_file = "docs/adaptation/phase-work-progress.json"
    require(digest(target / ledger_file) == parent_proof["source_pins"][ledger_file])
    evidence_registry = read(target / ledger_file)["evidence_registry"]
    supplement = read(ROOT / "artifacts/p3-es/p2-replay-support.json")
    require(digest(ROOT / supplement["archive"]) == supplement["archive_sha256"])
    with zipfile.ZipFile(ROOT / supplement["archive"]) as saved:
        require(
            set(saved.namelist()) == {e["archive_name"] for e in supplement["files"]}
        )
        for entry in supplement["files"]:
            require(
                any(
                    e["file"] == entry["path"]
                    and e["source_sha256_at_review"] == entry["sha256"]
                    for e in evidence_registry.values()
                )
            )
            raw = saved.read(entry["archive_name"])
            require(hashlib.sha256(raw).hexdigest() == entry["sha256"])
            path = (target / entry["path"]).resolve()
            require(path.is_relative_to(base))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    require(
        digest(target / "docs/adaptation/sql/p2_es_validation.json")
        == baseline["parent_P2_proof_sha256"]
    )
    result = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-B",
            str(target / "backend/tools/check_p2_es_checkpoint.py"),
            "--self-test",
        ],
        cwd=target,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode:
        (ROOT / ".local/p3-es/parent-replay-last-error.txt").write_text(
            result.stderr, encoding="utf-8"
        )
    require(result.returncode == 0)
    value = json.loads(result.stdout)
    require(value["P2"] == "100.00%" and value["frozen_P1_checker_replayed"])
    receipt = ROOT / "artifacts/p3-es/p2-replay-result.json"
    if receipt.is_file():
        require(read(receipt)["replayed_result"] == value)
    return dict(
        status="passed",
        preimages=len(baseline["files"]),
        archive=ARCHIVE,
        frozen_P2_and_P1_checkers_replayed=True,
        replayed_result=value,
        independently_verified_public_registry_supplements=1 + len(supplement["files"]),
        current_sources_overwritten=False,
        SQL_connections=0,
    )


def validate(proof):
    require(
        proof["unit"] == "P3-ES"
        and proof["P3_accepted"] is True
        and proof["institutional_production_accepted"] is False
    )
    package = ROOT / "backend/migrations/cbn_workspace_spanish_v1"
    require(digest(package / "release.json") == proof["release_sha256"] == RELEASE)
    release = read(package / "release.json")
    require(len(release["files"]) == 3)
    for name, expected in release["files"].items():
        require(digest(package / name) == expected)
    parent = ROOT / ("backend/migrations/cbn_institutional_spanish_v1/release.json")
    require(digest(parent) == proof["parent_P2_release_sha256"] == PARENT)
    for name, expected in read(parent)["inputs"].items():
        require(digest(ROOT / name) == expected)
    baseline = read(ROOT / "docs/adaptation/sql/p3_es_input_baseline.json")
    require(
        len(baseline["files"]) == 993
        and digest(ROOT / ARCHIVE)
        == proof["preimages_sha256"]
        == baseline["source_archive_sha256"]
    )
    require(
        digest(ROOT / "docs/adaptation/sql/p2_es_validation.json")
        == baseline["parent_P2_proof_sha256"]
    )
    changed = {}
    with zipfile.ZipFile(ROOT / ARCHIVE) as saved:
        require(
            set(saved.namelist())
            == {entry["archive_name"] for entry in baseline["files"]}
        )
        for entry in baseline["files"]:
            require(
                hashlib.sha256(saved.read(entry["archive_name"])).hexdigest()
                == entry["sha256"]
            )
            current = digest((ROOT / entry["path"]).resolve())
            if current != entry["sha256"]:
                require(entry["path"] in ALLOWED)
                changed[entry["path"]] = dict(
                    before=entry["sha256"],
                    after=current,
                    archive_name=entry["archive_name"],
                )
    require(changed == proof["changed_predecessors"])
    require(MANDATORY <= set(proof["source_pins"]))
    for name, expected in proof["source_pins"].items():
        path = (ROOT / name).resolve()
        require(
            path.is_relative_to(ROOT) and path.is_file() and digest(path) == expected
        )
    review = read(ROOT / "artifacts/p3-es/acceptance-review.json")
    require(review["P3_accepted"] and not review["institutional_production_accepted"])
    require(
        {c["id"] for c in review["criteria"]}
        == {"P3.1", "P3.2", "P3.3", "P3.4", "P3.close"}
        and all(c["accepted"] for c in review["criteria"])
    )
    for evidence in review["evidence"].values():
        require(digest(ROOT / evidence["file"]) == evidence["sha256"])
    preservation = read(ROOT / "artifacts/p3-es/source-preservation-result.json")
    require(
        preservation["status"] == "passed"
        and preservation["before_sha256"] == preservation["after_sha256"]
        and preservation["Windows_sources"] == 6
        and preservation["SQL2019_prior_copies"] == 77
    )
    fixture = read(ROOT / "artifacts/p3-es/final-fixture-result.json")
    require(
        fixture["status"] == "passed"
        and fixture["count"] == len(set(fixture["checks"])) == 24
    )
    migrations = read(ROOT / "artifacts/p3-es/migration-result.json")
    require(
        migrations["status"] == "passed"
        and len(migrations["faults"]) == 3
        and sorted(migrations["concurrency"]) == ["committed", "noop"]
        and migrations["restored_accounts"] == 2
        and migrations["runtime_SQL_denials"] == 4
        and migrations["CRM_workspace_binary_hashes_equal"]
    )
    risk = read(ROOT / "artifacts/p3-es/risk-result.json")
    require(
        risk["status"] == "passed"
        and risk["count"] == len(set(risk["checks"])) == 16
        and risk["live_provider_acceptance"] is False
    )
    clean = read(ROOT / "artifacts/p3-es/clean-result.json")
    require(
        clean["status"] == "passed"
        and clean["accounts"] == 1
        and clean["fixtures"] == 0
    )
    restart = read(ROOT / "artifacts/p3-es/restart-result.json")
    require(
        restart["status"] == "passed"
        and restart["before"] == restart["after"]
        and restart["image_digest"] == proof["image_digest"]
    )
    require(
        read(ROOT / ("artifacts/p3-es/browser/restart-session-result.json"))[
            "opaque_session_survives_application_restart"
        ]
    )
    require(
        read(ROOT / "artifacts/p3-es/deployment-result.json")["image_digest"]
        == proof["image_digest"]
    )
    from p3_es_graphs import check as graph_check
    from phase_work_progress import check as work_check

    work = work_check()
    require(
        work["accepted_criteria"] == 20
        and work["milestone_count"] == 279
        and work["done_milestones"] == 147
        and work["pending_milestones"] == 132
    )
    require(
        work["phases"][3]["phase_accepted"]
        and proof["phase_percentages"]
        == {p["id"]: p["work_percent_display"] for p in work["phases"]}
    )
    require(
        read(ROOT / "artifacts/p3-es/p2-replay-result.json")[
            "frozen_P2_and_P1_checkers_replayed"
        ]
    )
    return dict(
        baseline_files_checked=993,
        changed_predecessors=len(changed),
        pinned_sources=len(proof["source_pins"]),
        P3="100.00%",
        graph=graph_check(),
        SQL_connections=0,
    )


def negatives(proof):
    mutations = [
        lambda p: p.__setitem__("P3_accepted", False),
        lambda p: p.__setitem__("institutional_production_accepted", True),
        lambda p: p.__setitem__("release_sha256", "0" * 64),
        lambda p: p.__setitem__("parent_P2_release_sha256", "0" * 64),
        lambda p: p.__setitem__("preimages_sha256", "0" * 64),
        lambda p: p.__setitem__("image_digest", "sha256:" + "0" * 64),
        lambda p: p["source_pins"].pop("backend/app/institutional/workspace.py"),
        lambda p: p["changed_predecessors"].clear(),
    ]
    for mutate in mutations:
        wrong = copy.deepcopy(proof)
        mutate(wrong)
        try:
            validate(wrong)
        except (AssertionError, ValueError):
            pass
        else:
            raise AssertionError("invalid_P3_checkpoint_accepted")
    return len(mutations)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--skip-replay", action="store_true")
    args = parser.parse_args()
    proof = read(PROOF)
    result = validate(proof)
    if not args.skip_replay:
        receipt = replay_parent()
        result.update(
            frozen_P2_and_P1_checkers_replayed=True, preimages=receipt["preimages"]
        )
    if args.self_test:
        from check_phase_progress import self_test
        from phase_work_progress import check

        result["checkpoint_negatives_rejected"] = negatives(proof)
        result["work_negatives_rejected"] = check(negatives=True)[
            "negative_cases_rejected"
        ]
        result["canonical_negatives_rejected"] = self_test(
            read(ROOT / "docs/adaptation/phase-progress-contract.json")
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
