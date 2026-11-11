"""Private conversation-scoped media, bounded uploads and durable retrieval work."""

import asyncio
import hashlib
import json
import os
import re
from urllib.parse import quote, unquote
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.sql_workspace import Identifier
from app.modules.inbox.infrastructure import media_files as files
from app.modules.inbox.application.service import rows

PUBLIC_COLUMNS = "MediaId AS id,State AS state,Kind AS kind,FileName AS name,ActualMime AS mime,ByteLength AS size,DurationSeconds AS duration,LastError AS error"


def verify(cursor):
    if not cursor.execute("SELECT OBJECT_ID(N'crm_channels.MediaAsset')").fetchval():
        raise HTTPException(503, "inbox_media_required")


def lookup(cursor, conversation, identifier):
    verify(cursor)
    found = rows(
        cursor.execute(
            "SELECT "
            + PUBLIC_COLUMNS
            + " FROM crm_channels.MediaAsset WHERE ConversationId=? AND MediaId=? AND State<>'deleted' AND (ExpiresAt IS NULL OR ExpiresAt>SYSUTCDATETIME())",
            conversation,
            identifier,
        )
    )
    if not found:
        raise HTTPException(404, "media_not_found")
    if found[0]["duration"] is not None:
        found[0]["duration"] = float(found[0]["duration"])
    return found[0]


def quota(cursor, conversation):
    total, own = cursor.execute(
        "SELECT COALESCE(SUM(COALESCE(ByteLength,5000000)),0),COALESCE(SUM(CASE WHEN ConversationId=? THEN COALESCE(ByteLength,5000000) ELSE 0 END),0) "
        "FROM crm_channels.MediaAsset WHERE State NOT IN('deleted','rejected','failed')",
        conversation,
    ).fetchone()
    if (
        total + files.MAX_BYTES > files.TOTAL_BYTES
        or own + files.MAX_BYTES > files.CONVERSATION_BYTES
    ):
        raise HTTPException(413, "media_storage_quota")


def attachment(
    cursor, conversation, identifier, delivery="local", channel=None, caption=""
):
    found = lookup(cursor, conversation, identifier)
    row = cursor.execute(
        "SELECT MessageId,SourceKind,ExpiresAt FROM crm_channels.MediaAsset WHERE MediaId=?",
        identifier,
    ).fetchone()
    if found["state"] != "ready" or row[0] is not None or row[1] != "upload":
        raise HTTPException(409, "media_not_ready_or_used")
    if cursor.execute(
        "SELECT CASE WHEN ExpiresAt<=SYSUTCDATETIME() THEN 1 ELSE 0 END FROM crm_channels.MediaAsset WHERE MediaId=?",
        identifier,
    ).fetchval():
        raise HTTPException(410, "media_expired")
    if not files.path(identifier).is_file():
        raise HTTPException(409, "media_content_unavailable")
    if delivery == "external" and channel not in (
        "whatsapp",
        "messenger",
        "instagram",
        "tiktok",
    ):
        raise HTTPException(409, "channel_media_not_supported")
    if delivery == "external" and channel == "instagram":
        config = json.loads(
            cursor.execute(
                "SELECT Configuration FROM crm_channels.Account WHERE Channel='instagram'"
            ).fetchval()
        )
        if config.get("instagramLogin") != "facebook" or not config.get("pageId"):
            raise HTTPException(409, "instagram_page_media_required")
        if found["kind"] == "document" and found["mime"] != "application/pdf":
            raise HTTPException(409, "channel_media_not_supported")
    if (
        delivery == "external"
        and channel == "tiktok"
        and (found["kind"] != "image" or found["size"] > 3_000_000)
    ):
        raise HTTPException(409, "tiktok_image_limit")
    if (
        delivery == "external"
        and caption
        and (
            channel in ("messenger", "instagram", "tiktok") or found["kind"] == "audio"
        )
    ):
        raise HTTPException(409, "media_caption_unsupported")
    return found


