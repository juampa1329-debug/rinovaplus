"""Offline P5 evidence validation and replay of frozen P4/P3/P2/P1 sources."""

import argparse
import copy
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok):
    if not ok:
        raise ValueError("P5ES_checkpoint_mismatch")


def replay_parent():
    baseline = read(ROOT / "docs/adaptation/sql/p5_es_input_baseline.json")
    archive = ROOT / ".local/p5-es/public-preimages.zip"
    require(sha(archive) == baseline["source_archive_sha256"])
    script = """
import hashlib,io,json,subprocess,sys,tempfile,zipfile,os
from pathlib import Path
length=int(sys.stdin.buffer.readline());baseline=json.loads(sys.stdin.buffer.read(length))
temp_root=Path('/var/lib/cbn-p2/p5-es-v1/replay-temp');temp_root.mkdir(mode=0o700,parents=True,exist_ok=True)
os.environ['TMPDIR']=str(temp_root);tempfile.tempdir=None
base=Path(tempfile.mkdtemp(prefix='cbn-p5-replay-'));target=base/'CRM_CBN';target.mkdir()
with zipfile.ZipFile(io.BytesIO(sys.stdin.buffer.read())) as saved:
 assert set(saved.namelist())=={v['archive_name'] for v in baseline['files']}
 for entry in baseline['files']:
  raw=saved.read(entry['archive_name']);assert hashlib.sha256(raw).hexdigest()==entry['sha256']
  path=(target/entry['path']).resolve();assert path.is_relative_to(base)
  path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
assert hashlib.sha256((target/'docs/adaptation/sql/p4_es_validation.json').read_bytes()).hexdigest()==baseline['parent_P4_proof_sha256']
result=subprocess.run([sys.executable,'-B','tools/check_p4_es_checkpoint.py','--self-test','--replay-parent'],cwd=target/'backend',capture_output=True,text=True)
(base/'parent-replay.txt').write_text(result.stdout+result.stderr)
if result.returncode:
 print(result.stderr);print('diagnostics:',base);sys.exit(result.returncode)
print(json.dumps({'status':'passed','exact_preimages':len(baseline['files']),'chain':['P4-ES','PREVIEW-DEMO-1','P3-ES','P2-ES','P1-ES'],'modified_parent_checkers':False,'execution':'offline_Linux_filesystem_no_SQL'}))
"""
    encoded = json.dumps(baseline).encode()
    result = subprocess.run(
        ["docker", "exec", "-i", "crm-cbn-p2-tools", "python", "-B", "-c", script],
        input=str(len(encoded)).encode() + b"\n" + encoded + archive.read_bytes(),
        capture_output=True,
    )
    (ROOT / ".local/p5-es/parent-replay.txt").write_bytes(result.stdout + result.stderr)
    require(result.returncode == 0)
    return json.loads(result.stdout)


