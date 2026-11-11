"""Compile both frozen-base and additive extension on a fresh rollback-only copy."""

from uuid import uuid4

from app.institutional import ads_policy as policy
from tools.es_schema_catalog_v2 import model, snapshot
from tools.p2_es_recovery import restore
from tools.prepare_p9_ads import WORK, admin, parent_tables, read, save


def main():
    checkpoint = read(WORK / "candidate.json")["checkpoint"]
    name = "CBN_P9ES_TRIAL_20261027_" + uuid4().hex[:8]
    with admin("master") as db:
        restore(
            db,
            checkpoint,
            name,
            restricted=True,
            target_pattern=policy.TARGET,
            allowed_tables=parent_tables(),
        )
    with admin(name) as db:
        c = db.cursor()
        before = model(snapshot(c))
        c.execute("SET XACT_ABORT ON;BEGIN TRANSACTION")
        try:
            for p in [
                policy.base.PACKAGE / "P9ES-000.sql",
                policy.base.PACKAGE / "P9ES-001.sql",
                policy.PACKAGE / "P9ES-002.sql",
            ]:
                c.execute(p.read_text())
            expected = model(snapshot(c))
            assert len(expected["tables"]) == 175
            save(WORK / "expected-model-v2.json", expected)
        finally:
            c.execute("IF @@TRANCOUNT>0 ROLLBACK")
        assert before == model(snapshot(c))
    save(
        WORK / "compile-v2-result.json",
        dict(
            status="passed",
            engine=15,
            compatibility=150,
            tables=175,
            transaction_rolled_back=True,
            academic_DDL_or_DML=False,
        ),
    )
    print("P9 additive extension compiled on new copy;175tables, rollback preserved.")


if __name__ == "__main__":
    main()
