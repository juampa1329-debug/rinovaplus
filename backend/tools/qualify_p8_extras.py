"""Controlled P8 permissions, future transitions, delayed STOP and capacity fences."""

import hmac, json, secrets, time
from uuid import uuid4
from app.institutional.campaign_runtime import Worker
from app.institutional.channel_outbox import Dispatcher
from app.institutional.channel_events import EventWorker
from app.institutional.channel_operations import account, app_secret_kind
from app.institutional.channel_secrets import get
from app.institutional.store import transaction
from tools.p8_test_support import Harness
from tools.qualify_p3_workspace import Browser
from tools.prepare_p8_campaign import WORK, save


def main():
    h = Harness("qa-r2")
    checks = []

    def check(n, ok=True):
        assert ok, n
        checks.append(n)
        save(WORK / "extras-result.json", dict(status="in_progress", checks=checks))

    row = h.sql(
        "SELECT IdentityId,ContactId,ConversationId,IntegrationId FROM crm_channels2.ExternalIdentity WHERE ExternalId='573100000081'"
    )[0]
    p = dict(
        id=str(row[0]).lower(),
        contact=str(row[1]).lower(),
        conversation=str(row[2]).lower(),
        phone="573100000081",
    )
    a = str(row[3]).lower()
    h.grant(a, p)
    template = h.template8()
    worker = Worker(h.settings, h.gateway)
    # Actual stage/program observations enqueue only a future matching trigger.
    for field, event, value in [
        ("Stage", "stage_changed", "p8_observed_stage"),
        ("ProgramId", "program_changed", 9797),
    ]:
        f = h.flow8(a, template, steps=[dict(kind="wait", wait_minutes=60)])
        t = h.save8(
            "trigger",
            dict(
                flow_id=f["id"],
                flow_version=f["version"],
                event_type=event,
                cooldown_minutes=0,
            ),
        )
        h.act8(t["id"], "activate")
        worker.once()
        old = h.sql(
            "SELECT " + field + " FROM crm.Contact WHERE ContactId=?", p["contact"]
        )[0][0]
        h.sql(
            "UPDATE crm.Contact SET " + field + "=? WHERE ContactId=?",
            value,
            p["contact"],
            write=True,
        )
        worker.once()
        check(
            "observed_" + event + "_creates_one_versioned_execution",
            h.sql(
                "SELECT COUNT(*) FROM crm_campaign8.Enrollment WHERE FlowId=?", f["id"]
            )[0][0]
            == 1,
        )
        h.act8(t["id"], "pause")
        h.act8(f["id"], "pause")
        h.sql(
            "UPDATE crm.Contact SET " + field + "=? WHERE ContactId=?",
            old,
            p["contact"],
            write=True,
        )
        worker.once()
    # User permissions cannot be carried by a stale scheduled approval.
    role = "flows_" + uuid4().hex[:8]
    password = "CBN!" + secrets.token_urlsafe(24)
    email = role + "@cbn.local"
    h.call(
        "roles/" + role,
        "PUT",
        dict(
            operation_id=str(uuid4()),
            revision=0,
            name="Control de flujos",
            active=True,
            actions=["campaigns.manage", "crm.read"],
        ),
    )
    h.call(
        "users",
        "POST",
        dict(
            operation_id=str(uuid4()),
            email=email,
            full_name="Control de flujos",
            password=password,
            role=role,
        ),
    )
    user = Browser(h.app)
    user.login(email, password)
    f = h.flow8(a, template)
    cur = user.request("campaigns/" + f["id"]).json()
    user.request(
        "campaigns/" + f["id"] + "/activate",
        "POST",
        h.cmd(cur["revision"], confirmed=True),
        403,
    )
    check("current_role_without_inbox_write_cannot_approve_flow")
    # CSRF is checked before any modification of a valid owned record.
    response = h.b.client.post(
        "/api/institution/campaigns/" + f["id"] + "/pause",
        headers={"X-CRM-Local": "1"},
        json=h.cmd(f["revision"], confirmed=True),
    )
    check("CSRF_required_for_campaign_mutations", response.status_code == 403)
    # STOP is classified from this authenticated event even when timestamp is older.
    h.incoming(a, p["phone"], "Ana Controlada", "Mensaje posterior en el reloj")
    item = next(v for v in h.call("channels")["items"] if v["id"] == a)
    with transaction(h.settings, anonymous=True) as c:
        owned = account(c, h.settings, a)
        secret, _ = get(
            c, h.settings, "application", item["application_id"], app_secret_kind(owned)
        )
    message = dict(
        id="delayed_stop_" + uuid4().hex,
        **{"from": p["phone"]},
        type="text",
        text={"body": "STOP"},
        timestamp=str(int(time.time()) - 3600),
    )
    raw = json.dumps(
        dict(
            object="whatsapp_business_account",
            entry=[
                dict(
                    id=owned["ParentExternalId"],
                    changes=[
                        dict(
                            field="messages",
                            value=dict(
                                messaging_product="whatsapp",
                                metadata={
                                    "phone_number_id": owned["ExternalAccountId"]
                                },
                                messages=[message],
                            ),
                        )
                    ],
                )
            ],
        )
    ).encode()
    response = h.b.client.post(
        item["webhook"]["path"],
        content=raw,
        headers={
            "X-Hub-Signature-256": "sha256="
            + hmac.digest(secret.encode(), raw, "sha256").hex()
        },
    )
    assert response.status_code == 200
    events = EventWorker(h.settings)
    events.once()
    events.project_once()
    check(
        "delayed_authenticated_STOP_overrides_later_message_and_old_consent",
        h.call("campaigns/" + f["id"] + "/preview")["counts"]["eligible"] == 0
        and h.sql(
            "SELECT COUNT(*) FROM crm_campaign8.Event WHERE Kind='opt_out' AND JSON_VALUE(Document,'$.identity_id')=?",
            p["id"],
        )[0][0]
        >= 2,
    )
    h.grant(a, p)
    # Change a referenced template after queueing: final boundary must refuse it.
    f = h.flow8(a, template)
    r = h.enroll8(f, p)
    worker.once()
    before = []
    template_now = h.call("campaigns/" + template["id"])
    h.save8(
        "template",
        dict(channel="whatsapp", body="Nueva versión", variables={}),
        id=template["id"],
        revision=template_now["revision"],
    )
    h.release8(a)
    Dispatcher(
        h.settings, transport=lambda *a, **kw: before.append(1), allow_controlled=True
    ).once()
    worker.once()
    check(
        "referenced_template_edit_cancels_run_without_provider_effect",
        not before and h.run8(r)["state"] == "cancelled",
    )
    save(
        WORK / "extras-result.json",
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
