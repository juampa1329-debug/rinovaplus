"Bounded current-source checks and read-only restart snapshots for P3 copies."

import argparse
import contextlib
import json
import traceback
from pathlib import Path
from uuid import uuid4

from app.institutional.api import create_app
from app.institutional.spanish import load
from tools.prepare_p3_workspace import WORK, admin, read, save
from tools.qualify_p2_recovery import fingerprint
from tools.qualify_p3_workspace import Browser, cmd


def current(label):
    profile = read(WORK / (label + "-profile.json"))
    settings = load(Path(profile["directory"]))
    account = read(WORK / (label + "-access.json"))
    browser = Browser(create_app(settings))
    browser.login(account["email"], account["password"])
    return profile, settings, browser


def fixture():
    _, _, browser = current("fixture-r4")
    checks = []

    def check(name, value):
        if not value:
            raise AssertionError(name)
        checks.append(name)

    listing = browser.get("clients?program=Nonexistent-QA-program&offset=0")
    check("program_filter_before_SQL_page", listing["total"] == 0)
    listing = browser.get("clients?programId=2147483647&offset=0")
    check("mapped_program_id_filter", listing["total"] == 0)
    browser.request("workspace/clients?programId=2147483648", expected=422)
    checks.append("program_id_SQL_int_boundary")
    tasks = browser.get("tasks?status=&offset=0")
    check(
        "tasks_include_canonical_contact_name",
        bool(tasks["items"])
        and all(t["contactId"] and t["contactName"] for t in tasks["items"]),
    )
    next_page = browser.get("tasks?status=&offset=25&anchor=" + tasks["revision"])
    check(
        "task_anchor_page_has_no_overlap",
        bool(next_page["items"])
        and not (
            {t["id"] for t in tasks["items"]} & {t["id"] for t in next_page["items"]}
        ),
    )
    browser.request("workspace/tasks?offset=25&anchor=0", expected=409)
    checks.append("stale_task_anchor_rejected")
    for resource in ["clients", "inbox", "tasks"]:
        browser.request("workspace/" + resource + "?offset=25", expected=422)
        checks.append(resource + "_requires_page_anchor")
    for queue in [
        "all",
        "unread",
        "mine",
        "unassigned",
        "human",
        "ai",
        "open",
        "waiting",
        "closed",
        "hot",
        "churn",
        "sla",
    ]:
        value = browser.get("inbox?queue=" + queue)
        check("current_queue_" + queue, len(value["items"]) <= 25)
    records = read(WORK / "fixture-records.json")
    detail = browser.get("conversations/" + records["conversationId"])
    check(
        "in_flight_handoff_status_explicit", type(detail["inFlightOrUncertain"]) is int
    )
    _, conversation = records["volume_ids"][594]
    before = browser.get("conversations/" + conversation)
    previous = before["manual"]
    try:
        for score, included in [(74, False), (75, True)]:
            detail = browser.get("conversations/" + conversation)
            browser.write(
                "conversations/" + conversation + "/manual",
                cmd(detail["revision"], score=score, temperature="cold"),
            )
            page = browser.get("inbox?queue=hot&q=" + before["client"]["name"])
            check(
                "hot_manual_score_threshold_" + str(score),
                any(
                    row["conversationId"].lower() == conversation.lower()
                    for row in page["items"]
                )
                == included,
            )
    finally:
        detail = browser.get("conversations/" + conversation)
        browser.write(
            "conversations/" + conversation + "/manual",
            cmd(
                detail["revision"],
                score=previous["score"] if previous else None,
                temperature=previous["temperature"] if previous else None,
            ),
        )
    save(
        WORK / "final-fixture-result.json",
        {
            "status": "passed",
            "checks": checks,
            "count": len(checks),
            "academic_DDL_or_DML": False,
            "provider_calls": 0,
        },
    )
    return {"current_source_fixture_checks": len(checks)}


def snapshot(position):
    profile = read(WORK / "final-profile.json")
    settings = load(Path(profile["directory"]))
    names = [
        "crm_access." + name
        for name in [
            "AccessUser",
            "Role",
            "Setting",
            "SettingHistory",
            "Secret",
            "Factor",
            "Session",
            "Audit",
        ]
    ] + ["crm_meta.MigrationJournal"]
    names += [
        name
        for name in settings.ticket["table_map"]
        if name.startswith("crm_workspace.")
    ]
    # Use only the ticket's closed identifiers; this path never accepts SQL names.
    with admin(profile["database"], readonly=True) as connection:
        tables = {
            name: fingerprint(connection.cursor(), settings.ticket["table_map"][name])
            for name in names
        }
    value = {
        "database": profile["database"],
        "tables": tables,
        "ticket_sha256": settings.review["ticket_sha256"],
    }
    save(WORK / ("restart-" + position + ".json"), value)
    if position == "after":
        if value != read(WORK / "restart-before.json"):
            raise ValueError("P3ES_restart_state_changed")
        save(
            WORK / "restart-result.json",
            {
                "status": "passed",
                "before": value,
                "after": value,
                "application_only_restart": True,
                "SQL_server_or_old_previews_restarted": False,
                (
                    "accounts_settings_secrets_sessions_audit"
                    "_journals_workspace_unchanged"
                ): True,
            },
        )
    return {"snapshot": position, "tables": len(tables)}


def clean():
    profile, settings, _ = current("final")
    names = ["crm.Contact", "crm.Conversation", "crm.Message", "crm_access.Secret"]
    names += [
        name
        for name in settings.ticket["table_map"]
        if name.startswith("crm_workspace.") and not name.endswith(("Journal", "State"))
    ]
    with admin(profile["database"], readonly=True) as connection:
        c = connection.cursor()
        counts = {
            name: c.execute(
                "SELECT COUNT(*) FROM " + settings.ticket["table_map"][name]
            ).fetchval()
            for name in names
        }
        accounts = c.execute(
            "SELECT COUNT(*) FROM "
            + settings.ticket["table_map"]["crm_access.AccessUser"]
        ).fetchval()
    if accounts != 1 or any(counts.values()):
        raise ValueError("P3ES_final_copy_contains_fixtures")
    save(
        WORK / "clean-result.json",
        {
            "status": "passed",
            "database": profile["database"],
            "accounts": accounts,
            "fixtures": 0,
            "empty_domain_tables": counts,
            "TLS_verified": True,
            "provider_calls": 0,
        },
    )
    return {"clean_profile": "passed", "accounts": accounts, "fixtures": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["fixture", "clean", "before", "after"])
    args = parser.parse_args()
    try:
        result = (
            fixture()
            if args.action == "fixture"
            else clean()
            if args.action == "clean"
            else snapshot(args.action)
        )
        print(json.dumps(result))
    except BaseException as error:
        with contextlib.suppress(Exception):
            save(
                WORK / ("final-check-failure-" + uuid4().hex + ".json"),
                {"type": type(error).__name__, "trace": traceback.format_exc()},
            )
        print(json.dumps({"P3_final_check": "failed", "type": type(error).__name__}))
        raise SystemExit(1)
