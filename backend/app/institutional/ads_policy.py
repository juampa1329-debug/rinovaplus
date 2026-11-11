"""P9 additive extension; v1 release and populated prototypes remain verifiable."""

import hashlib
import json

from app.institutional import ads_policy_v1 as base
from tools.foundation_snapshot import sha

VERSION, TARGET, EXTRA = base.VERSION, base.TARGET, base.EXTRA
PACKAGE = base.PACKAGE.parent / "cbn_ads_operations_v2"
principal, layout, rights, columns, parent_digest, history_digest = (
    base.principal,
    base.layout,
    base.rights,
    base.columns,
    base.parent_digest,
    base.history_digest,
)


def release():
    raw = (PACKAGE / "release.json").read_bytes()
    value = json.loads(raw)
    if value["base_release_sha256"] != base.release():
        raise ValueError("P9ES_base_release_changed")
    for name, h in value["files"].items():
        if hashlib.sha256((PACKAGE / name).read_bytes()).hexdigest() != h:
            raise ValueError("P9ES_extension_input_changed")
    return hashlib.sha256(raw).hexdigest()


def partition(ticket):
    if ticket.get("ads_schema_revision", 1) == 1:
        return base.partition(ticket)
    if (
        ticket["ads_schema_revision"] != 2
        or ticket["ads_release_sha256"] != release()
        or ticket["ads_base_release_sha256"] != base.release()
    ):
        raise ValueError("P9ES_extension_partition")
    return base.partition(dict(ticket, ads_release_sha256=base.release()))


def base_history_digest(c):
    names = [
        "UnitId",
        "ManifestSha256",
        "TargetDatabase",
        "ParentHistorySha256",
        "Status",
        "StartedAt",
        "CommittedAt",
    ]
    data = c.execute(
        "SELECT "
        + ",".join("CONVERT(varbinary(max)," + n + ")" for n in names)
        + " FROM dbo.CRMPublicidadMigracion WHERE UnitId='P9ES-001'"
    ).fetchall()
    return sha(
        [[bytes(v).hex() if v is not None else None for v in row] for row in data]
    )


def verify(c, ticket):
    if ticket.get("ads_schema_revision", 1) == 1:
        return base.verify(c, ticket)
    base.parent.verify(c, ticket)
    for unit, expected in [
        (
            "P9ES-001",
            (
                base.release(),
                ticket["ads_migration_origin"],
                ticket["ads_parent_history_sha256"],
                "COMMITTED",
            ),
        ),
        (
            "P9ES-002",
            (
                release(),
                ticket["ads_migration_origin"],
                ticket["ads_base_history_sha256"],
                "COMMITTED",
            ),
        ),
    ]:
        row = c.execute(
            "SELECT ManifestSha256,TargetDatabase,ParentHistorySha256,Status FROM dbo.CRMPublicidadMigracion WHERE UnitId=?",
            unit,
        ).fetchone()
        if not row or tuple(row) != expected:
            raise ValueError("P9ES_extension_history_drift")
    if (
        base_history_digest(c) != ticket["ads_base_history_sha256"]
        or history_digest(c) != ticket["ads_history_sha256"]
        or parent_digest(c) != ticket["ads_parent_history_sha256"]
    ):
        raise ValueError("P9ES_extension_history_content_drift")
