"""Bounded persistent journey transitions; C10 remains the only dispatcher."""

import json
import base64
import hmac
from app.institutional.contact_intent import opted_out
from datetime import timedelta
from uuid import uuid4, uuid5, NAMESPACE_URL
from fastapi import HTTPException
from app.institutional.db import institution, one, rows, uid
from app.institutional.store import transaction
from app.institutional.channel_operations import account, configuration
from app.institutional.channel_provider import provider_account
from app.institutional.broadcasts import audience, cancel as cancel_native
from app.institutional import broadcast_templates as meta
from app.institutional.campaign_models import now, next_allowed, scheduled
from app.institutional.campaigns import (
    get,
    event,
    key,
    packed,
    person,
    snapshot,
    matches,
    reasons,
    send_document,
    authority,
    enabled,
)
from app.modules.channels import providers


def stop(c, s, run, reason, *, paused=False):
    uncertain = False
    from app.institutional.campaign_chat import links

    for value in rows(
        c,
        "SELECT * FROM crm_campaign8.Step WHERE InstitutionId=? AND EnrollmentId=? AND NativeCampaignId IS NULL",
        institution(s),
        run["EnrollmentId"],
    ):
        for job in links(c, s, value):
            if job["State"] in {"sending", "uncertain"}:
                uncertain = True
            if job["State"] == "queued":
                c.execute(
                    "UPDATE crm_channels2.SendJob SET State='cancelled',LastErrorCode=?,CompletedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND QueueId=? AND State='queued'",
                    reason[:64],
                    institution(s),
                    job["QueueId"],
                )
                c.execute(
                    "UPDATE crm_channels2.ProviderOperation SET Status='failed',ResultCode=? WHERE InstitutionId=? AND OperationId=? AND Status='pending'",
                    reason[:64],
                    institution(s),
                    job["OperationId"],
                )
    for step in rows(
        c,
        "SELECT * FROM crm_campaign8.Step WHERE InstitutionId=? AND EnrollmentId=? AND NativeCampaignId IS NOT NULL",
        institution(s),
        run["EnrollmentId"],
    ):
        if c.execute(
            "SELECT 1 FROM crm_broadcast7.Recipient r JOIN crm_channels2.SendJob q ON q.InstitutionId=r.InstitutionId AND q.QueueId=r.CurrentQueueId WHERE r.InstitutionId=? AND r.CampaignId=? AND q.State IN('sending','uncertain')",
            institution(s),
            step["NativeCampaignId"],
        ).fetchone():
            uncertain = True
        cancel_native(c, s, str(step["NativeCampaignId"]), reason)
        c.execute(
            "UPDATE crm_broadcast7.Campaign SET State='paused',Epoch=Epoch+1,Revision=Revision+1 WHERE InstitutionId=? AND CampaignId=? AND State IN('running','scheduled')",
            institution(s),
            step["NativeCampaignId"],
        )
    state = (
        "uncertain"
        if uncertain or run["State"] == "uncertain"
        else "paused"
        if paused
        else "cancelled"
    )
    c.execute(
        "UPDATE crm_campaign8.Enrollment SET State=?,LastReason=?,UpdatedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND EnrollmentId=?",
        state,
        reason,
        institution(s),
        run["EnrollmentId"],
    )
    event(
        c,
        s,
        "execution_stopped",
        {"state": state, "reason": reason},
        record=str(run["FlowId"]),
        enrollment=str(run["EnrollmentId"]),
        source=key("stop", run["EnrollmentId"], run["FlowEpoch"], reason, state),
    )


def retire(c, s, record, reason):
    for run in rows(
        c,
        "SELECT * FROM crm_campaign8.Enrollment WHERE InstitutionId=? AND (FlowId=? OR TriggerId=?) AND State IN('waiting','queued','paused','uncertain')",
        institution(s),
        record["RecordId"],
        record["RecordId"],
    ):
        stop(c, s, run, reason, paused=reason == "campaign_pause")


def guard(c, s, run, *, for_send=False, ignore_state=False):
    record = get(c, s, str(run["FlowId"]))
    doc = json.loads(record["Document"])
    if (
        record["State"] != "active"
        or record["CurrentVersion"] != run["VersionNo"]
        or record["Epoch"] != run["FlowEpoch"]
    ):
        raise HTTPException(409, "campaign_version_or_pause_changed")
    if not ignore_state and run["State"] not in {"waiting", "queued"}:
        raise HTTPException(409, "campaign_execution_not_active")
    authority(c, s, record)
    if run["TriggerId"]:
        trigger = get(c, s, str(run["TriggerId"]), "trigger")
        authority(c, s, trigger)
        if (
            trigger["State"] != "active"
            or trigger["CurrentVersion"] != run["TriggerVersion"]
        ):
            raise HTTPException(409, "campaign_trigger_changed")
    p = person(c, s, str(run["IdentityId"]))
    context = json.loads(run["Context"])
    current = snapshot(p)
    for field, reason in [
        ("canonical_contact", "campaign_identity_changed"),
        ("stage", "campaign_stage_changed"),
        ("program_id", "campaign_program_changed"),
        ("control_epoch", "campaign_handoff_changed"),
    ]:
        if context[field] != current[field]:
            raise HTTPException(409, reason)
    if (
        doc["exit_on_response"]
        and context["incoming_count"] != current["incoming_count"]
    ):
        raise HTTPException(409, "campaign_response_received")
    excluded = reasons(c, s, doc, p)
    if excluded:
        raise HTTPException(409, excluded[0])
    moment = now()
    if for_send and (
        (run["State"] == "waiting" and run["DueAt"] > moment)
        or next_allowed(moment, doc["quiet_hours"]) > moment
    ):
        raise HTTPException(409, "campaign_quiet_or_not_due")
    return record, doc, p


