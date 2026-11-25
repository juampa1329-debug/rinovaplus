"""Reviewed registration commands; durable intent precedes every SIIE write."""

import hashlib
import re
from typing import Annotated, Literal

from fastapi import HTTPException, Request
from pydantic import Field
from starlette.concurrency import run_in_threadpool

from app.institutional import siie_forms as forms
from app.institutional import siie_records as records
from app.institutional import siie_registration_client as source
from app.institutional.auth import authorize, rate
from app.institutional.channel_ingress import strict_json
from app.institutional.crypto import canonical
from app.institutional.db import audit, bound_hash, institution, uid
from app.institutional.models import Strict
from app.institutional.policy import request_authority
from app.institutional.siie_webhook import HOOK_PATH, config, person_ref, secret
from app.institutional.store import transaction

PREFIX = "/api/institution/siie-registration"


class Draft(Strict):
    operation_id: str
    revision: Annotated[int, Field(ge=0)]
    kind: Literal["applicant", "registration"]
    selection: dict
    form: dict


class Command(Strict):
    operation_id: str
    revision: Annotated[int, Field(ge=1)]
    reviewed: bool


class Configuration(Strict):
    revision: Annotated[int, Field(ge=0)]
    webhook_enabled: bool
    writes_enabled: bool
    stage_key: Annotated[str, Field(max_length=40)]


class Link(Strict):
    contact_id: str
    reviewed: bool


def own(c, settings, identity):
    value = records.get(c, settings, "sd", identity)
    if not value:
        raise HTTPException(404, "siie_draft_not_found")
    return value


def catalogs(context=None):
    result = {}
    try:
        result["tiposDocumento"] = source.document_types()
    except HTTPException:
        result["tiposDocumento"] = []
    if context and context.get("shift_id"):
        result["jornadas"] = [
            {
                "value": int(source.siie_api.positive(context["shift_id"])),
                "label": context.get("schedule") or "Jornada de la oferta",
            }
        ]
    return {
        "items": result,
        "missing": [name for name in forms.CATALOGS if not result.get(name)],
    }


