"""Explicit localhost C13 API acceptance; no profile discovery or provider calls."""

import argparse
import http.cookiejar
import json
import urllib.error
import urllib.request
import uuid
from pathlib import Path


def check(work):
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
    )
    passed = []

    def expect(value, label):
        if not value:
            raise AssertionError("C13 HTTP " + label)
        passed.append(label)
        print(json.dumps({"passed": label}), flush=True)

    def request(path, method="GET", body=None, headers=None):
        data = None if body is None else json.dumps(body).encode()
        value = urllib.request.Request(
            "http://127.0.0.1:4176" + path,
            data=data,
            method=method,
            headers={
                "X-CRM-Local": "1",
                **({"Content-Type": "application/json"} if body is not None else {}),
                **(headers or {}),
            },
        )
        try:
            response = opener.open(value, timeout=35)
        except urllib.error.HTTPError as error:
            response = error
        raw = response.read()
        content = (
            json.loads(raw)
            if response.headers.get("Content-Type", "").startswith("application/json")
            else None
        )
        return response.status, content, response.headers

    expect(request("/api/local/crm")[0] == 403, "session_required")
    expect(
        request("/api/local/session", "POST", headers={"Origin": "http://evil.test"})[0]
        == 403,
        "cross_origin_bootstrap_rejected",
    )
    status, body, headers = request("/api/local/session", "POST")
    expect(
        status == 200
        and body == {"scope": "local_owner_preview"}
        and "HttpOnly" in headers["Set-Cookie"]
        and "SameSite=strict" in headers["Set-Cookie"],
        "private_session_bootstrap",
    )
    expect(
        request("/api/local/runtime", headers={"Host": "evil.test"})[0] == 403,
        "original_host_rejected",
    )
    status, manifest, _ = request("/api/local/runtime")
    expect(
        status == 200
        and manifest["version"] == "cbn-general-preview-c13-v1"
        and manifest["profile"] == "general_preview",
        "own_manifest",
    )
    expect(
        len(manifest["sections"]) == 14
        and sum(s["available"] for s in manifest["sections"]) == 5
        and not any(manifest["features"].values()),
        "all_sections_with_explicit_pending_states",
    )
    for path in (
        "/api/local/crm",
        "/api/local/crm/configuration",
        "/api/local/crm/inbox",
        "/api/local/progress",
        "/api/local/channels/integrations",
        "/api/local/channels/secrets",
    ):
        status, value, _ = request(path)
        expect(status == 200, "read_" + path.rsplit("/", 1)[-1])
        if "/channels/" in path:
            expect(
                not any(
                    k in json.dumps(value)
                    for k in (
                        "Ciphertext",
                        "Fingerprint",
                        "BodyNonce",
                        "BodyCiphertext",
                        "Payload",
                    )
                ),
                "safe_" + path.rsplit("/", 1)[-1],
            )
    expect(request("/api/v1/ai/chat", "POST", {})[0] == 503, "AI_not_activated")
    expect(
        request("/api/v1/webhooks/meta", "POST", {})[0] == 503,
        "public_webhook_not_activated",
    )
    expect(
        request("/api/local/channels/integrations", "POST", {})[0] == 503,
        "channel_read_only_contract",
    )
    expect(
        request(
            "/api/local/runtime",
            headers={"X-Forwarded-For": "203.0.113.1", "X-Forwarded-Proto": "https"},
        )[0]
        == 200,
        "forwarded_headers_do_not_change_loopback_peer",
    )
    case_path = work / "http-case.json"
    if not case_path.exists():
        _, snapshot, _ = request("/api/local/crm")
        template = snapshot["clients"][0].copy()
        template.update(
            id=str(uuid.uuid4()),
            name="Prueba de preview C13",
            phone="",
            city="Ensayo C13",
            programId=None,
            program="",
            notes="Fixture sintética C13",
        )
        body = {
            "operationId": str(uuid.uuid4()),
            "expectedRevision": snapshot["revision"],
            "conversationId": str(uuid.uuid4()),
            "client": template,
        }
        case_path.parent.mkdir(parents=True, exist_ok=True)
        case_path.write_text(json.dumps(body), encoding="utf-8")
    body = json.loads(case_path.read_text(encoding="utf-8"))
    status, created, _ = request("/api/local/crm/clients", "POST", body)
    expect(
        status == 201
        and any(c["id"] == body["client"]["id"] for c in created["clients"]),
        "CRM_create_on_own_copy",
    )
    status, replay, _ = request("/api/local/crm/clients", "POST", body)
    expect(status == 201 and replay == created, "CRM_operation_exact_replay")
    stale = {
        **body,
        "operationId": str(uuid.uuid4()),
        "client": {**body["client"], "notes": "must not save stale edit"},
    }
    expect(
        request("/api/local/crm/clients/" + body["client"]["id"], "PUT", stale)[0]
        == 409,
        "CRM_stale_revision_rejected",
    )
    external = {
        "operationId": str(uuid.uuid4()),
        "expectedRevision": created["revision"],
        "messageId": str(uuid.uuid4()),
        "body": "No external delivery",
        "delivery": "external",
        "identityId": str(uuid.uuid4()),
    }
    expect(
        request(
            "/api/local/crm/conversations/" + body["conversationId"] + "/messages",
            "POST",
            external,
        )[0]
        == 503,
        "external_delivery_blocked",
    )
    message_path = work / "http-message.json"
    if not message_path.exists():
        message = {
            "operationId": str(uuid.uuid4()),
            "expectedRevision": created["revision"],
            "messageId": str(uuid.uuid4()),
            "body": "Mensaje local sintético C13",
            "delivery": "local",
        }
        message_path.write_text(json.dumps(message), encoding="utf-8")
    message = json.loads(message_path.read_text(encoding="utf-8"))
    status, saved, _ = request(
        "/api/local/crm/conversations/" + body["conversationId"] + "/messages",
        "POST",
        message,
    )
    expect(status == 201, "local_message_persisted")
    expect(
        request(
            "/api/local/crm/conversations/" + body["conversationId"] + "/messages",
            "POST",
            message,
        )[1]
        == saved,
        "local_message_replay_without_duplicate",
    )
    _, readback, _ = request("/api/local/crm/clients/" + body["client"]["id"])
    expect(
        readback["client"]["notes"] == "Fixture sintética C13",
        "CRM_readback_and_draft_conflict_preservation",
    )
    return {
        "unit": "SQL-C13",
        "status": "passed",
        "scope": "own_general_preview_localhost",
        "checks": passed,
        "check_count": len(passed),
        "academic_DML": False,
        "external_effects": 0,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = check(args.work)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"passed": result["check_count"]}))
