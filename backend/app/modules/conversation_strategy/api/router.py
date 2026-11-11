"""Versioned plans and internal follow-up under the existing workspace lock."""

import json
import sys
from uuid import UUID, uuid4

from fastapi import HTTPException

from app.modules.conversation_analysis.domain.models import PROMPT_VERSION, redact
from app.modules.conversation_analysis.api.router import STATE_SELECT, ConversationAnalysis, digest
from app.modules.inbox.application.service import rows as inbox_rows
from app.modules.inbox.application.operations import InboxOperations
from app.sql_workspace_shape import SHAPE_SQL

STRATEGY_SHAPE = SHAPE_SQL.replace("N'crm'", "N'crm_strategy'").replace(
    "N'crm.shape'", "N'crm_strategy.shape'"
)
PLAN_SELECT = """SELECT TOP(1) PlanId AS id,Generation AS generation,
 AnalysisRevision AS revision,Fingerprint AS fingerprint,Binding AS binding,
 SemanticFingerprint AS semanticFingerprint,DocumentJson AS documentJson,
 Provider AS provider,Model AS model,PromptVersion AS promptVersion,
 PolicyRevision AS policyRevision,CreatedAt AS createdAt
 FROM crm_strategy.EvaluationPlan WHERE ConversationId=?
 ORDER BY AnalysisRevision DESC,PlanId"""


def rows(cursor):
    """Honor the legacy bridge while the migration compatibility window is open."""
    legacy = getattr(sys.modules.get(__name__), "rows", None)
    if legacy is not None and legacy is not rows:
        return legacy(cursor)
    return inbox_rows(cursor)


def present(c, required=False):
    legacy = getattr(sys.modules.get(__name__), "present", None)
    if legacy is not None and legacy is not present:
        return legacy(c, required=True) if required else legacy(c)
    row = c.execute("SELECT SCHEMA_ID(N'crm_strategy')").fetchone()
    if row is None or row[0] is None:
        if required:
            raise HTTPException(503, "strategy_not_installed")
        return False
    version = c.execute(
        "SELECT CONVERT(nvarchar(128),value) FROM sys.extended_properties "
        "WHERE class=3 AND major_id=SCHEMA_ID(N'crm_strategy') "
        "AND name=N'crm_strategy.contract'"
    ).fetchval()
    if version != "strategy-v1" or not c.execute(STRATEGY_SHAPE).fetchval():
        raise HTTPException(503, "strategy_shape_changed")
    return True


def semantic_fingerprint(c, conversation):
    """Control/task metadata does not change the evidence submitted to inference."""
    legacy = getattr(
        sys.modules.get(__name__), "semantic_fingerprint", None
    )
    if legacy is not None and legacy is not semantic_fingerprint:
        return legacy(c, conversation)
    from app.modules.contacts.application.merge import membership

    contact = str(
        c.execute(
            "SELECT ContactId FROM crm.Conversation WHERE ConversationId=?",
            conversation,
        ).fetchone()[0]
    )
    messages = [
        tuple(r)
        for r in c.execute(
            "SELECT MessageId,Sequence,Direction,Body FROM crm.Message "
            "WHERE ConversationId=? ORDER BY Sequence",
            conversation,
        ).fetchall()
    ]
    feedback = [
        tuple(r)
        for r in c.execute(
            "SELECT FeedbackId,SourceRevision,Text FROM crm_analysis.Feedback "
            "WHERE ConversationId=? ORDER BY FeedbackId",
            conversation,
        ).fetchall()
    ]
    context = c.execute(
        "SELECT ContextJson,ContextGeneration,ContextProvider,ContextModel,"
        "ContextPromptVersion,ContextPolicyRevision "
        "FROM crm_analysis.ConversationState "
        "WHERE ConversationId=?",
        conversation,
    ).fetchone()
    return digest(
        [
            messages,
            feedback,
            tuple(context) if context else None,
            membership(c, contact),
            ConversationAnalysis.identity(c, conversation),
        ]
    )


