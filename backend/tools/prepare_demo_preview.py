"Create persisted fictional records in a new, explicitly bound preview copy."

import contextlib
import json
import traceback
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

from app.institutional.api import create_app
from app.institutional.spanish import load
from app.institutional.spanish_bindings import Cursor
from app.institutional.workspace_policy import TARGET, principal
from app.modules.campaigns.domain.scoring import (
    ChurnInputs,
    ConfirmedResponse,
    IncomingEvidence,
    assess_churn,
)
from tools.p2_es_migrations import shape
from tools.p3_workspace_recovery import fingerprint
from tools.prepare_p3_workspace import WORK, admin, prepare, read, save
from tools.qualify_p3_workspace import Browser, cmd, contact
from tools.rehearse_p2_spanish import source_2019

PRIVATE = Path("/var/lib/cbn-p2/preview-demo-v1")
LABEL = "fixture-r5"
PEOPLE = [
    ("Valentina Ríos", "Bogotá", "Enfermería", "Interés", "Beca", 88),
    ("Mateo Salazar", "Medellín", "Sistemas", "Contactado", "Admisiones", 65),
    (
        "Camila Torres",
        "Cali",
        "Administración",
        "Documentación",
        "Documentos pendientes",
        92,
    ),
    ("Santiago Vega", "Barranquilla", "Inglés", "Nuevo", "Admisiones", None),
    ("Isabella Duarte", "Bogotá", "Enfermería", "Inscripción", "Cita programada", 95),
    ("Nicolás Méndez", "Medellín", "Sistemas", "Matriculado", "Admisiones", 100),
    ("Luciana Pardo", "Cali", "Inglés", "Contactado", "Requiere seguimiento", 40),
    (
        "Tomás Herrera",
        "Bogotá",
        "Administración",
        "Interés",
        "Requiere seguimiento",
        55,
    ),
]
STAGES = [
    "Nuevo",
    "Contactado",
    "Interés",
    "Documentación",
    "Inscripción",
    "Matriculado",
]


def guard(profile, settings, clean_database, occupied):
    database = profile["database"]
    if (
        not TARGET.fullmatch(database)
        or database == clean_database
        or database != settings.ticket["identity"]["database"]
        or database != settings.connection["database"]
        or settings.connection["username"] != principal(database)
        or occupied
    ):
        raise ValueError("demo_requires_new_empty_bound_copy")


def configuration():
    return {
        "stages": [
            {
                "key": "demo_" + str(i),
                "label": name,
                "probability": None,
                "active": True,
            }
            for i, name in enumerate(STAGES)
        ],
        "tags": [
            "Admisiones",
            "Requiere seguimiento",
            "Documentos pendientes",
            "Beca",
            "Cita programada",
        ],
        "fields": [
            {
                "key": "programa_interes",
                "label": "Programa de interés (declarado)",
                "type": "List",
                "options": ["Enfermería", "Sistemas", "Administración", "Inglés"],
                "active": True,
                "required": False,
            },
            {
                "key": "modalidad_interes",
                "label": "Modalidad de interés",
                "type": "List",
                "options": ["Presencial", "Virtual"],
                "active": True,
                "required": False,
            },
        ],
    }


