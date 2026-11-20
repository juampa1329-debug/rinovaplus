"""Local office/keyboard mixing. Fixed assets, no external URLs or paid calls."""

import hashlib
import shutil
import subprocess
import threading
from pathlib import Path

from fastapi import HTTPException

from app.institutional.voice_policy import VoiceAmbience
from app.modules.inbox.infrastructure import media_files as files

ASSETS = Path(__file__).with_name("voice_assets")
SLOTS = threading.BoundedSemaphore(2)
VERSION = "office-keyboard-recordings-v2"


def filter_graph(options, duration):
    end = max(0, duration - 0.2)
    graph = (
        "[0:a]aresample=48000,aformat=channel_layouts=mono,asplit=2[voice][key];"
        f"[voice]volume={options.voice_volume:.4f}[main];"
        f"[1:a]aresample=48000,volume={options.office_volume:.4f}[office];"
        f"[2:a]aresample=48000,volume={options.typing_volume:.4f}[typing];"
        "[office][typing]amix=inputs=2:normalize=0[bed];"
    )
    if options.ducking:
        graph += "[bed][key]sidechaincompress=threshold=0.025:ratio=8:attack=12:release=350:makeup=1[quiet];"
    else:
        graph += "[key]anullsink;[bed]anull[quiet];"
    return graph + (
        f"[quiet]afade=t=in:d=0.15,afade=t=out:st={end:.4f}:d=0.2[background];"
        "[main][background]amix=inputs=2:duration=first:normalize=0,"
        "alimiter=limit=0.95:level=false:latency=true[out]"
    )


def mix(source, destination, options, duration):
    options = VoiceAmbience.model_validate(options)
    if not options.enabled:
        shutil.copyfile(source, destination)
        return
    if not 0 < duration <= 300:
        raise HTTPException(409, "voice_mix_duration_invalid")
    if not SLOTS.acquire(blocking=False):
        raise HTTPException(429, "voice_mix_busy")
    try:
        if not shutil.which("ffmpeg"):
            raise HTTPException(503, "voice_mix_unavailable")
        arguments = ["ffmpeg", "-nostdin", "-v", "error", "-threads", "1", "-filter_complex_threads", "1",
                     "-protocol_whitelist", "file,pipe", "-i", str(source)]
        for name in ("office.wav", "typing.wav"):
            arguments += ["-stream_loop", "-1", "-i", str(ASSETS / name)]
        arguments += ["-filter_complex", filter_graph(options, duration), "-map", "[out]", "-map_metadata", "-1",
                      "-t", str(duration), "-ac", "1", "-ar", "48000", "-c:a", "libopus", "-b:a", "48k",
                      "-fs", str(files.MAX_BYTES + 1), "-f", "ogg", "-y", str(destination)]
        result = subprocess.run(arguments, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, timeout=25, check=False)
        if result.returncode or not destination.is_file() or not 0 < destination.stat().st_size <= files.MAX_BYTES:
            raise HTTPException(503, "voice_mix_failed")
        destination.chmod(0o600)
    except (OSError, subprocess.TimeoutExpired):
        raise HTTPException(503, "voice_mix_failed") from None
    finally:
        SLOTS.release()


def apply(identifier, info, options):
    """Preserve an inspected dry master for private remix previews."""
    source, dry, target = files.path(identifier), files.path(identifier, ".dry"), files.path(identifier, ".part")
    shutil.copyfile(source, dry)
    dry.chmod(0o600)
    receipt = {"version": VERSION, "settings": VoiceAmbience.model_validate(options).model_dump(),
               "dry_hash": hashlib.sha256(dry.read_bytes()).hexdigest()}
    if receipt["settings"]["enabled"]:
        try:
            mix(dry, target, receipt["settings"], info["duration"])
            info = files.inspect_file(identifier, "nota-de-voz.ogg")
        finally:
            target.unlink(missing_ok=True)
    return info, receipt
