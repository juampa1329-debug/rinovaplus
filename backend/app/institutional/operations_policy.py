"""Closed local P11 profile; schema and migration journals remain P10's."""

import hashlib
import json
import re
from pathlib import Path

from app.institutional import learning_policy as parent

VERSION = "cbn-institutional-operations-p11-v1"
TARGET = re.compile(r"CBN_P11ES_(TRIAL|FAULT|RECOVERY)_20261028_([0-9a-f]{8})\Z")
PACKAGE = (
    Path(__file__).resolve().parents[2] / "operations/cbn_institutional_operations_v1"
)
layout, rights, columns = parent.layout, parent.rights, parent.columns


class DeploymentError(ValueError):
    """Only constant messages and allowlisted catalog identifiers reach the log."""


def principal(database):
    match = TARGET.fullmatch(database)
    if not match:
        raise ValueError("P11ES_isolated_target_required")
    return "cbn_ops11_" + match[2]


def release():
    raw = (PACKAGE / "release.json").read_bytes()
    value = json.loads(raw)
    if value["parent_release_sha256"] != parent.release():
        raise ValueError("P11ES_parent_release_changed")
    for name, digest in value["files"].items():
        if (
            name != "contract.json"
            or hashlib.sha256((PACKAGE / name).read_bytes()).hexdigest() != digest
        ):
            raise ValueError("P11ES_release_input_changed")
    return hashlib.sha256(raw).hexdigest()


def partition(ticket):
    mapping = layout()
    lineage = ticket.get("operations_lineage", [])
    origin = ticket.get("operations_origin")
    if (
        ticket.get("version") != VERSION
        or ticket.get("scope") != "isolated_institutional_operations"
        or not TARGET.fullmatch(ticket["identity"]["database"])
        or ticket.get("operations_release_sha256") != release()
        or not parent.TARGET.fullmatch(str(origin))
        or not lineage
        or lineage[0]["source_database"] != origin
        or lineage[-1]["source_database"] != ticket["restored_from"]["source_database"]
        or any(
            not (
                TARGET.fullmatch(row["source_database"])
                or parent.TARGET.fullmatch(row["source_database"])
            )
            for row in lineage
        )
    ):
        raise ValueError("P11ES_ticket_partition")
    # Preserve every P10 journal/origin check using its original migration identity.
    parent.partition(
        dict(
            ticket,
            version=parent.VERSION,
            scope="isolated_institutional_learning",
            identity={**ticket["identity"], "database": origin},
        )
    )
    if (
        ticket["table_map"] != mapping["tables"]
        or set(ticket["tables"])
        != set(mapping["tables"].values()) | set(mapping["academic_tables"])
        or ticket["academic_tables"] != mapping["academic_tables"]
    ):
        raise ValueError("P11ES_table_partition")
    return mapping


def verify(cursor, ticket):
    partition(ticket)
    parent.verify(cursor, ticket)


def _deployment_index_model(model):
    # SQL Server treats a fill factor of 0 and 100 identically.
    return {
        **model,
        "indexes": [
            {**index, "fill_factor": 0} if index["fill_factor"] == 100 else index
            for index in model["indexes"]
        ],
    }


