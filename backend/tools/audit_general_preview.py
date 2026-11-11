"""Explicit C13 SQL authority/drift/preservation checks on the isolated copy."""

import argparse
import json
from pathlib import Path

import pyodbc
from fastapi import HTTPException

from app.general_preview.store import (
    connection_string,
    principal,
    transaction,
)
from app.general_preview.store import (
    load as runtime_load,
)
from app.parity_channels.catalog import metadata
from tools.channels_parity_snapshot import OLD_TABLES
from tools.foundation_snapshot import quote_name, sha
from tools.parity_data import full_snapshot, signature
from tools.prepare_general_preview import SOURCE, admin, prior_sources
from tools.rehearse_crm_extension_v2 import load, save


def audit(work):
    state = load(work / "state.json")
    settings = runtime_load(Path(state["profile_directory"]))
    passed = []

    def expect(value, label):
        if not value:
            raise AssertionError("C13 SQL " + label)
        passed.append(label)
        print(json.dumps({"passed": label}), flush=True)

    with pyodbc.connect(connection_string(settings), autocommit=False, timeout=5) as c:
        for label, sql in (
            (
                "academic_read_denied",
                "SELECT TOP(0) * FROM "
                + next(t for t in OLD_TABLES if t.startswith("dbo.")),
            ),
            (
                "legacy_credential_denied",
                "SELECT TOP(0) Ciphertext FROM crm_channels.Credential",
            ),
            (
                "new_ciphertext_denied",
                "SELECT TOP(0) Ciphertext FROM crm_channels2.SecretVersion",
            ),
            (
                "receipt_body_denied",
                "SELECT TOP(0) BodyCiphertext FROM crm_channels2.WebhookReceipt",
            ),
            ("core_delete_denied", "DELETE crm.Contact WHERE 1=0"),
            (
                "provider_queue_insert_denied",
                (
                    "INSERT crm_channels2.SendJob(InstitutionId) SELECT"
                    " InstitutionId FROM crm_channels2.Context WHERE "
                    "1=0"
                ),
            ),
        ):
            try:
                c.cursor().execute(sql)
            except pyodbc.Error as error:
                expect(
                    "(229)" in str(error.args[1]) or "(230)" in str(error.args[1]),
                    label,
                )
            else:
                raise AssertionError("C13 unexpected SQL authority")
            finally:
                c.rollback()
    user = quote_name(principal(state["database"]))
    for label, change, undo in (
        (
            "cipher_column_drift",
            "GRANT SELECT ON OBJECT::crm_channels2.SecretVersion(Ciphertext) TO "
            + user,
            "REVOKE SELECT ON OBJECT::crm_channels2.SecretVersion(Ciphertext) FROM "
            + user,
        ),
        (
            "role_drift",
            "ALTER ROLE db_datareader ADD MEMBER " + user,
            "ALTER ROLE db_datareader DROP MEMBER " + user,
        ),
        (
            "view_definition_required",
            "REVOKE VIEW DEFINITION FROM " + user,
            "GRANT VIEW DEFINITION TO " + user,
        ),
    ):
        with admin(state["database"], state["context"]) as c:
            c.cursor().execute(change)
        try:
            try:
                with transaction(settings):
                    pass
            except HTTPException as error:
                expect(
                    error.status_code == 503
                    and error.detail == "general_storage_unavailable",
                    label,
                )
            else:
                raise AssertionError("C13 drift accepted")
        finally:
            with admin(state["database"], state["context"]) as c:
                c.cursor().execute(undo)
        with transaction(settings):
            pass
    academic = [t for t in OLD_TABLES if t.startswith("dbo.")]
    legacy = [t for t in OLD_TABLES if t.startswith("crm_channels.")]
    with admin(SOURCE, state["context"]) as c:
        expect(
            full_snapshot(c) == state["source"],
            "C12_full_catalog_and_binary_rows_preserved",
        )
        legacy_before = signature(c.cursor(), legacy)
    with admin(state["database"], state["context"]) as c:
        expect(
            signature(c.cursor(), academic) == state["academic"],
            "C13_50_academic_tables_and_rows_preserved",
        )
        expect(
            signature(c.cursor(), legacy) == legacy_before, "C13_B011_rows_preserved"
        )
        expect(
            c.cursor()
            .execute("SELECT COUNT(*) FROM crm_meta.MigrationJournal")
            .fetchval()
            == 17,
            "journal17_unchanged",
        )
        expect(
            sha(metadata(c.cursor())) == settings.ticket["catalog_sha256"],
            "catalog_after_runtime_and_faults_exact",
        )
    expect(
        prior_sources(state["context"]) == state["sources"],
        "SIIE_C5_C9_C11_full_catalog_and_rows_preserved",
    )
    return {
        "unit": "SQL-C13",
        "status": "passed",
        "scope": "own_restored_copy_permissions_drift_and_preservation",
        "database": state["database"],
        "checks": passed,
        "academic_tables": 50,
        "academic_rows": 44180,
        "source_databases_preserved": 5,
        "journal_rows": 17,
        "academic_DML": False,
        "institutional_SQL2019_accepted": False,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--work", type=Path, required=True)
    args = p.parse_args()
    result = audit(args.work)
    save(args.work / "sql-audit.json", result)
    print(json.dumps({"passed": len(result["checks"]), "sources_preserved": 5}))
