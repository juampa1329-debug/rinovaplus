BEGIN;
DO $$ BEGIN
  IF current_database() NOT IN ('rinovaplus','rinovaplus_rehearsal')
     OR to_regclass('rinovaplus_crm.crmcontacto') IS NULL
  THEN RAISE EXCEPTION 'Unexpected CRM PostgreSQL target'; END IF;
END $$;

CREATE FUNCTION rinovaplus_crm.contact_page(
    institution uuid, query_text text, page_size integer, page_offset integer
) RETURNS TABLE (id uuid, name text, phone text, city text, stage text, program_id integer)
LANGUAGE sql STABLE SET search_path = pg_catalog, rinovaplus_crm AS $$
    SELECT p.contactid, p.name, p.phone, p.city, p.stage, p.programid
    FROM crmcontacto p
    WHERE EXISTS (SELECT 1 FROM crmcanalinstitucionalcontexto c
                  WHERE c.contextid = 1 AND c.institutionid = $1)
      AND (coalesce($2, '') = '' OR
           strpos(lower(p.name COLLATE "default"), lower($2 COLLATE "default")) > 0 OR
           strpos(p.phone COLLATE "C", $2 COLLATE "C") > 0)
    ORDER BY p.updatedat DESC, p.contactid
    LIMIT least(greatest(coalesce($3, 50), 1), 100)
    OFFSET greatest(coalesce($4, 0), 0)
$$;

CREATE FUNCTION rinovaplus_crm.message_page(institution uuid, conversation uuid, before_sequence bigint)
RETURNS TABLE (id uuid, body text, direction text, created_at timestamp, sequence bigint)
LANGUAGE sql STABLE SET search_path = pg_catalog, rinovaplus_crm AS $$
    SELECT m.messageid, m.body, m.direction, m.createdat, m.sequence
    FROM crmmensaje m
    WHERE m.conversationid = $2 AND ($3 IS NULL OR m.sequence < $3)
      AND EXISTS (SELECT 1 FROM crmcanalinstitucionalcontexto c
                  WHERE c.contextid = 1 AND c.institutionid = $1)
    ORDER BY m.sequence DESC
    LIMIT 51
$$;

CREATE FUNCTION rinovaplus_crm.queue_counts(institution uuid)
RETURNS TABLE (queue text, state text, rows bigint)
LANGUAGE sql STABLE SET search_path = pg_catalog, rinovaplus_crm AS $$
    SELECT 'webhook_receipts', status, count(*) FROM crmcanalinstitucionalwebhookrecepcion WHERE institutionid=$1 GROUP BY status
    UNION ALL SELECT 'webhook_events', status, count(*) FROM crmcanalinstitucionalwebhookevento WHERE institutionid=$1 GROUP BY status
    UNION ALL SELECT 'outbound', state, count(*) FROM crmcanalinstitucionalenviotrabajo WHERE institutionid=$1 GROUP BY state
    UNION ALL SELECT 'provider_operations', status, count(*) FROM crmcanalinstitucionaloperacionproveedor WHERE institutionid=$1 GROUP BY status
    UNION ALL SELECT 'media', state, count(*) FROM crmcanaloperacionarchivo WHERE institutionid=$1 GROUP BY state
    UNION ALL SELECT 'agent_requests', state, count(*) FROM crmagenteoperacionsolicitud WHERE institutionid=$1 GROUP BY state
    UNION ALL SELECT 'broadcasts', state, count(*) FROM crmmasivocampana WHERE institutionid=$1 GROUP BY state
    UNION ALL SELECT 'campaign_enrollments', state, count(*) FROM crmflujoinscripcion WHERE institutionid=$1 GROUP BY state
$$;

-- Keep the transaction open through processing or until a durable lease is committed.
CREATE FUNCTION rinovaplus_crm.next_webhook_receipt(institution uuid)
RETURNS SETOF rinovaplus_crm.crmcanalinstitucionalwebhookrecepcion
LANGUAGE sql VOLATILE SET search_path = pg_catalog, rinovaplus_crm AS $$
    SELECT r.* FROM crmcanalinstitucionalwebhookrecepcion r
    JOIN crmcanalinstitucionalwebhook e USING (institutionid, endpointid)
    WHERE r.institutionid=$1 AND r.status='queued' AND r.authentication='verified'
    ORDER BY r.receivedat, r.receiptid LIMIT 1 FOR UPDATE OF r SKIP LOCKED
$$;

CREATE FUNCTION rinovaplus_crm.next_webhook_event(institution uuid)
RETURNS SETOF rinovaplus_crm.crmcanalinstitucionalwebhookevento
LANGUAGE sql VOLATILE SET search_path = pg_catalog, rinovaplus_crm AS $$
    SELECT e.* FROM crmcanalinstitucionalwebhookevento e
    JOIN crmcanalinstitucionalintegracion i USING (institutionid, integrationid)
    JOIN crmcanalinstitucionalwebhook p ON p.institutionid=e.institutionid AND p.endpointid=e.endpointid
    WHERE e.institutionid=$1 AND e.status='queued' AND i.requestedstatus='connected'
      AND i.verifiedstatus='verified' AND p.isactive=1
    ORDER BY e.createdat, e.eventid LIMIT 1 FOR UPDATE OF e SKIP LOCKED
$$;

