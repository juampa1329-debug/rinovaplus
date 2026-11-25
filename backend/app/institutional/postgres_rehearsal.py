"""PostgreSQL connection and transaction guards for RinovaPlus CRM."""

import hashlib
import hmac
import json
import logging
import os
import re
from time import monotonic
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
DEPLOYMENT_DATABASE = "rinovaplus"
DEPLOYMENT_USER = "rinovaplus_app"
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
    "/api/institution/settings/{section}": {"get", "put"},
    "/api/institution/users": {"get"},
    "/api/institution/roles": {"get"},
    "/api/institution/sessions": {"get"},
    "/api/institution/campaigns": {"get"},
    "/api/institution/campaigns/{record}": {"get", "put"},
    "/api/institution/campaigns/{record}/preflight": {"post"},
    "/api/institution/campaigns/{record}/{action}": {"post"},
    "/api/institution/broadcasts": {"get"},
    "/api/institution/broadcasts/options": {"get"},
    "/api/institution/broadcasts/{campaign}": {"get", "put"},
    "/api/institution/broadcasts/{campaign}/report": {"get"},
    "/api/institution/broadcasts/{campaign}/{action}": {"post"},
    "/api/institution/broadcasts/accounts/{integration}/identities": {"get"},
    "/api/institution/broadcasts/accounts/{integration}/cadence": {"get", "put"},
    "/api/institution/broadcasts/accounts/{integration}/consent/{identity}": {"put"},
    "/api/institution/broadcasts/accounts/{integration}/templates/sync": {"post"},
    "/api/institution/broadcasts/accounts/{integration}/templates/sample": {"post"},
    "/api/institution/knowledge": {"get"},
    "/api/institution/memory": {"get"},
    "/api/institution/ads/accounts": {"get"},
    "/api/institution/learning/packs": {"get"},
    "/api/v1/agents/selection": {"get"},
    "/api/v1/agents/profiles/{agent_id}": {"put"},
    "/api/v1/agents/simulate": {"post"},
    "/api/institution/media/{identity}": {"get"},
    "/api/institution/workspace/clients": {"get"},
    "/api/institution/workspace/clients/{contact_id}": {"post", "put"},
    "/api/institution/workspace/inbox": {"get"},
    "/api/institution/workspace/conversations/{conversation_id}/messages": {"get", "post"},
    "/api/institution/workspace/conversations/{conversation_id}/read": {"put"},
    "/api/institution/workspace/conversations/{conversation_id}/social-profile": {"get"},
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

    deployment_mode = env.get("CRM_DATABASE_ENGINE") == "postgresql"
    database = DEPLOYMENT_DATABASE if deployment_mode else DATABASE
    origin = None
    if deployment_mode:
        from app.institutional.deployment import DeploymentError, public_origin

        try:
            origin = public_origin(env)
        except DeploymentError as error:
            raise ProfileError(str(error)) from None
        if not origin:
            raise ProfileError("postgres_public_origin_required")
    dsn = env.get("CRM_POSTGRES_URL", "")
    try:
        url = urlsplit(dsn)
        port = url.port
    except ValueError:
        raise ProfileError("postgres_url_invalid") from None
    if (
        url.scheme not in {"postgres", "postgresql"}
        or url.path != "/" + database or not url.hostname or port == 0
        or url.query or url.fragment or (not deployment_mode and env.get("CRM_SQL_URL"))
    ):
        raise ProfileError("postgres_deployment_target_required" if deployment_mode else "postgres_rehearsal_target_required")
    user = env.get("CRM_POSTGRES_USER")
    password = env.get("CRM_POSTGRES_PASSWORD")
    if deployment_mode and (user != DEPLOYMENT_USER or not password):
        raise ProfileError("postgres_deployment_credentials_required")
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
            target, version, actor, privileged, create_database, create_schema = c.fetchone()
            if (target != database or version < 160000 or privileged or create_database or create_schema
                    or (deployment_mode and actor != DEPLOYMENT_USER)):
                raise ProfileError("postgres_identity_or_privilege")
            c.execute(
                """SELECT c.relname FROM pg_catalog.pg_class c
                   JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
                   WHERE n.nspname='rinovaplus_crm' AND c.relkind='r'"""
            )
            if {row[0] for row in c} != {v.split(".", 1)[1].lower() for v in physical}:
                raise ProfileError("postgres_crm_catalog_drift")
            c.execute("SELECT archive_sha256 FROM rinova_migration.source_snapshot")
            if c.fetchall() != [(digest,)]:
                raise ProfileError("postgres_snapshot_mismatch")
            c.execute(
                """SELECT institutionid,contractversion FROM rinovaplus_crm.crmcanalinstitucionalcontexto
                   WHERE contextid=1"""
            )
            context = c.fetchall()
            if len(context) != 1 or context[0][1] != "CBN-channels-parity-v1":
                raise ProfileError("postgres_institution_context_required")
    except Error:
        raise ProfileError("postgres_connection_or_permissions") from None
    institution = str(UUID(context[0][0]))
    binding = hashlib.sha256((database + ":" + digest + ":" + institution).encode()).hexdigest()
    session_key = hmac.digest(key, ("rinova-pg-session:" + binding).encode(), "sha256")
    return SimpleNamespace(
        postgres_profile=True,
        postgres_deployment=deployment_mode,
        postgres_connect=lambda: open_connection(dsn),
        postgres_user=actor,
        postgres_columns=columns,
        connection={"database": database},
        public_origin=origin,
        public_host=urlsplit(origin).netloc if origin else None,
        review={"secrets_key": encoded, "session_token": b64encode(session_key).decode()},
        ticket={
            "version": PROFILE, "scope": "postgres_deployment" if deployment_mode else "postgres_rehearsal",
            "identity": {"database": database}, "context": [[1, institution, context[0][1]]],
            "table_map": mapping,
        },
    )


