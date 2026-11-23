import json
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.institutional import broadcast_prospects as setup
from app.institutional import broadcasts, db


def command(**changes):
    return setup.ProspectSetup(**{
        "operation_id": str(uuid4()), "reason": "Seguimiento autorizado",
        "confirmed": True, "evidence": "El titular confirma la autorización",
        "origin": "Políticas de preinscripción, según el titular",
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
        "program": "logistica", "contact_ids": [str(uuid4())], **changes,
    })


def person(**changes):
    return {
        "ContactId": str(uuid4()), "Type": "Preinscrito", "Phone": "+573001234567",
        "CustomValues": json.dumps({
            "pre_import_ref": "PRE-1234567890abcdef",
            "pre_programas": "LOGISTICA PORTUARIA Y MARITIMA",
        }), **changes,
    }


@pytest.mark.parametrize("changes", [
    {"confirmed": False}, {"evidence": ""}, {"program": "cocina"},
    {"expires_at": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()},
    {"contact_ids": ["invalid"]},
])
def test_setup_requires_explicit_bounded_evidence_and_valid_contacts(changes):
    with pytest.raises(ValidationError):
        command(**changes)


@pytest.mark.parametrize("changes", [
    {"Phone": ""}, {"Phone": "+123"}, {"Type": "Estudiante activo"},
    {"CustomValues": "{}"},
    {"CustomValues": json.dumps({
        "pre_import_ref": "PRE-1234567890abcdef", "pre_programas": "COCINA",
    })},
])
def test_reviewed_contact_rejects_unrelated_or_unusable_sources(changes):
    with pytest.raises(HTTPException):
        setup.reviewed_contact(person(**changes), "logistica")


def test_aduanas_accepts_the_actual_source_label():
    value = person(CustomValues=json.dumps({
        "pre_import_ref": "PRE-1234567890abcdef",
        "pre_programas": "ADUANAS, PROCESOS LOGISTICOS Y AUTOMATIZACIÓN",
    }))
    assert setup.reviewed_contact(value, "aduanas") == "573001234567"


def test_all_programs_still_requires_source_program_and_valid_phone():
    value = person(CustomValues=json.dumps({
        "pre_import_ref": "PRE-1234567890abcdef", "pre_programas": "ENFERMERIA",
    }))
    assert setup.reviewed_contact(value, "all") == "573001234567"
    value["CustomValues"] = json.dumps({
        "pre_import_ref": "PRE-1234567890abcdef", "pre_programas": "",
    })
    with pytest.raises(HTTPException):
        setup.reviewed_contact(value, "all")


class Cursor:
    def __init__(self, *, existing_channel=False, human_history=False):
        self.writes = []
        self.existing_channel = existing_channel
        self.human_history = human_history
        self.result = None

    def execute(self, sql, *params):
        self.writes.append((sql, params))
        if sql.startswith("SELECT 1 FROM crm_channels2.ExternalIdentity"):
            self.result = (1,) if self.existing_channel else None
        elif sql.startswith("SELECT 1 FROM crm.Conversation"):
            self.result = (1,) if self.human_history else None
        return self

    def fetchone(self):
        return self.result


def link_harness(monkeypatch, *, linked=None, placeholder=None, **cursor_options):
    value = person()
    c = Cursor(**cursor_options)
    monkeypatch.setattr(db, "institution", lambda _: "institution")
    monkeypatch.setattr(db, "one", lambda _, sql, *args:
                        value if "FROM crm.Contact" in sql else
                        placeholder if "FROM crm.Conversation" in sql else linked)
    monkeypatch.setattr(setup, "control", lambda *_: None)
    return c, value


@pytest.mark.parametrize("flag", ["existing_channel", "human_history"])
def test_onboarding_cannot_bypass_existing_channels_or_human_history(monkeypatch, flag):
    c, value = link_harness(monkeypatch, **{flag: True})
    with pytest.raises(HTTPException):
        setup.link(c, None, "account", value["ContactId"], "logistica")
    assert not any(sql.startswith("INSERT") for sql, _ in c.writes)


def test_new_outbound_route_preserves_old_chat_and_has_no_incoming_message(monkeypatch):
    c, value = link_harness(monkeypatch)
    setup.link(c, None, "account", value["ContactId"], "logistica")
    inserts = [sql for sql, _ in c.writes if sql.startswith("INSERT")]
    assert len(inserts) == 2
    assert not any("LastIncomingAt" in sql for sql in inserts)
    assert not any("crm.Message" in sql for sql in inserts)
    assert not any(sql.startswith("UPDATE") for sql, _ in c.writes)


