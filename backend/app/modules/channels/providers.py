"""Fixed-host provider HTTP adapters; credentials never enter returned errors."""

import json
import re

import httpx2 as httpx


class ProviderFailure(Exception):
    def __init__(self, code, retry=False, uncertain=False):
        self.code, self.retry, self.uncertain = code, retry, uncertain


def whatsapp_user_id(value):
    return isinstance(value, str) and re.fullmatch(r"[A-Z]{2}\.(?:ENT\.)?[A-Za-z0-9]{1,128}", value) is not None


def whatsapp_recipient(target):
    return {"recipient" if whatsapp_user_id(target) else "to": target}


def whatsapp_delivery_error(error):
    if not isinstance(error, dict):
        return None
    return {
        131042: "whatsapp_billing_issue",
        131047: "whatsapp_reply_window_closed",
        131026: "whatsapp_recipient_unreachable",
        130429: "whatsapp_rate_limit",
        131053: "whatsapp_media_upload_failed",
    }.get(error["code"]) if type(error.get("code")) is int else None


def graph_base(account):
    config = account["configuration"]
    host = (
        "graph.instagram.com"
        if account["channel"] == "instagram"
        and config.get("instagramLogin") == "instagram"
        else "graph.facebook.com"
    )
    version = config.get("apiVersion", "")
    return f"https://{host}/" + (version + "/" if version else "")


def request(
    account, method, path, body=None, params=None, response_metadata=None, files=None
):
    token = account["secrets"].get("accessToken")
    if not token:
        raise ProviderFailure("access_token_required")
    if (
        account["channel"] != "tiktok"
        and method != "GET"
        and not account["configuration"].get("apiVersion")
    ):
        raise ProviderFailure("api_version_required")
    headers = {"Authorization": "Bearer " + token}
    base = graph_base(account)
    if account["channel"] == "tiktok":
        base = "https://business-api.tiktok.com/open_api/v1.3/"
        headers = (
            {}
            if path in ("business/webhook/update/", "tt_user/token_info/get/")
            else {"Access-Token": token}
        )
    try:
        with httpx.Client(
            timeout=12, follow_redirects=False, trust_env=False
        ) as client:
            with client.stream(
                method,
                base + path,
                headers=headers,
                json=body,
                params=params,
                files=files,
            ) as response:
                data = bytearray()
                for chunk in response.iter_bytes():
                    data.extend(chunk)
                    if len(data) > 1_000_000:
                        raise ProviderFailure(
                            "provider_response_too_large", uncertain=method != "GET"
                        )
                try:
                    result = json.loads(data)
                except (ValueError, UnicodeDecodeError):
                    result = None
                if account["channel"] != "tiktok" and isinstance(result, dict):
                    error = result.get("error")
                    if isinstance(error, dict) and error.get("code") == 190:
                        raise ProviderFailure(
                            "meta_access_token_expired"
                            if error.get("error_subcode") == 463
                            else "meta_access_token_invalid"
                        )
                    if account["channel"] == "whatsapp" and method == "POST":
                        reason = whatsapp_delivery_error(error)
                        if reason:
                            raise ProviderFailure(reason)
                if response.status_code >= 300:
                    raise ProviderFailure(
                        "provider_permission_or_request_rejected"
                        if response.status_code in (400, 401, 403)
                        else "provider_unavailable",
                        retry=response.status_code == 429
                        or (
                            method == "GET"
                            and response.status_code in (500, 502, 503, 504)
                        ),
                        uncertain=method != "GET" and response.status_code >= 500,
                    )
                if not isinstance(result, dict):
                    raise ProviderFailure(
                        "provider_response_invalid", uncertain=method != "GET"
                    )
                if result.get("error") or (
                    account["channel"] == "tiktok" and result.get("code") != 0
                ):
                    raise ProviderFailure("provider_permission_or_request_rejected")
                if response_metadata is not None and account["channel"] != "tiktok":
                    version = response.headers.get("facebook-api-version", "")
                    if re.fullmatch(r"v[0-9]{1,2}\.0", version):
                        if response_metadata.get("apiVersion") not in (None, version):
                            raise ProviderFailure("provider_api_version_inconsistent")
                        response_metadata["apiVersion"] = version
                return result
    except (httpx.ConnectError, httpx.ConnectTimeout):
        raise ProviderFailure("provider_connection_failed", retry=True) from None
    except (
        httpx.ReadTimeout,
        httpx.WriteTimeout,
        httpx.ReadError,
        httpx.WriteError,
        httpx.RemoteProtocolError,
    ):
        raise ProviderFailure(
            "provider_outcome_unknown", uncertain=method != "GET", retry=method == "GET"
        ) from None
    except (ValueError, KeyError):
        raise ProviderFailure(
            "provider_response_invalid", uncertain=method != "GET"
        ) from None


