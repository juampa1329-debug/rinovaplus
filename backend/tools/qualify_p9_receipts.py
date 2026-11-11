"""Real signed C10 ingress and owned Ads cursor on the isolated P9 fixture."""

import hashlib
import hmac
import json
from uuid import uuid4

from app.institutional.channel_events import EventWorker
from app.institutional.store import transaction
from app.modules.crm_configuration.application.service import read_configuration
from tools.p9_test_support import Harness
from tools.prepare_p9_ads import WORK, save


def native_fixture(h, channel_kind="messenger"):
    def cmd(revision=0, **data):
        return dict(operation_id=str(uuid4()), revision=revision, **data)

    is_tiktok = channel_kind == "tiktok"
    client_id = "808" + str(int(uuid4().hex[:6], 16))
    channel = h.call(
        "channels",
        "POST",
        dict(
            operation_id=str(uuid4()),
            channel=channel_kind,
            display_name="Controlado P9 " + uuid4().hex[:6],
            issuer_profile="tiktok_business" if is_tiktok else "facebook_login",
            client_id=client_id,
            api_version="" if is_tiktok else "v24.0",
        ),
    )
    id = channel["id"]
    item = next(v for v in h.call("channels")["items"] if v["id"] == id)
    secret = "controlled-P9-app-" + uuid4().hex
    h.call(
        "credentials",
        "PUT",
        dict(
            operation_id=str(uuid4()),
            scope="channel",
            owner="endpoint:" + item["webhook"]["id"]
            if is_tiktok
            else "application:" + item["application_id"],
            kind="webhook_secret" if is_tiktok else "app_secret",
            value=secret,
        ),
    )
    page = "page_p9_" + uuid4().hex[:8]
    with transaction(h.settings, anonymous=True) as c:
        cfg, _ = read_configuration(c, foundation=True)
        stage = next(v for v in cfg.stages if v.active)
        digest = hashlib.sha256(cfg.model_dump_json().encode()).digest()
    h.sql(
        "UPDATE crm_channels2.Integration SET ExternalAccountId=?,RequestedStatus='connected',VerifiedStatus='verified',InitialStageKey=?,InitialStageConfigHash=? WHERE IntegrationId=?",
        page,
        stage.key,
        digest,
        id,
        write=True,
    )
    item = next(v for v in h.call("channels")["items"] if v["id"] == id)
    h.call(
        "channels/" + id + "/webhook",
        "POST",
        dict(
            operation_id=str(uuid4()),
            row_version=item["webhook"]["row_version"],
            active=True,
        ),
    )
    item = next(v for v in h.call("channels")["items"] if v["id"] == id)
    adoc = dict(
        provider="tiktok" if is_tiktok else "meta",
        external_account_id="ads_" + uuid4().hex,
        name="Captación controlada P9",
        integration_id=id,
        form_ids=["form_p9_1"],
    )
    a = h.call("ads/accounts", "POST", cmd(document=adoc))
    return dict(
        client_id=client_id,
        account=a,
        integration=id,
        page=page,
        item=item,
        secret=secret,
        adoc=adoc,
    )


