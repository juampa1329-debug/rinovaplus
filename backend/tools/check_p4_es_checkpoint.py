"""Offline P4 handoff checks and exact replay of the unchanged parent chain."""

import argparse
import copy
import hashlib
import json
import os
import subprocess
import sys
import uuid
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(value):
    if not value:
        raise ValueError("P4ES_checkpoint_mismatch")


def replay_parent():
    baseline = read(ROOT / "docs/adaptation/sql/p4_es_input_baseline.json")
    archive = ROOT / ".local/p4-es/public-preimages.zip"
    require(sha(archive) == baseline["source_archive_sha256"])
    if os.name == "nt":
        # Frozen checkers create nested native replay directories. Linux avoids
        # Windows import-path limits without changing any historical checker.
        code = """
import hashlib,io,json,subprocess,sys,tempfile,zipfile
from pathlib import Path
length=int(sys.stdin.buffer.readline());baseline=json.loads(sys.stdin.buffer.read(length))
base=Path(tempfile.mkdtemp(prefix='cbn-p4-replay-'))
target=base/'CRM_CBN';target.mkdir()
(target/'.local/current-preview').mkdir(parents=True)
with zipfile.ZipFile(io.BytesIO(sys.stdin.buffer.read())) as saved:
 for entry in baseline['files']:
  raw=saved.read(entry['archive_name'])
  assert hashlib.sha256(raw).hexdigest()==entry['sha256']
  path=(target/entry['path']).resolve();assert path.is_relative_to(base)
  path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
result=subprocess.run([sys.executable,'-B','tools/check_current_preview.py','--self-test','--replay-parent'],cwd=target/'backend',capture_output=True,text=True)
(base/'parent-replay.txt').write_text(result.stdout+result.stderr)
if result.returncode:
 print(result.stderr);print('diagnostics:',base);sys.exit(result.returncode)
print(json.dumps({'status':'passed','exact_preimages':len(baseline['files']),'chain':['PREVIEW-DEMO-1','P3-ES','P2-ES','P1-ES'],'modified_parent_checkers':False,'execution':'offline_Linux_filesystem_no_SQL'}))
"""
        encoded = json.dumps(baseline).encode()
        result = subprocess.run(
            ["docker", "exec", "-i", "crm-cbn-p2-tools", "python", "-B", "-c", code],
            input=str(len(encoded)).encode() + b"\n" + encoded + archive.read_bytes(),
            capture_output=True,
        )
        (ROOT / ".local/p4-es/parent-replay.txt").write_bytes(
            result.stdout + result.stderr
        )
        require(result.returncode == 0)
        return json.loads(result.stdout)
    base = ROOT / ".local/r" / uuid.uuid4().hex[:8]
    target = base / "CRM_CBN"
    target.mkdir(parents=True)
    (target / ".local/current-preview").mkdir(parents=True)
    with zipfile.ZipFile(archive) as saved:
        require(set(saved.namelist()) == {v["archive_name"] for v in baseline["files"]})
        for entry in baseline["files"]:
            raw = saved.read(entry["archive_name"])
            require(hashlib.sha256(raw).hexdigest() == entry["sha256"])
            path = (target / entry["path"]).resolve()
            require(path.is_relative_to(base.resolve()))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    proof = target / "docs/adaptation/sql/current_preview_validation.json"
    require(sha(proof) == baseline["parent_preview_proof_sha256"])
    result = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-B",
            "tools/check_current_preview.py",
            "--self-test",
            "--replay-parent",
        ],
        cwd=target / "backend",
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    (base / "parent-replay.txt").write_text(
        result.stdout + result.stderr, encoding="utf-8"
    )
    require(result.returncode == 0)
    return {
        "status": "passed",
        "exact_preimages": len(baseline["files"]),
        "chain": ["PREVIEW-DEMO-1", "P3-ES", "P2-ES", "P1-ES"],
        "modified_parent_checkers": False,
    }


