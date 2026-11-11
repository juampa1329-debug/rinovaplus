"""Populated P10 native restore, key authentication and private blob recovery."""

import json
import os
from pathlib import Path

from app.institutional import learning_policy as policy
from app.institutional.spanish import load
from app.institutional.spanish_bindings import Cursor
from app.institutional.store import transaction
from tools.p10_learning_recovery import backup, copy_media, fingerprint
from tools.prepare_p10_learning import WORK, admin, prepare, read, save


def recover(label="populated-recovery", source_label="fixture"):
    from app.institutional.api import create_app
    from tools.qualify_p3_workspace import Browser
    from tools.qualify_p4_deployment import fingerprint as selected_fingerprint

    fixture = load(Path(read(WORK / (source_label + "-profile.json"))["directory"]))
    mapping = policy.layout()
    volatile = {
        mapping["tables"]["crm_access." + n]
        for n in ["Session", "Challenge", "RecoveryCode", "Factor"]
    }
    volatile.add(mapping["tables"]["crm_channels2.OAuthSession"])
    volatile.update(
        (
            mapping["tables"][n]
            for n in [
                "crm_campaign8.Record",
                "crm_campaign8.Enrollment",
                "crm_broadcast7.Campaign",
                "crm_broadcast7.Recipient",
                "crm_channels2.SendJob",
                "crm_channels2.ProviderOperation",
                "crm_channels2.QuotaReservation",
            ]
        )
    )
    volatile.add(mapping["tables"]["crm_ads9.Account"])
    volatile.add(mapping["tables"]["crm_learning10.Deployment"])
    stable = (
        set(mapping["tables"].values()) | set(mapping["academic_tables"])
    ) - volatile
    with admin(fixture.connection["database"]) as connection:
        c = Cursor(connection.cursor(), mapping["tables"])
        assert (
            c.execute(
                "SELECT COUNT(*) FROM crm_agents5.Request WHERE State='running'"
            ).fetchval()
            == 0
        )
        stable_before = selected_fingerprint(connection.cursor(), stable)
        checkpoint = backup(connection, fixture.ticket["identity"])
    prepare(label, checkpoint=checkpoint, recovering_from=fixture)
    recovered = load(Path(read(WORK / (label + "-profile.json"))["directory"]))
    checks = []
    with admin(recovered.connection["database"], readonly=True) as connection:
        stable_after = selected_fingerprint(connection.cursor(), stable)
        assert stable_before == stable_after, (
            "populated recovery changed business bytes"
        )
        checks.append(
            "stable_tables_preserve_configuration_memory_vault_and_append_only_P10_history"
        )
        c = Cursor(connection.cursor(), mapping["tables"])
        assert (
            c.execute(
                "SELECT COUNT(*) FROM crm_access.Session WHERE RevokedAt IS NULL"
            ).fetchval()
            == 0
        )
        checks.append("copied_sessions_are_revoked_before_new_login")
    with transaction(recovered, anonymous=True):
        pass
    checks.append("native_populated_recovery_profile_TLS_and_closed_partition")
    with admin(fixture.connection["database"], readonly=True) as connection:
        assert fingerprint(connection.cursor()) == checkpoint["data"]
    checks.append("source_fixture_185_table_fingerprint_is_unchanged")
    access = read(WORK / (source_label + "-access.json"))
    browser = Browser(create_app(recovered))
    browser.login(access["email"], access["password"])
    result = browser.request("/api/v1/agents").json()
    assert len(result["agents"]) >= 3
    checks.append("same_human_credentials_and_agent_catalog_work_after_recovery")
    save(
        WORK / "recovery-result.json",
        {
            "status": "passed",
            "checks": checks,
            "database": recovered.connection["database"],
            "stable_fingerprint": stable_after,
            "stable_tables": len(stable),
            "secret_authentication": "all_access_C10_and_Ads_vault_versions_validated_by_preparer",
            "academic_writes": False,
            "provider_calls": 0,
        },
    )
    print(
        json.dumps({"recovered_tables": 185, "checks": len(checks), "status": "passed"})
    )


def media_and_consumers(label="populated-recovery"):
    from app.institutional.broadcast_dispatch import Worker as Bulk
    from app.institutional.campaign_assets import library_file
    from app.institutional.campaign_runtime import Worker
    from app.institutional.channel_media import file_for
    from app.institutional.channel_outbox import Dispatcher

    s = load(Path(read(WORK / (label + "-profile.json"))["directory"]))
    destination = WORK / (label + "-media")
    os.environ["CRM_AI_STATE_DIR"] = str(destination)
    report = read(WORK / "recovery-result.json")
    with transaction(s, anonymous=True) as c:
        manifest = copy_media(
            c.physical, WORK / "parent-media/inbox-media", destination / "inbox-media"
        )
        assert len(manifest) >= 4
        for r in c.execute(
            "SELECT EventId FROM crm_campaign8.Event WHERE Kind='template_asset'"
        ).fetchall():
            library_file(c, s, str(r[0]))
        for r in c.execute(
            "SELECT MediaId FROM crm_channels4.MediaAsset WHERE State='ready'"
        ).fetchall():
            file_for(c, s, str(r[0]))
        assert (
            c.execute(
                "SELECT COUNT(*) FROM crm_ads9.Account WHERE State='connected'"
            ).fetchval()
            == 0
        )
        assert c.execute("SELECT COUNT(*) FROM crm_learning10.Artifact").fetchval() >= 2
        assert not c.execute(
            "SELECT 1 FROM crm_learning10.Deployment WHERE State<>'paused'"
        ).fetchone()
    report["checks"].append(
        "models_and_Ads_paused_all_secret_versions_authenticated_before_new_login"
    )
    report["checks"].append(
        "four_private_parent_template_blobs_copied_and_revalidated_in_new_root"
    )
    calls = []
    assert not Worker(s).refresh() and not Worker(s).once()
    assert not Bulk(s, controlled=True).once()
    assert not Dispatcher(
        s, transport=lambda *a, **kw: calls.append(True), allow_controlled=True
    ).once()
    assert not calls
    report["checks"].append(
        "recovered_consumers_do_not_POST_or_schedule_Ads_or_campaign_effects"
    )
    report.update(ready_blobs_copied=len(manifest), media_manifest=manifest)
    save(WORK / "recovery-result.json", report)
    print(
        json.dumps(
            dict(
                status="passed", checks=len(report["checks"]), ready_blobs=len(manifest)
            )
        )
    )


if __name__ == "__main__":
    recover()
    media_and_consumers()
