"""Connected C7 fault scenarios on new isolated copies only. Explicit invocation."""

import argparse
import copy
import json
import uuid
from pathlib import Path

import pyodbc

from app import foundation
from app.foundation_profile import load_settings
from tools.cbn_foundation import Audit, acquire
from tools.crm_extension_snapshot_v2 import preservation, require, sha
from tools.crm_extension_v2 import (
    ACTOR,
    PACKAGE,
    SQL_FILE,
    CommitUnknown,
    assets,
    guard,
    reconcile,
    run,
    verified_state,
)
from tools.rehearse_crm_extension_v2 import (
    SOURCE,
    admin,
    capture,
    load,
    prepare_database,
    report,
    restore,
    save,
)
from tools.rehearse_foundation_ui import signatures


def passed(work, results, label):
    if label not in results:
        results.append(label)
    save(work / "connected-checks.json", results)
    print(
        json.dumps(
            {
                "stage": "SQL-C7",
                "check": label,
                "status": "passed",
                "completed": len(results),
            }
        ),
        flush=True,
    )


def new_case(work, state, label):
    require(label not in state.setdefault("case_tickets", {}), "case_already_exists")
    with admin("master", state["context"]) as master:
        name = restore(master.cursor(), state["backup"], state["context"], "FAULT")
    state["databases"].append({"kind": "FAULT", "name": name, "case": label})
    save(work / "state.json", state)
    with admin(name, state["context"]) as connection:
        ticket = prepare_database(connection, state["source"])
    ticket["release_sha256"] = assets()[1]
    state["case_tickets"][label] = ticket
    save(work / "state.json", state)
    return ticket


def expect_rejected(call, reason=None):
    try:
        call()
    except (ValueError, RuntimeError) as error:
        if reason is not None:
            require(reason in str(error), "wrong_rejection")
        return
    raise AssertionError("Unsafe state was accepted")


def rollback_case(connection, ticket, statements):
    cursor = connection.cursor()
    cursor.execute("BEGIN TRANSACTION;")
    acquire(cursor, "crm.local.commit", "Transaction")
    try:
        for statement in statements:
            cursor.execute(statement)
        release = assets()[0]
        expect_rejected(lambda: verified_state(cursor, ticket, release))
    finally:
        cursor.execute("IF @@TRANCOUNT>0 ROLLBACK;")
        cursor.close()
    require(verified_state(connection.cursor(), ticket, assets()[0]), "rollback_state")


def boundary_failures(work):
    state = load(work / "state.json")
    ticket = state["tickets"]["FAULT"]
    require(not (work / "connected-checks.json").exists(), "checks_already_started")
    results = []
    boundary_count = len((PACKAGE / SQL_FILE).read_text().split("-- C7_BOUNDARY")) + 2
    with admin(ticket["identity"]["database"], state["context"]) as connection:
        for index in range(boundary_count):
            try:
                run(connection, ticket, work / "boundary-audit.jsonl", fail_at=index)
            except RuntimeError as error:
                require(str(error).startswith("injected_"), "unexpected_unit_failure")
            else:
                raise AssertionError("Injected failure did not occur")
            require(
                not verified_state(connection.cursor(), ticket, assets()[0]),
                "failure_applied",
            )
            require(
                not Audit(
                    work / "boundary-audit.jsonl", sha(ticket["identity"])
                ).unresolved(),
                "failure_audit_unresolved",
            )
            passed(work, results, "rollback_boundary_" + str(index))
        try:
            run(connection, ticket, work / "boundary-audit.jsonl", lose_ack="applied")
        except CommitUnknown:
            pass
        else:
            raise AssertionError("Lost COMMIT acknowledgement was not blocked")
        expect_rejected(
            lambda: run(connection, ticket, work / "boundary-audit.jsonl"),
            "audit_requires_reconciliation",
        )
        require(
            reconcile(connection, ticket, work / "boundary-audit.jsonl")
            == "RECONCILED_COMMITTED",
            "reconcile_commit",
        )
        require(
            run(connection, ticket, work / "boundary-audit.jsonl") == "NOOP",
            "reconciled_noop",
        )
        passed(work, results, "committed_ack_reconciliation_after_all_boundaries")
    report(
        work,
        "boundary_failures",
        passed=len(results),
        ddl_and_journal_boundaries=boundary_count,
        academic_and_populated_crm_preserved=True,
    )


