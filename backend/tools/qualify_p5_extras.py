"""Current archive/restore, task approval and profile ceilings on owned SQL."""

from pathlib import Path
from uuid import uuid4
import json
from app.institutional.api import create_app
from app.institutional.spanish import load
from app.institutional.spanish_bindings import Cursor
from tools.prepare_p5_agents import WORK, read, save, admin
from tools.qualify_p3_workspace import Browser


def main():
    settings = load(Path(read(WORK / "fixture-r3-profile.json")["directory"]))
    access = read(WORK / "fixture-r3-access.json")
    ids = read(WORK / "fixture-records.json")
    calls = []

    class Gateway:
        def __init__(self, keys):
            self.keys = keys
            self.hermes_base = ""
            self.transport = None

        async def generate(self, *args, **kw):
            calls.append(True)
            raise AssertionError("No provider IO permitted in ceiling negatives")

    b = Browser(create_app(settings, agent_gateway_factory=Gateway))
    b.login(access["email"], access["password"])
    checks = []

    def check(n, v=True):
        assert v, n
        checks.append(n)
        save(
            WORK / "extras-result.json",
            {"status": "in_progress", "checks": checks, "real_provider_calls": 0},
        )

    def api(path="", method="GET", body=None, expected=200):
        return b.request("/api/v1/agents" + path, method, body, expected).json()

    def mutate(revision, **kw):
        return dict(operation_id=str(uuid4()), revision=revision, **kw)

    def current(key):
        return next(a for a in api()["agents"] if a["id"] == key)

    def state(key, value, expected=200):
        return api(
            "/profiles/" + key + "/state",
            "POST",
            mutate(
                current(key)["revision"],
                state=value,
                note="Control de ciclo P5",
                confirmed=True,
            ),
            expected,
        )

    def write(key, config, expected=200):
        a = current(key)
        return api(
            "/profiles/" + key,
            "PUT",
            mutate(
                a["revision"],
                **{
                    k: a[k]
                    for k in ["name", "level", "parent_id", "program_id", "stage_id"]
                },
                configuration=config,
            ),
            expected,
        )

    def sql(query, *params):
        with admin(settings.connection["database"], readonly=True) as connection:
            return (
                Cursor(connection.cursor(), settings.ticket["table_map"])
                .execute(query, *params)
                .fetchall()
            )

    guide, program = ids["guide_id"], ids["program_agent_id"]
    child = next(a for a in api()["agents"] if a["parent_id"] == program)
    denied = state(program, "archived", 409)
    check(
        "parent_archive_requires_children_to_be_paused",
        denied["code"] == "agents_active_children_require_pause",
    )
    state(child["id"], "archived")
    check(
        "leaf_archives_without_deleting_profile",
        current(child["id"])["state"] == "archived",
    )
    denied = write(child["id"], child["configuration"], 409)
    check(
        "archived_configuration_is_read_only",
        denied["code"] == "agents_archived_read_only",
    )
    state(child["id"], "draft")
    state(program, "active")
    config = current(program)["configuration"]
    write(child["id"], config)
    check(
        "restored_draft_becomes_available_when_valid_configuration_is_saved",
        current(child["id"])["state"] == "active",
    )
    # A fresh action requires its own approval, separately from profile saving.
    original = current(program)["configuration"]
    root_original = current(guide)["configuration"]
    root = {
        **root_original,
        "capabilities": list(
            dict.fromkeys(root_original["capabilities"] + ["advisor.actions"])
        ),
        "allow_safe_actions": True,
    }
    write(guide, root)
    cfg = {
        **original,
        "capabilities": list(
            dict.fromkeys(original["capabilities"] + ["advisor.actions"])
        ),
        "allow_safe_actions": True,
    }
    write(program, cfg)
    conversation = str(
        sql(
            "SELECT TOP(1) a.ConversationId FROM crm_agents.Assignment a JOIN crm_agents.Context c ON c.ContextId=a.ContextId WHERE c.ProgramId=901"
        )[0][0]
    ).lower()
    before = sql("SELECT COUNT(*) FROM crm_workspace.Task")[0][0]
    action = mutate(
        current(program)["revision"],
        kind="followup_task",
        impact="medium",
        risk="medium",
        title="Seguimiento aprobado P5",
        context="Contexto controlado, sin cambios académicos",
        conversation_id=conversation,
    )
    api("/profiles/" + program + "/actions", "POST", action)
    execution = mutate(
        current(program)["revision"],
        action_id=action["operation_id"],
        decision="execute",
    )
    api("/profiles/" + program + "/actions/decision", "POST", execution, 409)
    check(
        "task_is_not_written_without_separate_action_approval",
        sql("SELECT COUNT(*) FROM crm_workspace.Task")[0][0] == before,
    )
    api(
        "/profiles/" + program + "/actions/decision",
        "POST",
        mutate(
            current(program)["revision"],
            action_id=action["operation_id"],
            decision="approve",
        ),
    )
    api("/profiles/" + program + "/actions/decision", "POST", execution)
    api("/profiles/" + program + "/actions/decision", "POST", execution)
    check(
        "approved_task_is_persisted_once_in_shared_CRM",
        sql("SELECT COUNT(*) FROM crm_workspace.Task")[0][0] == before + 1,
    )
    root = current(guide)["configuration"]
    write(guide, {**root, "monthly_usd_limit": 0.000001, "hard_stop": True})
    a = current(guide)
    result = api(
        "/simulate",
        "POST",
        dict(
            agent_id=guide,
            config_version=a["version"],
            question="No debe consumir",
            request_id=str(uuid4()),
            call_provider=True,
            acknowledge_consumption=True,
        ),
        409,
    )
    check(
        "profile_USD_hard_ceiling_denies_before_paid_IO",
        result["code"] in ["agents_budget_exhausted", "agents_cost_uncertain"]
        and not calls,
    )
    write(guide, root)
    denied = write(guide, {**root, "monthly_token_limit": 0}, 409)
    check(
        "zero_profile_token_budget_cannot_activate_execution",
        denied["code"] == "agents_incomplete_configuration" and not calls,
    )
    save(
        WORK / "extras-result.json",
        {
            "status": "passed",
            "checks": checks,
            "real_provider_calls": 0,
            "academic_writes": False,
        },
    )
    print(json.dumps({"passed": len(checks), "real_provider_calls": 0}))


if __name__ == "__main__":
    main()
