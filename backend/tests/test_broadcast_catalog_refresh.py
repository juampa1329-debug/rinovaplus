import ast
import json
import re
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.institutional import broadcast_catalog_refresh as refresh
from app.institutional import broadcast_dispatch as dispatch
from app.institutional.broadcast_audience import contact_details
from app.institutional.broadcast_templates import display_parts


@pytest.fixture
def harness(monkeypatch):
    c = Mock()
    settings = SimpleNamespace(postgres_profile=False)
    campaign = dict(
        CampaignId="campaign",
        IntegrationId="account",
        State="running",
        Revision=1,
        Epoch=2,
        ActorId="actor",
        ActorSessionId="session",
        ActorAuthVersion=3,
    )
    actor = dict(
        UserId="actor",
        Actions=json.dumps(["campaigns.manage", "inbox.write", "crm.read"]),
    )
    account = dict(
        IntegrationId="account",
        RowVersion=b"one",
        Channel="whatsapp",
        RequestedStatus="connected",
        VerifiedStatus="verified",
        ApplicationState="active",
    )
    adapter = {"configuration": {"wabaId": "waba"}}
    remote = dict(
        id="remote",
        name="reviewed_template",
        language="es",
        category="MARKETING",
        status="APPROVED",
        components=[dict(type="BODY", text="Hola")],
    )
    request = Mock(return_value={"data": [remote]})
    writes = Mock()
    moment = [100.0]
    queries = []

    @contextmanager
    def tx(*args, **kwargs):
        yield c

    monkeypatch.setattr(refresh, "transaction", tx)
    monkeypatch.setattr(refresh, "enabled", lambda *args: True)
    monkeypatch.setattr(
        refresh, "configuration", lambda *args: {"OutboundEnabled": True}
    )
    monkeypatch.setattr(refresh, "current", lambda *args: campaign)
    monkeypatch.setattr(refresh, "authority", Mock(return_value=actor))
    monkeypatch.setattr(refresh, "account", lambda *args: account)
    monkeypatch.setattr(
        refresh, "provider_account", lambda *args: (adapter, {"SecretId": "credential"})
    )
    monkeypatch.setattr(refresh, "institution", lambda *args: "institution")

    def due(*args):
        queries.append(args[1])
        return {"CampaignId": "campaign"}

    monkeypatch.setattr(refresh, "one", due)
    monkeypatch.setattr(refresh.templates, "append", writes)
    monkeypatch.setattr(refresh, "catalog", lambda *args: [])
    monkeypatch.setattr(refresh, "audit", Mock())
    worker = refresh.Refresher(settings, request=request, clock=lambda: moment[0])
    return SimpleNamespace(
        c=c,
        settings=settings,
        campaign=campaign,
        actor=actor,
        account=account,
        request=request,
        writes=writes,
        worker=worker,
        moment=moment,
        queries=queries,
    )


def test_refresh_is_catalog_get_only_and_throttled(harness):
    h = harness
    assert h.worker.once()
    assert not h.worker.once()
    h.request.assert_called_once_with(
        {"configuration": {"wabaId": "waba"}},
        "GET",
        "waba/message_templates",
        params={
            "limit": 100,
            "fields": (
                "id,name,language,category,status,components,"
                "quality_score,rejected_reason"
            ),
        },
    )
    assert h.writes.call_count == 1
    assert "-45" in h.queries[0] and "running','scheduled" in h.queries[0]


def test_refresh_is_disabled_in_rehearsal(harness):
    h = harness
    h.settings.postgres_profile = True
    assert not h.worker.once()
    assert not h.queries
    h.request.assert_not_called()


@pytest.mark.parametrize("change", [{"State": "paused"}, {"State": "completed"}])
def test_inactive_campaign_does_not_read_provider(harness, change):
    h = harness
    h.campaign.update(change)
    with pytest.raises(HTTPException):
        h.worker.once()
    h.request.assert_not_called()


def test_revocation_before_and_during_get_never_updates_catalog(harness, monkeypatch):
    h = harness
    monkeypatch.setattr(
        refresh, "authority", Mock(side_effect=HTTPException(403, "revoked"))
    )
    with pytest.raises(HTTPException):
        h.worker.once()
    h.request.assert_not_called()
    h.moment[0] += 61
    monkeypatch.setattr(
        refresh, "authority", Mock(side_effect=[h.actor, HTTPException(403, "revoked")])
    )
    with pytest.raises(HTTPException):
        h.worker.once()
    assert h.request.call_count == 1
    h.writes.assert_not_called()


def test_account_binding_change_during_get_keeps_previous_evidence(harness):
    h = harness

    def changed(*args, **kwargs):
        h.account["RowVersion"] = b"two"
        return {"data": []}

    h.request.side_effect = changed
    with pytest.raises(HTTPException, match="broadcast_catalog_binding_changed"):
        h.worker.once()
    h.writes.assert_not_called()


