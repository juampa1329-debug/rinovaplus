"""SQL+private media restoration receipt, separate from online commissioning."""

import json
import os
import time
from pathlib import Path

from app.institutional import operations_policy as policy
from app.institutional.operations import inspect_receipt, sign_receipt
from app.institutional.spanish import load, transaction
from app.institutional.spanish_bindings import Cursor
from tools.p11_operations_recovery import backup, copy_media, fingerprint
from tools.prepare_p11_operations import WORK, admin, prepare, read, save
from tools.qualify_p4_deployment import fingerprint as selected_fingerprint
from tools.rehearse_foundation import execute_results


def recover(source_label="fixture", label="recovery", media_root=None):
    assert not (WORK / (label + "-result.json")).exists(), (
        "fresh recovery qualification required"
    )
    started = time.monotonic()
    source = load(Path(read(WORK / (source_label + "-profile.json"))["directory"]))
    assert source.ticket["version"] == policy.VERSION
    mapping = policy.layout()
    volatile = {
        "crm_access." + n for n in ["Session", "Challenge", "RecoveryCode", "Factor"]
    } | {
        "crm_channels2.OAuthSession",
        "crm_agents5.Request",
        "crm_channels2.SendJob",
        "crm_channels2.ProviderOperation",
        "crm_broadcast7.Campaign",
        "crm_broadcast7.Recipient",
        "crm_campaign8.Record",
        "crm_campaign8.Enrollment",
        "crm_ads9.Account",
        "crm_learning10.Deployment",
    }
    stable = (set(mapping["tables"].values()) | set(mapping["academic_tables"])) - {
        mapping["tables"][v] for v in volatile
    }
    with transaction(source, anonymous=True):
        pass
    with admin(source.connection["database"]) as connection:
        before = selected_fingerprint(connection.cursor(), stable)
        checkpoint = backup(connection, source.ticket["identity"])
    access = read(WORK / (source_label + "-access.json"))
    prepare(label, checkpoint=checkpoint, recovering_from=source, access=access)
    recovered = load(Path(read(WORK / (label + "-profile.json"))["directory"]))
    destination = WORK / (label + "-media")
    with admin(recovered.connection["database"]) as connection:
        c = connection.cursor()
        if execute_results(c, "DBCC CHECKDB WITH NO_INFOMSGS, ALL_ERRORMSGS"):
            raise ValueError("P11ES_CHECKDB_errors")
        after = selected_fingerprint(c, stable)
        assert before == after, "P11ES_stable_business_or_academic_data_changed"
        media = copy_media(
            c,
            (Path(media_root) if media_root else WORK / "parent-media") / "inbox-media",
            destination / "inbox-media",
        )
        mapped = Cursor(c, mapping["tables"])
        assert not mapped.execute(
            "SELECT 1 FROM crm_access.Session WHERE RevokedAt IS NULL"
        ).fetchone()
        assert not mapped.execute(
            "SELECT 1 FROM crm_learning10.Deployment WHERE State<>'paused'"
        ).fetchone()
        assert not mapped.execute(
            "SELECT 1 FROM crm_channels2.SendJob WHERE State IN('queued','sending')"
        ).fetchone()
        assert not mapped.execute(
            "SELECT 1 FROM crm_campaign8.Record WHERE Kind IN('campaign','flow','trigger') AND State='active'"
        ).fetchone()
    with transaction(recovered, anonymous=True):
        pass
    with admin(source.connection["database"], readonly=True) as connection:
        assert fingerprint(connection.cursor()) == checkpoint["data"]
    # Check private files through the same SQL-bound readers used by the product.
    os.environ["CRM_AI_STATE_DIR"] = str(destination)
    from app.institutional.broadcast_dispatch import Worker as Bulk
    from app.institutional.campaign_assets import library_file
    from app.institutional.campaign_runtime import Worker as Flow
    from app.institutional.channel_media import file_for
    from app.institutional.channel_outbox import Dispatcher

    calls = []
    with transaction(recovered, anonymous=True) as c:
        for row in c.execute(
            "SELECT EventId FROM crm_campaign8.Event WHERE Kind='template_asset'"
        ).fetchall():
            library_file(c, recovered, str(row[0]))
        for row in c.execute(
            "SELECT MediaId FROM crm_channels4.MediaAsset WHERE State='ready'"
        ).fetchall():
            file_for(c, recovered, str(row[0]))
    assert not Flow(recovered).refresh() and not Flow(recovered).once()
    assert not Bulk(recovered, controlled=True).once()
    assert not Dispatcher(
        recovered, transport=lambda *a, **kw: calls.append(True), allow_controlled=True
    ).once()
    assert not calls
    receipt = sign_receipt(
        source,
        backup_uuid=checkpoint["backup_uuid"],
        ready_blobs=len(media),
        restored_database=recovered.connection["database"],
    )
    assert inspect_receipt(source, receipt)["state"] == "verified"
    assert inspect_receipt(recovered, receipt)["state"] == "invalid"
    save(WORK / (source_label + "-verified-receipt.json"), receipt)
    report = {
        "status": "passed",
        "source": source.connection["database"],
        "restored": recovered.connection["database"],
        "stable_tables": len(stable),
        "stable_fingerprint": after,
        "ready_blobs": len(media),
        "media_manifest": media,
        "elapsed_local_seconds": round(time.monotonic() - started, 2),
        "checks": [
            "COPY_ONLY_CHECKSUM_VERIFYONLY_native_restore_full_185_table_bytes",
            "CHECKDB_no_errors",
            "stable_business_configuration_journals_models_and_30_academic_tables_equal",
            "all_Access_C10_Ads_secret_versions_authenticated",
            "copied_sessions_OAuth_authority_and_producers_quarantined",
            "closed_profile_TLS_catalog_journals_ACL_revalidated",
            "private_SQL_bound_media_readers_validate_restored_bytes",
            "source_all_185_tables_unchanged_by_recovery",
            "restored_consumers_do_not_emit_or_reenqueue",
            "signed_receipt_binds_source_profile_and_rejects_restored_identity",
        ],
        "provider_calls": 0,
        "academic_writes": False,
        "institutional_RPO_RTO_accepted": False,
    }
    save(WORK / (label + "-result.json"), report)
    print(
        json.dumps(
            {
                k: report[k]
                for k in [
                    "status",
                    "stable_tables",
                    "ready_blobs",
                    "elapsed_local_seconds",
                ]
            }
        )
    )


if __name__ == "__main__":
    recover()
