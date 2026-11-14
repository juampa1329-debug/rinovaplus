"""Environment SQL transport and independently validated deployment authority."""

import base64
import hashlib
import hmac
import json
import logging
import os
import re
from contextlib import contextmanager
from dataclasses import dataclass, field
from types import SimpleNamespace
from urllib.parse import urlsplit

import pyodbc

from app.institutional import operations_policy
from app.institutional.operations_policy import DeploymentError
from app.sql_target import HOST, _quoted
from tools.es_schema_migrate_v2 import identity
from tools.foundation_snapshot import sha

VARIABLES = ("CRM_SQL_URL", "CRM_SQL_USER", "CRM_SQL_PASSWORD")
DATABASE_VARIABLE = "CRM_SQL_DATABASE"
DATABASE_NAME = re.compile(r"[\w -]{1,128}")
SYSTEM_DATABASES = frozenset(
    {"master", "model", "msdb", "tempdb", "mssqlsystemresource"}
)
TEST_DATABASE = re.compile(r"RinovaPlus_Trial_[a-f0-9]{8}", re.IGNORECASE)
LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class Transport:
    host: str
    port: int
    database: str
    user: str = field(repr=False)
    password: str = field(repr=False)

    def odbc_string(self):
        values = {
            "DRIVER": "{ODBC Driver 18 for SQL Server}",
            "SERVER": f"tcp:{self.host},{self.port}",
            "DATABASE": _quoted(self.database),
            "UID": _quoted(self.user),
            "PWD": _quoted(self.password),
            "Encrypt": "Yes",
            "TrustServerCertificate": "Yes",
            "APP": "RinovaPlus",
        }
        return ";".join(f"{name}={value}" for name, value in values.items()) + ";"


def transport_from_env(env):
    if DATABASE_VARIABLE not in env and not any(name in env for name in VARIABLES):
        return None
    if not all(env.get(name) for name in VARIABLES):
        raise DeploymentError(
            "sql_environment_incomplete: set CRM_SQL_URL, CRM_SQL_USER and "
            "CRM_SQL_PASSWORD"
        )
    url, user, password = (env[name] for name in VARIABLES)
    match = re.fullmatch(
        r"sqlserver://([A-Za-z0-9.-]+):([0-9]{1,5})(?:/([A-Za-z0-9_]{1,128})?)?", url
    )
    if not match or not HOST.fullmatch(match[1]) or not 1 <= int(match[2]) <= 65535:
        raise DeploymentError(
            "sql_url_invalid: use sqlserver://host:port or sqlserver://host:port/database"
        )
    if DATABASE_VARIABLE in env:
        database = env[DATABASE_VARIABLE]
        if (
            not DATABASE_NAME.fullmatch(database)
            or database != database.strip()
            or database.lower() in SYSTEM_DATABASES
        ):
            raise DeploymentError(
                "sql_database_invalid: set CRM_SQL_DATABASE to a valid database name"
            )
    else:
        database = match[3]
        if database is None:
            raise DeploymentError("sql_database_missing: set CRM_SQL_DATABASE")
        if not (
            database.lower() == "dbsiie"
            or operations_policy.TARGET.fullmatch(database)
            or TEST_DATABASE.fullmatch(database)
        ):
            raise DeploymentError(
                "sql_database_not_allowed: use dbsiie or set CRM_SQL_DATABASE"
            )
    if (
        not user.strip()
        or len(user) > 128
        or not password.strip()
        or len(password) > 128
        or any(ord(character) < 32 or ord(character) == 127 for character in user + password)
    ):
        raise DeploymentError("sql_credentials_invalid")
    return Transport(match[1], int(match[2]), database, user, password)


def public_origin(env):
    value = env.get("CRM_PUBLIC_BASE_URL")
    if value is None:
        return None
    match = re.fullmatch(r"https://([A-Za-z0-9.-]+)/?", value)
    if not match or not HOST.fullmatch(match[1]):
        raise DeploymentError("public_origin_invalid: use an HTTPS origin without a port or path")
    return "https://" + match[1].lower()


