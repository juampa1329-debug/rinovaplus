"""Verify the SQL-C6 design offline; never import the app, ODBC or secrets."""

import argparse
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOCS = Path(__file__).resolve().parent
PLAN = DOCS / "crm-extension-plan.json"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(value, reason):
    if not value:
        raise ValueError(reason)


def validate(plan):
    require(plan["unit"] == "SQL-C6", "wrong_unit")
    require(plan["status"] == "reviewed_design_only", "not_design_only")
    for flag in (
        "database_connection_allowed",
        "execution_allowed",
        "runtime_changes_allowed",
    ):
        require(plan[flag] is False, flag)
    require(plan["baseline_file"] == "sql_c6_input_baseline.json", "wrong_baseline")
    require(
        digest(DOCS / plan["baseline_file"]) == plan["baseline_sha256"],
        "baseline_changed",
    )
    baseline = read(DOCS / plan["baseline_file"])
    for record in baseline["files"]:
        require(digest(ROOT / record["path"]) == record["sha256"], record["path"])
    require(
        plan["runtime_checkpoint"]["sha256"]
        == baseline["runtime_checkpoint_sha256"]
        == digest(DOCS / "sql_c5_validation.json"),
        "runtime_checkpoint_changed",
    )
    require(plan["runtime_checkpoint"]["preserve_current_preview"] is True, "preview")
    inventory = read(DOCS / "inventory.active.json")
    comparison = read(DOCS / "horariosiie-comparison.json")
    observed = read(DOCS / "observed-schema.json")
    inherited = read(DOCS / "migration-plan.json")
    sources = {m["id"]: m for m in inventory["migrations"]}
    inherited_units = {u["id"]: u for u in inherited["institutional_units"]}
    release, partition = plan["release"], plan["partition"]
    require(release["status"] == "not_implemented", "release_not_implemented")
    require(release["scope"] == "new_restored_copy_only", "release_scope")
    require(release["source_ids"] == ["011", "012"], "source_closure")
    require(release["unit"] == "CBN-B011", "unit")
    require(
        release["depends_on"] == inherited_units["CBN-B011"]["depends_on"],
        "inherited_dependencies",
    )
    for field in ("sql_file", "release_sha256", "expected_shape_sha256"):
        require(release[field] is None, "invented_implementation")
    require(
        release["base_release_sha256"]
        == digest(ROOT / "backend/migrations/cbn_foundation/release.json"),
        "base_release",
    )
    require(
        release["source_files"]
        == [
            {"path": sources[i]["file"], "sha256": sources[i]["sha256"]}
            for i in ("011", "012")
        ],
        "source_bytes",
    )
    academic = {t["schema"] + "." + t["name"] for t in observed["tables"]}
    foundation = {
        "crm.Contact",
        "crm.Conversation",
        "crm.Message",
        "crm.Operation",
        "crm_config.Configuration",
        "crm_config.Operation",
        "crm_meta.MigrationJournal",
    }
    extension = {t["name"] for t in sources["011"]["tables"]}
    for key, expected in (
        ("academic_tables", academic),
        ("foundation_tables", foundation),
        ("extension_tables", extension),
    ):
        require(set(partition[key]) == expected, key)
        require(len(partition[key]) == len(expected), "duplicate_partition_entry")
    require(
        not (academic & (foundation | extension) or foundation & extension), "overlap"
    )
    require((len(academic), len(foundation), len(extension)) == (50, 7, 8), "counts")
    require(partition["unknown_objects"] == "reject_inconclusive_or_drift", "unknown")
    require(partition["metadata_visibility"] == "complete_required", "visibility")
    require(partition["prefix_exclusion_allowed"] is False, "prefix_exclusion")
    require(partition["count_only_acceptance_allowed"] is False, "count_only")
    deferred = {
        t["name"]
        for t in comparison["tables"]
        if t["name"] not in foundation | extension
    }
    require(
        {t["name"] for t in partition["deferred_declared_tables"]} == deferred
        and len(partition["deferred_declared_tables"]) == len(deferred) == 54,
        "deferred_closure",
    )
    require(release["new_table_count"] == 8, "new_count")
    require(release["total_crm_table_count"] == 15, "total_count")
    require(release["initial_rows"] == 0, "seeds")
    rights = plan["migration_permission_plan"]
    require(rights["principal_kind"] == "new_database_user_without_login", "principal")
    require(
        rights["database"] == ["CREATE TABLE", "VIEW DEFINITION"], "database_rights"
    )
    require(rights["schemas"] == {"crm_channels": ["ALTER"]}, "schema_rights")
    require(
        rights["objects"]
        == {
            "crm.Contact": ["REFERENCES"],
            "crm.Conversation": ["REFERENCES"],
            "crm.Message": ["REFERENCES"],
            "crm_meta.MigrationJournal": ["SELECT", "INSERT"],
        },
        "object_rights",
    )
    require({t["name"] for t in plan["extension_tables"]} == extension, "tables")
    for table in plan["extension_tables"]:
        source = next(t for t in sources["011"]["tables"] if t["name"] == table["name"])
        require(table["column_count"] == len(source["columns"]), "columns")
    fks = [f for f in comparison["foreign_keys"] if f["source_table"] in extension]
    require(plan["foreign_keys"] == fks and len(fks) == 10, "foreign_keys")
    require(plan["explicit_indexes"] == sources["011"]["indexes"], "indexes")
    require(
        plan["final_named_keys"]
        == [
            {
                "table": "crm_channels.ExternalIdentity",
                "name": "UQ_Channels_Identity",
                "kind": "UNIQUE",
                "columns": ["Channel", "ExternalId"],
            },
            {
                "table": "crm_channels.ExternalMessage",
                "name": "PK_Channels_ExternalMessage",
                "kind": "PRIMARY KEY",
                "columns": ["Channel", "ExternalId"],
            },
            {
                "table": "crm_channels.social_comments",
                "name": "UQ_Channels_Comment",
                "kind": "UNIQUE",
                "columns": ["Channel", "ExternalId"],
            },
        ],
        "final_keys",
    )
    order = release["create_order"]
    require(set(order) == extension and len(order) == 8, "create_order")
    for fk in fks:
        target = fk["target_table"]
        require(target in foundation | extension, "foreign_boundary")
        if target in extension:
            require(order.index(target) < order.index(fk["source_table"]), "fk_order")
    expected_columns = {
        ("crm_channels.ExternalIdentity", "ExternalId"),
        ("crm_channels.ExternalMessage", "ExternalId"),
        ("crm_channels.outbound_queue", "ExternalId"),
        ("crm_channels.social_comments", "ExternalId"),
        ("crm_channels.social_comments", "AuthorId"),
    }
    require(
        {(c["table"], c["column"]) for c in plan["provider_identifier_collations"]}
        == expected_columns,
        "bin2_columns",
    )
    require(
        all(
            c["collation"] == "Latin1_General_100_BIN2"
            for c in plan["provider_identifier_collations"]
        ),
        "bin2",
    )
    required = {
        "partition_v2",
        "preservation",
        "security",
        "history",
        "destination",
        "snapshots",
        "runtime_promotion",
    }
    require({c["id"] for c in plan["required_contracts"]} == required, "contracts")
    require(
        all(c["status"] == "not_implemented" for c in plan["required_contracts"]),
        "contracts_implemented",
    )
    disabled = {
        "workers",
        "provider_calls",
        "external_delivery",
        "webhook_ingestion",
        "comments_ui",
        "unified_inbox_controls",
        "churn_evaluation",
        "campaigns",
        "academic_lookup",
        "contact_merge",
        "inbox_operations",
    }
    require(disabled <= set(plan["disabled_capabilities"]), "activation")
    steps = plan["rehearsal_sequence"]
    names = [f"C7-0{i}" for i in range(1, 7)] + ["C8"]
    require(
        [(step["id"], step["depends_on"]) for step in steps]
        == [(name, [] if i == 0 else [names[i - 1]]) for i, name in enumerate(names)],
        "required_stage_dependencies",
    )
    seen = set()
    for step in plan["rehearsal_sequence"]:
        require(step["id"] not in seen and set(step["depends_on"]) <= seen, "stage_dag")
        seen.add(step["id"])
    require(seen == {f"C7-0{i}" for i in range(1, 7)} | {"C8"}, "stage_closure")
    return len(baseline["files"])