def link(cursor, conversation, identifier, message_id):
    cursor.execute(
        "UPDATE crm_channels.MediaAsset SET MessageId=?,ExpiresAt=NULL WHERE MediaId=? AND ConversationId=? AND MessageId IS NULL AND State='ready'",
        message_id,
        identifier,
        conversation,
    )
    if cursor.rowcount != 1:
        raise HTTPException(409, "media_not_ready_or_used")


def complete(cursor, identifier, lease, result):
    cursor.execute(
        "UPDATE crm_channels.MediaAsset SET State='ready',Kind=?,FileName=?,ActualMime=?,StorageKey=?,ByteLength=?,ContentHash=?,SourceHash=?,"
        "DurationSeconds=?,LeaseId=NULL,LastError=NULL WHERE MediaId=? AND LeaseId=? AND State IN('uploading','processing')",
        result["kind"],
        result["name"],
        result["mime"],
        files.path(identifier).name,
        result["size"],
        result["hash"],
        result["source_hash"],
        result["duration"],
        identifier,
        lease,
    )
    if cursor.rowcount != 1:
        files.path(identifier).unlink(missing_ok=True)
        raise HTTPException(409, "media_operation_changed")


def install_media(application):
    def require_local(request: Request):
        if request.app.state.settings.mode != "local_sql_copy":
            raise HTTPException(503, "local_sql_copy_disabled")

    router = APIRouter(
        prefix="/api/local/crm/inbox/conversations/{conversation_id}/media",
        tags=["private-inbox-media"],
        dependencies=[Depends(require_local)],
    )

    @router.put("/{media_id}")
    async def upload(
        request: Request, conversation_id: Identifier, media_id: Identifier
    ):
        workspace = request.app.state.sql_workspace
        lease = str(uuid4())
        name = files.filename(
            unquote(request.headers.get("x-crm-filename", "adjunto")[:600])
        )
        existing_hash = None
        with workspace.transaction(write=True) as cursor:
            verify(cursor)
            conversation = cursor.execute(
                "SELECT State,ControlMode FROM crm.Conversation WHERE ConversationId=?",
                conversation_id,
            ).fetchone()
            if not conversation:
                raise HTTPException(404, "conversation_not_found")
            if conversation[0] == "closed" or conversation[1] != "human":
                raise HTTPException(409, "human_open_conversation_required")
            existing = cursor.execute(
                "SELECT ConversationId,State,SourceHash,MessageId FROM crm_channels.MediaAsset WHERE MediaId=?",
                media_id,
            ).fetchone()
            if existing:
                if (
                    str(existing[0]).lower() != conversation_id.lower()
                    or existing[3] is not None
                ):
                    raise HTTPException(409, "media_operation_changed")
                if existing[1] == "ready":
                    existing_hash = bytes(existing[2])
                elif existing[1] not in ("failed", "rejected"):
                    raise HTTPException(409, "media_operation_in_progress")
                else:
                    quota(cursor, conversation_id)
                    cursor.execute(
                        "UPDATE crm_channels.MediaAsset SET State='uploading',LeaseId=?,ExpiresAt=DATEADD(hour,1,SYSUTCDATETIME()) WHERE MediaId=?",
                        lease,
                        media_id,
                    )
            else:
                quota(cursor, conversation_id)
                cursor.execute(
                    "INSERT crm_channels.MediaAsset(MediaId,ConversationId,SourceKind,State,FileName,LeaseId,ExpiresAt) VALUES(?,?,'upload','uploading',?,?,DATEADD(hour,1,SYSUTCDATETIME()))",
                    media_id,
                    conversation_id,
                    name,
                    lease,
                )
        count = 0
        digest = hashlib.sha256()
        confirmed = False
        try:
            # A replay compares source bytes without rewriting an existing ready file.
            handle = (
                None if existing_hash else open(files.path(media_id, ".part"), "xb")
            )
            try:
                if handle:
                    os.chmod(handle.name, 0o600)
                async for chunk in request.stream():
                    count += len(chunk)
                    if count > files.MAX_BYTES:
                        raise HTTPException(413, "media_size_limit")
                    digest.update(chunk)
                    if handle:
                        handle.write(chunk)
            finally:
                if handle:
                    handle.close()
            if not count:
                raise HTTPException(415, "media_empty")
            if existing_hash:
                if digest.digest() != existing_hash:
                    raise HTTPException(409, "media_operation_changed")
            else:
                inspection = asyncio.create_task(
                    asyncio.to_thread(files.inspect_file, media_id, name)
                )
                try:
                    result = await asyncio.shield(inspection)
                except asyncio.CancelledError:
                    await inspection
                    raise
                with workspace.transaction(write=True) as cursor:
                    complete(cursor, media_id, lease, result)
                confirmed = True
            with workspace.transaction() as cursor:
                return JSONResponse(
                    lookup(cursor, conversation_id, media_id),
                    headers={"Cache-Control": "no-store"},
                )
        except BaseException as error:
            if not existing_hash and not confirmed:
                for suffix in (".part", ".checked", ".bin"):
                    files.path(media_id, suffix).unlink(missing_ok=True)
                with workspace.transaction(write=True) as cursor:
                    cursor.execute(
                        "UPDATE crm_channels.MediaAsset SET State='rejected',LastError=?,LeaseId=NULL WHERE MediaId=? AND LeaseId=?",
                        error.detail
                        if isinstance(error, HTTPException)
                        else "media_upload_failed",
                        media_id,
                        lease,
                    )
            raise

    @router.get("/{media_id}")
    def metadata(request: Request, conversation_id: Identifier, media_id: Identifier):
        with request.app.state.sql_workspace.transaction() as cursor:
            return JSONResponse(
                lookup(cursor, conversation_id, media_id),
                headers={"Cache-Control": "no-store"},
            )

    @router.delete("/{media_id}")
    def discard(request: Request, conversation_id: Identifier, media_id: Identifier):
        with request.app.state.sql_workspace.transaction(write=True) as cursor:
            lookup(cursor, conversation_id, media_id)
            row = cursor.execute(
                "SELECT MessageId,SourceKind FROM crm_channels.MediaAsset WHERE MediaId=?",
                media_id,
            ).fetchone()
            if row[0] is not None or row[1] != "upload":
                raise HTTPException(409, "media_already_attached")
            cursor.execute(
                "UPDATE crm_channels.MediaAsset SET State='deleted',LeaseId=NULL WHERE MediaId=?",
                media_id,
            )
        for suffix in (".part", ".checked", ".bin"):
            files.path(media_id, suffix).unlink(missing_ok=True)
        return JSONResponse({"discarded": True}, headers={"Cache-Control": "no-store"})

    @router.get("/{media_id}/content")
    async def content(
        request: Request, conversation_id: Identifier, media_id: Identifier
    ):
        with request.app.state.sql_workspace.transaction() as cursor:
            item = lookup(cursor, conversation_id, media_id)
            if item["state"] != "ready":
                raise HTTPException(409, "media_not_ready_or_used")
        source = files.path(media_id)
        if (
            not source.is_file()
            or source.is_symlink()
            or source.stat().st_size != item["size"]
        ):
            raise HTTPException(404, "media_content_unavailable")
        size = item["size"]
        start, end, status = 0, size - 1, 200
        requested = request.headers.get("range")
        if requested:
            match = (
                re.fullmatch(r"bytes=(\d*)-(\d*)", requested[:120])
                if len(requested) <= 120
                else None
            )
            if not match or not any(match.groups()):
                raise HTTPException(
                    416,
                    "media_range_invalid",
                    headers={"Content-Range": f"bytes */{size}"},
                )
            left, right = match.groups()
            if left:
                start, end = int(left), min(int(right), size - 1) if right else size - 1
            else:
                length = int(right)
                if not length:
                    raise HTTPException(
                        416,
                        "media_range_invalid",
                        headers={"Content-Range": f"bytes */{size}"},
                    )
                start = max(0, size - length)
            if start >= size or start > end:
                raise HTTPException(
                    416,
                    "media_range_invalid",
                    headers={"Content-Range": f"bytes */{size}"},
                )
            status = 206

        async def chunks():
            with source.open("rb") as handle:
                handle.seek(start)
                remaining = end - start + 1
                while remaining and not await request.is_disconnected():
                    value = handle.read(min(65536, remaining))
                    if not value:
                        break
                    remaining -= len(value)
                    yield value

        disposition = "attachment" if item["kind"] == "document" else "inline"
        headers = {
            "Cache-Control": "no-store",
            "Accept-Ranges": "bytes",
            "Content-Length": str(end - start + 1),
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": f"{disposition}; filename*=UTF-8''{quote(item['name'], safe='')}",
        }
        if status == 206:
            headers["Content-Range"] = f"bytes {start}-{end}/{size}"
        return StreamingResponse(
            chunks(), status_code=status, media_type=item["mime"], headers=headers
        )

    application.include_router(router)