def test_empty_import_placeholder_is_reused_with_native_control_epoch(monkeypatch):
    placeholder = {"ConversationId": str(uuid4()), "ControlMode": "human"}
    c, value = link_harness(monkeypatch, placeholder=placeholder)
    changes = []
    monkeypatch.setattr(setup, "change_control", lambda *args: changes.append(args))
    setup.link(c, None, "account", value["ContactId"], "logistica")
    assert not any(sql.startswith("INSERT crm.Conversation") for sql, _ in c.writes)
    assert changes == [(c, placeholder["ConversationId"], "human", "ai")]
    assert any(sql.startswith("UPDATE crm.Conversation") for sql, _ in c.writes)


def test_shared_phone_identity_conflict_never_merges_or_reassigns(monkeypatch):
    c, value = link_harness(monkeypatch, linked={"ContactId": str(uuid4())})
    with pytest.raises(HTTPException, match="prospect_phone_identity_conflict"):
        setup.link(c, None, "account", value["ContactId"], "logistica")
    assert not c.writes


def setup_harness(monkeypatch, *, previous=None, prior=None):
    c = Cursor()
    identity = str(uuid4())
    calls = []

    @contextmanager
    def tx(auth, write=False, recent=False):
        assert write and recent
        yield c, {"UserId": "actor"}

    service = SimpleNamespace(
        settings=SimpleNamespace(postgres_deployment=False), tx=tx,
        save_consent=lambda *args: calls.append(args[-1]),
    )
    monkeypatch.setattr(setup, "authorize", lambda *args: None)
    monkeypatch.setattr(db, "institution", lambda _: "institution")
    monkeypatch.setattr(db, "replay", lambda *args: (b"hash", prior))
    monkeypatch.setattr(db, "record_operation", lambda *args: None)
    monkeypatch.setattr(setup, "account", lambda *args: {
        "Channel": "whatsapp", "RequestedStatus": "connected",
        "VerifiedStatus": "verified",
    })
    monkeypatch.setattr(setup, "link", lambda *args: identity)
    monkeypatch.setattr(broadcasts, "consent", lambda *args: previous)
    return service, calls, c


def test_revoked_permission_is_not_recreated_by_batch_onboarding(monkeypatch):
    service, calls, _ = setup_harness(monkeypatch, previous={"State": "revoked"})
    with pytest.raises(HTTPException, match="prospect_revoked_consent_review_required"):
        setup.setup(service, {}, "account", command())
    assert calls == []


def test_native_consent_replay_uses_same_operation_and_real_audit_contract(monkeypatch):
    service, calls, c = setup_harness(monkeypatch)
    body = command()
    first = setup.setup(service, {}, "account", body)
    assert first["messages_sent"] == 0 and first["consent_saved"]
    assert any(sql.startswith("INSERT crm_access.Audit") for sql, _ in c.writes)
    monkeypatch.setattr(db, "replay", lambda *args: (b"hash", first))
    monkeypatch.setattr(
        setup, "link", lambda *args: pytest.fail("replay must not relink"),
    )
    setup.setup(service, {}, "account", body)
    assert len(calls) == 2
    assert calls[0].operation_id == calls[1].operation_id
    assert calls[0].evidence == body.evidence and calls[0].confirmed


def test_all_programs_keeps_revocations_for_review_and_continues(monkeypatch):
    service, calls, _ = setup_harness(monkeypatch, previous={"State": "revoked"})
    result = setup.setup(service, {}, "account", command(program="all"))
    assert result["items"] == [] and len(result["held"]) == 1
    assert result["held"][0]["reason"] == "prospect_revoked_consent_review_required"
    assert calls == [] and result["messages_sent"] == 0


def test_valid_existing_consent_is_preserved_without_repeated_registration(monkeypatch):
    service, calls, _ = setup_harness(monkeypatch, previous={
        "State": "granted", "VersionNo": 3,
        "ExpiresAt": (
            datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1)
        ),
    })
    result = setup.setup(service, {}, "account", command(program="all"))
    assert result["items"][0]["preserve_consent"] and calls == []
