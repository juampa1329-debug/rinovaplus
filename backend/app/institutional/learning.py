"""Institution-scoped learning lifecycle. Immutable evidence, explicit human gates."""

import json
from contextlib import contextmanager
from datetime import timezone
from uuid import uuid4

from fastapi import HTTPException

from app.institutional.auth import authorize
from app.institutional.crypto import canonical
from app.institutional.db import (
    institution,
    one,
    record_operation,
    replay,
    rows,
    uid,
    utc,
)
from app.institutional.learning_engine import (
    ALGORITHM,
    FEATURES,
    digest,
    drift,
    features,
    score,
    split,
    train,
)
from app.institutional.learning_models import PURPOSE
from app.institutional.store import transaction
from app.institutional.workspace import primary, read_contact

TABLES = {
    "packs": ("Pack", "PackId"),
    "versions": ("PackVersion", "VersionId"),
    "grants": ("Grant", "GrantId"),
    "samples": ("Sample", "SampleId"),
    "datasets": ("Dataset", "DatasetId"),
    "artifacts": ("Artifact", "ArtifactId"),
    "predictions": ("Prediction", "PredictionId"),
    "events": ("Event", "EventId"),
}


def packed(v):
    return canonical(v).decode()


def doc(row):
    value = json.loads(row["Document"])
    if row.get("DocumentHash") and digest(value) != row["DocumentHash"]:
        raise HTTPException(409, "learning_evidence_integrity")
    return value


def get(c, s, kind, id, pack=None):
    table, col = TABLES[kind]
    row = one(
        c,
        "SELECT * FROM crm_learning10."
        + table
        + " WHERE InstitutionId=? AND "
        + col
        + "=?",
        institution(s),
        id,
    )
    if not row or pack is not None and uid(str(row["PackId"])) != pack:
        raise HTTPException(404, "learning_record_not_found")
    doc(row)
    return row


def public(kind, row):
    table, id = TABLES[kind]
    result = {
        "id": uid(str(row[id])),
        "document": doc(row),
        "created_at": utc(row["CreatedAt"]),
    }
    for col, key in [
        ("PackId", "pack_id"),
        ("Revision", "revision"),
        ("State", "state"),
        ("Scope", "scope"),
        ("Task", "task"),
        ("VersionNo", "version"),
        ("DocumentHash", "hash"),
        ("Kind", "kind"),
        ("Mode", "mode"),
    ]:
        if col in row:
            result[key] = str(row[col]).lower() if col.endswith("Id") else row[col]
    if "TrainEnabled" in row:
        result["training_enabled"] = bool(row["TrainEnabled"])
    if "FeatureAt" in row:
        result.update(
            feature_at=utc(row["FeatureAt"]),
            outcome_at=utc(row["OutcomeAt"]),
            label=int(row["Label"]),
            grant_id=uid(str(row["GrantId"])),
        )
    return result


def event(c, s, actor, pack, kind, value):
    c.execute(
        "INSERT crm_learning10.Event(InstitutionId,EventId,PackId,Kind,Document,ActorId) VALUES(?,?,?,?,?,?)",
        institution(s),
        str(uuid4()),
        pack,
        kind,
        packed(value),
        actor["UserId"],
    )


def group_key(s, pack, subject, demo=None):
    return digest([institution(s), pack, "demo" if demo else "native", demo or subject])


def grant_binding(c, s, pack, g):
    if g["State"] != "active" or g["Purpose"] != PURPOSE[pack["Task"]]:
        raise HTTPException(409, "learning_purpose_authorization_required")
    d = doc(g)
    if pack["Scope"] == "native":
        subject = uid(str(g["SubjectId"]))
        if (
            primary(c, subject) != subject
            or group_key(s, uid(str(pack["PackId"])), subject) != g["GroupKey"]
        ):
            raise HTTPException(409, "learning_subject_changed_rebuild_required")
    elif not d.get("synthetic_demo") or g["SubjectId"] is not None:
        raise HTTPException(409, "learning_demo_scope_required")
    return digest(
        [str(g["GrantId"]), g["Revision"], g["State"], g["Purpose"], g["GroupKey"]]
    )


