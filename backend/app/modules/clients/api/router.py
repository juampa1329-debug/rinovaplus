"""HTTP composition for local client capabilities."""

from uuid import UUID

import pyodbc
from fastapi import APIRouter, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from app.modules.catalog.domain.contracts import CatalogUnavailable
from app.modules.clients.application.synthetic import install_local_clients
from app.sql_workspace import (
    ContactMutation,
    ConversationMutation,
    Identifier,
    MessageMutation,
    matches_client,
)


def install_clients(application: FastAPI) -> None:
    """Register exactly one local client transport for the selected local mode."""
    if application.state.settings.mode not in ("local_sql_copy", "local_foundation"):
        install_local_clients(application)

    router = APIRouter(prefix="/api/local/crm", tags=["local-sql-copy"])

    def run(request: Request, action=None, entity_id=None, body=None):
        if request.app.state.settings.mode not in (
            "local_sql_copy",
            "local_foundation",
        ):
            raise HTTPException(503, "local_sql_copy_disabled")
        try:
            store = request.app.state.sql_workspace
            return (
                store.read()
                if action is None
                else store.mutate(action, entity_id, body)
            )
        except (pyodbc.Error, CatalogUnavailable):
            raise HTTPException(503, "local_sql_unavailable") from None

    @router.get("")
    def workspace(request: Request):
        return JSONResponse(run(request), headers={"Cache-Control": "no-store"})

    @router.get("/clients")
    def clients(
        request: Request,
        q: str = Query("", max_length=200),
        stage: str = Query("", max_length=60),
        tag: str = Query("", max_length=1000),
        city: str = Query("", max_length=100),
        contactType: str = Query("", max_length=100),
        programId: int | None = Query(None, ge=-2147483648, le=2147483647),
        program: str = Query("", max_length=200),
    ):
        value = run(request)
        aliases = {
            row["sourceContactId"]: row["targetContactId"]
            for row in value["contactGroups"]
        }
        matches = {
            aliases.get(client["id"], client["id"])
            for client in value["clients"]
            if matches_client(
                client, q, stage, tag, city, contactType, programId, program
            )
        }
        value["clients"] = [
            client
            for client in value["clients"]
            if client["id"] not in aliases and client["id"] in matches
        ]
        return JSONResponse(value, headers={"Cache-Control": "no-store"})

    @router.get("/clients/{client_id}")
    def client(request: Request, client_id: Identifier):
        value = run(request)
        found = next(
            (item for item in value["clients"] if item["id"] == str(UUID(client_id))),
            None,
        )
        if found is None:
            raise HTTPException(404, "client_not_found")
        return JSONResponse(
            {"client": found, "revision": value["revision"]},
            headers={"Cache-Control": "no-store"},
        )

    @router.post("/clients", status_code=201)
    def create(request: Request, body: ContactMutation):
        return run(request, "create_contact", body.client.id, body)

    @router.put("/clients/{client_id}")
    def edit(request: Request, client_id: Identifier, body: ContactMutation):
        return run(request, "edit_contact", client_id, body)

    @router.put("/conversations/{conversation_id}")
    def update(
        request: Request, conversation_id: Identifier, body: ConversationMutation
    ):
        return run(request, "update_conversation", conversation_id, body)

    @router.post("/conversations/{conversation_id}/messages", status_code=201)
    def message(request: Request, conversation_id: Identifier, body: MessageMutation):
        return run(request, "add_message", conversation_id, body)

    application.include_router(router)
