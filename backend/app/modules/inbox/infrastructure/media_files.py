"""Private bounded file inspection and storage; no application/provider secrets."""

import hashlib
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import threading
import warnings
import zipfile
from pathlib import Path
from uuid import UUID
from xml.etree import ElementTree

from fastapi import HTTPException

MAX_BYTES = 5_000_000
TOTAL_BYTES = 250_000_000
CONVERSATION_BYTES = 50_000_000
INSPECTION_SLOTS = threading.BoundedSemaphore(2)


def root():
    folder = Path(os.environ.get("CRM_AI_STATE_DIR", ".local")) / "inbox-media"
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    return folder.resolve()


def path(identifier, suffix=".bin"):
    return root() / (UUID(str(identifier)).hex + suffix)


def filename(value):
    value = str(value).replace("\\", "/").split("/")[-1]
    return (
        re.sub(r'[\x00-\x1f\x7f<>:"/\\|?*]', "_", value).strip(" .")[:140] or "adjunto"
    )


def inspect_file(identifier, name):
    if not INSPECTION_SLOTS.acquire(blocking=False):
        raise HTTPException(429, "media_inspection_busy")
    try:
        return inspect_content(identifier, name)
    finally:
        INSPECTION_SLOTS.release()


def inspect_content(identifier, name):
    source = path(identifier, ".part")
    data = source.read_bytes()
    if not data or len(data) > MAX_BYTES:
        raise HTTPException(413, "media_size_limit")
    source_hash = hashlib.sha256(data).digest()
    output = path(identifier, ".checked")
    duration = None
    try:
        if data.startswith((b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff")):
            from PIL import Image, ImageOps, UnidentifiedImageError

            Image.MAX_IMAGE_PIXELS = 16_000_000
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("error", Image.DecompressionBombWarning)
                    with Image.open(io.BytesIO(data), formats=("JPEG", "PNG")) as image:
                        image.verify()
                    with Image.open(io.BytesIO(data), formats=("JPEG", "PNG")) as image:
                        image.load()
                        clean = ImageOps.exif_transpose(image)
                        if image.format == "PNG":
                            clean.convert("RGBA").save(output, format="PNG")
                            mime, extension = "image/png", ".png"
                        else:
                            clean.convert("RGB").save(output, format="JPEG", quality=90)
                            mime, extension = "image/jpeg", ".jpg"
                kind = "image"
            except (
                UnidentifiedImageError,
                OSError,
                ValueError,
                Image.DecompressionBombWarning,
                Image.DecompressionBombError,
            ):
                raise HTTPException(415, "media_image_invalid") from None
        elif data.startswith(b"%PDF-"):
            inspect_pdf(source)
            output.write_bytes(data)
            kind, mime, extension = "document", "application/pdf", ".pdf"
        elif data.startswith(b"PK\x03\x04"):
            mime, extension = inspect_office(data)
            output.write_bytes(data)
            kind = "document"
        elif Path(name).suffix.lower() == ".txt":
            try:
                content = data.decode("utf-8-sig")
                if "\x00" in content or re.search(
                    r"<\s*(!doctype|html|svg|script)\b", content, re.I
                ):
                    raise ValueError()
            except (UnicodeError, ValueError):
                raise HTTPException(415, "media_document_invalid") from None
            output.write_bytes(data)
            kind, mime, extension = "document", "text/plain", ".txt"
        else:
            audio_magic = data.startswith(
                (b"OggS", b"ID3", b"RIFF", b"fLaC", b"\x1aE\xdf\xa3")
            ) or (
                len(data) > 12
                and (data[4:8] == b"ftyp" or data[0] == 255 and data[1] & 224 == 224)
            )
            if not audio_magic:
                raise HTTPException(415, "media_type_unsupported")
            probe = audio_probe(source)
            if (
                len(probe.get("streams", [])) != 1
                or probe["streams"][0].get("codec_type") != "audio"
            ):
                raise HTTPException(415, "media_audio_invalid")
            if not shutil.which("ffmpeg"):
                raise HTTPException(503, "media_inspector_unavailable")
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-nostdin",
                    "-v",
                    "error",
                    "-threads",
                    "1",
                    "-protocol_whitelist",
                    "file,pipe",
                    "-format_whitelist",
                    "mp3,ogg,wav,matroska,webm,mov,flac,aac,amr",
                    "-i",
                    str(source),
                    "-map",
                    "0:a:0",
                    "-vn",
                    "-sn",
                    "-dn",
                    "-map_metadata",
                    "-1",
                    "-c:a",
                    "libopus",
                    "-b:a",
                    "48k",
                    "-ac",
                    "1",
                    "-ar",
                    "48000",
                    "-t",
                    "301",
                    "-fs",
                    str(MAX_BYTES + 1),
                    "-f",
                    "ogg",
                    "-y",
                    str(output),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=25,
                check=False,
            )
            if result.returncode or not output.exists():
                raise HTTPException(415, "media_audio_invalid")
            probe = audio_probe(output)
            duration = float(probe.get("format", {}).get("duration", 0))
            if not math.isfinite(duration) or not 0 < duration <= 300:
                raise HTTPException(413, "media_audio_duration_limit")
            kind, mime, extension = "audio", "audio/ogg", ".ogg"
        size = output.stat().st_size
        if not 0 < size <= MAX_BYTES:
            raise HTTPException(413, "media_size_limit")
        final = path(identifier)
        os.chmod(output, 0o600)
        os.replace(output, final)
        return {
            "kind": kind,
            "mime": mime,
            "size": size,
            "duration": duration,
            "name": filename(Path(name).stem)[:120] + extension,
            "hash": hashlib.sha256(final.read_bytes()).digest(),
            "source_hash": source_hash,
        }
    except (subprocess.TimeoutExpired, OSError, ValueError):
        raise HTTPException(415, "media_inspection_failed") from None
    finally:
        source.unlink(missing_ok=True)
        output.unlink(missing_ok=True)


def inspect_pdf(source):
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).with_name("pdf_inspector.py")),
                str(source),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise HTTPException(415, "media_document_limit") from None
    if result.returncode:
        code = {
            2: "media_document_active",
            3: "media_document_invalid",
            5: "media_inspector_unavailable",
        }.get(result.returncode, "media_document_limit")
        raise HTTPException(503 if result.returncode == 5 else 415, code)