def test_failed_get_does_not_fabricate_freshness_or_immediately_retry(harness):
    h = harness
    h.request.side_effect = HTTPException(502, "temporary")
    with pytest.raises(HTTPException):
        h.worker.once()
    assert not h.worker.once()
    h.writes.assert_not_called()
    assert h.request.call_count == 1


def test_remote_removal_stays_not_found_and_preserves_local_library_controls(
    harness, monkeypatch
):
    h = harness
    monkeypatch.setattr(
        refresh,
        "catalog",
        lambda *args: [
            dict(
                Origin="provider",
                ProviderId="removed",
                Name="removed_template",
                Language="es",
                Category="MARKETING",
                Definition="[]",
            )
        ],
    )
    assert h.worker.once()
    removed = h.writes.call_args_list[-1].args[3]
    assert removed["status"] == "NOT_FOUND"
    assert "paused" not in h.writes.call_args_list[-1].kwargs
    assert "removed" not in h.writes.call_args_list[-1].kwargs


@pytest.mark.parametrize(
    "reason,waiting",
    [
        ("broadcast_template_refresh_required", True),
        ("broadcast_authority_revoked", False),
    ],
)
def test_catalog_wait_preserves_unsent_recipient_but_not_revoked_authority(
    monkeypatch, reason, waiting
):
    c = Mock()

    @contextmanager
    def tx(*args, **kwargs):
        yield c

    monkeypatch.setattr(dispatch, "transaction", tx)
    monkeypatch.setattr(dispatch, "enabled", lambda *a: True)
    monkeypatch.setattr(dispatch, "configuration", lambda *a: {"OutboundEnabled": True})
    monkeypatch.setattr(dispatch, "institution", lambda *a: "institution")
    monkeypatch.setattr(
        dispatch,
        "one",
        lambda *a: {"RecipientId": "recipient", "CampaignId": "campaign"},
    )
    monkeypatch.setattr(dispatch, "current", lambda *a: {"IntegrationId": "account"})
    monkeypatch.setattr(dispatch, "check", Mock(side_effect=HTTPException(409, reason)))
    from app.institutional import channel_outbox

    enqueue = Mock()
    monkeypatch.setattr(channel_outbox, "enqueue", enqueue)
    assert dispatch.Worker(SimpleNamespace()).once() is not waiting
    statements = [args.args[0] for args in c.execute.call_args_list]
    assert any("State='blocked'" in sql for sql in statements) is not waiting
    assert (
        any("UPDATE crm_broadcast7.Cadence SET NextAt=" in sql for sql in statements)
        is waiting
    )
    enqueue.assert_not_called()


def test_contact_detail_distinguishes_current_human_stage_from_send_target():
    value = contact_details(
        {
            "CurrentStage": "Matriculado",
            "CurrentProgram": "Cocina",
            "CurrentCustomValues": json.dumps(
                {"pre_programas": "Barismo", "pre_ultima_fecha": "2026-11-01"}
            ),
            "Snapshot": json.dumps({"sent_stage": "Seguimiento"}),
        }
    )
    assert value["stage"] == "Matriculado" and value["sent_stage"] == "Seguimiento"
    assert value["requested_program"] == "Barismo" and value["program"] == "Cocina"
    assert (
        contact_details({"CurrentCustomValues": "invalid"})["requested_program"] == ""
    )


def test_template_preview_uses_frozen_header_parameters_and_plain_button_labels():
    definition = [
        {"type": "HEADER", "text": "CBN {{1}}"},
        {"type": "FOOTER", "text": "Admisiones"},
        {"type": "BUTTONS", "buttons": [{"text": "Conocer el programa"}]},
    ]
    parts = display_parts(
        definition,
        {
            "template": {
                "components": [
                    {
                        "type": "header",
                        "parameters": [{"type": "text", "text": "Cocina"}],
                    }
                ]
            }
        },
    )
    assert parts == {
        "header": "CBN Cocina",
        "footer": "Admisiones",
        "buttons": ["Conocer el programa"],
    }
    assert display_parts(definition, {})["header"] == ""


def test_new_queries_translate_and_parse_as_postgres(harness):
    parse = pytest.importorskip("pglast").parse_sql
    from app.institutional.postgres_dialect import postgres_sql

    harness.worker.once()
    tree = ast.parse(
        Path(refresh.__file__).with_name("broadcasts.py").read_text(encoding="utf-8")
    )
    service = next(
        n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Broadcasts"
    )
    method = next(
        n for n in service.body if isinstance(n, ast.FunctionDef) and n.name == "report"
    )
    base = next(
        ast.literal_eval(n.value)
        for n in ast.walk(method)
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "base" for t in n.targets)
    )
    for query in [harness.queries[0], base + "SELECT * FROM filtered"]:
        tables = {
            t: "dbo." + t.replace(".", "_")
            for t in re.findall(
                r"(?:FROM|JOIN)\s+(crm(?:_[a-z0-9]+)?\.[A-Za-z0-9]+)", query
            )
        }
        converted = postgres_sql(query, tables)
        parse(converted.replace("%s", "NULL"))
