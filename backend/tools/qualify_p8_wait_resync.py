"""Resumed waits preserve their stored deadline and do not starve a ready run."""

import json
from tools.p8_test_support import Harness
from tools.prepare_p8_campaign import WORK, save
from app.institutional.campaign_runtime import Worker


def main():
    h = Harness("runtime-r2")
    row = h.sql(
        "SELECT IdentityId,ContactId,ConversationId,IntegrationId FROM crm_channels2.ExternalIdentity WHERE ExternalId='573100000082'"
    )[0]
    p = dict(
        id=str(row[0]).lower(),
        contact=str(row[1]).lower(),
        conversation=str(row[2]).lower(),
    )
    a = str(row[3]).lower()
    t = h.template8()
    f = h.flow8(a, t, steps=[dict(kind="wait", wait_minutes=10)])
    r = h.enroll8(f, p)
    w = Worker(h.settings, h.gateway)
    for _ in range(10):
        w.once()
        if h.sql("SELECT COUNT(*) FROM crm_campaign8.Step WHERE EnrollmentId=?", r)[0][
            0
        ]:
            break
    due = h.run8(r)["due"]
    h.act8(f["id"], "pause")
    h.act8(f["id"], "activate")
    h.act8(f["id"], "resume", identity_ids=[r])
    assert h.run8(r)["due"] == due
    second = h.flow8(a, t, steps=[dict(kind="condition", conditions={})])
    other = h.enroll8(second, p)
    # Fault is confined to the fixture: its authoritative Step deadline stays intact.
    h.sql(
        "UPDATE crm_campaign8.Enrollment SET DueAt=DATEADD(minute,-1,SYSUTCDATETIME()) WHERE EnrollmentId=?",
        r,
        write=True,
    )
    w.once()
    assert h.run8(r)["due"] == due and h.run8(r)["step"] == 0
    for _ in range(5):
        w.once()
    assert h.run8(other)["state"] == "completed"
    h.act8(f["id"], "pause")
    checks = [
        "pause_and_reviewed_resume_keep_persisted_wait_deadline",
        "inconsistent_poll_clock_resyncs_from_authoritative_step",
        "future_wait_does_not_starve_ready_condition_execution",
    ]
    save(
        WORK / "wait-resync-result.json",
        dict(
            status="passed", checks=checks, real_provider_calls=0, academic_writes=False
        ),
    )
    print(json.dumps(dict(status="passed", checks=len(checks))))


if __name__ == "__main__":
    main()
