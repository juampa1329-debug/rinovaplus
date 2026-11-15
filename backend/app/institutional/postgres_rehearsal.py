"""Opt-in PostgreSQL backend and transaction guards for the rehearsal copy."""

import hashlib
import hmac
import json
import logging
import os
import re
from base64 import b64decode, b64encode
from contextlib import closing, contextmanager
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import HTTPException

from app.institutional import operations_policy
from app.institutional.operations import STAGES
from app.institutional.policy import request_authority
from app.institutional.postgres_dialect import Cursor


DATABASE = "rinovaplus_rehearsal"
PROFILE = operations_policy.VERSION
WORKER_STAGES = STAGES
REHEARSAL_ROUTES = {
    "/api/institution/auth/status": {"get"},
    "/api/institution/auth/login": {"post"},
    "/api/institution/auth/verify": {"post"},
    "/api/institution/auth/me": {"get"},
    "/api/institution/auth/logout": {"post"},
    "/api/institution/auth/confirm": {"post"},
    "/api/institution/operations": {"get"},
    "/api/institution/runtime": {"get"},
    "/api/institution/settings/{section}": {"get"},
    "/api/institution/users": {"get"},
    "/api/institution/roles": {"get"},
    "/api/institution/sessions": {"get"},
    "/api/institution/campaigns": {"get"},
    "/api/institution/broadcasts": {"get"},
    "/api/institution/knowledge": {"get"},
    "/api/institution/memory": {"get"},
    "/api/institution/ads/accounts": {"get"},
    "/api/institution/learning/packs": {"get"},
    "/api/v1/agents/selection": {"get"},
    "/api/institution/media/{identity}": {"get"},
    "/api/institution/workspace/clients": {"get"},
    "/api/institution/workspace/clients/{contact_id}": {"post", "put"},
    "/api/institution/workspace/inbox": {"get"},
    "/api/institution/workspace/conversations/{conversation_id}/messages": {"get", "post"},
}
LOG = logging.getLogger(__name__)


class ProfileError(ValueError):
    pass


def open_connection(dsn):
    import psycopg2

    return psycopg2.connect(dsn, connect_timeout=4, application_name="rinovaplus-rehearsal")


