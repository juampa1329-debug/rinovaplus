"""Offline canonical roadmap/percentage consistency; no application or SQL IO."""

import argparse
import copy
import hashlib
import json
import re
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def sha(value):
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


def require(value):
    if not value:
        raise ValueError("Phase progress contract mismatch")


def canonical_roadmap():
    phases = []
    for line in (
        (ROOT / "docs/SCENTRA_ADAPTATION_ROADMAP.md")
        .read_text(encoding="utf-8-sig")
        .splitlines()
    ):
        match = re.match(r"^### (P\d+) (.+)$", line)
        if match:
            phases.append({"id": match[1], "units": [], "closure": None})
        match = re.match(r"^- \*\*(P\d+\.\d+)(?:,[^*]*)?:\*\*\s*(.*)$", line)
        if match:
            require(phases and match[1].startswith(phases[-1]["id"] + "."))
            phases[-1]["units"].append({"id": match[1], "text": line})
        if line.startswith("**Cierre:**"):
            require(phases and phases[-1]["closure"] is None)
            phases[-1]["closure"] = line
    require(
        len(phases) == 12
        and sum(len(p["units"]) for p in phases) == 44
        and all(p["closure"] for p in phases)
    )
    return phases


def validate(document):
    canonical = canonical_roadmap()
    require(document["basis"]["canonical_definition_sha256"] == sha(canonical))
    require(
        document["basis"]["fixed_criteria_total"] == 56
        and document["basis"]["unit_count"] == 44
        and document["basis"]["closure_count"] == 12
    )
    require(
        document["counting_policy"]["criterion_weight"] == 1
        and document["counting_policy"]["accepted_credit"] == 1
        and all(
            document["counting_policy"][s + "_credit"] == 0
            for s in ("partial", "pending", "blocked")
        )
    )
    phases = document["phases"]
    require([p["id"] for p in phases] == [p["id"] for p in canonical])
    accepted = 0
    for phase, source in zip(phases, canonical, strict=True):
        criteria = phase["criteria"]
        expected = {u["id"]: u["text"] for u in source["units"]} | {
            source["id"] + ".close": source["closure"]
        }
        require([c["id"] for c in criteria] == list(expected))
        for criterion in criteria:
            state = criterion["state"]
            require(
                state in {"accepted", "partial", "pending", "blocked"}
                and criterion["weight"] == 1
                and criterion["credit"] == int(state == "accepted")
            )
            require(
                criterion["source"]["canonical_text_sha256"]
                == hashlib.sha256(expected[criterion["id"]].encode()).hexdigest()
            )
            if state == "accepted":
                require(criterion.get("evidence") and criterion.get("accepted_scope"))
            for evidence in criterion.get("evidence", []):
                path = ROOT / evidence["file"]
                require(path.is_file() and not Path(evidence["file"]).is_absolute())
        count = sum(c["credit"] for c in criteria)
        total = len(criteria)
        completion = phase["completion"]
        fraction = Fraction(count, total)
        percent = 100 * fraction
        require(
            total == document["basis"]["counts_by_phase"][phase["id"]]
            and completion["accepted"] == count
            and completion["total"] == total
        )
        require(
            completion["fraction"] == {"numerator": count, "denominator": total}
            and completion["reduced_fraction"]
            == {"numerator": fraction.numerator, "denominator": fraction.denominator}
            and completion["percent_exact"]
            == {"numerator": percent.numerator, "denominator": percent.denominator}
        )
        display = (Decimal(100) * Decimal(count) / Decimal(total)).quantize(
            Decimal(".01"), rounding=ROUND_HALF_UP
        )
        require(
            completion["percent_display"] == str(display) + "%"
            and completion["phase_accepted"] == (count == total)
        )
        require(
            completion["partial"] == sum(c["state"] == "partial" for c in criteria)
            and completion["pending"] == sum(c["state"] == "pending" for c in criteria)
        )
        if criteria[-1]["state"] == "accepted":
            require(all(c["state"] == "accepted" for c in criteria))
            require(
                all(
                    next(p for p in phases if p["id"] == dependency)["completion"][
                        "phase_accepted"
                    ]
                    for dependency in phase["depends_on"]
                )
            )
        if completion["phase_accepted"]:
            require(
                all(
                    next(p for p in phases if p["id"] == dependency)["completion"][
                        "phase_accepted"
                    ]
                    for dependency in phase["depends_on"]
                )
            )
        accepted += count
    require(sum(len(p["criteria"]) for p in phases) == 56)
    require(document["summary"]["accepted_criteria"] == accepted)
    return {
        "phases": 12,
        "criteria": 56,
        "accepted": accepted,
        "percentages": {p["id"]: p["completion"]["percent_display"] for p in phases},
    }


def self_test(document):
    def false_close(d):
        phase = d["phases"][4]
        phase["criteria"][-1].update(
            state="accepted",
            credit=1,
            accepted_scope="invalid_partial_close",
            evidence=[{"file": "docs/adaptation/sql/SQL_C12_REVIEW.md"}],
        )
        phase["completion"].update(
            accepted=1,
            partial=2,
            fraction={"numerator": 1, "denominator": 5},
            reduced_fraction={"numerator": 1, "denominator": 5},
            percent_exact={"numerator": 20, "denominator": 1},
            percent_display="20.00%",
        )
        d["summary"]["accepted_criteria"] += 1

    mutations = [
        false_close,
        lambda d: d["summary"].__setitem__("accepted_criteria", 9),
        lambda d: d["basis"].__setitem__("fixed_criteria_total", 57),
        lambda d: d["basis"].__setitem__("canonical_definition_sha256", "a" * 64),
        lambda d: d["counting_policy"].__setitem__("partial_credit", 0.5),
        lambda d: d["phases"][4]["completion"].__setitem__("accepted", 1),
        lambda d: d["phases"][1]["completion"].__setitem__("total", 4),
        lambda d: d["phases"][1]["completion"].__setitem__(
            "percent_display", "99.99%" if d["phases"][1]["completion"]["percent_display"] == "100.00%" else "100.00%"
        ),
        lambda d: d["phases"][0]["criteria"][0].__setitem__("credit", 0),
        lambda d: d["phases"][0]["criteria"][0].__setitem__("weight", 2),
        lambda d: d["phases"][0]["criteria"][0].__setitem__("evidence", []),
        lambda d: d["phases"][4]["criteria"][0].__setitem__(
            "credit", 1 - d["phases"][4]["criteria"][0]["credit"]
        ),
        lambda d: d["phases"][0]["criteria"].pop(),
        lambda d: d["phases"][1]["completion"]["percent_exact"].__setitem__(
            "numerator", 101
        ),
    ]
    for mutation in mutations:
        bad = copy.deepcopy(document)
        mutation(bad)
        require(bad != document)
        try:
            validate(bad)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid progress definition accepted")
    return len(mutations)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    document = json.loads(
        (ROOT / "docs/adaptation/phase-progress-contract.json").read_text(
            encoding="utf-8-sig"
        )
    )
    result = validate(document)
    if args.self_test:
        result["invalid_progress_definitions_rejected"] = self_test(document)
    print(json.dumps(result))
