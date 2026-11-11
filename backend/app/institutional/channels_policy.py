"""Closed P4 SQL authority; existing P2/P3 contracts remain strict."""

import hashlib
import json
import re
from pathlib import Path

from app.institutional import workspace_policy as parent

VERSION = "cbn-institutional-channels-p4-v1"
TARGET = re.compile(r"CBN_P4ES_(TRIAL|FAULT|RECOVERY)_20261026_([0-9a-f]{8})\Z")
PACKAGE = Path(__file__).resolve().parents[2] / "migrations/cbn_channels_operations_v1"
EXTRA = {
    "crm_channels4.Configuration": "dbo.CRMCanalOperacionConfiguracion",
    "crm_channels4.MediaAsset": "dbo.CRMCanalOperacionArchivo",
    "crm_channels4.Journal": "dbo.CRMCanalOperacionMigracion",
}


def principal(database):
    match = TARGET.fullmatch(database)
    if not match:
        raise ValueError("P4ES_isolated_target_required")
    return "cbn_channels_ops_" + match[2]


def layout():
    value = parent.layout()
    return dict(value, tables={**value["tables"], **EXTRA})


def rights(base):
    result = parent.rights(base)
    for name in [
        "Application",
        "Integration",
        "ProviderOperation",
        "ProviderAsset",
        "OAuthSession",
        "SecretVersion",
        "WebhookEndpoint",
        "EndpointIntegration",
        "WebhookReceipt",
        "WebhookEvent",
        "ExternalIdentity",
        "ExternalMessage",
        "SocialComment",
        "SendJob",
        "MessageRoute",
        "ConversationProfile",
        "ConversationControl",
        "TikTokPolicy",
        "QuotaBucket",
        "QuotaReservation",
    ]:
        result["crm_channels2." + name] = ("SELECT", "INSERT", "UPDATE")
    result["crm_channels2.VerificationEvidence"] = ("SELECT", "INSERT")
    result["crm_channels4.Configuration"] = ("SELECT", "INSERT", "UPDATE")
    result["crm_channels4.MediaAsset"] = ("SELECT", "INSERT", "UPDATE")
    result["crm_channels4.Journal"] = ("SELECT",)
    return result


def columns(base):
    # Operational records require their encrypted bodies, leases and bindings.
    # The runtime role still has no access to historical migration bindings.
    return {
        key: value
        for key, value in base.items()
        if key == "crm_channels2.LegacyBinding"
    }


def release():
    raw = (PACKAGE / "release.json").read_bytes()
    value = json.loads(raw)
    if value["parent_release_sha256"] != parent.release():
        raise ValueError("P4ES_parent_release_changed")
    for name, digest in value["files"].items():
        if hashlib.sha256((PACKAGE / name).read_bytes()).hexdigest() != digest:
            raise ValueError("P4ES_release_input_changed")
    return hashlib.sha256(raw).hexdigest()


def partition(ticket):
    mapping = layout()
    origin = ticket.get("channels_migration_origin", ticket["identity"]["database"])
    if not TARGET.fullmatch(origin):
        raise ValueError("P4ES_history_origin")
    lineage = ticket.get("channels_lineage", [])
    if origin != ticket["identity"]["database"] and (
        not lineage
        or lineage[0]["source_database"] != origin
        or lineage[-1]["source_database"] != ticket["restored_from"]["source_database"]
    ):
        raise ValueError("P4ES_native_lineage")
    if (
        ticket.get("version") != VERSION
        or ticket.get("scope") != "isolated_institutional_channels_operations"
        or not TARGET.fullmatch(ticket["identity"]["database"])
        or ticket.get("channels_release_sha256") != release()
        or ticket.get("table_map") != mapping["tables"]
        or set(ticket.get("tables", []))
        != set(mapping["tables"].values()) | set(mapping["academic_tables"])
        or ticket.get("academic_tables") != mapping["academic_tables"]
        or not re.fullmatch(r"[0-9a-f]{64}", ticket.get("channels_history_sha256", ""))
    ):
        raise ValueError("P4ES_ticket_partition")
    prior = parent.layout()
    parent.partition(
        dict(
            ticket,
            version=parent.VERSION,
            scope="isolated_institutional_workspace",
            table_map=prior["tables"],
            tables=sorted(
                set(prior["tables"].values()) | set(prior["academic_tables"])
            ),
        )
    )
    return mapping


def parent_digest(cursor):
    from app.es_schema_profile import journal_digest
    from tools.foundation_snapshot import sha

    return sha(
        {"baseline": journal_digest(cursor), "workspace": parent.history_digest(cursor)}
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
    values = cursor.execute(
        "SELECT "
        + ",".join("CONVERT(varbinary(max)," + name + ")" for name in names)
        + " FROM dbo.CRMCanalOperacionMigracion ORDER BY UnitId"
    ).fetchall()
    return sha(
        [
            [bytes(value).hex() if value is not None else None for value in row]
            for row in values
        ]
    )