def fence(c, s, campaign_id):
    step = one(
        c,
        "SELECT * FROM crm_campaign8.Step WHERE InstitutionId=? AND NativeCampaignId=?",
        institution(s),
        campaign_id,
    )
    if not step:
        return
    run = one(
        c,
        "SELECT * FROM crm_campaign8.Enrollment WHERE InstitutionId=? AND EnrollmentId=?",
        institution(s),
        step["EnrollmentId"],
    )
    if not run or step["State"] != "queued" or run["StepIndex"] != step["StepIndex"]:
        raise HTTPException(409, "campaign_step_changed")
    guard(c, s, run, for_send=True)


def enroll(c, s, record, identity, entry_key, *, trigger=None, controlled=False):
    if record["Kind"] not in {"campaign", "flow"} or record["State"] != "active":
        raise HTTPException(409, "campaign_active_flow_required")
    doc = json.loads(record["Document"])
    authority(c, s, record)
    p = person(c, s, identity)
    excluded = reasons(c, s, doc, p)
    if excluded:
        return {"identity_id": identity, "enrolled": False, "reason": excluded[0]}
    old = one(
        c,
        "SELECT EnrollmentId FROM crm_campaign8.Enrollment WHERE InstitutionId=? AND FlowId=? AND CanonicalContactId=? AND EntryKey=?",
        institution(s),
        record["RecordId"],
        p["CanonicalContactId"],
        entry_key,
    )
    if old:
        return {
            "enrolled": True,
            "id": uid(str(old["EnrollmentId"])),
            "duplicate": True,
        }
    active = one(
        c,
        "SELECT State FROM crm_campaign8.Enrollment WHERE InstitutionId=? AND FlowId=? AND CanonicalContactId=? AND (State IN('waiting','queued','paused','uncertain') OR CreatedAt>DATEADD(minute,?,SYSUTCDATETIME()))",
        institution(s),
        record["RecordId"],
        p["CanonicalContactId"],
        -doc["cooldown_minutes"],
    )
    if active:
        return {
            "identity_id": identity,
            "enrolled": False,
            "reason": "campaign_existing_execution_or_cooldown",
        }
    if (
        c.execute(
            "SELECT COUNT(*) FROM crm_campaign8.Enrollment WHERE InstitutionId=? AND State IN('waiting','queued','paused','uncertain')",
            institution(s),
        ).fetchval()
        >= 500
    ):
        raise HTTPException(413, "campaign_active_scope_limit")
    variant = "A"
    if doc["ab_test"]["enabled"]:
        secret = hmac.digest(
            base64.b64decode(s.review["secrets_key"]), b"campaign-ab-key-v1", "sha256"
        )
        value = hmac.digest(
            secret,
            packed(
                {
                    "institution": institution(s),
                    "record": str(record["RecordId"]),
                    "version": record["CurrentVersion"],
                    "contact": str(p["CanonicalContactId"]),
                }
            ).encode(),
            "sha256",
        )
        variant = (
            "A"
            if int.from_bytes(value[:8], "big") % 100 < doc["ab_test"]["a_percent"]
            else "B"
        )
    id = str(uuid4())
    due = max(now(), scheduled(doc["scheduled_local"], doc["timezone"]) or now())
    due = next_allowed(due, doc["quiet_hours"])
    c.execute(
        "INSERT crm_campaign8.Enrollment(InstitutionId,EnrollmentId,FlowId,VersionNo,FlowEpoch,TriggerId,TriggerVersion,IdentityId,ContactId,CanonicalContactId,ConversationId,EntryKey,Variant,State,StepIndex,DueAt,Context) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,'waiting',0,?,?)",
        institution(s),
        id,
        record["RecordId"],
        record["CurrentVersion"],
        record["Epoch"],
        trigger["RecordId"] if trigger else None,
        trigger["CurrentVersion"] if trigger else None,
        identity,
        p["OriginalContactId"],
        p["CanonicalContactId"],
        p["ConversationId"],
        entry_key,
        variant,
        due,
        packed(snapshot(p)),
    )
    event(
        c,
        s,
        "enrolled",
        {
            "variant": variant,
            "source_key": entry_key,
            "version": record["CurrentVersion"],
        },
        record=str(record["RecordId"]),
        enrollment=id,
        actor=record["ActorId"],
        source=key("enrolled", id),
    )
    return {"enrolled": True, "id": id, "variant": variant}


