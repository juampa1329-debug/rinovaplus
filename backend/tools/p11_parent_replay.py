"""Reconstruct exact P10 inputs; immutable large archives are verified hardlinks."""

import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        while block := source.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def replay_parent():
    baseline = json.loads((ROOT / "docs/adaptation/sql/p11_es_input_baseline.json").read_text())
    archive = ROOT / ".local/p11-es/public-preimages.zip"
    assert sha(archive) == baseline["source_archive_sha256"]
    base = ROOT / ".local/p11-es/replay"
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
            if "immutable_archive_reference" in entry:
                original = (ROOT / entry["immutable_archive_reference"]).resolve()
                assert original.is_relative_to((ROOT / ".local").resolve()) and original.name == "public-preimages.zip"
                assert sha(original) == entry["sha256"] and original.suffix == ".zip"
                # Never hardlink source code or any mutable file.
                os.link(original, path)
            else:
                digest = hashlib.sha256()
                with zipped.open(entry["archive_name"]) as source, path.open("xb") as output:
                    while block := source.read(1024 * 1024):
                        output.write(block)
                        digest.update(block)
                assert digest.hexdigest() == entry["sha256"]
    assert sha(target / "docs/adaptation/sql/p10_es_validation.json") == baseline["parent_P10_proof_sha256"]
    result = subprocess.run([sys.executable, "-X", "utf8", "-B", "tools/check_p10_es_checkpoint.py", "--self-test", "--replay-parent"], cwd=target / "backend", capture_output=True)
    (ROOT / ".local/p11-es/parent-replay.txt").write_bytes(result.stdout + result.stderr)
    assert result.returncode == 0, "frozen_P10_replay_failed_see_private_log"
    return {"status": "passed", "exact_preimages": len(baseline["files"]), "parent_checker_bytes_modified": False, "SQL_connected": False, "immutable_archive_references": sum("immutable_archive_reference" in v for v in baseline["files"]), "chain": ["P10", "P9", "P8", "P7", "P6", "P5", "P4", "PREVIEW-DEMO-1", "P3", "P2", "P1"], "source_archive_sha256": baseline["source_archive_sha256"], "result": json.loads(result.stdout)}


if __name__ == "__main__":
    value = replay_parent()
    (ROOT / "artifacts/p11-es/parent-replay-result.json").write_text(json.dumps(value, indent=2) + "\n")
    print(json.dumps({k: v for k, v in value.items() if k != "result"}))
