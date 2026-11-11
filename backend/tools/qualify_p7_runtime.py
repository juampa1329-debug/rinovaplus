"""Controlled P7 frontiers, native queue, cadence and authenticated receipt races."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from uuid import uuid4

from app.institutional.broadcast_dispatch import Worker, reconcile_receipts
from app.institutional.broadcast_templates import send
from app.institutional.channel_events import EventWorker
from app.institutional.channel_outbox import Dispatcher
from app.institutional.store import transaction
from tools.p7_test_support import Harness
from tools.prepare_p7_broadcast import WORK, read, save


def main():
    import os

    h = Harness(os.environ.get("P7_FIXTURE", "fixture-r5"))
    resume = os.environ.get("P7_RESUME") == "future"
    checks = read(WORK / "runtime-result.json")["checks"] if resume else []
    assert not resume or len(checks) == 14, (
        "resume requires the exact already-recorded controlled checkpoint"
    )

    def check(name, condition=True):
        assert condition, name
        checks.append(name)
        save(WORK / "runtime-result.json", {"status": "in_progress", "checks": checks})

    if resume:
        identity = h.sql(
            (
                "SELECT IdentityId,ContactId,Conversati"
                "onId,IntegrationId FROM crm_channels2."
                "ExternalIdentity WHERE ExternalId='573"
                "100000004'"
            )
        )[0]
        person = dict(
            id=str(identity[0]).lower(),
            contact=str(identity[1]).lower(),
            conversation=str(identity[2]).lower(),
            phone="573100000004",
        )
        integration = str(identity[3]).lower()
    else:
        integration = h.account("2")
        person = h.incoming(integration, "573100000004", "Diana Controlada")
        h.sync(integration)
        h.grant(integration, person)

    def cadence(limit=100, revision=None):
        current = h.call("broadcasts/accounts/" + integration + "/cadence")
        h.call(
            "broadcasts/accounts/" + integration + "/cadence",
            "PUT",
            h.cmd(
                current["revision"] if revision is None else revision,
                enabled=True,
                daily_limit=limit,
                interval_seconds=1,
            ),
        )

    cadence()
    worker = Worker(h.settings, controlled=True)
    dispatcher = Dispatcher(
        h.settings,
        transport=lambda a, p, **kw: send(a, p, request=h.gateway, **kw),
        allow_controlled=True,
    )

    def release_cadence():
        h.sql(
            (
                "UPDATE crm_broadcast7.Cadence SET Next"
                "At=DATEADD(second,-1,SYSUTCDATETIME())"
                " WHERE IntegrationId=?"
            ),
            integration,
            write=True,
        )

    def make(**changes):
        key = h.campaign(
            integration, filters={"contact_ids": [person["contact"]]}, **changes
        )
        h.action(key, "activate")
        release_cadence()
        return key

    def row(key):
        return h.call("broadcasts/" + key + "/report")["items"][0]

    def queue(key):
        assert worker.once()
        value = row(key)
        assert value["status"] == "queued"
        return value

    if not resume:
        key = make()
        rec = queue(key)
        before = len(h.gateway.posts)
        h.gateway.before_get = lambda: h.grant(integration, person, "revoked")
        dispatcher.once()
        check(
            ("consent_revoked_between_catalog_GET_and_POST_fences_actual_effect"),
            len(h.gateway.posts) == before and row(key)["status"] == "failed",
        )
        h.grant(integration, person)
        h.action(key, "retry", recipient_ids=[rec["id"]])
        release_cadence()
        queue(key)
        dispatcher.once()
        check(
            ("selective_reviewed_retry_creates_new_attempt_preserving_old_failure"),
            row(key)["status"] == "accepted"
            and row(key)["attempts"] == 2
            and h.sql(
                ("SELECT COUNT(*) FROM crm_broadcast7.Attempt WHERE RecipientId=?"),
                rec["id"],
            )[0][0]
            == 2,
        )
        h.action(key, "retry", 409, recipient_ids=[rec["id"]])
        h.action(key, "pause")
        key = make()
        rec = queue(key)
        before = len(h.gateway.posts)
        h.action(key, "pause")
        dispatcher.once()
        check(
            ("pause_cancels_queued_work_and_increments_epoch_without_POST"),
            row(key)["status"] == "cancelled"
            and len(h.gateway.posts) == before
            and h.call("broadcasts/" + key)["epoch"] == 2,
        )
        h.action(key, "activate")
        release_cadence()
        resumed = queue(key)
        check(
            (
                "reviewed_resume_preserves_cancelled_un"
                "started_attempt_and_creates_new_one"
            ),
            resumed["attempts"] == 2,
        )
        dispatcher.once()
        worker.once()
        check(
            ("fully_accepted_campaign_finishes_without_fabricating_delivery"),
            h.call("broadcasts/" + key)["state"] == "completed"
            and row(key)["status"] == "accepted",
        )
        h.action(key, "pause")
        key = make()
        rec = queue(key)
        h.gateway.fail = "timeout"
        dispatcher.once()
        h.gateway.fail = None
        check(
            ("timeout_after_POST_remains_uncertain_with_durable_attempt"),
            row(key)["status"] == "uncertain",
        )
        before = len(h.gateway.posts)
        dispatcher.once()
        release_cadence()
        worker.once()
        h.action(key, "retry", 409, recipient_ids=[rec["id"]])
        check(
            ("restart_does_not_requeue_uncertain_or_accepted_attempts"),
            len(h.gateway.posts) == before and row(key)["attempts"] == 1,
        )
        h.action(key, "pause")
        key = make()
        rec = queue(key)
        h.gateway.fail = "definitive"
        dispatcher.once()
        h.gateway.fail = None
        check(
            ("definite_rejection_is_failed_without_provider_acceptance"),
            row(key)["status"] == "failed" and not row(key)["provider_message_id"],
        )
        h.action(key, "retry", recipient_ids=[rec["id"]])
        release_cadence()
        queue(key)
        external = "wamid.early.controlled." + uuid4().hex
        h.gateway.next_external = external
        h.gateway.before_post = lambda: h.receipt(
            integration, external, "delivered", person["phone"]
        )
        dispatcher.once()
        check(
            "early_signed_receipt_is_durable_quarantine_not_lost",
            h.sql(
                (
                    "SELECT COUNT(*) FROM crm_channels2.Web"
                    "hookEvent WHERE LastErrorCode='deliver"
                    "y_unmatched'"
                )
            )[0][0]
            >= 1
            and row(key)["status"] == "accepted",
        )
        with transaction(h.settings, True, anonymous=True) as c:
            reconcile_receipts(c, h.settings)
        EventWorker(h.settings).project_once()
        check(
            ("early_receipt_reconciles_after_acceptance_without_resending"),
            row(key)["status"] == "delivered",
        )
        h.receipt(integration, external, "read", person["phone"])
        h.receipt(integration, external, "sent", person["phone"])
        h.receipt(integration, external, "read", person["phone"])
        check(
            ("signed_duplicate_and_out_of_order_receipts_never_regress_read"),
            row(key)["status"] == "read",
        )
        h.incoming(integration, person["phone"], body="Pregunta sin referencia")
        check(
            ("unrelated_incoming_is_not_fabricated_as_campaign_reply"),
            h.call("broadcasts/" + key + "/report")["metrics"]["replied"] == 0,
        )
        h.incoming(
            integration,
            person["phone"],
            body="Respuesta con referencia explícita",
            reply_to=external,
        )
        report = h.call("broadcasts/" + key + "/report")
        check(
            (
                "explicit_signed_reply_context_is_attri"
                "buted_to_the_exact_account_message"
            ),
            report["metrics"]["replied"] == 1
            and report["items"][0]["replied_at"] is not None
            and report["items"][0]["delivered_at"] is not None,
        )
        check(
            "report_search_status_and_SQL_offset_are_consistent",
            h.call("broadcasts/" + key + "/report?state=read&search=Diana")["total"]
            == 1
            and h.call("broadcasts/" + key + "/report?search=inexistente")["total"] == 0
            and h.call("broadcasts/" + key + "/report?offset=100")["items"] == [],
        )
        h.action(key, "pause")

    future = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
    key = (
        str(
            h.sql(
                (
                    "SELECT TOP(1) CampaignId FROM crm_broa"
                    "dcast7.Campaign WHERE State='scheduled"
                    "' ORDER BY CreatedAt DESC"
                )
            )[0][0]
        ).lower()
        if resume
        else make(scheduled_local=future)
    )
    before = len(h.gateway.posts)
    check(
        "future_UTC_schedule_does_not_produce_queue_early",
        not worker.once()
        and h.call("broadcasts/" + key)["state"] == "scheduled"
        and h.sql(
            (
                "SELECT COUNT(*) FROM crm_broadcast7.At"
                "tempt a JOIN crm_broadcast7.Recipient "
                "r ON r.RecipientId=a.RecipientId WHERE"
                " r.CampaignId=?"
            ),
            key,
        )[0][0]
        == 0,
    )
    h.action(key, "pause")
    key = make()
    rec = queue(key)
    h.sql(
        (
            "UPDATE crm_channels2.SendJob SET State"
            "='sending',LeaseId=?,LeaseUntil=DATEAD"
            "D(second,-1,SYSUTCDATETIME()) WHERE Qu"
            "eueId=?"
        ),
        str(uuid4()),
        rec["queue_id"],
        write=True,
    )
    dispatcher.once()
    check(
        "expired_send_lease_is_uncertain_never_queued",
        row(key)["status"] == "uncertain" and len(h.gateway.posts) == before,
    )
    h.action(key, "pause")
    key = make()
    queue(key)
    before = len(h.gateway.posts)
    h.gateway.before_get = lambda: h.sql(
        ("UPDATE crm.Conversation SET ControlMode='human' WHERE ConversationId=?"),
        person["conversation"],
        write=True,
    )
    dispatcher.once()
    check(
        ("human_takeover_immediately_before_POST_blocks_bulk_effect"),
        row(key)["status"] == "failed" and len(h.gateway.posts) == before,
    )
    h.action(key, "pause")
    h.sql(
        ("UPDATE crm.Conversation SET ControlMode='ai' WHERE ConversationId=?"),
        person["conversation"],
        write=True,
    )
    key = make()
    queue(key)
    h.gateway.status = "PAUSED"
    before = len(h.gateway.posts)
    dispatcher.once()
    h.gateway.status = "APPROVED"
    check(
        ("live_Meta_template_pause_prevents_POST_even_with_old_approved_cache"),
        row(key)["status"] == "failed" and len(h.gateway.posts) == before,
    )
    h.action(key, "pause")
    # One account cadence is shared across two campaigns, with serialized workers.
    h.sql(
        (
            "UPDATE crm_broadcast7.Cadence SET Rese"
            "rved=0,WindowAt=SYSUTCDATETIME() WHERE"
            " IntegrationId=?"
        ),
        integration,
        write=True,
    )
    cadence(1)
    first = make()
    second = make()
    start = h.sql("SELECT COUNT(*) FROM crm_broadcast7.Attempt")[0][0]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda _: Worker(h.settings, controlled=True).once(), range(2))
        )
    check(
        ("concurrent_campaign_workers_share_one_atomic_account_cadence"),
        sum(results) == 1
        and h.sql("SELECT COUNT(*) FROM crm_broadcast7.Attempt")[0][0] == start + 1,
    )
    release_cadence()
    check(
        ("rolling_24_hour_limit_cannot_be_bypassed_by_second_campaign"),
        not worker.once(),
    )
    for key in [first, second]:
        h.action(key, "pause")
    # HTTP permission and CSRF enforcement are exercised against the real API.
    response = h.b.client.put(
        "/api/institution/broadcasts/accounts/" + integration + "/cadence",
        json=h.cmd(enabled=True, daily_limit=1, interval_seconds=1),
        headers={"X-CRM-Local": "1"},
    )
    check("native_mutation_requires_CSRF", response.status_code == 403)
    from tools.qualify_p3_workspace import Browser

    anonymous = Browser(h.app)
    response = anonymous.client.get(
        "/api/institution/broadcasts", headers={"X-CRM-Local": "1"}
    )
    check("unauthenticated_campaign_data_is_denied", response.status_code == 401)
    save(
        WORK / "runtime-result.json",
        {
            "status": "passed",
            "checks": checks,
            "engine": 15,
            "compatibility": 150,
            "controlled_provider_POSTs_observed_in_this_process": len(h.gateway.posts),
            "resumed_from_recorded_checks": 14 if resume else 0,
            "real_provider_calls": 0,
            "actual_external_receipts": False,
            "academic_writes": False,
        },
    )
    print(json.dumps({"P7_runtime_checks": len(checks), "status": "passed"}))


if __name__ == "__main__":
    main()
