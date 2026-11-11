"""Compare captured metadata to CRM declarations offline; never connect or apply SQL."""

import argparse
import ast
import copy
import json
import re
from pathlib import Path

from adaptation_graphs import digest, read, render, write
from check_migration_plan import validate
from historical_checkpoint import (
    checkpoint_evidence_files,
    checkpoint_statuses,
    verify_active_checkpoint,
    verify_historical_manifest,
    verify_records,
)

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs/adaptation/sql"
OUTPUT = ROOT / "graphify-out/sql-comparison"
RESULT = DOCS / "horariosiie-comparison.json"
DOMAINS = {
    "crm": "Contactos y conversaciones",
    "crm_admissions": "Seguimiento de admisiones",
    "crm_inbox": "Inbox y asignación",
    "crm_events": "Eventos de conversación",
    "crm_analysis": "Análisis de conversaciones",
    "crm_config": "Configuración del CRM",
    "crm_identity": "Identidad declarada",
    "crm_merge": "Unificación de contactos",
    "crm_strategy": "Estrategia de conversación",
    "crm_channels": "Canales y medios",
    "crm_ai": "Proveedores y conocimiento",
    "crm_marketing": "Campañas y abandono",
    "crm_agents": "Agentes y ejecución",
    "dbo": "Fuentes académicas",
}
INPUTS = [
    DOCS / name
    for name in (
        "inventory.json",
        "observed-schema.json",
        "migration-plan.json",
        "sql_c2_preflight.json",
        "sql_c2_destination_metadata.json",
        "sql_c2_input_baseline.json",
    )
]


def academic_references():
    """Literal SQL references only; AST joins adjacent Python strings correctly."""
    refs = {}
    for path in sorted((ROOT / "backend/app").rglob("*.py")):
        if path.is_relative_to(ROOT / "backend/app/crm"):
            continue
        if path.name == "database_connections.py":
            continue  # diagnostic expectations are not runtime academic queries
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                for name in re.findall(r"\bdbo\.([A-Za-z_][A-Za-z0-9_]*)", node.value):
                    evidence = {
                        "file": path.relative_to(ROOT).as_posix(),
                        "line": node.lineno,  # beginning of the SQL string constant
                    }
                    bucket = refs.setdefault("dbo." + name, [])
                    if evidence not in bucket:
                        bucket.append(evidence)
    return refs


