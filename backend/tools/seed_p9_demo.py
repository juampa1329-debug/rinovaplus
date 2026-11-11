"""Explicit fictitious Ads records in the newly prepared own preview only."""

import json
from uuid import uuid4

from tools.p9_test_support import Harness
from tools.prepare_p9_ads import WORK, save


def main():
    h = Harness("final")
    assert h.settings.connection["database"] == "CBN_P9ES_TRIAL_20261027_94ba4b55"
    assert not (WORK / "demo-result.json").exists(), "completed demo must not rerun"
    assert all(
        v["external_account_id"].startswith("demo_cbn_")
        for v in h.call("ads/accounts")["items"]
    )

    def cmd(**kw):
        return dict(operation_id=str(uuid4()), revision=0, **kw)

    created = []
    for provider, channel, title in [
        ("meta", "facebook", "Admisiones Meta · ejemplo"),
        ("tiktok", "tiktok", "Programas TikTok · ejemplo"),
    ]:
        previous = next(
            (
                v
                for v in h.call("ads/accounts")["items"]
                if v["external_account_id"] == "demo_cbn_" + provider
            ),
            None,
        )
        document = dict(
            provider=provider,
            external_account_id="demo_cbn_" + provider,
            name=title,
            status="connected",
            form_ids=["demo_form_" + provider],
        )
        body = cmd(document=document)
        if previous:
            body["revision"] = previous["revision"]
        a = h.call(
            "ads/accounts" + ("/" + previous["id"] if previous else ""),
            "PATCH" if previous else "POST",
            body,
        )
        campaign = next(
            (
                v
                for v in h.call("ads/campaigns?account_id=" + a["id"])["items"]
                if v["external_campaign_id"] == "demo_campaign_" + provider
            ),
            None,
        )
        if not campaign:
            campaign = h.call(
                "ads/campaigns",
                "POST",
                cmd(
                    document=dict(
                        account_id=a["id"],
                        channel=channel,
                        external_campaign_id="demo_campaign_" + provider,
                        name="Inscripciones · ejemplo ficticio",
                        objective="leads",
                        status="draft",
                        daily_budget_cents=0,
                        lifetime_budget_cents=0,
                        metrics_json=dict(ctr=0, cpc=0, leads=1),
                        period_start="2026-10-01",
                        period_end="2026-10-27",
                    )
                ),
            )
        row = h.call(
            "ads/leads/import",
            "POST",
            cmd(
                document=dict(
                    account_id=a["id"],
                    channel=channel,
                    external_id="demo_lead_" + provider,
                    external_form_id="demo_form_" + provider,
                    external_campaign_id="demo_campaign_" + provider,
                    contact_name="Laura Ejemplo"
                    if provider == "meta"
                    else "Miguel Ejemplo",
                    email=provider + "@example.invalid",
                    message="Quisiera información sobre los programas y el proceso de admisión.",
                    captured_at="2026-10-27T14:00:00Z",
                ),
                create_conversation=True,
            ),
        )
        ids = [row["id"]]
        if provider == "meta":
            comment = h.call(
                "ads/comments/import",
                "POST",
                cmd(
                    document=dict(
                        account_id=a["id"],
                        channel=channel,
                        external_id="demo_comment_meta",
                        external_post_id="demo_post",
                        author_id="demo_author",
                        contact_name="Valentina Ejemplo",
                        message="¿Cuándo comienzan las inscripciones?",
                        captured_at="2026-10-27T14:10:00Z",
                    ),
                    create_conversation=True,
                ),
            )
            ids.append(comment["id"])
        for id in ids:
            h.sql(
                "UPDATE crm_ads9.Intake SET Origin='synthetic_demo' WHERE IntakeId=?",
                id,
                write=True,
            )
        h.sql(
            "INSERT crm_ads9.Event(InstitutionId,EventId,AccountId,Kind,ActorId,Document) SELECT InstitutionId,NEWID(),AccountId,'synthetic_demo_seed',(SELECT TOP(1) UserId FROM crm_access.AccessUser WHERE NormalizedLogin=?),? FROM crm_ads9.Account WHERE AccountId=?",
            h.access["email"],
            json.dumps(
                dict(
                    capture_ids=ids,
                    provider_calls=0,
                    marketing_consent=False,
                    advertising_spend=0,
                )
            ),
            a["id"],
            write=True,
        )
        document["status"] = "paused"
        h.call(
            "ads/accounts/" + a["id"],
            "PATCH",
            dict(cmd(document=document), revision=a["revision"]),
        )
        created.append(
            dict(account_id=a["id"], campaign_id=campaign["id"], intakes=ids)
        )
    assert h.sql("SELECT COUNT(*) FROM crm_ads9.Secret")[0][0] == 0
    save(
        WORK / "demo-result.json",
        dict(
            status="passed",
            accounts=2,
            campaigns=2,
            leads=2,
            comments=1,
            created=created,
            origin="synthetic_demo",
            real_provider_calls=0,
            marketing_consent_created=False,
            academic_writes=False,
        ),
    )
    print(
        json.dumps(dict(status="passed", accounts=2, campaigns=2, leads=2, comments=1))
    )


if __name__ == "__main__":
    main()
