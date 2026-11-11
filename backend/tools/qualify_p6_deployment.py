"""Read-only final preservation and restart checks, with explicit snapshots."""

from pathlib import Path
import json
from app.institutional.spanish import load
from app.institutional import knowledge_policy as agents_policy, agents_policy as channels_policy
from tools.prepare_p6_knowledge import WORK, source, admin, read, save
from tools.qualify_p4_deployment import fingerprint
from tools.qualify_p4_storage import academic


def preservation():
    parent = source()
    final = load(Path(read(WORK / "final-profile.json")["directory"]))
    snapshot = read(WORK / "final-source-snapshot.json")
    with admin(parent.connection["database"], readonly=True) as connection:
        business = fingerprint(connection.cursor(), snapshot["names"])
        academics = academic(connection.cursor())
    assert business == snapshot["business"] and academics == snapshot["academic"], (
        "P5 source changed since native backup"
    )
    changed_demo = {
        "crm_agents.Profile",
        "crm_agents.Stage",
        "crm_agents.History",
        "crm_inbox.Agent",
        "crm_ai.KnowledgeDocument",
        "crm_ai.KnowledgeChunk",
        "crm_ai.KnowledgeTerm",
        "crm_agents.SourceScope",
    }
    mapping = channels_policy.layout()["tables"]
    stable = set(snapshot["names"]) - {mapping[n] for n in changed_demo}
    with admin(parent.connection["database"], readonly=True) as connection:
        expected = fingerprint(connection.cursor(), stable)
        from app.institutional.spanish_bindings import Cursor
        c=Cursor(connection.cursor(),mapping)
        assert c.execute("SELECT COUNT(*) FROM crm_ai.KnowledgeDocument").fetchval()==0
        states=[tuple(r) for r in c.execute("SELECT AgentId,State FROM crm_agents.Profile ORDER BY AgentId").fetchall()]
    with admin(final.connection["database"], readonly=True) as connection:
        actual = fingerprint(connection.cursor(), stable)
        final_academics = academic(connection.cursor())
        c=Cursor(connection.cursor(),final.ticket["table_map"])
        assert [tuple(r) for r in c.execute("SELECT AgentId,State FROM crm_agents.Profile ORDER BY AgentId").fetchall()]==states
        expected_docs={v['id'] for v in read(WORK/'demo-result.json')['records'] if v['kind']=='document'}
        assert {str(r[0]).lower() for r in c.execute("SELECT DocumentId FROM crm_ai.KnowledgeDocument").fetchall()}==expected_docs
    assert actual == expected and final_academics == academics
    save(
        WORK / "preservation-result.json",
        {
            "status": "passed",
            "P5_business_matches_fresh_backup": True,
            "P5_agent_states_preserved": True,
            "new_source_rows_match_only_explicit_demo_records": True,
            "stable_business_tables": len(stable),
            "stable_business_fingerprint": actual,
            "academic_tables": academics["tables"],
            "academic_rows": academics["rows"],
            "academic_fingerprints_equal": True,
            "SIIE_Windows_requeried": False,
            "previous_profiles_redirected": False,
            "academic_writes": False,
        },
    )
    print(
        json.dumps(
            {
                "preserved_business_tables": len(stable),
                "academic_tables": academics["tables"],
                "source_matches_fresh_backup": True,
            }
        )
    )


def restart(action):
    final = load(Path(read(WORK / "final-profile.json")["directory"]))
    mapping = agents_policy.layout()
    volatile = {
        mapping["tables"]["crm_access." + n] for n in ["Session", "RateBucket", "Audit"]
    }
    stable = (
        set(mapping["tables"].values()) | set(mapping["academic_tables"])
    ) - volatile
    with admin(final.connection["database"], readonly=True) as connection:
        value = fingerprint(connection.cursor(), stable)
    if action == "capture":
        save(WORK / "restart-before.json", value)
    else:
        assert value == read(WORK / "restart-before.json"), (
            "restart changed business bytes"
        )
        save(
            WORK / "restart-result.json",
            {
                "status": "passed",
                "stable_tables": len(stable),
                "fingerprint": value,
                "provider_calls": 0,
                "academic_writes": False,
            },
        )
    print("P6 restart " + action + " passed")


if __name__ == "__main__":
    import sys

    preservation() if sys.argv[1] == "preservation" else restart(sys.argv[1])
