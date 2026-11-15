-- Run on the PostgreSQL copy. Synthetic records are always rolled back.
BEGIN;
SET LOCAL search_path = pg_catalog, rinovaplus_crm;
SET LOCAL lock_timeout = '2s';
SET LOCAL statement_timeout = '20s';

DO $$
DECLARE
    inst uuid;
    person uuid := gen_random_uuid();
    thread_id uuid := gen_random_uuid();
    msg uuid := gen_random_uuid();
    app_id uuid := gen_random_uuid();
    integration_id uuid := gen_random_uuid();
    comment_id uuid := gen_random_uuid();
    operation_id uuid := gen_random_uuid();
    job_id uuid := gen_random_uuid();
    quota_id uuid := gen_random_uuid();
    lease uuid := gen_random_uuid();
    now_utc timestamp := statement_timestamp() AT TIME ZONE 'UTC';
    token_before bytea;
    number_tables integer;
    number_fks integer;
    count_mismatches integer := 0;
    total_rows bigint := 0;
    source_record record;
    actual_rows bigint;
BEGIN
    IF current_database() NOT IN ('rinovaplus', 'rinovaplus_rehearsal') THEN
        RAISE EXCEPTION 'Unexpected CRM smoke target';
    END IF;
    SELECT count(*) INTO number_tables FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
      WHERE n.nspname='rinovaplus_crm' AND c.relkind='r';
    SELECT count(*) INTO number_fks FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace
      WHERE n.nspname='rinovaplus_crm' AND c.contype='f';
    IF number_tables<>155 OR number_fks<>298 THEN RAISE EXCEPTION 'Wrong typed catalog'; END IF;
    FOR source_record IN
        SELECT entry.key AS name, coalesce((entry.value->>'rows')::bigint,0) AS rows
        FROM rinova_migration.source_snapshot s, json_each(s.manifest->'tables') entry
    LOOP
        EXECUTE format('SELECT count(*) FROM rinovaplus_crm.%I', lower(split_part(source_record.name,'.',2)))
          INTO actual_rows;
        IF actual_rows<>source_record.rows THEN count_mismatches := count_mismatches + 1; END IF;
        total_rows := total_rows + actual_rows;
    END LOOP;
    IF count_mismatches <> 0 THEN RAISE EXCEPTION 'Typed reconciliation failed'; END IF;

    SELECT institutionid INTO STRICT inst FROM crmcanalinstitucionalcontexto WHERE contextid=1;
    PERFORM count(*) FROM next_webhook_receipt(inst);
    PERFORM count(*) FROM next_webhook_event(inst);
    PERFORM count(*) FROM next_media(inst);
    INSERT INTO crmcontacto(contactid,name,phone,city,program,schedule,stage,tags,notes,type,interests,customvalues)
      VALUES(person,'Árbol sintético','000','Ensayo','','','new','','','','','{}');
    INSERT INTO crmconversacion(conversationid,contactid,state,priority,controlmode,unread)
      VALUES(thread_id,person,'open','normal','human',0);
    INSERT INTO crmmensaje(messageid,conversationid,body,direction)
      VALUES(msg,thread_id,'Mensaje sintético','incoming');
    IF NOT EXISTS(SELECT 1 FROM contact_page(inst,'árbol',20,0) p WHERE p.id=person)
       OR EXISTS(SELECT 1 FROM contact_page(gen_random_uuid(),'árbol',20,0))
       OR NOT EXISTS(SELECT 1 FROM message_page(inst,thread_id,NULL) p WHERE p.id=msg)
       OR EXISTS(SELECT 1 FROM message_page(inst,thread_id,0))
    THEN RAISE EXCEPTION 'CRM read query failed'; END IF;
    IF tsql_isjson('{}') <> 1 OR tsql_isjson('1') <> 0
       OR tsql_len(chr(128512) || ' ') <> 2
    THEN RAISE EXCEPTION 'SQL Server predicate conversion failed'; END IF;

    INSERT INTO crmcanalinstitucionalaplicacion
      (institutionid,applicationid,clientid,provider,apiversion,issuerprofile,redirecturi,egressprofile,createdat,updatedat)
      VALUES(inst,app_id,app_id::text,'meta','v1','fixture','https://example.invalid','fixture',now_utc,now_utc);
    INSERT INTO crmcanalinstitucionalintegracion
      (institutionid,integrationid,applicationid,channel,provider,apiversion,dispatchmode,displayname,externalnamespace,createdat,updatedat)
      VALUES(inst,integration_id,app_id,'facebook','meta','v1','fixture','Ensayo',
        decode(repeat('ef',32),'hex'),now_utc,now_utc);
    INSERT INTO crmcanalinstitucionalcomentariosocial
      (institutionid,commentid,integrationid,externalid,authorexternalid,body,payload,receivedat)
      VALUES(inst,comment_id,integration_id,comment_id::text,'fixture','Ensayo','{}',now_utc);
    INSERT INTO crmcanalinstitucionaloperacionproveedor
      (institutionid,operationid,applicationid,integrationid,actorref,action,requestdigest,resultmetadata,effectkey,createdat)
      VALUES(inst,operation_id,app_id,integration_id,'fixture','comment_reply',
         decode(repeat('ab',32),'hex'),'{}',decode(repeat('cd',32),'hex'),now_utc);
    INSERT INTO crmcanalinstitucionalcuota(institutionid,integrationid,dayutc,action,reserved,updatedat)
      VALUES(inst,integration_id,now_utc::date,'outbound',1,now_utc);
    INSERT INTO crmcanalinstitucionalcuotareserva
      (institutionid,integrationid,operationid,reservationid,dayutc,action,units,status,createdat,updatedat)
      VALUES(inst,integration_id,operation_id,quota_id,now_utc::date,'outbound',1,'reserved',now_utc,now_utc);
    INSERT INTO crmcanalinstitucionalenviotrabajo
      (institutionid,queueid,integrationid,operationid,commentid,kind,payload,dueat,createdat)
      VALUES(inst,job_id,integration_id,operation_id,comment_id,'comment_reply','{}','1900-01-01',now_utc)
      RETURNING rowversion INTO token_before;
    IF NOT EXISTS(SELECT 1 FROM next_outbound(inst) q WHERE q.queueid=job_id)
    THEN RAISE EXCEPTION 'Outbound candidate missing'; END IF;
    IF lease_outbound(inst,job_id,lease,gen_random_uuid())
    THEN RAISE EXCEPTION 'Outbound accepted invalid reservation'; END IF;
    IF NOT lease_outbound(inst,job_id,lease,quota_id)
    THEN RAISE EXCEPTION 'Outbound lease failed'; END IF;
    IF lease_outbound(inst,job_id,gen_random_uuid(),quota_id)
    THEN RAISE EXCEPTION 'Outbound duplicate lease'; END IF;
    IF NOT EXISTS(SELECT 1 FROM queue_counts(inst) q WHERE q.queue='outbound' AND q.state='sending')
       OR NOT EXISTS(SELECT 1 FROM crmcanalinstitucionalenviotrabajo q WHERE q.queueid=job_id
                     AND q.leaseid=lease AND q.rowversion<>token_before AND q.attempts=1)
    THEN RAISE EXCEPTION 'Outbound state or version check failed'; END IF;
    IF expire_one_outbound(inst)
    THEN RAISE EXCEPTION 'Outbound expired too soon'; END IF;
    UPDATE crmcanalinstitucionalenviotrabajo SET leaseuntil=now_utc-interval '1 second' WHERE queueid=job_id;
    IF NOT expire_one_outbound(inst) THEN RAISE EXCEPTION 'Expired lease was not fenced'; END IF;
    IF NOT EXISTS(SELECT 1 FROM crmcanalinstitucionalenviotrabajo q
                   WHERE q.queueid=job_id AND q.state='uncertain' AND q.leaseid IS NULL)
       OR NOT EXISTS(SELECT 1 FROM crmcanalinstitucionaloperacionproveedor o
                     WHERE o.operationid=operation_id AND o.status='uncertain' AND o.leaseid IS NULL)
       OR NOT EXISTS(SELECT 1 FROM crmcanalinstitucionalcuotareserva r
                     WHERE r.reservationid=quota_id AND r.status='uncertain')
       OR EXISTS(SELECT 1 FROM next_outbound(inst) q WHERE q.queueid=job_id)
    THEN RAISE EXCEPTION 'Expired work returned to the dispatch queue'; END IF;
    RAISE NOTICE 'CRM_COPY_SMOKE_OK tables=% fk=% rows=% count_mismatches=%', number_tables, number_fks, total_rows, count_mismatches;
END $$;
ROLLBACK;
