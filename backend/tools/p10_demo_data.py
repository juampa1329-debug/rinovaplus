"""Explicit synthetic numeric fixture. Never claims institutional effectiveness."""

from uuid import uuid4

from app.institutional.db import institution
from app.institutional.learning import group_key, packed
from app.institutional.learning_engine import FEATURES, digest
from app.institutional.learning_models import PURPOSE
from app.institutional.spanish_bindings import Cursor
from tools.prepare_p10_learning import admin


def seed(h, pack, task, actor, *, program="general", stage="demo_new", variant=0):
    # Intended only for a just-created demo pack on an explicit own new copy.
    assert h.settings.connection["database"].startswith("CBN_P10ES_TRIAL_20261028_")
    assert not h.sql(
        "SELECT SampleId FROM crm_learning10.Sample WHERE InstitutionId=? AND PackId=?",
        institution(h.settings),
        pack,
    )
    version = h.sql(
        "SELECT TOP(1) VersionId FROM crm_learning10.PackVersion WHERE InstitutionId=? AND PackId=? ORDER BY VersionNo DESC",
        institution(h.settings),
        pack,
    )[0][0]
    result = []
    with admin(h.settings.connection["database"]) as connection:
        c = Cursor(connection.cursor(), h.settings.ticket["table_map"])
        c.execute("SET XACT_ABORT ON;BEGIN TRANSACTION")
        try:
            assert (
                c.execute(
                    "SELECT Scope FROM crm_learning10.Pack WHERE InstitutionId=? AND PackId=?",
                    institution(h.settings),
                    pack,
                ).fetchval()
                == "demo"
            )
            for i in range(64):
                segment_program = (
                    str(program[(i // 2) % len(program)])
                    if isinstance(program, (list, tuple))
                    else program
                )
                subject = str(uuid4())
                grant = str(uuid4())
                sample = str(uuid4())
                label = i % 2
                future = i >= 48
                key = group_key(h.settings, pack, None, subject)
                gd = dict(
                    basis="synthetic_demo",
                    reference="CBN-DEMO-P10",
                    synthetic_demo=True,
                    purpose=PURPOSE[task],
                    demo_subject=subject,
                    subject_id=None,
                )
                c.execute(
                    "INSERT crm_learning10.Grant(InstitutionId,GrantId,PackId,GroupKey,SubjectId,Purpose,State,Revision,Document,ActorId) VALUES(?,?,?,?,NULL,?,'active',1,?,?)",
                    institution(h.settings),
                    grant,
                    pack,
                    key,
                    PURPOSE[task],
                    packed(gd),
                    actor,
                )
                values = {
                    k: float(label * 80 + 10 + (i % 3) + variant)
                    for k in FEATURES[task]
                }
                for feature_name in {
                    "negative_sentiment_ratio",
                    "event_failure_rate",
                } & values.keys():
                    values[feature_name] = 0.1 + 0.8 * label
                if "asked_for_price" in values:
                    values["asked_for_price"] = float(label)
                if "best_hour" in values:
                    values["best_hour"] = float(8 + 12 * label)
                feature = "2026-09-02T00:00:00Z" if future else "2026-08-01T00:00:00Z"
                outcome = "2026-09-03T00:00:00Z" if future else "2026-08-02T00:00:00Z"
                d = dict(
                    features=values,
                    observation="synthetic_demo",
                    source_kind="demo",
                    source_id=None,
                    feature_at=feature,
                    outcome_at=outcome,
                    label=label,
                    program=segment_program,
                    stage=stage,
                    synthetic_demo=True,
                )
                c.execute(
                    "INSERT crm_learning10.Sample(InstitutionId,SampleId,PackId,GrantId,VersionId,GroupKey,SourceKind,ProgramKey,StageKey,FeatureAt,OutcomeAt,Label,DocumentHash,Document,ActorId) VALUES(?,?,?,?,?,?,'demo',?,?,?,?,?,?,?,?)",
                    institution(h.settings),
                    sample,
                    pack,
                    grant,
                    str(version),
                    key,
                    segment_program,
                    stage,
                    feature.replace("Z", ""),
                    outcome.replace("Z", ""),
                    label,
                    digest(d),
                    packed(d),
                    actor,
                )
                result.append(
                    dict(
                        grant_id=grant,
                        sample_id=sample,
                        demo_subject=subject,
                        features=values,
                    )
                )
            c.execute("COMMIT")
        except BaseException:
            c.execute("IF @@TRANCOUNT>0 ROLLBACK")
            raise
    return result
