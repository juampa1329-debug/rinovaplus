"""Signed TikTok fixture through actual C10 ingress; no external provider IO."""

import hashlib
import hmac
import json
import time
from uuid import uuid4

from tools.p9_test_support import Harness
from tools.prepare_p9_ads import WORK, save
from tools.qualify_p9_receipts import native_fixture


def main():
    h = Harness()
    f = native_fixture(h, "tiktok")
    a = f["account"]
    checks = []

    def cmd(**kw):
        return dict(operation_id=str(uuid4()), revision=a["revision"], **kw)

    payload = dict(
        client_key=f["client_id"],
        user_openid=f["page"],
        event="lead_received",
        content=dict(
            advertiser_id=a["external_account_id"],
            data=[
                dict(
                    leadID="tt_" + uuid4().hex,
                    instant_form_id="form_p9_1",
                    answers=[
                        dict(name="full_name", value="Aspirante TikTok ficticio"),
                        dict(name="email", value="tt@example.invalid"),
                    ],
                )
            ],
        ),
    )
    raw = json.dumps(payload).encode()
    now = str(int(time.time()))
    headers = {
        "tiktok-signature": "t="
        + now
        + ",s="
        + hmac.digest(f["secret"].encode(), now.encode() + b"." + raw, "sha256").hex()
    }
    path = f["item"]["webhook"]["path"]
    assert h.b.client.post(path, content=raw, headers=headers).status_code == 200
    receipt = str(
        h.sql(
            "SELECT ReceiptId FROM crm_channels2.WebhookReceipt WHERE Digest=?",
            hashlib.sha256(raw).digest(),
        )[0][0]
    ).lower()
    for _ in range(50):
        r = h.call("ads/accounts/" + a["id"] + "/process", "POST", cmd())
        if r.get("receipt_id") == receipt:
            break
    assert r["state"] == "processed" and r["leads"] == 1, r
    checks.append("signed_TikTok_lead_uses_native_application_and_Ads_account_binding")
    row = h.call("ads/leads?account_id=" + a["id"])["items"][0]
    assert (
        row["origin"] == "verified_receipt"
        and row["channel"] == "tiktok"
        and row["contact_name"] == "Aspirante TikTok ficticio"
        and row["email"] == "tt@example.invalid"
    )
    checks.append("nested_leadID_instant_form_answers_are_normalized_with_original_ids")
    assert not h.sql(
        "SELECT IdentityId FROM crm_channels2.ExternalIdentity WHERE ConversationId=?",
        row["conversation_id"],
    )
    checks.append("lead_form_does_not_fabricate_TikTok_DM_permission_or_recipient")
    invalid = {"tiktok-signature": "t=" + now + ",s=" + "0" * 64}
    assert h.b.client.post(path, content=raw, headers=invalid).status_code == 403
    wrong = dict(payload, client_key="wrong_application")
    raw2 = json.dumps(wrong).encode()
    headers2 = {
        "tiktok-signature": "t="
        + now
        + ",s="
        + hmac.digest(f["secret"].encode(), now.encode() + b"." + raw2, "sha256").hex()
    }
    assert h.b.client.post(path, content=raw2, headers=headers2).status_code == 403
    checks.append("bad_signature_and_different_client_key_are_rejected_before_capture")
    save(
        WORK / "tiktok-result.json",
        dict(
            status="passed",
            checks=checks,
            engine=15,
            real_provider_calls=0,
            academic_writes=False,
        ),
    )
    print(json.dumps(dict(status="passed", checks=len(checks))))


if __name__ == "__main__":
    main()