def discover(account):
    config = account["configuration"]
    channel = account["channel"]
    if channel == "tiktok":
        return tiktok_discover(account)
    asset = (
        config.get("phoneNumberId")
        if channel == "whatsapp"
        else config.get("accountId")
        if channel == "instagram"
        else config.get("pageId")
    )
    if not asset:
        raise ProviderFailure("asset_id_required")
    fields = (
        "id,display_phone_number,verified_name"
        if channel == "whatsapp"
        else "id,username"
        if channel == "instagram"
        else "id,name"
    )
    metadata = {}
    resource = request(
        account, "GET", asset, params={"fields": fields}, response_metadata=metadata
    )
    if str(resource.get("id")) != asset:
        raise ProviderFailure("provider_asset_mismatch")
    result = {
        "asset": {
            k: v
            for k, v in resource.items()
            if k in ("id", "name", "username", "display_phone_number", "verified_name")
        },
        "supportedMessages": channel != "facebook",
        "supportedComments": channel in ("facebook", "instagram"),
        "apiAssetValidated": True,
    }
    if metadata.get("apiVersion"):
        result["observedApiVersion"] = metadata["apiVersion"]
    if channel == "whatsapp":
        numbers = request(
            account,
            "GET",
            config["wabaId"] + "/phone_numbers",
            response_metadata=metadata,
        )
        if not any(str(n.get("id")) == asset for n in numbers.get("data", [])):
            raise ProviderFailure("phone_not_in_waba")
        result["numbers"] = [
            {k: n[k] for k in ("id", "display_phone_number", "verified_name") if k in n}
            for n in numbers.get("data", [])
        ]
        if not config.get("apiVersion") and metadata.get("apiVersion"):
            result["discoveredApiVersion"] = metadata["apiVersion"]
    return result


def whatsapp_webhook_configuration(account, *, allow_unconfigured=False):
    phone = account["configuration"]["phoneNumberId"]
    value = request(account, "GET", phone, params={"fields": "webhook_configuration"})
    # Meta omits this field for a number without a configured route. Permit
    # initial setup, but never treat that omission as post-write confirmation.
    routing = value.get("webhook_configuration")
    if allow_unconfigured and "webhook_configuration" not in value:
        routing = {}
    if str(value.get("id")) != phone or not isinstance(routing, dict):
        raise ProviderFailure("whatsapp_webhook_route_unavailable")
    return routing


def subscribe_whatsapp_callback(account, callback_url, verify_token):
    routing = whatsapp_webhook_configuration(account, allow_unconfigured=True)
    phone_route = routing.get("phone_number")
    if phone_route and phone_route != callback_url:
        raise ProviderFailure("whatsapp_phone_webhook_override_conflict")
    if routing.get("whatsapp_business_account") == callback_url:
        return {"success": True}
    result = request(
        account, "POST", account["configuration"]["wabaId"] + "/subscribed_apps",
        {"override_callback_uri": callback_url, "verify_token": verify_token},
    )
    if result.get("success") is not True:
        raise ProviderFailure("subscription_not_confirmed")
    try:
        routing = whatsapp_webhook_configuration(account)
    except ProviderFailure:
        raise ProviderFailure("whatsapp_webhook_route_unavailable", uncertain=True) from None
    if (
        routing.get("whatsapp_business_account") != callback_url
        or routing.get("phone_number") not in {None, "", callback_url}
    ):
        raise ProviderFailure("whatsapp_webhook_route_not_confirmed", uncertain=True)
    return result