def acknowledgements(work):
    state = load(work / "state.json")
    results = load(work / "connected-checks.json")
    cases = [
        "started",
        "started_rolled_back",
        "applied",
        "applied_rolled_back",
        "failure",
        "failure_rolled_back",
    ]
    for label in cases:
        ticket = new_case(work, state, "ack_" + label)
        audit_path = work / ("ack-" + label + ".jsonl")
        with admin(ticket["identity"]["database"], state["context"]) as connection:
            try:
                run(
                    connection,
                    ticket,
                    audit_path,
                    lose_ack=label,
                    fail_at=1 if label.startswith("failure") else None,
                )
            except CommitUnknown:
                pass
            else:
                raise AssertionError("ACK loss did not quarantine")
            expect_rejected(
                lambda: run(connection, ticket, audit_path),
                "audit_requires_reconciliation",
            )
            outcome = reconcile(connection, ticket, audit_path)
            expected = (
                "RECONCILED_COMMITTED"
                if label == "applied"
                else "NO_SQL_ATTEMPT"
                if label == "started_rolled_back"
                else "ALREADY_RECORDED"
                if label == "failure"
                else "RECONCILED_NOT_APPLIED"
            )
            require(outcome == expected, "wrong_reconciliation_outcome")
            applied = run(connection, ticket, audit_path)
            require(
                applied == ("NOOP" if label == "applied" else "APPLIED"),
                "replay_outcome",
            )
            require(run(connection, ticket, audit_path) == "NOOP", "repeat_noop")
            require(
                preservation(connection.cursor()) == state["source"]["preservation"],
                "ack_data_changed",
            )
            passed(work, results, "ack_" + label)
    for fault in ("reconciled", "reconciled_rolled_back"):
        ticket = new_case(work, state, "ack_" + fault)
        audit_path = work / ("ack-" + fault + ".jsonl")
        with admin(ticket["identity"]["database"], state["context"]) as connection:
            try:
                run(connection, ticket, audit_path, lose_ack="applied")
            except CommitUnknown:
                pass
            else:
                raise AssertionError("Expected uncertain apply")
            try:
                reconcile(connection, ticket, audit_path, lose_ack=fault)
            except CommitUnknown:
                pass
            else:
                raise AssertionError("Expected uncertain reconciliation")
            expect_rejected(
                lambda: run(connection, ticket, audit_path),
                "audit_requires_reconciliation",
            )
            result = reconcile(connection, ticket, audit_path)
            require(
                result
                == (
                    "ALREADY_RECORDED"
                    if fault == "reconciled"
                    else "RECONCILED_COMMITTED"
                ),
                "reconciliation_repeat",
            )
            require(
                run(connection, ticket, audit_path) == "NOOP", "reconciliation_noop"
            )
            passed(work, results, "ack_" + fault)
    report(
        work,
        "acknowledgements",
        cases=8,
        all_unknown_outcomes_reconciled=True,
        no_duplicate_ddl_or_success=True,
    )


