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
    return c.native(
        "SELECT rinovaplus_crm.lease_outbound(%s,%s,%s,%s)",
        institution, queue_id, lease_id, reservation,
    ).fetchval()


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
