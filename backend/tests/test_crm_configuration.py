"""Definition validation and route boundaries without external IO."""

from contextlib import contextmanager
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.modules.crm_configuration.application.service import (
    Configuration,
    ConfigurationWrite,
    CrmConfiguration,
    CrmDefinitionField,
    valid_value,
    validate_contact,
)
from app.sql_workspace import Contact


def configuration():
    return Configuration(
        stages=[{"key": "new", "label": "Guardada", "probability": None}],
        tags=["Real"],
        fields=[],
    )


@pytest.mark.parametrize(
    "kind,good,bad",
    [
        ("Text", "text", None),
        ("Number", "-12.50", "NaN"),
        ("List", "A", "C"),
        ("Date", "2026-10-16", "2026-02-30"),
        ("Boolean", "false", "False"),
        ("Email", "test@example.invalid", "bad"),
        ("Phone", "+57 3001234567", "DEMO-005"),
        ("URL", "https://example.invalid/path", "javascript:alert(1)"),
    ],
)
def test_values_and_required(kind, good, bad):
    field = CrmDefinitionField(
        key="human_field",
        label="Human field",
        type=kind,
        options=["A", "B"] if kind == "List" else [],
    )
    assert valid_value(field, good)
    if bad is not None:
        assert not valid_value(field, bad)
    assert valid_value(field, "")
    assert not valid_value(field.model_copy(update={"required": True}), "")


@pytest.mark.parametrize(
    "changes",
    [
        {"tags": ["Duplicada", "duplicada"]},
        {"tags": ["Con,coma"]},
        {"inactiveTags": ["Desconocida"]},
        {"stages": [{"key": "x", "label": "X", "probability": 101}]},
        {"stages": [{"key": "x", "label": "X"}, {"key": "y", "label": "x"}]},
        {"fields": [{"key": "lead_score", "label": "Score", "type": "Text"}]},
        {
            "fields": [
                {"key": "list", "label": "Lista", "type": "List", "options": ["A", "a"]}
            ]
        },
    ],
)
def test_invalid_definitions(changes):
    with pytest.raises(ValidationError):
        Configuration.model_validate(configuration().model_dump() | changes)


@pytest.mark.parametrize(
    "kind,value",
    [
        ("Text", "   "),
        ("Phone", " (---) "),
        ("URL", "https://bad host.invalid"),
        ("URL", "https://example.invalid:99999"),
    ],
)
def test_required_and_formats_cannot_be_whitespace(kind, value):
    field = CrmDefinitionField(key="field", label="Field", type=kind, required=True)
    assert not valid_value(field, value)


def contact(**changes):
    return Contact(
        id=str(uuid4()),
        name="Synthetic unit",
        phone="",
        city="",
        program="",
        schedule="",
        stage="Guardada",
        tags="Real",
        notes="",
        type="",
        interests="",
        customValues={},
        **changes,
    )


def test_contact_checks_inactive_retention_required_and_unknown_values(monkeypatch):
    config = configuration()
    config.stages[0].active = False
    config.inactiveTags = ["Real"]
    config.fields = [
        CrmDefinitionField(key="hidden", label="Hidden", type="Text", active=False)
    ]
    monkeypatch.setattr(
        "app.modules.crm_configuration.application.service.read_configuration", lambda c: (config, "1")
    )
    value = contact()
    value.customValues = {"hidden": "original", "legacy": "untouched"}
    previous = value.model_dump()
    validate_contact(None, value, previous)

    with pytest.raises(HTTPException) as error:
        validate_contact(None, value)
    assert error.value.status_code == 422
    value.customValues["hidden"] = "changed"
    with pytest.raises(HTTPException):
        validate_contact(None, value, previous)
    value.customValues = previous["customValues"]
    config.fields.append(
        CrmDefinitionField(
            key="required", label="Required", type="Email", required=True
        )
    )
    with pytest.raises(HTTPException):
        validate_contact(None, value, previous)
    value.customValues["required"] = "test@example.invalid"
    validate_contact(None, value, previous)


def test_uncatalogued_stage_can_only_be_retained_on_same_contact(monkeypatch):
    config = configuration()
    monkeypatch.setattr(
        "app.modules.crm_configuration.application.service.read_configuration", lambda c: (config, "1")
    )
    value = contact()
    value.stage = "Historic mixed-version stage"
    validate_contact(None, value, value.model_dump())
    with pytest.raises(HTTPException):
        validate_contact(None, value)


class Cursor:
    def __init__(self):
        self.result = None
        self.operation = None
        self.writes = []

    def execute(self, sql, *args):
        self.result = self.operation if "SELECT PayloadHash" in sql else None
        if sql.startswith(("INSERT", "UPDATE")):
            self.writes.append((sql, args))
        return self

    def fetchone(self):
        return self.result


def test_write_replay_conflict_and_non_destructive_contract(monkeypatch):
    config = configuration()
    cursor = Cursor()

    @contextmanager
    def transaction(write=False):
        yield cursor

    store = type("Workspace", (), {"transaction": staticmethod(transaction)})()
    monkeypatch.setattr(
        "app.modules.crm_configuration.application.service.read_configuration", lambda c: (config, "1")
    )
    repository = CrmConfiguration(store)
    body = ConfigurationWrite(
        operationId=str(uuid4()), expectedRevision="1", config=config
    )
    result = repository.save(body)
    assert result["revision"] == "2" and len(cursor.writes) == 2
    digest = cursor.writes[-1][1][1]
    cursor.operation = (digest, 2)
    assert repository.save(body)["revision"] == "1"
    assert len(cursor.writes) == 2
    cursor.operation = (b"x" * 32, 2)
    with pytest.raises(HTTPException) as error:
        repository.save(body)
    assert error.value.status_code == 409
    cursor.operation = None
    with pytest.raises(HTTPException):
        repository.save(body.model_copy(update={"expectedRevision": "0"}))
    removed = configuration().model_copy(update={"stages": []})
    with pytest.raises(HTTPException) as error:
        repository.save(body.model_copy(update={"config": removed}))
    assert error.value.status_code == 422 and len(cursor.writes) == 2
