"Own encrypted Spanish SQL2019 profile and transaction authority for P2."

import base64
import hashlib
import json
import logging
import re
import time
from contextlib import contextmanager, suppress
from pathlib import Path
from types import SimpleNamespace

import pyodbc
from fastapi import HTTPException

from app.es_schema_profile import journal_digest
from app.foundation import RIGHTS as CORE_RIGHTS
from app.institutional import deployment
from app.institutional.policy import request_authority
from app.institutional.spanish_bindings import (
    TARGET,
    VERSION,
    Cursor,
    canonical_context,
    layout,
    principal,
)
from app.parity_channels.catalog import metadata
from app.parity_channels.policy import COLUMNS
from app.parity_channels.policy import RIGHTS as CHANNEL_RIGHTS
from app.sql_profile import SqlProfileStore
from app.sql_target import HOST, _quoted
from tools.es_schema_catalog_v2 import snapshot
from tools.es_schema_migrate_v2 import identity
from tools.foundation_snapshot import sha

RIGHTS = {
    **CORE_RIGHTS,
    **CHANNEL_RIGHTS,
    "crm_channels.Audit": ("SELECT",),
    "crm_channels2.ProviderOperation": ("SELECT",),
}
for name in (
    "Role",
    "AccessUser",
    "Session",
    "Setting",
    "Secret",
    "Factor",
    "RecoveryCode",
    "Challenge",
    "Operation",
    "ChannelSetting",
    "BudgetUsage",
):
    RIGHTS["crm_access." + name] = ("SELECT", "INSERT", "UPDATE")
RIGHTS.update(
    {
        "crm_access.Institution": ("SELECT", "UPDATE"),
        "crm_access.Audit": ("SELECT", "INSERT"),
        "crm_access.SettingHistory": ("SELECT", "INSERT"),
        "crm_access.RateBucket": ("SELECT", "INSERT", "UPDATE", "DELETE"),
    }
)
RIGHTS["crm_channels2.WebhookEndpoint"] = ("SELECT", "INSERT", "UPDATE")
RIGHTS["crm_channels2.EndpointIntegration"] = ("SELECT", "INSERT", "UPDATE")
PERMISSIONS = ("SELECT", "INSERT", "UPDATE", "DELETE", "ALTER", "REFERENCES", "CONTROL")