def latest_version(c, s, pack):
    row = one(
        c,
        "SELECT TOP(1) * FROM crm_learning10.PackVersion WHERE InstitutionId=? AND PackId=? ORDER BY VersionNo DESC",
        institution(s),
        pack,
    )
    if not row:
        raise HTTPException(409, "learning_pack_version_required")
    doc(row)
    return row


def samples(c, s, pack, dataset=None):
    id = uid(str(pack["PackId"]))
    raw = rows(
        c,
        "SELECT TOP(1001) * FROM crm_learning10.Sample WHERE InstitutionId=? AND PackId=? ORDER BY CreatedAt,SampleId",
        institution(s),
        id,
    )
    if len(raw) > 1000:
        raise HTTPException(409, "learning_pack_sample_limit")
    wanted = None if dataset is None else doc(dataset)["samples"]
    superseded = {uid(str(v["Supersedes"])) for v in raw if v["Supersedes"] is not None}
    grants = {
        uid(str(v["GrantId"])): v
        for v in rows(
            c,
            "SELECT * FROM crm_learning10.Grant WHERE InstitutionId=? AND PackId=?",
            institution(s),
            id,
        )
    }
    output = []
    for row in raw:
        sample = uid(str(row["SampleId"]))
        if wanted is not None and sample not in wanted:
            continue
        if sample in superseded:
            if wanted is not None:
                raise HTTPException(409, "learning_dataset_corrected_rebuild_required")
            continue
        g = grants[uid(str(row["GrantId"]))]
        if row["GroupKey"] != g["GroupKey"]:
            raise HTTPException(409, "learning_sample_subject_binding")
        if wanted is None and g["State"] != "active":
            continue
        binding = grant_binding(c, s, pack, g)
        d = doc(row)
        if wanted is not None and wanted[sample] != digest(
            [row["DocumentHash"], binding]
        ):
            raise HTTPException(409, "learning_authorization_changed_rebuild_required")
        output.append(
            dict(
                id=sample,
                group=row["GroupKey"],
                grant_id=uid(str(row["GrantId"])),
                grant_binding=binding,
                sample_hash=row["DocumentHash"],
                feature_at=utc(row["FeatureAt"]),
                outcome_at=utc(row["OutcomeAt"]),
                features=d["features"],
                label=int(row["Label"]),
                program=row["ProgramKey"],
                stage=row["StageKey"],
            )
        )
    if wanted is not None and len(output) != len(wanted):
        raise HTTPException(409, "learning_dataset_evidence_missing")
    return output


def deployment(c, s, pack):
    row = one(
        c,
        "SELECT * FROM crm_learning10.Deployment WHERE InstitutionId=? AND PackId=?",
        institution(s),
        pack,
    )
    if not row:
        raise HTTPException(409, "learning_deployment_required")
    return row


def deployed_public(row):
    return dict(
        revision=row["Revision"],
        state=row["State"],
        active_id=uid(str(row["ActiveId"])) if row["ActiveId"] else None,
        shadow_id=uid(str(row["ShadowId"])) if row["ShadowId"] else None,
        document=doc(row),
    )


