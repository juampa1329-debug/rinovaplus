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
    from tools.foundation_snapshot import metadata, records
    from tools.p9_catalog_snapshot import compare, snapshot

    # Reuse the structure reader without the wider dependency-visibility
    # grants required by the signed rehearsal's complete ACL snapshot.
    sections = ("columns", "indexes", "checks", "foreign_keys")
    left, right = (metadata(cursor, managed=scope) for scope in (True, False))
    raw = {key: left[key] + right[key] for key in sections}
    raw["catalog"] = records(
        cursor,
        "SELECT s.name AS schema_name,o.name,o.type,OBJECT_NAME(o.parent_object_id) AS parent_name "
        "FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id WHERE o.is_ms_shipped=0",
    )
    expected = json.loads((parent.PACKAGE / "expected-model.json").read_text(encoding="utf-8"))
    model = {
        key: [
            row for row in rows
            if f"{row['schema']}.{row['name'] if key == 'tables' else row['table']}" in managed
        ]
        for key, rows in expected.items()
    }
    actual = snapshot(cursor, raw_catalog=raw, only_tables=managed)
    drift = compare(actual, model)["differing_sections"]
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
    history = {"baseline": baseline_digest}
    prior = baseline_digest
    for phase, journal, policy in stages:
        parent_column = "ParentJournalSha256" if phase == "P3" else "ParentHistorySha256"
        units = [(phase + "ES-001", policy.release(), prior)]
        if phase == "P9":
            units = [
                ("P9ES-001", ads_policy.base.release(), prior),
                ("P9ES-002", policy.release(), ads_policy.base_history_digest(cursor)),
            ]
        rows = cursor.execute(
            f"SELECT UnitId,ManifestSha256,{parent_column},Status FROM {table_map[journal]} ORDER BY UnitId"
        ).fetchall()
        if [tuple(row) for row in rows] != [(*unit, "COMMITTED") for unit in units]:
            raise DeploymentError("sql_crm_journal_invalid: " + phase)
        history[phase] = policy.history_digest(cursor)
        prior = sha({phase: history[phase], "parents": prior})
        if phase == "P3":
            prior = sha({"baseline": baseline_digest, "workspace": history[phase]})
    return sha(history)
