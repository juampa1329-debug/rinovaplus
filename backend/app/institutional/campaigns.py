"""Versioned institutional CRM campaigns. Every provider effect belongs to C10/P7."""

import hashlib
import json
import re
from contextlib import contextmanager
from datetime import timedelta
from uuid import uuid4

from fastapi import HTTPException

from app.institutional import broadcast_templates as meta
from app.institutional.auth import authorize
from app.institutional.broadcasts import consent, same
from app.institutional.campaign_models import next_allowed, now, scheduled
from app.institutional.channel_operations import account
from app.institutional.db import (
    audit,
    institution,
    one,
    record_operation,
    replay,
    rows,
    uid,
    utc,
)
from app.institutional.settings import setting
from app.institutional.store import transaction

VERSION = "cbn-institutional-campaign-p8-v1"
OPEN = {"waiting", "queued", "paused", "uncertain"}


def next_message_name(run):
    """Read the frozen version, including the send following an active wait."""
    if run["State"] not in OPEN:
        return None
    steps = json.loads(run["VersionDocument"]).get("steps", [])
    return next((v.get("name") or f"Mensaje {i + 1}"
                 for i, v in enumerate(steps) if i >= run["StepIndex"] and v["kind"] == "send"), None)


def packed(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def key(*parts):
    return hashlib.sha256(packed([str(v) for v in parts]).encode()).hexdigest()


def get(c, s, id, kind=None):
    v = one(
        c,
        "SELECT * FROM crm_campaign8.Record WHERE InstitutionId=? AND RecordId=?",
        institution(s),
        id,
    )
    if not v or kind and v["Kind"] != kind:
        raise HTTPException(404, "campaign_record_not_found")
    return v


def public(v):
    return dict(
        id=uid(str(v["RecordId"])),
        kind=v["Kind"],
        name=v["Name"],
        state=v["State"],
        revision=v["Revision"],
        version=v["CurrentVersion"],
        epoch=v["Epoch"],
        document=json.loads(v["Document"]),
    )


def event(
    c,
    s,
    kind,
    data,
    *,
    record=None,
    enrollment=None,
    step=None,
    actor=None,
    source=None,
    event_id=None,
):
    source = source or key(kind, uuid4())
    old = one(
        c,
        "SELECT EventId FROM crm_campaign8.Event WHERE InstitutionId=? AND SourceKey=?",
        institution(s),
        source,
    )
    if old:
        return uid(str(old["EventId"]))
    id = event_id or str(uuid4())
    c.execute(
        "INSERT crm_campaign8.Event(InstitutionId,EventId,RecordId,EnrollmentId,StepId,Kind,SourceKey,Document,ActorId) VALUES(?,?,?,?,?,?,?,?,?)",
        institution(s),
        id,
        record,
        enrollment,
        step,
        kind,
        source,
        packed(data),
        actor,
    )
    return id


def enabled(c, s):
    flags = setting(c, s, "modules")["document"]["enabled"]
    return all(
        flags.get(n, False) for n in ["campaigns", "broadcasts", "channels", "inbox"]
    )


def authority(c, s, record):
    from app.institutional.broadcasts import authority as approved_actor

    actor = approved_actor(c, s, record)
    if not enabled(c, s):
        raise HTTPException(403, "module_disabled")
    return actor


def person(c, s, identity):
    v = one(
        c,
        "SELECT i.*,i.ContactId AS OriginalContactId,p.ContactId AS CanonicalContactId,p.Name,p.City,p.ProgramId,p.Program,p.Stage,p.Tags,p.Phone,p.Schedule,p.CustomValues,v.ControlMode,v.State AS ConversationState,COALESCE(ctrl.Epoch,0) AS ControlEpoch FROM crm_channels2.ExternalIdentity i JOIN crm.Conversation v ON v.ConversationId=i.ConversationId AND v.ContactId=i.ContactId LEFT JOIN crm_workspace.Merge g ON g.SourceContactId=i.ContactId AND g.Active=1 JOIN crm.Contact p ON p.ContactId=COALESCE(g.TargetContactId,i.ContactId) LEFT JOIN crm_channels.ConversationControl ctrl ON ctrl.ConversationId=v.ConversationId WHERE i.InstitutionId=? AND i.IdentityId=?",
        institution(s),
        identity,
    )
    if not v:
        raise HTTPException(404, "campaign_identity_not_found")
    v["IncomingCount"] = c.execute(
        "SELECT COUNT_BIG(*) FROM crm_channels2.MessageRoute r JOIN crm.Message m ON m.MessageId=r.MessageId WHERE r.InstitutionId=? AND r.IdentityId=? AND r.ActorKind='external' AND m.Direction='incoming'",
        institution(s),
        identity,
    ).fetchval()
    latest = one(
        c,
        "SELECT TOP(1) m.MessageId,m.Body FROM crm_channels2.MessageRoute r JOIN crm.Message m ON m.MessageId=r.MessageId WHERE r.InstitutionId=? AND r.IdentityId=? AND r.ActorKind='external' AND m.Direction='incoming' ORDER BY m.CreatedAt DESC,m.MessageId DESC",
        institution(s),
        identity,
    )
    if getattr(s, "postgres_deployment", False):
        from app.institutional.commercial_followup import read
        v["CommercialProgress"], _ = read(c, s, v["CanonicalContactId"])
    v["LastIncomingId"] = latest["MessageId"] if latest else None
    v["IncomingText"] = latest["Body"] if latest else ""
    return v


def matches(v, filters):
    if filters.get("followup_states") and v.get("CommercialProgress", {}).get("state") not in filters["followup_states"]:
        return False
    for name, col in [
        ("contact_ids", "CanonicalContactId"),
        ("program_ids", "ProgramId"),
        ("stages", "Stage"),
        ("cities", "City"),
    ]:
        values = filters.get(name, [])
        current = str(v.get(col))
        expected = {str(x) for x in values}
        if name == "contact_ids":
            current = current.lower()
            expected = {x.lower() for x in expected}
        if values and current not in expected:
            return False
    tags = {x.strip().casefold() for x in re.split("[,;|]", v.get("Tags") or "")}
    if not {t.casefold().strip() for t in filters.get("tags", [])} <= tags:
        return False
    words = filters.get("keywords", [])
    return not words or any(
        x.casefold() in v.get("IncomingText", "").casefold() for x in words
    )


def reference(c, s, id, version, kind):
    if not id:
        return None
    value = get(c, s, str(id), kind)
    if value["State"] != "active" or value["CurrentVersion"] != version:
        raise HTTPException(409, "campaign_reference_changed")
    return json.loads(value["Document"])


def filters_for(c, s, doc):
    segment = reference(
        c, s, doc.get("segment_id"), doc.get("segment_version", 1), "segment"
    )
    template = reference(
        c, s, doc.get("crm_template_id"), doc.get("crm_template_version", 1), "template"
    )
    if template and template["channel"] != doc["channel"]:
        raise HTTPException(409, "campaign_CRM_template_channel_required")
    for step in doc.get("steps", []):
        if step["kind"] != "send":
            continue
        refs = [(step.get("crm_template_id"), step.get("crm_template_version", 1))]
        if doc["ab_test"]["enabled"]:
            refs.append(
                (
                    step.get("variant_b_crm_template_id"),
                    step.get("variant_b_crm_template_version", 1),
                )
            )
        for id, version in refs:
            value = reference(c, s, id, version, "template")
            if value and value["channel"] != doc["channel"]:
                raise HTTPException(409, "campaign_CRM_template_channel_required")
    return [doc["entry_conditions"]] + ([segment["filters"]] if segment else [])


def marketing_allowed(c, s, p):
    g = consent(c, s, str(p["IdentityId"]))
    if (
        not g
        or g["State"] != "granted"
        or not g["ExpiresAt"]
        or g["ExpiresAt"] <= now()
    ):
        return False
    last = one(
        c,
        "SELECT TOP(1) CreatedAt FROM crm_campaign8.Event WHERE InstitutionId=? AND Kind='opt_out' AND JSON_VALUE(Document,'$.identity_id')=? ORDER BY CreatedAt DESC",
        institution(s),
        uid(str(p["IdentityId"])),
    )
    return not last or g["CreatedAt"] > last["CreatedAt"]


def customer_window(doc, p):
    return bool(doc.get("followup_only") and doc.get("contact_basis") == "customer_request"
                and p.get("IncomingCount", 0) > 0 and p.get("LastIncomingAt")
                and now() - timedelta(hours=24) < p["LastIncomingAt"] <= now())


def reasons(c, s, doc, p):
    found = []
    from app.institutional.prospect_source_status import promotion_exclusion
    source_reason = promotion_exclusion(p.get("CustomValues"), doc)
    if source_reason:
        found.append(source_reason)
    from app.institutional.siie_classification import blocked as siie_registered
    if siie_registered(c, s, p.get("CanonicalContactId") or p.get("ContactId"), p.get("Phone", "")):
        found.append("siie_registered_no_promotions")
    if getattr(s, "postgres_deployment", False):
        from app.institutional.commercial_followup import read, exclusion
        progress, _ = read(c, s, p.get("CanonicalContactId") or p["ContactId"])
        reason = exclusion(progress, p.get("Stage"), doc)
        if reason:
            found.append(reason)
        allowed = doc.get("entry_conditions", {}).get("followup_states", [])
        if allowed and progress.get("state") not in allowed:
            found.append("campaign_followup_case_changed")
    if not same(p["IntegrationId"], doc["integration_id"]):
        found.append("campaign_account_mismatch")
    if p["ControlMode"] == "human":
        found.append("human_control")
    if p["ConversationState"] == "closed":
        found.append("conversation_closed")
    if doc.get("followup_only") and not (p.get("IncomingCount") and p.get("LastIncomingAt")):
        found.append("genuine_incoming_required")
    if not marketing_allowed(c, s, p) and not customer_window(doc, p):
        found.append("marketing_consent_required")
    try:
        if any(not matches(p, f) for f in filters_for(c, s, doc)):
            found.append("campaign_segment_excluded")
    except HTTPException as error:
        found.append(str(error.detail))
    from app.institutional.contact_preference import blocked
    denied = blocked(c, s, p["CanonicalContactId"])
    if denied:
        found.append("no_contact")
    return found


def send_document(doc, step, variant):
    b = variant == "B" and doc["ab_test"]["enabled"]
    return dict(
        name="Flujo CRM",
        integration_id=doc["integration_id"],
        template_id=step["variant_b_template_id"] if b else step["meta_template_id"],
        template_version=step["variant_b_template_version"]
        if b
        else step["meta_template_version"],
        filters={},
        followup_only=doc.get("followup_only", False),
        entry_conditions={"followup_states": doc.get("entry_conditions", {}).get("followup_states", [])},
        variables=step["variant_b_variables"] if b else step["variables"],
        header_media_url=step["header_media_url"],
        timezone=doc["timezone"],
        scheduled_local=None,
    )


def issues(c, s, record, *, controlled=False):
    doc = json.loads(record["Document"])
    found = []
    if record["Kind"] in {"template", "segment"}:
        if (
            record["Kind"] == "template"
            and not doc["body"].strip()
            and not doc["blocks"]
        ):
            found.append("campaign_CRM_template_empty")
        if record["Kind"] == "template" and any(
            v["source"] == "literal" and not v["value"].strip()
            for v in doc["variables"].values()
        ):
            found.append("campaign_template_literal_required")
        return found
    if record["Kind"] == "trigger":
        flow = get(c, s, doc["flow_id"])
        if (
            flow["Kind"] not in {"flow", "campaign"}
            or flow["State"] != "active"
            or flow["CurrentVersion"] != doc["flow_version"]
            or json.loads(flow["Document"])["channel"] != doc["channel"]
        ):
            found.append("campaign_trigger_flow_review_required")
        return found
    try:
        filters_for(c, s, doc)
        item = account(c, s, doc["integration_id"])
        if (
            item["RequestedStatus"] != "connected"
            or item["VerifiedStatus"] != "verified"
        ):
            found.append("verified_connected_account_required")
        if item["Channel"] != doc["channel"]:
            found.append("campaign_account_mismatch")
        if any(x["kind"] == "send" for x in doc["steps"]):
            from app.institutional.campaign_chat import capability
            from app.institutional.channel_provider import provider_account

            provider_account(c, s, item)
            capability(c, s, item)
        cadence = one(
            c,
            "SELECT Enabled FROM crm_broadcast7.Cadence WHERE InstitutionId=? AND IntegrationId=?",
            institution(s),
            doc["integration_id"],
        )
        if any(x["kind"] == "send" for x in doc["steps"]) and (
            not cadence or not cadence["Enabled"]
        ):
            found.append("campaign_cadence_required")
        for step in doc["steps"]:
            if step["kind"] != "send":
                continue
            for variant in ["A", "B"] if doc["ab_test"]["enabled"] else ["A"]:
                sample = dict(
                    Name="Aspirante de ejemplo",
                    CustomValues='{"email":"ejemplo@example.invalid"}',
                    City="Ciudad",
                    Phone="573100000000",
                    Program="Programa",
                    Stage="Etapa",
                    Schedule="Jornada",
                )
                if step["crm_template_id"]:
                    from app.institutional.campaign_chat import content

                    content(c, s, doc, step, variant, sample, record["Name"])
                    if (
                        item["Channel"] == "instagram"
                        and item["IssuerProfile"] == "instagram_login"
                    ):
                        from app.institutional.campaign_chat import parts
                        from app.institutional.campaign_delivery import origin

                        if any(
                            v["kind"] != "text"
                            for v in parts(
                                c, s, doc, step, variant, sample, record["Name"]
                            )
                        ):
                            origin(c, s)
                    continue
                if doc["channel"] != "whatsapp":
                    found.append("campaign_Meta_requires_WhatsApp")
                    continue
                selected = send_document(doc, step, variant)
                if not selected["template_id"]:
                    found.append("campaign_Meta_template_required")
                    continue
                template = meta.approved(
                    c,
                    s,
                    {
                        "TemplateId": selected["template_id"],
                        "TemplateVersion": selected["template_version"],
                    },
                    item,
                    controlled=controlled,
                )
                sample = dict(
                    Name="Aspirante de ejemplo",
                    CustomValues='{"email":"ejemplo@example.invalid"}',
                    City="Ciudad",
                    Phone="573100000000",
                    Program="Programa",
                    Stage="Etapa",
                    Schedule="Jornada",
                )
                meta.parameters(template, selected, sample, record["Name"])
    except HTTPException as error:
        found.append(str(error.detail))
    return list(dict.fromkeys(found))


def candidates(c, s, record, *, controlled=False):
    doc = json.loads(record["Document"])
    global_issues = issues(c, s, record, controlled=controlled)
    values = rows(
        c,
        "SELECT TOP(5001) IdentityId FROM crm_channels2.ExternalIdentity WHERE InstitutionId=? AND IntegrationId=? ORDER BY IdentityId",
        institution(s),
        doc["integration_id"],
    )
    if len(values) > 5000:
        raise HTTPException(413, "campaign_audience_scope_limit")
    output = []
    seen = set()
    for row in values:
        p = person(c, s, str(row["IdentityId"]))
        r = global_issues + reasons(c, s, doc, p)
        canonical = uid(str(p["CanonicalContactId"]))
        if canonical in seen:
            r.append("duplicate_contact")
        elif not r:
            seen.add(canonical)
        output.append(
            dict(
                identity_id=uid(str(p["IdentityId"])),
                name=p["Name"],
                contact_id=canonical,
                eligible=not r,
                reasons=list(dict.fromkeys(r)),
                person=p,
            )
        )
    return output, global_issues


def snapshot(p):
    return dict(
        canonical_contact=uid(str(p["CanonicalContactId"])),
        stage=p["Stage"],
        program_id=p["ProgramId"],
        incoming_count=p["IncomingCount"],
        control_epoch=p["ControlEpoch"],
    )


def render_crm(doc, p, name):
    source = dict(
        Name=p.get("Name", ""),
        CustomValues=p.get("CustomValues", "{}"),
        City=p.get("City", ""),
        Phone=p.get("Phone", ""),
        Program=p.get("Program", ""),
        Stage=p.get("Stage", ""),
        Schedule=p.get("Schedule", ""),
    )
    values = {
        "customer_name": source["Name"],
        "customer_first_name": source["Name"].split(" ")[0],
        "customer_email": json.loads(source["CustomValues"]).get("email", ""),
        "customer_city": source["City"],
        "customer_phone": source["Phone"],
        "program": source["Program"],
        "stage": source["Stage"],
        "schedule": source["Schedule"],
        "campaign_name": name,
    }

    def replace(m):
        binding = doc["variables"].get(m[1].strip())
        value = (
            binding.get("value", "")
            if binding and binding["source"] == "literal"
            else values.get(binding["source"], "")
            if binding
            else ""
        )
        return value or "[dato no disponible]"

    text = "\n".join(
        [doc["body"]]
        + [(v["text"] + " " + v["url"]).strip() for v in doc.get("blocks", [])]
    )
    return re.sub(r"\{\{\s*([^{}]+)\s*\}\}", replace, text)


class Campaigns:
    def __init__(self, settings, gateway=None):
        self.settings = settings
        self.gateway = gateway
        self.controlled = gateway is not None

    @contextmanager
    def tx(self, auth, write=False, recent=False):
        with transaction(self.settings, write, anonymous=True) as c:
            actor = authorize(c, self.settings, auth, "campaigns.manage", recent=recent)
            authorize(c, self.settings, auth, "crm.read")
            if not setting(c, self.settings, "modules")["document"]["enabled"].get(
                "campaigns", False
            ):
                raise HTTPException(403, "module_disabled")
            yield c, actor

    def listing(self, auth):
        with self.tx(auth) as (c, _):
            found = rows(
                c,
                "SELECT TOP(501) * FROM crm_campaign8.Record WHERE InstitutionId=? ORDER BY UpdatedAt DESC,RecordId",
                institution(self.settings),
            )
            if len(found) > 500:
                raise HTTPException(413, "campaign_record_scope_limit")
            return {
                "items": [public(v) for v in found],
                "limits": {"records": 500, "audience": 5000, "steps": 20},
                "provider_acceptance_is_not_inferred": True,
            }

    def metadata(self, auth):
        from app.institutional.broadcasts import Broadcasts

        value = Broadcasts(self.settings, self.gateway).metadata(auth)
        with self.tx(auth) as (c, _):
            value["accounts"] = [
                dict(
                    id=uid(str(v["IntegrationId"])),
                    name=v["DisplayName"],
                    channel=v["Channel"],
                    verified_status=v["VerifiedStatus"],
                )
                for v in rows(
                    c,
                    "SELECT * FROM crm_channels2.Integration WHERE InstitutionId=? AND Channel IN('whatsapp','instagram','messenger','tiktok') ORDER BY DisplayName",
                    institution(self.settings),
                )
            ]
        return dict(
            value,
            CRM_templates_are_not_Meta_approval=True,
            trigger_events=[
                "message_in",
                "stage_changed",
                "program_changed",
                "inactivity",
            ],
            step_kinds=["wait", "condition", "send"],
        )

    def get(self, auth, id):
        with self.tx(auth) as (c, _):
            return public(get(c, self.settings, id))

    def save(self, auth, id, body):
        with self.tx(auth, True) as (c, actor):
            h, prior = replay(
                c,
                self.settings,
                actor["UserId"],
                str(body.operation_id),
                "campaign8.save",
                id,
                body.model_dump(mode="json"),
            )
            if prior:
                return prior
            result = self.write_record(c, actor, id, body)
            record_operation(
                c,
                self.settings,
                actor["UserId"],
                str(body.operation_id),
                "campaign8.save",
                id,
                h,
                result,
            )
            return result

    def write_record(self, c, actor, id, body):
        if body.kind == "template":
            from app.institutional.campaign_assets import library_file

            for block in body.document["blocks"]:
                if block.get("asset_id"):
                    v, _ = library_file(c, self.settings, block["asset_id"], actor)
                    if v["kind"] != block["type"]:
                        raise HTTPException(409, "campaign_media_kind_mismatch")
        old = one(
            c,
            "SELECT * FROM crm_campaign8.Record WHERE InstitutionId=? AND RecordId=?",
            institution(self.settings),
            id,
        )
        if body.revision != (old["Revision"] if old else 0):
            raise HTTPException(409, "revision_conflict")
        if old and old["Kind"] != body.kind:
            raise HTTPException(409, "campaign_record_kind_immutable")
        if old:
            from app.institutional.campaign_runtime import retire

            retire(c, self.settings, old, "campaign_version_changed")
        version = (old["CurrentVersion"] if old else 0) + 1
        if old:
            c.execute(
                "UPDATE crm_campaign8.Record SET Name=?,Document=?,State='draft',Revision=Revision+1,CurrentVersion=?,Epoch=Epoch+1,ActorId=NULL,ActorAuthVersion=NULL,ActorSessionId=NULL,ApprovedAt=NULL,UpdatedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND RecordId=?",
                body.name,
                packed(body.document),
                version,
                institution(self.settings),
                id,
            )
        else:
            c.execute(
                "INSERT crm_campaign8.Record(InstitutionId,RecordId,Kind,Name,State,Revision,CurrentVersion,Epoch,Document) VALUES(?,?,?,?,'draft',1,1,1,?)",
                institution(self.settings),
                id,
                body.kind,
                body.name,
                packed(body.document),
            )
        c.execute(
            "INSERT crm_campaign8.Version(InstitutionId,RecordId,VersionNo,Kind,Name,Document,Reason,ActorId,OperationId) VALUES(?,?,?,?,?,?,?,?,?)",
            institution(self.settings),
            id,
            version,
            body.kind,
            body.name,
            packed(body.document),
            body.reason,
            actor["UserId"],
            str(body.operation_id),
        )
        result = public(get(c, self.settings, id))
        audit(c, self.settings, actor["UserId"], "campaign8.save", id, version=version)
        return result

    def history(self, auth, id, offset=0):
        with self.tx(auth) as (c, _):
            get(c, self.settings, id)
            total = c.execute(
                "SELECT COUNT(*) FROM crm_campaign8.Version WHERE InstitutionId=? AND RecordId=?",
                institution(self.settings),
                id,
            ).fetchval()
            return {
                "offset": offset,
                "has_more": total > offset + 100,
                "total": total,
                "items": [
                    dict(
                        version=v["VersionNo"],
                        name=v["Name"],
                        reason=v["Reason"],
                        document=json.loads(v["Document"]),
                        created_at=utc(v["CreatedAt"]),
                    )
                    for v in rows(
                        c,
                        "SELECT * FROM crm_campaign8.Version WHERE InstitutionId=? AND RecordId=? ORDER BY VersionNo DESC OFFSET ? ROWS FETCH NEXT 100 ROWS ONLY",
                        institution(self.settings),
                        id,
                        offset,
                    )
                ],
            }

    def preview(self, auth, id):
        with self.tx(auth) as (c, _):
            record = get(c, self.settings, id)
            if record["Kind"] == "segment":
                f = json.loads(record["Document"])["filters"]
                values = rows(
                    c, "SELECT TOP(5001) * FROM crm.Contact ORDER BY ContactId"
                )
                if len(values) > 5000:
                    raise HTTPException(413, "campaign_audience_scope_limit")
                selected = [
                    dict(id=uid(str(v["ContactId"])), name=v["Name"], stage=v["Stage"])
                    for v in values
                    if matches(
                        dict(v, CanonicalContactId=v["ContactId"], IncomingText=""), f
                    )
                ]
                return {
                    "items": selected[:100],
                    "total": len(selected),
                    "authority": "declared_CRM_not_verified_SIIE",
                    "provider_eligible": False,
                }
            if record["Kind"] not in {"campaign", "flow"}:
                return {
                    "issues": issues(
                        c, self.settings, record, controlled=self.controlled
                    )
                }
            found, problems = candidates(
                c, self.settings, record, controlled=self.controlled
            )
            return {
                "items": [
                    {
                        k: v[k]
                        for k in [
                            "identity_id",
                            "contact_id",
                            "name",
                            "eligible",
                            "reasons",
                        ]
                    }
                    for v in found[:100]
                ],
                "counts": {
                    "matched": len(found),
                    "eligible": sum(v["eligible"] for v in found),
                    "excluded": sum(not v["eligible"] for v in found),
                },
                "issues": problems,
                "authority": "declared_CRM_not_verified_SIIE",
            }

    def preflight(self, auth, id, body):
        with self.tx(auth, True) as (c, actor):
            record = get(c, self.settings, id)
            if body.revision != record["Revision"]:
                raise HTTPException(409, "revision_conflict")
            problems = issues(c, self.settings, record, controlled=self.controlled)
            value = {
                "actor": actor["UserId"],
                "session": actor["SessionId"],
                "auth_version": actor["AuthVersion"],
                "record_revision": record["Revision"],
                "record_hash": key(record["Document"]),
                "issues": problems,
            }
            found = one(
                c,
                "SELECT Document FROM crm_campaign8.Event WHERE InstitutionId=? AND EventId=?",
                institution(self.settings),
                str(body.operation_id),
            )
            if found:
                if json.loads(found["Document"]) != value:
                    raise HTTPException(409, "operation_conflict")
            else:
                event(
                    c,
                    self.settings,
                    "preflight",
                    value,
                    record=id,
                    actor=actor["UserId"],
                    source=key("preflight", body.operation_id),
                    event_id=str(body.operation_id),
                )
            return {
                "id": str(body.operation_id),
                "valid": not problems,
                "issues": problems,
                "revision": record["Revision"],
                "no_provider_POST": True,
            }

    def action(self, auth, id, action, body):
        from app.institutional.campaign_runtime import enroll, resume_run, retire

        with self.tx(
            auth,
            True,
            recent=action in {"activate", "enroll", "resume", "retry", "restore"},
        ) as (c, actor):
            h, prior = replay(
                c,
                self.settings,
                actor["UserId"],
                str(body.operation_id),
                "campaign8." + action,
                id,
                body.model_dump(mode="json"),
            )
            if prior:
                return prior
            record = get(c, self.settings, id)
            if body.revision != record["Revision"]:
                raise HTTPException(409, "revision_conflict")
            if not body.confirmed:
                raise HTTPException(409, "campaign_review_required")
            if action in {"activate", "enroll", "resume", "retry"} and record[
                "Kind"
            ] not in {"template", "segment"}:
                authorize(c, self.settings, auth, "inbox.write")
            if action == "activate":
                if record["State"] == "active":
                    raise HTTPException(409, "campaign_already_active")
                pre = one(
                    c,
                    "SELECT * FROM crm_campaign8.Event WHERE InstitutionId=? AND EventId=? AND RecordId=? AND Kind='preflight'",
                    institution(self.settings),
                    str(body.preflight_id),
                    id,
                )
                expected = {
                    "actor": actor["UserId"],
                    "session": actor["SessionId"],
                    "auth_version": actor["AuthVersion"],
                    "record_revision": record["Revision"],
                    "record_hash": key(record["Document"]),
                    "issues": [],
                }
                if (
                    not pre
                    or pre["CreatedAt"] < now() - timedelta(minutes=10)
                    or json.loads(pre["Document"]) != expected
                ):
                    raise HTTPException(409, "campaign_preflight_required")
                if issues(c, self.settings, record, controlled=self.controlled):
                    raise HTTPException(409, "campaign_preflight_invalid")
                if (
                    record["Kind"] == "trigger"
                    and c.execute(
                        "SELECT COUNT(*) FROM crm_campaign8.Record WHERE InstitutionId=? AND Kind='trigger' AND State='active' AND RecordId<>?",
                        institution(self.settings),
                        id,
                    ).fetchval()
                    >= 100
                ):
                    raise HTTPException(413, "campaign_trigger_scope_limit")
                c.execute(
                    "UPDATE crm_campaign8.Record SET State='active',Revision=Revision+1,ActorId=?,ActorAuthVersion=?,ActorSessionId=?,ApprovedAt=SYSUTCDATETIME(),UpdatedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND RecordId=?",
                    actor["UserId"],
                    actor["AuthVersion"],
                    actor["SessionId"],
                    institution(self.settings),
                    id,
                )
                result = public(get(c, self.settings, id))
            elif action in {"pause", "archive"}:
                retire(c, self.settings, record, "campaign_" + action)
                c.execute(
                    "UPDATE crm_campaign8.Record SET State=?,Revision=Revision+1,Epoch=Epoch+1,UpdatedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND RecordId=?",
                    "paused" if action == "pause" else "archived",
                    institution(self.settings),
                    id,
                )
                result = public(get(c, self.settings, id))
            elif action == "enroll":
                if (
                    record["Kind"] not in {"flow", "campaign"}
                    or record["State"] != "active"
                ):
                    raise HTTPException(409, "campaign_active_flow_required")
                if not body.identity_ids:
                    raise HTTPException(422, "campaign_select_identities")
                results = [
                    enroll(
                        c,
                        self.settings,
                        record,
                        str(v),
                        key("manual", body.operation_id, v),
                        controlled=self.controlled,
                    )
                    for v in dict.fromkeys(body.identity_ids)
                ]
                result = {"items": results}
            elif action in {"resume", "retry"}:
                results = []
                for run_id in body.identity_ids:
                    results.append(
                        resume_run(
                            c,
                            self.settings,
                            record,
                            str(run_id),
                            retry=action == "retry",
                            controlled=self.controlled,
                        )
                    )
                result = {"items": results}
            elif action == "cancel_runs":
                from app.institutional.campaign_runtime import stop

                for id_run in body.identity_ids:
                    run = one(
                        c,
                        "SELECT * FROM crm_campaign8.Enrollment WHERE InstitutionId=? AND FlowId=? AND EnrollmentId=?",
                        institution(self.settings),
                        record["RecordId"],
                        str(id_run),
                    )
                    if not run:
                        raise HTTPException(404, "campaign_execution_not_found")
                    stop(c, self.settings, run, "campaign_user_cancel")
                result = {"cancelled": len(body.identity_ids)}
            else:
                raise HTTPException(404, "campaign_action_not_found")
            record_operation(
                c,
                self.settings,
                actor["UserId"],
                str(body.operation_id),
                "campaign8." + action,
                id,
                h,
                result,
            )
            audit(c, self.settings, actor["UserId"], "campaign8." + action, id)
            return result

    def copy_restore(self, auth, id, action, body):
        from app.institutional.campaign_models import Save

        with self.tx(auth, True, recent=action == "restore") as (c, actor):
            digest, prior = replay(
                c,
                self.settings,
                actor["UserId"],
                str(body.operation_id),
                "campaign8." + action,
                id,
                body.model_dump(mode="json"),
            )
            if prior:
                return prior
            source = get(c, self.settings, id)
            if body.revision != source["Revision"] or not body.confirmed:
                raise HTTPException(409, "campaign_review_required")
            if action == "restore":
                version = one(
                    c,
                    "SELECT * FROM crm_campaign8.Version WHERE InstitutionId=? AND RecordId=? AND VersionNo=?",
                    institution(self.settings),
                    id,
                    body.version,
                )
                if not version:
                    raise HTTPException(404, "campaign_version_not_found")
                target = id
                name = version["Name"]
                content = json.loads(version["Document"])
                revision = source["Revision"]
            else:
                target = str(body.operation_id)
                name = body.name or (source["Name"][:140] + " · Copia")
                content = json.loads(source["Document"])
                revision = 0
            value = Save(
                operation_id=body.operation_id,
                revision=revision,
                reason=body.reason,
                kind=source["Kind"],
                name=name,
                document=content,
            )
            result = self.write_record(c, actor, target, value)
            record_operation(
                c,
                self.settings,
                actor["UserId"],
                str(body.operation_id),
                "campaign8." + action,
                id,
                digest,
                result,
            )
            return result

    def simulate(self, auth, id, body):
        with self.tx(auth) as (c, _):
            record = get(c, self.settings, id)
            doc = json.loads(record["Document"])
            p = (
                person(c, self.settings, str(body.identity_id))
                if body.identity_id
                else dict(
                    Name=body.sample.get("name", "Aspirante ficticio"),
                    Phone=body.sample.get("phone", ""),
                    City=body.sample.get("city", ""),
                    Program=body.sample.get("program", ""),
                    Stage=body.sample.get("stage", ""),
                    Schedule=body.sample.get("schedule", ""),
                    CustomValues=packed({"email": body.sample.get("email", "")}),
                    IncomingText=body.sample.get("message", ""),
                    Tags="",
                    CanonicalContactId="",
                    ProgramId=None,
                )
            )
            if record["Kind"] == "template":
                return {
                    "text": render_crm(doc, p, record["Name"]),
                    "scope": "CRM_preview_not_Meta_approval",
                    "provider_POSTs": 0,
                }
            if record["Kind"] not in {"flow", "campaign"}:
                return {
                    "matches": matches(
                        p, doc.get("conditions", doc.get("filters", {}))
                    ),
                    "provider_POSTs": 0,
                }
            timeline = []
            time = scheduled(doc["scheduled_local"], doc["timezone"]) or now()
            for i, step in enumerate(doc["steps"]):
                time = next_allowed(time, doc["quiet_hours"])
                if step["kind"] == "wait":
                    time += timedelta(minutes=step["wait_minutes"])
                    text = "Espera persistida"
                elif step["kind"] == "condition":
                    result = matches(p, step["conditions"])
                    text = "Condición cumplida" if result else "Condición no cumplida"
                    timeline.append(
                        {"index": i, "kind": "condition", "at": utc(time), "text": text}
                    )
                    if not result and step["on_false"] == "stop":
                        break
                    continue
                else:
                    selected = send_document(doc, step, body.variant)
                    text = "Selecciona una plantilla Meta"
                    if step["crm_template_id"]:
                        from app.institutional.campaign_chat import content

                        text = content(
                            c,
                            self.settings,
                            doc,
                            step,
                            body.variant,
                            p,
                            record["Name"],
                            preview=True,
                        )
                    elif selected["template_id"]:
                        row = meta.latest(
                            c,
                            self.settings,
                            selected["template_id"],
                            selected["template_version"],
                        )
                        _, text = meta.parameters(row, selected, p, record["Name"])
                timeline.append(
                    {"index": i, "kind": step["kind"], "at": utc(time), "text": text}
                )
            return {
                "timeline": timeline,
                "variant": body.variant,
                "provider_POSTs": 0,
                "simulation_only": True,
                "uses_existing_identity": body.identity_id is not None,
            }

    def runs(self, auth, id, offset=0, q="", state="", step=-1):
        with self.tx(auth) as (c, _):
            record = get(c, self.settings, id)
            clauses = ["r.InstitutionId=?", "r.FlowId=?"]
            params = [institution(self.settings), id]
            if q.strip():
                clauses.append("p.Name LIKE ?")
                params.append("%" + q.strip().replace("%", "[%]").replace("_", "[_]") + "%")
            if state:
                if state not in OPEN | {"completed", "cancelled", "failed"}:
                    raise HTTPException(422, "campaign_execution_state_invalid")
                clauses.append("r.State=?")
                params.append(state)
            steps = json.loads(record["Document"]).get("steps", [])
            if step >= 0:
                if step >= len(steps) or steps[step]["kind"] != "send":
                    raise HTTPException(422, "campaign_execution_step_invalid")
                start = step
                while start and steps[start - 1]["kind"] != "send":
                    start -= 1
                clauses.extend(["r.VersionNo=?", "r.StepIndex>=?", "r.StepIndex<=?",
                                "r.State IN('waiting','queued','paused','uncertain')"])
                params.extend([record["CurrentVersion"], start, step])
            source = " FROM crm_campaign8.Enrollment r JOIN crm.Contact p ON p.ContactId=r.CanonicalContactId "
            where = " WHERE " + " AND ".join(clauses)
            total = c.execute(
                "SELECT COUNT(*)" + source + where, *params,
            ).fetchval()
            values = rows(
                c,
                "SELECT r.*,p.Name,v.Document AS VersionDocument" + source +
                " JOIN crm_campaign8.Version v ON v.InstitutionId=r.InstitutionId AND v.RecordId=r.FlowId AND v.VersionNo=r.VersionNo" +
                where + " ORDER BY r.CreatedAt DESC,r.EnrollmentId OFFSET ? ROWS FETCH NEXT 100 ROWS ONLY",
                *params, offset,
            )
            return {
                "items": [
                    dict(
                        id=uid(str(v["EnrollmentId"])),
                        identity_id=uid(str(v["IdentityId"])),
                        name=v["Name"],
                        state=v["State"],
                        step_index=v["StepIndex"],
                        version=v["VersionNo"],
                        variant=v["Variant"],
                        due_at=utc(v["DueAt"]),
                        reason=v["LastReason"],
                        next_step=next_message_name(v),
                    )
                    for v in values
                ],
                "total": total,
                "offset": offset,
                "has_more": total > offset + 100,
                "record": public(record),
                "lists": [{"value": i, "name": v.get("name") or f"Mensaje {i + 1}"}
                          for i, v in enumerate(steps) if v["kind"] == "send"],
            }

    def trace(self, auth, id, run_id):
        with self.tx(auth) as (c, _):
            if not c.execute(
                "SELECT 1 FROM crm_campaign8.Enrollment WHERE InstitutionId=? AND FlowId=? AND EnrollmentId=?",
                institution(self.settings),
                id,
                run_id,
            ).fetchone():
                raise HTTPException(404, "campaign_execution_not_found")
            found = rows(
                c,
                "SELECT * FROM crm_campaign8.Event WHERE InstitutionId=? AND EnrollmentId=? ORDER BY CreatedAt,EventId",
                institution(self.settings),
                run_id,
            )
            if len(found) > 1000:
                raise HTTPException(413, "campaign_trace_scope_limit")
            return {
                "events": [
                    dict(
                        kind=v["Kind"],
                        at=utc(v["CreatedAt"]),
                        data=json.loads(v["Document"]),
                    )
                    for v in found
                ],
                "steps": [
                    dict(
                        id=uid(str(v["StepId"])),
                        index=v["StepIndex"],
                        kind=v["Kind"],
                        state=v["State"],
                        due_at=utc(v["DueAt"]),
                        native_campaign_id=uid(str(v["NativeCampaignId"]))
                        if v["NativeCampaignId"]
                        else None,
                        reason=v["LastReason"],
                    )
                    for v in rows(
                        c,
                        "SELECT * FROM crm_campaign8.Step WHERE InstitutionId=? AND EnrollmentId=? ORDER BY StepIndex",
                        institution(self.settings),
                        run_id,
                    )
                ],
            }

    def metrics(self, auth, id):
        with self.tx(auth) as (c, _):
            get(c, self.settings, id)
            runs = rows(
                c,
                "SELECT Variant,State,COUNT(*) AS Total FROM crm_campaign8.Enrollment WHERE InstitutionId=? AND FlowId=? GROUP BY Variant,State",
                institution(self.settings),
                id,
            )
            # All immutable attempts participate, not only CurrentQueueId. A failed
            # attempt remains visible after a reviewed successful retry.
            from app.institutional.campaign_metrics import attempts_query
            jobs = rows(
                c, attempts_query(materialized=getattr(self.settings, "postgres_deployment", False)),
                institution(self.settings), id,
            )
            if len(jobs) > 100000:
                raise HTTPException(413, "campaign_metrics_scope_limit")
            variants = []
            for variant in ["A", "B"]:
                selected = [v for v in jobs if v["Variant"] == variant]
                people = sum(v["Total"] for v in runs if v["Variant"] == variant)
                replied = {str(v["EnrollmentId"]) for v in selected if v["Replied"]}
                variants.append(
                    dict(
                        variant=variant,
                        enrollments=people,
                        attempts=len(selected),
                        accepted=sum(v["ExternalId"] is not None for v in selected),
                        delivered=sum(
                            v["State"] in {"delivered", "read"} for v in selected
                        ),
                        read=sum(v["State"] == "read" for v in selected),
                        failed=sum(v["State"] == "failed" for v in selected),
                        uncertain=sum(v["State"] == "uncertain" for v in selected),
                        replied=len(replied),
                        reply_percent=round(len(replied) * 100 / people, 2)
                        if people
                        else None,
                    )
                )
            return {
                "variants": variants,
                "assignment": "institution_flow_version_canonical_contact_HMAC_v1",
                "attribution": "authenticated_explicit_reply_context_same_account_and_identity",
                "automatic_winner": False,
                "conversion_inferred": False,
            }
