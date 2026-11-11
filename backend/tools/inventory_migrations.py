"""Offline source inventory. Never imports the app, loads .env or executes SQL.

This bounded scanner extracts explicit CREATE TABLE/INDEX declarations and keeps
ALTER statements separately. It is not a T-SQL compiler or a live schema reader.
"""

import argparse
import hashlib
import json
import os
import re
from pathlib import Path

from historical_checkpoint import verify_active_checkpoint, verify_frozen_release

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "docs/adaptation/sql"
NAME = r"(?:\[[^\]]+\]|[A-Za-z_]\w*)(?:\s*\.\s*(?:\[[^\]]+\]|[A-Za-z_]\w*))*"


def normalized(value):
    return re.sub(r"\s+", "", value).replace("[", "").replace("]", "")


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def location(text, offset):
    return text.count("\n", 0, offset) + 1


def unquoted_positions(text):
    """Yield character positions outside SQL strings and bracketed identifiers."""
    i = 0
    while i < len(text):
        if text[i] in "'[":
            close = "'" if text[i] == "'" else "]"
            i += 1
            while i < len(text):
                if text[i] == close:
                    if i + 1 < len(text) and text[i + 1] == close:
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
        else:
            yield i
            i += 1


def strip_comments(text):
    return re.sub(r"'(?:''|[^'])*'|--[^\n]*|/\*[\s\S]*?\*/", lambda m: m[0] if m[0].startswith("'") else "".join("\n" if c == "\n" else " " for c in m[0]), text)


def balanced(text, start):
    depth = 0
    for offset in unquoted_positions(text[start:]):
        i = start + offset
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[start + 1:i], i + 1
    raise ValueError("Unclosed declaration parentheses")


def definitions(body):
    depth, start = 0, 0
    for i in unquoted_positions(body):
        if body[i] == "(":
            depth += 1
        elif body[i] == ")":
            depth -= 1
        elif body[i] == "," and depth == 0:
            yield body[start:i], start
            start = i + 1
    yield body[start:], start


