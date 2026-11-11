"""Read-only deployment snapshots and proof against the fresh native checkpoint."""

import hashlib
import json
from pathlib import Path
from uuid import uuid4

from app.institutional import channels_policy as policy
from app.institutional.spanish import load
from app.institutional.workspace_policy import layout as parent_layout
from tools.foundation_snapshot import encode, quote_name, sha
from tools.p2_es_recovery import restore
from tools.p3_workspace_recovery import tables
from tools.prepare_p4_channels import WORK, admin, read, save, source
from tools.qualify_p4_storage import academic


def fingerprint(c, names):
    result = []
    for name in sorted(names):
        columns = [
            r[0]
            for r in c.execute(
                "SELECT name FROM sys.columns "
                "WHERE object_id=OBJECT_ID(?) ORDER BY column_id",
                name,
            ).fetchall()
        ]
        values = c.execute(
            "SELECT "
            + ",".join("CONVERT(varbinary(max)," + quote_name(v) + ")" for v in columns)
            + " FROM "
            + ".".join(map(quote_name, name.split(".")))
        ).fetchall()
        result.append(
            {
                "table": name,
                "rows": len(values),
                "sha256": hashlib.sha256(
                    b"".join(
                        sorted(hashlib.sha256(encode(list(v))).digest() for v in values)
                    )
                ).hexdigest(),
            }
        )
    return {
        "tables": len(result),
        "sha256": sha(result),
        "rows": sum(v["rows"] for v in result),
    }


def main(action):
    final = load(Path(read(WORK / "final-profile.json")["directory"]))
    if action == "preservation":
        checkpoint = read(WORK / "final-checkpoint.json")
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
        mapping = parent_layout()["tables"]
        volatile = {
            "crm_access." + v
            for v in [
                "Session",
                "Challenge",
                "RecoveryCode",
                "Factor",
                "RateBucket",
                "Operation",
                "Audit",
            ]
        }
        names = {value for logical, value in mapping.items() if logical not in volatile}
        with admin(name, readonly=True) as connection:
            native, native_academic = (
                fingerprint(connection.cursor(), names),
                academic(connection.cursor()),
            )
        parent = source()
        with admin(parent.connection["database"], readonly=True) as connection:
            current, source_academic = (
                fingerprint(connection.cursor(), names),
                academic(connection.cursor()),
            )
        with admin(final.connection["database"], readonly=True) as connection:
            final_academic = academic(connection.cursor())
        assert (
            native == current and native_academic == source_academic == final_academic
        )
        save(
            WORK / "preservation-result.json",
            {
                "status": "passed",
                "source_business_tables": native["tables"],
                "source_business_equal_fresh_native_checkpoint": True,
                "academic": native_academic,
                "source_and_final_academic_bytes_equal": True,
                "excluded_volatile_tables": sorted(volatile),
                "academic_writes": False,
                "older_database_fingerprints_claimed": False,
            },
        )
        print(
            json.dumps(
                {"source_business_preserved": True, "academic_bytes_equal": True}
            )
        )
        return
    names = set(policy.layout()["tables"].values()) | set(
        policy.layout()["academic_tables"]
    )
    mapping = policy.layout()["tables"]
    for logical in [
        "crm_access.Session",
        "crm_access.Challenge",
        "crm_access.RateBucket",
        "crm_access.Audit",
        "crm_access.Operation",
    ]:
        names.discard(mapping[logical])
    with admin(final.connection["database"], readonly=True) as connection:
        value = fingerprint(connection.cursor(), names)
    if action == "before":
        save(WORK / "restart-before.json", value)
    else:
        before = read(WORK / "restart-before.json")
        assert before == value
        save(
            WORK / "restart-result.json",
            {
                "status": "passed",
                "before": before,
                "after": value,
                "excluded": "session/challenge/rate/audit/operation",
                "persistent_media_volume": True,
            },
        )
    print(
        json.dumps(
            {"action": action, "business_tables": value["tables"], "passed": True}
        )
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["preservation", "before", "after"])
    main(parser.parse_args().action)