def prepare_native(c, s, record, doc, run, step, p, *, controlled=False, retry=False):
    if doc["steps"][run["StepIndex"]]["crm_template_id"]:
        from app.institutional.campaign_chat import prepare

        return prepare(c, s, record, doc, run, step, p, retry=retry)
    selected = send_document(doc, doc["steps"][run["StepIndex"]], run["Variant"])
    if not selected["template_id"]:
        raise HTTPException(409, "campaign_Meta_template_required")
    selected["name"] = record["Name"][:120] + " · Paso " + str(run["StepIndex"] + 1)
    selected["filters"] = {"contact_ids": [str(p["CanonicalContactId"])]}
    selected.update(
        flow_id=uid(str(record["RecordId"])),
        flow_version=run["VersionNo"],
        execution_id=uid(str(run["EnrollmentId"])),
        step_id=uid(str(step["StepId"])),
        variant=run["Variant"],
    )
    campaign = (
        str(step["NativeCampaignId"])
        if step["NativeCampaignId"]
        else str(uuid5(NAMESPACE_URL, "CBN-P8-step:" + str(step["StepId"])))
    )
    old = one(
        c,
        "SELECT * FROM crm_broadcast7.Campaign WHERE InstitutionId=? AND CampaignId=?",
        institution(s),
        campaign,
    )
    if not old:
        c.execute(
            "INSERT crm_broadcast7.Campaign(InstitutionId,CampaignId,Name,IntegrationId,TemplateId,TemplateVersion,Document,State,Revision,Epoch,ScheduledAt,Timezone,ActorId,ActorAuthVersion,ActorSessionId,ApprovedAt) VALUES(?,?,?,?,?,?,?,'running',1,1,NULL,?,?,?,?,?)",
            institution(s),
            campaign,
            selected["name"],
            doc["integration_id"],
            selected["template_id"],
            selected["template_version"],
            packed(selected),
            doc["timezone"],
            record["ActorId"],
            record["ActorAuthVersion"],
            record["ActorSessionId"],
            record["ApprovedAt"],
        )
    else:
        existing = one(
            c,
            "SELECT r.*,q.State AS QueueState,q.ExternalId,q.Attempts AS DispatchAttempts FROM crm_broadcast7.Recipient r LEFT JOIN crm_channels2.SendJob q ON q.InstitutionId=r.InstitutionId AND q.QueueId=r.CurrentQueueId WHERE r.InstitutionId=? AND r.CampaignId=?",
            institution(s),
            campaign,
        )
        if existing and existing["CurrentQueueId"] is not None:
            allowed = (
                existing["QueueState"] == "failed" and existing["ExternalId"] is None
                if retry
                else existing["QueueState"] == "cancelled"
                and existing["DispatchAttempts"] == 0
            )
            if not allowed:
                raise HTTPException(
                    409, "campaign_retry_requires_definitive_unaccepted_effect"
                )
        c.execute(
            "UPDATE crm_broadcast7.Campaign SET State='running',Epoch=Epoch+1,Revision=Revision+1,ActorId=?,ActorAuthVersion=?,ActorSessionId=?,ApprovedAt=? WHERE InstitutionId=? AND CampaignId=?",
            record["ActorId"],
            record["ActorAuthVersion"],
            record["ActorSessionId"],
            record["ApprovedAt"],
            institution(s),
            campaign,
        )
    native = one(
        c,
        "SELECT * FROM crm_broadcast7.Campaign WHERE InstitutionId=? AND CampaignId=?",
        institution(s),
        campaign,
    )
    found, item = audience(c, s, native, controlled=controlled)
    candidate = next(
        (
            v
            for v in found
            if v["identity_id"] == uid(str(run["IdentityId"])) and v["eligible"]
        ),
        None,
    )
    if not candidate:
        raise HTTPException(
            409,
            next(
                (v["reasons"][0] for v in found if v["reasons"]),
                "campaign_recipient_excluded",
            ),
        )
    native_snapshot = {
        "template": candidate["template"],
        "body": candidate["text"],
        "target": candidate["phone"],
        "canonical_contact": candidate["contact_id"],
        "template_material_revision": json.loads(
            candidate["template_record"]["ProviderMetadata"]
        )["material_revision"],
    }
    rec = one(
        c,
        "SELECT * FROM crm_broadcast7.Recipient WHERE InstitutionId=? AND CampaignId=? AND IdentityId=?",
        institution(s),
        campaign,
        run["IdentityId"],
    )
    args = (
        native["Revision"],
        native["Epoch"],
        candidate["consent"]["ConsentId"],
        candidate["consent"]["VersionNo"],
        p["ControlEpoch"],
        item["RowVersion"],
        packed(native_snapshot),
    )
    if rec:
        c.execute(
            "UPDATE crm_broadcast7.Recipient SET CampaignRevision=?,CampaignEpoch=?,ConsentId=?,ConsentVersion=?,ControlEpoch=?,AccountVersion=?,Snapshot=?,CurrentQueueId=NULL,State='prepared',LastError=NULL WHERE InstitutionId=? AND RecipientId=?",
            *args,
            institution(s),
            rec["RecipientId"],
        )
    else:
        c.execute(
            "INSERT crm_broadcast7.Recipient(CampaignRevision,CampaignEpoch,ConsentId,ConsentVersion,ControlEpoch,AccountVersion,Snapshot,InstitutionId,RecipientId,CampaignId,IdentityId,ContactId,ConversationId,State) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,'prepared')",
            *args,
            institution(s),
            str(uuid4()),
            campaign,
            run["IdentityId"],
            p["OriginalContactId"],
            p["ConversationId"],
        )
    c.execute(
        "UPDATE crm_campaign8.Step SET NativeCampaignId=?,State='queued',LastReason=NULL WHERE InstitutionId=? AND StepId=?",
        campaign,
        institution(s),
        step["StepId"],
    )
    c.execute(
        "UPDATE crm_campaign8.Enrollment SET State='queued',LastReason=NULL WHERE InstitutionId=? AND EnrollmentId=?",
        institution(s),
        run["EnrollmentId"],
    )
    event(
        c,
        s,
        "step_prepared",
        {"native_campaign_id": campaign, "variant": run["Variant"]},
        record=str(record["RecordId"]),
        enrollment=str(run["EnrollmentId"]),
        step=str(step["StepId"]),
    )