class Registration:
    def __init__(self, settings):
        self.settings = settings

    def tx(self, write=False):
        return transaction(self.settings, write)

    def read(self, kind, identity=None, offset=0):
        with self.tx() as c:
            if identity is None:
                return records.recent(c, self.settings, kind, offset=offset)
            row = records.get(c, self.settings, kind, uid(identity))
            if not row:
                raise HTTPException(404, "siie_draft_not_found")
            private = row["private"]
            # Internal request hashes/actor identities are not UI fields.
            result = {
                "id": uid(identity),
                "revision": row["revision"],
                **row["metadata"],
                **{
                    k: v
                    for k, v in private.items()
                    if k
                    in {
                        "form",
                        "context",
                        "result",
                        "last_result",
                        "event",
                        "contact_id",
                        "pending_operation",
                    }
                },
            }
            if kind == "se" and private.get("event"):
                from app.institutional.db import rows

                link_id = person_ref(self.settings, private["event"])
                link = records.get(c, self.settings, "sl", link_id)
                ids = link["private"].get("candidates", []) if link else []
                result["candidates"] = (
                    rows(
                        c,
                        "SELECT ContactId AS id,Name AS name,Phone AS phone FROM crm.Contact WHERE ContactId IN("
                        + ",".join("?" for _ in ids)
                        + ")",
                        *ids,
                    )
                    if ids
                    else []
                )
            return result

    def link(self, identity, body):
        from app.institutional.db import one
        from app.institutional.siie_classification import mark

        identity, contact_id = uid(identity), uid(body.contact_id)
        if not body.reviewed:
            raise HTTPException(422, "siie_review_required")
        with self.tx(True) as c:
            actor = authorize(c, self.settings, request_authority.get(), "crm.write")
            receipt = records.get(c, self.settings, "se", identity)
            if not receipt:
                raise HTTPException(404, "siie_draft_not_found")
            event = receipt["private"]["event"]
            link_id = person_ref(self.settings, event)
            link = records.get(c, self.settings, "sl", link_id)
            private = link["private"] if link else {}
            if private.get("contact_id") == contact_id:
                return {"linked": True, "contact_id": contact_id}
            if private.get("contact_id") or contact_id not in private.get(
                "candidates", []
            ):
                raise HTTPException(409, "siie_contact_link_changed")
            person = one(
                c, "SELECT Phone FROM crm.Contact WHERE ContactId=?", contact_id
            )
            from app.institutional.prospect_import import phone

            source_phone = (
                private.get("snapshot", {}).get("persona", {}).get("celular", "")
            )
            if (
                not person
                or not phone(person["Phone"])
                or phone(person["Phone"]) != phone(source_phone)
            ):
                raise HTTPException(409, "siie_contact_link_changed")
            records.put(
                c,
                self.settings,
                "sl",
                link_id,
                {"state": "linked"},
                {**private, "contact_id": contact_id},
                link,
            )
            mark(
                c, self.settings, contact_id, private.get("registered", False), identity
            )
            if private.get("registered"):
                c.execute(
                    "UPDATE crm.Contact SET Type='Inscrito' WHERE ContactId=?",
                    contact_id,
                )
            records.put(
                c,
                self.settings,
                "se",
                identity,
                {**receipt["metadata"], "projection": "linked"},
                {
                    **receipt["private"],
                    "contact_id": contact_id,
                    "projection": "linked",
                },
                receipt,
            )
            c.execute(
                "UPDATE crm_workspace.State SET Revision=Revision+1 WHERE StateId=1"
            )
            audit(c, self.settings, actor["UserId"], "siie.contact.linked", identity)
        return {"linked": True, "contact_id": contact_id}

    def save(self, identity, body):
        identity = uid(identity)
        uid(body.operation_id)
        if len(canonical(body.form)) > 262144:
            raise HTTPException(413, "siie_form_too_large")
        forms.validate(body.kind, body.form)
        allowed = {"program_id", "program_cursor", "offer_cursor", "offer_ref"}
        if (
            set(body.selection) - allowed
            or not {"program_id", "offer_ref"} <= body.selection.keys()
        ):
            raise HTTPException(422, "siie_offer_selection_invalid")
        # Authorization before IO; no remote IO while holding the SQL lock.
        with self.tx():
            pass
        context = source.offer_context(body.selection)
        with self.tx(True) as c:
            old = records.get(c, self.settings, "sd", identity)
            if (old["revision"] if old else 0) != body.revision:
                raise HTTPException(409, "revision_conflict")
            if old and old["metadata"]["state"] not in {"draft", "rejected"}:
                raise HTTPException(409, "siie_registration_reconciliation_required")
            actor = authorize(c, self.settings, request_authority.get(), "crm.write")
            revision = records.put(
                c,
                self.settings,
                "sd",
                identity,
                {
                    "kind": body.kind,
                    "state": "draft",
                    "program_name": context["program_name"],
                },
                {
                    "form": body.form,
                    "context": context,
                    "actor_id": str(actor["UserId"]),
                },
                old,
            )
            audit(c, self.settings, actor["UserId"], "siie.draft.saved", identity)
        return {"id": identity, "revision": revision, "state": "draft"}

    def requirements(self, identity):
        with self.tx() as c:
            row = own(c, self.settings, uid(identity))
            ctx = row["private"]["context"]
            payload = {k: ctx[k] for k in ("idOferta", "idPeriodo")}
            confirmed = row["private"].get("result", {})
            if confirmed.get("state") == "confirmed" and confirmed.get("data", {}).get(
                "idEstudiante"
            ):
                payload["idEstudiante"] = confirmed["data"]["idEstudiante"]
        result = source.request("requirements", payload)
        with self.tx():
            pass
        return result

    def submit(self, identity, command, files=(), *, documents=False):
        identity, operation = uid(identity), uid(command.operation_id)
        if not command.reviewed:
            raise HTTPException(422, "siie_review_required")
        source.files_for(files)  # Magic, duplicate types and limits before intent.
        request_hash = bound_hash(
            self.settings,
            {
                "draft_id": identity,
                "revision": command.revision,
                "documents": documents,
                "files": [
                    {"id": v[0], "sha256": hashlib.sha256(v[2]).hexdigest()}
                    for v in files
                ],
            },
            "siie_write_command",
        ).hex()
        with self.tx() as c:
            old = own(c, self.settings, identity)
            prior = records.get(c, self.settings, "sw", operation)
            if prior:
                if prior["private"].get("request_hash") != request_hash:
                    raise HTTPException(409, "operation_conflict")
                return {
                    "operation_id": operation,
                    **prior["private"]["result"],
                    "repeated": True,
                }
            if old["revision"] != command.revision:
                raise HTTPException(409, "revision_conflict")
            cfg = config(c, self.settings)
            if not cfg["writes_enabled"]:
                raise HTTPException(409, "siie_registration_writes_disabled")
            private = old["private"]
        context = source.offer_context(private["context"]["selection"])
        if context != private["context"]:
            raise HTTPException(409, "siie_offer_selection_changed")
        kind = "documents" if documents else old["metadata"]["kind"]
        payload = {k: context[k] for k in ("idOferta", "idPeriodo")}
        if documents:
            result = private.get("result", {})
            if (
                result.get("state") != "confirmed"
                or not result.get("data", {}).get("idEstudiante")
                or not files
            ):
                raise HTTPException(409, "siie_confirmed_registration_required")
            payload["idEstudiante"] = result["data"]["idEstudiante"]
        else:
            choices = catalogs(context)
            forms.validate(
                kind,
                private["form"],
                final=True,
                catalogs=choices["items"],
                program_name=context["program_name"],
            )
            payload.update(private["form"])
        if kind in {"documents", "registration"}:
            requirements = self.requirements(identity)["data"]["items"]
            supplied = {v[0] for v in files}
            for item in requirements:
                document = item.get("idDocumento")
                if document in supplied and (
                    item.get("soportado") is not True
                    or item.get("aplica") is False
                    or item.get("recibido") is True
                ):
                    raise HTTPException(409, "siie_document_review_required")
            known = {v.get("idDocumento") for v in requirements}
            required = {
                v.get("idDocumento")
                for v in requirements
                if v.get("obligatorioAlInscribir") is True
            }
            if supplied - known or kind == "registration" and required - supplied:
                raise HTTPException(422, "siie_initial_documents_required")
        digest = bound_hash(
            self.settings,
            {
                "draft": identity,
                "kind": kind,
                "payload": payload,
                "files": [
                    {"id": v[0], "sha256": hashlib.sha256(v[2]).hexdigest()}
                    for v in files
                ],
            },
            "siie_write",
        ).hex()
        with self.tx(True) as c:
            current = own(c, self.settings, identity)
            actor = authorize(c, self.settings, request_authority.get(), "crm.write")
            prior = records.get(c, self.settings, "sw", operation)
            if prior:
                if prior["private"].get("digest") != digest:
                    raise HTTPException(409, "operation_conflict")
                return {
                    "operation_id": operation,
                    **prior["private"]["result"],
                    "repeated": True,
                }
            if current["revision"] != command.revision:
                raise HTTPException(409, "revision_conflict")
            expected_state = "confirmed" if documents else {"draft", "rejected"}
            if (
                current["metadata"]["state"] != expected_state
                if documents
                else current["metadata"]["state"] not in expected_state
            ):
                raise HTTPException(409, "siie_registration_reconciliation_required")
            if not config(c, self.settings)["writes_enabled"]:
                raise HTTPException(409, "siie_registration_writes_disabled")
            if not rate(c, self.settings, "siie-registration-write", 30, 60):
                raise HTTPException(
                    429, "siie_registration_rate_limited", headers={"Retry-After": "60"}
                )
            pending = {
                "state": "pending_review",
                "data": {},
                "code": "siie_write_pending",
            }
            records.put(
                c,
                self.settings,
                "sw",
                operation,
                {"state": "pending_review", "kind": kind},
                {
                    "draft_id": identity,
                    "digest": digest,
                    "request_hash": request_hash,
                    "result": pending,
                },
            )
            private = {**current["private"], "pending_operation": operation}
            records.put(
                c,
                self.settings,
                "sd",
                identity,
                {**current["metadata"], "state": "pending_review"},
                private,
                current,
            )
            audit(
                c,
                self.settings,
                actor["UserId"],
                "siie.write.prepared",
                operation,
                kind=kind,
            )
        # Durable non-repeatable intent is committed before entering transport.
        # Never retry after a timeout, invalid 201, server restart or lost receipt.
        with self.tx():
            pass
        result = source.request(kind, payload, files)
        # Persist the provider receipt even if the initiating session expires
        # during IO. The pending intent is the exact authority for this update.
        with transaction(self.settings, True, anonymous=True) as c:
            current = own(c, self.settings, identity)
            op = records.get(c, self.settings, "sw", operation)
            if (
                not op
                or op["private"].get("digest") != digest
                or current["private"].get("pending_operation") != operation
            ):
                raise HTTPException(409, "siie_registration_reconciliation_required")
            records.put(
                c,
                self.settings,
                "sw",
                operation,
                {"state": result["state"], "kind": kind},
                {**op["private"], "result": result},
                op,
            )
            # Keep the confirmed registration IDs when delivering later files.
            updated = (
                {**current["private"], "last_result": result}
                if documents
                else {**current["private"], "result": result}
            )
            state = (
                "confirmed"
                if documents and result["state"] in {"confirmed", "rejected"}
                else result["state"]
            )
            revision = records.put(
                c,
                self.settings,
                "sd",
                identity,
                {**current["metadata"], "state": state},
                updated,
                current,
            )
            audit(
                c,
                self.settings,
                None,
                "siie.write.result",
                operation,
                "accepted" if result["state"] == "confirmed" else "failed",
                kind=kind,
            )
        with self.tx():
            pass
        return {"operation_id": operation, "revision": revision, **result}


