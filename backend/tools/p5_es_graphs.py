"""Bounded Graphify P5 extension; previous graphs stay frozen."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "graphify-out/p5-es"
CODE = sorted(
    {
        p.relative_to(ROOT).as_posix()
        for pattern in [
            "backend/app/institutional/agent*.py",
            "backend/app/institutional/channel*.py",
            "backend/app/modules/agents/*.py",
            "backend/tools/*p5*.py",
            "frontend/src/modules/agents/*.tsx",
            "frontend/src/modules/agents/api.ts",
            "frontend/src/modules/ai/pages/AgentAssistantChat.tsx",
            "backend/tests/test_agent*.py",
            "backend/tests/test_institutional_agents.py",
            "frontend/src/test/institutionAgentsP5.test.tsx",
            "frontend/src/test/institutionWorkspace.test.tsx",
        ]
        for p in ROOT.glob(pattern)
    }
    | {
        "backend/app/institutional/" + n + ".py"
        for n in ["api", "auth", "settings", "spanish", "store", "ui_contract"]
    }
    | {
        "frontend/src/institution/" + n + ".tsx"
        for n in ["Workspace", "InstitutionApp", "AgentsWorkspace", "api"]
    }
    | {
        "backend/app/modules/channels/providers.py",
        "backend/app/modules/inbox/application/state.py",
    }
)
DOCS = [
    "docs/adaptation/sql/SQL_P5_ES_REVIEW.md",
    "docs/adaptation/phase-work-progress.json",
    "artifacts/p5-es/final-review.json",
    "artifacts/p5-es/reference-review.json",
    "docs/adaptation/fragments/p5-final.draft.json",
    "docs/adaptation/fragments/p5-reference.draft.json",
    "artifacts/p5-es/acceptance-review.json",
    "artifacts/p5-es/final-checks.json",
    "artifacts/p5-es/browser/result.json",
    "artifacts/p5-es/browser/final-result.json",
] + [
    "artifacts/p5-es/" + n + "-result.json"
    for n in [
        "api",
        "runtime",
        "lifecycle",
        "channels",
        "extras",
        "negatives",
        "storage",
        "recovery",
        "compile",
        "demo",
        "preservation",
        "restart",
        "deployment",
        "media",
    ]
]


def read(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def extract_code():
    from graphify.extract import extract

    value = extract(
        [ROOT / n for n in CODE],
        root=ROOT,
        cache_root=ROOT / ".local/p5-es/final-graph-cache",
        max_workers=3,
    )
    save(ROOT / ".local/p5-es/final-ast.json", value)
    print(
        json.dumps(
            {
                "code_files": len(CODE),
                "nodes": len(value["nodes"]),
                "edges": len(value["edges"]),
            }
        )
    )


def build():
    from adaptation_graphs import render
    from graphify.cache import save_semantic_cache
    from graphify.detect import detect

    corpus = ROOT / ".local/p5-es" / ("final-corpus-" + uuid4().hex[:8])
    corpus.mkdir()
    (corpus / ".graphifyignore").write_text("!**/*.md\n!**/*.json\n")
    for i, name in enumerate(CODE + DOCS):
        shutil.copyfile(ROOT / name, corpus / (str(i) + "_" + Path(name).name))
    detection = detect(corpus)
    assert 0 < detection["total_files"] < 150 and detection["total_words"] < 250000
    save(OUT / "detection.json", detection)
    ast = read(ROOT / ".local/p5-es/final-ast.json")
    final = read(ROOT / "docs/adaptation/fragments/p4-final.draft.json")
    reference = read(ROOT / "docs/adaptation/fragments/p4-reference.draft.json")
    nodes = {v["id"]: v for v in ast["nodes"] + reference["nodes"] + final["nodes"]}
    edges = ast["edges"] + reference["edges"] + final["edges"]
    for phase in read(ROOT / "docs/adaptation/phase-work-progress.json")["summary"][
        "phases"
    ]:
        identity = "p5_progress_" + phase["id"]
        nodes[identity] = {
            "id": identity,
            "label": phase["id"] + " " + phase["work_percent_display"],
            "file_type": "document",
            "source_file": "docs/adaptation/phase-work-progress.json",
            "source_location": "$.summary.phases",
            "accepted": phase["phase_accepted"],
            "domain": "fixed_weight_roadmap",
        }
    for edge in edges:
        for identity in [edge["source"], edge["target"]]:
            if identity not in nodes:
                nodes[identity] = {
                    "id": identity,
                    "label": identity,
                    "file_type": "document",
                    "source_file": edge["source_file"],
                    "source_location": edge.get("source_location"),
                    "domain": "explicit_context",
                }
    save_semantic_cache(
        final["nodes"],
        final["edges"],
        final.get("hyperedges", []),
        root=ROOT,
        allowed_source_files=[ROOT / n["source_file"] for n in final["nodes"]],
        cache_root=ROOT / ".local/p5-es/final-graph-cache",
    )
    counts = render(
        {
            **ast,
            "nodes": list(nodes.values()),
            "edges": edges,
            "hyperedges": reference.get("hyperedges", []) + final.get("hyperedges", []),
        },
        OUT,
        detection,
        coverage_note=(
            "P5 educational agents accepted in the local canonical scope: "
            "selected-profile inference, hierarchy, permissions, source scope, "
            "one owner, human handoff and paused version restoration, with "
            "controlled provider tests and one integrated preview4178. "
            "External OAuth/callback/delivery/recovery acceptance pending: "
            "no domain/provider applications. Empty ready-blob partition only. Initial Scentra reference "
            "review retained; final source review does not execute SQL "
            "or providers. Previous graphs frozen. Phase weights "
            "unchanged; token usage not measured."
        ),
    )
    save(
        OUT / "source-manifest.json",
        {
            "unit": "P5-ES",
            **counts,
            "sources": {n: sha(ROOT / n) for n in CODE + DOCS},
            "artifacts": {
                n: sha(OUT / n)
                for n in [
                    "graph.json",
                    "graph.html",
                    "GRAPH_REPORT.md",
                    "detection.json",
                ]
            },
            "old_graphs_rebuilt": False,
        },
    )
    print(json.dumps({"bounded_files": detection["total_files"], **counts}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["extract", "build", "check"])
    action = parser.parse_args().action
    if action == "extract":
        extract_code()
    elif action == "build":
        build()
    else:
        manifest = read(OUT / "source-manifest.json")
        for name, expected in manifest["sources"].items():
            assert sha(ROOT / name) == expected, name
        for name, expected in manifest["artifacts"].items():
            assert sha(OUT / name) == expected, name
        print(json.dumps({"status": "passed", "sources": len(manifest["sources"])}))