def drift_and_privileges(work):
    state = load(work / "state.json")
    ticket = state["tickets"]["TRIAL"]
    results = load(work / "connected-checks.json")
    mutations = {
        "filtered_index": [
            "DROP INDEX IX_Channels_Queue_Message ON crm_channels.outbound_queue;",
            "CREATE UNIQUE INDEX IX_Channels_Queue_Message ON "
            "crm_channels.outbound_queue(MessageId) WHERE MessageId IS NULL;",
        ],
        "untrusted_fk": [
            "ALTER TABLE crm_channels.ExternalIdentity NOCHECK CONSTRAINT "
            "FK_Channels_Identity_Contact;"
        ],
        "check_semantics": [
            "ALTER TABLE crm_channels.outbound_queue DROP CONSTRAINT "
            "CK_Channels_Queue_State;",
            "ALTER TABLE crm_channels.outbound_queue ADD CONSTRAINT "
            "CK_Channels_Queue_State CHECK(1=1);",
        ],
        "extra_empty_schema": ["CREATE SCHEMA crm_unknown_c7 AUTHORIZATION dbo;"],
        "extra_module": ["CREATE VIEW crm_channels.Unexpected AS SELECT 1 AS value;"],
        "extra_synonym": ["CREATE SYNONYM crm_channels.Unexpected FOR crm.Contact;"],
        "metadata_visibility": ["REVOKE VIEW DEFINITION FROM " + ACTOR + ";"],
        "inherited_role": ["ALTER ROLE db_datareader ADD MEMBER " + ACTOR + ";"],
        "public_impersonation": [
            "GRANT IMPERSONATE ON USER::cbn_foundation_migrator TO public;"
        ],
        "original_actor_acl": [
            "GRANT IMPERSONATE ON USER::" + ACTOR + " TO cbn_foundation_migrator;"
        ],
    }
    with admin(ticket["identity"]["database"], state["context"]) as connection:
        for label, statements in mutations.items():
            rollback_case(connection, ticket, statements)
            passed(work, results, "reject_" + label)
        wrong = copy.deepcopy(ticket)
        wrong["identity"]["database"] = SOURCE
        expect_rejected(lambda: guard(connection.cursor(), wrong), "target_name")
        passed(work, results, "reject_original_destination")
        old_settings = load_settings(Path(state["runtime_directory"]))
        expect_rejected(lambda: foundation.verify(connection.cursor(), old_settings))
        passed(work, results, "C5_ticket_refuses_extended_copy")
        # Binary SQL values differ at the seventh digit; no academic or CRM writes.
        row = (
            connection.cursor()
            .execute("""SELECT CONVERT(varbinary(max),
          CONVERT(datetime2(7),'2026-01-01T00:00:00.0000001')),
          CONVERT(varbinary(max),CONVERT(datetime2(7),'2026-01-01T00:00:00.0000002'))""")
            .fetchone()
        )
        require(row[0] != row[1], "binary_datetime_precision")
        passed(work, results, "binary_datetime2_seventh_digit")
    report(
        work,
        "drift_privileges",
        cases=13,
        all_rejected_or_verified=True,
        no_academic_ddl_dml_or_acl_tests=True,
    )


