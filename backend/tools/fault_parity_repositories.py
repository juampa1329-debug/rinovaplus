"""Explicit C12 fault tests, recovery restore and final preservation checks."""

import argparse
import json
from pathlib import Path

from cryptography.exceptions import InvalidTag
from fastapi import HTTPException

from app.parity_channels.guard import transaction
from app.parity_channels.policy import principal, require
from app.parity_channels.profile import load as settings_load
from tools.channels_parity_snapshot import OLD_TABLES
from tools.foundation_snapshot import quote_name
from tools.parity_data import full_snapshot, signature
from tools.rehearse_parity_repositories import (
    admin,
    load,
    restore,
    run_import,
    save,
    sources,
)


def check(work):
    state = load(work / "state.json")
    settings = settings_load(Path(state["profile_directory"]))
    name = state["database"]
    user = quote_name(principal(name))
    passed = []

    def expect(value, label):
        require(value, "C12_fault_" + label)
        passed.append(label)
        print(json.dumps({"fault_passed": label}), flush=True)

    def blocked():
        try:
            with transaction(settings):
                pass
        except HTTPException as error:
            return (
                error.status_code == 503
                and error.detail == "parity_storage_unavailable"
            )
        return False

    for label, apply, undo in (
        (
            "column_secret_escalation",
            "GRANT SELECT ON OBJECT::crm_channels2.SecretVersion(Ciphertext) TO "
            + user,
            "REVOKE SELECT ON OBJECT::crm_channels2.SecretVersion(Ciphertext) FROM "
            + user,
        ),
        (
            "role_escalation",
            "ALTER ROLE db_datareader ADD MEMBER " + user,
            "ALTER ROLE db_datareader DROP MEMBER " + user,
        ),
        (
            "extra_grant_other_actor",
            "GRANT SELECT ON OBJECT::crm_channels2.Context TO public",
            "REVOKE SELECT ON OBJECT::crm_channels2.Context FROM public",
        ),
        (
            "extra_schema_property",
            (
                "EXEC sys.sp_addextendedproperty @name=N'c12.fault'"
                ",@value=N'probe',@level0type=N'SCHEMA',@level0name"
                "=N'crm_channels2';"
            ),
            (
                "EXEC sys.sp_dropextendedproperty @name=N'c12.fault"
                "',@level0type=N'SCHEMA',@level0name=N'crm_channels"
                "2';"
            ),
        ),
        (
            "context_contract_drift",
            (
                "UPDATE crm_channels2.Context SET "
                "ContractVersion='c12-fault' WHERE ContextId=1;"
            ),
            (
                "UPDATE crm_channels2.Context SET "
                "ContractVersion='CBN-channels-parity-v1' WHERE "
                "ContextId=1;"
            ),
        ),
    ):
        # The academic objects and old CRM rows are never mutation targets.
        if label == "context_contract_drift":
            with admin(name, state["context"], True) as c:
                original = (
                    c.cursor()
                    .execute(
                        (
                            "SELECT ContractVersion FROM crm_channels2.Context "
                            "WHERE ContextId=1"
                        )
                    )
                    .fetchval()
                )
            undo = (
                "UPDATE crm_channels2.Context SET ContractVersion="
                + "N'"
                + original.replace("'", "''")
                + "' WHERE ContextId=1;"
            )
        with admin(name, state["context"]) as c:
            c.cursor().execute(apply)
        try:
            expect(blocked(), label)
        finally:
            with admin(name, state["context"]) as c:
                c.cursor().execute(undo)
        with transaction(settings):
            pass
    with admin(name, state["context"]) as c:
        expect(
            run_import(c, work)["status"] == "noop",
            "replay_after_runtime_configuration",
        )
        cursor = c.cursor()
        cursor.execute("BEGIN TRANSACTION;")
        try:
            cursor.execute(
                (
                    "UPDATE crm_channels2.LegacyBinding SET "
                    "TargetKeyJson=N'[]' WHERE "
                    "LegacyTable='crm_channels.outbound_queue'"
                )
            )
            from tools.parity_mapping import import_rows

            try:
                import_rows(cursor, work)
            except ValueError as error:
                expect(
                    str(error) == "C12_binding_target_substitution",
                    "binding_target_substitution",
                )
            else:
                raise ValueError("C12_corrupt_binding_accepted")
        finally:
            cursor.execute("IF @@TRANCOUNT>0 ROLLBACK;")
    keypath = work / "vault.key"
    key = keypath.read_bytes()
    try:
        keypath.write_bytes(b"0" * 32)
        with admin(name, state["context"]) as c:
            try:
                run_import(c, work)
            except InvalidTag:
                expect(True, "wrong_vault_key_rejected")
            else:
                raise ValueError("C12_wrong_key_accepted")
    finally:
        keypath.write_bytes(key)
    bodypath = work / "receipt.key"
    bodykey = bodypath.read_bytes()
    try:
        bodypath.write_bytes(b"1" * 32)
        with admin(name, state["context"]) as c:
            try:
                run_import(c, work)
            except InvalidTag:
                expect(True, "wrong_receipt_key_rejected")
            else:
                raise ValueError("C12_wrong_receipt_key_accepted")
    finally:
        bodypath.write_bytes(bodykey)
    for label, sql, code in (
        (
            "immutable_identity_content",
            (
                "UPDATE crm_channels2.ExternalIdentity SET "
                "ExternalId='C12-fault-identity';"
            ),
            "C12_immutable_target_content_drift",
        ),
        (
            "immutable_external_account",
            (
                "UPDATE crm_channels2.Integration SET "
                "ExternalAccountId='C12-fault-account' WHERE "
                "Channel='tiktok';"
            ),
            "C12_account_immutable_configuration",
        ),
    ):
        with admin(name, state["context"]) as c:
            cursor = c.cursor()
            cursor.execute("BEGIN TRANSACTION;")
            try:
                cursor.execute(sql)
                try:
                    import_rows(cursor, work)
                except ValueError as error:
                    expect(str(error) == code, label)
                else:
                    raise ValueError("C12_immutable_content_accepted")
            finally:
                cursor.execute("IF @@TRANCOUNT>0 ROLLBACK;")
    # Missing imported key must never be regenerated on replay.
    parked = work / "vault.test-parked"
    require(not parked.exists(), "C12_key_parking_collision")
    keypath.rename(parked)
    try:
        with admin(name, state["context"]) as c:
            try:
                run_import(c, work)
            except ValueError as error:
                expect(
                    str(error) == "C12_missing_import_key",
                    "missing_vault_key_not_regenerated",
                )
            else:
                raise ValueError("C12_missing_key_accepted")
    finally:
        parked.rename(keypath)
    with transaction(settings):
        pass
    with admin(name, state["context"], True) as c:
        expect(
            signature(c.cursor(), OLD_TABLES) == state["old_data"],
            "all65_old_tables_after_faults",
        )
    # Reversal means a separate exact recovery, no destructive DOWN/reset.
    with admin("master", state["context"]) as c:
        recovery = restore(c.cursor(), state["backup"], state["context"], "FAULT")
    with admin(recovery, state["context"], True) as c:
        expect(full_snapshot(c) == state["source"], "recovery_exact_C11_backup")
    expect(
        sources(state["context"]) == state["sources"],
        "SIIE_C5_C9_C11_final_preservation",
    )
    state.update(fault_checks=passed, recovery_database=recovery)
    save(work / "state.json", state)
    print(
        json.dumps(
            {
                "phase": "faults_and_recovery",
                "passed": len(passed),
                "recovery_database": recovery,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--work", type=Path, required=True)
    check(p.parse_args().work)