# Deployment only needs the structural sections and the object inventory.
# The foundation reader also captures permissions and other rehearsal evidence.
_DEPLOYMENT_CATALOG = {
    "columns": """SELECT s.name AS schema_name,o.name AS table_name,c.name,
          c.column_id AS ordinal,TYPE_NAME(c.user_type_id) AS type_name,
          c.max_length,c.precision,c.scale,c.is_nullable,c.is_identity,c.is_computed,
          c.collation_name,cc.definition AS computed_definition,cc.is_persisted,
          dc.name AS default_name,dc.definition AS default_definition,
          CONVERT(nvarchar(100),ic.seed_value) AS identity_seed,
          CONVERT(nvarchar(100),ic.increment_value) AS identity_increment
          FROM sys.columns c JOIN sys.objects o ON o.object_id=c.object_id
          JOIN sys.schemas s ON s.schema_id=o.schema_id
          LEFT JOIN sys.identity_columns ic ON ic.object_id=c.object_id
            AND ic.column_id=c.column_id
          LEFT JOIN sys.computed_columns cc ON cc.object_id=c.object_id
            AND cc.column_id=c.column_id
          LEFT JOIN sys.default_constraints dc ON dc.object_id=c.default_object_id
          WHERE o.is_ms_shipped=0 ORDER BY s.name,o.name,c.column_id""",
    "indexes": """SELECT s.name AS schema_name,o.name AS table_name,i.name,
          i.type_desc,i.is_unique,i.is_primary_key,i.is_unique_constraint,
          i.is_disabled,i.has_filter,i.filter_definition,i.fill_factor,i.is_padded,
          i.ignore_dup_key,i.allow_row_locks,i.allow_page_locks,
          c.name AS column_name,ic.key_ordinal,ic.is_descending_key,
          ic.is_included_column,
          ic.index_column_id
          FROM sys.indexes i JOIN sys.objects o ON o.object_id=i.object_id
          JOIN sys.schemas s ON s.schema_id=o.schema_id
          LEFT JOIN sys.index_columns ic ON ic.object_id=i.object_id
            AND ic.index_id=i.index_id
          LEFT JOIN sys.columns c ON c.object_id=ic.object_id
            AND c.column_id=ic.column_id
          WHERE o.is_ms_shipped=0
          ORDER BY s.name,o.name,i.name,ic.index_column_id""",
    "checks": """SELECT s.name AS schema_name,
          OBJECT_NAME(c.parent_object_id) AS table_name,
          c.name,c.definition,c.is_disabled,c.is_not_trusted,c.is_not_for_replication
          FROM sys.check_constraints c JOIN sys.schemas s ON s.schema_id=c.schema_id
          ORDER BY s.name,c.name""",
    "foreign_keys": """SELECT s.name AS schema_name,
          OBJECT_NAME(f.parent_object_id) AS table_name,
          f.name,COL_NAME(k.parent_object_id,k.parent_column_id) AS column_name,
          OBJECT_SCHEMA_NAME(k.referenced_object_id) AS target_schema,
          OBJECT_NAME(k.referenced_object_id) AS target_table,
          COL_NAME(k.referenced_object_id,k.referenced_column_id) AS target_column,
          k.constraint_column_id AS ordinal,f.delete_referential_action,
          f.update_referential_action,f.is_disabled,f.is_not_trusted,
          f.is_not_for_replication
          FROM sys.foreign_keys f JOIN sys.foreign_key_columns k
            ON k.constraint_object_id=f.object_id
          JOIN sys.schemas s ON s.schema_id=f.schema_id
          ORDER BY s.name,f.name,k.constraint_column_id""",
    "catalog": """SELECT s.name AS schema_name,o.name,o.type,
          OBJECT_NAME(o.parent_object_id) AS parent_name
          FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
          WHERE o.is_ms_shipped=0""",
}


def _read_catalog_batch(cursor):
    cursor.execute(";\n".join(_DEPLOYMENT_CATALOG.values()))
    catalog = {}
    for section in _DEPLOYMENT_CATALOG:
        if cursor.description is None:
            raise DeploymentError("sql_catalog_read_failed")
        columns = [column[0] for column in cursor.description]
        rows = []
        while chunk := cursor.fetchmany(1000):
            rows.extend(dict(zip(columns, row, strict=True)) for row in chunk)
            if len(rows) > 200000:
                raise DeploymentError("sql_catalog_read_failed")
        catalog[section] = rows
        more = cursor.nextset()
        if bool(more) != (section != "catalog"):
            raise DeploymentError("sql_catalog_read_failed")
    return catalog


def deployment_catalog(cursor, *, inventory_only=False):
    if cursor.execute(
        "SELECT HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','VIEW DEFINITION')"
    ).fetchval() != 1:
        raise DeploymentError("sql_metadata_permissions: grant database VIEW DEFINITION for a complete inventory")
    mapping = layout()
    managed = set(mapping["tables"].values())
    rows = cursor.execute(
        "SELECT s.name,t.name FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id "
        "WHERE t.is_ms_shipped=0"
    ).fetchall()
    found = {f"{schema}.{table}" for schema, table in rows}
    missing = sorted((managed | set(mapping["academic_tables"])) - found)
    if missing:
        raise DeploymentError("sql_tables_missing: " + ", ".join(missing))
    if inventory_only:
        return mapping

    # Only CRM schema is frozen. SIIE remains owned by the institution.
    from tools.p9_catalog_snapshot import compare, snapshot

    raw = _read_catalog_batch(cursor)
    expected = json.loads((parent.PACKAGE / "expected-model.json").read_text(encoding="utf-8"))
    model = {
        key: [
            row for row in rows
            if f"{row['schema']}.{row['name'] if key == 'tables' else row['table']}" in managed
        ]
        for key, rows in expected.items()
    }
    actual = snapshot(cursor, raw_catalog=raw, only_tables=managed)
    drift = compare(
        _deployment_index_model(actual), _deployment_index_model(model)
    )["differing_sections"]
    if drift:
        raise DeploymentError("sql_crm_schema_drift: " + ", ".join(drift))

    # A trigger or inbound cascade could mutate protected rows via otherwise
    # legitimate CRM DML. This check covers CRM tables and extra SIIE tables.
    if any(
        f"{row['schema_name']}.{row['parent_name']}" in managed and row["type"].strip() == "TR"
        for row in raw["catalog"]
    ) or any(
        f"{row['target_schema']}.{row['target_table']}" in managed
        and f"{row['schema_name']}.{row['table_name']}" not in managed
        and (row["delete_referential_action"] or row["update_referential_action"])
        for row in raw["foreign_keys"]
    ):
        raise DeploymentError("sql_unreviewed_trigger_or_cascade")
    return mapping


