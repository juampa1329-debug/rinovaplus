"""Offline P11 checkpoint, including partial canonical progress and frozen replay."""

import argparse
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACCEPTED = {"P11.1", "P11.2"}
PENDING = {"P11.3.m2", "P11.3.m4", "P11.3.m5", "P11.close.m1", "P11.close.m4"}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as source:
        while block := source.read(1024 * 1024):
            value.update(block)
    return value.hexdigest()


def require(ok):
    if not ok:
        raise ValueError("invalid_P11_local_partial_checkpoint")


def validate(proof):
    require(proof["unit"] == "P11-ES" and proof["status"] == "local_sprint_complete_external_gates_pending")
    require(proof["P11_accepted"] is False and proof["local_sprint_accepted"] is True and proof["local_sprint_percent"] == "100.00%")
    require(proof["engine"] == 15 and proof["compatibility"] == 150 and proof["primary_port"] == 4178)
    require(proof["tables"] == 185 and proof["foreign_keys"] == 330 and proof["bindings"] == 155 and proof["new_domain_tables"] == 0)
    require(proof["database"] == "CBN_P11ES_TRIAL_20261028_e0a14ef5")
    require(proof["academic_DDL_or_DML"] is False and proof["real_provider_calls"] == 0 and proof["actual_external_receipts"] is False)
    require(proof["metadata_or_history_cache"] is False and proof["institutional_commissioning_accepted"] is False)
    require(proof["fixed_criteria"] == 56 and proof["fixed_milestones"] == 279 and proof["done_milestones"] == 261 and proof["accepted_criteria"] == 45)
    require(proof["overall_technical_percent"] == "93.62%" and proof["phase_percentages"]["P11"] == "72.50%")
    require(proof["P12_auxiliary_percent"] == "0.00%" and proof["P12_canonical_weight_added"] == 0)
    require(proof["phase_percentages"] == {"P0":"100.00%","P1":"100.00%","P2":"100.00%","P3":"100.00%","P4":"82.29%","P5":"100.00%","P6":"100.00%","P7":"82.29%","P8":"95.00%","P9":"93.75%","P10":"95.00%","P11":"72.50%"})
    required = {"backend/tools/check_p11_es_checkpoint.py", "backend/tools/p11_parent_replay.py", "backend/tools/p11_es_graphs.py", "backend/app/institutional/operations.py", "backend/app/institutional/operations_policy.py", "backend/app/institutional/spanish.py", "frontend/src/institution/OperationsWorkspace.tsx", "frontend/src/institution/Settings.tsx", "compose.operations.yaml", "tasks/p11-es-progress.json", "tasks/p12-online-backlog.json", "artifacts/p11-es/criteria-matrix.json"}
    require(required <= set(proof["source_pins"]))
    baseline = read(ROOT / "docs/adaptation/sql/p11_es_input_baseline.json")
    previous = {e["path"]:e for e in baseline["files"]}
    require(sha(ROOT / ".local/p11-es/public-preimages.zip") == baseline["source_archive_sha256"])
    require(sha(ROOT / "docs/adaptation/sql/p10_es_validation.json") == baseline["parent_P10_proof_sha256"])
    for name, digest in proof["source_pins"].items():
        path = (ROOT / name).resolve()
        require(path.is_relative_to(ROOT.resolve()) or name in previous and path.is_relative_to((ROOT.parent / "saas-version").resolve()))
        if name.startswith(".local/") and name not in previous:
            require(path.suffix in {".py", ".cjs"} or path.name == "public-preimages.zip")
        require(sha(path) == digest)
    for name, transition in proof["changed_predecessors"].items():
        require(previous[name]["sha256"] == transition["before"] and sha(ROOT / name) == transition["after"])
        require(not name.startswith("../") and "/migrations/" not in name and not name.endswith("_policy.py"))
    for name, digest in proof["frozen_releases"].items():
        require(sha(ROOT / name) == digest)
    require(sha(ROOT / "backend/operations/cbn_institutional_operations_v1/release.json") == proof["release_sha256"])
    original_reader = previous["backend/tools/es_schema_catalog_v2.py"]
    require(sha(ROOT / original_reader["path"]) == original_reader["sha256"])
    review = read(ROOT / "artifacts/p11-es/acceptance-review.json")
    require(review["P11_accepted"] is False and review["local_sprint_accepted"] and set(review["accepted_criteria"]) == ACCEPTED and set(review["pending_milestones"]) == PENDING)
    for name, digest in review["evidence"].items():
        require(sha(ROOT / name) == digest)
    for name, minimum in {"workers":22,"guards":8,"extras":5,"boundaries":5,"recovery":10,"final-recovery":10,"preservation":6,"restart":15,"reversal":8}.items():
        receipt = read(ROOT / ("artifacts/p11-es/" + name + "-result.json"))
        require(receipt["status"] == "passed" and len(receipt["checks"]) >= minimum)
    access = read(ROOT / "artifacts/p11-es/access-result.json")
    require(access["status"] == "passed" and access["role_action_cells"] == 150 and access["route_method_boundaries"] == 188)
    require(sum(len(v["csrf_roles"]) for v in access["routes"]) == 510 and all(v["anonymous_status"] == 401 for v in access["routes"]))
    for name in ["recovery","final-recovery"]:
        receipt = read(ROOT / ("artifacts/p11-es/" + name + "-result.json"))
        require(receipt["stable_tables"] == 171 and receipt["ready_blobs"] == 4 and receipt["provider_calls"] == 0)
    guards = read(ROOT / "artifacts/p11-es/guards-result.json")
    require(guards["metadata_or_history_cache"] is False and guards["P3_P4_guards_retained"] and guards["before"]["queries"] == 273 and guards["after"]["queries"] == 121)
    restart = read(ROOT / "artifacts/p11-es/restart-result.json")
    require(restart["stable_tables"] == 182 and restart["ready_blobs"] == 4 and len(restart["message_read_latency_ms"]) == 6 and restart["burst_concurrency"] == 2)
    reversal = read(ROOT / "artifacts/p11-es/reversal-result.json")
    require(reversal["stable_tables"] == 182 and reversal["original_database_used_for_rollback"] is False and reversal["final_image"] == "crm-cbn-workspace:p11es-r3")
    deployment = read(ROOT / "artifacts/p11-es/deployment-result.json")
    require(deployment["image_tag"] == "crm-cbn-workspace:p11es-r3" and deployment["image_digest"] == proof["image_digest"] and deployment["runtime_Python_application_files_match_workspace"] == 224 and deployment["old_P10_container_retained_stopped"] and deployment["root_read_only"] and deployment["SQL_profile_and_CA_read_only"])
    checks = read(ROOT / "artifacts/p11-es/final-checks.json")
    require(checks["status"] == "passed" and checks["checks"]["backend"]["passed"] == 440 and checks["checks"]["frontend"]["passed"] == 354 and all(v["status"] == "passed" for v in checks["checks"].values()))
    ui = read(ROOT / "artifacts/p11-es/browser/final-result.json")
    mobile = read(ROOT / "artifacts/p11-es/browser/mobile-light-result.json")
    require(ui["status"] == mobile["status"] == "passed" and len(ui["cells"]) == 84 and len(mobile["cells"]) == 28)
    require(all(not c["overflow"] and c.get("keyboard") is not False for c in ui["cells"] + mobile["cells"]))
    require(len({(c["route"], c["theme"], c["viewport"]) for c in ui["cells"] + mobile["cells"]}) == 112)
    require(len(read(ROOT / "artifacts/p11-es/browser/errors-result.json")["checks"]) >= 7)
    require(len(proof["memory_transitions"]) == 13 and all(t["before"] != t["after"] and previous[name]["sha256"] == t["before"] and sha(ROOT / name) == t["after"] for name,t in proof["memory_transitions"].items()))
    for kind in ["access", "operations"]:
        static = read(ROOT / ("artifacts/p11-es/" + kind + "-review.json"))
        for entry in static["source_manifest"]:
            require(sha(ROOT / entry["path"]) == entry["sha256"])
    matrix = read(ROOT / "artifacts/p11-es/criteria-matrix.json")
    require(len(matrix["criteria"]) == 56 and matrix["no_blanket_reacceptance"])
    online = read(ROOT / "tasks/p12-online-backlog.json")
    require(online["canonical_weight_added"] == 0 and len(online["pending_existing_milestones"]) == 18 and online["no_double_credit"])
    parent = read(ROOT / "artifacts/p11-es/parent-replay-result.json")
    require(parent["status"] == "passed" and parent["exact_preimages"] == 1769 and parent["SQL_connected"] is False and parent["parent_checker_bytes_modified"] is False)
    return dict(status="passed", P11="72.50%", local_sprint="100.00%", overall="93.62%", source_pins=len(proof["source_pins"]), accepted_P11_criteria=sorted(ACCEPTED), pending_dependencies=sorted(PENDING), memory_transitions=13, SQL_connected=False)


