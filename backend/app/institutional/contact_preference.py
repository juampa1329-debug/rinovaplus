"""Read-only, canonical no-contact status from authenticated requests and reviews."""

from fastapi import HTTPException, Request

from app.institutional import db
from app.institutional.auth import authorize
from app.institutional.store import transaction


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
    @app.get("/api/institution/workspace/contact-preference/{contact_id}")
    def read(request: Request, contact_id: str):
        with transaction(s, anonymous=True) as c:
            authorize(c, s, request.state.authority, "crm.read")
            contact = db.uid(contact_id)
            if not c.execute("SELECT 1 FROM crm.Contact WHERE ContactId=?", contact).fetchone():
                raise HTTPException(404, "contact_not_found")
            return {"no_contact": blocked(c, s, contact), "read_only": True,
                    "scope": "canonical_contact", "marketing_consent_unchanged": True}
