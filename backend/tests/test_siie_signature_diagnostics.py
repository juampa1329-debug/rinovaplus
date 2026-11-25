"""Signature diagnostics distinguish clock errors without exposing credentials."""

import hmac
import logging

import pytest
from fastapi import HTTPException

from app.institutional import siie_webhook as hook

NOW = 1795646000
KEY = "fixture-only-signature-key-never-log-this-value"
BODY = b'{"private-person-field":"do-not-log-person-or-document"}'


def headers(stamp, *, other_key=None):
    stamp = str(stamp)
    signature = hmac.digest(
        (other_key or KEY).encode(),
        b"rinovaplus-siie-v1." + stamp.encode() + b"." + BODY,
        "sha256",
    ).hex()
    return {"x-siie-timestamp": stamp, "x-siie-signature": "sha256=" + signature}


@pytest.mark.parametrize(
    "stamp,other_key,reason,skew",
    [
        (NOW + 10800, None, "clock_skew", -10800),
        (NOW, "wrong-test-key", "signature_mismatch", 0),
        (NOW + 10800, "wrong-test-key", "clock_skew_and_signature_mismatch", -10800),
    ],
)
def test_signature_rejects_with_safe_operator_reason(
    monkeypatch, caplog, stamp, other_key, reason, skew
):
    monkeypatch.setenv("SIIE_WEBHOOK_SECRET", KEY)
    supplied = headers(stamp, other_key=other_key)
    with caplog.at_level(logging.WARNING), pytest.raises(HTTPException) as caught:
        hook.verify(supplied, BODY, now=NOW)
    assert caught.value.status_code == 403
    assert caught.value.detail == "siie_webhook_signature_rejected"
    assert f"reason={reason} skew_seconds={skew}" in caplog.text
    assert KEY not in caplog.text
    assert supplied["x-siie-signature"] not in caplog.text
    assert supplied["x-siie-timestamp"] not in caplog.text
    assert "private-person-field" not in caplog.text
    assert "do-not-log-person-or-document" not in caplog.text


@pytest.mark.parametrize("stamp", [NOW - 300, NOW, NOW + 300])
def test_valid_signature_keeps_exact_five_minute_boundary(monkeypatch, caplog, stamp):
    monkeypatch.setenv("SIIE_WEBHOOK_SECRET", KEY)
    hook.verify(headers(stamp), BODY, now=NOW)
    assert "siie_webhook_rejected" not in caplog.text


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"x-siie-timestamp": "1795646000000"}, "timestamp_format"),
        ({"x-siie-signature": "SHA256=" + "a" * 64}, "signature_format"),
    ],
)
def test_malformed_headers_log_only_a_constant_reason(
    monkeypatch, caplog, change, reason
):
    monkeypatch.setenv("SIIE_WEBHOOK_SECRET", KEY)
    supplied = {**headers(NOW), **change}
    with caplog.at_level(logging.WARNING), pytest.raises(HTTPException):
        hook.verify(supplied, BODY, now=NOW)
    assert f"reason={reason}" in caplog.text
    assert KEY not in caplog.text
    assert all(value not in caplog.text for value in supplied.values())
