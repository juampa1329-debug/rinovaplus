"""Authenticate raw webhook bytes, then durably acknowledge without ingestion."""

import asyncio
import hashlib
import hmac
import json
import time
from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from .storage import CHANNELS, document


async def receive(request: Request, provider: str):
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > 1_000_000:
            raise HTTPException(413, "webhook_too_large")
    raw = bytes(raw)
    return await asyncio.to_thread(persist_receipt, request, provider, raw)


def persist_receipt(request, provider, raw):
    store = request.app.state.channel_store
    with store.transaction() as cursor:
        accounts = [
            store.get(cursor, c, True)
            for c in CHANNELS
            if (c == "tiktok") == (provider == "tiktok")
        ]
    matched = []
    for account in accounts:
        secret = account["secrets"].get("appSecret")
        if not secret:
            continue
        if provider == "meta":
            expected = (
                "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
            )
            valid = hmac.compare_digest(
                expected, request.headers.get("x-hub-signature-256", "")
            )
        else:
            valid = verify_tiktok(account, request.headers, raw)
        if valid:
            matched.append(account["channel"])
    if not matched:
        raise HTTPException(403, "webhook_signature_rejected")
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError()
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(400, "invalid_webhook_payload") from None
    # Persist the matched channel set, never credentials or signature headers.
    envelope = {"payload": payload, "channels": matched, "raw": raw.decode("utf-8")}
    digest = hashlib.sha256(raw).digest()
    with store.transaction() as cursor:
        cursor.execute(
            "IF NOT EXISTS(SELECT 1 FROM crm_channels.webhook_events WITH(UPDLOCK,HOLDLOCK) WHERE Provider=? AND Digest=?) INSERT crm_channels.webhook_events(EventId,Provider,Digest,Payload) VALUES(?,?,?,?)",
            provider,
            digest,
            str(uuid4()),
            provider,
            digest,
            document(envelope),
        )
    return JSONResponse({"received": True}, headers={"Cache-Control": "no-store"})


def verify_tiktok(account, headers, raw):
    try:
        pairs = [
            item.strip().split("=", 1)
            for item in headers.get("tiktok-signature", "").split(",")
        ]
        if len(pairs) != 2 or {p[0] for p in pairs} != {"t", "s"}:
            return False
        fields = dict(pairs)
        timestamp = fields["t"]
        if not timestamp.isdigit() or abs(time.time() - int(timestamp)) > 300:
            return False
        expected = hmac.new(
            account["secrets"]["appSecret"].encode(),
            timestamp.encode() + b"." + raw,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, fields["s"])
    except (ValueError, KeyError, IndexError):
        return False
