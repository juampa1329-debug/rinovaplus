"""One runtime SIIE origin; durable work never migrates to another environment."""

import hashlib
import os
import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

from fastapi import HTTPException
from app.institutional.program_commercial import approved_url


@dataclass(frozen=True)
class Environment:
    base_url: str

    @property
    def fingerprint(self):
        return hashlib.sha256(self.base_url.encode()).hexdigest()

    def document(self):
        return {"base_url": self.base_url, "fingerprint": self.fingerprint}

    def endpoint(self, path):
        if not re.fullmatch(r"[A-Za-z0-9_-]+(?:/[A-Za-z0-9_.-]+)*", path) or any(
            part in {".", ".."} for part in path.split("/")):
            raise ValueError("invalid_siie_relative_route")
        return urljoin(self.base_url, path)


def current():
    value = os.getenv("SIIE_BASE_URL", "").strip()
    hosts = {v.strip().lower() for v in os.getenv("SIIE_API_HOSTS", "siieplus.online").split(",") if v.strip()}
    try:
        checked = approved_url(value, hosts)
    except HTTPException:
        raise HTTPException(409, "siie_base_url_invalid") from None
    parsed = urlsplit(checked)
    if (not checked.endswith("/") or parsed.query or parsed.fragment or
            not parsed.path or any(p in {".", ".."} for p in parsed.path.split("/")) or
            "%" in parsed.path or "\\" in parsed.path):
        raise HTTPException(409, "siie_base_url_invalid")
    return Environment(checked)


def configured():
    return bool(os.getenv("SIIE_BASE_URL", "").strip())


def require(expected):
    environment = current()
    if expected != environment.document():
        raise HTTPException(409, "siie_environment_changed")
    return environment


def request_context(request):
    environment = current()
    if request.headers.get("X-SIIE-Environment") != environment.fingerprint:
        raise HTTPException(409, "siie_environment_refresh_required")
    return environment
