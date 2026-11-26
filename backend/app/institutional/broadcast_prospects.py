"""Explicit outbound WhatsApp onboarding for reviewed imported CRM prospects."""

import json
import re
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID, uuid4, uuid5

from fastapi import HTTPException
from pydantic import Field, model_validator

from app.institutional import broadcast_alternate_phones as alternate
from app.institutional import db
from app.institutional.auth import authorize
from app.institutional.broadcast_models import ConsentWrite
from app.institutional.channel_operations import account
from app.institutional.prospect_import import normalize, phone
from app.modules.inbox.application.state import change_control, control

PROGRAMS = {
    "logistica": "logistica portuaria y maritima",
    "aduanas": "aduanas, procesos logisticos y automatizacion",
}


class ProspectSetup(ConsentWrite):
    state: Literal["granted"] = "granted"
    program: Literal["logistica", "aduanas", "all"]
    contact_ids: list[str] = Field(min_length=1, max_length=10)
    additional_phones: dict[str, str] = Field(default_factory=dict, max_length=10)

    @model_validator(mode="after")
    def bounded_setup(self):
        self.contact_ids = [str(UUID(v)) for v in self.contact_ids]
        if len(set(self.contact_ids)) != len(self.contact_ids):
            raise ValueError("prospect_contacts_duplicate")
        additional = {str(UUID(k)): phone(v) for k, v in self.additional_phones.items()}
        if (
            set(additional) - set(self.contact_ids)
            or any(not value for value in additional.values())
            or len(set(additional.values())) != len(additional)
        ):
            raise ValueError("prospect_alternate_phone_review_required")
        self.additional_phones = additional
        expires = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
        if expires > datetime.now(timezone.utc) + timedelta(days=2):
            raise ValueError("prospect_setup_expiry_maximum_two_days")
        return self


def reviewed_contact(value, program):
    if not value:
        raise HTTPException(404, "prospect_contact_not_found")
    custom = json.loads(value["CustomValues"])
    from app.institutional.prospect_source_status import promotion_exclusion
    if promotion_exclusion(custom):
        raise HTTPException(409, "prospect_source_status_excluded")
    interests = {normalize(v) for v in custom.get("pre_programas", "").split("|")}
    if (
        value["Type"] != "Preinscrito"
        or not re.fullmatch(
            r"(?:PRE-[a-f0-9]{16}|SIIE-[a-f0-9]{32})",
            custom.get("pre_import_ref", ""),
        )
        or not any(interests)
        or (program != "all" and PROGRAMS[program] not in interests)
        or not phone(value["Phone"])
    ):
        raise HTTPException(409, "prospect_phone_program_review_required")
    return phone(value["Phone"]).removeprefix("+")


def review_all(service, auth):
    with service.tx(auth) as (c, _):
        values = db.rows(
            c, "SELECT TOP(5001) ContactId,Phone,Type,CustomValues "
            "FROM crm.Contact WHERE Type='Preinscrito' ORDER BY ContactId",
        )
        if len(values) > 5000:
            raise HTTPException(409, "prospect_import_scope_limit")
        ids = []
        for value in values:
            try:
                reviewed_contact(value, "all")
            except HTTPException:
                continue
            ids.append(str(value["ContactId"]))
        return {
            "version": "rinovaplus-whatsapp-prospects-v1", "program": "all",
            "contact_ids": ids, "review_count": len(values) - len(ids),
        }


