"""Account-scoped recipient route selection without weakening contact deduplication."""

import json

from fastapi import HTTPException

from app.institutional import db


def validate_selection(c, settings, document):
    filters = document["filters"]
    identities = {str(v).lower() for v in filters.get("identity_ids", [])}
    contacts = {str(v).lower() for v in filters.get("contact_ids", [])}
    if not identities:
        return
    selected = db.rows(
        c,
        "SELECT IdentityId,ContactId FROM crm_channels2.ExternalIdentity "
        "WHERE InstitutionId=? AND IntegrationId=? AND IdentityId IN "
        "(SELECT CONVERT(uniqueidentifier,value) FROM OPENJSON(?))",
        db.institution(settings),
        document["integration_id"],
        json.dumps(sorted(identities)),
    )
    if (
        {str(row["IdentityId"]).lower() for row in selected} != identities
        or any(str(row["ContactId"]).lower() not in contacts for row in selected)
        or len({str(row["ContactId"]).lower() for row in selected}) != len(selected)
    ):
        raise HTTPException(409, "broadcast_identity_selection_review_required")
