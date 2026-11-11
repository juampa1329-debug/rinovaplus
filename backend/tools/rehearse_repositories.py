"""Explicit SQL-C4 runtime preparation/acceptance, only on the accepted restoration.

Run inside the existing local Docker test environment. Never starts the server,
workers or providers. Credentials stay in a separate encrypted private store.
"""

import argparse
import hashlib
import json
import secrets
import uuid
from dataclasses import replace
from pathlib import Path

import pyodbc
from fastapi.testclient import TestClient

from app import foundation
from app.config import Settings
from app.foundation_app import create_foundation_app
from app.sql_profile import SqlProfileStore
from app.sql_target import connection_string
from app.sql_workspace import ContactMutation, MessageMutation
from tools.cbn_foundation import current_history, successful_prefix
from tools.foundation_snapshot import (
    data_signature,
    metadata,
    quote_name,
    sha,
)
from tools.rehearse_foundation import (
    SOURCE,
    admin,
    capture,
    literal,
    load,
    private_profile,
    save,
)

C3 = Path("/tmp/cbn-c3/private/v2")


def check(condition, code):
    if not condition:
        raise RuntimeError(code)


def administrative_signature(connection):
    cursor = connection.cursor()
    cursor.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE; BEGIN TRANSACTION")
    try:
        result = {
            "metadata_sha256": sha(
                foundation.project_academic(metadata(cursor, managed=False))
            ),
            "data": data_signature(cursor),
        }
        cursor.execute("COMMIT; SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
        return result
    except BaseException:
        cursor.execute("IF @@TRANCOUNT>0 ROLLBACK")
        raise
    finally:
        cursor.close()


def runtime_settings(directory):
    profile = SqlProfileStore(directory / "runtime").load()
    check(profile is not None, "runtime_profile_missing")
    c, review = profile["connection"], profile["review"]
    check(
        c["database"] == foundation.DATABASE and c["username"] == foundation.PRINCIPAL,
        "runtime_profile_changed",
    )
    path = directory / "runtime-ticket.json"
    return Settings(
        mode="local_foundation",
        sql_environment="foundation_rehearsal",
        sql_host=c["server"],
        sql_port=c["port"],
        sql_database=c["database"],
        sql_user=c["username"],
        sql_password=c["password"],
        sql_certificate_hostname=c["certificate_hostname"],
        sql_expected_machine=review["machine"],
        sql_expected_server=review["server"],
        sql_expected_login=foundation.PRINCIPAL,
        sql_expected_database_user=foundation.PRINCIPAL,
        foundation_ticket_path=str(path),
        foundation_ticket_sha256=review["ticket_sha256"],
    )


def prepare(directory):
    check(
        not (directory / "runtime/profile.enc").exists(),
        "runtime_already_prepared_use_verify",
    )
    state, old_ticket = load(C3 / "state.json"), load(C3 / "trial-ticket.json")
    context = state["context"]
    check(
        old_ticket["identity"]["database"] == foundation.DATABASE, "wrong_restoration"
    )
    release, expected = foundation.assets()
    with admin(SOURCE, context, readonly=True) as connection:
        source = capture(connection)
    check(source == state["source_signature"], "source_changed_since_C3")
    with admin(foundation.DATABASE, context) as connection:
        cursor = connection.cursor()
        check(
            foundation.identity(cursor) == old_ticket["identity"],
            "restored_identity_changed",
        )
        check(sha(metadata(cursor, managed=True)) == sha(expected), "C3_shape_changed")
        check(
            successful_prefix(
                current_history(cursor, old_ticket, release, foundation.RELEASE_SHA)
            )
            == ["CBN-B000", "CBN-B001", "CBN-B006"],
            "C3_history_incomplete",
        )
        before = capture(connection)
        check(before == source, "restored_academics_changed")
        journal = foundation.journal_signature(cursor, expected)
        check(
            not cursor.execute(
                "SELECT 1 FROM sys.database_principals WHERE name=?",
                foundation.PRINCIPAL,
            ).fetchone(),
            "runtime_user_already_exists",
        )
    # All preconditions are read-only. These are the only new administrative writes.
    password = "C4!" + secrets.token_urlsafe(48)
    name = quote_name(foundation.PRINCIPAL)
    with admin("master", context) as connection:
        cursor = connection.cursor()
        check(
            not cursor.execute(
                "SELECT 1 FROM sys.server_principals WHERE name=?", foundation.PRINCIPAL
            ).fetchone(),
            "runtime_login_already_exists",
        )
        cursor.execute(
            f"CREATE LOGIN {name} WITH PASSWORD={literal(password)}, "
            f"DEFAULT_DATABASE={quote_name(foundation.DATABASE)},CHECK_POLICY=ON,CHECK_EXPIRATION=OFF"
        )
        sid = cursor.execute(
            "SELECT CONVERT(varchar(170),SUSER_SID(?),2)", foundation.PRINCIPAL
        ).fetchval()
    with admin(foundation.DATABASE, context) as connection:
        cursor = connection.cursor()
        cursor.execute(f"CREATE USER {name} FOR LOGIN {name} WITH DEFAULT_SCHEMA=crm")
        cursor.execute(f"GRANT CONNECT,VIEW DEFINITION TO {name}")
        cursor.execute(f"DENY {','.join(foundation.DENIED)} ON SCHEMA::dbo TO {name}")
        for table, permissions in foundation.RIGHTS.items():
            cursor.execute(
                f"GRANT {','.join(permissions)} ON OBJECT::{table} TO {name}"
            )
        check(
            administrative_signature(connection) == before,
            "academic_projection_changed",
        )
    value = {
        "scope": "SQL-C4-restored-repositories-only",
        "release_sha256": foundation.RELEASE_SHA,
        "identity": old_ticket["identity"],
        "login_sid": sid,
        "journal_sha256": journal,
    }
    save(directory / "runtime-ticket.json", value)
    ticket_hash = hashlib.sha256(
        (directory / "runtime-ticket.json").read_bytes()
    ).hexdigest()
    source_connection = private_profile()["connection"]
    SqlProfileStore(directory / "runtime").save(
        {
            "revision": 1,
            "connection": {
                **source_connection,
                "database": foundation.DATABASE,
                "username": foundation.PRINCIPAL,
                "password": password,
            },
            "review": {
                "machine": value["identity"]["machine"],
                "server": value["identity"]["server"],
                "ticket_sha256": ticket_hash,
            },
        }
    )
    save(
        directory / "baseline.json",
        {
            "source": source,
            "restored": before,
            "journal_sha256": journal,
            "context": context,
        },
    )
    settings = runtime_settings(directory)
    with create_foundation_app(settings).state.sql_workspace.transaction():
        pass
    return {
        "prepared": True,
        "scope": "accepted_restoration_only",
        "source_unchanged": True,
    }


def identifier():
    return str(uuid.uuid4())


def acceptance(directory):
    settings = runtime_settings(directory)
    baseline = load(directory / "baseline.json")
    application = create_foundation_app(settings)
    workspace = application.state.sql_workspace
    checks = []

    def accepted(condition, label):
        check(condition, label)
        checks.append(label)

    def post(client, path, value, status=200):
        response = client.post(path, json=value)
        accepted(response.status_code == status, "POST " + path + " " + str(status))
        return response.json()

    def put(client, path, value, status=200):
        response = client.put(path, json=value)
        accepted(response.status_code == status, "PUT " + path + " " + str(status))
        return response.json()

    def get(client, path):
        response = client.get(path)
        accepted(
            response.status_code == 200
            and response.headers.get("cache-control") == "no-store",
            "GET " + path,
        )
        return response.json()

    with TestClient(
        application,
        base_url="http://127.0.0.1:8000",
        client=("127.0.0.1", 7001),
        headers={"X-CRM-Local": "1"},
    ) as client:
        get(client, "/api/local/foundation")
        accepted(
            not any(
                hasattr(application.state, k)
                for k in (
                    "ai",
                    "event_worker",
                    "analysis_worker",
                    "channel_worker",
                    "campaign_worker",
                    "catalog_reader",
                )
            ),
            "no_workers_providers_catalog_or_synthetic_transport",
        )
        original = get(client, "/api/local/crm")
        recovered = None
        if len(original["clients"]) == 1 and not original["threads"][0]["messages"]:
            # Resume only the recorded initial test assertion failure; no reset,
            # deletion or weakening of operation hashes. Replay proves ownership.
            with workspace.transaction() as cursor:
                operations = cursor.execute(
                    "SELECT OperationId,Action FROM crm.Operation"
                ).fetchall()
                definitions = cursor.execute(
                    "SELECT OperationId FROM crm_config.Operation"
                ).fetchall()
                check(
                    len(operations) == len(definitions) == 1
                    and operations[0][1] == "create_contact",
                    "nonempty_rehearsal_requires_review",
                )
                recovered = (str(operations[0][0]), str(definitions[0][0]))
        accepted(
            (not original["clients"] and original["revision"] == "0")
            or recovered is not None,
            "fresh_restored_crm_or_exact_initial_seed_replay",
        )
        config_path = "/api/local/crm/configuration"
        get(client, config_path)
        body = {
            "operationId": recovered[1] if recovered else identifier(),
            "expectedRevision": "1",
            "config": {
                "stages": [{"key": "c4_trial", "label": "Ensayo C4"}],
                "tags": ["Ensayo C4"],
                "inactiveTags": [],
                "fields": [
                    {"key": "c4_note", "label": "Nota de ensayo", "type": "Text"}
                ],
            },
        }
        new_config = put(client, config_path, body)
        accepted(put(client, config_path, body) == new_config, "configuration_replay")
        changed = {**body, "config": {**body["config"], "tags": ["Otro ensayo"]}}
        put(client, config_path, changed, 409)
        put(client, config_path, {**body, "operationId": identifier()}, 409)
        contact_id = original["clients"][0]["id"] if recovered else identifier()
        conversation_id = original["threads"][0]["id"] if recovered else identifier()
        create = {
            "operationId": recovered[0] if recovered else identifier(),
            "expectedRevision": "0",
            "conversationId": conversation_id,
            "client": {
                "id": contact_id,
                "name": "Contacto sintético C4",
                "phone": "",
                "city": "",
                "programId": None,
                "program": "",
                "schedule": "",
                "stage": "Ensayo C4",
                "tags": "Ensayo C4",
                "notes": "Sólo ensayo local",
                "type": "",
                "interests": "",
                "customValues": {"c4_note": "prueba"},
            },
        }
        first = post(client, "/api/local/crm/clients", create, 201)
        accepted(
            int(first["revision"]) > 0
            and len(first["clients"]) == 1
            and len(first["threads"]) == 1,
            "contact_and_conversation_atomic",
        )
        accepted(
            post(client, "/api/local/crm/clients", create, 201) == first,
            "contact_replay_no_duplicate",
        )
        post(
            client,
            "/api/local/crm/clients",
            {**create, "operationId": identifier()},
            409,
        )
        post(
            client,
            "/api/local/crm/clients",
            {**create, "client": {**create["client"], "notes": "cambiado"}},
            409,
        )
        edited = {
            **create,
            "operationId": identifier(),
            "expectedRevision": first["revision"],
            "client": {**create["client"], "notes": "Nota editada"},
        }
        updated = put(client, "/api/local/crm/inbox/contacts/" + contact_id, edited)
        accepted(
            int(updated["revision"]) > int(first["revision"]),
            "inbox_contact_edit_shared_revision",
        )
        listed = get(
            client, "/api/local/crm/inbox?q=Contacto&channel=Local&stage=Ensayo%20C4"
        )
        accepted(
            len(listed["items"]) == 1 and listed["items"][0]["channel"] == "Local",
            "inbox_after_first_contact",
        )
        accepted(
            get(client, "/api/local/crm/inbox/options")["channels"] == ["Local"],
            "options_after_first_contact",
        )
        detail = get(client, "/api/local/crm/inbox/contacts/" + contact_id)
        accepted(
            detail["client"]["notes"] == "Nota editada" and not detail["destinations"],
            "detail_without_optional_tables",
        )
        message_path = (
            "/api/local/crm/inbox/conversations/" + conversation_id + "/messages"
        )
        message = {
            "operationId": identifier(),
            "expectedRevision": updated["revision"],
            "messageId": identifier(),
            "body": "Mensaje de ensayo local",
        }
        sent = post(client, message_path, message)
        accepted(
            post(client, message_path, message) == sent, "message_replay_no_duplicate"
        )
        accepted(
            get(client, message_path)["items"][0]["deliveryState"] == "local",
            "local_message_without_transport",
        )
        revision = sent["revision"]
        change = {
            "operationId": identifier(),
            "expectedRevision": revision,
            "state": "closed",
            "priority": "high",
            "assignee": "",
            "mode": "human",
            "unread": True,
        }
        conversation_path = "/api/local/crm/inbox/conversations/" + conversation_id
        closed = put(client, conversation_path, change)
        post(
            client,
            message_path,
            {
                **message,
                "operationId": identifier(),
                "messageId": identifier(),
                "expectedRevision": closed["revision"],
            },
            409,
        )
        revision = put(
            client,
            conversation_path,
            {
                **change,
                "operationId": identifier(),
                "expectedRevision": closed["revision"],
                "state": "open",
                "unread": False,
            },
        )["revision"]
        for extra in (
            {"mode": "ai"},
            {"assignee": "persona"},
            {"assessmentChanged": True},
            {"leadScore": 42},
            {"temperature": "warm"},
            {"readThroughSequence": "0"},
        ):
            put(
                client,
                conversation_path,
                {
                    **change,
                    "operationId": identifier(),
                    "expectedRevision": revision,
                    **extra,
                },
                503,
            )
        for extra in (
            {"mediaId": identifier()},
            {"delivery": "external", "identityId": identifier()},
        ):
            post(
                client,
                message_path,
                {
                    **message,
                    "operationId": identifier(),
                    "expectedRevision": revision,
                    **extra,
                },
                503,
            )
        for extra in (
            {"programId": 1, "program": "No mapear"},
            {"institutionalProfile": {}},
        ):
            put(
                client,
                "/api/local/crm/clients/" + contact_id,
                {
                    **edited,
                    "operationId": identifier(),
                    "expectedRevision": revision,
                    "client": {**edited["client"], **extra},
                },
                503,
            )
        for path in (
            "/api/local/admissions",
            "/api/v1/catalog/programs",
            "/api/v1/agents",
            "/api/v1/channels",
            "/api/v1/campaigns",
            "/api/ai/settings",
            "/api/local/clients",
            "/api/local/database",
        ):
            accepted(client.get(path).status_code == 503, "capability_blocked " + path)
        accepted(
            client.get("/api/local/crm", headers={"X-CRM-Local": "0"}).status_code
            == 403,
            "local_guard_required",
        )
        accepted(
            client.get("/health/ready").status_code == 503,
            "global_readiness_remains_incomplete",
        )
        # Roll back successful writes using the real restricted connection.
        try:
            with workspace.transaction(write=True) as cursor:
                rollback = MessageMutation.model_validate(
                    {
                        **message,
                        "operationId": identifier(),
                        "messageId": identifier(),
                        "expectedRevision": revision,
                    }
                )
                workspace.mutate_in(
                    cursor, "add_message", conversation_id, rollback, compact=True
                )
                raise RuntimeError("injected_after_write")
        except RuntimeError as error:
            accepted(str(error) == "injected_after_write", "rollback_fault_injected")
        accepted(
            get(client, "/api/local/crm")["revision"] == revision
            and len(get(client, message_path)["items"]) == 1,
            "rollback_data_and_operation_atomic",
        )
        # Seed boundary data through the same repository in one owned transaction.
        with workspace.transaction(write=True) as cursor:
            for index in range(25):
                payload = ContactMutation.model_validate(
                    {
                        **create,
                        "operationId": identifier(),
                        "expectedRevision": revision,
                        "conversationId": identifier(),
                        "client": {
                            **create["client"],
                            "id": identifier(),
                            "name": f"Ensayo paginado C4 {index}",
                        },
                    }
                )
                revision = workspace.mutate_in(
                    cursor, "create_contact", payload.client.id, payload, compact=True
                )["revision"]
            for index in range(51):
                payload = MessageMutation.model_validate(
                    {
                        **message,
                        "operationId": identifier(),
                        "expectedRevision": revision,
                        "messageId": identifier(),
                        "body": f"Ensayo página {index}",
                    }
                )
                revision = workspace.mutate_in(
                    cursor, "add_message", conversation_id, payload, compact=True
                )["revision"]
        page = get(client, "/api/local/crm/inbox")
        next_page = get(client, "/api/local/crm/inbox?offset=25")
        accepted(
            len(page["items"]) == 25
            and page["hasMore"]
            and len(next_page["items"]) == 1
            and not (
                {i["id"] for i in page["items"]} & {i["id"] for i in next_page["items"]}
            ),
            "inbox_pagination_boundary",
        )
        page = get(client, message_path)
        next_page = get(client, message_path + "?before=" + page["before"])
        accepted(
            len(page["items"]) == 50
            and page["hasMore"]
            and len(next_page["items"]) == 2
            and not (
                {i["id"] for i in page["items"]} & {i["id"] for i in next_page["items"]}
            ),
            "message_pagination_boundary",
        )
    # Negative SQL operations run in rollback-only transactions under the runtime login.
    for statement in (
        "SELECT TOP(0) * FROM dbo.ACProgramas",
        "DELETE crm.Contact WHERE 1=0",
        "UPDATE crm_meta.MigrationJournal SET ErrorCode=ErrorCode WHERE 1=0",
        "INSERT crm_meta.MigrationJournal(EventKind) VALUES('STARTED')",
        "CREATE TABLE crm.C4Forbidden(Id int)",
        "ALTER TABLE crm.Contact ADD C4Forbidden int",
    ):
        connection = pyodbc.connect(
            connection_string(settings), autocommit=False, timeout=5
        )
        try:
            try:
                connection.cursor().execute(statement)
            except pyodbc.Error as error:
                accepted(
                    "permission" in str(error).lower()
                    or "denied" in str(error).lower(),
                    "runtime_permission_denied " + statement.split()[0],
                )
            else:
                raise RuntimeError("runtime_excess_permission")
        finally:
            connection.rollback()
            connection.close()
    for bad in (
        replace(settings, sql_database=SOURCE),
        replace(settings, sql_user="sa"),
        replace(settings, sql_environment="institutional"),
    ):
        try:
            create_foundation_app(bad)
        except ValueError:
            accepted(True, "alternate_profile_blocked_before_connection")
        else:
            raise RuntimeError("alternate_profile_accepted")
    with admin(SOURCE, baseline["context"], readonly=True) as connection:
        accepted(
            capture(connection) == baseline["source"],
            "original_source_metadata_and_full_precision_data_unchanged",
        )
    with admin(foundation.DATABASE, baseline["context"]) as connection:
        accepted(
            administrative_signature(connection) == baseline["restored"],
            "all_academic_tables_data_and_preexisting_acl_unchanged",
        )
        accepted(
            foundation.journal_signature(connection.cursor(), foundation.assets()[1])
            == baseline["journal_sha256"],
            "migration_journal_unchanged",
        )
        connection.cursor().execute(
            "DBCC CHECKDB ("
            + quote_name(foundation.DATABASE)
            + ") WITH NO_INFOMSGS,ALL_ERRORMSGS"
        )
        accepted(True, "restored_checkdb")
    with workspace.transaction():
        accepted(True, "runtime_contract_after_writes")
    return {
        "scope": "restored_repositories_only",
        "database": foundation.DATABASE,
        "checks": checks,
        "checks_passed": len(checks),
        "synthetic_contacts": 26,
        "synthetic_messages": 52,
        "academic_tables_unchanged": 50,
        "academic_rows_verified": baseline["source"]["data"]["rows"],
        "source_unchanged": True,
        "journal_unchanged": True,
        "institutional_sql2019_accepted": False,
    }


def audit(directory):
    """Repeatable acceptance after CRUD, including reversible CRM-only drift probes."""
    from app.modules.catalog.domain.contracts import CatalogUnavailable

    settings = runtime_settings(directory)
    workspace = create_foundation_app(settings).state.sql_workspace
    baseline = load(directory / "baseline.json")
    checks = []

    def blocked(label):
        try:
            with workspace.transaction():
                pass
        except CatalogUnavailable:
            checks.append(label)
        else:
            raise RuntimeError("runtime_drift_was_accepted")

    with admin(foundation.DATABASE, baseline["context"]) as connection:
        cursor = connection.cursor()
        # Exact newly granted permission is revoked even if verification fails.
        cursor.execute(
            "GRANT DELETE ON OBJECT::crm.Message TO " + quote_name(foundation.PRINCIPAL)
        )
        try:
            blocked("real_overgrant_blocks_runtime")
        finally:
            cursor.execute(
                "REVOKE DELETE ON OBJECT::crm.Message FROM "
                + quote_name(foundation.PRINCIPAL)
            )
        cursor.execute("""EXEC sys.sp_addextendedproperty @name=N'c4.drift.probe',
          @value=N'synthetic',@level0type=N'SCHEMA',@level0name=N'crm'""")
        try:
            blocked("real_managed_metadata_drift_blocks_runtime")
        finally:
            cursor.execute("""EXEC sys.sp_dropextendedproperty @name=N'c4.drift.probe',
              @level0type=N'SCHEMA',@level0name=N'crm'""")
    for field in ("journal_sha256", "identity"):
        value = foundation.ticket(settings)
        if field == "identity":
            value["identity"]["database_id"] += 1
        else:
            value[field] = "0" * 64
        path = directory / "negative-ticket.json"
        save(path, value)
        alternate = replace(
            settings,
            foundation_ticket_path=str(path),
            foundation_ticket_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        original = workspace
        try:
            workspace = create_foundation_app(alternate).state.sql_workspace
            blocked("pinned_" + field + "_mismatch_blocks_runtime")
        finally:
            workspace = original
            path.unlink(missing_ok=True)
    with workspace.transaction() as cursor:
        check(
            cursor.execute("SELECT COUNT(*) FROM crm.Contact").fetchval() == 26,
            "synthetic_contact_count_changed",
        )
        check(
            cursor.execute("SELECT COUNT(*) FROM crm.Message").fetchval() == 52,
            "synthetic_message_count_changed",
        )
        checks.append("final_runtime_contract_and_synthetic_counts")
    with admin(SOURCE, baseline["context"], readonly=True) as connection:
        check(capture(connection) == baseline["source"], "source_changed")
        checks.append("source_full_precision_signature_unchanged")
    with admin(foundation.DATABASE, baseline["context"]) as connection:
        check(
            administrative_signature(connection) == baseline["restored"],
            "academics_changed",
        )
        check(
            foundation.journal_signature(connection.cursor(), foundation.assets()[1])
            == baseline["journal_sha256"],
            "journal_changed",
        )
        checks.extend(
            ["academic_signature_and_preexisting_acl_unchanged", "journal_unchanged"]
        )
    return {
        "checks": checks,
        "checks_passed": len(checks),
        "source_unchanged": True,
        "academic_tables_unchanged": 50,
        "journal_unchanged": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "verify", "audit"))
    parser.add_argument("--private-directory", type=Path, required=True)
    args = parser.parse_args()
    check(args.private_directory.is_absolute(), "absolute_private_directory_required")
    try:
        result = {"prepare": prepare, "verify": acceptance, "audit": audit}[
            args.action
        ](args.private_directory)
        save(args.private_directory / (args.action + "-result.json"), result)
        print(json.dumps(result, ensure_ascii=False))
    except Exception as error:
        # SQL errors can include identifiers or the DDL containing a password.
        # Retain only the exception type/code, never stringify SQL diagnostics.
        safe = str(error) if type(error) is RuntimeError else type(error).__name__
        print(json.dumps({"status": "blocked", "error": safe}))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
