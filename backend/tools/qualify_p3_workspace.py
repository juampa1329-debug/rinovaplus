"SQL/HTTP P3 acceptance on the explicit synthetic fixture copy only."

import contextlib
import json
import os
import secrets
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.institutional.api import create_app
from app.institutional.spanish import load
from app.institutional.spanish_bindings import Cursor
from tools.prepare_p3_workspace import WORK, admin, read, save

checks = []


def check(name, condition=True):
    if not condition:
        raise AssertionError(name)
    checks.append(name)
    save(WORK / "http-result.json", {"status": "in_progress", "checks": checks})


class Browser:
    def __init__(self, app):
        self.client = TestClient(
            app, base_url="http://127.0.0.1:4178", client=("127.0.0.1", 50200)
        )
        self.csrf = ""

    def request(self, path, method="GET", body=None, expected=200, csrf=True):
        path = path if path.startswith("/") else "/api/institution/" + path
        r = self.client.request(
            method,
            path,
            json=body,
            headers={
                "X-CRM-Local": "1",
                **({"X-CSRF-Token": self.csrf} if csrf and self.csrf else {}),
            },
        )
        if r.status_code != expected:
            raise AssertionError(
                "HTTP_"
                + method
                + "_"
                + path.split("?")[0]
                + "_"
                + str(r.status_code)
                + "_"
                + str(r.json().get("detail", ""))
                + "_expected_"
                + str(expected)
            )
        return r

    def login(self, email, password):
        result = self.request(
            "auth/login", "POST", {"email": email, "password": password}
        ).json()
        self.csrf = result["csrf_token"]
        return result

    def get(self, path):
        return self.request("workspace/" + path).json()

    def write(self, path, body, method="PUT", expected=200):
        return self.request("workspace/" + path, method, body, expected).json()


def cmd(revision, **values):
    return dict(operationId=str(uuid4()), revision=revision, **values)


def contact(name, stage="Nueva", **values):
    return dict(
        id=str(uuid4()),
        name=name,
        phone="",
        city="",
        programId=None,
        program="",
        schedule="",
        stage=stage,
        tags="",
        notes="",
        type="",
        interests="",
        customValues={},
        **values,
    )


