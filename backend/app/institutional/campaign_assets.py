"""Bounded template uploads and public media become native C10 assets."""

import base64
import hashlib
import http.client
import ipaddress
import json
import os
import socket
import ssl
import time
from contextlib import suppress
from pathlib import Path
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, uuid4, uuid5

from fastapi import HTTPException
from fastapi.responses import FileResponse
from pydantic import Field

from app.institutional.campaigns import event, key
from app.institutional.channel_media import file_for, mark_ready
from app.institutional.channel_media import quota as native_quota
from app.institutional.db import institution, one, record_operation, replay, uid
from app.institutional.models import Strict
from app.institutional.store import transaction
from app.modules.channels.providers import ProviderFailure
from app.modules.inbox.infrastructure import media_files as files

MEDIA = {"image", "video", "audio", "document"}


class Upload(Strict):
    operation_id: str = Field(
        pattern=r"^[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$"
    )
    filename: str = Field(min_length=1, max_length=160)
    kind: str = Field(pattern="^(image|video|audio|document)$")
    content_base64: str = Field(min_length=1, max_length=6666668)


def quota(c, s, conversation):
    native_quota(c, s, conversation)
    total = c.execute(
        "SELECT (SELECT ISNULL(SUM(ISNULL(ByteLength,5000000)),0) FROM crm_channels4.MediaAsset WHERE InstitutionId=? AND State NOT IN('deleted','rejected','failed')) + (SELECT ISNULL(SUM(TRY_CONVERT(bigint,JSON_VALUE(Document,'$.size'))),0) FROM crm_campaign8.Event WHERE InstitutionId=? AND Kind='template_asset')",
        institution(s),
        institution(s),
    ).fetchval()
    if total + files.MAX_BYTES > files.TOTAL_BYTES:
        raise HTTPException(413, "media_storage_quota")


def library_file(c, s, id, actor=None):
    row = one(
        c,
        "SELECT Document,ActorId FROM crm_campaign8.Event WHERE InstitutionId=? AND EventId=? AND Kind='template_asset'",
        institution(s),
        uid(str(id)),
    )
    if not row:
        raise HTTPException(404, "campaign_asset_not_found")
    if actor and uid(str(row["ActorId"])) != uid(str(actor["UserId"])):
        shared = c.execute(
            "SELECT 1 FROM crm_campaign8.Version v CROSS APPLY OPENJSON(v.Document,'$.blocks') WITH(AssetId uniqueidentifier '$.asset_id') b WHERE v.InstitutionId=? AND v.Kind='template' AND b.AssetId=?",
            institution(s),
            id,
        ).fetchone()
        if not shared:
            raise HTTPException(404, "campaign_asset_not_found")
    v = json.loads(row["Document"])
    path = files.path(id)
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_size != v["size"]
        or hashlib.sha256(path.read_bytes()).hexdigest() != v["sha256"]
    ):
        raise HTTPException(409, "campaign_asset_unavailable")
    return v, dict(
        path=path, kind=v["kind"], mime=v["mime"], name=v["name"], size=v["size"]
    )


