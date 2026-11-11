"""Current offline checkpoint; preserves C13/P2 source history and checks P1."""

import argparse
import copy
import hashlib
import json
import zipfile

from check_phase_progress import ROOT
from phase_work_progress import check as progress_check

PROOF = ROOT / "docs/adaptation/sql/p1_es_validation.json"
MUTABLE_PREDECESSORS = {
    "AGENTS.md",
    "README.md",
    "docs/ADAPTATION_STATUS.md",
    "docs/SCENTRA_ADAPTATION_ROADMAP.md",
    "docs/roadmap.md",
    "docs/adaptation/GRAPH_GUIDE.md",
    "docs/adaptation/RESUME.md",
    "ai-memory/CURRENT_STATE.md",
    "tasks/TASK_STATE.md",
    "docs/adaptation/phase-progress-contract.json",
}


def require(condition):
    if not condition:
        raise ValueError("P1-ES checkpoint mismatch")


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(document):
    require(
        document["unit"] == "P1-ES"
        and document["P1_technical_foundation_accepted"] is True
    )
    baseline = read(ROOT / "docs/adaptation/sql/p1_es_input_baseline.json")
    require(len(baseline["files"]) == 787)
    require(
        document["parent_C13_sha256"]
        == baseline["parent_C13_sha256"]
        == "c55373d5c9a517f1691e9c3cb528336c8615b933253585902f0650cc8b1cfb75"
    )
    require(
        digest(ROOT / "docs/adaptation/sql/sql_c13_validation.json")
        == document["parent_C13_sha256"]
    )
    require(
        digest(ROOT / "docs/adaptation/sql/p2_offline_validation.json")
        == baseline["previous_P2_evidence_sha256"]
    )
    changed = {}
    for entry in baseline["files"]:
        path = (ROOT / entry["path"]).resolve()
        require(path.is_file())
        current = digest(path)
        if current != entry["sha256"]:
            require(entry["path"] in MUTABLE_PREDECESSORS)
            changed[entry["path"]] = {
                "before": entry["sha256"],
                "after": current,
                "archive_name": entry["archive_name"],
            }
    require(changed == document["changed_predecessors"])
    archive = ROOT / "artifacts/p1-es/changed-preimages.zip"
    require(digest(archive) == document["changed_preimages_sha256"])
    with zipfile.ZipFile(archive) as saved:
        require(
            set(saved.namelist())
            == {entry["archive_name"] for entry in changed.values()}
        )
        for entry in changed.values():
            require(
                hashlib.sha256(saved.read(entry["archive_name"])).hexdigest()
                == entry["before"]
            )
    for relative, expected in document["source_pins"].items():
        path = (ROOT / relative).resolve()
        require(
            path.is_relative_to(ROOT) and path.is_file() and digest(path) == expected
        )
    require(
        {
            "backend/tools/check_p1_es_checkpoint.py",
            "backend/tools/phase_work_progress.py",
            "backend/migrations/cbn_spanish_schema_v2/release.json",
            "docs/adaptation/phase-work-progress.json",
            "docs/adaptation/phase-work-definition.json",
            "docs/adaptation/phase-progress-contract.json",
            "docs/adaptation/sql/p1_es_input_baseline.json",
            "artifacts/p1-es/connected-result.json",
            "artifacts/p1-es/acceptance-review.json",
            "artifacts/p1-es/offline-checks.json",
            "graphify-out/p1-es/source-manifest.json",
            "tasks/p1-es-progress.json",
        }
        <= set(document["source_pins"])
    )
    connected = read(ROOT / "artifacts/p1-es/connected-result.json")
    require(connected["engine_major"] == 15 and connected["compatibility"] == 150)
    require(
        connected["six_sources_before"] == connected["six_sources_after"]
        and len(connected["six_sources_after"]) == 6
    )
    require(
        connected["migration_manifest_sha256"]
        == "5457c8da43a9c303c5b7032cff625a3d7ae112c876187c61fdb31e7a8948e2d3"
    )
    require(
        digest(ROOT / "backend/migrations/cbn_spanish_schema_v2/release.json")
        == connected["migration_manifest_sha256"]
    )
    require(
        len(connected["scenarios"]["faults"]) == 8
        and all(case["passed"] for case in connected["scenarios"]["faults"])
    )
    require(
        len(connected["scenarios"]["drift"]) == 6
        and len(connected["scenarios"]["negatives"]) == 8
    )
    require(
        connected["scenarios"]["concurrency"]["parallel_outcomes"]
        == ["committed", "noop"]
    )
    require(
        connected["scenarios"]["restart"]["catalog_data_journal_profile_unchanged"]
        is True
    )
    require(
        connected["old_runtime_redirected"] is False
        and connected["academic_source_DDL_or_DML"] is False
    )
    require(
        document["P2_accepted"] is False
        and document["institutional_production_accepted"] is False
    )
    return {
        "baseline_files_checked": 787,
        "unchanged": 787 - len(changed),
        "document_transitions": len(changed),
        "pinned_sources": len(document["source_pins"]),
    }


def negatives(document):
    cases = [
        lambda d: d.__setitem__("P1_technical_foundation_accepted", False),
        lambda d: d.__setitem__("parent_C13_sha256", "0" * 64),
        lambda d: d.__setitem__("changed_preimages_sha256", "0" * 64),
        lambda d: d["changed_predecessors"].pop(next(iter(d["changed_predecessors"]))),
        lambda d: next(iter(d["changed_predecessors"].values())).__setitem__(
            "before", "0" * 64
        ),
        lambda d: d["source_pins"].__setitem__(next(iter(d["source_pins"])), "0" * 64),
        lambda d: d.__setitem__("P2_accepted", True),
        lambda d: d.__setitem__("institutional_production_accepted", True),
        lambda d: d["source_pins"].pop("backend/tools/check_p1_es_checkpoint.py"),
    ]
    for mutate in cases:
        wrong = copy.deepcopy(document)
        mutate(wrong)
        require(wrong != document)
        try:
            validate(wrong)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid checkpoint accepted")
    return len(cases)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    document = read(PROOF)
    result = validate(document)
    progress = progress_check(negatives=args.self_test)
    from p1_es_graphs import check as graph_check

    graph_check()
    result.update(
        P1="100.00% technical foundation",
        P2=progress["phases"][2]["work_percent_display"],
        SQL_connections=0,
    )
    if args.self_test:
        result["checkpoint_negative_cases_rejected"] = negatives(document)
    print(json.dumps(result, ensure_ascii=False, indent=2))
