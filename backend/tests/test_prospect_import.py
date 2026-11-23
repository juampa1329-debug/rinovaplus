from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.institutional import prospect_import as imports
from app.institutional.api import core_permission


def entry(**changes):
    return imports.Entry.model_validate(
        {
            "ref": "PRE-0123456789abcdef",
            "name": "Persona de Prueba",
            "phone": "+573001234567",
            "email": "persona@example.org",
            "programs": ["COCINA"],
            "stages": ["Pendiente de calificación"],
            "first_date": "2026-10-01",
            "last_date": "2026-10-01",
            "channels": "En linea",
            "source_files": "test.xls",
            "notes": ["Evidencia sintética; ninguna conversación verificada."],
            **changes,
        }
    )


def test_source_ambiguity_is_never_imported():
    assert imports.decision(entry(review=["Dato compartido"]), [])[0] == "review"
    assert (
        imports.decision(entry(stages=["En negociación", "Inscrito según origen"]), [])[
            0
        ]
        == "review"
    )
    assert imports.decision(entry(name="3001234567"), [])[0] == "review"


@pytest.mark.parametrize(
    "name,phone,email",
    [
        ("Otra persona", "3001234567", "otro@example.org"),
        ("Otra persona", "3112345678", "persona@example.org"),
        ("Persona de Prueba", "3112345678", "otro@example.org"),
    ],
)
def test_existing_crm_coordinates_or_name_are_held(name, phone, email):
    existing = [{"Name": name, "Phone": phone, "custom": {"correo": email}}]
    assert imports.decision(entry(), existing)[0] == "review"


def test_reupload_is_skipped_and_changed_source_is_not_overwritten():
    source = entry()
    existing = [
        {
            "Name": source.name,
            "Phone": source.phone,
            "custom": imports.custom_values(source),
        }
    ]
    assert imports.decision(source, existing)[0] == "imported"
    assert imports.decision(entry(advisor="Otra gestión"), existing)[0] == "review"


def test_unknown_authority_fields_and_oversized_batches_are_rejected():
    with pytest.raises(ValidationError):
        entry(consent=True)
    with pytest.raises(ValidationError):
        imports.Batch(
            operation_id=str(uuid4()), batch_id=str(uuid4()), entries=[entry()] * 11
        )
    assert core_permission(
        "/api/institution/workspace/prospect-import/commit", "POST"
    ) == ("crm.write", "clients")


def test_commit_only_creates_clear_contacts_and_never_calls_message_action(monkeypatch):
    executed, calls, records = [], [], []
    cursor = SimpleNamespace(execute=lambda sql, *p: executed.append((sql, p)))

    @contextmanager
    def transaction(profile, write, **kwargs):
        assert write and kwargs["permission"] == "crm.write"
        yield cursor

    profile = SimpleNamespace(ticket={"context": [["institution", str(uuid4())]]})
    monkeypatch.setattr(imports, "transaction", transaction)
    monkeypatch.setattr(imports, "authorize", lambda *a: {"UserId": str(uuid4())})
    monkeypatch.setattr(imports, "snapshot", lambda c: [])
    monkeypatch.setattr(imports, "revision", lambda c: "2")
    monkeypatch.setattr(imports.db, "replay", lambda *a: (b"digest", None))
    monkeypatch.setattr(imports.db, "record_operation", lambda *a: records.append(a))
    monkeypatch.setattr(imports.db, "audit", lambda *a, **k: None)

    def apply(c, action, resource, body, actor):
        assert action == "create"
        assert body.client.programId is None and body.client.program == ""
        calls.append(body.client)
        return {"conversationId": str(uuid4())}

    body = imports.Batch(
        operation_id=str(uuid4()),
        batch_id=str(uuid4()),
        entries=[
            entry(),
            entry(ref="PRE-fedcba9876543210", review=["Revisar"]),
        ],
    )
    result = imports.process(profile, SimpleNamespace(apply=apply), body, True)
    assert [r["state"] for r in result["items"]] == ["imported", "review"]
    assert len(calls) == len(records) == 1
    assert result["messages_created"] == result["consents_granted"] == 0
    assert any("ControlMode='human'" in sql for sql, _ in executed)
    assert not any(
        "crm.Message" in sql or "Consent" in sql or "SendJob" in sql
        for sql, _ in executed
    )


def test_replayed_commit_does_not_read_or_write_contacts(monkeypatch):
    @contextmanager
    def transaction(*a, **k):
        yield object()

    monkeypatch.setattr(imports, "transaction", transaction)
    monkeypatch.setattr(imports, "authorize", lambda *a: {"UserId": str(uuid4())})
    prior = {"items": [{"state": "imported"}]}
    monkeypatch.setattr(imports.db, "replay", lambda *a: (b"digest", prior))
    monkeypatch.setattr(imports, "snapshot", lambda c: pytest.fail("Replay read CRM"))
    assert (
        imports.process(
            SimpleNamespace(),
            None,
            imports.Batch(
                operation_id=str(uuid4()), batch_id=str(uuid4()), entries=[entry()]
            ),
            True,
        )
        == prior
    )


def test_field_preparation_requires_configuration_permission(monkeypatch):
    @contextmanager
    def transaction(*a, **kwargs):
        assert kwargs["permission"] == "settings.crm.write"
        raise HTTPException(403, "permission_required")
        yield

    monkeypatch.setattr(imports, "transaction", transaction)
    with pytest.raises(HTTPException) as failure:
        imports.prepare(None, imports.Prepare(operation_id=str(uuid4())))
    assert failure.value.status_code == 403
