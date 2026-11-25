"""Reviewed alternate routes for an untouched imported contact; no delivery IO."""

import json
from uuid import uuid4

from fastapi import HTTPException

from app.institutional import db
from app.institutional.prospect_import import phone


def plan(c, settings, integration, contact_id, destination, program):
    from app.institutional.broadcast_prospects import reviewed_contact

    person = db.one(
        c,
        "SELECT ContactId,Phone,Type,CustomValues FROM crm.Contact WHERE ContactId=?",
        contact_id,
    )
    primary_phone = reviewed_contact(person, program)
    normalized = phone(destination).removeprefix("+")
    if not normalized or normalized == primary_phone:
        raise HTTPException(422, "prospect_alternate_phone_invalid")
    primary = db.one(
        c,
        "SELECT * FROM crm_channels2.ExternalIdentity WHERE InstitutionId=? "
        "AND IntegrationId=? AND ExternalId=?",
        db.institution(settings),
        integration,
        primary_phone,
    )
    if not primary or str(primary["ContactId"]).lower() != contact_id:
        raise HTTPException(409, "prospect_primary_route_required")
    existing = db.one(
        c,
        "SELECT * FROM crm_channels2.ExternalIdentity WHERE InstitutionId=? "
        "AND IntegrationId=? AND ExternalId=?",
        db.institution(settings),
        integration,
        normalized,
    )
    if existing:
        if str(existing["ContactId"]).lower() != contact_id or str(
            existing["ConversationId"]
        ) != str(primary["ConversationId"]):
            raise HTTPException(409, "prospect_phone_identity_conflict")
        return dict(existing, destination=normalized)
    if c.execute(
        "SELECT 1 FROM crm_workspace.Merge WHERE Active=1 "
        "AND (SourceContactId=? OR TargetContactId=?)",
        contact_id,
        contact_id,
    ).fetchone():
        raise HTTPException(409, "prospect_alternate_merge_review_required")
    conversation = db.one(
        c,
        "SELECT v.ConversationId,v.ContactId,v.ControlMode,v.State,"
        "COALESCE(ctrl.Epoch,0) AS ControlEpoch FROM crm.Conversation v "
        "LEFT JOIN crm_channels.ConversationControl ctrl "
        "ON ctrl.ConversationId=v.ConversationId WHERE v.ConversationId=?",
        primary["ConversationId"],
    )
    if (
        not conversation
        or str(conversation["ContactId"]).lower() != contact_id
        or conversation["ControlMode"] != "ai"
        or conversation["State"] == "closed"
        or conversation["ControlEpoch"] > 1
        or c.execute(
            "SELECT 1 FROM crm.Message WHERE ConversationId=?",
            primary["ConversationId"],
        ).fetchone()
    ):
        raise HTTPException(409, "prospect_existing_history_review_required")
    contacts = db.rows(c, "SELECT TOP(20001) ContactId,Phone FROM crm.Contact")
    if len(contacts) > 20000:
        raise HTTPException(409, "prospect_import_scope_limit")
    if any(
        str(row["ContactId"]).lower() != contact_id
        and phone(row["Phone"]).removeprefix("+") == normalized
        for row in contacts
    ):
        raise HTTPException(409, "prospect_phone_identity_conflict")
    # Source phone declarations remain separate from academic identity.
    custom = json.loads(person["CustomValues"])
    if not custom.get("pre_import_ref"):
        raise HTTPException(409, "prospect_phone_program_review_required")
    return {
        "IdentityId": None,
        "ContactId": contact_id,
        "ConversationId": primary["ConversationId"],
        "destination": normalized,
    }


def link(c, settings, integration, planned):
    if planned["IdentityId"]:
        return str(planned["IdentityId"])
    identity = str(uuid4())
    c.execute(
        "INSERT crm_channels2.ExternalIdentity(InstitutionId,IdentityId,"
        "IntegrationId,ExternalId,ContactId,ConversationId,CreatedAt) "
        "VALUES(?,?,?,?,?,?,SYSUTCDATETIME())",
        db.institution(settings),
        identity,
        integration,
        planned["destination"],
        planned["ContactId"],
        planned["ConversationId"],
    )
    return identity