def self_test(proof):
    cases = [("engine",16),("compatibility",160),("primary_port",4173),("tables",138),("new_domain_tables",1),("database","HORARIOSSIIE"),("real_provider_calls",1),("academic_DDL_or_DML",True),("P11_accepted",True),("local_sprint_accepted",False),("fixed_criteria",57),("done_milestones",279),("accepted_criteria",56),("overall_technical_percent","100.00%"),("P12_canonical_weight_added",1),("actual_external_receipts",True),("institutional_commissioning_accepted",True),("metadata_or_history_cache",True)]
    for key,value in cases:
        bad = copy.deepcopy(proof);bad[key] = value
        try: validate(bad)
        except (ValueError, AssertionError): pass
        else: raise AssertionError("false_P11_completion_accepted")
    return len(cases)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--replay-parent", action="store_true")
    args = parser.parse_args()
    proof = read(ROOT / "docs/adaptation/sql/p11_es_validation.json")
    result = validate(proof)
    from phase_work_progress import check as progress_check
    from p11_es_graphs import check as graph_check
    result["work_progress"] = progress_check(negatives=args.self_test)
    result["graph"] = graph_check()
    if args.self_test: result["negative_cases_rejected"] = self_test(proof)
    if args.replay_parent:
        from p11_parent_replay import replay_parent
        result["parent"] = {k:v for k,v in replay_parent().items() if k!="result"}
    print(json.dumps(result, ensure_ascii=False))
