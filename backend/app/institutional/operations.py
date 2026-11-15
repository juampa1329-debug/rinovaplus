"""Local operational observations. No migration, provider, backup or restore API."""

import base64
import hashlib
import hmac
import json
import math
import os
import threading
import time
from pathlib import Path
from uuid import UUID

from fastapi import Request
from fastapi.responses import JSONResponse

from app.institutional.auth import authorize
from app.institutional.db import institution
from app.institutional.operations_policy import VERSION
from app.institutional.store import transaction

STAGES = (
    "events",
    "projection",
    "media",
    "campaigns",
    "broadcasts",
    "dispatch",
    "maintenance",
    "agents",
)
WORKER_MAX_AGE = 180
BACKUP_MAX_AGE = 86400


class Pulse:
    """A stage succeeds only after its consumer returns, including a no-work poll."""

    def __init__(self, clock=time.monotonic, *, stages=STAGES):
        self.clock = clock
        self.lock = threading.Lock()
        self.started = clock()
        self.values = {
            stage: {"success": None, "failure": None, "failures": 0} for stage in stages
        }

    def observe(self, stage, action):
        try:
            result = action()
        except Exception:
            with self.lock:
                self.values[stage]["failure"] = self.clock()
                self.values[stage]["failures"] += 1
            raise
        with self.lock:
            self.values[stage]["success"] = self.clock()
            self.values[stage]["failures"] = 0
        return result

    def snapshot(self, alive):
        now = self.clock()
        with self.lock:
            items = []
            for stage, value in self.values.items():
                age = (
                    None
                    if value["success"] is None
                    else max(0, round(now - value["success"], 1))
                )
                state = (
                    "failed"
                    if value["failures"]
                    else "starting"
                    if age is None
                    else "stale"
                    if age > WORKER_MAX_AGE
                    else "ready"
                )
                items.append(
                    dict(
                        stage=stage,
                        state=state,
                        last_success_age_seconds=age,
                        consecutive_failures=value["failures"],
                    )
                )
        return {
            "alive": bool(alive),
            "ready": bool(alive) and all(v["state"] == "ready" for v in items),
            "freshness_seconds": WORKER_MAX_AGE,
            "stages": items,
        }


def binding(settings):
    ticket = settings.ticket
    return {
        "database": ticket["identity"]["database"],
        "institution": institution(settings),
        "principal_sid": ticket["sid"],
        "release": ticket["operations_release_sha256"],
        "profile_binding": settings.review["ticket_sha256"],
    }


def canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def receipt_key(settings):
    key = base64.b64decode(settings.review["secrets_key"], validate=True)
    return hmac.digest(
        key, b"cbn_ops11_receipt_v1\x00" + canonical(binding(settings)), "sha256"
    )


def sign_receipt(settings, *, backup_uuid, ready_blobs, restored_database, now=None):
    """Operator calls only after native SQL+file restore verification has succeeded."""
    from app.institutional.operations_policy import TARGET

    if (
        settings.ticket.get("version") != VERSION
        or not TARGET.fullmatch(restored_database)
        or restored_database == settings.ticket["identity"]["database"]
    ):
        raise ValueError("P11ES_verified_separate_restore_required")
    if type(ready_blobs) is not int or ready_blobs < 0:
        raise ValueError("P11ES_blob_count")
    body = {
        "version": 1,
        "binding": binding(settings),
        "backup_uuid": str(UUID(backup_uuid)),
        "verified_at": time.time() if now is None else now,
        "ready_blobs": ready_blobs,
        "sql_checksum_verified": True,
        "restored_and_checkdb_verified": True,
        "restored_database": restored_database,
    }
    return {
        "body": body,
        "signature": hmac.new(
            receipt_key(settings), canonical(body), hashlib.sha256
        ).hexdigest(),
    }


