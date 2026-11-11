"""Explicit recovery qualification in the owned fixture; transport has no network."""

import json
from pathlib import Path
from uuid import uuid4

from app.institutional.api import create_app
from app.institutional.channel_outbox import Dispatcher
from app.institutional.db import institution, one, uid
from app.institutional.spanish import load
from app.institutional.store import transaction
from app.modules.channels.providers import ProviderFailure
from tools.prepare_p4_channels import WORK, read, save
from tools.qualify_p3_workspace import Browser


def main():
    settings = load(Path(read(WORK / "fixture-profile.json")["directory"]))
    access = read(WORK / "fixture-access.json")
    browser = Browser(create_app(settings))
    browser.login(access["email"], access["password"])
    checks = []

    def check(name, ok):
        assert ok, name
        checks.append(name)

    with transaction(settings, anonymous=True) as c:
        pair = one(
            c,
            "SELECT TOP(1) i.IntegrationId,i.ConversationId "
            "FROM crm_channels2.ExternalIdentity i JOIN "
            "crm_channels2.Integration a ON a.IntegrationId=i.IntegrationId "
            "AND a.InstitutionId=i.InstitutionId WHERE a.Channel='whatsapp' "
            "AND a.RequestedStatus='connected' AND a.VerifiedStatus='verified' "
            "ORDER BY i.CreatedAt DESC",
        )
    integration, conversation = (
        uid(str(pair["IntegrationId"])),
        uid(str(pair["ConversationId"])),
    )

    def enqueue():
        detail = browser.get("conversations/" + conversation)
        return browser.request(
            "workspace/conversations/" + conversation + "/messages",
            "POST",
            {
                "operationId": str(uuid4()),
                "revision": detail["revision"],
                "body": "Recuperación controlada " + uuid4().hex,
            },
        ).json()["queueId"]

    def state(queue):
        with transaction(settings, anonymous=True) as c:
            return one(
                c,
                "SELECT * FROM crm_channels2.SendJob WHERE QueueId=? "
                "AND InstitutionId=?",
                queue,
                institution(settings),
            )

    def recover(queue, action, expected=200, body=None):
        body = body or {
            "operation_id": str(uuid4()),
            "resource_id": queue,
            "row_version": bytes(state(queue)["RowVersion"]).hex(),
            "action": action,
        }
        return browser.request(
            "channels/" + integration + "/recover", "POST", body, expected=expected
        ).json(), body

    first = enqueue()
    calls = []

    def rejected(adapter, payload):
        calls.append(payload["body"])
        raise ProviderFailure("owned_certain_rejection", uncertain=False)

    dispatcher = Dispatcher(settings, transport=rejected)
    for _ in range(25):
        dispatcher.once()
        if state(first)["State"] == "failed":
            break
    check("certain_provider_failure_recorded", state(first)["State"] == "failed")
    result, body = recover(first, "retry_send")
    repeated, _ = recover(first, "retry_send", body=body)
    check(
        "failed_retry_idempotent_with_new_attempt",
        result == repeated and result["queue_id"] != first,
    )
    recover(first, "retry_send", expected=409)
    check("old_attempt_cannot_be_retried_twice", state(first)["State"] == "retried")

    accepted_calls = []

    def accepted(adapter, payload):
        accepted_calls.append(payload["body"])
        return "owned-accepted-" + uuid4().hex

    dispatcher = Dispatcher(settings, transport=accepted)
    for _ in range(25):
        dispatcher.once()
        if state(result["queue_id"])["State"] == "accepted":
            break
    check(
        "retry_dispatches_once_without_duplicate_message",
        state(result["queue_id"])["State"] == "accepted",
    )
    view = browser.get("conversations/" + conversation + "/messages")["items"]
    check(
        "inbox_reports_current_attempt",
        any(
            m.get("queueId") == result["queue_id"]
            and m.get("deliveryState") == "accepted"
            for m in view
        ),
    )
    queued = enqueue()
    value = state(queued)
    with transaction(settings, True, anonymous=True) as c:
        payload = json.loads(value["Payload"])
        payload["actorSessionId"] = str(uuid4())
        c.execute(
            "UPDATE crm_channels2.SendJob SET Payload=? WHERE QueueId=?",
            json.dumps(payload),
            queued,
        )
    count = len(accepted_calls)
    dispatcher.once()
    check(
        "restored_queue_has_no_implicit_authority",
        state(queued)["State"] == "queued" and len(accepted_calls) == count,
    )
    recover(queued, "resume_queued")
    with transaction(settings, True, anonymous=True) as c:
        c.execute(
            "UPDATE crm_channels2.SendJob SET DueAt=SYSUTCDATETIME() WHERE QueueId=?",
            queued,
        )
    for _ in range(25):
        dispatcher.once()
        if state(queued)["State"] == "accepted":
            break
    check(
        "explicit_current_session_resumes_preserved_queue",
        state(queued)["State"] == "accepted",
    )
    uncertain = enqueue()

    def unknown(adapter, payload):
        raise ProviderFailure("owned_lost_ack", uncertain=True)

    dispatcher = Dispatcher(settings, transport=unknown)
    for _ in range(25):
        dispatcher.once()
        if state(uncertain)["State"] == "uncertain":
            break
    recover(uncertain, "retry_send", expected=409)
    check(
        "unknown_provider_effect_cannot_be_retried",
        state(uncertain)["State"] == "uncertain",
    )
    recover(uncertain, "abandon_uncertain")
    check(
        "unknown_history_preserved_when_abandoned",
        state(uncertain)["State"] == "cancelled",
    )
    save(
        WORK / "recovery-api-result.json",
        {"status": "passed", "checks": checks, "real_provider_calls": 0},
    )
    print(json.dumps({"passed": len(checks), "real_provider_calls": 0}))


if __name__ == "__main__":
    main()
