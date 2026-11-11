"""Reconstruct exact public P9 preimages; replay frozen checkers without SQL IO."""

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as f:
        while block := f.read(1024 * 1024):
            value.update(block)
    return value.hexdigest()


def replay_parent():
    baseline = json.loads(
        (ROOT / "docs/adaptation/sql/p10_es_input_baseline.json").read_text()
    )
    archive = ROOT / ".local/p10-es/public-preimages.zip"
    assert sha(archive) == baseline["source_archive_sha256"]
    base = ROOT / ".local/r10"
    target = base / "CRM_CBN"
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zipped:
        for entry in baseline["files"]:
            path = (target / entry["path"]).resolve()
            assert path.is_relative_to(base.resolve())
            if path.exists():
                assert sha(path) == entry["sha256"]
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            h = hashlib.sha256()
            with (
                zipped.open(entry["archive_name"]) as source,
                path.open("xb") as output,
            ):
                while block := source.read(1024 * 1024):
                    output.write(block)
                    h.update(block)
            assert h.hexdigest() == entry["sha256"]
    assert (
        sha(target / "docs/adaptation/sql/p9_es_validation.json")
        == baseline["parent_P9_proof_sha256"]
    )
    result = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-B",
            "tools/check_p9_es_checkpoint.py",
            "--self-test",
            "--replay-parent",
        ],
        cwd=target / "backend",
        capture_output=True,
    )
    (ROOT / ".local/p10-es/parent-replay.txt").write_bytes(
        result.stdout + result.stderr
    )
    assert result.returncode == 0, "frozen_parent_replay_failed_see_private_log"
    return dict(
        status="passed",
        exact_preimages=len(baseline["files"]),
        parent_checker_bytes_modified=False,
        SQL_connected=False,
        chain=["P9", "P8", "P7", "P6", "P5", "P4", "PREVIEW-DEMO-1", "P3", "P2", "P1"],
        source_archive_sha256=baseline["source_archive_sha256"],
        result=json.loads(result.stdout),
    )


if __name__ == "__main__":
    result = replay_parent()
    (ROOT / "artifacts/p10-es/parent-replay-result.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps({k: v for k, v in result.items() if k != "result"}))
