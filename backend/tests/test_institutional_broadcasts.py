"""P7 command, template protocol and capability boundaries without SQL IO."""

import json
from datetime import datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.institutional.api import core_permission
from app.institutional.broadcast_models import (
    CampaignWrite,
    ConsentWrite,
    Filters,
    TemplateWrite,
    scheduled,
)
from app.institutional.broadcast_policy import layout, release, rights
from app.institutional.broadcast_templates import (
    definition,
    fetch,
    fingerprint,
    parameters,
    send,
)
from app.modules.channels import providers


def command(**extra):
    return dict(operation_id=uuid4(), reason="Revisión institucional", **extra)


def campaign(**extra):
    return command(
        **(
            dict(
                name="Admisiones",
                integration_id=uuid4(),
                template_id=uuid4(),
                template_version=1,
            )
            | extra
        )
    )


@pytest.mark.parametrize(
    "extra",
    [
        {"status": "APPROVED"},
        {"actor_id": str(uuid4())},
        {"name": "😀" * 81},
        {"name": "a\x00"},
        {"timezone": "Mars/CBN"},
        {"scheduled_local": "2026-03-08T02:30", "timezone": "America/New_York"},
        {"scheduled_local": "2026-11-01T01:30", "timezone": "America/New_York"},
        {"header_media_url": "http://127.0.0.1/private"},
        {"template_version": 0},
    ],
)
def test_client_cannot_supply_approval_authority_or_invalid_schedule(extra):
    with pytest.raises((ValidationError, HTTPException)):
        CampaignWrite(**campaign(**extra))


@pytest.mark.parametrize(
    "extra",
    [
        {"confirmed": False},
        {"evidence": ""},
        {"origin": "x\x00"},
        {"expires_at": None},
        {"expires_at": "2027-01-01T00:00"},
        {"expires_at": "2020-01-01T00:00:00Z"},
        {"evidence": "😀" * 501},
    ],
)
def test_explicit_consent_requires_bound_evidence_and_aware_future_expiry(extra):
    with pytest.raises(ValidationError):
        ConsentWrite(
            **command(
                **(
                    dict(
                        state="granted",
                        confirmed=True,
                        evidence="Formulario firmado",
                        origin="Admisiones",
                        expires_at="2027-12-31T00:00:00Z",
                    )
                    | extra
                )
            )
        )


@pytest.mark.parametrize(
    "extra",
    [
        {"program_ids": [0]},
        {"cities": [""]},
        {"tags": ["x\x00"]},
        {"stages": ["😀" * 251]},
    ],
)
def test_filter_bounds(extra):
    with pytest.raises(ValidationError):
        Filters(**extra)


def test_wall_time_is_converted_to_UTC_and_aware_offset_is_preserved():
    assert scheduled("2026-10-27T08:00", "America/Bogota") == datetime(2026, 10, 27, 13)
    assert scheduled("2026-10-27T08:00+01:00", "America/Bogota") == datetime(
        2026, 10, 27, 7
    )


def test_template_components_and_named_aliases_are_normalized():
    template = TemplateWrite(
        **command(
            name="admisiones",
            body_text="Hola {{nombre}}, {{nombre}} {{programa}}",
            header_type="TEXT",
            header_text="CBN {{sede}}",
            footer_text="Admisiones",
            buttons=[
                {"type": "URL", "text": "Ver", "url": "https://cbn.example/{{1}}"},
                {
                    "type": "PHONE_NUMBER",
                    "text": "Llamar",
                    "phone_number": "+573100000000",
                },
            ],
        )
    )
    value = definition(template)
    assert value[0]["text"] == "Hola {{1}}, {{1}} {{2}}"
    assert {v["type"] for v in value} == {"BODY", "HEADER", "FOOTER", "BUTTONS"}


@pytest.mark.parametrize("kind", ["IMAGE", "VIDEO", "DOCUMENT"])
def test_media_header_requires_Meta_example_and_public_delivery_URL(kind):
    with pytest.raises(HTTPException):
        definition(
            TemplateWrite(
                **command(name="admisiones", body_text="Hola", header_type=kind)
            )
        )
    value = definition(
        TemplateWrite(
            **command(
                name="admisiones",
                body_text="Hola",
                header_type=kind,
                header_media_handle="meta-example",
            )
        )
    )
    with pytest.raises(HTTPException):
        parameters(
            {"Definition": json.dumps(value), "Name": "admisiones", "Language": "es"},
            {"variables": {}},
            person(),
            "Campaña",
        )
    result, _ = parameters(
        {"Definition": json.dumps(value), "Name": "admisiones", "Language": "es"},
        {"variables": {}, "header_media_url": "https://cbn.example/archivo"},
        person(),
        "Campaña",
    )
    assert result["components"][0]["parameters"][0]["type"] == kind.lower()