def load(env):
    from psycopg2 import Error
    from psycopg2.extensions import make_dsn

    dsn = env.get("CRM_POSTGRES_URL", "")
    try:
        url = urlsplit(dsn)
    except ValueError:
        raise ProfileError("postgres_url_invalid") from None
    if (
        url.scheme not in {"postgres", "postgresql"}
        or url.path != "/" + DATABASE or not url.hostname
        or url.query or url.fragment or env.get("CRM_SQL_URL")
    ):
        raise ProfileError("postgres_rehearsal_target_required")
    user = env.get("CRM_POSTGRES_USER")
    password = env.get("CRM_POSTGRES_PASSWORD")
    if user is not None or password is not None:
        if not user or not password or url.username is not None or url.password is not None:
            raise ProfileError("postgres_credentials_invalid")
        try:
            dsn = make_dsn(dsn, user=user, password=password)
        except (ValueError, Error):
            raise ProfileError("postgres_credentials_invalid") from None
    elif not url.username:
        raise ProfileError("postgres_credentials_required")
    digest = env.get("CRM_POSTGRES_SNAPSHOT_SHA256", "")
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ProfileError("postgres_snapshot_required")
    encoded = env.get("CRM_SECURITY_KEY", "")
    try:
        key = b64decode(encoded, validate=True)
    except ValueError:
        key = b""
    if len(key) != 32:
        raise ProfileError("postgres_rehearsal_key_required")

    mapping = operations_policy.layout()["tables"]
    model_path = operations_policy.parent.PACKAGE / "expected-model.json"
    blueprint = json.loads(Path(model_path).read_text(encoding="utf-8"))
    physical = set(mapping.values())
    columns = {
        row["name"].lower(): row["name"] for row in blueprint["columns"]
        if row["schema"] + "." + row["table"] in physical
    }
    try:
        with closing(open_connection(dsn)) as conn, conn, conn.cursor() as c:
            c.execute(
                """SELECT current_database(),current_setting('server_version_num')::integer,
                   current_user, rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls,
                   has_database_privilege(current_user, current_database(), 'CREATE'),
                   has_schema_privilege(current_user, 'rinovaplus_crm', 'CREATE')
                   FROM pg_catalog.pg_roles WHERE rolname=current_user"""
            )
            target, version, user, privileged, create_database, create_schema = c.fetchone()
            if target != DATABASE or version < 160000 or privileged or create_database or create_schema:
                raise ProfileError("postgres_rehearsal_identity_or_privilege")
            c.execute(
                """SELECT c.relname FROM pg_catalog.pg_class c
                   JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
                   WHERE n.nspname='rinovaplus_crm' AND c.relkind='r'"""
            )
            if {row[0] for row in c} != {v.split(".", 1)[1].lower() for v in physical}:
                raise ProfileError("postgres_crm_catalog_drift")
            c.execute("SELECT archive_sha256 FROM rinova_migration.source_snapshot")
            if c.fetchall() != [(digest,)]:
                raise ProfileError("postgres_rehearsal_snapshot_mismatch")
            c.execute(
                """SELECT institutionid,contractversion FROM rinovaplus_crm.crmcanalinstitucionalcontexto
                   WHERE contextid=1"""
            )
            context = c.fetchall()
            if len(context) != 1 or context[0][1] != "CBN-channels-parity-v1":
                raise ProfileError("postgres_institution_context_required")
    except Error:
        raise ProfileError("postgres_rehearsal_connection_or_permissions") from None
    institution = str(UUID(context[0][0]))
    binding = hashlib.sha256((DATABASE + ":" + digest + ":" + institution).encode()).hexdigest()
    session_key = hmac.digest(key, ("rinova-pg-session:" + binding).encode(), "sha256")
    return SimpleNamespace(
        postgres_profile=True,
        postgres_connect=lambda: open_connection(dsn),
        postgres_user=user,
        postgres_columns=columns,
        connection={"database": DATABASE},
        public_origin=None,
        public_host=None,
        review={"secrets_key": encoded, "session_token": b64encode(session_key).decode()},
        ticket={
            "version": PROFILE, "scope": "postgres_rehearsal",
            "identity": {"database": DATABASE}, "context": [[1, institution, context[0][1]]],
            "table_map": mapping,
        },
    )


@contextmanager
def transaction(settings, write=False, *, permission=None, anonymous=False, recent=False):
    from psycopg2 import Error

    try:
        with closing(settings.postgres_connect()) as conn, conn, conn.cursor() as raw:
            if not write:
                raw.execute("SET TRANSACTION READ ONLY")
            raw.execute("SET LOCAL search_path=pg_catalog,rinovaplus_crm")
            raw.execute("SET LOCAL statement_timeout='8s'")
            raw.execute("SET LOCAL lock_timeout='3s'")
            raw.execute(
                "SELECT current_database(), current_user, institutionid"
                " FROM rinovaplus_crm.crmcanalinstitucionalcontexto WHERE contextid=1"
            )
            if raw.fetchone() != (DATABASE, settings.postgres_user, settings.ticket["context"][0][1]):
                raise ProfileError("postgres_rehearsal_identity_changed")
            # Existing security and idempotency paths expect serialized writes.
            # Keep the lock within this PostgreSQL database and institution.
            lock = "pg_advisory_xact_lock" if write else "pg_advisory_xact_lock_shared"
            raw.execute(f"SELECT {lock}(hashtextextended(%s,0))", (settings.ticket["context"][0][1],))
            cursor = Cursor(raw, settings.ticket["table_map"], settings.postgres_columns)
            if not anonymous:
                from app.institutional.auth import authorize

                authority = request_authority.get()
                if authority is None:
                    raise HTTPException(401, "session_required")
                authorize(cursor, settings, authority, permission or authority["permission"], recent=recent)
            yield cursor
    except (Error, ProfileError, ValueError) as error:
        LOG.warning("postgres_rehearsal_storage_error state=%s", getattr(error, "pgcode", None) or type(error).__name__)
        raise HTTPException(503, "general_storage_unavailable") from None


def network_disabled(*_args, **_options):
    from app.modules.channels.providers import ProviderFailure

    raise ProviderFailure("provider_network_disabled")


def apply_environment():
    return load(os.environ)
