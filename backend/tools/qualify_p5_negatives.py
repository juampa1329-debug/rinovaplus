"""Resource-bound context replay and retired request leases on the owned copy."""

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
    browser = Browser(create_app(settings))
    browser.login(access["email"], access["password"])
    with admin(settings.connection["database"], readonly=True) as connection:
        c = Cursor(connection.cursor(), settings.ticket["table_map"])
        convos = [
            str(r[0]).lower()
            for r in c.execute(
                "SELECT TOP(2) ConversationId FROM crm.Conversation ORDER BY CreatedAt"
            ).fetchall()
        ]
    context = str(uuid4())
    body = dict(
        operation_id=str(uuid4()),
        revision=0,
        program_id=902,
        evidence="Contexto aislado controlado P5",
        confirmed=True,
    )
    path = (
        lambda conversation: "/api/v1/agents/conversations/"
        + conversation
        + "/contexts/"
        + context
    )
    browser.request(path(convos[0]), "PUT", body)
    replay = browser.request(path(convos[0]), "PUT", body).json()
    denied = browser.request(path(convos[1]), "PUT", body, 409).json()
    assert replay["replayed"] and denied.get("code") == "agents_operation_conflict"
    with admin(settings.connection["database"], readonly=True) as connection:
        c = Cursor(connection.cursor(), settings.ticket["table_map"])
        row = c.execute(
            "SELECT ConversationId FROM crm_agents.Context WHERE ContextId=?", context
        ).fetchone()
        assert str(row[0]).lower() == convos[0]
        assert (
            c.execute(
                "SELECT COUNT(*) FROM crm_agents.History WHERE OperationId=?",
                body["operation_id"],
            ).fetchval()
            == 1
        )
    result = {
        "status": "passed",
        "checks": [
            "context_replay_same_actor_and_resource_is_idempotent",
            "context_replay_under_another_conversation_is_denied",
            "one_context_and_history_event_remain_on_original_conversation",
        ],
        "academic_writes": False,
        "provider_calls": 0,
    }
    save(WORK / "negatives-result.json", result)
    print(json.dumps({"passed": len(result["checks"])}))


if __name__ == "__main__":
    main()
