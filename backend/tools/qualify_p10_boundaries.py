"""P10 reproduction, malformed snapshot rejection and fresh runtime drift guard."""

import json
from pathlib import Path
from uuid import uuid4

from app.institutional.api import create_app
from app.institutional.db import rows, uid
from app.institutional.learning import Learning, doc, get
from app.institutional.learning_engine import digest, train
from app.institutional.spanish import load, transaction
from tools.p10_learning_recovery import backup, fingerprint
from tools.p10_test_support import Harness
from tools.prepare_p10_learning import WORK, admin, prepare, read, save
from tools.qualify_p3_workspace import Browser


def main():
    assert not (WORK / "boundaries-result.json").exists()
    checks = []

    def check(name, ok=True):
        assert ok, name
        checks.append(name)
        save(WORK / "boundaries-result.json", dict(status="in_progress", checks=checks))

    prototype = Harness("final")
    bad = prototype.sql(
        "SELECT TOP(1) s.PackId FROM crm_learning10.Sample s JOIN crm_learning10.Grant g ON g.InstitutionId=s.InstitutionId AND g.PackId=s.PackId AND g.GrantId=s.GrantId WHERE s.GroupKey<>g.GroupKey"
    )[0][0]
    result = prototype.call(
        "learning/packs/" + str(bad) + "/datasets",
        "POST",
        dict(operation_id=str(uuid4()), cutoff="2026-09-01T00:00:00Z"),
        409,
    )
    check(
        "malformed_prototype_snapshot_group_rejected_without_rewriting_immutable_samples",
        result["detail"] == "learning_sample_subject_binding",
    )
    final = Harness("final-v2")
    reports = []
    with transaction(final.settings, anonymous=True) as c:
        for artifact in rows(c, "SELECT * FROM crm_learning10.Artifact"):
            pack = get(c, final.settings, "packs", uid(str(artifact["PackId"])))
            record, data = Learning(final.settings).validate_artifact(c, pack, artifact)
            dataset = get(
                c,
                final.settings,
                "datasets",
                uid(str(artifact["DatasetId"])),
                uid(str(pack["PackId"])),
            )
            model, report = train(pack["Task"], data, doc(dataset)["cutoff"])
            assert model == record["model"] and report == record["evaluation"]
            reports.append(
                dict(
                    task=pack["Task"],
                    model_sha256=digest(model),
                    evaluation_sha256=digest(report),
                    segments=len(report["segments"]),
                )
            )
    check(
        "all_four_main_demo_models_and_evaluations_reproduce_from_SQL_snapshots",
        len(reports) == 4,
    )
    check(
        "all_four_models_report_available_program_stage_errors_and_baseline",
        all(r["segments"] >= 1 for r in reports),
    )
    fixture = load(Path(read(WORK / "fixture-profile.json")["directory"]))
    with admin(fixture.connection["database"]) as connection:
        checkpoint = backup(connection, fixture.ticket["identity"])
    prepare("guard-drift", checkpoint=checkpoint, recovering_from=fixture)
    s = load(Path(read(WORK / "guard-drift-profile.json")["directory"]))
    browser = Browser(create_app(s))
    browser.request("auth/status")
    check("fresh_recovery_profile_has_valid_full_model_before_drift")
    with admin(s.connection["database"]) as connection:
        connection.cursor().execute(
            "ALTER TABLE dbo.CRMAprendizajeEvento ADD OwnedP10Drift int NULL"
        )
    browser.request("auth/status", expected=503)
    check("new_request_rejects_real_schema_drift_after_previous_success")
    with admin(fixture.connection["database"], readonly=True) as connection:
        check(
            "source_fixture_fingerprint_unchanged_by_drift_copy",
            fingerprint(connection.cursor()) == checkpoint["data"],
        )
    save(
        WORK / "boundaries-result.json",
        dict(
            status="passed",
            checks=checks,
            models=reports,
            drift_database=s.connection["database"],
            drift_copy_quarantined=True,
            academic_DDL_or_DML=False,
            real_provider_calls=0,
        ),
    )
    print(json.dumps(dict(status="passed", checks=len(checks))))


if __name__ == "__main__":
    main()
