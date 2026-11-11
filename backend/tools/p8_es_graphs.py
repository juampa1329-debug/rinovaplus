"""Bounded incremental Graphify P8 evidence; no preceding graph is rebuilt."""

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "graphify-out/p8-es"
CODE = sorted(
    {
        p.relative_to(ROOT).as_posix()
        for pattern in [
            "backend/app/institutional/campaign*.py",
            "backend/tools/*p8*.py",
            "backend/migrations/cbn_campaign_operations_v1/*.sql",
            "backend/tests/test_institutional_campaigns.py",
            "frontend/src/test/institutionCampaign*P8.test.tsx",
        ]
        for p in ROOT.glob(pattern)
    }
    | {
        "backend/app/institutional/" + n + ".py"
        for n in [
            "api",
            "auth",
            "settings",
            "spanish",
            "store",
            "agents",
            "workspace",
            "channel_outbox",
            "channel_events",
            "channel_workers",
            "channel_retry",
            "channel_workspace",
            "ui_contract",
            "broadcasts",
        ]
    }
    | {
        "frontend/src/institution/" + n + ".tsx"
        for n in ["CampaignWorkspace", "CampaignAssetInput", "InstitutionApp", "api"]
    }
    | {
        "backend/tools/foundation_snapshot.py",
        "backend/app/modules/channels/providers.py",
    }
)
DOCS = [
    "docs/adaptation/sql/SQL_P8_ES_REVIEW.md",
    "docs/adaptation/phase-work-progress.json",
    "artifacts/p8-es/existing-review-final.json",
    "artifacts/p8-es/reference-review-final.json",
    "artifacts/p8-es/acceptance-review.json",
    "artifacts/p8-es/final-checks.json",
    "artifacts/p8-es/browser/result.json",
    "artifacts/p8-es/browser/final-result.json",
    *[
        "artifacts/p8-es/" + n + "-result.json"
        for n in [
            "api",
            "runtime",
            "extras",
            "storage",
            "recovery",
            "compile",
            "demo",
            "preservation",
            "restart",
            "deployment",
            "parent-replay",
            "boundaries",
            "template-media",
            "wait-resync",
            "wait-restart",
            "captions",
            "delivery",
            "demo-media",
        ]
    ],
]
# Include all declared semantic sources, including Scentra, in the bounded manifest.
for name in ["p8-existing.json", "p8-reference.json"]:
    fragment = json.loads(
        (ROOT / "docs/adaptation/fragments" / name).read_text(encoding="utf-8")
    )
    for item in fragment["nodes"] + fragment["edges"] + fragment.get("hyperedges", []):
        source = item.get("source_file")
        if source and source not in CODE + DOCS:
            (
                CODE
                if Path(source).suffix in {".py", ".sql", ".js", ".jsx", ".tsx", ".ts"}
                else DOCS
            ).append(source)
CODE = sorted(set(CODE))
DOCS = sorted(set(DOCS))


def read(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(p, v):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(v, ensure_ascii=False, indent=2) + "\n")


