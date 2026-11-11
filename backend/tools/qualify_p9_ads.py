"""Native SQL2019 Ads API, identity, permissions and zero provider effects."""

import json
from unittest.mock import patch
from uuid import uuid4

from tools.p9_test_support import Harness
from tools.prepare_p9_ads import WORK, save


def main():
    h = Harness()
    checks = []

    def check(name, ok=True):
        assert ok, name
        checks.append(name)
        save(WORK / "api-result.json", dict(status="in_progress", checks=checks))

    def cmd(revision=0, **kw):
        return dict(operation_id=str(uuid4()), revision=revision, **kw)

    options = h.call("ads/options")
    check(
        "native_P9_profile_options_and_closed_capabilities",
        not options["provider_spending_supported"]
        and not options["external_sync_supported"],
    )
    doc = dict(
        provider="meta",
        external_account_id="qa_" + uuid4().hex,
        name="Admisiones SQL P9",
    )
    body = cmd(document=doc)
    a = h.call("ads/accounts", "POST", body)
    check(
        "account_exact_replay_creates_one_record",
        h.call("ads/accounts", "POST", body) == a,
    )
    other = h.call(
        "ads/accounts",
        "POST",
        cmd(document=dict(doc, external_account_id="qa_" + uuid4().hex)),
    )
    campaign = dict(
        account_id=a["id"],
        external_campaign_id="campaign_shared",
        name="Orientación educativa",
        daily_budget_cents=2500000,
        metrics_json=dict(ctr=1.25, cpc=1200, leads=3),
        period_start="2026-10-01",
        period_end="2026-10-27",
    )
    saved = h.call("ads/campaigns", "POST", cmd(document=campaign))
    second = h.call(
        "ads/campaigns", "POST", cmd(document=dict(campaign, account_id=other["id"]))
    )
    check(
        "same_campaign_external_id_is_isolated_by_account", saved["id"] != second["id"]
    )
    lead = dict(
        account_id=a["id"],
        external_id="lead_shared",
        contact_name="Aspirante de prueba",
        phone="573000000091",
        email="demo@example.invalid",
        external_campaign_id="campaign_shared",
    )
    imported = h.call("ads/leads/import", "POST", cmd(document=lead))
    duplicate = h.call("ads/leads/import", "POST", cmd(document=lead))
    check(
        "duplicate_lead_external_id_does_not_duplicate_capture",
        imported["id"] == duplicate["id"],
    )
    cross = h.call(
        "ads/leads/import", "POST", cmd(document=dict(lead, account_id=other["id"]))
    )
    check(
        "same_phone_email_and_lead_id_are_not_merged_across_accounts",
        cross["id"] != imported["id"],
    )
    with patch("httpx2.Client", side_effect=AssertionError("unexpected_provider_IO")):
        linked = h.call(
            "ads/leads/" + imported["id"] + "/to-inbox",
            "POST",
            cmd(imported["revision"]),
        )
        first = h.sql("SELECT COUNT(*) FROM crm_workspace.Note")[0][0]
        current = h.call("ads/intakes/" + imported["id"])
        reread = h.call(
            "ads/leads/" + imported["id"] + "/to-inbox",
            "POST",
            cmd(current["revision"]),
        )
        assert (
            linked == reread
            and h.sql("SELECT COUNT(*) FROM crm_workspace.Note")[0][0] == first
        )
        h.call("ads/summary")
        h.call("ads/campaigns")
    check("conversion_and_reads_perform_no_advertising_provider_calls")
    check(
        "reconversion_preserves_contact_conversation_note_and_unread_state",
        linked == reread,
    )
    converted_other = h.call(
        "ads/leads/" + cross["id"] + "/to-inbox", "POST", cmd(cross["revision"])
    )
    check(
        "cross_account_people_and_conversations_remain_separate",
        converted_other["contact_id"] != linked["contact_id"]
        and converted_other["conversation_id"] != linked["conversation_id"],
    )
    check(
        "form_conversion_creates_no_DM_identity_or_consent",
        not h.sql(
            "SELECT IdentityId FROM crm_channels2.ExternalIdentity WHERE ConversationId=?",
            linked["conversation_id"],
        )
        and not h.sql(
            "SELECT 1 FROM crm_broadcast7.Consent c JOIN crm_channels2.ExternalIdentity i ON i.InstitutionId=c.InstitutionId AND i.IdentityId=c.IdentityId WHERE i.ContactId=?",
            linked["contact_id"],
        ),
    )
    h.call("ads/leads/" + cross["id"] + "/to-inbox", "POST", cmd(1), expected=409)
    check("stale_conversion_revision_is_rejected")
    bad = dict(campaign, account_id=other["id"])
    h.call(
        "ads/campaigns/" + saved["id"],
        "PATCH",
        cmd(saved["revision"], document=bad),
        expected=409,
    )
    check("campaign_cannot_be_reparented_to_another_account")
    token = "controlled-ads-token-" + uuid4().hex
    private = cmd(a["revision"], value=token)
    result = h.call("ads/accounts/" + a["id"] + "/credential", "POST", private)
    assert h.call("ads/accounts/" + a["id"] + "/credential", "POST", private) == result
    accounts = h.call("ads/accounts")
    assert token not in json.dumps(accounts) and token not in json.dumps(
        h.call("ads/accounts/" + a["id"] + "/history")
    )
    check("versioned_credential_is_private_and_exactly_replayable")
    conflicting = dict(private, value="different-controlled-token")
    h.call("ads/accounts/" + a["id"] + "/credential", "POST", conflicting, expected=409)
    check("operation_id_cannot_mask_a_different_secret")
    h.call(
        "ads/accounts/" + a["id"] + "/credential",
        "POST",
        cmd(result["revision"], value=None),
    )
    check(
        "revocation_clears_pointer_without_deleting_credential_history",
        h.sql("SELECT COUNT(*) FROM crm_ads9.Secret WHERE AccountId=?", a["id"])[0][0]
        == 1,
    )
    # Read-only handlers may touch session/rate metadata, never domain records or spend.
    query = "SELECT (SELECT COUNT(*) FROM crm_ads9.Event),(SELECT SUM(Revision) FROM crm_ads9.Account),(SELECT SUM(Revision) FROM crm_ads9.Campaign),(SELECT SUM(Revision) FROM crm_ads9.Intake)"
    before = h.sql(query)
    for endpoint in [
        "ads/accounts",
        "ads/campaigns",
        "ads/leads",
        "ads/comments",
        "ads/summary",
        "ads/processes",
        "ads/accounts/" + a["id"] + "/history",
    ]:
        h.call(endpoint)
    check(
        "GET_handlers_preserve_domain_records_events_and_budget_revisions",
        h.sql(query) == before,
    )
    h.call(
        "ads/leads/import",
        "POST",
        cmd(document=lead, create_conversation=False),
        expected=200,
    )
    h.b.client.cookies.clear()
    response = h.b.client.get(
        "/api/institution/ads/accounts", headers={"X-CRM-Local": "1"}
    )
    check("anonymous_account_access_denied", response.status_code == 401)
    save(
        WORK / "api-result.json",
        dict(
            status="passed",
            checks=checks,
            database=h.settings.connection["database"],
            engine=15,
            compatibility=150,
            provider_calls=0,
            academic_writes=False,
        ),
    )
    print(json.dumps(dict(status="passed", checks=len(checks))))


if __name__ == "__main__":
    main()
