import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pglast import parse_sql

from app.institutional import context_recovery as recovery, whatsapp_gemini
from app.institutional.operations_policy import layout
from app.institutional.postgres_dialect import postgres_sql


def fixture(monkeypatch, *, job_state="queued", attempts=0, external=None, replans=0, source_error=None):
    inst, integration, operation, conversation, identity, incoming, part, queue, send = [str(uuid4()) for _ in range(9)]
    settings = SimpleNamespace(ticket={"context": [[1, inst]]})
    data = dict(conversation=conversation, identity=identity, incoming=incoming, epoch=7,
                response_parts=[{"id": part}], context_replans=replans,
                contextBinding="old-context", modelBinding="old-model", generated_text="obsolete reply")
    old = {"ResultMetadata": json.dumps(data)}
    jobs = [dict(QueueId=queue, OperationId=send, MessageId=part, State=job_state, Attempts=attempts, ExternalId=external)]
    statements, scheduled = [], []
    fresh = {}

    def validate(sql, params):
        assert sql.count("?") == len(params)
        parse_sql(postgres_sql(sql, layout()["tables"]).replace("%s", "NULL"))

    class Cursor:
        rowcount = 1

        def execute(self, sql, *params):
            validate(sql, params)
            statements.append((sql, params))
            if "ResultMetadata=?" in sql and params[-1] == operation:
                old["ResultMetadata"] = params[0]
            return self

    def one(_c, sql, *params):
        validate(sql, params)
        assert params[:2] == (inst, integration)
        return old if params[2] == operation else {"ResultMetadata": json.dumps(fresh)} if fresh else None

    def rows(_c, sql, *params):
        validate(sql, params)
        assert params == (inst, integration, identity, conversation, 7, operation)
        assert "r.ActorKind='bot'" in sql and "r.ControlEpoch=?" in sql
        return jobs

    def source(*_):
        if source_error:
            raise HTTPException(409, source_error)
        return {"IntegrationId": integration, "Channel": "whatsapp"}, {}, {}

    def schedule(_c, _s, _item, linked, message, *, operation_id):
        assert linked == {"ConversationId": conversation, "IdentityId": identity}
        assert message == incoming
        scheduled.append(operation_id)
        fresh.update({k: data[k] for k in ("conversation", "identity", "incoming", "epoch")})
        fresh["integration"] = integration

    monkeypatch.setattr(recovery.db, "one", one)
    monkeypatch.setattr(recovery.db, "rows", rows)
    monkeypatch.setattr(whatsapp_gemini, "source", source)
    monkeypatch.setattr(whatsapp_gemini, "schedule", schedule)
    return SimpleNamespace(settings=settings, integration=integration, operation=operation,
                           cursor=Cursor(), statements=statements, scheduled=scheduled, old=old, jobs=jobs)


def test_changed_prompt_replans_once_with_same_input_and_fresh_quiet_window(monkeypatch):
    state = fixture(monkeypatch)
    assert recovery.replan(state.cursor, state.settings, state.operation, state.integration, "gemini_reply_context_changed")
    assert len(state.scheduled) == 1
    metadata = [json.loads(args[0]) for sql, args in state.statements
                if "ResultMetadata=?" in sql and args[-1] == state.scheduled[0]][0]
    assert metadata["context_replans"] == 1 and metadata["recovery_from"] == state.operation
    assert metadata["cancelled_generations"][0]["reply_ids"] == [state.jobs[0]["MessageId"]]
    assert not {"generated_text", "contextBinding", "modelBinding"} & set(metadata)
    assert all("UPDATE crm.Message" not in sql for sql, _ in state.statements)
    assert not recovery.replan(state.cursor, state.settings, state.operation, state.integration, "gemini_reply_context_changed")
    assert len(state.scheduled) == 1  # Idempotent even when dispatcher revisits.


@pytest.mark.parametrize("job_state,attempts,external", [
    ("accepted", 1, "provider-id"), ("read", 1, "provider-id"), ("sending", 1, None),
    ("uncertain", 1, None), ("failed", 1, None), ("cancelled", 1, None),
    ("queued", 0, "provider-id"),
])
def test_attempted_or_possibly_delivered_answer_is_never_replayed(monkeypatch, job_state, attempts, external):
    state = fixture(monkeypatch, job_state=job_state, attempts=attempts, external=external)
    assert not recovery.replan(state.cursor, state.settings, state.operation, state.integration, "gemini_reply_context_changed")
    assert not state.statements and not state.scheduled


@pytest.mark.parametrize("error", ["gemini_whatsapp_control_or_history_changed", "contact_opted_out", "account_paused_or_unverified"])
def test_humano_new_input_or_revoked_authority_stops_recovery(monkeypatch, error):
    state = fixture(monkeypatch, source_error=error)
    assert not recovery.replan(state.cursor, state.settings, state.operation, state.integration, "gemini_reply_context_changed")
    assert not state.statements and not state.scheduled


def test_completed_generation_without_channel_jobs_can_rebuild_before_first_send(monkeypatch):
    state = fixture(monkeypatch)
    state.jobs.clear()
    data = json.loads(state.old["ResultMetadata"])
    data.pop("response_parts")
    state.old["ResultMetadata"] = json.dumps(data)
    assert recovery.replan(state.cursor, state.settings, state.operation, state.integration, "gemini_reply_context_changed")
    assert len(state.scheduled) == 1


def test_continuously_changing_prompt_does_not_create_unbounded_paid_work(monkeypatch):
    state = fixture(monkeypatch, replans=recovery.MAX_REPLANS)
    assert not recovery.replan(state.cursor, state.settings, state.operation, state.integration, "gemini_reply_context_changed")
    assert not state.scheduled


@pytest.mark.parametrize("reason", ["send_lease_expired", "gemini_whatsapp_intent_mismatch", "reply_turn_delivery_uncertain"])
def test_security_or_uncertain_results_do_not_trigger_context_recovery(monkeypatch, reason):
    state = fixture(monkeypatch)
    assert not recovery.replan(state.cursor, state.settings, state.operation, state.integration, reason)
    assert not state.scheduled and not state.statements


@pytest.mark.parametrize("reason", sorted(recovery.REASONS))
def test_approved_model_or_prompt_change_rebuilds_under_current_ai_authority(monkeypatch, reason):
    state = fixture(monkeypatch)
    assert recovery.replan(state.cursor, state.settings, state.operation, state.integration, reason)
    assert len(state.scheduled) == 1


def test_partial_reply_keeps_accepted_content_as_history_and_cancels_only_unsent_tail(monkeypatch):
    state = fixture(monkeypatch)
    accepted_id = str(uuid4())
    state.jobs.append(dict(QueueId=str(uuid4()), OperationId=str(uuid4()), MessageId=accepted_id,
                           State="delivered", Attempts=1, ExternalId="provider-receipt"))
    old = json.loads(state.old["ResultMetadata"])
    old["response_parts"].append({"id": accepted_id})
    state.old["ResultMetadata"] = json.dumps(old)
    assert recovery.replan(state.cursor, state.settings, state.operation, state.integration, "gemini_reply_context_changed")
    metadata = [json.loads(args[0]) for sql, args in state.statements
                if "ResultMetadata=?" in sql and args[-1] == state.scheduled[0]][0]
    assert metadata["accepted_continuation_ids"] == [accepted_id]
    cancellations = [args for sql, args in state.statements if "UPDATE crm_channels2.SendJob" in sql]
    assert len(cancellations) == 1 and cancellations[0][-1] == state.jobs[0]["QueueId"]
