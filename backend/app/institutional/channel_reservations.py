"""Reuse quota only for a known pre-provider wait, never an uncertain send."""

from fastapi import HTTPException

from app.institutional.db import institution, one, uid

KNOWN_WAITS = {"broadcast_cadence_wait", "campaign_quiet_or_not_due"}


def preflight_reservation(c, settings, job):
    previous = one(
        c, "SELECT ReservationId,IntegrationId,Status,Action,Units "
        "FROM crm_channels2.QuotaReservation WHERE InstitutionId=? AND OperationId=?",
        institution(settings), job["OperationId"],
    )
    if not previous:
        return None
    operation = one(
        c, "SELECT Status,ResultCode FROM crm_channels2.ProviderOperation "
        "WHERE InstitutionId=? AND OperationId=?",
        institution(settings), job["OperationId"],
    )
    if not (
        previous["Status"] == "released" and previous["Action"] == "outbound"
        and previous["Units"] == 1
        and uid(str(previous["IntegrationId"])) == uid(str(job["IntegrationId"]))
        and job.get("State") == "queued" and not job.get("ExternalId")
        and not job.get("LeaseId") and not job.get("LeaseUntil")
        and operation and operation["Status"] == "pending"
        and operation["ResultCode"] in KNOWN_WAITS
    ):
        raise HTTPException(409, "outbound_reservation_review_required")
    return uid(str(previous["ReservationId"]))


def restore(c, settings, reservation):
    if c.execute(
        "UPDATE crm_channels2.QuotaReservation SET Status='reserved',"
        "DayUtc=CONVERT(date,SYSUTCDATETIME()),UpdatedAt=SYSUTCDATETIME() "
        "WHERE InstitutionId=? AND ReservationId=? AND Status='released'",
        institution(settings), reservation,
    ).rowcount != 1:
        raise HTTPException(409, "outbound_reservation_review_required")
