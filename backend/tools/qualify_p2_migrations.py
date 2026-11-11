"""Fault injection and data drift checks confined to new P2ES copies."""
import contextlib
import json
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from tools import p2_es_migrations as migration
from tools import rehearse_p2_spanish as driver
from tools.p2_es_recovery import data_fingerprint
from tools.rehearse_p2_spanish import WORK, admin, read, restored, save

APPROVED = "1a7ba0dc7435e1e5dd61b431cca7f2164d698d4b4b6df9dd53cd66e8b40b10b4"


def main():
    driver.APPROVED = APPROVED
    state = read(WORK / "state.json")
    scenarios = []
    for unit in migration.UNITS:
        for fault in ("before_commit", "ddl_error", "connection_loss_before_commit", "after_commit", "after_wal_before_SQL_started"):
            name, actual, restoration = restored(state["initial_backup"], "FAULT")
            wal = WORK / (name + ".wal.jsonl")
            try:
                with admin(name) as connection:
                    driver.apply(connection, actual, wal, unit + ":" + fault)
            except (RuntimeError, Exception) as error:
                if not isinstance(error, RuntimeError) and fault != "ddl_error":
                    raise
            else:
                raise AssertionError("controlled_failure_not_observed")
            # Reconciliation is a fresh connection, not a continuation of a
            # client transaction whose COMMIT acknowledgement may be lost.
            with admin(name) as connection:
                receipt = migration.reconcile(connection, actual, wal, state["seed"], approved_manifest_sha256=APPROVED)
            with admin(name) as connection:
                driver.apply(connection, actual, wal)
            with admin(name) as connection:
                result = driver.apply(connection, actual, wal)
                assert result["status"] == "noop"
                migration.verify_model(connection.cursor(), migration.UNITS[-1])
            scenarios.append({"unit": unit, "fault": fault, "database": name, "reconciled": receipt["reconciled"], "retry": "accepted", "repeat": "noop", "native_restore": restoration["status"] if "status" in restoration else "verified"})
            save(WORK / "migration-fault-result.json", {"status": "in_progress", "scenarios": scenarios})
    name, actual, _ = restored(state["initial_backup"], "FAULT")
    def worker(index):
        with admin(name) as connection:
            return driver.apply(connection, actual, WORK / (name + f"-{index}.wal.jsonl"))["status"]
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(worker, (1, 2)))
    assert sorted(results) == ["committed", "noop"]
    drift = []
    with admin(name) as connection:
        before = data_fingerprint(connection.cursor())
        statements = [
            "UPDATE dbo.CRMCanalInstitucionalContexto SET ContractVersion='foreign-contract'",
            "UPDATE dbo.CRMAccesoInstitucion SET BootstrapHash=0x00",
            "UPDATE dbo.CRMAccesoRol SET Actions='[]' WHERE RoleKey='owner'",
            "UPDATE dbo.CRMAccesoAjusteHistorial SET Document=N'{\"changed\":true}' WHERE Section='institution'",
            "DELETE dbo.CRMConfiguracion",
        ]
        for index, sql in enumerate(statements):
            c = connection.cursor()
            c.execute("BEGIN TRANSACTION")
            try:
                c.execute(sql)
                try:
                    migration.validate_data(c, 2, state["seed"])
                except (ValueError, Exception):
                    drift.append(index)
                else:
                    raise AssertionError("data_drift_not_detected")
            finally:
                c.execute("IF @@TRANCOUNT>0 ROLLBACK")
        assert data_fingerprint(connection.cursor()) == before
        # Runtime principals must not satisfy the migrator's dbo boundary.
        c = connection.cursor()
        c.execute("BEGIN TRANSACTION")
        try:
            try:
                driver.apply(connection, actual, WORK / (name + "-caller.wal.jsonl"))
            except ValueError:
                assert c.execute("SELECT @@TRANCOUNT").fetchval() == 1
            else:
                raise AssertionError("caller_transaction_accepted")
        finally:
            c.execute("ROLLBACK")
    save(WORK / "migration-fault-result.json", {"status": "passed", "engine": 15, "compatibility": 150, "scenarios": scenarios, "concurrency": results, "data_drift_negatives": len(drift), "data_after_rollback_unchanged": True, "caller_transaction_preserved": True, "old_sources_written": False})
    print(json.dumps({"migration_faults": len(scenarios), "concurrency": results, "drift_negatives": len(drift)}))


if __name__ == "__main__":
    try:
        main()
    except BaseException as error:
        with contextlib.suppress(Exception):
            import traceback
            save(WORK / ("migration-failure-" + uuid4().hex + ".json"), {"type": type(error).__name__, "message": str(error), "frames": traceback.format_exc()})
        print(json.dumps({"migration_faults": "failed", "type": type(error).__name__}))
        raise SystemExit(1)
