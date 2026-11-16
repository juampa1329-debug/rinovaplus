"""Authenticate an exact application before durably acknowledging encrypted bytes."""

import asyncio
import hashlib
import hmac
import json
import time
from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.responses import PlainTextResponse

from app.institutional.channel_operations import app_secret_kind, configuration
from app.institutional.channel_secrets import get
from app.institutional.crypto import seal
from app.institutional.db import institution, key, one
from app.institutional.store import transaction


def endpoint(c, settings, endpoint_key):
    value = one(
        c,
        (
            "SELECT e.*,a.ClientId,a.IssuerProfile,a.State AS Application"
            "State FROM crm_channels2.WebhookEndpoint e JOIN crm_channels"
            "2.Application a ON a.InstitutionId=e.InstitutionId AND a.App"
            "licationId=e.ApplicationId WHERE e.InstitutionId=? AND e.End"
            "pointKey=?"
        ),
        institution(settings),
        endpoint_key,
    )
    if not value or value["ApplicationState"] == "retired":
        raise HTTPException(404, "webhook_unavailable")
    return value


def signature_valid(provider, secret, headers, raw, *, now=None):
    if provider == "meta":
        expected = "sha256=" + hmac.digest(secret.encode(), raw, "sha256").hex()
        return hmac.compare_digest(expected, headers.get("x-hub-signature-256", ""))
    # Strict timestamp/signature grammar rejects duplicates and old replay windows.
    try:
        pairs = [
            part.strip().split("=", 1)
            for part in headers.get("tiktok-signature", "").split(",")
        ]
        if len(pairs) != 2 or {p[0] for p in pairs} != {"t", "s"}:
            return False
        fields = dict(pairs)
        timestamp = fields["t"]
        if (
            not timestamp.isascii()
            or not timestamp.isdigit()
            or abs((time.time() if now is None else now) - int(timestamp)) > 300
        ):
            return False
        expected = hmac.digest(
            secret.encode(), timestamp.encode() + b"." + raw, "sha256"
        ).hex()
        return hmac.compare_digest(expected, fields["s"])
    except (ValueError, KeyError, IndexError):
        return False


def body_owner(settings, identity, ep):
    return {
        "institution": institution(settings),
        "receipt": str(identity).lower(),
        "endpoint": str(ep).lower(),
        "kind": "webhook_raw_v1",
    }


def strict_json(raw):
    def pairs(values):
        result = {}
        for name, value in values:
            if name in result:
                raise ValueError("duplicate_json_key")
            result[name] = value
        return result

    def constant(value):
        raise ValueError("nonfinite_json_number")

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


