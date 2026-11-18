"""Account-bound media using the existing bounded inspectors and pinned downloads."""

import base64
import hashlib
import json
import warnings
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import Field

from app.institutional import postgres_queue
from app.institutional.auth import authorize
from app.institutional import campaign_media
from app.institutional.channel_operations import account, configuration
from app.institutional.channel_provider import provider_account
from app.institutional.channel_text import sql_text
from app.institutional.db import institution, one, record_operation, replay, uid
from app.institutional.models import Strict
from app.institutional.store import transaction
from app.modules.inbox.infrastructure import media_files as files
from app.modules.inbox.infrastructure.media_remote import retrieve


class Upload(Strict):
    operation_id: str
    conversation_id: str
    filename: str = Field(min_length=1, max_length=160)
    content_base64: str = Field(min_length=1, max_length=6_666_668)
    kind: Literal["video"] | None = None


STICKER_MAX = 100_000
ANIMATED_STICKER_MAX = 500_000


def inspect_sticker(identity, name, *, incoming=False):
    from PIL import Image, UnidentifiedImageError

    source, output = files.path(identity, ".part"), files.path(identity, ".checked")
    if not files.INSPECTION_SLOTS.acquire(blocking=False):
        raise HTTPException(429, "media_inspection_busy")
    try:
        raw = source.read_bytes()
        if not 0 < len(raw) <= ANIMATED_STICKER_MAX:
            raise HTTPException(413, "media_sticker_limit")
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(source, formats=("WEBP",)) as image:
                if image.size != (512, 512):
                    raise HTTPException(415, "media_sticker_invalid")
                limit = ANIMATED_STICKER_MAX if incoming or image.is_animated else STICKER_MAX
                if len(raw) > limit:
                    raise HTTPException(413, "media_sticker_limit")
                if image.is_animated:
                    if image.n_frames > 600:
                        raise HTTPException(415, "media_sticker_invalid")
                    duration = 0
                    for frame in range(image.n_frames):
                        image.seek(frame)
                        image.load()
                        if not incoming:
                            frame_duration = image.info.get("duration", 0)
                            duration += frame_duration
                            if frame_duration < 8 or duration > 10_000:
                                raise HTTPException(415, "media_sticker_invalid")
                    output.write_bytes(raw)
                else:
                    image.load()
                    image.convert("RGBA").save(output, format="WEBP", quality=78)
        clean = output.read_bytes()
        if len(clean) > limit:
            raise HTTPException(413, "media_sticker_limit")
        output.chmod(0o600)
        output.replace(files.path(identity))
        return {
            "kind": "image", "mime": "image/webp", "size": len(clean),
            "name": files.filename(Path(name).stem) + ".webp",
            "hash": hashlib.sha256(clean).digest(),
        }
    except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError,
            Image.DecompressionBombWarning):
        raise HTTPException(415, "media_sticker_invalid") from None
    finally:
        source.unlink(missing_ok=True)
        output.unlink(missing_ok=True)
        files.INSPECTION_SLOTS.release()


def inspect_attachment(identity, name, kind=None, *, incoming=False):
    suffix = Path(name).suffix.lower()
    if kind == "sticker" or suffix == ".webp":
        return inspect_sticker(identity, name, incoming=incoming)
    if kind == "video":
        return campaign_media.inspect(identity, name, "video")
    return files.inspect_file(identity, name)


def quota(c, settings, conversation):
    total, own = c.execute(
        (
            "SELECT ISNULL(SUM(ISNULL(ByteLength,5000000)),0),ISNULL(SUM("
            "CASE WHEN ConversationId=? THEN ISNULL(ByteLength,5000000) E"
            "LSE 0 END),0) FROM crm_channels4.MediaAsset WHERE Institutio"
            "nId=? AND State NOT IN('deleted','rejected','failed')"
        ),
        conversation,
        institution(settings),
    ).fetchone()
    if (
        total + files.MAX_BYTES > files.TOTAL_BYTES
        or own + files.MAX_BYTES > files.CONVERSATION_BYTES
    ):
        raise HTTPException(413, "media_storage_quota")


