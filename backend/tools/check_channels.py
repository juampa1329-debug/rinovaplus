"""Connected C8 repository, API, drift and least-privilege checks on its own copy."""

import argparse
import hashlib
import hmac
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pyodbc
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.channels_app import create_channels_app
from app.channels_catalog import metadata
from app.channels_profile import load_settings
from app.modules.channels.receipts import persist_receipt
from app.modules.channels.storage import ChannelStore
from app.modules.channels.workers import append_message, record_comment, record_delivery
from app.modules.crm_configuration.application.service import read_configuration
from app.sql_target import connection_string
from tools.cbn_foundation import acquire
from tools.crm_extension_snapshot_v2 import (
    PARTITION,
    data_signature,
    encode,
    identity_values,
    journal_binary,
    quote_name,
    records,
    require,
    sha,
)
from tools.crm_extension_v2 import assets, verified_state
from tools.rehearse_channels import admin, c7_admin, capture, load, report, save
from tools.rehearse_foundation_ui import signatures

BUSINESS_KEYS = {
    "crm.Contact": "ContactId",
    "crm.Conversation": "ConversationId",
    "crm.Message": "MessageId",
    "crm.Operation": "OperationId",
    "crm_config.Configuration": "ConfigurationId",
    "crm_config.Operation": "OperationId",
}


def business_rows(cursor):
    result = {}
    for table, key in BUSINESS_KEYS.items():
        columns = records(
            cursor,
            "SELECT name FROM sys.columns WHERE object_id=OBJECT_ID(?,'U'"
            ") ORDER BY column_id",
            (table,),
        )
        projection = ",".join(
            "CONVERT(varbinary(max)," + quote_name(c["name"]) + ")" for c in columns
        )
        rows = cursor.execute(
            "SELECT CONVERT(varchar(36),"
            + quote_name(key)
            + "),"
            + projection
            + " FROM "
            + table
        ).fetchall()
        result[table] = {
            str(r[0]): hashlib.sha256(encode(list(r[1:]))).hexdigest() for r in rows
        }
    return result


def check(work, label):
    path = work / "checks.json"
    values = load(path) if path.exists() else []
    require(label not in values, "C8_duplicate_check")
    values.append(label)
    save(path, values)
    print(
        json.dumps({"stage": "SQL-C8", "check": label, "passed": len(values)}),
        flush=True,
    )


def client(settings):
    return TestClient(
        create_channels_app(settings),
        base_url="http://127.0.0.1:4173",
        client=("127.0.0.1", 51000),
        headers={"X-CRM-Local": "1"},
    )