def audio_probe(source):
    if not shutil.which("ffprobe"):
        raise HTTPException(503, "media_inspector_unavailable")
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-max_alloc",
            "67108864",
            "-protocol_whitelist",
            "file,pipe",
            "-format_whitelist",
            "mp3,ogg,wav,matroska,webm,mov,flac,aac,amr",
            "-show_entries",
            "stream=codec_name,codec_type,channels:format=format_name,duration",
            "-of",
            "json",
            str(source),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=10,
        check=False,
    )
    if result.returncode or len(result.stdout) > 16000:
        raise HTTPException(415, "media_audio_invalid")
    return json.loads(result.stdout)


def inspect_office(data):
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            items = archive.infolist()
            if len(items) > 2000 or sum(item.file_size for item in items) > 30_000_000:
                raise ValueError()
            names = set()
            for item in items:
                name = item.filename.lower()
                if (
                    name in names
                    or ".." in name.split("/")
                    or name.startswith(("/", "\\"))
                    or item.flag_bits & 1
                ):
                    raise ValueError()
                names.add(name)
                if (
                    item.file_size > 10_000_000
                    or item.file_size > max(1, item.compress_size) * 100
                ):
                    raise ValueError()
                if any(
                    part in name
                    for part in ("vba", "activex", "embeddings/", "externallinks/")
                ):
                    raise ValueError()
                if name.endswith((".exe", ".js", ".html", ".svg", ".bin")):
                    raise ValueError()
                if name.endswith((".xml", ".rels")):
                    value = archive.read(item)
                    if (
                        re.search(rb"<!\s*(DOCTYPE|ENTITY)", value, re.I)
                        or b"macroenabled" in value.lower()
                    ):
                        raise ValueError()
                    parsed = ElementTree.fromstring(value)
                    if any(
                        element.attrib.get("TargetMode", "").lower() == "external"
                        for element in parsed.iter()
                    ):
                        raise ValueError()
            if "[content_types].xml" not in names:
                raise ValueError()
            for marker, mime, extension in (
                (
                    "word/document.xml",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    ".docx",
                ),
                (
                    "xl/workbook.xml",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    ".xlsx",
                ),
                (
                    "ppt/presentation.xml",
                    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    ".pptx",
                ),
            ):
                if marker in names:
                    return mime, extension
    except (
        zipfile.BadZipFile,
        ValueError,
        KeyError,
        ElementTree.ParseError,
        RuntimeError,
        NotImplementedError,
    ):
        pass
    raise HTTPException(415, "media_office_invalid")


def audio_for_meta(source):
    """Create bounded AAC/MP4 without changing the private Ogg asset."""
    output = source.with_suffix(".send.m4a")
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-nostdin",
                "-v",
                "error",
                "-threads",
                "1",
                "-protocol_whitelist",
                "file,pipe",
                "-format_whitelist",
                "ogg",
                "-i",
                str(source),
                "-vn",
                "-sn",
                "-dn",
                "-map_metadata",
                "-1",
                "-c:a",
                "aac",
                "-b:a",
                "64k",
                "-ac",
                "1",
                "-fs",
                str(MAX_BYTES + 1),
                "-f",
                "ipod",
                "-y",
                str(output),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=25,
            check=False,
        )
        if (
            result.returncode
            or not output.is_file()
            or not 0 < output.stat().st_size <= MAX_BYTES
        ):
            raise HTTPException(415, "media_audio_invalid")
        os.chmod(output, 0o600)
        return output
    except (OSError, subprocess.TimeoutExpired):
        output.unlink(missing_ok=True)
        raise HTTPException(415, "media_audio_invalid") from None
