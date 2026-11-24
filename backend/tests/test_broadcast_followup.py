import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.institutional import broadcast_dispatch, broadcast_followup, broadcasts, db


def harness(monkeypatch, *, stage="Calificación", replay=False, merged=False):
    state = {"stage": stage, "operations": 0, "updates": 0, "audits": 0}
    snapshot = {
        "sent_stage": "Seguimiento", "canonical_contact": str(uuid4()),
        "audience_profile": {"stage": "Calificación"},
    }
    recipient = {
        "RecipientId": str(uuid4()), "CampaignId": str(uuid4()),
        "Snapshot": json.dumps(snapshot),
    }

    class Cursor:
        rowcount = 0
        result = None

        def execute(self, sql, *parameters):
            self.result = None
            if sql.startswith("SELECT 1 FROM crm_access.Operation"):
                self.result = (1,) if replay or state["operations"] else None
            elif sql.startswith("SELECT 1 FROM crm_workspace.Merge"):
                self.result = (1,) if merged else None
            elif sql.startswith("UPDATE crm.Contact"):
                self.rowcount = int(state["stage"] == parameters[2])
                if self.rowcount:
                    state["stage"] = parameters[0]
                    state["updates"] += 1
            elif sql.startswith("INSERT crm_access.Audit"):
                state["audits"] += 1
            return self

        def fetchone(self):
            return self.result

    monkeypatch.setattr(db, "institution", lambda _: "institution")
    monkeypatch.setattr(db, "bound_hash", lambda *args: b"hash")
    monkeypatch.setattr(db, "record_operation", lambda *args:
                        state.update(operations=state["operations"] + 1))
    monkeypatch.setattr(broadcast_dispatch, "record", lambda *args: recipient)
    monkeypatch.setattr(broadcasts, "current", lambda *args: {})
    monkeypatch.setattr(broadcasts, "authority", lambda *args: {
        "UserId": "actor", "Actions": '["crm.write"]',
    })
    monkeypatch.setattr(broadcast_followup, "read_configuration", lambda *args, **kw: (
        SimpleNamespace(stages=[SimpleNamespace(active=True, label="Seguimiento")]), 1,
    ))
    return Cursor(), state, SimpleNamespace(postgres_deployment=False)


@pytest.mark.parametrize(
    "status", ["prepared", "queued", "accepted", "failed", "uncertain"],
)
def test_stage_does_not_change_before_real_sent_receipt(monkeypatch, status):
    c, state, settings = harness(monkeypatch)
    assert not broadcast_followup.observe(c, settings, "queue", status)
    assert state["stage"] == "Calificación" and state["operations"] == 0


@pytest.mark.parametrize("status", ["sent", "delivered", "read"])
def test_real_receipts_update_once_and_write_the_shared_audit(monkeypatch, status):
    c, state, settings = harness(monkeypatch)
    assert broadcast_followup.observe(c, settings, "queue", status)
    assert state["stage"] == "Seguimiento" and state["audits"] == 1
    assert not broadcast_followup.observe(c, settings, "queue", "read")
    assert state["updates"] == 1


@pytest.mark.parametrize(
    "stage", ["Matriculado", "Inscripción", "Cerrado sin matrícula"],
)
def test_later_human_stage_is_preserved(monkeypatch, stage):
    c, state, settings = harness(monkeypatch, stage=stage)
    assert not broadcast_followup.observe(c, settings, "queue", "sent")
    assert state["stage"] == stage and state["updates"] == 0


def test_merged_contact_is_left_for_review(monkeypatch):
    c, state, settings = harness(monkeypatch, merged=True)
    assert not broadcast_followup.observe(c, settings, "queue", "sent")
    assert state["updates"] == 0


@pytest.mark.parametrize("revoked", [True, False])
def test_expired_authority_or_missing_crm_permission_keeps_receipt(
    monkeypatch, revoked,
):
    c, state, settings = harness(monkeypatch)

    def authority(*args):
        if revoked:
            raise HTTPException(409, "broadcast_authority_changed")
        return {"UserId": "actor", "Actions": "[]"}

    monkeypatch.setattr(broadcasts, "authority", authority)
    assert not broadcast_followup.observe(c, settings, "queue", "delivered")
    assert state["updates"] == 0 and state["operations"] == 0