def subscribe(account):
    config = account["configuration"]
    channel = account["channel"]
    if channel == "tiktok":
        return tiktok_subscribe(account)
    if channel == "whatsapp":
        result = request(account, "POST", config["wabaId"] + "/subscribed_apps", {})
    else:
        asset = config.get("accountId") if channel == "instagram" else config["pageId"]
        fields = (
            "comments,messages,messaging_postbacks,messaging_seen"
            if channel == "instagram"
            else "feed"
            if channel == "facebook"
            else "messages,messaging_postbacks,message_deliveries,message_reads"
        )
        if channel in {"facebook", "messenger"} and config.get("sharedPageSubscription"):
            fields = "feed,messages,messaging_postbacks,message_deliveries,message_reads"
        result = request(
            account, "POST", asset + "/subscribed_apps", {"subscribed_fields": fields}
        )
    if result.get("success") is not True:
        raise ProviderFailure("subscription_not_confirmed")
    return result


def tiktok_discover(account):
    config = account["configuration"]
    info = request(
        account,
        "POST",
        "tt_user/token_info/get/",
        {"app_id": config["appId"], "access_token": account["secrets"]["accessToken"]},
    )
    if str(info.get("data", {}).get("app_id", "")) != config["appId"]:
        raise ProviderFailure("provider_app_mismatch")
    business = request(
        account,
        "GET",
        "business/get/",
        params={
            "business_id": config["accountId"],
            "fields": json.dumps(["display_name"]),
        },
    )
    # This endpoint actually exercises Business Messaging access, even if empty.
    request(
        account,
        "GET",
        "business/message/conversation/list/",
        params={
            "business_id": config["accountId"],
            "conversation_type": "SINGLE",
            "limit": 1,
            "cursor": 0,
        },
    )
    return {
        "asset": {
            "id": config["accountId"],
            "name": business.get("data", {}).get("display_name", ""),
        },
        "supportedMessages": True,
        "supportedComments": True,
        "conversationReadConfirmed": True,
        "grantedScopes": info.get("data", {}).get("scope", ""),
    }


def tiktok_subscribe(account):
    config = account["configuration"]
    result = request(
        account,
        "POST",
        "business/webhook/update/",
        {
            "app_id": config["appId"],
            "secret": account["secrets"]["appSecret"],
            "event_type": "DIRECT_MESSAGE",
            "callback_url": config["callbackUrl"],
        },
    )
    request(
        account,
        "POST",
        "business/webhook/update/",
        {
            "app_id": config["appId"],
            "secret": account["secrets"]["appSecret"],
            "event_type": "COMMENT",
            "callback_url": config["callbackUrl"],
        },
    )
    return result


def send(account, payload, media=None, before_send=None):
    if payload.get("origin") == "broadcast":
        if before_send is None:
            raise ProviderFailure("broadcast_frontier_required")
        from app.institutional.broadcast_templates import send as send_broadcast

        return send_broadcast(account, payload, before_send=before_send)
    if media:
        return send_media(account, payload, media, before_send)
    if (payload.get("origin") == "bot" or "controlEpoch" in payload) and before_send:
        before_send()
    channel = account["channel"]
    config = account["configuration"]
    text = payload["body"]
    if channel == "tiktok":
        if payload["kind"] == "comment":
            result = request(
                account,
                "POST",
                "business/comment/reply/create/",
                {
                    "business_id": config["accountId"],
                    "video_id": payload["videoId"],
                    "comment_id": payload["target"],
                    "text": text,
                },
            )
            external = result.get("data", {}).get("comment_id")
        else:
            result = request(
                account,
                "POST",
                "business/message/send/",
                {
                    "business_id": config["accountId"],
                    "recipient_type": "CONVERSATION",
                    "recipient": payload["target"],
                    "message_type": "TEXT",
                    "text": {"body": text},
                },
            )
            external = result.get("data", {}).get("message", {}).get("message_id")
    elif payload["kind"] == "comment":
        path = payload["target"] + (
            "/replies" if channel == "instagram" else "/comments"
        )
        result = request(account, "POST", path, {"message": text})
        external = result.get("id")
    elif channel == "whatsapp":
        result = request(
            account,
            "POST",
            config["phoneNumberId"] + "/messages",
            {
                "messaging_product": "whatsapp",
                **whatsapp_recipient(payload["target"]),
                "type": "text",
                "text": {"body": text},
            },
        )
        external = (result.get("messages") or [{}])[0].get("id")
    elif channel in ("messenger", "instagram"):
        asset = config.get("accountId") if channel == "instagram" else config["pageId"]
        recipient = (
            {"comment_id": payload["target"]}
            if payload["kind"] == "private_reply"
            else {"id": payload["target"]}
        )
        body = {"recipient": recipient, "message": {"text": text}}
        if channel == "messenger":
            body["messaging_type"] = "RESPONSE"
        result = request(account, "POST", asset + "/messages", body)
        external = result.get("message_id")
    else:
        raise ProviderFailure("channel_messages_unavailable")
    if not external:
        raise ProviderFailure("provider_acceptance_not_confirmed", uncertain=True)
    return str(external)


