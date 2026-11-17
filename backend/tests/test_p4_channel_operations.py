import hmac
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import httpx2
import pytest
from cryptography.exceptions import InvalidTag
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.institutional.channel_events import delivery, normalize
from app.institutional import channel_events, channel_ingress, channel_operations
from app.institutional import whatsapp_gemini, channel_workspace
from app.institutional.comment_effects import call_provider as comment_provider
from app.institutional.auth import api_request_limit
from app.institutional.channel_ingress import signature_valid
from app.institutional.channel_oauth import OAuth, authorization_url, exchange, install
from app.institutional.channels import (
    FACEBOOK_LOGIN_CONFIGURATION,
    contract,
    validate_field,
)
from app.institutional.channel_operations import OperationalChannels, capabilities
from app.institutional.channel_operations import compatible_app_secret, reuse_app_secret
from app.institutional.models import SecretEdit
from app.institutional.channel_provider import ProviderAction, provider_account
from app.institutional.channel_secrets import binding
from app.institutional.channel_tokens import health
from app.institutional.channel_workspace import followup_risk, social_avatar_url
from app.institutional.channel_workers import Workers
from app.institutional.crypto import seal, unseal
from app.modules.channels import providers


@pytest.mark.parametrize("path", [
    "/api/institution/workspace/inbox",
    "/api/institution/workspace/conversations/{conversation_id}/messages",
])
def test_inbox_reads_leave_room_for_user_actions_in_same_limit(path):
    assert api_request_limit(120, {"method": "GET", "resource": path}) == 96
    assert api_request_limit(10, {"method": "GET", "resource": path}) == 8
    assert api_request_limit(120, {"method": "POST", "resource": path}) == 120


def test_public_sql_deployment_has_wakeable_inbound_and_outbound_queues():
    production = Workers(SimpleNamespace(public_origin="https://crm.example"))
    local = Workers(SimpleNamespace(public_origin=None))

    assert production.fast_queues
    assert not local.fast_queues


@pytest.mark.parametrize("channel", ["messenger", "instagram"])
def test_gemini_supports_social_channels_on_production_with_whatsapp_pin(monkeypatch, channel):
    settings = SimpleNamespace(
        ticket={"version": "cbn-institutional-operations-p11-v1"},
        postgres_deployment=True,
    )
    monkeypatch.setenv("RINOVA_GEMINI_WHATSAPP_INTEGRATION", str(uuid4()))
    assert whatsapp_gemini.available(settings, str(uuid4()), channel)
    settings.postgres_deployment = False
    assert not whatsapp_gemini.available(settings, str(uuid4()), channel)


@pytest.mark.parametrize(("channel", "expected"), [
    ("messenger", "facebook"), ("instagram", "instagram"), (None, "whatsapp"),
])
def test_gemini_resolves_the_agent_for_the_actual_channel(monkeypatch, channel, expected):
    def resolve(_c, conversation, actual_channel):
        assert actual_channel == expected
        return {
            "agent_id": "test-agent", "binding": "test-binding",
            "configuration": {
                "provider": "gemini", "allow_reply": True,
                "capabilities": ["conversation.reply"], "primary_model": "gemini-test",
                "input_usd_per_million": 0.25, "output_usd_per_million": 1.5,
            },
        }
    monkeypatch.setattr(whatsapp_gemini, "resolve_conversation", resolve)
    monkeypatch.setattr(whatsapp_gemini, "setting", lambda *_: {"document": {"enabled": True}})
    monkeypatch.setattr(whatsapp_gemini, "one", lambda *_: {"SecretId": str(uuid4())})
    settings = SimpleNamespace(ticket={"context": [[1, str(uuid4())]]})
    data = {"conversation": str(uuid4()), **({"channel": channel} if channel else {})}
    assert whatsapp_gemini.model_config(None, settings, data)[2]["model"] == "gemini-test"


