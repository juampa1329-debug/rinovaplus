"Bounded Graphify checkpoint for P3; previous graph artifacts stay frozen."

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "graphify-out/p3-es"
CODE = (
    [
        "backend/app/institutional/" + name + ".py"
        for name in [
            "workspace",
            "workspace_policy",
            "api",
            "auth",
            "store",
            "spanish",
            "spanish_bindings",
            "policy",
            "db",
            "settings",
            "management",
        ]
    ]
    + [
        "backend/tools/" + name + ".py"
        for name in [
            "p3_workspace_migrations",
            "p3_workspace_recovery",
            "prepare_p3_workspace",
            "qualify_p3_workspace",
            "qualify_p3_risk",
            "qualify_p3_migrations",
            "p3_workspace_final_checks",
            "phase_work_progress",
            "check_phase_progress",
        ]
    ]
    + [
        "frontend/src/" + name
        for name in [
            "institution/Workspace.tsx",
            "institution/InstitutionApp.tsx",
            "institution/api.tsx",
            "institution/workspace-main.tsx",
            "shared/workspaceSession.tsx",
            "shared/crm.ts",
            "modules/clients/components/ClientFields.tsx",
            ("modules/crm-configuration/hooks/useCrmConfiguration.ts"),
        ]
    ]
    + [
        "backend/tests/test_institutional_workspace.py",
        "frontend/src/test/institutionWorkspace.test.tsx",
    ]
)
SEMANTIC = [
    "docs/adaptation/fragments/p3-es-" + name + ".draft.json"
    for name in [
        "reference",
        "existing",
        "current",
        "evidence",
    ]
]
DOCS = (
    [
        "docs/adaptation/sql/P3_ES_CONTRACT.md",
        "docs/adaptation/phase-work-definition.json",
        "docs/adaptation/phase-work-progress.json",
        "docs/adaptation/phase-progress-contract.json",
        ("backend/migrations/cbn_workspace_spanish_v1/release.json"),
        ("backend/migrations/cbn_workspace_spanish_v1/expected-model.json"),
        ("backend/migrations/cbn_institutional_spanish_v1/table_map.json"),
    ]
    + [
        "artifacts/p3-es/" + name
        for name in [
            "http-result.json",
            "risk-result.json",
            "migration-result.json",
            "final-fixture-result.json",
            "source-preservation-result.json",
            "clean-result.json",
            "browser/workflow-result.json",
            "browser/final-result.json",
            "restart-result.json",
            "acceptance-review.json",
            "current-source-review.json",
            "evidence-source-review.json",
        ]
    ]
    + SEMANTIC
)


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def detect_sources():
    from graphify.detect import detect

    corpus = ROOT / ".local/p3-es/graph-corpora" / uuid4().hex
    corpus.mkdir(parents=True, exist_ok=True)
    (corpus / ".graphifyignore").write_text(
        "!**/*.md\n!**/*.json\n!**/*.test.*\n", encoding="utf-8"
    )
    # A new P3 corpus has an explicit inventory; no recursive private scan.
    files = [name for name in CODE + DOCS if (ROOT / name).is_file()]
    for index, name in enumerate(files):
        shutil.copyfile(ROOT / name, corpus / (str(index) + "_" + Path(name).name))
    detection = detect(corpus)
    assert 0 < detection["total_files"] < 200 and detection["total_words"] < 2000000
    save(OUT / "detection.json", detection)
    return detection


def structural():
    from graphify.extract import extract

    data = extract(
        [ROOT / name for name in CODE],
        root=ROOT,
        cache_root=ROOT / ".local/p3-es/graph-cache",
        max_workers=4,
    )
    save(ROOT / ".local/p3-es/final-ast.json", data)
    return data


