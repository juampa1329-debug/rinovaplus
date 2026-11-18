"""Check the owner-approved PostgreSQL closure; never replay historical SQL IO."""

import hashlib
import json
from fractions import Fraction
from pathlib import Path

from check_phase_progress import canonical_roadmap, sha
from check_phase_progress import validate as validate_historical_references
from phase_work_progress import calculated, definition, display, exact

ROOT = Path(__file__).resolve().parents[2]
ACCEPTANCE = "artifacts/live/p11-postgres-acceptance-20261118.json"
MILESTONES = {"P11.3.m2", "P11.3.m4", "P11.3.m5", "P11.close.m1", "P11.close.m4"}


def read(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8-sig"))


def digest(name):
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def reference_issues(ledger, work):
    missing = set()
    mismatches = set()
    for phase in ledger["phases"]:
        for criterion in phase["criteria"]:
            for item in criterion.get("evidence", []):
                if not (ROOT / item["file"]).is_file():
                    missing.add(item["file"])
    for item in work["evidence_registry"].values():
        if not (ROOT / item["file"]).is_file():
            missing.add(item["file"])
        elif digest(item["file"]) != item["source_sha256_at_review"]:
            mismatches.add(item["file"])
    return {"missing": sorted(missing), "hash_mismatches": sorted(mismatches)}


def check():
    a = read(ACCEPTANCE)
    for item in a["preimages"].values():
        require(digest(item["file"]) == item["sha256"], "Preimage changed")
    old_l = read(a["preimages"]["ledger"]["file"])
    old_w = read(a["preimages"]["work"]["file"])
    old_p12 = read(a["preimages"]["p12"]["file"])
    ledger = read("docs/adaptation/phase-progress-contract.json")
    work = read("docs/adaptation/phase-work-progress.json")
    live = read("tasks/rinovaplus-live-progress.json")
    p12 = read("tasks/p12-online-backlog.json")
    review = a["technical_review"]
    require(digest(review["file"]) == review["sha256"], "Technical proof changed")
    require(
        a["owner_acceptance"]["answer"]
        == "Aceptar ese alcance y registrar las mejoras pendientes",
        "Owner acceptance missing",
    )
    require(a["no_external_backup_or_key_custody_claimed"], "Residual limits missing")
    require(definition(work) == definition(old_w), "Milestone definition changed")
    require(
        definition(work) == read("docs/adaptation/phase-work-definition.json"),
        "Frozen definition changed",
    )
    require(
        sha(canonical_roadmap()) == ledger["basis"]["canonical_definition_sha256"],
        "Canonical text changed",
    )
    require(ledger["phases"][:-1] == old_l["phases"][:-1], "Prior closure changed")
    require(work["phases"][:-1] == old_w["phases"][:-1], "Prior work changed")
    require(
        ledger["phases"][-1]["criteria"][:2] == old_l["phases"][-1]["criteria"][:2],
        "Prior P11 acceptance changed",
    )
    changed_criteria = []
    for current, prior in zip(
        ledger["phases"][-1]["criteria"], old_l["phases"][-1]["criteria"], strict=True
    ):
        if current["state"] != prior["state"]:
            changed_criteria.append(current["id"])
            require(
                current["state"] == "accepted" and prior["state"] == "partial",
                "Unexpected criterion transition",
            )
        require(
            current["source"] == prior["source"]
            and current["requirement"] == prior["requirement"],
            "Criterion text changed",
        )
    require(changed_criteria == ["P11.3", "P11.close"], "Unexpected acceptance scope")
    changed_milestones = set()
    for phase, prior_phase, accepted in zip(
        work["phases"], old_w["phases"], ledger["phases"], strict=True
    ):
        for criterion, prior_criterion, canonical in zip(
            phase["criteria"],
            prior_phase["criteria"],
            accepted["criteria"],
            strict=True,
        ):
            require(
                criterion["current_acceptance"]
                == {k: canonical[k] for k in ("state", "credit", "accepted_scope")},
                "Acceptance/work disagreement",
            )
            for milestone, prior in zip(
                criterion["milestones"], prior_criterion["milestones"], strict=True
            ):
                require(milestone["state"] == "done", "Unfinished canonical work")
                if milestone["state"] != prior["state"]:
                    changed_milestones.add(milestone["id"])
                    require(
                        milestone["evidence_refs"]
                        == ["P11_PostgreSQL_owner_acceptance"],
                        "Missing new proof",
                    )
        completion = accepted["completion"]
        count = sum(c["credit"] for c in accepted["criteria"])
        total = len(accepted["criteria"])
        require(
            count == total
            and completion["accepted"] == count
            and completion["phase_accepted"],
            "Incomplete criterion",
        )
        require(
            completion["fraction"] == {"numerator": count, "denominator": total},
            "Invalid fraction",
        )
        require(
            completion["reduced_fraction"] == exact(Fraction(1))
            and completion["percent_display"] == display(Fraction(1)),
            "Invalid percent",
        )
        require(
            all(
                next(p for p in ledger["phases"] if p["id"] == dep)["completion"][
                    "phase_accepted"
                ]
                for dep in phase["depends_on"]
            ),
            "Dependency incomplete",
        )
    require(changed_milestones == MILESTONES, "Unexpected milestone transitions")
    summary = calculated(work, ledger)
    require(summary == work["summary"], "Incorrect work summary")
    require(
        summary["done_milestones"] == 279
        and summary["pending_milestones"] == 0
        and summary["accepted_criteria"] == 56,
        "Incorrect fixed totals",
    )
    require(ledger["summary"]["partial_criteria"] == 0, "Stale acceptance count")
    require(
        live["canonical_percent"]
        == summary["overall_technical_percent_display"]
        == "100.00%",
        "Live roadmap differs",
    )
    require(
        p12["resolved_existing_milestones"] == old_p12["pending_existing_milestones"]
        and len(p12["resolved_existing_milestones"]) == 18,
        "P12 backlog changed",
    )
    require(
        not p12["pending_existing_milestones"] and p12["canonical_weight_added"] == 0,
        "Double credit in P12",
    )
    risks = read(a["residual_improvements"])
    require(
        len(risks["items"]) == 6
        and all(r["state"] == "pending" for r in risks["items"]),
        "Residual risks silently closed",
    )
    issues_before = reference_issues(old_l, old_w)
    issues_after = reference_issues(ledger, work)
    require(issues_before == issues_after, "New missing or modified evidence reference")
    require(
        digest(ACCEPTANCE)
        == work["evidence_registry"]["P11_PostgreSQL_owner_acceptance"][
            "source_sha256_at_review"
        ],
        "Acceptance hash mismatch",
    )
    try:
        validate_historical_references(ledger)
        historical_check = "passed"
    except ValueError as exc:
        historical_check = (
            f"not_passed: {exc}; historical references remain explicitly listed"
        )
    return {
        "date": "2026-11-18",
        "definition_unchanged": True,
        "criterion_transitions": changed_criteria,
        "milestone_transitions": sorted(changed_milestones),
        "summary": summary,
        "P12_auxiliary_overlap_resolved": 18,
        "canonical_weight_added": 0,
        "open_operational_improvements": 6,
        "acceptance_sha256": digest(ACCEPTANCE),
        "historical_reference_issues_unchanged": issues_after,
        "original_full_reference_check": historical_check,
        "historical_full_SQL_replay_claimed": False,
    }


if __name__ == "__main__":
    print(json.dumps(check(), ensure_ascii=False, indent=2))
