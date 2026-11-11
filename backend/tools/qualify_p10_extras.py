"""P10 native negative boundaries, correction provenance and reviewed data sources."""

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.institutional.db import institution
from tools.p10_demo_data import seed
from tools.p10_test_support import Harness
from tools.prepare_p10_learning import WORK, save


def security(h, check):
    import secrets

    from tools.qualify_p3_workspace import Browser

    email = "p10-viewer-" + uuid4().hex[:10] + "@example.invalid"
    password = "CBN!" + secrets.token_urlsafe(32)
    h.call(
        "users",
        "POST",
        dict(
            operation_id=str(uuid4()),
            email=email,
            full_name="Consulta controlada P10",
            password=password,
            role="viewer",
        ),
    )
    viewer = Browser(h.app)
    viewer.login(email, password)
    viewer.request("learning/packs", expected=403)
    check("viewer_cannot_read_or_manage_training")
    viewer.request("auth/logout", "POST", {})
    old = h.call("settings/modules")
    document = old["document"]
    document["enabled"]["intelligence"] = False
    h.call(
        "settings/modules",
        "PUT",
        dict(operation_id=str(uuid4()), revision=old["revision"], document=document),
    )
    try:
        h.call("learning/packs", expected=403)
        check("module_disable_blocks_learning_API")
    finally:
        document["enabled"]["intelligence"] = True
        h.call(
            "settings/modules",
            "PUT",
            dict(
                operation_id=str(uuid4()),
                revision=old["revision"] + 1,
                document=document,
            ),
        )


def resume_security():
    from tools.prepare_p10_learning import read

    report = read(WORK / "extras-result.json")
    assert (
        report["status"] == "in_progress"
        and report["checks"][-1]
        == "revocation_blocks_new_samples_without_deleting_old_review"
    )
    h = Harness()
    checks = report["checks"]

    def check(name, ok=True):
        assert ok, name
        checks.append(name)
        save(WORK / "extras-result.json", dict(status="in_progress", checks=checks))

    security(h, check)
    check(
        "no_provider_IO_or_raw_content_export",
        not h.gateway.posts and not h.gateway.gets,
    )
    save(
        WORK / "extras-result.json",
        dict(
            status="passed",
            checks=checks,
            real_provider_calls=0,
            academic_DDL_or_DML=False,
            continuation="completed initial reviewed-data checks, then replaced invalid last-owner test setup with separate viewer account",
        ),
    )
    print(json.dumps(dict(status="passed", checks=len(checks))))