def validate(proof):
    required = {
        "backend/app/institutional/" + n + ".py"
        for n in [
            "channel_outbox",
            "channel_ingress",
            "channel_oauth",
            "channel_comments",
            "channel_events",
            "channel_retry",
            "channel_media",
            "channels_policy",
            "spanish",
        ]
    } | {
        "compose.channels.yaml",
        "graphify-out/p4-es/source-manifest.json",
        "tasks/p4-es-progress.json",
        "docs/adaptation/phase-work-progress.json",
    }
    require(required <= set(proof["source_pins"]))
    for name, expected in proof["source_pins"].items():
        require(sha(ROOT / name) == expected)
    require(
        proof["external_acceptance"]
        == "pending_no_public_domain_or_provider_applications"
    )
    require(proof["academic_DDL_or_DML"] is False)
    require(proof["real_provider_calls"] == 0)
    require(proof["P4_accepted"] is False and proof["primary_port"] == 4178)
    deploy = read(ROOT / "artifacts/p4-es/deployment-result.json")
    require(proof["image_digest"] == deploy["image_digest"])
    baseline = read(ROOT / "docs/adaptation/sql/p4_es_input_baseline.json")
    initial = {v["path"]: v["sha256"] for v in baseline["files"]}
    expected_memory = set(read(ROOT / "tasks/p4-es-progress.json")["memory_files"])
    require(set(proof["memory_transitions"]) == expected_memory)
    for name, transition in proof["memory_transitions"].items():
        require(transition == {"before": initial[name], "after": sha(ROOT / name)})
    for folder in ["p1-es", "p2-es", "p3-es", "current-preview"]:
        for name, expected in initial.items():
            if name.startswith("graphify-out/" + folder + "/"):
                require(sha(ROOT / name) == expected)
    p2 = ROOT / "backend/migrations/cbn_institutional_spanish_v1/release.json"
    require(
        sha(p2) == "1a7ba0dc7435e1e5dd61b431cca7f2164d698d4b4b6df9dd53cd66e8b40b10b4"
    )
    for name, expected in read(p2)["inputs"].items():
        require(sha(ROOT / name) == expected)
    p3 = ROOT / "backend/migrations/cbn_workspace_spanish_v1/release.json"
    require(
        sha(p3) == "7d4c3f55654d8d683246c2cd2547d29da5274825170f304b2c6b069e914d379b"
    )
    for name, expected in read(p3)["files"].items():
        require(sha(p3.parent / name) == expected)
    from phase_work_progress import check as progress

    state = progress(negatives=True)
    require(
        proof["phase_percentages"]
        == {p["id"]: p["work_percent_display"] for p in state["phases"]}
    )
    graph = read(ROOT / "graphify-out/p4-es/source-manifest.json")
    for name, expected in graph["sources"].items():
        require(sha(ROOT / name) == expected)
    for name, expected in graph["artifacts"].items():
        require(sha(ROOT / "graphify-out/p4-es" / name) == expected)
    return {
        "status": "passed",
        "source_pins": len(proof["source_pins"]),
        "roadmap": state,
    }


def check(negatives=False):
    proof = read(ROOT / "docs/adaptation/sql/p4_es_validation.json")
    result = validate(proof)
    if negatives:
        cases = [
            lambda p: p.__setitem__("real_provider_calls", 1),
            lambda p: p.__setitem__("academic_DDL_or_DML", True),
            lambda p: p.__setitem__("P4_accepted", True),
            lambda p: p.__setitem__("primary_port", 4179),
            lambda p: p["source_pins"].pop(
                "backend/app/institutional/channel_outbox.py"
            ),
            lambda p: p["memory_transitions"].clear(),
            lambda p: p["phase_percentages"].__setitem__("P4", "100.00%"),
        ]
        for mutation in cases:
            invalid = copy.deepcopy(proof)
            mutation(invalid)
            try:
                validate(invalid)
            except ValueError:
                pass
            else:
                raise AssertionError("P4ES_invalid_checkpoint_accepted")
        result["negative_cases_rejected"] = len(cases)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay-parent", action="store_true")
    parser.add_argument("--parent-only", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    result = {} if args.parent_only else check(args.self_test)
    if args.replay_parent:
        result["parent_replay"] = replay_parent()
    print(json.dumps(result, ensure_ascii=False))
