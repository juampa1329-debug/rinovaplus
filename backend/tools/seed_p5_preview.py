"""Persist clearly fictional educational profiles in the fresh final P5 copy only."""

from pathlib import Path
from uuid import uuid4
import json
from app.institutional.api import create_app
from app.institutional.spanish import load
from app.institutional.spanish_bindings import Cursor
from app.modules.agents.domain import Configuration
from tools.prepare_p5_agents import WORK, read, save, admin
from tools.qualify_p3_workspace import Browser


def main():
    assert not (WORK / "demo-result.json").exists(), "demo seed is not startup logic"
    settings = load(Path(read(WORK / "final-profile.json")["directory"]))
    access = read(WORK / "final-access.json")
    b = Browser(create_app(settings))
    b.login(access["email"], access["password"])

    def api(path="", method="GET", body=None):
        return b.request("/api/v1/agents" + path, method, body).json()

    assert not api()["agents"], "preserve existing profiles; explicit review required"

    def mutate(**kw):
        return dict(operation_id=str(uuid4()), revision=0, **kw)

    with admin(settings.connection["database"], readonly=True) as connection:
        c = Cursor(connection.cursor(), settings.ticket["table_map"])
        before = {
            n: c.execute("SELECT COUNT(*) FROM " + n).fetchval()
            for n in [
                "crm.Contact",
                "crm.Conversation",
                "crm.Message",
                "crm_workspace.Task",
                "crm_workspace.Note",
                "crm_channels2.SocialComment",
                "crm_channels2.SendJob",
            ]
        }
    program_id = 91001
    assert api("/programs/" + str(program_id))["exists"] is False
    api(
        "/programs/" + str(program_id),
        "PUT",
        mutate(
            name="Orientación educativa · ejemplo",
            school="Escuela de ejemplo",
            schedule="Jornada por confirmar",
        ),
    )
    with admin(settings.connection["database"]) as connection:
        Cursor(connection.cursor(), settings.ticket["table_map"]).execute(
            "UPDATE crm_agents5.Program SET Authority='synthetic_demo' WHERE ProgramId=?",
            program_id,
        )
    config = Configuration(
        provider="gemini",
        primary_model="cbn-demo-unconfigured",
        instructions="Eres una asistente virtual de orientación educativa. Este perfil es un ejemplo ficticio para explorar el constructor. Solicita información sólo cuando sea necesaria. Nunca inventes precios, requisitos, fechas, matrícula ni pagos. Usa únicamente fuentes revisadas y deriva las dudas a un asesor.",
        description="Ejemplo educativo sin proveedor conectado",
        tone="Claro, respetuoso y cercano",
        objectives=[
            "Orientar sobre el proceso de admisiones",
            "Derivar las decisiones académicas al equipo humano",
        ],
        rules=[
            "No presentar los datos de ejemplo como oferta académica oficial",
            "No confirmar inscripciones ni pagos",
        ],
        channels=["local", "whatsapp"],
        capabilities=[
            "program.read",
            "sources.read",
            "conversation.reply",
            "human.handoff",
        ],
        memories=["short", "knowledge", "vertical", "regulated"],
        monthly_token_limit=250000,
        input_usd_per_million=0,
        output_usd_per_million=0,
        allow_reply=True,
    ).model_dump(mode="json")
    guide, program, stage, subagent = [str(uuid4()) for _ in range(4)]
    api(
        "/profiles/" + guide,
        "PUT",
        mutate(
            name="Orientadora institucional · ejemplo",
            level="guide",
            configuration=config,
        ),
    )
    api(
        "/profiles/" + program,
        "PUT",
        mutate(
            name="Agente de programa · ejemplo",
            level="program",
            parent_id=guide,
            program_id=program_id,
            configuration=config,
        ),
    )
    api(
        "/stages/" + stage,
        "PUT",
        mutate(
            program_id=program_id,
            name="Interés inicial · ejemplo",
            entry_rule="La persona declara interés en orientación",
            exit_rule="El asesor confirma el siguiente paso",
            evidence_required="Nota de revisión humana",
        ),
    )
    item = next(s for s in api()["stages"] if s["id"] == stage)
    api(
        "/stages/" + stage + "/approve",
        "POST",
        dict(
            operation_id=str(uuid4()),
            revision=item["revision"],
            confirmed=True,
            note="Etapa ficticia para explorar la jerarquía educativa; no valida estados académicos",
        ),
    )
    api(
        "/profiles/" + subagent,
        "PUT",
        mutate(
            name="Subagente de etapa · ejemplo",
            level="stage",
            parent_id=program,
            program_id=program_id,
            stage_id=stage,
            configuration=config,
        ),
    )
    with admin(settings.connection["database"], readonly=True) as connection:
        c = Cursor(connection.cursor(), settings.ticket["table_map"])
        after = {n: c.execute("SELECT COUNT(*) FROM " + n).fetchval() for n in before}
    assert before == after, "existing demo content changed"
    save(
        WORK / "demo-records.json",
        {
            "guide_id": guide,
            "program_agent_id": program,
            "stage_agent_id": subagent,
            "stage_id": stage,
            "program_id": program_id,
        },
    )
    save(
        WORK / "demo-result.json",
        {
            "status": "passed",
            "educational_profiles": 3,
            "approved_example_stages": 1,
            "synthetic_programs": 1,
            "previous_records": before,
            "provider_calls": 0,
            "outbox_jobs_added": 0,
            "academic_writes": False,
        },
    )
    print(
        json.dumps(
            {
                "educational_profiles": 3,
                "previous_demo_content_preserved": True,
                "provider_calls": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
