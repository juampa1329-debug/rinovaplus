"""Download only authenticated-provider media using pinned public TLS destinations."""

import http.client
import ipaddress
import re
import socket
import ssl
import time
from urllib.parse import urlsplit

from app.modules.channels.providers import ProviderFailure, request
from app.modules.inbox.infrastructure.media_files import MAX_BYTES


def retrieve(account, reference, destination):
    token = None
    if account["channel"] == "whatsapp":
        identifier = reference.get("id", "")
        if not re.fullmatch(r"[0-9]{1,100}", identifier):
            raise ProviderFailure("media_reference_invalid")
        metadata = request(account, "GET", identifier)
        url = metadata.get("url", "")
        token = account["secrets"]["accessToken"]
    elif account["channel"] in ("instagram", "messenger"):
        url = reference.get("url", "")
    elif account["channel"] == "tiktok":
        metadata = request(
            account,
            "POST",
            "business/message/media/download/",
            {
                key: reference[key]
                for key in (
                    "business_id",
                    "conversation_id",
                    "message_id",
                    "media_id",
                    "media_type",
                )
            },
        )
        url = metadata.get("data", {}).get("download_url", "")
    else:
        raise ProviderFailure("channel_media_not_supported")
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        if (
            len(url) > 8192
            or parts.scheme != "https"
            or parts.username
            or parts.password
            or parts.port not in (None, 443)
            or parts.fragment
        ):
            raise ProviderFailure("media_remote_host_rejected")
        if account["channel"] == "tiktok" and host != "business-api.tiktok.com":
            raise ProviderFailure("tiktok_media_host_not_verified")
        if account["channel"] != "tiktok" and not (
            host == "lookaside.fbsbx.com"
            or host.endswith((".fbcdn.net", ".cdninstagram.com"))
        ):
            raise ProviderFailure("media_remote_host_rejected")
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        if not addresses or any(
            not ipaddress.ip_address(item[4][0]).is_global for item in addresses
        ):
            raise ProviderFailure("media_remote_host_rejected")
        address = addresses[0][4][0]
        connection = http.client.HTTPSConnection(
            host, timeout=15, context=ssl.create_default_context()
        )
        raw = socket.create_connection((address, 443), timeout=8)
        try:
            connection.sock = connection._context.wrap_socket(raw, server_hostname=host)
        except BaseException:
            raw.close()
            raise
        destination.unlink(missing_ok=True)
        try:
            headers = {"Host": host, "Accept-Encoding": "identity"}
            if token:
                headers["Authorization"] = "Bearer " + token
            if account["channel"] == "tiktok":
                headers["x-user"] = account["secrets"]["accessToken"]
            connection.request(
                "GET",
                (parts.path or "/") + ("?" + parts.query if parts.query else ""),
                headers=headers,
            )
            response = connection.getresponse()
            if response.status != 200:
                raise ProviderFailure(
                    "media_download_rejected",
                    retry=response.status in (429, 500, 502, 503, 504),
                )
            length = response.getheader("Content-Length")
            if length is not None and (
                not length.isdecimal() or int(length) > MAX_BYTES
            ):
                raise ProviderFailure("media_size_limit")
            if response.getheader("Content-Encoding", "identity") != "identity":
                raise ProviderFailure("media_encoding_rejected")
            total, started = 0, time.monotonic()
            with destination.open("xb") as handle:
                import os

                os.chmod(destination, 0o600)
                while True:
                    chunk = response.read(65536)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_BYTES or time.monotonic() - started > 40:
                        raise ProviderFailure("media_download_limit")
                    handle.write(chunk)
            if not total or length is not None and total != int(length):
                raise ProviderFailure("media_download_incomplete", retry=True)
        finally:
            connection.close()
    except (ValueError, OSError, ssl.SSLError, http.client.HTTPException):
        destination.unlink(missing_ok=True)
        raise ProviderFailure("media_download_unavailable", retry=True) from None