def partition(ticket):
    if ticket.get("version") == "cbn-institutional-operations-p11-v1":
        from app.institutional.operations_policy import partition as operations_partition

        return operations_partition(ticket)
    if ticket.get('version') in {'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
        from app.institutional.learning_policy import partition as learning_partition
        return learning_partition(ticket)
    if ticket.get("version") in {'cbn-institutional-ads-p9-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
        from app.institutional.ads_policy import partition as ads_partition

        return ads_partition(ticket)
    if ticket.get("version") in {
        "cbn-institutional-ads-p9-v1",
        "cbn-institutional-campaign-p8-v1",
    'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
        from app.institutional.campaign_policy import partition as flow_partition

        return flow_partition(ticket)
    if ticket.get("version") in {
        "cbn-institutional-broadcast-p7-v1",
        "cbn-institutional-campaign-p8-v1",
        "cbn-institutional-ads-p9-v1",
    'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
        from app.institutional.broadcast_policy import partition as broadcast_partition

        return broadcast_partition(ticket)
    if ticket.get("version") == "cbn-institutional-knowledge-p6-v1":
        from app.institutional.knowledge_policy import partition as knowledge_partition

        return knowledge_partition(ticket)
    if ticket.get("version") in {
        "cbn-institutional-agents-p5-v1",
        "cbn-institutional-knowledge-p6-v1",
        "cbn-institutional-broadcast-p7-v1",
        "cbn-institutional-campaign-p8-v1",
        "cbn-institutional-ads-p9-v1",
    'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
        from app.institutional.agents_policy import partition as agents_partition

        return agents_partition(ticket)
    from tools.p2_es_migrations import release, seed_binding

    release(ticket.get("migration_manifest_sha256"))
    if ticket.get("version") == "cbn-institutional-channels-p4-v1":
        from app.institutional.channels_policy import partition as channels_partition

        seed_binding(ticket["seed"])
        if ticket["seed"]["institution"] != ticket["context"][0][1]:
            raise ValueError("P4ES_ticket_institution_binding")
        return channels_partition(ticket)
    if ticket.get("version") == "cbn-institutional-spanish-p3-v1":
        from app.institutional.workspace_policy import partition as workspace_partition

        seed_binding(ticket["seed"])
        if ticket["seed"]["institution"] != ticket["context"][0][1]:
            raise ValueError("P3ES_ticket_institution_binding")
        return workspace_partition(ticket)
    mapping = layout()
    seed_binding(ticket["seed"])
    if ticket["seed"]["institution"] != ticket["context"][0][1]:
        raise ValueError("P2ES_ticket_institution_binding")
    tables = set(mapping["tables"].values()) | set(mapping["academic_tables"])
    if (
        ticket.get("version") != VERSION
        or ticket.get("scope") != "isolated_institutional_spanish"
        or ticket.get("table_map") != mapping["tables"]
        or len(ticket.get("tables", [])) != 138
        or set(ticket["tables"]) != tables
        or ticket.get("academic_tables") != mapping["academic_tables"]
    ):
        raise ValueError("P2ES_ticket_partition")
    return mapping


def load(directory):
    directory = Path(directory)
    if not directory.is_absolute():
        raise ValueError("P2ES_absolute_profile_required")
    value = SqlProfileStore(directory / "runtime").load()
    if value is None:
        raise ValueError("P2ES_profile_required")
    raw = (directory / "ticket.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != value["review"]["ticket_sha256"]:
        raise ValueError("P2ES_ticket_binding")
    ticket, review = json.loads(raw), value["review"]
    partition(ticket)
    if (
        time.time() >= ticket["expires_at"]
        or hashlib.sha256(review["session_token"].encode()).hexdigest()
        != ticket["session_sha256"]
    ):
        raise ValueError("P2ES_profile_expiry_or_session_key")
    secret_key = base64.b64decode(review["secrets_key"], validate=True)
    if (
        len(secret_key) != 32
        or hashlib.sha256(secret_key).hexdigest() != ticket["secret_key_sha256"]
    ):
        raise ValueError("P2ES_secret_key_binding")
    settings = SimpleNamespace(
        connection=value["connection"], review=review, ticket=ticket
    )
    connection_string(settings)
    return settings


def connection_string(settings):
    c = settings.connection
    target, login = TARGET, principal
    if settings.ticket.get("version") == "cbn-institutional-agents-p5-v1":
        from app.institutional.agents_policy import TARGET as target
        from app.institutional.agents_policy import principal as login
    if settings.ticket.get("version") == "cbn-institutional-channels-p4-v1":
        from app.institutional.channels_policy import TARGET as target
        from app.institutional.channels_policy import principal as login
    if settings.ticket.get("version") == "cbn-institutional-spanish-p3-v1":
        from app.institutional.workspace_policy import TARGET as target
        from app.institutional.workspace_policy import principal as login
    if settings.ticket.get("version") == "cbn-institutional-knowledge-p6-v1":
        from app.institutional.knowledge_policy import TARGET as target
        from app.institutional.knowledge_policy import principal as login
    if settings.ticket.get("version") in {
        "cbn-institutional-broadcast-p7-v1",
        "cbn-institutional-campaign-p8-v1",
        "cbn-institutional-ads-p9-v1",
    'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
        from app.institutional.broadcast_policy import TARGET as target
        from app.institutional.broadcast_policy import principal as login
    if settings.ticket.get("version") in {
        "cbn-institutional-ads-p9-v1",
        "cbn-institutional-campaign-p8-v1",
    'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
        from app.institutional.campaign_policy import (
            TARGET as target,
        )
        from app.institutional.campaign_policy import (
            principal as login,
        )
    if settings.ticket.get("version") in {'cbn-institutional-ads-p9-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
        from app.institutional.ads_policy import TARGET as target
        from app.institutional.ads_policy import principal as login
    if settings.ticket.get('version') in {'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
        from app.institutional.learning_policy import TARGET as target, principal as login
    if settings.ticket.get("version") == "cbn-institutional-operations-p11-v1":
        from app.institutional.operations_policy import TARGET as target, principal as login
    if (
        not target.fullmatch(c["database"])
        or c["database"] != settings.ticket["identity"]["database"]
        or c["username"] != login(c["database"])
        or not HOST.fullmatch(c["server"])
        or type(c["port"]) is not int
        or not 1 <= c["port"] <= 65535
        or c["certificate_hostname"] != "localhost"
    ):
        raise ValueError("P2ES_transport_boundary")
    return (
        ("DRIVER={ODBC Driver 18 for SQL Server};SERVER=tcp:")
        + c["server"]
        + ","
        + str(c["port"])
        + ";DATABASE="
        + _quoted(c["database"])
        + ";UID="
        + _quoted(c["username"])
        + ";PWD="
        + _quoted(c["password"])
        + (
            ";Encrypt=Yes;TrustServerCertificate=No"
            ";HostnameInCertificate=localhost;APP=C"
            "BN Institutional Spanish;"
        )
    )


def qualified_shape(cursor):
    return sha({"model": snapshot(cursor), "catalog": metadata(cursor)})


def verify(cursor, settings):
    ticket, c = settings.ticket, settings.connection
    if time.time() >= ticket["expires_at"]:
        raise ValueError("P2ES_profile_expired")
    mapping = partition(ticket)
    if identity(cursor) != ticket["identity"] or (
        ticket["identity"]["engine"],
        ticket["identity"]["compatibility"],
    ) != (15, 150):
        raise ValueError("P2ES_identity_drift")
    expected_rights = RIGHTS
    login = principal
    if ticket.get("version") in {
        "cbn-institutional-spanish-p3-v1",
        "cbn-institutional-channels-p4-v1",
        "cbn-institutional-agents-p5-v1",
        "cbn-institutional-knowledge-p6-v1",
        "cbn-institutional-broadcast-p7-v1",
        "cbn-institutional-campaign-p8-v1",
        "cbn-institutional-ads-p9-v1",
    'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
        from app.institutional.workspace_policy import principal as login
        from app.institutional.workspace_policy import rights

        expected_rights = rights(RIGHTS)
        row = cursor.execute(
            (
                "SELECT ManifestSha256,TargetDatabase,S"
                "tatus,ParentJournalSha256 FROM dbo.CRM"
                "TrabajoMigracion WHERE UnitId='P3ES-00"
                "1'"
            )
        ).fetchone()
        if row is None or tuple(row) != (
            ticket["workspace_release_sha256"],
            ticket.get("workspace_migration_origin", c["database"]),
            "COMMITTED",
            ticket["parent_journal_sha256"],
        ):
            raise ValueError("P3ES_workspace_history_drift")
        if ticket.get("workspace_profile_revision", 1) >= 2:
            from app.institutional.workspace_policy import history_digest

            if history_digest(cursor) != ticket.get("workspace_history_sha256"):
                raise ValueError("P3ES_workspace_history_content_drift")
    column_policy = COLUMNS
    if ticket.get("version") in {
        "cbn-institutional-channels-p4-v1",
        "cbn-institutional-agents-p5-v1",
        "cbn-institutional-knowledge-p6-v1",
        "cbn-institutional-broadcast-p7-v1",
        "cbn-institutional-campaign-p8-v1",
        "cbn-institutional-ads-p9-v1",
    'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
        from app.institutional import channels_policy as operations

        login = operations.principal
        expected_rights = operations.rights(RIGHTS)
        column_policy = operations.columns(COLUMNS)
        row = cursor.execute(
            (
                "SELECT ManifestSha256,TargetDatabase,P"
                "arentHistorySha256,Status FROM dbo.CRM"
                "CanalOperacionMigracion WHERE UnitId='"
                "P4ES-001'"
            )
        ).fetchone()
        if row is None or tuple(row) != (
            ticket["channels_release_sha256"],
            ticket.get("channels_migration_origin", c["database"]),
            ticket["channels_parent_history_sha256"],
            "COMMITTED",
        ):
            raise ValueError("P4ES_channels_history_drift")
        if (
            operations.history_digest(cursor) != ticket["channels_history_sha256"]
            or operations.parent_digest(cursor)
            != ticket["channels_parent_history_sha256"]
        ):
            raise ValueError("P4ES_channels_history_content_drift")
    if ticket.get("version") != "cbn-institutional-operations-p11-v1" and (ticket.get("version") in {
        "cbn-institutional-agents-p5-v1",
        "cbn-institutional-knowledge-p6-v1",
        "cbn-institutional-broadcast-p7-v1",
        "cbn-institutional-campaign-p8-v1",
        "cbn-institutional-ads-p9-v1",
    'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}):
        from app.institutional import agents_policy

        agents_policy.verify(cursor, ticket)
        expected_rights = agents_policy.rights(RIGHTS)
        column_policy = agents_policy.columns(COLUMNS)
        login = agents_policy.principal
    if ticket.get("version") == "cbn-institutional-knowledge-p6-v1":
        from app.institutional import knowledge_policy

        knowledge_policy.verify(cursor, ticket)
        expected_rights = knowledge_policy.rights(RIGHTS)
        column_policy = knowledge_policy.columns(COLUMNS)
        login = knowledge_policy.principal
    if ticket.get("version") != "cbn-institutional-operations-p11-v1" and (ticket.get("version") in {
        "cbn-institutional-broadcast-p7-v1",
        "cbn-institutional-campaign-p8-v1",
        "cbn-institutional-ads-p9-v1",
    'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}):
        from app.institutional import broadcast_policy

        broadcast_policy.verify(cursor, ticket)
        expected_rights = broadcast_policy.rights(RIGHTS)
        column_policy = broadcast_policy.columns(COLUMNS)
        login = broadcast_policy.principal
    if ticket.get("version") != "cbn-institutional-operations-p11-v1" and (ticket.get("version") in {
        "cbn-institutional-ads-p9-v1",
        "cbn-institutional-campaign-p8-v1",
    'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}):
        from app.institutional import campaign_policy

        campaign_policy.verify(cursor, ticket)
        expected_rights = campaign_policy.rights(RIGHTS)
        column_policy = campaign_policy.columns(COLUMNS)
        login = campaign_policy.principal
    if ticket.get("version") != "cbn-institutional-operations-p11-v1" and (ticket.get("version") in {'cbn-institutional-ads-p9-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}):
        from app.institutional import ads_policy

        ads_policy.verify(cursor, ticket)
        expected_rights = ads_policy.rights(RIGHTS)
        column_policy = ads_policy.columns(COLUMNS)
        login = ads_policy.principal
    if ticket.get("version") != "cbn-institutional-operations-p11-v1" and (ticket.get('version') in {'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}):
        from app.institutional import learning_policy
        learning_policy.verify(cursor,ticket)
        expected_rights=learning_policy.rights(RIGHTS)
        column_policy=learning_policy.columns(COLUMNS)
        login=learning_policy.principal
    # P11 verifies the complete P5-P10 parent chain once below. Its nested
    # verifiers retain every history/content check; P3/P4 checks above remain.
    # Older profiles keep their original path. No validation result is cached.
    if ticket.get("version") == "cbn-institutional-operations-p11-v1":
        from app.institutional import operations_policy

        operations_policy.verify(cursor, ticket)
        expected_rights = operations_policy.rights(RIGHTS)
        column_policy = operations_policy.columns(COLUMNS)
        login = operations_policy.principal
    user = login(c["database"])
    actual = cursor.execute(
        (
            "SELECT ORIGINAL_LOGIN(),SUSER_SNAME(),"
            "USER_NAME(),CONVERT(varchar(170),SUSER"
            "_SID(),2),IS_SRVROLEMEMBER('sysadmin')"
            ",HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE"
            "','CONTROL')"
        )
    ).fetchone()
    if (
        tuple(actual[:3]) != (user,) * 3
        or actual[3] != ticket["sid"]
        or tuple(actual[4:]) != (0, 0)
    ):
        raise ValueError("P2ES_effective_identity")
    for scope, expected in {
        "SERVER": {"CONNECT SQL", "VIEW ANY DATABASE"},
        "DATABASE": {
            "CONNECT",
            "VIEW DEFINITION",
            "VIEW ANY COLUMN ENCRYPTION KEY DEFINITION",
            "VIEW ANY COLUMN MASTER KEY DEFINITION",
        },
    }.items():
        if {
            r[0]
            for r in cursor.execute(
                ("SELECT permission_name FROM sys.fn_my_permissions(NULL,?)"), scope
            ).fetchall()
        } != expected:
            raise ValueError("P2ES_global_permissions")
    current = metadata(cursor)
    from tools.p9_catalog_snapshot import snapshot as p9_snapshot

    if (
        sha(current) != ticket["catalog_sha256"]
        or sha(
            {
                "model": p9_snapshot(cursor, raw_catalog=current)
                if ticket.get("version") in {'cbn-institutional-ads-p9-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}
                else snapshot(cursor),
                "catalog": current,
            }
        )
        != ticket["qualified_shape_sha256"]
        or journal_digest(cursor) != ticket["journal_sha256"]
    ):
        raise ValueError("P2ES_catalog_ACL_journal_drift")
    if tuple(
        cursor.execute(
            (
                "SELECT is_trustworthy_on,is_db_chainin"
                "g_on FROM sys.databases WHERE database"
                "_id=DB_ID()"
            )
        ).fetchone()
    ) != (0, 0):
        raise ValueError("P2ES_unsafe_chaining")
    context = mapping["tables"]["crm_channels2.Context"]
    if canonical_context(
        cursor.execute(
            (
                "SELECT ContextId,CONVERT(varchar(36),I"
                "nstitutionId),ContractVersion FROM "
            )
            + context
        ).fetchall()
    ) != canonical_context(ticket["context"]):
        raise ValueError("P2ES_institution_context_drift")
    from tools.p2_es_migrations import validate_data

    validate_data(cursor, 2, ticket["seed"])
    verify_object_permissions(cursor, mapping, ticket["tables"], expected_rights, column_policy)
    principals = {r["name"] for r in current["principals"]}
    if (
        principals != set(ticket["principals"])
        or "sa" not in ticket["protected_logins"]
    ):
        raise ValueError("P2ES_principal_partition")
    if ticket.get("version") in {'cbn-institutional-ads-p9-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
        # Evaluate every original impersonation check in bounded parameterized batches.
        for scope, actors in [
            ("USER", sorted(principals - {user})),
            ("LOGIN", ticket["protected_logins"]),
        ]:
            for start in range(0, len(actors), 200):
                batch = actors[start : start + 200]
                values = ",".join("(?)" for _ in batch)
                result = cursor.execute(
                    "SELECT v.name,HAS_PERMS_BY_NAME(v.name,?, 'IMPERSONATE') FROM (VALUES "
                    + values
                    + ") v(name)",
                    scope,
                    *batch,
                ).fetchall()
                if len(result) != len(batch) or any(value != 0 for _, value in result):
                    raise ValueError(
                        "P2ES_"
                        + ("user" if scope == "USER" else "login")
                        + "_impersonation"
                    )
    else:
        for actor in principals - {user}:
            if (
                cursor.execute(
                    ("SELECT HAS_PERMS_BY_NAME(?,'USER','IMPERSONATE')"), actor
                ).fetchval()
                != 0
            ):
                raise ValueError("P2ES_user_impersonation")
        for actor in ticket["protected_logins"]:
            if (
                cursor.execute(
                    ("SELECT HAS_PERMS_BY_NAME(?,'LOGIN','IMPERSONATE')"), actor
                ).fetchval()
                != 0
            ):
                raise ValueError("P2ES_login_impersonation")


def verify_object_permissions(
    cursor, mapping, tables, expected_rights, column_policy, *, deployment_mode=False
):
    rights = {
        mapping["tables"].get(table, table): set(right)
        for table, right in expected_rights.items()
    }
    columns = {
        mapping["tables"][table]: allowed for table, allowed in column_policy.items()
    }
    # One read evaluates every object permission; values are parameters, never SQL.
    table_values = ",".join("(?)" for _ in tables)
    permissions = (*PERMISSIONS, "TAKE OWNERSHIP") if deployment_mode else PERMISSIONS
    permission_values = ",".join("(?)" for _ in permissions)
    checks = cursor.execute(
        (
            "SELECT objects.name,permissions.name,H"
            "AS_PERMS_BY_NAME(objects.name,'OBJECT'"
            ",permissions.name) FROM (VALUES "
        )
        + table_values
        + ") objects(name) CROSS JOIN (VALUES "
        + permission_values
        + ") permissions(name)",
        *tables,
        *permissions,
    ).fetchall()
    for table, permission, actual_permission in checks:
        if table in columns and permission == "SELECT":
            continue
        if actual_permission != int(permission in rights.get(table, set())):
            raise ValueError("P2ES_effective_object_permission")
    if deployment_mode:
        no_update = [table for table in tables if "UPDATE" not in rights.get(table, set())]
        table_params = ",".join("(?)" for _ in no_update)
        if cursor.execute(
            "SELECT TOP(1) 1 FROM (VALUES " + table_params + ") v(name) "
            "JOIN sys.columns c ON c.object_id=OBJECT_ID(v.name) "
            "WHERE HAS_PERMS_BY_NAME(v.name,'OBJECT','UPDATE',c.name,'COLUMN')=1",
            *no_update,
        ).fetchone():
            raise ValueError("P2ES_column_update_permission")
    for table, allowed in columns.items():
        checks = cursor.execute(
            (
                "SELECT name,HAS_PERMS_BY_NAME(?,'OBJEC"
                "T','SELECT',name,'COLUMN') FROM sys.co"
                "lumns WHERE object_id=OBJECT_ID(?)"
            ),
            table,
            table,
        ).fetchall()
        if not checks or any(
            value != int(column in allowed) for column, value in checks
        ):
            raise ValueError("P2ES_column_permission")


@contextmanager
def transaction(
    settings, write=False, *, permission=None, anonymous=False, recent=False
):
    connection = None
    transport = getattr(settings, "deployment_transport", None)
    stage = "connect"
    try:
        connection = (
            deployment.open_connection(transport)
            if transport
            else pyodbc.connect(connection_string(settings), timeout=5, autocommit=False)
        )
        connection.timeout = 20
        cursor = connection.cursor()
        cursor.execute(
            (
                "SET XACT_ABORT ON;SET LOCK_TIMEOUT 500"
                "0;SET TRANSACTION ISOLATION LEVEL SERI"
                "ALIZABLE"
            )
        )
        stage = "locks"
        # Full P9 catalog guards can outlast the legacy 5s wait under parallel UI reads.
        # Keep both locks and verification; wait boundedly instead of returning false unavailability.
        lock_wait_ms = (
            15000
            if settings.ticket.get("version") in {'cbn-institutional-ads-p9-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}
            else 5000
        )
        for resource, mode in (
            ("crm.schema.migrate.v1", "Shared"),
            ("crm.local.commit", "Exclusive" if write else "Shared"),
        ):
            if (
                cursor.execute(
                    (
                        "DECLARE @r int;EXEC @r=sys.sp_getapplo"
                        "ck @Resource=?,@LockMode=?,@LockOwner="
                        "'Transaction',@LockTimeout=?;SELECT"
                        " @r"
                    ),
                    resource,
                    mode,
                    lock_wait_ms,
                ).fetchval()
                < 0
            ):
                raise ValueError("P2ES_transaction_lock")
            if transport and resource == "crm.schema.migrate.v1":
                # Writes never edit the SQL catalog or migration journals.
                # Validate them under the schema lock before competing for the
                # commit lock. Keep mutable-data checks and writes serialized.
                stage = "verify_schema"
                deployment.verify_schema_and_permissions(cursor, settings)
                stage = "locks"
        stage = "verify"
        if transport:
            deployment.verify_data(cursor, settings)
        else:
            verify(cursor, settings)
        mapped = Cursor(cursor, settings.ticket["table_map"])
        if not anonymous:
            from app.institutional.auth import authorize

            authority = request_authority.get()
            if authority is None:
                raise ValueError("P2ES_request_session_required")
            authorize(
                mapped,
                settings,
                authority,
                permission or authority["permission"],
                recent=recent,
            )
        stage = "body"
        yield mapped
        stage = "commit"
        connection.commit()
    except (pyodbc.Error, ValueError, OSError, KeyError, TypeError) as failure:
        if transport:
            logging.getLogger(__name__).warning(
                "Deployment SQL guard stage=%s reason=%s",
                stage,
                str(failure) if isinstance(failure, deployment.DeploymentError) else "redacted",
            )
        elif (
            getattr(settings, "ticket", {}).get("version") in {'cbn-institutional-ads-p9-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}
        ):
            tag = (
                "lock"
                if isinstance(failure, ValueError)
                and str(failure) == "P2ES_transaction_lock"
                else "validation_or_storage"
            )
            logging.getLogger(__name__).warning(
                "SQL guard stage=%s kind=%s tag=%s reason=%s",
                stage,
                type(failure).__name__,
                tag,
                str(failure) if isinstance(failure, ValueError) and re.fullmatch(r"P[0-9]{1,2}ES_[A-Za-z0-9_]{1,80}", str(failure)) else "redacted",
            )

        if connection:
            with suppress(pyodbc.Error):
                connection.rollback()
        raise HTTPException(503, "general_storage_unavailable") from None
    except BaseException:
        if connection:
            with suppress(pyodbc.Error):
                connection.rollback()
        raise
    finally:
        if connection:
            with suppress(pyodbc.Error):
                connection.close()
