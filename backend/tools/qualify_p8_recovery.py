"""Read and exercise the already restored P8 recovery, including real ready blobs."""

import json, os
from pathlib import Path
from app.institutional.spanish import load
from app.institutional.store import transaction
from app.institutional.campaign_runtime import Worker
from app.institutional.channel_outbox import Dispatcher
from app.institutional.broadcast_dispatch import Worker as Bulk
from app.institutional.channel_media import file_for
from tools.p8_campaign_recovery import copy_media
from app.institutional.campaign_assets import library_file
from tools.prepare_p8_campaign import WORK, admin, read, save
from app.institutional.spanish_bindings import Cursor


def main():
    label = os.environ.get("P8_RECOVERY_LABEL", "populated-recovery-v2")
    restored = load(Path(read(WORK / (label + "-profile.json"))["directory"]))
    source = load(Path(read(WORK / "runtime-r2-profile.json")["directory"]))
    report = read(WORK / "recovery-result.json")
    assert len(report["checks"]) == 5
    report["checks"][0] = (
        str(report["stable_tables"])
        + "_stable_tables_preserve_configuration_memory_vault_and_append_only_P8_history"
    )

    def uncertain(s):
        with admin(s.connection["database"], readonly=True) as db:
            c = Cursor(db.cursor(), s.ticket["table_map"])
            return sorted(
                str(v[0]).lower()
                for v in c.execute(
                    "SELECT QueueId FROM crm_channels2.SendJob WHERE State='uncertain'"
                ).fetchall()
            )

    expected = uncertain(source)
    assert len(expected) >= 1 and uncertain(restored) == expected
    report["checks"].append(
        "uncertain_native_queue_ids_preserved_exactly_in_restored_copy"
    )
    with transaction(restored, anonymous=True) as c:
        assert (
            c.execute(
                "SELECT COUNT(*) FROM crm_channels2.SendJob WHERE State IN('queued','sending')"
            ).fetchval()
            == 0
        )
        assert (
            c.execute(
                "SELECT COUNT(*) FROM crm_campaign8.Record WHERE Kind IN('flow','trigger','campaign') AND State='active'"
            ).fetchval()
            == 0
        )
        assert (
            c.execute(
                "SELECT COUNT(*) FROM crm_campaign8.Enrollment WHERE State IN('waiting','queued')"
            ).fetchval()
            == 0
        )
    report["checks"].append(
        "restored_approvals_retired_and_pending_flows_require_new_review"
    )
    destination = WORK / (label + "-media")
    os.environ["CRM_AI_STATE_DIR"] = str(destination)
    with transaction(restored, anonymous=True) as c:
        manifest = copy_media(
            c.physical,
            WORK / "runtime-r2-media/inbox-media",
            destination / "inbox-media",
        )
        assert len(manifest) >= 11
        for row in c.execute(
            "SELECT MediaId FROM crm_channels4.MediaAsset WHERE State='ready'"
        ).fetchall():
            file_for(c, restored, str(row[0]))
        library = c.execute("SELECT EventId FROM crm_campaign8.Event WHERE Kind='template_asset'").fetchall()
        assert len(library) >= 4
        for row in library:
            library_file(c, restored, str(row[0]))
    report["checks"].append(
        "native_media_and_global_template_library_copied_and_revalidated_in_separate_root"
    )
    calls = []
    assert not Worker(restored).refresh()
    assert not Worker(restored).once()
    assert not Bulk(restored, controlled=True).once()
    assert not Dispatcher(
        restored, transport=lambda *a, **kw: calls.append(True), allow_controlled=True
    ).once()
    assert not calls and uncertain(restored) == expected
    report["checks"].append(
        "fresh_recovered_consumers_neither_POST_nor_requeue_uncertain_effects"
    )
    report.update(
        status="passed",
        uncertain_jobs_preserved=len(expected),
        ready_blobs_copied=len(manifest),
        media_manifest=manifest,
        real_provider_calls=0,
    )
    save(WORK / "recovery-result.json", report)
    print(
        json.dumps(
            dict(
                status="passed", checks=len(report["checks"]), ready_blobs=len(manifest)
            )
        )
    )


if __name__ == "__main__":
    main()
