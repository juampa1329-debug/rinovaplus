import json
from copy import deepcopy
from datetime import datetime, timedelta
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.institutional import campaign_closure as f, campaign_runtime as runtime
from app.institutional.campaign_models import Flow, Trigger, Review
from app.institutional import campaigns


@pytest.fixture
def setup(monkeypatch):
    flow_id, trigger_id, account, template = [str(uuid4()) for _ in range(4)]
    doc = Flow(integration_id=account, followup_only=True, quiet_hours={"enabled": True},
               steps=[{"kind": kind, "name": "Paso revisado", "wait_minutes": wait,
                       **({"meta_template_id": template} if kind == "send" else {})}
                      for kind, wait in [("send", 0), ("wait", 1680), ("send", 0),
                                         ("wait", 1440), ("send", 0), ("wait", 26640), ("send", 0)]])
    flow = dict(RecordId=flow_id, Kind="flow", State="active", CurrentVersion=3,
                Epoch=4, Revision=6, Document=doc.model_dump_json())
    trigger = dict(RecordId=trigger_id, Kind="trigger", Name="Inactividad", State="active",
                   CurrentVersion=3, Revision=7, Epoch=5,
                   Document=Trigger(flow_id=flow_id, flow_version=3, event_type="inactivity",
                                    idle_minutes=480).model_dump_json())
    moment = datetime(2026, 11, 27, 16)
    actor = dict(UserId="actor", SessionId="session", AuthVersion=1)
    body = Review(closure_days=7, preflight_id=uuid4(), operation_id=uuid4(),
                  reason="Cierre autorizado", revision=6, confirmed=True)
    run = dict(EnrollmentId=str(uuid4()), TriggerId=trigger_id, FlowId=flow_id,
               VersionNo=3, FlowEpoch=4, TriggerVersion=3, StepIndex=1,
               State="waiting", DueAt=moment + timedelta(days=1), Context="unchanged")
    steps = [dict(StepIndex=0, State="completed", Kind="send", StepId="prior"),
             dict(StepIndex=1, State="waiting", Kind="wait", StepId="wait", DueAt=run["DueAt"])]
    c = Mock(rowcount=1)
    monkeypatch.setattr(f, "institution", lambda s: "institution")
    monkeypatch.setattr(f, "now", lambda: moment)
    monkeypatch.setattr(f, "rows", lambda c, sql, *a: [trigger] if "Record" in sql else [run] if "Enrollment " in sql else steps)
    monkeypatch.setattr(f, "one", lambda *a: dict(CreatedAt=moment, Document=json.dumps(dict(
        actor="actor", session="session", auth_version=1, record_revision=6,
        record_hash=f.key(flow["Document"]), issues=[]))))
    monkeypatch.setattr(f, "authority", Mock())
    monkeypatch.setattr(f, "issues", lambda *a, **kw: [])
    monkeypatch.setattr(f, "get", lambda *a: flow)
    monkeypatch.setattr(f, "public", lambda r: dict(id=r["RecordId"]))
    monkeypatch.setattr(f, "event", Mock())
    monkeypatch.setattr(runtime, "guard", Mock())
    monkeypatch.setattr(runtime, "stop", Mock())
    return c, flow, trigger, body, actor, run, steps, moment


def test_seven_days_counts_from_original_anchor_and_preserves_template(setup):
    _, flow, trigger, _, _, _, _, _ = setup
    original = deepcopy(flow)
    doc, delta = f.target(flow, trigger, 7)
    assert doc["steps"][5]["wait_minutes"] == 6480
    assert delta == -20160
    old = json.loads(flow["Document"])
    assert doc["steps"][:5] == old["steps"][:5]
    assert {k: v for k, v in doc["steps"][6].items() if k != "name"} == {
        k: v for k, v in old["steps"][6].items() if k != "name"}
    assert flow == original


def test_migration_preserves_current_wait_and_never_writes_receipts_or_jobs(setup):
    c, flow, _, body, actor, run, _, _ = setup
    result = f.shorten(c, None, flow, actor, body)
    assert result["reschedule"] == dict(closure_days=7, preserved=1, stopped=0, trigger_version=4)
    statements = [v.args for v in c.execute.call_args_list]
    assert len([v for v in statements if v[0].startswith("INSERT crm_campaign8.Version")]) == 2
    operations = [v[-1] for v in statements if v[0].startswith("INSERT crm_campaign8.Version")]
    assert len(set(operations)) == 2  # Version has UNIQUE(InstitutionId, OperationId).
    update = next(v for v in statements if v[0].startswith("UPDATE crm_campaign8.Enrollment"))
    assert update[1:5] == (4, 5, 4, run["DueAt"])
    assert "StepIndex=?" in update[0] and "StepIndex=" not in update[0].split("WHERE")[0]
    assert not any("SendJob" in v[0] or "ProviderOperation" in v[0] or "Context=" in v[0] for v in statements)
    runtime.stop.assert_not_called()


