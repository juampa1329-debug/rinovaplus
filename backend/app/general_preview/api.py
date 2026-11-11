"""General local preview: accepted data and explicit progress for every section."""

import hmac
import json
import os
import time
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.general_preview.store import VERSION, Workspace, load, transaction
from app.modules.clients.api.router import install_clients
from app.modules.crm_configuration.application.service import install_crm_configuration
from app.modules.inbox.application.service import install_inbox
from app.parity_channels.repository import PROJECTIONS, result_row
from tools.foundation_snapshot import quote_name

SECTIONS = [
    ("admissions", "Admisiones", "P3", False),
    ("overview", "Resumen", "P3", True),
    ("clients", "Clientes y prospectos", "P3", True),
    ("inbox", "Inbox", "P3", True),
    ("channels", "Canales", "P4", True),
    ("assistant", "Asistente", "P5", False),
    ("agents", "Agentes de admisiones", "P5", False),
    ("knowledge", "Conocimiento", "P6", False),
    ("memory", "Memoria colectiva y ADN", "P6", False),
    ("broadcasts", "Mensajería masiva", "P7", False),
    ("campaigns", "Campañas y remarketing", "P8", False),
    ("ads", "Meta Ads", "P9", False),
    ("intelligence", "Inteligencia y entrenamiento", "P10", False),
    ("settings", "Ajustes CRM", "P2", True),
]


def create_app(settings, workspace=None):
    app = FastAPI(
        title="CRM CBN general preview", docs_url=None, redoc_url=None, openapi_url=None
    )
    app.state.settings = SimpleNamespace(mode="local_foundation")
    app.state.sql_workspace = workspace or Workspace(settings)
    install_clients(app)
    install_crm_configuration(app)
    install_inbox(app)

    @app.middleware("http")
    async def access(request: Request, call_next):
        allowed = (
            request.client
            and request.client.host in {"127.0.0.1", "::1"}
            and request.headers.get("host")
            in {"127.0.0.1:8003", "127.0.0.1:4176", "localhost:4176"}
            and request.headers.get("origin")
            in {None, "http://127.0.0.1:4176", "http://localhost:4176"}
        )
        if not allowed:
            return JSONResponse({"detail": "local_access_required"}, 403)
        if request.url.path.startswith("/api/"):
            if time.time() >= settings.ticket["expires_at"]:
                return JSONResponse({"detail": "preview_profile_expired"}, 403)
            if request.headers.get("x-crm-local") != "1":
                return JSONResponse({"detail": "local_access_required"}, 403)
            if request.url.path == "/api/local/session" and request.method == "POST":
                response = JSONResponse({"scope": "local_owner_preview"})
                response.set_cookie(
                    "cbn_c13_session",
                    settings.review["session_token"],
                    httponly=True,
                    samesite="strict",
                    max_age=28800,
                    path="/api",
                )
                response.headers["Cache-Control"] = "no-store"
                return response
            token = request.cookies.get("cbn_c13_session", "")
            if not hmac.compare_digest(
                token.encode(), settings.review["session_token"].encode()
            ):
                return JSONResponse({"detail": "local_session_required"}, 403)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(RequestValidationError)
    async def invalid(request, error):
        return JSONResponse({"detail": "invalid_request"}, 422)

    @app.get("/health/live")
    def live():
        return {"status": "alive", "scope": "general_preview"}

    @app.get("/api/local/runtime")
    def capabilities():
        return {
            "version": VERSION,
            "profile": "general_preview",
            "scope": "isolated_local_preview",
            "sections": [
                {
                    "path": p,
                    "label": label,
                    "phase": phase,
                    "available": ready,
                    "status": "local_subset" if ready else "pending_integration",
                }
                for p, label, phase, ready in SECTIONS
            ],
            "features": {
                "providers": False,
                "institutional_auth": False,
                "provider_workers": False,
                "public_webhooks": False,
            },
        }

    @app.get("/api/local/progress")
    def progress():
        value = json.loads(
            (
                Path(__file__).resolve().parents[3]
                / "docs/adaptation/phase-progress-contract.json"
            ).read_text(encoding="utf-8")
        )
        return {
            "measurement": value["measurement_label"],
            "phases": [
                {"id": p["id"], "title": p["title"], **p["completion"]}
                for p in value["phases"]
            ],
        }

    @app.get("/api/local/channels/{kind}")
    def channels(kind: str):
        if kind not in PROJECTIONS:
            raise HTTPException(404, "resource_not_found")
        table, pk, columns = PROJECTIONS[kind]
        with transaction(settings) as cursor:
            rows = cursor.execute(
                "SELECT TOP(100) "
                + ",".join(map(quote_name, columns))
                + " FROM crm_channels2."
                + quote_name(table)
                + " WHERE InstitutionId=? ORDER BY "
                + quote_name(pk),
                settings.ticket["context"][0][1],
            ).fetchall()
            stages = {}
            if kind == "integrations":
                document = cursor.execute(
                    (
                        "SELECT Document FROM crm_config.Configuration "
                        "WHERE ConfigurationId=1"
                    )
                ).fetchval()
                stages = {
                    stage["key"]: stage["label"]
                    for stage in json.loads(document)["stages"]
                }
            values = [result_row(columns, r) for r in rows]
            if kind == "integrations":
                for value in values:
                    value["InitialStageLabel"] = stages.get(value["InitialStageKey"])
        return {
            "items": values,
            "editing": False,
            "scope": "safe_local_read",
        }

    @app.api_route(
        "/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"]
    )
    def unavailable(path: str):
        raise HTTPException(503, "section_not_integrated")

    return app


def application():
    return create_app(load(Path(os.environ["CRM_GENERAL_PROFILE_DIR"])))
