"""Validate the P1.3 definition using public local files only; never execute SQL."""

import argparse
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "docs/adaptation/sql/migration-plan.json"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def ordered(items):
    ids = [item["id"] for item in items]
    require(len(set(ids)) == len(ids), "Duplicate migration/unit ID")
    seen = set()
    for item in items:
        deps = item["depends_on"]
        require(len(set(deps)) == len(deps), "Duplicate dependency")
        require(
            set(deps) <= seen, f"Unknown, cyclic or unordered dependency: {item['id']}"
        )
        seen.add(item["id"])


def validate(plan):
    require(plan["schema_version"] == 1, "Unsupported definition version")
    require(plan["status"] == "definition_only_not_executable", "Not a definition")
    for key in (
        "execution_authorized",
        "database_connection_allowed",
        "legacy_execution_allowed",
    ):
        require(plan[key] is False, "P1.3 cannot authorize execution or a connection")
    inventory = json.loads(
        (ROOT / "docs/adaptation/sql/inventory.json").read_text(encoding="utf-8")
    )
    source = {m["id"]: m for m in inventory["migrations"]}
    legacy = plan["legacy"]
    ids = [m["id"] for m in legacy]
    require(
        ids == sorted(source) == plan["historical_order"], "Historical coverage/order"
    )
    require(len(ids) == 19 and "010" not in ids, "Do not invent legacy 010")
    ordered(legacy)
    for item in legacy:
        original = source[item["id"]]
        require(item["file"] == original["file"], "Historical file changed")
        digest = hashlib.sha256((ROOT / original["file"]).read_bytes()).hexdigest()
        require(
            digest == item["sha256"] == original["sha256"], "Historical bytes changed"
        )
        require(item["institutional_execution_allowed"] is False, "Legacy execution")
        number = int(item["id"])
        owner = (
            "script"
            if number <= 9
            else "caller_required_for_atomicity"
            if number <= 17
            else "caller_enforced"
        )
        require(item["transaction_owner"] == owner, "Historical transaction owner")
        require(
            item["declared_tables"] == [t["name"] for t in original["tables"]],
            "Declared table coverage changed",
        )
        dependencies = {
            source_id
            for source_id, m in source.items()
            if m["file"] in original["fk_dependencies"]
        }
        require(dependencies <= set(item["depends_on"]), "Missing FK dependency")
    units = plan["institutional_units"]
    require(len(units) == 18 and units[0]["id"] == "CBN-B000", "Baseline groups")
    ordered(units)
    require([u["order"] for u in units] == list(range(1, 19)), "Unit ordinal mismatch")
    coverage = [i for unit in units for i in unit["source_ids"]]
    require(sorted(coverage) == ids, "Source must map to exactly one proposed group")
    mapping = {i: u["id"] for u in units for i in u["source_ids"]}
    by_id = {item["id"]: item for item in legacy}
    for unit in units:
        require(unit["status"] == "design_only", "No SQL implementation claimed")
        require(unit["execution_authorized"] is False, "Unit execution not allowed")
        require(unit["transaction_owner"] == "runner", "New unit must be atomic")
        require(
            all(
                unit[k] is None
                for k in ("sql_file", "sql_sha256", "expected_shape_sha256")
            ),
            "Do not invent executable SQL or a final shape hash",
        )
        deps = {
            mapping[d]
            for i in unit["source_ids"]
            for d in by_id[i]["depends_on"]
        }
        deps.discard(unit["id"])
        if unit["id"] != "CBN-B000":
            deps.add("CBN-B000")
        require(deps <= set(unit["depends_on"]), "Missing baseline dependency")
    history = plan["history"]
    require(
        history["created"] is False and history["append_only"] is True, "Journal scope"
    )
    require(plan["atomic_success_with_ddl"] is True, "DDL/success must share commit")
    require(
        plan["uncertain_commit"] == "stop_and_reconcile_no_automatic_retry",
        "Unsafe retry",
    )
    require(
        plan["unknown_or_partial_schema"] == "blocked_requires_explicit_transition",
        "Unsafe repair",
    )
    require(
        plan["whole_database_restore"]
        == "prohibited_without_separate_institutional_decision",
        "Unsafe restore",
    )


def self_test(plan):
    mutations = [
        lambda p: p.update(execution_authorized=True),
        lambda p: p["legacy"][0].update(sha256="0" * 64),
        lambda p: p["legacy"][0].update(depends_on=["020"]),
        lambda p: p["legacy"][1].update(transaction_owner="caller_enforced"),
        lambda p: p["legacy"][8].update(depends_on=["001"]),
        lambda p: p["institutional_units"][1].update(source_ids=[]),
        lambda p: p["institutional_units"][1].update(sql_file="unreleased.sql"),
        lambda p: p["institutional_units"][1].update(depends_on=[]),
        lambda p: p.update(uncertain_commit="retry"),
        lambda p: p.update(whole_database_restore="automatic"),
        lambda p: p.update(atomic_success_with_ddl=False),
        lambda p: p.update(unknown_or_partial_schema="repair_automatically"),
    ]
    for mutate in mutations:
        candidate = copy.deepcopy(plan)
        mutate(candidate)
        try:
            validate(candidate)
        except ValueError:
            continue
        raise AssertionError("Unsafe/inconsistent definition was accepted")
    return len(mutations)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    validate(plan)
    cases = self_test(plan) if args.self_test else 0
    print(
        f"P1.3 definition verified: 19 sources, 18 proposed units; "
        f"{cases} negative checks."
    )


if __name__ == "__main__":
    main()
