"""Fresh controlled backlog, merge and template-creation uncertainty negatives."""

import json
from uuid import uuid4

from app.institutional.broadcast_dispatch import Worker
from app.institutional.broadcast_templates import send
from app.institutional.channel_outbox import Dispatcher
from tools.p7_test_support import Harness
from tools.prepare_p7_broadcast import WORK, save


def main():
    h = Harness("extras")
    checks = []

    def check(name, condition=True):
        assert condition, name
        checks.append(name)
        save(WORK / "extras-result.json", {"status": "in_progress", "checks": checks})

    integration = h.account("3")
    a = h.incoming(integration, "573100000005", "Elena Controlada")
    b = h.incoming(integration, "573100000006", "Fabio Controlado")
    h.sync(integration)
    for person in [a, b]:
        h.grant(integration, person)
    h.call(
        "broadcasts/accounts/" + integration + "/cadence",
        "PUT",
        h.cmd(enabled=True, daily_limit=100, interval_seconds=300),
    )
    worker = Worker(h.settings, controlled=True)
    dispatcher = Dispatcher(
        h.settings,
        transport=lambda x, p, **kw: send(x, p, request=h.gateway, **kw),
        allow_controlled=True,
    )

    def campaign(people):
        key = h.campaign(
            integration, filters={"contact_ids": [v["contact"] for v in people]}
        )
        h.action(key, "activate")
        return key

    first = campaign([a])
    second = campaign([b])
    assert worker.once() and worker.once()
    check(
        ("backlog_uses_two_existing_C10_jobs_not_a_second_dispatcher"),
        h.sql("SELECT COUNT(*) FROM crm_broadcast7.Attempt")[0][0] == 2,
    )
    dispatcher.once()
    before = len(h.gateway.posts)
    dispatcher.once()
    check(
        ("actual_POST_cadence_prevents_burst_after_backlog_or_budget_release"),
        len(h.gateway.posts) == before == 1
        and h.sql(
            (
                "SELECT COUNT(*) FROM crm_channels2.Sen"
                "dJob WHERE State='queued' AND LastErro"
                "rCode='broadcast_cadence_wait'"
            )
        )[0][0]
        == 1,
    )
    for key in [first, second]:
        h.action(key, "pause")
    h.sql(
        (
            "UPDATE crm_broadcast7.Cadence SET Next"
            "At=DATEADD(second,-1,SYSUTCDATETIME())"
            " WHERE IntegrationId=?"
        ),
        integration,
        write=True,
    )
    key = campaign([a, b])
    assert worker.once() and worker.once()
    dispatcher.once()
    report = h.call("broadcasts/" + key + "/report")
    accepted = next(v for v in report["items"] if v["status"] == "accepted")
    pending = next(v for v in report["items"] if v["status"] == "queued")
    source = next(v for v in [a, b] if v["id"] == accepted["identity_id"])
    target = next(v for v in [a, b] if v["id"] == pending["identity_id"])
    h.sql(
        (
            "INSERT crm_workspace.Merge(MergeId,Sou"
            "rceContactId,TargetContactId,Active) V"
            "ALUES(?,?,?,1)"
        ),
        str(uuid4()),
        source["contact"],
        target["contact"],
        write=True,
    )
    h.sql(
        (
            "UPDATE crm_broadcast7.Cadence SET Next"
            "At=DATEADD(second,-1,SYSUTCDATETIME())"
            " WHERE IntegrationId=?"
        ),
        integration,
        write=True,
    )
    h.sql(
        ("UPDATE crm_channels2.SendJob SET DueAt=SYSUTCDATETIME() WHERE QueueId=?"),
        pending["queue_id"],
        write=True,
    )
    before = len(h.gateway.posts)
    dispatcher.once()
    check(
        ("merge_after_first_acceptance_cannot_send_second_canonical_identity"),
        len(h.gateway.posts) == before
        and h.sql(
            ("SELECT LastErrorCode FROM crm_channels2.SendJob WHERE QueueId=?"),
            pending["queue_id"],
        )[0][0]
        == "canonical_contact_prior_effect",
    )
    h.action(key, "pause")
    tid = str(uuid4())
    draft = h.call(
        "broadcasts/accounts/" + integration + "/templates/" + tid,
        "PUT",
        h.cmd(
            name="creacion_incierta_controlada", body_text="Información institucional"
        ),
    )
    command = h.cmd(draft["version"], confirmed=True)
    h.gateway.fail = "timeout"
    result = h.call("broadcasts/templates/" + tid + "/submit", "POST", command)
    h.gateway.fail = None
    check("uncertain_template_submission_is_durable", result["status"] == "uncertain")
    before = len(h.gateway.posts)
    again = h.call("broadcasts/templates/" + tid + "/submit", "POST", command)
    h.call(
        "broadcasts/templates/" + tid + "/submit",
        "POST",
        h.cmd(draft["version"], confirmed=True),
        409,
    )
    check(
        "new_nonce_cannot_repeat_uncertain_template_creation",
        again["duplicate"] and len(h.gateway.posts) == before,
    )
    h.grant(integration, target, "revoked")
    # A campaign administrator without inbox.write cannot approve or retry sends.
    qualify_role(h, first)
    check(("current_role_without_inbox_write_cannot_activate_bulk_sends"))
    save(
        WORK / "extras-result.json",
        {
            "status": "passed",
            "checks": checks,
            "engine": 15,
            "compatibility": 150,
            "real_provider_calls": 0,
            "actual_Meta_catalog_approved": False,
            "academic_writes": False,
        },
    )
    print(json.dumps({"status": "passed", "P7_extra_checks": len(checks)}))


def qualify_role(h, key):
    import secrets

    from tools.qualify_p3_workspace import Browser

    role = "bulk_" + uuid4().hex[:8]
    password = "CBN!" + secrets.token_urlsafe(24)
    h.call(
        "roles/" + role,
        "PUT",
        dict(
            operation_id=str(uuid4()),
            revision=0,
            name="Campañas sin permiso de Inbox",
            active=True,
            actions=["campaigns.manage", "crm.read"],
        ),
    )
    email = role + "@cbn.local"
    h.call(
        "users",
        "POST",
        dict(
            operation_id=str(uuid4()),
            email=email,
            full_name="Campañas controladas sin envío",
            password=password,
            role=role,
        ),
    )
    limited = Browser(h.app)
    limited.login(email, password)
    current = limited.request("broadcasts/" + key).json()
    limited.request(
        "broadcasts/" + key + "/activate",
        "POST",
        h.cmd(current["revision"], confirmed=True),
        403,
    )


if __name__ == "__main__":
    import os

    if os.environ.get("P7_EXTRAS_RESUME") == "role":
        from tools.prepare_p7_broadcast import read

        checks = read(WORK / "extras-result.json")["checks"]
        assert len(checks) == 5
        h = Harness("extras")
        key = str(
            h.sql(
                (
                    "SELECT TOP(1) CampaignId FROM crm_broa"
                    "dcast7.Campaign ORDER BY CreatedAt"
                )
            )[0][0]
        ).lower()
        qualify_role(h, key)
        checks.append(("current_role_without_inbox_write_cannot_activate_bulk_sends"))
        save(
            WORK / "extras-result.json",
            dict(
                status="passed",
                checks=checks,
                engine=15,
                compatibility=150,
                real_provider_calls=0,
                actual_Meta_catalog_approved=False,
                academic_writes=False,
                resumed_from_recorded_checks=5,
            ),
        )
        print(json.dumps(dict(status="passed", P7_extra_checks=len(checks))))
    else:
        main()
