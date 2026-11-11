"""Local-copy transaction, boundary and retry proof without database IO."""

from uuid import uuid4

import pyodbc
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.config import Settings
from app.sql_workspace import (
    ContactMutation,
    MessageMutation,
    SqlWorkspace,
    payload_hash,
    verify_target,
)


def contact_body():
    return ContactMutation.model_validate(
        {
            "operationId": str(uuid4()),
            "expectedRevision": "0",
            "conversationId": str(uuid4()),
            "client": {
                "id": str(uuid4()),
                "name": "Local test",
                "phone": "",
                "city": "",
                "programId": None,
                "program": "",
                "schedule": "",
                "stage": "Nuevo",
                "tags": "",
                "notes": "",
                "type": "",
                "interests": "",
                "customValues": {},
            },
        }
    )


class Cursor:
    def __init__(self):
        self.statements = []
        self.depth = 1
        self.pending_writes = []
        self.previous = None
        self.revision = 0
        self.fail = False
        self.result = None

    def execute(self, sql, *args):
        self.statements.append((sql, args))
        if sql in (
            "SELECT SCHEMA_ID(N'crm_merge')",
            "SELECT SCHEMA_ID(N'crm_strategy')",
        ):
            self.result = (None,)
            return self
        if "BEGIN TRANSACTION" in sql:
            self.depth += 1
        if sql.startswith("INSERT"):
            self.pending_writes.append((sql, args))
        if "sp_getapplock" in sql:
            self.result = (0,)
        elif "SERVERPROPERTY" in sql:
            self.result = (
                "DBSIIE",
                "SQLEXPRESS",
                "TESTMACHINE",
                r"TESTMACHINE\SQLEXPRESS",
                15,
                150,
                4,
                "Express Edition",
                "reader",
                "reader",
                "reader",
            )
        elif "sys.extended_properties" in sql:
            self.result = ("ADR-006-v1",)
        elif "@manifest" in sql:
            self.result = (1,)
        elif "SELECT PayloadHash" in sql:
            self.result = self.previous
        elif "MAX(Revision)" in sql:
            self.result = (self.revision,)
        elif sql == "SELECT OBJECT_ID(N'crm_channels.Audit')":
            self.result = (None,)
        elif "SELECT ContactId FROM crm.Contact" in sql:
            self.result = None
        elif "INSERT crm.Conversation" in sql and self.fail:
            raise pyodbc.OperationalError("injected")
        return self

    def fetchone(self):
        return self.result

    def close(self):
        pass


class Connection:
    def __init__(self):
        self.cur = Cursor()
        self.commits = self.rollbacks = self.closes = 0
        self.persisted_writes = []

    def cursor(self):
        return self.cur

    def commit(self):
        self.commits += 1
        self.cur.depth -= 1
        if self.cur.depth == 0:
            self.persisted_writes.extend(self.cur.pending_writes)
            self.cur.pending_writes.clear()

    def rollback(self):
        self.rollbacks += 1
        self.cur.pending_writes.clear()

    def close(self):
        self.closes += 1
        self.cur.pending_writes.clear()


@pytest.fixture
def repository(monkeypatch):
    from app.modules.crm_configuration.application.service import Configuration

    monkeypatch.setattr(
        "app.modules.crm_configuration.application.service.read_configuration",
        lambda cursor: (
            Configuration(
                stages=[{"key": "new", "label": "Nuevo"}], tags=[], fields=[]
            ),
            "1",
        ),
    )
    connection = Connection()
    monkeypatch.setattr(pyodbc, "connect", lambda *args, **kwargs: connection)
    store = SqlWorkspace(
        Settings(
            mode="local_sql_copy",
            sql_expected_machine="TESTMACHINE",
            sql_host="localhost",
            sql_user="synthetic",
            sql_password="synthetic",
            sql_certificate_hostname="localhost",
        )
    )
    monkeypatch.setattr(
        store,
        "snapshot",
        lambda cursor: {"clients": [], "threads": [], "revision": str(cursor.revision)},
    )
    return store, connection


