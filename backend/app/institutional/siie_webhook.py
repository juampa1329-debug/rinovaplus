"""SIIE -> CRM ingress: signed minimal snapshots, no messages or enrollment claims."""

import hmac
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal
from uuid import UUID, uuid4, uuid5

from fastapi import HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from starlette.concurrency import run_in_threadpool

from app.institutional import siie_records as records
from app.institutional.channel_ingress import strict_json
from app.institutional.db import audit, bound_hash, institution, one
from app.institutional.store import transaction

HOOK_PATH = "/hooks/siie/v1"
MAX_BODY = 65536
LOG = logging.getLogger(__name__)
Positive = Annotated[int, Field(strict=True, ge=1, le=2147483647)]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)


class Person(Strict):
    nombres: Annotated[str, Field(min_length=1, max_length=100)]
    primerApellido: Annotated[str, Field(min_length=1, max_length=30)]
    segundoApellido: Annotated[str, Field(max_length=30)] = ""
    celular: Annotated[str, Field(pattern=r"^\+?[0-9 ()-]{7,23}$")]
    correo: Annotated[str, Field(max_length=50)] = ""
    ciudad: Annotated[str, Field(max_length=100)] = ""

    @field_validator("correo")
    @classmethod
    def email(cls, value):
        if value and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("invalid_email")
        return value


class Event(Strict):
    schema_version: Literal["siie-crm-event-v1"]
    event_id: Annotated[str, Field(max_length=36)]
    event_type: Literal[
        "pre_registration.created",
        "pre_registration.updated",
        "applicant.created",
        "registration.created",
        "registration.updated",
        "documents.updated",
    ]
    occurred_at: Annotated[str, Field(max_length=40)]
    sequence: Annotated[int, Field(strict=True, ge=1, le=9223372036854775807)]
    documento: Annotated[str, Field(pattern=r"^[A-Za-z0-9]{1,16}$")] | None = None
    idOferta: Positive
    idPeriodo: Positive
    idAspirante: Positive | None = None
    idPreinscripcion: Positive | None = None
    idEstudiante: Positive | None = None
    idInscripcion: Positive | None = None
    persona: Person | None = None
    programa: Annotated[str, Field(max_length=200)] = ""
    jornada: Annotated[str, Field(max_length=100)] = ""
    documentos: Annotated[list[Positive], Field(max_length=18)] = []

    @field_validator("event_id")
    @classmethod
    def event_uuid(cls, value):
        return str(UUID(value))

    @field_validator("occurred_at")
    @classmethod
    def event_time(cls, value):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed > datetime.now(timezone.utc).replace(
            microsecond=0
        ) + timedelta(minutes=5):
            raise ValueError("invalid_event_time")
        return parsed.astimezone(timezone.utc).isoformat()


def secret():
    value = os.getenv("SIIE_WEBHOOK_SECRET", "").strip()
    return (
        value
        if 32 <= len(value) <= 512
        and value.isascii()
        and not any(c.isspace() for c in value)
        else ""
    )


def verify(headers, raw, *, now=None):
    key = secret()
    if not key:
        LOG.warning("siie_webhook_rejected status=503 reason=secret_not_configured")
        raise HTTPException(
            503, "siie_webhook_not_configured", headers={"Retry-After": "300"}
        )
    timestamp, signature = (
        headers.get("x-siie-timestamp", ""),
        headers.get("x-siie-signature", ""),
    )
    if not re.fullmatch(r"[0-9]{10,11}", timestamp):
        LOG.warning("siie_webhook_rejected status=403 reason=timestamp_format")
        raise HTTPException(403, "siie_webhook_signature_rejected")
    if not re.fullmatch(r"sha256=[0-9a-f]{64}", signature):
        LOG.warning("siie_webhook_rejected status=403 reason=signature_format")
        raise HTTPException(403, "siie_webhook_signature_rejected")
    expected = (
        "sha256="
        + hmac.digest(
            key.encode(),
            b"rinovaplus-siie-v1." + timestamp.encode() + b"." + raw,
            "sha256",
        ).hex()
    )
    skew = (time.time() if now is None else now) - int(timestamp)
    signature_matches = hmac.compare_digest(signature, expected)
    if abs(skew) > 300 or not signature_matches:
        # Private operator diagnostics only. Never log request values, the key,
        # signature, payload or even its event/person identifiers.
        reason = (
            ("clock_skew" if signature_matches else "clock_skew_and_signature_mismatch")
            if abs(skew) > 300
            else "signature_mismatch"
        )
        LOG.warning(
            "siie_webhook_rejected status=403 reason=%s skew_seconds=%s",
            reason,
            round(skew),
        )
        raise HTTPException(403, "siie_webhook_signature_rejected")


def config(c, settings):
    row = one(
        c,
        "SELECT Document,Revision FROM crm_access.Setting WHERE InstitutionId=? AND Section='siie-registration'",
        institution(settings),
    )
    import json

    return (
        {"revision": row["Revision"], **json.loads(row["Document"])}
        if row
        else {
            "revision": 0,
            "webhook_enabled": False,
            "stage_key": "",
            "writes_enabled": False,
        }
    )


