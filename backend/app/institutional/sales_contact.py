"""Customer-declared display fields, with provenance and manual-edit protection."""
import json
import re
import unicodedata
from uuid import UUID

from fastapi import HTTPException

from app.institutional import db

FIELDS = {"name": ("Name", 100), "city": ("City", 100), "schedule": ("Schedule", 100), "interests": ("Interests", 300)}


def section(contact):
    return "cf-" + UUID(str(contact)).hex


def read(c, settings, contact):
    value = db.one(c, "SELECT Document,Revision FROM crm_access.Setting WHERE InstitutionId=? AND Section=?",
                   db.institution(settings), section(contact))
    return (json.loads(value["Document"]), value["Revision"]) if value else ({"fields": {}}, 0)


def save(c, settings, contact, document, revision):
    payload = json.dumps(document, ensure_ascii=False)
    if revision:
        c.execute("UPDATE crm_access.Setting SET Document=?,Revision=Revision+1,UpdatedAt=SYSUTCDATETIME(),UpdatedBy=NULL WHERE InstitutionId=? AND Section=? AND Revision=?",
                  payload, db.institution(settings), section(contact), revision)
        if c.rowcount != 1:
            raise HTTPException(409, "sales_contact_revision_conflict")
    else:
        c.execute("INSERT crm_access.Setting(InstitutionId,Section,Document,Revision,UpdatedAt) VALUES(?,?,?,1,SYSUTCDATETIME())",
                  db.institution(settings), section(contact), payload)
    c.execute("INSERT crm_access.SettingHistory(InstitutionId,Section,Revision,Document,RecordedAt,ActorId) VALUES(?,?,?,?,SYSUTCDATETIME(),NULL)",
              db.institution(settings), section(contact), revision + 1, payload)


def mark_manual(c, settings, contact, previous, current):
    changed = [key for key in FIELDS if previous.get(key) != getattr(current, key)]
    if not changed:
        return
    document, revision = read(c, settings, contact)
    for key in changed:
        document["fields"][key] = {"authority": "manual", "value": getattr(current, key)}
    save(c, settings, contact, document, revision)


def contact(c, conversation):
    return db.one(c, "SELECT p.ContactId,p.Name,p.City,p.Schedule,p.Interests FROM crm.Conversation v JOIN crm.Contact p ON p.ContactId=COALESCE((SELECT TargetContactId FROM crm_workspace.Merge WHERE SourceContactId=v.ContactId AND Active=1),v.ContactId) WHERE v.ConversationId=?", conversation)


def display_name(value):
    name = " ".join("".join(ch for ch in str(value or "") if unicodedata.category(ch)[0] in {"L", "M"} or ch in " '-").split())[:100]
    if not name or re.search(r"contacto|dm sender|facebook user|instagram user|usuario de|whatsapp|sin nombre", name, re.I):
        return None
    return name


def personalization(c, settings, conversation, sequence=None):
    row = contact(c, conversation)
    if not row:
        return None
    document, _ = read(c, settings, row["ContactId"])
    field = document.get("fields", {}).get("name", {})
    name = row["Name"]
    # A response must not invalidate its own dispatch binding after saving a name.
    if sequence and field.get("conversation") == str(conversation) and field.get("sequence", 0) >= sequence and field.get("value") == name:
        name = field.get("previous", name)
    return {"display_name": display_name(name), "authority": "CRM_display_name_not_legal_identity",
            "instructions": "Usa el nombre disponible de forma cálida cuando encaje, sin repetirlo ni saludar en cada turno. No vuelvas a pedirlo si ya está confirmado; respeta correcciones explícitas del contacto. No infieras identidad legal."}


def declared_value(item, incoming, previous_reply=""):
    field, quote, value = item.get("field"), item.get("quote"), item.get("value")
    if field not in FIELDS or not isinstance(value, str) or not isinstance(quote, str):
        return None
    value = value.strip()
    if not 2 <= len(value.encode("utf-16-le")) // 2 <= FIELDS[field][1] or value not in quote or quote not in incoming["Body"] or any(ord(ch) < 32 for ch in value):
        return None
    if field == "name":
        explicit = re.search(r"(?:me llamo|mi nombre es|ll[aá]mame|puedes decirme|prefiero que me llames)\s+" + re.escape(value) + r"(?:\b|$)", incoming["Body"], re.I)
        asked = re.search(r"c[oó]mo te llamas|tu nombre|con qui[eé]n tengo el gusto", previous_reply, re.I)
        if display_name(value) != value or not (explicit or asked and incoming["Body"].strip(" .!¡") == value):
            return None
    return value


def project(c, settings, data, observations, incoming):
    candidates = list({v["field"]: v for v in observations if v.get("field") in FIELDS and v.get("declared_value")}.values())
    if not candidates:
        return []
    person = contact(c, data["conversation"])
    if not person:
        return []
    document, revision = read(c, settings, person["ContactId"])
    legacy_manual = revision == 0 and db.one(c, "SELECT TOP(1) 1 AS Found FROM crm_access.Audit WHERE InstitutionId=? AND Action='workspace.contact' AND ResourceRef=?",
                                           db.institution(settings), str(person["ContactId"]).lower())
    if legacy_manual:
        for key, (column, _) in FIELDS.items():
            if person[column]:
                document["fields"][key] = {"authority": "manual", "value": person[column]}
    outcomes, changed = [], False
    for item in candidates:
        field = item["field"]
        column = FIELDS[field][0]  # Fixed allowlist; never a model-provided SQL identifier.
        value, current = item["declared_value"], person[column] or ""
        prior = document["fields"].get(field)
        manual = prior and (prior.get("authority") == "manual" or prior.get("value") != current)
        if manual or legacy_manual and current:
            outcomes.append({"field": field, "state": "manual_preserved", "source_message_id": item["source_message_id"]})
            continue
        if value != current:
            c.execute(f"UPDATE crm.Contact SET {column}=? WHERE ContactId=? AND COALESCE({column},'')=?", value, person["ContactId"], current)
            if c.rowcount != 1:
                raise HTTPException(409, "sales_contact_revision_conflict")
            document["fields"][field] = {"authority": "customer_declared_automatic", "value": value, "previous": current,
                "conversation": str(data["conversation"]), "sequence": incoming["Sequence"], "source_message_id": item["source_message_id"], "origin": item["origin"]}
            changed = True
        outcomes.append({"field": field, "state": "updated" if value != current else "already_current", "source_message_id": item["source_message_id"]})
    if changed:
        save(c, settings, person["ContactId"], document, revision)
        c.execute("UPDATE crm.Conversation SET UpdatedAt=SYSUTCDATETIME() WHERE ContactId=?", person["ContactId"])
        c.execute("UPDATE crm_workspace.State SET Revision=Revision+1 WHERE StateId=1")
        db.audit(c, settings, None, "sales.contact.project", str(person["ContactId"]), fields=[v["field"] for v in outcomes if v["state"] == "updated"], reason="customer_quote")
    return outcomes
