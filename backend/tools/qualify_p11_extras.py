"""Effective sensitive writes and untruncated monitoring on controlled P11 copies."""

import hashlib
from uuid import uuid4

from tools.p11_test_support import Harness
from tools.prepare_p11_operations import WORK, read, save
from tools.qualify_p3_workspace import Browser


def main():
    assert not (WORK / "extras-result.json").exists(), "fresh qualification required"
    assert read(WORK / "access-result.json")["status"] == "passed"
    checks = []
    h = Harness()
    creds = read(WORK / "access-matrix-actors.json")
    for role in ["viewer", "supervisor"]:
        b = Browser(h.app)
        b.login(creds[role]["email"], creds[role]["password"])
        b.request("credentials", "PUT", dict(operation_id=str(uuid4()), scope="provider", owner="openai", kind="api_key", value="synthetic-P11-never-saved-secret"), 403)
    checks.append("valid_credential_payload_with_valid_CSRF_still_denies_viewer_and_supervisor")
    b = Browser(h.app)
    b.login(creds["viewer"]["email"], creds["viewer"]["password"])
    setting = h.call("settings/institution")
    b.request("settings/institution", "PUT", dict(operation_id=str(uuid4()), revision=setting["revision"], document=setting["document"]), 403)
    b.request("channels", "POST", dict(operation_id=str(uuid4()), channel="whatsapp", display_name="P11 denied fixture", issuer_profile="meta_whatsapp", client_id="2707000", api_version="v24.0"), 403)
    checks.append("service_settings_and_channel_creation_deny_valid_viewer_payloads")
    owner = h.call("auth/me")["session_id"]
    h.sql("UPDATE crm_access.Session SET RecentAt=DATEADD(minute,-6,SYSUTCDATETIME()) WHERE SessionId=?", owner, write=True)
    h.call("credentials", "PUT", dict(operation_id=str(uuid4()), scope="provider", owner="openai", kind="api_key", value="synthetic-P11-never-saved-secret"), 428)
    h.call("auth/confirm", "POST", {"current_password": h.access["password"]})
    checks.append("sensitive_write_requires_real_password_reconfirmation_after_five_minutes")
    assert "synthetic-P11-never-saved-secret" not in str(h.call("credentials/provider"))
    checks.append("credential_metadata_does_not_echo_submitted_secret")
    # The worker fixture has real, signed controlled C10 events. Clone only
    # quarantined synthetic events there, never in the populated user preview.
    w = Harness("workers")
    origin = w.sql("SELECT TOP(1) EventId FROM crm_channels2.WebhookEvent ORDER BY CreatedAt")[0][0]
    for i in range(37):
        identity = str(uuid4())
        w.sql("INSERT crm_channels2.WebhookEvent(InstitutionId,EventId,ReceiptId,IntegrationId,SubeventPath,Kind,ProviderEventId,DedupeKey,IdentityStrength,Status,Payload,ProviderOccurredAt,CreatedAt,LeaseId,LeaseUntil,LeaseVersion,Attempts,LastErrorCode,ApplicationId,EndpointId,RouteKind,RouteExternalId) SELECT InstitutionId,?,ReceiptId,IntegrationId,?,Kind,ProviderEventId,?,IdentityStrength,'quarantined',Payload,ProviderOccurredAt,SYSUTCDATETIME(),NULL,NULL,0,0,'p11_monitor_fixture',ApplicationId,EndpointId,RouteKind,RouteExternalId FROM crm_channels2.WebhookEvent WHERE EventId=?", identity, "p11_monitor_" + str(i), hashlib.sha256(identity.encode()).digest(), origin, write=True)
    expected = dict((str(state), int(count)) for state, count in w.sql("SELECT Status,COUNT_BIG(*) FROM crm_channels2.WebhookEvent GROUP BY Status"))
    observed = w.call("operations")["queues"]["webhook_events"]
    assert observed == expected and observed["quarantined"] >= 37
    checks.append("native_monitor_counts_more_than_25_quarantined_events_without_truncation")
    report = dict(status="passed", checks=checks, fixture_only_quarantined_rows_added=37, actual_quarantined_total=observed["quarantined"], no_secret_saved=True, real_provider_calls=0, academic_writes=False)
    save(WORK / "extras-result.json", report)
    print({"status": "passed", "checks": len(checks), "quarantined_total": observed["quarantined"]})


if __name__ == "__main__":
    main()