def upload(service, auth, body):
    from app.institutional.campaign_media import inspect

    id = str(uuid4())
    completed = False
    try:
        try:
            raw = base64.b64decode(body.content_base64, validate=True)
        except (ValueError, TypeError):
            raise HTTPException(422, "invalid_media_encoding") from None
        if not raw or len(raw) > files.MAX_BYTES:
            raise HTTPException(413, "media_size_limit")
        request = dict(
            kind=body.kind, name=body.filename, sha256=hashlib.sha256(raw).hexdigest()
        )
        with service.tx(auth) as (c, actor):
            _, old = replay(
                c,
                service.settings,
                actor["UserId"],
                body.operation_id,
                "campaign8.asset",
                "assets",
                request,
            )
            if old:
                return old
        files.path(id, ".part").write_bytes(raw)
        info = inspect(id, body.filename, body.kind)
        if info["kind"] != body.kind:
            raise HTTPException(415, "campaign_media_kind_mismatch")
        with service.tx(auth, True) as (c, actor):
            digest, old = replay(
                c,
                service.settings,
                actor["UserId"],
                body.operation_id,
                "campaign8.asset",
                "assets",
                request,
            )
            if old:
                return old
            count, total = c.execute(
                "SELECT COUNT(*),ISNULL(SUM(TRY_CONVERT(bigint,JSON_VALUE(Document,'$.size'))),0) FROM crm_campaign8.Event WHERE InstitutionId=? AND Kind='template_asset'",
                institution(service.settings),
            ).fetchone()
            other = c.execute(
                "SELECT ISNULL(SUM(ISNULL(ByteLength,5000000)),0) FROM crm_channels4.MediaAsset WHERE InstitutionId=? AND State NOT IN('deleted','rejected','failed')",
                institution(service.settings),
            ).fetchval()
            if count >= 500 or total + other + info["size"] > files.TOTAL_BYTES:
                raise HTTPException(413, "media_storage_quota")
            value = dict(
                id=id,
                kind=info["kind"],
                name=info["name"],
                mime=info["mime"],
                size=info["size"],
                sha256=bytes(info["hash"]).hex(),
            )
            event(
                c,
                service.settings,
                "template_asset",
                value,
                actor=actor["UserId"],
                event_id=id,
                source=key("template-asset", id),
            )
            result = {k: value[k] for k in ["id", "kind", "name", "size"]}
            record_operation(
                c,
                service.settings,
                actor["UserId"],
                body.operation_id,
                "campaign8.asset",
                "assets",
                digest,
                result,
            )
        completed = True
        return result
    finally:
        if not completed:
            for suffix in [".part", ".checked", ".bin"]:
                with suppress(OSError):
                    files.path(id, suffix).unlink(missing_ok=True)


def download(service, auth, id):
    with service.tx(auth) as (c, actor):
        value, info = library_file(c, service.settings, id, actor)
    return FileResponse(
        info["path"],
        media_type=info["mime"],
        filename=info["name"],
        content_disposition_type="attachment",
        headers={
            "Content-Security-Policy": "default-src 'none'; sandbox",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store",
        },
    )


def retrieve(url, destination, *, max_bytes=None):
    """No credentials, redirects, private addresses or unverified TLS destinations."""
    connection = None
    limit = files.MAX_BYTES if max_bytes is None else min(files.MAX_BYTES, max_bytes)
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").encode("idna").decode()
        if (
            parts.scheme != "https"
            or not host
            or parts.username
            or parts.password
            or parts.port not in (None, 443)
            or parts.fragment
        ):
            raise ProviderFailure("campaign_image_public_https_required")
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        if not addresses or any(
            not ipaddress.ip_address(v[4][0]).is_global for v in addresses
        ):
            raise ProviderFailure("campaign_image_public_https_required")
        connection = http.client.HTTPSConnection(
            host, timeout=12, context=ssl.create_default_context()
        )
        raw = socket.create_connection((addresses[0][4][0], 443), timeout=8)
        try:
            connection.sock = connection._context.wrap_socket(raw, server_hostname=host)
        except BaseException:
            raw.close()
            raise
        connection.request(
            "GET",
            (parts.path or "/") + ("?" + parts.query if parts.query else ""),
            headers={"Host": host, "Accept-Encoding": "identity"},
        )
        response = connection.getresponse()
        length = response.getheader("Content-Length")
        if response.status != 200:
            raise ProviderFailure("campaign_image_download_rejected")
        if (
            response.getheader("Content-Encoding", "identity") != "identity"
            or length is not None
            and (not length.isdecimal() or int(length) > limit)
        ):
            raise ProviderFailure("campaign_image_size_limit")
        total = 0
        started = time.monotonic()
        with destination.open("xb") as f:
            os.chmod(destination, 0o600)
            while True:
                chunk = response.read(65536)
                if not chunk:
                    break
                total += len(chunk)
                if total > limit or time.monotonic() - started > 30:
                    raise ProviderFailure("campaign_image_size_limit")
                f.write(chunk)
        if not total or length is not None and int(length) != total:
            raise ProviderFailure("campaign_image_incomplete")
    except (ValueError, OSError, ssl.SSLError, http.client.HTTPException):
        raise ProviderFailure("campaign_image_download_unavailable") from None
    finally:
        if connection:
            connection.close()


