"""Explicit local Inbox operations; stable references, no provider execution."""

import hashlib
import json
from contextlib import nullcontext
from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

import pyodbc
from fastapi import APIRouter, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import Field, field_validator, model_validator

from app.modules.catalog.domain.contracts import CatalogUnavailable
from app.modules.inbox.application.service import pattern, rows
from app.schemas import LocalModel
from app.sql_workspace import Identifier, Revision
from app.sql_workspace_shape import SHAPE_SQL

EmployeeId = Annotated[int, Field(ge=1, le=2147483647)]
OPS_SHAPE = SHAPE_SQL.replace("N'crm'", "N'crm_inbox'").replace(
    "N'crm.shape'", "N'crm_inbox.shape'"
)
SOURCE_GUARD = (
    "SELECT COUNT(*) FROM sys.columns WHERE\nobject"
    "_id=OBJECT_ID(N'dbo.GEEmpleado')\n AND ((name="
    "'CnsctvoEmpldo' AND TYPE_NAME(user_type_id)='"
    "int' AND\nis_nullable=0)\n OR (name='NmbrePrsna"
    "' AND TYPE_NAME(user_type_id)='varchar' AND\nm"
    "ax_length=20)\n OR (name='AplldosPrsna' AND TY"
    "PE_NAME(user_type_id)='varchar' AND\nmax_lengt"
    "h=30)\n OR (name='Actvo' AND TYPE_NAME(user_ty"
    "pe_id)='bit' AND is_nullable=0))"
)

# These joins never infer a delivered external response or a business calendar.
SLA_JOIN = """
 LEFT JOIN crm_inbox.Assignment ia ON ia.ConversationId=c.ConversationId
 LEFT JOIN crm_inbox.SlaPolicy sp ON sp.PolicyId=1 AND sp.Enabled=1
 OUTER APPLY (SELECT MAX(reply.Sequence) AS sequence FROM crm.Message reply
   WHERE reply.ConversationId=c.ConversationId AND reply.Direction='outgoing'
   AND (NOT EXISTS(SELECT 1 FROM crm_channels.ExternalIdentity i WHERE i.ConversationId=c.ConversationId)
     OR EXISTS(SELECT 1 FROM crm_channels.outbound_queue q WHERE q.MessageId=reply.MessageId
        AND q.State IN('sent','delivered','read')))) replied
 OUTER APPLY (SELECT MIN(CreatedAt) AS startedAt FROM crm.Message
   WHERE ConversationId=c.ConversationId AND Direction='incoming'
   AND Sequence>COALESCE(replied.sequence,0)) pending
 OUTER APPLY (SELECT MIN(CreatedAt) AS startedAt,MIN(Sequence) AS sequence FROM crm.Message
   WHERE ConversationId=c.ConversationId AND Direction='incoming') firstIncoming
 OUTER APPLY (SELECT CASE WHEN sp.PolicyId IS NOT NULL AND c.State<>'closed' AND pending.startedAt IS NOT NULL
   THEN DATEADD(minute,sp.ThresholdMinutes,pending.startedAt) END AS dueAt,
   CASE WHEN sp.PolicyId IS NOT NULL AND c.State<>'closed' AND firstIncoming.startedAt IS NOT NULL
     AND COALESCE(replied.sequence,0)<firstIncoming.sequence
   THEN DATEADD(minute,sp.ThresholdMinutes,firstIncoming.startedAt) END AS firstResponseDueAt) deadline
 OUTER APPLY (SELECT CASE WHEN sp.PolicyId IS NULL THEN 'not_configured'
   WHEN c.State='closed' THEN 'closed' WHEN pending.startedAt IS NULL THEN 'no_incoming'
   WHEN deadline.dueAt<SYSUTCDATETIME() THEN 'overdue' ELSE 'on_time' END AS status) sla
"""


class Write(LocalModel):
    operationId: Identifier
    expectedRevision: Revision

    @model_validator(mode="after")
    def normalize_id(self):
        self.operationId = str(UUID(self.operationId))
        return self


class MemberWrite(Write):
    enabled: bool


