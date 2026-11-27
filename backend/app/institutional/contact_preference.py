"""Canonical no-contact status and explicit operator-confirmed opt-out."""

from fastapi import HTTPException, Query, Request
from typing import Literal
from uuid import uuid4
from pydantic import Field, field_validator

from app.institutional import db
from app.institutional.models import Strict
from app.institutional.auth import authorize
from app.institutional.store import transaction
from app.sql_workspace import Identifier


class NoContactWrite(Strict):
    operationId: Identifier
    reason: str = Field(min_length=3, max_length=400)
    confirmed: Literal[True]

    @field_validator("reason")
    @classmethod
    def reason_text(cls, value):
        value = value.strip()
        if len(value) < 3 or any(ord(ch) < 32 for ch in value):
            raise ValueError("no_contact_reason_required")
        return value

    @field_validator("confirmed", mode="before")
    @classmethod
    def explicit_confirmation(cls, value):
        if value is not True:
            raise ValueError("no_contact_confirmation_required")
        return value


def record_no_contact(c, s, contact, body, actor):
    from app.institutional.workspace import members, primary, read_contact
    from app.institutional.campaigns import event, key
    from app.institutional.broadcasts import consent

    contact = db.uid(contact)
    if primary(c, contact) != contact:
        raise HTTPException(409, "canonical_contact_required")
    read_contact(c, contact)
    digest, prior = db.replay(c, s, actor, body.operationId, "workspace.no_contact", contact, body.model_dump())
    if prior is not None:
        return prior
    ids = members(c, contact)
    slots = ",".join("?" for _ in ids)
    identities = db.rows(c, "SELECT IdentityId,IntegrationId FROM crm_channels2.ExternalIdentity WHERE InstitutionId=? AND ContactId IN (" + slots + ")",
                         db.institution(s), *ids)
    if not identities:
        raise HTTPException(409, "contact_identity_not_found")
    for identity in identities:
        identity_id = db.uid(str(identity["IdentityId"]))
        event(c, s, "opt_out", {"identity_id": identity_id, "source": "operator_confirmed_request", "reason": body.reason},
              actor=actor, source=key("manual-no-contact", body.operationId, identity_id))
        previous = consent(c, s, identity_id)
        if not previous or previous["State"] != "revoked":
            c.execute("INSERT crm_broadcast7.Consent(InstitutionId,ConsentId,IntegrationId,IdentityId,VersionNo,State,Evidence,Origin,ExpiresAt,ActorId,OperationId) VALUES(?,?,?,?,?,'revoked',?,'operator_confirmed_opt_out',NULL,?,?)",
                      db.institution(s), str(uuid4()), identity["IntegrationId"], identity_id,
                      (previous["VersionNo"] if previous else 0) + 1, body.reason, actor, body.operationId)
        # No uncertain/sending job is repeated or rewritten. Stop only work
        # that has not started, through the existing channel outbox.
        c.execute("UPDATE crm_channels2.ProviderOperation SET Status='failed',ResultCode='contact_no_contact' WHERE InstitutionId=? AND Status='pending' AND OperationId IN (SELECT q.OperationId FROM crm_channels2.SendJob q JOIN crm_channels2.MessageRoute r ON r.InstitutionId=q.InstitutionId AND r.MessageId=q.MessageId WHERE q.InstitutionId=? AND r.IdentityId=? AND q.State='queued')",
                  db.institution(s), db.institution(s), identity_id)
        c.execute("UPDATE crm_channels2.SendJob SET State='cancelled',LastErrorCode='contact_no_contact',CompletedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND State='queued' AND MessageId IN (SELECT MessageId FROM crm_channels2.MessageRoute WHERE InstitutionId=? AND IdentityId=?)",
                  db.institution(s), db.institution(s), identity_id)
        c.execute("UPDATE crm_channels2.ProviderOperation SET Status='failed',ResultCode='contact_no_contact' WHERE InstitutionId=? AND Status='pending' AND OperationId IN (SELECT q.OperationId FROM crm_channels2.SendJob q JOIN crm_broadcast7.Recipient r ON r.InstitutionId=q.InstitutionId AND r.CurrentQueueId=q.QueueId WHERE q.InstitutionId=? AND r.IdentityId=? AND q.State='queued')",
                  db.institution(s), db.institution(s), identity_id)
        c.execute("UPDATE crm_channels2.SendJob SET State='cancelled',LastErrorCode='contact_no_contact',CompletedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND State='queued' AND QueueId IN (SELECT CurrentQueueId FROM crm_broadcast7.Recipient WHERE InstitutionId=? AND IdentityId=?)",
                  db.institution(s), db.institution(s), identity_id)
        c.execute("UPDATE crm_broadcast7.Recipient SET State='cancelled',LastError='contact_no_contact' WHERE InstitutionId=? AND IdentityId=? AND State='prepared'",
                  db.institution(s), identity_id)
    c.execute("UPDATE crm.Conversation SET State='closed',UpdatedAt=SYSUTCDATETIME() WHERE ContactId IN (" + slots + ")", *ids)
    c.execute("UPDATE crm_workspace.State SET Revision=Revision+1 WHERE StateId=1")
    result = {"no_contact": True, "closed": True, "identity_count": len(identities)}
    db.record_operation(c, s, actor, body.operationId, "workspace.no_contact", contact, digest, result)
    db.audit(c, s, actor, "workspace.no_contact", contact, count=len(identities), reason="operator_confirmed_request")
    return result


