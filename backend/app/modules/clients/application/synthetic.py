"""Synthetic client exercises in process memory; never a business datastore."""

import json
from pathlib import Path
from threading import RLock
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, FastAPI, HTTPException, Query, Response
from pydantic import Field, model_validator

from app.schemas import LocalModel

ClientId = Annotated[str, Field(pattern=r"^demo-[a-zA-Z0-9-]{1,64}$")]
ShortText = Annotated[str, Field(max_length=100)]


class SyntheticClient(LocalModel):
    id: ClientId
    name: ShortText
    phone: Annotated[str, Field(max_length=40)]
    city: ShortText
    program: Annotated[str, Field(min_length=1, max_length=200)]
    schedule: ShortText
    stage: Annotated[str, Field(min_length=1, max_length=60)]
    tags: Annotated[str, Field(max_length=1000)]
    notes: Annotated[str, Field(max_length=1000)]
    type: ShortText
    interests: Annotated[str, Field(max_length=300)]
    customValues: Annotated[
        dict[
            Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,39}$")],
            Annotated[str, Field(max_length=500)],
        ],
        Field(max_length=100),
    ]

    @model_validator(mode="after")
    def named_synthetic_record(self):
        self.name = self.name.strip()
        self.phone = self.phone.strip()
        if not self.name and not self.phone:
            raise ValueError("A name or synthetic identifier is required")
        if {"constructor", "prototype"} & self.customValues.keys():
            raise ValueError("Invalid custom field key")
        return self


class SyntheticClientSnapshot(LocalModel):
    clients: list[SyntheticClient]
    revision: str


class SyntheticClientMutation(LocalModel):
    client: SyntheticClient
    revision: Annotated[str, Field(min_length=1, max_length=64)]


class SyntheticClientReset(LocalModel):
    revision: Annotated[str, Field(min_length=1, max_length=64)]


class SyntheticClientResult(LocalModel):
    client: SyntheticClient
    revision: str


class LocalClients:
    def __init__(self):
        # One local process only; restart restores these public synthetic fixtures.
        self.lock = RLock()
        self.restore()

    def restore(self):
        values = json.loads(
            (Path(__file__).parents[3] / "client_fixtures.json").read_text(
                encoding="utf-8"
            )
        )
        self.clients = {
            value["id"]: SyntheticClient.model_validate(value) for value in values
        }
        self.revision = str(uuid4())

    def snapshot(self, query="", stage="", tag=""):
        query, tag = query.strip().lower(), tag.strip().lower()
        return SyntheticClientSnapshot(
            clients=[
                client.model_copy(deep=True)
                for client in self.clients.values()
                if (not stage or client.stage == stage)
                and (
                    not tag
                    or tag
                    in [value.strip().lower() for value in client.tags.split(",")]
                )
                and query
                in " ".join(
                    (
                        client.name,
                        client.phone,
                        client.city,
                        client.program,
                        client.tags,
                    )
                ).lower()
            ],
            revision=self.revision,
        )

    def current(self, revision):
        if revision != self.revision:
            raise HTTPException(409, detail="clients_changed")


def install_local_clients(application: FastAPI):
    store = LocalClients()
    application.state.local_clients = store
    router = APIRouter(prefix="/api/local/clients", tags=["synthetic-clients"])

    @router.get("", response_model=SyntheticClientSnapshot)
    def list_clients(
        response: Response,
        q: str = Query(default="", max_length=200),
        stage: str = Query(default="", max_length=60),
        tag: str = Query(default="", max_length=1000),
    ):
        response.headers["Cache-Control"] = "no-store"
        with store.lock:
            return store.snapshot(q, stage, tag)

    @router.post("/reset", response_model=SyntheticClientSnapshot)
    def reset_clients(body: SyntheticClientReset):
        with store.lock:
            store.current(body.revision)
            store.restore()
            return store.snapshot()

    @router.get("/{client_id}", response_model=SyntheticClientResult)
    def read_client(client_id: ClientId, response: Response):
        response.headers["Cache-Control"] = "no-store"
        with store.lock:
            client = store.clients.get(client_id)
            if client is None:
                raise HTTPException(404, detail="client_not_found")
            return SyntheticClientResult(
                client=client.model_copy(deep=True), revision=store.revision
            )

    @router.post("", response_model=SyntheticClientResult, status_code=201)
    def create_client(body: SyntheticClientMutation, response: Response):
        with store.lock:
            previous = store.clients.get(body.client.id)
            if previous is not None:
                # The same draft ID makes an uncertain create safe to retry.
                if previous == body.client:
                    response.status_code = 200
                    return SyntheticClientResult(
                        client=previous.model_copy(deep=True), revision=store.revision
                    )
                raise HTTPException(409, detail="client_id_exists")
            store.current(body.revision)
            if len(store.clients) >= 500:
                raise HTTPException(409, detail="clients_limit_reached")
            store.clients[body.client.id] = body.client.model_copy(deep=True)
            store.revision = str(uuid4())
            return SyntheticClientResult(client=body.client, revision=store.revision)

    @router.put("/{client_id}", response_model=SyntheticClientResult)
    def update_client(client_id: ClientId, body: SyntheticClientMutation):
        with store.lock:
            if client_id not in store.clients:
                raise HTTPException(404, detail="client_not_found")
            if body.client.id != client_id:
                raise HTTPException(422, detail="client_id_mismatch")
            store.current(body.revision)
            store.clients[client_id] = body.client.model_copy(deep=True)
            store.revision = str(uuid4())
            return SyntheticClientResult(client=body.client, revision=store.revision)

    application.include_router(router)
