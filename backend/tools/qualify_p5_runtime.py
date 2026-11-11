"""Paid-effect semantics on owned SQL fixture, with a controlled gateway only."""

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

from app.institutional.api import create_app
from app.institutional.spanish import load
from app.institutional.spanish_bindings import Cursor
from app.modules.ai.infrastructure.providers import AiError
from tools.prepare_p5_agents import WORK, read, save, admin
from tools.qualify_p3_workspace import Browser


def main():
    settings = load(Path(read(WORK / "fixture-r3-profile.json")["directory"]))
    access = read(WORK / "fixture-r3-access.json")
    records = read(WORK / "fixture-records.json")
    calls = []
    entered = threading.Event()
    release = threading.Event()

    class Gateway:
        def __init__(self, keys):
            self.keys = keys
            self.hermes_base = ""
            self.transport = None
            self.last_usage = None
            self.last_response_metadata = {}

        async def generate(
            self,
            provider,
            model,
            config,
            system,
            messages,
            *,
            before_attempt=None,
            response_schema=None,
        ):
            if before_attempt:
                before_attempt()
            calls.append((provider, model))
            assert provider == "gemini" and model == "owned-controlled-model"
            text = messages[-1]["content"]
            if "CONTROLLED_WAIT" in text:
                entered.set()
                assert release.wait(40), "fixture wait expired"
            if "CONTROLLED_TIMEOUT" in text:
                raise AiError("provider_timeout", 504)
            self.last_usage = {"input": 31, "output": 19}
            self.last_response_metadata = {"finish_reason": "STOP"}
            return json.dumps(
                {
                    "answer": "Puedo ayudarte a revisar la información con el equipo de admisiones.",
                    "handoff": True,
                    "references": [],
                    "memory": [],
                }
            )

    app = create_app(settings, agent_gateway_factory=Gateway)
    b = Browser(app)
    b.login(access["email"], access["password"])
    checks = []

    def check(name, condition=True):
        assert condition, name
        checks.append(name)
        save(
            WORK / "runtime-result.json",
            {
                "status": "in_progress",
                "checks": checks,
                "controlled_calls": len(calls),
                "real_provider_calls": 0,
            },
        )

    def api(path="", method="GET", body=None, expected=200, browser=None):
        return (
            (browser or b)
            .request("/api/v1/agents" + path, method, body, expected)
            .json()
        )

    def edit_setting(section, **fields):
        current = b.request("settings/" + section).json()
        return b.request(
            "settings/" + section,
            "PUT",
            {
                "operation_id": str(uuid4()),
                "revision": current["revision"],
                "document": dict(current["document"], **fields),
            },
        ).json()

    def current(key):
        return next(a for a in api()["agents"] if a["id"] == key)

    def state(key, value):
        a = current(key)
        return api(
            "/profiles/" + key + "/state",
            "POST",
            {
                "operation_id": str(uuid4()),
                "revision": a["revision"],
                "state": value,
                "note": "Comprobación controlada P5",
                "confirmed": True,
            },
        )

    def simulate(key, question="Consulta controlada", **extra):
        a = current(key)
        return dict(
            agent_id=key,
            config_version=a["version"],
            program_id=a["program_id"],
            stage_id=a["stage_id"],
            question=question,
            request_id=str(uuid4()),
            call_provider=True,
            acknowledge_consumption=True,
            **extra,
        )

    def sql(query, *params):
        with admin(settings.connection["database"], readonly=True) as connection:
            return (
                Cursor(connection.cursor(), settings.ticket["table_map"])
                .execute(query, *params)
                .fetchall()
            )

    guide, program = records["guide_id"], records["program_agent_id"]
    before_queue = sql("SELECT COUNT(*) FROM crm_channels2.SendJob")[0][0]
    preview = simulate(guide)
    preview["call_provider"] = False
    value = api("/simulate", "POST", preview)
    check(
        "selected_preview_has_no_provider_or_delivery",
        not value["network_called"] and not calls and value["agent_id"] == guide,
    )
    edit_setting("ai", enabled=True)
    b.request(
        "credentials",
        "PUT",
        {
            "operation_id": str(uuid4()),
            "scope": "provider",
            "owner": "gemini",
            "kind": "api_key",
            "value": "controlled-fixture-never-an-external-key-" + uuid4().hex,
        },
    )
    edit_setting("budgets", daily_tokens=10000000, daily_usd_micros=10000000)
    command = simulate(guide)
    result = api("/simulate", "POST", command)
    count = len(calls)
    repeated = api("/simulate", "POST", command)
    check(
        "actor_bound_success_replays_without_second_inference",
        result == repeated and len(calls) == count == 1,
    )
    check(
        "selected_profile_model_and_version_are_returned",
        result["agent_id"] == guide
        and result["model"] == "owned-controlled-model"
        and result["config_version"] == current(guide)["version"],
    )
    api("/simulate", "POST", {**command, "question": "Cambiar el mismo nonce"}, 409)
    check("changed_payload_same_request_is_denied_before_IO", len(calls) == count)
    usage = sql(
        "SELECT State,TokensUsed FROM crm_agents.Usage WHERE RequestId=?",
        command["request_id"],
    )[0]
    execution = sql(
        "SELECT State,InputTokens,OutputTokens,CostEstimated FROM crm_agents.Execution WHERE RequestId=?",
        command["request_id"],
    )[0]
    check(
        "known_usage_settles_once_in_SQL",
        tuple(usage) == ("completed", 50)
        and tuple(execution[:3]) == ("completed", 31, 19)
        and execution[3] > 0,
    )
    paused = simulate(program)
    api("/simulate", "POST", paused, 409)
    check("paused_profile_denies_paid_IO", len(calls) == count)
    state(program, "active")
    chosen = api("/simulate", "POST", simulate(program))
    check(
        "program_simulator_uses_selected_agent_without_guide_fallback",
        chosen["agent_id"] == program and chosen["program_id"] == 901,
    )
    api("/simulate", "POST", {**simulate(program), "program_id": 902}, 409)
    check("another_program_cannot_be_selected_by_question_or_request", True)
    # Existing settings may change the default, but a saved profile owns its route.
    ai = b.request("settings/ai").json()
    check(
        "profile_route_does_not_replace_global_selection",
        ai["document"]["model"] == "owned-controlled-model",
    )
    unknown = simulate(guide, "CONTROLLED_TIMEOUT")
    api("/simulate", "POST", unknown, 504)
    count = len(calls)
    api("/simulate", "POST", unknown, 409)
    unsettled = sql(
        "SELECT State,TokensReserved,TokensUsed FROM crm_agents.Usage WHERE RequestId=?",
        unknown["request_id"],
    )[0]
    check(
        "uncertain_POST_is_not_retried_and_keeps_reservation",
        len(calls) == count
        and unsettled[0] == "uncertain"
        and unsettled[1] > 0
        and unsettled[2] is None,
    )
    edit_setting("budgets", daily_tokens=0)
    api("/simulate", "POST", simulate(guide), 429)
    check("zero_global_budget_denies_before_IO", len(calls) == count)
    edit_setting("budgets", daily_tokens=10000000)
    # A different authorized actor cannot obtain the first actor's cached result.
    password = "Controlled P5 actor passphrase 73!"
    email = "p5-admin-" + uuid4().hex[:8] + "@cbn.invalid"
    b.request(
        "users",
        "POST",
        {
            "operation_id": str(uuid4()),
            "email": email,
            "full_name": "Administrador controlado P5",
            "password": password,
            "role": "admin",
        },
    )
    other = Browser(app)
    other.login(email, password)
    api("/simulate", "POST", command, 409, browser=other)
    check("cached_result_is_bound_to_original_actor", len(calls) == count)
    email = "p5-viewer-" + uuid4().hex[:8] + "@cbn.invalid"
    b.request(
        "users",
        "POST",
        {
            "operation_id": str(uuid4()),
            "email": email,
            "full_name": "Consulta controlada P5",
            "password": password,
            "role": "viewer",
        },
    )
    viewer = Browser(app)
    viewer.login(email, password)
    api("", expected=403, browser=viewer)
    api("/simulate", "POST", simulate(guide), 403, browser=viewer)
    check("viewer_cannot_read_constructor_or_consume_AI", len(calls) == count)
    selection = api("/selection", browser=viewer)
    check(
        "inbox_selection_does_not_disclose_prompt_configuration",
        all("configuration" not in v for v in selection["agents"]),
    )
    b.request(
        "/api/v1/agents/profiles/" + guide + "/state",
        "POST",
        {
            "operation_id": str(uuid4()),
            "revision": current(guide)["revision"],
            "state": "paused",
        },
        expected=403,
        csrf=False,
    )
    check("agent_mutations_require_CSRF", True)
    # Root-only long configuration round-trips whole and execution rejects overflow.
    a = current(program)
    config = {**a["configuration"], "instructions": "Texto largo íntegro. " * 3000}
    api(
        "/profiles/" + program,
        "PUT",
        {
            "operation_id": str(uuid4()),
            "revision": a["revision"],
            "name": a["name"],
            "level": a["level"],
            "parent_id": a["parent_id"],
            "program_id": a["program_id"],
            "stage_id": a["stage_id"],
            "configuration": config,
        },
    )
    check(
        "long_configuration_is_not_silently_truncated",
        current(program)["configuration"] == config,
    )
    api("/simulate", "POST", simulate(program), 413)
    check("execution_context_overflow_denies_before_provider_IO", len(calls) == count)
    a = current(program)
    restore = {
        "operation_id": str(uuid4()),
        "revision": a["revision"],
        "version": 1,
        "note": "Recuperar configuración inicial conservando historial",
    }
    api("/profiles/" + program + "/restore-version", "POST", restore)
    api("/profiles/" + program + "/restore-version", "POST", restore)
    a = current(program)
    check(
        "version_restore_is_idempotent_new_version_and_paused",
        a["version"] >= 4
        and a["state"] == "paused"
        and a["configuration"] == records["configuration"],
    )
    state(program, "active")
    # A lease is claimed before IO: a concurrent duplicate cannot call again.
    entered.clear()
    release.clear()
    race = simulate(guide, "CONTROLLED_WAIT")
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = pool.submit(api, "/simulate", "POST", race)
        assert entered.wait(40), "provider entry not observed"
        count = len(calls)
        api("/simulate", "POST", race, 409)
        check("concurrent_duplicate_has_one_inference_owner", len(calls) == count)
        release.set()
        pending.result(80)
    # Pause while IO is in progress: the returned content never becomes confirmed.
    entered.clear()
    release.clear()
    race = simulate(program, "CONTROLLED_WAIT")
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = pool.submit(api, "/simulate", "POST", race, 409)
        assert entered.wait(40), "provider entry not observed"
        state(program, "paused")
        release.set()
        pending.result(80)
    row = sql(
        "SELECT State,Result FROM crm_agents5.Request WHERE RequestId=?",
        race["request_id"],
    )[0]
    check(
        "pause_during_inference_fences_result_without_second_call",
        row[0] == "cancelled" and json.loads(row[1]) == {},
    )
    state(program, "active")
    check(
        "manual_simulation_does_not_create_channel_outbox_jobs",
        sql("SELECT COUNT(*) FROM crm_channels2.SendJob")[0][0] == before_queue,
    )
    check("supervision_uses_native_P5_requests", len(api("/supervision")["items"]) >= 5)
    save(
        WORK / "runtime-result.json",
        {
            "status": "passed",
            "checks": checks,
            "controlled_calls": len(calls),
            "real_provider_calls": 0,
            "academic_writes": False,
        },
    )
    print(
        json.dumps(
            {
                "passed": len(checks),
                "controlled_calls": len(calls),
                "real_provider_calls": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