def validate(proof):
    required = {
        "backend/app/institutional/" + n + ".py"
        for n in [
            "agents",
            "agents_api",
            "agents_policy",
            "agent_ai",
            "agent_catalog",
            "channel_outbox",
            "channel_workspace",
            "spanish",
        ]
    }
    required |= {
        "compose.agents.yaml",
        "docker/nginx.agents.conf",
        "graphify-out/p5-es/source-manifest.json",
        "tasks/p5-es-progress.json",
        "docs/adaptation/phase-work-progress.json",
    }
    require(required <= set(proof["source_pins"]))
    for name, expected in proof["source_pins"].items():
        require(sha(ROOT / name) == expected)
    require(
        proof["P5_accepted"] is True and proof["phase_percentages"]["P5"] == "100.00%"
    )
    require(
        proof["phase_percentages"]["P4"] == "82.29%" and proof["primary_port"] == 4178
    )
    require(proof["academic_DDL_or_DML"] is False and proof["real_provider_calls"] == 0)
    require(
        proof["release_sha256"]
        == "9046a8c33a3bbbb9d874ba0fc5451e3db5815c9afcc9b6552aabb6b0d2a2793a"
    )
    baseline = read(ROOT / "docs/adaptation/sql/p5_es_input_baseline.json")
    initial = {v["path"]: v["sha256"] for v in baseline["files"]}
    require(
        sha(ROOT / ".local/p5-es/public-preimages.zip")
        == baseline["source_archive_sha256"]
    )
    memory = read(ROOT / "tasks/p5-es-progress.json")["memory_files"]
    require(set(proof["memory_transitions"]) == set(memory))
    for name in memory:
        require(
            proof["memory_transitions"][name]
            == {"before": initial[name], "after": sha(ROOT / name)}
        )
    for name, before in initial.items():
        if name.startswith("graphify-out/") or name.startswith("../"):
            require(sha(ROOT / name) == before)
    for package, expected, key, rooted in [
        (
            "cbn_institutional_spanish_v1",
            "1a7ba0dc7435e1e5dd61b431cca7f2164d698d4b4b6df9dd53cd66e8b40b10b4",
            "inputs",
            True,
        ),
        (
            "cbn_workspace_spanish_v1",
            "7d4c3f55654d8d683246c2cd2547d29da5274825170f304b2c6b069e914d379b",
            "files",
            False,
        ),
        (
            "cbn_channels_operations_v1",
            "fd247602e95f7756deb77c7a71dfd53bf4b18f56eb555c499c1cc69a8d438e5b",
            "files",
            False,
        ),
        ("cbn_agents_operations_v1", proof["release_sha256"], "files", False),
    ]:
        path = ROOT / "backend/migrations" / package / "release.json"
        require(sha(path) == expected)
        for name, expected_input in read(path)[key].items():
            require(sha((ROOT if rooted else path.parent) / name) == expected_input)
    for name in [
        "api",
        "runtime",
        "lifecycle",
        "storage",
        "recovery",
        "channels",
        "extras",
        "negatives",
        "demo",
        "compile",
        "preservation",
        "restart",
        "deployment",
        "media",
    ]:
        require(
            read(ROOT / "artifacts/p5-es" / f"{name}-result.json")["status"] == "passed"
        )
    require(read(ROOT / "artifacts/p5-es/browser/result.json")["status"] == "passed")
    require(read(ROOT / "artifacts/p5-es/final-checks.json")["status"] == "passed")
    require(
        read(ROOT / "artifacts/p5-es/acceptance-review.json")["accepted_criteria"]
        == ["P5.1", "P5.2", "P5.3", "P5.close"]
    )
    from phase_work_progress import check as progress

    state = progress(negatives=True)
    require(
        proof["phase_percentages"]
        == {p["id"]: p["work_percent_display"] for p in state["phases"]}
    )
    graph = read(ROOT / "graphify-out/p5-es/source-manifest.json")
    for name, expected in graph["sources"].items():
        require(sha(ROOT / name) == expected)
    for name, expected in graph["artifacts"].items():
        require(sha(ROOT / "graphify-out/p5-es" / name) == expected)
    return {
        "status": "passed",
        "source_pins": len(proof["source_pins"]),
        "roadmap": state,
    }


def check(negatives=False):
    proof = read(ROOT / "docs/adaptation/sql/p5_es_validation.json")
    result = validate(proof)
    if negatives:
        mutations = [
            lambda p: p.__setitem__("P5_accepted", False),
            lambda p: p.__setitem__("academic_DDL_or_DML", True),
            lambda p: p.__setitem__("real_provider_calls", 1),
            lambda p: p.__setitem__("primary_port", 4179),
            lambda p: p["phase_percentages"].__setitem__("P4", "100.00%"),
            lambda p: p["source_pins"].pop("backend/app/institutional/agents.py"),
            lambda p: p["memory_transitions"].clear(),
            lambda p: p.__setitem__("release_sha256", "0" * 64),
        ]
        for mutate in mutations:
            bad = copy.deepcopy(proof)
            mutate(bad)
            try:
                validate(bad)
            except ValueError:
                pass
            else:
                raise AssertionError("P5ES_invalid_checkpoint_accepted")
        result["negative_cases_rejected"] = len(mutations)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--replay-parent", action="store_true")
    parser.add_argument("--parent-only", action="store_true")
    args = parser.parse_args()
    result = {} if args.parent_only else check(args.self_test)
    if args.replay_parent:
        result["parent_replay"] = replay_parent()
    print(json.dumps(result, ensure_ascii=False))
