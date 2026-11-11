"""Real SQL acceptance on owned TRIAL restorations only; never on the source."""

import copy
import json
import re

import pyodbc

from tools import cbn_foundation as f
from tools.foundation_contract import inspect_reference, integrity_checks
from tools.foundation_snapshot import metadata
from tools.rehearse_foundation import (
    SOURCE,
    admin,
    capture,
    checkdb,
    connection_text,
    load,
    restricted,
    save,
)


class FaultCursor:
    def __init__(self, cursor, mode):
        self.cursor, self.mode = cursor, mode
        self.fired = False
        self.ack_pending = False

    def execute(self, sql, *params):
        if self.mode == "ack_B001" and "INSERT crm_meta.MigrationJournal" in sql:
            if params[1:3] == ("CBN-B001", "COMMITTED"):
                self.ack_pending = True
        if sql == "COMMIT TRANSACTION;" and self.ack_pending and not self.fired:
            self.fired = True
            self.cursor.execute(
                sql, *params
            )  # real commit, simulated lost acknowledgement
            raise RuntimeError("synthetic_commit_ack_lost")
        target = {
            "fail_B000": "CREATE TABLE crm_meta.MigrationJournal",
            "fail_B001": "CREATE TABLE crm.Contact",
            "fail_B006": "CREATE TABLE crm_config.Configuration",
        }.get(self.mode)
        if target and target in sql and not self.fired:
            self.fired = True
            sql += "\nTHROW 51199, 'Synthetic rehearsal failure.', 1;"
        self.cursor.execute(sql, *params)
        return self

    def __getattr__(self, name):
        return getattr(self.cursor, name)


class FaultConnection:
    def __init__(self, connection, mode):
        self.connection, self.mode = connection, mode

    def cursor(self):
        return FaultCursor(self.connection.cursor(), self.mode)


