"""Source-backed SIIE classification, distinct from marketing consent and tags."""

from app.institutional import siie_records as records
from app.institutional.db import bound_hash, institution, one, uid


def phone_hash(settings, value):
    from app.institutional.prospect_import import phone

    canonical = phone(value)
    return (
        bound_hash(settings, canonical, "siie_registered_phone").hex()
        if canonical
        else ""
    )


def mark(c, settings, contact, registered, event_id):
    contact = uid(str(contact))
    old = records.get(c, settings, "sg", contact)
    enrolled = registered or bool(
        old and old["metadata"].get("classification") == "registered"
    )
    person = one(c, "SELECT Phone FROM crm.Contact WHERE ContactId=?", contact)
    records.put(
        c,
        settings,
        "sg",
        contact,
        {
            "source": "siie",
            "classification": "registered" if enrolled else "pre_registered",
            "contact_id": contact,
            "phone_hash": phone_hash(settings, person["Phone"]) if person else "",
        },
        {"event_id": event_id},
        old,
    )


def blocked(c, settings, contact, phone=""):
    if not contact:
        return False
    # Include merged identities: changing the canonical CRM contact cannot
    # reintroduce a registered student into a promotional campaign.
    return bool(
        one(
            c,
            "SELECT TOP(1) st.Section FROM crm_access.Setting st JOIN crm.Contact p "
            "ON st.Section=CONCAT('sg:',REPLACE(LOWER(CONVERT(varchar(36),p.ContactId)),'-','')) "
            "LEFT JOIN crm_workspace.Merge g ON g.SourceContactId=p.ContactId AND g.Active=1 "
            "WHERE st.InstitutionId=? AND st.Section LIKE 'sg:%' AND (COALESCE(g.TargetContactId,p.ContactId)=? "
            "OR (?<>'' AND JSON_VALUE(st.Document,'$.metadata.phone_hash')=?)) "
            "AND JSON_VALUE(st.Document,'$.metadata.classification')='registered'",
            institution(settings),
            uid(str(contact)),
            phone_hash(settings, phone),
            phone_hash(settings, phone),
        )
    )


def registered_contacts(c, settings):
    return promotion_exclusions(c, settings)[0]


def promotion_exclusions(c, settings):
    from app.institutional.db import rows

    values = rows(
        c,
        "SELECT COALESCE(g.TargetContactId,p.ContactId) AS ContactId,JSON_VALUE(st.Document,'$.metadata.phone_hash') AS PhoneHash FROM crm_access.Setting st "
        "JOIN crm.Contact p ON st.Section=CONCAT('sg:',REPLACE(LOWER(CONVERT(varchar(36),p.ContactId)),'-','')) "
        "LEFT JOIN crm_workspace.Merge g ON g.SourceContactId=p.ContactId AND g.Active=1 "
        "WHERE st.InstitutionId=? AND st.Section LIKE 'sg:%' "
        "AND JSON_VALUE(st.Document,'$.metadata.classification')='registered'",
        institution(settings),
    )
    return {uid(str(v["ContactId"])) for v in values}, {
        v["PhoneHash"] for v in values if v["PhoneHash"]
    }
