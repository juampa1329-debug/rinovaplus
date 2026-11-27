"""Commercial progress from authenticated statements and real outbound receipts.

This is an admissions follow-up queue, never an academic enrollment or payment.
"""

import hmac
import json
import re
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid5

from fastapi import HTTPException
from pydantic import Field, model_validator

from app.institutional import db
from app.institutional.agent_catalog import normalized
from app.institutional.auth import authorize
from app.institutional.cbn_profile import PREICFES_REGISTRATION_URL, REGISTRATION_URL
from app.institutional.models import Strict
from app.institutional.policy import request_authority
from app.institutional.store import transaction

PURPOSE = "crm.commercial_followup"
CASES = {
    "interest_confirmed": (
        "Interés confirmado",
        "Confirmar programa, grupo y siguiente paso solicitado",
    ),
    "form_sent": (
        "Formulario enviado · pendiente de diligenciar",
        "Consultar si pudo diligenciar el formulario y resolver dificultades",
    ),
    "form_reported_complete": (
        "Formulario diligenciado · por verificar",
        "Verificar inscripción en SIIE antes de pedir nuevamente el formulario",
    ),
    "payment_requested": (
        "Datos de pago solicitados · pendiente de orientación",
        "Compartir los medios oficiales de pago y verificar el siguiente paso con Admisiones",
    ),
}
RANK = {key: i for i, key in enumerate(CASES, 1)}
ADVANCED = {
    "inscripcion",
    "matriculado",
    "propuesta y financiacion",
    "dudas y objeciones",
}
POLICY = (
    "Seguimiento según el avance: si confirmó interés, "
    "concreta el siguiente paso; si ya recibió "
    "el formulario, pregunta por ese trámite y ofrece ayuda; "
    "si declara haberlo completado, pide "
    "verificación a Admisiones; si solicita datos de pago, acompaña ese trámite "
    "sin recordarle llenar el formulario. No reinicies una presentación "
    "o promoción general ni vuelvas a pedir "
    "datos ya aportados. Estos estados comerciales no "
    "acreditan inscripción, pago ni matrícula."
)


def section(contact):
    return "cp-" + UUID(str(contact)).hex


def read(c, s, contact):
    row = db.one(
        c,
        "SELECT Document,Revision FROM crm_access.Setting WHERE "
        "InstitutionId=? AND Section=?",
        db.institution(s),
        section(contact),
    )
    return (json.loads(row["Document"]), row["Revision"]) if row else ({}, 0)


def classification(text, direction, *, accepted=False, previous=""):
    value = normalized(str(text or "")).strip(" .!¡?¿,;:👋😊👍")
    if direction == "outgoing":
        if accepted and any(
            url.casefold() in str(text).casefold()
            for url in (REGISTRATION_URL, PREICFES_REGISTRATION_URL)
        ):
            # Exact URL boundary: a similarly named path/domain is not evidence.
            urls = re.findall(r"https?://[^\s<>]+", str(text), re.I)
            if any(
                url.rstrip(".,;:!?)]*").casefold()
                in {REGISTRATION_URL.casefold(), PREICFES_REGISTRATION_URL.casefold()}
                for url in urls
            ):
                return "form_sent"
        return None
    if direction != "incoming" or re.search(
        r"\b(no|nunca|todavia no|aun no|no he)\b", value
    ):
        return None
    if re.search(
        r"\b(?:datos|cuenta|numero de cuenta|link|enlace)\b"
        r".{0,40}\b(?:pago|pagar|abonar|transferir|consignar)\b|"
        r"\b(?:como|donde|a que cuenta)\s+(?:puedo\s+)?"
        r"(?:pagar|abonar|transferir|consignar|pago)\b|"
        r"\b(?:enviame|comparteme|pasame)\s+(?:la\s+)?cuenta\b",
        value,
    ):
        return "payment_requested"
    if (
        "?" not in str(text)
        and "¿" not in str(text)
        and re.search(
            "\\b(?:ya (?:llene|diligencie|complete|envie|termine)|he "
            "(?:llenado|diligenciado|completado|enviado))\\b.{0,60}\\b(?:"
            "formulario|inscripcion)\\b",
            value,
        )
    ):
        return "form_reported_complete"
    if (
        "?" not in str(text) and "¿" not in str(text)
        and re.fullmatch(r"ya (?:lo )?(?:llene|diligencie|complete|envie|termine)", value)
        and re.search(r"\bformulario\b", normalized(previous))
        and not re.search(r"\b(?:pago|pagaste)\b", normalized(previous))
    ):
        return "form_reported_complete"
    if (
        value
        in {
            "quiero aprovecharlo",
            "quiero inscribirme",
            "deseo inscribirme",
            "quiero matricularme",
        }
        or re.search(
            "\\b(?:quiero|deseo|me interesa)\\s+(?:la "
            "inscripcion|inscribirme|matricularme|estudiar|iniciar el "
            "proceso|el programa|el curso)\\b",
            value,
        )
        or re.search(
            r"\b(?:enviame|envienme|comparteme|pasame)\s+(?:el )?formulario\b", value
        )
    ):
        return "interest_confirmed"
    if value in {"si", "si por favor", "claro", "de acuerdo", "listo"}:
        question = normalized(previous)
        # A bare yes to another question or multiple alternatives stays for review.
        if (
            re.search(
                "(?:te gustaria|quieres|deseas|te comparto|te "
                "envio).{0,65}(?:inscri|formulario)",
                question,
            )
            and "?" in previous
            and not re.search(
                r"\b(?:o|no|pago|pagaste|terminaste|llenaste)\b", question
            )
        ):
            return "interest_confirmed"
        return "review_positive"
    return None