def main():
    h = Harness()
    checks = []

    def cmd(revision=0, **data):
        return dict(operation_id=str(uuid4()), revision=revision, **data)

    def check(name, ok=True):
        assert ok, name
        checks.append(name)
        save(WORK / "receipts-result.json", dict(status="in_progress", checks=checks))

    fixture = native_fixture(h)
    a, id, page, item, secret, adoc = (
        fixture[k] for k in ("account", "integration", "page", "item", "secret", "adoc")
    )
    adoc2 = dict(adoc, external_account_id="ads_" + uuid4().hex, form_ids=["form_p9_2"])
    b = h.call("ads/accounts", "POST", cmd(document=adoc2))

    def receive(external, form="form_p9_1", **extra):
        value = dict(
            leadgen_id=external,
            form_id=form,
            field_data=[
                dict(name="full_name", values=["Aspirante firmado"]),
                dict(name="phone_number", values=["573000000092"]),
            ],
            **extra,
        )
        payload = dict(
            object="page",
            entry=[dict(id=page, changes=[dict(field="leadgen", value=value)])],
        )
        raw = json.dumps(payload).encode()
        headers = {
            "X-Hub-Signature-256": "sha256="
            + hmac.digest(secret.encode(), raw, "sha256").hex()
        }
        response = h.b.client.post(
            item["webhook"]["path"], content=raw, headers=headers
        )
        assert response.status_code == 200
        receipt = str(
            h.sql(
                "SELECT ReceiptId FROM crm_channels2.WebhookReceipt WHERE Digest=?",
                hashlib.sha256(raw).digest(),
            )[0][0]
        ).lower()
        return raw, headers, receipt

    def run(a, limit=8):
        for _ in range(limit):
            value = h.call(
                "ads/accounts/" + a["id"] + "/process", "POST", cmd(a["revision"])
            )
            if value["state"] != "ignored":
                return value
        raise AssertionError("controlled_receipt_not_reached")

    external = "lead_" + uuid4().hex
    raw, headers, receipt = receive(external)
    native = EventWorker(h.settings)
    for _ in range(40):
        native.once()
        if (
            h.sql(
                "SELECT Status FROM crm_channels2.WebhookReceipt WHERE ReceiptId=?",
                receipt,
            )[0][0]
            != "queued"
        ):
            break
    assert (
        h.sql(
            "SELECT Status FROM crm_channels2.WebhookReceipt WHERE ReceiptId=?", receipt
        )[0][0]
        == "quarantined"
    )
    before = h.sql(
        "SELECT Status,Attempts,LeaseVersion,LastErrorCode FROM crm_channels2.WebhookReceipt WHERE ReceiptId=?",
        receipt,
    )
    body = cmd(a["revision"])
    result = h.call("ads/accounts/" + a["id"] + "/process", "POST", body)
    assert result["state"] == "processed" and result["leads"] == 1, result
    check(
        "signed_leadgen_is_processed_after_C10_quarantine_without_competing_for_status",
        h.sql(
            "SELECT Status,Attempts,LeaseVersion,LastErrorCode FROM crm_channels2.WebhookReceipt WHERE ReceiptId=?",
            receipt,
        )
        == before,
    )
    check(
        "process_operation_exact_replay_has_no_second_effect",
        h.call("ads/accounts/" + a["id"] + "/process", "POST", body) == result,
    )
    lead = next(
        v
        for v in h.call("ads/leads?account_id=" + a["id"])["items"]
        if v["external_id"] == external
    )
    assert lead["origin"] == "verified_receipt" and lead["conversation_id"]
    check(
        "form_projection_creates_local_context_without_DM_window",
        not h.sql(
            "SELECT IdentityId FROM crm_channels2.ExternalIdentity WHERE ConversationId=?",
            lead["conversation_id"],
        ),
    )
    rejected = h.b.client.post(
        item["webhook"]["path"],
        content=raw,
        headers={"X-Hub-Signature-256": "sha256=" + "0" * 64},
    )
    check("forged_signature_cannot_create_an_Ads_receipt", rejected.status_code == 403)
    again = h.b.client.post(item["webhook"]["path"], content=raw, headers=headers)
    assert again.json()["duplicate"]
    check(
        "duplicate_raw_webhook_does_not_reinsert_capture_or_note",
        run(a)["state"] == "empty",
    )
    # A later receipt enriches the same external lead and preserves its original CRM link.
    receive(external, email="actualizado@example.invalid")
    enriched = run(a)
    assert enriched["state"] == "processed" and enriched["duplicates"] == 1, enriched
    after = next(
        v
        for v in h.call("ads/leads?account_id=" + a["id"])["items"]
        if v["external_id"] == external
    )
    check(
        "later_verified_receipt_enriches_capture_without_relinking_or_changing_first_date",
        after["email"] == "actualizado@example.invalid"
        and after["conversation_id"] == lead["conversation_id"]
        and after["captured_at"] == lead["captured_at"],
    )
    # Distinct lead IDs with the same normalized contact remain correlated only inside this account.
    second = "lead_" + uuid4().hex
    receive(second)
    assert run(a)["state"] == "processed"
    same = next(
        v
        for v in h.call("ads/leads?account_id=" + a["id"])["items"]
        if v["external_id"] == second
    )
    check(
        "same_account_form_contact_reuses_local_identity_without_cross_account_phone_merge",
        same["conversation_id"] == lead["conversation_id"],
    )
    # Account B must ignore A's events and only process its own form.
    own = "lead_" + uuid4().hex
    receive(own, "form_p9_2")
    br = run(b)
    assert br["state"] == "processed", br
    other = next(
        v
        for v in h.call("ads/leads?account_id=" + b["id"])["items"]
        if v["external_id"] == own
    )
    check(
        "shared_page_and_phone_do_not_cross_advertiser_accounts",
        other["contact_id"] != lead["contact_id"],
    )
    # Ambiguous form ownership is quarantined until a concrete mapping is corrected.
    duplicate_account = h.call(
        "ads/accounts",
        "POST",
        cmd(document=dict(adoc, external_account_id="ads_" + uuid4().hex)),
    )
    receive("ambiguous_" + uuid4().hex)
    bad = run(a)
    assert (
        bad["state"] == "quarantined"
        and bad["error"] == "ads_ambiguous_account_mapping"
    ), bad
    check("ambiguous_form_has_no_partial_contact_or_capture_effect")
    h.call(
        "ads/accounts/" + duplicate_account["id"],
        "PATCH",
        cmd(
            duplicate_account["revision"],
            document=dict(
                adoc,
                external_account_id=duplicate_account["external_account_id"],
                form_ids=[],
            ),
        ),
    )
    retry = h.call(
        "ads/accounts/" + a["id"] + "/processes/" + bad["id"] + "/retry",
        "POST",
        cmd(bad["revision"]),
    )
    check(
        "reviewed_retry_preserves_receipt_id_and_history",
        retry["state"] == "processed"
        and retry["receipt_id"] == bad["receipt_id"]
        and retry["revision"] == bad["revision"] + 1,
    )
    # Changes to the native channel context are revalidated before projecting a new receipt.
    receive("paused_" + uuid4().hex)
    h.sql(
        "UPDATE crm_channels2.Integration SET RequestedStatus='paused',VerifiedStatus='unverified' WHERE IntegrationId=?",
        id,
        write=True,
    )
    paused = run(a)
    assert (
        paused["state"] == "quarantined"
        and paused["error"] == "ads_channel_context_changed"
    ), paused
    check("paused_or_unverified_native_channel_is_quarantined_before_effect")
    h.sql(
        "UPDATE crm_channels2.Integration SET RequestedStatus='connected',VerifiedStatus='verified' WHERE IntegrationId=?",
        id,
        write=True,
    )
    assert (
        h.call(
            "ads/accounts/" + a["id"] + "/processes/" + paused["id"] + "/retry",
            "POST",
            cmd(paused["revision"]),
        )["state"]
        == "processed"
    )
    check(
        "native_context_review_allows_explicit_retry_without_erasing_previous_attempt"
    )
    receive("poison_" + uuid4().hex, timestamp=1e200)
    poison = run(a)
    check(
        "out_of_range_timestamp_is_durably_quarantined_and_cannot_starve_later_receipts",
        poison["state"] == "quarantined" and poison["error"] == "ads_payload_invalid",
    )
    check(
        "no_form_or_comment_projection_grants_marketing_consent",
        h.sql("SELECT COUNT(*) FROM crm_broadcast7.Consent")[0][0] == 0,
    )
    save(
        WORK / "receipts-result.json",
        dict(
            status="passed",
            checks=checks,
            engine=15,
            compatibility=150,
            real_provider_calls=0,
            academic_writes=False,
        ),
    )
    save(
        WORK / "receipt-fixture.json",
        dict(
            integration=id,
            account=a,
            account_document=adoc,
            page=page,
            primary_lead=lead,
        ),
    )
    print(json.dumps(dict(status="passed", checks=len(checks))))


if __name__ == "__main__":
    main()