def deployment_authority(cursor, login, mapping):
    from app.es_schema_profile import journal_digest
    from app.institutional.spanish import RIGHTS, verify_object_permissions
    from app.institutional.spanish_bindings import canonical_context
    from app.parity_channels.policy import COLUMNS
    from tools.p2_es_migrations import validate_data

    actor = cursor.execute(
        """SELECT ORIGINAL_LOGIN(),SUSER_SNAME(),USER_NAME(),
           CONVERT(varchar(170),SUSER_SID(),2),
           CONVERT(varchar(170),dp.sid,2),IS_SRVROLEMEMBER('sysadmin'),
           d.is_trustworthy_on,d.is_db_chaining_on
           FROM sys.databases d CROSS JOIN sys.database_principals dp
           WHERE d.database_id=DB_ID() AND dp.principal_id=USER_ID()"""
    ).fetchone()
    if (
        not actor or actor[0] != login or actor[1] != login or actor[2] in {"dbo", "guest"}
        or not actor[3] or actor[3] != actor[4] or tuple(actor[5:]) != (0, 0, 0)
    ):
        raise DeploymentError("sql_runtime_identity_or_privilege: use a dedicated SQL login and database user")
    for scope, allowed, required in (
        ("SERVER", {"CONNECT SQL", "VIEW ANY DATABASE"}, {"CONNECT SQL"}),
        (
            "DATABASE",
            {"CONNECT", "VIEW DEFINITION", "VIEW ANY COLUMN ENCRYPTION KEY DEFINITION",
             "VIEW ANY COLUMN MASTER KEY DEFINITION"},
            {"CONNECT", "VIEW DEFINITION"},
        ),
    ):
        permissions = {
            row[0] for row in cursor.execute(
                "SELECT permission_name FROM sys.fn_my_permissions(NULL,?)", scope
            ).fetchall()
        }
        if not required <= permissions <= allowed:
            raise DeploymentError("sql_runtime_global_permissions: remove broad database or server grants")

    try:
        verify_object_permissions(
            cursor, mapping, list(mapping["tables"].values()), rights(RIGHTS), columns(COLUMNS),
            deployment_mode=True,
        )
    except ValueError:
        raise DeploymentError("sql_crm_object_permissions: match the object and column grants in the CRM policy") from None
    # Check individual columns as a column GRANT can bypass an object-level DENY.
    names = sorted(mapping["tables"].values())
    values = ",".join("(?)" for _ in names)
    outside = (
        " FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id"
        " CROSS APPLY (VALUES(QUOTENAME(s.name)+N'.'+QUOTENAME(o.name),s.name+N'.'+o.name)) n(quoted,name)"
        " WHERE o.is_ms_shipped=0 AND o.parent_object_id=0 AND NOT EXISTS"
        " (SELECT 1 FROM (VALUES " + values + ") allowed(name)"
        " WHERE allowed.name COLLATE Latin1_General_100_BIN2=n.name COLLATE Latin1_General_100_BIN2)"
    )
    outside_access = cursor.execute(
        "SELECT TOP (1) 1" + outside +
        """ AND (EXISTS(SELECT 1 FROM (VALUES('SELECT'),('INSERT'),('UPDATE'),('DELETE'),
            ('ALTER'),('REFERENCES'),('CONTROL'),('EXECUTE'),('TAKE OWNERSHIP')) p(name)
            WHERE HAS_PERMS_BY_NAME(n.quoted,'OBJECT',p.name)=1)
            OR (o.type IN ('U','V') AND EXISTS(SELECT 1 FROM sys.columns c WHERE c.object_id=o.object_id
                AND (HAS_PERMS_BY_NAME(n.quoted,'OBJECT','SELECT',c.name,'COLUMN')=1
                  OR HAS_PERMS_BY_NAME(n.quoted,'OBJECT','UPDATE',c.name,'COLUMN')=1))))""",
        *names,
    ).fetchone()
    if outside_access:
        raise DeploymentError("sql_runtime_access_outside_crm: remove grants on SIIE and unrelated objects")
    if cursor.execute(
        """SELECT TOP (1) 1 FROM sys.database_principals
           WHERE principal_id<>USER_ID() AND HAS_PERMS_BY_NAME(name,'USER','IMPERSONATE')=1
           UNION ALL SELECT TOP (1) 1 FROM sys.server_principals
           WHERE sid<>SUSER_SID() AND HAS_PERMS_BY_NAME(name,'LOGIN','IMPERSONATE')=1"""
    ).fetchone():
        raise DeploymentError("sql_runtime_impersonation_permission")

    context = canonical_context(cursor.execute(
        "SELECT ContextId,InstitutionId,ContractVersion FROM dbo.CRMCanalInstitucionalContexto"
    ).fetchall())
    if len(context) != 1 or context[0][0] != 1 or context[0][2] != "CBN-channels-parity-v1":
        raise DeploymentError("sql_institution_context_invalid")
    bootstrap = cursor.execute(
        "SELECT BootstrapHash,InitializedAt FROM dbo.CRMAccesoInstitucion WHERE InstitutionId=?",
        context[0][1],
    ).fetchone()
    if not bootstrap or not bootstrap[1]:
        raise DeploymentError("sql_institution_not_initialized: provision the institutional owner before deployment")
    validate_data(cursor, 2, {"institution": context[0][1]})
    return {
        "sid": actor[3],
        "context": context,
        "history_sha256": deployment_history(cursor, journal_digest(cursor), mapping["tables"]),
    }


