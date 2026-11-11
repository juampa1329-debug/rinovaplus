"""Ads processing has its own cursor; never consumes or acknowledges C10 message work."""

import json
from datetime import datetime, timezone

from cryptography.exceptions import InvalidTag
from fastapi import HTTPException
from pydantic import ValidationError

from app.institutional.ads import (
    account,
    clock,
    convert,
    event,
    get,
    packed,
    public,
    stable,
)
from app.institutional.ads_models import Intake
from app.institutional.auth import authorize
from app.institutional.channel_ingress import body_owner, strict_json
from app.institutional.crypto import unseal
from app.institutional.db import (
    institution,
    key,
    one,
    record_operation,
    replay,
    rows,
    uid,
)


def moment(value, fallback):
    if value in (None, ""):
        return fallback.replace(tzinfo=timezone.utc).isoformat()
    if isinstance(value, (int, float)) or isinstance(value, str) and value.isdecimal():
        return datetime.fromtimestamp(float(value), timezone.utc).isoformat()
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).isoformat()


def fields(v):
    result = {}
    for name in ["field_data", "fields", "answers", "questions", "form_values"]:
        data = v.get(name, [])
        if isinstance(data, dict):
            for k, value in list(data.items())[:100]:
                if isinstance(k, str) and isinstance(value, (str, int, float)):
                    result[k.lower()] = str(value)
        elif isinstance(data, list):
            for item in data[:100]:
                if not isinstance(item, dict):
                    continue
                key = (
                    item.get("name")
                    or item.get("key")
                    or item.get("question")
                    or item.get("field")
                )
                values = item.get("values", [])
                value = (
                    item.get("value")
                    or item.get("answer")
                    or (values[0] if isinstance(values, list) and values else "")
                )
                if isinstance(key, str) and isinstance(value, (str, int, float)):
                    result[key.lower()] = str(value)
    return result


