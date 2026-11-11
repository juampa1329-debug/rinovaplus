"""Explicit local CRM definitions; never seed business defaults on reads."""

import hashlib
import math
import re
from datetime import date
from typing import Annotated, Literal
from urllib.parse import urlsplit
from uuid import UUID

import pyodbc
from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import Field, model_validator

from app.modules.catalog.domain.contracts import CatalogUnavailable
from app.schemas import LocalModel
from app.sql_workspace import Mutation
from app.sql_workspace_shape import SHAPE_SQL

Key = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,39}$")]
Label = Annotated[str, Field(min_length=1, max_length=60)]
FieldType = Literal[
    "Text", "Number", "List", "Date", "Boolean", "Email", "Phone", "URL"
]


class CrmDefinitionStage(LocalModel):
    key: Key
    label: Label
    probability: Annotated[int, Field(ge=0, le=100)] | None = None
    active: bool = True


class CrmDefinitionField(LocalModel):
    key: Key
    label: Label
    type: FieldType
    options: Annotated[
        list[Annotated[str, Field(min_length=1, max_length=80)]], Field(max_length=30)
    ] = []
    active: bool = True
    required: bool = False

    @model_validator(mode="after")
    def coherent(self):
        if self.key in {
            "constructor",
            "prototype",
            "summary",
            "intention",
            "behavior",
            "objections",
            "commitments",
            "next_action",
            "lead_score",
            "lead_temperature",
            "churn_risk",
            "ai_context",
        }:
            raise ValueError("Reserved derived or unsafe field")
        if self.type == "List" and not self.options:
            raise ValueError("List options required")
        if self.type != "List" and self.options:
            raise ValueError("Options only apply to lists")
        unique(self.options)
        return self


def unique(values):
    normalized = [v.strip().casefold() for v in values]
    if any(not v for v in normalized) or len(set(normalized)) != len(normalized):
        raise ValueError("Blank or duplicate definitions")


class Configuration(LocalModel):
    stages: Annotated[list[CrmDefinitionStage], Field(max_length=200)]
    tags: Annotated[
        list[Annotated[str, Field(min_length=1, max_length=1000)]],
        Field(max_length=500),
    ]
    inactiveTags: Annotated[list[str], Field(max_length=500)] = []
    fields: Annotated[list[CrmDefinitionField], Field(max_length=100)]

    @model_validator(mode="after")
    def coherent(self):
        unique([s.key for s in self.stages])
        unique([s.label for s in self.stages])
        unique(self.tags)
        unique(self.inactiveTags)
        unique([f.key for f in self.fields])
        if any("," in t or t != t.strip() for t in self.tags) or not set(
            self.inactiveTags
        ) <= set(self.tags):
            raise ValueError("Invalid tags")
        if any(v.label != v.label.strip() for v in [*self.stages, *self.fields]):
            raise ValueError("Untrimmed label")
        return self


class ConfigurationWrite(Mutation):
    config: Configuration


def read_configuration(cursor, *, foundation=False):
    if foundation:
        # Called only inside SqlWorkspace.transaction after full C3+C4 validation.
        row = cursor.execute(
            "SELECT Document,Revision FROM crm_config.Configuration "
            "WHERE ConfigurationId=1"
        ).fetchone()
        if row is None:
            raise HTTPException(503, "crm_configuration_unavailable")
        return Configuration.model_validate_json(row[0]), str(row[1])
    marker = cursor.execute(
        "SELECT CONVERT(nvarchar(80),value) FROM sys.extended_properties "
        "WHERE class=3 AND major_id=SCHEMA_ID(N'crm_config') AND "
        "name=N'crm_config.contract'"
    ).fetchone()
    if marker is None or marker[0] != "CRM-config-v1":
        raise HTTPException(503, "crm_configuration_unavailable")
    shape = cursor.execute(
        SHAPE_SQL.replace("N'crm'", "N'crm_config'").replace(
            "N'crm.shape'", "N'crm_config.shape'"
        )
    ).fetchone()
    if shape is None or not shape[0]:
        raise HTTPException(503, "crm_configuration_unavailable")
    row = cursor.execute(
        "SELECT Document,Revision FROM crm_config.Configuration WHERE ConfigurationId=1"
    ).fetchone()
    if row is None:
        raise HTTPException(503, "crm_configuration_unavailable")
    return Configuration.model_validate_json(row[0]), str(row[1])


def valid_value(field, value):
    if not value.strip():
        if value and field.type not in {"Text"}:
            return False
        return not field.required
    if field.type == "Text":
        return True
    if field.type == "Number":
        return bool(re.fullmatch(r"-?\d+(\.\d+)?", value)) and math.isfinite(
            float(value)
        )
    if field.type == "List":
        return value in field.options
    if field.type == "Boolean":
        return value in {"true", "false"}
    if field.type == "Date":
        try:
            return date.fromisoformat(value).isoformat() == value
        except ValueError:
            return False
    if field.type == "Email":
        return bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value))
    if field.type == "Phone":
        return (
            bool(re.fullmatch(r"\+?[\d ()-]{5,30}", value))
            and sum(c.isdigit() for c in value) >= 5
        )
    try:
        parsed = urlsplit(value)
        return (
            parsed.scheme in {"http", "https"}
            and bool(parsed.hostname)
            and not any(c.isspace() for c in value)
            and (parsed.port is None or 0 < parsed.port < 65536)
        )
    except ValueError:
        return False


