"""Explicit one-time local replacement of the acceptance guide with Bety."""

import argparse
from copy import deepcopy
from uuid import UUID, uuid5

from app.main import app
from app.modules.agents.domain import StateWrite, digest, validate_hierarchy
from app.modules.agents.generation import provider_options, validate_selection
from app.modules.agents.service import check_available_scope, history, invalidate, load, packed, preflight, replay
from app.modules.ai.infrastructure.providers import AiError


BETY = "3e21137f-bb18-48ae-a1b7-21e0463de625"
PREVIOUS = "2c85911d-33fa-481a-bcc8-8085a49cd958"
PROGRAM = "0618918f-2b65-4f9c-a04a-91af7c9ee0ca"
CAPABILITIES = ["program.read", "sources.read", "conversation.reply", "human.handoff"]


def drain(cursor):
    while cursor.nextset():
        if cursor.description is not None:
            cursor.fetchall()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--operation-id", type=UUID, required=True)
    parser.add_argument("--bety-revision", type=int, required=True)
    parser.add_argument("--previous-revision", type=int, required=True)
    parser.add_argument("--program-revision", type=int, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    service = app.state.agents
    options = provider_options(service.ai)
    provider = next(item for item in options["providers"] if item["id"] == "gemini")
    if not provider["configured"]:
        raise AiError("agents_provider_not_configured", 409)
    revisions = {BETY: args.bety_revision, PREVIOUS: args.previous_revision, PROGRAM: args.program_revision}
    requests = {
        key: StateWrite(operation_id=uuid5(args.operation_id, key), revision=revision,
                        state="archived" if key == PREVIOUS else "active",
                        note="Sustitución autorizada del orientador por Bety; conservación del agente de programa.")
        for key, revision in revisions.items()
    }
    with service.transaction(True) as cursor:
        agents, stages = load(cursor)
        prior = {
            key: replay(cursor, "agent_state" if key == PREVIOUS else "agent_config", key, request)
            for key, request in requests.items()
        }
        if all(item[0] for item in prior.values()):
            print("Previously applied operation; no changes.")
            return
        if any(item[0] for item in prior.values()):
            raise AiError("agents_operation_conflict", 409)
        if any(key not in agents or agents[key]["revision"] != revision for key, revision in revisions.items()):
            raise AiError("agents_revision_conflict", 409)
        bety, previous, child = (agents[key] for key in (BETY, PREVIOUS, PROGRAM))
        if (bety["state"], bety["version"], bety["level"]) != ("archived", 2, "guide"):
            raise AiError("agents_maintenance_baseline_changed", 409)
        if (previous["state"], previous["version"], previous["level"]) != ("active", 2, "guide"):
            raise AiError("agents_maintenance_baseline_changed", 409)
        if (child["state"], child["version"], child["program_id"], child["parent_id"]) != ("active", 1, 331, PREVIOUS):
            raise AiError("agents_maintenance_baseline_changed", 409)
        if {item["id"] for item in agents.values() if item["parent_id"] == PREVIOUS} != {PROGRAM}:
            raise AiError("agents_maintenance_dependencies_changed", 409)
        baseline = digest(agents)
        proposed = deepcopy(agents)
        configured = proposed[BETY]["configuration"]
        original_instructions = configured["instructions"]
        if original_instructions.count("Eres July") != 1:
            raise AiError("agents_maintenance_identity_marker_changed", 409)
        configured.update(provider="gemini", primary_model="gemini-3.5-flash-lite", fallback_model="",
                          monthly_token_limit=250000, allow_reply=True, capabilities=CAPABILITIES,
                          instructions=original_instructions.replace("Eres July", "Eres Bety", 1))
        configured["channels"] = list(dict.fromkeys([*configured.get("channels", []), "local"]))
        proposed[BETY].update(state="active", enabled=True, version=3, revision=bety["revision"] + 1, approved_version=3)
        proposed[PREVIOUS].update(state="archived", enabled=False, revision=previous["revision"] + 1)
        proposed[PROGRAM].update(parent_id=BETY, version=child["version"] + 1,
                                 revision=child["revision"] + 1, approved_version=child["version"] + 1)
        validate_selection(configured, options, bety["configuration"])
        for key in (BETY, PROGRAM):
            validate_hierarchy(proposed[key], proposed, stages)
            check_available_scope(proposed[key], proposed)
            check = preflight(cursor, proposed[key], proposed, stages)
            if not check["ready"]:
                raise AiError(check["checks"][0], 409)
        if proposed[PROGRAM]["configuration"] != child["configuration"] or proposed[PREVIOUS]["configuration"] != previous["configuration"]:
            raise AiError("agents_maintenance_configuration_changed", 409)
        for field in ("objectives", "rules", "tone"):
            if configured.get(field) != bety["configuration"].get(field):
                raise AiError("agents_maintenance_configuration_changed", 409)
        # Reacquire the shared commit fence after read-only preflight work.
        locks = cursor.execute("DECLARE @a int,@b int; EXEC @a=sys.sp_getapplock @Resource=N'crm.ai.settings',@LockMode='Exclusive',@LockOwner='Transaction',@LockTimeout=3000; EXEC @b=sys.sp_getapplock @Resource=N'crm.local.commit',@LockMode='Exclusive',@LockOwner='Transaction',@LockTimeout=3000; SELECT @a,@b").fetchall()
        drain(cursor)
        if len(locks) != 1 or any(value < 0 for value in locks[0]):
            raise AiError("admissions_storage_busy", 503)
        fresh, _ = load(cursor)
        if digest(fresh) != baseline:
            raise AiError("agents_revision_conflict", 409)
        if not args.apply:
            print("Preflight ready; no profile, history or transport changes.")
            return
        cursor.execute("SET NOCOUNT ON; UPDATE crm_agents.Profile SET State='archived',Revision=Revision+1,UpdatedAt=SYSUTCDATETIME() WHERE AgentId=?; UPDATE crm_inbox.Agent SET Enabled=0 WHERE AgentId=?", PREVIOUS, PREVIOUS)
        drain(cursor)
        cursor.execute("UPDATE crm_agents.Profile SET State='active',Document=?,Version=3,ApprovedVersion=3,Revision=Revision+1,UpdatedAt=SYSUTCDATETIME() WHERE AgentId=?; UPDATE crm_inbox.Agent SET Enabled=1 WHERE AgentId=?", packed(configured), BETY, BETY)
        drain(cursor)
        cursor.execute("UPDATE crm_agents.Profile SET ParentId=?,Version=Version+1,ApprovedVersion=Version+1,Revision=Revision+1,UpdatedAt=SYSUTCDATETIME() WHERE AgentId=?", BETY, PROGRAM)
        drain(cursor)
        for key in (PREVIOUS, BETY, PROGRAM):
            history(cursor, "agent_state" if key == PREVIOUS else "agent_config", key, requests[key], prior[key][1], proposed[key])
            drain(cursor)
        invalidate(cursor)
        drain(cursor)
        actual, _ = load(cursor)
        if any(actual[key] != proposed[key] for key in revisions):
            raise AiError("agents_maintenance_readback_conflict", 503)
    print("Applied atomically: Bety active v3; previous guide archived; program preserved under Bety.")


if __name__ == "__main__":
    main()