def person(c, s, contact):
    row = db.one(
        c,
        "SELECT p.ContactId,p.Name,p.Stage FROM crm.Contact p WHERE p.ContactId=? "
        "AND EXISTS(SELECT 1 FROM crm_channels2.ExternalIdentity i "
        "LEFT JOIN crm_workspace.Merge g "
        "ON g.SourceContactId=i.ContactId AND g.Active=1 WHERE i.InstitutionId=? "
        "AND COALESCE(g.TargetContactId,i.ContactId)=p.ContactId)",
        contact,
        db.institution(s),
    )
    if not row:
        raise HTTPException(404, "contact_not_found")
    return row


def signals(c, s, contact=None):
    # Authenticated incoming, acknowledged jobs or provider-confirmed imports. Canceled
    # drafts and mere mentions of a form never count. Read-only bounded review.
    return db.rows(
        c,
        "SELECT TOP(5001) COALESCE(g.TargetContactId,i.ContactId) AS ContactId,"
        "m.MessageId,m.ConversationId,m.Body,m.Direction,m.Sequence"
        ",m.CreatedAt,CASE WHEN q.ExternalId IS NOT NULL THEN q.State "
        "WHEN JSON_VALUE(xm.Payload,'$.meta_outgoing')='true' "
        "AND JSON_VALUE(xm.Payload,'$.source')='meta_confirmed_outgoing' "
        "AND xm.ExternalId IS NOT NULL THEN 'accepted' END AS ReceiptState "
        "FROM crm_channels2.MessageRoute r JOIN crm_channels2.ExternalIdentity i "
        "ON i.InstitutionId=r.InstitutionId AND i.IdentityId=r.IdentityId "
        "JOIN crm.Message m ON m.MessageId=r.MessageId AND "
        "m.ConversationId=i.ConversationId "
        "LEFT JOIN crm_channels2.SendJob q ON "
        "q.InstitutionId=r.InstitutionId AND q.QueueId=r.QueueId "
        "LEFT JOIN crm_channels2.ExternalMessage xm "
        "ON xm.InstitutionId=r.InstitutionId AND xm.IntegrationId=r.IntegrationId "
        "AND xm.MessageId=m.MessageId "
        "LEFT JOIN crm_workspace.Merge g ON "
        "g.SourceContactId=i.ContactId AND g.Active=1 "
        "WHERE r.InstitutionId=? AND m.CreatedAt>=DATEADD(day,-90,SYSUTCDATETIME()) "
        + ("AND COALESCE(g.TargetContactId,i.ContactId)=? " if contact else "")
        + "AND ((m.Direction='incoming' AND r.ActorKind='external' AND "
        "(LOWER(m.Body) IN('si','sí','si por favor','sí por "
        "favor','claro','de acuerdo','listo','quiero "
        "aprovecharlo') "
        "OR m.Body LIKE '%inscri%' OR m.Body LIKE '%formulario%' "
        "OR m.Body LIKE '%me interesa%' OR m.Body "
        "LIKE '%quiero estudiar%' OR m.Body LIKE '%pago%' "
        "OR m.Body LIKE '%pagar%' OR m.Body LIKE '%cuenta%' "
        "OR m.Body LIKE '%abonar%' OR m.Body LIKE '%transferir%' "
        "OR m.Body LIKE '%consignar%' OR m.Body LIKE '%llene%' "
        "OR m.Body LIKE '%llené%' OR m.Body LIKE '%diligenci%' "
        "OR m.Body LIKE '%complet%' OR m.Body LIKE '%termine%' "
        "OR m.Body LIKE '%terminé%' OR m.Body LIKE '%envie%' "
        "OR m.Body LIKE '%envié%')) "
        "OR (m.Direction='outgoing' AND ((q.ExternalId IS NOT NULL "
        "AND q.State IN('accepted','sent','delivered','read')) OR "
        "(JSON_VALUE(xm.Payload,'$.meta_outgoing')='true' "
        "AND JSON_VALUE(xm.Payload,'$.source')='meta_confirmed_outgoing' "
        "AND xm.ExternalId IS NOT NULL)) "
        "AND (m.Body LIKE '%siieplus.online/siiewebplus/inscripciones%' "
        "OR m.Body LIKE "
        "'%siieplus.online/siiewebplus/preicfes/inscripcion.html%')"
        ")) "
        "ORDER BY m.CreatedAt,m.MessageId",
        db.institution(s),
        *((contact,) if contact else ()),
    )