def exercise(work):
    f.require(
        not (work / "rehearsal-result.json").exists(), "rehearsal_already_recorded"
    )
    state = load(work / "state.json")
    tickets = {
        label: load(work / (label + "-ticket.json")) for label in ("trial", "faults")
    }
    directory, context = work / "release", state["context"]
    manifest, shapes, manifest_hash = f.load_release(directory)
    checks = []

    def audit(label):
        return f.Audit(
            work / (label + "-audit.jsonl"), f.sha(tickets[label]["identity"])
        )

    def run(label, mode=None):
        with restricted(tickets[label], context) as connection:
            wrapped = FaultConnection(connection, mode) if mode else connection
            return f.apply(wrapped, tickets[label], audit(label), directory=directory)

    def rejected(label, action, expected=None):
        try:
            action()
        except f.Blocked as error:
            f.require(
                expected is None or expected in str(error),
                "wrong_rehearsal_rejection_" + label,
            )
            checks.append(label)
        else:
            raise AssertionError("rehearsal_did_not_reject_" + label)

    for label in tickets:
        with admin(tickets[label]["identity"]["database"], context) as connection:
            f.require(
                capture(connection) == state["source_signature"],
                "trial_before_core_changed",
            )
    result = run("trial")
    f.require(result["applied"] == list(f.UNITS), "trial_units_not_applied")
    f.require(run("trial")["noop"], "repeat_not_noop")
    checks.extend(["separate_restoration_release_applied", "repeat_noop"])
    print(
        json.dumps({"stage": "trial_release_applied", "units": result["applied"]}),
        flush=True,
    )
    with restricted(tickets["trial"], context) as connection:
        inspection = inspect_reference(
            connection, tickets["trial"]["identity"]["collation"]
        )
        constraints = integrity_checks(connection)

    changed = copy.deepcopy(tickets["trial"])
    changed["identity"]["database"] = SOURCE
    with restricted(tickets["trial"], context) as connection:
        rejected(
            "source_target_refused",
            lambda: f.apply(connection, changed, audit("trial"), directory=directory),
            "restored_name_required",
        )
    with admin(tickets["trial"]["identity"]["database"], context) as connection:
        rejected(
            "administrative_principal_refused",
            lambda: f.apply(
                connection, tickets["trial"], audit("trial"), directory=directory
            ),
            "restricted_principal_required",
        )
    with restricted(tickets["trial"], context) as connection:
        connection.cursor().execute("BEGIN TRANSACTION;")
        rejected(
            "outer_transaction_refused",
            lambda: f.apply(
                connection, tickets["trial"], audit("trial"), directory=directory
            ),
            "existing_transaction_refused",
        )
        connection.cursor().execute("ROLLBACK TRANSACTION;")
    invalid_tls = re.sub(
        r"HostnameInCertificate=[^;]+;",
        "HostnameInCertificate=invalid.example.invalid;",
        connection_text(tickets["trial"]["identity"]["database"]),
    )
    try:
        unexpected = pyodbc.connect(invalid_tls, timeout=3, autocommit=True)
    except pyodbc.Error as error:
        f.require(error.args[0] == "08001", "wrong_tls_rejection")
        checks.append("wrong_certificate_hostname_refused")
    else:
        unexpected.close()
        raise AssertionError("invalid_TLS_hostname_accepted")

    drifts = [
        (
            "column_drift",
            "ALTER TABLE crm.Contact ALTER COLUMN City nvarchar(101) NOT NULL;",
            "ALTER TABLE crm.Contact ALTER COLUMN City nvarchar(100) NOT NULL;",
        ),
        (
            "check_trust_drift",
            "ALTER TABLE crm.Contact NOCHECK CONSTRAINT CK_Contact_Custom;",
            "ALTER TABLE crm.Contact WITH CHECK CHECK CONSTRAINT CK_Contact_Custom;",
        ),
        (
            "fk_trust_drift",
            "ALTER TABLE crm.Conversation NOCHECK CONSTRAINT FK_Conversation_Contact;",
            "ALTER TABLE crm.Conversation WITH CHECK "
            "CHECK CONSTRAINT FK_Conversation_Contact;",
        ),
        (
            "index_drift",
            "DROP INDEX IX_Message_Conversation_Sequence ON crm.Message;",
            "CREATE UNIQUE INDEX IX_Message_Conversation_Sequence "
            "ON crm.Message(ConversationId,Sequence);",
        ),
        (
            "marker_drift",
            "EXEC sys.sp_updateextendedproperty @name=N'crm.contract',"
            "@value=N'tampered',@level0type=N'SCHEMA',@level0name=N'crm';",
            "EXEC sys.sp_updateextendedproperty @name=N'crm.contract',"
            "@value=N'CBN-foundation-B001-v1',"
            "@level0type=N'SCHEMA',@level0name=N'crm';",
        ),
        (
            "unknown_partial_object",
            "CREATE TABLE crm.CbnRehearsalUnexpected(Id int NOT NULL);",
            "DROP TABLE crm.CbnRehearsalUnexpected;",
        ),
    ]
    for label, mutation, repair in drifts:
        with restricted(tickets["trial"], context) as connection:
            cursor = connection.cursor()
            cursor.execute(mutation)
            try:
                rejected(label, lambda: run("trial"), "entry_shape_drift")
            finally:
                cursor.execute(repair)
        f.require(run("trial")["noop"], "repaired_test_shape_not_equal")
    with restricted(tickets["trial"], context) as holder:
        f.acquire(holder.cursor(), "crm.schema.migrate.v1", "Session")
        try:
            rejected(
                "second_executor_lock_refused",
                lambda: run("trial"),
                "migration_lock_unavailable",
            )
        finally:
            holder.cursor().execute(
                "EXEC sys.sp_releaseapplock "
                "@Resource=N'crm.schema.migrate.v1',@LockOwner=N'Session';"
            )
    print(json.dumps({"stage": "trial_drift_and_guard_checks_passed"}), flush=True)

    # Faults use another restoration, so the accepted TRIAL seed stays untouched.
    for mode, expected_prefix in (("fail_B000", "prepared"), ("fail_B001", "CBN-B000")):
        try:
            run("faults", mode)
        except pyodbc.Error:
            pass
        else:
            raise AssertionError("injected_failure_not_raised")
        with restricted(tickets["faults"], context) as connection:
            f.require(
                metadata(connection.cursor(), managed=True) == shapes[expected_prefix],
                "failed_unit_did_not_rollback",
            )
        checks.append(mode + "_rollback")
    with restricted(tickets["faults"], context) as writer:
        writer.cursor().execute("BEGIN TRANSACTION;")
        f.acquire(writer.cursor(), "crm.local.commit", "Transaction")
        try:
            rejected(
                "writer_lock_refused",
                lambda: run("faults"),
                "migration_lock_unavailable",
            )
        finally:
            writer.cursor().execute("ROLLBACK TRANSACTION;")
    rejected(
        "lost_commit_ack_requires_reconciliation",
        lambda: run("faults", "ack_B001"),
        "unit_commit_outcome_unknown",
    )
    rejected(
        "unknown_not_retried",
        lambda: run("faults"),
        "external_unknown_requires_reconciliation",
    )
    with restricted(tickets["faults"], context) as connection:
        reconciled = f.reconcile(
            connection, tickets["faults"], audit("faults"), directory=directory
        )
        f.require(reconciled["unresolved"] == 0, "reconciliation_not_complete")
    checks.append("explicit_reconciliation_without_ddl")
    try:
        run("faults", "fail_B006")
    except pyodbc.Error:
        pass
    else:
        raise AssertionError("configuration_failure_not_raised")
    with restricted(tickets["faults"], context) as connection:
        f.require(
            metadata(connection.cursor(), managed=True) == shapes["CBN-B001"],
            "configuration_unit_did_not_rollback",
        )
    checks.append("fail_B006_rollback")
    f.require(run("faults")["applied"] == ["CBN-B006"], "resume_known_prefix_failed")
    checks.append("resume_verified_prefix")
    with restricted(tickets["faults"], context) as connection:
        edited = {
            "stages": [{"key": "review", "label": "Review", "active": True}],
            "tags": [],
            "inactiveTags": [],
            "fields": [],
        }
        connection.cursor().execute(
            "UPDATE crm_config.Configuration SET Document=?,Revision=2 "
            "WHERE ConfigurationId=1",
            json.dumps(edited),
        )
    f.require(run("faults")["noop"], "edited_config_not_noop")
    with restricted(tickets["faults"], context) as connection:
        row = (
            connection.cursor()
            .execute("SELECT Document,Revision FROM crm_config.Configuration")
            .fetchone()
        )
        f.require(
            json.loads(row[0]) == edited and row[1] == 2, "configuration_overwritten"
        )
        connection.cursor().execute("DELETE FROM crm_config.Configuration;")
    checks.append("legitimate_config_edit_preserved")
    try:
        rejected(
            "missing_singleton_blocks_noop",
            lambda: run("faults"),
            "configuration_singleton_missing",
        )
        with restricted(tickets["faults"], context) as connection:
            rejected(
                "missing_singleton_blocks_reconcile",
                lambda: f.reconcile(
                    connection, tickets["faults"], audit("faults"), directory=directory
                ),
                "configuration_singleton_missing",
            )
    finally:
        with restricted(tickets["faults"], context) as connection:
            connection.cursor().execute(
                "INSERT crm_config.Configuration(ConfigurationId,Document,Revision) "
                "VALUES(1,?,2)",
                json.dumps(edited),
            )
    f.require(run("faults")["noop"], "fault_copy_final_state_invalid")

    preserved = []
    for target in [*state["targets"].values(), *state.get("retired_targets", [])]:
        with admin(target["database"], context) as connection:
            f.require(
                capture(connection) == state["source_signature"],
                "restored_academic_state_changed",
            )
            preserved.append(target["database"])
    for label in tickets:
        with admin(tickets[label]["identity"]["database"], context) as connection:
            checkdb(connection.cursor(), tickets[label]["identity"]["database"])
    with admin(SOURCE, context, readonly=True) as connection:
        f.require(
            capture(connection) == state["source_signature"],
            "source_changed_after_rehearsal",
        )
        f.require(
            not connection.cursor()
            .execute(
                "SELECT 1 FROM sys.schemas WHERE name=N'crm' OR name LIKE N'crm[_]%'"
            )
            .fetchone(),
            "source_managed_namespace_changed",
        )
    result = {
        "release_sha256": manifest_hash,
        "release_id": manifest["release_id"],
        "trial_database": tickets["trial"]["identity"]["database"],
        "fault_database": tickets["faults"]["identity"]["database"],
        "inspection": inspection,
        "integrity_checks": constraints,
        "rehearsal_checks": checks,
        "all_restored_academic_signatures_equal": preserved,
        "source_unchanged": True,
        "post_release_checkdb": 2,
        "institutional_sql2019_accepted": False,
        "runtime_activated": False,
    }
    save(work / "rehearsal-result.json", result)
    return result