def save_plan(c, job, document):
    if document is None or not present(c):
        return
    # Historical suppression is evaluated separately; never rewrite model provenance.
    c.execute(
        """INSERT crm_strategy.EvaluationPlan(PlanId,ConversationId,Generation,
        AnalysisRevision,Fingerprint,Binding,SemanticFingerprint,DocumentJson,
        Provider,Model,PromptVersion,PolicyRevision)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
        str(uuid4()),
        job["id"],
        job["generation"],
        job["revision"] + 1,
        job["fingerprint"],
        job["binding"],
        semantic_fingerprint(c, job["id"]),
        json.dumps(document, ensure_ascii=False),
        job["policy"]["provider"],
        job["policy"]["model"],
        PROMPT_VERSION,
        int(job["policy"]["revision"]),
    )


def no_contact(c, conversation):
    from app.modules.contacts.application.merge import historical_ids

    contact = str(
        c.execute(
            "SELECT ContactId FROM crm.Conversation WHERE ConversationId=?",
            conversation,
        ).fetchone()[0]
    )
    ids = sorted(historical_ids(c, contact))
    return bool(
        c.execute(
            """SELECT TOP(1) 1 FROM crm_strategy.EvaluationPlan p
        JOIN crm.Conversation v
        ON v.ConversationId=p.ConversationId WHERE v.ContactId IN
        (SELECT CONVERT(uniqueidentifier,value) FROM OPENJSON(?))
        AND JSON_VALUE(p.DocumentJson,'$.noContact')='true'""",
            json.dumps(ids),
        ).fetchval()
    )


class ConversationStrategy:
    def __init__(self, workspace):
        self.workspace = workspace

    @staticmethod
    def revision(c):
        return str(
            c.execute(
                "SELECT COALESCE(MAX(Revision),0) FROM crm_strategy.Operation"
            ).fetchval()
        )

    @staticmethod
    def policy(c, key):
        return bool(
            c.execute(
                "SELECT Enabled FROM crm_strategy.Policy WHERE ScopeKey=?", key
            ).fetchval()
        )

    def inspect(self, c, conversation, binding):
        found = c.execute(
            "SELECT ControlMode,State FROM crm.Conversation WHERE ConversationId=?",
            conversation,
        ).fetchone()
        if not found:
            raise HTTPException(404, "conversation_not_found")
        plan_rows = rows(c.execute(PLAN_SELECT, conversation))
        plan = plan_rows[0] if plan_rows else None
        state_rows = rows(c.execute(STATE_SELECT, conversation))
        state = state_rows[0] if state_rows else None
        policy = ConversationAnalysis.policy(c)
        requested = self.policy(c, conversation)
        paused = self.policy(c, "global")
        reasons = []
        if paused:
            reasons.append("global_pause")
        if not requested:
            reasons.append("not_requested")
        if found[0] != "ai":
            reasons.append("human_control")
        if found[1] == "closed":
            reasons.append("conversation_closed")
        if not policy or not policy["enabled"] or not binding or ":False:" in binding:
            reasons.append("analysis_unavailable")
        coverage = (
            ConversationAnalysis.coverage(c, conversation, state["generation"])
            if state
            else None
        )
        current = bool(
            plan
            and state
            and coverage["coveredMessages"] == coverage["totalMessages"]
            and coverage["pendingReferences"] == 0
            and state["status"] == "current"
            and state["generation"] == plan["generation"]
            and state["contextGeneration"] == plan["generation"]
            and plan["binding"] == binding
            and plan["promptVersion"] == PROMPT_VERSION
            and plan["semanticFingerprint"] == semantic_fingerprint(c, conversation)
            and state["fingerprint"]
            == ConversationAnalysis.fingerprint(c, conversation)
        )
        if not current:
            reasons.append("plan_missing_or_stale")
        document = json.loads(plan["documentJson"]) if plan else None
        if not document or not document["followupSupported"]:
            reasons.append("insufficient_incoming_evidence")
        if no_contact(c, conversation):
            reasons.append("no_contact")
        if c.execute(
            "SELECT TOP(1) 1 FROM crm_inbox.Task "
            "WHERE ConversationId=? AND Status='pending'",
            conversation,
        ).fetchval():
            reasons.append("pending_task")
        if (
            plan
            and c.execute(
                "SELECT TOP(1) 1 FROM crm_strategy.Operation "
                "WHERE PlanId=? AND Action='task_create'",
                plan["id"],
            ).fetchval()
        ):
            reasons.append("plan_already_executed")
        assignment = c.execute(
            """SELECT a.HumanEmployeeId,CASE WHEN m.Enabled=1 AND e.Actvo=1
            THEN 1 ELSE 0 END,CASE WHEN g.Enabled=1 THEN 1 ELSE 0 END
            FROM crm_inbox.Assignment a
            LEFT JOIN crm_inbox.Member m ON m.EmployeeId=a.HumanEmployeeId
            LEFT JOIN dbo.GEEmpleado e ON e.CnsctvoEmpldo=a.HumanEmployeeId
            LEFT JOIN crm_inbox.Agent g ON g.AgentId=a.AiAgentId
            WHERE a.ConversationId=?""",
            conversation,
        ).fetchone()
        employee = assignment[0] if assignment else None
        if employee is not None and not assignment[1]:
            reasons.append("human_assignee_unavailable")
        if not assignment or not assignment[2]:
            reasons.append("ai_assignee_unavailable")
        if c.execute(
            """SELECT TOP(1) 1 FROM crm_strategy.Operation WHERE ConversationId=?
                     AND Action='feedback'
                     AND JSON_VALUE(DocumentJson,'$.outcome')='no_contact'""",
            conversation,
        ).fetchval():
            reasons.append("operator_no_contact_report")
        from app.modules.contacts.application.merge import analysis_guard, historical_ids

        contact = str(
            c.execute(
                "SELECT ContactId FROM crm.Conversation WHERE ConversationId=?",
                conversation,
            ).fetchone()[0]
        )
        try:
            analysis_guard(c, historical_ids(c, contact))
        except HTTPException as error:
            if error.status_code != 409 or error.detail != "analysis_attempt_reserved":
                raise
            reasons.append("analysis_reserved")
        return (
            plan,
            document,
            state,
            employee,
            {
                "requested": requested,
                "globalPaused": paused,
                "effective": not reasons,
                "reasons": reasons,
                "planCurrent": current,
            },
        )

    def read(self, conversation, binding):
        with self.workspace.transaction() as c:
            present(c, required=True)
            ConversationAnalysis.verify(c)
            plan, document, state, _, autonomy = self.inspect(c, conversation, binding)
            known = ConversationAnalysis.identity(c, conversation)
            if document:
                for key in (
                    "signals",
                    "recommendations",
                    "objections",
                    "remarketing",
                    "drafts",
                ):
                    for item in document[key]:
                        item["text"] = redact(item["text"], known)
                document["churn"]["text"] = redact(document["churn"]["text"], known)
            metrics = rows(
                c.execute(
                    """SELECT COUNT_BIG(CASE WHEN Action='task_create'
                    THEN 1 END) AS tasksCreated,
                COUNT_BIG(CASE WHEN Action='feedback' THEN 1 END) AS feedback,
                COUNT_BIG(CASE WHEN Action='feedback' AND
                 JSON_VALUE(DocumentJson,'$.usefulness')='useful' THEN 1 END) AS useful
                FROM crm_strategy.Operation WHERE ConversationId=?""",
                    conversation,
                )
            )[0]
            return {
                "revision": self.revision(c),
                "conversationId": conversation,
                "autonomy": autonomy,
                "metrics": metrics,
                "plan": document,
                "provenance": {
                    k: plan[k]
                    for k in (
                        "id",
                        "revision",
                        "generation",
                        "provider",
                        "model",
                        "promptVersion",
                        "policyRevision",
                        "createdAt",
                    )
                }
                if plan
                else None,
                "analysisRevision": str(state["revision"]) if state else "0",
                "validation": {
                    "analysisRevision": str(state["revision"]) if state else "0",
                    "current": autonomy["planCurrent"],
                    "scope": "current_source_guard_not_new_inference",
                },
                "rubric": ["interest", "next_step", "commitment"],
                "scope": "selected_conversation_internal_tasks_only",
            }

    def mutate(self, conversation, action, body, binding):
        payload_hash = bytes.fromhex(
            digest([conversation, action, body.model_dump(exclude={"operationId"})])
        )
        with self.workspace.transaction(write=True) as c:
            present(c, required=True)
            ConversationAnalysis.verify(c)
            previous = c.execute(
                "SELECT PayloadHash,DocumentJson FROM crm_strategy.Operation "
                "WHERE OperationId=?",
                body.operationId,
            ).fetchone()
            if previous:
                if bytes(previous[0]) != payload_hash:
                    raise HTTPException(409, "strategy_operation_conflict")
                return json.loads(previous[1])["response"]
            if self.revision(c) != body.expectedRevision:
                raise HTTPException(409, "strategy_revision_conflict")
            plan, _, state, _, _ = self.inspect(c, conversation, binding)
            document = {}
            if action in ("autonomy", "pause"):
                key = conversation if action == "autonomy" else "global"
                enabled = body.enabled if action == "autonomy" else body.paused
                if c.execute(
                    "SELECT 1 FROM crm_strategy.Policy WHERE ScopeKey=?", key
                ).fetchval():
                    c.execute(
                        "UPDATE crm_strategy.Policy SET Enabled=? WHERE ScopeKey=?",
                        enabled,
                        key,
                    )
                else:
                    c.execute(
                        "INSERT crm_strategy.Policy(ScopeKey,ConversationId,Enabled) "
                        "VALUES(?,?,?)",
                        key,
                        conversation if action == "autonomy" else None,
                        enabled,
                    )
            else:
                if (
                    not plan
                    or str(plan["id"]).lower() != str(UUID(body.planId))
                    or plan["revision"] != body.planRevision
                ):
                    raise HTTPException(409, "strategy_plan_conflict")
                text = redact(
                    body.correction, ConversationAnalysis.identity(c, conversation)
                )
                document = {
                    "usefulness": body.usefulness,
                    "outcome": body.outcome,
                    "correction": text,
                }
                # Operator evidence remains explicitly attributed to an operator.
                feedback_text = (
                    "Evaluación de propuesta: "
                    + body.usefulness
                    + "; resultado observado: "
                    + body.outcome
                )
                if text:
                    feedback_text += ". Corrección del operador: " + text
                c.execute(
                    """INSERT crm_analysis.Feedback(
                          FeedbackId,ConversationId,SourceRevision,Text,CreatedAt)
                          VALUES(?,?,?,?,SYSUTCDATETIME())""",
                    body.operationId,
                    conversation,
                    state["revision"],
                    feedback_text[:1000],
                )
                c.execute(
                    """UPDATE crm_analysis.ConversationState
                          SET Status='pending',Revision=Revision+1,
                          Failures=0,ErrorCode=NULL,
                          LeaseToken=NULL,LeaseUntil=NULL,NextAttemptAt=SYSUTCDATETIME()
                          WHERE ConversationId=?""",
                    conversation,
                )
            self.record(
                c,
                body.operationId,
                conversation,
                action,
                payload_hash,
                plan["id"] if action == "feedback" else None,
                None,
                document,
            )
            return document["response"]

    def record(
        self, c, operation, conversation, action, payload_hash, plan, task, document
    ):
        c.execute(
            """INSERT crm_strategy.Operation(OperationId,ConversationId,Action,
                  PayloadHash,PlanId,TaskId,Actor,DocumentJson)
                  VALUES(?,?,?,?,?,?,?,?)""",
            operation,
            conversation,
            action,
            payload_hash,
            plan,
            task,
            "automation" if action == "task_create" else "local-operator",
            "{}",
        )
        document["response"] = {"revision": self.revision(c)}
        c.execute(
            "UPDATE crm_strategy.Operation SET DocumentJson=? WHERE OperationId=?",
            json.dumps(document, ensure_ascii=False),
            operation,
        )

    def execute(self, binding):
        """One bounded internal action per cycle; no model or outbound calls."""
        with self.workspace.transaction(write=True) as c:
            if not present(c):
                return "not_installed"
            ConversationAnalysis.verify(c)
            InboxOperations.verify(c)
            conversations = c.execute(
                "SELECT ConversationId FROM crm_strategy.Policy WHERE Enabled=1 "
                "AND ConversationId IS NOT NULL ORDER BY ConversationId"
            ).fetchall()
            for row in conversations:
                conversation = str(row[0]).lower()
                plan, _, _, employee, autonomy = self.inspect(c, conversation, binding)
                if not autonomy["effective"]:
                    continue
                # C4 reservations in historical privacy peers must remain protected.
                from app.modules.contacts.application.merge import analysis_guard, historical_ids

                contact = str(
                    c.execute(
                        "SELECT ContactId FROM crm.Conversation WHERE ConversationId=?",
                        conversation,
                    ).fetchone()[0]
                )
                try:
                    analysis_guard(c, historical_ids(c, contact))
                except HTTPException as error:
                    if (
                        error.status_code == 409
                        and error.detail == "analysis_attempt_reserved"
                    ):
                        continue
                    raise
                task = str(uuid4())
                c.execute(
                    """INSERT crm_inbox.Task(
                          TaskId,ConversationId,Title,HumanEmployeeId,DueAt,Priority,Status)
                          VALUES(?,?,?,?,NULL,'normal','pending')""",
                    task,
                    conversation,
                    "Revisar seguimiento solicitado",
                    employee,
                )
                operation = str(uuid4())
                self.record(
                    c,
                    operation,
                    conversation,
                    "task_create",
                    bytes.fromhex(digest([str(plan["id"]), "task_create"])),
                    plan["id"],
                    task,
                    {"origin": "validated_ai_plan", "dueAt": None},
                )
                return "task_created"
            return "no_eligible_plan"
