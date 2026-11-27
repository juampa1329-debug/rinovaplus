from contextlib import nullcontext
from copy import deepcopy
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException
import pytest

from app.institutional.contact_changes import merge_contact_edit
from app.institutional import workspace
from app.sql_workspace import Contact


def person(**change):
    return dict(id="00000000-0000-4000-8000-000000000001", name="QA", phone="", city="",
                programId=None, program="", schedule="", stage="Seguimiento", tags="", notes="",
                type="", interests="", customValues={"correo": "anterior"}, **change)


def test_stage_edit_preserves_concurrent_city_notes_and_new_custom_value():
    base = person()
    current = {**base, "city": "Santa Marta", "notes": "Revisada por otro asesor",
               "customValues": {"correo": "nuevo", "origen": "SIIE"}}
    result = merge_contact_edit(current, Contact(**{**base, "stage": "Cerrado sin matrícula"}), Contact(**base))
    assert result.stage == "Cerrado sin matrícula"
    assert result.city == current["city"] and result.notes == current["notes"]
    assert result.customValues == current["customValues"]


@pytest.mark.parametrize("key,value", [("stage", "Matriculado"), ("name", "Otro nombre"), ("phone", "nuevo")])
def test_same_field_changes_conflict_instead_of_overwriting(key, value):
    base = person()
    with pytest.raises(HTTPException, match="contact_fields_changed"):
        merge_contact_edit({**base, key: value}, Contact(**{**base, key: "Mi edición"}), Contact(**base))


def test_two_custom_fields_merge_but_same_custom_field_conflicts():
    base = person()
    draft = Contact(**{**base, "customValues": {"correo": "anterior", "otro": "mío"}})
    actual = {**base, "customValues": {"correo": "nuevo"}}
    assert merge_contact_edit(actual, draft, Contact(**base)).customValues == {"correo": "nuevo", "otro": "mío"}
    with pytest.raises(HTTPException, match="contact_fields_changed"):
        merge_contact_edit(actual, Contact(**{**base, "customValues": {}}), Contact(**base))


def test_already_applied_value_and_deleting_unchanged_custom_field_are_safe():
    base = person()
    draft = Contact(**{**base, "stage": "Cerrado sin matrícula", "customValues": {}})
    actual = {**base, "stage": draft.stage, "city": "Otra ciudad"}
    result = merge_contact_edit(actual, draft, Contact(**base))
    assert result.stage == draft.stage and result.city == "Otra ciudad" and result.customValues == {}


def test_changed_academic_identity_is_preserved_but_cannot_be_edited_here():
    base = person()
    actual = {**base, "programId": 10, "program": "Actual confirmado"}
    result = merge_contact_edit(actual, Contact(**{**base, "stage": "Cerrado sin matrícula"}), Contact(**base))
    assert (result.programId, result.program) == (10, "Actual confirmado")
    with pytest.raises(HTTPException, match="academic_mapping_not_bound"):
        merge_contact_edit(actual, Contact(**actual), Contact(**base))
    wrong = Contact(**{**base, "id": str(uuid4())})
    with pytest.raises(HTTPException, match="canonical_contact_required"):
        merge_contact_edit(actual, wrong, Contact(**base))


def fixture_writer(monkeypatch, *, replay=None):
    events = []
    cursor = SimpleNamespace(execute=lambda *args: events.append(("sql", args)))
    monkeypatch.setattr(workspace, "transaction", lambda *a, **kw: events.append(("authority", kw)) or nullcontext(cursor))
    monkeypatch.setattr(workspace, "authorize", lambda *a: {"UserId": str(uuid4())})
    monkeypatch.setattr(workspace, "revision", lambda c: "999")
    monkeypatch.setattr(workspace.db, "replay", lambda *a: ("digest", replay))
    monkeypatch.setattr(workspace.db, "record_operation", lambda *a, **kw: events.append(("operation", a[-1])))
    monkeypatch.setattr(workspace.db, "audit", lambda *a, **kw: events.append(("audit", kw)))
    writer = workspace.Workspace.__new__(workspace.Workspace)
    writer.profile = SimpleNamespace(ticket={"version": "fixture"})
    writer.apply = lambda *a: events.append(("apply", a)) or {"contactId": person()["id"]}
    return writer, events


def test_contact_with_base_ignores_unrelated_global_revision_but_requires_writer_authority(monkeypatch):
    writer, events = fixture_writer(monkeypatch)
    base = person()
    command = workspace.ContactWrite(operationId=str(uuid4()), revision="1", baseClient=base,
                                     client={**base, "stage": "Cerrado sin matrícula"})
    result = writer.write("contact", base["id"], command)
    assert result["revision"] == "999" and any(e[0] == "apply" for e in events)
    assert events[0] == ("authority", {"permission": "crm.write", "recent": False})
    assert any(e[0] == "operation" for e in events)


def test_legacy_client_without_base_still_requires_global_revision(monkeypatch):
    writer, events = fixture_writer(monkeypatch)
    with pytest.raises(HTTPException, match="revision_conflict"):
        writer.write("contact", person()["id"], workspace.ContactWrite(operationId=str(uuid4()), revision="1", client=person()))
    assert not any(e[0] == "apply" for e in events)


def test_replayed_accepted_contact_command_does_not_apply_or_record_again(monkeypatch):
    prior = {"revision": "2", "contactId": person()["id"]}
    writer, events = fixture_writer(monkeypatch, replay=deepcopy(prior))
    result = writer.write("contact", person()["id"], workspace.ContactWrite(operationId=str(uuid4()), revision="1", client=person(), baseClient=person()))
    assert result == prior
    assert not any(e[0] in {"apply", "operation", "sql"} for e in events)
