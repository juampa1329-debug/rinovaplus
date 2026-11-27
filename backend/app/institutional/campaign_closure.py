"""Shorten the general silence closure without replaying completed steps."""

import json
from copy import deepcopy
from datetime import timedelta
from uuid import UUID, uuid5

from fastapi import HTTPException

from app.institutional.db import institution, one, rows
from app.institutional.campaign_models import document, now, next_allowed
from app.institutional.campaigns import event, get, issues, key, packed, public, authority


def target(flow, trigger, days):
    doc = json.loads(flow["Document"])
    bound = json.loads(trigger["Document"])
    steps = doc.get("steps", [])
    if (
        days != 7 or flow["Kind"] != "flow" or flow["State"] != "active"
        or not doc.get("followup_only") or not doc.get("exit_on_response")
        or doc.get("entry_conditions", {}).get("followup_states")
        or [v["kind"] for v in steps] != ["send", "wait", "send", "wait", "send", "wait", "send"]
        or not steps[-1].get("meta_template_id")
        or trigger["State"] != "active" or bound.get("event_type") != "inactivity"
        or str(bound.get("flow_id")) != str(flow["RecordId"])
        or bound.get("flow_version") != flow["CurrentVersion"]
        or bound.get("channel") != doc.get("channel")
        or bound.get("conditions", {}).get("followup_states")
        or bound.get("idle_minutes") != 480
        or [steps[i]["wait_minutes"] for i in (1, 3)] != [1680, 1440]
    ):
        raise HTTPException(409, "campaign_closure_scope_changed")
    minutes = days * 1440 - bound["idle_minutes"] - sum(
        v["wait_minutes"] for v in steps[:-2] if v["kind"] == "wait"
    )
    if not 0 < minutes < steps[-2]["wait_minutes"]:
        raise HTTPException(409, "campaign_closure_not_shorter")
    changed = deepcopy(doc)
    changed["steps"][-2]["wait_minutes"] = minutes
    changed["steps"][-2]["name"] = "Esperar hasta el cierre · 7 días"
    changed["steps"][-1]["name"] = "Cierre respetuoso · 7 días"
    # Only timing and human labels change; approved template and all bindings stay.
    return document("flow", changed), minutes - steps[-2]["wait_minutes"]


def waiting_due(run, step, delta, quiet, moment):
    if run["StepIndex"] != 5 or not step:
        return run["DueAt"]
    return next_allowed(max(moment, step["DueAt"] + timedelta(minutes=delta)), quiet)


def version(c, s, record, doc, name, actor, body):
    c.execute(
        "UPDATE crm_campaign8.Record SET Name=?,Document=?,Revision=Revision+1,"
        "CurrentVersion=CurrentVersion+1,Epoch=Epoch+1,ActorId=?,ActorAuthVersion=?,"
        "ActorSessionId=?,ApprovedAt=SYSUTCDATETIME(),UpdatedAt=SYSUTCDATETIME() "
        "WHERE InstitutionId=? AND RecordId=? AND Revision=? AND State='active'",
        name, packed(doc), actor["UserId"], actor["AuthVersion"], actor["SessionId"],
        institution(s), record["RecordId"], record["Revision"],
    )
    if c.rowcount != 1:
        raise HTTPException(409, "revision_conflict")
    c.execute(
        "INSERT crm_campaign8.Version(InstitutionId,RecordId,VersionNo,Kind,Name,"
        "Document,Reason,ActorId,OperationId) VALUES(?,?,?,?,?,?,?,?,?)",
        institution(s), record["RecordId"], record["CurrentVersion"] + 1,
        record["Kind"], name, packed(doc), body.reason, actor["UserId"],
        str(uuid5(UUID(str(body.operation_id)), "closure-version:" + str(record["RecordId"]))),
    )


