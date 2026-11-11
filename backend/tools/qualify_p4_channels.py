"""Owned SQL/API fixture qualification; no real provider calls or source writes."""

import hmac
import json
from pathlib import Path
from uuid import uuid4

from app.institutional.api import create_app
from app.institutional.spanish import load
from tools.prepare_p4_channels import WORK, admin, read, save
from tools.qualify_p3_workspace import Browser


def main():
    profile = read(WORK / "fixture-profile.json")
    settings = load(Path(profile["directory"]))
    owner = Browser(create_app(settings))
    access = read(WORK / "fixture-access.json")
    owner.login(access["email"], access["password"])
    checks = []

    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append(name)
        save(WORK / "api-result.json", {"status": "in_progress", "checks": checks})

    def post(path, body, method="POST", expected=200):
        return owner.request(
            path, method, dict(operation_id=str(uuid4()), **body), expected=expected
        ).json()

    runtime = owner.request("channels/runtime").json()
    if runtime["public_base_url"] or runtime["outbound_enabled"]:
        post(
            "channels/runtime",
            {**runtime, "public_base_url": "", "outbound_enabled": False},
            method="PUT",
        )

    body = dict(
        operation_id=str(uuid4()),
        channel="whatsapp",
        display_name="Prueba controlada P4",
        issuer_profile="meta_whatsapp",
        client_id="owned-fixture-" + uuid4().hex,
        api_version="v24.0",
    )
    created = owner.request("channels", "POST", body).json()
    identity = created["id"]
    check(
        "generated_endpoint_and_one_time_verify",
        bool(created["webhook"]["path"]) and len(created["verify_token"]) >= 32,
    )
    repeat = owner.request("channels", "POST", body).json()
    check(
        "create_replay_without_secret",
        repeat["id"] == identity and "verify_token" not in repeat,
    )
    listed = owner.request("channels").json()
    item = next(i for i in listed["items"] if i["id"] == identity)
    check(
        "read_has_no_plaintext_verify",
        created["verify_token"] not in json.dumps(listed),
    )
    check(
        "no_domain_no_fabricated_callback",
        item["webhook"]["callback_url"] == ""
        and item["webhook"]["public_origin_required"],
    )
    secret = "owned-provider-fixture-" + uuid4().hex
    post(
        "credentials",
        {
            "scope": "channel",
            "owner": "application:" + item["application_id"],
            "kind": "app_secret",
            "value": secret,
        },
        method="PUT",
    )
    meta = owner.request("credentials/channel").json()
    check("credential_metadata_only", secret not in json.dumps(meta))
    # Configure the account's real routing field using its catalog mapping.
    from app.institutional.channels import contract

    field = next(
        f
        for f in contract()["fields"]
        if f["group"].startswith("whatsapp")
        and (f.get("p2_mapping") or {}).get("column") == "ExternalAccountId"
    )
    item = next(
        i for i in owner.request("channels").json()["items"] if i["id"] == identity
    )
    post(
        "channels/" + identity,
        {
            "revision": item["revision"],
            "row_version": item["row_version"],
            "application_version": item["application_version"],
            "values": {field["id"]: "1555" + uuid4().hex[:8]},
        },
        method="PUT",
    )
    item = next(
        i for i in owner.request("channels").json()["items"] if i["id"] == identity
    )
    active = post(
        "channels/" + identity + "/webhook",
        {"row_version": item["webhook"]["row_version"], "active": True},
    )
    path = active["webhook"]["path"]
    client = owner.client
    challenge = client.get(
        path,
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": created["verify_token"],
            "hub.challenge": "owned-test-challenge",
        },
    )
    check(
        "strict_meta_challenge",
        challenge.status_code == 200 and challenge.text == "owned-test-challenge",
    )
    denied = client.get(
        path,
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong",
            "hub.challenge": "must-not-return",
        },
    )
    check("invalid_verify_rejected", denied.status_code == 403)
    raw = b'{"object":"whatsapp_business_account","entry":[]}'
    headers = {
        "X-Hub-Signature-256": "sha256="
        + hmac.digest(secret.encode(), raw, "sha256").hex()
    }
    received = client.post(path, content=raw, headers=headers)
    check(
        "signed_receipt_ack_after_persist",
        received.status_code == 200 and received.json()["received"],
    )
    duplicate = client.post(path, content=raw, headers=headers)
    check(
        "receipt_deduplicated",
        duplicate.status_code == 200 and duplicate.json()["duplicate"],
    )
    check(
        "signature_tamper_denied",
        client.post(path, content=raw + b" ", headers=headers).status_code == 403,
    )
    check(
        "oversized_raw_denied",
        client.post(path, content=b"x" * 1000001, headers=headers).status_code == 413,
    )
    with admin(profile["database"], readonly=True) as connection:
        c = connection.cursor()
        c.execute(
            (
                "SELECT BodyCiphertext,BodyNonce,Authentication"
                " FROM dbo.CRMCanalInstitucionalWebhookRecepcio"
                "n WHERE EndpointId=?"
            ),
            item["webhook"]["id"],
        )
        receipt = c.fetchone()
        check(
            "raw_encrypted_and_verified",
            raw not in bytes(receipt[0])
            and len(receipt[1]) == 12
            and receipt[2] == "verified",
        )
        count = c.execute(
            (
                "SELECT COUNT(*) FROM dbo.CRMCanalInstitucional"
                "WebhookRecepcion WHERE EndpointId=?"
            ),
            item["webhook"]["id"],
        ).fetchval()
        check("one_receipt_no_rejected_data", count == 1)
    check(
        "anonymous_human_route_denied",
        __import__("fastapi.testclient", fromlist=["TestClient"])
        .TestClient(
            create_app(settings),
            base_url="http://127.0.0.1:4178",
            client=("127.0.0.1", 50300),
        )
        .get("/api/institution/channels", headers={"X-CRM-Local": "1"})
        .status_code
        == 401,
    )
    check(
        "CSRF_denial",
        owner.request(
            "channels/" + identity + "/webhook",
            "POST",
            {
                "operation_id": str(uuid4()),
                "row_version": active["webhook"]["row_version"],
                "active": False,
            },
            expected=403,
            csrf=False,
        ).status_code
        == 403,
    )
    from tools.qualify_p4_flows import qualify

    qualify(settings, owner, identity, secret, check)
    save(
        WORK / "api-result.json",
        {
            "status": "passed",
            "checks": checks,
            "real_provider_calls": 0,
            "source_database_modified": False,
        },
    )
    print(json.dumps({"passed": len(checks), "real_provider_calls": 0}))


if __name__ == "__main__":
    main()
