"""Offline partial-work accounting, alongside immutable canonical acceptance."""

import argparse
import copy
import hashlib
import json
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction
from pathlib import Path

from check_phase_progress import ROOT
from check_phase_progress import validate as validate_acceptance

DEFINITION_SHA256 = "3ada201775c4955cb88796252ad684e257d64733598a6d4bae238529867d101a"
DIRECTORY = Path("docs/adaptation")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition):
    if not condition:
        raise ValueError("Partial work progress mismatch")


def fraction(value):
    require(set(value) == {"numerator", "denominator"})
    numerator, denominator = value["numerator"], value["denominator"]
    require(type(numerator) is int and type(denominator) is int)
    require(numerator >= 0 and denominator > 0)
    return Fraction(numerator, denominator)


def exact(value):
    return {"numerator": value.numerator, "denominator": value.denominator}


def display(value):
    return (
        str(
            (
                Decimal(100) * Decimal(value.numerator) / Decimal(value.denominator)
            ).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
        )
        + "%"
    )


def definition(document):
    return {
        "schema_version": "fixed-work-milestones-v1",
        "canonical_definition_sha256": document["baseline"][
            "canonical_definition_sha256"
        ],
        "criterion_count": 56,
        "milestone_count": 279,
        "phases": [
            {
                "id": phase["id"],
                "criteria": [
                    {
                        "id": criterion["id"],
                        "canonical_text_sha256": criterion["canonical_reference"][
                            "canonical_text_sha256"
                        ],
                        "milestones": [
                            {
                                key: milestone[key]
                                for key in (
                                    "id",
                                    "description",
                                    "criterion_share",
                                    "work_kind",
                                    "evidence_level",
                                )
                            }
                            for milestone in criterion["milestones"]
                        ],
                    }
                    for criterion in phase["criteria"]
                ],
            }
            for phase in document["phases"]
        ],
    }


def calculated(document, ledger):
    phases = []
    done = pending = 0
    for phase, accepted in zip(document["phases"], ledger["phases"], strict=True):
        portions = []
        for criterion in phase["criteria"]:
            portions.append(
                sum(
                    (
                        fraction(m["criterion_share"])
                        for m in criterion["milestones"]
                        if m["state"] == "done"
                    ),
                    Fraction(),
                )
            )
            done += sum(m["state"] == "done" for m in criterion["milestones"])
            pending += sum(m["state"] == "pending" for m in criterion["milestones"])
        work = sum(portions, Fraction()) / len(portions)
        phases.append(
            {
                "id": phase["id"],
                "criterion_denominator": len(portions),
                "criterion_equivalents_completed": exact(sum(portions, Fraction())),
                "work_fraction": exact(work),
                "work_percent_display": display(work),
                "accepted_criteria": accepted["completion"]["accepted"],
                "acceptance_percent_display": accepted["completion"]["percent_display"],
                "phase_accepted": accepted["completion"]["phase_accepted"],
            }
        )
    overall = (
        sum(
            (fraction(p["criterion_equivalents_completed"]) for p in phases), Fraction()
        )
        / 56
    )
    return {
        "overall_technical_fraction": exact(overall),
        "overall_technical_percent_display": display(overall),
        "overall_formula": "Suma del trabajo realizado de cada criterio, incluido parcial, dividida por56 criterios de peso1; no promedio simple de fases ni ratio de hitos.",
        "criterion_count": 56,
        "milestone_count": done + pending,
        "done_milestones": done,
        "pending_milestones": pending,
        "accepted_criteria": ledger["summary"]["accepted_criteria"],
        "milestone_counts_are_not_weights": True,
        "phases": phases,
    }


def evidence_path(root, relative):
    require(isinstance(relative, str) and "\\" not in relative and ":" not in relative)
    path = (root / relative).resolve()
    allowed = (
        root.resolve()
        if not relative.startswith("../saas-version/")
        else root.parent / "saas-version"
    )
    require(path.is_relative_to(allowed.resolve()) and path.is_file())
    return path


