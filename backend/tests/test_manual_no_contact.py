from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException
from pglast import parse_sql
from pydantic import ValidationError
import pytest

from app.institutional import contact_preference as target, workspace, campaigns, broadcasts
from app.institutional.operations_policy import layout
from app.institutional.postgres_dialect import postgres_sql


@pytest.mark.parametrize("change", [{"confirmed": 1}, {"confirmed": False}, {"reason": "   "},
                                     {"reason": "abc\x00"}, {"operationId": "-" * 36}])
def test_no_contact_requires_explicit_confirmation_and_valid_intent(change):
    with pytest.raises(ValidationError):
        target.NoContactWrite(**{**dict(operationId=str(uuid4()), reason="Solicitud declarada al asesor", confirmed=True), **change})


def setup(monkeypatch, *, replay=None, identities=True):
    contact, actor = str(uuid4()), str(uuid4())
    ids = [contact, str(uuid4())]
    identity_rows = [{"IdentityId": str(uuid4()), "IntegrationId": str(uuid4())} for _ in range(2)] if identities else []
    calls, events, records = [], [], []
    class Cursor:
        def execute(self, sql, *args):
            assert sql.count("?") == len(args)
            parse_sql(postgres_sql(sql, layout()["tables"]).replace("%s", "NULL"))
            calls.append((sql, args))
            return self
    monkeypatch.setattr(workspace, "primary", lambda *a: contact)
    monkeypatch.setattr(workspace, "members", lambda *a: ids)
    monkeypatch.setattr(workspace, "read_contact", lambda *a: {"id": contact})
    def rows(c, sql, *args):
        c.execute(sql, *args)
        if "FROM crm_campaign8.Enrollment" in sql:
            return []
        assert "InstitutionId=? AND ContactId IN" in sql and args[-2:] == tuple(ids)
        return identity_rows
    monkeypatch.setattr(target.db, "rows", rows)
    monkeypatch.setattr(target.db, "replay", lambda *a: (b"digest", replay))
    monkeypatch.setattr(target.db, "record_operation", lambda *a: records.append(a))
    monkeypatch.setattr(target.db, "audit", lambda *a, **kw: records.append(kw))
    monkeypatch.setattr(campaigns, "event", lambda *a, **kw: events.append((a, kw)))
    monkeypatch.setattr(broadcasts, "consent", lambda *a: {"State": "granted", "VersionNo": 3})
    settings = SimpleNamespace(ticket={"context": [[1, str(uuid4())]]})
    body = target.NoContactWrite(operationId=str(uuid4()), reason="La persona pidió no recibir mensajes; confirmado por el asesor.", confirmed=True)
    return Cursor(), settings, contact, actor, body, calls, events, records


def test_manual_optout_all_aliases_revokes_and_closes_without_sending_or_touching_uncertain(monkeypatch):
    c, settings, contact, actor, body, calls, events, records = setup(monkeypatch)
    result = target.record_no_contact(c, settings, contact, body, actor)
    assert result == {"no_contact": True, "closed": True, "identity_count": 2}
    assert len(events) == 2 and all(e[0][2] == "opt_out" for e in events)
    assert all(e[0][3]["source"] == "operator_confirmed_request" and "message_id" not in e[0][3] for e in events)
    assert all(e[1]["actor"] == actor for e in events)
    revokes = [sql for sql, _ in calls if sql.startswith("INSERT crm_broadcast7.Consent")]
    assert len(revokes) == 2 and all("'revoked'" in sql for sql in revokes)
    queue_updates = [sql for sql, _ in calls if "UPDATE crm_channels2.SendJob SET" in sql]
    assert len(queue_updates) == 4 and all("State='queued'" in sql for sql in queue_updates)
    assert any("SET State='closed'" in sql for sql, _ in calls)
    assert any(isinstance(record, dict) and record.get("reason") == "operator_confirmed_request" for record in records)


def test_manual_optout_same_command_replay_never_repeats_changes(monkeypatch):
    prior = {"no_contact": True, "closed": True, "identity_count": 2}
    c, settings, contact, actor, body, calls, events, records = setup(monkeypatch, replay=prior)
    assert target.record_no_contact(c, settings, contact, body, actor) == prior
    assert not calls and not events and not records


def test_contact_without_channel_fails_before_changes_instead_of_claiming_optout(monkeypatch):
    c, settings, contact, actor, body, calls, events, records = setup(monkeypatch, identities=False)
    with pytest.raises(HTTPException, match="contact_identity_not_found"):
        target.record_no_contact(c, settings, contact, body, actor)
    assert not events and not records and all(sql.startswith("SELECT") for sql, _ in calls)
