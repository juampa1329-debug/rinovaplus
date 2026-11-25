"""Reviewed prospect import. Existing CRM tables only; no messages or consent IO."""

import hashlib
import json
import re
import unicodedata
from datetime import date
from types import SimpleNamespace
from uuid import NAMESPACE_URL, uuid4, uuid5

from fastapi import HTTPException, Request
from pydantic import Field, model_validator

from app.institutional import db
from app.institutional.auth import authorize
from app.institutional.models import Strict
from app.institutional.policy import request_authority
from app.institutional.store import transaction
from app.institutional.workspace import revision
from app.modules.crm_configuration.application.service import (
    Configuration,
    CrmDefinitionField,
    read_configuration,
)
from app.sql_workspace import Contact, Identifier

FIELDS = [
    ("correo_preinscripcion", "Correo de preinscripción", "Email"),
    ("pre_fecha", "Fecha de primera preinscripción", "Date"),
    ("pre_ultima_fecha", "Fecha de última preinscripción", "Date"),
    ("pre_ultima_gestion", "Última gestión registrada en origen", "Date"),
    ("pre_asesor", "Último asesor registrado en origen", "Text"),
    ("pre_estado", "Estado original de preinscripción", "Text"),
    ("pre_programas", "Programas de interés en origen", "Text"),
    ("pre_canal", "Canal de preinscripción", "Text"),
    ("pre_origen", "Archivos de preinscripción", "Text"),
    ("pre_import_ref", "Referencia de importación", "Text"),
    ("pre_import_hash", "Huella de los datos importados", "Text"),
]
STAGES = {
    "Pendiente de calificación": "Calificación",
    "En negociación": "Seguimiento",
    "Intento sin respuesta": "Seguimiento",
    "Negociación no aceptada": "Cerrado sin matrícula",
    "Inscrito según origen": "Inscripción",
}


def normalize(value):
    value = unicodedata.normalize("NFKD", value.strip()).casefold()
    return " ".join("".join(c for c in value if not unicodedata.combining(c)).split())


def phone(value):
    if not re.fullmatch(r"[+\d ()-]+", value.strip()):
        return ""
    digits = re.sub(r"\D", "", value)
    if re.fullmatch(r"3\d{9}", digits):
        digits = "57" + digits
    return "+" + digits if re.fullmatch(r"573\d{9}", digits) else ""


class Entry(Strict):
    ref: str = Field(pattern=r"^PRE-[a-f0-9]{16}$")
    name: str = Field(min_length=1, max_length=100)
    phone: str = Field(max_length=40)
    email: str = Field(default="", max_length=254)
    programs: list[str] = Field(min_length=1, max_length=30)
    stages: list[str] = Field(min_length=1, max_length=30)
    first_date: str = Field(default="", pattern=r"^(?:\d{4}-\d{2}-\d{2})?$")
    last_date: str = Field(default="", pattern=r"^(?:\d{4}-\d{2}-\d{2})?$")
    management_date: str = Field(default="", max_length=10)
    advisor: str = Field(default="", max_length=200)
    channels: str = Field(max_length=500)
    source_files: str = Field(max_length=500)
    review: list[str] = Field(default_factory=list, max_length=30)
    notes: list[str] = Field(min_length=1, max_length=40)

    @model_validator(mode="after")
    def bounded(self):
        for value in [self.first_date, self.last_date, self.management_date]:
            if value and date.fromisoformat(value).isoformat() != value:
                raise ValueError("invalid_source_date")
        for value in [*self.programs, *self.stages, *self.review]:
            if not value.strip() or len(value) > 500 or "\x00" in value:
                raise ValueError("invalid_source_value")
        if any(not n.strip() or len(n.encode("utf-16-le")) > 4000 for n in self.notes):
            raise ValueError("source_note_exceeds_limit")
        if self.email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", self.email):
            raise ValueError("invalid_source_email")
        return self


