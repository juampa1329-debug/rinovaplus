"""Explicit additive P9 runner. No startup DDL and no academic mutations."""

import json

from app.institutional.ads_policy_v1 import PACKAGE, TARGET, release
from app.institutional.ads_policy_v1 import parent_digest as journal_digest
from tools.es_schema_catalog_v2 import model, snapshot
from tools.es_schema_migrate_v2 import identity


def apply(connection, expected, *, approved_release, parent_journal, fault=None):
    c = connection.cursor()
    if c.execute("SELECT @@TRANCOUNT").fetchval() != 0:
        raise ValueError("P9ES_caller_transaction_must_be_absent")
    if (
        connection.autocommit is not True
        or identity(c) != expected
        or (not TARGET.fullmatch(expected["database"]))
        or ((expected["engine"], expected["compatibility"]) != (15, 150))
    ):
        raise ValueError("P9ES_explicit_isolated_target_required")
    if release() != approved_release or journal_digest(c) != parent_journal:
        raise ValueError("P9ES_release_or_parent_history_drift")
    c.execute("SET XACT_ABORT ON;SET LOCK_TIMEOUT 10000;BEGIN TRANSACTION")
    try:
        lock = c.execute(
            "DECLARE @r int;EXEC @r=sys.sp_getapplock @Resource='crm.schema.migrate.v1',@LockMode='Exclusive',@LockOwner='Transaction',@LockTimeout=10000;SELECT @r"
        ).fetchval()
        if lock < 0:
            raise ValueError("P9ES_migration_lock")
        if c.execute("SELECT OBJECT_ID(N'dbo.CRMPublicidadMigracion')").fetchval():
            prior = c.execute(
                "SELECT ManifestSha256,TargetDatabase,ParentHistorySha256,Status FROM dbo.CRMPublicidadMigracion WHERE UnitId='P9ES-001'"
            ).fetchone()
            if prior and tuple(prior) == (
                approved_release,
                expected["database"],
                parent_journal,
                "COMMITTED",
            ):
                expected_model = json.loads(
                    (PACKAGE / "expected-model.json").read_text()
                )
                if model(snapshot(c)) != expected_model:
                    raise ValueError("P9ES_post_commit_model_drift")
                c.execute("COMMIT")
                return {"status": "noop", "parent_journal_preserved": True}
            if prior and tuple(prior) != (
                approved_release,
                expected["database"],
                parent_journal,
                "STARTED",
            ):
                raise ValueError("P9ES_history_conflict")
        else:
            parent = json.loads(
                (
                    PACKAGE.parent / "cbn_campaign_operations_v1/expected-model.json"
                ).read_text()
            )
            if model(snapshot(c)) != parent:
                raise ValueError("P9ES_parent_model_drift")
            c.execute((PACKAGE / "P9ES-000.sql").read_text())
        c.execute(
            "IF NOT EXISTS(SELECT 1 FROM dbo.CRMPublicidadMigracion WHERE UnitId='P9ES-001') INSERT dbo.CRMPublicidadMigracion(UnitId,ManifestSha256,TargetDatabase,ParentHistorySha256,Status) VALUES('P9ES-001',?,?,?,'STARTED')",
            approved_release,
            expected["database"],
            parent_journal,
        )
        c.execute("COMMIT")
        if fault == "after_started":
            raise RuntimeError("P9ES_injected_after_started")
        c.execute("BEGIN TRANSACTION")
        lock = c.execute(
            "DECLARE @r int;EXEC @r=sys.sp_getapplock @Resource='crm.schema.migrate.v1',@LockMode='Exclusive',@LockOwner='Transaction',@LockTimeout=10000;SELECT @r"
        ).fetchval()
        if lock < 0:
            raise ValueError("P9ES_migration_lock")
        status = c.execute(
            "SELECT Status FROM dbo.CRMPublicidadMigracion WITH(UPDLOCK,HOLDLOCK) WHERE UnitId='P9ES-001'"
        ).fetchval()
        if status == "COMMITTED":
            if model(snapshot(c)) != json.loads(
                (PACKAGE / "expected-model.json").read_text()
            ):
                raise ValueError("P9ES_concurrent_model_drift")
            c.execute("COMMIT")
            return {"status": "noop", "parent_journal_preserved": True}
        parent = json.loads(
            (
                PACKAGE.parent / "cbn_campaign_operations_v1/expected-model.json"
            ).read_text()
        )
        actual = model(snapshot(c))
        for section, values in actual.items():
            expected_rows = [
                r
                for r in values
                if r.get("table") != "CRMPublicidadMigracion"
                and r.get("name") != "CRMPublicidadMigracion"
            ]
            if expected_rows != parent[section]:
                raise ValueError("P9ES_started_model_drift")
        c.execute((PACKAGE / "P9ES-001.sql").read_text())
        if fault == "before_commit":
            raise RuntimeError("P9ES_injected_before_commit")
        if (PACKAGE / "expected-model.json").exists() and model(
            snapshot(c)
        ) != json.loads((PACKAGE / "expected-model.json").read_text()):
            raise ValueError("P9ES_result_model_drift")
        if journal_digest(c) != parent_journal:
            raise ValueError("P9ES_parent_journal_changed")
        c.execute(
            "UPDATE dbo.CRMPublicidadMigracion SET Status='COMMITTED',CommittedAt=SYSUTCDATETIME() WHERE UnitId='P9ES-001'"
        )
        c.execute("COMMIT")
        if fault == "after_commit":
            raise RuntimeError("P9ES_injected_after_commit")
        return {"status": "committed", "parent_journal_preserved": True}
    except BaseException:
        c.execute("IF @@TRANCOUNT>0 ROLLBACK")
        raise
