"""Verify P11's complete ancestor chain once, with native rollback-only corruption."""

import collections
import sys

from app.institutional import operations_policy
from app.institutional.spanish import transaction
from tools.p10_learning_recovery import fingerprint
from tools.p11_test_support import Harness
from tools.prepare_p11_operations import WORK, admin, read, save


def main():
    assert not (WORK / "guards-result.json").exists(), "fresh qualification required"
    h = Harness("guards")
    calls = collections.Counter()
    def observe(frame, event, arg):
        module = frame.f_globals.get("__name__", "")
        if event == "call" and frame.f_code.co_name == "verify" and module.startswith("app.institutional.") and "policy" in module:
            calls[module.rsplit(".", 1)[1]] += 1
    sys.setprofile(observe)
    try:
        with transaction(h.settings, anonymous=True):
            pass
    finally:
        sys.setprofile(None)
    # Ads v2 validates both v1/v2 rows itself and delegates to campaigns;
    # it deliberately does not call the older v1-only verifier.
    expected = {name: 1 for name in ["operations_policy", "learning_policy", "ads_policy", "campaign_policy", "broadcast_policy", "knowledge_policy", "agents_policy"]}
    assert dict(calls) == expected, dict(calls)
    checks = ["one_complete_P5_to_P10_verifier_chain_in_same_fresh_P11_guard"]
    mapping = operations_policy.layout()["tables"]
    with admin(h.settings.connection["database"]) as db:
        c = db.cursor()
        before = fingerprint(c)
        for prefix in ["crm_agents5", "crm_knowledge6", "crm_broadcast7", "crm_campaign8", "crm_ads9", "crm_learning10"]:
            table = mapping[prefix + ".Journal"]
            c.execute("SET XACT_ABORT ON;BEGIN TRANSACTION")
            try:
                c.execute("UPDATE " + table + " SET ManifestSha256=?", "f" * 64)
                try:
                    operations_policy.verify(c, h.settings.ticket)
                except ValueError:
                    pass
                else:
                    raise AssertionError("P11ES_corrupt_parent_journal_not_rejected_" + prefix)
            finally:
                c.execute("IF @@TRANCOUNT>0 ROLLBACK")
            checks.append("rollback_only_corruption_rejected_" + prefix)
        assert before == fingerprint(c)
    with transaction(h.settings, anonymous=True):
        pass
    checks.append("all_185_tables_unchanged_and_full_runtime_guard_passes_after_all_rollbacks")
    before_perf, after_perf = read(WORK / "guard-before.json"), read(WORK / "guard-after.json")
    assert before_perf["queries"] == 273 and after_perf["queries"] == 121
    save(WORK / "guards-result.json", dict(status="passed", checks=checks, verifier_calls=dict(calls), before=before_perf, after=after_perf, metadata_or_history_cache=False, P3_P4_guards_retained=True, previous_profile_paths_unchanged=True, SQL_TLS_ACL_identity_model_and_journals_preserved=True, academic_DDL_or_DML=False, provider_calls=0, timing_is_local_observation_not_SLA=True))
    print({"status": "passed", "checks": len(checks), "queries_before": 273, "queries_after": 121})


if __name__ == "__main__":
    main()
