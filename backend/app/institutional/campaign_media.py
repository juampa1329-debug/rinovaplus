"""P8 reuses bounded C10 inspectors and adds an isolated, bounded MP4 inspector."""

import hashlib, json, math, os, subprocess
from pathlib import Path
from fastapi import HTTPException
from app.modules.inbox.infrastructure import media_files as files
from app.institutional.channel_text import sql_text


def inspect(id, name, kind):
    if kind != "video":
        info = files.inspect_file(id, name)
        info["name"] = (
            sql_text(Path(info["name"]).stem, 140) + Path(info["name"]).suffix[:10]
        )
        return info
    if not files.INSPECTION_SLOTS.acquire(blocking=False):
        raise HTTPException(429, "media_inspection_busy")
    source = files.path(id, ".part")
    output = files.path(id, ".checked")
    try:
        raw = source.read_bytes()
        if not raw or len(raw) > files.MAX_BYTES:
            raise HTTPException(413, "media_size_limit")
        probe = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-protocol_whitelist",
                "file,pipe",
                "-format_whitelist",
                "mov,matroska,webm",
                "-show_entries",
                "format=duration:stream=codec_type,width,height",
                "-of",
                "json",
                str(source),
            ],
            capture_output=True,
            timeout=8,
            check=False,
        )
        if probe.returncode or len(probe.stdout) > 20000:
            raise HTTPException(415, "campaign_video_invalid")
        value = json.loads(probe.stdout)
        duration = float(value.get("format", {}).get("duration", 0))
        streams = value.get("streams", [])
        video = [s for s in streams if s.get("codec_type") == "video"]
        audio = [s for s in streams if s.get("codec_type") == "audio"]
        if (
            len(video) != 1
            or len(audio) > 1
            or len(streams) != len(video) + len(audio)
            or not math.isfinite(duration)
            or not 0 < duration <= 120
            or not 2 <= video[0].get("width", 0) <= 1920
            or not 2 <= video[0].get("height", 0) <= 1080
        ):
            raise HTTPException(413, "campaign_video_limit")
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
                "mov,matroska,webm",
                "-i",
                str(source),
                "-map",
                "0:v:0",
                "-map",
                "0:a:0?",
                "-sn",
                "-dn",
                "-map_metadata",
                "-1",
                "-vf",
                "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-crf",
                "28",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-ac",
                "2",
                "-ar",
                "48000",
                "-t",
                "120",
                "-fs",
                str(files.MAX_BYTES + 1),
                "-movflags",
                "+faststart",
                "-f",
                "mp4",
                "-y",
                str(output),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
            check=False,
        )
        if result.returncode or not output.is_file():
            raise HTTPException(415, "campaign_video_invalid")
        size = output.stat().st_size
        if not 0 < size <= files.MAX_BYTES:
            raise HTTPException(413, "media_size_limit")
        os.chmod(output, 0o600)
        final = files.path(id)
        os.replace(output, final)
        return dict(
            kind="video",
            mime="video/mp4",
            size=size,
            duration=duration,
            name=sql_text(files.filename(Path(name).stem), 140) + ".mp4",
            hash=hashlib.sha256(final.read_bytes()).digest(),
            source_hash=hashlib.sha256(raw).digest(),
        )
    except (OSError, ValueError, subprocess.TimeoutExpired):
        raise HTTPException(415, "campaign_video_invalid") from None
    finally:
        source.unlink(missing_ok=True)
        output.unlink(missing_ok=True)
        files.INSPECTION_SLOTS.release()
