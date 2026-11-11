"""Real loopback HTTP; production adapters still construct fixed HTTPS URLs."""

import http.client
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import httpx2 as httpx
import pytest

from app.institutional.channel_provider import call_provider, safe_result
from app.institutional.channel_tokens import health, renew
from app.modules.channels import providers


@pytest.fixture
def server(monkeypatch):
    state = {"paths": [], "wrong_app": False, "mode": "normal"}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            self.respond()

        def do_POST(self):
            self.respond()

        def respond(self):
            path = urlsplit(self.path).path
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            state["paths"].append((self.command, path))
            if state["mode"] == "lost_ack" and self.command == "POST":
                self.close_connection = True
                return
            if state["mode"] == "redirect":
                self.send_response(302)
                self.send_header("Location", "https://unapproved.example.test")
                self.end_headers()
                return
            if state["mode"] == "oversized":
                data = b"x" * 1_000_001
            elif state["mode"] == "rejected":
                self.send_response(403)
                self.end_headers()
                self.wfile.write(
                    b'{"error":{"message":"owned-secret-must-not-escape"}}'
                )
                return
            else:
                values = {
                    "/v24.0/phone": {
                        "id": "phone",
                        "display_phone_number": "+573000000000",
                        "verified_name": "Owned fixture",
                    },
                    "/v24.0/waba/phone_numbers": {
                        "data": [
                            {
                                "id": "phone",
                                "display_phone_number": "+573000000000",
                                "verified_name": "Owned fixture",
                            }
                        ]
                    },
                    "/v24.0/debug_token": {
                        "data": {
                            "is_valid": True,
                            "app_id": "another-app"
                            if state["wrong_app"]
                            else "owned-app",
                            "expires_at": 2000000000,
                            "scopes": ["pages_show_list"],
                        }
                    },
                    "/v24.0/phone/register": {"success": True},
                    "/v24.0/phone/messages": {
                        "messages": [{"id": "owned-external-message"}]
                    },
                    "/v24.0/oauth/access_token": {
                        "access_token": "owned-renewed-user-token",
                        "expires_in": 5184000,
                    },
                    "/v24.0/me/accounts": {
                        "data": [
                            {"id": "page", "access_token": "owned-renewed-page-token"}
                        ]
                    },
                }
                if path.endswith("/register"):
                    assert json.loads(body) == {
                        "messaging_product": "whatsapp",
                        "pin": "123456",
                    }
                data = json.dumps(values.get(path, {"success": True})).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    listener = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=listener.serve_forever, daemon=True)
    thread.start()
    original = httpx.Client

    def route(request):
        assert request.url.scheme == "https"
        assert request.url.host == "graph.facebook.com"
        connection = http.client.HTTPConnection(
            "127.0.0.1", listener.server_port, timeout=2
        )
        try:
            connection.request(
                request.method,
                request.url.raw_path.decode(),
                body=request.content,
                headers=dict(request.headers),
            )
            response = connection.getresponse()
            return httpx.Response(
                response.status,
                content=response.read(),
                headers=dict(response.getheaders()),
                request=request,
            )
        except http.client.RemoteDisconnected:
            raise httpx.ReadError("owned_ack_lost", request=request) from None
        finally:
            connection.close()

    def client(**kwargs):
        assert kwargs["trust_env"] is False and kwargs["follow_redirects"] is False
        return original(**kwargs, transport=httpx.MockTransport(route))

    monkeypatch.setattr(httpx, "Client", client)
    try:
        yield state
    finally:
        listener.shutdown()
        listener.server_close()
        thread.join(timeout=2)


def fixture():
    item = {
        "Provider": "meta",
        "IssuerProfile": "meta_whatsapp",
        "ClientId": "owned-app",
        "Channel": "whatsapp",
        "ApiVersion": "v24.0",
        "ExternalAccountId": "phone",
        "ParentExternalId": "waba",
    }
    adapter = {
        "channel": "whatsapp",
        "configuration": {
            "phoneNumberId": "phone",
            "wabaId": "waba",
            "apiVersion": "v24.0",
        },
        "secrets": {
            "accessToken": "owned-access-token",
            "appSecret": "owned-app-secret",
        },
    }
    return item, adapter


def test_verification_checks_asset_waba_and_application(server):
    item, adapter = fixture()
    value = call_provider(adapter, "verify", item)
    assert value["apiAssetValidated"] and value["applicationValidated"]
    assert {p for _, p in server["paths"]} == {
        "/v24.0/phone",
        "/v24.0/waba/phone_numbers",
        "/v24.0/debug_token",
    }


def test_wrong_token_application_is_not_verified(server):
    item, adapter = fixture()
    server["wrong_app"] = True
    with pytest.raises(
        providers.ProviderFailure, match="token_application_mismatch_or_invalid"
    ):
        health(adapter, item)


def test_number_discovery_does_not_require_preselected_phone(server):
    item, adapter = fixture()
    item["ExternalAccountId"] = None
    value = call_provider(adapter, "numbers", item)
    assert value["numbers"][0]["id"] == "phone"
    assert server["paths"] == [("GET", "/v24.0/waba/phone_numbers")]


def test_register_uses_six_digit_pin_not_an_otp_contract(server):
    item, adapter = fixture()
    assert call_provider(adapter, "register", item, "123456") == {"success": True}
    assert server["paths"] == [("POST", "/v24.0/phone/register")]


def test_post_acceptance_is_only_external_identifier(server):
    _, adapter = fixture()
    assert (
        providers.send(
            adapter,
            {"kind": "chat", "target": "573000000000", "body": "Owned response"},
        )
        == "owned-external-message"
    )


@pytest.mark.parametrize("mode", ["redirect", "oversized", "rejected"])
def test_untrusted_provider_response_stays_bounded_and_redacted(server, mode):
    _, adapter = fixture()
    server["mode"] = mode
    with pytest.raises(providers.ProviderFailure) as error:
        providers.request(adapter, "GET", "phone")
    assert "owned-secret-must-not-escape" not in str(error.value)
    assert len(server["paths"]) == 1


def test_lost_post_ack_is_uncertain_and_not_repeated(server):
    _, adapter = fixture()
    server["mode"] = "lost_ack"
    with pytest.raises(providers.ProviderFailure) as error:
        providers.send(
            adapter,
            {"kind": "chat", "target": "573000000000", "body": "Owned response"},
        )
    assert error.value.uncertain
    assert len(server["paths"]) == 1


def test_token_renewal_returns_secrets_only_to_internal_rotation(server):
    item, adapter = fixture()
    item.update(
        IssuerProfile="facebook_login", Channel="facebook", ExternalAccountId="page"
    )
    adapter["secrets"]["userToken"] = "owned-user-token"
    value = renew(adapter, item)
    assert value["_tokens"]["facebook_page_access"] == "owned-renewed-page-token"
    metadata = safe_result("refresh", value)
    assert metadata["confirmed"] and "owned-" not in json.dumps(metadata)
