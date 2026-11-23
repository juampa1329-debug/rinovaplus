"""Explicit outbound WhatsApp onboarding for reviewed imported CRM prospects."""

import json
import re
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID, uuid4, uuid5

from fastapi import HTTPException
from pydantic import Field, model_validator

from app.institutional import db
from app.institutional.auth import authorize
from app.institutional.broadcast_models import ConsentWrite
from app.institutional.channel_operations import account
from app.institutional.prospect_import import normalize, phone
from app.modules.inbox.application.state import control

PROGRAMS = {
    "logistica": "logistica portuaria y maritima",
    "aduanas": "aduanas, procesos logisticos y automatizacion",
}


class ProspectSetup(ConsentWrite):
    state: Literal["granted"] = "granted"
    program: Literal["logistica", "aduanas"]
    contact_ids: list[str] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def bounded_setup(self):
        self.contact_ids = [str(UUID(v)) for v in self.contact_ids]
        if len(set(self.contact_ids)) != len(self.contact_ids):
            raise ValueError("prospect_contacts_duplicate")
        expires = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
        if expires > datetime.now(timezone.utc) + timedelta(days=2):
            raise ValueError("prospect_setup_expiry_maximum_two_days")
        return self


def reviewed_contact(value, program):
    if not value:
        raise HTTPException(404, "prospect_contact_not_found")
    custom = json.loads(value["CustomValues"])
    interests = {normalize(v) for v in custom.get("pre_programas", "").split("|")}
    if (
        value["Type"] != "Preinscrito"
        or not re.fullmatch(r"PRE-[a-f0-9]{16}", custom.get("pre_import_ref", ""))
        or PROGRAMS[program] not in interests
        or not phone(value["Phone"])
    ):
        raise HTTPException(409, "prospect_phone_program_review_required")
    return phone(value["Phone"]).removeprefix("+")


def link(c, settings, integration, contact_id, program):
    person = db.one(
        c, "SELECT ContactId,Phone,Type,CustomValues FROM crm.Contact "
        "WHERE ContactId=?", contact_id,
    )
    destination = reviewed_contact(person, program)
    existing = db.one(
        c, "SELECT * FROM crm_channels2.ExternalIdentity "
        "WHERE InstitutionId=? AND IntegrationId=? AND ExternalId=?",
        db.institution(settings), integration, destination,
    )
    if existing:
        if str(existing["ContactId"]).lower() != contact_id:
            raise HTTPException(409, "prospect_phone_identity_conflict")
        return str(existing["IdentityId"])
    if c.execute(
        "SELECT 1 FROM crm_channels2.ExternalIdentity "
        "WHERE InstitutionId=? AND ContactId=?",
        db.institution(settings), contact_id,
    ).fetchone():
        raise HTTPException(409, "prospect_existing_channel_review_required")
    # An untouched import placeholder is not an existing WhatsApp chat. Never
    # replace, unpause, or create an alternate route around real human history.
    if c.execute(
        "SELECT 1 FROM crm.Conversation v WHERE v.ContactId=? AND "
        "(EXISTS(SELECT 1 FROM crm.Message m WHERE m.ConversationId=v.ConversationId) "
        "OR EXISTS(SELECT 1 FROM crm_channels.ConversationControl ctrl "
        "WHERE ctrl.ConversationId=v.ConversationId AND ctrl.Epoch<>0))",
        contact_id,
    ).fetchone():
        raise HTTPException(409, "prospect_existing_history_review_required")
    conversation, identity = str(uuid4()), str(uuid4())
    c.execute(
        "INSERT crm.Conversation(ConversationId,ContactId,State,Priority,"
        "ControlMode,Unread) VALUES(?,?,'open','normal','ai',0)",
        conversation, contact_id,
    )
    control(c, conversation)
    c.execute(
        "INSERT crm_channels2.ExternalIdentity(InstitutionId,IdentityId,"
        "IntegrationId,ExternalId,ContactId,ConversationId,CreatedAt) "
        "VALUES(?,?,?,?,?,?,SYSUTCDATETIME())",
        db.institution(settings), identity, integration, destination,
        contact_id, conversation,
    )
    return identity


def setup(service, auth, integration, body):
    from app.institutional.broadcasts import consent

    with service.tx(auth, True, recent=True) as (c, actor):
        authorize(c, service.settings, auth, "crm.write")
        authorize(c, service.settings, auth, "inbox.write")
        digest, prior = db.replay(
            c, service.settings, actor["UserId"], str(body.operation_id),
            "broadcast.prospect_setup", integration, body.model_dump(mode="json"),
        )
        if prior:
            result = prior
        else:
            item = account(c, service.settings, integration)
            if (
                item["Channel"] != "whatsapp"
                or item["RequestedStatus"] != "connected"
                or item["VerifiedStatus"] != "verified"
            ):
                raise HTTPException(409, "broadcast_verified_whatsapp_account_required")
            items = []
            for contact_id in body.contact_ids:
                identity = link(
                    c, service.settings, integration, contact_id, body.program,
                )
                old = consent(c, service.settings, identity)
                if old and old["State"] == "revoked":
                    raise HTTPException(409, "prospect_revoked_consent_review_required")
                items.append({
                    "contact_id": contact_id, "identity_id": identity,
                    "consent_revision": old["VersionNo"] if old else 0,
                })
            result = {"items": items, "program": body.program}
            db.record_operation(
                c, service.settings, actor["UserId"], str(body.operation_id),
                "broadcast.prospect_setup", integration, digest, result,
            )
            db.audit(
                c, service.settings, actor["UserId"], "broadcast.prospect_setup",
                integration, count=len(items), scope=body.program,
                fields=["outbound_whatsapp_route"],
            )
    # Separate native consent transactions retain existing CAS/reauth/revocation
    # rules. Deterministic operation IDs recover a partial HTTP response safely.
    for item in result["items"]:
        command = ConsentWrite(
            operation_id=uuid5(UUID(str(body.operation_id)), item["identity_id"]),
            revision=item["consent_revision"], reason=body.reason,
            confirmed=True, state="granted", evidence=body.evidence,
            origin=body.origin, expires_at=body.expires_at,
        )
        service.save_consent(auth, integration, item["identity_id"], command)
    return {**result, "consent_saved": True, "messages_sent": 0}
