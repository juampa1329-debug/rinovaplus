"""Bounded Graphify checkpoint for P1-ES and partial roadmap; offline only."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from check_phase_progress import ROOT

OUT = ROOT / "graphify-out/p1-es"
CODE = [
    "backend/tools/es_schema_migrate_v2.py",
    "backend/tools/es_schema_catalog_v2.py",
    "backend/tools/es_schema_recovery_v2.py",
    "backend/tools/qualify_spanish_schema.py",
    "backend/tools/qualify_spanish_checks.py",
    "backend/app/es_schema_profile.py",
    "backend/tools/phase_work_progress.py",
    "backend/tools/p1_es_graphs.py",
    "backend/tests/test_es_schema.py",
    "backend/tests/test_es_schema_v2.py",
    "backend/tests/test_es_schema_protocol.py",
    "backend/tests/test_es_schema_profile.py",
]
DOCS = [
    "docs/adaptation/phase-work-progress.json",
    "docs/adaptation/phase-work-definition.json",
    "docs/adaptation/phase-progress-contract.json",
    "backend/migrations/cbn_spanish_schema_v2/expected_catalog.json",
    "backend/migrations/cbn_spanish_schema_v2/table_map.json",
    "backend/migrations/cbn_spanish_schema_v2/release.json",
    "artifacts/p1-es/connected-result.json",
    "artifacts/p1-es/acceptance-review.json",
    "docs/adaptation/fragments/p1-es-accepted.draft.json",
]


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def build():
    from adaptation_graphs import render
    from graphify.detect import detect
    from graphify.extract import extract

    corpus = ROOT / ".local/p1-es/graph-corpus"
    corpus.mkdir(parents=True, exist_ok=True)
    for index, name in enumerate(CODE + DOCS):
        shutil.copyfile(ROOT / name, corpus / (str(index) + "_" + Path(name).name))
    detection = detect(corpus)
    assert 0 < detection["total_files"] < 200 and detection["total_words"] < 2000000
    save(OUT / "detection.json", detection)
    data = extract(
        [ROOT / name for name in CODE],
        root=ROOT,
        cache_root=ROOT / ".local/p1-es/graph-cache",
        max_workers=4,
    )
    nodes = {node["id"]: node for node in data["nodes"]}
    edges = data["edges"]

    def node(identity, label, source, location="$", **attributes):
        nodes.setdefault(
            identity,
            {
                "id": identity,
                "label": label,
                "file_type": "document",
                "source_file": source,
                "source_location": location,
                **attributes,
            },
        )

    def edge(source, target, relation, evidence, location="$", **attributes):
        edges.append(
            {
                "source": source,
                "target": target,
                "relation": relation,
                "confidence": "EXTRACTED",
                "confidence_score": 1,
                "source_file": evidence,
                "source_location": location,
                **attributes,
            }
        )

    fragment = read(ROOT / DOCS[-1])
    graph = fragment.get("graph")
    assert graph and graph["nodes"] and graph["edges"]
    for item in graph["nodes"]:
        nodes[item["id"]] = item
    edges.extend(graph["edges"])
    work_source = DOCS[0]
    work = read(ROOT / work_source)
    for phase in work["phases"]:
        phase_id = "p1es_roadmap_" + phase["id"]
        node(
            phase_id,
            phase["id"]
            + " · "
            + phase["technical_work"]["percent_display"]
            + " trabajo",
            work_source,
            domain="roadmap",
            phase_accepted=phase["technical_work"]["phase_accepted"],
        )
        for criterion in phase["criteria"]:
            criterion_id = "p1es_criterion_" + criterion["id"]
            node(
                criterion_id,
                criterion["id"]
                + " · "
                + criterion["technical_completion"]["percent_display"],
                work_source,
                domain=phase["id"],
                accepted=criterion["current_acceptance"]["state"] == "accepted",
            )
            edge(
                phase_id,
                criterion_id,
                "contains_fixed_canonical_criterion",
                work_source,
            )
            for milestone in criterion["milestones"]:
                mid = "p1es_milestone_" + milestone["id"]
                node(
                    mid,
                    milestone["id"] + " · " + milestone["description"],
                    work_source,
                    domain=phase["id"],
                    state=milestone["state"],
                    criterion_share=milestone["criterion_share"],
                    evidence_level=milestone["evidence_level"],
                )
                edge(criterion_id, mid, "contains_fixed_weight_milestone", work_source)
                for reference in milestone["evidence_refs"]:
                    evidence = work["evidence_registry"][reference]
                    eid = "p1es_evidence_" + reference
                    node(
                        eid,
                        reference + " · " + evidence["scope"],
                        evidence["file"],
                        evidence["source_location"],
                        domain="evidence",
                        sha256=evidence["source_sha256_at_review"],
                    )
                    edge(mid, eid, "supported_in_declared_evidence_scope", work_source)
    model_source = DOCS[3]
    model = read(ROOT / model_source)
    layout = read(ROOT / DOCS[4])
    tables = [table["schema"] + "." + table["name"] for table in model["tables"]] + [
        "crm_meta.MigrationJournal"
    ]
    for table in tables:
        node(
            "p1es_table_" + table,
            table,
            model_source if table != "crm_meta.MigrationJournal" else DOCS[5],
            domain="academic_structure_only"
            if table in layout["academic_tables"]
            else "CRM_or_journal",
            live_source_modified=False,
        )
    for original, spanish in layout["CRM_map"].items():
        identity = "p1es_original_name_" + original
        node(
            identity,
            original,
            DOCS[4],
            domain="name_mapping_reference",
            runtime_alias_active=False,
        )
        edge(
            identity,
            "p1es_table_" + spanish,
            "renamed_in_isolated_release_only",
            DOCS[4],
        )
    for foreign in model["foreign_keys"]:
        table = foreign["schema"] + "." + foreign["table"]
        referenced = foreign["referenced_schema"] + "." + foreign["referenced_table"]
        fid = "p1es_fk_" + table + "." + foreign["name"]
        node(
            fid,
            foreign["name"],
            model_source,
            domain="physical_FK",
            columns=foreign["columns"],
        )
        edge("p1es_table_" + table, fid, "defines_physical_FK", model_source)
        edge(fid, "p1es_table_" + referenced, "references_physical_table", model_source)
    # AST external symbols and semantic phase anchors remain explicit context.
    for item in edges:
        for identity in (item["source"], item["target"]):
            if identity not in nodes:
                node(
                    identity,
                    identity,
                    item.get("source_file", work_source),
                    domain="external_context",
                )
    extraction = {**data, "nodes": list(nodes.values()), "edges": edges}
    counts = render(
        extraction,
        OUT,
        detection,
        coverage_note="P1 technical foundation accepted on actual SQL2019. The 279 milestones quantify evidenced partial work over 56 fixed criteria, separate from acceptance. Physical FK/name mapping applies only to the isolated 98+1 release. No Spanish runtime adoption, P2 closure, academic data import or production acceptance. Historical C13/P2 graphs stay unchanged.",
    )
    artifacts = ["graph.json", "graph.html", "GRAPH_REPORT.md", "detection.json"]
    manifest = {
        "unit": "P1-ES",
        "status": "scoped_technical_foundation_and_work_progress_graph",
        **counts,
        "physical_tables": 99,
        "physical_FKs": 125,
        "fixed_milestones": 279,
        "fixed_criteria": 56,
        "sources": {name: digest(ROOT / name) for name in CODE + DOCS},
        "artifacts": {name: digest(OUT / name) for name in artifacts},
    }
    save(OUT / "source-manifest.json", manifest)
    print(
        json.dumps(
            {
                "bounded_corpus_files": detection["total_files"],
                "bounded_corpus_words": detection["total_words"],
                **counts,
            }
        )
    )


def check():
    manifest = read(OUT / "source-manifest.json")
    assert (
        manifest["physical_tables"] == 99
        and manifest["physical_FKs"] == 125
        and manifest["fixed_milestones"] == 279
    )
    assert set(manifest["sources"]) == set(CODE + DOCS)
    for relative, expected in manifest["sources"].items():
        assert digest(ROOT / relative) == expected, relative
    for relative, expected in manifest["artifacts"].items():
        assert digest(OUT / relative) == expected, relative
    graph = read(OUT / "graph.json")
    ids = {item["id"] for item in graph["nodes"]}
    links = graph.get("links", graph.get("edges"))
    assert len(ids) == len(graph["nodes"]) == manifest["nodes"]
    assert all(link["source"] in ids and link["target"] in ids for link in links)
    assert (
        len([identity for identity in ids if identity.startswith("p1es_milestone_")])
        == 279
    )
    assert len([identity for identity in ids if identity.startswith("p1es_fk_")]) == 125
    print(
        json.dumps(
            {
                "P1_ES_graph": "valid",
                "nodes": len(ids),
                "edges": len(links),
                "missing_endpoints": 0,
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    check() if arguments.check else build()
