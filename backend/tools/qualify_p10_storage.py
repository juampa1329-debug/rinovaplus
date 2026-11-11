"""P10 native-copy migration faults, drift, permissions and populated recovery."""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pyodbc

from app.institutional import learning_policy as policy
from app.institutional.spanish import connection_string, load
from tools.es_schema_migrate_v2 import identity
from tools.p2_es_recovery import restore
from tools.p10_learning_migrations import apply
from tools.prepare_p10_learning import WORK, admin, parent_tables, read, save
from tools.qualify_p4_storage import academic


def main():
    checks = []
    copies = []

    def check(name, condition=True):
        assert condition, name
        checks.append(name)
        save(
            WORK / "storage-result.json",
            {"status": "in_progress", "checks": checks, "copies": copies},
        )

    checkpoint = read(WORK / "candidate.json")["checkpoint"]

    def restored():
        name = "CBN_P10ES_FAULT_20261028_" + uuid4().hex[:8]
        with admin("master") as connection:
            restore(
                connection,
                checkpoint,
                name,
                restricted=True,
                target_pattern=policy.TARGET,
                allowed_tables=parent_tables(),
            )
        copies.append(name)
        return name

    for fault in ["after_started", "before_commit", "after_commit"]:
        name = restored()
        with admin(name) as connection:
            c = connection.cursor()
            target = identity(c)
            before = academic(c)
            parent = policy.parent_digest(c)
            try:
                apply(
                    connection,
                    target,
                    approved_release=policy.release(),
                    parent_journal=parent,
                    fault=fault,
                )
            except RuntimeError:
                pass
            else:
                raise AssertionError("fault not injected")
            status = c.execute(
                "SELECT Status FROM dbo.CRMAprendizajeMigracion WHERE UnitId='P10ES-001'"
            ).fetchval()
            assert status == ("COMMITTED" if fault == "after_commit" else "STARTED")
            result = apply(
                connection,
                target,
                approved_release=policy.release(),
                parent_journal=parent,
            )
            assert result["status"] == (
                "noop" if fault == "after_commit" else "committed"
            )
            check(
                "fault_" + fault + "_reconciles_without_academic_changes",
                academic(c) == before and policy.parent_digest(c) == parent,
            )
    name = restored()
    with admin(name) as connection:
        target = identity(connection.cursor())
        parent = policy.parent_digest(connection.cursor())

    def migrate():
        with admin(name) as connection:
            return apply(
                connection,
                target,
                approved_release=policy.release(),
                parent_journal=parent,
            )["status"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: migrate(), range(2)))
    check("concurrent_migrators_commit_once", sorted(outcomes) == ["committed", "noop"])
    with admin(name) as connection:
        c = connection.cursor()
        before = academic(c)
        c.execute("ALTER TABLE dbo.CRMAprendizajeMuestra ADD OwnedDrift int NULL")
        try:
            apply(
                connection,
                target,
                approved_release=policy.release(),
                parent_journal=parent,
            )
        except ValueError as error:
            assert "drift" in str(error)
        else:
            raise AssertionError("drift accepted")
        check("additive_model_drift_is_rejected", academic(c) == before)
    fixture = load(Path(read(WORK / "fixture-profile.json")["directory"]))
    for statement, label in [
        ("SELECT TOP(1) * FROM dbo.ACProgramas", "academic_read_denied"),
        (
            "UPDATE dbo.ACProgramas SET Id_Programa=Id_Programa WHERE 1=0",
            "academic_write_denied",
        ),
        ("CREATE TABLE dbo.P10Forbidden(OwnedId int)", "runtime_DDL_denied"),
        (
            "UPDATE dbo.CRMAprendizajeMigracion SET Status=Status WHERE 1=0",
            "journal_mutation_denied",
        ),
        (
            "UPDATE dbo.CRMAprendizajeEvento SET Kind=Kind WHERE 1=0",
            "history_rewrite_denied",
        ),
        (
            "UPDATE dbo.CRMAprendizajeArtefacto SET Document=Document WHERE 1=0",
            "artifact_rewrite_denied",
        ),
        (
            "DELETE FROM dbo.CRMMasivoConsentimiento WHERE 1=0",
            "consent_history_delete_denied",
        ),
    ]:
        connection = pyodbc.connect(connection_string(fixture), autocommit=False)
        try:
            try:
                connection.cursor().execute(statement)
            except pyodbc.Error as error:
                assert (
                    "permission" in str(error).lower()
                    or "(229)" in str(error)
                    or "(262)" in str(error)
                ), "SQL permission denial must be explicit"
                check(label)
            else:
                raise AssertionError(label)
        finally:
            connection.rollback()
            connection.close()
    save(
        WORK / "storage-result.json",
        {
            "status": "passed",
            "checks": checks,
            "copies": copies,
            "engine": 15,
            "compatibility": 150,
            "academic_writes": False,
        },
    )
    print(json.dumps({"passed": len(checks), "fresh_copies": len(copies)}))


if __name__ == "__main__":
    main()
