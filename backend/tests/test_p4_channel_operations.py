import hmac
from contextlib import nullcontext
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import httpx2
import pytest
from cryptography.exceptions import InvalidTag
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.institutional.channel_events import delivery, normalize
from app.institutional import channel_ingress, channel_operations
from app.institutional.channel_ingress import signature_valid
from app.institutional.channel_oauth import OAuth, authorization_url, exchange, install
from app.institutional.channels import (
    FACEBOOK_LOGIN_CONFIGURATION,
    contract,
    validate_field,
)
from app.institutional.channel_operations import OperationalChannels, capabilities
from app.institutional.channel_provider import ProviderAction, provider_account
from app.institutional.channel_secrets import binding
from app.institutional.channel_tokens import health
from app.institutional.channel_workspace import social_avatar_url
from app.institutional.crypto import seal, unseal
from app.modules.channels import providers


def test_social_avatars_only_accept_https_meta_media_hosts():
    official = "https://scontent.xx.fbcdn.net/profile.jpg"
    assert social_avatar_url(official) == official
    assert social_avatar_url("https://notfbcdn.net/profile.jpg") == ""
    assert social_avatar_url("https://scontent.xx.fbcdn.net@other.test/profile.jpg") == ""
    assert social_avatar_url("http://scontent.xx.fbcdn.net/profile.jpg") == ""


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
    field = next(
        field
        for field in OperationalChannels(None)._fields(contract())
        if field["id"] == FACEBOOK_LOGIN_CONFIGURATION
    )
    configuration = validate_field(field, " 123456789 ")
    with pytest.raises(ValueError):
        validate_field(field, "123&scope=other")
    url = authorization_url(
        {"IssuerProfile": "facebook_login", "ClientId": "123", "ApiVersion": "v25.0"},
        "state",
        "https://crm.example.test/hooks/oauth/id",
        ["pages_show_list"],
        None,
        configuration_id=configuration,
    )
    params = parse_qs(urlsplit(url).query)
    assert params["config_id"] == ["123456789"]
    assert params["response_type"] == ["code"]
    assert params["override_default_response_type"] == ["true"]
    assert "scope" not in params


@pytest.mark.parametrize("needs_confirmation", [False, True])
def test_oauth_callback_redirects_back_without_provider_credentials(monkeypatch, needs_confirmation):
    account_id, oauth_id = str(uuid4()), str(uuid4())

    def callback(_service, *_args, **_kwargs):
        if needs_confirmation:
            raise HTTPException(403, "password_confirmation_required")
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
    expected = "confirm" if needs_confirmation else f"{account_id}/{oauth_id}"
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