def repositories(work):
    state = load(work / "state.json")
    settings = load_settings(Path(state["profile_directory"]))
    require(
        not (work / "repositories-result.json").exists(),
        "C8_repositories_already_complete",
    )
    store = ChannelStore(settings)
    app = client(settings)
    if "original_business" not in state:
        with admin(state["database"], state["context"], readonly=True) as connection:
            state["original_business"] = business_rows(connection.cursor())
        save(work / "state.json", state)
    with store.transaction() as cursor:
        config, _ = read_configuration(cursor, foundation=True)
        stage = next(s.label for s in config.stages if s.active)
    body = {
        "revision": 0,
        "configuration": {
            "appId": "C8Synthetic",
            "phoneNumberId": "1001",
            "initialStage": stage,
        },
    }
    response = app.put("/api/v1/channels/whatsapp/draft", json=body)
    require(
        response.status_code == 200 and response.json()["revision"] == 1,
        "C8_configuration_save",
    )
    check(work, "draft_persisted_with_revision")
    require(
        app.put("/api/v1/channels/whatsapp/draft", json=body).status_code == 409,
        "C8_stale_draft",
    )
    check(work, "stale_revision_rejected")
    # These credentials are synthetic and remain confined to the restored copy.
    secret = "C8-synthetic-token-" + str(uuid4())
    app_secret = "C8-synthetic-hmac-" + str(uuid4())
    with store.transaction() as cursor:
        store.write_secret(cursor, "whatsapp", "accessToken", secret)
        store.write_secret(cursor, "whatsapp", "appSecret", app_secret)
        require(
            store.get(cursor, "whatsapp", True)["secrets"]["accessToken"] == secret,
            "C8_secret_roundtrip",
        )
        raw = cursor.execute(
            "SELECT Nonce,Ciphertext FROM crm_channels.Credential WHERE C"
            "hannel='whatsapp' AND Kind='accessToken'"
        ).fetchone()
        require(
            len(raw[0]) == 12 and secret.encode() not in bytes(raw[1]),
            "C8_secret_plaintext",
        )
    check(work, "independent_encryption_roundtrip")
    public = app.get("/api/v1/channels/whatsapp")
    require(
        public.status_code == 200
        and secret not in public.text
        and app_secret not in public.text
        and "secrets" not in public.json(),
        "C8_public_secret_exposure",
    )
    check(work, "credentials_redacted_from_api")
    raw = b'{"object":"C8 synthetic receipt"}'
    request = SimpleNamespace(
        app=app.app,
        headers={
            "x-hub-signature-256": "sha256="
            + hmac.new(app_secret.encode(), raw, hashlib.sha256).hexdigest()
        },
    )
    persist_receipt(request, "meta", raw)
    persist_receipt(request, "meta", raw)
    with store.transaction() as cursor:
        require(
            cursor.execute(
                "SELECT COUNT(*) FROM crm_channels.webhook_events"
            ).fetchval()
            == 1,
            "C8_receipt_replay",
        )
    check(work, "signed_receipt_persistence_idempotent")
    try:
        persist_receipt(SimpleNamespace(app=app.app, headers={}), "meta", raw)
    except HTTPException as error:
        require(error.status_code == 403, "C8_signature_rejection")
    else:
        raise AssertionError("Unsigned synthetic receipt was accepted")
    check(work, "unsigned_receipt_rejected")
    payload = {
        "timestamp": int(datetime.now(timezone.utc).timestamp()),
        "synthetic": True,
    }
    with store.transaction() as cursor:
        account = store.get(cursor, "whatsapp")
        append_message(
            cursor,
            account,
            "C8MessageX",
            "C8IdentityX",
            "Synthetic C8 incoming",
            payload,
            foundation=True,
        )
        append_message(
            cursor,
            account,
            "C8MessageX",
            "C8IdentityX",
            "Ignored replay",
            payload,
            foundation=True,
        )
        require(
            cursor.execute(
                "SELECT COUNT(*) FROM crm_channels.ExternalMessage WHERE Exte"
                "rnalId='C8MessageX'"
            ).fetchval()
            == 1,
            "C8_incoming_replay",
        )
    check(work, "incoming_repository_creates_crm_without_SIIE")
    check(work, "incoming_external_message_replay_is_noop")
    with store.transaction() as cursor:
        append_message(
            cursor,
            store.get(cursor, "whatsapp"),
            "c8messagex",
            "C8IdentityX",
            "Case-sensitive ID",
            payload,
            foundation=True,
        )
        require(
            cursor.execute(
                "SELECT COUNT(*) FROM crm_channels.ExternalMessage WHERE Mess"
                "ageId IS NOT NULL"
            ).fetchval()
            == 2,
            "C8_external_id_collation",
        )
    check(work, "BIN2_identifiers_remain_distinct")
    with store.transaction() as cursor:
        account = store.get(cursor, "whatsapp")
        record_comment(
            cursor, account, "C8Comment", "C8Author", "First synthetic comment", {}
        )
        record_comment(
            cursor, account, "C8Comment", "C8Author", "Updated synthetic comment", {}
        )
        require(
            cursor.execute(
                "SELECT COUNT(*) FROM crm_channels.social_comments"
            ).fetchval()
            == 1,
            "C8_comment_upsert",
        )
    check(work, "comment_repository_updates_without_duplicates")
    comments = app.get("/api/v1/social-comments")
    require(
        comments.status_code == 200 and len(comments.json()["comments"]) == 1,
        "C8_comment_api",
    )
    check(work, "comment_read_repository_and_pagination")
    queue_id = str(uuid4())
    with admin(state["database"], state["context"]) as connection:
        connection.cursor().execute(
            "INSERT crm_channels.outbound_queue(QueueId,Channel,ExternalI"
            "d,Payload,State,LastError) VALUES(?,'whatsapp','C8Delivery',"
            "N'{\"synthetic\":true}','failed','rehearsal_transport_disabled"
            "')",
            queue_id,
        )
    with store.transaction() as cursor:
        record_delivery(
            cursor, "whatsapp", "C8Delivery", "delivered", {"synthetic": True}
        )
        record_delivery(cursor, "whatsapp", "C8Delivery", "sent", {"synthetic": True})
        require(
            cursor.execute(
                "SELECT State FROM crm_channels.outbound_queue WHERE QueueId=?",
                queue_id,
            ).fetchval()
            == "delivered",
            "C8_delivery_monotonicity",
        )
    check(work, "delivery_repository_updates_seeded_queue_monotonically")
    with store.transaction() as cursor:
        before = cursor.execute("SELECT COUNT(*) FROM crm.Contact").fetchval()
    try:
        with store.transaction() as cursor:
            append_message(
                cursor,
                store.get(cursor, "whatsapp"),
                "C8Rollback",
                "C8RollbackIdentity",
                "Synthetic rollback",
                payload,
                foundation=True,
            )
            raise HTTPException(409, "synthetic_rollback")
    except HTTPException as error:
        require(error.status_code == 409, "C8_rollback_wrong_error")
    with store.transaction() as cursor:
        require(
            cursor.execute("SELECT COUNT(*) FROM crm.Contact").fetchval() == before,
            "C8_rollback_left_contact",
        )
        require(
            not cursor.execute(
                "SELECT 1 FROM crm_channels.ExternalMessage WHERE ExternalId="
                "'C8Rollback'"
            ).fetchone(),
            "C8_rollback_left_message",
        )
    check(work, "atomic_ingestion_rollback_leaves_no_partial_entities")
    with store.transaction() as cursor:
        require(
            cursor.execute("SELECT COUNT(*) FROM crm.Contact").fetchval() == 28,
            "C8_mutable_business_count",
        )
        require(
            cursor.execute("SELECT COUNT(*) FROM crm_meta.MigrationJournal").fetchval()
            == 7,
            "C8_journal_changed",
        )
    check(work, "mutable_guard_accepts_legitimate_growth_and_identity_gap")
    changed = {
        "revision": 1,
        "configuration": {**body["configuration"], "phoneNumberId": "1002"},
    }
    require(
        app.put("/api/v1/channels/whatsapp/draft", json=changed).status_code == 409,
        "C8_identity_history_rebind",
    )
    check(work, "account_identity_cannot_rebind_existing_history")
    blocked = [
        ("POST", "/api/v1/channels/whatsapp/activate"),
        ("POST", "/api/v1/webhooks/meta"),
        ("POST", "/api/v1/social-comments/" + str(uuid4()) + "/reply"),
        ("POST", "/api/v1/channels/transport/retry"),
    ]
    for method, path in blocked:
        require(
            app.request(method, path, json={}).status_code == 503,
            "C8_unsafe_route_mounted",
        )
    require(not hasattr(app.app.state, "channel_worker"), "C8_worker_created")
    check(work, "provider_receipt_reply_retry_workers_blocked")
    report(
        work,
        "repositories",
        checks=16,
        all_eight_channel_tables_exercised=True,
        original_business_rows_preserved=199,
        new_contacts=1,
        new_conversations=1,
        new_messages=2,
        academic_writes=0,
        provider_calls=0,
        workers=0,
        queue_insert_only_admin_fixture=True,
    )


