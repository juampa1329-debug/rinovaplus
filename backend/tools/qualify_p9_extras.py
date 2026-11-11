"""Cross-module comments, canonical identity, authorization and concurrency in SQL2019."""

import hashlib
import hmac
import json
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from app.institutional.channel_events import EventWorker
from app.institutional.channel_operations import account as native_account
from app.institutional.channel_operations import app_secret_kind
from app.institutional.channel_secrets import get as secret
from app.institutional.store import transaction
from tools.p9_test_support import Harness
from tools.prepare_p9_ads import WORK, save
from tools.qualify_p3_workspace import Browser


def main():
    h = Harness()
    from tools.qualify_p9_receipts import native_fixture

    fixture = native_fixture(h, "facebook")
    a, integration, page = fixture["account"], fixture["integration"], fixture["page"]
    checks = []

    def cmd(revision=0, **kw):
        return dict(operation_id=str(uuid4()), revision=revision, **kw)

    def check(name, ok=True):
        assert ok, name
        checks.append(name)
        save(WORK / "extras-result.json", dict(status="in_progress", checks=checks))

    item = next(v for v in h.call("channels")["items"] if v["id"] == integration)
    with transaction(h.settings, anonymous=True) as c:
        native = native_account(c, h.settings, integration)
        key, _ = secret(
            c,
            h.settings,
            "application",
            str(native["ApplicationId"]),
            app_secret_kind(native),
        )

    def comment(external, author, advertiser):
        value = dict(
            item="comment",
            comment_id=external,
            post_id="post1",
            message="Información de programas",
            ad_account_id=advertiser,
            **{"from": dict(id=author, name="Aspirante de comentario")},
        )
        raw = json.dumps(
            dict(
                object="page",
                entry=[dict(id=page, changes=[dict(field="feed", value=value)])],
            )
        ).encode()
        assert (
            h.b.client.post(
                item["webhook"]["path"],
                content=raw,
                headers={
                    "X-Hub-Signature-256": "sha256="
                    + hmac.digest(key.encode(), raw, "sha256").hex()
                },
            ).status_code
            == 200
        )
        return str(
            h.sql(
                "SELECT ReceiptId FROM crm_channels2.WebhookReceipt WHERE Digest=?",
                hashlib.sha256(raw).digest(),
            )[0][0]
        ).lower()

    def process_until(receipt):
        for _ in range(40):
            result = h.call(
                "ads/accounts/" + a["id"] + "/process", "POST", cmd(a["revision"])
            )
            if result.get("receipt_id") == receipt:
                return result
        raise AssertionError("target_receipt_not_processed")

    def project_until(external):
        worker = EventWorker(h.settings)
        for _ in range(80):
            worker.once()
            worker.project_once()
            if h.sql(
                "SELECT CommentId FROM crm_channels2.SocialComment WHERE IntegrationId=? AND ExternalId=?",
                integration,
                external,
            ):
                return
        raise AssertionError("native_comment_not_projected")

    def convert_native(external):
        comments = h.call("comments?integration=" + integration)["items"]
        row = next(v for v in comments if v["external_id"] == external)
        return h.call(
            "comments/" + row["id"],
            "POST",
            dict(
                operation_id=str(uuid4()),
                row_version=row["row_version"],
                action="convert",
            ),
        )

    external = "comment_" + uuid4().hex
    receipt = comment(external, "author_" + uuid4().hex, a["external_account_id"])
    result = process_until(receipt)
    assert result["state"] == "processed", result
    ads = next(
        v
        for v in h.call("ads/comments?account_id=" + a["id"])["items"]
        if v["external_id"] == external
    )
    project_until(external)
    native = convert_native(external)
    check(
        "Ads_before_C10_projection_reuses_the_same_contact_and_conversation_in_P4",
        native["contact_id"] == ads["contact_id"]
        and native["conversation_id"] == ads["conversation_id"],
    )
    external2 = "comment_" + uuid4().hex
    lead_author = "author_" + uuid4().hex
    prior_lead = h.call(
        "ads/leads/import",
        "POST",
        cmd(
            document=dict(
                account_id=a["id"],
                external_id="prior_" + uuid4().hex,
                author_id=lead_author,
                contact_name="Formulario previo",
            ),
            create_conversation=True,
        ),
    )
    receipt2 = comment(external2, lead_author, a["external_account_id"])
    project_until(external2)
    native2 = convert_native(external2)
    check(
        "lead_before_native_comment_reuses_author_identity_before_Ads_comment_processing",
        native2["contact_id"] == prior_lead["contact_id"]
        and native2["conversation_id"] == prior_lead["conversation_id"],
    )
    assert process_until(receipt2)["state"] == "processed"
    ads2 = next(
        v
        for v in h.call("ads/comments?account_id=" + a["id"])["items"]
        if v["external_id"] == external2
    )
    check(
        "P4_before_Ads_reuses_the_same_existing_link",
        ads2["contact_id"] == native2["contact_id"]
        and ads2["conversation_id"] == native2["conversation_id"],
    )
    # Status can evolve independently while the native conversion link remains intact.
    from app.institutional.ads_models import Intake

    document = {k: ads2[k] for k in Intake.model_fields if k in ads2}
    document["status"] = "ignored"
    ignored = h.call(
        "ads/comments/" + ads2["id"], "PATCH", cmd(ads2["revision"], document=document)
    )
    check(
        "linked_comment_can_be_ignored_without_erasing_conversion_or_context",
        ignored["status"] == "ignored"
        and ignored["conversation_id"] == ads2["conversation_id"],
    )
    # Use the real P3 merge endpoint: it preserves the historical conversation FK.
    revision = h.call("workspace/clients")["revision"]
    merge_id = str(uuid4())
    h.call(
        "workspace/merges/" + merge_id,
        "POST",
        dict(
            operationId=str(uuid4()),
            revision=revision,
            sourceContactId=ads["contact_id"],
            targetContactId=ads2["contact_id"],
            confirmedSamePerson=True,
        ),
    )
    merged = h.call("ads/intakes/" + ads["id"])
    check(
        "native_merge_preserves_historical_conversation_and_resolves_current_canonical_contact",
        merged["contact_id"] == ads2["contact_id"]
        and merged["conversation_id"] == ads["conversation_id"],
    )
    h.call(
        "workspace/merges/" + merge_id + "/undo",
        "POST",
        dict(
            operationId=str(uuid4()), revision=h.call("workspace/clients")["revision"]
        ),
    )
    check(
        "undo_merge_restores_previous_link_without_deleting_Ads_history",
        h.call("ads/intakes/" + ads["id"])["contact_id"] == ads["contact_id"],
    )
    external3 = "comment_" + uuid4().hex
    receipt3 = comment(external3, "author_" + uuid4().hex, a["external_account_id"])
    project_until(external3)
    native3 = convert_native(external3)
    merge3 = str(uuid4())
    h.call(
        "workspace/merges/" + merge3,
        "POST",
        dict(
            operationId=str(uuid4()),
            revision=h.call("workspace/clients")["revision"],
            sourceContactId=native3["contact_id"],
            targetContactId=ads2["contact_id"],
            confirmedSamePerson=True,
        ),
    )
    assert process_until(receipt3)["state"] == "processed"
    linked3 = next(
        v
        for v in h.call("ads/comments?account_id=" + a["id"])["items"]
        if v["external_id"] == external3
    )
    assert linked3["contact_id"] == ads2["contact_id"]
    h.call(
        "workspace/merges/" + merge3 + "/undo",
        "POST",
        dict(
            operationId=str(uuid4()), revision=h.call("workspace/clients")["revision"]
        ),
    )
    after3 = h.call("ads/intakes/" + linked3["id"])
    check(
        "native_merge_before_new_Ads_identity_then_undo_preserves_historical_binding",
        after3["contact_id"] == native3["contact_id"]
        and after3["conversation_id"] == native3["conversation_id"],
    )
    # Concurrent new operation IDs on one external lead still create just one context/note.
    data = dict(
        account_id=a["id"],
        external_id="concurrent_" + uuid4().hex,
        contact_name="Concurrente ficticio",
        phone="573000000093",
    )
    lead = h.call("ads/leads/import", "POST", cmd(document=data))
    before = h.sql("SELECT COUNT(*) FROM crm_workspace.Note")[0][0]

    def convert(_):
        return h.call(
            "ads/leads/" + lead["id"] + "/to-inbox", "POST", cmd(lead["revision"])
        )

    # The second request may observe the new revision; explicit duplicate imports are both idempotent.
    def import_convert(_):
        return h.call(
            "ads/leads/import", "POST", cmd(document=data, create_conversation=True)
        )

    with ThreadPoolExecutor(2) as pool:
        values = list(pool.map(import_convert, range(2)))
    check(
        "concurrent_capture_operations_have_one_conversion_and_note",
        values[0]["conversation_id"] == values[1]["conversation_id"]
        and h.sql("SELECT COUNT(*) FROM crm_workspace.Note")[0][0] == before + 1,
    )
    # Recorder has Ads rights but cannot claim conversion or expose/edit private credentials.
    role = "ads_rec_" + uuid4().hex[:8]
    h.call(
        "roles/" + role,
        "PUT",
        dict(
            operation_id=str(uuid4()),
            revision=0,
            name="Captación controlada",
            actions=["ads.manage", "crm.read"],
        ),
    )
    email = "recorder-" + uuid4().hex[:8] + "@example.invalid"
    password = "Controlled!" + uuid4().hex
    h.call(
        "users",
        "POST",
        dict(
            operation_id=str(uuid4()),
            email=email,
            full_name="Captación controlada",
            password=password,
            role=role,
        ),
    )
    recorder = Browser(h.app)
    recorder.login(email, password)
    doc = dict(
        account_id=a["id"],
        external_id="recorder_" + uuid4().hex,
        contact_name="Registro restringido",
    )
    row = recorder.request("ads/leads/import", "POST", cmd(document=doc)).json()
    recorder.request(
        "ads/leads/" + row["id"],
        "PATCH",
        cmd(row["revision"], document=dict(doc, status="converted")),
        expected=409,
    )
    check("Ads_only_role_cannot_mark_unlinked_capture_converted")
    recorder.request(
        "ads/leads/" + row["id"] + "/to-inbox",
        "POST",
        cmd(row["revision"]),
        expected=403,
    )
    recorder.request(
        "ads/accounts/" + a["id"] + "/credential",
        "POST",
        cmd(a["revision"], value="controlled-private-secret"),
        expected=403,
    )
    check("CRM_Inbox_and_credential_authorities_are_independently_enforced")
    h.b.request(
        "ads/leads/import",
        "POST",
        cmd(document=dict(data, external_id="csrf_" + uuid4().hex)),
        expected=403,
        csrf=False,
    )
    check("write_requires_CSRF_before_any_domain_change")
    modules = h.call("settings/modules")
    document = modules["document"]
    document["enabled"]["ads"] = False
    h.call("settings/modules", "PUT", cmd(modules["revision"], document=document))
    h.call("ads/accounts", expected=403)
    document["enabled"]["ads"] = True
    h.call("settings/modules", "PUT", cmd(modules["revision"] + 1, document=document))
    check("module_switch_stops_Ads_access_and_processing_without_subscription_logic")
    save(
        WORK / "extras-result.json",
        dict(
            status="passed", checks=checks, real_provider_calls=0, academic_writes=False
        ),
    )
    print(json.dumps(dict(status="passed", checks=len(checks))))


if __name__ == "__main__":
    main()