def person():
    return dict(
        Name="Ana CBN",
        CustomValues="{}",
        City="Bogotá",
        Phone="573100000000",
        Program="Programa",
        Stage="Interesado",
        Schedule="Diurna",
    )


def test_all_parameter_groups_are_explicit_and_extra_bindings_are_rejected():
    components = [
        {"type": "HEADER", "format": "TEXT", "text": "CBN {{1}}"},
        {"type": "BODY", "text": "Hola {{1}}"},
        {
            "type": "BUTTONS",
            "buttons": [{"type": "URL", "url": "https://cbn.example/{{1}}"}],
        },
    ]
    template = {
        "Name": "admisiones",
        "Language": "es",
        "Definition": json.dumps(components),
    }
    variables = {
        "header.1": {"source": "literal", "value": "Principal"},
        "body.1": {"source": "customer_name"},
        "button.0.1": {"source": "literal", "value": "programas"},
    }
    result, text = parameters(
        template, {"variables": variables}, person(), "Admisiones"
    )
    assert text == "Hola Ana CBN" and len(result["components"]) == 3
    with pytest.raises(HTTPException):
        parameters(
            template,
            {"variables": variables | {"body.99": {"source": "literal", "value": "x"}}},
            person(),
            "Admisiones",
        )


def test_catalog_fetch_never_follows_arbitrary_provider_next_URL():
    paths = []

    def request(a, m, p, body=None, **kw):
        paths.append(p)
        return (
            {
                "data": [],
                "paging": {
                    "next": "http://127.0.0.1/internal",
                    "cursors": {"after": "cursor1"},
                },
            }
            if len(paths) == 1
            else {"data": []}
        )

    assert fetch({"configuration": {"wabaId": "123"}}, request) == []
    assert paths == ["123/message_templates", "123/message_templates"]


def test_frontier_runs_after_live_catalog_and_immediately_before_POST():
    events = []
    components = [{"type": "BODY", "text": "Hola"}]

    def request(a, m, p, body=None, **kw):
        events.append(m)
        return (
            {
                "data": [
                    {
                        "id": "777",
                        "name": "admisiones",
                        "language": "es",
                        "status": "APPROVED",
                        "components": components,
                    }
                ]
            }
            if m == "GET"
            else {"messages": [{"id": "wamid.controlled"}]}
        )

    payload = {
        "target": "573100000000",
        "template": {"name": "admisiones"},
        "broadcastTemplate": {
            "provider_id": "777",
            "name": "admisiones",
            "language": "es",
            "components_fingerprint": fingerprint(components),
        },
    }
    assert (
        send(
            {"configuration": {"wabaId": "123", "phoneNumberId": "456"}},
            payload,
            before_send=lambda: events.append("frontier"),
            request=request,
        )
        == "wamid.controlled"
    )
    assert events == ["GET", "frontier", "POST"]


@pytest.mark.parametrize("status", ["PENDING", "REJECTED", "PAUSED", "DISABLED"])
def test_live_catalog_rejection_prevents_frontier_and_POST(status):
    calls = []

    def request(a, m, p, body=None, **kw):
        calls.append(m)
        return {
            "data": [
                {
                    "id": "777",
                    "name": "admisiones",
                    "language": "es",
                    "status": status,
                    "components": [],
                }
            ]
        }

    with pytest.raises(providers.ProviderFailure):
        send(
            {"configuration": {"wabaId": "123"}},
            {
                "broadcastTemplate": {
                    "provider_id": "777",
                    "name": "admisiones",
                    "language": "es",
                    "components_fingerprint": fingerprint([]),
                }
            },
            before_send=lambda: calls.append("frontier"),
            request=request,
        )
    assert calls == ["GET"]


def test_partition_uses_only_own_spanish_tables_and_immutable_history():
    mapping = layout()
    assert len(mapping["tables"]) == 130 and len(mapping["academic_tables"]) == 30
    assert not set(mapping["academic_tables"]) & set(mapping["tables"].values())
    granted = rights({})
    assert granted["crm_broadcast7.Template"] == ("SELECT", "INSERT")
    assert granted["crm_broadcast7.Consent"] == ("SELECT", "INSERT")
    assert granted["crm_broadcast7.Journal"] == ("SELECT",)
    assert len(release()) == 64


def test_bulk_route_requires_campaigns_permission_and_module():
    assert core_permission("/api/institution/broadcasts/options", "GET") == (
        "campaigns.manage",
        "broadcasts",
    )
