"Closed P3 partition and additional rights; no academic authority is granted."

import hashlib
import json
import re
from pathlib import Path

from app.institutional.spanish_bindings import layout as parent_layout

VERSION = "cbn-institutional-spanish-p3-v1"
TARGET = re.compile(("CBN_P3ES_(TRIAL|FAULT|RECOVERY)_20261026_([0-9a-f]{8})\\Z"))
PACKAGE = Path(__file__).resolve().parents[2] / "migrations/cbn_workspace_spanish_v1"
EXTRA = {
    f"crm_workspace.{key}": "dbo." + value
    for key, value in {
        "State": "CRMTrabajoEstado",
        "Assignment": "CRMTrabajoAsignacion",
        "Task": "CRMTrabajoTarea",
        "Note": "CRMTrabajoNota",
        "Merge": "CRMTrabajoUnificacion",
        "Journal": "CRMTrabajoMigracion",
    }.items()
}


def principal(database):
    match = TARGET.fullmatch(database)
    if not match:
        raise ValueError("P3ES_isolated_target_required")
    return "cbn_workspace_es_" + match[2]


def layout():
    parent = parent_layout()
    return dict(parent, tables={**parent["tables"], **EXTRA})


def rights(parent):
    result = dict(parent)
    for table in [
        "crm_channels.ConversationControl",
        "crm_channels.ConversationProfile",
    ]:
        result[table] = ("SELECT", "INSERT", "UPDATE")
    for table in [
        "crm_workspace.State",
        "crm_workspace.Assignment",
        "crm_workspace.Task",
        "crm_workspace.Merge",
    ]:
        result[table] = ("SELECT", "INSERT", "UPDATE")
    result["crm_workspace.Note"] = ("SELECT", "INSERT")
    result["crm_workspace.Journal"] = ("SELECT",)
    for table in [
        "crm_marketing.ChurnAssessment",
        "crm_marketing.EvaluationRun",
        "crm_identity.Profile",
        "crm_merge.MergeCase",
        "crm_channels.MessageRoute",
        "crm_channels.outbound_queue",
        "crm_channels.ExternalIdentity",
        "crm_inbox.SlaPolicy",
    ]:
        result[table] = ("SELECT",)
    # Existing bot routes are cancelled transactionally on human takeover.
    result["crm_channels.outbound_queue"] = ("SELECT", "UPDATE")
    result["crm_inbox.SlaPolicy"] = ("SELECT", "INSERT", "UPDATE")
    return result


def release():
    raw = (PACKAGE / "release.json").read_bytes()
    value = json.loads(raw)
    for name, digest in value["files"].items():
        if hashlib.sha256((PACKAGE / name).read_bytes()).hexdigest() != digest:
            raise ValueError("P3ES_release_input_changed")
    return hashlib.sha256(raw).hexdigest()


def partition(ticket):
    mapping = layout()
    revision = ticket.get("workspace_profile_revision", 1)
    if type(revision) is not int or revision not in {1, 2}:
        raise ValueError("P3ES_profile_revision")
    if revision == 2 and not re.fullmatch(
        r"[0-9a-f]{64}", ticket.get("workspace_history_sha256", "")
    ):
        raise ValueError("P3ES_history_pin_required")
    origin = ticket.get("workspace_migration_origin", ticket["identity"]["database"])
    if not TARGET.fullmatch(origin):
        raise ValueError("P3ES_history_origin")
    lineage = ticket.get("workspace_lineage", [])
    if origin != ticket["identity"]["database"] and (
        not lineage
        or lineage[0]["source_database"] != origin
        or lineage[-1]["source_database"] != ticket["restored_from"]["source_database"]
    ):
        raise ValueError("P3ES_native_lineage")
    if (
        ticket.get("version") != VERSION
        or ticket.get("scope") != "isolated_institutional_workspace"
        or ticket.get("workspace_release_sha256") != release()
        or ticket.get("table_map") != mapping["tables"]
        or set(ticket.get("tables", []))
        != set(mapping["tables"].values()) | set(mapping["academic_tables"])
        or ticket.get("academic_tables") != mapping["academic_tables"]
    ):
        raise ValueError("P3ES_ticket_partition")
    return mapping


def history_digest(cursor):
    from tools.foundation_snapshot import sha

    fields = (
        "UnitId,ManifestSha256,TargetDatabase,Par"
        "entJournalSha256,Status,StartedAt,Commit"
        "tedAt"
    ).split(",")
    rows = cursor.execute(
        "SELECT "
        + ",".join("CONVERT(varbinary(max)," + name + ")" for name in fields)
        + " FROM dbo.CRMTrabajoMigracion ORDER BY UnitId"
    ).fetchall()
    return sha(
        [
            [bytes(value).hex() if value is not None else None for value in row]
            for row in rows
        ]
    )