def test_instagram_preview_includes_carousel_images_and_video(monkeypatch):
    def request(_adapter, method, target, params):
        assert (method, target) == ("GET", "123")
        assert "children" in params["fields"] and "media_url" in params["fields"]
        return {
            "id": "123", "caption": "Oferta institucional",
            "permalink": "https://www.instagram.com/p/example/",
            "children": {"data": [
                {"media_type": "IMAGE", "media_url": "https://scontent.cdninstagram.com/image.jpg"},
                {"media_type": "VIDEO", "media_url": "https://video.cdninstagram.com/clip.mp4",
                 "thumbnail_url": "https://scontent.cdninstagram.com/poster.jpg"},
            ]},
        }
    monkeypatch.setattr(providers, "request", request)
    result = comment_provider(
        {"channel": "instagram"}, "preview",
        {"ExternalId": "456", "Payload": '{"provider":{"media":{"id":"123"}}}'},
    )["preview"]
    assert result["caption"] == "Oferta institucional"
    assert [item["type"] for item in result["media"]] == ["image", "video"]
    assert result["media"][1]["poster"].endswith("/poster.jpg")


@pytest.mark.parametrize(("hours", "expected"), [(1, (10, "low")), (72, (50, "medium")), (168, (75, "high"))])
def test_followup_risk_uses_the_same_confirmed_activity(hours, expected):
    now = datetime(2026, 11, 17, 15, tzinfo=timezone.utc)
    incoming, reply = now - timedelta(hours=hours + 1), now - timedelta(hours=hours)
    risk = {"status": "unknown", "score": None, "fresh": False}
    evidence = {"IncomingAt": incoming, "ReplyAt": reply, "AsOfUtc": now}
    scored = followup_risk(evidence, risk)
    assert (scored["score"], scored["level"]) == expected
    assert scored["source"] == "channel_activity"
    evidence["ReplyAt"] = None
    assert followup_risk(evidence, risk)["status"] == "unknown"


def test_whatsapp_oauth_discovers_numbers_from_configured_waba(monkeypatch):
    def request(method, url, *, params=None, headers=None):
        assert method == "GET"
        if url.endswith("/oauth/access_token"):
            return {"access_token": "synthetic-access"}
        assert url == "https://graph.facebook.com/v25.0/890/phone_numbers"
        assert headers == {"Authorization": "Bearer synthetic-access"}
        assert params["fields"] == "id,display_phone_number,verified_name"
        return {"data": [{"id": "123", "display_phone_number": "+15555550100"}]}

    monkeypatch.setattr("app.institutional.channel_oauth.http_json", request)
    result = exchange(
        {"IssuerProfile": "meta_whatsapp", "ApiVersion": "v25.0", "ClientId": "999",
         "Channel": "whatsapp", "ParentExternalId": "890"},
        "synthetic-secret", "code", "https://crm.example/hooks/oauth/fixture", None,
    )
    assert [(v["kind"], v["parent"], v["id"]) for v in result["assets"]] == [
        ("whatsapp_phone", "890", "123"),
    ]


def test_whatsapp_oauth_lists_business_numbers_without_entering_a_waba(monkeypatch):
    def request(method, url, *, params=None, headers=None):
        assert method == "GET"
        if url.endswith("/oauth/access_token"):
            return {"access_token": "synthetic-access"}
        assert url == "https://graph.facebook.com/v25.0/me/businesses"
        assert headers == {"Authorization": "Bearer synthetic-access"}
        assert "owned_whatsapp_business_accounts" in params["fields"]
        assert "client_whatsapp_business_accounts" in params["fields"]
        waba = {"id": "890", "name": "CBN", "phone_numbers": {
            "data": [{"id": "123", "display_phone_number": "+15555550100"}],
        }}
        return {"data": [{"id": "889", "owned_whatsapp_business_accounts": {"data": [waba]}}]}

    monkeypatch.setattr("app.institutional.channel_oauth.http_json", request)
    result = exchange(
        {"IssuerProfile": "meta_whatsapp", "ApiVersion": "v25.0", "ClientId": "999",
         "Channel": "whatsapp", "ParentExternalId": None},
        "synthetic-secret", "code", "https://crm.example/hooks/oauth/fixture", None,
    )
    assert [(v["parent"], v["id"], v["name"]) for v in result["assets"]] == [
        ("890", "123", "CBN · +15555550100"),
    ]


def test_whatsapp_oauth_uses_configuration_selected_by_meta():
    url = authorization_url(
        {"IssuerProfile": "meta_whatsapp", "ApiVersion": "v25.0", "ClientId": "999"},
        "state", "https://crm.example/hooks/oauth/fixture",
        ["whatsapp_business_management"], None, configuration_id="234",
    )
    query = parse_qs(urlsplit(url).query)
    assert query["config_id"] == ["234"]
    assert "scope" not in query


