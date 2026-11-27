"""Build a bounded, offline Graphify continuity snapshot; never touches the app.

Run with the Python interpreter that has graphifyy installed:
    python backend/tools/conversation_continuity_graph.py build
    python backend/tools/conversation_continuity_graph.py check

Semantic fragments are reviewed inputs, not generated assertions about current
production. To extend the documentary scope, add another continuity-20261127*.json
fragment with complete EOF coverage and source_sha256, then rebuild. Source hashes
must only be refreshed after re-reading/re-extracting the changed document.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "graphify-out"
FRAGMENTS = ROOT / "docs/adaptation/fragments"
FRAGMENT_GLOB = "continuity-20261127*.json"
CODE_SOURCES = (
    "backend/app/institutional/broadcast_audience.py",
    "backend/app/institutional/broadcast_followup.py",
    "backend/app/institutional/broadcast_conversation.py",
    "backend/app/institutional/broadcast_inbox.py",
    "backend/app/institutional/broadcast_dispatch.py",
    "backend/app/institutional/broadcast_consent_correction.py",
    "backend/app/institutional/broadcast_prospects.py",
    "backend/app/institutional/broadcast_report.py",
    "backend/app/institutional/commercial_followup.py",
    "backend/app/institutional/prospect_source_status.py",
    "backend/app/institutional/sales_memory.py",
    "backend/app/institutional/campaign_runtime.py",
    "backend/app/institutional/campaign_delivery.py",
    "backend/app/institutional/campaigns.py",
    "backend/app/institutional/campaign_metrics.py",
    "backend/app/institutional/contact_preference.py",
    "backend/app/institutional/campaign_api.py",
    "backend/app/institutional/campaign_policy.py",
    "backend/app/institutional/channel_events.py",
    "frontend/src/institution/BroadcastWorkspace.tsx",
    "frontend/src/institution/BroadcastProspectSetup.tsx",
    "frontend/src/institution/CampaignWorkspace.tsx",
    "frontend/src/institution/Workspace.tsx",
    "frontend/src/institution/NoContactList.tsx",
)
SNAPSHOT_NOTE = (
    "Vista específica de continuidad compilada el 27 de noviembre de 2026. "
    "Conserva los cortes históricos 24–26 y las fechas propias de nuevas fuentes; "
    "el AST refleja el checkout al construir. No equivale por sí sola a una lectura "
    "productiva en vivo ni a un inventario completo del repositorio o sus conversaciones."
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(value: str) -> str:
    """Reject out-of-scope/private paths, rather than silently making them public."""
    path = Path(value)
    absolute = (path if path.is_absolute() else ROOT / path).resolve()
    result = absolute.relative_to(ROOT).as_posix()
    if not result.startswith(("backend/", "frontend/", "docs/adaptation/", "artifacts/live/")):
        raise ValueError(f"Source outside the explicit public scope: {result}")
    return result


def fingerprint(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def portable_diagnostic(summary: dict) -> dict:
    """Keep installed-package provenance without publishing a user's home path."""
    producer = summary.get("producer_suppression", {})
    if producer.get("path"):
        producer["path"] = "graphify/" + Path(producer["path"]).name
    return summary


