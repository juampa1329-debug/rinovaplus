"""Declared identities, legacy replay and bounded read-only lookup without IO."""

import hashlib
import json
from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from test_sql_workspace import contact_body

from app.modules.conversation_analysis.domain.models import redact
from app.config import Settings
from app.modules.contacts.api.router import (
    LOOKUP_SQL,
    InstitutionalIdentity,
    available,
    decorate,
    private_identifiers,
    save_profile,
)
from app.modules.contacts.domain.models import IdentityLookup, InstitutionalProfile
from app.main import create_app
from app.sql_workspace import payload_hash


@pytest.mark.parametrize("document", ["001234", "00-123.A", "\t001\t"])
def test_document_is_text_and_only_ascii_spaces_are_trimmed(document):
    profile = InstitutionalProfile(documentTypeId=1, document=" " + document + " ")
    assert profile.document == document
    assert (
        IdentityLookup(documentTypeId=1, document=profile.document).document == document
    )


@pytest.mark.parametrize(
    "input",
    [
        {"document": "0001"},
        {"documentTypeId": 1},
        {"document": "0" * 17, "documentTypeId": 1},
        {"givenNames": "N" * 101},
        {"firstSurname": "S" * 31},
        {"email": "bad mail"},
        {"aspirationPeriodId": 0},
        {"documentTypeId": 256},
    ],
)
def test_invalid_profile_is_rejected(input):
    with pytest.raises(ValidationError):
        InstitutionalProfile(**input)


def test_crm_email_has_its_own_length_without_core_truncation():
    email = "a" * 145 + "@example.test"
    assert len(email) <= 160 and len(email) > 50
    assert InstitutionalProfile(email=email).email == email


@pytest.mark.parametrize(
    "input",
    [{"ownContactId": ""}, {"ownContactId": "bad"}, {"periodId": 1}, {"programId": 1}],
)
def test_bad_uuid_and_identity_filters_are_rejected(input):
    with pytest.raises(ValidationError):
        IdentityLookup(documentTypeId=1, document="0001", **input)