class AgentWrite(Write):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    description: Annotated[str, Field(max_length=1000)]
    enabled: bool

    @model_validator(mode="after")
    def trim_name(self):
        self.name = self.name.strip()
        self.description = self.description.strip()
        if not self.name:
            raise ValueError("Name required")
        return self


class AssignmentWrite(Write):
    humanEmployeeId: EmployeeId | None
    aiAgentId: Identifier | None

    @model_validator(mode="after")
    def normalize_agent(self):
        if self.aiAgentId:
            self.aiAgentId = str(UUID(self.aiAgentId))
        return self


class PolicyWrite(Write):
    enabled: bool
    thresholdMinutes: Annotated[int, Field(ge=1, le=525600)]


class TaskWrite(Write):
    title: Annotated[str, Field(min_length=1, max_length=120)]
    priority: Literal["low", "normal", "high", "urgent"]
    humanEmployeeId: EmployeeId | None
    dueAt: datetime | None
    status: Literal["pending", "completed", "cancelled"]

    @field_validator("dueAt", mode="before")
    @classmethod
    def parse_due(cls, value):
        return (
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            if isinstance(value, str)
            else value
        )

    @model_validator(mode="after")
    def normalize_task(self):
        self.title = self.title.strip()
        if not self.title:
            raise ValueError("Title required")
        if self.dueAt:
            if self.dueAt.tzinfo is None:
                raise ValueError("Timezone required")
            self.dueAt = self.dueAt.astimezone(timezone.utc)
        return self


def sla_status(enabled, threshold, state, started, now):
    if not enabled:
        return "not_configured"
    if state == "closed":
        return "closed"
    if started is None:
        return "no_incoming"
    return "overdue" if (now - started).total_seconds() >= threshold * 60 else "on_time"


