"""Current progress checks reusing the immutable C12 canonical validator."""

import argparse
import copy
import json

from check_phase_progress import ROOT, validate


def self_test(document):
    def false_close(value):
        phase = value["phases"][4]
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
        value["summary"]["accepted_criteria"] += 1

    mutations = [
        false_close,
        lambda d: d["summary"].__setitem__(
            "accepted_criteria", d["summary"]["accepted_criteria"] + 1
        ),
        lambda d: d["basis"].__setitem__("fixed_criteria_total", 57),
        lambda d: d["basis"].__setitem__("canonical_definition_sha256", "a" * 64),
        lambda d: d["counting_policy"].__setitem__("partial_credit", 0.5),
        lambda d: d["phases"][4]["completion"].__setitem__("accepted", 1),
        lambda d: d["phases"][1]["completion"].__setitem__("total", 4),
        lambda d: d["phases"][1]["completion"].__setitem__(
            "percent_display", "100.00%"
        ),
        lambda d: d["phases"][0]["criteria"][0].__setitem__("credit", 0),
        lambda d: d["phases"][0]["criteria"][0].__setitem__("weight", 2),
        lambda d: d["phases"][0]["criteria"][0].__setitem__("evidence", []),
        lambda d: d["phases"][4]["criteria"][0].__setitem__("credit", 1),
        lambda d: d["phases"][0]["criteria"].pop(),
        lambda d: d["phases"][1]["completion"]["percent_exact"].__setitem__(
            "numerator", 100
        ),
    ]
    for mutation in mutations:
        invalid = copy.deepcopy(document)
        mutation(invalid)
        if invalid == document:
            raise AssertionError("Progress negative case made no change")
        try:
            validate(invalid)
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
