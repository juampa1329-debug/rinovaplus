"""Explicit, inspected sample uploads to Meta; no message or template is published."""

import base64
import hashlib
import json
import re
from contextlib import suppress
from uuid import uuid4

import httpx2 as httpx
from fastapi import HTTPException

from app.institutional import broadcast_templates as templates
from app.institutional.channel_operations import account
from app.institutional.channel_provider import provider_account
from app.institutional.db import bound_hash, institution, one
from app.modules.channels import providers
from app.modules.inbox.infrastructure import media_files as files

MIMES = {"image": {"image/jpeg", "image/png"}, "video": {"video/mp4"}, "document": {"application/pdf"}}


def checked(body):
    from app.institutional.campaign_media import inspect

    try:
        raw = base64.b64decode(body.content_base64, validate=True)
    except (ValueError, TypeError):
        raise HTTPException(422, "invalid_media_encoding") from None
    if not 0 < len(raw) <= files.MAX_BYTES:
        raise HTTPException(413, "media_size_limit")
    identity = str(uuid4())
    try:
        files.path(identity, ".part").write_bytes(raw)
        info = inspect(identity, body.filename, body.kind)
        if info["kind"] != body.kind or info["mime"] not in MIMES[body.kind]:
            raise HTTPException(415, "template_sample_format_invalid")
        return files.path(identity).read_bytes(), info
    finally:
        for suffix in (".part", ".checked", ".bin"):
            with suppress(OSError):
                files.path(identity, suffix).unlink(missing_ok=True)


def graph_upload(adapter, data, info, before_part):
    """Meta's official two-stage resumable upload, fixed host, bounded response."""
    app = adapter["configuration"].get("appId", "")
    version = adapter["configuration"].get("apiVersion", "")
    token = adapter["secrets"].get("accessToken")
    if adapter["channel"] != "whatsapp" or not re.fullmatch(r"[0-9]{1,30}", app) or not re.fullmatch(r"v[0-9]{1,2}\.[0-9]{1,2}", version):
        raise HTTPException(409, "template_sample_account_required")
    if not token:
        raise providers.ProviderFailure("access_token_required")
    before_part()
    session = providers.request(adapter, "POST", app + "/uploads", params={
        "file_name": info["name"], "file_length": len(data), "file_type": info["mime"],
    }).get("id")
    # Provider's opaque upload ID may include its signed query. It cannot change
    # the graph host, introduce a path separator, fragment, or header control.
    if not isinstance(session, str) or not re.fullmatch(r"upload:[A-Za-z0-9_.:=+?&%\-]{1,4000}", session):
        raise providers.ProviderFailure("template_sample_session_invalid", uncertain=True)
    before_part()
    try:
        with httpx.Client(timeout=30, follow_redirects=False, trust_env=False) as client:
            with client.stream("POST", f"https://graph.facebook.com/{version}/{session}",
                               headers={"Authorization": "OAuth " + token, "file_offset": "0", "Content-Type": "application/octet-stream"},
                               content=data) as response:
                raw = bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw) > 100000:
                        raise providers.ProviderFailure("provider_response_too_large", uncertain=True)
                if response.status_code >= 300:
                    raise providers.ProviderFailure("template_sample_upload_rejected", uncertain=response.status_code >= 500)
                try:
                    value = json.loads(raw)
                except (ValueError, UnicodeDecodeError):
                    value = {}
                handle = value.get("h") if isinstance(value, dict) else None
                if not isinstance(handle, str) or not 1 <= len(handle) <= 2000 or any(ord(c) < 33 for c in handle):
                    raise providers.ProviderFailure("template_sample_handle_missing", uncertain=True)
                return handle
    except (httpx.HTTPError, OSError):
        raise providers.ProviderFailure("template_sample_upload_unknown", uncertain=True) from None


def phone_upload(adapter, data, info, before_part):
    before_part()
    phone = adapter["configuration"].get("phoneNumberId", "")
    if adapter["channel"] != "whatsapp" or not re.fullmatch(r"[0-9]{1,100}", phone):
        raise HTTPException(409, "template_sample_account_required")
    result = providers.request(adapter, "POST", phone + "/media", files=[
        ("messaging_product", (None, "whatsapp")),
        ("type", (None, info["mime"])),
        ("file", (info["name"], data, info["mime"])),
    ])
    identity = result.get("id")
    if not isinstance(identity, str) or not re.fullmatch(r"[0-9]{1,100}", identity):
        raise providers.ProviderFailure("template_sample_handle_missing", uncertain=True)
    return identity


def public_result(status, result):
    return {"status": status, **{k:v for k,v in result.items() if k not in {"account_version", "credential"}}}