def scan(path):
    text = strip_comments(path.read_text(encoding="utf-8-sig"))
    file = path.relative_to(ROOT).as_posix()
    tables, indexes, changes = [], [], []
    for match in re.finditer(r"CREATE\s+TABLE\s+(" + NAME + r")\s*\(", text, re.I):
        body, _ = balanced(text, match.end() - 1)
        table = {"name": normalized(match[1]), "file": file, "line": location(text, match.start()), "columns": [], "constraints": [], "foreign_keys": []}
        for raw, offset in definitions(body):
            declaration = " ".join(raw.split())
            if not declaration:
                continue
            line = location(text, match.end() + offset + len(raw) - len(raw.lstrip()))
            constraint = re.match(r"(?:CONSTRAINT|PRIMARY|FOREIGN|UNIQUE|CHECK)\b", declaration, re.I)
            column_name = None
            if constraint:
                table["constraints"].append({"definition": declaration, "line": line})
            else:
                column = re.match(r"(\[[^\]]+\]|\w+)\s+(\w+(?:\s*\([^)]*\))?)", declaration)
                if not column:
                    raise ValueError(f"Unrecognized column at {file}:{line}: {declaration}")
                column_name = normalized(column[1])
                null_clause = re.split(r"\b(?:CHECK|DEFAULT|REFERENCES)\b", declaration, maxsplit=1, flags=re.I)[0]
                table["columns"].append({"name": column_name, "type": normalized(column[2]), "nullable": False if re.search(r"\bNOT\s+NULL\b|\bPRIMARY\s+KEY\b", null_clause, re.I) else True if re.search(r"\bNULL\b", null_clause, re.I) else None, "identity": bool(re.search(r"\bIDENTITY\b", declaration, re.I)), "definition": declaration, "line": line})
            for reference in re.finditer(r"REFERENCES\s+(" + NAME + r")\s*\(([^)]+)\)", declaration, re.I):
                foreign = re.search(r"FOREIGN\s+KEY\s*\(([^)]+)\)", declaration, re.I)
                columns = [normalized(c) for c in foreign[1].split(",")] if foreign else [column_name]
                table["foreign_keys"].append({"source_columns": columns, "target_table": normalized(reference[1]), "target_columns": [normalized(c) for c in reference[2].split(",")], "line": line, "definition": declaration})
        tables.append(table)
    for match in re.finditer(r"CREATE\s+(UNIQUE\s+)?(?:(CLUSTERED|NONCLUSTERED)\s+)?INDEX\s+(\w+)\s+ON\s+(" + NAME + r")\s*\(", text, re.I):
        keys, end = balanced(text, match.end() - 1)
        semicolon = text.find(";", end)
        tail = text[end:semicolon] if semicolon != -1 else text[end:].splitlines()[0]
        indexes.append({"name": match[3], "table": normalized(match[4]), "unique": bool(match[1]), "kind": match[2] or "NONCLUSTERED (default)", "keys": " ".join(keys.split()), "tail": " ".join(tail.split()), "file": file, "line": location(text, match.start())})
    for match in re.finditer(r"ALTER\s+TABLE\s+(" + NAME + r")", text, re.I):
        end = text.find(";", match.start())
        statement = " ".join(text[match.start():end if end != -1 else len(text)].split())
        change = {"table": normalized(match[1]), "file": file, "line": location(text, match.start()), "statement": statement}
        column = re.match(r"ALTER\s+TABLE\s+" + NAME + r"\s+(ADD|ALTER COLUMN)\s+(?!CONSTRAINT\b)(\w+)\s+(\w+(?:\s*\([^)]*\))?)", statement, re.I)
        if column:
            change["column"] = {"name": column[2], "type": normalized(column[3]), "action": column[1].upper()}
            reference = re.search(r"REFERENCES\s+(" + NAME + r")\s*\(([^)]+)\)", statement, re.I)
            if reference:
                change["foreign_key"] = {"source_columns": [column[2]], "target_table": normalized(reference[1]), "target_columns": [normalized(c) for c in reference[2].split(",")], "line": change["line"], "definition": statement}
        changes.append(change)
    features = {}
    for feature, pattern in {"OPENJSON": r"\bOPENJSON\s*\(", "ISJSON": r"\bISJSON\s*\(", "FOR_JSON": r"\bFOR\s+JSON\b", "STRING_AGG": r"\bSTRING_AGG\s*\(", "sp_getapplock": r"\bsp_getapplock\b", "SHA2_256": r"SHA2_256", "BIN2": r"Latin1_General_100_BIN2"}.items():
        hits = list(re.finditer(pattern, text, re.I))
        if hits:
            features[feature] = {"count": len(hits), "first_line": location(text, hits[0].start())}
    newer = []
    for match in re.finditer(r"\b(?:DATETRUNC|DATE_BUCKET|GENERATE_SERIES|JSON_OBJECT|JSON_ARRAY|JSON_PATH_EXISTS|REGEXP_\w+)\s*\(", text, re.I):
        newer.append({"token": match[0], "line": location(text, match.start())})
    for match in re.finditer(r"\b(?:ISJSON|STRING_SPLIT)\s*\(", text, re.I):
        args, _ = balanced(text, match.end() - 1)
        count = len(list(definitions(args)))
        if (match[0].upper().startswith("ISJSON") and count > 1) or count > 2:
            newer.append({"token": match[0], "argument_count": count, "line": location(text, match.start())})
    return {"id": path.name[:3], "file": file, "sha256": fingerprint(path), "tables": tables, "indexes": indexes, "alterations": changes, "features": features, "post_2019_candidates": newer, "insert_targets": sorted(set(normalized(m[1]) for m in re.finditer(r"\bINSERT\s+(?:INTO\s+)?(" + NAME + r")", text, re.I))), "go_separators": len(re.findall(r"^\s*GO\s*$", text, re.I | re.M))}


