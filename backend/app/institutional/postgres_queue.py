"""PostgreSQL queue bindings. The caller owns the transaction and authorization."""

def one(c, sql, *params):
    c.native(sql, *params)
    row = c.fetchone()
    return dict(zip((col[0] for col in c.description), row, strict=True)) if row else None


def receipt(c, institution):
    return one(c, """
        SELECT r.*,e.provider AS Provider
        FROM rinovaplus_crm.next_webhook_receipt(%s) r
        JOIN rinovaplus_crm.crmcanalinstitucionalwebhook e USING (institutionid,endpointid)
    """, institution)


def event(c, institution):
    return one(c, "SELECT * FROM rinovaplus_crm.next_webhook_event(%s)", institution)


def media(c, institution):
    return one(c, "SELECT * FROM rinovaplus_crm.next_media(%s)", institution)


def outbound(c, institution):
    return one(c, "SELECT * FROM rinovaplus_crm.next_outbound(%s)", institution)


def lease(c, institution, queue_id, lease_id, reservation):
    claimed = c.native(
        "SELECT rinovaplus_crm.lease_outbound(%s,%s,%s,%s)",
        institution, queue_id, lease_id, reservation,
    ).fetchval()
    if not claimed:
        return False
    # Existing stored claim grants 60 s. Bound the live dispatch to 180 s so
    # current authority/context checks, typing and the provider's 12 s request
    # can finish under contention. Same nonexpired lease only; no resurrection,
    # retry, extra attempt, quota change or migration of the frozen SQL unit.
    renewed = c.native("""
        WITH active AS (
          UPDATE rinovaplus_crm.crmcanalinstitucionalenviotrabajo q
          SET leaseuntil=(statement_timestamp() AT TIME ZONE 'UTC')+interval '180 seconds'
          WHERE q.institutionid=%s AND q.queueid=%s AND q.leaseid=%s
            AND q.state='sending' AND q.leaseuntil>statement_timestamp() AT TIME ZONE 'UTC'
            AND EXISTS(SELECT 1 FROM rinovaplus_crm.crmcanalinstitucionaloperacionproveedor o
              WHERE o.institutionid=q.institutionid AND o.integrationid=q.integrationid
                AND o.operationid=q.operationid AND o.status='running' AND o.leaseid=q.leaseid
                AND o.leaseuntil>statement_timestamp() AT TIME ZONE 'UTC')
          RETURNING q.institutionid,q.integrationid,q.operationid,q.leaseid,q.leaseuntil
        )
        UPDATE rinovaplus_crm.crmcanalinstitucionaloperacionproveedor o
        SET leaseuntil=active.leaseuntil FROM active
        WHERE o.institutionid=active.institutionid AND o.integrationid=active.integrationid
          AND o.operationid=active.operationid AND o.status='running' AND o.leaseid=active.leaseid
        RETURNING true
    """, institution, queue_id, lease_id).fetchval()
    if not renewed:
        from fastapi import HTTPException

        raise HTTPException(409, "send_lease_lost")
    return True


def expire(c, institution):
    for _ in range(20):
        if not c.native("SELECT rinovaplus_crm.expire_one_outbound(%s)", institution).fetchval():
            break


def counts(c, institution):
    definitions = [
        "webhook_receipts", "webhook_events", "outbound", "provider_operations",
        "media", "agent_requests", "broadcasts", "campaign_enrollments",
    ]
    result = {item: {} for item in definitions}
    for label, status, count in c.native(
        "SELECT * FROM rinovaplus_crm.queue_counts(%s)", institution
    ).fetchall():
        result[label][status] = count
    return result