def record_incoming(cursor, account, identity_id, conversation, message_id, payload):
    verify(cursor)
    channel = account["channel"]
    reference, name, kind = None, "adjunto", None
    state, error = "pending", None
    if channel == "whatsapp":
        kind = payload.get("type")
        if kind not in ("image", "audio", "document"):
            return
        value = payload.get(kind, {})
        reference = {"id": str(value.get("id", ""))}
        name = value.get("filename") or kind
    elif channel in ("messenger", "instagram"):
        values = payload.get("message", {}).get("attachments", [])
        if not values:
            return
        item = values[0]
        kind = {"image": "image", "audio": "audio", "file": "document"}.get(
            item.get("type")
        )
        reference = {"url": item.get("payload", {}).get("url", "")}
        if not kind or len(values) != 1:
            state, error = "failed", "media_attachment_type_unavailable"
            kind = None
    elif channel == "tiktok" and payload.get("type") not in ("text", "TEXT", None):
        image = payload.get("image", {})
        if (
            str(payload.get("type")).upper() == "IMAGE"
            and isinstance(image, dict)
            and image.get("media_id")
        ):
            kind = "image"
            reference = {
                "business_id": account["configuration"].get("accountId"),
                "conversation_id": str(payload.get("conversation_id", "")),
                "message_id": str(payload.get("message_id", "")),
                "media_id": str(image["media_id"]),
                "media_type": "IMAGE",
            }
        else:
            reference, state, error = {}, "failed", "channel_media_not_supported"
    else:
        return
    reference["asset"] = {
        key: account["configuration"].get(key, "")
        for key in (
            "phoneNumberId",
            "wabaId",
            "pageId",
            "accountId",
            "appId",
            "instagramLogin",
        )
    }
    if state == "pending":
        try:
            quota(cursor, conversation)
        except HTTPException:
            state, error = "failed", "media_storage_quota"
    cursor.execute(
        "INSERT crm_channels.MediaAsset(MediaId,ConversationId,MessageId,IdentityId,Channel,SourceKind,State,Kind,FileName,ProviderReference,LastError) "
        "VALUES(?,?,?,?,?,'provider',?,?,?,?,?)",
        str(uuid4()),
        conversation,
        message_id,
        identity_id,
        channel,
        state,
        kind,
        files.filename(name),
        json.dumps(reference),
        error,
    )


