"P3 projection, SLA, pagination and handoff tests using synthetic SQL evidence."

import contextlib
import json
import traceback
from dataclasses import asdict
from datetime import timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

from app.institutional.api import create_app
from app.institutional.spanish import load
from app.institutional.spanish_bindings import Cursor
from app.modules.campaigns.domain.scoring import (
    ChurnInputs,
    ConfirmedResponse,
    IncomingEvidence,
    assess_churn,
)
from tools.prepare_p3_workspace import WORK, admin, read, save
from tools.qualify_p3_workspace import Browser, cmd

checks = []


def check(name, condition=True):
    if not condition:
        raise AssertionError(name)
    checks.append(name)
    save(WORK / "risk-result.json", {"status": "in_progress", "checks": checks})


def main():
    profile = read(WORK / "fixture-r4-profile.json")
    settings = load(Path(profile["directory"]))
    account = read(WORK / "fixture-r4-access.json")
    browser = Browser(create_app(settings))
    signed = browser.login(account["email"], account["password"])
    records = read(WORK / "fixture-records.json")
    if (WORK / "risk-volume-ready.json").exists():
        volume = read(WORK / "risk-volume-ready.json")
        if volume["database"] != profile["database"]:
            raise ValueError("P3ES_volume_scope_mismatch")
        previous = read(WORK / "risk-result.json")
        checks.extend(previous["checks"])
        return finish_volume(profile, browser, records)
    contact, conversation = records["volume_ids"][582]
    if (WORK / "risk-seed.json").exists():
        seed = read(WORK / "risk-seed.json")
        if seed["database"] != profile["database"]:
            raise ValueError("P3ES_seed_database_mismatch")
        previous = read(WORK / "risk-result.json")
        checks.extend(previous["checks"])
        return continue_projection(
            profile,
            settings,
            browser,
            signed,
            records,
            seed["contactId"],
            seed["conversationId"],
            seed["assessmentId"],
            seed["score"],
        )
    save(
        WORK / "risk-private-v2.json",
        {
            "database": profile["database"],
            "contactId": contact,
            "conversationId": conversation,
        },
    )
    prior = read(WORK / "risk-result.json")
    expected = [
        "SLA_starts_unconfigured",
        "SLA_filter_before_pagination_is_operator_debt",
        "SLA_is_not_churn",
    ]
    if (
        prior["checks"] != expected
        or read(WORK / "risk-private.json")["database"] != profile["database"]
    ):
        raise ValueError("P3ES_prior_SLA_evidence_mismatch")
    save(WORK / "risk-attempt-v1-result.json", prior)
    checks.extend(expected)
    policy = browser.get("policy")
    check(
        ("prior_SLA_configuration_preserved_for_projection_fixture"),
        policy["enabled"] is True and policy["thresholdMinutes"] == 30,
    )
    # A persisted completed rule run is a controlled input fixture, never a claim
    # of current provider connectivity or a live authenticated webhook execution.
    incoming, outgoing, identity, queue, run = map(
        str, [uuid4(), uuid4(), uuid4(), uuid4(), uuid4()]
    )
    with admin(profile["database"]) as connection:
        c = Cursor(connection.cursor(), settings.ticket["table_map"])
        now = (
            c.execute("SELECT SYSUTCDATETIME()").fetchval().replace(tzinfo=timezone.utc)
        )
        at = now - timedelta(days=6)
        sent = now - timedelta(days=5)
        c.execute(
            (
                "IF NOT EXISTS(SELECT 1 FROM crm_channels"
                ".Account WHERE Channel='whatsapp') INSER"
                "T crm_channels.Account(Channel,Configura"
                "tion) VALUES('whatsapp','{}')"
            )
        )
        c.execute(
            (
                "INSERT crm_channels.ExternalIdentity(Ide"
                "ntityId,Channel,ExternalId,ContactId,Con"
                "versationId) VALUES(?,'whatsapp','p3-con"
                "trolled-fixture-v2',?,?)"
            ),
            identity,
            contact,
            conversation,
        )
        c.execute(
            (
                "INSERT crm.Message(MessageId,Conversatio"
                "nId,Body,Direction,CreatedAt) VALUES(?,?"
                ",?,'incoming',?)"
            ),
            incoming,
            conversation,
            "Solicitud controlada",
            at.replace(tzinfo=None),
        )
        sequence_in = c.execute(
            ("SELECT Sequence FROM crm.Message WHERE MessageId=?"), incoming
        ).fetchval()
        c.execute(
            (
                "INSERT crm.Message(MessageId,Conversatio"
                "nId,Body,Direction,CreatedAt) VALUES(?,?"
                ",?,'outgoing',?)"
            ),
            outgoing,
            conversation,
            "Respuesta confirmada de prueba",
            sent.replace(tzinfo=None),
        )
        sequence_out = c.execute(
            ("SELECT Sequence FROM crm.Message WHERE MessageId=?"), outgoing
        ).fetchval()
        c.execute(
            (
                "INSERT crm_channels.outbound_queue(Queue"
                "Id,Channel,IdentityId,MessageId,Payload,"
                "State,ExternalId) VALUES(?,'whatsapp',?,"
                "?,?,'delivered','p3-fixture-delivery-v2'"
                ")"
            ),
            queue,
            identity,
            outgoing,
            json.dumps({"replyToMessageId": incoming}),
        )
        for message, kind, q in [
            (incoming, "external", None),
            (outgoing, "human", queue),
        ]:
            c.execute(
                (
                    "INSERT crm_channels.MessageRoute(Message"
                    "Id,IdentityId,QueueId,ActorKind,ControlE"
                    "poch,CompletedAt) VALUES(?,?,?,?,NULL,?)"
                ),
                message,
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
        inputs = ChurnInputs(
            UUID(conversation),
            now,
            "open",
            "Nueva",
            sequence_out,
            IncomingEvidence(UUID(incoming), UUID(identity), sequence_in, at),
            (
                ConfirmedResponse(
                    UUID(outgoing),
                    UUID(identity),
                    UUID(queue),
                    UUID(incoming),
                    sequence_out,
                    sent,
                    "provider_delivered",
                    uuid4(),
                ),
            ),
            True,
        )
        result = assess_churn(inputs, {"Nueva": 25})
        assert result.status == "known" and result.level == "high"
        assessment = str(uuid4())
        evidence = json.dumps(asdict(result), default=str)
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
            conversation,
            identity,
            now.replace(tzinfo=None),
            sequence_out,
            result.formula_version,
            result.status,
            result.score,
            result.level,
            "Nueva",
            result.waiting_since.replace(tzinfo=None),
            json.dumps(result.reasons),
            evidence,
            run,
        )
    save(
        WORK / "risk-seed.json",
        {
            "contactId": contact,
            "conversationId": conversation,
            "assessmentId": assessment,
            "score": result.score,
            "database": profile["database"],
        },
    )
    return continue_projection(
        profile,
        settings,
        browser,
        signed,
        records,
        contact,
        conversation,
        assessment,
        result.score,
    )