def open_connection(transport, *, probe=False):
    try:
        connection = pyodbc.connect(
            transport.odbc_string(), timeout=5, autocommit=probe, readonly=probe
        )
    except pyodbc.Error as error:
        message = str(error).lower()
        state = error.args[0] if error.args else ""
        if state == "28000" or "login failed" in message:
            raise DeploymentError("sql_login_rejected") from None
        if any(word in message for word in ("certificate", "ssl provider", "tls")):
            raise DeploymentError(
                "sql_tls_negotiation_failed: check that SQL Server and ODBC support a common TLS configuration"
            ) from None
        raise DeploymentError("sql_connection_failed: check routing, firewall and TCP port") from None
    return connection


@contextmanager
def probe_connection(transport):
    connection = open_connection(transport, probe=True)
    try:
        connection.timeout = 20
        yield connection.cursor()
    finally:
        connection.close()


def check_target(cursor, transport, *, expected=None):
    current = identity(cursor)
    if (
        str(current["database"]).lower() != transport.database.lower()
        or (current["engine"], current["compatibility"]) != (15, 150)
        or (expected is not None and current != expected)
    ):
        raise DeploymentError("sql_database_identity_mismatch: expected SQL Server 2019 and compatibility 150")
    return current


def inspect(transport, *, runtime):
    try:
        with probe_connection(transport) as cursor:
            target = check_target(cursor, transport)
            mapping = operations_policy.deployment_catalog(cursor, inventory_only=not runtime)
            if runtime:
                return target, operations_policy.deployment_authority(cursor, transport.user, mapping)
    except pyodbc.Error:
        raise DeploymentError("sql_catalog_read_failed: check metadata and CRM permissions") from None
    except DeploymentError:
        raise
    except (ValueError, KeyError, TypeError, OSError) as error:
        if isinstance(error, ValueError) and re.fullmatch(r"P[0-9]{1,2}ES_[A-Za-z0-9_]{1,80}", str(error)):
            raise DeploymentError("sql_deployment_policy_failed: " + str(error)) from None
        raise DeploymentError("sql_deployment_policy_failed") from None


def load(transport, env):
    # Reject the public configuration before doing any network I/O.
    origin = public_origin(env)
    encoded = env.get("CRM_SECURITY_KEY", "")
    try:
        key = base64.b64decode(encoded, validate=True)
    except ValueError:
        key = b""
    if len(key) != 32:
        raise DeploymentError("security_key_invalid: set CRM_SECURITY_KEY to a persistent base64-encoded 32-byte key")
    target, authority = inspect(transport, runtime=True)
    partition = operations_policy.layout()
    ticket = {
        **authority,
        "version": operations_policy.VERSION,
        "scope": "institutional_deployment",
        "identity": target,
        "operations_release_sha256": operations_policy.release(),
        "table_map": partition["tables"],
    }
    binding = sha({
        "identity": target,
        "institution": authority["context"][0][1],
        "scope": ticket["scope"],
    })
    session_key = hmac.digest(key, ("rinovaplus-session-v1:" + binding).encode(), "sha256")
    review = {
        "ticket_sha256": binding,
        "secrets_key": encoded,
        "session_token": base64.b64encode(session_key).decode(),
    }
    return SimpleNamespace(
        deployment_transport=transport,
        public_origin=origin,
        public_host=urlsplit(origin).netloc if origin else None,
        ticket=ticket,
        review=review,
    )


def verify(cursor, settings):
    transport = settings.deployment_transport
    check_target(cursor, transport, expected=settings.ticket["identity"])
    mapping = operations_policy.deployment_catalog(cursor)
    if operations_policy.deployment_authority(cursor, transport.user, mapping) != {
        key: settings.ticket[key] for key in ("sid", "context", "history_sha256")
    }:
        raise DeploymentError("sql_deployment_authority_drift")


def diagnose():
    """Read only, for an operator with CONNECT and VIEW DEFINITION."""
    try:
        transport = transport_from_env(os.environ)
        if transport is None:
            raise DeploymentError("sql_environment_incomplete")
        inspect(transport, runtime=False)
    except DeploymentError as error:
        LOG.error("%s", error)
        return 1
    print(json.dumps({"sql": "verified", "scope": "catalog_read_only"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(diagnose())