def save_followup_query() -> dict:
    """Query a bounded directed semantic neighbourhood, without silent truncation."""
    from graphify.build import build_from_json
    from graphify.serve import _query_graph_text

    graph_path = OUT / "graph.json"
    graph = build_from_json(load(graph_path), root=ROOT, directed=True)
    scope_sources = {
        "docs/adaptation/FOLLOWUP_SEQUENCE_POLICY_20261127.md",
        "artifacts/live/followup-automation-20261127.json",
    }
    selected_nodes = [node_id for node_id, node in graph.nodes(data=True)
                      if node.get("_origin") == "semantic"
                      and node.get("source_file") in scope_sources
                      and not node_id.endswith(("_document", "_documento", "_informe"))]
    focused = graph.subgraph(selected_nodes).copy()
    if not selected_nodes:
        raise ValueError("No current follow-up semantic sources were found")
    vocabulary = set()
    for _, node in focused.nodes(data=True):
        for word in re.findall(r"[^\W\d_]+", node.get("label", ""), re.UNICODE):
            parts = re.findall(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+", word) or [word]
            vocabulary.update(part.lower() for part in parts if 3 <= len(part) <= 30)
    selected = [word for word in ("contactar", "cierre", "general", "borrador", "avance", "activador",
                                 "avanzados", "recorridos", "aprobado")
                if word in vocabulary]
    if not selected:
        raise ValueError("No follow-up vocabulary is present; query was not fabricated")
    (OUT / ".vocab.txt").write_text("\n".join(sorted(vocabulary)), encoding="utf-8")
    output = _query_graph_text(focused, " ".join(selected), depth=1, token_budget=8000)
    found = re.search(r"\|\s*(\d+) nodes found", output)
    rendered = sum(line.lstrip().startswith("NODE ") for line in output.splitlines())
    complete = bool(found) and int(found.group(1)) == rendered and "truncat" not in output.casefold()
    if not complete:
        raise ValueError("Focused query was truncated or empty; it has not replaced the saved query")
    sources = sorted({node["source_file"] for _, node in focused.nodes(data=True)})
    payload = {
        "original_question": "tienes conocimiento sobre los seguimientos a las conversaciones?",
        "focused_question": "No contactar, cierre, flujo general y borradores por avance",
        "expanded_tokens": selected,
        "command": ["python", "backend/tools/conversation_continuity_graph.py", "query"],
        "run_from": ".", "exit_code": 0, "graph_sha256": sha(graph_path),
        "scope": {"sources": sources, "semantic_only": True, "document_anchors_excluded": True,
                  "scope_nodes": len(selected_nodes), "directed": True, "depth": 1},
        "complete": complete, "nodes_found": int(found.group(1)), "nodes_rendered": rendered,
        "estimated_token_budget": 8000, "stdout": output, "stderr": "",
    }
    write(OUT / "query-followup.json", payload)
    (OUT / "query-followup.txt").write_text(
        "Consulta Graphify local acotada a conceptos de seguimiento; no ejecuta acciones.\n"
        + f"Completitud: {rendered}/{found.group(1)} nodos, sin truncamiento; profundidad1.\n"
        + "Las fuentes conservan sus cortes históricos; no fusionar versiones de fechas distintas.\n"
        + "Tokens de etiquetas: " + ", ".join(selected) + "\n\n" + output, encoding="utf-8")
    manifest_path = OUT / "source-manifest.json"
    if manifest_path.exists():
        manifest = load(manifest_path)
        if manifest.get("graph_sha256") == payload["graph_sha256"]:
            manifest["query_sha256"] = sha(OUT / "query-followup.json")
            write(manifest_path, manifest)
    return {"ok": True, "nodes_found": payload["nodes_found"], "nodes_rendered": rendered,
            "complete": complete, "scope_sources": sources, "expanded_tokens": selected}


def read_fragments() -> tuple[dict, dict, list[str]]:
    semantic = {"nodes": [], "edges": [], "hyperedges": []}
    sources: dict[str, dict] = {}
    fragments = sorted(FRAGMENTS.glob(FRAGMENT_GLOB))
    if not fragments:
        raise ValueError("No reviewed semantic fragments were found")
    for fragment in fragments:
        data = load(fragment)
        coverage = data.get("coverage", {})
        hashes = data.get("source_sha256", {})
        if not coverage or set(coverage) != set(hashes):
            raise ValueError(f"Coverage/hash mismatch: {fragment.name}")
        represented = {relative(n["source_file"]) for n in data["nodes"]}
        for raw_path, lines in coverage.items():
            path = relative(raw_path)
            if path in sources:
                raise ValueError(f"Overlapping fragment coverage: {path}")
            source = ROOT / path
            actual_lines = len(source.read_text(encoding="utf-8-sig").splitlines())
            if lines != actual_lines or sha(source) != hashes[raw_path]:
                raise ValueError(f"Stale or partial semantic extraction: {path}")
            if path not in represented:
                raise ValueError(f"Covered file has no semantic node: {path}")
            sources[path] = {"sha256": sha(source), "lines": lines, "kind": "semantic"}
        for section in semantic:
            for raw in data.get(section, []):
                item = copy.deepcopy(raw)
                if item.get("source_file"):
                    item["source_file"] = relative(item["source_file"])
                    if item["source_file"] not in coverage:
                        raise ValueError(f"Uncovered semantic provenance: {item['source_file']}")
                item["_origin"] = "semantic"
                semantic[section].append(item)
    ids = [n["id"] for n in semantic["nodes"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate semantic node IDs; resolve explicitly before building")
    known = set(ids)
    for edge in semantic["edges"]:
        if edge["source"] not in known or edge["target"] not in known:
            raise ValueError("Semantic edge has a missing endpoint")
    return semantic, sources, [p.relative_to(ROOT).as_posix() for p in fragments]


def explicit_document_code_links(semantic: dict, ast: dict, sources: dict) -> list[dict]:
    """Link only literal, exact source-path mentions; never infer implementation."""
    anchors = {
        n["source_file"]: n["id"] for n in semantic["nodes"]
        if str(n["source_location"]).lower() in ("documento completo", "línea 1: documento completo")
    }
    # Chunk 1 uses the documented suffix for its file anchor.
    for n in semantic["nodes"]:
        if n["id"].endswith(("_documento", "_document")):
            anchors[n["source_file"]] = n["id"]
    modules = {
        n["source_file"]: n["id"] for n in ast["nodes"]
        if n.get("source_file") in CODE_SOURCES
        and n.get("label") == Path(n["source_file"]).name
    }
    links = []
    for source in sorted(sources):
        if source not in anchors:
            continue
        lines = (ROOT / source).read_text(encoding="utf-8-sig").splitlines()
        for code, module in sorted(modules.items()):
            hits = [i for i, line in enumerate(lines, 1) if code in line]
            if hits:
                links.append({
                    "source": anchors[source], "target": module, "relation": "references",
                    "confidence": "EXTRACTED", "confidence_score": 1.0,
                    "source_file": source, "source_location": ", ".join(f"L{i}" for i in hits),
                    "context": "Referencia literal a la ruta de código; no acredita comportamiento ejecutado.",
                    "weight": 1.0, "_origin": "semantic",
                })
    return links


def make_view(raw: dict) -> tuple[dict, list[dict], list[dict], list[dict]]:
    """Retain every raw assertion separately; compact pairs with all provenance."""
    known = {n["id"] for n in raw["nodes"]}
    excluded = []
    self_loops = []
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for edge in raw["edges"]:
        if edge.get("source") not in known or edge.get("target") not in known:
            excluded.append(edge)
        elif edge["source"] == edge["target"]:
            self_loops.append(edge)
        else:
            grouped[(edge["source"], edge["target"])].append(edge)
    duplicate_pairs = []
    edges = []
    for (source, target), assertions in grouped.items():
        edge = copy.deepcopy(assertions[0])
        if len(assertions) > 1:
            evidence = [{k: v for k, v in assertion.items() if k not in ("source", "target")}
                        for assertion in assertions]
            edge["parallel_assertions"] = evidence
            edge["parallel_assertion_count"] = len(assertions)
            duplicate_pairs.append({"source": source, "target": target, "assertions": evidence})
        edges.append(edge)
    return {**copy.deepcopy(raw), "edges": edges}, excluded, duplicate_pairs, self_loops


def community_labels(graph, communities: dict) -> dict:
    """Curated names refer to the highest-ranked actual member's source."""
    names = {
        "campaigns": "Gestión de campañas",
        "campaign_metrics": "Métricas de seguimiento",
        "contact_preference": "Preferencias y exclusiones",
        "campaign_api": "API de campañas",
        "channel_events": "Eventos y recibos entrantes",
        "COMMERCIAL_PROGRESS_FOLLOWUP_20261125": "Avance comercial y exclusiones",
        "BroadcastWorkspace": "Panel de mensajería masiva",
        "CampaignWorkspace": "Panel de campañas y seguimiento",
        "Workspace": "Espacio institucional",
        "NoContactList": "Lista de no contactar",
        "commercial_followup": "Seguimiento comercial",
        "broadcast_prospects": "Importación de prospectos",
        "CRM_FOLLOWUPS_20261124": "Seguimiento y preferencias",
        "sales_memory": "Memoria comercial",
        "P23_SIIE_IMPLEMENTATION_20261125": "Contrato y límites SIIE",
        "broadcast_audience": "Destinatarios y elegibilidad",
        "CRM_IMPORT_2026_20261126": "Importación del lote 2026",
        "campaign_policy": "Políticas de campañas",
        "AGENT_LANGUAGE_STAGES_20261125": "Motores por etapa",
        "PREICFES_CAMPAIGN_LAUNCH_20261125": "Campaña PRE-ICFES y destinos",
        "SIIE_WEBHOOK_PILOT_20261125": "Piloto y recepción SIIE",
        "P24_INBOX_LIST_DIAGNOSIS_20261125": "Diagnóstico de listas",
        "broadcast_conversation": "Detalle de conversación",
        "BROADCAST_REPORT_TIMEOUT_20261125": "Informe y consultas agregadas",
        "PROGRAM_HOURS_AND_COST_SCOPE_20261124": "Horarios y costes",
        "campaign_delivery": "Entrega y recibos",
        "CAMPAIGN_ADVISOR_ENTRY_20261124": "Respuesta y entrada al Inbox",
        "INBOX_EDITS_SENDERS_PREICFES_20261125": "Ediciones y remitentes",
        "PREICFES_PROSPECTS_20261125": "Prospectos y promoción PRE-ICFES",
        "PROGRAM_CAMPAIGNS_20261124": "Campañas por programa",
        "INBOX_QUEUE_STORAGE_WAIT_20261125": "Espera interna y continuidad",
        "INBOX_RESPONSE_RECOVERY_20261125": "Recuperación de respuestas",
        "HIGHER_INITIAL_PAYMENT_POLICY_20261124": "Política de abono inicial",
        "INBOX_STORAGE_CONTENTION_20261124": "Contención de almacenamiento",
        "MASTERCLASS_INTERESTS_20261124": "Intereses en clases abiertas",
        "P23_RINOVA_WEBHOOK_PREPARATION_20261125": "Preparación del receptor SIIE",
        "broadcast_report": "Métricas de campañas",
        "broadcast_inbox": "Promoción y bandeja entrante",
    }
    result = {}
    for cid, members in communities.items():
        ranked = sorted(members, key=lambda n: (
            graph.nodes[n].get("_origin") == "semantic", graph.degree(n), n), reverse=True)
        label = graph.nodes[ranked[0]].get("label", ranked[0])
        words = str(label).replace("_", " ").split()
        stem = Path(graph.nodes[ranked[0]].get("source_file", "")).stem
        result[cid] = names.get(stem, " ".join(words[:5]))
    return result


def current_sources(semantic_sources: dict, fragments: list[str]) -> dict:
    sources = dict(semantic_sources)
    for path in (*CODE_SOURCES, *fragments, relative(str(Path(__file__)))):
        source = ROOT / path
        sources[path] = {"sha256": sha(source),
                         "lines": len(source.read_text(encoding="utf-8-sig").splitlines()),
                         "kind": "code" if path in CODE_SOURCES else "build_input"}
    return dict(sorted(sources.items()))


def discover_document_scope() -> list[str]:
    return sorted(p.relative_to(ROOT).as_posix()
                  for p in (ROOT / "docs/adaptation").glob("*2026112[4567].md"))


def spanish_report(manifest: dict, analysis: dict) -> str:
    counts = manifest["counts"]
    integrity = manifest["integrity_counts"]
    lines = ["# Grafo de continuidad de RinovaPlus", "", SNAPSHOT_NOTE, "",
             "Esta vista específica complementa el grafo general histórico en "
             "`graphify-out/live-project-20261126/`; no lo sustituye ni lo modifica.", "",
             "## Alcance y procedencia", "",
             f"{counts['semantic_sources']} fuentes documentales/JSON agregados con lectura completa "
             f"hasta EOF y SHA-256, más {counts['code_sources']} archivos de código por AST. "
             f"La vista dirigida contiene {counts['nodes']} nodos y {counts['edges']} aristas "
             f"en {counts['communities']} comunidades. No incluye fichas nominales, teléfonos "
             "ni conversaciones privadas. El número de nodos no mide implementación ni aceptación.", "",
             "Candidatos fechados presentes pero fuera de la selección semántica: "
             + json.dumps(manifest["uncovered_dated_documents"], ensure_ascii=False)
             + ". Su aparición se informa; no se finge haberlos extraído.", "",
             "## Integridad y límites", "",
             f"La extracción AST aporta {counts['ast_nodes']} nodos y {counts['ast_edges']} aristas. "
             f"Se excluyen de la vista {integrity['excluded_dangling_edges']} aristas con extremo "
             "ausente. Sus afirmaciones originales se conservan en raw-extraction.json y "
             "sus detalles en integrity.json. Son referencias/importaciones fuera del ámbito "
             "o destinos no resueltos; no se han inventado nodos para completarlas.", "",
             f"También se excluyen explícitamente {integrity['excluded_self_loop_edges']} "
             "autobucle(s) emitido(s) por el AST. Los originales permanecen en integrity.json "
             "y raw-extraction.json: un autobucle del extractor no acredita por sí mismo "
             "recursión funcional. Esta separación hace visible lo que Graphify descartaría "
             "internamente al construir la vista.", "",
             f"Hay {integrity['duplicate_pair_groups']} par(es) dirigido(s) con varias afirmaciones "
             f"({integrity['compacted_parallel_edges']} arista(s) compactada(s)). Una identidad "
             "AST puede agrupar referencias de distintas líneas: no equivale a dos "
             "implementaciones distintas en este grafo. parallel_assertions preserva "
             "las procedencias en graph.json; "
             "el original completo permanece en raw-extraction.json.", "",
             "Pares compactados y ubicaciones: "
             + json.dumps(manifest["parallel_pair_summary"], ensure_ascii=False) + ".", "",
             f"Enlaces documento→código: {counts['literal_code_references']}, exclusivamente por "
             "rutas literales presentes en las fuentes. Dirección conservada mediante DiGraph. "
             "Graphify agrupa comunidades sobre una proyección no dirigida internamente; "
             "esto no cambia la dirección de las aristas exportadas.", "",
             "## Seguimientos: lectura correcta", "",
             "El avance comercial, la etapa CRM, el consentimiento y los recibos de entrega "
             "son conceptos distintos. Los cortes documentan formulario enviado, interés "
             "confirmado y casos por aclarar; una respuesta no equivale a matrícula. Los "
             "avances excluyen la reactivación general y orientan el próximo seguimiento. "
             "Los borradores de flujos no prueban activación ni aprobación de Meta. "
             "Consultar las fuentes y fechas de cada nodo antes de usarlo para actuar.", "",
             "P23 conserva 0/9 aceptaciones: la recepción real SIIE no equivale al evento "
             "sintético, a vínculo de identidad aceptado ni a PDF/pagos finalizados. P24 "
             "sigue como diagnóstico: 0% de implementación y 0/6 aceptaciones. Las "
             "propuestas de rendimiento no se presentan como cambios publicados. Los "
             "errores y cortes históricos permanecen diferenciados del estado actual.", "",
             "## Comunidades y cohesión", "",
             "La cohesión es el resultado numérico de Graphify, sin umbral de aprobación.", "",
             "| Comunidad | Nodos | Cohesión |", "|---|---:|---:|"]
    for key, nodes in analysis["communities"].items():
        label = analysis["labels"][key].replace("|", "/")
        lines.append(f"| {label} | {len(nodes)} | {analysis['cohesion'][key]} |")
    lines += ["", "## Nodos centrales", "", "```json",
              json.dumps(analysis["gods"][:5], ensure_ascii=False, indent=2), "```", "",
              "## Conexiones entre comunidades", "", "```json",
              json.dumps(analysis["surprises"][:5], ensure_ascii=False, indent=2), "```", "",
              "## Consultas sugeridas", "",
              "Usar etiquetas presentes en graph.json; la búsqueda por términos no "
              "presentes puede omitir conceptos. El recorrido demuestra acceso al grafo, "
              "no ejecución de seguimiento ni estado productivo.", "",
              "- `python backend/tools/conversation_continuity_graph.py query`",
              "- `graphify query \"P23 aceptación webhook recepción\" --budget 1200`", "",
              "## Reproducir y comprobar vigencia", "",
              "Ejecutar con el intérprete local que tenga instalado graphifyy:", "",
              "```text", "python backend/tools/conversation_continuity_graph.py build",
              "python backend/tools/conversation_continuity_graph.py check", "```", "",
              "`build` usa únicamente AST local y fragmentos revisados; no llama modelos, "
              "SQL, HTTP, RinovaPlus ni Meta. Exporta JSON antes del HTML y del informe; "
              "respeta el bloqueo de reducción de Graphify y no usa force. `check` "
              "compara SHA-256 de fuentes, fragmentos, constructor y grafo; también "
              "detecta documentos nuevos del ámbito fechado 24–27 de noviembre. Devuelve "
              "código 2 ante cambios, faltantes o nuevas fuentes aún no incluidas.", "",
              "Cada construcción también regenera `query-followup.json` y "
              "`query-followup.txt` mediante una consulta real de Graphify, limitada a "
              "conceptos semánticos del informe de seguimiento y su evidencia final, "
              "profundidad1 y hasta8.000 tokens estimados. Usa sólo términos de etiquetas, "
              "conserva la dirección y excluye anclas documentales y módulos AST para "
              "acotar el vecindario. Exige que todos los nodos encontrados se impriman, "
              "sin truncamiento. El JSON guarda contadores, ámbito, comando reproducible "
              "y SHA-256 del grafo. No ejecuta acciones en RinovaPlus.", "",
              "Para ampliar el ámbito, leer íntegramente el documento nuevo y añadir un "
              "fragmento `docs/adaptation/fragments/continuity-20261127-03.json` con "
              "`nodes`, `edges`, `hyperedges`, `coverage` (líneas hasta EOF) y "
              "`source_sha256` (bytes del archivo). Usar rutas relativas con `/`, "
              "`_origin: semantic`, evidencia y confianza; no basta actualizar el hash "
              "sin renovar la extracción. El constructor descubre todos los fragmentos "
              "de ese prefijo y exige cobertura sin solapamientos. Para nuevas áreas "
              "de código, ampliar CODE_SOURCES deliberadamente y reconstruir.", "",
              "No se instalaron hooks de Git, observadores, servicios ni automatización "
              "de actualización. Esto es un snapshot; no se mantiene solo. El manifiesto "
              "enumera exactamente lo incluido. Los archivos graphify-out/ se escriben "
              "en el árbol de trabajo; su publicación depende de las reglas del repositorio.", "",
              "La generación del HTML es local. El visualizador estándar de Graphify "
              "carga vis-network desde un CDN cuando se abre; no se descargó esa biblioteca "
              "durante la construcción. JSON, informe y comprobación de vigencia no la necesitan.", "",
              "## Coste y reproducibilidad", "",
              "Cero invocaciones externas de modelos desde este constructor. La extracción "
              "semántica fue realizada por la sesión y sus subagentes; sus tokens y coste "
              "no se midieron. Los ceros heredados del protocolo no representan consumo "
              "total nulo. AST y exportación son locales. Versión Graphify: "
              f"`{manifest['graphify_version']}`. Huella de entradas: "
              f"`{manifest['input_fingerprint']}`. El informe nativo de la API Graphify "
              "se conserva como graphify-analysis-native.md; este es el informe en español.", ""]
    return "\n".join(lines)


def build() -> dict:
    # Imports stay inside build: `check` works with standard-library Python only.
    from graphify.analyze import god_nodes, suggest_questions, surprising_connections
    from graphify.build import build_from_json
    from graphify.cluster import cluster, score_all
    from graphify.detect import save_manifest
    from graphify.diagnostics import diagnose_extraction
    from graphify.export import to_html, to_json
    from graphify.extract import extract
    from graphify.report import generate

    semantic, documentary_sources, fragments = read_fragments()
    sources = current_sources(documentary_sources, fragments)
    OUT.mkdir(exist_ok=True)
    ast = extract([ROOT / path for path in CODE_SOURCES], root=ROOT, cache_root=ROOT,
                  parallel=False)
    for section in ("nodes", "edges"):
        for item in ast[section]:
            if item.get("source_file"):
                item["source_file"] = relative(item["source_file"])
            item["_origin"] = "ast"
    literal_links = explicit_document_code_links(semantic, ast, documentary_sources)
    raw = {"nodes": ast["nodes"] + semantic["nodes"],
           "edges": ast["edges"] + semantic["edges"] + literal_links,
           "hyperedges": semantic["hyperedges"], "input_tokens": 0, "output_tokens": 0}
    raw_diagnostic = portable_diagnostic(
        diagnose_extraction(copy.deepcopy(raw), root=ROOT, directed=True))
    view, excluded, duplicate_pairs, self_loops = make_view(raw)
    graph = build_from_json(copy.deepcopy(view), root=ROOT, directed=True)
    if graph.number_of_nodes() == 0:
        raise ValueError("Empty graph: existing outputs have not been overwritten")
    if graph.number_of_nodes() != len(raw["nodes"]):
        raise ValueError("Unexpected node merge; investigate before publishing a partial graph")
    graph.graph.update(snapshot_note=SNAPSHOT_NOTE, semantic_source_count=len(documentary_sources),
                       code_source_count=len(CODE_SOURCES),
                       excluded_dangling_edge_count=len(excluded),
                       excluded_self_loop_edge_count=len(self_loops),
                       compacted_parallel_edge_count=sum(len(p["assertions"]) - 1 for p in duplicate_pairs))
    communities = cluster(graph)
    cohesion = score_all(graph, communities)
    labels = community_labels(graph, communities)
    gods = god_nodes(graph)
    surprises = surprising_connections(graph, communities)
    questions = suggest_questions(graph, communities, labels)
    if current_sources(documentary_sources, fragments) != sources:
        raise ValueError("Inputs changed during AST extraction; rerun with a stable source snapshot")
    if not to_json(graph, communities, str(OUT / "graph.json"), force=False,
                   built_at_commit="", community_labels=labels):
        raise ValueError("Graphify shrink guard refused JSON; HTML/report were not overwritten")
    # Every secondary artifact is written only after the JSON guard succeeds.
    counts = {"semantic_sources": len(documentary_sources), "code_sources": len(CODE_SOURCES),
              "semantic_nodes": len(semantic["nodes"]), "semantic_edges": len(semantic["edges"]),
              "ast_nodes": len(ast["nodes"]), "ast_edges": len(ast["edges"]),
              "literal_code_references": len(literal_links), "raw_edges": len(raw["edges"]),
              "nodes": graph.number_of_nodes(), "edges": graph.number_of_edges(),
              "communities": len(communities)}
    integrity_counts = {
        "excluded_dangling_edges": len(excluded),
        "excluded_self_loop_edges": len(self_loops),
        "dangling_by_relation": dict(Counter(e.get("relation") for e in excluded)),
        "duplicate_pair_groups": len(duplicate_pairs),
        "compacted_parallel_edges": sum(len(p["assertions"]) - 1 for p in duplicate_pairs),
        "raw_missing_endpoints": raw_diagnostic["missing_endpoint_edges"],
        "raw_self_loops": raw_diagnostic["self_loop_edges"],
    }
    manifest = {"schema": 1, "snapshot_note": SNAPSHOT_NOTE, "sources": sources,
                "document_scope_pattern": "docs/adaptation/*2026112[4567].md",
                "discovered_document_scope": discover_document_scope(),
                "uncovered_dated_documents": sorted(set(discover_document_scope()) - set(documentary_sources)),
                "semantic_fragments": fragments, "counts": counts,
                "integrity_counts": integrity_counts, "input_fingerprint": fingerprint(sources),
                "parallel_pair_summary": [
                    {"source": p["source"], "target": p["target"],
                     "locations": [{"source_file": a.get("source_file"),
                                    "source_location": a.get("source_location")}
                                   for a in p["assertions"]]}
                    for p in duplicate_pairs],
                "graph_sha256": sha(OUT / "graph.json"),
                "graphify_version": importlib.metadata.version("graphifyy"),
                "cost": {"external_model_calls": 0, "host_tokens": None,
                         "note": "Session/subagent token consumption was not measured"}}
    analysis = {"communities": {str(k): v for k, v in communities.items()},
                "cohesion": {str(k): v for k, v in cohesion.items()},
                "labels": {str(k): v for k, v in labels.items()},
                "gods": gods, "surprises": surprises, "questions": questions}
    write(OUT / "raw-extraction.json", raw)
    write(OUT / ".graphify_ast.json", ast)
    write(OUT / ".graphify_semantic.json", semantic)
    write(OUT / "view-extraction.json", view)
    write(OUT / "integrity.json", {"raw_graphify_diagnostic": raw_diagnostic,
          "counts": integrity_counts, "excluded_edges": excluded,
          "excluded_self_loops": self_loops,
          "duplicate_pairs": duplicate_pairs,
          "view_graphify_diagnostic": portable_diagnostic(
              diagnose_extraction(copy.deepcopy(view), root=ROOT, directed=True))})
    write(OUT / "source-manifest.json", manifest)
    write(OUT / ".graphify_analysis.json", analysis)
    write(OUT / ".graphify_labels.json", analysis["labels"])
    # Save Graphify's own manifest too, limited to the files that produced output.
    categories = {"code": list(CODE_SOURCES), "document": sorted(documentary_sources)}
    absolute_categories = {kind: [str(ROOT / path) for path in paths]
                           for kind, paths in categories.items()}
    save_manifest(absolute_categories, str(OUT / "manifest.json"), root=ROOT,
                  scan_corpus={path for paths in absolute_categories.values() for path in paths})
    if graph.number_of_nodes() > 5000:
        print("WARNING: over 5,000 nodes; HTML uses an aggregated view")
    to_html(graph, communities, str(OUT / "graph.html"), community_labels=labels, node_limit=5000)
    detection = {"total_files": len(CODE_SOURCES) + len(documentary_sources),
                 "total_words": sum(len((ROOT / p).read_text(encoding="utf-8-sig").split())
                                    for p in documentary_sources), "files": categories}
    native_report = generate(graph, communities, cohesion, labels, gods, surprises,
                             detection, {"input": 0, "output": 0}, ".",
                             suggested_questions=questions, built_at_commit="")
    (OUT / "graphify-analysis-native.md").write_text(
        "> Tokens del host/subagentes no medidos; los ceros siguientes son placeholders.\n\n"
        + native_report, encoding="utf-8")
    (OUT / "GRAPH_REPORT.md").write_text(spanish_report(manifest, analysis), encoding="utf-8")
    save_followup_query()
    manifest["query_sha256"] = sha(OUT / "query-followup.json")
    write(OUT / "source-manifest.json", manifest)
    checked = check()
    return {"ok": checked["snapshot_current"], **counts, **integrity_counts,
            "scope_complete": checked["scope_complete"],
            "uncovered_dated_documents": checked["uncovered_dated_documents"],
            "input_fingerprint": manifest["input_fingerprint"]}


def check() -> dict:
    manifest = load(OUT / "source-manifest.json")
    changed, missing = [], []
    for path, expected in manifest["sources"].items():
        source = ROOT / relative(path)
        if not source.is_file():
            missing.append(path)
        elif sha(source) != expected["sha256"]:
            changed.append(path)
    graph_changed = not (OUT / "graph.json").is_file() or sha(OUT / "graph.json") != manifest["graph_sha256"]
    query_path = OUT / "query-followup.json"
    query_changed = not query_path.is_file() or sha(query_path) != manifest.get("query_sha256")
    if not query_changed:
        query_changed = load(query_path).get("graph_sha256") != manifest["graph_sha256"]
    actual_fragments = sorted(p.relative_to(ROOT).as_posix() for p in FRAGMENTS.glob(FRAGMENT_GLOB))
    new_fragments = sorted(set(actual_fragments) - set(manifest["semantic_fragments"]))
    covered = {path for path, metadata in manifest["sources"].items() if metadata["kind"] == "semantic"}
    new_documents = sorted(set(discover_document_scope()) - covered)
    snapshot_current = not (changed or missing or graph_changed or query_changed or new_fragments)
    result = {"ok": snapshot_current and not new_documents,
              "snapshot_current": snapshot_current, "scope_complete": not new_documents,
              "changed": changed, "missing": missing, "graph_changed": graph_changed,
              "query_changed": query_changed,
              "new_fragments": new_fragments, "uncovered_dated_documents": new_documents,
              "semantic_sources": manifest["counts"]["semantic_sources"],
              "input_fingerprint": manifest["input_fingerprint"],
              "note": "Checks local provenance only; does not attest current production state"}
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "check", "query"))
    args = parser.parse_args()
    if args.command == "build":
        result = build()
    elif args.command == "query":
        result = save_followup_query()
        print((OUT / "query-followup.txt").read_text(encoding="utf-8"))
    else:
        result = check()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