@pytest.mark.parametrize(("message", "expected"), [
    ("Error validating client secret.", "meta_app_secret_rejected"),
    ("Error validating verification code.", "oauth_code_exchange_rejected"),
])
def test_meta_oauth_classifies_exchange_rejection_without_exposing_details(
    monkeypatch, message, expected
):
    client = httpx2.Client

    def reject(request):
        assert request.url.path == "/v27.0/oauth/access_token"
        return httpx2.Response(400, json={"error": {"code": 1, "message": message}})

    monkeypatch.setattr(
        "app.institutional.channel_oauth.httpx.Client",
        lambda **kwargs: client(transport=httpx2.MockTransport(reject), **kwargs),
    )
    with pytest.raises(providers.ProviderFailure) as failure:
        exchange(
            {"IssuerProfile": "meta_whatsapp", "ApiVersion": "v27.0", "ClientId": "999"},
            "synthetic-secret", "code", "https://crm.example/hooks/oauth/fixture", None,
        )
    assert failure.value.code == expected
    assert not failure.value.uncertain


def test_new_contact_routing_survives_unrelated_crm_changes(monkeypatch):
    selected = SimpleNamespace(key="new", active=True, label="Nuevo")
    monkeypatch.setattr(
        channel_events, "read_configuration",
        lambda *_args, **_kwargs: (SimpleNamespace(stages=[selected]), None),
    )
    item = {"InitialStageKey": "new", "InitialStageConfigHash": b"prior approval"}
    assert channel_events.stage(None, item) == "Nuevo"
    selected.active = False
    with pytest.raises(HTTPException) as error:
        channel_events.stage(None, item)
    assert error.value.detail == "initial_stage_review_required"


def test_whatsapp_business_scoped_sender_without_phone():
    user_id = "CO.13491208655302741918"
    message = {"id": "wamid.example", "from_user_id": user_id, "type": "text",
               "text": {"body": "Hola"}}
    payload = {"entry": [{"id": "777", "changes": [{"field": "messages", "value": {
        "messaging_product": "whatsapp",
        "metadata": {"phone_number_id": "1234"},
        "contacts": [{"user_id": user_id, "profile": {"name": "Contacto de prueba"}}],
        "messages": [message],
    }}]}]}
    current, = normalize("meta", payload)
    old, = normalize("meta", payload, whatsapp_identifiers=False)
    assert (current["author"], current["contact_name"], current["normalizer_version"]) == (
        user_id, "Contacto de prueba", 3,
    )
    assert old["author"] == "" and old["normalizer_version"] == 1
    assert providers.whatsapp_recipient(current["author"]) == {"recipient": user_id}
    message["from"] = "573000000000"
    current, = normalize("meta", payload)
    assert current["author"] == "573000000000"
    assert current["whatsapp_user_id"] == user_id
    assert providers.whatsapp_recipient(current["author"]) == {"to": "573000000000"}


def test_social_avatars_only_accept_https_meta_media_hosts():
    official = "https://scontent.xx.fbcdn.net/profile.jpg"
    assert social_avatar_url(official) == official
    assert social_avatar_url("https://notfbcdn.net/profile.jpg") == ""
    assert social_avatar_url("https://scontent.xx.fbcdn.net@other.test/profile.jpg") == ""
    assert social_avatar_url("http://scontent.xx.fbcdn.net/profile.jpg") == ""


@pytest.mark.parametrize("participant_id", ["123", "999"])
def test_messenger_profile_falls_back_only_to_the_matching_conversation_participant(monkeypatch, participant_id):
    profile = SimpleNamespace(ticket={"context": [[1, str(uuid4())]]})
    service = SimpleNamespace(profile=profile, transaction=lambda: nullcontext(None))
    monkeypatch.setattr(channel_workspace.db, "one", lambda *_: {
        "ExternalId": "123", "IntegrationId": str(uuid4()),
    })
    monkeypatch.setattr(channel_workspace, "account", lambda *_: {
        "Channel": "messenger", "ExternalAccountId": "456",
    })
    monkeypatch.setattr(channel_workspace, "provider_account", lambda *_: ({}, None))
    def request(_adapter, _method, path, params):
        if path == "123":
            raise providers.ProviderFailure("provider_permission_or_request_rejected")
        assert path == "456/conversations"
        assert params["user_id"] == "123"
        return {"data": [{"participants": {"data": [
            {"id": participant_id, "name": "Nombre autorizado"},
        ]}}]}
    monkeypatch.setattr(providers, "request", request)
    result = channel_workspace.Workspace.social_profile(service, str(uuid4()))["profile"]
    assert (result["name"] if result else None) == (
        "Nombre autorizado" if participant_id == "123" else None
    )


