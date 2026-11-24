"""Owner-reviewed commercial recommendations; original imports and SIIE stay intact."""

import hmac
import json
import re
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import Field, model_validator

from app.institutional import db, sales_contact
from app.institutional.agent_catalog import Catalog, normalized
from app.institutional.auth import authorize
from app.institutional.models import Strict
from app.institutional.policy import request_authority
from app.institutional.store import transaction

PURPOSE = "crm.masterclass.interests"
AUTHORITY = "owner_masterclass_related_programs_v1"
POLICY = (
    "\nORIENTACIÓN DESDE MASTERCLASS: opciones_relacionadas_masterclass contiene propuestas comerciales "
    "revisadas por el titular, no programas elegidos por el cliente ni matrículas. Relaciona su masterclass "
    "con esas opciones de formación. Si hay varios programas, ofrece brevemente las alternativas de esa "
    "escuela y pregunta cuál le interesa; no selecciones carrera ni jornada por la persona. Si hay un solo "
    "programa relacionado, preséntalo como una opción para continuar su formación. Una elección expresa "
    "más reciente del contacto tiene prioridad; no vuelvas a ofrecer toda la escuela si ya eligió. "
    "No afirmes que asistió, terminó o pagó la masterclass: el dato sólo acredita interés registrado. "
    "Consulta las fichas vigentes para beneficios, requisitos y financiación, usando las skills comerciales."
)


def is_masterclass(text):
    return bool(re.search(r"\bmaster\s*class(?:es|s)?\b", normalized(str(text or ""))))


def targets(source, programs):
    text = normalized(source)
    field = "name"
    if re.search(r"baris|bartend|cafe|caffe", text):
        pattern = r"baris|bartend"
    elif re.search(r"repost|pastel|cupcake|dulce", text):
        pattern = r"repost|pastel"
    elif re.search(r"cocina|culinari|pasta artesanal|sabores de latinoamerica", text):
        pattern = r"cocina nacional"
    elif re.search(r"turism|hoteler", text):
        pattern = r"servicios hoteleros"
    elif "aduan" in text:
        pattern = r"aduanas"
    elif "logistic" in text:
        pattern = r"^logistica portuaria"
    elif re.search(r"ingles|english|idiomas", text):
        pattern = r"ingles"
    else:
        school = next((v for v in ("salud", "tic", "gastronom", "administracion")
                       if re.search(r"\b" + v, text)), None)
        if not school:
            return []
        field, pattern = "school", r"\b" + school
    combined = any("barismo" in normalized(p["name"]) and "bartender" in normalized(p["name"]) for p in programs)
    return [p for p in programs if re.search(pattern, normalized(p.get(field) or "")) and not is_masterclass(p["name"])
            and not str(p.get("authority", "")).startswith("synthetic")
            and not (combined and normalized(p["name"]) in {"barismo", "bartender"})]


def catalog(c, settings):
    return Catalog(settings).programs(c, 0, 300)["items"]


def contact_rows(c, contact=None):
    return db.rows(c,
        "SELECT TOP(20001) p.ContactId,p.Interests,p.CustomValues FROM crm.Contact p "
        "WHERE NOT EXISTS(SELECT 1 FROM crm_workspace.Merge g WHERE g.SourceContactId=p.ContactId AND g.Active=1) "
        + ("AND p.ContactId=? " if contact else
           "AND (p.Interests LIKE '%master%class%' OR JSON_VALUE(p.CustomValues,'$.pre_programas') LIKE '%master%class%') ")
        + "ORDER BY p.ContactId", *((contact,) if contact else ()))


def proposal(person, programs):
    current = person["Interests"] or ""
    source = current
    if current == "Varios intereses; consultar programas y notas de origen":
        source = json.loads(person["CustomValues"] or "{}").get("pre_programas", "")
    pieces = [v.strip() for v in source.split("|") if v.strip()]
    originals = [v for v in pieces if is_masterclass(v)]
    if not originals:
        return None
    related, unresolved = [], []
    for value in originals:
        found = targets(value, programs)
        if not found:
            unresolved.append(value)
        for p in found:
            if not any(old["program_id"] == p["program_id"] for old in related):
                related.append({k: p.get(k, "") for k in ("program_id", "name", "school", "schedule")})
    names = list(dict.fromkeys([*[v for v in pieces if not is_masterclass(v)], *[p["name"] for p in related]]))
    updated = " | ".join(names)
    return {"contact_id": str(person["ContactId"]), "previous_interests": current,
            "source_interests": source, "original_masterclasses": originals,
            "interests": updated, "programs": related,
            "reason": "Tema sin relación revisada" if unresolved else
                      "Los intereses completos superan 300 caracteres" if len(updated.encode("utf-16-le")) // 2 > 300 else "",
            "unresolved": unresolved}


