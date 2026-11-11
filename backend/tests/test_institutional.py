"""Security properties independent of SQL transport. Connected tests are separate."""

import base64
import json
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from app.institutional import auth
from app.institutional.crypto import (
    matching_step,
    password_hash,
    password_matches,
    recovery_codes,
    seal,
    token,
    totp_code,
    unseal,
)
from app.institutional.db import bound_hash
from app.institutional.management import manageable
from app.institutional.models import (
    Availability,
    Bootstrap,
    Institution,
    RoleEdit,
    UserCreate,
)
from app.institutional.policy import ACTIONS, MODULES, principal
from cryptography.exceptions import InvalidTag
from fastapi import HTTPException
from pydantic import ValidationError


def test_password_kdf_preserves_long_unicode_and_rejects_wrong_password():
    encoded = password_hash("Una contraseña larga y única 2026")
    assert password_matches("Una contraseña larga y única 2026", encoded)
    assert not password_matches("Una contraseña larga y única 2027", encoded)
    assert "Una contraseña" not in encoded
    assert encoded != password_hash("Una contraseña larga y única 2026")


@pytest.mark.parametrize("value", ["corta", "123456789012345", "x" * 129])
def test_invalid_passwords_rejected(value):
    with pytest.raises(ValueError):
        password_hash(value)


@pytest.mark.parametrize(
    "timestamp,expected",
    [
        (59, "287082"),
        (1111111109, "081804"),
        (1111111111, "050471"),
        (1234567890, "005924"),
        (2000000000, "279037"),
        (20000000000, "353130"),
    ],
)
def test_totp_interoperability_vectors(timestamp, expected):
    # RFC6238 SHA1 vectors truncated to six digits, as used by authenticators.
    secret = base64.b32encode(b"12345678901234567890").decode()
    assert totp_code(secret, timestamp // 30) == expected


def test_totp_replay_and_unicode_digits_are_rejected():
    secret = base64.b32encode(b"12345678901234567890").decode()
    assert matching_step(secret, "287082", now=59) == 1
    assert matching_step(secret, "287082", last=1, now=59) is None
    assert matching_step(secret, "２８７０８２", now=59) is None


def test_ciphertext_cannot_move_to_another_owner_or_version():
    key = b"k" * 32
    owner = {"institution": "a", "owner": "integration-a", "version": 1}
    nonce, cipher = seal(key, owner, "synthetic token")
    assert unseal(key, owner, nonce, cipher) == "synthetic token"
    for changed in ({**owner, "owner": "integration-b"}, {**owner, "version": 2}):
        with pytest.raises(InvalidTag):
            unseal(key, changed, nonce, cipher)


def test_tokens_and_recovery_codes_have_independent_entropy():
    codes = recovery_codes()
    assert len(codes) == len(set(codes)) == 8
    assert all(len(c) == 32 for c in codes)
    assert len(token()) >= 40


def test_sessions_are_bound_to_target_database_and_purpose():
    a = SimpleNamespace(
        connection={"database": "a"},
        review={"session_token": "s" * 64},
        ticket={"context": [[1, "00000000-0000-0000-0000-000000000001", "v"]]},
    )
    b = SimpleNamespace(connection={"database": "b"}, review=a.review, ticket=a.ticket)
    assert bound_hash(a, "synthetic", "session") != bound_hash(
        b, "synthetic", "session"
    )
    assert bound_hash(a, "synthetic", "session") != bound_hash(a, "synthetic", "redeem")


def test_delegated_user_manager_cannot_reset_or_edit_a_superior_account():
    class Cursor:
        def execute(self, *args):
            return self

        def fetchval(self):
            return json.dumps(list(ACTIONS))

    settings = SimpleNamespace(
        ticket={"context": [[1, "00000000-0000-0000-0000-000000000001", "v"]]}
    )
    actor = {"RoleKey": "helpdesk", "Actions": json.dumps(["users.manage"])}
    with pytest.raises(HTTPException) as denied:
        manageable(Cursor(), settings, actor, {"RoleKey": "admin"})
    assert denied.value.status_code == 403


def test_rate_rejection_does_not_compute_password_kdf(monkeypatch):
    @contextmanager
    def fake_transaction(*args, **kwargs):
        yield object()

    monkeypatch.setattr(auth, "transaction", fake_transaction)
    monkeypatch.setattr(auth, "rate", lambda *args: False)
    monkeypatch.setattr(auth, "audit", lambda *args, **kwargs: None)

    def forbidden(*args, **kwargs):
        raise AssertionError("Password KDF/user lookup ran after rate denial")

    monkeypatch.setattr(auth, "password_matches", forbidden)
    monkeypatch.setattr(auth, "one", forbidden)
    body = SimpleNamespace(
        email="user@example.invalid",
        password=SimpleNamespace(get_secret_value=lambda: "synthetic"),
    )
    with pytest.raises(HTTPException) as denied:
        auth.Identity(object()).login(body)
    assert denied.value.status_code == 429


def test_authority_cannot_be_mass_assigned():
    with pytest.raises(ValidationError):
        UserCreate(
            operation_id="00000000-0000-0000-0000-000000000001",
            email="u@example.invalid",
            full_name="Usuario",
            role="viewer",
            AuthVersion=999,
        )
    with pytest.raises(ValidationError):
        Bootstrap(
            email="owner@example.invalid",
            password="Una contraseña muy larga 2026",
            bootstrap_token="x" * 43,
            full_name="Persona",
            role="owner",
        )


def test_unknown_actions_modules_and_timezone_rejected():
    with pytest.raises(ValidationError):
        RoleEdit(operation_id="x", revision=0, name="Rol", actions=["billing.manage"])
    with pytest.raises(ValidationError):
        Availability(enabled={m: True for m in MODULES} | {"woocommerce": True})
    with pytest.raises(ValidationError):
        Institution(name="Institución", timezone="not-a-zone")


@pytest.mark.parametrize(
    "database", ["HORARIOSSIIE", "DBSIIE", "CBN_C13_TRIAL_20261025_1f10a824", "master"]
)
def test_prior_source_never_a_P2_runtime_target(database):
    with pytest.raises(ValueError):
        principal(database)
