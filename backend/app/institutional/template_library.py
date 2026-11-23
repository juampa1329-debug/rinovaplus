"""Recoverable removal from the CRM library, preserving provider and send history."""

import json

from fastapi import HTTPException

from app.institutional import broadcast_templates as templates
from app.institutional.broadcast_models import Command
from app.institutional.channel_operations import account
from app.institutional.db import (
    audit,
    institution,
    record_operation,
    replay,
)


class LibraryWrite(Command):
    removed: bool
    confirmed: bool = False


def change(service, auth, key, body):
    if not body.confirmed:
        raise HTTPException(409, "broadcast_library_confirmation_required")
    with service.tx(auth, True) as (c, actor):
        digest, prior = replay(
            c,
            service.settings,
            actor["UserId"],
            str(body.operation_id),
            "broadcast.template_library",
            key,
            body.model_dump(mode="json"),
        )
        if prior:
            return prior
        old = templates.latest(c, service.settings, key)
        if old["VersionNo"] != body.revision:
            raise HTTPException(409, "revision_conflict")
        if (
            body.removed
            and c.execute(
                "SELECT 1 FROM crm_broadcast7.Campaign "
                "WHERE InstitutionId=? AND TemplateId=?",
                institution(service.settings),
                key,
            ).fetchone()
        ):
            raise HTTPException(409, "broadcast_template_still_in_campaign")
        item = account(c, service.settings, str(old["IntegrationId"]))
        credential = {"SecretId": old["CredentialId"]} if old["CredentialId"] else None
        result = templates.append(
            c,
            service.settings,
            item,
            {
                "id": old["ProviderId"],
                "name": old["Name"],
                "language": old["Language"],
                "category": old["Category"],
                "status": old["ProviderStatus"],
                "components": json.loads(old["Definition"]),
                "quality_score": json.loads(old["ProviderMetadata"]).get(
                    "quality_score", ""
                ),
                "rejection_reason": json.loads(old["ProviderMetadata"]).get(
                    "rejection_reason", ""
                ),
                "allow_category_change": json.loads(old["ProviderMetadata"]).get(
                    "allow_category_change", True
                ),
            },
            credential,
            old["Origin"],
            key=key,
            paused=True,
            observed=old["ObservedAt"],
            removed=body.removed,
        )
        result["removed"] = body.removed
        record_operation(
            c,
            service.settings,
            actor["UserId"],
            str(body.operation_id),
            "broadcast.template_library",
            key,
            digest,
            result,
        )
        audit(
            c,
            service.settings,
            actor["UserId"],
            "broadcast.template_library",
            key,
            fields=["library_removed"],
            version=result["version"],
            reason="removed" if body.removed else "restored_in_pause",
        )
        return result
