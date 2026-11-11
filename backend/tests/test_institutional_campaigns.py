"""P8 protocol, scheduling and CRM/Meta distinction without database access."""

from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.institutional.campaign_models import (
    Flow,
    Quiet,
    Save,
    Step,
    Template,
    next_allowed,
)
from app.institutional.campaign_policy import layout, release, rights
from app.institutional.campaigns import matches, render_crm


def test_own_frozen_release_and_seven_native_bindings():
    assert len(release()) == 64
    assert len([k for k in layout()["tables"] if k.startswith("crm_campaign8.")]) == 7
    assert rights({})["crm_campaign8.Event"] == ("SELECT", "INSERT")
    assert rights({})["crm_campaign8.Version"] == ("SELECT", "INSERT")


@pytest.mark.parametrize(
    "extra",
    [
        {"status": "APPROVED"},
        {"actor_id": str(uuid4())},
        {"name": "😀" * 81},
        {"document": {"filters": {"keywords": [""]}}},
    ],
)
def test_no_client_approval_authority_or_unbounded_documents(extra):
    command = (
        dict(
            operation_id=uuid4(),
            reason="Revisión",
            name="Segmento",
            kind="segment",
            document={"filters": {}},
        )
        | extra
    )
    with pytest.raises(ValidationError):
        Save(**command)


@pytest.mark.parametrize(
    "doc",
    [
        {"body": "Hola {{nombre}}"},
        {"body": "Hola", "variables": {"x": {"source": "literal", "value": "texto"}}},
        {"body": "{{", "variables": {}},
        {"blocks": [{"type": "image", "url": "http://127.0.0.1/private"}]},
    ],
)
def test_template_bindings_and_public_links_are_validated(doc):
    with pytest.raises(ValidationError):
        Template(**doc)


def test_saved_filters_normalize_uuid_case_but_do_not_invent_academic_data():
    id = uuid4()
    assert matches(
        {
            "CanonicalContactId": str(id).upper(),
            "Stage": "aspirante",
            "Tags": "Nuevo; Bogotá",
            "IncomingText": "Quiero ADMISIONES",
        },
        dict(contact_ids=[str(id)], tags=["nuevo"], keywords=["admisiones"]),
    )
    assert not matches({"ProgramId": None}, dict(program_ids=[10]))


def test_template_renders_declared_fields_as_plain_text():
    t = Template(
        body="Hola {{nombre}}",
        variables={"nombre": {"source": "customer_first_name"}},
        blocks=[
            {
                "type": "button",
                "text": "Programas",
                "url": "https://cbn.example/programas",
            }
        ],
    )
    assert (
        render_crm(t.model_dump(), dict(Name="Ana Pérez"), "Admisiones")
        == "Hola Ana\nProgramas https://cbn.example/programas"
    )


def test_overnight_quiet_hours_use_start_day_and_real_timezone():
    q = Quiet(
        enabled=True,
        timezone="America/Bogota",
        start_time="21:00",
        end_time="08:00",
        days=[0],
    )
    assert next_allowed(datetime(2026, 10, 27, 3), q) == datetime(2026, 10, 27, 13)
    assert next_allowed(datetime(2026, 10, 28, 3), q) == datetime(2026, 10, 28, 3)


def test_DST_quiet_window_is_a_real_UTC_transition():
    q = Quiet(
        enabled=True, timezone="America/New_York", start_time="01:00", end_time="03:00"
    )
    assert next_allowed(datetime(2026, 11, 1, 5, 30), q) == datetime(2026, 11, 1, 8)


@pytest.mark.parametrize(
    "extra",
    [
        {"timezone": "Mars/CBN"},
        {"days": [7]},
        {"days": [1, 1]},
        {"start_time": "08:00", "end_time": "08:00"},
    ],
)
def test_invalid_quiet_windows_rejected(extra):
    with pytest.raises(ValidationError):
        Quiet(**extra)


def test_send_must_choose_exactly_one_template_contract():
    with pytest.raises(ValidationError):
        Step(kind="send")
    with pytest.raises(ValidationError):
        Step(kind="send", crm_template_id=uuid4(), meta_template_id=uuid4())
    assert Step(kind="send", crm_template_id=uuid4()).crm_template_id


@pytest.mark.parametrize(
    "extra",
    [
        {"steps": []},
        {"steps": [{"kind": "wait"}] * 21},
        {"scheduled_local": "2026-03-08T02:30", "timezone": "America/New_York"},
        {"scheduled_local": "2026-11-01T01:30", "timezone": "America/New_York"},
        {
            "ab_test": {"enabled": True},
            "steps": [{"kind": "send", "crm_template_id": str(uuid4())}],
        },
    ],
)
def test_closed_flow_bounds_and_ambiguous_local_time(extra):
    with pytest.raises(ValidationError):
        Flow(**(dict(integration_id=uuid4(), steps=[{"kind": "wait"}]) | extra))


@pytest.mark.parametrize("kind", ["image", "audio", "video", "document"])
def test_uploaded_asset_and_bounded_block_delay_are_closed(kind):
    from app.institutional.campaign_models import Block

    v = Block(type=kind, asset_id=uuid4(), delay_ms=15000)
    assert v.asset_id and v.delay_ms == 15000
    with pytest.raises(ValidationError):
        Block(type=kind, asset_id=uuid4(), url="https://cbn.example/file")
    with pytest.raises(ValidationError):
        Block(type=kind, asset_id=uuid4(), delay_ms=300001)