def seed_rule(profile, record, stage):
    "Controlled synthetic rule evidence, with no provider call or pending send."
    identity, queue, run, assessment = [str(uuid4()) for _ in range(4)]
    with admin(profile["database"]) as connection:
        c = Cursor(
            connection.cursor(), load(Path(profile["directory"])).ticket["table_map"]
        )
        c.execute("BEGIN TRANSACTION")
        try:
            now = (
                c.execute("SELECT SYSUTCDATETIME()")
                .fetchval()
                .replace(tzinfo=timezone.utc)
            )
            at, sent = now - timedelta(days=6), now - timedelta(days=5)
            c.execute(
                (
                    "INSERT crm_channels.Account(Channel,Conf"
                    "iguration) VALUES('whatsapp','{}')"
                )
            )
            c.execute(
                (
                    "INSERT crm_channels.ExternalIdentity(Ide"
                    "ntityId,Channel,ExternalId,ContactId,Con"
                    "versationId) VALUES(?,'whatsapp','demo-f"
                    "ictional-followup',?,?)"
                ),
                identity,
                record["contactId"],
                record["conversationId"],
            )
            incoming, outgoing = [str(uuid4()) for _ in range(2)]
            for mid, direction, text, timestamp in [
                (
                    incoming,
                    "incoming",
                    ("[DEMO] ¿Qué documentos debo reunir para inscribirme?"),
                    at,
                ),
                (
                    outgoing,
                    "outgoing",
                    (
                        "[DEMO] Te compartimos los requisitos. Po"
                        "demos agendar una llamada de seguimiento"
                        "."
                    ),
                    sent,
                ),
            ]:
                c.execute(
                    (
                        "INSERT crm.Message(MessageId,Conversatio"
                        "nId,Body,Direction,CreatedAt) VALUES(?,?"
                        ",?,?,?)"
                    ),
                    mid,
                    record["conversationId"],
                    text,
                    direction,
                    timestamp.replace(tzinfo=None),
                )
            first = c.execute(
                ("SELECT Sequence FROM crm.Message WHERE MessageId=?"), incoming
            ).fetchval()
            last = c.execute(
                ("SELECT Sequence FROM crm.Message WHERE MessageId=?"), outgoing
            ).fetchval()
            c.execute(
                (
                    "INSERT crm_channels.outbound_queue(Queue"
                    "Id,Channel,IdentityId,MessageId,Payload,"
                    "State,ExternalId) VALUES(?,'whatsapp',?,"
                    "?,?,'delivered','demo-synthetic-receipt'"
                    ")"
                ),
                queue,
                identity,
                outgoing,
                json.dumps({"replyToMessageId": incoming, "demo": True}),
            )
            for mid, kind, q in [
                (incoming, "external", None),
                (outgoing, "human", queue),
            ]:
                c.execute(
                    (
                        "INSERT crm_channels.MessageRoute(Message"
                        "Id,IdentityId,QueueId,ActorKind,ControlE"
                        "poch,CompletedAt) VALUES(?,?,?,?,NULL,?)"
                    ),
                    mid,
                    identity,
                    q,
                    kind,
                    sent.replace(tzinfo=None),
                )
            c.execute(
                (
                    "INSERT crm_marketing.EvaluationRun(RunId"
                    ",Kind,TriggerKind,State,StartedAtUtc,Com"
                    "pletedAtUtc) VALUES(?,'predictions','man"
                    "ual','completed',?,?)"
                ),
                run,
                now.replace(tzinfo=None),
                now.replace(tzinfo=None),
            )
            result = assess_churn(
                ChurnInputs(
                    UUID(record["conversationId"]),
                    now,
                    "open",
                    stage,
                    last,
                    IncomingEvidence(UUID(incoming), UUID(identity), first, at),
                    (
                        ConfirmedResponse(
                            UUID(outgoing),
                            UUID(identity),
                            UUID(queue),
                            UUID(incoming),
                            last,
                            sent,
                            "provider_delivered",
                            uuid4(),
                        ),
                    ),
                    True,
                ),
                {stage: 25},
            )
            if result.status != "known" or result.level != "high":
                raise ValueError("demo_rule_fixture_not_known")
            c.execute(
                (
                    "INSERT crm_marketing.ChurnAssessment(Ass"
                    "essmentId,ConversationId,IdentityId,AsOf"
                    "Utc,InputSequence,FormulaVersion,Status,"
                    "RiskScore,RiskLevel,StageSnapshot,Waitin"
                    "gSinceUtc,ReasonsJson,EvidenceJson,RunId"
                    ") VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
                ),
                assessment,
                record["conversationId"],
                identity,
                now.replace(tzinfo=None),
                last,
                result.formula_version,
                result.status,
                result.score,
                result.level,
                stage,
                result.waiting_since.replace(tzinfo=None),
                json.dumps(result.reasons),
                json.dumps(asdict(result), default=str),
                run,
            )
            c.execute(
                (
                    "UPDATE crm.Conversation SET UpdatedAt=SY"
                    "SUTCDATETIME() WHERE ConversationId=?"
                ),
                record["conversationId"],
            )
            c.execute(
                ("UPDATE crm_workspace.State SET Revision=Revision+1 WHERE StateId=1")
            )
            c.execute("COMMIT")
        except BaseException:
            c.execute("IF @@TRANCOUNT>0 ROLLBACK")
            raise