def validate(document, ledger, frozen, *, root=ROOT):
    validate_acceptance(ledger)
    require(document["schema_version"] == "technical-work-milestones-v1")
    require(
        document["baseline"]["canonical_definition_sha256"]
        == ledger["basis"]["canonical_definition_sha256"]
    )
    require(definition(document) == frozen)
    require(frozen["criterion_count"] == 56 and frozen["milestone_count"] == 279)
    require(len(document["phases"]) == 12)
    registry = document["evidence_registry"]
    for entry in registry.values():
        path = evidence_path(root, entry["file"])
        require(entry.get("scope") and entry.get("source_location"))
        require(digest(path) == entry["source_sha256_at_review"])
    milestone_ids = set()
    for phase, accepted in zip(document["phases"], ledger["phases"], strict=True):
        require(
            phase["id"] == accepted["id"]
            and phase["depends_on"] == accepted["depends_on"]
        )
        require(phase["canonical_criterion_denominator"] == len(accepted["criteria"]))
        require(len(phase["criteria"]) == len(accepted["criteria"]))
        for criterion, canonical in zip(
            phase["criteria"], accepted["criteria"], strict=True
        ):
            require(criterion["id"] == canonical["id"] and criterion["weight"] == 1)
            require(
                criterion["canonical_reference"]["canonical_text_sha256"]
                == canonical["source"]["canonical_text_sha256"]
            )
            require(
                sum(
                    (fraction(m["criterion_share"]) for m in criterion["milestones"]),
                    Fraction(),
                )
                == 1
            )
            all_done = True
            for milestone in criterion["milestones"]:
                require(milestone["id"] not in milestone_ids)
                milestone_ids.add(milestone["id"])
                require(milestone["state"] in {"done", "pending"})
                require(fraction(milestone["criterion_share"]) > 0)
                if milestone["state"] == "done":
                    require(
                        milestone["evidence_refs"]
                        and all(ref in registry for ref in milestone["evidence_refs"])
                    )
                else:
                    all_done = False
            require(all_done == (canonical["state"] == "accepted"))
            require(
                criterion["current_acceptance"]
                == {
                    "state": canonical["state"],
                    "credit": canonical["credit"],
                    "accepted_scope": canonical.get("accepted_scope"),
                }
            )
    result = calculated(document, ledger)
    require(len(milestone_ids) == 279 and document["summary"] == result)
    for phase in result["phases"]:
        if fraction(phase["work_fraction"]) == 1:
            require(phase["phase_accepted"])
    return result


def self_test(document, ledger, frozen):
    cases = [
        lambda d: d["summary"]["phases"][2].__setitem__(
            "work_percent_display",
            "99.99%"
            if d["summary"]["phases"][2]["work_percent_display"] == "100.00%"
            else "100.00%",
        ),
        lambda d: d["summary"].__setitem__(
            "done_milestones", d["summary"]["done_milestones"] + 1
        ),
        lambda d: d["phases"][2]["criteria"][0]["milestones"].pop(),
        lambda d: d["phases"][2]["criteria"][0]["milestones"][0][
            "criterion_share"
        ].__setitem__("numerator", 2),
        lambda d: d["phases"][2]["criteria"][0]["milestones"][0].__setitem__(
            "evidence_refs", []
        ),
        lambda d: d["phases"][2]["criteria"][0]["milestones"][-1].__setitem__(
            "state",
            "pending"
            if d["phases"][2]["criteria"][0]["milestones"][-1]["state"] == "done"
            else "done",
        ),
        lambda d: d["phases"][2].__setitem__("canonical_criterion_denominator", 4),
        lambda d: d["phases"][2]["criteria"][0].__setitem__("weight", 2),
        lambda d: d["phases"][2]["criteria"][0]["milestones"][0].__setitem__(
            "state", "partial"
        ),
        lambda d: next(iter(d["evidence_registry"].values())).__setitem__(
            "source_sha256_at_review", "0" * 64
        ),
        lambda d: next(iter(d["evidence_registry"].values())).__setitem__(
            "file", "../../unapproved"
        ),
        lambda d: d["phases"][2].__setitem__("depends_on", []),
        lambda d: d["phases"][2]["criteria"][0]["milestones"][0].__setitem__(
            "description", "Easier replacement"
        ),
        lambda d: d["phases"][2]["criteria"][0].__setitem__(
            "current_acceptance",
            {"state": "accepted", "credit": 1, "accepted_scope": "false"},
        ),
    ]
    cases.append(
        lambda d: d["summary"].__setitem__(
            "overall_technical_percent_display", "100.00%"
        )
    )
    for mutate in cases:
        invalid = copy.deepcopy(document)
        mutate(invalid)
        require(invalid != document)
        try:
            validate(invalid, ledger, frozen)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid partial progress accepted")
    return len(cases)


def check(*, negatives=False):
    frozen_path = ROOT / DIRECTORY / "phase-work-definition.json"
    require(digest(frozen_path) == DEFINITION_SHA256)
    document = read(ROOT / DIRECTORY / "phase-work-progress.json")
    ledger = read(ROOT / DIRECTORY / "phase-progress-contract.json")
    frozen = read(frozen_path)
    result = validate(document, ledger, frozen)
    if negatives:
        result["negative_cases_rejected"] = self_test(document, ledger, frozen)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    arguments = parser.parse_args()
    print(
        json.dumps(check(negatives=arguments.self_test), ensure_ascii=False, indent=2)
    )