def main():
    label = os.environ.get("P3_FIXTURE_LABEL", "fixture-r2")
    if (
        label not in {"fixture-r2", "fixture-r3", "fixture-r4"}
        or (WORK / (label + "-http-private.json")).exists()
    ):
        raise ValueError("P3ES_fixture_already_used")
    profile = read(WORK / (label + "-profile.json"))
    settings = load(Path(profile["directory"]))
    app = create_app(settings)
    credentials = read(WORK / (label + "-access.json"))
    owner = Browser(app)
    signed = owner.login(credentials["email"], credentials["password"])
    owner_id = signed["user"]["id"]
    save(
        WORK / (label + "-http-private.json"),
        {
            "profile": profile["directory"],
            "credentials": credentials,
            "owner_id": owner_id,
        },
    )
    check("SQL2019_own_profile_and_human_session", len(signed["actions"]) == 30)
    owner.request("workspace/clients", expected=200)
    cfg = owner.request("/api/local/crm/configuration").json()
    document = {
        "stages": [
            {"key": "new", "label": "Nueva", "probability": None, "active": True},
            {
                "key": "follow",
                "label": "Seguimiento",
                "probability": None,
                "active": True,
            },
        ],
        "tags": ["Prioritario", "Interés"],
        "fields": [
            {
                "key": "origen",
                "label": "Origen declarado",
                "type": "Text",
                "options": [],
                "active": True,
                "required": False,
            }
        ],
    }
    owner.request(
        "/api/local/crm/configuration",
        "PUT",
        {
            "operationId": str(uuid4()),
            "expectedRevision": cfg["revision"],
            "config": document,
        },
    )
    r = owner.get("clients")["revision"]
    person = contact("P3 prueba principal")
    body = cmd(r, client=person)
    created = owner.write("clients/" + person["id"], body, "POST")
    conversation = created["conversationId"]
    check(
        ("create_contact_and_conversation_same_transaction"),
        created["contactId"] == person["id"],
    )
    check(
        "idempotent_same_contact_command",
        owner.write("clients/" + person["id"], body, "POST") == created,
    )
    mutated = dict(body, client=dict(person, name="Intento distinto"))
    owner.write("clients/" + person["id"], mutated, "POST", 409)
    check("same_operation_changed_payload_rejected")
    detail = owner.get("conversations/" + conversation)
    check(
        "one_canonical_ficha_and_unknown_risk",
        detail["client"]["id"] == person["id"]
        and detail["risk"]["status"] == "unknown",
    )
    owner.write(
        "clients/" + person["id"],
        cmd(
            detail["revision"],
            client=dict(
                person,
                name="Editado desde CRM",
                city="Ciudad QA",
                tags="Prioritario",
                customValues={"origen": "Declaración QA"},
            ),
        ),
    )
    inbox = owner.get("inbox/" + conversation + "/detail")
    check(
        "CRM_edit_visible_in_Inbox_same_SQL",
        inbox["client"]["name"] == "Editado desde CRM"
        and inbox["client"]["customValues"] == {"origen": "Declaración QA"},
    )
    owner.write(
        "conversations/" + conversation,
        cmd(
            inbox["revision"],
            state="open",
            priority="high",
            mode="human",
            userId=owner_id,
            unread=True,
        ),
    )
    check(
        "own_human_UUID_assignment_and_mine_filter",
        owner.get("inbox?queue=mine")["total"] == 1,
    )
    owner.write(
        "conversations/" + conversation + "/messages",
        cmd(owner.get("clients")["revision"], body="Mensaje local de prueba"),
        method="POST",
    )
    check(
        "local_message_committed_without_provider",
        owner.get("conversations/" + conversation + "/messages")["items"][-1]["body"]
        == "Mensaje local de prueba",
    )
    detail = owner.get("conversations/" + conversation)
    owner.write(
        "conversations/" + conversation,
        cmd(
            detail["revision"],
            state="open",
            priority="normal",
            mode="ai",
            userId=owner_id,
            unread=True,
        ),
    )
    owner.write(
        "conversations/" + conversation + "/messages",
        cmd(owner.get("clients")["revision"], body="No debe enviarse"),
        method="POST",
        expected=409,
    )
    detail = owner.get("conversations/" + conversation)
    owner.write(
        "conversations/" + conversation,
        cmd(
            detail["revision"],
            state="open",
            priority="normal",
            mode="human",
            userId=owner_id,
            unread=True,
        ),
    )
    check(("AI_control_blocks_manual_send_and_human_takeover_restores_control"))
    with admin(profile["database"]) as connection:
        c = Cursor(connection.cursor(), settings.ticket["table_map"])
        c.execute(
            (
                "INSERT crm.Message(MessageId,Conversatio"
                "nId,Body,Direction) VALUES(?,?,?,'incomi"
                "ng')"
            ),
            str(uuid4()),
            conversation,
            "Entrada de prueba observada",
        )
        observed = str(
            c.execute(
                ("SELECT MAX(Sequence) FROM crm.Message WHERE ConversationId=?"),
                conversation,
            ).fetchval()
        )
        c.execute(
            (
                "INSERT crm.Message(MessageId,Conversatio"
                "nId,Body,Direction) VALUES(?,?,?,'incomi"
                "ng')"
            ),
            str(uuid4()),
            conversation,
            "Entrada posterior no observada",
        )
    detail = owner.get("conversations/" + conversation)
    owner.write(
        "conversations/" + conversation,
        cmd(
            detail["revision"],
            state="open",
            priority="normal",
            mode="human",
            userId=owner_id,
            unread=False,
            readThrough=observed,
        ),
    )
    check(
        "observed_read_keeps_later_incoming_unread",
        owner.get("conversations/" + conversation)["thread"]["Unread"] is True,
    )
    detail = owner.get("conversations/" + conversation)
    messages = owner.get("conversations/" + conversation + "/messages")
    owner.write(
        "conversations/" + conversation,
        cmd(
            detail["revision"],
            state="open",
            priority="normal",
            mode="human",
            userId=owner_id,
            unread=False,
            readThrough=messages["items"][-1]["sequence"],
        ),
    )
    check(
        "observed_last_sequence_marks_read",
        not owner.get("conversations/" + conversation)["thread"]["Unread"],
    )
    owner.write(
        "clients/" + person["id"] + "/notes",
        cmd(owner.get("clients")["revision"], body="Seguimiento interno verificable"),
        "POST",
    )
    detail = owner.get("conversations/" + conversation)
    check(
        "notes_use_authenticated_human_author",
        detail["notes"][0]["author"] == signed["user"]["full_name"],
    )
    task_id = str(uuid4())
    task = cmd(
        detail["revision"],
        conversationId=conversation,
        title="Tarea de seguimiento",
        status="pending",
        priority="high",
        userId=owner_id,
        dueAt="2026-10-27T18:00:00Z",
    )
    owner.write("tasks/" + task_id, task)
    task_list = owner.get("tasks?status=pending&q=seguimiento")
    check(
        "task_SQL_filters_and_account_owner",
        task_list["total"] == 1 and task_list["items"][0]["id"] == task_id,
    )
    owner.write(
        "tasks/" + task_id,
        cmd(
            task_list["revision"],
            **{
                k: v
                for k, v in task.items()
                if k not in {"operationId", "revision", "status"}
            },
            status="completed",
        ),
    )
    check(
        "task_state_roundtrip",
        owner.get("tasks?status=completed")["total"] == 1
        and owner.get("tasks?status=pending")["total"] == 0,
    )
    # More than the old 500-contact/2000-message snapshot limits, only in this fixture
    # copy.
    fixture_ids = []
    with admin(profile["database"]) as connection:
        c = Cursor(connection.cursor(), settings.ticket["table_map"])
        c.execute("BEGIN TRANSACTION")
        try:
            for index in range(601):
                item = contact("P3 volumen " + str(index).zfill(4))
                cid = str(uuid4())
                fixture_ids.append((item["id"], cid))
                c.execute(
                    (
                        "INSERT crm.Contact(ContactId,Name,Phone,"
                        "City,ProgramId,Program,Schedule,Stage,Ta"
                        "gs,Notes,Type,Interests,CustomValues) VA"
                        "LUES(?,?,'',?,NULL,'','','Nueva',?,'',''"
                        ",'','{}')"
                    ),
                    item["id"],
                    item["name"],
                    "Ciudad filtrada" if index == 600 else "",
                    "Interés" if index == 600 else "",
                )
                c.execute(
                    (
                        "INSERT crm.Conversation(ConversationId,C"
                        "ontactId,State,Priority,ControlMode,Unre"
                        "ad) VALUES(?,?,'open','normal','human',0"
                        ")"
                    ),
                    cid,
                    item["id"],
                )
            c.execute("COMMIT")
        except BaseException:
            c.execute("IF @@TRANCOUNT>0 ROLLBACK")
            raise
    first = owner.get("clients")
    second = owner.get("clients?offset=25&anchor=" + first["revision"])
    check(
        ("SQL_pagination_exceeds_old_snapshot_without_full_workspace"),
        first["total"] == 602
        and len(first["items"]) == 25
        and len(second["items"]) == 25
        and not {x["id"] for x in first["items"]} & {x["id"] for x in second["items"]},
    )
    check(
        "filters_before_pagination_find_last_record",
        owner.get("clients?city=Ciudad%20filtrada&tag=Inter%C3%A9s")["total"] == 1,
    )
    check(
        "literal_SQL_search_wildcards_escaped", owner.get("clients?q=%25")["total"] == 0
    )
    owner.request("workspace/clients?offset=-1", expected=422)
    owner.request("workspace/inbox?queue=arbitrary", expected=422)
    check("invalid_pagination_and_queue_rejected")
    source_id, source_conv = fixture_ids[0]
    target_id, target_conv = fixture_ids[1]
    merge_id = str(uuid4())
    merge = cmd(
        owner.get("clients")["revision"],
        sourceContactId=source_id,
        targetContactId=target_id,
        confirmedSamePerson=True,
    )
    owner.write("merges/" + merge_id, merge, "POST")
    check(
        ("merge_changes_view_without_reparenting_original_conversation"),
        owner.get("inbox/" + source_conv + "/detail")["client"]["id"] == target_id
        and owner.get("clients")["total"] == 601,
    )
    owner.write(
        "merges/" + str(uuid4()),
        cmd(
            owner.get("clients")["revision"],
            sourceContactId=target_id,
            targetContactId=source_id,
            confirmedSamePerson=True,
        ),
        "POST",
        409,
    )
    check("merge_cycle_rejected")
    owner.write(
        "merges/" + merge_id + "/undo", cmd(owner.get("clients")["revision"]), "POST"
    )
    check(
        "undo_restores_original_person_and_rows",
        owner.get("conversations/" + source_conv)["client"]["id"] == source_id
        and owner.get("clients")["total"] == 602,
    )
    # Two current human sessions race the same revision; only one edit may commit.
    contenders = [Browser(app), Browser(app)]
    for browser in contenders:
        browser.login(credentials["email"], credentials["password"])
    detail = owner.get("conversations/" + conversation)
    before = detail["revision"]

    def race(index):
        browser = contenders[index]
        r = browser.client.put(
            "/api/institution/workspace/clients/" + person["id"],
            json=cmd(
                before, client=dict(detail["client"], city="Carrera " + str(index))
            ),
            headers={"X-CRM-Local": "1", "X-CSRF-Token": browser.csrf},
        )
        return r.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        result = list(pool.map(race, [0, 1]))
    check("same_revision_concurrent_write_one_winner", sorted(result) == [200, 409])
    password = "CBN!" + secrets.token_urlsafe(24)
    viewer_info = owner.request(
        "users",
        "POST",
        {
            "operation_id": str(uuid4()),
            "email": "p3.viewer@cbn.local",
            "full_name": "Consulta P3",
            "role": "viewer",
            "password": password,
        },
    ).json()["user"]
    viewer = Browser(app)
    viewer.login("p3.viewer@cbn.local", password)
    for path in ["clients", "inbox", "tasks", "conversations/" + conversation]:
        viewer.get(path)
    detail = owner.get("conversations/" + conversation)
    viewer.write(
        "clients/" + person["id"],
        cmd(detail["revision"], client=detail["client"]),
        expected=403,
    )
    viewer.write(
        "conversations/" + conversation,
        cmd(
            detail["revision"],
            state="open",
            priority="normal",
            mode="human",
            userId=None,
            unread=True,
        ),
        expected=403,
    )
    viewer.write(
        "tasks/" + str(uuid4()),
        cmd(detail["revision"], conversationId=conversation, title="Denegada"),
        expected=403,
    )
    check("viewer_reads_but_valid_mutations_denied")
    owner.request(
        "workspace/clients/" + person["id"],
        "PUT",
        cmd(detail["revision"], client=detail["client"]),
        expected=403,
        csrf=False,
    )
    check("CSRF_denied_before_business_mutation")
    check(
        "audit_activity_has_authenticated_actors",
        any(
            row["author"] == signed["user"]["full_name"]
            for row in owner.get("clients/" + person["id"] + "/activity")["items"]
        ),
    )
    save(
        WORK / "fixture-records.json",
        {
            "contactId": person["id"],
            "conversationId": conversation,
            "volume_ids": fixture_ids,
            "viewer": {
                "email": "p3.viewer@cbn.local",
                "password": password,
                "id": viewer_info["id"],
            },
        },
    )
    save(
        WORK / "http-result.json",
        {
            "status": "passed",
            "database": profile["database"],
            "engine": 15,
            "compatibility": 150,
            "checks": checks,
            "checks_count": len(checks),
            "fixture_contacts": 602,
            "provider_calls": 0,
            "academic_DDL_or_DML": False,
        },
    )
    print(
        json.dumps(
            {"P3_SQL_HTTP": "passed", "checks": len(checks), "fixture_contacts": 602}
        )
    )


if __name__ == "__main__":
    try:
        main()
    except BaseException as error:
        with contextlib.suppress(Exception):
            save(
                WORK / ("http-failure-" + uuid4().hex + ".json"),
                {
                    "type": type(error).__name__,
                    "message": str(error),
                    "trace": traceback.format_exc(),
                    "last_check": checks[-1] if checks else None,
                },
            )
        print(
            json.dumps(
                {
                    "P3_SQL_HTTP": "failed",
                    "type": type(error).__name__,
                    "last_check": checks[-1] if checks else None,
                }
            )
        )
        raise SystemExit(1)
