"""Bounded incremental Graphify P10 evidence; no preceding graph is rebuilt."""

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "graphify-out/p10-es"
CODE = sorted(
    {
        p.relative_to(ROOT).as_posix()
        for pattern in [
            "backend/app/institutional/learning*.py",
            "backend/tools/*p10*.py",
            "backend/migrations/cbn_learning_operations_v*/*.sql",
            "backend/tests/test_institutional_learning.py",
            "frontend/src/test/institutionLearningP10.test.tsx",
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
            "channel_comments",
        ]
    }
    | {
        "frontend/src/institution/" + n + ".tsx"
        for n in ["LearningWorkspace", "InstitutionApp", "Workspace", "api"]
    }
    | {
        "frontend/src/institution/adsResource.ts",
        "backend/tools/foundation_snapshot.py",
        "backend/app/modules/channels/providers.py",
    }
)
DOCS = [
    "docs/adaptation/sql/SQL_P10_ES_REVIEW.md",
    "docs/adaptation/sql/P10_ES_CHECKPOINT.md",
    "docs/adaptation/sql/P10_ES_PLAN.md",
    "docs/decisions/ADR-027-institutional-learning.md",
    "tasks/p10-es-progress.json",
    "docs/adaptation/phase-work-progress.json",
    "docs/adaptation/phase-work-definition.json",
    "artifacts/p10-es/existing-review-final.json",
    "artifacts/p10-es/reference-review-final.json",
    "artifacts/p10-es/acceptance-review.json",
    "artifacts/p10-es/final-checks.json",
    "artifacts/p10-es/browser/result.json",
    "artifacts/p10-es/browser/final-result.json",
    "artifacts/p10-es/api-result.json",
    "artifacts/p10-es/extras-result.json",
    "artifacts/p10-es/gates-result.json",
    "artifacts/p10-es/storage-result.json",
    "artifacts/p10-es/recovery-result.json",
    "artifacts/p10-es/boundaries-result.json",
    "artifacts/p10-es/compile-result.json",
    "artifacts/p10-es/demo-result.json",
    "artifacts/p10-es/preservation-result.json",
    "artifacts/p10-es/restart-result.json",
    "artifacts/p10-es/deployment-result.json",
    "artifacts/p10-es/parent-replay-result.json",
    "artifacts/p10-es/media-result.json",
]
# Include all declared semantic sources, including Scentra, in the bounded manifest.
for name in ["p10-existing.json", "p10-reference.json"]:
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

    corpus = ROOT / ".local/p10-es" / ("final-corpus-" + uuid4().hex[:8])
    corpus.mkdir()
    (corpus / ".graphifyignore").write_text("!**/*.md\n!**/*.json\n")
    for i, n in enumerate(CODE + DOCS):
        shutil.copyfile(ROOT / n, corpus / (str(i) + "_" + Path(n).name))
    detection = detect(corpus)
    assert 0 < detection["total_files"] < 200 and detection["total_words"] < 2000000
    ast = extract(
        [ROOT / n for n in CODE],
        root=ROOT,
        cache_root=ROOT / ".local/p10-es/final-cache",
        max_workers=3,
    )
    fragments = [
        read(ROOT / "docs/adaptation/fragments" / n)
        for n in ["p10-existing.json", "p10-reference.json"]
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
            cache_root=ROOT / ".local/p10-es/final-cache",
        )
    overall = read(ROOT / "docs/adaptation/phase-work-progress.json")["summary"]
    nodes["p10_overall_progress"] = dict(
        id="p10_overall_progress",
        label="Roadmap general " + overall["overall_technical_percent_display"],
        file_type="document",
        source_file="docs/adaptation/phase-work-progress.json",
        source_location="$.summary.overall_technical_percent_display",
        domain="fixed_weight_roadmap",
    )
    for phase in read(ROOT / "docs/adaptation/phase-work-progress.json")["summary"][
        "phases"
    ]:
        key = "p10_progress_" + phase["id"]
        nodes[key] = {
            "id": key,
            "label": phase["id"] + " " + phase["work_percent_display"],
            "file_type": "document",
            "source_file": "docs/adaptation/phase-work-progress.json",
            "source_location": "$.summary.phases",
            "accepted": phase["phase_accepted"],
            "domain": "fixed_weight_roadmap",
        }
    for phase in overall["phases"]:
        edges.append(
            dict(
                source="p10_overall_progress",
                target="p10_progress_" + phase["id"],
                relation="includes_fixed_weight_criterion_work",
                confidence="EXTRACTED",
                confidence_score=1.0,
                weight=phase["criterion_denominator"],
                source_file="docs/adaptation/phase-work-progress.json",
                source_location="$.summary.phases",
                evidence_mode="calculated_fixed_weight_progress",
            )
        )
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
            "P10 institutional reviewed numeric learning: explicit purpose grants, immutable corrections, temporal/disjoint-subject datasets, train-only normalization, deterministic logistic JSON artifacts, baseline/segment evaluation, current-grant/current-revision distinct-subject shadow promotion, approved rollback while training paused, drift and typed paginated UI. This is an explicit estimator variant, not identical to Scentra HistGradientBoosting or LLM tuning. Synthetic gains do not establish institutional efficacy. Native receipts remain distinct from static review. P10 criteria4/5 locally accepted; closure depends on full P8/P9 external acceptance. General fixed-weight progress includes partial work; academics and preceding graphs preserved. Token usage unmeasured."
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
        "no está instalado; no se atribuye extracción AST a los archivos DDL. "
        "Los hashes del manifiesto incluyen el trabajo sin commit. "
        "Regeneración acotada: `python -X utf8 -B "
        "backend/tools/p10_es_graphs.py build`.\n"
    )
    report.write_text(text, encoding="utf-8")
    save(OUT / "detection.json", detection)
    save(
        OUT / "source-manifest.json",
        {
            "unit": "P10-ES",
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
