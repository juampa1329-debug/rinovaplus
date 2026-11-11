import hmac
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest
from cryptography.exceptions import InvalidTag
from fastapi import HTTPException

from app.institutional.channel_events import delivery, normalize
from app.institutional.channel_ingress import signature_valid
from app.institutional.channel_oauth import authorization_url
from app.institutional.channel_operations import capabilities
from app.institutional.channel_provider import ProviderAction, provider_account
from app.institutional.channel_secrets import binding
from app.institutional.crypto import seal, unseal


@pytest.mark.parametrize("raw", ['{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'])
def test_strict_provider_json_rejects_ambiguous_input(raw):
    from app.institutional.channel_ingress import strict_json

    with pytest.raises((ValueError, HTTPException)):
        strict_json(raw)


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