def resume_run(c, s, record, id, *, retry=False, controlled=False):
    run = one(
        c,
        "SELECT * FROM crm_campaign8.Enrollment WHERE InstitutionId=? AND FlowId=? AND EnrollmentId=?",
        institution(s),
        record["RecordId"],
        id,
    )
    if not run or run["State"] not in ({"failed"} if retry else {"paused"}):
        raise HTTPException(409, "campaign_execution_requires_review")
    if record["State"] != "active" or run["VersionNo"] != record["CurrentVersion"]:
        raise HTTPException(409, "campaign_version_or_pause_changed")
    run["FlowEpoch"] = record["Epoch"]
    run["State"] = "waiting"
    _, doc, p = guard(c, s, run)
    c.execute(
        "UPDATE crm_campaign8.Enrollment SET State='waiting',FlowEpoch=?,DueAt=?,LastReason=NULL WHERE InstitutionId=? AND EnrollmentId=?",
        record["Epoch"],
        next_allowed(max(now(), run["DueAt"]), doc["quiet_hours"]),
        institution(s),
        id,
    )
    step = one(
        c,
        "SELECT * FROM crm_campaign8.Step WHERE InstitutionId=? AND EnrollmentId=? AND StepIndex=?",
        institution(s),
        id,
        run["StepIndex"],
    )
    if step and step["Kind"] == "send":
        from app.institutional.campaign_chat import links

        attempts = links(c, s, step) if not step["NativeCampaignId"] else []
        if step["NativeCampaignId"]:
            job = one(
                c,
                "SELECT q.State FROM crm_broadcast7.Recipient r JOIN crm_channels2.SendJob q ON q.InstitutionId=r.InstitutionId AND q.QueueId=r.CurrentQueueId WHERE r.InstitutionId=? AND r.CampaignId=?",
                institution(s),
                step["NativeCampaignId"],
            )
            attempts = [job] if job else []
        if attempts and attempts[-1]["State"] in {
            "accepted",
            "sent",
            "delivered",
            "read",
        }:
            c.execute(
                "UPDATE crm_campaign8.Enrollment SET State='queued' WHERE InstitutionId=? AND EnrollmentId=?",
                institution(s),
                id,
            )
            c.execute(
                "UPDATE crm_campaign8.Step SET State='queued',LastReason=NULL WHERE InstitutionId=? AND StepId=?",
                institution(s),
                step["StepId"],
            )
        elif step["NativeCampaignId"] or attempts:
            prepare_native(
                c, s, record, doc, run, step, p, controlled=controlled, retry=retry
            )
        else:
            c.execute(
                "UPDATE crm_campaign8.Step SET State='waiting',LastReason=NULL WHERE InstitutionId=? AND StepId=?",
                institution(s),
                step["StepId"],
            )
    event(
        c,
        s,
        "execution_reviewed",
        {"retry": retry, "epoch": record["Epoch"]},
        record=str(record["RecordId"]),
        enrollment=id,
        actor=record["ActorId"],
    )
    return {"id": id, "resumed": True}


def observe_identity(
    c, s, identity, *, incoming=False, incoming_text=None, incoming_id=None
):
    p = person(c, s, identity)
    old = one(
        c,
        "SELECT * FROM crm_campaign8.Observation WHERE InstitutionId=? AND IdentityId=?",
        institution(s),
        identity,
    )
    current = snapshot(p)
    revision = (old["Revision"] if old else 0) + 1
    changed = (
        not old
        or old["Stage"] != p["Stage"]
        or old["ProgramId"] != p["ProgramId"]
        or old["IncomingCount"] != p["IncomingCount"]
        or str(old["CanonicalContactId"]) != str(p["CanonicalContactId"])
    )
    if not changed:
        return
    if old:
        c.execute(
            "UPDATE crm_campaign8.Observation SET CanonicalContactId=?,Stage=?,ProgramId=?,IncomingCount=?,LastIncomingId=?,Revision=?,ObservedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND IdentityId=?",
            p["CanonicalContactId"],
            p["Stage"],
            p["ProgramId"],
            p["IncomingCount"],
            p["LastIncomingId"],
            revision,
            institution(s),
            identity,
        )
    else:
        c.execute(
            "INSERT crm_campaign8.Observation(InstitutionId,IdentityId,CanonicalContactId,Stage,ProgramId,IncomingCount,LastIncomingId,Revision,ObservedAt) VALUES(?,?,?,?,?,?,?,?,SYSUTCDATETIME())",
            institution(s),
            identity,
            p["CanonicalContactId"],
            p["Stage"],
            p["ProgramId"],
            p["IncomingCount"],
            p["LastIncomingId"],
            revision,
        )
    types = []
    if old and old["Stage"] != p["Stage"]:
        types.append("stage_changed")
    if old and old["ProgramId"] != p["ProgramId"]:
        types.append("program_changed")
    if incoming or old and old["IncomingCount"] != p["IncomingCount"]:
        types.append("message_in")
    for kind in types:
        event(
            c,
            s,
            "signal",
            {
                "type": kind,
                "identity_id": identity,
                "text": incoming_text
                if incoming_text is not None
                else p["IncomingText"],
                "context": current,
            },
            source=key("signal", identity, revision, kind),
        )
    if incoming and opted_out(incoming_text if incoming_text is not None else p["IncomingText"]):
        event(
            c,
            s,
            "opt_out",
            {
                "identity_id": identity,
                "message_id": str(incoming_id or p["LastIncomingId"]),
                "source": "authenticated_incoming",
            },
            source=key("optout", identity, incoming_id or p["LastIncomingId"]),
        )


def observe_contact(c, s, id):
    for row in rows(
        c,
        "SELECT IdentityId FROM crm_channels2.ExternalIdentity WHERE InstitutionId=? AND ContactId=?",
        institution(s),
        id,
    ):
        observe_identity(c, s, str(row["IdentityId"]))