def mark_ready(c, settings, identity, info, reference=None):
    info["name"] = (
        sql_text(Path(info["name"]).stem, 140) + Path(info["name"]).suffix[:10]
    )
    reference = dict(reference or {})
    if info["kind"] == "audio":
        reference["durationSeconds"] = max(1, round(info["duration"]))
    c.execute(
        (
            "UPDATE crm_channels4.MediaAsset SET State='ready',Kind=?,Act"
            "ualMime=?,FileName=?,StorageKey=?,ByteLength=?,ContentHash=?"
            ",ProviderReference=?"
            ",LastErrorCode=NULL,UpdatedAt=SYSUTCDATETIME() WHERE Institu"
            "tionId=? AND MediaId=?"
        ),
        info["kind"],
        info["mime"],
        info["name"],
        files.path(identity).name,
        info["size"],
        info["hash"],
        json.dumps(reference),
        institution(settings),
        identity,
    )


def file_for(c, settings, identity, *, conversation=None):
    value = one(
        c,
        (
            "SELECT * FROM crm_channels4.MediaAsset WHERE InstitutionId=?"
            " AND MediaId=? AND State='ready' AND (ExpiresAt IS NULL OR E"
            "xpiresAt>SYSUTCDATETIME())"
        ),
        institution(settings),
        uid(identity),
    )
    if (
        not value
        or conversation
        and str(value["ConversationId"]).lower() != uid(conversation)
    ):
        raise HTTPException(404, "media_not_found")
    source = files.path(identity)
    if (
        value["StorageKey"] != source.name
        or not source.is_file()
        or hashlib.sha256(source.read_bytes()).digest() != bytes(value["ContentHash"])
    ):
        raise HTTPException(409, "media_content_unavailable")
    if (
        value["MessageId"]
        and not c.execute(
            "SELECT 1 FROM crm.Message WHERE MessageId=? AND ConversationId=?",
            value["MessageId"],
            value["ConversationId"],
        ).fetchone()
    ):
        raise HTTPException(409, "media_message_mismatch")
    if (
        value["IdentityId"]
        and not c.execute(
            (
                "SELECT 1 FROM crm_channels2.ExternalIdentity WHERE Instituti"
                "onId=? AND IntegrationId=? AND IdentityId=? AND Conversation"
                "Id=?"
            ),
            institution(settings),
            value["IntegrationId"],
            value["IdentityId"],
            value["ConversationId"],
        ).fetchone()
    ):
        raise HTTPException(409, "media_identity_mismatch")
    return value, {
        "path": source,
        "kind": value["Kind"],
        "mime": value["ActualMime"],
        "name": value["FileName"],
        "size": value["ByteLength"],
    }


def attach(c, settings, identity, conversation, message, actor, integration=None):
    value, media = file_for(c, settings, identity, conversation=conversation)
    if (
        value["SourceKind"] != "upload"
        or str(value["UserId"]).lower() != actor
        or value["MessageId"] is not None
    ):
        raise HTTPException(409, "media_not_owned_or_already_used")
    c.execute(
        (
            "UPDATE crm_channels4.MediaAsset SET MessageId=?,IntegrationI"
            "d=?,ExpiresAt=NULL,UpdatedAt=SYSUTCDATETIME() WHERE Institut"
            "ionId=? AND MediaId=? AND MessageId IS NULL"
        ),
        message,
        integration,
        institution(settings),
        identity,
    )
    if c.rowcount != 1:
        raise HTTPException(409, "media_already_used")
    return media