@pytest.mark.parametrize("raw", ['{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'])
def test_strict_provider_json_rejects_ambiguous_input(raw):
    from app.institutional.channel_ingress import strict_json

    with pytest.raises((ValueError, HTTPException)):
        strict_json(raw)


def test_meta_verification_logs_a_rejection_without_logging_the_token(monkeypatch, caplog):
    ingress = channel_ingress.Ingress(SimpleNamespace())
    monkeypatch.setattr(
        channel_ingress, "transaction", lambda *_args, **_kwargs: nullcontext(object())
    )
    monkeypatch.setattr(
        channel_ingress,
        "endpoint",
        lambda *_args: {"EndpointId": "endpoint", "Provider": "meta"},
    )
    monkeypatch.setattr(channel_ingress, "get", lambda *_args: ("correct-private", {}))
    with caplog.at_level("INFO", logger="uvicorn.error"), pytest.raises(HTTPException) as error:
        ingress.challenge("endpoint", "subscribe", "incorrecto-privadó", "123")
    assert error.value.status_code == 403
    assert "outcome=token_mismatch" in caplog.text
    assert "correct-private" not in caplog.text
    assert "incorrecto-privadó" not in caplog.text


def test_webhook_creation_issues_the_canonical_url_and_token_together(monkeypatch):
    service = channel_operations.Operations(SimpleNamespace())
    endpoint = {
        "id": "page-endpoint",
        "callback_url": "https://crm.example.test/hooks/channels/ep_example",
        "row_version": "0000000000000001",
    }
    state = {}

    def get_endpoint(*_args, create=False):
        if create:
            state["endpoint"] = endpoint
            return endpoint, {"verify_token": "private-test-token"}
        return state.get("endpoint"), {}

    def record(*args):
        state["receipt"] = args[-1]

    monkeypatch.setattr(
        channel_operations, "transaction", lambda *_args, **_kwargs: nullcontext(object())
    )
    monkeypatch.setattr(
        channel_operations, "authorize", lambda *_args, **_kwargs: {"UserId": "owner"}
    )
    monkeypatch.setattr(channel_operations, "account", lambda *_args: {})
    monkeypatch.setattr(channel_operations, "endpoint", get_endpoint)
    monkeypatch.setattr(channel_operations, "replay", lambda *_args: ("digest", state.get("receipt")))
    monkeypatch.setattr(channel_operations, "record_operation", record)
    body = channel_operations.EndpointIssue(operation_id=str(uuid4()))
    assert service.webhook({}, "messenger", body, rotate=True) == {
        "webhook": endpoint,
        "verify_token": "private-test-token",
    }
    assert service.webhook({}, "messenger", body, rotate=True) == {
        "webhook": endpoint,
        "secrets_already_issued": True,
    }


def test_provider_payload_is_bounded_and_identity_is_never_truncated_to_valid():
    from app.institutional.channel_events import bounded_provider, event
    from app.institutional.channel_text import sql_text

    assert len(sql_text("😀" * 4000, 4000).encode("utf-16-le")) == 8000
    value = event("facebook", "x" * 201, "comment", "id", "a", "😀" * 4001, {})
    assert not value["valid_source_ids"]
    assert len(value["text"].encode("utf-16-le")) == 8000
    assert bounded_provider({"_crm": {"state": "connected"}, "text": "ok"}) == {
        "text": "ok"
    }


def test_verify_is_not_a_meta_signature_secret():
    raw = b'{"entry":[]}'
    headers = {
        "x-hub-signature-256": "sha256="
        + hmac.digest(b"application-secret", raw, "sha256").hex()
    }
    assert signature_valid("meta", "application-secret", headers, raw)
    assert not signature_valid("meta", "generated-verify-token", headers, raw)
    assert not signature_valid("meta", "application-secret", headers, raw + b" ")