class InboxOperations:
    def __init__(self, workspace):
        self.workspace = workspace

    @staticmethod
    def present(cursor):
        return cursor.execute(("SELECT SCHEMA_ID(N'crm_inbox')")).fetchval() is not None

    @staticmethod
    def verify(cursor):
        version = cursor.execute(
            (
                "SELECT CONVERT(nvarchar(128),value) FROM sys."
                "extended_properties WHERE class=3 AND major_i"
                "d=SCHEMA_ID(N'crm_inbox') AND name=N'crm_inbo"
                "x.contract'"
            )
        ).fetchone()
        if not version or version[0] != "inbox-v1":
            raise HTTPException(503, "inbox_operations_not_installed")
        if not cursor.execute(OPS_SHAPE).fetchval():
            raise HTTPException(503, "inbox_operations_shape_changed")
        source_key = cursor.execute(
            "SELECT COUNT(*),SUM(CASE WHEN ic.key_ordinal=1 "
            "AND c.name='CnsctvoEmpldo' THEN 1 ELSE 0 END) "
            "FROM sys.indexes i JOIN sys.index_columns ic "
            "ON ic.object_id=i.object_id AND ic.index_id=i.index_id "
            "JOIN sys.columns c ON c.object_id=ic.object_id "
            "AND c.column_id=ic.column_id "
            "WHERE i.object_id=OBJECT_ID(N'dbo.GEEmpleado') "
            "AND i.is_primary_key=1 AND ic.key_ordinal>0"
        ).fetchone()
        if cursor.execute(SOURCE_GUARD).fetchval() != 4 or tuple(source_key) != (1, 1):
            raise HTTPException(503, "employee_source_changed")

    @staticmethod
    def revision(cursor):
        from app.modules.conversation_strategy.api.router import present

        revision = cursor.execute(
            "SELECT COALESCE(MAX(Revision),0) FROM crm_inbox.Operation"
        ).fetchval()
        if cursor.execute("SELECT OBJECT_ID(N'crm_ai.ResponseJob')").fetchval():
            revision += cursor.execute("SELECT COUNT_BIG(*) FROM crm_ai.ResponseJob WHERE TaskId IS NOT NULL").fetchval()
        if present(cursor):
            revision += cursor.execute(
                "SELECT COUNT_BIG(*) FROM crm_strategy.Operation "
                "WHERE Action='task_create'"
            ).fetchval()
        return str(revision)

    def configuration(self):
        with self.workspace.transaction() as cursor:
            self.verify(cursor)
            policies = rows(
                cursor.execute(
                    (
                        "SELECT Enabled AS enabled,ThresholdMinutes AS"
                        " thresholdMinutes,UpdatedAt AS updatedAt FROM"
                        " crm_inbox.SlaPolicy WHERE PolicyId=1"
                    )
                )
            )
            return {
                "policy": policies[0] if policies else None,
                "revision": self.revision(cursor),
            }

    def directory(self, scope, q="", offset=0, eligible=False):
        with self.workspace.transaction() as cursor:
            self.verify(cursor)
            if scope == "agents":
                found = rows(
                    cursor.execute(
                        (
                            "SELECT AgentId AS id,Name AS name,Description"
                            " AS description,Enabled AS\nenabled,Enabled AS"
                            " selectable\n      FROM crm_inbox.Agent WHERE "
                            "(?=0 OR Enabled=1) AND (?='' OR Name LIKE\n?)\n"
                            "      ORDER BY Name,AgentId OFFSET ? ROWS FET"
                            "CH NEXT 26 ROWS ONLY"
                        ),
                        int(eligible),
                        q,
                        pattern(q),
                        offset,
                    )
                )
            elif scope == "employees":
                found = rows(
                    cursor.execute(
                        (
                            "SELECT e.CnsctvoEmpldo AS id,LTRIM(RTRIM(CONC"
                            "AT(e.NmbrePrsna,' ',e.AplldosPrsna))) AS name"
                            ",\n      e.Actvo AS sourceActive,COALESCE(m.En"
                            "abled,0) AS enabled,e.Actvo AS\nselectable\n   "
                            "   FROM dbo.GEEmpleado e LEFT JOIN crm_inbox."
                            "Member m ON\nm.EmployeeId=e.CnsctvoEmpldo\n    "
                            "  WHERE e.Actvo=1 AND (?='' OR CONCAT(e.Nmbre"
                            "Prsna,' ',e.AplldosPrsna)\nLIKE ?)\n      ORDER"
                            " BY e.NmbrePrsna,e.AplldosPrsna,e.CnsctvoEmpl"
                            "do OFFSET ? ROWS\nFETCH NEXT 26 ROWS ONLY"
                        ),
                        q,
                        pattern(q),
                        offset,
                    )
                )
            else:
                found = rows(
                    cursor.execute(
                        (
                            "SELECT m.EmployeeId AS id,COALESCE(LTRIM(RTRI"
                            "M(CONCAT(e.NmbrePrsna,' ',e.AplldosPrsna))),'"
                            "') AS name,\n      COALESCE(e.Actvo,0) AS sour"
                            "ceActive,m.Enabled AS enabled,\n      CONVERT("
                            "bit,CASE WHEN m.Enabled=1 AND e.Actvo=1 THEN "
                            "1 ELSE 0 END) AS\nselectable\n      FROM crm_in"
                            "box.Member m LEFT JOIN dbo.GEEmpleado e ON\ne."
                            "CnsctvoEmpldo=m.EmployeeId\n      WHERE (?=0 O"
                            "R (m.Enabled=1 AND e.Actvo=1)) AND (?='' OR\nC"
                            "ONCAT(e.NmbrePrsna,' ',e.AplldosPrsna) LIKE ?"
                            ")\n      ORDER BY e.NmbrePrsna,e.AplldosPrsna,"
                            "m.EmployeeId OFFSET ? ROWS FETCH\nNEXT 26 ROWS"
                            " ONLY"
                        ),
                        int(eligible),
                        q,
                        pattern(q),
                        offset,
                    )
                )
            for item in found:
                if scope == "agents":
                    item["id"] = str(item["id"]).lower()
            return {
                "items": found[:25],
                "offset": offset,
                "hasMore": len(found) > 25,
                "revision": self.revision(cursor),
            }

    def conversation(self, identifier, offset=0, cursor=None):
        with (
            self.workspace.transaction() if cursor is None else nullcontext(cursor)
        ) as cursor:
            self.verify(cursor)
            found = rows(
                cursor.execute(
                    (
                        "SELECT ia.HumanEmployeeId AS humanEmployeeId,"
                        "ia.AiAgentId AS aiAgentId,\n    COALESCE(LTRIM"
                        "(RTRIM(CONCAT(e.NmbrePrsna,' ',e.AplldosPrsna"
                        "))),'') AS\nhumanName,\n    CONVERT(bit,CASE WH"
                        "EN member.Enabled=1 AND e.Actvo=1 THEN 1 ELSE"
                        " 0 END)\nAS humanSelectable,\n    agent.Name AS"
                        " aiName,COALESCE(agent.Enabled,0) AS aiSelect"
                        "able,\n    pending.startedAt AS startedAt,dead"
                        "line.dueAt AS dueAt,sla.status AS\nslaStatus,\n"
                        "    sp.ThresholdMinutes AS thresholdMinutes,c"
                        ".ControlMode AS controlMode,deadline.firstResponseDueAt AS firstResponseDueAt\n    FROM crm.Conv"
                        "ersation c"
                    )
                    + SLA_JOIN
                    + (
                        "\n    LEFT JOIN crm_inbox.Member member ON mem"
                        "ber.EmployeeId=ia.HumanEmployeeId\n    LEFT JO"
                        "IN dbo.GEEmpleado e ON e.CnsctvoEmpldo=ia.Hum"
                        "anEmployeeId\n    LEFT JOIN crm_inbox.Agent ag"
                        "ent ON agent.AgentId=ia.AiAgentId\n    WHERE c"
                        ".ConversationId=?"
                    ),
                    identifier,
                )
            )
            if not found:
                raise HTTPException(404, "conversation_not_found")
            value = found[0]
            if value["aiAgentId"]:
                value["aiAgentId"] = str(value["aiAgentId"]).lower()
            tasks = rows(
                cursor.execute(
                    (
                        "SELECT t.TaskId AS id,t.Title AS title,t.Huma"
                        "nEmployeeId AS humanEmployeeId,\n    COALESCE("
                        "LTRIM(RTRIM(CONCAT(e.NmbrePrsna,' ',e.Aplldos"
                        "Prsna))),'') AS\nhumanName,\n    CONVERT(bit,CA"
                        "SE WHEN member.Enabled=1 AND e.Actvo=1 THEN 1"
                        " ELSE 0 END)\nAS humanSelectable,\n    t.DueAt "
                        "AS dueAt,t.Priority AS priority,t.Status AS s"
                        "tatus,t.CreatedAt\nAS createdAt,\n    CONVERT(b"
                        "it,CASE WHEN t.Status='pending' AND t.DueAt<="
                        "SYSUTCDATETIME()\nTHEN 1 ELSE 0 END) AS overdu"
                        "e\n    FROM crm_inbox.Task t LEFT JOIN dbo.GEE"
                        "mpleado e ON\ne.CnsctvoEmpldo=t.HumanEmployeeI"
                        "d\n    LEFT JOIN crm_inbox.Member member ON me"
                        "mber.EmployeeId=t.HumanEmployeeId\n    WHERE t"
                        ".ConversationId=? ORDER BY t.CreatedAt DESC,t"
                        ".TaskId\n    OFFSET ? ROWS FETCH NEXT 26 ROWS "
                        "ONLY"
                    ),
                    identifier,
                    offset,
                )
            )
            for task in tasks:
                task["id"] = str(task["id"]).lower()
            return {
                "assignment": value,
                "tasks": tasks[:25],
                "offset": offset,
                "hasMore": len(tasks) > 25,
                "revision": self.revision(cursor),
            }

    @staticmethod
    def valid_member(cursor, employee):
        if (
            employee is not None
            and not cursor.execute(
                (
                    "SELECT m.EmployeeId FROM crm_inbox.Member m J"
                    "OIN dbo.GEEmpleado e ON e.CnsctvoEmpldo=m.Emp"
                    "loyeeId WHERE m.EmployeeId=? AND m.Enabled=1 "
                    "AND e.Actvo=1"
                ),
                employee,
            ).fetchone()
        ):
            raise HTTPException(422, "admissions_member_unavailable")

    def mutate(self, action, key, body, conversation_id=None, transaction_cursor=None):
        payload = body.model_dump(mode="json", exclude={"expectedRevision"})
        digest = hashlib.sha256(
            json.dumps(
                [action, key, conversation_id, payload],
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).digest()
        with (self.workspace.transaction(write=True) if transaction_cursor is None else nullcontext(transaction_cursor)) as cursor:
            self.verify(cursor)
            previous = cursor.execute(
                (
                    "SELECT PayloadHash,Revision FROM crm_inbox.Op"
                    "eration WHERE OperationId=?"
                ),
                body.operationId,
            ).fetchone()
            if previous:
                if bytes(previous[0]) != digest:
                    raise HTTPException(409, "operation_changed")
                return {"revision": str(previous[1])}
            if body.expectedRevision != self.revision(cursor):
                raise HTTPException(409, "inbox_operations_changed")
            if (
                conversation_id
                and not cursor.execute(
                    (
                        "SELECT ConversationId FROM crm.Conversation W"
                        "HERE ConversationId=?"
                    ),
                    conversation_id,
                ).fetchone()
            ):
                raise HTTPException(404, "conversation_not_found")
            if action == "member":
                previous = cursor.execute(
                    ("SELECT Enabled FROM crm_inbox.Member WHERE EmployeeId=?"), key
                ).fetchone()
                if (
                    body.enabled
                    and not cursor.execute(
                        (
                            "SELECT CnsctvoEmpldo FROM dbo.GEEmpleado WHER"
                            "E CnsctvoEmpldo=? AND Actvo=1"
                        ),
                        key,
                    ).fetchone()
                ):
                    raise HTTPException(422, "employee_not_active")
                if not previous and not body.enabled:
                    raise HTTPException(404, "member_not_found")
                if previous:
                    cursor.execute(
                        (
                            "UPDATE crm_inbox.Member SET Enabled=?,Updated"
                            "At=SYSUTCDATETIME() WHERE EmployeeId=?"
                        ),
                        body.enabled,
                        key,
                    )
                else:
                    cursor.execute(
                        ("INSERT crm_inbox.Member(EmployeeId,Enabled) VALUES(?,?)"),
                        key,
                        body.enabled,
                    )
            elif action == "agent":
                if cursor.execute("SELECT OBJECT_ID(N'crm_agents.Profile')").fetchval() and cursor.execute("SELECT 1 FROM crm_agents.Profile WHERE AgentId=?", key).fetchone():
                    raise HTTPException(409, "agents_use_versioned_constructor")
                if cursor.execute(
                    ("SELECT AgentId FROM crm_inbox.Agent WHERE AgentId=?"), key
                ).fetchone():
                    cursor.execute(
                        (
                            "UPDATE crm_inbox.Agent SET Name=?,Description"
                            "=?,Enabled=?,UpdatedAt=SYSUTCDATETIME() WHERE"
                            " AgentId=?"
                        ),
                        body.name,
                        body.description,
                        body.enabled,
                        key,
                    )
                else:
                    cursor.execute(
                        (
                            "INSERT crm_inbox.Agent(AgentId,Name,Descripti"
                            "on,Enabled) VALUES(?,?,?,?)"
                        ),
                        key,
                        body.name,
                        body.description,
                        body.enabled,
                    )
            elif action == "policy":
                if cursor.execute(
                    ("SELECT PolicyId FROM crm_inbox.SlaPolicy WHERE PolicyId=1")
                ).fetchone():
                    cursor.execute(
                        (
                            "UPDATE crm_inbox.SlaPolicy SET Enabled=?,Thre"
                            "sholdMinutes=?,UpdatedAt=SYSUTCDATETIME() WHE"
                            "RE PolicyId=1"
                        ),
                        body.enabled,
                        body.thresholdMinutes,
                    )
                else:
                    cursor.execute(
                        (
                            "INSERT crm_inbox.SlaPolicy(PolicyId,Enabled,T"
                            "hresholdMinutes) VALUES(1,?,?)"
                        ),
                        body.enabled,
                        body.thresholdMinutes,
                    )
            elif action == "assignment":
                previous = cursor.execute(
                    (
                        "SELECT HumanEmployeeId,AiAgentId FROM crm_inb"
                        "ox.Assignment WHERE ConversationId=?"
                    ),
                    conversation_id,
                ).fetchone()
                old_human, old_ai = (
                    (previous[0], str(previous[1]).lower() if previous[1] else None)
                    if previous
                    else (None, None)
                )
                if body.humanEmployeeId != old_human:
                    self.valid_member(cursor, body.humanEmployeeId)
                if (
                    body.aiAgentId != old_ai
                    and body.aiAgentId
                    and not cursor.execute(
                        (
                            "SELECT AgentId FROM crm_inbox.Agent WHERE Age"
                            "ntId=? AND Enabled=1"
                        ),
                        body.aiAgentId,
                    ).fetchone()
                ):
                    raise HTTPException(422, "agent_unavailable")
                if body.aiAgentId != old_ai and cursor.execute("SELECT OBJECT_ID(N'crm_agents.Profile')").fetchval():
                    managed = cursor.execute("SELECT 1 FROM crm_agents.Assignment WHERE ConversationId=?", conversation_id).fetchone()
                    target = cursor.execute("SELECT 1 FROM crm_agents.Profile WHERE AgentId=?", body.aiAgentId).fetchone() if body.aiAgentId else None
                    if managed or target:
                        raise HTTPException(409, "agents_use_protected_assignment")
                if previous:
                    cursor.execute(
                        (
                            "UPDATE crm_inbox.Assignment SET HumanEmployee"
                            "Id=?,AiAgentId=?,UpdatedAt=SYSUTCDATETIME() W"
                            "HERE ConversationId=?"
                        ),
                        body.humanEmployeeId,
                        body.aiAgentId,
                        conversation_id,
                    )
                else:
                    cursor.execute(
                        (
                            "INSERT crm_inbox.Assignment(ConversationId,Hu"
                            "manEmployeeId,AiAgentId) VALUES(?,?,?)"
                        ),
                        conversation_id,
                        body.humanEmployeeId,
                        body.aiAgentId,
                    )
                label = None
                if body.humanEmployeeId:
                    label = cursor.execute(
                        (
                            "SELECT LTRIM(RTRIM(CONCAT(NmbrePrsna,' ',Apll"
                            "dosPrsna))) FROM dbo.GEEmpleado WHERE Cnsctvo"
                            "Empldo=?"
                        ),
                        body.humanEmployeeId,
                    ).fetchval()
                cursor.execute(
                    (
                        "UPDATE crm.Conversation SET Assignee=?,Update"
                        "dAt=SYSUTCDATETIME() WHERE ConversationId=?"
                    ),
                    label,
                    conversation_id,
                )
                cursor.execute(
                    (
                        "INSERT\ncrm.Operation(OperationId,Action,Paylo"
                        "adHash,ContactId,ConversationId,MessageId,Act"
                        "or)\n       SELECT\n?,'update_conversation',?,C"
                        "ontactId,ConversationId,NULL,'local-operator'"
                        "\nFROM crm.Conversation WHERE ConversationId=?"
                    ),
                    body.operationId,
                    digest,
                    conversation_id,
                )
            else:
                previous = cursor.execute(
                    (
                        "SELECT HumanEmployeeId,Status,ConversationId "
                        "FROM crm_inbox.Task WHERE TaskId=?"
                    ),
                    key,
                ).fetchone()
                if action == "task_create" and previous:
                    raise HTTPException(409, "task_exists")
                if action == "task_edit" and (
                    not previous or str(previous[2]).lower() != conversation_id
                ):
                    raise HTTPException(404, "task_not_found")
                if action == "task_create" and body.status != "pending":
                    raise HTTPException(422, "new_task_must_be_pending")
                if previous and previous[1] != "pending" and body.status != previous[1]:
                    raise HTTPException(422, "task_already_closed")
                if not previous or previous[0] != body.humanEmployeeId:
                    self.valid_member(cursor, body.humanEmployeeId)
                due = body.dueAt.replace(tzinfo=None) if body.dueAt else None
                if previous:
                    cursor.execute(
                        (
                            "UPDATE crm_inbox.Task SET Title=?,HumanEmploy"
                            "eeId=?,DueAt=?,Priority=?,Status=?,UpdatedAt="
                            "SYSUTCDATETIME() WHERE TaskId=?"
                        ),
                        body.title,
                        body.humanEmployeeId,
                        due,
                        body.priority,
                        body.status,
                        key,
                    )
                else:
                    cursor.execute(
                        (
                            "INSERT crm_inbox.Task(TaskId,ConversationId,T"
                            "itle,HumanEmployeeId,DueAt,Priority,Status) V"
                            "ALUES(?,?,?,?,?,?,?)"
                        ),
                        key,
                        conversation_id,
                        body.title,
                        body.humanEmployeeId,
                        due,
                        body.priority,
                        body.status,
                    )
            cursor.execute(
                (
                    "INSERT crm_inbox.Operation(OperationId,Action"
                    ",EntityKey,PayloadHash,Actor) VALUES(?,?,?,?,"
                    "'local-operator')"
                ),
                body.operationId,
                action,
                str(key),
                digest,
            )
            return {"revision": self.revision(cursor)}


def install_inbox_operations(app: FastAPI):
    app.state.inbox_operations = InboxOperations(app.state.sql_workspace)
    router = APIRouter(
        prefix="/api/local/crm/inbox/operations", tags=["local-inbox-operations"]
    )

    def call(request, method, *args):
        if request.app.state.settings.mode != "local_sql_copy":
            raise HTTPException(503, "local_sql_copy_disabled")
        try:
            return JSONResponse(
                getattr(request.app.state.inbox_operations, method)(*args),
                headers={"Cache-Control": "no-store"},
            )
        except (pyodbc.Error, CatalogUnavailable):
            raise HTTPException(503, "local_sql_unavailable") from None

    @router.get("/configuration")
    def configuration(request: Request):
        return call(request, "configuration")

    @router.get("/directory")
    def directory(
        request: Request,
        scope: Literal["employees", "members", "agents"],
        q: str = Query("", max_length=100),
        offset: int = Query(0, ge=0, le=1000000),
        eligible: bool = False,
    ):
        return call(request, "directory", scope, q.strip(), offset, eligible)

    @router.put("/members/{employee_id}")
    def member(request: Request, employee_id: EmployeeId, body: MemberWrite):
        return call(request, "mutate", "member", employee_id, body)

    @router.put("/agents/{agent_id}")
    def agent(request: Request, agent_id: Identifier, body: AgentWrite):
        return call(request, "mutate", "agent", str(UUID(agent_id)), body)

    @router.put("/policy")
    def policy(request: Request, body: PolicyWrite):
        return call(request, "mutate", "policy", "1", body)

    @router.get("/conversations/{conversation_id}")
    def conversation(
        request: Request,
        conversation_id: Identifier,
        offset: int = Query(0, ge=0, le=1000000),
    ):
        return call(request, "conversation", str(UUID(conversation_id)), offset)

    @router.put("/conversations/{conversation_id}/assignment")
    def assignment(
        request: Request, conversation_id: Identifier, body: AssignmentWrite
    ):
        return call(
            request,
            "mutate",
            "assignment",
            str(UUID(conversation_id)),
            body,
            str(UUID(conversation_id)),
        )

    @router.put("/conversations/{conversation_id}/tasks/{task_id}")
    def task(
        request: Request,
        conversation_id: Identifier,
        task_id: Identifier,
        body: TaskWrite,
        create: bool = False,
    ):
        return call(
            request,
            "mutate",
            "task_create" if create else "task_edit",
            str(UUID(task_id)),
            body,
            str(UUID(conversation_id)),
        )

    app.include_router(router)