@pytest.mark.parametrize("state,index", [("queued", 1), ("uncertain", 1), ("paused", 1), ("waiting", 6)])
def test_in_flight_or_ambiguous_work_aborts_before_any_mutation(setup, state, index):
    c, flow, _, body, actor, run, _, _ = setup
    run.update(State=state, StepIndex=index)
    with pytest.raises(HTTPException, match="campaign_closure_busy"):
        f.shorten(c, None, flow, actor, body)
    c.execute.assert_not_called()


@pytest.mark.parametrize("reason", ["no_contact", "campaign_response_received", "marketing_consent_required"])
def test_current_guards_stop_ineligible_instead_of_reenabling(setup, reason):
    c, flow, _, body, actor, run, _, _ = setup
    runtime.guard.side_effect = HTTPException(409, reason)
    assert f.shorten(c, None, flow, actor, body)["reschedule"]["stopped"] == 1
    runtime.stop.assert_called_once_with(c, None, run, reason)
    assert not any(v.args[0].startswith("UPDATE crm_campaign8.Enrollment") for v in c.execute.call_args_list)


def test_retiming_only_materialized_final_wait(setup):
    _, flow, _, _, _, run, _, moment = setup
    quiet = json.loads(flow["Document"])["quiet_hours"]
    run.update(StepIndex=5, DueAt=moment + timedelta(days=21))
    assert f.waiting_due(run, None, -20160, quiet, moment) == run["DueAt"]
    step = dict(DueAt=run["DueAt"])
    assert f.waiting_due(run, step, -20160, quiet, moment) == moment + timedelta(days=7)
    step["DueAt"] = moment + timedelta(days=1)
    assert f.waiting_due(run, step, -20160, quiet, moment) == moment


def test_cas_failure_does_not_continue_to_run_updates(setup):
    c, flow, _, body, actor, _, _, _ = setup
    c.rowcount = 0
    with pytest.raises(HTTPException, match="revision_conflict"):
        f.shorten(c, None, flow, actor, body)
    assert len(c.execute.call_args_list) == 1


def test_case_specific_flow_is_not_general_closure(setup):
    c, flow, _, body, actor, _, _, _ = setup
    doc = json.loads(flow["Document"])
    doc["entry_conditions"]["followup_states"] = ["form_sent"]
    flow["Document"] = json.dumps(doc)
    with pytest.raises(HTTPException):
        f.shorten(c, None, flow, actor, body)
    c.execute.assert_not_called()


def test_native_sql_is_portable_to_deployed_postgres(setup, monkeypatch):
    from app.institutional.campaign_policy import layout
    from app.institutional.postgres_dialect import postgres_sql
    from pglast import parse_sql
    c, flow, _, body, actor, _, _, _ = setup
    queries = []
    for name in ("rows", "one"):
        original = getattr(f, name)
        def capture(c, sql, *args, fn=original):
            queries.append(sql)
            return fn(c, sql, *args)
        monkeypatch.setattr(f, name, capture)
    f.shorten(c, None, flow, actor, body)
    queries += [v.args[0] for v in c.execute.call_args_list]
    assert len(queries) >= 9
    for sql in queries:
        parse_sql(postgres_sql(sql, layout()["tables"]).replace("%s", "NULL"))


def test_action_requires_recent_authority_and_replay_returns_before_migration(setup, monkeypatch):
    from contextlib import contextmanager
    c, flow, _, body, actor, _, _, _ = setup
    calls = []
    @contextmanager
    def tx(auth, write=False, recent=False):
        calls.append((write, recent))
        yield c, actor
    service = campaigns.Campaigns(None)
    monkeypatch.setattr(service, "tx", tx)
    monkeypatch.setattr(campaigns, "replay", lambda *a: ("digest", {"reschedule": {"preserved": 6}}))
    shorten = Mock(side_effect=AssertionError("must not repeat"))
    monkeypatch.setattr(f, "shorten", shorten)
    assert service.action(None, flow["RecordId"], "shorten_closure", body)["reschedule"]["preserved"] == 6
    assert calls == [(True, True)]
    shorten.assert_not_called()
