"""Offline current-project Graphify snapshot; never import CRM, .env or live data.

Historical phase graphs remain frozen. Code is AST-extracted in bounded batches;
reviewed docs/tests/configuration are file nodes, not inferred implementation.
"""
import hashlib
import json
import subprocess
from pathlib import Path

from graphify.build import build_from_json
from graphify.cluster import cluster
from graphify.export import to_html, to_json
from graphify.extract import extract

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "graphify-out/live-project-20261126"


def build():
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    files = [p for p in tracked if p and (ROOT / p).is_file() and p.startswith(
        ("backend/app/", "frontend/src/", "backend/tests/", "backend/tools/", "docs/", "tasks/")
    ) and not any(v in p.split("/") for v in ("history", "fragments", "assets", "__pycache__"))
        and Path(p).suffix in {".py", ".ts", ".tsx", ".js", ".md", ".json", ".yaml", ".toml"}]
    code = [ROOT / p for p in files if p.startswith(("backend/app/", "frontend/src/"))
            and Path(p).suffix in {".py", ".ts", ".tsx", ".js"} and ".test." not in p]
    nodes, edges = {}, []
    for start in range(0, len(code), 150):
        result = extract(code[start:start + 150], root=ROOT,
                         cache_root=ROOT / ".local/live-project-graph", max_workers=3)
        nodes.update({n["id"]: n for n in result["nodes"]})
        edges.extend(result["edges"])
        print(f"AST {min(start + 150, len(code))}/{len(code)}", flush=True)
    for p in files:
        key = "project-file:" + p
        nodes[key] = {"id": key, "label": p, "file_type": "document", "source_file": p,
                      "domain": "reviewed_project_files", "source_location": "file"}
    for n in list(nodes.values()):
        path = str(n.get("source_file", "")).replace("\\", "/")
        if path.startswith(str(ROOT).replace("\\", "/") + "/"):
            path = path[len(str(ROOT)) + 1:]
        parent = "project-file:" + path
        if parent in nodes and n["id"] != parent:
            edges.append({"source": parent, "target": n["id"], "relation": "defines",
                          "source_file": path, "confidence": "EXTRACTED"})
    # Every edge endpoint must be present; external imports remain explicit.
    for e in edges:
        for key in (e["source"], e["target"]):
            nodes.setdefault(key, {"id": key, "label": key, "file_type": "code",
                                   "source_file": e.get("source_file", ""), "domain": "external_or_resolved_reference"})
    graph = build_from_json({"nodes": list(nodes.values()), "edges": edges, "hyperedges": []}, root=ROOT, directed=True)
    communities = cluster(graph)
    OUT.mkdir(parents=True, exist_ok=True)
    to_json(graph, communities, str(OUT / "graph.json"))
    # Current Graphify returns None after a successful aggregated HTML export.
    # Validate the produced artifacts instead of relying on the old helper's bool.
    to_html(graph, communities, str(OUT / "graph.html"), node_limit=5000)
    assert (OUT / "graph.json").stat().st_size and (OUT / "graph.html").stat().st_size
    counts = {"nodes": graph.number_of_nodes(), "edges": graph.number_of_edges(), "communities": len(communities)}
    (OUT / "COVERAGE.md").write_text(
        "# Current project graph\n\nTracked runtime AST plus file-level docs/tests/tools/tasks. No SQL, CRM messages, secrets, network or LLM calls. Documentation nodes do not prove implementation or accepted roadmap criteria. Cross-file edges across extraction batches may be incomplete. Frozen historical graphs are unchanged. This developer graph is separate from private per-conversation CRM memory. The interactive view aggregates communities above 5000 nodes; JSON retains all nodes.\n", encoding="utf-8")
    manifest = {"schema": "rinova-live-project-graph-v1", "commit": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "counts": counts,
        "runtime_ast_files": len(code), "tracked_file_nodes": len(files),
        "sources": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in files},
        "external_calls": 0, "crm_data": False}
    (OUT / "source-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in manifest.items() if k != "sources"}), flush=True)


if __name__ == "__main__":
    build()
