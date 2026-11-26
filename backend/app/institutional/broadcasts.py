"""Institutional broadcasts on C10 identities/outbox. No academic queries or writes."""

import csv
import io
import json
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from app.institutional import broadcast_templates as templates
from app.institutional import broadcast_variables
from app.institutional import broadcast_audience as segments
from app.institutional.auth import authorize
from app.institutional.broadcast_models import scheduled
from app.institutional.channel_operations import account, configuration
from app.institutional.channel_provider import provider_account
from app.institutional.db import (
    audit,
    bound_hash,
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
from app.modules.channels import providers

VERSION = "cbn-institutional-broadcast-p7-v1"


def current(c, s, key):
    value = one(
        c,
        (
            "SELECT * FROM crm_broadcast7.Campaign "
            "WHERE InstitutionId=? AND CampaignId=?"
        ),
        institution(s),
        key,
    )
    if not value:
        raise HTTPException(404, "broadcast_not_found")
    return value


def public_campaign(v):
    return {
        "id": uid(str(v["CampaignId"])),
        "name": v["Name"],
        "state": v["State"],
        "revision": v["Revision"],
        "epoch": v["Epoch"],
        "integration_id": uid(str(v["IntegrationId"])),
        "template_id": uid(str(v["TemplateId"])),
        "template_version": v["TemplateVersion"],
        "document": json.loads(v["Document"]),
        "scheduled_at": utc(v["ScheduledAt"]),
        "timezone": v["Timezone"],
    }


def public_template(v):
    return {
        "id": uid(str(v["TemplateId"])),
        "version": v["VersionNo"],
        "integration_id": uid(str(v["IntegrationId"])),
        "provider_id": v["ProviderId"],
        "name": v["Name"],
        "language": v["Language"],
        "category": v["Category"],
        "status": v["ProviderStatus"],
        "origin": v["Origin"],
        "paused": bool(v["Paused"]),
        "components": json.loads(v["Definition"]),
        "metadata": json.loads(v["ProviderMetadata"]),
        "observed_at": utc(v["ObservedAt"]),
    }


def catalog(c, s, integration=None):
    where = " AND t.IntegrationId=?" if integration else ""
    return rows(
        c,
        ("SELECT t.* FROM crm_broadcast7.Template t WHERE t.InstitutionId=?")
        + where
        + (
            " AND NOT EXISTS(SELECT 1 FROM crm_broa"
            "dcast7.Template x WHERE x.InstitutionI"
            "d=t.InstitutionId AND x.TemplateId=t.T"
            "emplateId AND x.VersionNo>t.VersionNo)"
            " ORDER BY t.Name,t.Language"
        ),
        institution(s),
        *([integration] if integration else []),
    )


def consent(c, s, identity):
    return one(
        c,
        (
            "SELECT TOP(1) * FROM crm_broadcast7.Co"
            "nsent WHERE InstitutionId=? AND Identi"
            "tyId=? ORDER BY VersionNo DESC"
        ),
        institution(s),
        identity,
    )


def same(value, other):
    return str(value).lower() == str(other).lower()


def enabled(c, s):
    flags = setting(c, s, "modules")["document"]["enabled"]
    return all(flags.get(v, False) for v in ["broadcasts", "channels", "inbox"])


def authority(c, s, campaign):
    # Durable scheduled approval survives expiry, but explicit session/user/role
    # revocation still fences it. No credentials or anonymous identity are used.
    value = one(
        c,
        (
            "SELECT u.*,r.Actions,s.SessionId FROM "
            "crm_access.AccessUser u JOIN crm_acces"
            "s.Role r ON r.InstitutionId=u.Institut"
            "ionId AND r.RoleKey=u.RoleKey JOIN crm"
            "_access.Session s ON s.InstitutionId=u"
            ".InstitutionId AND s.UserId=u.UserId W"
            "HERE u.InstitutionId=? AND u.UserId=? "
            "AND s.SessionId=? AND s.RevokedAt IS N"
            "ULL AND u.Active=1 AND r.Active=1 AND "
            "u.AuthVersion=?"
        ),
        institution(s),
        campaign["ActorId"],
        campaign["ActorSessionId"],
        campaign["ActorAuthVersion"],
    )
    if (
        not value
        or not {"campaigns.manage", "inbox.write"} <= set(json.loads(value["Actions"]))
        or not enabled(c, s)
    ):
        raise HTTPException(403, "broadcast_authority_revoked")
    value["UserId"], value["SessionId"] = (
        uid(str(value["UserId"])),
        uid(str(value["SessionId"])),
    )
    return value


def candidate_rows(c, s, document):
    where = ["i.InstitutionId=?", "i.IntegrationId=?"]
    args = [institution(s), document["integration_id"]]
    for field, column in [
        ("contact_ids", "p.ContactId"),
        ("identity_ids", "i.IdentityId"),
        ("program_ids", "p.ProgramId"),
        ("stages", "p.Stage"),
        ("cities", "p.City"),
        ("schedules", "p.Schedule"),
        ("contact_types", "p.Type"),
    ]:
        values = document["filters"].get(field, [])
        if values:
            cast = (
                "CONVERT(uniqueidentifier,value)"
                if field in {"contact_ids", "identity_ids"}
                else "TRY_CONVERT(int,value)"
                if field == "program_ids"
                else "value"
            )
            where.append(column + " IN(SELECT " + cast + " FROM OPENJSON(?))")
            args.append(json.dumps(values))
    result = rows(
        c,
        (
            "SELECT TOP(5001) i.IdentityId,i.Integr"
            "ationId,i.ExternalId,i.ContactId AS Or"
            "iginalContactId,i.ConversationId,i.Las"
            "tIncomingAt,p.*,v.ControlMode,v.State "
            "AS ConversationState,COALESCE(ctrl.Epo"
            "ch,0) AS ControlEpoch FROM crm_channel"
            "s2.ExternalIdentity i JOIN crm.Convers"
            "ation v ON v.ConversationId=i.Conversa"
            "tionId AND v.ContactId=i.ContactId LEF"
            "T JOIN crm_workspace.Merge g ON g.Sour"
            "ceContactId=i.ContactId AND g.Active=1"
            " JOIN crm.Contact p ON p.ContactId=COA"
            "LESCE(g.TargetContactId,i.ContactId) L"
            "EFT JOIN crm_channels.ConversationCont"
            "rol ctrl ON ctrl.ConversationId=v.Conv"
            "ersationId WHERE "
        )
        + " AND ".join(where)
        + (" ORDER BY p.ContactId,i.LastIncomingAt DESC,i.IdentityId"),
        *args,
    )
    if len(result) > 5000:
        raise HTTPException(413, "broadcast_audience_scope_limit")
    requested = {v.casefold().strip() for v in document["filters"].get("tags", [])}
    return [
        v
        for v in result
        if not requested
        or (bool(requested & set(
            x.strip().casefold() for x in v["Tags"].replace(";", ",").replace("|", ",").split(",")
        )) if document["filters"].get("tag_match") == "any" else requested <= set(
            x.strip().casefold()
            for x in v["Tags"].replace(";", ",").replace("|", ",").split(",")
        ))
    ]


def audience(c, s, campaign, *, controlled=False):
    document = json.loads(campaign["Document"])
    if document["filters"].get("identity_ids"):
        from app.institutional.broadcast_routes import validate_selection

        validate_selection(c, s, document)
    from app.modules.crm_configuration.application.service import read_configuration

    crm_config, _ = read_configuration(c, foundation=True)
    segments.configuration(document, crm_config.fields)
    as_of = datetime.now(timezone.utc).astimezone(ZoneInfo(document.get("timezone", "America/Bogota"))).date()
    allowed_custom_fields = set()
    if any(v.get("source") == "custom_field" for v in document.get("variables", {}).values()):
        allowed_custom_fields = {f.key for f in crm_config.fields if f.active}
    item = account(c, s, str(campaign["IntegrationId"]))
    template = None
    global_reasons = []
    try:
        template = templates.approved(c, s, campaign, item, controlled=controlled)
    except HTTPException as e:
        global_reasons.append(e.detail)
    if (
        item["Channel"] != "whatsapp"
        or item["RequestedStatus"] != "connected"
        or item["VerifiedStatus"] != "verified"
        or item["ApplicationState"] == "retired"
    ):
        global_reasons.append("broadcast_verified_whatsapp_account_required")
    if not enabled(c, s):
        global_reasons.append("module_disabled")
    # One no-contact decision on any member of the current identity group wins.
    no_contact = {
        uid(str(v[0]))
        for v in c.execute(
            (
                "SELECT DISTINCT COALESCE(g.TargetConta"
                "ctId,v.ContactId) FROM crm_strategy.Ev"
                "aluationPlan e JOIN crm.Conversation v"
                " ON v.ConversationId=e.ConversationId "
                "LEFT JOIN crm_workspace.Merge g ON g.S"
                "ourceContactId=v.ContactId AND g.Activ"
                "e=1 WHERE JSON_VALUE(e.DocumentJson,'$"
                ".noContact')='true'"
            )
        ).fetchall()
    }
    prior_effects = rows(
        c,
        (
            "SELECT r.IdentityId,COALESCE(g.TargetC"
            "ontactId,r.ContactId) AS CanonicalId F"
            "ROM crm_broadcast7.Recipient r JOIN cr"
            "m_broadcast7.Attempt a ON a.Institutio"
            "nId=r.InstitutionId AND a.RecipientId="
            "r.RecipientId JOIN crm_channels2.SendJ"
            "ob q ON q.InstitutionId=a.InstitutionI"
            "d AND q.QueueId=a.QueueId LEFT JOIN cr"
            "m_workspace.Merge g ON g.SourceContact"
            "Id=r.ContactId AND g.Active=1 WHERE r."
            "InstitutionId=? AND r.CampaignId=? AND"
            " (q.ExternalId IS NOT NULL OR q.State "
            "IN('sending','uncertain'))"
        ),
        institution(s),
        campaign["CampaignId"],
    )
    from app.institutional.siie_classification import phone_hash, promotion_exclusions
    registered_siie, registered_phones = promotion_exclusions(c, s)
    from app.institutional.commercial_followup import progress_map, exclusion
    progress = progress_map(c, s)
    candidates = []
    for person in candidate_rows(c, s, document):
        if not segments.matches(person, document, as_of):
            continue
        reasons = list(global_reasons)
        from app.institutional.prospect_source_status import promotion_exclusion
        source_reason = promotion_exclusion(person.get("CustomValues"), document)
        if source_reason:
            reasons.append(source_reason)
        if getattr(s, "postgres_deployment", False):
            progress_reason = exclusion(progress.get(uid(str(person["ContactId"])), {}), person["Stage"], document)
            if progress_reason:
                reasons.append(progress_reason)
        if uid(str(person["ContactId"])) in registered_siie or phone_hash(s, person.get("Phone", "")) in registered_phones:
            reasons.append("siie_registered_no_promotions")
        if s.ticket.get("version") in {'cbn-institutional-ads-p9-v1', 'cbn-institutional-campaign-p8-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
            from app.institutional.campaigns import marketing_allowed

            if not marketing_allowed(
                c, s, dict(person, IdentityId=person["IdentityId"])
            ):
                reasons.append("marketing_consent_required")
        if any(
            same(v["CanonicalId"], person["ContactId"])
            and not same(v["IdentityId"], person["IdentityId"])
            for v in prior_effects
        ):
            reasons.append("canonical_contact_prior_effect")
        key = uid(str(person["IdentityId"]))
        grant = consent(c, s, key)
        if person["ConversationState"] == "closed":
            reasons.append("conversation_closed")
        if person["ControlMode"] == "human":
            reasons.append("human_control")
        if uid(str(person["ContactId"])) in no_contact:
            reasons.append("no_contact")
        if (
            not grant
            or not same(grant["IntegrationId"], item["IntegrationId"])
            or grant["State"] != "granted"
            or not grant["ExpiresAt"]
            or grant["ExpiresAt"] <= datetime.utcnow()
        ):
            reasons.append("marketing_consent_required")
        if (
            not person["ExternalId"].isdigit()
            or not 5 <= len(person["ExternalId"]) <= 20
        ):
            reasons.append("whatsapp_identity_invalid")
        rendered = None
        text = ""
        if template:
            try:
                rendered, text = templates.parameters(
                    template, document, person, campaign["Name"],
                    allowed_custom_fields=allowed_custom_fields,
                )
            except HTTPException as e:
                reasons.append(e.detail)
        candidates.append(
            {
                "person": person,
                "identity_id": key,
                "contact_id": uid(str(person["ContactId"])),
                "conversation_id": uid(str(person["ConversationId"])),
                "name": person["Name"],
                "phone": person["ExternalId"],
                "program": person["Program"],
                "stage": person["Stage"],
                "consent": grant,
                "reasons": list(dict.fromkeys(reasons)),
                "eligible": not reasons,
                "audience_profile": segments.details(person, document, as_of)[0],
                "template": rendered,
                "text": text,
                "template_record": template,
            }
        )
    # Prefer an eligible account identity, then the newest incoming. One person
    # receives at most one message even after a reversible CRM merge.
    selected = set()
    for v in sorted(
        candidates,
        key=lambda v: (
            bool(v["reasons"]),
            v["contact_id"],
            -(
                (v["person"]["LastIncomingAt"] or datetime.min) - datetime(1970, 1, 1)
            ).total_seconds(),
            v["identity_id"],
        ),
    ):
        if v["contact_id"] in selected:
            v["reasons"].append("duplicate_contact")
            v["eligible"] = False
        elif v["eligible"]:
            selected.add(v["contact_id"])
    return candidates, item


def preview(c, s, campaign, *, controlled=False):
    found, _ = audience(c, s, campaign, controlled=controlled)
    reasons = Counter(reason for v in found for reason in v["reasons"])
    return {
        "items": [
            {
                k: v[k]
                for k in [
                    "identity_id",
                    "contact_id",
                    "conversation_id",
                    "name",
                    "phone",
                    "program",
                    "stage",
                    "reasons",
                    "eligible",
                    "text",
                ]
            }
            for v in found
        ],
        "counts": {
            "matched": len(found),
            "eligible": sum(v["eligible"] for v in found),
            "excluded": sum(not v["eligible"] for v in found),
        },
        "exclusions": dict(reasons),
        "authority": "declared_CRM_not_verified_SIIE",
        "external_acceptance": False if controlled else None,
    }


def cancel(c, s, key, reason):
    c.execute(
        (
            "UPDATE q SET State='cancelled',LastErrorCode=?,"
            "CompletedAt=SYSUTCDATETIME() FROM crm_channels2.SendJob q "
            "WHERE q.InstitutionId=? AND q.State='queued' AND EXISTS("
            "SELECT 1 FROM crm_broadcast7.Attempt a "
            "JOIN crm_broadcast7.Recipient r ON r.InstitutionId=a.InstitutionId "
            "AND r.RecipientId=a.RecipientId WHERE a.InstitutionId=q.InstitutionId "
            "AND a.QueueId=q.QueueId AND r.CampaignId=?)"
        ),
        reason,
        institution(s),
        key,
    )
    c.execute(
        (
            "UPDATE crm_broadcast7.Recipient SET St"
            "ate='cancelled',LastError=?,UpdatedAt="
            "SYSUTCDATETIME() WHERE InstitutionId=?"
            " AND CampaignId=? AND State='prepared'"
        ),
        reason,
        institution(s),
        key,
    )


class Broadcasts:
    def __init__(self, settings, request=None):
        self.settings = settings
        self.request = request or providers.request
        self.controlled = request is not None

    @contextmanager
    def tx(self, auth, write=False, recent=False):
        with transaction(self.settings, write, anonymous=True) as c:
            actor = authorize(c, self.settings, auth, "campaigns.manage", recent=recent)
            authorize(c, self.settings, auth, "crm.read")
            if not setting(c, self.settings, "modules")["document"]["enabled"].get(
                "broadcasts", False
            ):
                raise HTTPException(403, "module_disabled")
            yield c, actor

    def metadata(self, auth):
        from app.institutional.agent_catalog import Catalog
        from app.modules.crm_configuration.application.service import read_configuration

        with self.tx(auth) as (c, _):
            accounts = rows(
                c,
                (
                    "SELECT i.IntegrationId,i.DisplayName,i"
                    ".RequestedStatus,i.VerifiedStatus,a.Eg"
                    "ressProfile FROM crm_channels2.Integra"
                    "tion i JOIN crm_channels2.Application "
                    "a ON a.InstitutionId=i.InstitutionId A"
                    "ND a.ApplicationId=i.ApplicationId WHE"
                    "RE i.InstitutionId=? AND i.Channel='wh"
                    "atsapp' AND i.RequestedStatus<>'retire"
                    "d' ORDER BY i.DisplayName"
                ),
                institution(self.settings),
            )
            config, _ = read_configuration(c, foundation=True)
            return {
                "accounts": [
                    {
                        "id": uid(str(v["IntegrationId"])),
                        "name": v["DisplayName"],
                        "requested_status": v["RequestedStatus"],
                        "verified_status": v["VerifiedStatus"],
                        "provider_profile": v["EgressProfile"],
                    }
                    for v in accounts
                ],
                "templates": [public_template(v) for v in catalog(c, self.settings)],
                "programs": Catalog(self.settings).programs(c, 0, 300)["items"],
                "stages": [v.label for v in config.stages if v.active],
                "variables": broadcast_variables.catalog(config.fields),
                "crm_fields": [f.model_dump() for f in config.fields if f.active],
                "tags": [t for t in config.tags if t not in config.inactiveTags],
                "audience_facets": {
                    key: [v["Value"] for v in rows(c, f"SELECT TOP(500) {column} AS Value FROM crm.Contact WHERE {column}<>'' GROUP BY {column} ORDER BY {column}")]
                    for key, column in [("schedules", "Schedule"), ("contact_types", "Type"), ("cities", "City")]
                },
                "outbound_enabled": bool(
                    configuration(c, self.settings)["OutboundEnabled"]
                ),
                "external_acceptance": False,
                "audience_import_supported": False,
                "audience_limit": 5000,
            }

    def listing(self, auth):
        with self.tx(auth) as (c, _):
            suffix = (
                " AND NOT EXISTS(SELECT 1 FROM crm_campaign8.Step step WHERE step.InstitutionId=b.InstitutionId AND step.NativeCampaignId=b.CampaignId)"
                if self.settings.ticket.get("version") in {'cbn-institutional-ads-p9-v1', 'cbn-institutional-campaign-p8-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}
                else ""
            )
            return {
                "items": [
                    public_campaign(v)
                    for v in rows(
                        c,
                        "SELECT b.* FROM crm_broadcast7.Campaign b WHERE b.InstitutionId=?"
                        + suffix
                        + " ORDER BY b.UpdatedAt DESC,b.CampaignId",
                        institution(self.settings),
                    )
                ]
            }

    def get(self, auth, key):
        with self.tx(auth) as (c, _):
            return public_campaign(current(c, self.settings, key))

    def save(self, auth, key, body):
        document = body.model_dump(
            mode="json", exclude={"operation_id", "revision", "reason"}
        )
        with self.tx(auth, True) as (c, actor):
            from app.modules.crm_configuration.application.service import read_configuration

            crm_config, _ = read_configuration(c, foundation=True)
            segments.configuration(document, crm_config.fields)
            if body.sent_stage:
                authorize(c, self.settings, auth, "crm.write")
                if not any(
                    v.active and v.label == body.sent_stage
                    for v in crm_config.stages
                ):
                    raise HTTPException(409, "broadcast_sent_stage_unavailable")
            if (
                self.settings.ticket.get("version") in {'cbn-institutional-ads-p9-v1', 'cbn-institutional-campaign-p8-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}
                and c.execute(
                    "SELECT 1 FROM crm_campaign8.Step WHERE InstitutionId=? AND NativeCampaignId=?",
                    institution(self.settings),
                    key,
                ).fetchone()
            ):
                raise HTTPException(409, "campaign_child_managed_from_flows")
            h, prior = replay(
                c,
                self.settings,
                actor["UserId"],
                str(body.operation_id),
                "broadcast.edit",
                key,
                body.model_dump(mode="json"),
            )
            if prior:
                return prior
            item = account(c, self.settings, str(body.integration_id))
            if body.filters.identity_ids:
                from app.institutional.broadcast_routes import validate_selection

                validate_selection(c, self.settings, document)
            if item["Channel"] != "whatsapp":
                raise HTTPException(422, "broadcast_whatsapp_required")
            template = templates.latest(
                c, self.settings, str(body.template_id), body.template_version
            )
            if json.loads(template["ProviderMetadata"]).get("library_removed"):
                raise HTTPException(409, "broadcast_template_removed_from_library")
            if not same(template["IntegrationId"], item["IntegrationId"]):
                raise HTTPException(409, "broadcast_template_account_mismatch")
            old = one(
                c,
                (
                    "SELECT * FROM crm_broadcast7.Campaign "
                    "WHERE InstitutionId=? AND CampaignId=?"
                ),
                institution(self.settings),
                key,
            )
            if body.revision != (old["Revision"] if old else 0):
                raise HTTPException(409, "revision_conflict")
            if old:
                if old["State"] in {"running", "scheduled", "cancelled", "completed"}:
                    raise HTTPException(409, "broadcast_pause_before_edit")
                if c.execute(
                    (
                        "SELECT 1 FROM crm_broadcast7.Attempt a"
                        " JOIN crm_broadcast7.Recipient r ON r."
                        "InstitutionId=a.InstitutionId AND r.Re"
                        "cipientId=a.RecipientId JOIN crm_chann"
                        "els2.SendJob q ON q.InstitutionId=a.In"
                        "stitutionId AND q.QueueId=a.QueueId WH"
                        "ERE r.InstitutionId=? AND r.CampaignId"
                        "=? AND q.State IN('sending','uncertain"
                        "')"
                    ),
                    institution(self.settings),
                    key,
                ).fetchone():
                    raise HTTPException(
                        409, "broadcast_uncertain_requires_reconciliation"
                    )
                cancel(c, self.settings, key, "broadcast_edited")
                c.execute(
                    (
                        "UPDATE crm_broadcast7.Campaign SET Nam"
                        "e=?,IntegrationId=?,TemplateId=?,Templ"
                        "ateVersion=?,Document=?,State='draft',"
                        "Revision=Revision+1,Epoch=Epoch+1,Sche"
                        "duledAt=?,Timezone=?,ActorId=NULL,Acto"
                        "rAuthVersion=NULL,ActorSessionId=NULL,"
                        "ApprovedAt=NULL,UpdatedAt=SYSUTCDATETI"
                        "ME() WHERE InstitutionId=? AND Campaig"
                        "nId=?"
                    ),
                    body.name,
                    str(body.integration_id),
                    str(body.template_id),
                    body.template_version,
                    templates.encoded(document),
                    scheduled(body.scheduled_local, body.timezone),
                    body.timezone,
                    institution(self.settings),
                    key,
                )
            else:
                c.execute(
                    (
                        "INSERT crm_broadcast7.Campaign(Institu"
                        "tionId,CampaignId,Name,IntegrationId,T"
                        "emplateId,TemplateVersion,Document,Sta"
                        "te,Revision,Epoch,ScheduledAt,Timezone"
                        ") VALUES(?,?,?,?,?,?,?,'draft',1,1,?,?"
                        ")"
                    ),
                    institution(self.settings),
                    key,
                    body.name,
                    str(body.integration_id),
                    str(body.template_id),
                    body.template_version,
                    templates.encoded(document),
                    scheduled(body.scheduled_local, body.timezone),
                    body.timezone,
                )
            result = {
                "saved": True,
                "id": key,
                "revision": body.revision + 1,
                "state": "draft",
            }
            record_operation(
                c,
                self.settings,
                actor["UserId"],
                str(body.operation_id),
                "broadcast.edit",
                key,
                h,
                result,
            )
            audit(
                c,
                self.settings,
                actor["UserId"],
                "broadcast.edit",
                key,
                revision=body.revision + 1,
            )
            return result

    def preview(self, auth, key):
        with self.tx(auth) as (c, _):
            return preview(
                c,
                self.settings,
                current(c, self.settings, key),
                controlled=self.controlled,
            )

    def action(self, auth, key, action, body):
        if not body.confirmed:
            raise HTTPException(409, "broadcast_review_confirmation_required")
        with self.tx(auth, True, recent=action in {"activate", "retry"}) as (c, actor):
            if (
                self.settings.ticket.get("version") in {'cbn-institutional-ads-p9-v1', 'cbn-institutional-campaign-p8-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}
                and c.execute(
                    "SELECT 1 FROM crm_campaign8.Step WHERE InstitutionId=? AND NativeCampaignId=?",
                    institution(self.settings),
                    key,
                ).fetchone()
            ):
                raise HTTPException(409, "campaign_child_managed_from_flows")
            h, prior = replay(
                c,
                self.settings,
                actor["UserId"],
                str(body.operation_id),
                "broadcast." + action,
                key,
                body.model_dump(mode="json"),
            )
            if prior:
                return prior
            campaign = current(c, self.settings, key)
            if campaign["Revision"] != body.revision:
                raise HTTPException(409, "revision_conflict")
            if action in {"pause", "cancel"}:
                cancel(c, self.settings, key, "broadcast_" + action)
                c.execute(
                    (
                        "UPDATE crm_broadcast7.Campaign SET Sta"
                        "te=?,Revision=Revision+1,Epoch=Epoch+1"
                        ",UpdatedAt=SYSUTCDATETIME() WHERE Inst"
                        "itutionId=? AND CampaignId=?"
                    ),
                    "paused" if action == "pause" else "cancelled",
                    institution(self.settings),
                    key,
                )
                result = {
                    "saved": True,
                    "revision": body.revision + 1,
                    "state": "paused" if action == "pause" else "cancelled",
                }
            elif action in {"prepare", "activate"}:
                authorize(c, self.settings, auth, "inbox.write")
                if campaign["State"] in {"cancelled", "completed"}:
                    raise HTTPException(409, "broadcast_state_not_editable")
                if action == "prepare" and campaign["State"] in {
                    "running",
                    "scheduled",
                }:
                    raise HTTPException(409, "broadcast_pause_before_prepare")
                found, item = audience(
                    c, self.settings, campaign, controlled=self.controlled
                )
                prepared = 0
                for candidate in found:
                    if not candidate["eligible"]:
                        continue
                    old = one(
                        c,
                        (
                            "SELECT r.*,q.State AS QueueState,q.Ext"
                            "ernalId AS PreviousExternalId,q.Attemp"
                            "ts AS DispatchAttempts FROM crm_broadc"
                            "ast7.Recipient r LEFT JOIN crm_channel"
                            "s2.SendJob q ON q.InstitutionId=r.Inst"
                            "itutionId AND q.QueueId=r.CurrentQueue"
                            "Id WHERE r.InstitutionId=? AND r.Campa"
                            "ignId=? AND r.IdentityId=?"
                        ),
                        institution(self.settings),
                        key,
                        candidate["identity_id"],
                    )
                    if (
                        old
                        and old["CurrentQueueId"] is not None
                        and not (
                            old["QueueState"] == "cancelled"
                            and old["PreviousExternalId"] is None
                            and old["DispatchAttempts"] == 0
                        )
                    ):
                        continue
                    recipient = (
                        str(uuid4()) if not old else uid(str(old["RecipientId"]))
                    )
                    snapshot = {
                        "audience_profile": candidate["audience_profile"],
                        "sent_stage": json.loads(campaign["Document"]).get(
                            "sent_stage", "",
                        ),
                        "template": candidate["template"],
                        "body": candidate["text"],
                        "target": candidate["phone"],
                        "canonical_contact": candidate["contact_id"],
                        "template_material_revision": json.loads(
                            candidate["template_record"]["ProviderMetadata"]
                        )["material_revision"],
                    }
                    args = (
                        campaign["Revision"],
                        campaign["Epoch"],
                        candidate["consent"]["ConsentId"],
                        candidate["consent"]["VersionNo"],
                        candidate["person"]["ControlEpoch"],
                        item["RowVersion"],
                        templates.encoded(snapshot),
                    )
                    if old:
                        c.execute(
                            (
                                "UPDATE crm_broadcast7.Recipient SET Ca"
                                "mpaignRevision=?,CampaignEpoch=?,Conse"
                                "ntId=?,ConsentVersion=?,ControlEpoch=?"
                                ",AccountVersion=?,Snapshot=?,State='pr"
                                "epared',CurrentQueueId=NULL,LastError="
                                "NULL,UpdatedAt=SYSUTCDATETIME() WHERE "
                                "InstitutionId=? AND RecipientId=?"
                            ),
                            *args,
                            institution(self.settings),
                            recipient,
                        )
                    else:
                        c.execute(
                            (
                                "INSERT crm_broadcast7.Recipient(Campai"
                                "gnRevision,CampaignEpoch,ConsentId,Con"
                                "sentVersion,ControlEpoch,AccountVersio"
                                "n,Snapshot,InstitutionId,RecipientId,C"
                                "ampaignId,IdentityId,ContactId,Convers"
                                "ationId,State) VALUES(?,?,?,?,?,?,?,?,"
                                "?,?,?,?,?,'prepared')"
                            ),
                            *args,
                            institution(self.settings),
                            recipient,
                            key,
                            candidate["identity_id"],
                            candidate["person"]["OriginalContactId"],
                            candidate["conversation_id"],
                        )
                    prepared += 1
                if action == "activate":
                    if not c.execute(
                        (
                            "SELECT 1 FROM crm_broadcast7.Recipient"
                            " WHERE InstitutionId=? AND CampaignId="
                            "? AND State='prepared'"
                        ),
                        institution(self.settings),
                        key,
                    ).fetchone():
                        raise HTTPException(409, "broadcast_no_eligible_recipients")
                    c.execute(
                        (
                            "UPDATE crm_broadcast7.Campaign SET Sta"
                            "te=CASE WHEN ScheduledAt>SYSUTCDATETIM"
                            "E() THEN 'scheduled' ELSE 'running' EN"
                            "D,ActorId=?,ActorAuthVersion=?,ActorSe"
                            "ssionId=?,ApprovedAt=SYSUTCDATETIME(),"
                            "UpdatedAt=SYSUTCDATETIME() WHERE Insti"
                            "tutionId=? AND CampaignId=?"
                        ),
                        actor["UserId"],
                        actor["AuthVersion"],
                        actor["SessionId"],
                        institution(self.settings),
                        key,
                    )
                result = {
                    "prepared": prepared,
                    "eligible": sum(v["eligible"] for v in found),
                    "excluded": sum(not v["eligible"] for v in found),
                    "state": current(c, self.settings, key)["State"],
                    "revision": body.revision,
                }
            elif action == "retry":
                if not body.recipient_ids:
                    raise HTTPException(422, "broadcast_select_failed_recipients")
                authorize(c, self.settings, auth, "inbox.write")
                if campaign["State"] not in {"running", "scheduled", "paused"}:
                    raise HTTPException(409, "broadcast_resume_required")
                fresh, item = audience(
                    c, self.settings, campaign, controlled=self.controlled
                )
                by_identity = {v["identity_id"]: v for v in fresh if v["eligible"]}
                for key_id in set(body.recipient_ids):
                    rec = one(
                        c,
                        (
                            "SELECT r.*,q.State AS QueueState,q.Ext"
                            "ernalId FROM crm_broadcast7.Recipient "
                            "r JOIN crm_channels2.SendJob q ON q.In"
                            "stitutionId=r.InstitutionId AND q.Queu"
                            "eId=r.CurrentQueueId WHERE r.Instituti"
                            "onId=? AND r.CampaignId=? AND r.Recipi"
                            "entId=?"
                        ),
                        institution(self.settings),
                        key,
                        str(key_id),
                    )
                    if (
                        not rec
                        or rec["QueueState"] != "failed"
                        or rec["ExternalId"] is not None
                        or rec["Attempts"] >= 20
                    ):
                        raise HTTPException(
                            409, "broadcast_retry_only_definitive_unaccepted_failure"
                        )
                    candidate = by_identity.get(uid(str(rec["IdentityId"])))
                    if not candidate:
                        raise HTTPException(409, "broadcast_recipient_excluded")
                    snapshot = {
                        "audience_profile": candidate["audience_profile"],
                        "template": candidate["template"],
                        "body": candidate["text"],
                        "target": candidate["phone"],
                        "canonical_contact": candidate["contact_id"],
                        "template_material_revision": json.loads(
                            candidate["template_record"]["ProviderMetadata"]
                        )["material_revision"],
                    }
                    c.execute(
                        (
                            "UPDATE crm_broadcast7.Recipient SET St"
                            "ate='prepared',CurrentQueueId=NULL,Las"
                            "tError=NULL,CampaignRevision=?,Campaig"
                            "nEpoch=?,ConsentId=?,ConsentVersion=?,"
                            "ControlEpoch=?,AccountVersion=?,Snapsh"
                            "ot=?,UpdatedAt=SYSUTCDATETIME() WHERE "
                            "InstitutionId=? AND RecipientId=?"
                        ),
                        campaign["Revision"],
                        campaign["Epoch"],
                        candidate["consent"]["ConsentId"],
                        candidate["consent"]["VersionNo"],
                        candidate["person"]["ControlEpoch"],
                        item["RowVersion"],
                        templates.encoded(snapshot),
                        institution(self.settings),
                        str(key_id),
                    )
                c.execute(
                    (
                        "UPDATE crm_broadcast7.Campaign SET Sta"
                        "te=CASE WHEN ScheduledAt>SYSUTCDATETIM"
                        "E() THEN 'scheduled' ELSE 'running' EN"
                        "D,ActorId=?,ActorAuthVersion=?,ActorSe"
                        "ssionId=?,ApprovedAt=SYSUTCDATETIME() "
                        "WHERE InstitutionId=? AND CampaignId=?"
                    ),
                    actor["UserId"],
                    actor["AuthVersion"],
                    actor["SessionId"],
                    institution(self.settings),
                    key,
                )
                result = {
                    "retried": len(set(body.recipient_ids)),
                    "revision": body.revision,
                }
            else:
                raise HTTPException(404, "broadcast_action_unknown")
            record_operation(
                c,
                self.settings,
                actor["UserId"],
                str(body.operation_id),
                "broadcast." + action,
                key,
                h,
                result,
            )
            audit(
                c,
                self.settings,
                actor["UserId"],
                "broadcast." + action,
                key,
                revision=body.revision,
            )
            return result

    def identities(self, auth, integration, *, audience=False, search="", offset=0):
        with self.tx(auth) as (c, _):
            account(c, self.settings, integration)
            if audience:
                found = rows(c, "WITH base AS (SELECT i.IdentityId,i.ExternalId AS Phone,p.ContactId,p.Name FROM crm_channels2.ExternalIdentity i LEFT JOIN crm_workspace.Merge g ON g.SourceContactId=i.ContactId AND g.Active=1 JOIN crm.Contact p ON p.ContactId=COALESCE(g.TargetContactId,i.ContactId) WHERE i.InstitutionId=? AND i.IntegrationId=?) SELECT * FROM base WHERE (?='' OR CHARINDEX(?,Name)>0 OR CHARINDEX(?,Phone)>0) ORDER BY Name,IdentityId OFFSET ? ROWS FETCH NEXT 101 ROWS ONLY", institution(self.settings), integration, search, search, search, offset)
                return {"items": [{"id": uid(str(v["IdentityId"])), "contact_id": uid(str(v["ContactId"])), "name": v["Name"], "phone": v["Phone"]} for v in found[:100]], "has_more": len(found)>100, "offset": offset}
            found = rows(
                c,
                (
                    "WITH base AS (SELECT i.IdentityId,i.ExternalId,"
                    "i.ExternalId AS Phone,i.ContactId,i.ConversationId,p.Nam"
                    "e FROM crm_channels2.ExternalIdentity "
                    "i JOIN crm.Contact p ON p.ContactId=i."
                    "ContactId WHERE i.InstitutionId=? AND "
                    "i.IntegrationId=?) SELECT * FROM base "
                    "WHERE (?='' OR CHARINDEX(?,Name)>0 "
                    "OR CHARINDEX(?,Phone)>0) ORDER BY Name,IdentityId "
                    "OFFSET ? ROWS FETCH NEXT 101 ROWS ONLY"
                ),
                institution(self.settings),
                integration,
                search, search, search, offset,
            )
            return {
                "has_more": len(found) > 100,
                "offset": offset,
                "items": [
                    {
                        "id": uid(str(v["IdentityId"])),
                        "name": v["Name"],
                        "phone": v["ExternalId"],
                        "contact_id": uid(str(v["ContactId"])),
                        "conversation_id": uid(str(v["ConversationId"])),
                        "consent": (
                            {
                                "state": g["State"],
                                "version": g["VersionNo"],
                                "expires_at": utc(g["ExpiresAt"]),
                                "evidence": g["Evidence"],
                            }
                            if (g := consent(c, self.settings, str(v["IdentityId"])))
                            else None
                        ),
                    }
                    for v in found[:100]
                ]
            }

    def save_consent(self, auth, integration, identity, body):
        with self.tx(auth, True, recent=True) as (c, actor):
            authorize(c, self.settings, auth, "inbox.write")
            resource = integration + "/" + identity
            h, prior = replay(
                c,
                self.settings,
                actor["UserId"],
                str(body.operation_id),
                "broadcast.consent",
                resource,
                body.model_dump(mode="json"),
            )
            if prior:
                return prior
            if not c.execute(
                (
                    "SELECT 1 FROM crm_channels2.ExternalId"
                    "entity WHERE InstitutionId=? AND Integ"
                    "rationId=? AND IdentityId=?"
                ),
                institution(self.settings),
                integration,
                identity,
            ).fetchone():
                raise HTTPException(404, "broadcast_identity_not_found")
            previous = consent(c, self.settings, identity)
            if body.revision != (previous["VersionNo"] if previous else 0):
                raise HTTPException(409, "revision_conflict")
            expires = (
                datetime.fromisoformat(body.expires_at.replace("Z", "+00:00"))
                .astimezone(timezone.utc)
                .replace(tzinfo=None)
                if body.expires_at
                else None
            )
            key = str(uuid4())
            c.execute(
                (
                    "INSERT crm_broadcast7.Consent(Institut"
                    "ionId,ConsentId,IntegrationId,Identity"
                    "Id,VersionNo,State,Evidence,Origin,Exp"
                    "iresAt,ActorId,OperationId) VALUES(?,?"
                    ",?,?,?,?,?,?,?,?,?)"
                ),
                institution(self.settings),
                key,
                integration,
                identity,
                body.revision + 1,
                body.state,
                body.evidence,
                body.origin,
                expires,
                actor["UserId"],
                str(body.operation_id),
            )
            if body.state == "revoked":
                c.execute(
                    (
                        "UPDATE q SET State='cancelled',LastErr"
                        "orCode='marketing_consent_revoked',Com"
                        "pletedAt=SYSUTCDATETIME() FROM crm_cha"
                        "nnels2.SendJob q JOIN crm_broadcast7.R"
                        "ecipient r ON r.InstitutionId=q.Instit"
                        "utionId AND r.CurrentQueueId=q.QueueId"
                        " WHERE r.InstitutionId=? AND r.Identit"
                        "yId=? AND q.State='queued'"
                    ),
                    institution(self.settings),
                    identity,
                )
                c.execute(
                    (
                        "UPDATE crm_broadcast7.Recipient SET St"
                        "ate='cancelled',LastError='marketing_c"
                        "onsent_revoked' WHERE InstitutionId=? "
                        "AND IdentityId=? AND State='prepared'"
                    ),
                    institution(self.settings),
                    identity,
                )
            result = {"saved": True, "version": body.revision + 1, "state": body.state}
            record_operation(
                c,
                self.settings,
                actor["UserId"],
                str(body.operation_id),
                "broadcast.consent",
                resource,
                h,
                result,
            )
            audit(
                c,
                self.settings,
                actor["UserId"],
                "broadcast.consent",
                identity,
                version=body.revision + 1,
            )
            return result

    def cadence(self, auth, integration, body=None):
        with self.tx(auth, body is not None, recent=body is not None) as (c, actor):
            account(c, self.settings, integration)
            old = one(
                c,
                (
                    "SELECT * FROM crm_broadcast7.Cadence W"
                    "HERE InstitutionId=? AND IntegrationId"
                    "=?"
                ),
                institution(self.settings),
                integration,
            )
            if body:
                h, prior = replay(
                    c,
                    self.settings,
                    actor["UserId"],
                    str(body.operation_id),
                    "broadcast.cadence",
                    integration,
                    body.model_dump(mode="json"),
                )
                if prior:
                    return prior
                if body.revision != (old["Revision"] if old else 0):
                    raise HTTPException(409, "revision_conflict")
                if old:
                    c.execute(
                        (
                            "UPDATE crm_broadcast7.Cadence SET Enab"
                            "led=?,DailyLimit=?,IntervalSeconds=?,R"
                            "evision=Revision+1 WHERE InstitutionId"
                            "=? AND IntegrationId=?"
                        ),
                        body.enabled,
                        body.daily_limit,
                        body.interval_seconds,
                        institution(self.settings),
                        integration,
                    )
                else:
                    c.execute(
                        (
                            "INSERT crm_broadcast7.Cadence(Institut"
                            "ionId,IntegrationId,Enabled,DailyLimit"
                            ",IntervalSeconds,WindowAt,Reserved,Nex"
                            "tAt,Revision) VALUES(?,?,?,?,?,SYSUTCD"
                            "ATETIME(),0,SYSUTCDATETIME(),1)"
                        ),
                        institution(self.settings),
                        integration,
                        body.enabled,
                        body.daily_limit,
                        body.interval_seconds,
                    )
                result = {"saved": True, "revision": body.revision + 1}
                record_operation(
                    c,
                    self.settings,
                    actor["UserId"],
                    str(body.operation_id),
                    "broadcast.cadence",
                    integration,
                    h,
                    result,
                )
                return result
            return {
                "revision": old["Revision"] if old else 0,
                "enabled": bool(old["Enabled"]) if old else False,
                "daily_limit": old["DailyLimit"] if old else 100,
                "interval_seconds": old["IntervalSeconds"] if old else 30,
                "reserved": old["Reserved"] if old else 0,
                "next_at": utc(old["NextAt"]) if old else None,
            }

    def sync(self, auth, integration, body):
        with self.tx(auth) as (c, _):
            item = account(c, self.settings, integration)
            adapter, credential = provider_account(c, self.settings, item)
            if item["Channel"] != "whatsapp" or not item["ParentExternalId"]:
                raise HTTPException(409, "broadcast_waba_required")
            binding = (bytes(item["RowVersion"]), str(credential["SecretId"]))
        try:
            fetched = templates.fetch(adapter, self.request)
        except providers.ProviderFailure as e:
            raise HTTPException(502, e.code) from e
        with self.tx(auth, True) as (c, actor):
            item = account(c, self.settings, integration)
            _, credential = provider_account(c, self.settings, item)
            if (bytes(item["RowVersion"]), str(credential["SecretId"])) != binding:
                raise HTTPException(409, "broadcast_account_changed")
            h, prior = replay(
                c,
                self.settings,
                actor["UserId"],
                str(body.operation_id),
                "broadcast.sync",
                integration,
                body.model_dump(mode="json"),
            )
            if prior:
                return prior
            result = [
                templates.append(
                    c,
                    self.settings,
                    item,
                    v,
                    credential,
                    "controlled" if self.controlled else "provider",
                )
                for v in fetched
            ]
            for observed in result:
                c.execute(
                    (
                        "UPDATE crm_channels2.ProviderOperation"
                        " SET Status='confirmed',ResultCode='te"
                        "mplate_catalog_reconciled',CompletedAt"
                        "=SYSUTCDATETIME(),LeaseUntil=NULL WHER"
                        "E InstitutionId=? AND IntegrationId=? "
                        "AND Action='template_create' AND Statu"
                        "s IN('running','uncertain') AND JSON_V"
                        "ALUE(ResultMetadata,'$.template_id')=?"
                    ),
                    institution(self.settings),
                    integration,
                    observed["id"],
                )
            seen = {str(v["id"]) for v in fetched}
            for old in catalog(c, self.settings, integration):
                if old["Origin"] != "operator" and old["ProviderId"] not in seen:
                    templates.append(
                        c,
                        self.settings,
                        item,
                        {
                            "id": old["ProviderId"],
                            "name": old["Name"],
                            "language": old["Language"],
                            "category": old["Category"],
                            "status": "NOT_FOUND",
                            "components": json.loads(old["Definition"]),
                        },
                        credential,
                        "controlled" if self.controlled else "provider",
                    )
            result = {
                "synced": len(result),
                "origin": "controlled" if self.controlled else "provider",
                "external_acceptance": not self.controlled,
            }
            record_operation(
                c,
                self.settings,
                actor["UserId"],
                str(body.operation_id),
                "broadcast.sync",
                integration,
                h,
                result,
            )
            return result

    def create_template(self, auth, integration, key, body):
        components = templates.definition(body)
        with self.tx(auth, True) as (c, actor):
            h, prior = replay(
                c,
                self.settings,
                actor["UserId"],
                str(body.operation_id),
                "broadcast.template_draft",
                key,
                body.model_dump(mode="json"),
            )
            if prior:
                return prior
            from app.modules.crm_configuration.application.service import read_configuration

            crm_config, _ = read_configuration(c, foundation=True)
            default_bindings = broadcast_variables.bindings([
                {"type": "BODY", "text": body.body_text},
                {"type": "HEADER", "text": body.header_text if body.header_type == "TEXT" else ""},
            ], broadcast_variables.catalog(crm_config.fields), templates.TOKEN)
            item = account(c, self.settings, integration)
            if item["Channel"] != "whatsapp":
                raise HTTPException(422, "broadcast_whatsapp_required")
            old = one(
                c,
                (
                    "SELECT MAX(VersionNo) AS VersionNo FRO"
                    "M crm_broadcast7.Template WHERE Instit"
                    "utionId=? AND TemplateId=?"
                ),
                institution(self.settings),
                key,
            )
            if body.revision != (old["VersionNo"] or 0):
                raise HTTPException(409, "revision_conflict")
            duplicate = one(
                c,
                (
                    "SELECT TOP(1) TemplateId FROM crm_broa"
                    "dcast7.Template WHERE InstitutionId=? "
                    "AND IntegrationId=? AND Name=? AND Lan"
                    "guage=? AND TemplateId<>?"
                ),
                institution(self.settings),
                integration,
                body.name,
                body.language,
                key,
            )
            if duplicate:
                raise HTTPException(409, "broadcast_template_name_language_exists")
            result = templates.append(
                c,
                self.settings,
                item,
                {
                    "id": "local:" + key,
                    "name": body.name,
                    "language": body.language,
                    "category": body.category,
                    "status": "LOCAL_DRAFT",
                    "components": components,
                    "allow_category_change": body.allow_category_change,
                    "variable_bindings": default_bindings,
                },
                None,
                "operator",
                key=key,
            )
            record_operation(
                c,
                self.settings,
                actor["UserId"],
                str(body.operation_id),
                "broadcast.template_draft",
                key,
                h,
                result,
            )
            return result

    def submit_template(self, auth, key, body):
        if not body.confirmed:
            raise HTTPException(409, "broadcast_review_confirmation_required")
        operation = str(body.operation_id)
        with self.tx(auth, True, recent=True) as (c, actor):
            original = templates.latest(c, self.settings, key)
            if json.loads(original["ProviderMetadata"]).get("library_removed"):
                raise HTTPException(409, "broadcast_template_removed_from_library")
            item = account(c, self.settings, str(original["IntegrationId"]))
            adapter, credential = provider_account(c, self.settings, item)
            h = bound_hash(
                self.settings,
                {
                    "template": key,
                    "body": body.model_dump(mode="json"),
                    "actor": actor["UserId"],
                },
                "template-create",
            )
            prior = one(
                c,
                (
                    "SELECT RequestDigest,Status,ResultCode"
                    " FROM crm_channels2.ProviderOperation "
                    "WHERE InstitutionId=? AND OperationId="
                    "?"
                ),
                institution(self.settings),
                operation,
            )
            if prior:
                if bytes(prior["RequestDigest"]) != h:
                    raise HTTPException(409, "operation_conflict")
                return {
                    "status": prior["Status"],
                    "code": prior["ResultCode"],
                    "duplicate": True,
                }
            if original["VersionNo"] != body.revision:
                raise HTTPException(409, "revision_conflict")
            if original["Origin"] != "operator":
                raise HTTPException(409, "broadcast_template_already_submitted")
            if c.execute(
                (
                    "SELECT 1 FROM crm_channels2.ProviderOp"
                    "eration WHERE InstitutionId=? AND Inte"
                    "grationId=? AND Action='template_creat"
                    "e' AND Status IN('running','uncertain'"
                    ") AND (JSON_VALUE(ResultMetadata,'$.te"
                    "mplate_id')=? OR ResultMetadata='{}')"
                ),
                institution(self.settings),
                item["IntegrationId"],
                key,
            ).fetchone():
                raise HTTPException(
                    409, "broadcast_template_creation_requires_reconciliation"
                )
            binding = (
                bytes(item["RowVersion"]),
                str(credential["SecretId"]),
                original["VersionNo"],
            )
            c.execute(
                (
                    "INSERT crm_channels2.ProviderOperation"
                    "(InstitutionId,OperationId,Application"
                    "Id,IntegrationId,ActorRef,Action,Reque"
                    "stDigest,Status,ResultMetadata,EffectK"
                    "ey,CreatedAt,LeaseUntil,Attempts) VALU"
                    "ES(?,?,?,?,?,'template_create',?,'runn"
                    "ing','{}',?,SYSUTCDATETIME(),DATEADD(s"
                    "econd,60,SYSUTCDATETIME()),1)"
                ),
                institution(self.settings),
                operation,
                item["ApplicationId"],
                item["IntegrationId"],
                actor["UserId"],
                h,
                h,
            )
            c.execute(
                (
                    "UPDATE crm_channels2.ProviderOperation"
                    " SET ResultMetadata=? WHERE Institutio"
                    "nId=? AND OperationId=?"
                ),
                templates.encoded(
                    {"template_id": key, "template_version": original["VersionNo"]}
                ),
                institution(self.settings),
                operation,
            )
        result = None
        status = "uncertain"
        code = "provider_result_unknown"
        try:
            with self.tx(auth, True, recent=True) as (c, _):
                live = account(c, self.settings, str(item["IntegrationId"]))
                _, secret = provider_account(c, self.settings, live)
                if (
                    bytes(live["RowVersion"]),
                    str(secret["SecretId"]),
                    templates.latest(c, self.settings, key)["VersionNo"],
                ) != binding:
                    raise HTTPException(409, "broadcast_context_changed")
            result = self.request(
                adapter,
                "POST",
                adapter["configuration"]["wabaId"] + "/message_templates",
                {
                    "name": original["Name"],
                    "language": original["Language"],
                    "category": original["Category"],
                    "components": json.loads(original["Definition"]),
                    "allow_category_change": json.loads(
                        original["ProviderMetadata"]
                    ).get("allow_category_change", True),
                },
            )
            if not isinstance(result.get("id"), str) or not result["id"]:
                raise providers.ProviderFailure(
                    "provider_acceptance_not_confirmed", uncertain=True
                )
            status, code = "confirmed", "provider_template_created"
        except providers.ProviderFailure as e:
            status, code = ("uncertain" if e.uncertain else "failed"), e.code
        except HTTPException as e:
            status, code = "failed", str(e.detail)[:80]
        except Exception:
            pass
        with self.tx(auth, True) as (c, _):
            live = account(c, self.settings, str(item["IntegrationId"]))
            _, secret = provider_account(c, self.settings, live)
            latest = templates.latest(c, self.settings, key)
            if (
                bytes(live["RowVersion"]),
                str(secret["SecretId"]),
                latest["VersionNo"],
            ) != binding:
                status, code = "uncertain", "broadcast_context_changed"
            if status == "confirmed":
                templates.append(
                    c,
                    self.settings,
                    live,
                    {
                        "id": result["id"],
                        "name": original["Name"],
                        "language": original["Language"],
                        "category": original["Category"],
                        "status": "PENDING",
                        "components": json.loads(original["Definition"]),
                    },
                    secret,
                    "controlled" if self.controlled else "provider",
                    key=key,
                )
            c.execute(
                (
                    "UPDATE crm_channels2.ProviderOperation"
                    " SET Status=?,ResultCode=?,CompletedAt"
                    "=SYSUTCDATETIME(),LeaseUntil=NULL WHER"
                    "E InstitutionId=? AND OperationId=? AN"
                    "D Status='running'"
                ),
                status,
                code,
                institution(self.settings),
                operation,
            )
            return {"status": status, "code": code, "approval_requires_sync": True}

    def pause_template(self, auth, key, body):
        with self.tx(auth, True) as (c, actor):
            h, prior = replay(
                c,
                self.settings,
                actor["UserId"],
                str(body.operation_id),
                "broadcast.template_pause",
                key,
                body.model_dump(mode="json"),
            )
            if prior:
                return prior
            old = templates.latest(c, self.settings, key)
            if old["VersionNo"] != body.revision:
                raise HTTPException(409, "revision_conflict")
            item = account(c, self.settings, str(old["IntegrationId"]))
            credential = (
                {"SecretId": old["CredentialId"]} if old["CredentialId"] else None
            )
            result = templates.append(
                c,
                self.settings,
                item,
                {
                    "id": old["ProviderId"],
                    "name": old["Name"],
                    "language": old["Language"],
                    "category": old["Category"],
                    "status": old["ProviderStatus"],
                    "components": json.loads(old["Definition"]),
                },
                credential,
                old["Origin"],
                key=key,
                paused=body.paused,
                observed=old["ObservedAt"],
            )
            record_operation(
                c,
                self.settings,
                actor["UserId"],
                str(body.operation_id),
                "broadcast.template_pause",
                key,
                h,
                result,
            )
            return result

    def report(self, auth, key, offset=0, *, state="", search="", all_items=False, include_analytics=False):
        with self.tx(auth) as (c, _):
            campaign = current(c, self.settings, key)
            # Status dates are authenticated event observation dates, never inferred
            # from acceptance. Reply attribution requires an explicit context.id.
            from app.institutional.broadcast_report import projection

            base = projection(materialized=getattr(c, "dialect", None) == "postgresql")
            args = (
                institution(self.settings),
                key,
                state,
                state,
                state,
                search,
                search,
                search,
                search,
            )
            aggregates = rows(
                c,
                base
                + (
                    "SELECT Status,COUNT(*) AS Total,SUM(CA"
                    "SE WHEN RepliedAt IS NOT NULL THEN 1 E"
                    "LSE 0 END) AS Replied FROM filtered GR"
                    "OUP BY Status"
                ),
                *args,
            )
            total = sum(v["Total"] for v in aggregates)
            counts = {v["Status"]: v["Total"] for v in aggregates}
            query = base + ("SELECT * FROM filtered ORDER BY PreparedAt,RecipientId")
            found = rows(
                c,
                query
                if all_items
                else query + " OFFSET ? ROWS FETCH NEXT 100 ROWS ONLY",
                *args,
                *([] if all_items else [offset]),
            )
            try:
                pinned_definition = json.loads(templates.latest(c, self.settings, str(campaign["TemplateId"]), campaign["TemplateVersion"])["Definition"])
            except HTTPException as error:
                if error.status_code != 404:
                    raise
                pinned_definition = []
            items = [
                {
                    "id": uid(str(v["RecipientId"])),
                    "identity_id": uid(str(v["IdentityId"])),
                    "name": v["Name"],
                    "phone": v["Phone"],
                    "status": v["Status"],
                    "error": v["Error"],
                    "attempts": v["Attempts"],
                    "provider_message_id": v["ProviderMessageId"],
                    "queue_id": uid(str(v["CurrentQueueId"]))
                    if v["CurrentQueueId"]
                    else None,
                    "body": v["Body"],
                    "profile": segments.snapshot_profile(v["Snapshot"]),
                    "contact": segments.contact_details(v),
                    "template_parts": templates.display_parts(pinned_definition, json.loads(v["Snapshot"] or "{}")),
                    **{
                        n: utc(v[col])
                        for n, col in [
                            ("prepared_at", "PreparedAt"),
                            ("queued_at", "QueuedAt"),
                            ("accepted_at", "AcceptedAt"),
                            ("sent_at", "SentAt"),
                            ("delivered_at", "DeliveredAt"),
                            ("read_at", "ReadAt"),
                            ("replied_at", "RepliedAt"),
                            ("failed_at", "FailedAt"),
                        ]
                    },
                }
                for v in found
            ]
            delivered = counts.get("delivered", 0) + counts.get("read", 0)
            read = counts.get("read", 0)
            replied = sum(v["Replied"] for v in aggregates)
            analysis = None
            if include_analytics:
                analysis_rows = rows(c, base + "SELECT Status,Snapshot,SentAt,DeliveredAt,ReadAt,RepliedAt FROM filtered ORDER BY RecipientId OFFSET 0 ROWS FETCH NEXT 5001 ROWS ONLY", *args)
                if len(analysis_rows) > 5000:
                    raise HTTPException(413, "broadcast_analytics_scope_limit")
                analysis = segments.analytics(analysis_rows)
            return {
                "campaign": public_campaign(campaign),
                "counts": counts,
                "total": total,
                "items": items,
                "has_more": total > offset + 100,
                "offset": offset,
                "metrics": {
                    "replied": replied,
                    "delivered_percent": round(delivered * 100 / total, 2)
                    if total
                    else None,
                    "read_percent": round(read * 100 / total, 2) if total else None,
                    "reply_percent": round(replied * 100 / total, 2) if total else None,
                },
                "analytics": analysis,
                "timestamp_semantics": "authenticated_event_observation_UTC",
                "external_acceptance": False if self.controlled else None,
            }

    def export(self, auth, key, *, state="", search=""):
        all_items = self.report(auth, key, state=state, search=search, all_items=True)[
            "items"
        ]
        out = io.StringIO()
        writer = csv.writer(out)
        fields = [
            "id",
            "name",
            "phone",
            "status",
            "attempts",
            "body",
            "prepared_at",
            "queued_at",
            "accepted_at",
            "sent_at",
            "delivered_at",
            "read_at",
            "replied_at",
            "failed_at",
            "provider_message_id",
            "error",
            *segments.DIMENSIONS,
        ]
        writer.writerow(
            [
                "destinatario",
                "nombre",
                "telefono",
                "estado",
                "intentos",
                "mensaje",
                "preparado_UTC",
                "pendiente_UTC",
                "aceptado_UTC",
                "enviado_observado_UTC",
                "entregado_observado_UTC",
                "leido_observado_UTC",
                "respuesta_atribuida_observada_UTC",
                "fallo_observado_UTC",
                "id_proveedor",
                "error",
                "genero", "franja_edad", "ciudad", "region", "pais", "programa", "jornada", "tipo_contacto", "estado_crm",
            ]
        )

        def cell(value):
            text = "" if value is None else str(value)
            return (
                "'" + text
                if text.lstrip().startswith(("=", "+", "-", "@"))
                or text.startswith(("\t", "\r", "\n"))
                else text
            )

        for item in all_items:
            writer.writerow([cell(item["profile"].get(k, "Sin dato") if k in segments.DIMENSIONS else item[k]) for k in fields])
        return out.getvalue()
