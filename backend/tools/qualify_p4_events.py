"""Signed delivery, pause and exact-account boundaries in the owned SQL fixture."""

import hmac
import json
import os
import time
from pathlib import Path
from uuid import uuid4

from app.institutional.api import create_app
from app.institutional.channel_events import EventWorker
from app.institutional.channel_operations import account
from app.institutional.channel_secrets import get
from app.institutional.db import one, uid
from app.institutional.spanish import load
from app.institutional.store import transaction
from tools.prepare_p4_channels import WORK, read, save
from tools.qualify_p3_workspace import Browser


def main():
    os.environ["CRM_AI_STATE_DIR"] = str(WORK / "media-fixture")
    settings = load(Path(read(WORK / "fixture-profile.json")["directory"]))
    access = read(WORK / "fixture-access.json")
    browser = Browser(create_app(settings))
    browser.login(access["email"], access["password"])
    checks = []

    def check(name, ok):
        assert ok, name
        checks.append(name)

    with transaction(settings, anonymous=True) as c:
        job = one(
            c,
            "SELECT TOP(1) q.* FROM crm_channels2.SendJob q JOIN "
            "crm_channels2.Integration i ON i.InstitutionId=q.InstitutionId "
            "AND i.IntegrationId=q.IntegrationId WHERE q.State='accepted' "
            "AND i.Channel='whatsapp' AND i.RequestedStatus='connected' "
            "ORDER BY q.CreatedAt DESC",
        )
        item = account(c, settings, str(job["IntegrationId"]))
        secret, _ = get(
            c, settings, "application", str(item["ApplicationId"]), "meta_app_secret"
        )
    identity = uid(str(item["IntegrationId"]))
    view = next(
        v for v in browser.request("channels").json()["items"] if v["id"] == identity
    )
    worker = EventWorker(settings)

    def emit(value, route=None):
        raw = json.dumps(
            {
                "object": "whatsapp_business_account",
                "entry": [
                    {
                        "id": "owned-waba",
                        "changes": [
                            {
                                "field": "messages",
                                "value": {
                                    "messaging_product": "whatsapp",
                                    "metadata": {
                                        "phone_number_id": route
                                        or item["ExternalAccountId"]
                                    },
                                    **value,
                                },
                            }
                        ],
                    }
                ],
            }
        ).encode()
        headers = {
            "X-Hub-Signature-256": "sha256="
            + hmac.digest(secret.encode(), raw, "sha256").hex()
        }
        response = browser.client.post(
            view["webhook"]["path"], content=raw, headers=headers
        )
        assert response.status_code == 200
        for _ in range(30):
            if not worker.once():
                break
        return raw, headers

    def drain():
        for _ in range(30):
            if not worker.project_once():
                break

    def state():
        with transaction(settings, anonymous=True) as c:
            return c.execute(
                "SELECT State FROM crm_channels2.SendJob WHERE QueueId=?",
                job["QueueId"],
            ).fetchval()

    emit({"statuses": [{"id": job["ExternalId"], "status": "delivered"}]})
    drain()
    check("signed_delivery_updates_exact_accepted_job", state() == "delivered")
    emit({"statuses": [{"id": job["ExternalId"], "status": "sent"}]})
    drain()
    check("older_status_does_not_regress_delivery", state() == "delivered")
    emit(
        {"statuses": [{"id": job["ExternalId"], "status": "read"}]},
        "owned-different-account",
    )
    drain()
    check("signed_other_account_cannot_change_delivery", state() == "delivered")
    runtime = browser.request("channels/runtime").json()
    browser.request(
        "channels/runtime",
        "PUT",
        {
            **runtime,
            "operation_id": str(uuid4()),
            "ingress_enabled": False,
            "outbound_enabled": False,
        },
    )
    external = "owned-paused-" + uuid4().hex
    payload = {
        "messages": [
            {
                "id": external,
                "from": "573000111222",
                "type": "text",
                "timestamp": str(int(time.time())),
                "text": {"body": "Entrada firmada conservada durante pausa"},
            }
        ]
    }
    raw, headers = emit(payload)
    check("paused_projection_stops_effects", worker.project_once() is False)
    with transaction(settings, anonymous=True) as c:
        queued = one(
            c,
            "SELECT * FROM crm_channels2.WebhookEvent WHERE IntegrationId=? "
            "AND ProviderEventId=?",
            identity,
            external,
        )
    check(
        "signed_event_durably_retained_while_paused",
        queued is not None and queued["Status"] == "queued",
    )
    duplicate = browser.client.post(
        view["webhook"]["path"], content=raw, headers=headers
    )
    check(
        "paused_duplicate_is_acknowledged_without_new_effect",
        duplicate.status_code == 200,
    )
    runtime = browser.request("channels/runtime").json()
    browser.request(
        "channels/runtime",
        "PUT",
        {
            **runtime,
            "operation_id": str(uuid4()),
            "ingress_enabled": True,
            "outbound_enabled": True,
        },
    )
    drain()
    with transaction(settings, anonymous=True) as c:
        projected = c.execute(
            "SELECT Status FROM crm_channels2.WebhookEvent WHERE EventId=?",
            queued["EventId"],
        ).fetchval()
        count = c.execute(
            "SELECT COUNT(*) FROM crm_channels2.WebhookEvent WHERE IntegrationId=? "
            "AND ProviderEventId=?",
            identity,
            external,
        ).fetchval()
    check("resumed_event_projected_once", projected == "processed" and count == 1)
    external = "owned-media-" + uuid4().hex
    emit(
        {
            "messages": [
                {
                    "id": external,
                    "from": "573000111222",
                    "type": "document",
                    "timestamp": str(int(time.time())),
                    "document": {
                        "id": "owned-provider-media",
                        "filename": "admisiones.txt",
                    },
                }
            ]
        }
    )
    drain()
    from app.institutional.channel_media import MediaWorker

    content = b"Adjunto recibido en una prueba controlada"

    def download(adapter, reference, path):
        assert reference["id"] == "owned-provider-media"
        path.write_bytes(content)

    media = MediaWorker(settings, downloader=download)
    for _ in range(20):
        if not media.once():
            break
    with transaction(settings, anonymous=True) as c:
        value = one(
            c,
            "SELECT a.* FROM crm_channels4.MediaAsset a JOIN "
            "crm_channels2.ExternalMessage e ON e.MessageId=a.MessageId "
            "AND e.IntegrationId=a.IntegrationId AND e.InstitutionId=a.InstitutionId "
            "WHERE e.ExternalId=? AND a.IntegrationId=?",
            external,
            identity,
        )
    check(
        "incoming_media_bound_to_exact_identity_message_account",
        value is not None and value["State"] == "ready",
    )
    response = browser.request("media/" + uid(str(value["MediaId"])))
    check(
        "incoming_media_inspected_and_authenticated_download",
        response.content == content,
    )
    check("incoming_media_worker_does_not_repeat_ready_download", media.once() is False)
    # Per-account pause retains both signed input and human output.
    conversation = uid(str(value["ConversationId"]))
    detail = browser.get("conversations/" + conversation)
    text = "Salida retenida por pausa de cuenta " + uuid4().hex
    queued_send = browser.request(
        "workspace/conversations/" + conversation + "/messages",
        "POST",
        {
            "operationId": str(uuid4()),
            "revision": detail["revision"],
            "body": text,
        },
    ).json()["queueId"]

    def routing(status):
        item_view = next(
            v
            for v in browser.request("channels").json()["items"]
            if v["id"] == identity
        )
        browser.request(
            "channels/" + identity + "/routing",
            "PUT",
            {
                "operation_id": str(uuid4()),
                "row_version": item_view["row_version"],
                "initial_stage_key": item_view["initial_stage_key"],
                "status": status,
            },
        )

    routing("paused")
    external = "owned-account-paused-" + uuid4().hex
    emit(
        {
            "messages": [
                {
                    "id": external,
                    "from": "573000111222",
                    "type": "text",
                    "timestamp": str(int(time.time())),
                    "text": {"body": "Entrada con cuenta pausada"},
                }
            ]
        }
    )
    from app.institutional.channel_outbox import Dispatcher

    sent = []

    def send(adapter, payload):
        sent.append(payload["body"])
        return "owned-resumed-" + uuid4().hex

    dispatcher = Dispatcher(settings, transport=send)
    for _ in range(20):
        if not dispatcher.once():
            break
    with transaction(settings, anonymous=True) as c:
        retained = one(
            c,
            "SELECT * FROM crm_channels2.WebhookEvent WHERE IntegrationId=? "
            "AND ProviderEventId=?",
            identity,
            external,
        )
        state = c.execute(
            "SELECT State FROM crm_channels2.SendJob WHERE QueueId=?", queued_send
        ).fetchval()
    check(
        "paused_account_retains_event_and_queue_without_provider_effect",
        retained["Status"] == "quarantined" and state == "queued" and text not in sent,
    )
    routing("connected")
    command = {
        "operation_id": str(uuid4()),
        "resource_id": uid(str(retained["EventId"])),
        "row_version": bytes(retained["RowVersion"]).hex(),
        "action": "reprocess_event",
    }
    result = browser.request(
        "channels/" + identity + "/recover", "POST", command
    ).json()
    assert (
        result
        == browser.request("channels/" + identity + "/recover", "POST", command).json()
    )
    drain()
    with transaction(settings, True, anonymous=True) as c:
        check(
            "signed_quarantine_recovered_idempotently_with_exact_route",
            c.execute(
                "SELECT Status FROM crm_channels2.WebhookEvent WHERE EventId=?",
                retained["EventId"],
            ).fetchval()
            == "processed",
        )
        c.execute(
            "UPDATE crm_channels2.SendJob SET DueAt=SYSUTCDATETIME() WHERE QueueId=?",
            queued_send,
        )
    for _ in range(20):
        if not dispatcher.once():
            break
    check("resumed_account_sends_preserved_job_once", sent.count(text) == 1)
    save(
        WORK / "events-result.json",
        {"status": "passed", "checks": checks, "real_provider_calls": 0},
    )
    print(json.dumps({"passed": len(checks), "real_provider_calls": 0}))


if __name__ == "__main__":
    main()