def install(app, settings):
    service = Registration(settings)

    @app.get(PREFIX + "/status")
    def status():
        from app.modules.crm_configuration.application.service import read_configuration

        with service.tx() as c:
            cfg = config(c, settings)
            crm, _ = read_configuration(c, foundation=True)
            return {
                **cfg,
                "webhook_path": HOOK_PATH,
                "webhook_secret_configured": bool(secret()),
                "api_configured": source.siie_api.configured("admissions"),
                "stages": [
                    {"key": s.key, "label": s.label} for s in crm.stages if s.active
                ],
                "schema": forms.SCHEMA,
                "applicant_fields": forms.APPLICANT,
                "catalog_dependencies": forms.CATALOGS,
            }

    @app.put(PREFIX + "/configuration")
    def configure(body: Configuration):
        from app.modules.crm_configuration.application.service import read_configuration

        with service.tx(True) as c:
            actor = authorize(
                c,
                settings,
                request_authority.get(),
                "settings.webhooks.write",
                recent=True,
            )
            old = config(c, settings)
            if old["revision"] != body.revision:
                raise HTTPException(409, "revision_conflict")
            crm, _ = read_configuration(c, foundation=True)
            if body.webhook_enabled and (
                not secret()
                or not any(s.key == body.stage_key and s.active for s in crm.stages)
            ):
                raise HTTPException(409, "siie_webhook_configuration_required")
            document = body.model_dump(exclude={"revision"})
            if old["revision"]:
                c.execute(
                    "UPDATE crm_access.Setting SET Document=?,Revision=Revision+1,UpdatedBy=?,UpdatedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND Section='siie-registration' AND Revision=?",
                    canonical(document).decode(),
                    actor["UserId"],
                    institution(settings),
                    old["revision"],
                )
            else:
                c.execute(
                    "INSERT crm_access.Setting(InstitutionId,Section,Document,Revision,UpdatedBy,UpdatedAt) VALUES(?,'siie-registration',?,1,?,SYSUTCDATETIME())",
                    institution(settings),
                    canonical(document).decode(),
                    actor["UserId"],
                )
            audit(
                c,
                settings,
                actor["UserId"],
                "siie.configuration.saved",
                "siie-registration",
            )
        return {"revision": old["revision"] + 1, **document}

    @app.get(PREFIX + "/catalogs")
    def query_catalogs(draft_id: str | None = None):
        with service.tx() as c:
            context = (
                own(c, settings, uid(draft_id))["private"]["context"]
                if draft_id
                else None
            )
        result = catalogs(context)
        with service.tx():
            pass
        return result

    @app.get(PREFIX + "/selection/{kind}")
    def selection(kind: Literal["programs", "offers"], request: Request):
        pairs = list(request.query_params.multi_items())
        if len({k for k, _ in pairs}) != len(pairs):
            raise HTTPException(422, "siie_invalid_parameter")
        with service.tx():
            pass
        result = source.siie_api.read(kind, dict(pairs))
        with service.tx():
            pass
        return result

    @app.get(PREFIX + "/records/{kind}")
    def recent(
        kind: Literal["sd", "se", "sw"],
        offset: Annotated[int, Field(ge=0, le=1000000)] = 0,
    ):
        return service.read(kind, offset=offset)

    @app.get(PREFIX + "/records/{kind}/{identity}")
    def record(kind: Literal["sd", "se", "sw"], identity: str):
        return service.read(kind, identity)

    @app.post(PREFIX + "/events/{identity}/link")
    def link(identity: str, body: Link):
        return service.link(identity, body)

    @app.put(PREFIX + "/drafts/{identity}")
    def save(identity: str, body: Draft):
        return service.save(identity, body)

    @app.get(PREFIX + "/drafts/{identity}/requirements")
    def requirements(identity: str):
        return service.requirements(identity)

    @app.post(PREFIX + "/drafts/{identity}/submit")
    @app.post(PREFIX + "/drafts/{identity}/documents")
    async def submit(identity: str, request: Request):
        files = []
        try:
            if request.headers.get("content-type", "").startswith(
                "multipart/form-data"
            ):
                async with request.form(
                    max_files=18, max_fields=1, max_part_size=262144
                ) as form:
                    if len(form.getlist("command")) != 1 or not isinstance(
                        form["command"], str
                    ):
                        raise ValueError()
                    command = Command.model_validate(strict_json(form["command"]))
                    for name, value in form.multi_items():
                        if name == "command":
                            continue
                        match = re.fullmatch(r"documentos\[([1-9][0-9]?)\]", name)
                        if not match or not hasattr(value, "read"):
                            raise ValueError()
                        content = await value.read(source.MAX_FILE + 1)
                        files.append((int(match[1]), value.filename or "", content))
                    source.files_for(files)
            else:
                command = Command.model_validate(strict_json(await request.body()))
        except (ValueError, TypeError, UnicodeError, RecursionError):
            raise HTTPException(422, "siie_registration_invalid_command") from None
        return await run_in_threadpool(
            service.submit,
            identity,
            command,
            files,
            documents=request.url.path.endswith("/documents"),
        )