def source_state(clean, parent):
    result = source_2019([parent])
    with admin(clean, readonly=True) as connection:
        cursor = connection.cursor()
        result[clean] = {"shape": shape(cursor), "data": fingerprint(cursor)}
    return result


def main():
    if (PRIVATE / "started.json").exists() or (
        WORK / (LABEL + "-profile.json")
    ).exists():
        raise ValueError("demo_already_prepared_do_not_reseed")
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    clean = read(WORK / "final-profile.json")["database"]
    parent = read(Path("/var/lib/cbn-p2/p2-es-v1/final-profile.json"))["database"]
    source_before = source_state(clean, parent)
    save(PRIVATE / "source-before.json", source_before)
    prepare(LABEL)
    profile = read(WORK / (LABEL + "-profile.json"))
    settings = load(Path(profile["directory"]))
    with admin(profile["database"], readonly=True) as connection:
        c = Cursor(connection.cursor(), settings.ticket["table_map"])
        occupied = any(
            c.execute("SELECT COUNT(*) FROM " + table).fetchval()
            for table in [
                "crm.Contact",
                "crm.Conversation",
                "crm.Message",
                "crm_workspace.Task",
                "crm_workspace.Note",
            ]
        )
    guard(profile, settings, clean, occupied)
    save(
        PRIVATE / "started.json",
        {"database": profile["database"], "scope": "fictional_demo_only"},
    )
    account = read(WORK / (LABEL + "-access.json"))
    browser = Browser(create_app(settings))
    signed = browser.login(account["email"], account["password"])
    cfg = browser.request("/api/local/crm/configuration").json()
    browser.request(
        "/api/local/crm/configuration",
        "PUT",
        dict(
            operationId=str(uuid4()),
            expectedRevision=cfg["revision"],
            config=configuration(),
        ),
    )
    records = []
    for index, (name, city, program, stage, tag, score) in enumerate(PEOPLE):
        person = dict(
            contact("Demo · " + name, stage),
            city=city,
            tags=tag,
            notes=(
                "Datos ficticios para explorar el CRM. No"
                " corresponden a una persona real."
            ),
            customValues={
                "programa_interes": program,
                "modalidad_interes": "Virtual" if index % 2 else "Presencial",
            },
        )
        created = browser.write(
            "clients/" + person["id"],
            cmd(browser.get("clients")["revision"], client=person),
            "POST",
        )
        record = dict(created, name=person["name"])
        records.append(record)
        conversation = record["conversationId"]
        browser.write(
            "clients/" + person["id"] + "/notes",
            cmd(
                browser.get("clients")["revision"],
                body="[DEMO] Solicita información de "
                + program
                + ". Próximo paso: confirmar jornada y requisitos.",
            ),
            "POST",
        )
        browser.write(
            "tasks/" + str(uuid4()),
            cmd(
                browser.get("clients")["revision"],
                conversationId=conversation,
                title="Seguimiento de admisiones: " + name,
                priority="high" if index % 3 == 0 else "normal",
                status="completed" if index == 5 else "pending",
                userId=signed["user"]["id"],
                dueAt=(
                    datetime.now(timezone.utc) + timedelta(days=index - 2)
                ).isoformat(),
            ),
        )
        browser.write(
            "conversations/" + conversation + "/manual",
            cmd(
                browser.get("clients")["revision"],
                score=score,
                temperature="hot"
                if score and score >= 75
                else "warm"
                if score
                else None,
            ),
        )
        with admin(profile["database"]) as connection:
            c = Cursor(connection.cursor(), settings.ticket["table_map"])
            for direction, body in [
                (
                    "incoming",
                    "[DEMO] Hola, quisiera conocer el programa de " + program + ".",
                ),
                (
                    "outgoing",
                    (
                        "[DEMO] Con gusto. Podemos orientarte sob"
                        "re modalidad, requisitos y proceso de ad"
                        "misión."
                    ),
                ),
                (
                    "incoming",
                    (
                        "[DEMO] Me interesa conocer los horarios "
                        "y las opciones de inscripción."
                    ),
                ),
            ]:
                c.execute(
                    (
                        "INSERT crm.Message(MessageId,Conversatio"
                        "nId,Body,Direction) VALUES(?,?,?,?)"
                    ),
                    str(uuid4()),
                    conversation,
                    body,
                    direction,
                )
        detail = browser.get("conversations/" + conversation)
        messages = browser.get("conversations/" + conversation + "/messages")["items"]
        browser.write(
            "conversations/" + conversation,
            cmd(
                detail["revision"],
                state="closed" if index == 5 else "waiting" if index == 6 else "open",
                priority="high" if index in {0, 2, 7} else "normal",
                mode="ai" if index == 3 else "human",
                userId=None if index % 2 else signed["user"]["id"],
                unread=index % 2 == 0,
                readThrough=messages[-1]["sequence"],
            ),
        )
    save(PRIVATE / "records.json", records)
    seed_rule(profile, records[-1], PEOPLE[-1][3])
    if (
        browser.get("inbox/" + records[-1]["conversationId"] + "/detail")["risk"][
            "level"
        ]
        != "high"
    ):
        raise AssertionError("demo_risk_surface_not_visible")
    finish_report(profile, account, records, source_before, clean, parent)