class Batch(Strict):
    operation_id: Identifier
    batch_id: Identifier
    entries: list[Entry] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def distinct(self):
        if len({e.ref for e in self.entries}) != len(self.entries):
            raise ValueError("duplicate_import_reference")
        return self


class Prepare(Strict):
    operation_id: Identifier


def snapshot(c):
    values = db.rows(
        c, "SELECT TOP (20001) ContactId,Name,Phone,CustomValues FROM crm.Contact"
    )
    if len(values) > 20000:
        raise HTTPException(409, "prospect_import_scope_limit")
    for row in values:
        row["custom"] = json.loads(row["CustomValues"])
    return values


def entry_hash(entry):
    return hashlib.sha256(entry.model_dump_json().encode()).hexdigest()


def decision(entry, existing):
    if entry.review:
        return "review", " | ".join(entry.review)
    if not any(c.isalpha() for c in entry.name) or not phone(entry.phone):
        return "review", "Nombre o celular pendiente de revisión"
    if any(s not in STAGES for s in entry.stages) or len(set(entry.stages)) != 1:
        return "review", "Etapas distintas o sin equivalencia segura"
    if len(" | ".join(entry.programs)) > 500:
        return "review", "Varios programas: revisar la ficha principal"
    for row in existing:
        if row["custom"].get("pre_import_ref") == entry.ref:
            if row["custom"].get("pre_import_hash") == entry_hash(entry):
                return "imported", "Importación ya registrada; no se repite"
            return "review", "Referencia importada con otros datos; no se sobrescribe"
    for row in existing:
        same_phone = phone(row["Phone"]) == phone(entry.phone)
        emails = [
            v.casefold()
            for k, v in row["custom"].items()
            if isinstance(v, str) and ("correo" in k or "email" in k)
        ]
        same_email = bool(entry.email and entry.email.casefold() in emails)
        if same_phone or same_email or normalize(row["Name"]) == normalize(entry.name):
            return "review", "Posible contacto existente en CRM; conservar y revisar"
    return "ready", "Datos claros para crear un contacto nuevo"


def custom_values(entry):
    return {
        "correo_preinscripcion": entry.email,
        "pre_fecha": entry.first_date,
        "pre_ultima_fecha": entry.last_date,
        "pre_ultima_gestion": entry.management_date,
        "pre_asesor": entry.advisor,
        "pre_estado": " | ".join(entry.stages),
        "pre_programas": " | ".join(entry.programs),
        "pre_canal": entry.channels,
        "pre_origen": entry.source_files,
        "pre_import_ref": entry.ref,
        "pre_import_hash": entry_hash(entry),
    }


def prepare(profile, body):
    with transaction(profile, True, permission="settings.crm.write") as c:
        actor = authorize(c, profile, request_authority.get(), "settings.crm.write")
        actor_id = db.uid(str(actor["UserId"]))
        digest, prior = db.replay(
            c,
            profile,
            actor_id,
            body.operation_id,
            "prospect.fields",
            "crm",
            body.model_dump(),
        )
        if prior is not None:
            return prior
        config, current_revision = read_configuration(c, foundation=True)
        fields = {f.key: f for f in config.fields}
        added = []
        for key, label, kind in FIELDS:
            if key in fields:
                if fields[key].type != kind or not fields[key].active:
                    raise HTTPException(409, "prospect_import_field_conflict")
                continue
            config.fields.append(
                CrmDefinitionField.model_validate({
                    "key": key,
                    "label": label,
                    "type": kind,
                    "active": True,
                    "required": False,
                    "options": [],
                })
            )
            added.append(key)
        config = Configuration.model_validate(config.model_dump())
        if added:
            c.execute(
                "UPDATE crm_config.Configuration SET Document=?,Revision=?,"
                "UpdatedAt=SYSUTCDATETIME() WHERE ConfigurationId=1",
                config.model_dump_json(),
                int(current_revision) + 1,
            )
        result = {"added": added, "available": [f[0] for f in FIELDS]}
        db.record_operation(
            c,
            profile,
            actor_id,
            body.operation_id,
            "prospect.fields",
            "crm",
            digest,
            result,
        )
        db.audit(c, profile, actor_id, "prospect.fields", count=len(added))
        return result


