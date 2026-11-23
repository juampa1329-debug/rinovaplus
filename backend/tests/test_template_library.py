"""Library removal is reversible, versioned, scoped, and survives Meta sync."""

import json
from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.institutional import broadcast_templates as templates
from app.institutional import db
from app.institutional import template_library as library


def harness(monkeypatch, *, referenced=False, revision=2, duplicate=None):
    old = {
        "VersionNo": 2,
        "TemplateId": str(uuid4()),
        "IntegrationId": str(uuid4()),
        "CredentialId": None,
        "ProviderId": "local:old",
        "Name": "old",
        "Language": "es",
        "Category": "MARKETING",
        "ProviderStatus": "LOCAL_DRAFT",
        "Definition": "[]",
        "ProviderMetadata": "{}",
        "Origin": "operator",
        "ObservedAt": None,
    }
    writes = []
    cursor = SimpleNamespace(
        execute=lambda *a: SimpleNamespace(
            fetchone=lambda: (1,) if referenced else None
        )
    )

    @contextmanager
    def tx(auth, write=False):
        assert write
        yield cursor, {"UserId": "actor"}

    service = SimpleNamespace(settings=None, tx=tx)
    monkeypatch.setattr(library, "replay", lambda *a: (b"hash", duplicate))
    monkeypatch.setattr(library, "institution", lambda *a: "institution")
    monkeypatch.setattr(library, "record_operation", lambda *a: None)
    monkeypatch.setattr(library, "audit", lambda *a, **k: None)
    monkeypatch.setattr(library, "account", lambda *a: {})
    monkeypatch.setattr(templates, "latest", lambda *a: old)

    def append(*args, **kwargs):
        writes.append(kwargs)
        return {"version": 3}

    monkeypatch.setattr(templates, "append", append)
    command = library.LibraryWrite(
        operation_id=uuid4(),
        revision=revision,
        reason="Retirar versión sustituida",
        removed=True,
        confirmed=True,
    )
    return service, old["TemplateId"], command, writes


@pytest.mark.parametrize(
    "referenced,revision,code",
    [
        (True, 2, "broadcast_template_still_in_campaign"),
        (False, 1, "revision_conflict"),
    ],
)
def test_library_rejects_referenced_or_stale_template(
    monkeypatch, referenced, revision, code
):
    service, key, command, writes = harness(
        monkeypatch, referenced=referenced, revision=revision
    )
    with pytest.raises(HTTPException, match=code):
        library.change(service, {}, key, command)
    assert writes == []


def test_library_removal_and_restore_append_in_pause_without_provider_io(monkeypatch):
    service, key, command, writes = harness(monkeypatch)
    assert library.change(service, {}, key, command)["removed"] is True
    assert writes[0]["paused"] is True and writes[0]["removed"] is True
    restore = command.model_copy(update={"removed": False})
    assert library.change(service, {}, key, restore)["removed"] is False
    assert writes[1]["paused"] is True and writes[1]["removed"] is False


def test_library_replay_does_not_append_a_second_version(monkeypatch):
    service, key, command, writes = harness(monkeypatch, duplicate={"removed": True})
    assert library.change(service, {}, key, command) == {"removed": True}
    assert writes == []


def test_library_change_uses_the_real_shared_audit_contract(monkeypatch):
    service, key, command, _ = harness(monkeypatch)
    monkeypatch.setattr(db, "institution", lambda _: "institution")
    monkeypatch.setattr(library, "audit", db.audit)
    recorded = []

    def execute(sql, *parameters):
        recorded.append((sql, parameters))
        return SimpleNamespace(fetchone=lambda: None)

    with service.tx({}, True) as (cursor, _):
        cursor.execute = execute
    assert library.change(service, {}, key, command)["removed"] is True
    entries = [p for sql, p in recorded if sql.startswith("INSERT crm_access.Audit")]
    assert len(entries) == 1 and entries[0][3] == key
    metadata = json.loads(entries[0][-1])
    assert metadata == {
        "fields": ["library_removed"], "version": 3, "reason": "removed"
    }


def test_library_requires_explicit_confirmation(monkeypatch):
    service, key, command, writes = harness(monkeypatch)
    with pytest.raises(HTTPException, match="broadcast_library_confirmation_required"):
        library.change(
            service, {}, key, command.model_copy(update={"confirmed": False})
        )
    assert writes == []


@pytest.mark.parametrize("restore", [False, True])
def test_meta_sync_and_unpause_cannot_resurrect_removed_template(monkeypatch, restore):
    old = {
        "TemplateId": str(uuid4()),
        "VersionNo": 2,
        "Paused": True,
        "Definition": "[]",
        "ProviderMetadata": '{"library_removed":true}',
    }
    monkeypatch.setattr(templates, "one", lambda *a: old)
    monkeypatch.setattr(templates, "institution", lambda *a: "institution")
    monkeypatch.setattr(templates, "rows", lambda *a: [])
    inserted = []
    cursor = SimpleNamespace(execute=lambda sql, *args: inserted.append(args))
    templates.append(
        cursor,
        None,
        {"IntegrationId": str(uuid4()), "RowVersion": b"version"},
        {
            "id": "123",
            "name": "old",
            "language": "es",
            "status": "APPROVED",
            "components": [],
        },
        None,
        "provider",
        paused=True if restore else False,
        **({"removed": False} if restore else {}),
    )
    assert inserted[0][10] is True
    metadata = json.loads(inserted[0][12])
    assert bool(metadata.get("library_removed")) is not restore