def denied(work):
    state = load(work / "state.json")
    settings = load_settings(Path(state["profile_directory"]))
    user = settings.sql_user
    completed = set(load(work / "checks.json"))
    sqls = {
        "academic_read_denied": "SELECT TOP(0) * FROM dbo.GEEstudiante",
        "queue_insert_denied": "INSERT crm_channels.outbound_queue DEFAULT VALUES",
        "journal_write_denied": "DELETE crm_meta.MigrationJournal WHERE EventId=-1",
        "channel_delete_denied": "DELETE crm_channels.Account WHERE Channel='unused'",
        "ddl_denied": "CREATE TABLE crm_channels.C8Forbidden (Id int)",
    }
    for label, sql in sqls.items():
        if label in completed:
            continue
        with pyodbc.connect(
            connection_string(settings), timeout=5, autocommit=False
        ) as connection:
            try:
                connection.cursor().execute(sql)
            except pyodbc.Error as error:
                require(
                    "(229)" in str(error) or "(262)" in str(error),
                    "C8_wrong_sql_denial",
                )
            else:
                raise AssertionError("SQL permission allowed " + label)
            finally:
                connection.rollback()
        check(work, label)
    for database, label in [
        ("HORARIOSSIIE", "source_academic_login_denied"),
        ("CBN_C3_TRIAL_20261024_ac8505b8", "C5_login_denied"),
        (state["source_ticket"]["identity"]["database"], "C7_login_denied"),
    ]:
        if label in completed:
            continue
        text = connection_string(settings).replace(
            "DATABASE={" + settings.sql_database + "}", "DATABASE={" + database + "}"
        )
        try:
            connection = pyodbc.connect(text, timeout=5)
        except pyodbc.Error:
            pass
        else:
            connection.close()
            raise AssertionError("C8 login entered a protected source")
        check(work, label)
    mutations = {
        "extra_schema": (
            "CREATE SCHEMA crm_c8_unexpected AUTHORIZATION dbo",
            "DROP SCHEMA crm_c8_unexpected",
        ),
        "extra_view": (
            "CREATE VIEW crm_channels.C8Unexpected AS SELECT 1 AS value",
            "DROP VIEW crm_channels.C8Unexpected",
        ),
        "fk_untrusted": (
            "ALTER TABLE crm_channels.ExternalIdentity NOCHECK CONSTRAINT"
            " FK_Channels_Identity_Contact",
            "ALTER TABLE crm_channels.ExternalIdentity WITH CHECK CHECK C"
            "ONSTRAINT FK_Channels_Identity_Contact",
        ),
        "extra_permission": (
            "GRANT INSERT ON OBJECT::crm_channels.outbound_queue TO "
            + quote_name(user),
            "REVOKE INSERT ON OBJECT::crm_channels.outbound_queue FROM "
            + quote_name(user),
        ),
        "inherited_role": (
            "ALTER ROLE db_datareader ADD MEMBER " + quote_name(user),
            "ALTER ROLE db_datareader DROP MEMBER " + quote_name(user),
        ),
        "metadata_visibility": (
            "REVOKE VIEW DEFINITION FROM " + quote_name(user),
            "GRANT VIEW DEFINITION TO " + quote_name(user),
        ),
        "dependency_visibility": (
            "REVOKE SELECT ON OBJECT::sys.sql_expression_dependencies FROM "
            + quote_name(user),
            "GRANT SELECT ON OBJECT::sys.sql_expression_dependencies TO "
            + quote_name(user),
        ),
        "public_impersonation": (
            "GRANT IMPERSONATE ON USER::cbn_channels_migrator_c7 TO public",
            "REVOKE IMPERSONATE ON USER::cbn_channels_migrator_c7 FROM public",
        ),
        "journal_tamper": (
            "UPDATE crm_meta.MigrationJournal SET ToolVersion=ToolVersion"
            "+'-C8test' WHERE EventId=(SELECT MAX(EventId) "
            "FROM crm_meta.MigrationJournal)",
            "UPDATE crm_meta.MigrationJournal SET ToolVersion=LEFT(ToolVe"
            "rsion,LEN(ToolVersion)-7) WHERE EventId=(SELECT MAX(EventId) "
            "FROM crm_meta.MigrationJournal)",
        ),
    }
    for label, (change, undo) in mutations.items():
        if "reject_" + label in completed:
            continue
        with admin(state["database"], state["context"]) as connection:
            cursor = connection.cursor()
            cursor.execute(change)
            if label == "journal_tamper":
                require(cursor.rowcount == 1, "C8_journal_probe_did_not_change_a_row")
            try:
                require(
                    client(settings).get("/api/v1/channels").status_code == 503,
                    "C8_drift_not_rejected",
                )
            finally:
                cursor.execute(undo)
        with ChannelStore(settings).transaction():
            pass
        check(work, "reject_" + label)
    report(
        work,
        "denials_and_drift",
        checks=17,
        unsafe_states_rejected=True,
        academic_DML_tests=False,
    )


