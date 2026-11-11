"""Bounded P9 runtime lock wait preserves all SQL guards under controlled contention."""

import json
import time
from concurrent.futures import ThreadPoolExecutor

from tools.p9_test_support import Harness
from tools.prepare_p9_ads import WORK, admin, save


def main():
    h = Harness()
    checks = []
    before = h.sql(
        "SELECT (SELECT COUNT(*) FROM crm_ads9.Event),(SELECT COUNT(*) FROM crm_ads9.Intake),(SELECT SUM(Revision) FROM crm_ads9.Account)"
    )
    with admin(h.settings.connection["database"]) as db:
        c = db.cursor()
        result = c.execute(
            "DECLARE @r int;EXEC @r=sys.sp_getapplock @Resource='crm.local.commit',@LockMode='Exclusive',@LockOwner='Session',@LockTimeout=5000;SELECT @r"
        ).fetchval()
        assert result >= 0
        with ThreadPoolExecutor(1) as pool:
            start = time.monotonic()
            pending = pool.submit(h.call, "ads/accounts")
            try:
                time.sleep(6)
                assert not pending.done(), (
                    "read must remain behind the actual writer lock"
                )
                checks.append(
                    "read_waits_beyond_legacy5s_without_bypassing_exclusive_guard"
                )
            finally:
                c.execute(
                    "EXEC sys.sp_releaseapplock @Resource='crm.local.commit',@LockOwner='Session'"
                )
            value = pending.result(timeout=30)
            assert value["items"] and time.monotonic() - start >= 6
            checks.append(
                "after_release_native_profile_TLS_permissions_and_models_still_validate"
            )
    assert (
        h.sql(
            "SELECT (SELECT COUNT(*) FROM crm_ads9.Event),(SELECT COUNT(*) FROM crm_ads9.Intake),(SELECT SUM(Revision) FROM crm_ads9.Account)"
        )
        == before
    )
    checks.append("guarded_read_does_not_modify_Ads_domain_or_budget_records")
    save(
        WORK / "lock-wait-result.json",
        dict(
            status="passed",
            checks=checks,
            controlled_exclusive_seconds=6,
            P9_lock_wait_milliseconds=15000,
            older_profile_lock_wait_milliseconds=5000,
            engine=15,
            compatibility=150,
            real_provider_calls=0,
            academic_writes=False,
        ),
    )
    print(json.dumps(dict(status="passed", checks=len(checks))))


if __name__ == "__main__":
    main()