def process(profile, workspace, body, commit=False):
    with transaction(profile, commit, permission="crm.write") as c:
        actor = authorize(c, profile, request_authority.get(), "crm.write")
        actor_id = db.uid(str(actor["UserId"]))
        if commit:
            digest, prior = db.replay(
                c,
                profile,
                actor_id,
                body.operation_id,
                "prospect.import",
                body.batch_id,
                body.model_dump(),
            )
            if prior is not None:
                return prior
        existing = snapshot(c)
        results = []
        for entry in body.entries:
            state, reason = decision(entry, existing)
            contact_id = str(
                uuid5(NAMESPACE_URL, db.institution(profile) + ":" + entry.ref)
            )
            if commit and state == "ready":
                # Program names are source declarations, never academic bindings.
                contact = Contact(
                    id=contact_id,
                    name=entry.name,
                    phone=phone(entry.phone),
                    city="",
                    programId=None,
                    program="",
                    schedule="",
                    stage=STAGES[entry.stages[0]],
                    tags="",
                    notes="Preinscripción importada. Ver notas de origen. "
                    "Gestión registrada no equivale a contacto verificado. "
                    "Autorización de campañas no activada por esta importación; "
                    "consultar la evidencia de origen antes de cualquier envío.",
                    type="Preinscrito",
                    interests=" | ".join(entry.programs)
                    if len(" | ".join(entry.programs)) <= 300
                    else "Varios intereses; consultar programas y notas de origen",
                    customValues=custom_values(entry),
                )
                result = workspace.apply(
                    c, "create", contact_id, SimpleNamespace(client=contact), actor_id
                )
                c.execute(
                    "UPDATE crm.Conversation SET ControlMode='human' "
                    "WHERE ConversationId=?",
                    result["conversationId"],
                )
                for note in entry.notes:
                    c.execute(
                        "INSERT crm_workspace.Note(NoteId,ContactId,InstitutionId,"
                        "AuthorId,Body) VALUES(?,?,?,?,?)",
                        str(uuid4()),
                        contact_id,
                        db.institution(profile),
                        actor_id,
                        note,
                    )
                existing.append(
                    {
                        "Name": entry.name,
                        "Phone": entry.phone,
                        "custom": contact.customValues,
                    }
                )
                state, reason = (
                    "imported",
                    "Contacto creado sin mensajes ni consentimiento",
                )
            results.append(
                {
                    "ref": entry.ref,
                    "state": state,
                    "reason": reason,
                    "contact_id": contact_id if state == "imported" else None,
                }
            )
        result = {"items": results, "messages_created": 0, "consents_granted": 0}
        if commit:
            c.execute(
                "UPDATE crm_workspace.State SET Revision=Revision+1 WHERE StateId=1"
            )
            result["revision"] = revision(c)
            db.record_operation(
                c,
                profile,
                actor_id,
                body.operation_id,
                "prospect.import",
                body.batch_id,
                digest,
                result,
            )
            db.audit(
                c,
                profile,
                actor_id,
                "prospect.import",
                body.batch_id,
                count=sum(r["state"] == "imported" for r in results),
            )
        return result


def install(app, profile, workspace):
    prefix = "/api/institution/workspace/prospect-import"

    @app.post(prefix + "/fields")
    def fields(request: Request, body: Prepare):
        # Configuration changes require their own permission as well as CSRF.
        return prepare(profile, body)

    @app.post(prefix + "/preview")
    def preview(request: Request, body: Batch):
        return process(profile, workspace, body)

    @app.post(prefix + "/commit")
    def commit(request: Request, body: Batch):
        return process(profile, workspace, body, commit=True)
