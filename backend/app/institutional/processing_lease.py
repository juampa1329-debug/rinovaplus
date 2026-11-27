"""Bounded renewal of a worker's own, still-live generation lease."""

import math
from time import monotonic

from fastapi import HTTPException

from app.institutional.db import institution
from app.institutional.store import transaction


def renew(settings, operation, lease, deadline):
    remaining = math.floor(deadline - monotonic())
    if remaining < 30:
        raise HTTPException(409, "ai_processing_deadline")
    with transaction(settings, True, anonymous=True) as c:
        c.execute(
            "UPDATE crm_channels2.ProviderOperation SET LeaseUntil=DATEADD(second,?,SYSUTCDATETIME()) "
            "WHERE InstitutionId=? AND OperationId=? AND Status='running' AND LeaseId=? "
            "AND LeaseUntil>SYSUTCDATETIME()",
            min(180, remaining), institution(settings), operation, lease,
        )
        if c.rowcount != 1:
            raise HTTPException(409, "gemini_whatsapp_claim_changed")