def test_private_DNS_media_destination_is_rejected_before_connect(
    monkeypatch, tmp_path
):
    from unittest.mock import Mock

    from app.institutional import campaign_assets
    from app.modules.channels.providers import ProviderFailure

    monkeypatch.setattr(
        campaign_assets.socket,
        "getaddrinfo",
        lambda *a, **kw: [(2, 1, 6, "", ("127.0.0.1", 443))],
    )
    connection = Mock()
    monkeypatch.setattr(campaign_assets.socket, "create_connection", connection)
    with pytest.raises(ProviderFailure):
        campaign_assets.retrieve(
            "https://files.example/test.png", tmp_path / "never-written"
        )
    connection.assert_not_called()


def test_video_limits_reject_before_transcode_and_cleanup(monkeypatch, tmp_path):
    import json
    from types import SimpleNamespace

    from fastapi import HTTPException

    from app.institutional import campaign_media
    from app.modules.inbox.infrastructure import media_files

    monkeypatch.setenv("CRM_AI_STATE_DIR", str(tmp_path))
    id = str(uuid4())
    source = media_files.path(id, ".part")
    source.write_bytes(b"controlled video fixture")
    monkeypatch.setattr(
        campaign_media.subprocess,
        "run",
        lambda *a, **kw: SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "format": {"duration": 121},
                    "streams": [{"codec_type": "video", "width": 16, "height": 16}],
                }
            ).encode(),
        ),
    )
    with pytest.raises(HTTPException) as failure:
        campaign_media.inspect(id, "test.mp4", "video")
    assert failure.value.status_code == 413 and not source.exists()


@pytest.mark.parametrize("channel", ["whatsapp", "instagram", "messenger", "tiktok"])
def test_native_media_caption_parts_preserve_variables_order_and_delay(
    monkeypatch, channel
):
    from app.institutional import campaign_assets, campaign_chat

    asset = str(uuid4())
    doc = dict(channel=channel)
    template = dict(
        body="",
        variables={"nombre": {"source": "customer_first_name"}},
        blocks=[
            dict(
                type="image",
                asset_id=asset,
                text="Hola {{nombre}}",
                url="",
                delay_ms=15000,
            ),
            dict(type="text", text="Consulta {{nombre}}", url="", delay_ms=10),
        ],
    )
    monkeypatch.setattr(campaign_chat, "template", lambda *a, **kw: template)
    monkeypatch.setattr(
        campaign_assets, "library_file", lambda *a: (dict(kind="image"), {})
    )
    parts = campaign_chat.parts(None, None, doc, {}, "A", dict(Name="Ana Pérez"), "CBN")
    assert parts[0]["kind"] == "image" and parts[0]["delay_ms"] == 15000
    assert parts[-1]["text"] == "Consulta Ana"
    if channel == "whatsapp":
        assert len(parts) == 2 and parts[0]["text"] == "Hola Ana"
    else:
        assert (
            len(parts) == 3
            and parts[0]["text"] == ""
            and parts[1]["text"] == "Hola Ana"
        )


def test_materialized_media_includes_template_library_in_total_quota(monkeypatch):
    from types import SimpleNamespace

    from fastapi import HTTPException

    from app.institutional import campaign_assets

    monkeypatch.setattr(campaign_assets, "native_quota", lambda *a: None)
    monkeypatch.setattr(campaign_assets, "institution", lambda s: "institution")
    c = SimpleNamespace(
        execute=lambda *a: SimpleNamespace(
            fetchval=lambda: campaign_assets.files.TOTAL_BYTES
        )
    )
    with pytest.raises(HTTPException) as e:
        campaign_assets.quota(c, None, "conversation")
    assert e.value.status_code == 413


@pytest.mark.parametrize("kind", ["audio", "video", "image", "document"])
def test_media_only_template_content_is_valid_without_inventing_a_caption(
    monkeypatch, kind
):
    from app.institutional import campaign_chat

    value = dict(body="", variables={}, blocks=[])
    monkeypatch.setattr(campaign_chat, "template", lambda *a, **kw: value)
    monkeypatch.setattr(
        campaign_chat, "parts", lambda *a, **kw: [dict(kind=kind, text="")]
    )
    assert campaign_chat.content(None, None, {}, {}, "A", {}, "CBN") == "[" + kind + "]"


def test_delivery_signature_is_bound_to_profile_media_queue_and_expiry(monkeypatch):
    import base64
    from types import SimpleNamespace

    from app.institutional import campaign_delivery as d

    monkeypatch.setattr(d, "institution", lambda s: "institution")
    s = SimpleNamespace(review={"secrets_key": base64.b64encode(b"a" * 32).decode()})
    a, q = str(uuid4()), str(uuid4())
    original = d.signature(s, a, q, 100)
    assert original != d.signature(s, a, q, 101)
    assert original != d.signature(s, str(uuid4()), q, 100)
    assert original != d.signature(s, a, str(uuid4()), 100)
