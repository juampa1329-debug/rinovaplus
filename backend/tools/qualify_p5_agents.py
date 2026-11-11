"""Institutional constructor qualification in the explicitly owned P5 fixture."""

import json
from pathlib import Path
from uuid import uuid4

from app.institutional.api import create_app
from app.institutional.spanish import load
from app.modules.agents.domain import Configuration
from tools.prepare_p5_agents import WORK, read, save
from tools.qualify_p3_workspace import Browser


def main():
    settings = load(Path(read(WORK / "fixture-r3-profile.json")["directory"]))
    access = read(WORK / "fixture-r3-access.json")
    browser = Browser(create_app(settings))
    browser.login(access["email"], access["password"])
    checks = []

    def check(name, ok):
        assert ok, name
        checks.append(name)
        save(WORK / "api-result.json", {"status": "in_progress", "checks": checks})

    def request(path="", method="GET", body=None, expected=200):
        response = browser.client.request(
            method,
            "/api/v1/agents" + path,
            json=body,
            headers={"X-CRM-Local": "1", "X-CSRF-Token": browser.csrf},
        )
        if response.status_code != expected:
            raise AssertionError((path, response.status_code, response.json()))
        return response.json()

    check(
        "own_P5_runtime_and_contract",
        browser.request("runtime").json()["agent_operations"],
    )
    check("institutional_agents_catalog_installed", request()["installed"])
    model = browser.request("settings/models").json()
    document = {
        "selections": [
            v
            for v in model["document"]["selections"]
            if not (v["provider"] == "gemini" and v["category"] == "text")
        ]
        + [
            {
                "provider": "gemini",
                "category": "text",
                "selected_model": "owned-controlled-model",
                "display_name": "Modelo controlado",
            }
        ]
    }
    browser.request(
        "settings/models",
        "PUT",
        {
            "operation_id": str(uuid4()),
            "revision": model["revision"],
            "document": document,
        },
    )
    providers = request("/providers")
    check(
        "model_metadata_uses_canonical_configuration_without_discovery",
        providers["network_called"] is False,
    )
    for program in [901, 902]:
        request(
            "/programs/" + str(program),
            "PUT",
            {
                "operation_id": str(uuid4()),
                "revision": 0,
                "name": "Programa de prueba " + str(program),
                "school": "Escuela declarada",
                "schedule": "Diurna",
            },
        )
    check(
        "declared_programs_do_not_claim_SIIE",
        request("/programs")["authority"] == "declared_CRM_catalog_not_verified_SIIE",
    )
    config = Configuration(
        provider="gemini",
        primary_model="owned-controlled-model",
        instructions="Orientación educativa con fuentes; nunca inventes matrícula ni pagos.",
        channels=["local", "whatsapp"],
        capabilities=[
            "program.read",
            "sources.read",
            "conversation.reply",
            "human.handoff",
        ],
        monthly_token_limit=2500000,
        input_usd_per_million=1.0,
        output_usd_per_million=1.0,
        memories=["short", "knowledge", "vertical", "regulated"],
        allow_reply=True,
    ).model_dump(mode="json")
    guide, program = str(uuid4()), str(uuid4())
    command = {
        "operation_id": str(uuid4()),
        "revision": 0,
        "name": "Orientadora controlada",
        "level": "guide",
        "configuration": config,
    }
    result = request("/profiles/" + guide, "PUT", command)
    repeat = request("/profiles/" + guide, "PUT", command)
    check(
        "valid_save_available_without_profile_approval",
        result["confirmed"] and repeat["replayed"],
    )
    catalog = request()
    item = next(a for a in catalog["agents"] if a["id"] == guide)
    check(
        "saved_profile_reloads_exact_model_and_active_state",
        item["state"] == "active" and item["configuration"] == config,
    )
    request(
        "/profiles/" + program,
        "PUT",
        {
            "operation_id": str(uuid4()),
            "revision": 0,
            "name": "Agente programa controlado",
            "level": "program",
            "parent_id": guide,
            "program_id": 901,
            "configuration": config,
        },
    )
    check(
        "guide_program_hierarchy_persisted",
        any(
            a["id"] == program and a["parent_id"] == guide for a in request()["agents"]
        ),
    )
    current = next(a for a in request()["agents"] if a["id"] == program)
    request(
        "/profiles/" + program + "/state",
        "POST",
        {
            "operation_id": str(uuid4()),
            "revision": current["revision"],
            "state": "paused",
            "note": "Pausa de prueba",
            "confirmed": True,
        },
    )
    current = next(a for a in request()["agents"] if a["id"] == program)
    request(
        "/profiles/" + program,
        "PUT",
        {
            "operation_id": str(uuid4()),
            "revision": current["revision"],
            "name": current["name"],
            "level": "program",
            "parent_id": guide,
            "program_id": 901,
            "configuration": {**config, "tone": "Claro y cercano"},
        },
    )
    check(
        "editing_a_paused_profile_preserves_pause",
        next(a for a in request()["agents"] if a["id"] == program)["state"] == "paused",
    )
    save(
        WORK / "fixture-records.json",
        {"guide_id": guide, "program_agent_id": program, "configuration": config},
    )
    save(
        WORK / "api-result.json",
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
