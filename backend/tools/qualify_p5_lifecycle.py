"""Hierarchy, scope, human ownership and sensitive actions on the owned P5 fixture."""

import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

from app.institutional.api import create_app
from app.institutional.spanish import load
from app.institutional.spanish_bindings import Cursor
from app.institutional.agents import expire_requests
from app.institutional.store import transaction
from tools.prepare_p5_agents import WORK, read, save, admin
from tools.qualify_p3_workspace import Browser


def main():
    settings = load(Path(read(WORK / "fixture-r3-profile.json")["directory"]))
    access = read(WORK / "fixture-r3-access.json")
    records = read(WORK / "fixture-records.json")
    entered = threading.Event()
    release = threading.Event()
    calls = []

    class Gateway:
        def __init__(self, keys):
            self.keys = keys
            self.transport = None
            self.hermes_base = ""
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
            calls.append(model)
            entered.set()
            assert release.wait(40)
            self.last_usage = {"input": 25, "output": 10}
            self.last_response_metadata = {"finish_reason": "STOP"}
            return json.dumps(
                {
                    "answer": "Respuesta controlada que debe invalidarse con la atención humana.",
                    "handoff": True,
                    "references": [],
                    "memory": [],
                }
            )

    app = create_app(settings, agent_gateway_factory=Gateway)
    b = Browser(app)
    b.login(access["email"], access["password"])
    checks = []

    def check(name, ok=True):
        assert ok, name
        checks.append(name)
        save(
            WORK / "lifecycle-result.json",
            {"status": "in_progress", "checks": checks, "real_provider_calls": 0},
        )

    def api(path="", method="GET", body=None, expected=200):
        return b.request("/api/v1/agents" + path, method, body, expected).json()

    def current(key):
        return next(v for v in api()["agents"] if v["id"] == key)

    def mutation(revision, **kw):
        return dict(operation_id=str(uuid4()), revision=revision, **kw)

    def edit(key, config):
        item = current(key)
        return api(
            "/profiles/" + key,
            "PUT",
            mutation(
                item["revision"],
                **{
                    k: item[k]
                    for k in ["name", "level", "parent_id", "program_id", "stage_id"]
                },
                configuration=config,
            ),
        )

    def sql(query, *params):
        with admin(settings.connection["database"], readonly=True) as connection:
            return (
                Cursor(connection.cursor(), settings.ticket["table_map"])
                .execute(query, *params)
                .fetchall()
            )

    guide, program = records["guide_id"], records["program_agent_id"]
    root = current(guide)
    config = {
        **root["configuration"],
        "capabilities": list(
            dict.fromkeys(
                root["configuration"]["capabilities"]
                + ["advisor.actions", "crm.update"]
            )
        ),
        "allow_safe_actions": True,
        "allow_crm_update": True,
    }
    edit(guide, config)
    edit(program, config)
    existing_stage = next(
        (
            s
            for s in api()["stages"]
            if s["program_id"] == 901 and s["name"] == "Etapa controlada"
        ),
        None,
    )
    stage = existing_stage["id"] if existing_stage else str(uuid4())
    api(
        "/stages/" + stage,
        "PUT",
        mutation(
            existing_stage["revision"] if existing_stage else 0,
            program_id=901,
            name="Etapa controlada",
            entry_rule="Interés declarado",
            exit_rule="Confirmación humana",
            evidence_required="Nota revisada",
        ),
    )
    existing_agent = next((a for a in api()["agents"] if a["stage_id"] == stage), None)
    stage_agent = existing_agent["id"] if existing_agent else str(uuid4())
    agent_body = mutation(
        0,
        name="Subagente controlado",
        level="stage",
        parent_id=program,
        program_id=901,
        stage_id=stage,
        configuration=config,
    )
    denied = api(
        "/profiles/" + stage_agent,
        "PUT",
        {**agent_body, "revision": existing_agent["revision"] if existing_agent else 0},
        409,
    )
    check(
        "unapproved_stage_cannot_become_executable",
        denied.get("code") == "agents_stage_approval_required",
    )
    s = next(s for s in api()["stages"] if s["id"] == stage)
    api(
        "/stages/" + stage + "/approve",
        "POST",
        mutation(s["revision"], note="Revisión humana de la etapa", confirmed=True),
    )
    if not existing_agent:
        api(
            "/profiles/" + stage_agent,
            "PUT",
            {**agent_body, "operation_id": str(uuid4())},
        )
    check(
        "three_level_hierarchy_has_approved_stage",
        current(stage_agent)["parent_id"] == program,
    )
    duplicate = mutation(
        0,
        name="Duplicado denegado",
        level="program",
        parent_id=guide,
        program_id=901,
        configuration=config,
    )
    api("/profiles/" + str(uuid4()), "PUT", duplicate, 409)
    check("same_scope_cannot_have_two_active_owners", True)
    # Knowledge is seeded solely as an owned qualification fixture; publication
    # and source CRUD acceptance belong to P6, scope enforcement belongs to P5.
    prior_docs = sql(
        "SELECT DocumentId,Title FROM crm_ai.KnowledgeDocument WHERE FileName='controlled.txt' ORDER BY Title"
    )
    docs = [
        str(
            next(
                (r[0] for r in prior_docs if r[1] == "Fuente controlada " + str(i)),
                uuid4(),
            )
        ).lower()
        for i in range(3)
    ]
    with admin(settings.connection["database"]) as connection:
        c = Cursor(connection.cursor(), settings.ticket["table_map"])
        for index, doc in enumerate(docs):
            if any(str(r[0]).lower() == doc for r in prior_docs):
                continue
            c.execute(
                "INSERT crm_ai.KnowledgeDocument(DocumentId,Title,FileName,ContentHash,ByteLength,State,Revision) VALUES(?,?,?,?,?,'published',1)",
                doc,
                "Fuente controlada " + str(index),
                "controlled.txt",
                hashlib.sha256(doc.encode()).digest(),
                100,
            )
            c.execute(
                "INSERT crm_ai.KnowledgeChunk(ChunkId,DocumentId,Ordinal,PageNumber,Body) VALUES(?,?,0,1,?)",
                str(uuid4()),
                doc,
                "Texto privado del programa " + str(901 + index),
            )
    for index, doc in enumerate(docs):
        prior_scope = sql(
            "SELECT Revision FROM crm_agents.SourceScope WHERE DocumentId=?", doc
        )
        api(
            "/sources/" + doc + "/scope",
            "PUT",
            mutation(
                prior_scope[0][0] if prior_scope else 0,
                program_id=901 if index != 1 else 902,
                owner="Responsable controlado",
                valid_until="2027-10-27",
                confirmed=True,
                note="Alcance revisado",
            ),
        )
    with admin(settings.connection["database"]) as connection:
        Cursor(connection.cursor(), settings.ticket["table_map"]).execute(
            "UPDATE crm_agents.SourceScope SET ValidUntil='2020-01-01' WHERE DocumentId=?",
            docs[2],
        )
    check("source_scope_requires_named_owner_and_validity", True)
    for doc, label in [
        (docs[1], "foreign_program_source_denied"),
        (docs[2], "expired_source_denied"),
    ]:
        a = current(program)
        api(
            "/profiles/" + program,
            "PUT",
            mutation(
                a["revision"],
                **{
                    k: a[k]
                    for k in ["name", "level", "parent_id", "program_id", "stage_id"]
                },
                configuration={**config, "document_ids": [doc]},
            ),
            409,
        )
        check(label)
    # The non-semantic path still filters before reading bodies.
    own = {
        **config,
        "document_ids": [docs[0]],
        "memories": ["short", "knowledge", "vertical", "regulated"],
    }
    edit(program, own)
    selected = current(program)
    chunks = sql("SELECT DocumentId,ChunkId FROM crm_ai.KnowledgeChunk")
    own_chunks = {str(r[1]).lower() for r in chunks if str(r[0]).lower() == docs[0]}
    foreign_chunks = {
        str(r[1]).lower() for r in chunks if str(r[0]).lower() in docs[1:]
    }
    preview = api(
        "/simulate",
        "POST",
        dict(
            agent_id=program,
            config_version=selected["version"],
            program_id=901,
            question="¿Qué información tiene?",
            request_id=str(uuid4()),
        ),
    )
    check(
        "preview_contains_only_approved_program_sources",
        bool(own_chunks.intersection(s["id"] for s in preview["sources"]))
        and not foreign_chunks.intersection(s["id"] for s in preview["sources"]),
    )
    with admin(settings.connection["database"]) as connection:
        Cursor(connection.cursor(), settings.ticket["table_map"]).execute(
            "UPDATE crm_ai.KnowledgeDocument SET Revision=Revision+1 WHERE DocumentId=?",
            docs[0],
        )
    api("/profiles/" + program + "/preflight")
    bad = api("/profiles/" + program + "/preflight")
    check(
        "changed_document_requires_scope_review_again",
        not bad["ready"] and "agents_source_not_approved_for_scope" in bad["checks"],
    )
    scope_revision = sql(
        "SELECT Revision FROM crm_agents.SourceScope WHERE DocumentId=?", docs[0]
    )[0][0]
    api(
        "/sources/" + docs[0] + "/scope",
        "PUT",
        mutation(
            scope_revision,
            program_id=901,
            owner="Responsable controlado",
            valid_until="2027-10-27",
            confirmed=True,
            note="Revisada la nueva versión",
        ),
    )
    conversation = str(
        sql("SELECT TOP(1) ConversationId FROM crm.Conversation ORDER BY CreatedAt")[0][
            0
        ]
    ).lower()
    context = str(uuid4())
    api(
        "/conversations/" + conversation + "/contexts/" + context,
        "PUT",
        mutation(
            0,
            program_id=901,
            stage_id=stage,
            evidence="Interés y etapa confirmados por operador",
            confirmed=True,
        ),
    )
    assignment = api("/conversations/" + conversation)
    api(
        "/conversations/" + conversation + "/assignment",
        "PUT",
        mutation(
            assignment["revision"],
            mode="automatic",
            context_id=context,
            note="Seleccionar etapa confirmada",
            confirmed=True,
        ),
    )
    detail = api("/conversations/" + conversation)
    check(
        "Inbox_selects_one_stage_owner_from_confirmed_context",
        detail["selection"]["agent_id"] == stage_agent,
    )
    check(
        "Inbox_selection_keeps_configuration_private",
        "configuration" not in detail["selection"],
    )
    assignment_before = sql(
        "SELECT Mode,ContextId,Revision FROM crm_agents.Assignment WHERE ConversationId=?",
        conversation,
    )
    memory_before = sql(
        "SELECT MemoryJson FROM crm_agents.Context WHERE ContextId=?", context
    )
    note_count = sql("SELECT COUNT(*) FROM crm_workspace.Note")[0][0]
    action = mutation(
        current(program)["revision"],
        kind="crm_note",
        impact="high",
        risk="high",
        title="Nota revisada",
        context="Contexto controlado de la conversación",
        conversation_id=conversation,
    )
    api("/profiles/" + program + "/actions", "POST", action)
    decision = mutation(
        current(program)["revision"],
        action_id=action["operation_id"],
        decision="execute",
    )
    api("/profiles/" + program + "/actions/decision", "POST", decision, 409)
    check(
        "sensitive_action_cannot_execute_without_separate_approval",
        sql("SELECT COUNT(*) FROM crm_workspace.Note")[0][0] == note_count,
    )
    api(
        "/profiles/" + program + "/actions/decision",
        "POST",
        mutation(
            current(program)["revision"],
            action_id=action["operation_id"],
            decision="approve",
        ),
    )
    api("/profiles/" + program + "/actions/decision", "POST", decision)
    api("/profiles/" + program + "/actions/decision", "POST", decision)
    check(
        "approved_CRM_note_is_written_once_as_note",
        sql("SELECT COUNT(*) FROM crm_workspace.Note")[0][0] == note_count + 1,
    )
    # Real SQL ownership changes while controlled inference is in flight.
    body = dict(
        request_id=str(uuid4()),
        revision=detail["revision"],
        question="Consulta controlada en vuelo",
        call_provider=True,
        acknowledge_consumption=True,
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = pool.submit(
            api, "/conversations/" + conversation + "/draft", "POST", body, 409
        )
        assert entered.wait(50), "inference did not start"
        latest = b.get("conversations/" + conversation)
        b.write(
            "conversations/" + conversation,
            {
                "operationId": str(uuid4()),
                "revision": latest["revision"],
                "state": "open",
                "priority": "normal",
                "mode": "human",
                "unread": True,
            },
        )
        release.set()
        pending.result(90)
    row = sql(
        "SELECT State,Result FROM crm_agents5.Request WHERE RequestId=?",
        body["request_id"],
    )[0]
    check(
        "human_takeover_during_inference_fences_AI_result",
        row[0] == "cancelled" and json.loads(row[1]) == {} and len(calls) == 1,
    )
    with transaction(settings, True, anonymous=True) as c:
        expire_requests(c)
    check(
        "cancelled_paid_work_retains_uncertain_reservation",
        sql(
            "SELECT State,TokensUsed FROM crm_agents.Usage WHERE RequestId=?",
            body["request_id"],
        )[0][0]
        == "uncertain",
    )
    api(
        "/conversations/" + conversation + "/draft",
        "POST",
        {**body, "request_id": str(uuid4())},
        409,
    )
    check("human_owner_blocks_new_AI_draft", len(calls) == 1)
    # Version restoration changes only configuration/lifecycle; context and
    # assignment records remain available for review, not silently rerouted.
    a = current(program)
    api(
        "/profiles/" + program + "/restore-version",
        "POST",
        mutation(a["revision"], version=1, note="Reversión completa P5"),
    )
    check(
        "version_reversal_preserves_memory_and_assignment",
        sql("SELECT MemoryJson FROM crm_agents.Context WHERE ContextId=?", context)
        == memory_before
        and sql(
            "SELECT Mode,ContextId,Revision FROM crm_agents.Assignment WHERE ConversationId=?",
            conversation,
        )
        == assignment_before,
    )
    check("reversal_leaves_new_version_paused", current(program)["state"] == "paused")
    check(
        "history_is_retained_after_reversal",
        len(api("/history?entity_id=" + program)["items"]) >= 5,
    )
    save(
        WORK / "lifecycle-result.json",
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
