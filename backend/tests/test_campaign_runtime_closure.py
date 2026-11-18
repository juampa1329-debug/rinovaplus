"""P8 exit and recovery boundaries with controlled SQL; no provider calls."""
import json
from datetime import datetime, timedelta
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.institutional import campaign_runtime as runtime
from app.institutional.campaign_models import Flow
from app.institutional.campaigns import snapshot


@pytest.fixture
def context(monkeypatch):
    moment = datetime(2026, 11, 18, 14)
    person = dict(CanonicalContactId=str(uuid4()), Stage="Nuevo", ProgramId=None,
                  IncomingCount=1, ControlEpoch=0)
    flow = Flow(integration_id=uuid4(), steps=[{"kind": "wait", "wait_minutes": 10}])
    record = dict(RecordId=str(uuid4()), State="active", CurrentVersion=1, Epoch=1,
                  Document=flow.model_dump_json(), ActorId=str(uuid4()))
    run = dict(EnrollmentId=str(uuid4()), FlowId=record["RecordId"], VersionNo=1,
               FlowEpoch=1, State="waiting", TriggerId=None, IdentityId=str(uuid4()),
               Context=json.dumps(snapshot(person)), DueAt=moment+timedelta(minutes=10), StepIndex=0)
    monkeypatch.setattr(runtime, "now", lambda: moment)
    monkeypatch.setattr(runtime, "get", lambda *args: record)
    monkeypatch.setattr(runtime, "person", lambda *args: person)
    monkeypatch.setattr(runtime, "reasons", lambda *args: [])
    monkeypatch.setattr(runtime, "authority", Mock())
    monkeypatch.setattr(runtime, "institution", lambda _: "institution")
    monkeypatch.setattr(runtime.providers, "request", Mock(side_effect=AssertionError("no provider IO")))
    cursor = Mock()
    return cursor, record, run, person


@pytest.mark.parametrize("field,value,reason", [
    ("Stage", "Contactado", "campaign_stage_changed"),
    ("ProgramId", 12, "campaign_program_changed"),
    ("ControlEpoch", 1, "campaign_handoff_changed"),
    ("IncomingCount", 2, "campaign_response_received"),
    ("CanonicalContactId", str(uuid4()), "campaign_identity_changed"),
])
def test_exit_invalidates_even_a_future_wait(context, field, value, reason):
    c, _, run, person = context
    person[field] = value
    with pytest.raises(HTTPException) as e:
        runtime.guard(c, None, run)
    assert e.value.detail == reason
    c.execute.assert_not_called()
    runtime.providers.request.assert_not_called()


@pytest.mark.parametrize("change", [{"State": "paused"}, {"CurrentVersion": 2}, {"Epoch": 2}])
def test_paused_or_replaced_version_is_not_executed(context, change):
    c, record, run, _ = context
    record.update(change)
    with pytest.raises(HTTPException) as e:
        runtime.guard(c, None, run, for_send=True)
    assert e.value.detail == "campaign_version_or_pause_changed"
    runtime.providers.request.assert_not_called()


def test_revoked_consent_stops_before_any_send(context, monkeypatch):
    c, _, run, _ = context
    monkeypatch.setattr(runtime, "reasons", lambda *args: ["marketing_consent_required"])
    with pytest.raises(HTTPException) as e:
        runtime.guard(c, None, run, for_send=True)
    assert e.value.detail == "marketing_consent_required"
    runtime.providers.request.assert_not_called()


def test_future_due_date_is_not_shortened_by_reviewed_resume(context, monkeypatch):
    c, record, run, _ = context
    run["State"] = "paused"
    deadline = run["DueAt"]
    monkeypatch.setattr(runtime, "one", Mock(side_effect=[run, None]))
    monkeypatch.setattr(runtime, "event", Mock())
    runtime.resume_run(c, None, record, run["EnrollmentId"])
    assert c.execute.call_args_list[0].args[2] == deadline
    runtime.providers.request.assert_not_called()


@pytest.mark.parametrize("state", ["uncertain", "queued", "completed"])
def test_unknown_or_started_work_cannot_be_resumed_as_paused(context, monkeypatch, state):
    c, record, run, _ = context
    run["State"] = state
    monkeypatch.setattr(runtime, "one", lambda *args: run)
    with pytest.raises(HTTPException) as e:
        runtime.resume_run(c, None, record, run["EnrollmentId"])
    assert e.value.detail == "campaign_execution_requires_review"
    c.execute.assert_not_called()
    runtime.providers.request.assert_not_called()


def test_accepted_send_is_observed_after_resume_without_repreparing(context, monkeypatch):
    from app.institutional import campaign_chat
    c, record, run, _ = context
    run["State"] = "paused"
    step = dict(Kind="send", NativeCampaignId=None, StepId=str(uuid4()))
    monkeypatch.setattr(runtime, "one", Mock(side_effect=[run, step]))
    monkeypatch.setattr(campaign_chat, "links", lambda *args: [{"State": "accepted"}])
    prepare = Mock(side_effect=AssertionError("must not duplicate accepted send"))
    monkeypatch.setattr(runtime, "prepare_native", prepare)
    monkeypatch.setattr(runtime, "event", Mock())
    assert runtime.resume_run(c, None, record, run["EnrollmentId"])["resumed"]
    prepare.assert_not_called()
    runtime.providers.request.assert_not_called()