def self_test(plan):
    mutations = [
        ("execution", lambda p: p.update(execution_allowed=True)),
        ("connection", lambda p: p.update(database_connection_allowed=True)),
        ("runtime", lambda p: p.update(runtime_changes_allowed=True)),
        ("fake_release", lambda p: p["release"].update(release_sha256="fake")),
        ("missing_012", lambda p: p["release"].update(source_ids=["011"])),
        ("academic_missing", lambda p: p["partition"]["academic_tables"].pop()),
        (
            "extra_object",
            lambda p: p["partition"]["extension_tables"].append("crm_x.Hidden"),
        ),
        ("unknown_ignored", lambda p: p["partition"].update(unknown_objects="ignore")),
        ("prefix", lambda p: p["partition"].update(prefix_exclusion_allowed=True)),
        (
            "count_only",
            lambda p: p["partition"].update(count_only_acceptance_allowed=True),
        ),
        ("foreign_key_missing", lambda p: p["foreign_keys"].pop()),
        ("index_missing", lambda p: p["explicit_indexes"].pop()),
        ("key_columns", lambda p: p["final_named_keys"][0].update(columns=["Channel"])),
        (
            "academic_grant",
            lambda p: p["migration_permission_plan"]["objects"].update(
                {"dbo.GEEmpleado": ["ALTER"]}
            ),
        ),
        (
            "collation",
            lambda p: p["provider_identifier_collations"][0].update(collation="CI_AS"),
        ),
        ("seed", lambda p: p["release"].update(initial_rows=1)),
        ("worker", lambda p: p["disabled_capabilities"].remove("workers")),
        ("cycle", lambda p: p["rehearsal_sequence"][0].update(depends_on=["C8"])),
        (
            "missing_trial_dependency",
            lambda p: p["rehearsal_sequence"][3].update(depends_on=[]),
        ),
        (
            "missing_runtime_dependency",
            lambda p: p["rehearsal_sequence"][-1].update(depends_on=[]),
        ),
    ]
    for name, mutate in mutations:
        invalid = copy.deepcopy(plan)
        mutate(invalid)
        try:
            validate(invalid)
        except ValueError:
            continue
        raise AssertionError("Invalid design accepted: " + name)
    return [name for name, _ in mutations]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--write-validation", action="store_true")
    args = parser.parse_args()
    plan = read(PLAN)
    protected = validate(plan)
    negative = self_test(plan) if args.self_test else []
    result = {
        "unit": "SQL-C6",
        "date": "2026-10-25",
        "status": "reviewed_design_only",
        "plan_sha256": digest(PLAN),
        "checker_sha256": digest(Path(__file__)),
        "baseline_sha256": plan["baseline_sha256"],
        "protected_inputs": protected,
        "partition_tables": {"academic": 50, "foundation": 7, "extension": 8},
        "deferred_tables": 54,
        "foreign_keys": 10,
        "negative_checks": negative,
        "database_connected": False,
        "sql_executed": False,
        "runtime_changed": False,
        "institutional_sql2019_accepted": False,
    }
    if args.write_validation:
        (DOCS / "sql_c6_validation.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    elif (DOCS / "sql_c6_validation.json").is_file():
        stored = read(DOCS / "sql_c6_validation.json")
        for key, value in result.items():
            if key != "negative_checks" or args.self_test:
                require(stored.get(key) == value, "stale_validation:" + key)
    print(json.dumps(result, ensure_ascii=False))