def main():
    assert not (WORK / "extras-result.json").exists(), "fresh qualification only"
    h = Harness()
    checks = []

    def check(name, ok=True):
        assert ok, name
        checks.append(name)
        save(WORK / "extras-result.json", dict(status="in_progress", checks=checks))

    def cmd(**v):
        return dict(operation_id=str(uuid4()), **v)

    actor = h.call("auth/me")["user"]["id"]
    catalog = h.call("learning/catalog")
    check(
        "CRM_contexts_and_programs_are_read_from_own_copy",
        len(catalog["contexts"]) >= 11,
    )
    made = h.call(
        "learning/packs",
        "POST",
        cmd(
            revision=0,
            document=dict(
                name="Calificación de correcciones", task="lead_scoring", scope="demo"
            ),
        ),
    )
    pack = made["id"]
    base = "learning/packs/" + pack
    data = seed(h, pack, "lead_scoring", actor)
    dataset = h.call(base + "/datasets", "POST", cmd(cutoff="2026-09-01T00:00:00Z"))
    fitbody = cmd(dataset_id=dataset["id"])
    artifact = h.call(base + "/train", "POST", fitbody)
    version = h.call(base)["pack"]
    h.call(
        base,
        "PATCH",
        cmd(
            revision=version["revision"],
            document=dict(version["document"], training_enabled=False),
        ),
    )
    check(
        "lost_training_ack_replays_after_training_paused",
        h.call(base + "/train", "POST", fitbody) == artifact,
    )
    h.call(base + "/train", "POST", cmd(dataset_id=dataset["id"]), 409)
    check("new_training_pauses_without_losing_evidence")
    sample = data[2]
    corrected = h.call(
        base + "/samples",
        "POST",
        cmd(
            grant_id=sample["grant_id"],
            source_kind="demo",
            stage="demo_new",
            feature_at="2026-08-01T00:00:00Z",
            outcome_at="2026-08-03T00:00:00Z",
            features=sample["features"],
            label=0,
            supersedes=sample["sample_id"],
        ),
    )
    check(
        "human_correction_appends_sample_and_retains_original",
        len(
            h.sql(
                "SELECT SampleId FROM crm_learning10.Sample WHERE InstitutionId=? AND PackId=?",
                institution(h.settings),
                pack,
            )
        )
        == 65,
    )
    h.call(
        base + "/samples",
        "POST",
        cmd(
            grant_id=sample["grant_id"],
            source_kind="demo",
            stage="demo_new",
            feature_at="2026-08-01T00:00:00Z",
            outcome_at="2026-08-03T00:00:00Z",
            features=sample["features"],
            label=1,
            supersedes=sample["sample_id"],
        ),
        409,
    )
    check("correction_fork_is_rejected")
    selected = h.call(base)["deployment"]
    h.call(
        base + "/selection",
        "POST",
        cmd(revision=selected["revision"], action="shadow", artifact_id=artifact["id"]),
        409,
    )
    check("corrected_frozen_dataset_blocks_old_model_selection")
    foreign = h.call(
        "learning/packs",
        "POST",
        cmd(
            revision=0,
            document=dict(
                name="Otro pack aislado", task="churn_prediction", scope="demo"
            ),
        ),
    )
    h.call(
        "learning/packs/" + foreign["id"] + "/train",
        "POST",
        cmd(dataset_id=dataset["id"]),
        404,
    )
    check("cross_pack_dataset_reference_denied")
    native = h.call(
        "learning/packs",
        "POST",
        cmd(
            revision=0,
            document=dict(
                name="Finalidad institucional", task="lead_scoring", scope="native"
            ),
        ),
    )
    nb = "learning/packs/" + native["id"]
    ctx = catalog["contexts"][0]
    h.call(
        nb + "/grants",
        "POST",
        cmd(
            revision=0,
            subject_id=ctx["subject_id"],
            approved=True,
            basis="synthetic_demo",
            reference="QA-REF",
        ),
        422,
    )
    check("synthetic_authority_cannot_authorize_native_data")
    grant = h.call(
        nb + "/grants",
        "POST",
        cmd(
            revision=0,
            subject_id=ctx["subject_id"],
            approved=True,
            basis="institutional_authorization",
            reference="QA-ACTA-2026",
        ),
    )
    now = datetime.now(timezone.utc)
    feature = (now - timedelta(seconds=30)).isoformat()
    outcome = (now - timedelta(seconds=15)).isoformat()
    stage = catalog["stages"][0]["id"]
    reviewed = cmd(
        grant_id=grant["id"],
        source_kind="conversation",
        source_id=ctx["conversation_id"],
        stage=stage,
        feature_at=feature,
        outcome_at=outcome,
        features=data[0]["features"],
        label=1,
    )
    saved = h.call(nb + "/samples", "POST", reviewed)
    check(
        "native_human_structured_observation_bound_to_CRM_source", bool(saved["hash"])
    )
    bad = dict(
        reviewed,
        operation_id=str(uuid4()),
        features={**data[0]["features"], "transcript": "private"},
    )
    h.call(nb + "/samples", "POST", bad, 422)
    check("raw_text_and_label_feature_injection_rejected")
    mismatch = next(
        v for v in catalog["contexts"] if v["subject_id"] != ctx["subject_id"]
    )
    h.call(
        nb + "/samples",
        "POST",
        dict(
            reviewed, operation_id=str(uuid4()), source_id=mismatch["conversation_id"]
        ),
        404,
    )
    check("source_must_belong_to_authorized_subject")
    h.call(
        nb + "/grants",
        "POST",
        cmd(
            revision=1,
            subject_id=ctx["subject_id"],
            approved=False,
            basis="institutional_authorization",
            reference="QA-ACTA-REVOKED",
        ),
    )
    h.call(nb + "/samples", "POST", dict(reviewed, operation_id=str(uuid4())), 409)
    check("revocation_blocks_new_samples_without_deleting_old_review")
    security(h, check)
    check(
        "no_provider_IO_or_raw_content_export",
        not h.gateway.posts and not h.gateway.gets,
    )
    save(
        WORK / "extras-result.json",
        dict(
            status="passed",
            checks=checks,
            real_provider_calls=0,
            academic_DDL_or_DML=False,
            corrected_sample_id=corrected["id"],
        ),
    )
    print(json.dumps({"status": "passed", "checks": len(checks)}))


if __name__ == "__main__":
    import sys

    resume_security() if "--resume-security" in sys.argv else main()