class Worker:
    def __init__(self, settings, gateway=None):
        self.settings = settings
        if getattr(settings, "postgres_profile", False) and not getattr(settings, "postgres_deployment", False):
            from app.institutional.postgres_rehearsal import network_disabled

            self.request = gateway or network_disabled
            self.downloader = network_disabled
        else:
            self.request = gateway or providers.request
            self.downloader = None
        self.controlled = gateway is not None

    def refresh(self):
        from app.institutional.campaign_assets import refresh as prepare_images

        if prepare_images(self.settings, self.downloader):
            return True
        selected = None
        with transaction(self.settings, anonymous=True) as c:
            if (
                not enabled(c, self.settings)
                or not configuration(c, self.settings)["OutboundEnabled"]
            ):
                return False
            run = one(
                c,
                "SELECT TOP(1) * FROM crm_campaign8.Enrollment WHERE InstitutionId=? AND State='waiting' AND DueAt<=SYSUTCDATETIME() ORDER BY DueAt,EnrollmentId",
                institution(self.settings),
            )
            if not run:
                return False
            try:
                _, doc, p = guard(c, self.settings, run)
                step = (
                    doc["steps"][run["StepIndex"]]
                    if run["StepIndex"] < len(doc["steps"])
                    else None
                )
                if not step or step["kind"] != "send" or step["crm_template_id"]:
                    return False
                item = account(c, self.settings, doc["integration_id"])
                adapter, credential = provider_account(c, self.settings, item)
                selected = send_document(doc, step, run["Variant"])
                template = meta.latest(c, self.settings, selected["template_id"])
                if template["ObservedAt"] > now() - timedelta(minutes=45):
                    return False
                binding = (bytes(item["RowVersion"]), str(credential["SecretId"]))
            except HTTPException:
                return False
        try:
            fetched = meta.fetch(adapter, self.request)
        except (HTTPException, providers.ProviderFailure):
            return False
        with transaction(self.settings, True, anonymous=True) as c:
            try:
                guard(c, self.settings, run)
            except HTTPException:
                return False
            live = account(c, self.settings, doc["integration_id"])
            _, secret = provider_account(c, self.settings, live)
            if (bytes(live["RowVersion"]), str(secret["SecretId"])) != binding:
                return False
            for row in fetched:
                meta.append(
                    c,
                    self.settings,
                    live,
                    row,
                    secret,
                    "controlled" if self.controlled else "provider",
                )
            if str(template["ProviderId"]) not in {str(v["id"]) for v in fetched}:
                meta.append(
                    c,
                    self.settings,
                    live,
                    {
                        "id": template["ProviderId"],
                        "name": template["Name"],
                        "language": template["Language"],
                        "status": "NOT_FOUND",
                        "category": template["Category"],
                        "components": json.loads(template["Definition"]),
                    },
                    secret,
                    "controlled" if self.controlled else "provider",
                )
            event(
                c,
                self.settings,
                "catalog_refreshed",
                {"integration_id": doc["integration_id"]},
                record=str(run["FlowId"]),
                enrollment=str(run["EnrollmentId"]),
            )
        return True

    def triggers(self, c):
        active = rows(
            c,
            "SELECT TOP(101) * FROM crm_campaign8.Record WHERE InstitutionId=? AND Kind='trigger' AND State='active' ORDER BY RecordId",
            institution(self.settings),
        )
        if len(active) > 100:
            raise HTTPException(413, "campaign_trigger_scope_limit")
        signals = rows(
            c,
            "SELECT TOP(100) e.* FROM crm_campaign8.Event e WHERE e.InstitutionId=? AND e.Kind='signal' AND NOT EXISTS(SELECT 1 FROM crm_campaign8.Event done WHERE done.InstitutionId=e.InstitutionId AND done.Kind='signal_complete' AND JSON_VALUE(done.Document,'$.signal_id')=LOWER(CONVERT(varchar(36),e.EventId))) AND EXISTS(SELECT 1 FROM crm_campaign8.Record t WHERE t.InstitutionId=e.InstitutionId AND t.Kind='trigger' AND t.State='active' AND t.ApprovedAt<=e.CreatedAt AND JSON_VALUE(t.Document,'$.event_type')=JSON_VALUE(e.Document,'$.type') AND NOT EXISTS(SELECT 1 FROM crm_campaign8.Event checked WHERE checked.InstitutionId=e.InstitutionId AND checked.RecordId=t.RecordId AND checked.Kind='trigger_checked' AND JSON_VALUE(checked.Document,'$.signal_id')=LOWER(CONVERT(varchar(36),e.EventId)) AND JSON_VALUE(checked.Document,'$.trigger_version')=CONVERT(varchar(20),t.CurrentVersion))) ORDER BY e.CreatedAt,e.EventId",
            institution(self.settings),
        )
        for signal in signals:
            value = json.loads(signal["Document"])
            eligible = sorted(
                active,
                key=lambda v: (
                    json.loads(v["Document"])["priority"],
                    str(v["RecordId"]),
                ),
            )
            for trigger in eligible:
                doc = json.loads(trigger["Document"])
                source = key(
                    "trigger-check",
                    signal["EventId"],
                    trigger["RecordId"],
                    trigger["CurrentVersion"],
                )
                if (
                    signal["CreatedAt"] < trigger["ApprovedAt"]
                    or doc["event_type"] != value["type"]
                    or c.execute(
                        "SELECT 1 FROM crm_campaign8.Event WHERE InstitutionId=? AND SourceKey=?",
                        institution(self.settings),
                        source,
                    ).fetchone()
                ):
                    continue
                result = {"enrolled": False, "reason": "campaign_condition_not_matched"}
                try:
                    authority(c, self.settings, trigger)
                    flow = get(c, self.settings, doc["flow_id"])
                    p = person(c, self.settings, value["identity_id"])
                    if flow["CurrentVersion"] != doc["flow_version"]:
                        raise HTTPException(409, "campaign_trigger_changed")
                    if snapshot(p) != value["context"]:
                        raise HTTPException(409, "campaign_signal_stale")
                    p["IncomingText"] = value.get("text", "")
                    if matches(p, doc["conditions"]):
                        previous = one(
                            c,
                            "SELECT TOP(1) CreatedAt FROM crm_campaign8.Enrollment WHERE InstitutionId=? AND TriggerId=? AND CanonicalContactId=? ORDER BY CreatedAt DESC",
                            institution(self.settings),
                            trigger["RecordId"],
                            p["CanonicalContactId"],
                        )
                        if previous and previous["CreatedAt"] > now() - timedelta(
                            minutes=doc["cooldown_minutes"]
                        ):
                            result = {"enrolled": False, "reason": "campaign_cooldown"}
                        else:
                            result = enroll(
                                c,
                                self.settings,
                                flow,
                                value["identity_id"],
                                key(
                                    "automatic", signal["EventId"], trigger["RecordId"]
                                ),
                                trigger=trigger,
                                controlled=self.controlled,
                            )
                except HTTPException as error:
                    result = {"enrolled": False, "reason": str(error.detail)}
                result.update(
                    signal_id=uid(str(signal["EventId"])),
                    trigger_version=trigger["CurrentVersion"],
                )
                event(
                    c,
                    self.settings,
                    "trigger_checked",
                    result,
                    record=str(trigger["RecordId"]),
                    source=source,
                )
                if result.get("enrolled") and doc["stop_on_match"]:
                    event(
                        c,
                        self.settings,
                        "signal_complete",
                        {"signal_id": uid(str(signal["EventId"]))},
                        source=key("signal-complete", signal["EventId"]),
                    )
                    break
        return bool(signals and active)

    def observe(self, c):
        row = one(
            c,
            "SELECT TOP(1) i.IdentityId FROM crm_channels2.ExternalIdentity i LEFT JOIN crm_workspace.Merge g ON g.SourceContactId=i.ContactId AND g.Active=1 JOIN crm.Contact p ON p.ContactId=COALESCE(g.TargetContactId,i.ContactId) LEFT JOIN crm_campaign8.Observation o ON o.InstitutionId=i.InstitutionId AND o.IdentityId=i.IdentityId WHERE i.InstitutionId=? AND (o.IdentityId IS NULL OR o.CanonicalContactId<>p.ContactId OR o.Stage<>p.Stage OR ISNULL(o.ProgramId,-1)<>ISNULL(p.ProgramId,-1) OR o.IncomingCount<>(SELECT COUNT_BIG(*) FROM crm_channels2.MessageRoute r JOIN crm.Message m ON m.MessageId=r.MessageId WHERE r.InstitutionId=i.InstitutionId AND r.IdentityId=i.IdentityId AND r.ActorKind='external' AND m.Direction='incoming')) ORDER BY i.IdentityId",
            institution(self.settings),
        )
        if row:
            observe_identity(c, self.settings, uid(str(row["IdentityId"])))

    def inactivity(self, c):
        triggers = rows(
            c,
            "SELECT TOP(101) * FROM crm_campaign8.Record WHERE InstitutionId=? AND Kind='trigger' AND State='active' AND JSON_VALUE(Document,'$.event_type')='inactivity'",
            institution(self.settings),
        )
        if len(triggers) > 100:
            raise HTTPException(413, "campaign_trigger_scope_limit")
        for trigger in triggers:
            doc = json.loads(trigger["Document"])
            flow = get(c, self.settings, doc["flow_id"])
            flowdoc = json.loads(flow["Document"])
            try:
                authority(c, self.settings, trigger)
                authority(c, self.settings, flow)
            except HTTPException:
                continue
            job = one(
                c,
                "SELECT TOP(1) q.QueueId,q.IdentityId,MIN(receipt.CreatedAt) AS ObservedAt "
                "FROM crm_channels2.SendJob q JOIN crm_channels2.ExternalIdentity i "
                "ON i.InstitutionId=q.InstitutionId AND i.IdentityId=q.IdentityId "
                "JOIN crm_channels2.WebhookEvent receipt ON receipt.InstitutionId=q.InstitutionId "
                "AND receipt.IntegrationId=q.IntegrationId AND receipt.ProviderEventId COLLATE Latin1_General_100_BIN2=q.ExternalId "
                "AND receipt.Kind='status' AND receipt.Status='processed' AND JSON_VALUE(receipt.Payload,'$.text') IN('sent','delivered','read') "
                "WHERE q.InstitutionId=? AND q.IntegrationId=? AND q.State IN('sent','delivered','read') "
                + ("AND i.LastIncomingAt IS NOT NULL AND EXISTS(SELECT 1 FROM crm_channels2.MessageRoute inbound JOIN crm.Message received ON received.MessageId=inbound.MessageId WHERE inbound.InstitutionId=q.InstitutionId AND inbound.IntegrationId=q.IntegrationId AND inbound.IdentityId=q.IdentityId AND inbound.ActorKind='external' AND received.Direction='incoming' AND received.CreatedAt<=q.CreatedAt) " if flowdoc.get("followup_only") else "")
                + "AND NOT EXISTS(SELECT 1 FROM crm_channels2.SendJob newer JOIN crm.Message later ON later.MessageId=newer.MessageId JOIN crm.Message anchor ON anchor.MessageId=q.MessageId WHERE newer.InstitutionId=q.InstitutionId AND newer.IntegrationId=q.IntegrationId AND newer.IdentityId=q.IdentityId AND later.ConversationId=anchor.ConversationId AND later.Sequence>anchor.Sequence AND newer.State IN('queued','sending','uncertain','accepted','sent','delivered','read')) "
                "AND NOT EXISTS(SELECT 1 FROM crm_campaign8.Event link WHERE link.InstitutionId=q.InstitutionId AND link.Kind='native_chat' AND JSON_VALUE(link.Document,'$.queue_id')=LOWER(CONVERT(varchar(36),q.QueueId))) "
                "AND NOT EXISTS(SELECT 1 FROM crm_broadcast7.Attempt a JOIN crm_broadcast7.Recipient r ON r.InstitutionId=a.InstitutionId AND r.RecipientId=a.RecipientId JOIN crm_campaign8.Step step ON step.InstitutionId=r.InstitutionId AND step.NativeCampaignId=r.CampaignId WHERE a.InstitutionId=q.InstitutionId AND a.QueueId=q.QueueId) "
                "AND NOT EXISTS(SELECT 1 FROM crm_campaign8.Event e WHERE e.InstitutionId=q.InstitutionId AND e.Kind='signal' AND e.RecordId=? AND JSON_VALUE(e.Document,'$.inactivity_queue_id')=LOWER(CONVERT(varchar(36),q.QueueId)) AND JSON_VALUE(e.Document,'$.trigger_version')=?) "
                "GROUP BY q.QueueId,q.IdentityId,i.LastIncomingAt HAVING MIN(receipt.CreatedAt)<=DATEADD(minute,?,SYSUTCDATETIME()) "
                "AND (i.LastIncomingAt IS NULL OR i.LastIncomingAt<=MIN(receipt.CreatedAt)) ORDER BY MIN(receipt.CreatedAt),q.QueueId",
                institution(self.settings),
                flowdoc["integration_id"],
                trigger["RecordId"],
                str(trigger["CurrentVersion"]),
                -doc["idle_minutes"],
            )
            if job:
                p = person(c, self.settings, uid(str(job["IdentityId"])))
                event(
                    c,
                    self.settings,
                    "signal",
                    {
                        "type": "inactivity",
                        "identity_id": uid(str(job["IdentityId"])),
                        "context": snapshot(p),
                        "text": p["IncomingText"],
                        "inactivity_queue_id": uid(str(job["QueueId"])),
                        "trigger_version": trigger["CurrentVersion"],
                        "sent_observed_at": job["ObservedAt"].isoformat(),
                    },
                    record=str(trigger["RecordId"]),
                    source=key(
                        "inactivity",
                        trigger["RecordId"],
                        trigger["CurrentVersion"],
                        job["QueueId"],
                    ),
                )

    def once(self):
        with transaction(self.settings, True, anonymous=True) as c:
            if not enabled(c, self.settings):
                return False
            # Inspect contexts even while due dates are in the future.
            pending = rows(
                c,
                "SELECT TOP(501) * FROM crm_campaign8.Enrollment WHERE InstitutionId=? AND State IN('waiting','queued') ORDER BY DueAt,EnrollmentId",
                institution(self.settings),
            )
            if len(pending) > 500:
                raise HTTPException(413, "campaign_active_scope_limit")
            for run in pending:
                try:
                    guard(c, self.settings, run)
                except HTTPException as error:
                    stop(c, self.settings, run, str(error.detail))
                    return True
            trigger_types = rows(
                c,
                "SELECT TOP(101) JSON_VALUE(Document,'$.event_type') AS EventType FROM crm_campaign8.Record WHERE InstitutionId=? AND Kind='trigger' AND State='active'",
                institution(self.settings),
            )
            if len(trigger_types) > 100:
                raise HTTPException(413, "campaign_trigger_scope_limit")
            # Observation scans are needed only for change-based triggers.
            # Do not hold the institutional write lock scanning every contact
            # when no trigger consumes those signals (including inactivity-only).
            kinds = {v["EventType"] for v in trigger_types}
            if kinds & {"message_in", "stage_changed", "program_changed"}:
                self.observe(c)
            if "inactivity" in kinds:
                self.inactivity(c)
            if kinds:
                self.triggers(c)
            run = one(
                c,
                "SELECT TOP(1) * FROM crm_campaign8.Enrollment WHERE InstitutionId=? AND State IN('waiting','queued') AND DueAt<=SYSUTCDATETIME() ORDER BY DueAt,EnrollmentId",
                institution(self.settings),
            )
            if not run:
                return False
            record, doc, p = guard(c, self.settings, run)
            if run["StepIndex"] >= len(doc["steps"]):
                c.execute(
                    "UPDATE crm_campaign8.Enrollment SET State='completed',LastReason=NULL WHERE InstitutionId=? AND EnrollmentId=?",
                    institution(self.settings),
                    run["EnrollmentId"],
                )
                event(
                    c,
                    self.settings,
                    "execution_completed",
                    {},
                    record=str(record["RecordId"]),
                    enrollment=str(run["EnrollmentId"]),
                )
                return True
            step = one(
                c,
                "SELECT * FROM crm_campaign8.Step WHERE InstitutionId=? AND EnrollmentId=? AND StepIndex=?",
                institution(self.settings),
                run["EnrollmentId"],
                run["StepIndex"],
            )
            definition = doc["steps"][run["StepIndex"]]
            if not step:
                id = str(uuid4())
                due = (
                    run["DueAt"] + timedelta(minutes=definition["wait_minutes"])
                    if definition["kind"] == "wait"
                    else run["DueAt"]
                )
                c.execute(
                    "INSERT crm_campaign8.Step(InstitutionId,StepId,EnrollmentId,StepIndex,Kind,State,DueAt) VALUES(?,?,?,?,?,'waiting',?)",
                    institution(self.settings),
                    id,
                    run["EnrollmentId"],
                    run["StepIndex"],
                    definition["kind"],
                    due,
                )
                step = one(
                    c,
                    "SELECT * FROM crm_campaign8.Step WHERE InstitutionId=? AND StepId=?",
                    institution(self.settings),
                    id,
                )
                if definition["kind"] == "wait":
                    c.execute(
                        "UPDATE crm_campaign8.Enrollment SET DueAt=? WHERE InstitutionId=? AND EnrollmentId=?",
                        due,
                        institution(self.settings),
                        run["EnrollmentId"],
                    )
                    run["DueAt"] = due
            if step["State"] == "queued":
                job = one(
                    c,
                    "SELECT q.* FROM crm_broadcast7.Recipient r JOIN crm_channels2.SendJob q ON q.InstitutionId=r.InstitutionId AND q.QueueId=r.CurrentQueueId WHERE r.InstitutionId=? AND r.CampaignId=?",
                    institution(self.settings),
                    step["NativeCampaignId"],
                )
                if not step["NativeCampaignId"]:
                    from app.institutional.campaign_chat import links

                    attempts = links(c, self.settings, step)
                    job = attempts[-1] if attempts else None
                if not job or job["State"] in {"queued", "sending"}:
                    c.execute(
                        "UPDATE crm_campaign8.Enrollment SET DueAt=DATEADD(second,1,SYSUTCDATETIME()) WHERE InstitutionId=? AND EnrollmentId=?",
                        institution(self.settings),
                        run["EnrollmentId"],
                    )
                    return False
                if job["State"] not in {"accepted", "sent", "delivered", "read"}:
                    state = "uncertain" if job["State"] == "uncertain" else "failed"
                    c.execute(
                        "UPDATE crm_campaign8.Step SET State=?,LastReason=? WHERE InstitutionId=? AND StepId=?",
                        state,
                        job["LastErrorCode"],
                        institution(self.settings),
                        step["StepId"],
                    )
                    c.execute(
                        "UPDATE crm_campaign8.Enrollment SET State=?,LastReason=? WHERE InstitutionId=? AND EnrollmentId=?",
                        state,
                        job["LastErrorCode"],
                        institution(self.settings),
                        run["EnrollmentId"],
                    )
                    return True
                if not step["NativeCampaignId"]:
                    from app.institutional.campaign_chat import parts, prepare, links

                    attempts = links(c, self.settings, step)
                    index = json.loads(attempts[-1]["LinkDocument"]).get(
                        "part_index", 0
                    )
                    if index + 1 < len(
                        parts(
                            c,
                            self.settings,
                            doc,
                            definition,
                            run["Variant"],
                            p,
                            record["Name"],
                        )
                    ):
                        c.execute("SAVE TRANSACTION p8_next_part")
                        try:
                            prepare(
                                c,
                                self.settings,
                                record,
                                doc,
                                run,
                                step,
                                p,
                                next_part=True,
                            )
                        except HTTPException as e:
                            c.execute("ROLLBACK TRANSACTION p8_next_part")
                            c.execute(
                                "UPDATE crm_campaign8.Enrollment SET DueAt=DATEADD(second,30,SYSUTCDATETIME()),LastReason=? WHERE InstitutionId=? AND EnrollmentId=?",
                                str(e.detail)[:100],
                                institution(self.settings),
                                run["EnrollmentId"],
                            )
                        return True
                completed = job["CompletedAt"] or now()
            elif definition["kind"] == "wait":
                if step["DueAt"] > now():
                    c.execute(
                        "UPDATE crm_campaign8.Enrollment SET DueAt=? WHERE InstitutionId=? AND EnrollmentId=?",
                        step["DueAt"],
                        institution(self.settings),
                        run["EnrollmentId"],
                    )
                    return True
                completed = step["DueAt"]
            elif definition["kind"] == "condition":
                matched = matches(p, definition["conditions"])
                if not matched and definition["on_false"] == "stop":
                    stop(c, self.settings, run, "campaign_condition_not_matched")
                    return True
                completed = now()
            else:
                moment = now()
                due = next_allowed(moment, doc["quiet_hours"])
                if due > moment:
                    c.execute(
                        "UPDATE crm_campaign8.Enrollment SET DueAt=? WHERE InstitutionId=? AND EnrollmentId=?",
                        due,
                        institution(self.settings),
                        run["EnrollmentId"],
                    )
                    return True
                c.execute("SAVE TRANSACTION p8_prepare_step")
                try:
                    prepare_native(
                        c,
                        self.settings,
                        record,
                        doc,
                        run,
                        step,
                        p,
                        controlled=self.controlled,
                    )
                except HTTPException as error:
                    c.execute("ROLLBACK TRANSACTION p8_prepare_step")
                    c.execute(
                        "UPDATE crm_campaign8.Enrollment SET DueAt=DATEADD(second,60,SYSUTCDATETIME()),LastReason=? WHERE InstitutionId=? AND EnrollmentId=?",
                        str(error.detail)[:100],
                        institution(self.settings),
                        run["EnrollmentId"],
                    )
                    event(
                        c,
                        self.settings,
                        "step_blocked",
                        {"reason": str(error.detail)},
                        record=str(record["RecordId"]),
                        enrollment=str(run["EnrollmentId"]),
                        step=str(step["StepId"]),
                    )
                return True
            c.execute(
                "UPDATE crm_campaign8.Step SET State='completed',CompletedAt=? WHERE InstitutionId=? AND StepId=?",
                completed,
                institution(self.settings),
                step["StepId"],
            )
            c.execute(
                "UPDATE crm_campaign8.Enrollment SET State='waiting',StepIndex=StepIndex+1,DueAt=?,LastReason=NULL,UpdatedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND EnrollmentId=?",
                completed,
                institution(self.settings),
                run["EnrollmentId"],
            )
            event(
                c,
                self.settings,
                "step_completed",
                {"step_index": run["StepIndex"], "variant": run["Variant"]},
                record=str(record["RecordId"]),
                enrollment=str(run["EnrollmentId"]),
                step=str(step["StepId"]),
                source=key("complete-step", step["StepId"]),
            )
            return True