def continue_projection(
    profile,
    settings,
    browser,
    signed,
    records,
    contact,
    conversation,
    assessment,
    expected_score,
):
    detail = browser.get("conversations/" + conversation)
    inbox = browser.get("inbox/" + conversation + "/detail")
    listing = browser.get("clients?q=P3%20volumen%200582")
    check(
        ("one_rule_projection_shared_by_CRM_Inbox_and_miniCRM"),
        detail["risk"] == inbox["risk"]
        and listing["items"][0]["risk"] == detail["risk"]
        and detail["risk"]["status"] == "known"
        and detail["risk"]["source"] == "rule"
        and detail["risk"]["trainedPrediction"] is False,
    )
    check(
        ("high_churn_filter_uses_same_current_SQL_evidence"),
        browser.get("inbox?queue=churn")["total"] == 1,
    )
    browser.write(
        "conversations/" + conversation + "/manual",
        cmd(detail["revision"], score=5, temperature="cold"),
    )
    after = browser.get("conversations/" + conversation)
    check(
        "manual_score_separate_from_rule",
        after["manual"]["score"] == 5 and after["risk"]["score"] == expected_score,
    )
    with admin(profile["database"]) as connection:
        c = Cursor(connection.cursor(), settings.ticket["table_map"])
        c.execute(
            (
                "UPDATE crm_marketing.ChurnAssessment SET"
                " AsOfUtc=DATEADD(day,-2,SYSUTCDATETIME()"
                ") WHERE AssessmentId=?"
            ),
            assessment,
        )
    check(
        ("stale_rule_never_appears_as_current_or_high_queue"),
        browser.get("conversations/" + conversation)["risk"]["status"] == "unknown"
        and browser.get("inbox?queue=churn")["total"] == 0,
    )
    with admin(profile["database"]) as connection:
        c = Cursor(connection.cursor(), settings.ticket["table_map"])
        c.execute(
            (
                "UPDATE crm_marketing.ChurnAssessment SET"
                " AsOfUtc=SYSUTCDATETIME() WHERE Assessme"
                "ntId=?"
            ),
            assessment,
        )
        c.execute(
            (
                "INSERT crm.Message(MessageId,Conversatio"
                "nId,Body,Direction) VALUES(?,?,?,'incomi"
                "ng')"
            ),
            str(uuid4()),
            conversation,
            "Nueva evidencia invalida el watermark",
        )
    check(
        "new_incoming_invalidates_existing_evaluation",
        browser.get("conversations/" + conversation)["risk"]["status"] == "unknown"
        and browser.get("inbox?queue=churn")["total"] == 0,
    )
    # No sender is configured: taking control cancels only bot jobs that have not
    # started.
    target_contact, target_conversation = records["volume_ids"][581]
    with admin(profile["database"]) as connection:
        c = Cursor(connection.cursor(), settings.ticket["table_map"])
        bot_identity, bot_message, bot_queue = map(str, [uuid4(), uuid4(), uuid4()])
        c.execute(
            (
                "INSERT crm_channels.ExternalIdentity(Ide"
                "ntityId,Channel,ExternalId,ContactId,Con"
                "versationId) VALUES(?,'whatsapp','p3-bot"
                "-fixture',?,?)"
            ),
            bot_identity,
            target_contact,
            target_conversation,
        )
        c.execute(
            (
                "INSERT crm.Message(MessageId,Conversatio"
                "nId,Body,Direction) VALUES(?,?,?,'outgoi"
                "ng')"
            ),
            bot_message,
            target_conversation,
            "Bot pendiente de prueba",
        )
        c.execute(
            (
                "INSERT crm_channels.outbound_queue(Queue"
                "Id,Channel,IdentityId,MessageId,Payload,"
                "State) VALUES(?,'whatsapp',?,?,'{}','que"
                "ued')"
            ),
            bot_queue,
            bot_identity,
            bot_message,
        )
        c.execute(
            (
                "INSERT crm_channels.MessageRoute(Message"
                "Id,IdentityId,QueueId,ActorKind,ControlE"
                "poch) VALUES(?,?,?,'bot',0)"
            ),
            bot_message,
            bot_identity,
            bot_queue,
        )
        c.execute(
            ("UPDATE crm.Conversation SET ControlMode='ai' WHERE ConversationId=?"),
            target_conversation,
        )
    detail = browser.get("conversations/" + target_conversation)
    browser.write(
        "conversations/" + target_conversation,
        cmd(
            detail["revision"],
            state="open",
            priority="normal",
            mode="human",
            userId=signed["user"]["id"],
            unread=True,
        ),
    )
    with admin(profile["database"], readonly=True) as connection:
        c = Cursor(connection.cursor(), settings.ticket["table_map"])
        state = c.execute(
            ("SELECT State,LastError FROM crm_channels.outbound_queue WHERE QueueId=?"),
            bot_queue,
        ).fetchone()
        epoch = c.execute(
            (
                "SELECT Epoch FROM crm_channels.Conversat"
                "ionControl WHERE ConversationId=?"
            ),
            target_conversation,
        ).fetchval()
    check(
        ("human_takeover_increments_epoch_and_cancels_unstarted_bot"),
        tuple(state) == ("failed", "control_epoch_obsolete") and epoch == 1,
    )
    browser.write(
        "conversations/" + target_conversation + "/messages",
        cmd(browser.get("clients")["revision"], body="No entrega externa"),
        method="POST",
        expected=409,
    )
    check("provider_route_cannot_be_sent_as_local")
    anchor = browser.get("clients")["revision"]
    detail = browser.get("conversations/" + records["conversationId"])
    browser.write(
        "clients/" + records["contactId"],
        cmd(
            detail["revision"], client=dict(detail["client"], city="Ciudad del anclaje")
        ),
    )
    browser.request("workspace/clients?offset=25&anchor=" + anchor, expected=409)
    check("changed_revision_rejects_stale_page_anchor")
    browser.request(
        "workspace/conversations/"
        + conversation
        + "/messages?before=9999999999999999999",
        expected=422,
    )
    check("bigint_cursor_overflow_rejected_at_boundary")
    # Permission and module enforcement remain inside the actual business transaction.
    modules = browser.request("settings/modules").json()
    document = modules["document"]
    document["enabled"]["inbox"] = False
    browser.request(
        "settings/modules",
        "PUT",
        {
            "operation_id": str(uuid4()),
            "revision": modules["revision"],
            "document": document,
        },
    )
    browser.request("workspace/inbox", expected=403)
    current = browser.request("settings/modules").json()
    current["document"]["enabled"]["inbox"] = True
    browser.request(
        "settings/modules",
        "PUT",
        {
            "operation_id": str(uuid4()),
            "revision": current["revision"],
            "document": current["document"],
        },
    )
    check("disabled_module_denied_and_restored")
    # Force >50 messages and >25 tasks; no in-memory global snapshot is needed.
    with admin(profile["database"]) as connection:
        c = Cursor(connection.cursor(), settings.ticket["table_map"])
        c.execute("BEGIN TRANSACTION")
        try:
            for index in range(105):
                c.execute(
                    (
                        "INSERT crm.Message(MessageId,Conversatio"
                        "nId,Body,Direction) VALUES(?,?,?,'incomi"
                        "ng')"
                    ),
                    str(uuid4()),
                    records["conversationId"],
                    "Histórico QA " + str(index),
                )
            for index in range(58):
                c.execute(
                    (
                        "INSERT crm_workspace.Task(TaskId,Institu"
                        "tionId,ConversationId,Title,Status,Prior"
                        "ity) VALUES(?,?,?,?,'pending','normal')"
                    ),
                    str(uuid4()),
                    settings.ticket["context"][0][1],
                    records["conversationId"],
                    "Volumen tarea " + str(index),
                )
            c.execute("COMMIT")
        except BaseException:
            c.execute("IF @@TRANCOUNT>0 ROLLBACK")
            raise
    save(
        WORK / "risk-volume-ready.json",
        {
            "database": profile["database"],
            "contactId": records["contactId"],
            "conversationId": records["conversationId"],
        },
    )
    return finish_volume(profile, browser, records)