def cleanup(workspace):
    with workspace.transaction(write=True) as cursor:
        verify(cursor)
        stale = cursor.execute(
            "SELECT MediaId FROM crm_channels.MediaAsset WHERE SourceKind='upload' AND MessageId IS NULL "
            "AND State<>'deleted' AND ExpiresAt<SYSUTCDATETIME()"
        ).fetchall()
        for row in stale:
            cursor.execute(
                "UPDATE crm_channels.MediaAsset SET State='deleted',LeaseId=NULL WHERE MediaId=? AND MessageId IS NULL",
                str(row[0]),
            )
            for suffix in (".part", ".checked", ".bin"):
                files.path(row[0], suffix).unlink(missing_ok=True)
    # Remove only unreferenced expired temporary files; never confirmed message assets.
    import time

    with workspace.transaction() as cursor:
        known = {
            str(row[0]).replace("-", "").lower()
            for row in cursor.execute(
                "SELECT MediaId FROM crm_channels.MediaAsset WHERE State NOT IN('deleted','rejected','failed')"
            ).fetchall()
        }
    for candidate in files.root().iterdir():
        if (
            candidate.is_file()
            and not candidate.is_symlink()
            and candidate.stem not in known
            and time.time() - candidate.stat().st_mtime > 3600
        ):
            candidate.unlink(missing_ok=True)


