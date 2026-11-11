"""Closed P5 authority on a native copy; historical profiles stay unchanged."""

import hashlib
import json
import re
from pathlib import Path

from app.institutional import agents_policy as parent

VERSION = "cbn-institutional-knowledge-p6-v1"
TARGET = re.compile(r"CBN_P6ES_(TRIAL|FAULT|RECOVERY)_20261027_([0-9a-f]{8})\Z")
PACKAGE = Path(__file__).resolve().parents[2] / "migrations/cbn_knowledge_operations_v1"
EXTRA = {
    "crm_knowledge6.Journal": "dbo.CRMConocimientoOperacionMigracion",
    "crm_knowledge6.Record": "dbo.CRMConocimientoRegistro",
    "crm_knowledge6.Version": "dbo.CRMConocimientoVersion",
}


def principal(database):
    match = TARGET.fullmatch(database)
    if not match:
        raise ValueError("P6ES_isolated_target_required")
    return "cbn_knowledge_ops_" + match[2]


def layout():
    base = parent.layout()
    return dict(base, tables={**base["tables"], **EXTRA})


def rights(base):
    result = parent.rights(base)
    result["crm_ai.KnowledgeDocument"] = ("SELECT", "INSERT", "UPDATE")
    for name in ["KnowledgeChunk", "KnowledgeTerm"]:
        result["crm_ai." + name] = ("SELECT", "INSERT", "DELETE")
    result["crm_knowledge6.Record"] = ("SELECT", "INSERT", "UPDATE")
    result["crm_knowledge6.Version"] = ("SELECT", "INSERT")
    result["crm_knowledge6.Journal"] = ("SELECT",)
    return result


def columns(base):
    return parent.columns(base)


def release():
    raw = (PACKAGE / "release.json").read_bytes()
    value = json.loads(raw)
    if value["parent_release_sha256"] != parent.release():
        raise ValueError("P6ES_parent_release_changed")
    for name, expected in value["files"].items():
        if hashlib.sha256((PACKAGE / name).read_bytes()).hexdigest() != expected:
            raise ValueError("P6ES_release_input_changed")
    return hashlib.sha256(raw).hexdigest()


def partition(ticket):
    from tools.p2_es_migrations import release as baseline_release
    from tools.p2_es_migrations import seed_binding

    baseline_release(ticket.get("migration_manifest_sha256"))
    seed_binding(ticket["seed"])
    if ticket["seed"]["institution"] != ticket["context"][0][1]:
        raise ValueError("P6ES_institution_binding")
    mapping = layout()
    origin = ticket.get("knowledge_migration_origin", ticket["identity"]["database"])
    if (
        ticket.get("version") != VERSION
        or ticket.get("scope") != "isolated_institutional_knowledge"
        or not TARGET.fullmatch(ticket["identity"]["database"])
        or not TARGET.fullmatch(origin)
        or ticket.get("knowledge_release_sha256") != release()
        or ticket.get("table_map") != mapping["tables"]
        or set(ticket.get("tables", []))
        != set(mapping["tables"].values()) | set(mapping["academic_tables"])
        or ticket.get("academic_tables") != mapping["academic_tables"]
    ):
        raise ValueError("P6ES_ticket_partition")
    if origin != ticket["identity"]["database"]:
        lineage = ticket.get("knowledge_lineage", [])
        if (
            not lineage
            or lineage[0]["source_database"] != origin
            or lineage[-1]["source_database"]
            != ticket["restored_from"]["source_database"]
        ):
            raise ValueError("P6ES_native_lineage")
    previous = parent.layout()
    # Validate the preserved P4 contract against its recorded native origin.
    # No journal rows, historical targets or parent tickets are rewritten.
    parent.partition(
        dict(
            ticket,
            version=parent.VERSION,
            scope="isolated_institutional_agents",
            identity={
                **ticket["identity"],
                "database": ticket["agents_migration_origin"],
            },
            table_map=previous["tables"],
            tables=sorted(
                set(previous["tables"].values()) | set(previous["academic_tables"])
            ),
        )
    )
    return mapping


def parent_digest(cursor):
    from tools.foundation_snapshot import sha

    return sha(
        {"P5": parent.history_digest(cursor), "parents": parent.parent_digest(cursor)}
    )


def history_digest(cursor):
    from tools.foundation_snapshot import sha

    names = [
        "UnitId",
        "ManifestSha256",
        "TargetDatabase",
        "ParentHistorySha256",
        "Status",
        "StartedAt",
        "CommittedAt",
    ]
    rows = cursor.execute(
        "SELECT "
        + ",".join("CONVERT(varbinary(max)," + n + ")" for n in names)
        + " FROM dbo.CRMConocimientoOperacionMigracion ORDER BY UnitId"
    ).fetchall()
    return sha(
        [[bytes(v).hex() if v is not None else None for v in row] for row in rows]
    )


def verify(cursor, ticket):
    parent.verify(cursor, ticket)
    row = cursor.execute(
        (
    (
    'SELECT ManifestSha256,TargetDatabase,ParentHistorySha256,S'
    'tatus FROM dbo.CRMConocimientoOperacionMigracion WHERE Uni'
    "tId='P6ES-001'"
)
)
    ).fetchone()
    if (
        not row
        or tuple(row)
        != (
            ticket["knowledge_release_sha256"],
            ticket["knowledge_migration_origin"],
            ticket["knowledge_parent_history_sha256"],
            "COMMITTED",
        )
        or history_digest(cursor) != ticket["knowledge_history_sha256"]
        or parent_digest(cursor) != ticket["knowledge_parent_history_sha256"]
    ):
        raise ValueError("P6ES_history_drift")