def evidence(c, s, messages):
    result = {}
    if len(messages) > 5000:
        raise HTTPException(409, "commercial_followup_scope_limit")
    for msg in messages:
        previous = ""
        state = classification(
            msg["Body"],
            msg["Direction"],
            accepted=msg.get("ReceiptState")
            in {"accepted", "sent", "delivered", "read"},
        )
        if state == "review_positive" or (
            state is None and msg["Direction"] == "incoming"
            and re.fullmatch(r"ya (?:lo )?(?:llene|diligencie|complete|envie|termine)",
                             normalized(msg["Body"]).strip(" .!¡?¿,;:👋😊👍"))
        ):
            prior = db.one(
                c,
                "SELECT TOP(1) m.Body FROM crm.Message m JOIN "
                "crm_channels2.MessageRoute r "
                "ON r.MessageId=m.MessageId JOIN crm_channels2.SendJob q "
                "ON q.InstitutionId=r.InstitutionId "
                "AND q.QueueId=r.QueueId WHERE r.InstitutionId=? AND "
                "m.ConversationId=? AND m.Sequence<? "
                "AND m.CreatedAt>=DATEADD(hour,-24,CONVERT(datetime2,?)) "
                "AND NOT EXISTS(SELECT 1 FROM crm.Message newer WHERE "
                "newer.ConversationId=m.ConversationId AND newer.Sequence>m.Sequence "
                "AND newer.Sequence<? AND newer.Direction='incoming') "
                "AND m.Direction='outgoing' AND q.ExternalId IS NOT NULL "
                "AND q.State IN('accepted','sent','delivered','read') "
                "ORDER BY m.Sequence DESC",
                db.institution(s),
                msg["ConversationId"],
                msg["Sequence"],
                msg["CreatedAt"],
                msg["Sequence"],
            )
            previous = prior["Body"] if prior else ""
            state = classification(msg["Body"], "incoming", previous=previous)
        if not state:
            continue
        contact = db.uid(str(msg["ContactId"]))
        value = {
            "state": state,
            "message_id": db.uid(str(msg["MessageId"])),
            "conversation_id": db.uid(str(msg["ConversationId"])),
            "observed_at": db.utc(msg["CreatedAt"]),
            "receipt_state": msg.get("ReceiptState"),
            "quote": msg["Body"][:400],
            "previous_question": previous[:400],
        }
        if contact not in result or RANK.get(state, 0) >= RANK.get(
            result[contact]["state"], 0
        ):
            result[contact] = value
    return result


def plan(c, s, contact, found):
    p = person(c, s, contact)
    saved, revision = read(c, s, contact)
    existing = saved.get("state")
    if RANK.get(existing, 0) > RANK.get(found["state"], 0):
        return None
    if saved.get("message_id") == found["message_id"]:
        return None
    from app.institutional.contact_preference import blocked
    from app.institutional.siie_classification import blocked as registered

    denied = blocked(c, s, contact)
    suppressed = (
        denied or normalized(p["Stage"]) == "matriculado" or registered(c, s, contact)
    )
    held = found["state"] == "review_positive" or suppressed
    return {
        "contact_id": contact,
        "name": p["Name"],
        "stage": p["Stage"],
        "previous_revision": revision,
        "held": held,
        "no_contact": denied,
        "suppressed": suppressed,
        "label": CASES.get(
            found["state"],
            ("Respuesta positiva por aclarar", "Revisar a qué respondió que sí"),
        )[0],
        "next_action": CASES.get(
            found["state"], ("", "Revisar a qué respondió que sí")
        )[1],
        **found,
    }


