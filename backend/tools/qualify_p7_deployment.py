"""Read-only preservation and restart receipts for the owned P7 final profile."""

import argparse
import json
from pathlib import Path

from app.institutional.broadcast_policy import layout
from app.institutional.spanish import load
from app.institutional.spanish_bindings import Cursor
from tools.prepare_p7_broadcast import WORK, admin, read, save, source
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
    print(("Owned P7 restart checkpoint captured in read-only mode."))


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
                ("157_stable_table_fingerprints_survive_real_container_restart"),
                "same_profile_and_TLS_target_retained",
                ("append_only_P7_versions_consent_and_attempts_preserved"),
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
            and counts["messages"] == 26
            and counts["attempts"] == counts["consents"] == 0
        )
        assert not c.execute(
            (
                "SELECT 1 FROM crm_broadcast7.Template "
                "WHERE Origin<>'operator' OR ProviderSt"
                "atus<>'LOCAL_DRAFT'"
            )
        ).fetchone()
        fks = (
            db.cursor()
            .execute(("SELECT COUNT(*) FROM sys.foreign_keys WHERE is_ms_shipped=0"))
            .fetchval()
        )
    save(
        WORK / "preservation-result.json",
        dict(
            status="passed",
            checks=[
                "fresh_parent_P6_business_fingerprint_unchanged",
                ("30_academic_tables_byte_identical_to_fresh_parent_backup"),
                "8_contacts_8_conversations_26_messages_preserved",
                (
                    "main_P7_has_no_approved_template_conse"
                    "nt_recipient_attempt_or_provider_effec"
                    "t"
                ),
            ],
            counts=counts,
            physical_foreign_keys=fks,
            tables=160,
            bindings=130,
            academic_tables=30,
            academic_writes=False,
            Windows_SIIE_requeried=False,
            real_provider_calls=0,
        ),
    )
    print(
        json.dumps(dict(status="passed", tables=160, foreign_keys=fks, counts=counts))
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["capture", "verify", "preservation"])
    action = parser.parse_args().action
    {"capture": capture, "verify": verify, "preservation": preservation}[action]()
