"""Additional controlled provider, OAuth, event and outbox acceptance cases."""

import hmac
import json
import time
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

from fastapi import HTTPException

from app.institutional.auth import cookie_name
from app.institutional.channel_events import EventWorker
from app.institutional.channel_oauth import OAuth, Start
from app.institutional.channel_outbox import Dispatcher
from app.institutional.channel_provider import ProviderAction, ProviderOperations
from app.institutional.db import institution
from app.institutional.store import transaction
from app.modules.channels.providers import ProviderFailure


def qualify(settings, owner, identity, secret, check):
    authority = {
        "token": owner.client.cookies.get(cookie_name(settings)),
        "csrf": owner.csrf,
        "method": "POST",
        "module": "settings",
    }

    def current():
        return next(
            i for i in owner.request("channels").json()["items"] if i["id"] == identity
        )

    def post(path, body, method="POST", expected=200):
        return owner.request(
            path, method, dict(operation_id=str(uuid4()), **body), expected=expected
        ).json()

    post(
        "credentials",
        {
            "scope": "channel",
            "owner": "integration:" + identity,
            "kind": "access_token",
            "value": "owned-access-" + uuid4().hex,
        },
        method="PUT",
    )
    calls = []

    def provider(adapter, action, item, pin):
        calls.append(action)
        return {
            "asset": {"id": item["ExternalAccountId"]},
            "apiAssetValidated": True,
            "numbers": [{"id": item["ExternalAccountId"]}],
        }

    service = ProviderOperations(settings, transport=provider)
    body = ProviderAction(
        operation_id=str(uuid4()), row_version=current()["row_version"]
    )
    result = service.perform(authority, identity, "verify", body)
    repeat = service.perform(authority, identity, "verify", body)
    check(
        "provider_intent_exactly_once",
        result["status"] == "confirmed"
        and repeat["status"] == "confirmed"
        and calls == ["verify"],
    )
    body = ProviderAction(
        operation_id=str(uuid4()), row_version=current()["row_version"], pin="123456"
    )

    def unknown(*args):
        calls.append("register")
        raise ProviderFailure("provider_timeout", uncertain=True)

    uncertain = ProviderOperations(settings, transport=unknown)
    result = uncertain.perform(authority, identity, "register", body)
    uncertain.perform(authority, identity, "register", body)
    check(
        "ambiguous_registration_not_repeated",
        result["status"] == "uncertain" and calls.count("register") == 1,
    )
    cfg = owner.request("channels/runtime").json()
    post(
        "channels/runtime",
        {
            **cfg,
            "public_base_url": "https://crm-cbn.example.test",
            "outbound_enabled": True,
        },
        method="PUT",
    )
    oauth_calls = []

    def exchange(item, raw_secret, code, redirect, verifier):
        oauth_calls.append(code)
        return {
            "access": "owned-oauth-access-" + uuid4().hex,
            "assets": [
                {
                    "id": item["ExternalAccountId"],
                    "kind": "whatsapp_phone",
                    "name": "Owned phone",
                    "parent": item["ParentExternalId"],
                }
            ],
        }

    oauth = OAuth(settings, transport=exchange)
    start = oauth.start(
        authority,
        identity,
        Start(operation_id=str(uuid4()), scopes=["whatsapp_business_management"]),
    )
    state = parse_qs(urlsplit(start["authorization_url"]).query)["state"][0]
    result = oauth.callback(
        current()["application_id"], state, "owned-code", authority["token"]
    )
    check(
        "oauth_provisional_assets_not_connected",
        result["status"] == "assets_ready"
        and current()["requested_status"] == "paused",
    )
    try:
        oauth.callback(
            current()["application_id"], state, "owned-code", authority["token"]
        )
    except HTTPException as error:
        check(
            "oauth_state_single_use", error.status_code == 403 and len(oauth_calls) == 1
        )
    else:
        check("oauth_state_single_use", False)
    assets = oauth.assets(authority, start["oauth_session_id"])
    check(
        "oauth_assets_without_tokens",
        len(assets["items"]) == 1 and "owned-oauth-access" not in json.dumps(assets),
    )
    from app.institutional.channel_oauth import SelectAsset

    selected = oauth.assets(
        authority,
        start["oauth_session_id"],
        SelectAsset(operation_id=str(uuid4()), asset_id=assets["items"][0]["id"]),
    )
    check(
        "oauth_selection_requires_fresh_verification",
        selected["verification_required"]
        and current()["verified_status"] == "unverified",
    )
    service.perform(
        authority,
        identity,
        "verify",
        ProviderAction(operation_id=str(uuid4()), row_version=current()["row_version"]),
    )
    configuration = owner.request("/api/local/crm/configuration").json()
    stage = next(s["key"] for s in configuration["config"]["stages"] if s["active"])
    post(
        "channels/" + identity + "/routing",
        {
            "row_version": current()["row_version"],
            "initial_stage_key": stage,
            "status": "connected",
        },
        method="PUT",
    )
    item = current()
    field = next(
        v for k, v in item["fields"].items() if k == "meta:whatsapp_phone_number_id"
    )
    path = item["webhook"]["path"]
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
                                "metadata": {"phone_number_id": field},
                                "messages": [
                                    {
                                        "id": "owned-message-" + uuid4().hex,
                                        "from": "573000" + uuid4().hex[:6],
                                        "type": "text",
                                        "text": {
                                            "body": "Consulta educativa controlada"
                                        },
                                        "timestamp": str(int(time.time())),
                                    }
                                ],
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
    check(
        "routed_signed_message_receipt",
        owner.client.post(path, content=raw, headers=headers).status_code == 200,
    )
    worker = EventWorker(settings)
    for _ in range(12):
        if not worker.once():
            break
    for _ in range(12):
        if not worker.project_once():
            break
    with transaction(settings, anonymous=True) as c:
        row = c.execute(
            (
                "SELECT i.ConversationId FROM crm_channels2.Ext"
                "ernalIdentity i WHERE i.InstitutionId=? AND i."
                "IntegrationId=?"
            ),
            institution(settings),
            identity,
        ).fetchone()
    check("incoming_C10_identity_in_CRM", row is not None)
    conversation = str(row[0]).lower()
    detail = owner.get("conversations/" + conversation)
    check("inbox_account_bound_detail", detail["channelAccounts"][0]["id"] == identity)
    reply_text = "Respuesta controlada " + uuid4().hex
    msg = owner.request(
        "workspace/conversations/" + conversation + "/messages",
        "POST",
        {
            "operationId": str(uuid4()),
            "revision": detail["revision"],
            "body": reply_text,
        },
    ).json()
    check("human_send_enters_single_outbox", bool(msg.get("queueId")))
    # Use the normal revision/history contract, even in the synthetic fixture.
    budget = owner.request("settings/budgets").json()
    document = dict(budget["document"], daily_messages=1000)
    post(
        "settings/budgets",
        {"revision": budget["revision"], "document": document},
        method="PUT",
    )
    sends = []

    def send(adapter, payload):
        sends.append((adapter["channel"], payload["body"]))
        return "owned-provider-message-" + uuid4().hex

    dispatcher = Dispatcher(settings, transport=send)
    for _ in range(20):
        if not dispatcher.once():
            break
    messages = owner.get("conversations/" + conversation + "/messages")["items"]
    sent = next(m for m in messages if m.get("queueId") == msg["queueId"])
    check(
        "provider_acceptance_is_not_delivery",
        sent["deliveryState"] == "accepted"
        and sum(text == reply_text for _, text in sends) == 1,
    )
