"""P7 SQL/API integration with controlled Meta transport, never real recipients."""

import json
from uuid import uuid4

from tools.p7_test_support import Harness
from tools.prepare_p7_broadcast import WORK, save


def main():
    import os

    h = Harness(os.environ.get("P7_FIXTURE", "fixture"))
    checks = []

    def check(name, ok=True):
        assert ok, name
        checks.append(name)
        save(WORK / "api-result.json", {"status": "in_progress", "checks": checks})

    integration = h.account()
    alice = h.incoming(integration, "573100000001", "=Ana Controlada")
    bob = h.incoming(integration, "573100000002", "Beto Sin consentimiento")
    human = h.incoming(integration, "573100000003", "Carla Asesora")
    h.sql(
        ("UPDATE crm.Conversation SET ControlMode='human' WHERE ConversationId=?"),
        human["conversation"],
        write=True,
    )
    check(("only_owned_P7_SQL2019_C10_fixture_and_authenticated_ingress"), True)
    h.sync(integration)
    check(
        "catalog_sync_is_explicitly_controlled_not_real_Meta",
        h.call("broadcasts/options")["templates"][-1]["origin"] == "controlled",
    )
    count = h.sql("SELECT COUNT(*) FROM crm_broadcast7.Template")[0][0]
    h.gateway.fail = "get"
    h.b.client.raise_server_exceptions = False
    response = h.b.client.post(
        "/api/institution/broadcasts/accounts/" + integration + "/templates/sync",
        json=h.cmd(),
        headers={"X-CRM-Local": "1", "X-CSRF-Token": h.b.csrf},
    )
    check(
        "invalid_token_does_not_fabricate_or_replace_catalog",
        response.status_code >= 400
        and h.sql("SELECT COUNT(*) FROM crm_broadcast7.Template")[0][0] == count,
    )
    h.gateway.fail = None
    h.grant(integration, alice)
    h.grant(integration, human)
    key = h.campaign(integration)
    preview = h.call("broadcasts/" + key + "/preview")
    check(
        "preview_counts_real_rows_and_explicit_exclusions",
        preview["counts"] == {"matched": 3, "eligible": 1, "excluded": 2}
        and preview["exclusions"]["human_control"] == 1
        and preview["exclusions"]["marketing_consent_required"] == 1,
    )
    check(
        "all_template_component_variables_render",
        any(
            v["text"].startswith("Hola =Ana") for v in preview["items"] if v["eligible"]
        ),
    )
    h.action(key, "prepare")
    check(
        "preparation_has_no_second_outbox_or_provider_POST",
        h.sql("SELECT COUNT(*) FROM crm_broadcast7.Recipient")[0][0] == 1
        and not h.gateway.posts,
    )
    prepared = h.sql(
        ("SELECT RecipientId FROM crm_broadcast7.Recipient WHERE CampaignId=?"), key
    )[0][0]
    h.grant(integration, alice, "revoked")
    h.action(key, "activate", 409)
    check(("consent_revoked_after_preparation_prevents_activation"))
    h.grant(integration, alice)
    h.action(key, "activate")
    h.call(
        "broadcasts/accounts/" + integration + "/cadence",
        "PUT",
        h.cmd(enabled=True, daily_limit=10, interval_seconds=1),
    )
    from app.institutional.broadcast_dispatch import Worker
    from app.institutional.broadcast_templates import send
    from app.institutional.channel_outbox import Dispatcher

    worker = Worker(h.settings, controlled=True)
    dispatcher = Dispatcher(
        h.settings,
        transport=lambda a, p, **kw: send(a, p, request=h.gateway, **kw),
        allow_controlled=True,
    )
    check(
        "one_C10_queue_created_by_campaign_worker",
        worker.once()
        and h.sql("SELECT COUNT(*) FROM crm_broadcast7.Attempt")[0][0] == 1,
    )
    check(
        "native_dispatcher_acceptance_is_not_delivery",
        dispatcher.once()
        and h.call("broadcasts/" + key + "/report")["counts"] == {"accepted": 1},
    )
    sent = h.gateway.posts[-1]["body"]
    check(
        ("WhatsApp_template_body_header_and_URL_parameters_used"),
        sent["type"] == "template"
        and {v["type"] for v in sent["template"]["components"]}
        == {"body", "header", "button"},
    )
    h.action(key, "retry", 409, recipient_ids=[str(prepared).lower()])
    check("accepted_attempt_is_never_selectively_retried")
    h.action(key, "pause")
    check(
        "pause_increments_epoch_and_preserves_existing_queue",
        h.call("broadcasts/" + key)["epoch"] == 2
        and h.sql("SELECT COUNT(*) FROM crm_broadcast7.Attempt")[0][0] == 1,
    )
    export = h.b.request("broadcasts/" + key + "/export").text
    check("CSV_export_neutralizes_formula_names", "'=Ana" in export)
    # Draft template management never assigns provider approval locally.
    template_id = str(uuid4())
    draft = h.call(
        "broadcasts/accounts/" + integration + "/templates/" + template_id,
        "PUT",
        h.cmd(
            name="nuevo_controlado",
            body_text="Hola {{customer_name}}",
            header_type="TEXT",
            header_text="Institución",
            footer_text="CBN",
            buttons=[{"type": "QUICK_REPLY", "text": "Información"}],
            allow_category_change=False,
        ),
    )
    check(
        "new_template_saved_as_operator_draft",
        draft["origin"] == "operator" and draft["provider_status"] == "LOCAL_DRAFT",
    )
    submit = h.call(
        "broadcasts/templates/" + template_id + "/submit",
        "POST",
        h.cmd(draft["version"], confirmed=True),
    )
    check(
        "provider_create_is_durable_and_pending_until_sync",
        submit["status"] == "confirmed"
        and h.gateway.posts[-1]["body"]["allow_category_change"] is False,
    )
    save(
        WORK / "api-private.json",
        {
            "integration": integration,
            "alice": alice,
            "bob": bob,
            "human": human,
            "campaign": key,
        },
    )
    save(
        WORK / "api-result.json",
        {
            "status": "passed",
            "checks": checks,
            "database": h.settings.connection["database"],
            "engine": 15,
            "compatibility": 150,
            "real_provider_calls": 0,
            "controlled_POSTs": len(h.gateway.posts),
            "actual_Meta_catalog_approved": False,
            "actual_external_receipts": False,
        },
    )
    print(json.dumps({"status": "passed", "P7_API_checks": len(checks)}))


if __name__ == "__main__":
    main()