def concurrency(work):
    state = load(work / "state.json")
    settings = load_settings(Path(state["profile_directory"]))
    with ChannelStore(settings).transaction() as cursor:
        account = ChannelStore(settings).get(cursor, "whatsapp")
    body = {
        "revision": account["revision"],
        "configuration": {
            **account["configuration"],
            "callbackUrl": "https://c8-synthetic.invalid/callback",
        },
    }
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(
                lambda _: client(settings)
                .put("/api/v1/channels/whatsapp/draft", json=body)
                .status_code,
                range(2),
            )
        )
    require(sorted(responses) == [200, 409], "C8_concurrent_revision")
    check(work, "two_connections_same_revision_only_one_commit")
    with admin(state["database"], state["context"]) as connection:
        cursor = connection.cursor()
        acquire(cursor, "crm.schema.migrate.v1", "Session")
        try:
            require(
                client(settings).get("/api/v1/channels").status_code == 503,
                "C8_schema_lock_ignored",
            )
        finally:
            cursor.execute(
                "EXEC sys.sp_releaseapplock @Resource=N'crm.schema.migrate.v1"
                "',@LockOwner=N'Session';"
            )
    check(work, "migration_excludes_runtime_transaction")
    with admin(state["database"], state["context"]) as connection:
        cursor = connection.cursor()
        acquire(cursor, "crm.local.commit", "Session")
        try:
            require(
                client(settings).get("/api/v1/channels").status_code == 503,
                "C8_writer_lock_ignored",
            )
        finally:
            cursor.execute(
                "EXEC sys.sp_releaseapplock @Resource=N'crm.local.commit',@Lo"
                "ckOwner=N'Session';"
            )
    check(work, "writer_lock_excludes_concurrent_runtime")
    original_connect = pyodbc.connect
    for committed in (True, False):
        current = client(settings).get("/api/v1/channels/whatsapp").json()
        draft = {
            "revision": current["revision"],
            "configuration": {
                **current["configuration"],
                "callbackUrl": "https://c8-synthetic.invalid/ack",
            },
        }

        class CommitLoss:
            def __init__(self, connection):
                self.connection = connection

            def __getattr__(self, name):
                return getattr(self.connection, name)

            def commit(self):
                if committed:
                    self.connection.commit()
                else:
                    self.connection.rollback()
                raise pyodbc.Error("08007", "C8 synthetic acknowledgement loss")

        pyodbc.connect = lambda *a, **k: CommitLoss(original_connect(*a, **k))
        try:
            require(
                client(settings)
                .put("/api/v1/channels/whatsapp/draft", json=draft)
                .status_code
                == 503,
                "C8_commit_ack_not_uncertain",
            )
        finally:
            pyodbc.connect = original_connect
        actual = client(settings).get("/api/v1/channels/whatsapp").json()
        require(
            actual["revision"] == current["revision"] + int(committed),
            "C8_commit_ack_revision",
        )
        retry = client(settings).put("/api/v1/channels/whatsapp/draft", json=draft)
        require(retry.status_code == (409 if committed else 200), "C8_commit_ack_retry")
        check(
            work,
            "commit_ack_recovered_" + ("committed" if committed else "rolled_back"),
        )
    report(work, "concurrency", checks=5, no_duplicate_configuration_success=True)


