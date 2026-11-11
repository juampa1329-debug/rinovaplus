"""Add P9ES-002 without editing the committed P9ES-001 journal entry."""

import json

from app.institutional import ads_policy as policy
from tools.es_schema_catalog_v2 import model, snapshot
from tools.es_schema_migrate_v2 import identity
from tools.p9_ads_base_migrations import apply as apply_base


def _apply(connection, expected, *, approved_release, parent_journal, fault=None):
    c = connection.cursor()
    if (
        c.execute("SELECT @@TRANCOUNT").fetchval() != 0
        or connection.autocommit is not True
        or identity(c) != expected
        or not policy.TARGET.fullmatch(expected["database"])
        or (expected["engine"], expected["compatibility"]) != (15, 150)
    ):
        raise ValueError("P9ES_explicit_isolated_target_required")
    if approved_release != policy.release() or parent_journal != policy.parent_digest(
        c
    ):
        raise ValueError("P9ES_release_or_parent_drift")
    prior = c.execute("SELECT OBJECT_ID(N'dbo.CRMPublicidadMigracion')").fetchval()
    state = (
        c.execute(
            "SELECT Status FROM dbo.CRMPublicidadMigracion WHERE UnitId='P9ES-002'"
        ).fetchval()
        if prior
        else None
    )
    expected_model = json.loads((policy.PACKAGE / "expected-model.json").read_text())
    if state == "COMMITTED":
        row = c.execute(
            "SELECT ManifestSha256,TargetDatabase,ParentHistorySha256 FROM dbo.CRMPublicidadMigracion WHERE UnitId='P9ES-002'"
        ).fetchone()
        if (
            tuple(row)
            != (approved_release, expected["database"], policy.base_history_digest(c))
            or model(snapshot(c)) != expected_model
        ):
            raise ValueError("P9ES_extension_committed_drift")
        return dict(status="noop", parent_journal_preserved=True)
    if not state:
        apply_base(
            connection,
            expected,
            approved_release=policy.base.release(),
            parent_journal=parent_journal,
        )
    before = policy.base_history_digest(c)

    def lock():
        r = c.execute(
            "DECLARE @r int;EXEC @r=sys.sp_getapplock @Resource='crm.schema.migrate.v1',@LockMode='Exclusive',@LockOwner='Transaction',@LockTimeout=10000;SELECT @r"
        ).fetchval()
        if r < 0:
            raise ValueError("P9ES_extension_lock")

    c.execute("SET XACT_ABORT ON;SET LOCK_TIMEOUT 10000;BEGIN TRANSACTION")
    try:
        lock()
        row = c.execute(
            "SELECT ManifestSha256,TargetDatabase,ParentHistorySha256,Status FROM dbo.CRMPublicidadMigracion WHERE UnitId='P9ES-002'"
        ).fetchone()
        if row and tuple(row) != (
            approved_release,
            expected["database"],
            before,
            "STARTED",
        ):
            if (
                tuple(row)
                == (approved_release, expected["database"], before, "COMMITTED")
                and model(snapshot(c)) == expected_model
            ):
                c.execute("COMMIT")
                return dict(status="noop", parent_journal_preserved=True)
            raise ValueError("P9ES_extension_history_conflict")
        if not row:
            c.execute(
                "INSERT dbo.CRMPublicidadMigracion(UnitId,ManifestSha256,TargetDatabase,ParentHistorySha256,Status) VALUES('P9ES-002',?,?,?,'STARTED')",
                approved_release,
                expected["database"],
                before,
            )
        c.execute("COMMIT")
        if fault == "after_started":
            raise RuntimeError("P9ES_injected_after_started")
        c.execute("BEGIN TRANSACTION")
        lock()
        state = c.execute(
            "SELECT Status FROM dbo.CRMPublicidadMigracion WITH(UPDLOCK,HOLDLOCK) WHERE UnitId='P9ES-002'"
        ).fetchval()
        if state == "COMMITTED":
            if model(snapshot(c)) != expected_model:
                raise ValueError("P9ES_extension_concurrent_drift")
            c.execute("COMMIT")
            return dict(status="noop", parent_journal_preserved=True)
        if model(snapshot(c)) != json.loads(
            (policy.base.PACKAGE / "expected-model.json").read_text()
        ):
            raise ValueError("P9ES_extension_parent_model_drift")
        c.execute((policy.PACKAGE / "P9ES-002.sql").read_text())
        if fault == "before_commit":
            raise RuntimeError("P9ES_injected_before_commit")
        if (
            model(snapshot(c)) != expected_model
            or policy.base_history_digest(c) != before
            or policy.parent_digest(c) != parent_journal
        ):
            raise ValueError("P9ES_extension_result_drift")
        c.execute(
            "UPDATE dbo.CRMPublicidadMigracion SET Status='COMMITTED',CommittedAt=SYSUTCDATETIME() WHERE UnitId='P9ES-002'"
        )
        c.execute("COMMIT")
        if fault == "after_commit":
            raise RuntimeError("P9ES_injected_after_commit")
        return dict(status="committed", parent_journal_preserved=True)
    except BaseException:
        c.execute("IF @@TRANCOUNT>0 ROLLBACK")
        raise


def apply(connection, expected, *, approved_release, parent_journal, fault=None):
    c = connection.cursor()
    if (
        connection.autocommit is not True
        or c.execute("SELECT @@TRANCOUNT").fetchval() != 0
    ):
        raise ValueError("P9ES_caller_transaction_must_be_absent")
    lock = c.execute(
        "DECLARE @r int;EXEC @r=sys.sp_getapplock @Resource='crm.ads.schema.extend.v2',@LockMode='Exclusive',@LockOwner='Session',@LockTimeout=10000;SELECT @r"
    ).fetchval()
    if lock < 0:
        raise ValueError("P9ES_extension_session_lock")
    try:
        return _apply(
            connection,
            expected,
            approved_release=approved_release,
            parent_journal=parent_journal,
            fault=fault,
        )
    finally:
        c.execute(
            "EXEC sys.sp_releaseapplock @Resource='crm.ads.schema.extend.v2',@LockOwner='Session'"
        )