class Ingress:
    def __init__(self, settings):
        self.settings = settings

    def challenge(self, endpoint_key, mode, verify, challenge):
        if (
            mode != "subscribe"
            or not challenge
            or len(challenge) > 2048
            or len(verify) > 256
        ):
            raise HTTPException(403, "webhook_challenge_rejected")
        with transaction(self.settings, True, anonymous=True) as c:
            ep = endpoint(c, self.settings, endpoint_key)
            if ep["Provider"] != "meta":
                raise HTTPException(403, "webhook_challenge_rejected")
            expected, _ = get(
                c, self.settings, "endpoint", str(ep["EndpointId"]), "webhook_verify"
            )
            if not hmac.compare_digest(expected, verify):
                raise HTTPException(403, "webhook_challenge_rejected")
            c.execute(
                (
                    "UPDATE crm_channels2.WebhookEndpoint SET ChallengeVerifiedAt"
                    "=SYSUTCDATETIME(),UpdatedAt=SYSUTCDATETIME() WHERE Instituti"
                    "onId=? AND EndpointId=?"
                ),
                institution(self.settings),
                ep["EndpointId"],
            )
        return challenge

    def receive(self, endpoint_key, headers, raw):
        if len(raw) > 1_000_000:
            raise HTTPException(413, "webhook_too_large")
        with transaction(self.settings, True, anonymous=True) as c:
            ep = endpoint(c, self.settings, endpoint_key)
            if ep["Provider"] == "meta":
                secret, version = get(
                    c,
                    self.settings,
                    "application",
                    str(ep["ApplicationId"]),
                    app_secret_kind(ep),
                )
            else:
                secret, version = get(
                    c,
                    self.settings,
                    "endpoint",
                    str(ep["EndpointId"]),
                    "tiktok_webhook_secret",
                )
            if not signature_valid(ep["Provider"], secret, headers, raw):
                raise HTTPException(403, "webhook_signature_rejected")
            try:
                payload = strict_json(raw)
                if not isinstance(payload, dict):
                    raise ValueError()
            except (ValueError, UnicodeDecodeError, RecursionError):
                raise HTTPException(400, "invalid_webhook_payload") from None
            if (
                ep["Provider"] == "tiktok"
                and payload.get("client_key") != ep["ClientId"]
            ):
                raise HTTPException(403, "webhook_application_mismatch")
            digest = hashlib.sha256(raw).digest()
            existing = c.execute(
                (
                    "SELECT ReceiptId FROM crm_channels2.WebhookReceipt WITH(UPDL"
                    "OCK,HOLDLOCK) WHERE InstitutionId=? AND EndpointId=? AND Dig"
                    "est=?"
                ),
                institution(self.settings),
                ep["EndpointId"],
                digest,
            ).fetchval()
            if existing:
                return {"received": True, "duplicate": True}
            identity = str(uuid4())
            nonce, encrypted = seal(
                key(self.settings),
                body_owner(self.settings, identity, ep["EndpointId"]),
                raw.decode("utf-8"),
            )
            c.execute(
                (
                    "INSERT crm_channels2.WebhookReceipt(InstitutionId,ReceiptId,"
                    "EndpointId,Digest,BodyKeyVersion,BodyNonce,BodyCiphertext,Si"
                    "gnatureKeyVersion,SignatureProfile,Authentication,Status,Rec"
                    "eivedAt,ExpiresAt,ApplicationId,EndpointVersion,SignatureSec"
                    "retId,SignatureVerifiedAt) VALUES(?,?,?,?,?,?,?,?,?,'verifie"
                    "d','queued',SYSUTCDATETIME(),DATEADD(day,?,SYSUTCDATETIME())"
                    ",?,?,?,SYSUTCDATETIME())"
                ),
                institution(self.settings),
                identity,
                ep["EndpointId"],
                digest,
                hashlib.sha256(key(self.settings)).hexdigest()[:32],
                nonce,
                encrypted,
                version["KeyVersion"],
                ep["SignatureProfile"],
                configuration(c, self.settings)["ReceiptRetentionDays"],
                ep["ApplicationId"],
                ep["RowVersion"],
                version["SecretId"],
            )
            c.execute(
                (
                    "UPDATE crm_channels2.WebhookEndpoint SET LastSeenAt=SYSUTCDA"
                    "TETIME() WHERE InstitutionId=? AND EndpointId=?"
                ),
                institution(self.settings),
                ep["EndpointId"],
            )
            return {"received": True, "duplicate": False}


def install(app, settings):
    service = Ingress(settings)

    @app.get("/hooks/channels/{endpoint_key}", include_in_schema=False)
    def challenge(request: Request, endpoint_key: str):
        fields = request.query_params
        if any(
            len(fields.getlist(k)) != 1
            for k in ["hub.mode", "hub.verify_token", "hub.challenge"]
        ):
            raise HTTPException(403, "webhook_challenge_rejected")
        return PlainTextResponse(
            service.challenge(
                endpoint_key,
                fields["hub.mode"],
                fields["hub.verify_token"],
                fields["hub.challenge"],
            )
        )

    @app.post("/hooks/channels/{endpoint_key}", include_in_schema=False)
    async def receive(request: Request, endpoint_key: str):
        if (
            len(request.headers.getlist("x-hub-signature-256")) > 1
            or len(request.headers.getlist("tiktok-signature")) > 1
        ):
            raise HTTPException(403, "webhook_signature_rejected")
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 1_000_000:
                raise HTTPException(413, "webhook_too_large")
        result = await asyncio.to_thread(
            service.receive, endpoint_key, request.headers, bytes(body)
        )
        worker = getattr(app.state, "channel_workers", None)
        if worker is not None and not result["duplicate"]:
            worker.ingress_wake.set()
        return result