def inspect_receipt(settings, value, now=None):
    now = time.time() if now is None else now
    try:
        body = value["body"]
        if set(value) != {"body", "signature"} or set(body) != {
            "version",
            "binding",
            "backup_uuid",
            "verified_at",
            "ready_blobs",
            "sql_checksum_verified",
            "restored_and_checkdb_verified",
            "restored_database",
        }:
            raise ValueError("shape")
        expected = hmac.new(
            receipt_key(settings), canonical(body), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, value["signature"]) or body[
            "binding"
        ] != binding(settings):
            raise ValueError("binding")
        if (
            body["version"] != 1
            or body["sql_checksum_verified"] is not True
            or body["restored_and_checkdb_verified"] is not True
            or type(body["ready_blobs"]) is not int
            or body["ready_blobs"] < 0
        ):
            raise ValueError("evidence")
        stamp = body["verified_at"]
        if (
            type(stamp) not in (float, int)
            or not math.isfinite(stamp)
            or stamp > now + 5
        ):
            raise ValueError("time")
        if str(UUID(body["backup_uuid"])) != body["backup_uuid"]:
            raise ValueError("backup")
        from app.institutional.operations_policy import TARGET

        if (
            not TARGET.fullmatch(body["restored_database"])
            or body["restored_database"] == settings.ticket["identity"]["database"]
        ):
            raise ValueError("restore")
        age = max(0, int(now - stamp))
        return {
            "state": "verified" if age <= BACKUP_MAX_AGE else "stale",
            "verified_at": stamp,
            "age_seconds": age,
            "freshness_seconds": BACKUP_MAX_AGE,
            "ready_blobs": body["ready_blobs"],
            "restore_verified": True,
        }
    except (KeyError, TypeError, ValueError, AttributeError):
        return {"state": "invalid", "restore_verified": False}


def receipt_path():
    return (
        Path(os.environ.get("CRM_AI_STATE_DIR", "/var/lib/crm-ai"))
        / "operations/latest-receipt.json"
    )


def backup_status(settings):
    path = receipt_path()
    try:
        if path.is_symlink() or path.parent.is_symlink() or path.stat().st_size > 8192:
            return {"state": "invalid", "restore_verified": False}
        return inspect_receipt(settings, json.loads(path.read_text(encoding="utf-8")))
    except FileNotFoundError:
        return {"state": "missing", "restore_verified": False}
    except (OSError, ValueError):
        return {"state": "invalid", "restore_verified": False}


def worker_status(app):
    workers = getattr(app.state, "channel_workers", None)
    if workers is None:
        return {
            "alive": False,
            "ready": False,
            "freshness_seconds": WORKER_MAX_AGE,
            "stages": [],
        }
    return workers.pulse.snapshot(
        workers.thread is not None
        and workers.thread.is_alive()
        and not workers.stop_event.is_set()
    )


def queues(c, settings):
    """Global grouped counts, never the truncated administrative activity list."""
    if getattr(settings, "postgres_profile", False):
        from app.institutional.postgres_queue import counts

        return counts(c, institution(settings))
    definitions = {
        "webhook_receipts": ("crm_channels2.WebhookReceipt", "Status"),
        "webhook_events": ("crm_channels2.WebhookEvent", "Status"),
        "outbound": ("crm_channels2.SendJob", "State"),
        "provider_operations": ("crm_channels2.ProviderOperation", "Status"),
        "media": ("crm_channels4.MediaAsset", "State"),
        "agent_requests": ("crm_agents5.Request", "State"),
        "broadcasts": ("crm_broadcast7.Campaign", "State"),
        "campaign_enrollments": ("crm_campaign8.Enrollment", "State"),
    }
    result = {}
    for label, (table, column) in definitions.items():
        # Identifiers are closed constants; institution is always parameterized.
        result[label] = {
            str(row[0]): int(row[1])
            for row in c.execute(
                "SELECT "
                + column
                + ",COUNT_BIG(*) FROM "
                + table
                + " WHERE InstitutionId=? GROUP BY "
                + column,
                institution(settings),
            ).fetchall()
        }
    return result


def install(app, settings):
    postgres = getattr(settings, "postgres_profile", False)
    deployment = getattr(settings, "postgres_deployment", False)
    scope = "postgres_deployment" if deployment else "postgres_rehearsal" if postgres else "local"

    @app.get("/api/institution/operations")
    def status(request: Request):
        # A separate transaction revalidates SQL identity, model, journals and ACL.
        with transaction(settings, anonymous=True) as c:
            authorize(c, settings, request.state.authority, "users.manage")
            counts = queues(c, settings)
        workers = worker_status(app)
        return {
            "scope": scope,
            "sql": {
                "state": "verified",
                "engine": 16 if postgres else 2019,
                "tables": len(settings.ticket["table_map"]) if postgres else 185,
                "academic_access": False,
            },
            "workers": workers,
            "queues": counts,
            "backup": {"state": "unverified" if deployment else "rehearsal"} if postgres else backup_status(settings),
            "local_ready": workers["ready"],
            "online": {"state": "pending", "phase": "P12"},
            "observed_at": time.time(),
        }

    @app.get("/health/ready")
    def ready():
        try:
            with transaction(settings, anonymous=True):
                pass
            ok = worker_status(app)["ready"]
        except Exception:
            ok = False
        return JSONResponse(
            {"status": "ready" if ok else "unavailable", "scope": scope},
            200 if ok else 503,
        )