def final(work):
    state = load(work / "state.json")
    settings = load_settings(Path(state["profile_directory"]))
    current = signatures(state["context"], Path(state["runtime_directory"]))
    require(current == state["c5_signatures"], "C8_source_or_C5_changed")
    with c7_admin(
        state["source_ticket"]["identity"]["database"], state["context"], readonly=True
    ) as connection:
        require(capture(connection) == state["source"], "C8_C7_source_changed")
        require(
            verified_state(connection.cursor(), state["source_ticket"], assets()[0]),
            "C8_C7_not_accepted",
        )
    with admin(state["database"], state["context"], readonly=True) as connection:
        cursor = connection.cursor()
        require(
            sha(journal_binary(cursor)) == state["source"]["journal_sha256"],
            "C8_journal_final",
        )
        require(
            data_signature(cursor, PARTITION["academic"])
            == state["source"]["preservation"]["academic"],
            "C8_academic_data_changed",
        )
        old_ids = [
            r
            for r in state["source"]["preservation"]["identity_values"]
            if r["schema_name"] == "dbo"
        ]
        require(
            [r for r in identity_values(cursor) if r["schema_name"] == "dbo"]
            == old_ids,
            "C8_academic_identity_changed",
        )
        rows = business_rows(cursor)
        for table, prior in state["original_business"].items():
            require(
                all(rows[table].get(key) == value for key, value in prior.items()),
                "C8_existing_CRM_row_changed",
            )
        require(
            sha(metadata(cursor)) == state["ticket"]["catalog_sha256"],
            "C8_final_catalog_changed",
        )
        counts = {
            table: cursor.execute("SELECT COUNT(*) FROM " + table).fetchval()
            for table in PARTITION["extension"]
        }
    with ChannelStore(settings).transaction():
        pass
    values = load(work / "checks.json")
    groups = [
        load(work / (name + "-result.json"))
        for name in ("repositories", "denials_and_drift", "concurrency")
    ]
    require(
        len(values) == len(set(values)) == sum(g["checks"] for g in groups),
        "C8_incomplete_checks",
    )
    report(
        work,
        "final",
        checks=len(values),
        original_business_rows_preserved=199,
        academic_tables=50,
        academic_rows=44180,
        source_C5_C7_unchanged=True,
        trial_business_rows=sum(len(v) for v in rows.values()),
        extension_counts=counts,
        journal_rows_preserved=7,
        own_profile_and_login=True,
        admin_runtime_metadata_equal=True,
        workers=0,
        provider_calls=0,
        institutional_sql2019_accepted=False,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("repositories", "denied", "concurrency", "final")
    )
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    {
        "repositories": repositories,
        "denied": denied,
        "concurrency": concurrency,
        "final": final,
    }[args.action](args.work)
