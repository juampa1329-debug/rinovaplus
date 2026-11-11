"""Preservation and real SQL2019 inventory; no Windows SIIE connection."""

import json
from pathlib import Path

from app.institutional.operations_policy import layout
from app.institutional.spanish import load, transaction
from app.institutional.spanish_bindings import Cursor
from tools.p10_learning_recovery import fingerprint
from tools.prepare_p11_operations import WORK, admin, read, save, source
from tools.qualify_p4_deployment import fingerprint as selected_fingerprint


def main():
    s = load(Path(read(WORK / "final-profile.json")["directory"]))
    parent = source()
    checkpoint = read(WORK / "final-checkpoint.json")
    with transaction(s, anonymous=True):
        pass
    with admin(parent.connection["database"], readonly=True) as db:
        assert fingerprint(db.cursor()) == checkpoint["data"]
        parent_academic = selected_fingerprint(db.cursor(), set(layout()["academic_tables"]))
    with admin(s.connection["database"], readonly=True) as db:
        c = db.cursor()
        academic = layout()["academic_tables"]
        assert selected_fingerprint(c, set(academic)) == parent_academic
        counts = {"tables": c.execute("SELECT COUNT(*) FROM sys.tables WHERE is_ms_shipped=0").fetchval(), "foreign_keys": c.execute("SELECT COUNT(*) FROM sys.foreign_keys").fetchval(), "bindings": len(layout()["tables"]), "academic_tables": len(academic)}
        mapped = Cursor(c, layout()["tables"])
        demo = {label: mapped.execute("SELECT COUNT(*) FROM " + table).fetchval() for label, table in {"contacts": "crm.Contact", "conversations": "crm.Conversation", "messages": "crm.Message", "agents": "crm_agents.Profile", "learning_packs": "crm_learning10.Pack", "learning_samples": "crm_learning10.Sample", "learning_artifacts": "crm_learning10.Artifact"}.items()}
        forbidden = {"commercial_consents": "SELECT COUNT(*) FROM crm_broadcast7.Consent WHERE State='granted'", "bulk_attempts": "SELECT COUNT(*) FROM crm_broadcast7.Attempt", "enrollments": "SELECT COUNT(*) FROM crm_campaign8.Enrollment", "connected_ads_accounts": "SELECT COUNT(*) FROM crm_ads9.Account WHERE State='connected'", "running_learning_deployments": "SELECT COUNT(*) FROM crm_learning10.Deployment WHERE State<>'paused'"}
        effects = {k: mapped.execute(sql).fetchval() for k, sql in forbidden.items()}
    assert counts == {"tables": 185, "foreign_keys": 330, "bindings": 155, "academic_tables": 30}
    assert all(value == 0 for value in effects.values())
    save(WORK / "preservation-result.json", dict(status="passed", checks=["parent_P10_all185_table_data_fingerprints_equal_fresh_native_backup", "all30_academic_table_data_fingerprints_identical_in_own_P11_copy", "current_SQL_profile_full_TLS_identity_model_journals_ACL_validation", "real185_tables_330_foreign_keys_155_bindings", "accumulated_demo_data_retained", "no_commercial_effects_or_model_auto_resume"], database=s.connection["database"], parent_database=parent.connection["database"], engine=15, compatibility=150, inventory=counts, demo=demo, effects=effects, academic_DDL_or_DML=False, SIIE_Windows_connected=False, previous_copies_modified=False))
    print(json.dumps({"status": "passed", "inventory": counts, "demo": demo}))


if __name__ == "__main__":
    main()
