"Small Graphify extension for the single integrated preview and persisted demo."

import hashlib
import json
import shutil
import uuid
from pathlib import Path

from adaptation_graphs import render
from graphify.cache import save_semantic_cache
from graphify.detect import detect
from graphify.extract import extract

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "graphify-out/current-preview"
CODE = [
    "backend/tools/prepare_demo_preview.py",
    "backend/tools/check_current_preview.py",
    "backend/tests/test_demo_preview.py",
]
DOCS = [
    "docs/adaptation/PREVIEW_STATUS.md",
    "docs/adaptation/phase-work-progress.json",
    "graphify-out/p3-es/source-manifest.json",
    ("docs/adaptation/fragments/current-preview.draft.json"),
] + [
    "artifacts/current-preview/" + n
    for n in [
        "seed-result.json",
        "sql-result.json",
        "browser-result.json",
        "restart-result.json",
        "deployment-result.json",
        "semantic-review.json",
    ]
]


def read(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(p, v):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(v, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


corpus = ROOT / ".local/current-preview" / ("graph-" + uuid.uuid4().hex[:8])
corpus.mkdir()
(corpus / ".graphifyignore").write_text("!**/*.md\n!**/*.json\n")
for i, n in enumerate(CODE + DOCS):
    shutil.copyfile(ROOT / n, corpus / (str(i) + "_" + Path(n).name))
d = detect(corpus)
assert 0 < d["total_files"] < 200 and d["total_words"] < 2000000
save(OUT / "detection.json", d)
a = extract(
    [ROOT / n for n in CODE],
    root=ROOT,
    cache_root=ROOT / ".local/current-preview/graph-cache",
    max_workers=3,
)
f = read(ROOT / ("docs/adaptation/fragments/current-preview.draft.json"))
nodes = {n["id"]: n for n in a["nodes"] + f["nodes"]}
edges = a["edges"] + f["edges"]
save_semantic_cache(
    f["nodes"],
    f["edges"],
    f.get("hyperedges", []),
    root=ROOT,
    allowed_source_files=[ROOT / n["source_file"] for n in f["nodes"]],
    cache_root=ROOT / ".local/current-preview/graph-cache",
)
work = read(ROOT / "docs/adaptation/phase-work-progress.json")
for p in work["summary"]["phases"]:
    identity = "preview_phase_" + p["id"]
    nodes[identity] = {
        "id": identity,
        "label": p["id"] + " " + p["work_percent_display"],
        "file_type": "document",
        "source_file": "docs/adaptation/phase-work-progress.json",
        "source_location": "$.summary.phases",
        "accepted": p["phase_accepted"],
        "domain": "unchanged_roadmap",
    }
for e in edges:
    for identity in [e["source"], e["target"]]:
        if identity not in nodes:
            nodes[identity] = {
                "id": identity,
                "label": identity,
                "file_type": "document",
                "source_file": e["source_file"],
                "source_location": e.get("source_location"),
                "domain": "explicit_context",
            }
counts = render(
    {
        **a,
        "nodes": list(nodes.values()),
        "edges": edges,
        "hyperedges": f.get("hyperedges", []),
    },
    OUT,
    d,
    coverage_note=(
        "One CRM application: same P3 R6 image at"
        "4178, persisted fictional SQL2019 copy,8"
        "contacts/8conversations/26messages/8note"
        "s/8tasks. Previous clean copy/profile/im"
        "age retained. No real provider operation"
        " or academic writes. Nine demo business "
        "tables survive application restart. Road"
        "map percentages and frozen P3 graph unch"
        "anged; P1/P2/P3 evidence replays indepen"
        "dently. Semantic review is source/report"
        " inspection, not another SQL/browser exe"
        "cution; chat token usage is not measured"
        " here."
    ),
)
save(
    OUT / "source-manifest.json",
    {
        "unit": "PREVIEW-DEMO-1",
        **counts,
        "sources": {n: sha(ROOT / n) for n in CODE + DOCS},
        "artifacts": {
            n: sha(OUT / n)
            for n in ["graph.json", "graph.html", "GRAPH_REPORT.md", "detection.json"]
        },
        "old_graphs_rebuilt": False,
    },
)
print(json.dumps({"bounded_files": d["total_files"], **counts}))
