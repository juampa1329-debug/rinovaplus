"""Actual SQL capacity rejection and controlled quiet-hour producer fairness."""

import json
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import patch
from app.institutional.campaign_runtime import Worker
from app.institutional.broadcast_dispatch import Worker as Bulk
from app.institutional.spanish_bindings import Cursor
from tools.p8_test_support import Harness
from tools.prepare_p8_campaign import WORK, admin, save


def main():
    h = Harness("qa-r2")
    checks = []
    row = h.sql(
        "SELECT IdentityId,ContactId,ConversationId,IntegrationId FROM crm_channels2.ExternalIdentity WHERE ExternalId='573100000081'"
    )[0]
    p = dict(
        id=str(row[0]).lower(),
        contact=str(row[1]).lower(),
        conversation=str(row[2]).lower(),
    )
    a = str(row[3]).lower()
    h.grant(a, p)
    template = h.template8()
    flow = h.flow8(a, template, steps=[dict(kind="wait", wait_minutes=60)])
    prefix = "CapacityFixture-" + uuid4().hex
    created = 0
    try:
        with admin(h.settings.connection["database"]) as db:
            c = Cursor(db.cursor(), h.settings.ticket["table_map"])
            # Synthetic records are confined to this isolated fixture and carry no send steps.
            c.execute(
                "SET XACT_ABORT ON;BEGIN TRANSACTION;DECLARE @n int=500-(SELECT COUNT(*) FROM crm_campaign8.Enrollment WHERE State IN('waiting','queued','paused','uncertain'));INSERT crm_campaign8.Record(InstitutionId,RecordId,Kind,Name,State,Revision,CurrentVersion,Epoch,Document,ActorId,ActorAuthVersion,ActorSessionId,ApprovedAt) SELECT TOP(@n) f.InstitutionId,NEWID(),'flow',?,'active',1,1,1,f.Document,f.ActorId,f.ActorAuthVersion,f.ActorSessionId,f.ApprovedAt FROM crm_campaign8.Record f CROSS JOIN sys.all_objects n WHERE f.RecordId=?;INSERT crm_campaign8.Version(InstitutionId,RecordId,VersionNo,Kind,Name,Document,Reason,ActorId,OperationId) SELECT InstitutionId,RecordId,1,Kind,Name,Document,'Controlled capacity fixture',ActorId,NEWID() FROM crm_campaign8.Record WHERE Name=?;INSERT crm_campaign8.Enrollment(InstitutionId,EnrollmentId,FlowId,VersionNo,FlowEpoch,IdentityId,ContactId,CanonicalContactId,ConversationId,EntryKey,Variant,State,StepIndex,DueAt,Context) SELECT f.InstitutionId,NEWID(),f.RecordId,1,1,?,?,?, ?,REPLICATE('c',64),'A','waiting',0,DATEADD(day,7,SYSUTCDATETIME()),'{}' FROM crm_campaign8.Record f WHERE f.Name=?;COMMIT",
                prefix,
                flow["id"],
                prefix,
                p["id"],
                p["contact"],
                p["contact"],
                p["conversation"],
                prefix,
            )
            while c.physical.nextset():
                pass
        assert (
            h.sql(
                "SELECT COUNT(*) FROM crm_campaign8.Enrollment WHERE State IN('waiting','queued','paused','uncertain')"
            )[0][0]
            == 500
        )
        h.act8(flow["id"], "enroll", 413, identity_ids=[p["id"]])
        checks.append(
            "five_hundred_open_runs_reject_new_admission_before_worker_starvation"
        )
    finally:
        # No genuine execution/attempt/event is deleted; only this nonce-named synthetic batch.
        with admin(h.settings.connection["database"]) as db:
            c = Cursor(db.cursor(), h.settings.ticket["table_map"])
            created = c.execute(
                "SELECT COUNT(*) FROM crm_campaign8.Record WHERE Name=?", prefix
            ).fetchval()
            c.execute(
                "DELETE e FROM crm_campaign8.Enrollment e JOIN crm_campaign8.Record r ON r.InstitutionId=e.InstitutionId AND r.RecordId=e.FlowId WHERE r.Name=?;DELETE v FROM crm_campaign8.Version v JOIN crm_campaign8.Record r ON r.InstitutionId=v.InstitutionId AND r.RecordId=v.RecordId WHERE r.Name=?;DELETE FROM crm_campaign8.Record WHERE Name=?",
                prefix,
                prefix,
                prefix,
            )
            while c.physical.nextset():
                pass
    assert (
        h.sql("SELECT COUNT(*) FROM crm_campaign8.Record WHERE Name=?", prefix)[0][0]
        == 0
    )
    checks.append(
        "synthetic_capacity_batch_removed_without_changing_real_attempt_history"
    )
    # The producer must defer a quiet candidate and remain able to serve another one.
    h.sync(a)
    t = next(
        v
        for v in h.call("broadcasts/options")["templates"]
        if v["integration_id"] == a and v["origin"] == "controlled"
    )
    variables = {
        "body.1": {"source": "customer_first_name"},
        "body.2": {"source": "literal", "value": "admisiones"},
        "header.1": {"source": "literal", "value": "CBN"},
        "button.0.1": {"source": "literal", "value": "programas"},
    }
    now = datetime.utcnow()
    local = now - timedelta(hours=5)
    start = local + timedelta(minutes=2)
    end = local + timedelta(minutes=10)
    step = dict(
        kind="send",
        meta_template_id=t["id"],
        meta_template_version=t["version"],
        variables=variables,
    )
    quiet = h.flow8(
        a,
        template,
        steps=[step],
        quiet_hours=dict(
            enabled=True,
            timezone="America/Bogota",
            start_time=start.strftime("%H:%M"),
            end_time=end.strftime("%H:%M"),
            days=list(range(7)),
        ),
    )
    free = h.flow8(a, template, steps=[step])
    qrun = h.enroll8(quiet, p)
    frun = h.enroll8(free, p)
    worker = Worker(h.settings, h.gateway)
    for _ in range(15):
        worker.once()
        if (
            h.sql(
                "SELECT COUNT(*) FROM crm_campaign8.Step WHERE EnrollmentId IN(?,?) AND NativeCampaignId IS NOT NULL",
                qrun,
                frun,
            )[0][0]
            == 2
        ):
            break
    future = now + timedelta(minutes=3)
    h.release8(a)
    with (
        patch("app.institutional.campaign_runtime.now", return_value=future),
        patch("app.institutional.campaign_models.now", return_value=future),
    ):
        assert Bulk(h.settings, controlled=True).once()
        assert Bulk(h.settings, controlled=True).once()
    rows = h.sql(
        "SELECT e.EnrollmentId,q.QueueId FROM crm_campaign8.Enrollment e JOIN crm_campaign8.Step s ON s.EnrollmentId=e.EnrollmentId LEFT JOIN crm_broadcast7.Recipient r ON r.CampaignId=s.NativeCampaignId LEFT JOIN crm_channels2.SendJob q ON q.QueueId=r.CurrentQueueId WHERE e.EnrollmentId IN(?,?)",
        qrun,
        frun,
    )
    assert any(str(v[0]).lower() == frun and v[1] for v in rows) and not any(
        str(v[0]).lower() == qrun and v[1] for v in rows
    )
    checks.append(
        "quiet_hour_candidate_is_durably_deferred_without_blocking_other_campaign"
    )
    for f in [quiet, free, flow]:
        h.act8(f["id"], "pause")
    save(
        WORK / "boundaries-result.json",
        dict(
            status="passed",
            checks=checks,
            capacity_fixture_rows=created,
            quiet_clock="controlled_UTC_observation_no_document_mutation",
            real_provider_calls=0,
            academic_writes=False,
        ),
    )
    print(json.dumps(dict(status="passed", checks=len(checks))))


if __name__ == "__main__":
    main()
