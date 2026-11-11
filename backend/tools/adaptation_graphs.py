"""Build offline Graphify maps and verify the adaptation continuity checkpoint.

Run with the Python interpreter that already has Graphify installed.
Never imports the CRM application, loads .env, connects to SQL or calls an LLM.
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

from historical_checkpoint import (
    changed_source_paths,
    checkpoint_statuses,
    verify_active_checkpoint,
    verify_historical_manifest,
)

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "graphify-out"
SCOPE = ROOT / "docs/adaptation/scope.json"
FRAGMENTS = ROOT / "docs/adaptation/fragments"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path):
    import os

    return Path(os.path.relpath(path, ROOT)).as_posix()


def git(root, *args):
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True, encoding="utf-8"
    ).strip()


def render(extraction, output, detection, coverage_note=None):
    from graphify.analyze import god_nodes, suggest_questions, surprising_connections
    from graphify.build import build_from_json
    from graphify.cluster import cluster, score_all
    from graphify.export import to_html, to_json
    from graphify.report import generate

    output.mkdir(parents=True, exist_ok=True)
    graph = build_from_json(extraction, root=ROOT, directed=True)
    if not graph.number_of_nodes():
        raise ValueError("Graphify produced an empty graph")
    communities = cluster(graph)
    labels = {}
    for cid, members in communities.items():
        paths = Counter(
            graph.nodes[n].get("domain")
            or "/".join(
                str(graph.nodes[n].get("source_file", ""))
                .replace("\\", "/")
                .split("/")[:4]
            )
            for n in members
        )
        labels[cid] = paths.most_common(1)[0][0] or f"Comunidad {cid}"
    cohesion = score_all(graph, communities)
    hubs = god_nodes(graph)
    surprises = surprising_connections(graph, communities)
    questions = suggest_questions(graph, communities, labels)
    if not to_json(
        graph, communities, str(output / "graph.json"), community_labels=labels
    ):
        raise ValueError(
            "Graphify refused a smaller graph; "
            "inspect scope/deletions before rebuilding"
        )
    if graph.number_of_nodes() > 5000:
        print("Large graph: HTML uses the Graphify community view.")
    if not to_html(
        graph,
        communities,
        str(output / "graph.html"),
        community_labels=labels,
        node_limit=5000,
    ):
        raise ValueError("Graphify did not export graph.html")
    report = generate(
        graph,
        communities,
        cohesion,
        labels,
        hubs,
        surprises,
        detection,
        {"input": 0, "output": 0},
        str(ROOT),
        suggested_questions=questions,
        built_at_commit=git(ROOT, "rev-parse", "HEAD"),
    )
    note = (
        "\n\n"
        + (
            coverage_note
            or "Coverage: offline source inspection only. Token counters refer to "
            "external Graphify API calls (none); chat/subagent usage is not measured "
            "here. SQL schema, provider behaviour and production are not certified "
            "by this graph. Reviewed/planned edges do not represent "
            "implemented features."
        )
        + "\n"
    )
    (output / "GRAPH_REPORT.md").write_text(report + note, encoding="utf-8")
    write(output / ".graphify_labels.json", {str(k): v for k, v in labels.items()})
    (output / ".graphify_python").write_text(sys.executable, encoding="utf-8")
    write(
        output / "analysis.json",
        {
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
            "communities": len(communities),
            "hubs": hubs,
            "surprises": surprises,
            "questions": questions,
        },
    )
    return {
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "communities": len(communities),
    }


def reviewed_graph(scope, fragments):
    nodes, edges = [], []
    for phase in scope["phases"]:
        nodes.append(
            {
                "id": phase["id"],
                "label": phase["id"] + " " + phase["title"],
                "file_type": "document",
                "source_file": str(SCOPE),
                "status": phase["status"],
            }
        )
        for dependency in phase["depends_on"]:
            edges.append(
                {
                    "source": phase["id"],
                    "target": dependency,
                    "relation": "planned_dependency",
                    "confidence": "EXTRACTED",
                    "confidence_score": 1.0,
                    "source_file": str(SCOPE),
                }
            )
    for fragment_path, fragment in fragments:
        nodes.extend(fragment.get("graph", {}).get("nodes", []))
        edges.extend(fragment.get("graph", {}).get("edges", []))
        for finding in fragment["findings"]:
            key = finding["id"]
            phase = scope["finding_phases"][key]
            nodes.append(
                {
                    "id": key,
                    "label": finding["capability"],
                    "file_type": "document",
                    "source_file": str(fragment_path),
                    "status": finding["status"],
                    "phase": phase,
                }
            )
            edges.append(
                {
                    "source": key,
                    "target": phase,
                    "relation": "planned_for",
                    "confidence": "EXTRACTED",
                    "confidence_score": 1.0,
                    "source_file": str(SCOPE),
                }
            )
            for kind in ("source", "target"):
                for evidence in finding[kind]:
                    path = (ROOT / evidence["file"]).resolve()
                    file_id = (
                        "evidence_"
                        + hashlib.sha256(relative(path).lower().encode()).hexdigest()[
                            :20
                        ]
                    )
                    nodes.append(
                        {
                            "id": file_id,
                            "label": relative(path),
                            "file_type": "document" if path.suffix == ".md" else "code",
                            "source_file": relative(path),
                            "source_location": f"L{evidence['line']}",
                            "project": "Scentra" if kind == "source" else "CRM_CBN",
                        }
                    )
                    edges.append(
                        {
                            "source": key,
                            "target": file_id,
                            "relation": "reference_implementation"
                            if kind == "source"
                            else "current_implementation",
                            "confidence": "EXTRACTED",
                            "confidence_score": 1.0,
                            "source_file": str(fragment_path),
                        }
                    )
    return {
        "nodes": nodes,
        "edges": edges,
        "hyperedges": [],
        "input_tokens": 0,
        "output_tokens": 0,
    }


def write_matrix(scope, fragments):
    findings = [f for _, fragment in fragments for f in fragment["findings"]]
    lines = [
        "# Matriz de paridad Scentra y CRM CBN",
        "",
        f"Fecha: {scope['date']}. {len(findings)} hallazgos de inspección estática. "
        "Ninguno certifica SQL, navegador del producto o proveedor en este equipo. "
        "Cada etapa del roadmap conserva sus aceptaciones propias.",
        "",
        "Los estados describen la fuente actual. «Parcial» no significa fallido ni "
        "operativo en producción; «por preservar» identifica trabajo útil. Los "
        "fragmentos JSON conservan toda la evidencia, la aceptación y relaciones "
        "revisadas. Tabla generada por `backend/tools/adaptation_graphs.py`; "
        "editar los fragmentos y regenerar.",
        "",
        "| ID | Capacidad | Estado de fuente | Etapa |",
        "|---|---|---|---|",
    ]
    for finding in findings:
        lines.append(
            f"| {finding['id']} | {finding['capability'].replace('|', '/')} | "
            f"{finding['status'].replace('_', ' ')} | "
            f"{scope['finding_phases'][finding['id']]} |"
        )
    for path, fragment in fragments:
        lines.extend(
            [
                "",
                "## " + fragment["domain"],
                "",
                f"Evidencia estructurada: [{path.name}](fragments/{path.name}).",
            ]
        )
        for finding in fragment["findings"]:
            lines.extend(
                [
                    "",
                    f"### {finding['id']} — {finding['capability']}",
                    "",
                    "**Diferencia:** " + finding["gap"],
                    "",
                    "**Aceptación:** " + finding["acceptance"],
                    "",
                ]
            )
            for kind, label in (("source", "Scentra"), ("target", "CRM CBN")):
                refs = []
                for evidence in finding[kind]:
                    rel = relative((ROOT / evidence["file"]).resolve())
                    refs.append(
                        f"[{rel}:{evidence['line']}](../../{rel}#L{evidence['line']})"
                    )
                lines.append(f"**{label}:** " + ", ".join(refs) + ".")
    (ROOT / "docs/adaptation/PARITY_MATRIX.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def check(scope, fragments):
    findings = [f for _, fragment in fragments for f in fragment["findings"]]
    ids = [f["id"] for f in findings]
    if len(ids) != len(set(ids)) or set(ids) != set(scope["finding_phases"]):
        raise ValueError(
            "Finding IDs must be unique and every finding must have a phase"
        )
    phases = {phase["id"] for phase in scope["phases"]}
    if any(phase not in phases for phase in scope["finding_phases"].values()):
        raise ValueError("Unknown phase")
    import networkx as nx

    dependencies = nx.DiGraph(
        (p["id"], d) for p in scope["phases"] for d in p["depends_on"]
    )
    if not nx.is_directed_acyclic_graph(dependencies):
        raise ValueError("Phase dependencies contain a cycle")
    for finding in findings:
        for evidence in finding["source"] + finding["target"]:
            if Path(evidence["file"]).is_absolute():
                raise ValueError(
                    "Evidence paths must be relative to the CRM project root"
                )
            path = (ROOT / evidence["file"]).resolve()
            if not path.is_file() or not 1 <= evidence["line"] <= len(
                path.read_text(encoding="utf-8-sig").splitlines()
            ):
                raise ValueError(f"Invalid evidence: {path}:{evidence['line']}")
    for _, fragment in fragments:
        graph = fragment.get("graph", {})
        for item in graph.get("nodes", []) + graph.get("edges", []):
            location = item.get("source_location") or ""
            if re.fullmatch(r"L[1-9][0-9]*", location):
                path = (ROOT / item["source_file"]).resolve()
                if not path.is_file() or int(location[1:]) > len(
                    path.read_text(encoding="utf-8-sig").splitlines()
                ):
                    raise ValueError(
                        "Invalid semantic evidence: "
                        + item["source_file"]
                        + ":"
                        + location
                    )
    for graph_path in [
        OUT / "graph.json",
        OUT / "adaptation/graph.json",
        OUT / "sql-inventory/graph.json",
        OUT / "sql-observed/graph.json",
        OUT / "sql-comparison/graph.json",
        OUT / "sql-comparison-active/graph.json",
        OUT / "sql-foundation/graph.json",
    ]:
        if not graph_path.exists():
            continue
        data = read(graph_path)
        node_ids = {n["id"] for n in data["nodes"]}
        for edge in data.get("links", data.get("edges", [])):
            if edge["source"] not in node_ids or edge["target"] not in node_ids:
                raise ValueError(f"Dangling edge: {graph_path}")
    print(
        f"Validated {len(findings)} findings, evidence locations "
        f"and {len(phases)} acyclic phases."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Read-only: verify evidence, dependencies, graphs and source hashes",
    )
    args = parser.parse_args()
    verify_historical_manifest(OUT / "source-manifest.json", "files")
    scope = read(SCOPE)
    fragments = [(p, read(p)) for p in sorted(FRAGMENTS.glob("*.json"))]
    check(scope, fragments)
    active_accepted = verify_active_checkpoint()
    stages = checkpoint_statuses()
    if args.check:
        manifest_path = OUT / "source-manifest.json"
        if not manifest_path.is_file():
            raise ValueError("Build the graph before checking its manifest")
        for graph_path in (OUT / "graph.json", OUT / "adaptation/graph.json"):
            if not graph_path.is_file():
                raise ValueError(f"Missing graph: {graph_path}")
        for record in read(manifest_path)["files"]:
            path = (ROOT / record["path"]).resolve()
            if not path.is_file() or digest(path) != record["sha256"]:
                raise ValueError(
                    f"Changed source: {record['path']}; rebuild and review its evidence"
                )
        print("Source fingerprints match the continuity checkpoint.")
        if (ROOT / "docs/adaptation/sql/inventory.json").is_file():
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "backend/tools/inventory_migrations.py"),
                    "--check",
                ],
                check=True,
            )
        if (ROOT / "docs/adaptation/sql/inventory.active.json").is_file():
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "backend/tools/inventory_migrations.py"),
                    "--active",
                    "--check",
                ],
                check=True,
            )
        if (ROOT / "docs/adaptation/sql/migration-plan.json").is_file():
            subprocess.run(
                [sys.executable, str(ROOT / "backend/tools/check_migration_plan.py")],
                check=True,
            )
        if (ROOT / "docs/adaptation/sql/observed-schema.json").is_file():
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "backend/tools/observed_sql_graph.py"),
                    "--check",
                ],
                check=True,
            )
        if (ROOT / "docs/adaptation/sql/horariosiie-comparison.json").is_file():
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "backend/tools/compare_horariosiie.py"),
                    "--check",
                ],
                check=True,
            )
        if (ROOT / "backend/migrations/cbn_foundation/release.json").is_file():
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "backend/tools/foundation_graph.py"),
                    "--check",
                ],
                check=True,
            )
        if (ROOT / "docs/adaptation/sql/horariosiie-comparison.active.json").is_file():
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "backend/tools/compare_horariosiie.py"),
                    "--active",
                    "--check",
                ],
                check=True,
            )
        return
    from graphify.detect import detect, save_manifest
    from graphify.extract import extract

    write_matrix(scope, fragments)
    files, scans = [], []
    for layer in ("backend/app", "frontend/src"):
        detected = detect(ROOT / layer)
        code = [Path(p) for p in detected["files"].get("code", [])]
        if len(code) > 200:
            raise ValueError(
                f"Split the {layer} extraction into smaller approved scopes"
            )
        files.extend(code)
        scans.append(
            {
                "root": layer,
                "code_files": len(code),
                "words": detected.get("total_words", 0),
                "skipped_sensitive_count": len(detected.get("skipped_sensitive", [])),
            }
        )
    print("Scoped runtime corpus:", json.dumps(scans))
    extraction = extract(files, root=ROOT, cache_root=ROOT, max_workers=4)
    detection = {
        "total_files": len(files),
        "total_words": sum(s["words"] for s in scans),
        "files": {"code": [str(p) for p in files]},
    }
    code_stats = render(extraction, OUT, detection)
    adaptation = reviewed_graph(scope, fragments)
    adaptation_stats = render(
        adaptation,
        OUT / "adaptation",
        {
            "total_files": len(fragments) + 1,
            "total_words": 0,
            "files": {"document": [str(p) for p, _ in fragments] + [str(SCOPE)]},
        },
    )
    source = (ROOT / scope["source_project"]).resolve()
    evidence_files = {
        (ROOT / e["file"]).resolve()
        for _, fragment in fragments
        for f in fragment["findings"]
        for e in f["source"] + f["target"]
    }
    migrations = set((ROOT / "backend/migrations").glob("*.sql"))
    checkpoint_files = [
        ROOT / p
        for p in (
            "AGENTS.md",
            "README.md",
            "docs/SCENTRA_ADAPTATION_ROADMAP.md",
            "docs/adaptation/PARITY_MATRIX.md",
            "docs/adaptation/INFORMATION_DESIGN.md",
            "docs/adaptation/ARCHITECTURE.md",
            "docs/adaptation/RESUME.md",
            "docs/adaptation/GRAPH_GUIDE.md",
            "docs/decisions/ADR-011-scentra-educational-fork.md",
            "ai-memory/CURRENT_STATE.md",
            "ai-memory/CRITICAL_WARNINGS.md",
            "ai-memory/FILE_MAP.md",
            "tasks/TASK_STATE.md",
            "backend/tools/adaptation_graphs.py",
        )
    ]
    checkpoint_files.extend(
        ROOT / p
        for p in (
            ".env.example",
            "compose.yaml",
            "docs/configuration.md",
            "docs/decisions/ADR-012-sql-target-contract.md",
            "backend/tests/conftest.py",
            "backend/tests/test_sql_target.py",
            "backend/tests/test_catalog.py",
            "backend/tests/test_sql_workspace.py",
            "backend/tests/test_container_config.py",
            "docs/decisions/ADR-013-migration-lifecycle.md",
            "backend/tools/check_migration_plan.py",
            ".dockerignore",
            "Dockerfile",
            "docker/Dockerfile.development",
            "compose.local-sql.yaml",
            "docs/decisions/ADR-014-database-selection.md",
            "backend/tools/observed_sql_graph.py",
            "backend/tools/compare_horariosiie.py",
            "backend/tools/cbn_foundation.py",
            "backend/tools/foundation_snapshot.py",
            "backend/tools/foundation_contract.py",
            "backend/tools/rehearse_foundation.py",
            "backend/tools/foundation_rehearsal_checks.py",
            "backend/tools/foundation_graph.py",
            "backend/tools/historical_checkpoint.py",
            "backend/tests/test_foundation.py",
            "docs/decisions/ADR-015-foundation-restored-rehearsal.md",
            "backend/tests/test_database_connections.py",
            "frontend/src/features/DatabaseSettings.test.tsx",
        )
    )
    for directory, pattern in (
        ("backend/tools", "*foundation*.py"),
        ("backend/tools", "sql_c4*.py"),
        ("backend/tools", "sql_c5*.py"),
        ("backend/tests", "test_foundation*.py"),
        ("backend/tests", "test_sql_c4*.py"),
        ("backend/tests", "test_sql_c5*.py"),
        ("docs/decisions", "ADR-016*.md"),
        ("docs/decisions", "ADR-017*.md"),
        ("docs/adaptation/sql", "SQL_C4*"),
        ("docs/adaptation/sql", "sql_c4*"),
        ("docs/adaptation/fragments", "sql-c4*.json"),
        ("docs/adaptation/sql", "SQL_C5*"),
        ("docs/adaptation/sql", "sql_c5*"),
        ("docs/adaptation/fragments", "sql-c5*.json"),
    ):
        checkpoint_files.extend(
            p for p in (ROOT / directory).glob(pattern) if p.is_file()
        )
    if active_accepted:
        checkpoint_files.extend(changed_source_paths())
    sql_artifacts = {
        p
        for p in (ROOT / "docs/adaptation/sql").rglob("*")
        if p.is_file() and p.suffix in {".json", ".md"}
    }
    sql_tool = ROOT / "backend/tools/inventory_migrations.py"
    sql_inputs = {sql_tool} if sql_tool.is_file() else set()
    snapshot_files = (
        set(files)
        | evidence_files
        | migrations
        | {
            SCOPE,
            ROOT / ".graphifyignore",
            ROOT / "docs/adaptation/validation.json",
            ROOT
            / "docs/design/settings-reference"
            / "scentra-settings-specification-2026-10-13.md",
        }
        | {p for p, _ in fragments}
        | set(checkpoint_files)
        | sql_artifacts
        | sql_inputs
        | {
            p
            for p in (ROOT / "backend/migrations/cbn_foundation").glob("*")
            if p.is_file() and p.suffix in {".sql", ".json"}
        }
    )
    sql_stats = (
        read(OUT / "sql-inventory/analysis.json")
        if (OUT / "sql-inventory/analysis.json").is_file()
        else None
    )
    observed_stats = (
        read(OUT / "sql-observed/analysis.json")
        if (OUT / "sql-observed/analysis.json").is_file()
        else None
    )
    comparison_stats = (
        read(OUT / "sql-comparison/analysis.json")
        if (OUT / "sql-comparison/analysis.json").is_file()
        else None
    )
    foundation_stats = (
        read(OUT / "sql-foundation/analysis.json")
        if (OUT / "sql-foundation/analysis.json").is_file()
        else None
    )
    write(
        OUT / "source-manifest.json",
        {
            "date": scope["date"],
            "timezone": scope["timezone"],
            "source_commit": git(source, "rev-parse", "HEAD"),
            "target_commit": git(ROOT, "rev-parse", "HEAD"),
            "target_branch": git(ROOT, "branch", "--show-current"),
            "working_trees": (
                "Existing uncommitted changes are included; "
                "commit hashes alone do not identify these snapshots."
            ),
            "scans": scans,
            "code_graph": code_stats,
            "adaptation_graph": adaptation_stats,
            "sql_graph": {k: sql_stats[k] for k in ("nodes", "edges", "communities")}
            if sql_stats
            else None,
            "sql_coverage": (
                "Immutable historical inventory.json is retained; current "
                "consumers are in inventory.active.json. Declarations are "
                "inventoried offline in sql-inventory; "
                "separate from runtime AST, not a live schema or T-SQL compilation."
            )
            if sql_stats
            else (
                "Migration files fingerprinted and manually referenced; "
                "SQL is not parsed by this runtime-code graph."
            ),
            "sql_observed_graph": {
                k: observed_stats[k] for k in ("nodes", "edges", "communities")
            }
            if observed_stats
            else None,
            "sql_observed_coverage": (
                "Separate captured SQL catalog metadata graph; user-confirmed "
                "fragment, not full drift or SQL2019 acceptance. "
                "Build is offline, no live refresh."
            ),
            "sql_comparison_graph": {
                k: comparison_stats[k] for k in ("nodes", "edges", "communities")
            }
            if comparison_stats
            else None,
            "sql_foundation_graph": {
                k: foundation_stats[k] for k in ("nodes", "edges", "communities")
            }
            if foundation_stats
            else None,
            "sql_c4_checkpoint": stages.get("SQL-C4", "not_yet_recorded"),
            "sql_c5_checkpoint": stages.get("SQL-C5", "not_yet_recorded"),
            "sql_checkpoint_chain": stages,
            "files": [
                {"path": relative(p), "sha256": digest(p)}
                for p in sorted(snapshot_files)
            ],
        },
    )
    save_manifest({"code": [str(p) for p in files]}, root=ROOT)
    (OUT / ".graphify_root").write_text(str(ROOT), encoding="utf-8")
    check(scope, fragments)
    print(json.dumps({"code": code_stats, "adaptation": adaptation_stats}))


if __name__ == "__main__":
    main()
