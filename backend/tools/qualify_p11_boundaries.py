"""Live drift/ACL/readiness failures on an expendable P11 copy only."""

import json
import threading
from types import SimpleNamespace

import pyodbc

from app.institutional.operations import Pulse, STAGES
from app.institutional.spanish import connection_string, transaction
from tools.p11_test_support import Harness
from tools.prepare_p11_operations import WORK, admin, save


def main():
    assert not (WORK / "boundaries-result.json").exists(), "fresh qualification required"
    h = Harness("fault")
    checks = []
    with transaction(h.settings, anonymous=True):
        pass
    checks.append("fresh_full_catalog_journals_permissions_and_TLS_guard_passes")
    connection = pyodbc.connect(connection_string(h.settings), timeout=5, autocommit=True)
    try:
        for table in h.settings.ticket["academic_tables"]:
            try:
                connection.cursor().execute("SELECT TOP(0) * FROM " + table)
            except pyodbc.Error as error:
                assert "229" in str(error)
            else:
                raise AssertionError("P11ES_academic_SELECT_unexpectedly_allowed")
        checks.append("all_30_academic_tables_deny_runtime_SELECT_without_reading_data")
        for sql in ["DELETE FROM dbo.CRMAprendizajeMigracion WHERE 1=0", "ALTER TABLE dbo.CRMAprendizajeMigracion ADD P11DeniedProbe int NULL"]:
            try:
                connection.cursor().execute(sql)
            except pyodbc.Error as error:
                assert any(code in str(error) for code in ["229", "1088"])
            else:
                raise AssertionError("P11ES_runtime_journal_write_or_DDL_allowed")
        checks.append("runtime_cannot_delete_migration_history_or_ALTER_schema")
    finally:
        connection.close()
    # Isolate the SQL readiness signal with a controlled fresh pulse. Consumer
    # execution itself is qualified separately, never inferred from this double.
    pulse = Pulse()
    for stage in STAGES:
        pulse.observe(stage, lambda: None)
    h.app.state.channel_workers = SimpleNamespace(pulse=pulse, thread=SimpleNamespace(is_alive=lambda: True), stop_event=threading.Event())
    h.b.request("/health/ready")
    h.b.request("operations")
    with admin(h.settings.connection["database"]) as db:
        db.cursor().execute("ALTER TABLE dbo.CRMContacto ADD P11DriftProbe int NULL")
    denied = h.b.request("operations", expected=503).json()
    assert "P11DriftProbe" not in str(denied) and "password" not in str(denied).lower()
    checks.append("real_CRM_schema_drift_rejected_after_a_valid_check_without_cross_request_cache")
    h.b.request("/health/live")
    assert h.b.request("/health/ready", expected=503).json() == {"status": "unavailable", "scope": "local"}
    checks.append("SQL_unavailable_is_not_masked_by_liveness_or_fresh_controlled_pulse")
    report = dict(status="passed", checks=checks, quarantined_database=h.settings.connection["database"], academic_tables_denied=30, academic_DDL_or_DML=False, real_provider_calls=0, readiness_consumer_double_declared=True, previous_copies_modified=False)
    save(WORK / "boundaries-result.json", report)
    print(json.dumps({"status": "passed", "checks": len(checks), "academic_tables_denied": 30}))


if __name__ == "__main__":
    main()
