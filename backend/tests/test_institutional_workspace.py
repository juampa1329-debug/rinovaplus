"Boundary tests for P3; no SQL connection or private configuration is read."

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.institutional.api import core_permission
from app.institutional.auth import COOKIE, cookie_name
from app.institutional.spanish import RIGHTS
from app.institutional.workspace import (
    ContactWrite,
    ConversationWrite,
    MergeWrite,
    NoteWrite,
    TaskWrite,
    risk_projection,
)
from app.institutional.workspace_policy import layout, principal, rights


def test_preview_cookie_is_separate_and_parent_cookie_is_preserved():
    assert cookie_name(SimpleNamespace()) == COOKIE
    assert (
        cookie_name(
            SimpleNamespace(ticket={"version": "cbn-institutional-spanish-p3-v1"})
        )
        == COOKIE + "_workspace"
    )
    assert (
        cookie_name(SimpleNamespace(ticket={"version": "cbn-institutional-spanish-v1"}))
        == COOKIE
    )


def command(**kwargs):
    return {"operationId": str(uuid4()), "revision": "1", **kwargs}


def evidence():
    now = datetime.now(timezone.utc)
    row = {
        "AsOfUtc": now.replace(tzinfo=None),
        "Status": "known",
        "FormulaVersion": "churn-rubric-v1",
        "InputSequence": 12,
        "StageSnapshot": "Nueva",
        "RiskLevel": "high",
        "RiskScore": 80,
        "ReasonsJson": '["waiting_over_48h"]',
        "EvidenceJson": json.dumps(
            {
                "status": "known",
                "score": 80,
                "level": "high",
                "formula_version": "churn-rubric-v1",
                "input_sequence": 12,
                "evidence_message_ids": [str(uuid4())],
            }
        ),
    }
    return row, now


def test_closed_partition_and_readonly_academic_tables():
    value = layout()
    assert len(value["tables"]) == 114 and len(value["academic_tables"]) == 30
    assert not set(value["academic_tables"]) & set(value["tables"].values())
    assert rights(RIGHTS)["crm_workspace.Journal"] == ("SELECT",)
    with pytest.raises(ValueError):
        principal("HORARIOSSIIE")


@pytest.mark.parametrize(
    "path,method,expected",
    [
        ("clients", "GET", ("crm.read", "clients")),
        ("clients/uuid", "PUT", ("crm.write", "clients")),
        ("inbox", "GET", ("inbox.read", "inbox")),
        ("inbox/uuid/detail", "GET", ("inbox.read", "inbox")),
        ("conversations/uuid/messages", "GET", ("inbox.read", "inbox")),
        ("conversations/uuid", "PUT", ("inbox.write", "inbox")),
        ("conversations/uuid", "GET", ("crm.read", "clients")),
        ("conversations/uuid/manual", "PUT", ("crm.write", "clients")),
        ("tasks", "GET", ("crm.read", "clients")),
        ("merges/id", "POST", ("crm.write", "clients")),
    ],
)
def test_every_surface_has_its_own_authority(path, method, expected):
    assert core_permission("/api/institution/workspace/" + path, method) == expected


def test_observed_read_watermark_is_mandatory():
    values = command(state="open", priority="normal", mode="human", unread=False)
    with pytest.raises(ValidationError):
        ConversationWrite(**values)
    assert ConversationWrite(**values, readThrough="0").readThrough == "0"


@pytest.mark.parametrize("value", [True, False, "80", 80.5, -1, 101])
def test_invalid_risk_result_is_not_a_prediction(value):
    row, now = evidence()
    row["RiskScore"] = value
    result = risk_projection(row, sequence=12, stage="Nueva", state="open", now=now)
    assert result["score"] is None and result["status"] == "unknown"


@pytest.mark.parametrize(
    "change",
    [
        {"InputSequence": 11},
        {"StageSnapshot": "Otra"},
        {"AsOfUtc": datetime(2020, 1, 1)},
        {"AsOfUtc": datetime(2099, 1, 1)},
        {"FormulaVersion": "trained-model-v1"},
        {"EvidenceJson": "{}"},
        {
            "EvidenceJson": (
                '{"status":"known","formula_version":"chu'
                'rn-rubric-v1","input_sequence":12}'
            )
        },
        {"EvidenceJson": "invalid-json"},
        {"Status": "unknown"},
    ],
)
def test_risk_requires_same_current_complete_rule_evidence(change):
    row, now = evidence()
    row.update(change)
    result = risk_projection(row, sequence=12, stage="Nueva", state="open", now=now)
    assert result["status"] == "unknown" and result["probability"] is None


def test_current_rule_is_not_probability_or_manual_value():
    row, now = evidence()
    result = risk_projection(row, sequence=12, stage="Nueva", state="open", now=now)
    assert (
        result["source"] == "rule"
        and result["fresh"]
        and result["score"] == 80
        and result["probability"] is None
    )
    assert (
        risk_projection(row, sequence=12, stage="Nueva", state="closed", now=now)[
            "status"
        ]
        == "not_applicable"
    )
    assert (
        risk_projection(None, sequence=0, stage="Nueva", state="open", now=now)[
            "status"
        ]
        == "unknown"
    )


def test_task_requires_timezone_and_human_merge_confirmation():
    with pytest.raises(ValidationError):
        TaskWrite(
            **command(
                title="Tarea", conversationId=str(uuid4()), dueAt="2026-10-26T15:00:00"
            )
        )
    result = TaskWrite(
        **command(
            title=" Tarea ",
            conversationId=str(uuid4()),
            dueAt="2026-10-26T15:00:00-05:00",
        )
    )
    assert result.dueAt == "2026-10-26T20:00:00+00:00" and result.title == "Tarea"
    with pytest.raises(ValidationError):
        MergeWrite(
            **command(
                sourceContactId=str(uuid4()),
                targetContactId=str(uuid4()),
                confirmedSamePerson="true",
            )
        )
    with pytest.raises(ValidationError):
        NoteWrite(**command(body=" "))


@pytest.mark.parametrize(
    "field,limit",
    [("name", 100), ("phone", 40), ("city", 100), ("notes", 1000), ("interests", 300)],
)
def test_contact_uses_SQL_utf16_limit(field, limit):
    values = dict(
        id=str(uuid4()),
        name="QA",
        phone="",
        city="",
        programId=None,
        program="",
        schedule="",
        stage="Nueva",
        tags="",
        notes="",
        type="",
        interests="",
        customValues={},
    )
    values[field] = "😀" * (limit // 2 + 1)
    with pytest.raises(ValidationError):
        ContactWrite(**command(client=values))


def test_note_and_task_use_SQL_utf16_limit():
    with pytest.raises(ValidationError):
        NoteWrite(**command(body="😀" * 1001))
    with pytest.raises(ValidationError):
        TaskWrite(**command(conversationId=str(uuid4()), title="😀" * 61))
