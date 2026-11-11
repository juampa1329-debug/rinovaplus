"""Explicit rollback/ACK/drift/recovery checks on separate C11 restorations."""

import argparse
import json
from pathlib import Path

from tools.channels_parity import CommitUnknown, guard, reconcile, run
from tools.channels_parity_contract import PACKAGE, assets, compile_units, require
from tools.rehearse_channels_parity import (
    C9,
    admin,
    load,
    new_copy,
    protected_snapshots,
    restore,
    save,
    snapshot,
)


def fault_trial(work):
    name, ticket, state = new_copy(work, "FAULT")
    ticket["release_sha256"] = assets()[1]
    save(work / (name + ".json"), ticket)
    return name, ticket, state, work / (name + ".jsonl")


def check(work):
    results = []
    units = list(compile_units())
    for prefix, unit in enumerate(units):
        name, ticket, state, audit = fault_trial(work)
        with admin(name, state["context"]) as connection:
            for previous in units[:prefix]:
                run(connection, ticket, audit, unit_id=previous)
            for boundary in (
                2,
                len(compile_units()[unit].split("-- C11_BOUNDARY")) + 1,
            ):
                try:
                    run(connection, ticket, audit, unit_id=unit, fail_at=boundary)
                except RuntimeError as error:
                    require(
                        str(error).startswith("C11_injected_"),
                        "C11_expected_injected_failure",
                    )
                else:
                    raise AssertionError("C11_fault_did_not_fail")
                require(
                    guard(
                        connection.cursor(),
                        ticket,
                        load(PACKAGE / "expected-shapes.json"),
                    )
                    == prefix,
                    "C11_atomic_unit_rollback",
                )
                results.append(
                    {
                        "unit": unit,
                        "case": "rollback_boundary_" + str(boundary),
                        "passed": True,
                    }
                )
            require(
                run(connection, ticket, audit, unit_id=unit) == "APPLIED",
                "C11_retry_after_rollback",
            )
        print(
            json.dumps(
                {
                    "phase": "faults",
                    "unit": unit,
                    "rollback_checks": 2,
                    "retry": "passed",
                }
            ),
            flush=True,
        )
    for fault in (
        "started",
        "started_rolled_back",
        "applied",
        "applied_rolled_back",
        "failure",
        "failure_rolled_back",
    ):
        name, ticket, state, audit = fault_trial(work)
        with admin(name, state["context"]) as connection:
            try:
                run(
                    connection,
                    ticket,
                    audit,
                    lose_ack=fault,
                    fail_at=2 if fault.startswith("failure") else None,
                )
            except CommitUnknown:
                pass
            else:
                raise AssertionError("C11_ACK_not_unknown")
            try:
                run(connection, ticket, audit)
            except ValueError as error:
                require(
                    str(error) == "C11_external_unknown", "C11_UNKNOWN_blocks_retry"
                )
            else:
                raise AssertionError("C11_UNKNOWN_replayed")
            if fault == "started":
                try:
                    reconcile(connection, ticket, audit, lose_ack="reconciled")
                except CommitUnknown:
                    pass
                else:
                    raise AssertionError("C11_reconciliation_ACK_not_unknown")
            if fault == "applied_rolled_back":
                try:
                    reconcile(
                        connection, ticket, audit, lose_ack="reconciled_rolled_back"
                    )
                except CommitUnknown:
                    pass
                else:
                    raise AssertionError("C11_reconciliation_rollback_ACK_not_unknown")
            reconcile(connection, ticket, audit)
            require(
                reconcile(connection, ticket, audit) == "ALREADY_RECORDED",
                "C11_reconciliation_idempotent",
            )
            prefix = guard(
                connection.cursor(), ticket, load(PACKAGE / "expected-shapes.json")
            )
            if prefix == 0:
                require(
                    run(connection, ticket, audit) == "APPLIED",
                    "C11_retry_after_reconciliation",
                )
            else:
                require(prefix == 1, "C11_reconciliation_prefix")
        results.append(
            {"case": fault, "UNKNOWN_blocks_replay": True, "reconciled": True}
        )
        print(
            json.dumps({"phase": "ACK", "case": fault, "reconciled": True}), flush=True
        )
    state = load(work / "state.json")
    trial = load(work / "trial-result.json")
    ticket = load(work / (trial["database"] + ".json"))
    drifts = [
        ("column", "ALTER TABLE crm_channels2.Context ADD UnexpectedColumn int NULL"),
        (
            "object_owner",
            "ALTER AUTHORIZATION ON OBJECT::crm_channels2.SecretVersion "
            "TO cbn_channels_migrator_c7",
        ),
        (
            "extra_permission",
            "GRANT SELECT ON SCHEMA::crm_channels2 TO cbn_channels_parity_migrator_c11",
        ),
        (
            "unknown_table",
            "CREATE TABLE crm_channels2.UnexpectedObject(Id int NOT NULL)",
        ),
        (
            "untrusted_FK",
            "ALTER TABLE crm_channels2.Application NOCHECK CONSTRAINT FK_C11_0",
        ),
    ]
    with admin(trial["database"], state["context"]) as connection:
        c = connection.cursor()
        for label, sql in drifts:
            c.execute("BEGIN TRANSACTION;")
            try:
                c.execute(sql)
                try:
                    guard(c, ticket, load(PACKAGE / "expected-shapes.json"))
                except ValueError:
                    results.append({"case": "drift_" + label, "blocked": True})
                else:
                    raise AssertionError("C11_drift_not_blocked_" + label)
            finally:
                c.execute("IF @@TRANCOUNT>0 ROLLBACK;")
    with admin("master", state["context"]) as connection:
        recovery = restore(
            connection.cursor(), state["backup"], state["context"], "RECOVERY"
        )
    with admin(recovery, state["context"], readonly=True) as connection:
        require(
            snapshot(connection) == state["sources"][C9], "C11_backup_recovery_exact"
        )
    require(
        protected_snapshots(state["context"]) == state["sources"],
        "C11_fault_sources_unchanged",
    )
    result = {
        "phase": "faults",
        "checks": results,
        "checks_passed": len(results),
        "recovery_database": recovery,
        "restored_before_release_exact": True,
        "protected_sources_unchanged": True,
        "no_database_dropped_or_replaced": True,
    }
    save(work / "faults-result.json", result)
    print(
        json.dumps(
            {
                "phase": "faults_complete",
                "checks": len(results),
                "recovery_exact": True,
                "sources_unchanged": True,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, required=True)
    check(parser.parse_args().work)