def build():
    from adaptation_graphs import render
    from graphify.cache import save_semantic_cache
    from graphify.detect import detect
    from graphify.extract import extract

    corpus = ROOT / ".local/p8-es" / ("final-corpus-" + uuid4().hex[:8])
    corpus.mkdir()
    (corpus / ".graphifyignore").write_text("!**/*.md\n!**/*.json\n")
    for i, n in enumerate(CODE + DOCS):
        shutil.copyfile(ROOT / n, corpus / (str(i) + "_" + Path(n).name))
    detection = detect(corpus)
    assert 0 < detection["total_files"] < 200 and detection["total_words"] < 2000000
    ast = extract(
        [ROOT / n for n in CODE],
        root=ROOT,
        cache_root=ROOT / ".local/p8-es/final-cache",
        max_workers=3,
    )
    fragments = [
        read(ROOT / "docs/adaptation/fragments" / n)
        for n in ["p8-existing.json", "p8-reference.json"]
    ]
    nodes = {v["id"]: v for v in ast["nodes"]}
    edges = list(ast["edges"])
    hyper = []
    for f in fragments:
        nodes.update({v["id"]: v for v in f["nodes"]})
        edges.extend(f["edges"])
        hyper.extend(f.get("hyperedges", []))
        save_semantic_cache(
            f["nodes"],
            f["edges"],
            f.get("hyperedges", []),
            root=ROOT,
            allowed_source_files=[
                ROOT / name
                for name in {
                    v["source_file"]
                    for v in f["nodes"] + f["edges"] + f.get("hyperedges", [])
                    if v.get("source_file")
                }
            ],
            cache_root=ROOT / ".local/p8-es/final-cache",
        )
    for phase in read(ROOT / "docs/adaptation/phase-work-progress.json")["summary"][
        "phases"
    ]:
        key = "p8_progress_" + phase["id"]
        nodes[key] = {
            "id": key,
            "label": phase["id"] + " " + phase["work_percent_display"],
            "file_type": "document",
            "source_file": "docs/adaptation/phase-work-progress.json",
            "source_location": "$.summary.phases",
            "accepted": phase["phase_accepted"],
            "domain": "fixed_weight_roadmap",
        }
    for edge in edges:
        for key in [edge["source"], edge["target"]]:
            if key not in nodes:
                nodes[key] = {
                    "id": key,
                    "label": key,
                    "file_type": "document",
                    "source_file": edge["source_file"],
                    "source_location": edge.get("source_location"),
                    "domain": "explicit_context",
                }
    counts = render(
        {
            **ast,
            "nodes": list(nodes.values()),
            "edges": edges,
            "hyperedges": hyper,
            "input_tokens": 0,
            "output_tokens": 0,
        },
        OUT,
        detection,
        coverage_note=(
            "P8 native SQL2019 campaign/CRM templates/segments, durable versioned multi-step flows, future message/stage/program/inactivity triggers, waits and quiet windows, canonical identity/consent/role/handoff/response fences, native C10/P7 dispatcher, immutable attempts and uncertainty, typed media library/upload/microphone/inspection/private blobs, per-part delays/captions, Instagram Login expiring queue-bound delivery, deterministic AB and explicit-context attribution. SQL/API/browser/storage/recovery receipts are separate from static source review. Technical P8 95%, criteria3/4; closure depends on real P7/P4 Meta acceptance. No academic writes or previous-copy redirection. Old graphs frozen. Token usage not measured."
        ),
    )
    report = OUT / "GRAPH_REPORT.md"
    text = re.sub(
        r"^- Token cost:.*$",
        "- Uso de tokens: no medido; los ceros internos no son una medición.",
        report.read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )
    text += (
        "\n## Cobertura SQL y continuidad\n\n"
        "Las tablas y relaciones DDL se extraen semánticamente y se contrastan "
        "con el catálogo SQL2019 ejecutado. El parser SQL opcional de tree-sitter "
        "no está instalado; no se atribuye extracción AST a esos dos archivos. "
        "Los hashes del manifiesto incluyen el trabajo sin commit. "
        "Regeneración acotada: `python -X utf8 -B "
        "backend/tools/p8_es_graphs.py build`.\n"
    )
    report.write_text(text, encoding="utf-8")
    save(OUT / "detection.json", detection)
    save(
        OUT / "source-manifest.json",
        {
            "unit": "P8-ES",
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
            "token_usage_measured": False,
            "sql_structural_parser_available": importlib.util.find_spec(
                "tree_sitter_sql"
            )
            is not None,
            "sql_ddl_coverage": "semantic_extraction_and_executed_SQL2019_catalog",
        },
    )
    print(json.dumps({"files": detection["total_files"], **counts}))


def check():
    value = read(OUT / "source-manifest.json")
    for n, h in value["sources"].items():
        assert sha(ROOT / n) == h, n
    for n, h in value["artifacts"].items():
        assert sha(OUT / n) == h, n
    assert value["old_graphs_rebuilt"] is False
    return {"status": "passed", "sources": len(value["sources"])}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["build", "check"])
    args = parser.parse_args()
    build() if args.action == "build" else print(json.dumps(check()))