CREATE FUNCTION rinovaplus_crm.next_media(institution uuid)
RETURNS SETOF rinovaplus_crm.crmcanaloperacionarchivo
LANGUAGE sql VOLATILE SET search_path = pg_catalog, rinovaplus_crm AS $$
    SELECT m.* FROM crmcanaloperacionarchivo m
    JOIN crmcanalinstitucionalintegracion i USING (institutionid, integrationid)
    WHERE m.institutionid=$1 AND m.sourcekind='provider' AND m.state='pending'
      AND i.requestedstatus='connected' AND i.verifiedstatus='verified'
    ORDER BY m.createdat, m.mediaid LIMIT 1 FOR UPDATE OF m SKIP LOCKED
$$;

CREATE FUNCTION rinovaplus_crm.next_outbound(institution uuid)
RETURNS SETOF rinovaplus_crm.crmcanalinstitucionalenviotrabajo
LANGUAGE sql VOLATILE SET search_path = pg_catalog, rinovaplus_crm AS $$
    SELECT q.* FROM crmcanalinstitucionalenviotrabajo q
    WHERE q.institutionid=$1 AND q.state='queued'
      AND q.dueat<=statement_timestamp() AT TIME ZONE 'UTC'
    ORDER BY q.dueat, q.queueid LIMIT 1 FOR UPDATE OF q SKIP LOCKED
$$;

-- Called after the service authorizes the candidate and reserves its quota.
CREATE FUNCTION rinovaplus_crm.lease_outbound(institution uuid, queue_id uuid, lease_id uuid, reservation_id uuid)
RETURNS boolean LANGUAGE plpgsql VOLATILE SET search_path = pg_catalog, rinovaplus_crm AS $$
DECLARE
    job crmcanalinstitucionalenviotrabajo%ROWTYPE;
    expires timestamp := (statement_timestamp() AT TIME ZONE 'UTC') + interval '60 seconds';
BEGIN
    IF $3 IS NULL OR $4 IS NULL THEN RETURN false; END IF;
    SELECT * INTO job FROM crmcanalinstitucionalenviotrabajo q
      WHERE q.institutionid=$1 AND q.queueid=$2 AND q.state='queued'
        AND q.dueat<=statement_timestamp() AT TIME ZONE 'UTC' FOR UPDATE SKIP LOCKED;
    IF NOT FOUND THEN RETURN false; END IF;
    PERFORM 1 FROM crmcanalinstitucionalcuotareserva r
      WHERE r.institutionid=$1 AND r.reservationid=$4 AND r.operationid=job.operationid
        AND r.integrationid=job.integrationid AND r.status='reserved'
      FOR UPDATE;
    IF NOT FOUND THEN RETURN false; END IF;
    UPDATE crmcanalinstitucionaloperacionproveedor o
      SET status='running', leaseid=$3, leaseuntil=expires,
          leaseversion=o.leaseversion+1, attempts=o.attempts+1
      WHERE o.institutionid=$1 AND o.operationid=job.operationid
        AND o.integrationid=job.integrationid AND o.status='pending';
    IF NOT FOUND THEN RETURN false; END IF;
    UPDATE crmcanalinstitucionalenviotrabajo q
      SET state='sending', leaseid=$3, leaseuntil=expires, reservationid=$4,
          leaseversion=q.leaseversion+1, attempts=q.attempts+1
      WHERE q.institutionid=$1 AND q.queueid=$2;
    IF job.messageid IS NOT NULL THEN
        UPDATE crmcanalinstitucionalrutamensaje m SET startedat=statement_timestamp() AT TIME ZONE 'UTC'
          WHERE m.institutionid=$1 AND m.messageid=job.messageid AND m.queueid=$2;
    END IF;
    RETURN true;
END $$;

-- An expired provider effect becomes uncertain for reconciliation. Preserve quota fencing.
CREATE FUNCTION rinovaplus_crm.expire_one_outbound(institution uuid)
RETURNS boolean LANGUAGE plpgsql VOLATILE SET search_path = pg_catalog, rinovaplus_crm AS $$
DECLARE job crmcanalinstitucionalenviotrabajo%ROWTYPE;
BEGIN
    SELECT * INTO job FROM crmcanalinstitucionalenviotrabajo q
      WHERE q.institutionid=$1 AND q.state='sending'
        AND q.leaseuntil<statement_timestamp() AT TIME ZONE 'UTC'
      ORDER BY q.leaseuntil, q.queueid LIMIT 1 FOR UPDATE SKIP LOCKED;
    IF NOT FOUND THEN RETURN false; END IF;
    UPDATE crmcanalinstitucionalcuotareserva r
      SET status='uncertain', updatedat=statement_timestamp() AT TIME ZONE 'UTC'
      WHERE r.institutionid=$1 AND r.reservationid=job.reservationid
        AND r.operationid=job.operationid AND r.status='reserved';
    UPDATE crmcanalinstitucionaloperacionproveedor o
      SET status='uncertain', resultcode='send_lease_expired', leaseid=NULL, leaseuntil=NULL
      WHERE o.institutionid=$1 AND o.operationid=job.operationid AND o.status='running'
        AND o.leaseid=job.leaseid;
    IF NOT FOUND THEN RAISE EXCEPTION 'Outbound lease disagreement'; END IF;
    UPDATE crmcanalinstitucionalenviotrabajo q
      SET state='uncertain', lasterrorcode='send_lease_expired', leaseid=NULL, leaseuntil=NULL
      WHERE q.institutionid=$1 AND q.queueid=job.queueid;
    RETURN true;
END $$;

REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA rinovaplus_crm FROM PUBLIC;
COMMIT;
