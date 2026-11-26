from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.institutional import broadcast_consent_correction as correction
from app.institutional import broadcast_prospects, broadcasts
from app.institutional.broadcast_models import ConsentWrite


@pytest.fixture
def fixture(monkeypatch):
    actor = {"UserId": str(uuid4()), "RoleKey": "owner"}
    previous = {
        "State": "revoked",
        "VersionNo": 1,
        "ActorId": actor["UserId"],
        "Origin": "manual",
    }
    calls, recorded = [], []

    class Cursor:
        found = True

        def execute(self, sql, *params):
            calls.append((sql, params))
            return self

        def fetchone(self):
            return (1,) if self.found else None

    cursor = Cursor()

    @contextmanager
    def tx(auth, write, recent):
        assert write and recent
        yield cursor, actor

    service = SimpleNamespace(tx=tx, settings=None)
    monkeypatch.setattr(correction, "authorize", lambda *args: None)
    monkeypatch.setattr(correction.db, "institution", lambda _: "institution")
    monkeypatch.setattr(correction.db, "replay", lambda *args: (b"digest", None))
    monkeypatch.setattr(
        correction.db, "record_operation", lambda *args: recorded.append(args)
    )
    monkeypatch.setattr(correction.db, "audit", lambda *args, **kwargs: None)
    monkeypatch.setattr(broadcasts, "consent", lambda *args: previous)
    monkeypatch.setattr(broadcast_prospects, "prior_opt_out", lambda *args: False)
    body = correction.ConsentRestore(
        operation_id=uuid4(),
        revision=1,
        reason="Corrección autorizada del error inicial",
        evidence="Selección accidental del operador; no es una baja del destinatario.",
        confirmed=True,
    )
    return service, cursor, actor, previous, calls, recorded, body


def test_restore_appends_fail_closed_correction_without_deleting_or_resuming(fixture):
    service, _, _, _, calls, recorded, body = fixture
    result = correction.restore(service, {}, "account", "identity", body)
    assert result == {
        "saved": True,
        "version": 2,
        "state": "unregistered",
        "sending_enabled": False,
    }
    assert len(recorded) == 1
    writes = [(sql, params) for sql, params in calls if sql.startswith("INSERT")]
    assert len(writes) == 1
    sql, params = writes[0]
    assert "'revoked'" in sql and "NULL" in sql
    assert params[0] == "institution" and params[2:5] == ("account", "identity", 2)
    assert correction.UNREGISTERED_ORIGIN in params
    assert not any(
        "DELETE" in sql or "UPDATE" in sql or "SendJob" in sql for sql, _ in calls
    )
    query, scope = calls[0]
    assert "IntegrationId=? AND IdentityId=?" in query
    assert scope == ("institution", "account", "identity")


@pytest.mark.parametrize(
    "change,code",
    [
        ({"State": "granted"}, 409),
        ({"VersionNo": 2}, 409),
        ({"ActorId": str(uuid4())}, 409),
    ],
)
def test_never_overwrites_grants_later_history_or_another_actor(fixture, change, code):
    service, _, _, previous, calls, _, body = fixture
    previous.update(change)
    with pytest.raises(HTTPException) as error:
        correction.restore(service, {}, "account", "identity", body)
    assert error.value.status_code == code
    assert not any(sql.startswith("INSERT") for sql, _ in calls)


@pytest.mark.parametrize("case", ["role", "identity", "unconfirmed", "opt_out"])
def test_requires_owner_exact_identity_confirmation_and_no_real_opt_out(
    fixture, monkeypatch, case
):
    service, cursor, actor, _, calls, _, body = fixture
    if case == "role":
        actor["RoleKey"] = "admin"
    elif case == "identity":
        cursor.found = False
    elif case == "unconfirmed":
        body.confirmed = False
    else:
        monkeypatch.setattr(broadcast_prospects, "prior_opt_out", lambda *args: True)
    with pytest.raises(HTTPException):
        correction.restore(service, {}, "account", "identity", body)
    assert not any(sql.startswith("INSERT") for sql, _ in calls)


def test_replay_does_not_append_another_correction(fixture, monkeypatch):
    service, _, _, _, calls, _, body = fixture
    prior = {"saved": True, "state": "unregistered", "sending_enabled": False}
    monkeypatch.setattr(correction.db, "replay", lambda *args: (b"digest", prior))
    assert correction.restore(service, {}, "account", "identity", body) == prior
    assert not calls


def test_projection_preserves_version_and_can_never_be_a_grant():
    row = {
        "State": "revoked",
        "Origin": correction.UNREGISTERED_ORIGIN,
        "VersionNo": 2,
        "ExpiresAt": None,
    }
    projected = correction.project(row)
    assert projected["State"] == "unregistered" and projected["VersionNo"] == 2
    assert row["State"] == "revoked"
    assert correction.project({**row, "Origin": "manual"})["State"] == "revoked"
    assert correction.project(None) is None


def test_normal_consent_cannot_spoof_administrative_projection():
    with pytest.raises(ValidationError, match="consent_origin_reserved"):
        ConsentWrite(
            operation_id=uuid4(),
            reason="Revisión",
            confirmed=True,
            state="revoked",
            evidence="Texto",
            origin=correction.UNREGISTERED_ORIGIN,
        )
