"""Build/check the observed SQL metadata graph offline. Never connect to SQL."""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs/adaptation/sql/observed-schema.json"
OUTPUT = ROOT / "graphify-out/sql-observed"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def node_id(kind, *parts):
    key = json.dumps(parts, ensure_ascii=True).encode()
    return "observed_" + kind + "_" + hashlib.sha256(key).hexdigest()[:24]


def build(data):
    nodes, edges = [], []
    source = SOURCE.relative_to(ROOT).as_posix()
    database = node_id("database", data["database"])
    nodes.append(
        {
            "id": database,
            "label": data["database"] + " · fragmento observado",
            "file_type": "document",
            "source_file": source,
        }
    )

    def edge(a, b, relation, location):
        edges.append(
            {
                "source": a,
                "target": b,
                "relation": relation,
                "confidence": "EXTRACTED",
                "confidence_score": 1.0,
                "source_file": source,
                "source_location": location,
            }
        )

    for index, table in enumerate(data["tables"]):
        schema, name = table["schema"], table["name"]
        key = node_id("table", schema, name)
        nodes.append(
            {
                "id": key,
                "label": schema + "." + name,
                "file_type": "document",
                "source_file": source,
                "source_location": f"/tables/{index}",
                "observed": True,
            }
        )
        edge(database, key, "observed_table", f"/tables/{index}")
        for j, column in enumerate(table["columns"]):
            col = node_id("column", schema, name, column["name"])
            location = f"/tables/{index}/columns/{j}"
            nodes.append(
                {
                    "id": col,
                    "label": name + "." + column["name"],
                    "file_type": "document",
                    "source_file": source,
                    "source_location": location,
                    "sql_type": column["type"],
                    "nullable": column["nullable"],
                }
            )
            edge(key, col, "observed_column", location)
    for index, fk in enumerate(data["foreign_keys"]):
        location = f"/foreign_keys/{index}"
        key = node_id("fk", fk["source_schema"], fk["source_table"], fk["name"])
        nodes.append(
            {
                "id": key,
                "label": fk["name"],
                "file_type": "document",
                "source_file": source,
                "source_location": location,
                "disabled": fk["disabled"],
                "not_trusted": fk["not_trusted"],
            }
        )
        edge(
            key,
            node_id("table", fk["source_schema"], fk["source_table"]),
            "observed_fk_source",
            location,
        )
        edge(
            key,
            node_id("table", fk["target_schema"], fk["target_table"]),
            "observed_fk_target",
            location,
        )
        for column in fk["columns"]:
            edge(
                key,
                node_id(
                    "column", fk["source_schema"], fk["source_table"], column["source"]
                ),
                "observed_source_column",
                location,
            )
            edge(
                key,
                node_id(
                    "column", fk["target_schema"], fk["target_table"], column["target"]
                ),
                "observed_target_column",
                location,
            )
    ids = {n["id"] for n in nodes}
    if len(ids) != len(nodes) or any(
        e[k] not in ids for e in edges for k in ("source", "target")
    ):
        raise ValueError("Duplicate node or dangling metadata relationship")
    return {"nodes": nodes, "edges": edges}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    graph = build(data)
    counts = {
        "tables": len(data["tables"]),
        "columns": sum(len(t["columns"]) for t in data["tables"]),
        "foreign_keys": len(data["foreign_keys"]),
    }
    expected = data["review"]
    if list(counts.values()) != [
        expected["table_count"],
        expected["column_count"],
        expected["relation_count"],
    ]:
        raise ValueError("Observed counts do not match the capture")
    if digest(ROOT / data["query_source"]) != data["query_source_sha256"]:
        raise ValueError(
            "Query source changed after capture; review/recollect before updating"
        )
    manifest = {
        "source_sha256": digest(SOURCE),
        "tool_sha256": digest(Path(__file__)),
        "scope": data["verification"],
        "counts": counts,
        "nodes": len(graph["nodes"]),
        "edges": len(graph["edges"]),
    }
    path = OUTPUT / "source-manifest.json"
    if args.check:
        if json.loads(path.read_text(encoding="utf-8")) != manifest:
            raise ValueError("Observed metadata graph checkpoint is stale")
        print("Observed metadata checkpoint verified:", json.dumps(counts))
        return
    from adaptation_graphs import render

    stats = render(
        graph,
        OUTPUT,
        {"total_files": 1, "total_words": 0},
        coverage_note=(
            "Coverage: offline rendering of live read-only SQL catalog metadata "
            "captured on 2026-10-24. HORARIOSSIIE is a user-confirmed fragment. "
            "No business rows, migration execution, full drift acceptance or "
            "institutional SQL Server 2019 certification. Sources and query code "
            "are fingerprinted; this graph does not refresh SQL. "
            "Token counters cover external Graphify API calls only (none)."
        ),
    )
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("Observed SQL metadata graph:", json.dumps(stats))


if __name__ == "__main__":
    main()
