import json

import pytest

from app.modules.ai.application.admissions_prompt import validate_reply
from app.modules.ai.infrastructure.providers import AiError


@pytest.mark.parametrize("bad", [
    {"answer": ["private answer"], "handoff": False, "references": []},
    {"answer": "private answer", "handoff": False, "references": [str(i) for i in range(6)]},
    {"answer": "private answer", "handoff": False, "references": [], "private_extra_key": "private value"},
])
def test_schema_diagnostic_retains_rejection_without_logging_completion(caplog, bad):
    with pytest.raises(AiError, match="admissions_invalid_structured_response"):
        validate_reply(json.dumps(bad), [], [], allow_memory=False)
    assert "admissions_response_validation fields=" in caplog.text
    assert "types=" in caplog.text
    assert "private" not in caplog.text


def test_unknown_references_are_still_rejected():
    with pytest.raises(AiError, match="admissions_unknown_reference"):
        validate_reply('{"answer":"Hola","handoff":false,"references":["unknown"]}', [], [], allow_memory=False)
