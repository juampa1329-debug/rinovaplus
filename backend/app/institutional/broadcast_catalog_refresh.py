"""Refresh approved Meta catalog reads while authorized campaigns are running."""

import json
import time

from fastapi import HTTPException

from app.institutional import broadcast_templates as templates
from app.institutional.broadcasts import authority, catalog, current, enabled
from app.institutional.channel_operations import account, configuration
from app.institutional.channel_provider import provider_account
from app.institutional.db import audit, institution, one
from app.institutional.store import transaction
from app.modules.channels import providers


class Refresher:
    def __init__(self, settings, *, request=None, clock=time.monotonic):
        self.settings = settings
        self.request = request or providers.request
        self.clock = clock
        self.next_check = 0.0

    def source(self, c, key):
        campaign = current(c, self.settings, key)
        if campaign["State"] not in {"running", "scheduled"}:
            raise HTTPException(409, "broadcast_catalog_campaign_inactive")
        actor = authority(c, self.settings, campaign)
        if "crm.read" not in json.loads(actor["Actions"]):
            raise HTTPException(403, "broadcast_authority_revoked")
        item = account(c, self.settings, str(campaign["IntegrationId"]))
        if (
            item["Channel"] != "whatsapp"
            or item["RequestedStatus"] != "connected"
            or item["VerifiedStatus"] != "verified"
            or item["ApplicationState"] == "retired"
        ):
            raise HTTPException(409, "broadcast_catalog_account_unavailable")
        adapter, credential = provider_account(c, self.settings, item)
        binding = (
            campaign["Revision"],
            campaign["Epoch"],
            str(campaign["ActorId"]),
            str(campaign["ActorSessionId"]),
            campaign["ActorAuthVersion"],
            bytes(item["RowVersion"]),
            str(credential["SecretId"]),
        )
        return binding, actor, item, adapter, credential

    def once(self):
        if getattr(self.settings, "postgres_profile", False) and not getattr(
            self.settings, "postgres_deployment", False
        ):
            return False  # Rehearsals never acquire live provider IO.
        stamp = self.clock()
        if stamp < self.next_check:
            return False
        self.next_check = stamp + 60
        with transaction(self.settings, False, anonymous=True) as c:
            if (
                not enabled(c, self.settings)
                or not configuration(c, self.settings)["OutboundEnabled"]
            ):
                return False
            due = one(
                c,
                "SELECT TOP(1) b.CampaignId FROM crm_broadcast7.Campaign b "
                "JOIN crm_broadcast7.Template t ON t.InstitutionId=b.InstitutionId "
                "AND t.TemplateId=b.TemplateId "
                "AND t.VersionNo=(SELECT MAX(v.VersionNo) "
                "FROM crm_broadcast7.Template v WHERE v.InstitutionId=t.InstitutionId "
                "AND v.TemplateId=t.TemplateId) WHERE b.InstitutionId=? "
                "AND b.State IN('running','scheduled') AND t.Origin='provider' "
                "AND t.ProviderStatus='APPROVED' AND t.Paused=0 "
                "AND (b.ScheduledAt IS NULL OR b.ScheduledAt<="
                "DATEADD(minute,15,SYSUTCDATETIME())) "
                "AND (t.ObservedAt IS NULL OR t.ObservedAt<="
                "DATEADD(minute,-45,SYSUTCDATETIME())) "
                "ORDER BY t.ObservedAt,b.CampaignId",
                institution(self.settings),
            )
            if not due:
                return False
            key = str(due["CampaignId"])
            binding, _, _, adapter, _ = self.source(c, key)
        fetched = templates.fetch(
            adapter, self.request
        )  # Catalog GET only; never send/create.
        with transaction(self.settings, True, anonymous=True) as c:
            if (
                not enabled(c, self.settings)
                or not configuration(c, self.settings)["OutboundEnabled"]
            ):
                return False
            checked, actor, item, _, credential = self.source(c, key)
            if checked != binding:
                raise HTTPException(409, "broadcast_catalog_binding_changed")
            seen = {str(v["id"]) for v in fetched}
            for value in fetched:
                templates.append(c, self.settings, item, value, credential, "provider")
            for old in catalog(c, self.settings, str(item["IntegrationId"])):
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
                        "provider",
                    )
            audit(
                c,
                self.settings,
                actor["UserId"],
                "broadcast.catalog_refresh",
                str(item["IntegrationId"]),
                fields=["templates"],
                reason="running_campaign_catalog_read",
            )
        return True