def constraints(work):
    state = load(work / "state.json")
    ticket = state["tickets"]["TRIAL"]
    results = load(work / "connected-checks.json")
    with admin(ticket["identity"]["database"], state["context"]) as connection:
        row = (
            connection.cursor()
            .execute(
                "SELECT TOP(1) c.ContactId,v.ConversationId "
                "FROM crm.Contact c JOIN crm.Conversation v ON v.ContactId=c.ContactId"
            )
            .fetchone()
        )
        require(row is not None, "synthetic_crm_parent_required")
        contact, conversation = str(row[0]), str(row[1])
        message = str(
            connection.cursor()
            .execute("SELECT TOP(1) MessageId FROM crm.Message")
            .fetchval()
        )

        def account(c):
            c.execute(
                "INSERT crm_channels.Account(Channel,Configuration) VALUES('whatsap"
                "p',N'{}');"
            )

        def credential(c):
            account(c)
            c.execute(
                "INSERT crm_channels.Credential(Channel,Kind,KeyId,Nonce,Ciphertext) "
                "VALUES('whatsapp','test','synthetic',?,?)",
                bytes(12),
                bytes(1),
            )

        def identity(c, external):
            c.execute(
                "INSERT crm_channels.ExternalIdentity(IdentityId,Channel,ExternalId"
                ",ContactId,ConversationId) "
                "VALUES(?,'whatsapp',?,?,?)",
                str(uuid.uuid4()),
                external,
                contact,
                conversation,
            )

        def identity_pair(c):
            account(c)
            identity(c, "OpaqueX")
            identity(c, "opaquex")

        def external_message(c, external):
            c.execute(
                "INSERT crm_channels.ExternalMessage(Channel,ExternalId,Payload) "
                "VALUES('whatsapp',?,N'{}')",
                external,
            )

        def message_pair(c):
            account(c)
            external_message(c, "MsgX")
            external_message(c, "msgx")

        def comment(c, external, author):
            c.execute(
                "INSERT crm_channels.social_comments(CommentId,Channel,ExternalId,A"
                "uthorId,Body,Payload) "
                "VALUES(?,'whatsapp',?,?,N'synthetic',N'{}')",
                str(uuid.uuid4()),
                external,
                author,
            )

        def comment_pair(c):
            account(c)
            comment(c, "CommentX", "AuthorX")
            comment(c, "commentx", "authorx")
            require(
                c.execute(
                    "SELECT COUNT(*) FROM crm_channels.social_comments WHERE Author"
                    "Id=N'authorx'"
                ).fetchval()
                == 1,
                "author_identifier_not_bin2",
            )

        def queue(c, message_id=None, state="queued"):
            c.execute(
                "INSERT crm_channels.outbound_queue(QueueId,Channel,MessageId,Paylo"
                "ad,State) "
                "VALUES(?,'whatsapp',?,N'{}',?)",
                str(uuid.uuid4()),
                message_id,
                state,
            )

        def queue_setup(c):
            account(c)
            queue(c)
            queue(c)
            queue(c, message)

        checks = [
            (
                "channel_enum",
                lambda c: None,
                lambda c: c.execute(
                    "INSERT crm_channels.Account(Channel,Configuration) VALUES('inv"
                    "alid',N'{}')"
                ),
            ),
            (
                "account_json",
                lambda c: None,
                lambda c: c.execute(
                    "INSERT crm_channels.Account(Channel,Configuration) VALUES('wha"
                    "tsapp',N'invalid')"
                ),
            ),
            (
                "internal_foreign_key",
                lambda c: None,
                lambda c: c.execute(
                    "INSERT crm_channels.Credential(Channel,Kind,KeyId,Nonce,Cipher"
                    "text) VALUES('whatsapp','test','synthetic',?,?)",
                    bytes(12),
                    bytes(1),
                ),
            ),
            (
                "webhook_json",
                lambda c: None,
                lambda c: c.execute(
                    "INSERT crm_channels.webhook_events(EventId,Provider,Digest,Pay"
                    "load) VALUES(?,'test',?,N'invalid')",
                    str(uuid.uuid4()),
                    bytes(32),
                ),
            ),
            ("queue_state", account, lambda c: queue(c, state="invalid")),
            ("identity_bin2_unique", identity_pair, lambda c: identity(c, "OpaqueX")),
            (
                "message_bin2_primary_key",
                message_pair,
                lambda c: external_message(c, "MsgX"),
            ),
            (
                "comments_and_author_bin2",
                comment_pair,
                lambda c: comment(c, "CommentX", "AuthorX"),
            ),
            ("filtered_message_uniqueness", queue_setup, lambda c: queue(c, message)),
            (
                "delete_no_action",
                credential,
                lambda c: c.execute(
                    "DELETE crm_channels.Account WHERE Channel='whatsapp'"
                ),
            ),
        ]
        for label, setup, invalid in checks:
            cursor = connection.cursor()
            cursor.execute("SET XACT_ABORT ON; BEGIN TRANSACTION;")
            try:
                setup(cursor)
                try:
                    invalid(cursor)
                except pyodbc.IntegrityError as error:
                    require(error.args[0] == "23000", "wrong_integrity_error")
                else:
                    raise AssertionError("SQL integrity rule did not reject")
            finally:
                cursor.execute("IF @@TRANCOUNT>0 ROLLBACK;")
                cursor.close()
            require(
                verified_state(connection.cursor(), ticket, assets()[0]),
                "constraint_rollback_state",
            )
            passed(work, results, "constraint_" + label)
        cursor = connection.cursor()
        cursor.execute("BEGIN TRANSACTION;")
        cursor.execute(
            "INSERT crm_channels.Audit(Channel,Action) VALUES('test','synthetic rol"
            "lback')"
        )
        cursor.execute("ROLLBACK;")
        require(
            cursor.execute(
                "SELECT CONVERT(nvarchar(100),last_value) FROM sys.identity_columns "
                "WHERE object_id=OBJECT"
                "_ID('crm_channels.Audit')"
            ).fetchval()
            is not None,
            "audit_identity_was_reset",
        )
        require(verified_state(cursor, ticket, assets()[0]), "audit_gap_state")
        cursor.close()
        passed(work, results, "audit_identity_gap_preserved")
    report(
        work,
        "constraints",
        cases=11,
        all_test_rows_rolled_back=True,
        extension_rows=0,
        academic_and_populated_crm_unchanged=True,
    )