def phone(value):
    digits = re.sub(r"[^0-9]", "", value)
    return (
        "+57" + digits if len(digits) == 10 and digits.startswith("3") else "+" + digits
    )


def person_ref(settings, event):
    value = event.model_dump() if isinstance(event, Event) else event
    if value.get("idPreinscripcion"):
        reference = "siie-pre:" + str(value["idPreinscripcion"])
    elif value.get("documento"):
        reference = "siie-person:" + value["documento"].upper()
    else:
        raise HTTPException(422, "siie_webhook_invalid_event")
    return str(uuid5(UUID(institution(settings)), reference))


def project(c, settings, event, cfg):
    """A document-bound link is authority; a shared phone alone never is."""
    from app.modules.crm_configuration.application.service import (
        read_configuration,
        validate_contact,
    )
    from app.sql_workspace import Contact

    link_id = person_ref(settings, event)
    prior = records.get(c, settings, "sl", link_id)
    original_document = (
        prior["private"].get("snapshot", {}).get("documento") if prior else None
    )
    if (
        original_document
        and event.documento
        and original_document.upper() != event.documento.upper()
    ):
        raise HTTPException(409, "siie_webhook_person_conflict")
    from app.institutional.siie_classification import mark

    if prior and event.sequence <= prior["private"]["sequence"]:
        if event.event_type.startswith("registration.") and not prior["private"].get(
            "registered"
        ):
            # Delayed registration proof still closes promotions. It must not
            # replace a newer name, phone or program snapshot.
            for contact in (
                [prior["private"]["contact_id"]]
                if prior["private"].get("contact_id")
                else prior["private"].get("candidates", [])
            ):
                mark(c, settings, contact, True, event.event_id)
                if prior["private"].get("contact_id"):
                    c.execute(
                        "UPDATE crm.Contact SET Type='Inscrito' WHERE ContactId=?",
                        contact,
                    )
            records.put(
                c,
                settings,
                "sl",
                link_id,
                prior["metadata"],
                {**prior["private"], "registered": True},
                prior,
            )
            c.execute(
                "UPDATE crm_workspace.State SET Revision=Revision+1 WHERE StateId=1"
            )
        return {
            "projection": "stale_ignored",
            "contact_id": prior["private"].get("contact_id"),
        }
    linked = prior["private"].get("contact_id") if prior else None
    registered = event.event_type.startswith("registration.") or bool(
        prior and prior["private"].get("registered")
    )
    contact_id = linked
    state = "linked" if linked else "review_required"
    person = event.persona
    # Do not overwrite human edits in an existing CRM record on a webhook.
    candidates = []
    if not linked and person:
        crm, _ = read_configuration(c, foundation=True)
        stage = next(
            (s for s in crm.stages if s.key == cfg["stage_key"] and s.active), None
        )
        if not stage:
            raise HTTPException(409, "siie_webhook_stage_review_required")
        number = phone(person.celular)
        # Conservative candidates: contact/identity phone formatting variants.
        from app.institutional.db import rows

        candidates = rows(
            c,
            # PostgreSQL 16/17 cannot do substring replacement using the
            # imported nondeterministic ICU collation. Phone punctuation is
            # byte-exact; select the existing deterministic collation for this
            # expression only, without changing the column or identity rules.
            "SELECT TOP(21) ContactId,Phone FROM crm.Contact WHERE "
            "REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(Phone COLLATE Latin1_General_100_BIN2,"
            "'+',''),' ',''),'-',''),'(',''),')','') IN(?,?)",
            number[1:],
            number[3:] if number.startswith("+57") else number[1:],
        )
        if not candidates:
            contact_id = str(uuid4())
            active_fields = {f.key for f in crm.fields if f.active}
            source_values = {
                "correo_preinscripcion": person.correo,
                "pre_fecha": event.occurred_at[:10],
                "pre_ultima_fecha": event.occurred_at[:10],
                "pre_estado": "Inscrito según SIIE"
                if registered
                else "Preinscrito según SIIE",
                "pre_programas": event.programa,
                "pre_canal": "SIIE",
                "pre_origen": "SIIE · Webhook",
                "pre_import_ref": "SIIE-" + UUID(link_id).hex,
            }
            value = Contact(
                id=contact_id,
                name=" ".join(
                    filter(
                        None,
                        [person.nombres, person.primerApellido, person.segundoApellido],
                    )
                )[:100],
                phone=number,
                city=person.ciudad,
                programId=None,
                program="",
                schedule="",
                stage=stage.label,
                tags="",
                notes="",
                type="Inscrito" if registered else "Preinscrito",
                interests=event.programa,
                customValues={
                    k: v for k, v in source_values.items() if k in active_fields
                },
            )
            try:
                validate_contact(c, value, foundation=True)
            except HTTPException:
                # A required CRM custom field needs admission review, not retries.
                contact_id = None
            if contact_id:
                import json

                c.execute(
                    "INSERT crm.Contact(ContactId,Name,Phone,City,ProgramId,Program,Schedule,Stage,Tags,Notes,Type,Interests,CustomValues) VALUES(?,?,?,?,NULL,'','',?,'','',?,?,?)",
                    contact_id,
                    value.name,
                    value.phone,
                    value.city,
                    value.stage,
                    value.type,
                    value.interests,
                    json.dumps(value.customValues, ensure_ascii=False),
                )
                c.execute(
                    "INSERT crm.Conversation(ConversationId,ContactId,State,Priority,ControlMode,Unread) VALUES(?,?,'open','normal','human',0)",
                    str(uuid4()),
                    contact_id,
                )
                state = "created"
    if contact_id:
        mark(c, settings, contact_id, registered, event.event_id)
        if linked and registered:
            c.execute(
                "UPDATE crm.Contact SET Type='Inscrito' WHERE ContactId=?", contact_id
            )
    elif registered:
        # Ambiguous matching never merges people. Still stop promotional sends
        # to matching phones until admissions resolves the identity link.
        for candidate in candidates:
            mark(c, settings, candidate["ContactId"], True, event.event_id)
    snapshot = {
        **(prior["private"].get("snapshot", {}) if prior else {}),
        **event.model_dump(exclude_none=True, exclude_defaults=True),
    }
    content = {
        "sequence": event.sequence,
        "registered": registered,
        "contact_id": contact_id,
        "snapshot": snapshot,
        "candidates": [str(v["ContactId"]) for v in candidates],
    }
    records.put(c, settings, "sl", link_id, {"state": state}, content, prior)
    if contact_id or registered and candidates:
        c.execute("UPDATE crm_workspace.State SET Revision=Revision+1 WHERE StateId=1")
    return {"projection": state, "contact_id": contact_id}


