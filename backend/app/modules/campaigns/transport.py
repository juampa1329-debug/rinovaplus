"""Non-configurable marketing transport boundary shared by the dispatcher."""

from app.modules.channels.providers import ProviderFailure


def reject_marketing(cursor, queue_id, payload):
    if payload.get("origin") in ("marketing", "campaign", "remarketing", "broadcast") or "campaignId" in payload:
        raise ProviderFailure("marketing_transport_disabled")
    if cursor.execute("SELECT OBJECT_ID(N'crm_marketing.CampaignRecipient')").fetchval() is not None:
        if cursor.execute("SELECT 1 FROM crm_marketing.CampaignRecipient WHERE QueueId=?", str(queue_id)).fetchone():
            raise ProviderFailure("marketing_transport_disabled")