@pytest.mark.parametrize("channel", ["facebook", "messenger"])
def test_page_oauth_does_not_request_instagram_fields(monkeypatch, channel):
    def request(method, url, **options):
        if url.endswith("oauth/access_token"):
            return {"access_token": "user-test-key"}
        assert url.endswith("me/accounts")
        assert options["params"]["fields"] == "id,name,access_token"
        return {"data": [{"id": "12345", "name": "Página de prueba", "access_token": "page-test-key"}]}

    monkeypatch.setattr("app.institutional.channel_oauth.http_json", request)
    result = exchange(
        {"IssuerProfile": "facebook_login", "ApiVersion": "v26.0", "ClientId": "123",
         "Channel": channel}, "secret", "code", "https://example.invalid/return", None,
    )
    assert [(item["kind"], item["id"]) for item in result["assets"]] == [("facebook_page", "12345")]


@pytest.mark.parametrize("channel", ["facebook", "messenger"])
def test_page_subscription_preserves_comments_and_message_fields(monkeypatch, channel):
    def request(account, method, path, body):
        assert method == "POST" and path == "123/subscribed_apps"
        assert set(body["subscribed_fields"].split(",")) == {
            "feed", "messages", "messaging_postbacks", "message_deliveries", "message_reads",
        }
        return {"success": True}

    monkeypatch.setattr(providers, "request", request)
    assert providers.subscribe({
        "channel": channel,
        "configuration": {"pageId": "123", "sharedPageSubscription": True},
    })["success"]


@pytest.mark.parametrize("phone_override", [None, "https://other.example/webhook"])
def test_whatsapp_subscription_checks_precedence_and_verifies_the_waba_override(
    monkeypatch, phone_override,
):
    callback = "https://crm.example/hooks/channels/ep_fixture"
    account = {"channel": "whatsapp", "configuration": {
        "phoneNumberId": "456", "wabaId": "123",
    }}
    routing = {"application": "https://scentra.example/webhook"}
    if phone_override:
        routing["phone_number"] = phone_override
    calls = []

    def request(_account, method, path, body=None, *, params=None):
        calls.append((method, path))
        if method == "GET":
            assert path == "456" and params == {"fields": "webhook_configuration"}
            return {"id": "456", "webhook_configuration": routing.copy()}
        assert path == "123/subscribed_apps"
        assert body == {"override_callback_uri": callback, "verify_token": "synthetic-verify"}
        routing["whatsapp_business_account"] = callback
        return {"success": True}

    monkeypatch.setattr(providers, "request", request)
    if phone_override:
        with pytest.raises(providers.ProviderFailure, match="whatsapp_phone_webhook_override_conflict"):
            providers.subscribe_whatsapp_callback(account, callback, "synthetic-verify")
        assert calls == [("GET", "456")]
    else:
        assert providers.subscribe_whatsapp_callback(account, callback, "synthetic-verify")["success"]
        assert calls == [("GET", "456"), ("POST", "123/subscribed_apps"), ("GET", "456")]
        assert providers.subscribe_whatsapp_callback(account, callback, "synthetic-verify")["success"]
        assert calls[-1:] == [("GET", "456")] and len(calls) == 4
        assert routing["application"] == "https://scentra.example/webhook"


@pytest.mark.parametrize(
    ("app_id", "valid"), [("12345", True), ("12345", False), ("67890", True)]
)
def test_meta_debug_token_authenticates_with_app_token(monkeypatch, app_id, valid):
    adapter = {
        "channel": "whatsapp",
        "configuration": {"apiVersion": "v26.0"},
        "secrets": {"accessToken": "system-user-token", "appSecret": "app-secret"},
    }
    item = {
        "Provider": "meta",
        "IssuerProfile": "meta_whatsapp",
        "ClientId": "12345",
    }

    def respond(request):
        assert request.method == "GET"
        assert request.url.host == "graph.facebook.com"
        assert request.url.path == "/v26.0/debug_token"
        assert request.headers["Authorization"] == "Bearer 12345|app-secret"
        assert dict(request.url.params) == {"input_token": "system-user-token"}
        return httpx2.Response(
            200, json={"data": {"app_id": app_id, "is_valid": valid}}
        )

    client = httpx2.Client
    monkeypatch.setattr(
        httpx2,
        "Client",
        lambda **kwargs: client(transport=httpx2.MockTransport(respond), **kwargs),
    )
    if valid and app_id == item["ClientId"]:
        assert health(adapter, item)["applicationValidated"] is True
        assert adapter["secrets"]["accessToken"] == "system-user-token"
    else:
        with pytest.raises(
            providers.ProviderFailure, match="token_application_mismatch_or_invalid"
        ):
            health(adapter, item)