def source(c, s, step, index, part):
    if part.get("asset_id"):
        value, info = library_file(c, s, part["asset_id"])
        return part["asset_id"], value, info
    url = part["url"]
    link = one(
        c,
        "SELECT Document FROM crm_campaign8.Event WHERE InstitutionId=? AND StepId=? AND Kind IN('step_image','step_media') AND SourceKey=?",
        institution(s),
        step["StepId"],
        key("step-image", step["StepId"], index, url),
    )
    if not link:
        raise HTTPException(409, "campaign_image_preparation_pending")
    id = json.loads(link["Document"])["media_id"]
    value, info = file_for(c, s, id)
    return id, value, info


def attach_copy(c, s, step, index, part, message, p, actor, attempt):
    original, _, info = source(c, s, step, index, part)
    id = str(
        uuid5(
            NAMESPACE_URL,
            "CBN-P8-image-copy:"
            + str(step["StepId"])
            + ":"
            + str(index)
            + ":"
            + str(attempt),
        )
    )
    quota(c, s, str(p["ConversationId"]))
    # Copy only an already inspected immutable blob, then inspect it again under its own key.
    files.path(id, ".part").write_bytes(files.path(original).read_bytes())
    from app.institutional.campaign_media import inspect

    inspected = inspect(
        id,
        part.get("filename") or info["name"]
        if info["kind"] == "document"
        else info["name"],
        info["kind"],
    )
    c.execute(
        "INSERT crm_channels4.MediaAsset(MediaId,InstitutionId,ConversationId,MessageId,IntegrationId,UserId,SourceKind,State,FileName) VALUES(?,?,?,?,?,?,'upload','processing',?)",
        id,
        institution(s),
        p["ConversationId"],
        message,
        p["IntegrationId"],
        actor["UserId"],
        inspected["name"],
    )
    mark_ready(c, s, id, inspected)
    return id