def signature(settings, plan):
    return db.bound_hash(settings, plan, PURPOSE).hex()


class Item(Strict):
    contact_id: str
    signature: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def valid_id(self):
        self.contact_id = str(UUID(self.contact_id))
        return self


class Apply(Strict):
    operation_id: str
    items: list[Item] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def distinct(self):
        self.operation_id = str(UUID(self.operation_id))
        if len({v.contact_id for v in self.items}) != len(self.items):
            raise ValueError("masterclass_duplicate_contact")
        return self


def preview(settings):
    with transaction(settings, False, permission="crm.read") as c:
        authorize(c, settings, request_authority.get(), "crm.read")
        people, programs = contact_rows(c), catalog(c, settings)
        if len(people) > 20000:
            raise HTTPException(409, "masterclass_scope_limit")
        groups, ready, held = {}, [], 0
        for person in people:
            plan = proposal(person, programs)
            if not plan:
                continue
            key = " | ".join(plan["original_masterclasses"])
            group = groups.setdefault(key, {"source": key,
                "programs": list(dict.fromkeys(p["name"] for p in plan["programs"])),
                "count": 0, "review": 0, "reason": plan["reason"]})
            group["count"] += 1
            if plan["reason"]:
                group["review"] += 1
                held += 1
            else:
                ready.append({"contact_id": plan["contact_id"], "signature": signature(settings, plan)})
        return {"groups": list(groups.values()), "items": ready, "ready": len(ready), "review": held}


def apply(settings, body):
    with transaction(settings, True, permission="crm.write") as c:
        actor = authorize(c, settings, request_authority.get(), "crm.write")
        actor_id = db.uid(str(actor["UserId"]))
        digest, prior = db.replay(c, settings, actor_id, body.operation_id, PURPOSE, "crm", body.model_dump())
        if prior is not None:
            return prior
        programs = catalog(c, settings)
        result = []
        for item in body.items:
            found = contact_rows(c, item.contact_id)
            plan = proposal(found[0], programs) if len(found) == 1 else None
            if not plan or plan["reason"] or not hmac.compare_digest(signature(settings, plan), item.signature):
                raise HTTPException(409, "masterclass_preview_changed")
            c.execute("UPDATE crm.Contact SET Interests=?,UpdatedAt=SYSUTCDATETIME() WHERE ContactId=? AND COALESCE(Interests,'')=?",
                      plan["interests"], item.contact_id, plan["previous_interests"])
            if c.rowcount != 1:
                raise HTTPException(409, "masterclass_preview_changed")
            document, revision = sales_contact.read(c, settings, item.contact_id)
            document.setdefault("fields", {})["interests"] = {"authority": AUTHORITY, "value": plan["interests"]}
            document["masterclass_orientation"] = {**plan, "authority": AUTHORITY, "customer_choice": False}
            sales_contact.save(c, settings, item.contact_id, document, revision)
            c.execute("INSERT crm_workspace.Note(NoteId,ContactId,InstitutionId,AuthorId,Body) VALUES(?,?,?,?,?)",
                      str(uuid4()), item.contact_id, db.institution(settings), actor_id,
                      "Reorientación comercial de masterclass por indicación del titular. Interés original: "
                      + plan["previous_interests"] + ". Opciones relacionadas: " + plan["interests"]
                      + ". Pendiente de elección del contacto; no acredita matrícula ni asistencia.")
            result.append({"contact_id": item.contact_id, "state": "updated"})
        c.execute("UPDATE crm_workspace.State SET Revision=Revision+1 WHERE StateId=1")
        response = {"items": result, "updated": len(result)}
        db.record_operation(c, settings, actor_id, body.operation_id, PURPOSE, "crm", digest, response)
        db.audit(c, settings, actor_id, PURPOSE, count=len(result), fields=["interests"], reason="owner_reviewed_related_programs")
        return response


def orientation(c, settings, conversation):
    person = sales_contact.contact(c, conversation)
    if not person:
        return None
    document, _ = sales_contact.read(c, settings, person["ContactId"])
    value = document.get("masterclass_orientation", {})
    if value.get("authority") != AUTHORITY or value.get("interests") != person["Interests"]:
        return None
    return {"authority": AUTHORITY, "original_masterclasses": value["original_masterclasses"],
            "programs": value["programs"], "customer_choice": False}


def install(app, settings):
    prefix = "/api/institution/workspace/masterclass-interests"

    @app.get(prefix + "/preview")
    def review():
        return preview(settings)

    @app.post(prefix + "/apply")
    def commit(body: Apply):
        return apply(settings, body)
