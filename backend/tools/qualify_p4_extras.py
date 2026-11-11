"""Comments, media and recovery tests on the explicit owned P4 fixture only."""

import base64
import hmac
import json
import os
from pathlib import Path
from uuid import uuid4

from app.institutional.api import create_app
from app.institutional.auth import cookie_name
from app.institutional.channel_events import EventWorker
from app.institutional.channel_provider import ProviderAction, ProviderOperations
from app.institutional.comment_effects import Effect, Effects
from app.institutional.db import institution
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

    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append(name)
        save(WORK / "extras-result.json", {"status": "in_progress", "checks": checks})

    def post(path, body, method="POST", expected=200):
        return browser.request(
            path, method, dict(operation_id=str(uuid4()), **body), expected=expected
        ).json()

    authority = {
        "token": browser.client.cookies.get(cookie_name(settings)),
        "csrf": browser.csrf,
        "method": "POST",
        "module": "inbox",
    }
    suffix = uuid4().hex
    created = post(
        "channels",
        {
            "channel": "facebook",
            "display_name": "Facebook controlado " + suffix[:6],
            "issuer_profile": "facebook_login",
            "client_id": "owned-facebook-" + suffix,
            "api_version": "v24.0",
        },
    )
    identity = created["id"]

    def current():
        return next(
            v
            for v in browser.request("channels").json()["items"]
            if v["id"] == identity
        )

    secret = "owned-facebook-secret-" + suffix
    post(
        "credentials",
        {
            "scope": "channel",
            "owner": "application:" + created["application_id"],
            "kind": "app_secret",
            "value": secret,
        },
        method="PUT",
    )
    post(
        "credentials",
        {
            "scope": "channel",
            "owner": "integration:" + identity,
            "kind": "page_access_token",
            "value": "owned-page-token-" + suffix,
        },
        method="PUT",
    )
    item = current()
    page = "page_" + suffix[:12]
    post(
        "channels/" + identity,
        {
            "revision": item["revision"],
            "row_version": item["row_version"],
            "application_version": item["application_version"],
            "values": {"meta:facebook_page_id": page},
        },
        method="PUT",
    )
    provider = ProviderOperations(
        settings,
        transport=lambda adapter, action, item, pin: {
            "asset": {"id": item["ExternalAccountId"]},
            "apiAssetValidated": True,
        },
    )
    provider.perform(
        authority,
        identity,
        "verify",
        ProviderAction(operation_id=str(uuid4()), row_version=current()["row_version"]),
    )
    stages = browser.request("channels/routing-options").json()["stages"]
    post(
        "channels/" + identity + "/routing",
        {
            "row_version": current()["row_version"],
            "initial_stage_key": stages[0]["key"],
            "status": "connected",
        },
        method="PUT",
    )
    item = current()
    hook = post(
        "channels/" + identity + "/webhook",
        {"row_version": item["webhook"]["row_version"], "active": True},
    )["webhook"]
    author = "author_" + suffix[:12]

    def deliver(comments, *, verb="add"):
        raw = json.dumps(
            {
                "object": "page",
                "entry": [
                    {
                        "id": page,
                        "changes": [
                            {
                                "field": "feed",
                                "value": {
                                    "item": "comment",
                                    "verb": verb,
                                    "comment_id": value,
                                    "from": {"id": author},
                                    "message": "Consulta sobre admisiones",
                                    "post_id": "post_" + suffix,
                                    "_crm": {
                                        "state": "connected",
                                        "contact_id": str(uuid4()),
                                    },
                                },
                            }
                            for value in comments
                        ],
                    }
                ],
            }
        ).encode()
        return browser.client.post(
            hook["path"],
            content=raw,
            headers={
                "X-Hub-Signature-256": "sha256="
                + hmac.digest(secret.encode(), raw, "sha256").hex()
            },
        )

    ids = ["comment_" + suffix + "_" + str(i) for i in range(2)]
    check("signed_comments_ack", deliver(ids).status_code == 200)
    worker = EventWorker(settings)
    for _ in range(20):
        if not worker.once():
            break
    for _ in range(20):
        if not worker.project_once():
            break

    def comments():
        return browser.request("comments?integration=" + identity).json()["items"]

    values = comments()
    check(
        "comments_page_filters_exact_account",
        len(values) == 2 and all(v["integration_id"] == identity for v in values),
    )
    check(
        "provider_cannot_inject_CRM_state",
        all(v["state"] == "new" and not v["contact_id"] for v in values),
    )
    first = values[0]
    request = {
        "operation_id": str(uuid4()),
        "row_version": first["row_version"],
        "action": "convert",
        "display_name": "Contacto controlado",
    }
    converted = browser.request("comments/" + first["id"], "POST", request).json()
    repeat = browser.request("comments/" + first["id"], "POST", request).json()
    check("comment_conversion_replay_no_duplicate", converted == repeat)
    other = next(v for v in comments() if v["id"] != first["id"])
    second = post(
        "comments/" + other["id"],
        {
            "row_version": other["row_version"],
            "action": "convert",
            "display_name": "El mismo autor",
        },
    )
    check(
        "author_account_conversion_reuses_contact",
        second["contact_id"] == converted["contact_id"],
    )
    with transaction(settings, anonymous=True) as c:
        count = c.execute(
            (
                "SELECT COUNT(*) FROM crm_channels2.ExternalIde"
                "ntity WHERE InstitutionId=? AND IntegrationId="
                "?"
            ),
            institution(settings),
            identity,
        ).fetchval()
    check("comment_author_not_promoted_to_DM_identity", count == 0)
    first = next(v for v in comments() if v["id"] == first["id"])
    calls = []
    effects = Effects(
        settings,
        transport=lambda adapter, action, comment: calls.append(action)
        or {"liked": True},
    )
    body = Effect(operation_id=str(uuid4()), row_version=first["row_version"])
    reacted = effects.perform(authority, first["id"], "like", body)
    effects.perform(authority, first["id"], "like", body)
    check(
        "comment_like_effect_not_duplicated",
        reacted["status"] == "confirmed" and calls == ["like"],
    )
    first = next(v for v in comments() if v["id"] == first["id"])
    queued = post(
        "comments/" + first["id"],
        {
            "row_version": first["row_version"],
            "action": "reply",
            "body": "Respuesta pública controlada",
        },
    )
    check("comment_reply_uses_C10_outbox", bool(queued["queue_id"]))
    first = next(v for v in comments() if v["id"] == first["id"])
    post(
        "comments/" + first["id"],
        {"row_version": first["row_version"], "action": "reply", "body": "No duplicar"},
        expected=409,
    )
    check("pending_comment_reply_denied", True)
    external_comment = first["external_id"]
    check(
        "deleted_comment_event_ack",
        deliver([external_comment], verb="remove").status_code == 200,
    )
    while worker.once():
        pass
    while worker.project_once():
        pass
    with transaction(settings, anonymous=True) as c:
        state = c.execute(
            (
                "SELECT State FROM crm_channels2.SendJob WHERE "
                "InstitutionId=? AND QueueId=?"
            ),
            institution(settings),
            queued["queue_id"],
        ).fetchval()
    check("deleted_comment_cancels_queued_reply", state == "cancelled")
    first = next(v for v in comments() if v["id"] == first["id"])
    post(
        "comments/" + first["id"],
        {"row_version": first["row_version"], "action": "read"},
        expected=409,
    )
    check("deleted_comment_actions_blocked", True)
    conversation = converted["conversation_id"]
    upload = {
        "operation_id": str(uuid4()),
        "conversation_id": conversation,
        "filename": "consulta.txt",
        "content_base64": base64.b64encode(
            b"Documento controlado para admisiones"
        ).decode(),
    }
    file = browser.request("media/upload", "POST", upload).json()
    replayed = browser.request("media/upload", "POST", upload).json()
    check(
        "media_upload_replay_preserves_one_asset",
        file["id"] == replayed["id"] and file["state"] == "ready",
    )
    binary = browser.request("media/" + file["id"])
    check(
        "media_authenticated_download",
        binary.content == b"Documento controlado para admisiones"
        and "attachment" in binary.headers["content-disposition"],
    )
    detail = browser.get("conversations/" + conversation)
    browser.request(
        "workspace/conversations/" + conversation + "/messages",
        "POST",
        {
            "operationId": str(uuid4()),
            "revision": detail["revision"],
            "body": "Documento adjunto",
            "mediaId": file["id"],
        },
    )
    messages = browser.get("conversations/" + conversation + "/messages")
    check(
        "local_attachment_bound_to_message",
        any(
            any(a["id"] == file["id"] for a in m.get("attachments", []))
            for m in messages["items"]
        ),
    )
    post(
        "media/upload",
        {
            "conversation_id": conversation,
            "filename": "fake.png",
            "content_base64": base64.b64encode(
                b"<html><script>alert(1)</script></html>"
            ).decode(),
        },
        expected=415,
    )
    check("disguised_active_content_rejected", True)
    # Anonymous binary reads require the same human boundary as text.
    from fastapi.testclient import TestClient

    anonymous = TestClient(
        create_app(settings),
        base_url="http://127.0.0.1:4178",
        client=("127.0.0.1", 50330),
    )
    check(
        "media_anonymous_read_denied",
        anonymous.get(
            "/api/institution/media/" + file["id"], headers={"X-CRM-Local": "1"}
        ).status_code
        == 401,
    )
    from tools.qualify_p4_ai import qualify

    alive = next(v for v in comments() if v["state"] != "deleted")
    qualify(settings, browser, authority, identity, alive, check)
    save(
        WORK / "extras-result.json",
        {
            "status": "passed",
            "checks": checks,
            "real_provider_calls": 0,
            "academic_writes": False,
        },
    )
    print(json.dumps({"passed": len(checks), "real_provider_calls": 0}))


if __name__ == "__main__":
    main()
