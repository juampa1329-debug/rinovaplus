"""Offline Graphify view/checkpoint of the frozen and rehearsed foundation release."""

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

from adaptation_graphs import digest, read, render, write
from historical_checkpoint import (
    checkpoint_evidence_files,
    checkpoint_statuses,
    verify_active_checkpoint,
    verify_historical_manifest,
    verify_records,
)

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "backend/migrations/cbn_foundation"
PROOF = ROOT / "docs/adaptation/sql/sql_c3_validation.json"
BASELINE = ROOT / "docs/adaptation/sql/sql_c3_input_baseline.json"
OUT = ROOT / "graphify-out/sql-foundation"
DOMAINS = {
    "crm": "Núcleo CRM",
    "crm_config": "Configuración CRM",
    "crm_meta": "Diario de migraciones",
}


def identifier(kind, *parts):
    return (
        "foundation_"
        + kind
        + "_"
        + hashlib.sha256(json.dumps(parts).encode()).hexdigest()[:24]
    )


def build(manifest, shape, proof):
    nodes, edges = [], []
    source = "backend/migrations/cbn_foundation/expected-shapes.json"
    evidence = "docs/adaptation/sql/sql_c3_validation.json"

    def node(key, label, *, domain="Ensayo SQL C3", **attrs):
        nodes.append(
            {
                "id": key,
                "label": label,
                "file_type": "document",
                "source_file": source,
                "domain": domain,
                **attrs,
            }
        )

    def edge(a, b, relation, file=source):
        edges.append(
            {
                "source": a,
                "target": b,
                "relation": relation,
                "confidence": "EXTRACTED",
                "confidence_score": 1.0,
                "source_file": file,
            }
        )

    release = identifier("release", manifest["release_id"])
    node(release, manifest["release_id"] + " · ensayado, sólo restauraciones")
    for name, label in (
        ("source", "HORARIOSSIIE · fuente preservada, sin CRM"),
        ("reference", "Referencia separada · contrato validado"),
        ("trial", proof["trial_database"] + " · siete tablas verificadas"),
        ("faults", proof["fault_database"] + " · fallos ensayados"),
    ):
        node(name, label, source_file=evidence)
    edge("source", "reference", "copy_only_backup_restored_to_new_database", evidence)
    edge("reference", release, "independently_validated_then_frozen", evidence)
    edge(release, "trial", "applied_after_contract_freeze", evidence)
    edge(
        release, "faults", "fault_scenarios_verified_on_separate_restoration", evidence
    )
    node("prepared", "Preparación administrativa separada · tres esquemas vacíos")
    edge(release, "prepared", "requires_exact_prepared_state")
    for unit in manifest["units"]:
        node(unit["id"], unit["id"] + " · COMMITTED en ensayo")
        edge(release, unit["id"], "contains_rehearsed_unit", evidence)
        for dependency in unit["depends_on"]:
            edge(unit["id"], dependency, "requires_committed_dependency")
    tables = [o for o in shape["objects"] if o["type"].strip() == "U"]
    for table in tables:
        schema, name = table["schema_name"], table["name"]
        key = identifier("table", schema, name)
        domain = DOMAINS[schema]
        node(key, schema + "." + name + " · verificada en copia", domain=domain)
        unit = {"crm_meta": "CBN-B000", "crm": "CBN-B001", "crm_config": "CBN-B006"}[
            schema
        ]
        edge(unit, key, "created_and_verified_in_restoration", evidence)
    for index, column in enumerate(shape["columns"]):
        schema, table, name = (
            column["schema_name"],
            column["table_name"],
            column["name"],
        )
        key = identifier("column", schema, table, name)
        node(
            key,
            schema + "." + table + "." + name + " : " + column["type_name"],
            domain=DOMAINS[schema],
            source_location=f"/CBN-B006/columns/{index}",
            max_length_bytes=column["max_length"],
            nullable=column["is_nullable"],
            identity=column["is_identity"],
        )
        edge(identifier("table", schema, table), key, "has_verified_column")
    indexes = defaultdict(list)
    for row in shape["indexes"]:
        indexes[(row["schema_name"], row["table_name"], row["name"])].append(row)
    for (schema, table, name), rows in indexes.items():
        key = identifier("index", schema, table, name)
        node(
            key,
            name,
            domain=DOMAINS[schema],
            unique=rows[0]["is_unique"],
            index_type=rows[0]["type_desc"],
            filter=rows[0]["filter_definition"],
        )
        edge(identifier("table", schema, table), key, "has_verified_index")
        for row in rows:
            edge(
                key,
                identifier("column", schema, table, row["column_name"]),
                "indexes_column",
            )
    for check in shape["checks"]:
        schema, table, name = check["schema_name"], check["table_name"], check["name"]
        key = identifier("check", schema, table, name)
        node(
            key,
            name,
            domain=DOMAINS[schema],
            definition=check["definition"],
            trusted=not check["is_not_trusted"],
        )
        edge(identifier("table", schema, table), key, "has_verified_check")
    for fk in shape["foreign_keys"]:
        schema, table, name = fk["schema_name"], fk["table_name"], fk["name"]
        key = identifier("fk", schema, table, name)
        node(key, name, domain=DOMAINS[schema], trusted=not fk["is_not_trusted"])
        edge(identifier("table", schema, table), key, "has_verified_fk")
        edge(
            key, identifier("column", schema, table, fk["column_name"]), "source_column"
        )
        edge(
            key,
            identifier(
                "column", fk["target_schema"], fk["target_table"], fk["target_column"]
            ),
            "referenced_column",
        )
    ids = {n["id"] for n in nodes}
    assert len(ids) == len(nodes)
    assert all(e[k] in ids for e in edges for k in ("source", "target"))
    return {"nodes": nodes, "edges": edges}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    verify_historical_manifest(OUT / "source-manifest.json")
    sys.path.insert(0, str(ROOT / "backend"))
    from tools.cbn_foundation import load_release

    manifest, shapes, release_hash = load_release()
    proof = read(PROOF)
    assert release_hash == proof["release_sha256"]
    assert proof["source_unchanged"] and not proof["limits"] == []
    baseline = read(BASELINE)
    recognized = verify_records(baseline["files"])
    accepted = verify_active_checkpoint()
    shape = shapes["CBN-B006"]
    counts = {
        "tables": sum(o["type"].strip() == "U" for o in shape["objects"]),
        "columns": len(shape["columns"]),
        "indexes": len(
            {(i["schema_name"], i["table_name"], i["name"]) for i in shape["indexes"]}
        ),
        "checks": len(shape["checks"]),
        "foreign_keys": len(shape["foreign_keys"]),
    }
    assert counts == proof["restored_foundation"]
    extraction = build(manifest, shape, proof)
    inputs = [PROOF, BASELINE, Path(__file__), *sorted(PACKAGE.glob("*"))]
    inputs.append(Path(__file__).with_name("historical_checkpoint.py"))
    if accepted:
        inputs.extend(checkpoint_evidence_files())
    checkpoint = {
        "inputs": [
            {"path": p.relative_to(ROOT).as_posix(), "sha256": digest(p)}
            for p in inputs
            if p.is_file()
        ],
        "release_sha256": release_hash,
        "checkpoint_role": "historical_c3_shapes_not_current_runtime_acl",
        "authorized_source_transitions": recognized,
        "checkpoint_stages": checkpoint_statuses(),
        "counts": counts,
        "nodes": len(extraction["nodes"]),
        "edges": len(extraction["edges"]),
    }
    if args.check:
        assert read(OUT / "source-manifest.json") == checkpoint, (
            "Stale foundation graph"
        )
        print("Foundation release/shape/checkpoint verified:", json.dumps(counts))
        return
    stats = render(
        extraction,
        OUT,
        {"total_files": len(inputs), "total_words": 0},
        coverage_note="SQL-C3 frozen shapes verified in separate restored copies. "
        "HORARIOSSIIE source unchanged. Graph generation is offline; no app, .env, "
        "ODBC or SQL is loaded. No institutional SQL2019 or full CRM acceptance. "
        "The C3 shape/ACL snapshot is historical; C4 runtime ACL is a separate "
        "explicit overlay and does not replace these frozen shapes. "
        "Token counters cover external Graphify API calls only (none).",
    )
    assert stats["nodes"] == len(extraction["nodes"]), (
        "Graphify merged distinct SQL entities"
    )
    from graphify.build import build_from_json
    from graphify.cluster import cluster
    from graphify.export import to_canvas, to_obsidian

    graph = build_from_json(extraction, root=ROOT, directed=True)
    communities = cluster(graph)
    labels = {int(k): v for k, v in read(OUT / ".graphify_labels.json").items()}
    to_obsidian(graph, communities, str(OUT / "obsidian"), community_labels=labels)
    to_canvas(
        graph, communities, str(OUT / "obsidian/graph.canvas"), community_labels=labels
    )
    write(OUT / "source-manifest.json", checkpoint)
    print("Foundation graph:", json.dumps(stats))


if __name__ == "__main__":
    main()
