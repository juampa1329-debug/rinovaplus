"""Local campaigns, evidence and preparation; marketing transport stays disabled."""

import json
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException

from app.modules.channels import providers
from app.modules.catalog.infrastructure.institutional_context import programs
from app.modules.crm_configuration.application.service import read_configuration
from app.modules.conversation_strategy.api.router import no_contact
from .evidence import assess


def packed(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


def rows(cursor):
    names = [item[0] for item in cursor.description]
    return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]


def installed(cursor):
    marker = cursor.execute("SELECT CONVERT(nvarchar(80),value) FROM sys.extended_properties WHERE class=3 AND major_id=SCHEMA_ID(N'crm_marketing') AND name=N'crm_marketing.contract'").fetchone()
    if not marker or marker[0] != "campaigns-v1":
        raise HTTPException(503, "campaigns_migration_required")


def transport_disabled():
    raise HTTPException(423, "marketing_transport_disabled")


class CampaignService:
    def __init__(self, application):
        self.application = application

    @contextmanager
    def transaction(self, write=False):
        if self.application.state.settings.mode != "local_sql_copy":
            raise HTTPException(503, "local_sql_copy_required")
        with self.application.state.sql_workspace.transaction(write=write) as cursor:
            installed(cursor)
            yield cursor

    def overview(self):
        if self.application.state.settings.mode != "local_sql_copy":
            return {"installed": False, "transport_enabled": False}
        with self.application.state.sql_workspace.transaction() as cursor:
            if cursor.execute("SELECT SCHEMA_ID(N'crm_marketing')").fetchval() is None:
                return {"installed": False, "transport_enabled": False, "reason": "campaigns_migration_required"}
            installed(cursor)
            counts = {}
            for key, table in (("campaigns", "Campaign"), ("rules", "RemarketingRule"), ("templates", "MessageTemplate"), ("recipients", "CampaignRecipient")):
                counts[key] = cursor.execute("SELECT COUNT(*) FROM crm_marketing." + table).fetchval()
            policy = cursor.execute("SELECT EvaluationEnabled,NextRunAtUtc FROM crm_marketing.Policy WHERE PolicyId=1").fetchone()
            latest = rows(cursor.execute("SELECT TOP(1) RunId,Kind,State,RequestedAtUtc,CompletedAtUtc,CountsJson,LastError FROM crm_marketing.EvaluationRun ORDER BY RequestedAtUtc DESC"))
            return {"installed": True, "transport_enabled": False, "counts": counts, "evaluation_enabled": bool(policy[0]), "next_run_at": policy[1], "last_run": latest[0] if latest else None}

    def configuration(self):
        with self.transaction() as cursor:
            config, _ = read_configuration(cursor)
            row = cursor.execute("SELECT Revision,StageWeightsJson,EvaluationEnabled,IntervalMinutes,NextRunAtUtc FROM crm_marketing.Policy WHERE PolicyId=1").fetchone()
            catalog = programs(cursor, 0, 300)
            return {"revision": row[0], "stage_weights": json.loads(row[1]), "evaluation_enabled": bool(row[2]), "interval_minutes": row[3], "next_run_at": row[4], "stages": [stage.label for stage in config.stages if stage.active], "programs": catalog["items"], "period": catalog["period"], "catalog_has_more": catalog["has_more"], "transport_enabled": False}

    def save_configuration(self, request):
        with self.transaction(True) as cursor:
            config, _ = read_configuration(cursor)
            allowed = {stage.label for stage in config.stages if stage.active}
            if any(stage not in allowed for stage in request.stage_weights):
                raise HTTPException(422, "invalid_crm_stage")
            cursor.execute("UPDATE crm_marketing.Policy SET StageWeightsJson=?,EvaluationEnabled=?,IntervalMinutes=?,NextRunAtUtc=DATEADD(minute,?,SYSUTCDATETIME()),Revision=Revision+1,UpdatedAtUtc=SYSUTCDATETIME() WHERE PolicyId=1 AND Revision=?", packed(request.stage_weights), request.evaluation_enabled, request.interval_minutes, request.interval_minutes, request.revision)
            if cursor.rowcount != 1:
                raise HTTPException(409, "campaign_revision_conflict")
        return self.configuration()

    def predictions(self):
        with self.transaction() as cursor:
            items = rows(cursor.execute(
                "SELECT TOP(201) c.ConversationId,c.ContactId,p.Name,p.Stage,c.State,manual.LeadScore AS ManualLeadScore,a.RiskScore,a.RiskLevel,a.Status,a.ReasonsJson,a.AsOfUtc,a.FormulaVersion,a.ComputedLeadScore,a.LeadReasonsJson "
                "FROM crm.Conversation c JOIN crm.Contact p ON p.ContactId=c.ContactId LEFT JOIN crm_channels.ConversationProfile manual ON manual.ConversationId=c.ConversationId "
                "OUTER APPLY(SELECT TOP(1) * FROM crm_marketing.ChurnAssessment x WHERE x.ConversationId=c.ConversationId ORDER BY x.AsOfUtc DESC,x.CreatedAtUtc DESC) a "
                "WHERE c.State<>'closed' ORDER BY c.CreatedAt"))
            if len(items) > 200:
                raise HTTPException(413, "prediction_scope_limit")
            for item in items:
                item["Status"] = item["Status"] or "unknown"
                item["RiskLevel"] = item["RiskLevel"] or "unknown"
                item["reasons"] = json.loads(item.pop("ReasonsJson") or '["not_assessed"]')
                item["lead_reasons"] = json.loads(item.pop("LeadReasonsJson") or "[]")
                item["stage_age_days"] = None
                item["stage_age_reason"] = "stage_transition_evidence_unavailable"
            return {"items": items, "counts": {"total": len(items), "known": sum(i["Status"] == "known" for i in items), "unknown": sum(i["Status"] == "unknown" for i in items)}, "formula_version": "churn-rubric-v1", "lead_formula_version": "lead-observable-v1"}

    def submit_run(self, operation_id, kind, *, campaign_id=None, rule_id=None):
        with self.transaction(True) as cursor:
            previous = cursor.execute("SELECT Kind,CampaignId,RuleId FROM crm_marketing.EvaluationRun WHERE RunId=?", str(operation_id)).fetchone()
            if previous:
                if previous[0] != kind or str(previous[1] or "") != str(campaign_id or "") or str(previous[2] or "") != str(rule_id or ""):
                    raise HTTPException(409, "operation_id_conflict")
            else:
                if campaign_id and not cursor.execute("SELECT 1 FROM crm_marketing.Campaign WHERE CampaignId=?", str(campaign_id)).fetchone():
                    raise HTTPException(404, "campaign_not_found")
                if rule_id and not cursor.execute("SELECT 1 FROM crm_marketing.RemarketingRule WHERE RuleId=?", str(rule_id)).fetchone():
                    raise HTTPException(404, "rule_not_found")
                cursor.execute("INSERT crm_marketing.EvaluationRun(RunId,Kind,TriggerKind,CampaignId,RuleId) VALUES(?,?,'manual',?,?)", str(operation_id), kind, str(campaign_id) if campaign_id else None, str(rule_id) if rule_id else None)
        return {"run_id": str(operation_id), "state": "queued", "transport_enabled": False}

    def runs(self):
        with self.transaction() as cursor:
            return {"items": rows(cursor.execute("SELECT TOP(30) RunId,Kind,TriggerKind,CampaignId,RuleId,State,Attempts,RequestedAtUtc,CompletedAtUtc,CountsJson,LastError FROM crm_marketing.EvaluationRun ORDER BY RequestedAtUtc DESC"))}

    def templates(self):
        with self.transaction() as cursor:
            return {"items": rows(cursor.execute("SELECT TOP(500) t.TemplateId,t.Channel,t.AccountScope,t.Name,t.Language,t.Status,t.Version,t.StatusRevision,t.SyncedAtUtc FROM crm_marketing.MessageTemplate t WHERE NOT EXISTS(SELECT 1 FROM crm_marketing.MessageTemplate n WHERE n.Channel=t.Channel AND n.AccountScope=t.AccountScope AND n.ProviderTemplateId=t.ProviderTemplateId AND n.Version>t.Version) ORDER BY t.Name,t.Version DESC"))}

    def sync_templates(self, after=""):
        store = self.application.state.channel_store
        with store.transaction() as cursor:
            account = store.get(cursor, "whatsapp", True)
        waba = account["configuration"].get("wabaId", "")
        if not waba or not waba.isdigit() or not account["secrets"].get("accessToken"):
            raise HTTPException(409, "whatsapp_credentials_required")
        records, next_after = [], after
        try:
            for _ in range(5):
                params = {"fields": "id,name,language,status,components", "limit": 100}
                if next_after:
                    params["after"] = next_after
                data = providers.request(account, "GET", waba + "/message_templates", params=params)
                if not isinstance(data, dict) or not isinstance(data.get("data"), list):
                    raise HTTPException(502, "template_catalog_invalid")
                records.extend(data["data"])
                paging = data.get("paging", {})
                next_after = paging.get("cursors", {}).get("after", "") if paging.get("next") else ""
                if not next_after:
                    break
                if not isinstance(next_after, str) or len(next_after) > 1000:
                    raise HTTPException(502, "template_catalog_invalid")
        except providers.ProviderFailure as error:
            raise HTTPException(502, error.code) from None
        with self.transaction(True) as cursor:
            current = store.get(cursor, "whatsapp")
            if current["revision"] != account["revision"] or current["configuration"].get("wabaId") != waba:
                raise HTTPException(409, "channel_identity_changed")
            for record in records[:500]:
                if not isinstance(record, dict) or not all(isinstance(record.get(k), str) and 0 < len(record[k]) <= (20 if k == "language" else 128) for k in ("id", "name", "language")) or not isinstance(record.get("components", []), list):
                    raise HTTPException(502, "template_catalog_invalid")
                components = packed(record.get("components", []))
                if len(components) > 50000:
                    raise HTTPException(413, "template_components_limit")
                status = str(record.get("status", "unknown")).lower()
                if status not in ("pending", "approved", "rejected", "paused", "disabled", "deleted"):
                    status = "unknown"
                latest = cursor.execute("SELECT TOP(1) TemplateId,Version,ComponentsJson,Name,Language FROM crm_marketing.MessageTemplate WHERE Channel='whatsapp' AND AccountScope=? AND ProviderTemplateId=? ORDER BY Version DESC", waba, record["id"]).fetchone()
                if latest and (latest[2], latest[3], latest[4]) == (components, record["name"], record["language"]):
                    cursor.execute("UPDATE crm_marketing.MessageTemplate SET Status=?,StatusRevision=StatusRevision+1,AccountRevision=?,SyncedAtUtc=SYSUTCDATETIME() WHERE TemplateId=?", status, account["revision"], str(latest[0]))
                else:
                    cursor.execute("INSERT crm_marketing.MessageTemplate(TemplateId,Channel,AccountScope,AccountRevision,ProviderTemplateId,Name,Language,Status,Version,ComponentsJson,SyncedAtUtc) VALUES(?,'whatsapp',?,?,?,?,?,?,?,?,SYSUTCDATETIME())", str(uuid4()), waba, account["revision"], record["id"], record["name"], record["language"], status, latest[1] + 1 if latest else 1, components)
        return {"synced": len(records[:500]), "next_cursor": next_after, "has_more": bool(next_after), "transport_enabled": False}

    def template_binding(self, cursor, template_id):
        if template_id is None:
            return None
        row = cursor.execute("SELECT t.TemplateId,t.Channel,t.AccountScope,t.Version,t.Status,t.AccountRevision,t.SyncedAtUtc FROM crm_marketing.MessageTemplate t WHERE t.TemplateId=? AND NOT EXISTS(SELECT 1 FROM crm_marketing.MessageTemplate n WHERE n.Channel=t.Channel AND n.AccountScope=t.AccountScope AND n.ProviderTemplateId=t.ProviderTemplateId AND n.Version>t.Version)", str(template_id)).fetchone()
        if not row:
            raise HTTPException(409, "approved_current_template_required")
        account = self.application.state.channel_store.get(cursor, row[1])
        if row[4] != "approved" or not row[6] or row[5] != account["revision"] or account["configuration"].get("wabaId") != row[2]:
            raise HTTPException(409, "approved_current_template_required")
        return row

    def rules(self):
        with self.transaction() as cursor:
            return {"items": rows(cursor.execute("SELECT r.*,lastRun.State AS LastRunState,lastRun.CompletedAtUtc AS LastRunAt,lastRun.CountsJson AS LastRunCounts FROM crm_marketing.RemarketingRule r OUTER APPLY(SELECT TOP(1) State,CompletedAtUtc,CountsJson FROM crm_marketing.EvaluationRun x WHERE x.RuleId=r.RuleId ORDER BY RequestedAtUtc DESC) lastRun ORDER BY r.CreatedAtUtc DESC"))}

    def save_rule(self, request, rule_id=None):
        with self.transaction(True) as cursor:
            config, _ = read_configuration(cursor)
            if request.stage not in {stage.label for stage in config.stages if stage.active}:
                raise HTTPException(422, "invalid_crm_stage")
            template = self.template_binding(cursor, request.template_id)
            if request.enabled and template is None:
                raise HTTPException(409, "approved_current_template_required")
            values = (request.name, request.stage, template[1] if template else None, template[2] if template else None, str(template[0]) if template else None, template[3] if template else None, request.inactivity_days, request.cooldown_hours, request.minimum_risk, request.enabled)
            if rule_id:
                cursor.execute("UPDATE crm_marketing.RemarketingRule SET Name=?,StageValue=?,Channel=?,AccountScope=?,TemplateId=?,TemplateVersion=?,InactivityDays=?,CooldownHours=?,MinimumRisk=?,Enabled=?,Revision=Revision+1,NextEvaluationAtUtc=SYSUTCDATETIME(),UpdatedAtUtc=SYSUTCDATETIME() WHERE RuleId=? AND Revision=?", *values, str(rule_id), request.revision)
                if cursor.rowcount != 1:
                    raise HTTPException(409, "campaign_revision_conflict")
            else:
                rule_id = uuid4()
                cursor.execute("INSERT crm_marketing.RemarketingRule(Name,StageValue,Channel,AccountScope,TemplateId,TemplateVersion,InactivityDays,CooldownHours,MinimumRisk,Enabled,RuleId) VALUES(?,?,?,?,?,?,?,?,?,?,?)", *values, str(rule_id))
        return {"rule_id": str(rule_id), "transport_enabled": False}

    def delete_rule(self, rule_id, revision):
        with self.transaction(True) as cursor:
            current = cursor.execute("SELECT Revision FROM crm_marketing.RemarketingRule WHERE RuleId=?", str(rule_id)).fetchone()
            if not current or current[0] != revision:
                raise HTTPException(409, "campaign_revision_conflict")
            used = cursor.execute("SELECT 1 FROM crm_marketing.EvaluationRun WHERE RuleId=? UNION ALL SELECT 1 FROM crm_marketing.Campaign WHERE RuleId=?", str(rule_id), str(rule_id)).fetchone()
            if used:
                cursor.execute("UPDATE crm_marketing.RemarketingRule SET Enabled=0,Revision=Revision+1,UpdatedAtUtc=SYSUTCDATETIME() WHERE RuleId=?", str(rule_id))
            else:
                cursor.execute("DELETE crm_marketing.RemarketingRule WHERE RuleId=?", str(rule_id))
        return {"deleted": not bool(used), "disabled": bool(used)}

    def broadcasts(self):
        with self.transaction() as cursor:
            return {"items": rows(cursor.execute("SELECT c.*,totals.Recipients,totals.Prepared,totals.Blocked FROM crm_marketing.Campaign c OUTER APPLY(SELECT COUNT(*) AS Recipients,COUNT(CASE WHEN Status='prepared' THEN 1 END) AS Prepared,COUNT(CASE WHEN Status='blocked' THEN 1 END) AS Blocked FROM crm_marketing.CampaignRecipient r WHERE r.CampaignId=c.CampaignId) totals ORDER BY c.CreatedAtUtc DESC"))}

    def save_broadcast(self, request, campaign_id=None):
        with self.transaction(True) as cursor:
            config, _ = read_configuration(cursor)
            if any(stage not in {s.label for s in config.stages if s.active} for stage in request.segment.stage_values):
                raise HTTPException(422, "invalid_crm_stage")
            catalog = programs(cursor, 0, 300)
            if request.segment.period_id is not None and request.segment.period_id != catalog["period"]["id"]:
                raise HTTPException(409, "segment_period_not_active")
            if any(identifier not in {p["program_id"] for p in catalog["items"]} for identifier in request.segment.program_ids):
                raise HTTPException(422, "program_not_in_active_offer")
            if any(value not in {p["schedule"] for p in catalog["items"]} for value in request.segment.schedule_values):
                raise HTTPException(422, "invalid_academic_schedule")
            template = self.template_binding(cursor, request.template_id)
            if template:
                cursor.execute("IF NOT EXISTS(SELECT 1 FROM crm_marketing.AccountCadence WHERE Channel=? AND AccountScope=?) INSERT crm_marketing.AccountCadence(Channel,AccountScope,MinIntervalSeconds,DailyRecipientLimit,WindowStartedAtUtc,NextAllowedAtUtc) VALUES(?,?,?,?,SYSUTCDATETIME(),SYSUTCDATETIME())", template[1], template[2], template[1], template[2], request.interval_seconds, request.daily_limit)
                cursor.execute("UPDATE crm_marketing.AccountCadence SET MinIntervalSeconds=?,DailyRecipientLimit=?,Revision=Revision+1 WHERE Channel=? AND AccountScope=?", request.interval_seconds, request.daily_limit, template[1], template[2])
            values = (request.name, template[1] if template else None, template[2] if template else None, str(template[0]) if template else None, template[3] if template else None, packed(request.segment.model_dump()), request.scheduled_at)
            if campaign_id:
                cursor.execute("UPDATE crm_marketing.Campaign SET Name=?,Channel=?,AccountScope=?,TemplateId=?,TemplateVersion=?,SegmentJson=?,ScheduledAtUtc=?,Revision=Revision+1,InclusionEpoch=InclusionEpoch+1,Status='draft',UpdatedAtUtc=SYSUTCDATETIME() WHERE CampaignId=? AND Revision=? AND Status IN('draft','paused')", *values, str(campaign_id), request.revision)
                if cursor.rowcount != 1:
                    raise HTTPException(409, "campaign_revision_conflict")
                cursor.execute("UPDATE crm_marketing.CampaignRecipient SET Status='cancelled',LeaseId=NULL,LeaseUntilUtc=NULL,LastError='campaign_changed',UpdatedAtUtc=SYSUTCDATETIME() WHERE CampaignId=? AND QueueId IS NULL", str(campaign_id))
            else:
                campaign_id = uuid4()
                cursor.execute("INSERT crm_marketing.Campaign(Name,Channel,AccountScope,TemplateId,TemplateVersion,SegmentJson,ScheduledAtUtc,CampaignId,Kind) VALUES(?,?,?,?,?,?,?,?,'bulk')", *values, str(campaign_id))
        return {"campaign_id": str(campaign_id), "status": "draft", "transport_enabled": False}

    def broadcast(self, campaign_id):
        with self.transaction() as cursor:
            current = rows(cursor.execute("SELECT * FROM crm_marketing.Campaign WHERE CampaignId=?", str(campaign_id)))
            if not current:
                raise HTTPException(404, "campaign_not_found")
            recipients = rows(cursor.execute("SELECT TOP(200) RecipientId,IdentityId,ContactId,Status,EvidenceJson,UpdatedAtUtc FROM crm_marketing.CampaignRecipient WHERE CampaignId=? ORDER BY UpdatedAtUtc DESC", str(campaign_id)))
            metrics = rows(cursor.execute("SELECT Status,COUNT(*) AS Count FROM crm_marketing.CampaignRecipient WHERE CampaignId=? GROUP BY Status", str(campaign_id)))
            return {"campaign": current[0], "recipients": recipients, "metrics": metrics, "transport_enabled": False}

    def pause(self, campaign_id, revision):
        with self.transaction(True) as cursor:
            cursor.execute("UPDATE crm_marketing.Campaign SET Status='paused',PausedAtUtc=SYSUTCDATETIME(),Revision=Revision+1,InclusionEpoch=InclusionEpoch+1,UpdatedAtUtc=SYSUTCDATETIME() WHERE CampaignId=? AND Revision=?", str(campaign_id), revision)
            if cursor.rowcount != 1:
                raise HTTPException(409, "campaign_revision_conflict")
            cursor.execute("UPDATE crm_marketing.CampaignRecipient SET Status='cancelled',LeaseId=NULL,LeaseUntilUtc=NULL,LastError='campaign_paused',UpdatedAtUtc=SYSUTCDATETIME() WHERE CampaignId=? AND QueueId IS NULL", str(campaign_id))
        return {"status": "paused", "transport_enabled": False}

    def audience(self, cursor, campaign):
        segment = json.loads(campaign["SegmentJson"])
        template_reason = None
        if campaign["TemplateId"]:
            try:
                binding = self.template_binding(cursor, campaign["TemplateId"])
                if (binding[1], binding[2], binding[3]) != (campaign["Channel"], campaign["AccountScope"], campaign["TemplateVersion"]):
                    template_reason = "approved_current_template_required"
            except HTTPException as error:
                template_reason = error.detail
        catalog = programs(cursor, 0, 300)
        offered = {p["program_id"]: p for p in catalog["items"]}
        candidates = rows(cursor.execute("SELECT TOP(501) i.IdentityId,i.Channel,i.ContactId,i.ConversationId,p.Name,p.ProgramId,p.Stage,c.State,c.ControlMode,COALESCE(k.Epoch,0) AS ControlEpoch,a.Revision AS AccountRevision,a.Configuration FROM crm_channels.ExternalIdentity i JOIN crm.Contact p ON p.ContactId=i.ContactId JOIN crm.Conversation c ON c.ConversationId=i.ConversationId AND c.ContactId=p.ContactId JOIN crm_channels.Account a ON a.Channel=i.Channel LEFT JOIN crm_channels.ConversationControl k ON k.ConversationId=c.ConversationId ORDER BY i.IdentityId"))
        if len(candidates) > 500:
            raise HTTPException(413, "audience_scope_limit")
        result = []
        for candidate in candidates:
            offer = offered.get(candidate["ProgramId"])
            if segment.get("program_ids") and candidate["ProgramId"] not in segment["program_ids"] or segment.get("stage_values") and candidate["Stage"] not in segment["stage_values"]:
                continue
            if segment.get("period_id") is not None and (not offer or segment["period_id"] != catalog["period"]["id"]):
                continue
            if segment.get("schedule_values") and (not offer or offer["schedule"] not in segment["schedule_values"]):
                continue
            if campaign["Channel"] and candidate["Channel"] != campaign["Channel"]:
                continue
            config = json.loads(candidate.pop("Configuration"))
            scope = config.get("wabaId") if candidate["Channel"] == "whatsapp" else config.get("accountId") or config.get("pageId")
            reasons = ["marketing_transport_disabled"]
            if not campaign["TemplateId"]:
                reasons.append("approved_template_required")
            elif template_reason:
                reasons.append(template_reason)
            if campaign["Status"] == "paused":
                reasons.append("campaign_paused")
            if candidate["State"] == "closed" or candidate["ControlMode"] == "human":
                reasons.append("human_control_or_closed")
            if no_contact(cursor, str(candidate["ConversationId"])):
                reasons.append("no_contact")
            consent = cursor.execute("SELECT TOP(1) ConsentId,Version,Status,ExpiresAtUtc,DecisionAtUtc FROM crm_marketing.ContactConsent WHERE IdentityId=? AND Channel=? AND AccountScope=? AND Purpose='marketing' ORDER BY Version DESC", str(candidate["IdentityId"]), candidate["Channel"], scope or "").fetchone()
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            if not consent or consent[2] != "granted" or consent[4] is None or consent[4] > now or consent[3] and consent[3] <= now:
                reasons.append("marketing_consent_required")
            if not scope or campaign["AccountScope"] and scope != campaign["AccountScope"]:
                reasons.append("account_scope_mismatch")
            candidate.update(AccountScope=scope, ConsentId=str(consent[0]) if consent else None, ConsentVersion=consent[1] if consent else None, reasons=reasons, eligible=False)
            result.append(candidate)
        return result

    def preview(self, campaign_id):
        with self.transaction() as cursor:
            campaign = rows(cursor.execute("SELECT * FROM crm_marketing.Campaign WHERE CampaignId=?", str(campaign_id)))
            if not campaign:
                raise HTTPException(404, "campaign_not_found")
            audience = self.audience(cursor, campaign[0])
            unlinked = cursor.execute("SELECT COUNT(*) FROM crm.Contact p WHERE NOT EXISTS(SELECT 1 FROM crm_channels.ExternalIdentity i WHERE i.ContactId=p.ContactId)").fetchval()
            return {"items": audience, "counts": {"matched_identities": len(audience), "eligible": 0, "blocked": len(audience), "contacts_without_external_identity": unlinked}, "transport_enabled": False}

    def prepare(self, cursor, campaign_id, only_identities=None):
        campaign = rows(cursor.execute("SELECT * FROM crm_marketing.Campaign WHERE CampaignId=?", str(campaign_id)))
        if not campaign:
            raise HTTPException(404, "campaign_not_found")
        campaign = campaign[0]
        if campaign["Status"] == "paused":
            return {"matched": 0, "blocked": 0, "reason": "campaign_paused", "transport_enabled": False}
        audience = self.audience(cursor, campaign)
        if only_identities is not None:
            audience = [person for person in audience if str(person["IdentityId"]) in only_identities]
        for person in audience:
            identity = str(person["IdentityId"])
            watermark = cursor.execute("SELECT COALESCE(MAX(Sequence),0) FROM crm.Message WHERE ConversationId=?", str(person["ConversationId"])).fetchval()
            evidence = packed({"reasons": person["reasons"], "transport_enabled": False, "stage": person["Stage"], "stage_age_days": None})
            values = (person["Channel"], campaign["AccountScope"], str(person["ContactId"]), str(person["ConversationId"]), person["ConsentId"], person["ConsentVersion"], campaign["Revision"], person["AccountRevision"], person["ControlEpoch"], campaign["InclusionEpoch"], watermark, evidence)
            existing = cursor.execute("SELECT RecipientId,QueueId FROM crm_marketing.CampaignRecipient WHERE CampaignId=? AND IdentityId=?", str(campaign_id), identity).fetchone()
            if existing and existing[1] is not None:
                raise HTTPException(423, "marketing_transport_disabled")
            if existing:
                cursor.execute("UPDATE crm_marketing.CampaignRecipient SET Channel=?,AccountScope=?,ContactId=?,ConversationId=?,ConsentId=?,ConsentVersion=?,CampaignRevision=?,AccountRevision=?,ControlEpoch=?,InclusionEpoch=?,InputSequence=?,EvidenceJson=?,Status='blocked',LeaseId=NULL,LeaseUntilUtc=NULL,LastError='marketing_transport_disabled',UpdatedAtUtc=SYSUTCDATETIME() WHERE RecipientId=?", *values, str(existing[0]))
            else:
                cursor.execute("INSERT crm_marketing.CampaignRecipient(Channel,AccountScope,ContactId,ConversationId,ConsentId,ConsentVersion,CampaignRevision,AccountRevision,ControlEpoch,InclusionEpoch,InputSequence,EvidenceJson,RecipientId,CampaignId,IdentityId,Status,DueAtUtc,LastError) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'blocked',SYSUTCDATETIME(),'marketing_transport_disabled')", *values, str(uuid4()), str(campaign_id), identity)
        cursor.execute("UPDATE crm_marketing.Campaign SET LastPreparedAtUtc=SYSUTCDATETIME(),UpdatedAtUtc=SYSUTCDATETIME() WHERE CampaignId=?", str(campaign_id))
        return {"matched": len(audience), "blocked": len(audience), "prepared": 0, "transport_enabled": False}

    def process_one(self):
        lease = str(uuid4())
        with self.transaction(True) as cursor:
            cursor.execute("UPDATE crm_marketing.EvaluationRun SET State=CASE WHEN Attempts>=3 THEN 'failed' ELSE 'queued' END,LeaseId=NULL,LeaseUntilUtc=NULL,LastError='evaluation_interrupted' WHERE State='processing' AND LeaseUntilUtc<SYSUTCDATETIME()")
            policy = cursor.execute("SELECT EvaluationEnabled,IntervalMinutes,NextRunAtUtc FROM crm_marketing.Policy WHERE PolicyId=1").fetchone()
            if policy[0] and policy[2] <= datetime.now(timezone.utc).replace(tzinfo=None):
                cursor.execute("INSERT crm_marketing.EvaluationRun(RunId,Kind,TriggerKind) VALUES(?,'predictions','worker')", str(uuid4()))
                cursor.execute("UPDATE crm_marketing.Policy SET NextRunAtUtc=DATEADD(minute,?,SYSUTCDATETIME()) WHERE PolicyId=1", policy[1])
            for rule in cursor.execute("SELECT TOP(10) RuleId FROM crm_marketing.RemarketingRule WHERE Enabled=1 AND ?=1 AND NextEvaluationAtUtc<=SYSUTCDATETIME() ORDER BY NextEvaluationAtUtc", bool(policy[0])).fetchall():
                cursor.execute("INSERT crm_marketing.EvaluationRun(RunId,Kind,TriggerKind,RuleId) VALUES(?,'remarketing','worker',?)", str(uuid4()), str(rule[0]))
                cursor.execute("UPDATE crm_marketing.RemarketingRule SET NextEvaluationAtUtc=DATEADD(minute,?,SYSUTCDATETIME()) WHERE RuleId=?", policy[1], str(rule[0]))
            run = cursor.execute("SELECT TOP(1) RunId,Kind,CampaignId,RuleId FROM crm_marketing.EvaluationRun WHERE State='queued' AND DueAtUtc<=SYSUTCDATETIME() ORDER BY RequestedAtUtc").fetchone()
            if not run:
                return False
            cursor.execute("UPDATE crm_marketing.EvaluationRun SET State='processing',Attempts=Attempts+1,StartedAtUtc=SYSUTCDATETIME(),LeaseId=?,LeaseUntilUtc=DATEADD(minute,3,SYSUTCDATETIME()) WHERE RunId=?", lease, str(run[0]))
        try:
            with self.transaction(True) as cursor:
                if not cursor.execute("SELECT 1 FROM crm_marketing.EvaluationRun WHERE RunId=? AND State='processing' AND LeaseId=? AND LeaseUntilUtc>SYSUTCDATETIME()", str(run[0]), lease).fetchone():
                    return True
                counts = {"transport_enabled": False}
                if run[1] == "preparation":
                    counts.update(self.prepare(cursor, run[2]))
                else:
                    weights = json.loads(cursor.execute("SELECT StageWeightsJson FROM crm_marketing.Policy WHERE PolicyId=1").fetchval())
                    conversations = cursor.execute("SELECT TOP(201) c.ConversationId,c.State,p.Stage FROM crm.Conversation c JOIN crm.Contact p ON p.ContactId=c.ContactId WHERE c.State<>'closed' ORDER BY c.CreatedAt").fetchall()
                    if len(conversations) > 200:
                        raise HTTPException(413, "prediction_scope_limit")
                    now = datetime.now(timezone.utc)
                    counts.update(assessed=len(conversations), known=0, unknown=0, eligible=0)
                    eligible_ids = set()
                    for conversation in conversations:
                        assessment, identity, lead, lead_reasons = assess(cursor, self.application.state.channel_store, conversation, weights, now)
                        cursor.execute("INSERT crm_marketing.ChurnAssessment(AssessmentId,ConversationId,IdentityId,AsOfUtc,InputSequence,FormulaVersion,Status,RiskScore,RiskLevel,StageSnapshot,WaitingSinceUtc,ReasonsJson,EvidenceJson,ComputedLeadScore,LeadReasonsJson,RunId) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", str(uuid4()), str(conversation[0]), identity, now.replace(tzinfo=None), assessment.input_sequence or None, assessment.formula_version, assessment.status, assessment.score, assessment.level, conversation[2], assessment.waiting_since.replace(tzinfo=None) if assessment.waiting_since else None, packed(assessment.reasons), packed(asdict(assessment)), lead, packed(lead_reasons), str(run[0]))
                        counts["known" if assessment.status == "known" else "unknown"] += 1
                        if run[3] and assessment.status == "known":
                            rule = cursor.execute("SELECT Enabled,StageValue,InactivityDays,MinimumRisk,CooldownHours FROM crm_marketing.RemarketingRule WHERE RuleId=?", str(run[3])).fetchone()
                            if rule and rule[0] and conversation[2] == rule[1] and assessment.score >= rule[3] and now - assessment.waiting_since >= timedelta(days=rule[2]):
                                counts["eligible"] += 1
                                recent = cursor.execute("SELECT TOP(1) r.UpdatedAtUtc FROM crm_marketing.CampaignRecipient r JOIN crm_marketing.Campaign c ON c.CampaignId=r.CampaignId WHERE c.RuleId=? AND r.IdentityId=? ORDER BY r.UpdatedAtUtc DESC", str(run[3]), identity).fetchone()
                                if not recent or now.replace(tzinfo=None) - recent[0] >= timedelta(hours=rule[4]):
                                    eligible_ids.add(identity)
                    if run[3]:
                        counts["delivery_blocked"] = counts["eligible"]
                        counts["cooldown_held"] = counts["eligible"] - len(eligible_ids)
                        counts["stage_age_days"] = None
                        counts["rule_clock"] = "confirmed_response_inactivity_not_stage_age"
                        if eligible_ids:
                            rule = rows(cursor.execute("SELECT * FROM crm_marketing.RemarketingRule WHERE RuleId=?", str(run[3])))[0]
                            cadence = cursor.execute("SELECT 1 FROM crm_marketing.AccountCadence WHERE Channel=? AND AccountScope=?", rule["Channel"], rule["AccountScope"]).fetchone()
                            if cadence:
                                campaigns = rows(cursor.execute("SELECT TOP(1) * FROM crm_marketing.Campaign WHERE RuleId=? ORDER BY CreatedAtUtc DESC", str(run[3])))
                                campaign_id = str(campaigns[0]["CampaignId"]) if campaigns else str(uuid4())
                                if not campaigns:
                                    cursor.execute("INSERT crm_marketing.Campaign(CampaignId,Name,Kind,RuleId,Channel,AccountScope,TemplateId,TemplateVersion,SegmentJson) VALUES(?,?,'remarketing',?,?,?,?,?,?)", campaign_id, rule["Name"], str(run[3]), rule["Channel"], rule["AccountScope"], str(rule["TemplateId"]), rule["TemplateVersion"], packed({"stage_values": [rule["StageValue"]]}))
                                counts.update(self.prepare(cursor, campaign_id, eligible_ids))
                            else:
                                counts["preparation_blocked"] = "account_cadence_required"
                cursor.execute("UPDATE crm_marketing.EvaluationRun SET State='completed',CountsJson=?,CompletedAtUtc=SYSUTCDATETIME(),LeaseId=NULL,LeaseUntilUtc=NULL,LastError=NULL WHERE RunId=? AND LeaseId=?", packed(counts), str(run[0]), lease)
        except Exception as error:
            code = error.detail if isinstance(error, HTTPException) and isinstance(error.detail, str) else "campaign_evaluation_failed"
            with self.transaction(True) as cursor:
                cursor.execute("UPDATE crm_marketing.EvaluationRun SET State='failed',CompletedAtUtc=SYSUTCDATETIME(),LastError=?,LeaseId=NULL,LeaseUntilUtc=NULL WHERE RunId=? AND LeaseId=?", code[:80], str(run[0]), lease)
        return True