def normalize(provider, payload, received):
    output = []

    def add(kind, v, route, channel):
        data = fields(v)
        author = (
            v.get("from") or v.get("author") or v.get("sender") or v.get("user") or {}
        )
        author = author if isinstance(author, dict) else {}
        external = (
            v.get("leadgen_id")
            or v.get("lead_id")
            or v.get("leadgenId")
            or v.get("leadID")
            or v.get("id")
            if kind == "lead"
            else v.get("comment_id") or v.get("commentId") or v.get("id")
        )
        if not external:
            raise ValueError("ads_external_id_required")
        doc = dict(
            channel=channel,
            external_id=str(external),
            external_form_id=str(
                v.get("form_id") or v.get("formId") or v.get("instant_form_id") or ""
            ),
            external_ad_id=str(v.get("ad_id") or v.get("adId") or ""),
            external_campaign_id=str(v.get("campaign_id") or v.get("campaignId") or ""),
            author_id=str(
                author.get("id")
                or author.get("open_id")
                or author.get("user_id")
                or v.get("author_id")
                or v.get("sender_id")
                or ""
            ),
            contact_name=str(
                v.get("full_name")
                or v.get("name")
                or v.get("contact_name")
                or data.get("full_name")
                or data.get("name")
                or author.get("name")
                or author.get("display_name")
                or v.get("author_name")
                or v.get("username")
                or author.get("username")
                or ""
            ),
            email=str(v.get("email") or data.get("email") or ""),
            phone=str(
                v.get("phone")
                or v.get("phone_number")
                or data.get("phone_number")
                or data.get("phone")
                or ""
            ),
            message=str(
                v.get("message")
                or v.get("text")
                or v.get("comment_text")
                or v.get("commentText")
                or v.get("comment")
                or ""
            ),
            external_post_id=str(
                v.get("post_id")
                or v.get("media_id")
                or v.get("video_id")
                or v.get("item_id")
                or ""
            ),
            external_parent_id=str(
                v.get("parent_id") or v.get("parent_comment_id") or ""
            ),
            permalink_url=str(
                v.get("permalink_url") or v.get("permalink") or v.get("video_url") or ""
            ),
            captured_at=moment(v.get("created_time") or v.get("timestamp"), received),
            status="deleted" if v.get("verb") in {"remove", "delete"} else "new",
        )
        output.append(
            dict(
                kind=kind,
                route=str(route or ""),
                advertiser=str(v.get("ad_account_id") or v.get("advertiser_id") or ""),
                document=doc,
            )
        )
        if len(output) > 50:
            raise ValueError("ads_receipt_item_limit")

    if provider == "meta":
        channel = "instagram" if payload.get("object") == "instagram" else "facebook"
        entries = payload.get("entry", [])
        if not isinstance(entries, list) or len(entries) > 100:
            raise ValueError("ads_payload_invalid")
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            for change in entry.get("changes", [])[:100]:
                if not isinstance(change, dict):
                    continue
                value = change.get("value")
                if not isinstance(value, dict):
                    continue
                field = change.get("field")
                if field in {"leadgen", "leadgen_id"} or value.get("leadgen_id"):
                    add("lead", value, entry.get("id"), channel)
                elif field in {"feed", "comments", "comment"} and (
                    value.get("comment_id") or field in {"comments", "comment"}
                ):
                    add("comment", value, entry.get("id"), channel)
        direct_route = (
            payload.get("page_id")
            or payload.get("instagram_business_account_id")
            or payload.get("business_id")
        )
        direct_channel = (
            "instagram"
            if payload.get("channel") == "instagram"
            or payload.get("object") == "instagram"
            else "facebook"
        )
        if (
            payload.get("leadgen_id")
            or payload.get("lead_id")
            or payload.get("id")
            and any(
                payload.get(v)
                for v in [
                    "form_id",
                    "field_data",
                    "email",
                    "phone",
                    "phone_number",
                    "full_name",
                ]
            )
        ):
            if not direct_route:
                raise ValueError("ads_route_required")
            add("lead", payload, direct_route, direct_channel)
        if (
            payload.get("comment_id")
            or payload.get("id")
            and payload.get("message")
            and not (payload.get("lead_id") or payload.get("leadgen_id"))
        ):
            if not direct_route:
                raise ValueError("ads_route_required")
            add("comment", payload, direct_route, direct_channel)
    elif provider == "tiktok":
        content = payload.get("content", {})
        if isinstance(content, str):
            content = strict_json(content)
        if not isinstance(content, dict):
            raise ValueError("ads_payload_invalid")
        root = {**payload, **content}
        route = root.get("user_openid") or root.get("business_id")
        stack = [(root, 0)]
        seen = set()
        scanned = 0
        while stack:
            item, depth = stack.pop()
            scanned += 1
            if scanned > 160 or depth > 8:
                raise ValueError("ads_payload_depth_limit")
            if isinstance(item, dict):
                marker = " ".join(
                    str(item.get(k) or "")
                    for k in [
                        "event",
                        "event_type",
                        "type",
                        "field",
                        "object",
                        "object_type",
                        "action",
                        "verb",
                    ]
                ).lower()
                if isinstance(item.get("comment"), dict):
                    item = {**item, **item["comment"], "event": "comment"}
                    marker = "comment"
                lead_id = (
                    item.get("lead_id")
                    or item.get("leadgen_id")
                    or item.get("leadgenId")
                    or item.get("leadID")
                )
                comment_id = item.get("comment_id") or item.get("commentId")
                if not lead_id and ("lead" in marker or "form" in marker):
                    lead_id = item.get("id")
                if not comment_id and (
                    "comment" in marker
                    or item.get("comment_text")
                    or item.get("commentText")
                ):
                    comment_id = item.get("id")
                for kind, external in [("lead", lead_id), ("comment", comment_id)]:
                    if external and (kind, str(external)) not in seen:
                        seen.add((kind, str(external)))
                        v = {
                            **item,
                            "advertiser_id": item.get("advertiser_id")
                            or root.get("advertiser_id")
                            or "",
                        }
                        v["lead_id" if kind == "lead" else "comment_id"] = external
                        add(kind, v, route or item.get("business_id"), "tiktok")
                stack.extend(
                    (v, depth + 1) for v in item.values() if isinstance(v, (dict, list))
                )
            elif isinstance(item, list):
                stack.extend(
                    (v, depth + 1) for v in item if isinstance(v, (dict, list))
                )
    return output


def binding(c, s, a, effect):
    native = one(
        c,
        "SELECT ExternalAccountId,Channel,ApplicationId FROM crm_channels2.Integration WHERE InstitutionId=? AND IntegrationId=?",
        institution(s),
        a["IntegrationId"],
    )
    if (
        not native
        or effect["route"] != native["ExternalAccountId"]
        or native["Channel"]
        not in (
            {"facebook", "messenger"}
            if effect["document"]["channel"] == "facebook"
            else {effect["document"]["channel"]}
        )
    ):
        return False
    advertiser = effect["advertiser"].removeprefix("act_")
    if advertiser:
        if advertiser != a["ExternalId"].removeprefix("act_"):
            return False
        return True
    doc = effect["document"]
    matches = []
    for candidate in rows(
        c,
        "SELECT * FROM crm_ads9.Account WHERE InstitutionId=? AND IntegrationId=? AND State='connected'",
        institution(s),
        a["IntegrationId"],
    ):
        configured = json.loads(candidate["Document"])
        found = bool(
            doc["external_form_id"]
            and doc["external_form_id"] in configured["form_ids"]
        )
        if doc["external_campaign_id"]:
            found = found or bool(
                c.execute(
                    "SELECT 1 FROM crm_ads9.Campaign WHERE InstitutionId=? AND AccountId=? AND ExternalId=?",
                    institution(s),
                    candidate["AccountId"],
                    doc["external_campaign_id"],
                ).fetchone()
            )
        if found:
            matches.append(uid(str(candidate["AccountId"])))
    if not matches:
        raise HTTPException(409, "ads_campaign_or_form_mapping_required")
    if len(matches) != 1:
        raise HTTPException(409, "ads_ambiguous_account_mapping")
    return matches[0] == uid(str(a["AccountId"]))