def save(c, s, contact, value, revision):
    payload = json.dumps(value, ensure_ascii=False)
    if revision:
        c.execute(
            "UPDATE crm_access.Setting SET "
            "Document=?,Revision=Revision+1,UpdatedAt=SYSUTCDATETIME(),"
            "UpdatedBy=NULL "
            "WHERE InstitutionId=? AND Section=? AND Revision=?",
            payload,
            db.institution(s),
            section(contact),
            revision,
        )
        if c.rowcount != 1:
            raise HTTPException(409, "commercial_followup_preview_changed")
    else:
        c.execute(
            "INSERT crm_access.Setting(InstitutionId,Section,Document,R"
            "evision,UpdatedAt) VALUES(?,?,?,1,SYSUTCDATETIME())",
            db.institution(s),
            section(contact),
            payload,
        )
    c.execute(
        "INSERT crm_access.SettingHistory(InstitutionId,Section,Rev"
        "ision,Document,RecordedAt,ActorId) "
        "VALUES(?,?,?,?,SYSUTCDATETIME(),NULL)",
        db.institution(s),
        section(contact),
        revision + 1,
        payload,
    )


def commit(c, s, item, actor=None):
    contact = item["contact_id"]
    if item.get("suppressed", item["no_contact"]):
        return False
    value = {
        k: item[k]
        for k in (
            "state",
            "message_id",
            "conversation_id",
            "observed_at",
            "receipt_state",
            "quote",
            "label",
            "next_action",
        )
    }
    value["authority"] = "authenticated_commercial_evidence_v1"
    save(c, s, contact, value, item["previous_revision"])
    # Follow-up stage only for initial stages; never regress enrollment/finance
    # or any later human choice. Every change is CAS-bound to the review.
    changed = False
    manual = c.execute(
        "SELECT 1 FROM crm_access.Audit WHERE InstitutionId=? AND "
        "Action='workspace.contact' "
        "AND ResourceRef=? AND OccurredAt>?",
        db.institution(s),
        contact,
        datetime.fromisoformat(item["observed_at"].replace("Z", "+00:00")).replace(
            tzinfo=None
        ),
    ).fetchone()
    from app.modules.crm_configuration.application.service import read_configuration

    config, _ = read_configuration(c, foundation=True)
    valid_stage = any(v.active and v.label == "Seguimiento" for v in config.stages)
    if (
        valid_stage
        and not item["held"]
        and not manual
        and normalized(item["stage"]) in {"nuevo", "calificacion"}
    ):
        changed = (
            c.execute(
                "UPDATE crm.Contact SET Stage='Seguimiento',UpdatedAt=SYSUTCDATETIME() "
                "WHERE ContactId=? AND Stage=?",
                contact,
                item["stage"],
            ).rowcount
            == 1
        )
    task = str(uuid5(UUID(contact), "commercial-followup:" + item["state"]))
    # Separate tasks by case. Do not reopen a task completed by a person.
    if not c.execute(
        "SELECT 1 FROM crm_workspace.Task WHERE InstitutionId=? AND TaskId=?",
        db.institution(s),
        task,
    ).fetchone():
        c.execute(
            "INSERT crm_workspace.Task(TaskId,InstitutionId,Conversatio"
            "nId,UserId,Title,Status,Priority,DueAt) "
            "VALUES(?,?,?,NULL,?,'pending','normal',?)",
            task,
            db.institution(s),
            item["conversation_id"],
            item["next_action"][:120],
            datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=24),
        )
    for earlier in CASES:
        if RANK[earlier] < RANK.get(item["state"], 0):
            c.execute(
                "UPDATE crm_workspace.Task SET "
                "Status='cancelled',UpdatedAt=SYSUTCDATETIME() "
                "WHERE InstitutionId=? AND TaskId=? AND Status='pending'",
                db.institution(s),
                str(uuid5(UUID(contact), "commercial-followup:" + earlier)),
            )
    c.execute("UPDATE crm_workspace.State SET Revision=Revision+1 WHERE StateId=1")
    db.audit(
        c,
        s,
        actor,
        PURPOSE,
        contact,
        fields=["commercial_progress", "task"] + (["stage"] if changed else []),
        reason=item["state"],
    )
    return True


