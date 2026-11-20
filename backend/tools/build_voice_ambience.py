"""Rebuild packaged CC0 recordings from already-downloaded, hash-pinned sources.

No network IO. Usage: python tools/build_voice_ambience.py OFFICE.mp3 TYPING.mp3
See app/institutional/voice_assets/sources.json for provenance and source URLs.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[1] / "app/institutional/voice_assets"


def build(sources, folder=ASSETS):
    manifest = json.loads((ASSETS / "sources.json").read_text(encoding="utf-8"))
    encoder = shutil.which("ffmpeg")
    if not encoder:
        raise SystemExit("FFmpeg is required")
    for name, source in sources.items():
        item = manifest["tracks"][name]
        if hashlib.sha256(source.read_bytes()).hexdigest() != item["source_sha256"]:
            raise SystemExit(f"Unexpected source hash: {name}")
        subprocess.run([encoder, "-nostdin", "-v", "error", "-i", str(source),
                        "-map_metadata", "-1", "-af", "loudnorm=I=-24:TP=-3:LRA=11,aresample=16000",
                        "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", "-y",
                        str(folder / (name + ".wav"))], check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("office", type=Path)
    parser.add_argument("typing", type=Path)
    args = parser.parse_args()
    build({"office": args.office, "typing": args.typing})
