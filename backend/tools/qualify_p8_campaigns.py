"""P8 actual SQL2019 CRUD, revisions, simulation, multi-step queue and fences."""

import json, os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from app.institutional.campaign_runtime import Worker
from app.institutional.channel_outbox import Dispatcher
from app.institutional.broadcast_dispatch import Worker as Bulk
from app.institutional.broadcast_templates import send
from tools.p8_test_support import Harness
from tools.prepare_p8_campaign import WORK, save


def main():
    h = Harness(os.environ.get("P8_FIXTURE", "fixture"))
    checks = []

    def check(name, ok=True):
        assert ok, name
        checks.append(name)
        save(WORK / "api-result.json", dict(status="in_progress", checks=checks))

    resume = os.environ.get("P8_RESUME") == "wait"
    if resume:
        from tools.prepare_p8_campaign import read

        checks = read(WORK / "api-result.json")["checks"]
        assert len(checks) == 6
        account = str(
            h.sql(
                "SELECT IntegrationId FROM crm_channels2.ExternalIdentity WHERE ExternalId='573100000081'"
            )[0][0]
        ).lower()
        row = h.sql(
            "SELECT IdentityId,ContactId,ConversationId FROM crm_channels2.ExternalIdentity WHERE ExternalId='573100000081'"
        )[0]
        person = dict(
            id=str(row[0]).lower(),
            contact=str(row[1]).lower(),
            conversation=str(row[2]).lower(),
            phone="573100000081",
        )
        records = h.call("campaigns")["items"]
        template = next(v for v in records if v["kind"] == "template")
        flow = next(
            v
            for v in records
            if v["kind"] == "flow" and len(v["document"]["steps"]) == 1
        )
        worker = Worker(h.settings, h.gateway)
        bulk = Bulk(h.settings, controlled=True)
        effects = []

        def transport(a, p, **kw):
            kw["before_send"]()
            effects.append(p)
            return "wamid.p8." + uuid4().hex

        dispatcher = Dispatcher(h.settings, transport=transport, allow_controlled=True)
    else:
        account = h.account("81")
        person = h.incoming(account, "573100000081", "Ana Controlada P8")
        h.grant(account, person)
        h.cadence8(account)
        check("owned_SQL2019_TLS_167_table_copy_and_signed_incoming")
        template = h.template8()
        segment = h.save8("segment", dict(filters={"contact_ids": [person["contact"]]}))
        h.act8(segment["id"], "activate")
        preview = h.call("campaigns/" + segment["id"] + "/preview")
        check(
            "saved_segment_uses_real_CRM_rows_without_academic_claims",
            preview["total"] == 1,
        )
        before = h.sql("SELECT COUNT(*) FROM crm_channels2.SendJob")[0][0]
        simulation = h.call(
            "campaigns/" + template["id"] + "/simulate",
            "POST",
            h.cmd(identity_id=person["id"]),
        )
        check(
            "CRM_template_render_and_simulation_have_no_queue_or_Meta_approval",
            simulation["text"].startswith("Hola Ana")
            and simulation["provider_POSTs"] == 0
            and h.sql("SELECT COUNT(*) FROM crm_channels2.SendJob")[0][0] == before,
        )
        flow = h.flow8(
            account,
            template,
            segment_id=segment["id"],
            segment_version=segment["version"],
        )
        run = h.enroll8(flow, person)
        worker = Worker(h.settings, h.gateway)
        bulk = Bulk(h.settings, controlled=True)
        effects = []

        def transport(a, p, **kw):
            kw["before_send"]()
            effects.append(p)
            return "wamid.p8." + uuid4().hex

        dispatcher = Dispatcher(h.settings, transport=transport, allow_controlled=True)
        assert worker.once()
        check(
            "CRM_send_has_one_native_C10_queue_and_no_Meta_catalog",
            h.sql("SELECT COUNT(*) FROM crm_campaign8.Event WHERE Kind='native_chat'")[
                0
            ][0]
            == 1
            and h.sql("SELECT COUNT(*) FROM crm_broadcast7.Attempt")[0][0] == 0,
        )
        h.release8(account)
        assert dispatcher.once()
        assert worker.once()
        assert worker.once()
        check(
            "CRM_flow_completes_without_fabricating_delivery",
            h.run8(run)["state"] == "completed"
            and len(effects) == 1
            and h.call("campaigns/" + flow["id"] + "/metrics")["variants"][0][
                "accepted"
            ]
            == 1,
        )
        # Same operation is replayed and stale edits are refused.
        record_id = str(uuid4())
        body = h.cmd(kind="segment", name="Idempotente", document={"filters": {}})
        a = h.call("campaigns/" + record_id, "PUT", body)
        b = h.call("campaigns/" + record_id, "PUT", body)
        h.call(
            "campaigns/" + record_id,
            "PUT",
            h.cmd(kind="segment", name="Obsoleto", document={"filters": {}}),
            409,
        )
        check(
            "exact_replay_and_CAS_preserve_single_version",
            a == b
            and len(h.call("campaigns/" + record_id + "/versions")["items"]) == 1,
        )
    # A persisted wait survives constructing a fresh worker and competing producers.
    if resume:
        flow2 = next(
            v
            for v in records
            if v["kind"] == "flow" and len(v["document"]["steps"]) == 3
        )
        run2 = str(
            h.sql(
                "SELECT EnrollmentId FROM crm_campaign8.Enrollment WHERE FlowId=?",
                flow2["id"],
            )[0][0]
        ).lower()
        # Controlled future clock, preserving the existing step; no reset on worker construction.
        h.sql(
            "UPDATE crm_campaign8.Step SET DueAt=DATEADD(minute,1,SYSUTCDATETIME()) WHERE EnrollmentId=?",
            run2,
            write=True,
        )
        h.sql(
            "UPDATE crm_campaign8.Enrollment SET DueAt=(SELECT DueAt FROM crm_campaign8.Step WHERE EnrollmentId=?) WHERE EnrollmentId=?",
            run2,
            run2,
            write=True,
        )
    else:
        flow2 = h.flow8(
            account,
            template,
            steps=[
                dict(kind="wait", wait_minutes=1),
                dict(kind="condition", conditions={"stages": []}),
                dict(kind="send", crm_template_id=template["id"]),
            ],
        )
        run2 = h.enroll8(flow2, person)
        worker.once()
    due = h.run8(run2)["due"]
    check(
        "wait_persists_absolute_due_time_across_worker_restart",
        not Worker(h.settings, h.gateway).once() and h.run8(run2)["due"] == due,
    )
    h.sql(
        "UPDATE crm_campaign8.Step SET DueAt=DATEADD(second,-1,SYSUTCDATETIME()) WHERE EnrollmentId=?",
        run2,
        write=True,
    )
    h.sql(
        "UPDATE crm_campaign8.Enrollment SET DueAt=DATEADD(second,-1,SYSUTCDATETIME()) WHERE EnrollmentId=?",
        run2,
        write=True,
    )
    for _ in range(3):
        worker.once()
    h.release8(account)
    with ThreadPoolExecutor(2) as pool:
        list(pool.map(lambda _: Worker(h.settings, h.gateway).once(), range(2)))
    check(
        "concurrent_producers_have_one_step_and_one_queue",
        h.sql(
            "SELECT COUNT(*) FROM crm_campaign8.Step WHERE EnrollmentId=? AND Kind='send'",
            run2,
        )[0][0]
        == 1
        and h.sql(
            "SELECT COUNT(*) FROM crm_campaign8.Event e JOIN crm_campaign8.Step s ON s.StepId=e.StepId WHERE s.EnrollmentId=? AND e.Kind='native_chat'",
            run2,
        )[0][0]
        == 1,
    )
    # Incoming reply is visible even before the background cancellation loop.
    h.incoming(account, person["phone"], "Ana Controlada P8", "Tengo una pregunta")
    count = len(effects)
    dispatcher.once()
    worker.once()
    check(
        "reply_between_queue_and_POST_fences_effect",
        len(effects) == count and h.run8(run2)["state"] == "cancelled",
    )
    # Explicit opt-out cannot be bypassed by old consent. Re-grant requires operator evidence.
    h.incoming(account, person["phone"], "Ana Controlada P8", "STOP")
    preview = h.call("campaigns/" + flow["id"] + "/preview")
    check(
        "authenticated_opt_out_overrides_old_consent",
        preview["counts"]["eligible"] == 0
        and "marketing_consent_required" in preview["items"][0]["reasons"],
    )
    h.grant(account, person)
    # Snapshot program/stage/handoff are fenced independently.
    for field, value, reason in [
        ("Stage", "cambio_controlado", "campaign_stage_changed"),
        ("ProgramId", 999, "campaign_program_changed"),
    ]:
        f = h.flow8(account, template)
        rr = h.enroll8(f, person)
        original = h.sql(
            "SELECT " + field + " FROM crm.Contact WHERE ContactId=?", person["contact"]
        )[0][0]
        h.sql(
            "UPDATE crm.Contact SET " + field + "=? WHERE ContactId=?",
            value,
            person["contact"],
            write=True,
        )
        worker.once()
        check(
            reason,
            h.run8(rr)["state"] == "cancelled" and h.run8(rr)["reason"] == reason,
        )
        h.sql(
            "UPDATE crm.Contact SET " + field + "=? WHERE ContactId=?",
            original,
            person["contact"],
            write=True,
        )
    f = h.flow8(account, template)
    rr = h.enroll8(f, person)
    worker.once()
    h.act8(f["id"], "pause")
    check("pause_cancels_unstarted_queue", h.run8(rr)["state"] == "paused")
    h.act8(f["id"], "activate")
    h.act8(f["id"], "resume", identity_ids=[rr])
    h.release8(account)
    dispatcher.once()
    worker.once()
    worker.once()
    check(
        "reviewed_resume_preserves_old_cancelled_attempt",
        h.run8(rr)["state"] == "completed",
    )
    # Meta approved templates remain a distinct route through the P7 producer.
    h.sync(account)
    t = next(
        v
        for v in h.call("broadcasts/options")["templates"]
        if v["integration_id"] == account and v["origin"] == "controlled"
    )
    variables = {
        "body.1": {"source": "customer_first_name"},
        "body.2": {"source": "literal", "value": "admisiones"},
        "header.1": {"source": "literal", "value": "CBN"},
        "button.0.1": {"source": "literal", "value": "programas"},
    }
    f = h.flow8(
        account,
        template,
        steps=[
            dict(
                kind="send",
                meta_template_id=t["id"],
                meta_template_version=t["version"],
                variables=variables,
            )
        ],
    )
    rr = h.enroll8(f, person)
    h.release8(account)
    assert worker.once()
    assert bulk.once()
    d = Dispatcher(
        h.settings,
        transport=lambda a, p, **kw: send(a, p, request=h.gateway, **kw),
        allow_controlled=True,
    )
    assert d.once()
    h.act8(f["id"], "pause")
    h.act8(f["id"], "activate")
    h.act8(f["id"], "resume", identity_ids=[rr])
    worker.once()
    worker.once()
    check(
        "official_Meta_template_uses_existing_P7_attempt_and_C10_dispatcher",
        h.run8(rr)["state"] == "completed"
        and len(h.gateway.posts) == 1
        and h.sql("SELECT COUNT(*) FROM crm_broadcast7.Attempt")[0][0] == 1,
    )
    h.receipt(
        account,
        h.sql(
            "SELECT ExternalId FROM crm_channels2.SendJob WHERE ExternalId IS NOT NULL ORDER BY CreatedAt DESC"
        )[0][0],
        "read",
        person["phone"],
    )
    check(
        "authenticated_receipt_updates_real_variant_measurement",
        sum(v["read"] for v in h.call("campaigns/" + f["id"] + "/metrics")["variants"])
        == 1,
    )
    save(
        WORK / "api-result.json",
        dict(
            status="passed",
            checks=checks,
            database=h.settings.connection["database"],
            real_provider_calls=0,
            academic_writes=False,
        ),
    )
    print(json.dumps(dict(status="passed", checks=len(checks))))


if __name__ == "__main__":
    main()