def finish_report(profile, account, records, source_before, clean, parent):
    after = source_state(clean, parent)
    # The user is browsing the clean application's live API: its rate buckets
    # can change normally. Do not call that a binary preservation result.
    if (
        source_before[parent] != after[parent]
        or source_before[clean]["shape"] != after[clean]["shape"]
    ):
        raise ValueError("demo_source_schema_or_P2_changed")
    settings = load(Path(profile["directory"]))
    guard(profile, settings, clean, False)
    with admin(clean, readonly=True) as connection:
        c = Cursor(connection.cursor(), settings.ticket["table_map"])
        source_demo_rows = c.execute(
            ("SELECT COUNT(*) FROM crm.Contact WHERE Name LIKE N'Demo · %'")
        ).fetchval()
    if source_demo_rows:
        raise ValueError("demo_records_found_in_clean_source")
    save(PRIVATE / "profile.json", profile)
    save(PRIVATE / "access.json", account)
    save(
        PRIVATE / "result.json",
        {
            "status": "passed",
            "database": profile["database"],
            "contacts": len(records),
            "conversations": len(records),
            "messages": len(records) * 3 + 2,
            "notes": len(records),
            "tasks": len(records),
            "P2_source_catalog_and_data_unchanged": True,
            "clean_P3_catalog_unchanged": True,
            "clean_P3_has_no_demo_contacts": True,
            "clean_P3_aggregate_data_changed_while_live": source_before[clean]["data"]
            != after[clean]["data"],
            "clean_P3_binary_data_preservation_claimed": False,
            "persisted_SQL_Server_2019": True,
            "academic_DDL_or_DML": False,
            "provider_calls": 0,
            "pending_outbound_jobs": 0,
            "risk_fixture": ("synthetic_rule_example_expires_normally_after24h"),
            "all_people_marked_demo": True,
        },
    )
    print(
        json.dumps(
            {
                "persisted_demo": "passed",
                "contacts": len(records),
                "messages": len(records) * 3 + 2,
            }
        )
    )


if __name__ == "__main__":
    try:
        main()
    except BaseException as error:
        with contextlib.suppress(Exception):
            PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
            save(
                PRIVATE / "failure.json",
                {"type": type(error).__name__, "trace": traceback.format_exc()},
            )
        print(json.dumps({"demo_preparation": "failed", "type": type(error).__name__}))
        raise SystemExit(1)
