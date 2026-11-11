"""Export canonical local metadata; --check never writes or mutates source."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.contracts import BUSINESS_ROUTES, STUB_ROUTES, contract_catalog
from app.local_registry import LOCAL_CONTRACTS
from app.main import create_app

root = Path(__file__).resolve().parents[2]
catalog = contract_catalog().model_dump(mode="json")
outputs = {
    root / "frontend/src/shared/endpointCatalog.json": json.dumps(
        catalog, indent=2, ensure_ascii=False
    )
    + "\n",
    root / "docs/contracts/local-openapi.json": json.dumps(
        create_app().openapi(), indent=2, ensure_ascii=False
    )
    + "\n",
}
header = (
    "# Cobertura generada del catálogo LOCAL\n\n"
    "Generado desde `backend/app/contracts.py`; no editar la tabla manualmente. "
    f"{len(catalog['routes'])} operaciones: {len(STUB_ROUTES)} stubs "
    "de negocio; incluye los adaptadores operativos locales de canales, "
    "recepción firmada Meta/TikTok con ingesta y despacho separados, "
    "cuatro catálogos de lectura optativos y metadatos sin secretos. "
    "IA y Clientes sintéticos tienen "
    "namespaces independientes. "
    "Ningún stub es un contrato productivo aprobado.\n\n"
    "| Método / ruta | Capacidad / fase | Esquema / respuesta | Fuente |\n"
    "|---|---|---|---|\n"
)
for route in catalog["routes"]:
    header += (
        f"| `{route['method']} {route['path']}` | "
        f"{route['capability']} / {route['phase']} | "
        f"{route['schema_status']}: {route['request_schema']} / "
        f"{route['response_status']} | `{route['source_locator']}` |\n"
    )
header += (
    "\nLa propuesta original de `GET /api/v1/catalog/programs` se conserva "
    "en `superseded_proposals`; su ruta HTTP pertenece exclusivamente al "
    "adaptador de lectura. Los esquemas planeados no sustituyen su DTO real.\n"
    "\n## Disposiciones sin ruta\n\n"
    + "\n".join(f"- `{key}`: {value}." for key, value in catalog["exclusions"].items())
    + "\n"
)
outputs[root / "docs/contracts/local-endpoint-coverage.md"] = header
definitions = {}
coverage = (
    "# Cobertura generada de esquemas LOCAL-v2\n\n"
    "Registro canónico `backend/app/local_registry.py`; 148 operaciones: "
    "135 `local_defined`, 13 cuerpos heredados `provisional`, cero pendientes LOCAL. "
    "77 cuerpos nuevos y 58 operaciones nuevas sin cuerpo. "
    "Todos los contratos conectados siguen `approval_pending`; 38 operaciones "
    "condicionales no activadas. Resultados planeados en componentes, "
    "nunca respuestas 200. "
    "[Ejemplos canónicos](local-schema-catalog.json), "
    "[guía](local-schema-guide.md).\n\n"
    "| Operación | Cuerpo / campos | Query / path | "
    "Resultado planeado / campos | Evidencia |\n"
    "|---|---|---|---|---|\n"
)
for proposal in BUSINESS_ROUTES:
    route = proposal.model_dump(mode="json")
    key = (route["method"], route["path"].removeprefix("/api/v1"))
    if key not in LOCAL_CONTRACTS:
        continue
    definition = LOCAL_CONTRACTS[key]
    definitions[route["operation_id"]] = {
        "contract": route,
        "input": {
            "path": definition.path_example.model_dump(mode="json"),
            "query": definition.query_example.model_dump(
                mode="json", exclude_none=True
            ),
            "body": definition.body_example.model_dump(mode="json", exclude_unset=True)
            if definition.body_example
            else None,
        },
        "planned_result": definition.result_example.model_dump(
            mode="json", exclude_unset=True
        ),
    }
    fields = (
        ", ".join(definition.body_model.model_fields)
        if definition.body_model
        else "sin cuerpo"
    )
    queries = ", ".join(definition.query_model.model_fields) or "ninguno"
    paths = ", ".join(definition.path_model.model_fields) or "ninguno"
    results = ", ".join(definition.result_model.model_fields)
    coverage += (
        f"| `{route['operation_id']}` | `{route['request_schema']}`: {fields} | "
        f"`{route['query_schema']}`: {queries}; `{route['path_schema']}`: {paths} | "
        f"`{route['planned_result_schema']}`: {results} | {route['evidence']} |\n"
    )
outputs[root / "docs/contracts/local-schema-catalog.json"] = (
    json.dumps(definitions, indent=2, ensure_ascii=False) + "\n"
)
outputs[root / "docs/contracts/local-schema-coverage.md"] = coverage
check = argparse.ArgumentParser()
check.add_argument("--check", action="store_true")
args = check.parse_args()
for path, content in outputs.items():
    if args.check:
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        equal = (
            json.loads(existing) == json.loads(content)
            if path.suffix == ".json" and existing
            else existing == content
        )
        if not equal:
            raise SystemExit(
                "Generated metadata differs: " + path.relative_to(root).as_posix()
            )
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
print("Canonical exports verified" if args.check else "Canonical exports generated")