def refresh(s, downloader=None):
    from app.institutional.campaign_chat import parts
    from app.institutional.campaign_models import next_allowed, now
    from app.institutional.campaign_runtime import guard
    from app.institutional.campaigns import enabled
    from app.institutional.channel_operations import configuration

    chosen = None
    with transaction(s, True, anonymous=True) as c:
        if not enabled(c, s) or not configuration(c, s)["OutboundEnabled"]:
            return False
        run = one(
            c,
            "SELECT TOP(1) r.*,st.StepId FROM crm_campaign8.Enrollment r JOIN crm_campaign8.Step st ON st.InstitutionId=r.InstitutionId AND st.EnrollmentId=r.EnrollmentId AND st.StepIndex=r.StepIndex WHERE r.InstitutionId=? AND r.State IN('waiting','queued') AND st.Kind='send' AND st.NativeCampaignId IS NULL AND r.DueAt<=DATEADD(second,60,SYSUTCDATETIME()) ORDER BY r.DueAt,r.EnrollmentId",
            institution(s),
        )
        if not run:
            return False
        try:
            flow, doc, p = guard(c, s, run)
            if (
                next_allowed(now(), doc["quiet_hours"]) > now()
                or not doc["steps"][run["StepIndex"]]["crm_template_id"]
            ):
                return False
            for index, part in enumerate(
                parts(
                    c,
                    s,
                    doc,
                    doc["steps"][run["StepIndex"]],
                    run["Variant"],
                    p,
                    flow["Name"],
                )
            ):
                if part["kind"] not in MEDIA:
                    continue
                try:
                    source(c, s, run, index, part)
                    continue
                except HTTPException as e:
                    if e.detail != "campaign_image_preparation_pending":
                        raise
                id = str(
                    uuid5(
                        NAMESPACE_URL,
                        "CBN-P8-image-source:" + str(run["StepId"]) + ":" + str(index),
                    )
                )
                existing = one(
                    c,
                    "SELECT State,UpdatedAt FROM crm_channels4.MediaAsset WHERE InstitutionId=? AND MediaId=?",
                    institution(s),
                    id,
                )
                if existing:
                    from datetime import timedelta

                    if existing["State"] != "failed" and not (
                        existing["State"] == "processing"
                        and existing["UpdatedAt"] < now() - timedelta(minutes=2)
                    ):
                        continue
                    c.execute(
                        "UPDATE crm_channels4.MediaAsset SET State='processing',UpdatedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND MediaId=?",
                        institution(s),
                        id,
                    )
                else:
                    quota(c, s, str(p["ConversationId"]))
                    c.execute(
                        "INSERT crm_channels4.MediaAsset(MediaId,InstitutionId,ConversationId,IntegrationId,UserId,SourceKind,State,FileName) VALUES(?,?,?,?,?,'upload','processing','campaign-image.png')",
                        id,
                        institution(s),
                        p["ConversationId"],
                        p["IntegrationId"],
                        flow["ActorId"],
                    )
                chosen = (run, index, part, id)
                break
        except HTTPException:
            return False
    if not chosen:
        return False
    run, index, part, id = chosen
    success = False
    try:
        for suffix in [".part", ".checked", ".bin"]:
            files.path(id, suffix).unlink(missing_ok=True)
        (downloader or retrieve)(part["url"], files.path(id, ".part"))
        from app.institutional.campaign_media import inspect

        name = (
            part.get("filename")
            or Path(urlsplit(part["url"]).path).name
            or "campaign-" + part["kind"]
        )
        info = inspect(id, name, part["kind"])
        if info["kind"] != part["kind"]:
            raise HTTPException(415, "campaign_media_kind_mismatch")
        with transaction(s, True, anonymous=True) as c:
            live = one(
                c,
                "SELECT * FROM crm_campaign8.Enrollment WHERE InstitutionId=? AND EnrollmentId=?",
                institution(s),
                run["EnrollmentId"],
            )
            flow, doc, p = guard(c, s, live)
            current = parts(
                c,
                s,
                doc,
                doc["steps"][live["StepIndex"]],
                live["Variant"],
                p,
                flow["Name"],
            )
            if live["StepIndex"] != run["StepIndex"] or current[index] != part:
                raise HTTPException(409, "campaign_image_context_changed")
            mark_ready(c, s, id, info)
            event(
                c,
                s,
                "step_media",
                dict(media_id=id, part_index=index, kind=part["kind"]),
                record=str(flow["RecordId"]),
                enrollment=str(run["EnrollmentId"]),
                step=str(run["StepId"]),
                source=key("step-image", run["StepId"], index, part["url"]),
            )
        success = True
        return True
    except (HTTPException, ProviderFailure, OSError) as e:
        with transaction(s, True, anonymous=True) as c:
            code = str(
                e.detail
                if isinstance(e, HTTPException)
                else e.code
                if isinstance(e, ProviderFailure)
                else "campaign_image_storage_unavailable"
            )[:64]
            c.execute(
                "UPDATE crm_channels4.MediaAsset SET State='failed',LastErrorCode=? WHERE InstitutionId=? AND MediaId=?",
                code,
                institution(s),
                id,
            )
            from app.institutional.campaign_runtime import stop

            live = one(
                c,
                "SELECT * FROM crm_campaign8.Enrollment WHERE InstitutionId=? AND EnrollmentId=?",
                institution(s),
                run["EnrollmentId"],
            )
            stop(c, s, live, code)
            c.execute(
                "UPDATE crm_campaign8.Enrollment SET State='failed',LastReason=? WHERE InstitutionId=? AND EnrollmentId=? AND State<>'uncertain'",
                code,
                institution(s),
                run["EnrollmentId"],
            )
            c.execute(
                "UPDATE crm_campaign8.Step SET State='failed',LastReason=? WHERE InstitutionId=? AND StepId=?",
                code,
                institution(s),
                run["StepId"],
            )
            event(
                c,
                s,
                "image_failed",
                {"reason": code},
                record=str(run["FlowId"]),
                enrollment=str(run["EnrollmentId"]),
                step=str(run["StepId"]),
            )
        return False
    finally:
        if not success:
            for suffix in [".part", ".checked", ".bin"]:
                with suppress(OSError):
                    files.path(id, suffix).unlink(missing_ok=True)
