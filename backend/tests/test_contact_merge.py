"""C4 contracts with synthetic identities, without SQL/provider IO."""

from copy import deepcopy
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.modules.contacts.application.merge import (
    MergeCommit,
    MergePreview,
    UndoCommit,
    UndoPreview,
    analysis_guard,
    field_keys,
    historical_ids,
    identifiers,
    invalidate_analysis,
    select_fields,
)
from app.sql_workspace import Contact


def contact():
    return Contact(
        id=str(uuid4()),
        name="Synthetic contact",
        phone="",
        city="",
        program="",
        schedule="",
        stage="new",
        tags="",
        notes="",
        type="",
        interests="",
        customValues={},
    ).model_dump()


@pytest.mark.parametrize("value", [False, 1, 0, "true", None, [], {}])
@pytest.mark.parametrize("undo", [False, True])
def test_commit_confirmation_is_literal_boolean_true(value, undo):
    common = {"operationId": str(uuid4()), "expectedFingerprint": "a" * 64}
    body = (
        {"mergeId": str(uuid4()), "confirmedUndo": value}
        if undo
        else {
            "sourceContactId": str(uuid4()),
            "targetContactId": str(uuid4()),
            "confirmedSamePerson": value,
        }
    )
    with pytest.raises(ValidationError):
        (UndoCommit if undo else MergeCommit).model_validate(common | body)


def test_preflight_does_not_claim_human_identity_confirmation():
    body = MergePreview(sourceContactId=str(uuid4()), targetContactId=str(uuid4()))
    assert "confirmedSamePerson" not in body.model_dump()
    assert UndoPreview(mergeId=str(uuid4())).choices == {}


def test_choices_cover_disjoint_hundred_custom_fields_without_data_loss():
    left, right = contact(), contact()
    left["customValues"] = {f"left_{i}": "original" for i in range(100)}
    right["customValues"] = {f"right_{i}": "source" for i in range(100)}
    keys = field_keys(left, right)
    assert len(keys) == 216
    choices = {key: "source" for key in keys}
    body = MergePreview(
        sourceContactId=right["id"], targetContactId=left["id"], choices=choices
    )
    selected = select_fields(left, right, body.choices, "source")
    assert selected["customValues"] == right["customValues"]
    assert selected["id"] == left["id"]
    assert Contact.model_validate(selected)


def test_atomic_document_and_program_pairs_and_original_source_are_preserved():
    left, right = contact(), contact()
    right.update(
        programId=2,
        program="Synthetic program",
        institutionalProfile={"documentTypeId": 1, "document": "00.12-X"},
    )
    original = deepcopy(right)
    result = select_fields(
        left, right, {"program": "source", "profile.document": "source"}, "source"
    )
    assert (result["programId"], result["program"]) == (2, "Synthetic program")
    assert result["institutionalProfile"]["document"] == "00.12-X"
    assert result["institutionalProfile"]["documentTypeId"] == 1
    assert right == original and left["institutionalProfile"] is None


@pytest.mark.parametrize(
    "key",
    [
        "id",
        "score",
        "institutionalProfile",
        "profile.documentTypeId",
        "custom.__proto__",
    ],
)
def test_unknown_and_derived_fields_cannot_be_selected(key):
    with pytest.raises(HTTPException) as error:
        select_fields(contact(), contact(), {key: "source"}, "source")
    assert error.value.status_code == 422


def test_identifiers_include_separate_human_declared_name_parts_and_document():
    value = contact()
    value["institutionalProfile"] = {
        "givenNames": "Synthetic Unique",
        "firstSurname": "Example",
        "document": "001-X",
        "email": "synthetic@example.test",
    }
    assert {"Synthetic", "Unique", "Example", "001-X", "synthetic@example.test"} <= set(
        identifiers(value)
    )


def test_historical_closure_survives_undo_and_follows_later_relationship(monkeypatch):
    a, b, c, outside = [str(uuid4()) for _ in range(4)]

    class Cursor:
        def execute(self, sql):
            assert "WHERE Active" not in sql
            return self

        def fetchall(self):
            return [(b, a), (c, a)]

    monkeypatch.setattr("app.modules.contacts.application.merge.present", lambda c: True)
    assert historical_ids(Cursor(), b) == {a, b, c}
    assert historical_ids(Cursor(), outside) == {outside}


def test_reserved_attempt_blocks_even_without_state_or_current_lease():
    class Cursor:
        def execute(self, sql, *args):
            self.sql = sql
            return self

        def fetchone(self):
            return (1,)

    c = Cursor()
    with pytest.raises(HTTPException) as error:
        analysis_guard(c, [str(uuid4())])
    assert error.value.status_code == 409
    assert "a.Status='reserved'" in c.sql
    assert "LeaseUntil" not in c.sql and "ConversationState" not in c.sql


def test_invalidation_changes_existing_generation_without_overwriting_evidence():
    class Cursor:
        def execute(self, sql, *args):
            self.sql = sql
            return self

        def fetchone(self):
            return (1,)

    c = Cursor()
    invalidate_analysis(c, [str(uuid4())])
    assert "crm_analysis.ConversationState" in c.sql
    assert "Generation=Generation+1" in c.sql and "Revision=Revision+1" in c.sql
    assert all(
        key not in c.sql for key in ["ContextJson=", "INSERT", "Receipt", "Feedback"]
    )
