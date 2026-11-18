"""Read-only Marketing API. No advertising POST, spend or arbitrary next URL."""

import json
import re
import time
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

import httpx2 as httpx
from fastapi import HTTPException

INSIGHT_FIELDS = "date_start,date_stop,spend,impressions,reach,clicks,actions"


def external_id(value):
    value = str(value).removeprefix("act_")
    if not re.fullmatch(r"[0-9]{1,32}", value):
        raise HTTPException(422, "ads_meta_numeric_id_required")
    return value


def amount(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        result = Decimal(str(value))
        if result.is_finite() and 0 <= result <= Decimal("1000000000000000"):
            return float(result)
    except (InvalidOperation, ValueError):
        pass
    raise HTTPException(502, "ads_meta_invalid_response")


def metrics(row):
    spend = amount(row.get("spend"))
    impressions = amount(row.get("impressions"))
    clicks = amount(row.get("clicks"))
    reach = amount(row.get("reach"))
    actions = {}
    action_values = row.get("actions") or []
    if not isinstance(action_values, list):
        raise HTTPException(502, "ads_meta_invalid_response")
    for entry in action_values:
        if isinstance(entry, dict) and isinstance(entry.get("action_type"), str):
            actions[entry["action_type"]] = amount(entry.get("value"))
    # Meta's aggregate aliases overlap. Never add lead plus its components.
    leads = next(
        (
            actions[k]
            for k in (
                "lead",
                "onsite_conversion.lead_grouped",
                "offsite_conversion.fb_pixel_lead",
            )
            if k in actions
        ),
        0,
    )
    return dict(
        spend=spend,
        impressions=impressions,
        clicks=clicks,
        reach=reach,
        leads=leads,
        conversations=actions.get(
            "onsite_conversion.messaging_conversation_started_7d", 0
        ),
        ctr=100 * clicks / impressions if clicks is not None and impressions else None,
        cpc=spend / clicks if spend is not None and clicks else None,
        cpl=spend / leads if spend is not None and leads else None,
        cpm=1000 * spend / impressions if spend is not None and impressions else None,
    )


def validate_period(start, end):
    try:
        first, last = date.fromisoformat(start), date.fromisoformat(end)
    except (ValueError, TypeError):
        raise HTTPException(422, "ads_meta_invalid_period") from None
    # Account-local today may be one day ahead of UTC. Meta resolves its timezone.
    if last < first or (last - first).days > 92 or (last - date.today()).days > 1:
        raise HTTPException(422, "ads_meta_invalid_period")
    return {"since": first.isoformat(), "until": last.isoformat()}


class MetaReader:
    def __init__(self, token, version, *, transport=None):
        if not re.fullmatch(r"v[0-9]{1,3}\.0", version):
            raise HTTPException(409, "api_version_required")
        self.token, self.version = token, version
        self.transport = transport
        self.deadline = time.monotonic() + 40
        self.calls = 0

    def get(self, path, **params):
        if not re.fullmatch(r"(?:me|act_[0-9]{1,32}|[0-9]{1,32})(?:/[a-z_]+)?", path):
            raise HTTPException(422, "ads_meta_invalid_path")
        self.calls += 1
        left = self.deadline - time.monotonic()
        if self.calls > 40 or left <= 0:
            raise HTTPException(503, "ads_meta_scope_limit")
        if self.transport:
            value = self.transport(path, params)
        else:
            try:
                with httpx.Client(
                    trust_env=False, follow_redirects=False, timeout=min(left, 12)
                ) as client:
                    with client.stream(
                        "GET",
                        f"https://graph.facebook.com/{self.version}/{path}",
                        params=params,
                        headers={"Authorization": "Bearer " + self.token},
                    ) as response:
                        data = bytearray()
                        for chunk in response.iter_bytes():
                            data.extend(chunk)
                            if len(data) > 2_000_000:
                                raise HTTPException(502, "ads_meta_response_too_large")
                        value = json.loads(data)
                        if response.status_code >= 400 and (
                            not isinstance(value, dict) or not value.get("error")
                        ):
                            raise HTTPException(502, "ads_meta_unavailable")
            except (httpx.HTTPError, ValueError, TypeError):
                raise HTTPException(502, "ads_meta_unavailable") from None
        if not isinstance(value, dict):
            raise HTTPException(502, "ads_meta_invalid_response")
        if value.get("error"):
            code = (
                value["error"].get("code") if isinstance(value["error"], dict) else None
            )
            if code == 190:
                raise HTTPException(409, "ads_meta_token_expired")
            if code in {10, 200, 294}:
                raise HTTPException(403, "ads_meta_permission_required")
            if code in {4, 17, 32, 613, 80004}:
                raise HTTPException(
                    429, "ads_meta_rate_limited", headers={"Retry-After": "60"}
                )
            raise HTTPException(502, "ads_meta_request_rejected")
        return value

    def edge(self, path, **params):
        result, seen, after = [], set(), None
        for _ in range(10):
            value = self.get(
                path, **params, limit=100, **({"after": after} if after else {})
            )
            data = value.get("data")
            if not isinstance(data, list) or any(not isinstance(v, dict) for v in data):
                raise HTTPException(502, "ads_meta_invalid_response")
            result.extend(data)
            if len(result) > 500:
                raise HTTPException(413, "ads_meta_scope_limit")
            paging = value.get("paging", {})
            if not isinstance(paging, dict) or not paging.get("next"):
                return result
            cursors = paging.get("cursors")
            after = cursors.get("after") if isinstance(cursors, dict) else None
            if (
                not isinstance(after, str)
                or not 1 <= len(after) <= 2000
                or after in seen
            ):
                raise HTTPException(502, "ads_meta_invalid_pagination")
            seen.add(after)
        raise HTTPException(413, "ads_meta_scope_limit")

    def accounts(self):
        return [
            self.account_value(v)
            for v in self.edge(
                "me/adaccounts",
                fields="id,account_id,name,currency,timezone_name,account_status",
            )
        ]

    @staticmethod
    def account_value(value):
        identity = external_id(value.get("account_id") or value.get("id", ""))
        currency = str(value.get("currency", ""))
        if (
            not re.fullmatch(r"[A-Z]{3}", currency)
            or not str(value.get("name", "")).strip()
            or not value.get("timezone_name")
        ):
            raise HTTPException(502, "ads_meta_invalid_response")
        return dict(
            id=identity,
            name=str(value.get("name", ""))[:180],
            currency=currency,
            timezone=str(value["timezone_name"])[:80],
            account_status=value.get("account_status"),
        )

    def account(self, identity):
        identity = external_id(identity)
        value = self.account_value(
            self.get(
                "act_" + identity,
                fields="id,account_id,name,currency,timezone_name,account_status",
            )
        )
        if value["id"] != identity:
            raise HTTPException(409, "ads_meta_account_mismatch")
        return value

    def snapshot(self, identity, start, end):
        identity = external_id(identity)
        period = validate_period(start, end)
        target = "act_" + identity
        account = self.account(identity)
        campaigns = self.edge(
            target + "/campaigns",
            fields="id,name,status,effective_status,objective,daily_budget,lifetime_budget",
        )
        adsets = self.edge(
            target + "/adsets",
            fields="id,name,campaign_id,status,effective_status,daily_budget,lifetime_budget,optimization_goal,billing_event",
        )
        ads = self.edge(
            target + "/ads",
            fields="id,name,campaign_id,adset_id,status,effective_status,creative{id,name,title,body,image_url,thumbnail_url,object_story_spec}",
        )
        report = dict(
            time_range=json.dumps(period), fields=INSIGHT_FIELDS, level="account"
        )
        aggregate = self.edge(target + "/insights", **report)
        daily = self.edge(target + "/insights", **report, time_increment=1)
        by_ad = self.edge(
            target + "/insights",
            time_range=json.dumps(period),
            fields=INSIGHT_FIELDS + ",ad_id,campaign_id,adset_id",
            level="ad",
        )
        if len(aggregate) > 1:
            raise HTTPException(502, "ads_meta_invalid_response")
        for value in daily:
            try:
                day = date.fromisoformat(value.get("date_start", ""))
                if not date.fromisoformat(start) <= day <= date.fromisoformat(end):
                    raise ValueError()
            except (ValueError, TypeError):
                raise HTTPException(502, "ads_meta_invalid_response") from None
        # Missing aggregate is a successful, explicitly empty report, not a failed sync.
        empty = dict(spend="0", impressions="0", clicks="0", reach="0")

        def objects(values, fields):
            output = []
            for value in values:
                row = {k: value[k] for k in fields if k in value}
                row["id"] = external_id(value.get("id", ""))
                output.append(row)
            return output

        return dict(
            schema="meta_ads_snapshot_v1",
            source="meta_marketing_api",
            synced_at=datetime.now(timezone.utc).isoformat(),
            account=account,
            period={"start": start, "end": end},
            no_delivery=not aggregate,
            totals=metrics(aggregate[0] if aggregate else empty),
            daily=[dict(date=v["date_start"], **metrics(v)) for v in daily],
            campaigns=objects(
                campaigns,
                [
                    "name",
                    "status",
                    "effective_status",
                    "objective",
                    "daily_budget",
                    "lifetime_budget",
                ],
            ),
            adsets=objects(
                adsets,
                [
                    "name",
                    "campaign_id",
                    "status",
                    "effective_status",
                    "daily_budget",
                    "lifetime_budget",
                    "optimization_goal",
                    "billing_event",
                ],
            ),
            ads=[
                dict(v, creative=creative(v.get("creative", {})))
                for v in objects(
                    ads,
                    [
                        "name",
                        "campaign_id",
                        "adset_id",
                        "status",
                        "effective_status",
                        "creative",
                    ],
                )
            ],
            ad_insights=[
                dict(
                    ad_id=external_id(v.get("ad_id", "")),
                    campaign_id=v.get("campaign_id"),
                    adset_id=v.get("adset_id"),
                    **metrics(v),
                )
                for v in by_ad
            ],
            provider_writes=False,
        )


def creative(value):
    if not isinstance(value, dict):
        return {}
    story = value.get("object_story_spec") or {}
    if not isinstance(story, dict):
        story = {}
    link = story.get("link_data") or story.get("video_data") or {}
    if not isinstance(link, dict):
        link = {}
    # Drop all unexpected provider fields; never return access tokens or raw specs.
    return dict(
        id=str(value.get("id", ""))[:64],
        title=str(value.get("title") or link.get("name") or link.get("title") or "")[
            :500
        ],
        body=str(value.get("body") or link.get("message") or "")[:8000],
        image_url=str(
            value.get("image_url")
            or value.get("thumbnail_url")
            or link.get("picture")
            or link.get("image_url")
            or ""
        )[:2000],
        destination_url=str(link.get("link") or "")[:2000],
    )
