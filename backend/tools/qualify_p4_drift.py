"""Fail closed on additive drift in a new disposable native copy."""

import json
from uuid import uuid4

from app.institutional import channels_policy as policy
from tools.es_schema_migrate_v2 import identity
from tools.p2_es_recovery import restore
from tools.p3_workspace_recovery import tables
from tools.p4_channels_migrations import apply
from tools.prepare_p4_channels import WORK, admin, read, save
from tools.qualify_p4_storage import academic


def main():
    checkpoint = read(WORK / "candidate.json")["checkpoint"]
    name = "CBN_P4ES_FAULT_20261026_" + uuid4().hex[:8]
    with admin("master") as connection:
        restore(
            connection,
            checkpoint,
            name,
            restricted=True,
            target_pattern=policy.TARGET,
            allowed_tables=tables(),
        )
    with admin(name) as connection:
        c = connection.cursor()
        target, parent = identity(c), policy.parent_digest(c)
        apply(
            connection, target, approved_release=policy.release(), parent_journal=parent
        )
        before = academic(c)
        c.execute(
            "ALTER TABLE dbo.CRMCanalOperacionConfiguracion ADD OwnedDrift int NULL"
        )
        try:
            apply(
                connection,
                target,
                approved_release=policy.release(),
                parent_journal=parent,
            )
        except ValueError as error:
            reason = str(error)
            assert "drift" in reason.lower(), reason
        else:
            raise AssertionError("P4ES_drift_was_accepted")
        assert academic(c) == before
    save(
        WORK / "drift-result.json",
        {
            "status": "passed",
            "checks": ["additive_drift_rejected", "academic_bytes_unchanged"],
            "rejection": reason,
            "fault_copy": name,
        },
    )
    print(json.dumps({"passed": 2, "academic_writes": False}))


if __name__ == "__main__":
    main()
