"""Bounded incremental Graphify P7 evidence; no preceding graph is rebuilt."""

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "graphify-out/p7-es"
CODE = sorted(
    {
        p.relative_to(ROOT).as_posix()
        for pattern in [
            "backend/app/institutional/broadcast*.py",
            "backend/tools/*p7*.py",
            ("backend/migrations/cbn_broadcast_operations_v1/*.sql"),
            "backend/tests/test_institutional_broadcasts.py",
            "frontend/src/test/institutionBroadcastP7.test.tsx",
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
            "channel_outbox",
            "channel_events",
            "channel_workers",
            "channel_retry",
            "channel_workspace",
            "ui_contract",
            "agents",
        ]
    }
    | {
        "frontend/src/institution/" + n + ".tsx"
        for n in ["BroadcastWorkspace", "InstitutionApp", "api"]
    }
    | {
        "backend/tools/foundation_snapshot.py",
        "backend/app/modules/channels/providers.py",
    }
)
DOCS = [
    "docs/adaptation/sql/SQL_P7_ES_REVIEW.md",
    "docs/adaptation/phase-work-progress.json",
    "artifacts/p7-es/final-review.json",
    "artifacts/p7-es/reference-final-review.json",
    "artifacts/p7-es/acceptance-review.json",
    "artifacts/p7-es/final-checks.json",
    "artifacts/p7-es/browser/result.json",
    "artifacts/p7-es/browser/final-result.json",
    *(
        "artifacts/p7-es/" + n + "-result.json"
        for n in [
            "api",
            "runtime",
            "extras",
            "storage",
            "recovery",
            "catalog",
            "compile",
            "demo",
            "preservation",
            "restart",
            "deployment",
            "media",
            "parent-replay",
        ]
    ),
]


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

    corpus = ROOT / ".local/p7-es" / ("final-corpus-" + uuid4().hex[:8])
    corpus.mkdir()
    (corpus / ".graphifyignore").write_text("!**/*.md\n!**/*.json\n")
    for i, n in enumerate(CODE + DOCS):
        shutil.copyfile(ROOT / n, corpus / (str(i) + "_" + Path(n).name))
    detection = detect(corpus)
    assert 0 < detection["total_files"] < 120 and detection["total_words"] < 500000
    ast = extract(
        [ROOT / n for n in CODE],
        root=ROOT,
        cache_root=ROOT / ".local/p7-es/final-cache",
        max_workers=3,
    )
    fragments = [
        read(ROOT / "docs/adaptation/fragments" / n)
        for n in ["p7-final.draft.json", "p7-reference-final.draft.json"]
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
            cache_root=ROOT / ".local/p7-es/final-cache",
        )
    for phase in read(ROOT / "docs/adaptation/phase-work-progress.json")["summary"][
        "phases"
    ]:
        key = "p7_progress_" + phase["id"]
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
            "P7 native SQL2019/C10 WhatsApp broadca"
            "st integration: template catalog/provi"
            "der approval origin, typed body/header"
            "/button variables, educational audienc"
            "e/consent/exclusions, UTC schedule, ac"
            "count cadence reserved at actual POST "
            "frontier, one durable queue with immut"
            "able attempts, safe selective retry, u"
            "ncertain effects and explicit-context "
            "reply attribution. Report CSV is filte"
            "red and formula-safe. Local SQL/API/br"
            "owser/storage/recovery evidence is dis"
            "tinct from static source graphs. Main "
            "preview contains operator drafts and n"
            "o marketing consent or provider effect"
            "s. Catalog and receipts from real Meta"
            " plus P4 closure remain pending; P7 te"
            "chnical82.29%, criteria2/5. Catalog mo"
            "dule/constraint/trigger definitions us"
            "e equivalent set joins; real SQL/conta"
            "iner restarts qualified separately. No"
            " academic DDL/DML or previous-copy red"
            "irection. Old graphs frozen; token usa"
            "ge not measured."
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
        "backend/tools/p7_es_graphs.py build`.\n"
    )
    report.write_text(text, encoding="utf-8")
    save(OUT / "detection.json", detection)
    save(
        OUT / "source-manifest.json",
        {
            "unit": "P7-ES",
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
