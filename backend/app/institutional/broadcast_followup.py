"""Move CRM stage only after a real Meta sent/delivered/read receipt."""

import json
from uuid import UUID, uuid5

from fastapi import HTTPException

from app.institutional import db
from app.modules.crm_configuration.application.service import read_configuration


def observe(c, settings, queue, status):
    if status not in {"sent", "delivered", "read"}:
        return False
    from app.institutional.broadcast_dispatch import record
    from app.institutional.broadcasts import authority, current

    recipient = record(c, settings, str(queue))
    if not recipient:
        return False
    snapshot = json.loads(recipient["Snapshot"])
    target = snapshot.get("sent_stage", "")
    expected = snapshot.get("audience_profile", {}).get("stage", "")
    contact = snapshot.get("canonical_contact")
    if not target or not expected or not contact:
        return False
    operation = str(uuid5(UUID(str(recipient["RecipientId"])), "sent-crm-stage-v1"))
    if c.execute(
        "SELECT 1 FROM crm_access.Operation WHERE InstitutionId=? "
        "AND OperationId=? AND Action='broadcast.followup_stage'",
        db.institution(settings), operation,
    ).fetchone():
        return False
    campaign = current(c, settings, str(recipient["CampaignId"]))
    try:
        actor = authority(c, settings, campaign)
    except HTTPException:
        return False
    if "crm.write" not in json.loads(actor["Actions"]):
        return False
    configuration, _ = read_configuration(c, foundation=True)
    if not any(v.active and v.label == target for v in configuration.stages):
        return False
    changed = False
    if not c.execute(
        "SELECT 1 FROM crm_workspace.Merge WHERE SourceContactId=? AND Active=1",
        contact,
    ).fetchone() and expected != target:
        changed = c.execute(
            "UPDATE crm.Contact SET Stage=?,UpdatedAt=SYSUTCDATETIME() "
            "WHERE ContactId=? AND Stage=?",
            target, contact, expected,
        ).rowcount == 1
    if changed:
        c.execute("UPDATE crm_workspace.State SET Revision=Revision+1 WHERE StateId=1")
    result = {
        "changed": changed,
        "reason": "sent_receipt" if changed else "stage_preserved",
    }
    db.record_operation(
        c, settings, actor["UserId"], operation, "broadcast.followup_stage", contact,
        db.bound_hash(settings, snapshot, "broadcast.followup_stage"), result,
    )
    db.audit(
        c, settings, actor["UserId"], "broadcast.followup_stage", contact,
        fields=["stage"] if changed else [], reason=result["reason"],
    )
    return changed