class Ingress:
    def __init__(self, settings):
        self.settings = settings

    def receive(self, headers, raw):
        verify(headers, raw)
        try:
            return self.receive_verified(raw)
        except HTTPException as error:
            # Verification succeeded before storage/configuration was consulted.
            # Fixed codes only: never log body, document, key, signature or IDs.
            if error.status_code == 503:
                reason = str(error.detail) if error.detail in {
                    "storage_busy", "general_storage_unavailable", "siie_webhook_disabled"
                } else "unavailable"
                LOG.warning("siie_webhook_rejected status=503 reason=%s signature_verified=true", reason)
            raise

    def receive_verified(self, raw):
        try:
            event = Event.model_validate(strict_json(raw))
            if event.event_type.startswith("pre_registration.") and (
                not event.idPreinscripcion or event.persona is None
            ):
                raise ValueError("pre_registration_reference_required")
            if event.event_type == "applicant.created" and (
                not event.idAspirante or event.persona is None or not event.documento
            ):
                raise ValueError("applicant_reference_required")
            if event.event_type.startswith("registration.") and (
                not event.idEstudiante
                or not event.idInscripcion
                or event.persona is None
                or not event.documento
            ):
                raise ValueError("registration_reference_required")
            if event.event_type == "documents.updated" and (
                not event.idEstudiante or not event.documento
            ):
                raise ValueError("student_reference_required")
        except (ValidationError, ValueError, TypeError, UnicodeError, RecursionError):
            raise HTTPException(422, "siie_webhook_invalid_event") from None
        # Compare semantic JSON, not signature timestamp/whitespace on a retry.
        digest = bound_hash(
            self.settings, event.model_dump(), "siie_webhook_event"
        ).hex()
        with transaction(self.settings, True, anonymous=True) as c:
            cfg = config(c, self.settings)
            if not cfg["webhook_enabled"]:
                raise HTTPException(
                    503, "siie_webhook_disabled", headers={"Retry-After": "300"}
                )
            previous = records.get(c, self.settings, "se", event.event_id)
            if previous:
                if not hmac.compare_digest(digest, previous["private"]["digest"]):
                    raise HTTPException(409, "siie_webhook_event_conflict")
                return {
                    "received": True,
                    "duplicate": True,
                    "event_id": event.event_id,
                    "projection": previous["metadata"]["projection"],
                }
            result = project(c, self.settings, event, cfg)
            records.put(
                c,
                self.settings,
                "se",
                event.event_id,
                {"event_type": event.event_type, "projection": result["projection"]},
                {"digest": digest, "event": event.model_dump(), **result},
            )
            audit(
                c,
                self.settings,
                None,
                "siie.webhook.received",
                event.event_id,
                count=1,
                kind=event.event_type,
            )
        # Acknowledge only AFTER the transaction successfully commits.
        return {
            "received": True,
            "duplicate": False,
            "event_id": event.event_id,
            "projection": result["projection"],
        }


def install(app, settings):
    service = Ingress(settings)

    @app.post(HOOK_PATH, include_in_schema=False)
    async def receive(request: Request):
        if request.url.query or any(
            len(request.headers.getlist(k)) != 1
            for k in ("x-siie-timestamp", "x-siie-signature")
        ):
            raise HTTPException(403, "siie_webhook_signature_rejected")
        if (
            request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
            != "application/json"
        ):
            raise HTTPException(415, "siie_webhook_json_required")
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > MAX_BODY:
                raise HTTPException(413, "siie_webhook_too_large")
        return await run_in_threadpool(service.receive, request.headers, bytes(raw))