@contextmanager
def transaction(settings, write=False, *, permission=None, anonymous=False, recent=False):
    from psycopg2 import Error

    stage = "connect"
    started = monotonic()
    acquired = None
    cursor = None
    try:
        with closing(settings.postgres_connect()) as conn, conn, conn.cursor() as raw:
            if not write:
                raw.execute("SET TRANSACTION READ ONLY")
            raw.execute("SET LOCAL search_path=pg_catalog,rinovaplus_crm")
            raw.execute("SET LOCAL statement_timeout='8s'")
            raw.execute("SET LOCAL lock_timeout='3s'")
            stage = "identity"
            raw.execute(
                "SELECT current_database(), current_user, institutionid"
                " FROM rinovaplus_crm.crmcanalinstitucionalcontexto WHERE contextid=1"
            )
            if raw.fetchone() != (settings.connection["database"], settings.postgres_user, settings.ticket["context"][0][1]):
                raise ProfileError("postgres_identity_changed")
            # Existing security and idempotency paths expect serialized writes.
            # Keep the lock within this PostgreSQL database and institution.
            lock = "pg_advisory_xact_lock" if write else "pg_advisory_xact_lock_shared"
            stage = "institution_lock"
            raw.execute(f"SELECT {lock}(hashtextextended(%s,0))", (settings.ticket["context"][0][1],))
            acquired = monotonic()
            stage = "authorization"
            cursor = Cursor(raw, settings.ticket["table_map"], settings.postgres_columns)
            if not anonymous:
                from app.institutional.auth import authorize

                authority = request_authority.get()
                if authority is None:
                    raise HTTPException(401, "session_required")
                authorize(cursor, settings, authority, permission or authority["permission"], recent=recent)
            stage = "body"
            yield cursor
            stage = "commit"
    except (Error, ProfileError, ValueError) as error:
        safe_tags = {"password_policy", "invalid_password", "unported_statement", "unmapped_crm_table", "unported_update_target", "unported_update_join", "unported_subquery_limit", "unported_outer_apply"}
        tag = str(error) if type(error) is ValueError and str(error) in safe_tags else "unclassified"
        state = getattr(error, "pgcode", None) or type(error).__name__
        LOG.warning("postgres_storage_error state=%s tag=%s stage=%s write=%s elapsed_ms=%s", state, tag, stage, write, round((monotonic() - started) * 1000))
        if state == "55P03" and stage == "institution_lock":
            # No application work has begun. Distinguish contention from an
            # identity/permission failure; never replay a caller's mutation.
            raise HTTPException(503, "storage_busy", headers={"Retry-After": "1"}) from None
        raise HTTPException(503, "general_storage_unavailable") from None
    finally:
        if acquired is not None and (held := monotonic() - acquired) >= 1:
            timing = getattr(cursor, "slowest", None)
            statement_ms, statement_id, source = timing if isinstance(timing, tuple) else (0, "none", "none")
            LOG.warning("postgres_transaction_slow write=%s held_ms=%s stage=%s statement_ms=%s statement_id=%s source=%s", write, round(held * 1000), stage, statement_ms, statement_id, source)


def network_disabled(*_args, **_options):
    from app.modules.channels.providers import ProviderFailure

    raise ProviderFailure("provider_network_disabled")


def apply_environment():
    return load(os.environ)