class Learning:
    def __init__(self, settings):
        self.settings = settings

    @contextmanager
    def access(self, authority, write=False, recent=False):
        with transaction(self.settings, write, anonymous=True) as c:
            actor = authorize(
                c, self.settings, authority, "agents.manage", recent=recent
            )
            authorize(c, self.settings, authority, "crm.read")
            yield c, actor

    def mutate(self, authority, body, action, resource, fn, recent=False):
        with self.access(authority, True, recent) as (c, actor):
            h, prior = replay(
                c,
                self.settings,
                actor["UserId"],
                str(body.operation_id),
                "learning." + action,
                resource,
                body.model_dump(mode="json"),
            )
            if prior:
                return prior
            result = fn(c, actor)
            record_operation(
                c,
                self.settings,
                actor["UserId"],
                str(body.operation_id),
                "learning." + action,
                resource,
                h,
                result,
            )
            return result

    def catalog(self, authority):
        with self.access(authority) as (c, _):
            programs = [
                {"id": int(v["ProgramId"]), "name": v["Name"]}
                for v in rows(
                    c,
                    "SELECT ProgramId,Name FROM crm_agents5.Program WHERE InstitutionId=? AND Active=1",
                    institution(self.settings),
                )
            ]
            from app.modules.crm_configuration.application.service import (
                read_configuration,
            )

            config, _ = read_configuration(c, foundation=True)
            stages = [{"id": v.key, "name": v.label} for v in config.stages if v.active]
            contexts = [
                {
                    "conversation_id": uid(str(v["ConversationId"])),
                    "subject_id": primary(c, uid(str(v["ContactId"]))),
                    "label": v["Name"],
                }
                for v in rows(
                    c,
                    "SELECT TOP(200) v.ConversationId,v.ContactId,c.Name FROM crm.Conversation v JOIN crm.Contact c ON c.ContactId=v.ContactId ORDER BY v.CreatedAt DESC,v.ConversationId",
                )
            ]
            campaigns = [
                {"id": uid(str(v["RecordId"])), "label": v["Name"]}
                for v in rows(
                    c,
                    "SELECT TOP(200) RecordId,Name FROM crm_campaign8.Record WHERE InstitutionId=? AND Kind='campaign' ORDER BY CreatedAt DESC",
                    institution(self.settings),
                )
            ]
        return dict(
            tasks=[
                dict(id=k, features=v, purpose=PURPOSE[k]) for k, v in FEATURES.items()
            ],
            algorithm=ALGORITHM,
            programs=programs,
            stages=stages,
            contexts=contexts,
            campaigns=campaigns,
            training_scope="institution_only",
            raw_content_used=False,
            automatic_messages=False,
        )

    def listing(self, authority, kind, pack=None, offset=0):
        if kind not in TABLES:
            raise HTTPException(404, "learning_record_not_found")
        table, col = TABLES[kind]
        with self.access(authority) as (c, _):
            clause = "InstitutionId=?"
            params = [institution(self.settings)]
            if kind != "packs":
                if pack is None:
                    raise HTTPException(422, "learning_pack_required")
                get(c, self.settings, "packs", pack)
                clause += " AND PackId=?"
                params.append(pack)
            result = rows(
                c,
                "SELECT * FROM crm_learning10."
                + table
                + " WHERE "
                + clause
                + " ORDER BY CreatedAt DESC,"
                + col
                + " OFFSET ? ROWS FETCH NEXT 51 ROWS ONLY",
                *params,
                offset,
            )
            return dict(
                items=[public(kind, v) for v in result[:50]],
                more=len(result) > 50,
                offset=offset,
            )

    def detail(self, authority, pack):
        with self.access(authority) as (c, _):
            value = get(c, self.settings, "packs", pack)
            return dict(
                pack=public("packs", value),
                deployment=deployed_public(deployment(c, self.settings, pack)),
                version=public("versions", latest_version(c, self.settings, pack)),
            )

    def save_pack(self, authority, body, id=None):
        def perform(c, actor):
            current = get(c, self.settings, "packs", id) if id else None
            if body.revision != (current["Revision"] if current else 0):
                raise HTTPException(409, "revision_conflict")
            d = body.document.model_dump(mode="json")
            p = id or str(uuid4())
            if current and (
                current["Task"] != d["task"] or current["Scope"] != d["scope"]
            ):
                raise HTTPException(409, "learning_pack_identity_immutable")
            revision = body.revision + 1
            if current:
                c.execute(
                    "UPDATE crm_learning10.Pack SET Revision=?,TrainEnabled=?,Document=?,ActorId=? WHERE InstitutionId=? AND PackId=? AND Revision=?",
                    revision,
                    d["training_enabled"],
                    packed(d),
                    actor["UserId"],
                    institution(self.settings),
                    p,
                    body.revision,
                )
            else:
                c.execute(
                    "INSERT crm_learning10.Pack(InstitutionId,PackId,Task,Scope,Revision,TrainEnabled,Document,ActorId) VALUES(?,?,?,?,?,?,?,?)",
                    institution(self.settings),
                    p,
                    d["task"],
                    d["scope"],
                    revision,
                    d["training_enabled"],
                    packed(d),
                    actor["UserId"],
                )
                c.execute(
                    "INSERT crm_learning10.Deployment(InstitutionId,DeploymentId,PackId,State,Revision,Document,ActorId) VALUES(?,?,?,'enabled',1,'{}',?)",
                    institution(self.settings),
                    str(uuid4()),
                    p,
                    actor["UserId"],
                )
            version = str(uuid4())
            c.execute(
                "INSERT crm_learning10.PackVersion(InstitutionId,VersionId,PackId,VersionNo,DocumentHash,Document,ActorId) VALUES(?,?,?,?,?,?,?)",
                institution(self.settings),
                version,
                p,
                revision,
                digest(d),
                packed(d),
                actor["UserId"],
            )
            event(
                c,
                self.settings,
                actor,
                p,
                "pack.version",
                dict(version_id=version, revision=revision),
            )
            return dict(id=p, revision=revision, version_id=version)

        return self.mutate(authority, body, "pack.save", id or "new", perform)

    def grant(self, authority, pack, body):
        def perform(c, actor):
            p = get(c, self.settings, "packs", pack)
            demo = p["Scope"] == "demo"
            if demo:
                if (
                    not body.demo_subject
                    or body.subject_id
                    or body.basis != "synthetic_demo"
                ):
                    raise HTTPException(422, "learning_demo_scope_required")
                subject = None
                key = group_key(self.settings, pack, None, str(body.demo_subject))
            else:
                if (
                    body.subject_id is None
                    or body.demo_subject
                    or body.basis == "synthetic_demo"
                ):
                    raise HTTPException(422, "learning_native_authorization_required")
                subject = primary(c, str(body.subject_id))
                read_contact(c, subject)
                key = group_key(self.settings, pack, subject)
            prior = one(
                c,
                "SELECT * FROM crm_learning10.Grant WHERE InstitutionId=? AND PackId=? AND GroupKey=?",
                institution(self.settings),
                pack,
                key,
            )
            if body.revision != (prior["Revision"] if prior else 0):
                raise HTTPException(409, "revision_conflict")
            id = uid(str(prior["GrantId"])) if prior else str(uuid4())
            revision = body.revision + 1
            d = dict(
                basis=body.basis,
                reference=body.reference,
                synthetic_demo=demo,
                purpose=PURPOSE[p["Task"]],
                demo_subject=str(body.demo_subject) if demo else None,
                subject_id=subject,
            )
            state = "active" if body.approved else "revoked"
            if prior:
                c.execute(
                    "UPDATE crm_learning10.Grant SET State=?,Revision=?,Document=?,ActorId=? WHERE InstitutionId=? AND PackId=? AND GrantId=? AND Revision=?",
                    state,
                    revision,
                    packed(d),
                    actor["UserId"],
                    institution(self.settings),
                    pack,
                    id,
                    body.revision,
                )
            else:
                c.execute(
                    "INSERT crm_learning10.Grant(InstitutionId,GrantId,PackId,GroupKey,SubjectId,Purpose,State,Revision,Document,ActorId) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    institution(self.settings),
                    id,
                    pack,
                    key,
                    subject,
                    PURPOSE[p["Task"]],
                    state,
                    revision,
                    packed(d),
                    actor["UserId"],
                )
            event(
                c,
                self.settings,
                actor,
                pack,
                "purpose." + state,
                dict(grant_id=id, revision=revision, **d),
            )
            return dict(id=id, revision=revision, state=state)

        return self.mutate(
            authority, body, "purpose.review", pack, perform, recent=True
        )

    def capture(self, authority, pack, body):
        def perform(c, actor):
            p = get(c, self.settings, "packs", pack)
            g = get(c, self.settings, "grants", str(body.grant_id), pack)
            grant_binding(c, self.settings, p, g)
            demo = p["Scope"] == "demo"
            if demo != (body.source_kind == "demo") or demo and body.source_id:
                raise HTTPException(422, "learning_sample_scope_mismatch")
            if not demo:
                if not body.source_id:
                    raise HTTPException(422, "learning_source_required")
                if body.source_kind in {"conversation", "admissions"}:
                    source = one(
                        c,
                        "SELECT ContactId,CreatedAt FROM crm.Conversation WHERE ConversationId=?",
                        str(body.source_id),
                    )
                    if not source or primary(c, uid(str(source["ContactId"]))) != uid(
                        str(g["SubjectId"])
                    ):
                        raise HTTPException(404, "learning_source_not_found")
                else:
                    source = one(
                        c,
                        "SELECT CreatedAt FROM crm_campaign8.Record WHERE InstitutionId=? AND RecordId=? AND Kind='campaign'",
                        institution(self.settings),
                        str(body.source_id),
                    )
                    if not source:
                        raise HTTPException(404, "learning_source_not_found")
                if source["CreatedAt"].replace(tzinfo=timezone.utc) > body.feature_at:
                    raise HTTPException(422, "learning_source_after_features")
            try:
                numeric = features(p["Task"], body.features)
            except ValueError as e:
                raise HTTPException(422, str(e)) from None
            program = str(body.program_id) if body.program_id else "general"
            if not demo:
                from app.modules.crm_configuration.application.service import (
                    read_configuration,
                )

                config, _ = read_configuration(c, foundation=True)
                if not any(v.active and v.key == body.stage for v in config.stages):
                    raise HTTPException(409, "learning_stage_review_required")
            if (
                body.program_id
                and not c.execute(
                    "SELECT ProgramId FROM crm_agents5.Program WHERE InstitutionId=? AND ProgramId=? AND Active=1",
                    institution(self.settings),
                    program,
                ).fetchone()
            ):
                raise HTTPException(409, "learning_program_review_required")
            version = latest_version(c, self.settings, pack)
            document = dict(
                features=numeric,
                observation="synthetic_demo"
                if demo
                else "human_reviewed_structured_observation",
                source_kind=body.source_kind,
                source_id=str(body.source_id) if body.source_id else None,
                feature_at=body.feature_at.isoformat().replace("+00:00", "Z"),
                outcome_at=body.outcome_at.isoformat().replace("+00:00", "Z"),
                label=body.label,
                program=program,
                stage=body.stage,
                synthetic_demo=demo,
            )
            if body.supersedes:
                old = get(c, self.settings, "samples", str(body.supersedes), pack)
                if (
                    uid(str(old["GrantId"])) != str(body.grant_id)
                    or old["GroupKey"] != g["GroupKey"]
                    or doc(old)["features"] != numeric
                    or old["FeatureAt"].replace(tzinfo=timezone.utc) != body.feature_at
                ):
                    raise HTTPException(409, "learning_correction_snapshot_mismatch")
                if c.execute(
                    "SELECT SampleId FROM crm_learning10.Sample WHERE InstitutionId=? AND PackId=? AND Supersedes=?",
                    institution(self.settings),
                    pack,
                    str(body.supersedes),
                ).fetchone():
                    raise HTTPException(409, "learning_correction_already_superseded")
            id = str(uuid4())
            c.execute(
                "INSERT crm_learning10.Sample(InstitutionId,SampleId,PackId,GrantId,VersionId,GroupKey,SourceKind,SourceId,ProgramKey,StageKey,FeatureAt,OutcomeAt,Label,Supersedes,DocumentHash,Document,ActorId) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                institution(self.settings),
                id,
                pack,
                str(body.grant_id),
                str(version["VersionId"]),
                g["GroupKey"],
                body.source_kind,
                str(body.source_id) if body.source_id else None,
                program,
                body.stage,
                body.feature_at.replace(tzinfo=None),
                body.outcome_at.replace(tzinfo=None),
                body.label,
                str(body.supersedes) if body.supersedes else None,
                digest(document),
                packed(document),
                actor["UserId"],
            )
            event(
                c,
                self.settings,
                actor,
                pack,
                "sample.corrected" if body.supersedes else "sample.reviewed",
                dict(
                    sample_id=id,
                    supersedes=str(body.supersedes) if body.supersedes else None,
                    document_hash=digest(document),
                ),
            )
            return dict(id=id, hash=digest(document))

        return self.mutate(authority, body, "sample.review", pack, perform)

    def dataset(self, authority, pack, body):
        def perform(c, actor):
            p = get(c, self.settings, "packs", pack)
            version = latest_version(c, self.settings, pack)
            data = samples(c, self.settings, p)
            cutoff = body.cutoff.isoformat().replace("+00:00", "Z")
            try:
                training, holdout = split(data, cutoff)
            except ValueError as e:
                raise HTTPException(409, str(e)) from None
            d = dict(
                version_id=uid(str(version["VersionId"])),
                task=p["Task"],
                scope=p["Scope"],
                cutoff=cutoff,
                samples={
                    s["id"]: digest([s["sample_hash"], s["grant_binding"]])
                    for s in data
                },
                train_ids=[s["id"] for s in training],
                holdout_ids=[s["id"] for s in holdout],
                institution=institution(self.settings),
                raw_content_used=False,
            )
            id = str(uuid4())
            c.execute(
                "INSERT crm_learning10.Dataset(InstitutionId,DatasetId,PackId,VersionId,DocumentHash,Document,ActorId) VALUES(?,?,?,?,?,?,?)",
                institution(self.settings),
                id,
                pack,
                str(version["VersionId"]),
                digest(d),
                packed(d),
                actor["UserId"],
            )
            event(
                c,
                self.settings,
                actor,
                pack,
                "dataset.frozen",
                dict(dataset_id=id, hash=digest(d)),
            )
            return dict(
                id=id,
                hash=digest(d),
                training_count=len(training),
                holdout_count=len(holdout),
            )

        return self.mutate(authority, body, "dataset.freeze", pack, perform)

    def training(self, authority, pack, body):
        # CPU work is outside SQL locks. Commit rechecks evidence and authorization.
        with self.access(authority, recent=True) as (c, actor):
            _, prior = replay(
                c,
                self.settings,
                actor["UserId"],
                str(body.operation_id),
                "learning.model.train",
                pack,
                body.model_dump(mode="json"),
            )
            if prior:
                return prior
            p = get(c, self.settings, "packs", pack)
            dataset = get(c, self.settings, "datasets", str(body.dataset_id), pack)
            data = samples(c, self.settings, p, dataset)
            frozen = doc(dataset)
            if not p["TrainEnabled"]:
                raise HTTPException(409, "learning_training_paused")
            if frozen["version_id"] != uid(
                str(latest_version(c, self.settings, pack)["VersionId"])
            ):
                raise HTTPException(409, "learning_pack_version_changed")
        try:
            model, report = train(p["Task"], data, frozen["cutoff"])
        except ValueError as e:
            raise HTTPException(409, str(e)) from None

        def perform(c, actor):
            current = get(c, self.settings, "packs", pack)
            ds = get(c, self.settings, "datasets", str(body.dataset_id), pack)
            samples(c, self.settings, current, ds)
            if not current["TrainEnabled"]:
                raise HTTPException(409, "learning_training_paused")
            if (
                current["Revision"] != p["Revision"]
                or ds["DocumentHash"] != dataset["DocumentHash"]
            ):
                raise HTTPException(409, "learning_evidence_changed")
            d = dict(
                model=model,
                evaluation=report,
                dataset_hash=dataset["DocumentHash"],
                scope=current["Scope"],
                institution=institution(self.settings),
                source="reviewed_numeric_SQL2019",
                automatic_promotion=False,
            )
            id = str(uuid4())
            c.execute(
                "INSERT crm_learning10.Artifact(InstitutionId,ArtifactId,PackId,DatasetId,DocumentHash,Document,ActorId) VALUES(?,?,?,?,?,?,?)",
                institution(self.settings),
                id,
                pack,
                str(body.dataset_id),
                digest(d),
                packed(d),
                actor["UserId"],
            )
            event(
                c,
                self.settings,
                actor,
                pack,
                "model.trained",
                dict(artifact_id=id, hash=digest(d), eligible=report["eligible"]),
            )
            return dict(id=id, hash=digest(d), evaluation=report)

        return self.mutate(authority, body, "model.train", pack, perform, recent=True)

    def validate_artifact(self, c, p, artifact):
        d = doc(artifact)
        dataset = get(
            c,
            self.settings,
            "datasets",
            uid(str(artifact["DatasetId"])),
            uid(str(p["PackId"])),
        )
        if (
            d["institution"] != institution(self.settings)
            or d["scope"] != p["Scope"]
            or d["model"]["task"] != p["Task"]
            or d["dataset_hash"] != dataset["DocumentHash"]
        ):
            raise HTTPException(409, "learning_artifact_binding")
        data = samples(c, self.settings, p, dataset)
        return d, data

    def selection(self, authority, pack, body):
        def perform(c, actor):
            authorize(c, self.settings, authority, "settings.ai.write", recent=True)
            p = get(c, self.settings, "packs", pack)
            current = deployment(c, self.settings, pack)
            if current["Revision"] != body.revision:
                raise HTTPException(409, "revision_conflict")
            active = uid(str(current["ActiveId"])) if current["ActiveId"] else None
            shadow = uid(str(current["ShadowId"])) if current["ShadowId"] else None
            state = current["State"]
            history = doc(current)
            if body.action in {"pause", "resume"}:
                state = "paused" if body.action == "pause" else "enabled"
            else:
                if body.artifact_id is None:
                    raise HTTPException(422, "learning_artifact_required")
                id = str(body.artifact_id)
                artifact = get(c, self.settings, "artifacts", id, pack)
                d, _ = self.validate_artifact(c, p, artifact)
                if body.action != "rollback" and doc(
                    get(
                        c,
                        self.settings,
                        "datasets",
                        uid(str(artifact["DatasetId"])),
                        pack,
                    )
                )["version_id"] != uid(
                    str(latest_version(c, self.settings, pack)["VersionId"])
                ):
                    raise HTTPException(409, "learning_pack_version_changed")
                if body.action == "shadow":
                    shadow = id
                else:
                    if not d["evaluation"]["eligible"]:
                        raise HTTPException(409, "learning_evaluation_gate_failed")
                    if body.action == "rollback":
                        if id not in history.get("approved", []):
                            raise HTTPException(
                                409, "learning_previous_approved_required"
                            )
                    else:
                        if shadow != id:
                            raise HTTPException(409, "learning_shadow_required")
                        observations = []
                        bindings = {}
                        observed_subjects = set()
                        for observation in rows(
                            c,
                            "SELECT TOP(1000) GrantId,Document FROM crm_learning10.Prediction WHERE InstitutionId=? AND PackId=? AND ArtifactId=? AND Mode='shadow' ORDER BY CreatedAt DESC",
                            institution(self.settings),
                            pack,
                            id,
                        ):
                            grant_id = uid(str(observation["GrantId"]))
                            if grant_id not in bindings:
                                grant = get(c, self.settings, "grants", grant_id, pack)
                                bindings[grant_id] = (
                                    grant_binding(c, self.settings, p, grant)
                                    if grant["State"] == "active"
                                    else None
                                )
                            evidence = doc(observation)
                            if (
                                bindings[grant_id]
                                and evidence.get("grant_binding") == bindings[grant_id]
                                and evidence.get("deployment_revision")
                                == current["Revision"]
                                and grant_id not in observed_subjects
                            ):
                                observations.append(evidence)
                                observed_subjects.add(grant_id)
                        if len(observations) < 4:
                            raise HTTPException(
                                409, "learning_shadow_observations_required"
                            )
                        if drift(d["model"], [v["features"] for v in observations])[
                            "review_required"
                        ]:
                            raise HTTPException(409, "learning_drift_review_required")
                    history["previous_active"] = active
                    active = id
                    history["approved"] = sorted(
                        set(history.get("approved", [])) | {id}
                    )
                    history["last_action"] = body.action
                    event(
                        c,
                        self.settings,
                        actor,
                        pack,
                        "model." + body.action,
                        dict(
                            artifact_id=id,
                            previous_id=history["previous_active"],
                            scope=p["Scope"],
                        ),
                    )
            c.execute(
                "UPDATE crm_learning10.Deployment SET ActiveId=?,ShadowId=?,State=?,Revision=Revision+1,Document=?,ActorId=? WHERE InstitutionId=? AND PackId=? AND Revision=?",
                active,
                shadow,
                state,
                packed(history),
                actor["UserId"],
                institution(self.settings),
                pack,
                body.revision,
            )
            event(
                c,
                self.settings,
                actor,
                pack,
                "deployment." + body.action,
                dict(revision=body.revision + 1),
            )
            return deployed_public(deployment(c, self.settings, pack))

        return self.mutate(
            authority, body, "deployment.select", pack, perform, recent=True
        )

    def infer(self, authority, pack, body):
        def perform(c, actor):
            p = get(c, self.settings, "packs", pack)
            g = get(c, self.settings, "grants", str(body.grant_id), pack)
            grant_binding(c, self.settings, p, g)
            selected = deployment(c, self.settings, pack)
            if selected["State"] != "enabled":
                raise HTTPException(409, "learning_inference_paused")
            artifact_id = selected["ShadowId" if body.mode == "shadow" else "ActiveId"]
            if artifact_id is None:
                raise HTTPException(409, "learning_model_not_selected")
            a = get(c, self.settings, "artifacts", uid(str(artifact_id)), pack)
            d, _ = self.validate_artifact(c, p, a)
            try:
                numeric = features(p["Task"], body.features)
                probability = score(d["model"], numeric)
                shift = drift(d["model"], [numeric])
            except ValueError as e:
                raise HTTPException(422, str(e)) from None
            result = dict(
                deployment_revision=selected["Revision"],
                grant_id=str(body.grant_id),
                grant_binding=grant_binding(c, self.settings, p, g),
                artifact_id=uid(str(artifact_id)),
                artifact_hash=a["DocumentHash"],
                scope=p["Scope"],
                mode=body.mode,
                features=numeric,
                probability=probability,
                baseline_probability=d["model"]["baseline"],
                drift=shift,
                algorithm=ALGORITHM,
                source="trained_model",
                automatic_action=False,
                synthetic_demo=p["Scope"] == "demo",
            )
            id = str(uuid4())
            c.execute(
                "INSERT crm_learning10.Prediction(InstitutionId,PredictionId,PackId,ArtifactId,GrantId,Mode,Document,ActorId) VALUES(?,?,?,?,?,?,?,?)",
                institution(self.settings),
                id,
                pack,
                str(artifact_id),
                str(body.grant_id),
                body.mode,
                packed(result),
                actor["UserId"],
            )
            return dict(id=id, **result)

        return self.mutate(authority, body, "model.infer", pack, perform)