@pytest.mark.parametrize(
    "header", ["t=100,s=bad", "t=100,s=bad,t=100", "t=100,s=bad,x=1", "t=١٠٠,s=bad", ""]
)
def test_tiktok_malformed_timestamp_signature_is_rejected(header):
    assert not signature_valid(
        "tiktok", "secret", {"tiktok-signature": header}, b"{}", now=100
    )


def test_tiktok_signature_window_and_raw_binding():
    raw, secret, timestamp = b'{"event":"comment.update"}', "owned-secret", "1000"
    signed = hmac.digest(
        secret.encode(), timestamp.encode() + b"." + raw, "sha256"
    ).hex()
    headers = {"tiktok-signature": "t=" + timestamp + ",s=" + signed}
    assert signature_valid("tiktok", secret, headers, raw, now=1100)
    assert not signature_valid("tiktok", secret, headers, raw, now=1400)
    assert not signature_valid("tiktok", secret, headers, b"{}", now=1100)


def test_vault_aad_rejects_another_owner_or_version():
    settings = SimpleNamespace(ticket={"context": [[1, str(uuid4())]]})
    owner, identity = str(uuid4()), str(uuid4())
    aad = binding(settings, "application", owner, "meta_app_secret", 1, identity)
    key = b"x" * 32
    nonce, cipher = seal(key, aad, "owned-credential")
    assert unseal(key, aad, nonce, cipher) == "owned-credential"
    for changed in [
        dict(aad, owner=str(uuid4())),
        dict(aad, version=2),
        dict(aad, institution=str(uuid4())),
    ]:
        with pytest.raises(InvalidTag):
            unseal(key, changed, nonce, cipher)


def test_secret_kind_cannot_cross_owner_type():
    settings = SimpleNamespace(ticket={"context": [[1, str(uuid4())]]})
    with pytest.raises(ValueError, match="credential_owner_kind"):
        binding(
            settings,
            "application",
            str(uuid4()),
            "meta_permanent_access",
            1,
            str(uuid4()),
        )


@pytest.mark.parametrize(("source_issuer", "target_issuer", "source_client", "expected"), [
    ("meta_whatsapp", "facebook_login", "123", True),
    ("facebook_login", "meta_whatsapp", "123", True),
    ("instagram_login", "facebook_login", "123", False),
    ("meta_whatsapp", "facebook_login", "999", False),
])
def test_saved_app_secrets_require_matching_identity_and_login_family(
    source_issuer, target_issuer, source_client, expected
):
    source = {"IssuerProfile": source_issuer, "Provider": "meta", "ClientId": source_client}
    target = {"IssuerProfile": target_issuer, "Provider": "meta", "ClientId": "123"}
    assert compatible_app_secret(source, target) is expected
    assert not compatible_app_secret({**source, "Provider": "tiktok"}, target)


def test_saved_app_secret_reference_cannot_be_combined_with_raw_value():
    from pydantic import ValidationError
    values = {
        "operation_id": str(uuid4()), "scope": "channel", "owner": "application:" + str(uuid4()),
        "kind": "app_secret", "source_secret_id": str(uuid4()),
    }
    assert SecretEdit(**values).source_secret_id == values["source_secret_id"]
    for override in [
        {"value": "synthetic-secret"},
        {"kind": "access_token"},
        {"scope": "provider"},
        {"source_secret_id": "not-an-id"},
    ]:
        with pytest.raises(ValidationError):
            SecretEdit(**{**values, **override})