def compare(inventory, observed, plan, metadata, refs):
    visible = observed["review"]["metadata_visibility"] == "database"
    actual = {f"{t['schema']}.{t['name']}".casefold(): t for t in observed["tables"]}
    units, tables, fks = [], [], []
    by_source = {sid: u for u in plan["institutional_units"] for sid in u["source_ids"]}
    # Presence alone never accepts the employee PK/type/source contract of 003.
    blocked = set()
    for unit in plan["institutional_units"]:
        if "003" in unit["source_ids"] or any(d in blocked for d in unit["depends_on"]):
            blocked.add(unit["id"])
        units.append(
            {
                "id": unit["id"],
                "source_ids": unit["source_ids"],
                "depends_on": unit["depends_on"],
                "declared_tables": [],
                "classification": "employee_contract_pending"
                if unit["id"] in blocked
                else "history_design_only"
                if not unit["source_ids"]
                else "conditional_structural_candidate",
                "execution_allowed": False,
            }
        )
    unit_lookup = {u["id"]: u for u in units}
    for migration in inventory["migrations"]:
        unit = unit_lookup[by_source[migration["id"]]["id"]]
        for table in migration["tables"]:
            present = table["name"].casefold() in actual
            record = {
                "name": table["name"],
                "unit": unit["id"],
                "source_id": migration["id"],
                "source_file": table["file"],
                "source_line": table["line"],
                "create_column_count": len(table["columns"]),
                "presence": "present_requires_shape_review"
                if present
                else "absent_observed"
                if visible
                else "not_visible_inconclusive",
                "classification": unit["classification"],
                "shape_accepted": False,
            }
            tables.append(record)
            unit["declared_tables"].append(table["name"])
            for fk in table["foreign_keys"]:
                fks.append({"source_table": table["name"], **fk, "file": table["file"]})
        for alteration in migration["alterations"]:
            if alteration.get("foreign_key"):
                fks.append(
                    {
                        "source_table": alteration["table"],
                        **alteration["foreign_key"],
                        "file": alteration["file"],
                    }
                )
    academic = [
        {
            "name": name,
            "presence": "present_columns_not_fully_accepted"
            if name.casefold() in actual
            else "absent_observed"
            if visible
            else "not_visible_inconclusive",
            "references": evidence,
        }
        for name, evidence in sorted(refs.items())
    ]
    external = [f for f in fks if not f["target_table"].startswith("crm")]
    declared_names = {t["name"] for t in tables}
    if external or any(f["target_table"] not in declared_names for f in fks):
        raise ValueError("New or external FK target needs an explicit plan review")
    return {
        "schema_version": 1,
        "date": "2026-10-24",
        "unit": "SQL-C2",
        "status": "comparison_and_plan_only_not_executable",
        "database": observed["database"],
        "execution_allowed": False,
        "scope": "Captured table/column/FK metadata; no business rows or DDL",
        "summary": {
            "observed_tables": len(observed["tables"]),
            "declared_crm_tables": len(tables),
            "absent_crm_tables": sum(
                t["presence"] == "absent_observed" for t in tables
            ),
            "conditional_candidate_tables": sum(
                t["classification"] == "conditional_structural_candidate"
                for t in tables
            ),
            "employee_blocked_tables": sum(
                t["classification"] == "employee_contract_pending" for t in tables
            ),
            "declared_fk_including_alter": len(fks),
            "academic_fk": len(external),
            "academic_referenced_tables": len(academic),
            "academic_absent_tables": sum(
                t["presence"] == "absent_observed" for t in academic
            ),
        },
        "common_gates": {
            "full_metadata_visibility": visible,
            "managed_namespace_empty": not metadata["managed_schemas"]
            and not metadata["managed_objects"],
            "no_enabled_ddl_triggers_observed": not any(
                not t["disabled"] for t in metadata["database_ddl_triggers"]
            )
            and not any(not t[1] for t in metadata["server_ddl_triggers"]),
            "reviewed_sql_package_and_runner": False,
            "backup_restore_rehearsal": False,
            "target_version_principal_contract_accepted": False,
            "final_shape_and_academic_before_after_accepted": False,
        },
        "units": units,
        "tables": tables,
        "foreign_keys": fks,
        "academic_references": academic,
        "limits": [
            "Conditional candidates are not ready to execute or activate",
            "Employee contract is unaccepted even if a same-named table later appears",
            "Literal references are not a complete SQL parser "
            "or all dynamic dependencies",
            "CREATE columns omit ALTER final shape; use P1.3 final-shape contract",
            "Captured metadata is sequential, not a concurrent-DDL snapshot",
        ],
    }


def graph(data, result=RESULT):
    source = result.relative_to(ROOT).as_posix()
    nodes, edges = [], []

    def node(key, label, **attrs):
        nodes.append(
            {
                "id": key,
                "label": label,
                "file_type": "document",
                "source_file": source,
                "domain": DOMAINS.get(key.split(".")[0], "Plan de migración"),
                **attrs,
            }
        )

    def edge(a, b, relation, evidence=None):
        edges.append(
            {
                "source": a,
                "target": b,
                "relation": relation,
                "confidence": "EXTRACTED",
                "confidence_score": 1.0,
                "source_file": evidence["file"] if evidence else source,
                **({"source_location": f"L{evidence['line']}"} if evidence else {}),
            }
        )

    root = "sql_c2_HORARIOSSIIE"
    node(root, "HORARIOSSIIE · comparación; sin DDL aplicado")
    for unit in data["units"]:
        domain = (unit["declared_tables"] or [""])[0].split(".")[0]
        node(
            unit["id"],
            unit["id"] + " · " + unit["classification"],
            domain=DOMAINS.get(domain, "Historial de migraciones"),
        )
        edge(root, unit["id"], "has_proposed_unit")
        for dependency in unit["depends_on"]:
            edge(unit["id"], dependency, "planned_dependency")
    for table in data["tables"]:
        node(table["name"], table["name"] + " · " + table["presence"])
        edge(
            table["unit"],
            table["name"],
            "declares_missing_table",
            {"file": table["source_file"], "line": table["source_line"]},
        )
    for index, fk in enumerate(data["foreign_keys"]):
        key = "sql_c2_fk_" + str(index)
        node(
            key,
            fk["source_table"] + " → " + fk["target_table"],
            domain=DOMAINS[fk["source_table"].split(".")[0]],
        )
        for kind in ("source", "target"):
            edge(key, fk[kind + "_table"], "declared_fk_" + kind, fk)
    for table in data["academic_references"]:
        node(table["name"], table["name"] + " · " + table["presence"])
        edge(root, table["name"], "runtime_literal_academic_reference")
    edge(
        "CBN-B003",
        "dbo.GEEmpleado",
        "requires_unaccepted_employee_source_contract",
        {"file": "backend/migrations/003_local_inbox.sql", "line": 18},
    )
    ids = {n["id"] for n in nodes}
    assert len(ids) == len(nodes)
    assert all(e[k] in ids for e in edges for k in ("source", "target"))
    return {"nodes": nodes, "edges": edges}