def shorten(c, s, flow, actor, body, *, controlled=False):
    from app.institutional.campaign_runtime import guard, stop

    pre = one(c, "SELECT * FROM crm_campaign8.Event WHERE InstitutionId=? AND "
              "EventId=? AND RecordId=? AND Kind='preflight'", institution(s),
              str(body.preflight_id), flow["RecordId"])
    expected = dict(actor=actor["UserId"], session=actor["SessionId"],
                    auth_version=actor["AuthVersion"], record_revision=flow["Revision"],
                    record_hash=key(flow["Document"]), issues=[])
    if (not pre or pre["CreatedAt"] < now() - timedelta(minutes=10)
            or json.loads(pre["Document"]) != expected):
        raise HTTPException(409, "campaign_preflight_required")
    triggers = rows(c, "SELECT TOP(501) * FROM crm_campaign8.Record WHERE "
                    "InstitutionId=? AND Kind='trigger'", institution(s))
    bound = [v for v in triggers if
             str(json.loads(v["Document"]).get("flow_id")) == str(flow["RecordId"])]
    if len(triggers) > 500 or len(bound) != 1:
        raise HTTPException(409, "campaign_closure_scope_changed")
    trigger = bound[0]
    doc, delta = target(flow, trigger, body.closure_days)
    authority(c, s, flow)
    authority(c, s, trigger)
    proposal = dict(flow, Document=packed(doc))
    if issues(c, s, proposal, controlled=controlled):
        raise HTTPException(409, "campaign_preflight_invalid")
    runs = rows(c, "SELECT TOP(501) * FROM crm_campaign8.Enrollment WHERE "
                "InstitutionId=? AND FlowId=? AND VersionNo=? AND FlowEpoch=? "
                "AND State IN('waiting','queued','paused','uncertain')",
                institution(s), flow["RecordId"], flow["CurrentVersion"], flow["Epoch"])
    if len(runs) > 500:
        raise HTTPException(409, "campaign_closure_busy")
    prepared = []
    for run in runs:
        if (run["State"] != "waiting" or run["StepIndex"] not in {1, 3, 5}
                or str(run["TriggerId"]) != str(trigger["RecordId"])
                or run["TriggerVersion"] != trigger["CurrentVersion"]
                or run["VersionNo"] != flow["CurrentVersion"]
                or run["FlowEpoch"] != flow["Epoch"]):
            raise HTTPException(409, "campaign_closure_busy")
        steps = rows(c, "SELECT * FROM crm_campaign8.Step WHERE InstitutionId=? "
                     "AND EnrollmentId=?", institution(s), run["EnrollmentId"])
        current = next((v for v in steps if v["StepIndex"] == run["StepIndex"]), None)
        if any(v["StepIndex"] > run["StepIndex"] or
               (v["StepIndex"] < run["StepIndex"] and v["State"] != "completed")
               for v in steps) or (current and (current["Kind"] != "wait" or
                                                current["State"] != "waiting")):
            raise HTTPException(409, "campaign_closure_busy")
        denied = None
        try:
            guard(c, s, run)
        except HTTPException as exc:
            if exc.status_code != 409:
                raise
            denied = exc.detail
        prepared.append((run, current, denied))

    next_trigger = json.loads(trigger["Document"])
    next_trigger["flow_version"] = flow["CurrentVersion"] + 1
    version(c, s, flow, doc,
            "CRM · Seguimiento consultivo · 8h, 36h, 60h y cierre 7d · CBN", actor, body)
    version(c, s, trigger, document("trigger", next_trigger), trigger["Name"], actor, body)
    preserved = stopped = 0
    for run, step, denied in prepared:
        if denied:
            stop(c, s, run, denied)
            stopped += 1
            continue
        due = waiting_due(run, step, delta, doc["quiet_hours"], now())
        if step and run["StepIndex"] == 5:
            c.execute("UPDATE crm_campaign8.Step SET DueAt=? WHERE InstitutionId=? "
                      "AND StepId=? AND State='waiting'", due, institution(s), step["StepId"])
            if c.rowcount != 1:
                raise HTTPException(409, "campaign_closure_busy")
        c.execute(
            "UPDATE crm_campaign8.Enrollment SET VersionNo=?,FlowEpoch=?,TriggerVersion=?,"
            "DueAt=?,UpdatedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND EnrollmentId=? "
            "AND State='waiting' AND VersionNo=? AND FlowEpoch=? AND TriggerVersion=? AND StepIndex=?",
            flow["CurrentVersion"] + 1, flow["Epoch"] + 1, trigger["CurrentVersion"] + 1,
            due, institution(s), run["EnrollmentId"], run["VersionNo"], run["FlowEpoch"],
            run["TriggerVersion"], run["StepIndex"],
        )
        if c.rowcount != 1:
            raise HTTPException(409, "campaign_closure_busy")
        event(c, s, "closure_rescheduled", dict(old_version=run["VersionNo"],
              new_version=flow["CurrentVersion"] + 1, closure_days=7,
              step_index=run["StepIndex"], previous_due=run["DueAt"].isoformat(),
              due=due.isoformat()), record=str(flow["RecordId"]),
              enrollment=str(run["EnrollmentId"]), actor=actor["UserId"],
              source=key("closure", body.operation_id, run["EnrollmentId"]))
        preserved += 1
    result = public(get(c, s, str(flow["RecordId"])))
    result["reschedule"] = dict(closure_days=7, preserved=preserved, stopped=stopped,
                                trigger_version=trigger["CurrentVersion"] + 1)
    event(c, s, "closure_rescheduled_summary", result["reschedule"],
          record=str(flow["RecordId"]), actor=actor["UserId"],
          source=key("closure-summary", body.operation_id))
    return result