def tags(value):
    return [v.strip() for v in value.split(",") if v.strip()]


def validate_contact(cursor, contact, previous=None, *, foundation=False):
    config, _ = (
        read_configuration(cursor, foundation=True)
        if foundation
        else read_configuration(cursor)
    )
    stage = next((s for s in config.stages if s.label == contact.stage), None)
    if (stage is None or not stage.active) and (
        previous is None or contact.stage != previous["stage"]
    ):
        raise HTTPException(422, "invalid_crm_stage")
    old_tags = set(tags(previous["tags"])) if previous else set()
    active_tags = set(config.tags) - set(config.inactiveTags)
    if not set(tags(contact.tags)) <= active_tags | old_tags:
        raise HTTPException(422, "invalid_crm_tags")
    old_values = previous["customValues"] if previous else {}
    fields = {f.key: f for f in config.fields}
    for key in set(old_values) | set(contact.customValues):
        field = fields.get(key)
        if (field is None or not field.active) and contact.customValues.get(
            key
        ) != old_values.get(key):
            raise HTTPException(422, "inactive_crm_value_changed")
    for field in config.fields:
        if field.active and not valid_value(
            field, contact.customValues.get(field.key, "")
        ):
            raise HTTPException(422, "invalid_crm_value")


class CrmConfiguration:
    def __init__(self, workspace):
        self.workspace = workspace

    def read(self):
        with self.workspace.transaction() as cursor:
            config, revision = (
                read_configuration(cursor, foundation=True)
                if getattr(self.workspace, "foundation", False)
                else read_configuration(cursor)
            )
            return {"config": config.model_dump(), "revision": revision}

    def save(self, body):
        digest = hashlib.sha256(body.config.model_dump_json().encode()).digest()
        operation_id = str(UUID(body.operationId))
        with self.workspace.transaction(write=True) as cursor:
            old, revision = (
                read_configuration(cursor, foundation=True)
                if getattr(self.workspace, "foundation", False)
                else read_configuration(cursor)
            )
            replay = cursor.execute(
                "SELECT PayloadHash,Revision FROM crm_config.Operation WHERE "
                "OperationId=?",
                operation_id,
            ).fetchone()
            if replay:
                if bytes(replay[0]) != digest:
                    raise HTTPException(409, "operation_id_reused")
                return {"config": old.model_dump(), "revision": revision}
            if revision != body.expectedRevision:
                raise HTTPException(409, "configuration_changed")
            new = body.config
            new_stages = {s.key: s for s in new.stages}
            new_fields = {f.key: f for f in new.fields}
            if (
                any(
                    s.key not in new_stages or new_stages[s.key].label != s.label
                    for s in old.stages
                )
                or not set(old.tags) <= set(new.tags)
                or any(f.key not in new_fields for f in old.fields)
            ):
                raise HTTPException(422, "deactivate_instead_of_removing")
            previous_fields = {f.key: f for f in old.fields}
            for field in new.fields:
                before = previous_fields.get(field.key)
                if before and (
                    before.type != field.type or before.options != field.options
                ):
                    used = cursor.execute(
                        "SELECT TOP (1) 1 FROM crm.Contact c CROSS APPLY "
                        "OPENJSON(c.CustomValues) j WHERE j.[key]=? AND j.[value]<>N''",
                        field.key,
                    ).fetchone()
                    if used:
                        raise HTTPException(422, "used_crm_field_shape_changed")
            next_revision = int(revision) + 1
            cursor.execute(
                "UPDATE crm_config.Configuration SET "
                "Document=?,Revision=?,UpdatedAt=SYSUTCDATETIME() WHERE "
                "ConfigurationId=1",
                new.model_dump_json(),
                next_revision,
            )
            cursor.execute(
                "INSERT crm_config.Operation(OperationId,PayloadHash,Revision) "
                "VALUES(?,?,?)",
                operation_id,
                digest,
                next_revision,
            )
            return {"config": new.model_dump(), "revision": str(next_revision)}


def install_crm_configuration(app: FastAPI):
    app.state.crm_configuration = CrmConfiguration(app.state.sql_workspace)
    router = APIRouter(
        prefix="/api/local/crm/configuration", tags=["local-crm-configuration"]
    )

    def call(request, method, *args):
        if request.app.state.settings.mode not in (
            "local_sql_copy",
            "local_foundation",
        ):
            raise HTTPException(503, "local_sql_copy_disabled")
        try:
            return JSONResponse(
                getattr(request.app.state.crm_configuration, method)(*args),
                headers={"Cache-Control": "no-store"},
            )
        except (pyodbc.Error, CatalogUnavailable):
            raise HTTPException(503, "local_sql_unavailable") from None

    @router.get("")
    def read(request: Request):
        return call(request, "read")

    @router.put("")
    def save(request: Request, body: ConfigurationWrite):
        return call(request, "save", body)

    app.include_router(router)
