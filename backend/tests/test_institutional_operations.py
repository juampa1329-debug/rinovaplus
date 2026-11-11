"""Operational evidence must be fresh, scoped and fail closed."""

import base64
import copy
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.institutional.operations import (
    STAGES,
    Pulse,
    backup_status,
    inspect_receipt,
    sign_receipt,
)
from app.institutional.operations_policy import principal


def settings():
    return SimpleNamespace(
        ticket={
            "version": "cbn-institutional-operations-p11-v1",
            "context": [["institution", str(uuid4())]],
            "identity": {"database": "CBN_P11ES_TRIAL_20261028_1234abcd"},
            "sid": "0001",
            "operations_release_sha256": "a" * 64,
        },
        review={
            "secrets_key": base64.b64encode(b"s" * 32).decode(),
            "ticket_sha256": "b" * 64,
        },
    )


def receipt(s, stamp=1000):
    return sign_receipt(
        s,
        backup_uuid=str(uuid4()),
        ready_blobs=4,
        restored_database="CBN_P11ES_RECOVERY_20261028_deadbeef",
        now=stamp,
    )


def test_pulse_requires_every_consumer_and_freshness_and_thread():
    clock = [0.0]
    p = Pulse(lambda: clock[0])
    assert not p.snapshot(True)["ready"]
    for stage in STAGES:
        assert p.observe(stage, lambda: 4) == 4
    assert p.snapshot(True)["ready"] and not p.snapshot(False)["ready"]
    clock[0] = 181
    assert not p.snapshot(True)["ready"]
    assert {v["state"] for v in p.snapshot(True)["stages"]} == {"stale"}


def test_failed_consumer_is_not_masked_by_previous_success_or_other_stage():
    p = Pulse()
    for stage in STAGES:
        p.observe(stage, lambda: None)

    def fail():
        raise RuntimeError("private provider body")

    with pytest.raises(RuntimeError):
        p.observe("campaigns", fail)
    p.observe("events", lambda: None)
    state = p.snapshot(True)
    assert not state["ready"]
    assert "private" not in str(state)
    p.observe("campaigns", lambda: None)
    assert p.snapshot(True)["ready"]


def test_verified_receipt_becomes_stale_without_changing_its_signature():
    s = settings()
    value = receipt(s)
    assert inspect_receipt(s, value, 1100)["state"] == "verified"
    assert inspect_receipt(s, value, 88000)["state"] == "stale"


@pytest.mark.parametrize(
    "field,value",
    [
        ("ready_blobs", 99),
        ("verified_at", 9999),
        ("sql_checksum_verified", False),
        ("restored_and_checkdb_verified", False),
        ("backup_uuid", str(uuid4())),
    ],
)
def test_tampered_receipt_is_not_evidence(field, value):
    s = settings()
    result = receipt(s)
    result["body"][field] = value
    assert inspect_receipt(s, result, 1100)["state"] == "invalid"


@pytest.mark.parametrize(
    "part", ["database", "institution", "sid", "profile", "release", "key"]
)
def test_receipt_cannot_be_replayed_across_identity_or_profile(part):
    s = settings()
    value = receipt(s)
    other = copy.deepcopy(s)
    if part == "database":
        other.ticket["identity"]["database"] = "CBN_P11ES_TRIAL_20261028_deadbeef"
    if part == "institution":
        other.ticket["context"][0][1] = str(uuid4())
    if part == "sid":
        other.ticket["sid"] = "0002"
    if part == "profile":
        other.review["ticket_sha256"] = "c" * 64
    if part == "release":
        other.ticket["operations_release_sha256"] = "d" * 64
    if part == "key":
        other.review["secrets_key"] = base64.b64encode(b"t" * 32).decode()
    assert inspect_receipt(other, value, 1100)["state"] == "invalid"


def test_missing_corrupt_and_symlink_file_are_not_success(tmp_path, monkeypatch):
    monkeypatch.setenv("CRM_AI_STATE_DIR", str(tmp_path))
    s = settings()
    assert backup_status(s)["state"] == "missing"
    (tmp_path / "operations").mkdir()
    (tmp_path / "operations/latest-receipt.json").write_text("{broken")
    assert backup_status(s)["state"] == "invalid"


def test_future_signed_receipt_and_same_database_restore_are_rejected():
    s = settings()
    assert inspect_receipt(s, receipt(s, 5000), 1100)["state"] == "invalid"
    with pytest.raises(ValueError):
        sign_receipt(
            s,
            backup_uuid=str(uuid4()),
            ready_blobs=4,
            restored_database=s.ticket["identity"]["database"],
        )


@pytest.mark.parametrize(
    "database",
    [
        "HORARIOSSIIE",
        "DBSIIE",
        "CBN_P10ES_TRIAL_20261028_1234abcd",
        "CBN_P11ES_TRIAL_20261029_1234abcd",
        "CBN_P11ES_TRIAL_20261028_1234abcd;DROP DATABASE x",
    ],
)
def test_principal_cannot_target_academic_previous_or_arbitrary_database(database):
    with pytest.raises(ValueError):
        principal(database)