def send_media(account, payload, media, before_send):
    if media["mime"] == "image/webp" and account["channel"] != "whatsapp":
        raise ProviderFailure("channel_sticker_not_supported")
    if account["channel"] == "tiktok":
        return send_tiktok_image(account, payload, media, before_send)
    variant = None
    try:
        if (
            account["channel"] in ("messenger", "instagram")
            and media["kind"] == "audio"
        ):
            from fastapi import HTTPException

            from app.modules.inbox.infrastructure.media_files import audio_for_meta

            try:
                variant = audio_for_meta(media["path"])
            except HTTPException as error:
                raise ProviderFailure(error.detail) from None
            media = {
                **media,
                "path": variant,
                "mime": "audio/mp4",
                "name": "attachment.m4a",
            }
        return send_meta_media(account, payload, media, before_send)
    finally:
        if variant:
            variant.unlink(missing_ok=True)


def send_meta_media(account, payload, media, before_send):
    channel, config = account["channel"], account["configuration"]
    if channel not in ("whatsapp", "messenger", "instagram"):
        raise ProviderFailure("channel_media_not_supported")
    if (
        channel == "instagram"
        and config.get("instagramLogin") == "instagram"
        and payload.get("origin") == "campaign"
    ):
        if not media.get("public_url"):
            raise ProviderFailure("campaign_public_HTTPS_media_origin_required")
        before_send()
        result = request(
            account,
            "POST",
            config["accountId"] + "/messages",
            {
                "recipient": {"id": payload["target"]},
                "message": {
                    "attachment": {
                        "type": "file"
                        if media["kind"] == "document"
                        else media["kind"],
                        "payload": {"url": media["public_url"]},
                    }
                },
                "messaging_type": "RESPONSE",
            },
        )
        external = result.get("message_id")
        if not external:
            raise ProviderFailure("provider_acceptance_not_confirmed", uncertain=True)
        return str(external)
    with media["path"].open("rb") as handle:
        if channel == "whatsapp":
            kind = "sticker" if media["mime"] == "image/webp" else media["kind"]
            mime = (
                "audio/ogg; codecs=opus" if media["mime"] == "audio/ogg"
                else media["mime"]
            )
            uploaded = request(
                account,
                "POST",
                config["phoneNumberId"] + "/media",
                files={
                    "messaging_product": (None, "whatsapp"),
                    "file": (media["name"], handle, mime),
                },
            )
            identifier = uploaded.get("id")
            if not identifier:
                raise ProviderFailure(
                    "provider_media_upload_not_confirmed", uncertain=True
                )
            part = {"id": str(identifier)}
            if kind == "document":
                part["filename"] = media["name"]
            if kind == "audio" and media["name"] == "nota-de-voz.ogg":
                part["voice"] = True
            if payload["body"] and payload["body"] != "[Adjunto]" and kind in (
                "image", "document", "video"
            ):
                part["caption"] = payload["body"]
            before_send()
            result = request(
                account,
                "POST",
                config["phoneNumberId"] + "/messages",
                {
                    "messaging_product": "whatsapp",
                    **whatsapp_recipient(payload["target"]),
                    "type": kind,
                    kind: part,
                },
            )
            external = (result.get("messages") or [{}])[0].get("id")
        else:
            if channel == "instagram" and (
                config.get("instagramLogin") != "facebook" or not config.get("pageId")
            ):
                raise ProviderFailure("instagram_page_media_required")
            before_send()
            result = request(
                account,
                "POST",
                config["pageId"] + "/messages",
                files={
                    "recipient": (None, json.dumps({"id": payload["target"]})),
                    **(
                        {"messaging_type": (None, "RESPONSE")}
                        if channel == "messenger"
                        else {"platform": (None, "instagram")}
                    ),
                    "message": (
                        None,
                        json.dumps(
                            {
                                "attachment": {
                                    "type": "file"
                                    if media["kind"] == "document"
                                    else media["kind"],
                                    **({"payload": {}} if channel == "messenger" else {}),
                                }
                            }
                        ),
                    ),
                    "filedata": (
                        "attachment." + media["name"].rsplit(".", 1)[-1],
                        handle,
                        media["mime"],
                    ),
                },
            )
            external = result.get("message_id")
    if not external:
        raise ProviderFailure("provider_acceptance_not_confirmed", uncertain=True)
    return str(external)


