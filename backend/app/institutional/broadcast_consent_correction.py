"""Audited correction of an initial clerical revocation; never grants sending."""

from uuid import uuid4

from fastapi import HTTPException
from pydantic import Field

from app.institutional import db
from app.institutional.auth import authorize
from app.institutional.broadcast_models import Review

UNREGISTERED_ORIGIN = "administrative_unregistered_correction_v1"


class ConsentRestore(Review):
    evidence: str = Field(min_length=1, max_length=1000)


def project(value):
    if (
        value
        and value["State"] == "revoked"
        and value.get("Origin") == UNREGISTERED_ORIGIN
    ):
        return {**value, "State": "unregistered"}
    return value


def restore(service, auth, integration, identity, body):
    from app.institutional.broadcast_prospects import prior_opt_out
    from app.institutional.broadcasts import consent

    with service.tx(auth, True, recent=True) as (c, actor):
        authorize(c, service.settings, auth, "inbox.write")
        if actor["RoleKey"] != "owner":
            raise HTTPException(403, "permission_denied")
        if (
            not body.confirmed
            or not body.evidence.strip()
            or "\x00" in body.evidence
            or len(body.evidence.encode("utf-16-le")) > 2000
        ):
            raise HTTPException(422, "consent_evidence_required")
        resource = integration + "/" + identity
        digest, prior = db.replay(
            c,
            service.settings,
            actor["UserId"],
            str(body.operation_id),
            "broadcast.consent_restore_unregistered",
            resource,
            body.model_dump(mode="json"),
        )
        if prior:
            return prior
        if not c.execute(
            "SELECT 1 FROM crm_channels2.ExternalIdentity "
            "WHERE InstitutionId=? AND IntegrationId=? AND IdentityId=?",
            db.institution(service.settings),
            integration,
            identity,
        ).fetchone():
            raise HTTPException(404, "broadcast_identity_not_found")
        previous = consent(c, service.settings, identity)
        if not previous or previous["VersionNo"] != body.revision:
            raise HTTPException(409, "revision_conflict")
        if (
            previous["State"] != "revoked"
            or previous["VersionNo"] != 1
            or str(previous["ActorId"]).lower() != actor["UserId"].lower()
            or prior_opt_out(c, service.settings, identity)
        ):
            raise HTTPException(409, "consent_initial_clerical_correction_required")
        # Preserve the original row and all cancellations. The physical revoked
        # state also fails closed for older readers; only this marker projects
        # the correction as unregistered. No job or recipient is resumed.
        c.execute(
            "INSERT crm_broadcast7.Consent(InstitutionId,ConsentId,IntegrationId,"
            "IdentityId,VersionNo,State,Evidence,Origin,ExpiresAt,ActorId,OperationId) "
            "VALUES(?,?,?,?,?,'revoked',?,?,NULL,?,?)",
            db.institution(service.settings),
            str(uuid4()),
            integration,
            identity,
            previous["VersionNo"] + 1,
            body.evidence.strip(),
            UNREGISTERED_ORIGIN,
            actor["UserId"],
            str(body.operation_id),
        )
        result = {
            "saved": True,
            "version": 2,
            "state": "unregistered",
            "sending_enabled": False,
        }
        db.record_operation(
            c,
            service.settings,
            actor["UserId"],
            str(body.operation_id),
            "broadcast.consent_restore_unregistered",
            resource,
            digest,
            result,
        )
        db.audit(
            c,
            service.settings,
            actor["UserId"],
            "broadcast.consent_restore_unregistered",
            identity,
            version=2,
            reason=body.reason,
        )
        return result
