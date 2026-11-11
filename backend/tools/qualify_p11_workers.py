"""Requalify real consumers on P11 using the frozen controlled P7 frontier suite."""

import os
from concurrent.futures import ThreadPoolExecutor

from app.institutional.broadcast_dispatch import Worker
from tools import qualify_p7_runtime as suite
from tools.p11_test_support import Harness
from tools.prepare_p11_operations import WORK, read, save


def main():
    assert not (WORK / "runtime-result.json").exists(), "fresh worker qualification required"
    assert os.environ.get("P7_RESUME") is None
    suite.Harness = lambda _label: Harness("workers")
    suite.WORK = WORK
    suite.main()
    report = read(WORK / "runtime-result.json")
    assert report["status"] == "passed"
    report.update(profile="P11_workers_isolated_copy", parent_suite="unmodified_tools.qualify_p7_runtime", real_provider_calls=0, gateway="controlled_in_process_only", academic_writes=False)
    save(WORK / "workers-result.json", report)


def finish_after_recent_auth():
    """Continue exactly the recorded 18 checks, using an actual new login."""
    prior = read(WORK / "runtime-result.json")
    assert prior["status"] == "in_progress" and len(prior["checks"]) == 18
    assert prior["checks"][-1] == "live_Meta_template_pause_prevents_POST_even_with_old_approved_cache"
    assert not (WORK / "workers-first-segment.json").exists()
    save(WORK / "workers-first-segment.json", dict(prior, stopped_reason="428_recent_password_confirmation_required_before_cadence_write", completed_segment_not_full_run=True))
    h = Harness("workers")
    integration = str(h.sql("SELECT IntegrationId FROM crm_channels2.Integration WHERE ExternalAccountId='155570002'")[0][0]).lower()
    person = h.sql("SELECT ContactId FROM crm_channels2.ExternalIdentity WHERE IntegrationId=? AND ExternalId='573100000004'", integration)[0]
    current = h.call("broadcasts/accounts/" + integration + "/cadence")
    h.call("broadcasts/accounts/" + integration + "/cadence", "PUT", h.cmd(current["revision"], enabled=True, daily_limit=1, interval_seconds=1))
    def make():
        key = h.campaign(integration, filters={"contact_ids": [str(person[0]).lower()]})
        h.action(key, "activate")
        h.sql("UPDATE crm_broadcast7.Cadence SET NextAt=DATEADD(second,-1,SYSUTCDATETIME()) WHERE IntegrationId=?", integration, write=True)
        return key
    first, second = make(), make()
    start = h.sql("SELECT COUNT(*) FROM crm_broadcast7.Attempt")[0][0]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: Worker(h.settings, controlled=True).once(), range(2)))
    assert sum(results) == 1 and h.sql("SELECT COUNT(*) FROM crm_broadcast7.Attempt")[0][0] == start + 1
    checks = list(prior["checks"]) + ["concurrent_campaign_workers_share_one_atomic_account_cadence"]
    h.sql("UPDATE crm_broadcast7.Cadence SET NextAt=DATEADD(second,-1,SYSUTCDATETIME()) WHERE IntegrationId=?", integration, write=True)
    assert not Worker(h.settings, controlled=True).once()
    checks.append("rolling_24_hour_limit_cannot_be_bypassed_by_second_campaign")
    for key in [first, second]: h.action(key, "pause")
    h.b.request("broadcasts/accounts/" + integration + "/cadence", "PUT", h.cmd(enabled=True, daily_limit=1, interval_seconds=1), 403, csrf=False)
    checks.append("native_mutation_requires_CSRF")
    from tools.qualify_p3_workspace import Browser
    Browser(h.app).request("broadcasts", expected=401)
    checks.append("unauthenticated_campaign_data_is_denied")
    report = dict(status="passed", checks=checks, segments=[{"completed": 18, "receipt": "workers-first-segment.json"}, {"completed": 4, "recent_auth": "actual_new_owner_login"}], profile="P11_workers_isolated_copy", real_provider_calls=0, actual_external_receipts=False, gateway="controlled_in_process_only", academic_writes=False, completed_as_two_declared_segments=True)
    save(WORK / "workers-result.json", report)
    print({"status": "passed", "checks": len(checks), "segments": 2})


if __name__ == "__main__":
    main()