def finish_volume(profile, browser, records):
    latest = browser.get("conversations/" + records["conversationId"] + "/messages")
    older = browser.get(
        "conversations/"
        + records["conversationId"]
        + "/messages?before="
        + latest["before"]
    )
    check(
        "message_cursor_no_overlap_and_fixed_SQL_bound",
        latest["hasMore"]
        and older["hasMore"]
        and len(latest["items"]) == 50
        and len(older["items"]) == 50
        and not {r["id"] for r in latest["items"]} & {r["id"] for r in older["items"]},
    )
    tasks = browser.get("tasks?q=Volumen")
    next_tasks = browser.get("tasks?q=Volumen&offset=25&anchor=" + tasks["revision"])
    check(
        "tasks_filter_and_pagination_before_slice",
        tasks["total"] == 58
        and next_tasks["total"] == 58
        and len(tasks["items"]) == 25
        and len(next_tasks["items"]) == 25
        and not {r["id"] for r in tasks["items"]}
        & {r["id"] for r in next_tasks["items"]},
    )
    save(
        WORK / "risk-result.json",
        {
            "status": "passed",
            "database": profile["database"],
            "checks": list(dict.fromkeys(checks)),
            "count": len(set(checks)),
            "check_instances": len(checks),
            "source_scope": "synthetic_completed_rule_run_fixture",
            "live_provider_acceptance": False,
            "provider_calls": 0,
            "academic_DDL_or_DML": False,
        },
    )
    print(json.dumps({"P3_risk_and_operations": "passed", "checks": len(checks)}))


if __name__ == "__main__":
    try:
        main()
    except BaseException as error:
        with contextlib.suppress(Exception):
            save(
                WORK / ("risk-failure-" + uuid4().hex + ".json"),
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
                    "P3_risk_and_operations": "failed",
                    "type": type(error).__name__,
                    "last_check": checks[-1] if checks else None,
                }
            )
        )
        raise SystemExit(1)
