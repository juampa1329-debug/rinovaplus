import json
from types import SimpleNamespace

import pytest

from app.institutional import channel_provider
from app.modules.channels import providers


def test_instagram_media_adapter_uses_linked_page_and_retains_instagram_identity(
    monkeypatch,
):
    monkeypatch.setattr(
        channel_provider, "get", lambda *_: ("private-test-token", {"VersionNo": 1})
    )
    item = dict(
        Channel="instagram",
        IssuerProfile="facebook_login",
        Provider="meta",
        ApiVersion="v27.0",
        ExternalAccountId="17841401482189395",
        ParentExternalId="177905975625257",
        ClientId="1688152039579779",
        IntegrationId="integration-fixture",
    )
    adapter, _ = channel_provider.provider_account(None, SimpleNamespace(), item)
    assert adapter["configuration"]["pageId"] == item["ParentExternalId"]
    assert adapter["configuration"]["accountId"] == item["ExternalAccountId"]
    assert adapter["configuration"]["instagramLogin"] == "facebook"
    adapter, _ = channel_provider.provider_account(
        None, SimpleNamespace(), {**item, "ParentExternalId": ""}
    )
    assert adapter["configuration"]["pageId"] == ""


@pytest.mark.parametrize(
    "kind,mime",
    [("image", "image/png"), ("video", "video/mp4"), ("document", "application/pdf")],
)
def test_instagram_binary_media_uses_page_endpoint_and_rechecks_frontier(
    monkeypatch, tmp_path, kind, mime
):
    source = tmp_path / "fixture.bin"
    source.write_bytes(b"bounded-test-file")
    calls = []

    def request(adapter, method, path, body=None, files=None):
        assert adapter["configuration"]["accountId"] == "instagram-id"
        assert (method, path) == ("POST", "page-id/messages")
        assert files["platform"] == (None, "instagram")
        assert json.loads(files["recipient"][1]) == {"id": "own-test-recipient"}
        attachment = json.loads(files["message"][1])["attachment"]
        assert attachment == {"type": "file" if kind == "document" else kind}
        assert files["filedata"][1].read() == b"bounded-test-file"
        assert files["filedata"][2] == mime
        calls.append("post")
        return {"message_id": "confirmed-media-id"}

    monkeypatch.setattr(providers, "request", request)
    adapter = {
        "channel": "instagram",
        "configuration": {
            "pageId": "page-id",
            "accountId": "instagram-id",
            "instagramLogin": "facebook",
        },
    }
    media = {"kind": kind, "mime": mime, "path": source, "name": "archivo.png"}
    assert (
        providers.send_media(
            adapter,
            {"target": "own-test-recipient", "body": ""},
            media,
            lambda: calls.append("frontier"),
        )
        == "confirmed-media-id"
    )
    assert calls == ["frontier", "post"]


def test_instagram_page_media_never_posts_when_linked_page_is_missing(
    monkeypatch, tmp_path
):
    source = tmp_path / "fixture.png"
    source.write_bytes(b"fixture")
    monkeypatch.setattr(
        providers, "request", lambda *_a, **_k: pytest.fail("must not post")
    )
    adapter = {
        "channel": "instagram",
        "configuration": {"instagramLogin": "facebook", "pageId": ""},
    }
    with pytest.raises(providers.ProviderFailure) as raised:
        providers.send_media(
            adapter,
            {"body": ""},
            {"path": source, "kind": "image", "mime": "image/png"},
            lambda: None,
        )
    assert raised.value.code == "instagram_page_media_required"