def blocked(c, s, contact):
    return bool(c.execute(
        "SELECT 1 WHERE EXISTS(SELECT 1 FROM crm_strategy.EvaluationPlan e "
        "JOIN crm.Conversation v ON v.ConversationId=e.ConversationId "
        "LEFT JOIN crm_workspace.Merge g ON g.SourceContactId=v.ContactId AND g.Active=1 "
        "WHERE COALESCE(g.TargetContactId,v.ContactId)=? AND JSON_VALUE(e.DocumentJson,'$.noContact')='true') "
        "OR EXISTS(SELECT 1 FROM crm_campaign8.Event e "
        "JOIN crm_channels2.ExternalIdentity i ON i.InstitutionId=e.InstitutionId "
        "AND LOWER(CONVERT(varchar(36),i.IdentityId))=JSON_VALUE(e.Document,'$.identity_id') "
        "LEFT JOIN crm_workspace.Merge g ON g.SourceContactId=i.ContactId AND g.Active=1 "
        "WHERE e.InstitutionId=? AND e.Kind='opt_out' AND COALESCE(g.TargetContactId,i.ContactId)=? "
        "AND NOT EXISTS(SELECT 1 FROM crm_broadcast7.Consent grantor WHERE grantor.InstitutionId=i.InstitutionId "
        "AND grantor.IdentityId=i.IdentityId AND grantor.State='granted' AND grantor.CreatedAt>e.CreatedAt))",
        contact, db.institution(s), contact).fetchone())


def install(app, s):
    @app.post("/api/institution/workspace/contact-preference/{contact_id}")
    def write(request: Request, contact_id: str, body: NoContactWrite):
        with transaction(s, True, permission="crm.write") as c:
            actor = authorize(c, s, request.state.authority, "crm.write")
            return record_no_contact(c, s, contact_id, body, db.uid(str(actor["UserId"])))

    @app.get("/api/institution/workspace/contact-preferences")
    def listing(request: Request, q: str = Query("", max_length=120),
                offset: int = Query(0, ge=0, le=1000000)):
        with transaction(s, anonymous=True) as c:
            authorize(c, s, request.state.authority, "crm.read")
            return no_contact_list(c, s, q, offset)

    @app.get("/api/institution/workspace/contact-preference/{contact_id}")
    def read(request: Request, contact_id: str):
        with transaction(s, anonymous=True) as c:
            authorize(c, s, request.state.authority, "crm.read")
            contact = db.uid(contact_id)
            if not c.execute("SELECT 1 FROM crm.Contact WHERE ContactId=?", contact).fetchone():
                raise HTTPException(404, "contact_not_found")
            return {"no_contact": blocked(c, s, contact), "read_only": True,
                    "scope": "canonical_contact", "marketing_consent_unchanged": True}


def no_contact_list(c, s, q="", offset=0):
    """A live list over persisted requests; never writes a tag or grants consent."""
    query = """
        WITH base AS (
          SELECT COALESCE(g.TargetContactId,v.ContactId) AS ContactId
          FROM crm_strategy.EvaluationPlan e
          JOIN crm.Conversation v ON v.ConversationId=e.ConversationId
          LEFT JOIN crm_workspace.Merge g ON g.SourceContactId=v.ContactId AND g.Active=1
          WHERE JSON_VALUE(e.DocumentJson,'$.noContact')='true'
          UNION
          SELECT COALESCE(g.TargetContactId,i.ContactId) AS ContactId
          FROM crm_campaign8.Event e
          JOIN crm_channels2.ExternalIdentity i ON i.InstitutionId=e.InstitutionId
            AND LOWER(CONVERT(varchar(36),i.IdentityId))=JSON_VALUE(e.Document,'$.identity_id')
          LEFT JOIN crm_workspace.Merge g ON g.SourceContactId=i.ContactId AND g.Active=1
          WHERE e.InstitutionId=? AND e.Kind='opt_out'
            AND NOT EXISTS(SELECT 1 FROM crm_broadcast7.Consent grantor
              WHERE grantor.InstitutionId=i.InstitutionId AND grantor.IdentityId=i.IdentityId
              AND grantor.State='granted' AND grantor.CreatedAt>e.CreatedAt)
        )
        SELECT p.ContactId,p.Name,p.Phone,p.Stage FROM base d
        JOIN crm.Contact p ON p.ContactId=d.ContactId
        WHERE (?='' OR p.Name LIKE ?
          OR p.Phone LIKE ?)
        ORDER BY p.Name,p.ContactId OFFSET ? ROWS FETCH NEXT 26 ROWS ONLY
    """
    search = "%" + q.strip().replace("%", "[%]").replace("_", "[_]") + "%"
    values = db.rows(c, query, db.institution(s), q.strip(), search, search, offset)
    return {"items": [{"id": str(v["ContactId"]), "name": v["Name"],
                       "phone": v["Phone"], "stage": v["Stage"]} for v in values[:25]],
            "has_more": len(values) > 25, "offset": offset, "read_only": True}