def process(service, auth, id, body, retry_id=None):
    s = service.settings
    with service.tx(auth, True) as (c, actor):
        if body.create_conversation:
            authorize(c, s, auth, "crm.write")
            authorize(c, s, auth, "inbox.write")
        digest, old = replay(
            c,
            s,
            actor["UserId"],
            str(body.operation_id),
            "ads9.process",
            retry_id or id,
            body.model_dump(mode="json"),
        )
        if old:
            return old
        a = account(c, s, id)
        if a["State"] != "connected":
            raise HTTPException(409, "ads_account_paused")
        if not a["IntegrationId"]:
            raise HTTPException(409, "ads_channel_binding_required")
        previous = get(c, s, retry_id, "run") if retry_id else None
        if previous:
            if uid(str(previous["AccountId"])) != id:
                raise HTTPException(404, "ads_record_not_found")
            if (
                previous["Revision"] != body.revision
                or previous["State"] != "quarantined"
            ):
                raise HTTPException(409, "ads_retry_requires_quarantine")
        elif body.revision != a["Revision"]:
            raise HTTPException(409, "revision_conflict")
        query = "SELECT TOP(1) r.*,ep.Provider,ep.IsActive,app.State AS ApplicationState,i.ExternalAccountId,i.RequestedStatus,i.VerifiedStatus,i.Channel AS NativeChannel,ei.RouteKind,ei.ExternalId AS BoundExternalId FROM crm_channels2.WebhookReceipt r JOIN crm_channels2.WebhookEndpoint ep ON ep.InstitutionId=r.InstitutionId AND ep.EndpointId=r.EndpointId AND ep.ApplicationId=r.ApplicationId JOIN crm_channels2.Application app ON app.InstitutionId=ep.InstitutionId AND app.ApplicationId=ep.ApplicationId JOIN crm_channels2.EndpointIntegration ei ON ei.InstitutionId=r.InstitutionId AND ei.EndpointId=r.EndpointId AND ei.ApplicationId=r.ApplicationId JOIN crm_channels2.Integration i ON i.InstitutionId=ei.InstitutionId AND i.IntegrationId=ei.IntegrationId AND i.ApplicationId=ei.ApplicationId WHERE r.InstitutionId=? AND ei.IntegrationId=? AND ei.IsActive=1 AND r.Authentication='verified' AND r.SignatureVerifiedAt IS NOT NULL"
        params = [institution(s), a["IntegrationId"]]
        if previous:
            query += " AND r.ReceiptId=?"
            params.append(previous["ReceiptId"])
        else:
            query += " AND NOT EXISTS(SELECT 1 FROM crm_ads9.SyncRun p WHERE p.InstitutionId=r.InstitutionId AND p.AccountId=? AND p.ReceiptId=r.ReceiptId)"
            params.append(id)
        query += " ORDER BY r.ReceivedAt,r.ReceiptId"
        receipt = one(c, query, *params)
        if not receipt:
            result = dict(state="empty", processed=0, provider_writes=False)
            record_operation(
                c,
                s,
                actor["UserId"],
                str(body.operation_id),
                "ads9.process",
                retry_id or id,
                digest,
                result,
            )
            return result
        run_id = retry_id or stable(id, "receipt", uid(str(receipt["ReceiptId"])))
        stats = dict(leads=0, comments=0, conversations=0, duplicates=0)
        state, error = "ignored", None
        c.execute("SAVE TRANSACTION ads_capture")
        try:
            if (
                not receipt["IsActive"]
                or receipt["ApplicationState"] == "retired"
                or receipt["ExpiresAt"] <= clock()
                or receipt["BodyPurgedAt"] is not None
            ):
                raise HTTPException(409, "ads_receipt_unavailable")
            if (
                receipt["RequestedStatus"] != "connected"
                or receipt["VerifiedStatus"] != "verified"
                or receipt["RouteKind"] != "configured_" + receipt["NativeChannel"]
                or receipt["BoundExternalId"] != receipt["ExternalAccountId"]
            ):
                raise HTTPException(409, "ads_channel_context_changed")
            raw = unseal(
                key(s),
                body_owner(s, receipt["ReceiptId"], receipt["EndpointId"]),
                receipt["BodyNonce"],
                receipt["BodyCiphertext"],
            )
            effects = normalize(
                receipt["Provider"], strict_json(raw), receipt["ReceivedAt"]
            )
            prepared = []
            for effect in effects:
                if not binding(c, s, a, effect):
                    continue
                doc = Intake(account_id=id, **effect["document"]).model_dump(
                    mode="json"
                )
                prepared.append((effect["kind"], doc))
            for kind, doc in prepared:
                intake_id = stable(
                    institution(s), id, kind, doc["channel"], doc["external_id"]
                )
                current = one(
                    c,
                    "SELECT * FROM crm_ads9.Intake WHERE InstitutionId=? AND IntakeId=?",
                    institution(s),
                    intake_id,
                )
                if current:
                    stats["duplicates"] += 1
                    previous_doc = json.loads(current["Document"])
                    enriched = dict(previous_doc)
                    changed = []
                    for field in [
                        "contact_name",
                        "email",
                        "phone",
                        "author_id",
                        "message",
                        "external_form_id",
                        "external_ad_id",
                        "external_campaign_id",
                        "external_post_id",
                        "external_parent_id",
                        "permalink_url",
                    ]:
                        if (
                            doc[field]
                            and doc[field] != previous_doc[field]
                            and (
                                current["Origin"] == "verified_receipt"
                                or not previous_doc[field]
                            )
                        ):
                            enriched[field] = doc[field]
                            changed.append(field)
                    if changed:
                        c.execute(
                            "UPDATE crm_ads9.Intake SET Document=?,Revision=Revision+1,UpdatedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND IntakeId=?",
                            packed(enriched),
                            institution(s),
                            intake_id,
                        )
                        event(
                            c,
                            s,
                            id,
                            actor,
                            "capture_enriched",
                            dict(fields=changed, CRM_contact_overwritten=False),
                            intake=intake_id,
                        )
                    if doc["status"] == "deleted" and current["State"] != "deleted":
                        c.execute(
                            "UPDATE crm_ads9.Intake SET State='deleted',Revision=Revision+1,UpdatedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND IntakeId=?",
                            institution(s),
                            intake_id,
                        )
                        event(
                            c,
                            s,
                            id,
                            actor,
                            "provider_comment_deleted",
                            {},
                            intake=intake_id,
                        )
                else:
                    service.insert_intake(
                        c,
                        actor,
                        a,
                        kind,
                        intake_id,
                        doc,
                        receipt=str(receipt["ReceiptId"]),
                        origin="verified_receipt",
                    )
                current = get(c, s, intake_id, "intake")
                if body.create_conversation and current["State"] not in {
                    "hidden",
                    "deleted",
                }:
                    was = current["IdentityId"]
                    convert(c, s, auth, actor, current, a)
                    if not was:
                        stats["conversations"] += 1
                stats["leads" if kind == "lead" else "comments"] += 1
            if prepared:
                state = "processed"
        except (
            HTTPException,
            ValidationError,
            ValueError,
            TypeError,
            KeyError,
            AttributeError,
            InvalidTag,
            OverflowError,
            OSError,
        ) as failure:
            c.execute("ROLLBACK TRANSACTION ads_capture")
            state = "quarantined"
            stats = dict(leads=0, comments=0, conversations=0, duplicates=0)
            error = (
                str(failure.detail)[:100]
                if isinstance(failure, HTTPException)
                else "ads_payload_invalid"
            )
        if previous:
            c.execute(
                "UPDATE crm_ads9.SyncRun SET State=?,Revision=Revision+1,ActorId=?,OperationId=?,Document=?,ErrorCode=?,StartedAt=SYSUTCDATETIME(),CompletedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND RunId=?",
                state,
                actor["UserId"],
                str(body.operation_id),
                packed(stats),
                error,
                institution(s),
                run_id,
            )
        else:
            c.execute(
                "INSERT crm_ads9.SyncRun(InstitutionId,RunId,AccountId,ReceiptId,State,Revision,ActorId,OperationId,Document,ErrorCode) VALUES(?,?,?,?,?,1,?,?,?,?)",
                institution(s),
                run_id,
                id,
                receipt["ReceiptId"],
                state,
                actor["UserId"],
                str(body.operation_id),
                packed(stats),
                error,
            )
        event(
            c,
            s,
            id,
            actor,
            "receipt_" + state,
            dict(**stats, error=error, receipt_id=uid(str(receipt["ReceiptId"]))),
            run=run_id,
        )
        result = public(c, s, get(c, s, run_id, "run"), "run")
        record_operation(
            c,
            s,
            actor["UserId"],
            str(body.operation_id),
            "ads9.process",
            retry_id or id,
            digest,
            result,
        )
        return result