def test_legacy_hash_is_byte_exact_when_profile_is_omitted_or_none():
    body = contact_body()
    data = body.model_dump(exclude={"operationId", "expectedRevision"})
    data["client"].pop("institutionalProfile")
    legacy = hashlib.sha256(
        json.dumps(
            ["edit_contact", body.client.id, data],
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()
    ).digest()
    assert payload_hash("edit_contact", body.client.id, body) == legacy
    body.client.institutionalProfile = InstitutionalProfile(givenNames="Declared")
    assert payload_hash("edit_contact", body.client.id, body) != legacy
    body.client.institutionalProfile = None
    assert payload_hash("edit_contact", body.client.id, body) == legacy


class Cursor:
    def __init__(self, result=None):
        self.result = result
        self.calls = []

    def execute(self, sql, *args):
        self.calls.append((sql, args))
        return self

    def fetchone(self):
        return self.result


def test_absent_schema_preserves_old_reads_and_omitted_profile_never_writes():
    cursor = Cursor()
    clients = [{"id": str(uuid4()), "name": "Historical visible name"}]
    assert decorate(cursor, clients) == clients
    assert "institutionalProfile" not in clients[0]
    cursor.calls.clear()
    save_profile(cursor, contact_body().client)
    assert not cursor.calls
    with pytest.raises(HTTPException) as failure:
        available(cursor, required=True)
    assert failure.value.status_code == 503
    assert all("CREATE" not in sql for sql, _ in cursor.calls)


def test_empty_criteria_never_opens_a_database_transaction():
    repository = InstitutionalIdentity(None)
    for body in [
        IdentityLookup(),
        IdentityLookup(name="ab", mode="name"),
        IdentityLookup(email="invalid", phone="1234"),
    ]:
        page = repository.lookup(body)
        assert not page["items"] and page["criteriaRequired"]


def test_global_page_and_escaped_query_are_bound_with_no_source_truncation(monkeypatch):
    from test_admissions import ReadCursor

    rows = [
        {
            "source": "student",
            "sourceId": str(i),
            "documentMatch": 0,
            "emailMatch": 0,
            "phoneMatch": 0,
        }
        for i in range(26)
    ]
    cursor = ReadCursor([rows])

    @contextmanager
    def transaction():
        yield cursor

    monkeypatch.setattr("app.modules.contacts.api.router.available", lambda *a, **k: True)
    monkeypatch.setattr("app.modules.contacts.api.router.validate_catalogs", lambda *a: None)
    repository = InstitutionalIdentity(SimpleNamespace(transaction=transaction))
    own = str(uuid4())
    body = IdentityLookup(
        mode="name",
        name="[" * 200,
        ownContactId=own,
        periodId=1,
        programId=2,
        offset=25,
    )
    page = repository.lookup(body)
    sql, args = cursor.calls[0]
    assert len(args[7]) == 602 and "nvarchar(602)" in sql
    assert args[2] == own and args[-4:] == (1, 2, 25, "[]")
    assert len(page["items"]) == 25 and page["hasMore"]
    assert page["identityScope"] == "selected_period_and_program"
    assert page["items"][0]["reasons"] == ["name_search"]
    assert "TOP" not in LOOKUP_SQL and LOOKUP_SQL.count("OFFSET") == 1
    assert "WHERE (@own IS NULL OR c.ContactId<>@own)" in sql
    assert "Latin1_General_100_BIN2" in sql and "UPDATE" not in sql


def test_identity_has_no_email_truncation_and_ignores_invalid_optional_email(
    monkeypatch,
):
    from test_admissions import ReadCursor, Workspace

    monkeypatch.setattr("app.modules.contacts.api.router.available", lambda *a, **k: True)
    monkeypatch.setattr("app.modules.contacts.api.router.validate_catalogs", lambda *a: None)
    email = "a" * 90 + "@example.test"
    for candidate, expected in [(email, email), ("bad", "")]:
        cursor = ReadCursor([[]])
        page = InstitutionalIdentity(Workspace(cursor)).lookup(
            IdentityLookup(
                documentTypeId=1, document="00.01", email=candidate, phone="1234"
            )
        )
        assert cursor.calls[0][1][4:7] == ("00.01", expected, "")
        assert page["identityScope"] == "all_periods_and_programs"


def test_private_declared_name_parts_are_redacted_without_exporting_the_profile(
    monkeypatch,
):
    monkeypatch.setattr("app.modules.contacts.api.router.available", lambda *a, **k: True)
    cursor = Cursor(
        (
            "Synthetic Given",
            "Surname",
            "Second",
            1,
            "00-X",
            "example@example.invalid",
            None,
        )
    )
    known = private_identifiers(cursor, str(uuid4()))
    text = "Given Surname 00-X example@example.invalid"
    result = redact(text, known)
    assert all(
        value not in result
        for value in ["Given", "Surname", "00-X", "example@example.invalid"]
    )
    assert not any("INSERT" in sql or "UPDATE" in sql for sql, _ in cursor.calls)


def test_lookup_post_is_read_only_no_store_and_validation_never_reflects_pii():
    app = create_app()
    app.state.settings = Settings(mode="local_sql_copy")
    app.state.institutional_identity = InstitutionalIdentity(None)
    client = TestClient(
        app, base_url="http://127.0.0.1:8002", client=("127.0.0.1", 50000)
    )
    response = client.post(
        "/api/local/crm/identity/candidates", json={}, headers={"X-CRM-Local": "1"}
    )
    assert (
        response.status_code == 200 and response.headers["Cache-Control"] == "no-store"
    )
    assert response.json()["criteriaRequired"]
    bad = client.post(
        "/api/local/crm/identity/candidates",
        json={"ownContactId": "", "email": "private@example.invalid"},
        headers={"X-CRM-Local": "1"},
    )
    assert bad.status_code == 422 and "private@example.invalid" not in bad.text
    assert (
        client.get(
            "/api/local/crm/identity/candidates", headers={"X-CRM-Local": "1"}
        ).status_code
        == 405
    )