def build():
    from adaptation_graphs import render

    detection, data = detect_sources(), structural()
    assert all((ROOT / name).is_file() for name in CODE + DOCS)
    nodes = {node["id"]: node for node in data["nodes"]}
    edges = list(data["edges"])
    hyperedges = list(data.get("hyperedges", []))

    def node(identity, label, source, **attrs):
        nodes.setdefault(
            identity,
            dict(
                id=identity,
                label=label,
                file_type="document",
                source_file=source,
                source_location="$",
                **attrs,
            ),
        )

    def edge(a, b, relation, source):
        edges.append(
            dict(
                source=a,
                target=b,
                relation=relation,
                confidence="EXTRACTED",
                confidence_score=1,
                source_file=source,
                source_location="$",
            )
        )

    for name in SEMANTIC:
        fragment = read(ROOT / name)
        graph = fragment.get("graph", fragment)
        for item in graph["nodes"]:
            nodes[item["id"]] = item
        edges.extend(graph["edges"])
        hyperedges.extend(graph.get("hyperedges", []))
    ledger_name = "docs/adaptation/phase-work-progress.json"
    work = read(ROOT / ledger_name)
    for phase in work["phases"]:
        pid = "p3es_phase_" + phase["id"]
        node(
            pid,
            phase["id"] + " · " + phase["technical_work"]["percent_display"],
            ledger_name,
            domain="roadmap",
            accepted=phase["technical_work"]["phase_accepted"],
        )
        for criterion in phase["criteria"]:
            cid = "p3es_criterion_" + criterion["id"]
            node(
                cid,
                criterion["id"],
                ledger_name,
                domain=phase["id"],
                accepted=criterion["current_acceptance"]["state"] == "accepted",
            )
            edge(pid, cid, "contains_canonical_criterion", ledger_name)
            for milestone in criterion["milestones"]:
                mid = "p3es_milestone_" + milestone["id"]
                node(
                    mid,
                    milestone["id"] + " · " + milestone["description"],
                    ledger_name,
                    state=milestone["state"],
                    criterion_share=milestone["criterion_share"],
                )
                edge(cid, mid, "contains_fixed_weight_milestone", ledger_name)
                for ref in milestone["evidence_refs"]:
                    evidence = work["evidence_registry"][ref]
                    eid = "p3es_evidence_" + ref
                    node(
                        eid,
                        ref + " · " + evidence["scope"],
                        evidence["file"],
                        domain="scoped_evidence",
                        sha256=evidence["source_sha256_at_review"],
                    )
                    edge(mid, eid, "supported_in_declared_scope", ledger_name)
    model_name = "backend/migrations/cbn_workspace_spanish_v1/expected-model.json"
    model = read(ROOT / model_name)
    mapping_name = "backend/migrations/cbn_institutional_spanish_v1/table_map.json"
    mapping = read(ROOT / mapping_name)
    academics = set(mapping["academic_tables"])
    bindings = dict(mapping["tables"])
    for key, physical in {
        "State": "Estado",
        "Assignment": "Asignacion",
        "Task": "Tarea",
        "Note": "Nota",
        "Merge": "Unificacion",
        "Journal": "Migracion",
    }.items():
        bindings["crm_workspace." + key] = "dbo.CRMTrabajo" + physical
    for table in model["tables"]:
        name = table["schema"] + "." + table["name"]
        node(
            "p3es_table_" + name,
            name,
            model_name,
            academic_write_allowed=False,
            domain="academic_read_denied"
            if name in academics
            else "Spanish_CRM_storage",
        )
    for logical, physical in bindings.items():
        identity = "p3es_logical_" + logical
        node(
            identity,
            logical,
            mapping_name if not logical.startswith("crm_workspace.") else CODE[1],
            domain="closed_identifier_mapping",
            alias_or_view=False,
        )
        edge(identity, "p3es_table_" + physical, "maps_trusted_identifier", model_name)
    for foreign in model["foreign_keys"]:
        name = foreign["schema"] + "." + foreign["table"]
        target = foreign["referenced_schema"] + "." + foreign["referenced_table"]
        identity = "p3es_FK_" + name + "." + foreign["name"]
        node(
            identity,
            foreign["name"],
            model_name,
            domain="physical_FK",
            columns=foreign["columns"],
        )
        edge("p3es_table_" + name, identity, "defines_FK", model_name)
        edge(identity, "p3es_table_" + target, "references_physical_table", model_name)
    for item in edges:
        for identity in [item["source"], item["target"]]:
            if identity not in nodes:
                node(
                    identity,
                    identity,
                    item.get("source_file", ledger_name),
                    domain="external_context",
                )
    counts = render(
        {
            **data,
            "nodes": list(nodes.values()),
            "edges": edges,
            "hyperedges": hyperedges,
        },
        OUT,
        detection,
        coverage_note=(
            "P3 local SQL2019: Inbox/shared ficha/CRM"
            "/risk read model, own profile, 144 table"
            "s/229 FKs/114 bindings. Manual interest,"
            " SLA, rule evidence and future trained i"
            "nference remain distinct. Real provider "
            "operation and P10 are not accepted here."
            " All56 canonical criteria and279 weighte"
            "d milestones remain fixed. Previous grap"
            "hs preserved; P2/P1 replay frozen indepe"
            "ndently."
        ),
    )
    save(
        OUT / "source-manifest.json",
        dict(
            unit="P3-ES",
            physical_tables=144,
            physical_FKs=229,
            logical_bindings=114,
            fixed_criteria=56,
            fixed_milestones=279,
            **counts,
            sources={name: digest(ROOT / name) for name in CODE + DOCS},
            artifacts={
                name: digest(OUT / name)
                for name in [
                    "graph.json",
                    "graph.html",
                    "GRAPH_REPORT.md",
                    "detection.json",
                ]
            },
        ),
    )
    print(
        json.dumps(
            dict(
                bounded_files=detection["total_files"],
                bounded_words=detection["total_words"],
                **counts,
            )
        )
    )


def check():
    value = read(OUT / "source-manifest.json")
    assert (
        value["physical_tables"],
        value["physical_FKs"],
        value["logical_bindings"],
        value["fixed_criteria"],
        value["fixed_milestones"],
    ) == (144, 229, 114, 56, 279)
    assert set(value["sources"]) == set(CODE + DOCS)
    for name, expected in value["sources"].items():
        assert digest(ROOT / name) == expected, name
    for name, expected in value["artifacts"].items():
        assert digest(OUT / name) == expected, name
    graph = read(OUT / "graph.json")
    ids = {node["id"] for node in graph["nodes"]}
    links = graph.get("links", graph.get("edges"))
    assert len(ids) == len(graph["nodes"]) == value["nodes"]
    assert all(e["source"] in ids and e["target"] in ids for e in links)
    assert "p3es_criterion_P3.close" in ids
    return dict(
        nodes=len(ids),
        edges=len(links),
        communities=value["communities"],
        old_graphs_rebuilt=False,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--extract-only", action="store_true")
    args = parser.parse_args()
    if args.check:
        print(json.dumps(check()))
    elif args.extract_only:
        found, ast = detect_sources(), structural()
        print(
            json.dumps(
                dict(
                    files=found["total_files"],
                    words=found["total_words"],
                    nodes=len(ast["nodes"]),
                    edges=len(ast["edges"]),
                )
            )
        )
    else:
        build()