def retrieve_one(application):
    from app.modules.inbox.infrastructure.media_remote import retrieve
    from app.modules.channels.providers import ProviderFailure

    workspace = application.state.sql_workspace
    lease = str(uuid4())
    with workspace.transaction(write=True) as cursor:
        verify(cursor)
        cursor.execute(
            "UPDATE crm_channels.MediaAsset SET State='pending',LeaseId=NULL WHERE State='processing' AND DueAt<SYSUTCDATETIME()"
        )
        row = cursor.execute(
            ";WITH candidate AS(SELECT TOP(1) * FROM crm_channels.MediaAsset WITH(UPDLOCK,READPAST,ROWLOCK) WHERE State='pending' AND DueAt<=SYSUTCDATETIME() ORDER BY CreatedAt) "
            "UPDATE candidate SET State='processing',Attempts=Attempts+1,LeaseId=?,DueAt=DATEADD(second,180,SYSUTCDATETIME()) "
            "OUTPUT inserted.MediaId,inserted.Channel,inserted.ProviderReference,inserted.FileName,inserted.Attempts,inserted.IdentityId,inserted.ConversationId",
            lease,
        ).fetchone()
        if not row:
            return False
        identifier, channel, reference, name, attempts, identity_id, conversation = row
        identifier = str(identifier)
        account = application.state.channel_store.get(cursor, channel, True)
    try:
        reference = json.loads(reference)
        with workspace.transaction() as cursor:
            identity = cursor.execute(
                "SELECT 1 FROM crm_channels.ExternalIdentity WHERE IdentityId=? AND ConversationId=? AND Channel=?",
                str(identity_id),
                str(conversation),
                channel,
            ).fetchone()
            if not identity or reference.get("asset") != {
                key: account["configuration"].get(key, "")
                for key in (
                    "phoneNumberId",
                    "wabaId",
                    "pageId",
                    "accountId",
                    "appId",
                    "instagramLogin",
                )
            }:
                raise ProviderFailure("media_account_scope_changed")
        retrieve(account, reference, files.path(identifier, ".part"))
        result = files.inspect_file(identifier, name)
        with workspace.transaction(write=True) as cursor:
            current = application.state.channel_store.get(cursor, channel)
            if current["revision"] != account["revision"]:
                raise ProviderFailure("channel_configuration_changed", retry=True)
            complete(cursor, identifier, lease, result)
    except Exception as error:
        code = (
            error.code
            if isinstance(error, ProviderFailure)
            else error.detail
            if isinstance(error, HTTPException)
            else "media_download_failed"
        )
        retry = isinstance(error, ProviderFailure) and error.retry and attempts < 5
        with workspace.transaction(write=True) as cursor:
            cursor.execute(
                "UPDATE crm_channels.MediaAsset SET State=?,LeaseId=NULL,LastError=?,DueAt=DATEADD(second,?,SYSUTCDATETIME()) WHERE MediaId=? AND LeaseId=?",
                "pending" if retry else "failed",
                code,
                min(300, 2**attempts),
                identifier,
                lease,
            )
        for suffix in (".part", ".checked", ".bin"):
            files.path(identifier, suffix).unlink(missing_ok=True)
    return True
