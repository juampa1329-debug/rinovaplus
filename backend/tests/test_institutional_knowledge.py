"""P6 boundary tests; SQL acceptance lives in qualify_p6_knowledge."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.institutional.api import core_permission
from app.institutional.knowledge import chunks
from app.institutional.knowledge_models import DNA, RecordWrite
from app.institutional.knowledge_policy import layout, release, rights


def record(**extra):
    return (
        dict(
            operation_id=uuid4(),
            revision=0,
            reason="Revisión",
            kind="collective",
            title="Fuente",
            body="Dato editorial",
            owner="Admisiones",
            origin="Documento institucional",
            valid_until="2027-12-31",
        )
        | extra
    )


@pytest.mark.parametrize(
    "extra",
    [
        {"title": "😀" * 81},
        {"owner": "😀" * 81},
        {"confidence": -1},
        {"confidence": 101},
        {"visibility": "conversation_only"},
        {"stage_id": uuid4()},
        {"valid_until": "2026-02-30"},
        {"state": "published"},
        {"actor_id": uuid4()},
        {"kind": "private"},
        {"kind": "dna", "dna": DNA(mission="Misión"), "body": "dato"},
    ],
)
def test_invalid_or_client_authority_cannot_cross_boundary(extra):
    with pytest.raises(ValidationError):
        RecordWrite(**record(**extra))


def test_confidence_zero_is_preserved_not_replaced_by_default():
    assert RecordWrite(**record(confidence=0)).confidence == 0


@pytest.mark.parametrize(
    "name", ["mission", "voice", "principles", "boundaries", "escalation"]
)
def test_DNA_rejects_null_and_surrogate_overflow(name):
    with pytest.raises(ValidationError):
        DNA(**{name: "\x00"})
    with pytest.raises(ValidationError):
        DNA(**{name: "😀" * 2001})


def test_UTF16_chunks_preserve_full_text_and_original_pages():
    pages = [
        {"page": 2, "text": "😀" * 3000},
        {"page": 7, "text": "Inscripción y matrícula"},
    ]
    result = chunks(pages)
    assert result[-1] == (7, "Inscripción y matrícula")
    assert len(result) > 3 and all(
        len(v.encode("utf-16-le")) <= 3200 for _, v in result
    )
    merged = result[0][1]
    for _, part in result[1:-1]:
        merged += part[60:]
    assert merged == "😀" * 3000


@pytest.mark.parametrize(
    "path,method,expected",
    [
        ("/api/institution/knowledge/search", "POST", ("sources.manage", "knowledge")),
        (
            "/api/institution/memory/records/id/publish",
            "POST",
            ("sources.manage", "memory"),
        ),
        ("/api/institution/conversation-memory/id", "GET", ("inbox.read", "inbox")),
        (
            "/api/institution/conversation-memory/id/record",
            "PUT",
            ("inbox.write", "inbox"),
        ),
    ],
)
def test_private_authority_does_not_inherit_source_management(path, method, expected):
    assert core_permission(path, method) == expected


def test_closed_map_and_append_only_versions_do_not_grant_academic_writes():
    value = layout()
    allowed = rights({})
    assert allowed["crm_knowledge6.Version"] == ("SELECT", "INSERT")
    assert allowed["crm_knowledge6.Journal"] == ("SELECT",)
    assert set(value["tables"].values()).isdisjoint(value["academic_tables"])
    assert len(release()) == 64