def deployment_history(cursor, baseline_digest, table_map):
    from app.institutional import (
        ads_policy, agents_policy, broadcast_policy, campaign_policy, channels_policy,
        knowledge_policy, workspace_policy,
    )
    from tools.es_schema_migrate_v2 import PACKAGE as baseline_package
    from tools.foundation_snapshot import sha
    from tools.p2_es_migrations import PACKAGE as access_package

    for package in (baseline_package, access_package):
        raw = (package / "release.json").read_bytes()
        manifest = json.loads(raw)
        release_hash = hashlib.sha256(raw).hexdigest()
        for unit in manifest["units"]:
            row = cursor.execute(
                """SELECT ReleaseId,ManifestSha256,UnitSha256 FROM crm_meta.MigrationJournal
                   WHERE SuccessKey=? AND UnitId=? AND EventKind='COMMITTED'""",
                unit["id"], unit["id"],
            ).fetchone()
            if not row or (row[0], bytes(row[1]).hex(), bytes(row[2]).hex()) != (
                manifest["version"], release_hash, unit["sha256"]
            ):
                raise DeploymentError("sql_crm_journal_invalid: " + unit["id"])

    stages = (
        ("P3", "crm_workspace.Journal", workspace_policy),
        ("P4", "crm_channels4.Journal", channels_policy),
        ("P5", "crm_agents5.Journal", agents_policy),
        ("P6", "crm_knowledge6.Journal", knowledge_policy),
        ("P7", "crm_broadcast7.Journal", broadcast_policy),
        ("P8", "crm_campaign8.Journal", campaign_policy),
        ("P9", "crm_ads9.Journal", ads_policy),
        ("P10", "crm_learning10.Journal", parent),
    )
    # Read the state and the canonical digest inputs together. Every batch
    # runs under the caller's transaction and the same SQL application locks.
    journal_queries = []
    for phase, journal, _ in stages:
        parent_column = "ParentJournalSha256" if phase == "P3" else "ParentHistorySha256"
        digest_columns = (
            "UnitId", "ManifestSha256", "TargetDatabase", parent_column,
            "Status", "StartedAt", "CommittedAt",
        )
        binary = ",".join(f"CONVERT(varbinary(max),{name})" for name in digest_columns)
        journal_queries.append(
            f"SELECT UnitId,ManifestSha256,{parent_column},Status,{binary} "
            f"FROM {table_map[journal]} ORDER BY UnitId"
        )
    cursor.execute(";\n".join(journal_queries))
    history = {"baseline": baseline_digest}
    prior = baseline_digest
    for phase, _, policy in stages:
        rows = cursor.fetchmany(3)
        payload = [
            [bytes(value).hex() if value is not None else None for value in row[4:]]
            for row in rows
        ]
        units = [(phase + "ES-001", policy.release(), prior)]
        if phase == "P9":
            base_rows = [data for row, data in zip(rows, payload) if row[0] == "P9ES-001"]
            units = [
                ("P9ES-001", ads_policy.base.release(), prior),
                ("P9ES-002", policy.release(), sha(base_rows)),
            ]
        if [tuple(row[:4]) for row in rows] != [(*unit, "COMMITTED") for unit in units]:
            raise DeploymentError("sql_crm_journal_invalid: " + phase)
        history[phase] = sha(payload)
        if bool(cursor.nextset()) != (phase != "P10"):
            raise DeploymentError("sql_crm_journal_invalid: " + phase)
        prior = sha({phase: history[phase], "parents": prior})
        if phase == "P3":
            prior = sha({"baseline": baseline_digest, "workspace": history[phase]})
    return sha(history)
