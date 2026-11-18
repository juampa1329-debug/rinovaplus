"""Recovery claims fail closed and stay bound to their observed deployment."""

import base64
import copy
import json
from types import SimpleNamespace

import pytest

from app.institutional.postgres_operations import (
    backup_status,
    inspect_recovery_receipt,
    sign_recovery_receipt,
)


def settings():
    return SimpleNamespace(
        postgres_profile=True,
        postgres_user="rinovaplus_app",
        ticket={
            "identity": {"database": "rinovaplus"},
            "scope": "postgres_deployment",
            "context": [[1, "00000000-0000-4000-8000-000000000001"]],
        },
        review={
            "secrets_key": base64.b64encode(b"k" * 32).decode(),
            "session_token": "bound-profile",
        },
    )


def evidence():
    return dict(
        archive_sha256="a" * 64,
        source_manifest_sha256="b" * 64,
        restored_manifest_sha256="b" * 64,
        media_archive_sha256="c" * 64,
        media_manifest_sha256="d" * 64,
        restored_media_manifest_sha256="d" * 64,
        restored_database="rinovaplus_p11_restore_20261118_b",
        table_count=157,
        media_count=19,
        secrets_authenticated=True,
        runtime_restore_access=False,
    )


def test_dated_receipt_expires_without_claiming_continuous_backup_verification():
    s = settings()
    v = sign_recovery_receipt(s, evidence(), now=1000)
    assert inspect_recovery_receipt(s, v, now=1001)["state"] == "verified"
    assert inspect_recovery_receipt(s, v, now=88000)["state"] == "stale"
    assert "archive_sha256" not in inspect_recovery_receipt(s, v, now=1001)


@pytest.mark.parametrize(
    "field,value",
    [
        ("restored_manifest_sha256", "e" * 64),
        ("restored_media_manifest_sha256", "e" * 64),
        ("restored_database", "rinovaplus"),
        ("restored_database", "arbitrary"),
        ("table_count", 154),
        ("media_count", True),
        ("secrets_authenticated", False),
        ("runtime_restore_access", True),
        ("archive_sha256", "not-a-hash"),
    ],
)
def test_incomplete_or_unsafe_restore_cannot_be_signed(field, value):
    data = evidence()
    data[field] = value
    with pytest.raises(ValueError):
        sign_recovery_receipt(settings(), data, now=1000)


@pytest.mark.parametrize(
    "part", ["database", "institution", "principal", "scope", "profile", "key"]
)
def test_receipt_cannot_cross_deployment_binding(part):
    s = settings()
    signed = sign_recovery_receipt(s, evidence(), now=1000)
    other = copy.deepcopy(s)
    if part == "database":
        other.ticket["identity"]["database"] = "other"
    elif part == "institution":
        other.ticket["context"][0][1] = "00000000-0000-4000-8000-000000000002"
    elif part == "principal":
        other.postgres_user = "different"
    elif part == "scope":
        other.ticket["scope"] = "postgres_rehearsal"
    elif part == "profile":
        other.review["session_token"] = "other-profile"
    else:
        other.review["secrets_key"] = base64.b64encode(b"x" * 32).decode()
    assert inspect_recovery_receipt(other, signed, now=1001)["state"] == "invalid"


def test_tampering_future_nonfinite_and_unknown_fields_are_invalid():
    s = settings()
    signed = sign_recovery_receipt(s, evidence(), now=1000)
    changed = copy.deepcopy(signed)
    changed["body"]["evidence"]["media_count"] = 20
    assert inspect_recovery_receipt(s, changed, now=1001)["state"] == "invalid"
    assert inspect_recovery_receipt(s, signed, now=1)["state"] == "invalid"
    changed = copy.deepcopy(signed)
    changed["body"]["verified_at"] = float("nan")
    assert inspect_recovery_receipt(s, changed, now=1001)["state"] == "invalid"
    signed["extra"] = True
    assert inspect_recovery_receipt(s, signed, now=1001)["state"] == "invalid"


def test_missing_corrupt_oversized_and_valid_receipt(tmp_path, monkeypatch):
    monkeypatch.setenv("CRM_AI_STATE_DIR", str(tmp_path))
    s = settings()
    assert backup_status(s)["state"] == "missing"
    folder = tmp_path / "operations"
    folder.mkdir()
    p = folder / "postgres-recovery-receipt.json"
    p.write_text("{broken")
    assert backup_status(s)["state"] == "invalid"
    p.write_text(" " * 17000)
    assert backup_status(s)["state"] == "invalid"
    p.write_text(json.dumps(sign_recovery_receipt(s, evidence())))
    assert backup_status(s)["state"] == "verified"


def test_operations_endpoint_reports_actual_engine_and_preserves_global_queue_counts(
    tmp_path, monkeypatch
):
    from contextlib import nullcontext
    from unittest.mock import Mock, patch

    from fastapi import FastAPI, Request
    from fastapi.testclient import TestClient

    from app.institutional import operations

    s = settings()
    s.postgres_deployment = True
    s.public_origin = "https://app.example.test"
    s.ticket["table_map"] = {str(i): str(i) for i in range(155)}
    monkeypatch.setenv("CRM_AI_STATE_DIR", str(tmp_path))
    app = FastAPI()

    @app.middleware("http")
    async def test_authority(request: Request, call_next):
        request.state.authority = "verified-by-separate-auth-boundary-tests"
        return await call_next(request)

    operations.install(app, s)
    c = Mock()
    c.native.return_value.fetchval.return_value = "16.16"
    with (
        patch.object(operations, "transaction", return_value=nullcontext(c)),
        patch.object(operations, "authorize") as auth,
        patch.object(
            operations, "queues", return_value={"outbound": {"uncertain": 5001}}
        ),
    ):
        result = TestClient(app).get("/api/institution/operations")
    assert result.status_code == 200
    body = result.json()
    assert body["sql"]["product"] == "PostgreSQL" and body["sql"]["version"] == "16.16"
    assert body["queues"]["outbound"]["uncertain"] == 5001
    assert body["backup"] == {"state": "missing", "restore_verified": False}
    assert body["online"]["state"] == "configured"
    assert body["infrastructure"]["redis"] == "not_used"
    auth.assert_called_once_with(
        c, s, "verified-by-separate-auth-boundary-tests", "users.manage"
    )