def register_incoming(c, settings, item, effect, linked, message):
    provider = effect["provider"]
    if item["Channel"] == "whatsapp":
        kind = provider.get("type")
        reference = (
            provider.get(kind)
            if kind in {"image", "audio", "document", "video", "sticker"}
            else None
        )
    elif item["Channel"] in {"instagram", "messenger"}:
        attachments = (provider.get("message") or {}).get("attachments") or []
        first = attachments[0] if attachments else {}
        kind, reference = first.get("type"), first.get("payload")
    else:
        return  # TikTok download references require the approved Business API schema.
    if not isinstance(reference, dict) or kind not in {
        "image",
        "audio",
        "document",
        "video",
        "sticker",
    }:
        return
    error = None
    try:
        quota(c, settings, str(linked["ConversationId"]))
    except HTTPException as failure:
        if failure.detail != "media_storage_quota":
            raise
        error = failure.detail
    c.execute(
        (
            "INSERT crm_channels4.MediaAsset(MediaId,InstitutionId,Integr"
            "ationId,IdentityId,ConversationId,MessageId,SourceKind,State"
            ",Kind,FileName,ProviderReference,LastErrorCode) "
            "VALUES(?,?,?,?,?,?,'provider',?,?,?,?,?)"
        ),
        str(uuid4()),
        institution(settings),
        item["IntegrationId"],
        linked["IdentityId"],
        linked["ConversationId"],
        message,
        "failed" if error else "pending",
        "image" if kind == "sticker" else kind,
        "sticker.webp" if kind == "sticker" else
        "nota-de-voz.ogg" if kind == "audio" and reference.get("voice") is True else
        sql_text(files.filename(reference.get("filename") or "adjunto"), 160),
        json.dumps(reference),
        error,
    )


class Media:
    def __init__(self, settings):
        self.settings = settings

    def upload(self, authority, body):
        identity = str(uuid4())
        completed = False
        try:
            with transaction(self.settings, True, anonymous=True) as c:
                actor = authorize(c, self.settings, authority, "inbox.write")
                conversation = uid(body.conversation_id)
                if not c.execute(
                    (
                        "SELECT 1 FROM crm.Conversation WHERE ConversationId=? AND St"
                        "ate<>'closed' AND ControlMode='human'"
                    ),
                    conversation,
                ).fetchone():
                    raise HTTPException(409, "human_open_conversation_required")
                try:
                    raw = base64.b64decode(body.content_base64, validate=True)
                except (ValueError, TypeError):
                    raise HTTPException(422, "invalid_media_encoding") from None
                if not raw or len(raw) > files.MAX_BYTES:
                    raise HTTPException(413, "media_size_limit")
                payload = {
                    "conversation": conversation,
                    "name": body.filename,
                    "hash": hashlib.sha256(raw).hexdigest(),
                    **({"kind": body.kind} if body.kind else {}),
                }
                digest, prior = replay(
                    c,
                    self.settings,
                    actor["UserId"],
                    body.operation_id,
                    "media.upload",
                    conversation,
                    payload,
                )
                if prior:
                    return prior
                quota(c, self.settings, conversation)
                c.execute(
                    (
                        "INSERT crm_channels4.MediaAsset(MediaId,InstitutionId,Conver"
                        "sationId,UserId,SourceKind,State,FileName,ExpiresAt) VALUES("
                        "?,?,?,?,'upload','processing',?,DATEADD(hour,24,SYSUTCDATETI"
                        "ME()))"
                    ),
                    identity,
                    institution(self.settings),
                    conversation,
                    actor["UserId"],
                    sql_text(files.filename(body.filename), 160),
                )
                with files.path(identity, ".part").open("xb") as handle:
                    handle.write(raw)
                info = inspect_attachment(identity, body.filename, body.kind)
                mark_ready(c, self.settings, identity, info)
                result = {
                    "id": identity,
                    "name": info["name"],
                    "kind": info["kind"],
                    "mime": info["mime"],
                    "state": "ready",
                    "size": info["size"],
                }
                record_operation(
                    c,
                    self.settings,
                    actor["UserId"],
                    body.operation_id,
                    "media.upload",
                    conversation,
                    digest,
                    result,
                )
            completed = True
            return result
        finally:
            if not completed:
                for suffix in [".part", ".checked", ".bin"]:
                    files.path(identity, suffix).unlink(missing_ok=True)

    def download(self, authority, identity):
        with transaction(self.settings, anonymous=True) as c:
            authorize(c, self.settings, authority, "inbox.read")
            value, media = file_for(c, self.settings, identity)
            if value["MessageId"] is None:
                actor = authorize(c, self.settings, authority)
                if str(value["UserId"]).lower() != actor["UserId"]:
                    raise HTTPException(404, "media_not_found")
        return FileResponse(
            media["path"],
            media_type=media["mime"],
            filename=media["name"],
            content_disposition_type="attachment",
            headers={
                "Content-Security-Policy": "default-src 'none'; sandbox",
                "X-Content-Type-Options": "nosniff",
            },
        )