def test_saved_app_secret_is_reencrypted_for_the_destination(monkeypatch):
    source_id, source_app, target_app = [str(uuid4()) for _ in range(3)]
    values = iter([
        {"Provider": "meta", "ClientId": "123", "IssuerProfile": "facebook_login", "State": "draft"},
        {"Provider": "meta", "ClientId": "123", "IssuerProfile": "meta_whatsapp",
         "ApplicationId": source_app, "Kind": "meta_app_secret"},
    ])
    monkeypatch.setattr(channel_operations, "one", lambda *_args: next(values))
    def secret(*_args, **kwargs):
        if kwargs.get("identity") == source_id:
            return "synthetic-secret", {"ExpiresAt": None}
        raise HTTPException(409, "credential_required")

    monkeypatch.setattr(channel_operations, "get", secret)
    captured = []
    monkeypatch.setattr(channel_operations, "put", lambda *args, **kwargs: (
        captured.append((args, kwargs)) or {"configured": True, "version": 1}
    ))
    settings = SimpleNamespace(ticket={"context": [[1, str(uuid4())]]})
    assert reuse_app_secret(None, settings, source_id, target_app)["configured"]
    assert captured[0][0][2:] == ("application", target_app, "facebook_app_secret", "synthetic-secret")


def test_reusing_the_same_app_secret_preserves_the_current_version(monkeypatch):
    values = iter([
        {"Provider": "meta", "ClientId": "123", "IssuerProfile": "facebook_login", "State": "draft"},
        {"Provider": "meta", "ClientId": "123", "IssuerProfile": "meta_whatsapp",
         "ApplicationId": str(uuid4()), "Kind": "meta_app_secret"},
    ])
    monkeypatch.setattr(channel_operations, "one", lambda *_args: next(values))
    monkeypatch.setattr(channel_operations, "get", lambda *_args, **_kwargs: (
        "synthetic-secret", {"ExpiresAt": None},
    ))
    monkeypatch.setattr(channel_operations, "put", lambda *_args, **_kwargs: pytest.fail("must preserve version"))
    settings = SimpleNamespace(ticket={"context": [[1, str(uuid4())]]})
    assert reuse_app_secret(None, settings, str(uuid4()), str(uuid4())) == {
        "unchanged": True, "configured": True,
    }


def test_saved_app_secret_cannot_copy_another_application(monkeypatch):
    values = iter([
        {"Provider": "meta", "ClientId": "123", "IssuerProfile": "facebook_login", "State": "draft"},
        {"Provider": "meta", "ClientId": "456", "IssuerProfile": "meta_whatsapp",
         "ApplicationId": str(uuid4()), "Kind": "meta_app_secret"},
    ])
    monkeypatch.setattr(channel_operations, "one", lambda *_args: next(values))
    monkeypatch.setattr(channel_operations, "get", lambda *_args, **_kwargs: pytest.fail("must not decrypt"))
    settings = SimpleNamespace(ticket={"context": [[1, str(uuid4())]]})
    with pytest.raises(HTTPException, match="saved_app_secret_incompatible"):
        reuse_app_secret(None, settings, str(uuid4()), str(uuid4()))


def test_comment_delete_is_normalized_and_never_promotes_provider_crm_state():
    values = normalize(
        "meta",
        {
            "object": "page",
            "entry": [
                {
                    "id": "page-one",
                    "changes": [
                        {
                            "field": "feed",
                            "value": {
                                "item": "comment",
                                "verb": "remove",
                                "comment_id": "post_comment",
                                "_crm": {"state": "connected"},
                            },
                        }
                    ],
                }
            ],
        },
    )
    assert len(values) == 1
    assert values[0]["kind"] == "comment_deleted"
    assert values[0]["route"] == "page-one"
    assert "_crm" not in values[0]


def test_whatsapp_routes_on_phone_not_waba_or_channel_name():
    value = normalize(
        "meta",
        {
            "entry": [
                {
                    "id": "waba",
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {"phone_number_id": "phone-two"},
                                "messages": [
                                    {
                                        "id": "message",
                                        "from": "student",
                                        "type": "text",
                                        "text": {"body": "Hola"},
                                        "timestamp": "1000",
                                    }
                                ],
                            },
                        }
                    ],
                }
            ]
        },
    )[0]
    assert value["route"] == "phone-two"
    assert value["author"] == "student"