def build():
    migrations = [scan(p) for p in sorted((ROOT / "backend/migrations").glob("*.sql"))]
    tables = [t for m in migrations for t in m["tables"]]
    by_table = {t["name"].lower(): t for t in tables}
    if len(by_table) != len(tables):
        raise ValueError("Repeated CREATE TABLE requires a reviewed schema-evolution model")
    runtime = [p for p in (ROOT / "backend/app").rglob("*.py") if "crm" not in p.relative_to(ROOT / "backend/app").parts[:1] and "graphify-out" not in p.parts and "__pycache__" not in p.parts]
    runners = sorted((ROOT / "backend/tools").glob("migrate_*.py"))
    for table in tables:
        table["literal_consumers"] = []
        pattern = re.compile(r"(?<!\w)" + re.escape(table["name"]) + r"(?!\w)", re.I)
        for path in runtime:
            text = path.read_text(encoding="utf-8-sig")
            hits = list(pattern.finditer(text))
            if hits:
                table["literal_consumers"].append({"file": path.relative_to(ROOT).as_posix(), "first_line": location(text, hits[0].start()), "occurrences": len(hits)})
    for migration in migrations:
        filename = Path(migration["file"]).name
        migration["runners"] = [{"file": p.relative_to(ROOT).as_posix(), "line": location(p.read_text(encoding="utf-8-sig"), p.read_text(encoding="utf-8-sig").index(filename))} for p in runners if filename in p.read_text(encoding="utf-8-sig")]
        migration["fk_dependencies"] = sorted({by_table[fk["target_table"].lower()]["file"] for t in migration["tables"] for fk in t["foreign_keys"] if fk["target_table"].lower() in by_table and by_table[fk["target_table"].lower()]["file"] != migration["file"]})
    ids = {int(m["id"]) for m in migrations}
    reviews = set((OUTPUT / "reviews").glob("*.json"))
    mapping_path = OUTPUT / "capability-map.json"
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    evidence = {(ROOT / e["file"]).resolve() for group in mapping["groups"] for e in group["source_evidence"]}
    inputs = sorted({ROOT / m["file"] for m in migrations} | set(runtime) | set(runners) | {Path(__file__).resolve(), Path(__file__).with_name("historical_checkpoint.py"), mapping_path} | reviews | evidence)
    return {"date": "2026-10-24", "verification": "static_source_only_not_applied_schema", "limitations": ["Declarations, not live database objects or a T-SQL compilation result", "ALTER statements and dynamic drops are separate; column declarations are not a synthesized final schema", "Literal consumer matches do not resolve dynamic SQL or prove runtime use", "Nullability not explicitly declared is unknown; session/database defaults are not assumed"], "summary": {"migration_files": len(migrations), "maximum_ordinal": max(ids), "missing_ordinals": sorted(set(range(1, max(ids) + 1)) - ids), "schemas": len({t["name"].split('.')[0] for t in tables}), "declared_tables": len(tables), "declared_columns": sum(len(t["columns"]) for t in tables), "table_constraints": sum(len(t["constraints"]) for t in tables), "foreign_keys": sum(len(t["foreign_keys"]) for t in tables), "explicit_create_indexes": sum(len(m["indexes"]) for m in migrations), "alter_table_occurrences": sum(len(m["alterations"]) for m in migrations), "alter_added_columns": sum(a.get("column", {}).get("action") == "ADD" for m in migrations for a in m["alterations"]), "alter_modified_columns": sum(a.get("column", {}).get("action") == "ALTER COLUMN" for m in migrations for a in m["alterations"]), "alter_foreign_keys": sum("foreign_key" in a for m in migrations for a in m["alterations"]), "versioned_runners": len(runners)}, "migrations": migrations, "inputs": [{"file": Path(os.path.relpath(p, ROOT)).as_posix(), "sha256": fingerprint(p)} for p in inputs]}


def cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def documents(data):
    reviews = {}
    for path in sorted((OUTPUT / "reviews").glob("*.json")):
        for review in json.loads(path.read_text(encoding="utf-8"))["migrations"]:
            if review["id"] in reviews:
                raise ValueError("Repeated migration review: " + review["id"])
            reviews[review["id"]] = review
    if set(reviews) != {m["id"] for m in data["migrations"]}:
        raise ValueError("Every migration must have exactly one human/agent source review")
    lines = ["# Inventario de migraciones SQL Server", "", "P1.1 · 2026-10-24. Inventario estático reproducible; no se consultó ni modificó ninguna base. Declaraciones del repositorio no prueban aplicación en la base institucional. Los ALTER y cambios dinámicos se conservan por separado.", "", "## Recuento", ""]
    lines.extend(f"- {key}: {value}" for key, value in data["summary"].items())
    lines.extend(["", "**010 no existe:** no es una migración pendiente de aplicar ni se debe rellenar el ordinal por inferencia. El plan P0 decía 20 por el máximo ordinal; existen 19 archivos.", "", "## Secuencia y dependencias", "", "| ID | Propósito | Tablas | Dependencias por FK | Runner encontrado |", "|---|---|---:|---|---|"])
    for m in data["migrations"]:
        lines.append(f"| [{m['id']}](../../../{m['file']}) | {cell(reviews[m['id']]['purpose'])} | {len(m['tables'])} | {cell(', '.join(Path(p).name[:3] for p in m['fk_dependencies']) or '—')} | {cell(', '.join(Path(r['file']).name for r in m['runners']) or 'No versionado en tools')} |")
    lines.extend(["", "Las dependencias FK no sustituyen guards, contratos, orden dentro de runners ni prerrequisitos documentados. Ver revisiones [001–009](reviews/001-009.json), [011–020](reviews/011-020.json), [compatibilidad](COMPATIBILITY_SQL2019.md) y [mapa por capacidad](CAPABILITY_MAP.md). Ninguno de estos enlaces es un comando de aplicación."])
    for m in data["migrations"]:
        review = reviews[m["id"]]
        lines.extend(["", f"## {Path(m['file']).name}", "", review["purpose"], "", "**Reejecución y drift:** " + review["idempotency"], "", "**Escrituras iniciales:** " + (json.dumps(review["seed_writes"], ensure_ascii=False) if isinstance(review["seed_writes"], dict) else review["seed_writes"]), "", "**Efectos core:** " + review["core_effects"], "", "**Contratos y guards:** ver el fragmento de revisión y el SQL citado; no se ejecutaron. El mínimo operativo de la aplicación debe incluir las consultas JSON del runtime, además del DDL."])
        if m["alterations"]:
            lines.extend(["", "**ALTER detectados (históricos, no aplicados por este inventario):**", ""])
            lines.extend(f"- `{a['table']}`, línea {a['line']}: `{a['statement']}`" for a in m["alterations"])
    (OUTPUT / "MIGRATIONS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    lines = ["# Catálogo de declaraciones SQL", "", "Columnas y restricciones de CREATE TABLE, no esquema real ni esquema final reconstruido. Índices UNIQUE/PK declarados como restricciones figuran en la definición de columna o en las restricciones de tabla; el recuento de CREATE INDEX sólo cubre sentencias explícitas. Las definiciones retienen tipos, CHECK, DEFAULT, collation, IDENTITY y claves para revisar el contrato."]
    for m in data["migrations"]:
        for table in m["tables"]:
            lines.extend(["", f"## {table['name']}", "", f"[Declaración {m['id']}:{table['line']}](../../../{m['file']}#L{table['line']}).", "", "| Columna | Tipo | NULL explícito | Definición | Línea |", "|---|---|---|---|---:|"])
            for c in table["columns"]:
                lines.append(f"| {c['name']} | {c['type']} | {'No' if c['nullable'] is False else 'Sí' if c['nullable'] is True else 'No declarado'} | {cell(c['definition'])} | {c['line']} |")
            for kind, items in (("Restricciones de tabla", table["constraints"]), ("Claves foráneas", table["foreign_keys"])):
                if items:
                    lines.extend(["", f"**{kind}:**", ""])
                    lines.extend(f"- Línea {item['line']}: `{item['definition']}`" for item in items)
            indexes = [i for mig in data["migrations"] for i in mig["indexes"] if i["table"].lower() == table["name"].lower()]
            if indexes:
                lines.extend(["", "**CREATE INDEX explícitos:**", ""])
                lines.extend(f"- `{i['name']}`: {'UNIQUE ' if i['unique'] else ''}({i['keys']}) {i['tail']} · [{i['file']}:{i['line']}](../../../{i['file']}#L{i['line']})." for i in indexes)
            changes = [a for mig in data["migrations"] for a in mig["alterations"] if a["table"].lower() == table["name"].lower()]
            if changes:
                lines.extend(["", "**ALTER históricos posteriores (revisar además de CREATE):**", ""])
                lines.extend(f"- [{a['file']}:{a['line']}](../../../{a['file']}#L{a['line']}): `{a['statement']}`" for a in changes)
            consumers = table["literal_consumers"]
            lines.extend(["", "**Consumidores literales:** " + (", ".join(f"[{c['file']}:{c['first_line']}](../../../{c['file']}#L{c['first_line']})" for c in consumers) or "No encontrados; revisar SQL dinámico antes de concluir que no hay uso.")])
    (OUTPUT / "SCHEMA_CATALOG.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    mapping = json.loads((OUTPUT / "capability-map.json").read_text(encoding="utf-8"))
    declared = {t["name"] for m in data["migrations"] for t in m["tables"]}
    mapped = [t for group in mapping["groups"] for t in group["target_tables"]]
    if len(mapped) != len(set(mapped)) or set(mapped) != declared:
        raise ValueError("Capability mapping must cover every declared table exactly once")
    lines = ["# Mapa de persistencia por capacidad", "", "P1.1 · 2026-10-24. Mapeo semántico revisado, no equivalencia de esquemas ni propuesta de crear una tabla SQL Server por cada tabla SaaS. Las tablas destino están declaradas en fuente; no se verificó su presencia en la base. La ausencia de equivalente DDL significa diseño pendiente, no permiso para crearlo.", "", f"Cobertura: {len(mapped)}/{len(declared)} tablas destino, {len(mapping['groups'])} grupos. Las columnas, claves e índices existentes se detallan en [el catálogo](SCHEMA_CATALOG.md)."]
    for group in mapping["groups"]:
        lines.extend(["", f"## {group['id']} · {group['capability']}", "", f"**Clasificación:** {group['classification']}. **Etapa:** {group['phase']}.", "", "**Destino:** " + (", ".join(f"`{t}`" for t in group["target_tables"]) or "Sin estructura equivalente declarada; diseño pendiente."), "", "**Referencia Scentra:** " + (", ".join(f"`{t}`" for t in group["source_tables"]) or "Función educativa nativa; conservar sin duplicar SIIE."), "", group["notes"], ""])
        for evidence in group["source_evidence"]:
            path = (ROOT / evidence["file"]).resolve()
            if not path.is_file() or not 1 <= evidence["line"] <= len(path.read_text(encoding="utf-8-sig").splitlines()):
                raise ValueError("Invalid mapping evidence")
        lines.append("**Evidencia:** " + ", ".join(f"[{e['file']}:{e['line']}](../../../{e['file']}#L{e['line']})" for e in group["source_evidence"]) + ".")
    (OUTPUT / "CAPABILITY_MAP.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def graph(data):
    from adaptation_graphs import render

    nodes, edges = [], []
    owners = {t["name"].lower(): m["id"] for m in data["migrations"] for t in m["tables"]}
    for m in data["migrations"]:
        mid = "migration_" + m["id"]
        nodes.append({"id": mid, "label": "Migración " + Path(m["file"]).name, "file_type": "code", "source_file": m["file"], "source_location": "L1", "verification": "source_only"})
        for table in m["tables"]:
            tid = "table_" + table["name"].lower()
            nodes.append({"id": tid, "label": table["name"], "file_type": "code", "source_file": m["file"], "source_location": f"L{table['line']}"})
            edges.append({"source": mid, "target": tid, "relation": "declares_table", "confidence": "EXTRACTED", "confidence_score": 1.0, "source_file": m["file"]})
            for column in table["columns"]:
                cid = tid + "." + column["name"].lower()
                nodes.append({"id": cid, "label": table["name"] + "." + column["name"], "file_type": "code", "source_file": m["file"], "source_location": f"L{column['line']}", "sql_type": column["type"]})
                edges.append({"source": tid, "target": cid, "relation": "declares_column", "confidence": "EXTRACTED", "confidence_score": 1.0, "source_file": m["file"]})
            for number, fk in enumerate(table["foreign_keys"]):
                target = "table_" + fk["target_table"].lower()
                if fk["target_table"].lower() not in owners:
                    raise ValueError("External FK target requires explicit review: " + fk["target_table"])
                fid = "fk_" + table["name"].lower() + "_" + str(number)
                nodes.append({"id": fid, "label": table["name"] + "(" + ",".join(fk["source_columns"]) + ") → " + fk["target_table"] + "(" + ",".join(fk["target_columns"]) + ")", "file_type": "code", "source_file": m["file"], "source_location": f"L{fk['line']}"})
                edges.extend({"source": a, "target": b, "relation": relation, "confidence": "EXTRACTED", "confidence_score": 1.0, "source_file": m["file"], "source_location": f"L{fk['line']}"} for a, b, relation in [(tid, fid, "declares_fk"), (fid, target, "references_table")])
        for dependency in m["fk_dependencies"]:
            edges.append({"source": mid, "target": "migration_" + Path(dependency).name[:3], "relation": "requires_declared_fk_target", "confidence": "INFERRED", "confidence_score": 0.9, "source_file": m["file"]})
        for alteration in m["alterations"]:
            if alteration["table"].lower() in owners:
                tid = "table_" + alteration["table"].lower()
                edges.append({"source": mid, "target": tid, "relation": "contains_alter_reference", "confidence": "EXTRACTED", "confidence_score": 1.0, "source_file": m["file"], "source_location": f"L{alteration['line']}"})
                if alteration.get("column", {}).get("action") == "ADD":
                    column = alteration["column"]
                    cid = tid + "." + column["name"].lower()
                    nodes.append({"id": cid, "label": alteration["table"] + "." + column["name"], "file_type": "code", "source_file": m["file"], "source_location": f"L{alteration['line']}", "sql_type": column["type"], "declaration_kind": "ALTER_ADD"})
                    edges.append({"source": tid, "target": cid, "relation": "adds_column", "confidence": "EXTRACTED", "confidence_score": 1.0, "source_file": m["file"]})
                    if "foreign_key" in alteration:
                        target = "table_" + alteration["foreign_key"]["target_table"].lower()
                        edges.append({"source": cid, "target": target, "relation": "references_table", "confidence": "EXTRACTED", "confidence_score": 1.0, "source_file": m["file"], "source_location": f"L{alteration['line']}"})
    for path in sorted((OUTPUT / "reviews").glob("*.json")):
        fragment = json.loads(path.read_text(encoding="utf-8"))["graph"]
        nodes.extend(fragment["nodes"])
        edges.extend(fragment["edges"])
    mapping = json.loads((OUTPUT / "capability-map.json").read_text(encoding="utf-8"))
    for group in mapping["groups"]:
        gid = "capability_" + group["id"]
        nodes.append({"id": gid, "label": group["capability"], "file_type": "document", "source_file": "docs/adaptation/sql/capability-map.json", "classification": group["classification"], "phase": group["phase"]})
        edges.extend({"source": gid, "target": "table_" + table.lower(), "relation": "maps_declared_target", "confidence": "EXTRACTED", "confidence_score": 1.0, "source_file": "docs/adaptation/sql/capability-map.json"} for table in group["target_tables"])
        for evidence in group["source_evidence"]:
            sid = "scentra_" + evidence["table"]
            nodes.append({"id": sid, "label": "Scentra " + evidence["table"], "file_type": "code", "source_file": evidence["file"], "source_location": f"L{evidence['line']}"})
            edges.append({"source": gid, "target": sid, "relation": "maps_source_reference", "confidence": "EXTRACTED", "confidence_score": 1.0, "source_file": "docs/adaptation/sql/capability-map.json"})
    stats = render({"nodes": nodes, "edges": edges}, ROOT / "graphify-out/sql-inventory", {"total_files": len(data["migrations"]), "total_words": 0})
    print("SQL source graph:", json.dumps(stats))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify immutable historical inputs, or the exact active snapshot with --active")
    parser.add_argument("--active", action="store_true", help="Read/write inventory.active.json for current runtime consumers; preserve the frozen inventory")
    parser.add_argument("--graph", action="store_true", help="Also rebuild the source-declaration graph with installed Graphify")
    args = parser.parse_args()
    if args.check and args.graph:
        parser.error("--check never writes graphs; use --active --graph separately")
    sample = "Id int, Amount decimal(20,8), Value nvarchar(max) CHECK(JSON_VALUE(Value,'$.a,b') IS NOT NULL), PRIMARY KEY(Id)"
    assert len(list(definitions(sample))) == 4
    assert balanced("(f('a)''b'), decimal(9,3)) tail", 0)[0] == "f('a)''b'), decimal(9,3)"
    output = OUTPUT / ("inventory.active.json" if args.active else "inventory.json")
    if not args.active:
        if not args.check:
            raise ValueError("inventory.json is frozen by SQL-C3; use --active to build the current consumer inventory")
        if args.graph:
            parser.error("Use --active --graph to rebuild the source graph")
        verify_frozen_release()
        stored = json.loads(output.read_text(encoding="utf-8"))
        immutable_inputs = [r for r in stored["inputs"] if r["file"].startswith(("backend/migrations/", "backend/tools/migrate_", "../saas-version/", "docs/adaptation/sql/"))]
        for record in immutable_inputs:
            if fingerprint(ROOT / record["file"]) != record["sha256"]:
                raise ValueError("Frozen historical inventory input changed: " + record["file"])
        for directory, pattern in (("backend/migrations", "*.sql"), ("backend/tools", "migrate_*.py")):
            actual = {p.relative_to(ROOT).as_posix() for p in (ROOT / directory).glob(pattern)}
            expected = {r["file"] for r in immutable_inputs if r["file"].startswith(directory + "/")}
            if actual != expected:
                raise ValueError("Historical migration/runner membership changed: " + directory)
        accepted = verify_active_checkpoint()
        print("Frozen historical SQL/runners/Scentra inventory verified; historical runtime hashes are not current-source acceptance.")
        print("Active checkpoint chain " + ("verified" if accepted else "not yet recorded; use --active for current consumers"))
        return
    verify_frozen_release()
    data = build()
    data["checkpoint_role"] = "active_runtime_consumers_not_applied_schema"
    data["historical_inventory_sha256"] = fingerprint(OUTPUT / "inventory.json")
    if args.check:
        stored = json.loads(output.read_text(encoding="utf-8"))
        if stored != data:
            raise ValueError("Inventory is stale: source/tool changed; review and regenerate")
        accepted = verify_active_checkpoint()
        print("Active inventory and current source fingerprints verified:", json.dumps(data["summary"]))
        print("Acceptance checkpoint chain " + ("verified" if accepted else "not yet recorded"))
        return
    OUTPUT.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.graph:
        graph(data)
    print(json.dumps(data["summary"]))


if __name__ == "__main__":
    main()