def send_tiktok_image(account, payload, media, before_send):
    if (
        media["kind"] != "image"
        or media["path"].stat().st_size > 3_000_000
        or payload["body"]
    ):
        raise ProviderFailure("tiktok_image_limit")
    business = account["configuration"]["accountId"]
    conversation_type = None
    budget_exhausted = False
    for kind in ("STRANGER", "SINGLE"):
        cursor = 0
        seen = {cursor}
        for page_number in range(5):
            page = request(
                account,
                "GET",
                "business/message/conversation/list/",
                params={
                    "business_id": business,
                    "conversation_type": kind,
                    "limit": 100,
                    "cursor": cursor,
                },
            )
            data = page.get("data")
            if not isinstance(data, dict) or not isinstance(
                data.get("conversations"), list
            ):
                raise ProviderFailure("provider_response_invalid")
            if any(
                str(item.get("conversation_id", "")) == payload["target"]
                for item in data["conversations"]
                if isinstance(item, dict)
            ):
                conversation_type = kind
                break
            if data.get("has_more") is False:
                break
            next_cursor = data.get("cursor")
            if (
                data.get("has_more") is not True
                or type(next_cursor) is not int
                or next_cursor < 0
                or next_cursor in seen
            ):
                raise ProviderFailure("provider_response_invalid")
            if page_number == 4:
                budget_exhausted = True
                break
            seen.add(next_cursor)
            cursor = next_cursor
        if conversation_type is not None:
            break
    if conversation_type is None:
        raise ProviderFailure(
            "tiktok_conversation_lookup_budget"
            if budget_exhausted
            else "tiktok_conversation_type_unconfirmed"
        )
    capability = request(
        account,
        "GET",
        "business/message/capabilities/get/",
        params={
            "business_id": business,
            "conversation_id": payload["target"],
            "conversation_type": conversation_type,
            "capability_types": '["IMAGE_SEND"]',
        },
    )
    if not any(
        item.get("capability_type") == "IMAGE_SEND"
        and item.get("capability_result") is True
        for item in capability.get("data", {}).get("capability_infos", [])
        if isinstance(item, dict)
    ):
        raise ProviderFailure("tiktok_image_permission_unavailable")
    with media["path"].open("rb") as handle:
        uploaded = request(
            account,
            "POST",
            "business/message/media/upload/",
            files={
                "business_id": (None, business),
                "media_type": (None, "IMAGE"),
                "file": (
                    "attachment." + media["name"].rsplit(".", 1)[-1],
                    handle,
                    media["mime"],
                ),
            },
        )
    media_id = uploaded.get("data", {}).get("media_id")
    if not media_id:
        raise ProviderFailure("provider_media_upload_not_confirmed", uncertain=True)
    before_send()
    result = request(
        account,
        "POST",
        "business/message/send/",
        {
            "business_id": business,
            "recipient_type": "CONVERSATION",
            "recipient": payload["target"],
            "message_type": "IMAGE",
            "image": {"media_id": str(media_id)},
        },
    )
    external = result.get("data", {}).get("message", {}).get("message_id")
    if not external:
        raise ProviderFailure("provider_acceptance_not_confirmed", uncertain=True)
    return str(external)
