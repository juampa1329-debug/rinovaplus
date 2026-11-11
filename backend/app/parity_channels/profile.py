"""Fail-closed C12 encrypted profile, scoped capability and TLS connection."""

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from app.parity_channels.policy import TARGET, VERSION, principal, require
from app.sql_profile import SqlProfileStore
from app.sql_target import HOST, _quoted


@dataclass(frozen=True)
class Settings:
    connection: dict = field(repr=False)
    review: dict = field(repr=False)
    ticket: dict = field(repr=False)


def load(directory):
    directory = Path(directory)
    require(directory.is_absolute(), "C12_absolute_private_profile")
    stored = SqlProfileStore(directory / "runtime").load()
    require(stored is not None, "C12_profile_required")
    c, review = stored["connection"], stored["review"]
    require(
        TARGET.fullmatch(c["database"]) and c["username"] == principal(c["database"]),
        "C12_profile_target",
    )
    require(
        HOST.fullmatch(c["server"])
        and c["certificate_hostname"] == "localhost"
        and type(c["port"]) is int
        and 1 <= c["port"] <= 65535,
        "C12_profile_TLS",
    )
    raw = (directory / "runtime-ticket.json").read_bytes()
    require(
        hashlib.sha256(raw).hexdigest() == review["ticket_sha256"], "C12_ticket_digest"
    )
    ticket = json.loads(raw)
    require(
        ticket["scope"] == "SQL-C12-repositories-rehearsal-only"
        and ticket["version"] == VERSION
        and ticket["identity"]["database"] == c["database"],
        "C12_ticket_scope",
    )
    require(
        ticket["identity"]["engine"] == 16
        and ticket["identity"]["compatibility"] == 160
        and type(ticket["expires_at"]) is int
        and time.time() < ticket["expires_at"],
        "C12_local_engine_or_expiry",
    )
    require(
        hashlib.sha256(review["api_token"].encode()).hexdigest()
        == ticket["api_token_sha256"]
        and len(review["api_token"]) >= 40,
        "C12_capability",
    )
    require(len(bytes.fromhex(review["operation_key"])) == 32, "C12_operation_key")
    return Settings(c, review, ticket)


def connection_string(settings):
    c = settings.connection
    return (
        "DRIVER={ODBC Driver 18 for SQL Server};SERVER=tcp:"
        + c["server"]
        + ","
        + str(c["port"])
        + ";DATABASE="
        + _quoted(c["database"])
        + ";Encrypt=Yes;TrustServerCertificate=No;HostnameInCertificate=localhost;UID="
        + _quoted(c["username"])
        + ";PWD="
        + _quoted(c["password"])
        + ";APP=CBN C12 repositories;"
    )
