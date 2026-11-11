"""Closed P10 authority on a native copy; historical profiles stay unchanged."""

import hashlib
import json
import re
from pathlib import Path

from app.institutional import ads_policy as parent

VERSION = "cbn-institutional-learning-p10-v1"
TARGET = re.compile("CBN_P10ES_(TRIAL|FAULT|RECOVERY)_20261028_([0-9a-f]{8})\\Z")
PACKAGE = Path(__file__).resolve().parents[2] / "migrations/cbn_learning_operations_v1"
EXTRA = {
    "crm_learning10.Journal": "dbo.CRMAprendizajeMigracion",
    "crm_learning10.Pack": "dbo.CRMAprendizajePaquete",
    "crm_learning10.PackVersion": "dbo.CRMAprendizajePaqueteVersion",
    "crm_learning10.Grant": "dbo.CRMAprendizajeAutorizacion",
    "crm_learning10.Sample": "dbo.CRMAprendizajeMuestra",
    "crm_learning10.Dataset": "dbo.CRMAprendizajeConjunto",
    "crm_learning10.Artifact": "dbo.CRMAprendizajeArtefacto",
    "crm_learning10.Deployment": "dbo.CRMAprendizajeDespliegue",
    "crm_learning10.Prediction": "dbo.CRMAprendizajePrediccion",
    "crm_learning10.Event": "dbo.CRMAprendizajeEvento",
}


def principal(database):
    match = TARGET.fullmatch(database)
    if not match:
        raise ValueError("P10ES_isolated_target_required")
    return "cbn_learning_ops_" + match[2]


def layout():
    base = parent.layout()
    return dict(base, tables={**base["tables"], **EXTRA})


def rights(base):
    result = parent.rights(base)
    for name in ["Pack", "Grant", "Deployment"]:
        result["crm_learning10." + name] = ("SELECT", "INSERT", "UPDATE")
    for name in ["PackVersion", "Sample", "Dataset", "Artifact", "Prediction", "Event"]:
        result["crm_learning10." + name] = ("SELECT", "INSERT")
    result["crm_learning10.Journal"] = ("SELECT",)
    return result


def columns(base):
    return parent.columns(base)


def release():
    raw = (PACKAGE / "release.json").read_bytes()
    value = json.loads(raw)
    if value["parent_release_sha256"] != parent.release():
        raise ValueError("P10ES_parent_release_changed")
    for name, expected in value["files"].items():
        if hashlib.sha256((PACKAGE / name).read_bytes()).hexdigest() != expected:
            raise ValueError("P10ES_release_input_changed")
    return hashlib.sha256(raw).hexdigest()


def partition(ticket):
    from tools.p2_es_migrations import release as baseline_release
    from tools.p2_es_migrations import seed_binding

    baseline_release(ticket.get("migration_manifest_sha256"))
    seed_binding(ticket["seed"])
    if ticket["seed"]["institution"] != ticket["context"][0][1]:
        raise ValueError("P10ES_institution_binding")
    mapping = layout()
    origin = ticket.get("learning_migration_origin", ticket["identity"]["database"])
    if (
        ticket.get("version") != VERSION
        or ticket.get("scope") != "isolated_institutional_learning"
        or (not TARGET.fullmatch(ticket["identity"]["database"]))
        or (not TARGET.fullmatch(origin))
        or (ticket.get("learning_release_sha256") != release())
        or (ticket.get("table_map") != mapping["tables"])
        or (
            set(ticket.get("tables", []))
            != set(mapping["tables"].values()) | set(mapping["academic_tables"])
        )
        or (ticket.get("academic_tables") != mapping["academic_tables"])
    ):
        raise ValueError("P10ES_ticket_partition")
    if origin != ticket["identity"]["database"]:
        lineage = ticket.get("learning_lineage", [])
        if (
            not lineage
            or lineage[0]["source_database"] != origin
            or lineage[-1]["source_database"]
            != ticket["restored_from"]["source_database"]
        ):
            raise ValueError("P10ES_native_lineage")
    previous = parent.layout()
    parent.partition(
        dict(
            ticket,
            version=parent.VERSION,
            scope="isolated_institutional_ads",
            identity={
                **ticket["identity"],
                "database": ticket["ads_migration_origin"],
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
        {"P9": parent.history_digest(cursor), "parents": parent.parent_digest(cursor)}
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
        + ",".join(("CONVERT(varbinary(max)," + n + ")" for n in names))
        + " FROM dbo.CRMAprendizajeMigracion ORDER BY UnitId"
    ).fetchall()
    return sha(
        [[bytes(v).hex() if v is not None else None for v in row] for row in rows]
    )


def verify(cursor, ticket):
    parent.verify(cursor, ticket)
    row = cursor.execute(
        "SELECT ManifestSha256,TargetDatabase,ParentHistorySha256,Status FROM dbo.CRMAprendizajeMigracion WHERE UnitId='P10ES-001'"
    ).fetchone()
    if (
        not row
        or tuple(row)
        != (
            ticket["learning_release_sha256"],
            ticket["learning_migration_origin"],
            ticket["learning_parent_history_sha256"],
            "COMMITTED",
        )
        or history_digest(cursor) != ticket["learning_history_sha256"]
        or (parent_digest(cursor) != ticket["learning_parent_history_sha256"])
    ):
        raise ValueError("P10ES_history_drift")