def test_contact_and_conversation_and_audit_commit_together(repository):
    store, connection = repository
    body = contact_body()
    store.mutate("create_contact", body.client.id, body)
    inserts = [sql for sql, _ in connection.cur.statements if sql.startswith("INSERT")]
    assert len(inserts) == 3
    assert [
        "crm.Contact" in inserts[0],
        "crm.Conversation" in inserts[1],
        "crm.Operation" in inserts[2],
    ] == [True] * 3
    assert (connection.commits, connection.rollbacks, connection.closes) == (1, 0, 1)
    assert len(connection.persisted_writes) == 3


def test_partial_failure_rolls_back_every_write(repository):
    store, connection = repository
    connection.cur.fail = True
    body = contact_body()
    with pytest.raises(pyodbc.OperationalError):
        store.mutate("create_contact", body.client.id, body)
    assert (connection.commits, connection.rollbacks, connection.closes) == (0, 1, 1)
    assert not any(
        "INSERT crm.Operation" in sql for sql, _ in connection.cur.statements
    )


def test_replay_precedes_revision_comparison(repository):
    store, connection = repository
    body = contact_body()
    connection.cur.previous = (payload_hash("create_contact", body.client.id, body),)
    connection.cur.revision = 9
    assert store.mutate("create_contact", body.client.id, body)["revision"] == "9"
    assert not any(sql.startswith("INSERT") for sql, _ in connection.cur.statements)


@pytest.mark.parametrize("replay", [False, True])
def test_conflicts_have_no_writes(repository, replay):
    store, connection = repository
    body = contact_body()
    if replay:
        connection.cur.previous = (b"x" * 32,)
    else:
        connection.cur.revision = 9
    with pytest.raises(HTTPException) as error:
        store.mutate("create_contact", body.client.id, body)
    assert error.value.status_code == 409
    assert connection.rollbacks == 1
    assert not any(sql.startswith("INSERT") for sql, _ in connection.cur.statements)


def test_hash_excludes_transport_revision():
    body = contact_body()
    digest = payload_hash("create_contact", body.client.id, body)
    body.expectedRevision = "8"
    assert payload_hash("create_contact", body.client.id, body) == digest
    body.client.notes = "Changed"
    assert payload_hash("create_contact", body.client.id, body) != digest


@pytest.mark.parametrize(
    "field,value",
    [("name", ""), ("program", "Invented"), ("customValues", {"constructor": "x"})],
)
def test_contact_validation(field, value):
    body = contact_body().model_dump()
    body["client"][field] = value
    with pytest.raises(ValidationError):
        ContactMutation.model_validate(body)


def test_blank_message_is_rejected():
    with pytest.raises(ValidationError):
        MessageMutation(
            operationId=str(uuid4()),
            expectedRevision="0",
            messageId=str(uuid4()),
            body="   ",
        )


def test_target_machine_must_match():
    from app.modules.catalog.domain.contracts import CatalogUnavailable

    with pytest.raises(CatalogUnavailable):
        verify_target(Cursor(), Settings(sql_expected_machine="OTHER"))


@pytest.mark.parametrize("host", ["remote.example", "localhost;Encrypt=No"])
def test_copy_mode_rejects_unapproved_endpoint(monkeypatch, host):
    monkeypatch.setenv("CRM_APP_MODE", "local_sql_copy")
    monkeypatch.setenv("CRM_SQL_HOST", host)
    with pytest.raises(ValueError):
        Settings.from_environment()


def test_compact_commit_and_replay_never_read_bounded_snapshot(repository, monkeypatch):
    store, connection = repository
    monkeypatch.setattr(
        store,
        "snapshot",
        lambda cursor: (_ for _ in ()).throw(AssertionError("snapshot limit")),
    )
    body = contact_body()
    result = store.mutate("create_contact", body.client.id, body, compact=True)
    assert result == {"revision": "0"} and connection.commits == 1
    connection.cur.previous = (payload_hash("create_contact", body.client.id, body), 7)
    connection.cur.revision = 999
    assert store.mutate("create_contact", body.client.id, body, compact=True) == {
        "revision": "999"
    }
    assert len(connection.persisted_writes) == 3


def test_idempotence_hash_binds_action_entity_and_body():
    body = contact_body()
    original = payload_hash("edit_contact", body.client.id, body)
    assert original != payload_hash("create_contact", body.client.id, body)
    assert original != payload_hash("edit_contact", str(uuid4()), body)
    body.client.notes = "different"
    assert original != payload_hash("edit_contact", body.client.id, body)