def upload(service, auth, integration, body, transport=None):
    if not body.confirmed:
        raise HTTPException(409, "template_sample_confirmation_required")
    with service.tx(auth, recent=True) as (c, _):
        item = account(c, service.settings, integration)
        if item["Channel"] != "whatsapp" or item["RequestedStatus"] != "connected" or item["VerifiedStatus"] != "verified":
            raise HTTPException(409, "broadcast_verified_whatsapp_account_required")
    data, info = checked(body)
    transport = transport or (graph_upload if body.purpose == "review" else phone_upload)
    operation = str(body.operation_id)
    with service.tx(auth, True, recent=True) as (c, actor):
        item = account(c, service.settings, integration)
        adapter, credential = provider_account(c, service.settings, item)
        binding = (bytes(item["RowVersion"]), str(credential["SecretId"]))
        digest = bound_hash(service.settings, {
            "integration": integration, "actor": str(actor["UserId"]), "kind": body.kind,
            "name": info["name"], "sha256": hashlib.sha256(data).hexdigest(),
            "account_version": binding[0].hex(), "credential": binding[1],
            "purpose": body.purpose,
        }, "template-sample")
        prior = one(c, "SELECT RequestDigest,Status,ResultMetadata FROM crm_channels2.ProviderOperation WHERE InstitutionId=? AND OperationId=?",
                    institution(service.settings), operation)
        if prior:
            if bytes(prior["RequestDigest"]) != digest:
                raise HTTPException(409, "operation_conflict")
            return public_result(prior["Status"], json.loads(prior["ResultMetadata"]))
        c.execute("INSERT crm_channels2.ProviderOperation(InstitutionId,OperationId,ApplicationId,IntegrationId,ActorRef,Action,RequestDigest,Status,ResultMetadata,EffectKey,CreatedAt,LeaseUntil,Attempts) VALUES(?,?,?,?,?,'template_sample_upload',?,'running','{}',?,SYSUTCDATETIME(),DATEADD(second,120,SYSUTCDATETIME()),1)",
                  institution(service.settings), operation, item["ApplicationId"], integration, actor["UserId"], digest,
                  bound_hash(service.settings, operation, "template-media-intent"))

    def current():
        with service.tx(auth, recent=True) as (c, _):
            live = account(c, service.settings, integration)
            _, secret = provider_account(c, service.settings, live)
            if live["RequestedStatus"] != "connected" or live["VerifiedStatus"] != "verified" or (bytes(live["RowVersion"]), str(secret["SecretId"])) != binding:
                raise HTTPException(409, "broadcast_context_changed")

    status, result = "uncertain", {"code": "template_sample_upload_unknown"}
    try:
        handle = transport(adapter, data, info, current)
        current()
        status, result = "confirmed", {"handle" if body.purpose == "review" else "media_id": handle,
            "kind": body.kind, "name": info["name"], "size": len(data), "purpose": body.purpose,
            "operation_id": operation, "account_version": binding[0].hex(), "credential": binding[1]}
    except providers.ProviderFailure as e:
        status, result = ("uncertain" if e.uncertain else "failed"), {"code": e.code}
    except HTTPException as e:
        status, result = "failed", {"code": str(e.detail)}
    except Exception:
        pass
    with service.tx(auth, True) as (c, _):
        c.execute("UPDATE crm_channels2.ProviderOperation SET Status=?,ResultCode=?,ResultMetadata=?,CompletedAt=SYSUTCDATETIME(),LeaseUntil=NULL WHERE InstitutionId=? AND OperationId=? AND RequestDigest=? AND Status IN('running','uncertain')",
                  status, result.get("code", "template_sample_uploaded"), templates.encoded(result), institution(service.settings), operation, digest)
        if c.rowcount != 1:
            raise HTTPException(409, "template_sample_context_changed")
    return public_result(status, result)


def delivery_binding(c, settings, campaign, item, credential, definition):
    document = json.loads(campaign.get("Document", "{}"))
    if not document.get("header_media_id"):
        return
    if document.get("header_media_url") or not document.get("header_media_operation"):
        raise HTTPException(409, "broadcast_media_upload_required")
    value = one(c, "SELECT ResultMetadata FROM crm_channels2.ProviderOperation WHERE InstitutionId=? AND IntegrationId=? AND OperationId=? AND Action='template_sample_upload' AND Status='confirmed'",
                institution(settings), item["IntegrationId"], document["header_media_operation"])
    metadata = json.loads(value["ResultMetadata"]) if value else {}
    kind = next((v.get("format", "").lower() for v in json.loads(definition) if v.get("type", "").upper() == "HEADER"), "")
    if (metadata.get("purpose") != "delivery" or metadata.get("media_id") != document["header_media_id"]
        or metadata.get("account_version") != bytes(item["RowVersion"]).hex()
        or metadata.get("credential") != str(credential["SecretId"]) or metadata.get("kind") != kind):
        raise HTTPException(409, "broadcast_media_upload_required")
