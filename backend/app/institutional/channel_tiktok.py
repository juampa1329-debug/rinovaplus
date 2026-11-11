"""Explicit operator intent becomes a closed Business API policy, never a grant."""

import json

from fastapi import HTTPException

from app.institutional.db import institution


def apply_policy(c, settings, item):
    raw = c.execute(
        (
            "SELECT Document FROM crm_access.ChannelSetting WHERE Institu"
            "tionId=? AND IntegrationId=?"
        ),
        institution(settings),
        item["IntegrationId"],
    ).fetchval()
    value = json.loads(raw) if raw else {}
    base = (
        value.get("runtime_policy.business_api_base_url")
        or "https://business-api.tiktok.com"
    )
    version = value.get("runtime_policy.business_api_version") or "v1.3"
    if base.rstrip("/") != "https://business-api.tiktok.com" or version not in {
        "1.3",
        "v1.3",
    }:
        raise HTTPException(422, "tiktok_unapproved_api_destination")
    for key, approved in [
        ("runtime_policy.send_message_path", "/business/message/send/"),
        ("runtime_policy.comment_reply_path", "/business/comment/reply/create/"),
    ]:
        if value.get(key) and "/" + value[key].lstrip("/") != approved:
            raise HTTPException(422, "tiktok_unapproved_api_path")
    policy = {
        "ConfiguredScopes": json.dumps(value.get("scopes", [])),
        "ReviewStatus": value.get("app_review_status") or "untracked",
        "ApprovedProducts": json.dumps(value.get("approved_products", [])),
        "ApprovedScopes": json.dumps(value.get("approved_scopes", [])),
        "OperatorAttestedEvents": bool(value.get("payload_samples_validated", False)),
        "OutboundMode": value.get("runtime_policy.outbound_mode") or "disabled",
        "RolloutPercent": value.get("runtime_policy.rollout_percent") or 0,
        "DailyOutboundQuota": value.get("runtime_policy.daily_outbound_quota") or 0,
        "DailyAiQuota": value.get("runtime_policy.daily_ai_quota") or 0,
        "BusinessMessagingEnabled": bool(
            value.get("runtime_policy.business_messaging_enabled", False)
        ),
        "CommentReplyEnabled": bool(
            value.get("runtime_policy.comment_reply_enabled", False)
        ),
        "AiEnabled": bool(value.get("runtime_policy.ai_enabled", False)),
        # Those execution surfaces belong to later phases, not this manual channel
        # policy.
        "AgentsEnabled": False,
        "TriggersEnabled": False,
        "RemarketingEnabled": False,
        "BusinessApiBaseUrl": "https://business-api.tiktok.com",
        "BusinessApiVersion": "v1.3",
        "SendMessagePath": "/business/message/send/",
        "CommentReplyPath": "/business/comment/reply/create/",
        "RuntimeNotes": str(value.get("runtime_policy.notes") or "")[:1200],
    }
    if c.execute(
        (
            "SELECT 1 FROM crm_channels2.TikTokPolicy WHERE InstitutionId"
            "=? AND IntegrationId=?"
        ),
        institution(settings),
        item["IntegrationId"],
    ).fetchone():
        c.execute(
            "UPDATE crm_channels2.TikTokPolicy SET "
            + ",".join(k + "=?" for k in policy)
            + ",UpdatedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND IntegrationId=?",
            *policy.values(),
            institution(settings),
            item["IntegrationId"],
        )
    else:
        names = list(policy)
        c.execute(
            "INSERT crm_channels2.TikTokPolicy(InstitutionId,IntegrationId,"
            + ",".join(names)
            + ",UpdatedAt) VALUES("
            + ",".join("?" for _ in range(len(names) + 2))
            + ",SYSUTCDATETIME())",
            institution(settings),
            item["IntegrationId"],
            *policy.values(),
        )