@pytest.mark.parametrize(
    "previous,incoming,expected",
    [
        ("accepted", "delivered", "delivered"),
        ("delivered", "sent", "delivered"),
        ("read", "failed", "read"),
        ("uncertain", "sent", "sent"),
        ("accepted", "accepted", "accepted"),
        ("queued", "invented", "queued"),
    ],
)
def test_receipts_never_infer_delivery_or_downgrade_it(previous, incoming, expected):
    assert delivery(previous, incoming) == expected


def test_oauth_redirect_and_state_are_encoded_under_fixed_provider_host():
    item = {
        "IssuerProfile": "facebook_login",
        "ClientId": "owned-app",
        "ApiVersion": "v24.0",
    }
    value = authorization_url(
        item,
        "state&unexpected=x",
        "https://crm.example.test/hooks/oauth/id",
        ["pages_show_list"],
        None,
    )
    parsed = urlsplit(value)
    assert parsed.hostname == "www.facebook.com"
    assert parse_qs(parsed.query)["state"] == ["state&unexpected=x"]
    assert "unexpected" not in parse_qs(parsed.query)


def test_oauth_version_cannot_inject_an_endpoint():
    with pytest.raises(HTTPException):
        authorization_url(
            {
                "IssuerProfile": "facebook_login",
                "ClientId": "a",
                "ApiVersion": "v24.0/../../evil",
            },
            "s",
            "https://crm.example.test/cb",
            ["pages_show_list"],
            None,
        )


def test_business_login_uses_the_saved_configuration_instead_of_url_scopes():
    fields = [
        field for field in OperationalChannels(None)._fields(contract())
        if field["id"] == FACEBOOK_LOGIN_CONFIGURATION
    ]
    assert {field["group"] for field in fields} == {"facebook", "instagram"}
    for field in fields:
        assert field["p2_mapping"]["p2_flat_json_key"] == FACEBOOK_LOGIN_CONFIGURATION
        assert validate_field(field, " 123456789 ") == "123456789"
        with pytest.raises(ValueError):
            validate_field(field, "123&scope=other")
    url = authorization_url(
        {"IssuerProfile": "facebook_login", "ClientId": "123", "ApiVersion": "v25.0"},
        "state",
        "https://crm.example.test/hooks/oauth/id",
        ["pages_show_list"],
        None,
        configuration_id="123456789",
    )
    params = parse_qs(urlsplit(url).query)
    assert params["config_id"] == ["123456789"]
    assert params["response_type"] == ["code"]
    assert params["override_default_response_type"] == ["true"]
    assert "scope" not in params


@pytest.mark.parametrize(("failure", "return_reason"), [
    (None, None),
    ("password_confirmation_required", "confirm"),
    ("oauth_state_rejected", "invalid-attempt"),
    ("oauth_credential_changed", "configuration-changed"),
])
def test_oauth_callback_redirects_back_without_provider_credentials(monkeypatch, failure, return_reason):
    account_id, oauth_id = str(uuid4()), str(uuid4())

    def callback(_service, *_args, **_kwargs):
        if failure:
            raise HTTPException(403, failure)
        return {"integration_id": account_id, "oauth_session_id": oauth_id}

    monkeypatch.setattr(OAuth, "callback", callback)
    app = FastAPI()
    install(app, SimpleNamespace())
    with TestClient(app) as client:
        response = client.get(
            "/hooks/oauth/app",
            params={"state": "state-is-private", "code": "code-is-private"},
            follow_redirects=False,
        )
    expected = return_reason or f"{account_id}/{oauth_id}"
    assert response.status_code == 303
    assert response.headers["location"] == f"/#/channels/oauth/{expected}"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_tiktok_like_and_private_reply_are_not_invented_capabilities():
    values = capabilities(
        {
            "Channel": "tiktok",
            "RequestedStatus": "paused",
            "VerifiedStatus": "unverified",
        }
    )
    assert not values["comment_like"]
    assert not values["private_comment_reply"]
    assert not values["connected"]


def test_provider_account_cannot_turn_an_asset_id_into_a_path():
    with pytest.raises(HTTPException, match="external_account_required"):
        provider_account(
            None, None, {"ExternalAccountId": "../other/messages"}, require_access=False
        )


def test_registration_pin_is_redacted_in_model_representation():
    value = ProviderAction(
        operation_id=str(uuid4()), row_version="00" * 8, pin="123456"
    )
    assert "123456" not in repr(value)
