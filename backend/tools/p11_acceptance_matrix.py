"""Criterion-by-layer evidence inventory; never promotes inherited partial work."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8-sig"))


def main():
    ledger = read("docs/adaptation/phase-progress-contract.json")
    work = read("docs/adaptation/phase-work-progress.json")
    replay = read("artifacts/p11-es/parent-replay-result.json")
    assert replay["status"] == "passed" and not replay["SQL_connected"]
    rows = []
    for phase, technical in zip(ledger["phases"], work["phases"]):
        for c, t in zip(phase["criteria"], technical["criteria"]):
            assert c["id"] == t["id"]
            evidence = []
            for e in c["evidence"]:
                path = ROOT / e["file"]
                assert path.is_file(), e["file"]
                evidence.append(dict(e, sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
            rows.append(dict(id=c["id"], phase=phase["id"], requirement=c["requirement"], definition=c["source"], state=c["state"], accepted_scope=c.get("accepted_scope"), remaining_scope=c.get("remaining_scope"), technical_percent=t["technical_completion"]["percent_display"], milestones=[{k:m[k] for k in ["id","state","evidence_level","evidence_refs"]} for m in t["milestones"]], layers={"contract":dict(status="pinned_original_requirement", evidence=evidence), "inherited_acceptance":dict(status="exact_frozen_P10_to_P1_replay", evidence="artifacts/p11-es/parent-replay-result.json", reaccepted_by_this_inventory=False), "current_SQL_and_authority":dict(status="cross_cutting_current_profile_coverage_not_all_business_mutations", evidence=["artifacts/p11-es/access-result.json","artifacts/p11-es/guards-result.json","artifacts/p11-es/boundaries-result.json","artifacts/p11-es/preservation-result.json"]), "current_UI":dict(status="implemented_capability_routes_and_declared_pending_notice", evidence=["artifacts/p11-es/browser/routes-result.json","artifacts/p11-es/browser/final-result.json","artifacts/p11-es/browser/mobile-light-result.json","artifacts/p11-es/browser/errors-result.json"], deferred_not_accepted=["admissions"]), "operations":dict(status="local_only", evidence=["artifacts/p11-es/workers-result.json","artifacts/p11-es/final-recovery-result.json","artifacts/p11-es/restart-result.json","artifacts/p11-es/reversal-result.json"]), "institutional_external":dict(status="pending_P12_where_required", pending_milestones=[m["id"] for m in t["milestones"] if m["state"]!="done"], evidence="tasks/p12-online-backlog.json")}))
    assert len(rows) == 56
    value = dict(status="passed", unit="P11-ES", criteria=rows, accepted_criteria=sum(c["state"]=="accepted" for c in rows), no_blanket_reacceptance=True, current_evidence_is_cross_cutting_not_per_resource_lifecycle=True, definition_unchanged=True, academic_mapping_complete=False, online_accepted=False)
    (ROOT / "artifacts/p11-es/criteria-matrix.json").write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(dict(status="passed", criteria=56, accepted=value["accepted_criteria"]))


if __name__ == "__main__":
    main()
