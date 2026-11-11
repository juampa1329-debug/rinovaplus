"""Pure Meta subscription verification; never accepts webhook events."""

import hashlib
import hmac
import re


def verification_configured(expected_digest: str) -> bool:
    """Report configuration availability without exposing the digest."""
    return re.fullmatch(r"[0-9a-fA-F]{64}", expected_digest) is not None


def verify_subscription(mode: str, token: str, expected_digest: str) -> bool | None:
    """Return None for unavailable configuration, otherwise a token verdict."""
    if not verification_configured(expected_digest):
        return None
    supplied = hashlib.sha256(token.encode("utf-8")).digest()
    matches = hmac.compare_digest(supplied, bytes.fromhex(expected_digest))
    return mode == "subscribe" and matches