def observe(c, s, contact):
    if not getattr(s, "postgres_deployment", False):
        return
    from app.institutional.contact_preference import blocked
    from app.institutional.siie_classification import blocked as registered

    if blocked(c, s, contact) or registered(c, s, contact):
        for state in [*CASES, "review_positive"]:
            c.execute(
                "UPDATE crm_workspace.Task SET Status='cancelled',"
                "UpdatedAt=SYSUTCDATETIME() WHERE InstitutionId=? "
                "AND TaskId=? AND Status='pending'",
                db.institution(s),
                str(uuid5(UUID(str(contact)), "commercial-followup:" + state)),
            )
        return
    found = evidence(c, s, signals(c, s, contact)).get(db.uid(str(contact)))
    if found:
        item = plan(c, s, db.uid(str(contact)), found)
        if item and not item.get("suppressed", item["no_contact"]):
            commit(c, s, item)


def progress_map(c, s):
    if not getattr(s, "postgres_deployment", False):
        return {}
    found = db.rows(
        c,
        "SELECT Section,Document FROM crm_access.Setting WHERE "
        "InstitutionId=? AND Section LIKE 'cp-%'",
        db.institution(s),
    )
    result = {str(UUID(v["Section"][3:])): json.loads(v["Document"]) for v in found}
    merges = db.rows(
        c,
        "SELECT SourceContactId,TargetContactId FROM "
        "crm_workspace.Merge WHERE Active=1",
    )
    for merge in merges:
        source, target = (
            str(merge["SourceContactId"]).lower(),
            str(merge["TargetContactId"]).lower(),
        )
        if source in result and RANK.get(result[source].get("state"), 0) >= RANK.get(
            result.get(target, {}).get("state"), 0
        ):
            result[target] = result[source]
    return result


def exclusion(progress, stage, doc):
    state = progress.get("state")
    explicit = doc.get("followup_only") and state in doc.get(
        "entry_conditions", {}
    ).get("followup_states", [])
    if state in {*CASES, "review_positive"} and not explicit:
        return "commercial_progress_requires_case_followup"
    if normalized(stage or "") in ADVANCED and not explicit:
        return "advanced_stage_no_reactivation"
    return None


def signature(s, item):
    return db.bound_hash(s, item, PURPOSE).hex()


class Item(Strict):
    contact_id: str
    signature: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def valid(self):
        self.contact_id = str(UUID(self.contact_id))
        return self


class Apply(Strict):
    operation_id: str
    items: list[Item] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def valid(self):
        self.operation_id = str(UUID(self.operation_id))
        if len({i.contact_id for i in self.items}) != len(self.items):
            raise ValueError("duplicate_contact")
        return self


def preview(s):
    with transaction(s, False, permission="crm.read") as c:
        authorize(c, s, request_authority.get(), "crm.read")
        proposals = [
            plan(c, s, contact, found)
            for contact, found in evidence(c, s, signals(c, s)).items()
        ]
        items = [{**v, "signature": signature(s, v)} for v in proposals if v]
        return {
            "items": items,
            "ready": sum(not v["held"] for v in items),
            "review": sum(v["held"] for v in items),
        }


def apply(s, body):
    with transaction(s, True, permission="crm.write") as c:
        actor = authorize(c, s, request_authority.get(), "crm.write", recent=True)
        digest, prior = db.replay(
            c, s, actor["UserId"], body.operation_id, PURPOSE, "crm", body.model_dump()
        )
        if prior is not None:
            return prior
        updated = 0
        for chosen in body.items:
            found = evidence(c, s, signals(c, s, chosen.contact_id)).get(
                chosen.contact_id
            )
            item = plan(c, s, chosen.contact_id, found) if found else None
            if (
                not item
                or item.get("suppressed", item["no_contact"])
                or not hmac.compare_digest(signature(s, item), chosen.signature)
            ):
                raise HTTPException(409, "commercial_followup_preview_changed")
            updated += commit(c, s, item, actor["UserId"])
        result = {"updated": updated}
        db.record_operation(
            c, s, actor["UserId"], body.operation_id, PURPOSE, "crm", digest, result
        )
        return result


def install(app, s):
    @app.get("/api/institution/workspace/commercial-followup/preview")
    def review():
        return preview(s)

    @app.post("/api/institution/workspace/commercial-followup/apply")
    def update(body: Apply):
        return apply(s, body)

    @app.get("/api/institution/workspace/commercial-followup/{contact_id}")
    def contact(contact_id: str):
        with transaction(s, False, permission="crm.read") as c:
            authorize(c, s, request_authority.get(), "crm.read")
            key = db.uid(contact_id)
            if not c.execute(
                "SELECT 1 FROM crm.Contact WHERE ContactId=?", key
            ).fetchone():
                raise HTTPException(404, "contact_not_found")
            value, revision = read(c, s, key)
            return {"progress": value or None, "revision": revision, "policy": POLICY}
