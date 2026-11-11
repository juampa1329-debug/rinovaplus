"""Bounded incremental Graphify P11; preceding graphs are preserved."""

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "graphify-out/p11-es"
CODE = sorted({p.relative_to(ROOT).as_posix() for pattern in ["backend/app/institutional/operations*.py", "backend/tools/*p11*.py", "backend/tests/test_institutional_operations.py", "frontend/src/test/institutionOperationsP11.test.tsx"] for p in ROOT.glob(pattern)} | {"backend/app/institutional/" + n + ".py" for n in ["api", "auth", "settings", "spanish", "store", "channel_workers", "channel_outbox", "broadcast_dispatch", "campaign_runtime", "channel_events", "channel_comments", "channel_retry", "channel_workspace", "workspace", "agents", "ui_contract", "broadcasts"]} | {"frontend/src/institution/" + n for n in ["InstitutionApp.tsx", "Settings.tsx", "OperationsWorkspace.tsx", "adsResource.ts", "api.tsx"]})
DOCS = ["docs/adaptation/sql/SQL_P11_ES_REVIEW.md", "docs/adaptation/sql/P11_ES_CHECKPOINT.md", "docs/adaptation/sql/SQL_P11_ES_PLAN.md", "docs/adaptation/sql/SQL_P12_ONLINE_PLAN.md", "docs/adaptation/sql/P11_OPERATOR_RUNBOOK.md", "docs/decisions/ADR-028-local-institutional-operations.md", "tasks/p11-es-progress.json", "tasks/p12-online-backlog.json", "docs/adaptation/phase-work-progress.json", "docs/adaptation/phase-work-definition.json", "backend/operations/cbn_institutional_operations_v1/contract.json", "backend/operations/cbn_institutional_operations_v1/release.json", "compose.operations.yaml", "docker/Dockerfile.operations", "docker/nginx.operations.conf", "docker/Dockerfile.operations.dockerignore", "frontend/src/institution/institution.css", "artifacts/p11-es/access-review.json", "artifacts/p11-es/operations-review.json", "artifacts/p11-es/acceptance-review.json", "artifacts/p11-es/final-checks.json", "artifacts/p11-es/criteria-matrix.json", "artifacts/p11-es/failures.json"]
DOCS += ["artifacts/p11-es/" + n + "-result.json" for n in ["access", "workers", "recovery", "final-recovery", "boundaries", "preservation", "restart", "deployment", "parent-replay", "media", "reversal", "extras", "guards", "performance"]]
DOCS += ["artifacts/p11-es/browser/" + n + "-result.json" for n in ["routes", "states", "final", "mobile-light", "errors"]]
for name in ["p11-access.json", "p11-operations.json"]:
    fragment = json.loads((ROOT / "docs/adaptation/fragments" / name).read_text(encoding="utf-8"))
    for item in fragment["nodes"] + fragment["edges"] + fragment.get("hyperedges", []):
        source = item.get("source_file")
        if source and source not in CODE + DOCS:
            (CODE if Path(source).suffix in {".py", ".sql", ".js", ".jsx", ".tsx", ".ts"} else DOCS).append(source)
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

    corpus = ROOT / ".local/p11-es" / ("final-corpus-" + uuid4().hex[:8])
    corpus.mkdir()
    (corpus / ".graphifyignore").write_text("!**/*.md\n!**/*.json\n")
    for i, n in enumerate(CODE + DOCS):
        shutil.copyfile(ROOT / n, corpus / (str(i) + "_" + Path(n).name))
    detection = detect(corpus)
    assert 0 < detection["total_files"] < 200 and detection["total_words"] < 2000000
    ast = extract(
        [ROOT / n for n in CODE],
        root=ROOT,
        cache_root=ROOT / ".local/p11-es/final-cache",
        max_workers=3,
    )
    fragments = [
        read(ROOT / "docs/adaptation/fragments" / n)
        for n in ["p11-access.json", "p11-operations.json"]
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
            cache_root=ROOT / ".local/p11-es/final-cache",
        )
    overall = read(ROOT / "docs/adaptation/phase-work-progress.json")["summary"]
    nodes["p11_overall_progress"] = dict(
        id="p11_overall_progress",
        label="Roadmap general " + overall["overall_technical_percent_display"],
        file_type="document",
        source_file="docs/adaptation/phase-work-progress.json",
        source_location="$.summary.overall_technical_percent_display",
        domain="fixed_weight_roadmap",
    )
    for phase in read(ROOT / "docs/adaptation/phase-work-progress.json")["summary"][
        "phases"
    ]:
        key = "p11_progress_" + phase["id"]
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
                source="p11_overall_progress",
                target="p11_progress_" + phase["id"],
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
            "P11 local operations on a new SQL2019 native P10 copy: unchanged185-table schema, own principal/profile, complete fresh catalog/journal/ACL guards, effective role/action and route boundaries, eight-consumer pulse, liveness versus readiness, full grouped queues, signed restore receipt and private blobs, UI loading/error/path isolation, themes/mobile/keyboard and rollback. Static extraction and native/API/UI receipts remain separate. No external commissioning, institution-wide RPO/RTO or full DBSIIE mapping is claimed. P12 groups existing external dependencies without reweighting56criteria/279milestones or double credit. Previous graphs/releases/readers/copies remain intact. Tokens are unmeasured."
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
        "P11 no añade DDL: conserva el modelo P10 validado en SQL2019. Este "
        "grafo cubre operación, autoridad, recuperación y dependencias; no es un "
        "ERD completo de las185 tablas ni las330 FK. El parser SQL opcional "
        "de tree-sitter no está instalado; no se atribuye AST SQL a este corte. "
        "Los hashes del manifiesto incluyen el trabajo sin commit. "
        "Regeneración acotada: `python -X utf8 -B "
        "backend/tools/p11_es_graphs.py build`.\n"
    )
    report.write_text(text, encoding="utf-8")
    save(OUT / "detection.json", detection)
    save(
        OUT / "source-manifest.json",
        {
            "unit": "P11-ES",
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
            "sql_ddl_coverage": "inherited_P10_native_catalog_operations_graph_not_full_ERD",
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
