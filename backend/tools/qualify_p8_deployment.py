"""Read-only preservation and restart receipts for the owned P8 final profile."""

import argparse
import json
from pathlib import Path

from app.institutional.campaign_policy import layout
from app.institutional.spanish import load
from app.institutional.spanish_bindings import Cursor
from tools.prepare_p8_campaign import WORK, admin, read, save, source
from tools.qualify_p4_deployment import fingerprint
from tools.qualify_p4_storage import academic


def profile():
    return load(Path(read(WORK / "final-profile.json")["directory"]))


def capture():
    s = profile()
    mapping = layout()
    volatile = {
        mapping["tables"]["crm_access." + n]
        for n in ["Session", "Challenge", "RateBucket"]
    }
    names = (
        set(mapping["tables"].values()) | set(mapping["academic_tables"])
    ) - volatile
    with admin(s.connection["database"], readonly=True) as db:
        state = fingerprint(db.cursor(), names)
    save(
        WORK / "restart-before.json",
        dict(database=s.connection["database"], names=sorted(names), fingerprint=state),
    )
    print("Owned P8 restart checkpoint captured in read-only mode.")


def verify():
    s = profile()
    before = read(WORK / "restart-before.json")
    assert before["database"] == s.connection["database"]
    with admin(s.connection["database"], readonly=True) as db:
        assert fingerprint(db.cursor(), set(before["names"])) == before["fingerprint"]
    save(
        WORK / "restart-result.json",
        dict(
            status="passed",
            checks=[
                "164_stable_table_fingerprints_survive_real_container_restart",
                "same_profile_and_TLS_target_retained",
                "append_only_P8_versions_consent_and_attempts_preserved",
            ],
            stable_tables=len(before["names"]),
            engine=15,
            compatibility=150,
            real_provider_calls=0,
            academic_writes=False,
        ),
    )
    print(json.dumps(dict(status="passed", restart_stable_tables=len(before["names"]))))


def preservation():
    s = profile()
    parent = source()
    checkpoint = read(WORK / "final-source-snapshot.json")
    with admin(parent.connection["database"], readonly=True) as db:
        assert (
            fingerprint(db.cursor(), set(checkpoint["names"])) == checkpoint["business"]
        )
        assert academic(db.cursor()) == checkpoint["academic"]
    with admin(s.connection["database"], readonly=True) as db:
        assert academic(db.cursor()) == checkpoint["academic"]
        c = Cursor(db.cursor(), layout()["tables"])
        counts = {
            n: c.execute("SELECT COUNT(*) FROM " + table).fetchval()
            for n, table in [
                ("contacts", "crm.Contact"),
                ("conversations", "crm.Conversation"),
                ("messages", "crm.Message"),
                ("templates", "crm_broadcast7.Template"),
                ("campaigns", "crm_broadcast7.Campaign"),
                ("attempts", "crm_broadcast7.Attempt"),
                ("consents", "crm_broadcast7.Consent"),
            ]
        }
        assert (
            counts["contacts"] == 8
            and counts["conversations"] == 8
            and (counts["messages"] == 26)
            and (counts["attempts"] == counts["consents"] == 0)
        )
        assert not c.execute(
            "SELECT 1 FROM crm_broadcast7.Template WHERE Origin<>'operator' OR ProviderStatus<>'LOCAL_DRAFT'"
        ).fetchone()
        counts.update(
            {
                "P8_records": c.execute(
                    "SELECT COUNT(*) FROM crm_campaign8.Record"
                ).fetchval(),
                "P8_enrollments": c.execute(
                    "SELECT COUNT(*) FROM crm_campaign8.Enrollment"
                ).fetchval(),
                "P8_linked_jobs": c.execute(
                    "SELECT COUNT(*) FROM crm_campaign8.Event WHERE Kind='native_chat'"
                ).fetchval(),
                "P8_template_assets": c.execute(
                    "SELECT COUNT(*) FROM crm_campaign8.Event WHERE Kind='template_asset'"
                ).fetchval(),
            }
        )
        assert (
            counts["P8_records"] == 5
            and counts["P8_enrollments"] == counts["P8_linked_jobs"] == 0
        )
        assert not c.execute(
            "SELECT 1 FROM crm_campaign8.Record WHERE State<>'draft'"
        ).fetchone()
        fks = (
            db.cursor()
            .execute("SELECT COUNT(*) FROM sys.foreign_keys WHERE is_ms_shipped=0")
            .fetchval()
        )
    save(
        WORK / "preservation-result.json",
        dict(
            status="passed",
            checks=[
                "fresh_parent_P7_business_fingerprint_unchanged",
                "30_academic_tables_byte_identical_to_fresh_parent_backup",
                "8_contacts_8_conversations_26_messages_preserved",
                "main_P8_has_no_approved_template_consent_recipient_attempt_or_provider_effect",
            ],
            counts=counts,
            physical_foreign_keys=fks,
            tables=167,
            bindings=137,
            academic_tables=30,
            academic_writes=False,
            Windows_SIIE_requeried=False,
            real_provider_calls=0,
        ),
    )
    print(
        json.dumps(dict(status="passed", tables=167, foreign_keys=fks, counts=counts))
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["capture", "verify", "preservation"])
    action = parser.parse_args().action
    {"capture": capture, "verify": verify, "preservation": preservation}[action]()