def prior_opt_out(c, settings, identity):
    if getattr(settings, "ticket", {}).get("version") not in {
        "cbn-institutional-campaign-p8-v1", "cbn-institutional-ads-p9-v1",
        "cbn-institutional-learning-p10-v1", "cbn-institutional-operations-p11-v1",
    }:
        return False
    return bool(c.execute(
        "SELECT 1 FROM crm_campaign8.Event WHERE InstitutionId=? AND Kind='opt_out' "
        "AND JSON_VALUE(Document,'$.identity_id')=?",
        db.institution(settings), identity,
    ).fetchone())


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
    # An untouched import placeholder has no real human history. The CRM keeps
    # one conversation per contact; reuse that placeholder, never another route
    # around a real conversation or an explicit human intervention.
    if c.execute(
        "SELECT 1 FROM crm.Conversation v WHERE v.ContactId=? AND "
        "(EXISTS(SELECT 1 FROM crm.Message m WHERE m.ConversationId=v.ConversationId) "
        "OR EXISTS(SELECT 1 FROM crm_channels.ConversationControl ctrl "
        "WHERE ctrl.ConversationId=v.ConversationId AND ctrl.Epoch<>0))",
        contact_id,
    ).fetchone():
        raise HTTPException(409, "prospect_existing_history_review_required")
    placeholder = db.one(
        c, "SELECT ConversationId,ControlMode FROM crm.Conversation "
        "WHERE ContactId=?", contact_id,
    )
    identity = str(uuid4())
    if placeholder:
        conversation = str(placeholder["ConversationId"])
        previous = placeholder["ControlMode"]
        if previous != "ai":
            c.execute(
                "UPDATE crm.Conversation SET ControlMode='ai' "
                "WHERE ConversationId=? AND ControlMode=?",
                conversation, previous,
            )
            change_control(c, conversation, previous, "ai")
    else:
        conversation = str(uuid4())
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
            items, held, additional_items = [], [], []
            for contact_id in body.contact_ids:
                try:
                    planned, alternate_consent = None, None
                    if contact_id in body.additional_phones:
                        planned = alternate.plan(
                            c, service.settings, integration, contact_id,
                            body.additional_phones[contact_id], body.program,
                        )
                        if planned["IdentityId"]:
                            alternate_consent = consent(
                                c, service.settings, str(planned["IdentityId"]),
                            )
                            if (
                                alternate_consent
                                and alternate_consent["State"] == "revoked"
                            ):
                                raise HTTPException(
                                    409, "prospect_revoked_consent_review_required",
                                )
                            if prior_opt_out(
                                c, service.settings, str(planned["IdentityId"]),
                            ):
                                raise HTTPException(
                                    409, "prospect_opt_out_review_required",
                                )
                    identity = link(
                        c, service.settings, integration, contact_id, body.program,
                    )
                    old = consent(c, service.settings, identity)
                    if old and old["State"] == "revoked":
                        raise HTTPException(
                            409, "prospect_revoked_consent_review_required",
                        )
                    if prior_opt_out(c, service.settings, identity):
                        raise HTTPException(
                            409, "prospect_opt_out_review_required",
                        )
                except HTTPException as failure:
                    # All review guards run before writes. A revoked consent
                    # can only belong to an existing identity, also unchanged.
                    if body.program != "all" or failure.status_code != 409:
                        raise
                    held.append({"contact_id": contact_id, "reason": failure.detail})
                    continue
                items.append({
                    "contact_id": contact_id, "identity_id": identity,
                    "consent_revision": old["VersionNo"] if old else 0,
                    "preserve_consent": bool(
                        old and old["State"] == "granted" and old["ExpiresAt"]
                        and old["ExpiresAt"] > datetime.now(timezone.utc).replace(
                            tzinfo=None,
                        )
                    ),
                })
                if planned:
                    additional_identity = alternate.link(
                        c, service.settings, integration, planned,
                    )
                    additional_items.append({
                        "contact_id": contact_id, "identity_id": additional_identity,
                        "consent_revision": (
                            alternate_consent["VersionNo"] if alternate_consent else 0
                        ),
                        "preserve_consent": bool(
                            alternate_consent
                            and alternate_consent["State"] == "granted"
                            and alternate_consent["ExpiresAt"]
                            and alternate_consent["ExpiresAt"] > datetime.now(
                                timezone.utc,
                            ).replace(tzinfo=None)
                        ),
                    })
            result = {
                "items": items, "additional_items": additional_items,
                "held": held, "program": body.program,
            }
            db.record_operation(
                c, service.settings, actor["UserId"], str(body.operation_id),
                "broadcast.prospect_setup", integration, digest, result,
            )
            db.audit(
                c, service.settings, actor["UserId"], "broadcast.prospect_setup",
                integration, count=len(items) + len(additional_items),
                scope=body.program,
                fields=["outbound_whatsapp_route", "untouched_import_control"],
            )
    # Separate native consent transactions retain existing CAS/reauth/revocation
    # rules. Deterministic operation IDs recover a partial HTTP response safely.
    for item in [*result["items"], *result.get("additional_items", [])]:
        if item.get("preserve_consent"):
            continue
        command = ConsentWrite(
            operation_id=uuid5(UUID(str(body.operation_id)), item["identity_id"]),
            revision=item["consent_revision"], reason=body.reason,
            confirmed=True, state="granted", evidence=body.evidence,
            origin=body.origin, expires_at=body.expires_at,
        )
        service.save_consent(auth, integration, item["identity_id"], command)
    return {**result, "consent_saved": True, "messages_sent": 0}
