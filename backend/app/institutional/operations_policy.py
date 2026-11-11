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
