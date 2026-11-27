from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.institutional.agents_api import ProgramWrite
from app.institutional.program_validation import fields, response


def test_saved_academic_validation_identifies_the_field_without_echoing_input():
    secret = "private-value-" * 200
    with pytest.raises(ValidationError) as rejected:
        ProgramWrite(operation_id=uuid4(), revision=1, name="Programa", commercial={"aliases": secret})
    payload = response("/api/v1/agents/programs/13", "PUT", rejected.value.errors())
    assert payload["fields"] == ["commercial.aliases"]
    assert secret not in str(payload)
    assert "input" not in payload and "ctx" not in payload


def test_unknown_dynamic_keys_are_not_echoed_and_output_is_bounded():
    value = fields([{"loc": ("body", "commercial", "private@example.invalid"), "input": "secret"}] * 20)
    assert value == ["commercial"]
    assert fields([{"loc": ("body", "private@example.invalid")}]) == []


def test_root_rejections_report_only_allowlisted_categories():
    payload = response("/api/v1/agents/programs/13", "PUT", [
        {"loc": ("body", "private@example.invalid"), "type": "extra_forbidden", "input": "private"},
        {"loc": ("body",), "type": "private@example.invalid", "msg": "private"},
    ])
    assert payload["fields"] == []
    assert payload["validation_types"] == ["extra_forbidden"]
    assert "private" not in str(payload)


@pytest.mark.parametrize("path,method", [
    ("/api/institution/auth/login", "POST"),
    ("/api/v1/agents/profiles/id", "PUT"),
    ("/api/v1/agents/programs/13", "GET"),
])
def test_other_endpoints_keep_their_existing_generic_validation(path, method):
    assert response(path, method, [{"loc": ("body", "name")}]) == {"detail": "invalid_request"}
