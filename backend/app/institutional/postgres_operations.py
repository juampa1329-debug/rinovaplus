"""Read-only PostgreSQL recovery receipts, issued by an operator after a restore.

The signature authenticates a dated observation, not a continuously rehashed
archive. There is deliberately no HTTP endpoint to create or restore backups.
"""

import hashlib
import hmac
import json
import math
import os
import re
import time
from pathlib import Path

from app.institutional.db import institution, key

FIELDS = {
    "archive_sha256",
    "source_manifest_sha256",
    "restored_manifest_sha256",
    "media_archive_sha256",
    "media_manifest_sha256",
    "restored_media_manifest_sha256",
    "restored_database",
    "table_count",
    "media_count",
    "secrets_authenticated",
    "runtime_restore_access",
}


def canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def binding(settings):
    return {
        "database": settings.ticket["identity"]["database"],
        "institution": institution(settings),
        "principal": settings.postgres_user,
        "scope": settings.ticket["scope"],
        "profile": hashlib.sha256(
            settings.review["session_token"].encode()
        ).hexdigest(),
    }


def signing_key(settings):
    return hmac.digest(
        key(settings),
        b"rinova-pg-recovery-v1\0" + canonical(binding(settings)),
        "sha256",
    )


def valid_evidence(value, database):
    return (
        set(value) == FIELDS
        and all(
            isinstance(value[k], str) and re.fullmatch(r"[0-9a-f]{64}", value[k])
            for k in FIELDS
            if k.endswith("sha256")
        )
        and value["source_manifest_sha256"] == value["restored_manifest_sha256"]
        and value["media_manifest_sha256"] == value["restored_media_manifest_sha256"]
        and isinstance(value["restored_database"], str)
        and re.fullmatch(
            r"rinovaplus_p11_restore_[0-9]{8}_[a-z0-9]{1,16}",
            value["restored_database"],
        )
        and value["restored_database"] != database
        and type(value["table_count"]) is int
        and 155 <= value["table_count"] <= 10000
        and type(value["media_count"]) is int
        and 0 <= value["media_count"] <= 1000000
        and value["secrets_authenticated"] is True
        and value["runtime_restore_access"] is False
    )


def sign_recovery_receipt(settings, evidence, *, now=None):
    """Operator-only helper: call after dump/manifest/file/secret verification."""
    if not getattr(settings, "postgres_profile", False) or not valid_evidence(
        evidence, settings.ticket["identity"]["database"]
    ):
        raise ValueError("postgres_verified_restore_evidence_required")
    body = {
        "version": 1,
        "binding": binding(settings),
        "verified_at": time.time() if now is None else now,
        "evidence": dict(evidence),
    }
    return {
        "body": body,
        "signature": hmac.new(
            signing_key(settings), canonical(body), hashlib.sha256
        ).hexdigest(),
    }


def inspect_recovery_receipt(settings, value, *, now=None):
    now = time.time() if now is None else now
    try:
        body = value["body"]
        stamp = body["verified_at"]
        if (
            set(value) != {"body", "signature"}
            or set(body) != {"version", "binding", "verified_at", "evidence"}
            or body["version"] != 1
            or body["binding"] != binding(settings)
            or type(stamp) not in {int, float}
            or not math.isfinite(stamp)
            or stamp <= 0
            or stamp > now + 60
            or not valid_evidence(
                body["evidence"], settings.ticket["identity"]["database"]
            )
            or not hmac.compare_digest(
                value["signature"],
                hmac.new(
                    signing_key(settings), canonical(body), hashlib.sha256
                ).hexdigest(),
            )
        ):
            raise ValueError("invalid_receipt")
        age = max(0, now - stamp)
        return {
            "state": "verified" if age <= 86400 else "stale",
            "restore_verified": True,
            "verified_at": stamp,
            "age_seconds": round(age),
            "ready_blobs": body["evidence"]["media_count"],
            "tables": body["evidence"]["table_count"],
            "scope": "dated_operator_restore",
        }
    except (KeyError, TypeError, ValueError, AttributeError):
        return {"state": "invalid", "restore_verified": False}


def backup_status(settings):
    path = (
        Path(os.environ.get("CRM_AI_STATE_DIR", ".local"))
        / "operations/postgres-recovery-receipt.json"
    )
    try:
        if path.is_symlink() or path.stat().st_size > 16384:
            return {"state": "invalid", "restore_verified": False}
        return inspect_recovery_receipt(
            settings, json.loads(path.read_text(encoding="utf-8"))
        )
    except FileNotFoundError:
        return {"state": "missing", "restore_verified": False}
    except (OSError, ValueError):
        return {"state": "invalid", "restore_verified": False}