def locks(work):
    state = load(work / "state.json")
    ticket = state["tickets"]["TRIAL"]
    results = load(work / "connected-checks.json")
    for resource, owner in (
        ("crm.schema.migrate.v1", "Session"),
        ("crm.local.commit", "Transaction"),
    ):
        with admin(ticket["identity"]["database"], state["context"]) as first:
            cursor = first.cursor()
            if owner == "Transaction":
                cursor.execute("BEGIN TRANSACTION;")
            acquire(cursor, resource, owner)
            try:
                with admin(ticket["identity"]["database"], state["context"]) as second:
                    expect_rejected(
                        lambda: run(second, ticket, work / "lock-audit.jsonl"),
                        "migration_lock_unavailable",
                    )
            finally:
                if owner == "Transaction":
                    cursor.execute("ROLLBACK;")
                else:
                    cursor.execute(
                        "EXEC sys.sp_releaseapplock @Resource=?,@LockOwner='Session';",
                        resource,
                    )
            require(
                verified_state(first.cursor(), ticket, assets()[0]), "lock_data_changed"
            )
        passed(work, results, "exclusive_lock_" + owner.lower())
    report(work, "locks", independent_connections=2, writer_and_migrator_excluded=True)


def final(work):
    state = load(work / "state.json")
    current = signatures(state["context"], Path(state["runtime_directory"]))
    require(
        all(
            current[k] == state["c5_signatures"][k]
            for k in ("source", "academic", "journal", "crm_counts")
        ),
        "source_or_C5_runtime_changed",
    )
    with admin(SOURCE, state["context"], readonly=True) as connection:
        require(capture(connection) == state["source"], "C5_populated_source_changed")
    with admin(
        state["tickets"]["TRIAL"]["identity"]["database"],
        state["context"],
        readonly=True,
    ) as connection:
        require(
            verified_state(connection.cursor(), state["tickets"]["TRIAL"], assets()[0]),
            "trial_final",
        )
    results = load(work / "connected-checks.json")
    phases = {
        name: load(work / (name + "-result.json"))
        for name in (
            "boundary_failures",
            "acknowledgements",
            "drift_privileges",
            "constraints",
            "locks",
        )
    }
    expected = (
        phases["boundary_failures"]["passed"] + phases["acknowledgements"]["cases"]
    )
    expected += phases["drift_privileges"]["cases"] + phases["constraints"]["cases"] + 2
    require(
        len(results) == len(set(results)) == expected, "incomplete_or_duplicate_checks"
    )
    report(
        work,
        "final",
        connected_checks=len(results),
        restored_databases=len(state["databases"]),
        source_and_C5_unchanged=True,
        academic_tables=50,
        academic_rows=44180,
        populated_crm_rows=199,
        original_journal_rows_unchanged=5,
        trial_journal_rows=7,
        extension_tables=8,
        extension_rows=0,
        workers=0,
        provider_calls=0,
        institutional_sql2019_accepted=False,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=("boundaries", "acks", "drift", "constraints", "locks", "final"),
    )
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    {
        "boundaries": boundary_failures,
        "acks": acknowledgements,
        "drift": drift_and_privileges,
        "constraints": constraints,
        "locks": locks,
        "final": final,
    }[args.action](args.work)