class MediaWorker:
    def __init__(self, settings, downloader=None):
        self.settings = settings
        self.downloader = downloader or retrieve

    def once(self):
        with transaction(self.settings, True, anonymous=True) as c:
            config = configuration(c, self.settings)
            if not config["IngressEnabled"] or not config["ModuleEnabled"]:
                return False
            inst = institution(self.settings)
            value = postgres_queue.media(c, inst) if getattr(self.settings, "postgres_profile", False) else one(
                c,
                (
                    "SELECT TOP(1) m.* FROM crm_channels4.MediaAsset m JOIN crm_c"
                    "hannels2.Integration i ON i.InstitutionId=m.InstitutionId AN"
                    "D i.IntegrationId=m.IntegrationId WHERE m.InstitutionId=? AN"
                    "D m.SourceKind='provider' AND m.State='pending' AND i.Reques"
                    "tedStatus='connected' AND i.VerifiedStatus='verified' ORDER "
                    "BY m.CreatedAt,m.MediaId"
                ),
                inst,
            )
            if not value:
                return False
            item = account(c, self.settings, str(value["IntegrationId"]))
            if item["RequestedStatus"] != "connected":
                return False
            adapter, secret = provider_account(c, self.settings, item)
            c.execute(
                (
                    "UPDATE crm_channels4.MediaAsset SET State='processing',Updat"
                    "edAt=SYSUTCDATETIME() WHERE InstitutionId=? AND MediaId=?"
                ),
                institution(self.settings),
                value["MediaId"],
            )
        identity = str(value["MediaId"])
        try:
            reference = json.loads(value["ProviderReference"])
            self.downloader(
                adapter,
                reference,
                files.path(identity, ".part"),
            )
            info = inspect_attachment(
                identity, value["FileName"], value["Kind"], incoming=True,
            )
            with transaction(self.settings, True, anonymous=True) as c:
                mark_ready(c, self.settings, identity, info, reference)
                c.execute("UPDATE crm_workspace.State SET Revision=Revision+1 WHERE StateId=1")
        except Exception:
            for suffix in [".part", ".checked", ".bin"]:
                files.path(identity, suffix).unlink(missing_ok=True)
            with transaction(self.settings, True, anonymous=True) as c:
                c.execute(
                    (
                        "UPDATE crm_channels4.MediaAsset SET State='failed',LastError"
                        "Code='media_download_or_inspection_failed',UpdatedAt=SYSUTCD"
                        "ATETIME() WHERE InstitutionId=? AND MediaId=?"
                    ),
                    institution(self.settings),
                    value["MediaId"],
                )
        return True


def install(app, settings):
    service = Media(settings)

    @app.post("/api/institution/media/upload")
    def upload(request: Request, body: Upload):
        return service.upload(request.state.authority, body)

    @app.get("/api/institution/media/{identity}")
    def download(request: Request, identity: str):
        return service.download(request.state.authority, uid(identity))