def documents(data, active=False):
    lines = [
        "# HORARIOSSIIE frente a las declaraciones CRM CBN",
        "",
        "Generado offline por `backend/tools/compare_horariosiie.py`. "
        "SQL-C2, 2026-10-24. [Plan de creación](HORARIOSSIIE_CRM_PLAN.md). "
        "Ninguna clasificación concede permiso de ejecución o activa funciones.",
        "",
        "## Grupos y precondiciones",
        "",
        "| Grupo | Fuentes | Tablas | Clasificación | Depende de |",
        "|---|---|---:|---|---|",
    ]
    for unit in data["units"]:
        lines.append(
            f"| {unit['id']} | {', '.join(unit['source_ids']) or 'diario nuevo'} | "
            f"{len(unit['declared_tables'])} | {unit['classification']} | "
            f"{', '.join(unit['depends_on']) or '—'} |"
        )
    lines += [
        "",
        "## Las 68 tablas declaradas",
        "",
        "Todas están ausentes en esta captura con visibilidad completa. "
        "Las columnas contadas son CREATE; ALTER y forma final se revisan aparte.",
        "",
        "| Tabla | Fuente | Columnas CREATE | Grupo |",
        "|---|---|---:|---|",
    ]
    for table in data["tables"]:
        path = "../../../" + table["source_file"]
        lines.append(
            f"| {table['name']} | [{table['source_id']}:{table['source_line']}]"
            f"({path}#L{table['source_line']}) | {table['create_column_count']} | "
            f"{table['unit']} |"
        )
    lines += [
        "",
        "## Referencias académicas del código activo",
        "",
        "Presencia de nombre, no aceptación de columnas/PK/permisos/datos. "
        "Las referencias anclan el inicio del literal SQL Python; "
        "se excluyen expectativas del diagnóstico y router importado no montado.",
        "",
        "| Tabla | Presencia | Primera referencia |",
        "|---|---|---|",
    ]
    for table in data["academic_references"]:
        ev = table["references"][0]
        lines.append(
            f"| {table['name']} | {table['presence']} | "
            f"[{ev['file']}:{ev['line']}](../../../{ev['file']}#L{ev['line']}) |"
        )
    text = "\n".join(lines) + "\n"
    if active:
        text = text.replace(
            "SQL-C2, 2026-10-24.",
            "Consumidores actuales frente a la captura histórica SQL-C2.",
        )
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--active",
        action="store_true",
        help="Build/check current consumers separately; preserve SQL-C2 history",
    )
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    verify_historical_manifest(OUTPUT / "source-manifest.json")
    inputs = [*INPUTS]
    if args.active:
        inputs[0] = DOCS / "inventory.active.json"
    result = DOCS / "horariosiie-comparison.active.json" if args.active else RESULT
    output = ROOT / "graphify-out/sql-comparison-active" if args.active else OUTPUT
    document = DOCS / (
        "HORARIOSSIIE_COMPARISON.active.md"
        if args.active
        else "HORARIOSSIIE_COMPARISON.md"
    )
    inventory, observed, plan, preflight, metadata, baseline = map(read, inputs)
    validate(plan)
    assert preflight["snapshot_sha256"] == digest(INPUTS[1])
    assert (
        preflight["database"]
        == observed["database"]
        == metadata["database"]
        == "HORARIOSSIIE"
    )
    recognized = verify_records(baseline["files"])
    accepted = verify_active_checkpoint()
    # Current literals must not silently replace consumers captured in SQL-C2.
    refs = (
        academic_references()
        if args.active
        else {r["name"]: r["references"] for r in read(RESULT)["academic_references"]}
    )
    data = compare(inventory, observed, plan, metadata, refs)
    assert (
        data["summary"]["absent_crm_tables"],
        data["summary"]["conditional_candidate_tables"],
        data["summary"]["employee_blocked_tables"],
    ) == (68, 36, 32)
    if args.self_test:
        restricted = copy.deepcopy(observed)
        restricted["review"]["metadata_visibility"] = "restricted"
        assert (
            compare(inventory, restricted, plan, metadata, refs)["summary"][
                "absent_crm_tables"
            ]
            == 0
        )
        altered = copy.deepcopy(inventory)
        altered["migrations"][0]["tables"][1]["foreign_keys"][0]["target_table"] = (
            "dbo.GEEstudiante"
        )
        try:
            compare(altered, observed, plan, metadata, refs)
        except ValueError:
            pass
        else:
            raise AssertionError("Academic FK must require review")
        print("Self-check: restricted visibility and new academic FK rejected safely")
    extraction = graph(data, result)
    checkpoint_inputs = [
        *inputs,
        Path(__file__),
        Path(__file__).with_name("historical_checkpoint.py"),
    ]
    if accepted:
        checkpoint_inputs.extend(checkpoint_evidence_files())
    manifest = {
        "inputs": [
            {"path": p.relative_to(ROOT).as_posix(), "sha256": digest(p)}
            for p in checkpoint_inputs
        ],
        "checkpoint_role": "current_consumers_historical_capture"
        if args.active
        else "historical_sql_c2_not_current_runtime",
        "authorized_source_transitions": recognized,
        "checkpoint_stages": checkpoint_statuses(),
        "summary": data["summary"],
        "nodes": len(extraction["nodes"]),
        "edges": len(extraction["edges"]),
    }
    if args.check:
        assert read(result) == data, "Stale comparison"
        assert document.read_text(encoding="utf-8") == documents(data, args.active)
        assert read(output / "source-manifest.json") == manifest, (
            "Stale comparison graph"
        )
        print(
            "Comparison/checkpoint verified (" + manifest["checkpoint_role"] + "):",
            json.dumps(data["summary"]),
        )
        return
    if args.active:
        write(result, data)
        document.write_text(documents(data, True), encoding="utf-8")
    else:
        assert read(RESULT) == data, "Historical SQL-C2 comparison changed"
        assert document.read_text(encoding="utf-8") == documents(data), (
            "Historical SQL-C2 document changed"
        )
    stats = render(
        extraction,
        output,
        {"total_files": len(INPUTS), "total_words": 0},
        coverage_note=manifest["checkpoint_role"]
        + ": offline comparison of captured metadata "
        "and source declarations. "
        "Conditional candidates and dependencies are a plan, not applied SQL, "
        "full drift acceptance or functional activation. No LLM API calls.",
    )
    from graphify.build import build_from_json
    from graphify.cluster import cluster
    from graphify.export import to_canvas, to_obsidian

    mapped = build_from_json(extraction, root=ROOT, directed=True)
    communities = cluster(mapped)
    labels = {int(k): v for k, v in read(output / ".graphify_labels.json").items()}
    to_obsidian(mapped, communities, str(output / "obsidian"), community_labels=labels)
    to_canvas(
        mapped,
        communities,
        str(output / "obsidian/graph.canvas"),
        community_labels=labels,
    )
    write(output / "source-manifest.json", manifest)
    print("SQL-C2 graph:", json.dumps(stats))
    print(json.dumps(data["summary"]))


if __name__ == "__main__":
    main()
