"""Read-only contact activity from durable records, without invented history."""

import base64
import binascii
import hashlib
import json
from datetime import date, datetime, time, timedelta, timezone
from typing import Annotated, Literal
from uuid import UUID

import pyodbc
from fastapi import APIRouter, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import Field, ValidationError, model_validator

from app.modules.catalog.domain.contracts import CatalogUnavailable
from app.modules.inbox.application.service import rows
from app.modules.inbox.application.operations import SLA_JOIN, InboxOperations
from app.schemas import LocalModel
from app.sql_workspace import Identifier

Kind = Literal["all", "contact", "conversation", "message", "assignment", "task"]
Counter = Annotated[int, Field(ge=0, le=9223372036854775807)]
BOGOTA = timezone(timedelta(hours=-5))


class ActivityCursor(LocalModel):
    version: Literal[1] = 1
    scope: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    crm: Counter
    inbox: Counter
    message: Counter
    at: Annotated[str, Field(pattern=r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{7}Z$")]
    rank: Annotated[int, Field(ge=0, le=4)]
    sourceId: Identifier
    merge: Counter = 0
    strategy: Counter = 0

    @model_validator(mode="after")
    def normalize(self):
        # Validate the calendar, but retain all seven SQL fractional digits.
        datetime.fromisoformat(self.at)
        self.sourceId = str(UUID(self.sourceId))
        return self

    def encode(self):
        return (
            base64.urlsafe_b64encode(self.model_dump_json().encode())
            .decode()
            .rstrip("=")
        )

    @classmethod
    def decode(cls, value):
        try:
            raw = base64.b64decode(
                value + "=" * (-len(value) % 4), altchars=b"-_", validate=True
            )
            return cls.model_validate_json(raw)
        except (ValueError, ValidationError, binascii.Error):
            raise HTTPException(422, "invalid_activity_cursor") from None


def scope_key(contact, kind, start, end):
    return hashlib.sha256(
        json.dumps([str(UUID(contact)), kind, str(start), str(end)]).encode()
    ).hexdigest()


def date_bounds(start, end):
    if start and end and start > end:
        raise HTTPException(422, "invalid_activity_date_range")
    try:
        lower = (
            datetime.combine(start, time.min, BOGOTA).astimezone(timezone.utc)
            if start
            else None
        )
        upper = (
            datetime.combine(end + timedelta(days=1), time.min, BOGOTA).astimezone(
                timezone.utc
            )
            if end
            else None
        )
    except (OverflowError, ValueError):
        raise HTTPException(422, "invalid_activity_date_range") from None
    return lower.replace(tzinfo=None) if lower else None, upper.replace(
        tzinfo=None
    ) if upper else None


def utc_text(expression):
    """Format a fixed SQL expression, retaining zero fractions and 100 ns."""
    return (
        f"CONVERT(varchar(19),{expression},126)+'.'+RIGHT(CONVERT(varchar(8),"
        f"10000000+DATEPART(nanosecond,{expression})/100),7)+'Z'"
    )


def sources(with_operations, with_merge=False, with_strategy=False):
    assignment_duplicate = (
        """
 AND NOT (o.Action='update_conversation' AND EXISTS(
  SELECT 1 FROM crm_inbox.Operation i WHERE i.OperationId=o.OperationId
   AND i.Action='assignment' AND i.Revision<=@inbox
   AND TRY_CONVERT(uniqueidentifier,i.EntityKey)=o.ConversationId))
"""
        if with_operations
        else ""
    )
    inbox = (
        """
 UNION ALL
 SELECT CONVERT(tinyint,2),LOWER(CONVERT(varchar(36),i.OperationId)),
  i.CreatedAt,CASE WHEN i.Action='assignment' THEN 'assignment' ELSE 'task' END,
  i.Action,i.Actor,CONVERT(varchar(8),NULL),v.ContactId,v.ConversationId
 FROM crm_inbox.Operation i LEFT JOIN crm_inbox.Task t
  ON t.TaskId=TRY_CONVERT(uniqueidentifier,i.EntityKey)
 JOIN crm.Conversation v ON v.ConversationId=CASE WHEN i.Action='assignment'
  THEN TRY_CONVERT(uniqueidentifier,i.EntityKey) ELSE t.ConversationId END
 WHERE i.Revision<=@inbox AND
  v.ContactId IN (SELECT CONVERT(uniqueidentifier,value)
 FROM OPENJSON(@members))
  AND i.Action IN ('assignment','task_create','task_edit')
"""
        if with_operations
        else ""
    )
    return (
        """
 SELECT CONVERT(tinyint,0) AS sourceRank,
  LOWER(CONVERT(varchar(36),o.OperationId)) AS sourceId,o.CreatedAt AS occurredAt,
  CASE WHEN o.Action IN ('create_contact','edit_contact') THEN 'contact'
   WHEN o.Action='add_message' THEN 'message' ELSE 'conversation' END AS kind,
  o.Action AS action,o.Actor AS actor,CONVERT(varchar(8),NULL) AS direction,
  o.ContactId AS sourceContactId,o.ConversationId AS conversationId
 FROM crm.Operation o WHERE o.ContactId IN
 (SELECT CONVERT(uniqueidentifier,value) FROM OPENJSON(@members))
  AND o.Revision<=@crm AND NOT (o.Action='add_message' AND EXISTS(
   SELECT 1 FROM crm.Message m WHERE m.MessageId=o.MessageId
    AND m.ConversationId=o.ConversationId AND m.Sequence<=@message))
"""
        + assignment_duplicate
        + (
            (
                " AND NOT EXISTS(SELECT 1 FROM crm_merge.Operation x WHERE x."
                "OperationId=o.OperationId AND x.Action IN ('merge','undo') A"
                "ND x.Revision<=@merge)"
            )
            if with_merge
            else ""
        )
        + """
 UNION ALL
 SELECT CONVERT(tinyint,1),LOWER(CONVERT(varchar(36),m.MessageId)),m.CreatedAt,
  'message','message_recorded',CONVERT(varchar(32),NULL),m.Direction,v.ContactId,m.ConversationId
 FROM crm.Message m JOIN crm.Conversation v ON v.ConversationId=m.ConversationId
 WHERE v.ContactId IN (SELECT CONVERT(uniqueidentifier,value)
 FROM OPENJSON(@members))
 AND m.Sequence<=@message
"""
        + inbox
        + (
            """
 UNION ALL SELECT CONVERT(tinyint,4),LOWER(CONVERT(varchar(36),s.OperationId)),
 s.CreatedAt,'task',s.Action,s.Actor,CONVERT(varchar(8),NULL),v.ContactId,v.ConversationId
 FROM crm_strategy.Operation s JOIN crm.Conversation v
 ON v.ConversationId=s.ConversationId
 WHERE s.Action='task_create' AND s.Revision<=@strategy
 AND v.ContactId IN (SELECT CONVERT(uniqueidentifier,value) FROM OPENJSON(@members))
"""
            if with_strategy
            else ""
        )
        + (
            """
 UNION ALL SELECT CONVERT(tinyint,3),LOWER(CONVERT(varchar(36),x.OperationId)),
 x.CreatedAt,'contact',x.Action,x.Actor,CONVERT(varchar(8),NULL),x.TargetContactId,v.ConversationId
 FROM crm_merge.Operation x JOIN crm.Conversation v ON v.ContactId=x.TargetContactId
 WHERE x.Action IN ('merge','undo') AND x.Revision<=@merge
 AND (x.SourceContactId IN (SELECT CONVERT(uniqueidentifier,value)
 FROM OPENJSON(@members))
 OR x.TargetContactId IN (SELECT CONVERT(uniqueidentifier,value)
 FROM OPENJSON(@members)))
"""
            if with_merge
            else ""
        )
    )


def activity_sql(with_operations, with_merge=False, with_strategy=False):
    return (
        """
DECLARE @contact uniqueidentifier=?,@conversation uniqueidentifier=?,
 @crm bigint=?,@inbox bigint=?,@message bigint=?,@kind varchar(20)=?,
 @start datetime2(7)=?,@end datetime2(7)=?,@at datetime2(7)=CONVERT(datetime2(7),?,126),
 @rank tinyint=?,@id varchar(36)=?,@members nvarchar(max)=?,
 @merge bigint=?,@strategy bigint=?;
WITH activity AS (
"""
        + sources(with_operations, with_merge, with_strategy)
        + """
)
SELECT TOP(26) sourceRank,sourceId,
 {occurred} AS occurredAt,kind,action,actor,direction,
 LOWER(CONVERT(varchar(36),sourceContactId)) AS sourceContactId,
 LOWER(CONVERT(varchar(36),conversationId)) AS conversationId
FROM activity WHERE (@kind='all' OR kind=@kind)
 AND (@start IS NULL OR occurredAt>=@start) AND (@end IS NULL OR occurredAt<@end)
 AND (@at IS NULL OR occurredAt<@at OR (occurredAt=@at AND
  (sourceRank>@rank OR (sourceRank=@rank AND sourceId COLLATE Latin1_General_100_BIN2
   >@id COLLATE Latin1_General_100_BIN2))))
ORDER BY occurredAt DESC,sourceRank,sourceId COLLATE Latin1_General_100_BIN2;
""".replace("{occurred}", utc_text("occurredAt"))
    )


METRICS = """
DECLARE @now datetime2(7)=SYSUTCDATETIME();
SELECT {calculated} AS calculatedAt,
 (SELECT COUNT_BIG(*) FROM crm.Message
   WHERE ConversationId=c.ConversationId) AS messages,
 (SELECT COUNT_BIG(*) FROM crm.Message WHERE ConversationId=c.ConversationId
   AND Direction='incoming') AS incoming,
 (SELECT COUNT_BIG(*) FROM crm.Message WHERE ConversationId=c.ConversationId
   AND Direction='outgoing') AS outgoing,
 (SELECT {last_message} FROM crm.Message
   WHERE ConversationId=c.ConversationId) AS lastMessageAt
 {task_columns}
FROM crm.Conversation c {sla_join} WHERE c.ConversationId=?;
"""
TASK_METRICS = """
 ,(SELECT COUNT_BIG(*) FROM crm_inbox.Task WHERE ConversationId=c.ConversationId
   AND Status='pending') AS pendingTasks,
 (SELECT COUNT_BIG(*) FROM crm_inbox.Task WHERE ConversationId=c.ConversationId
   AND Status='completed') AS completedTasks,
 (SELECT COUNT_BIG(*) FROM crm_inbox.Task WHERE ConversationId=c.ConversationId
   AND Status='cancelled') AS cancelledTasks,
 (SELECT COUNT_BIG(*) FROM crm_inbox.Task WHERE ConversationId=c.ConversationId
   AND Status='pending' AND DueAt<=@now) AS overdueTasks,
 sla.status AS slaStatus,
 {sla_started} AS slaStartedAt,
 {sla_due} AS slaDueAt
"""


GROUP_MESSAGES = """
SELECT COUNT_BIG(*) AS messages,
 COALESCE(SUM(CONVERT(bigint,CASE WHEN m.Direction='incoming'
 THEN 1 ELSE 0 END)),0) AS incoming,
 COALESCE(SUM(CONVERT(bigint,CASE WHEN m.Direction='outgoing'
 THEN 1 ELSE 0 END)),0) AS outgoing,
 {last} AS lastMessageAt
FROM crm.Message m JOIN crm.Conversation v ON v.ConversationId=m.ConversationId
WHERE v.ContactId IN(SELECT CONVERT(uniqueidentifier,value) FROM OPENJSON(?))
""".format(last=utc_text("MAX(m.CreatedAt)"))
GROUP_TASKS = """
DECLARE @now datetime2(7)=SYSUTCDATETIME();
SELECT COALESCE(SUM(CONVERT(bigint,CASE WHEN t.Status='pending'
 THEN 1 ELSE 0 END)),0) AS pendingTasks,
 COALESCE(SUM(CONVERT(bigint,CASE WHEN t.Status='completed'
 THEN 1 ELSE 0 END)),0) AS completedTasks,
 COALESCE(SUM(CONVERT(bigint,CASE WHEN t.Status='cancelled'
 THEN 1 ELSE 0 END)),0) AS cancelledTasks,
 COALESCE(SUM(CONVERT(bigint,CASE WHEN t.Status='pending' AND t.DueAt<=@now
 THEN 1 ELSE 0 END)),0) AS overdueTasks
FROM crm_inbox.Task t JOIN crm.Conversation v ON v.ConversationId=t.ConversationId
WHERE v.ContactId IN(SELECT CONVERT(uniqueidentifier,value) FROM OPENJSON(?))
"""


class ContactActivity:
    def __init__(self, workspace):
        self.workspace = workspace

    def read(self, contact, kind="all", start=None, end=None, token=None):
        contact = str(UUID(contact))
        lower, upper = date_bounds(start, end)
        scope = scope_key(contact, kind, start, end)
        cursor = ActivityCursor.decode(token) if token else None
        if cursor and cursor.merge == 0 and cursor.scope != scope:
            raise HTTPException(422, "activity_cursor_scope_changed")
        with self.workspace.transaction() as sql:
            from app.modules.contacts.application.merge import membership, present

            merge_available = present(sql)
            group = (
                membership(sql, contact)
                if merge_available
                else {
                    "primaryContactId": contact,
                    "memberContactIds": [contact],
                    "links": [],
                }
            )
            merge_max = (
                int(
                    sql.execute(
                        "SELECT COALESCE(MAX(Revision),0) FROM crm_merge.Operation"
                    ).fetchone()[0]
                )
                if merge_available
                else 0
            )
            if cursor and cursor.merge > merge_max:
                raise HTTPException(422, "activity_cursor_out_of_bounds")
            if merge_max:
                scope = hashlib.sha256(
                    json.dumps([scope, group, merge_max], sort_keys=True).encode()
                ).hexdigest()
            if cursor and cursor.scope != scope:
                raise HTTPException(422, "activity_cursor_scope_changed")
            found = sql.execute(
                "SELECT ConversationId FROM crm.Conversation WHERE ContactId=?", contact
            ).fetchone()
            if found is None:
                raise HTTPException(404, "contact_not_found")
            conversation = str(found[0]).lower()
            optional = InboxOperations.present(sql)
            from app.modules.conversation_strategy.api.router import present as strategy_present

            strategy_available = strategy_present(sql)
            strategy_max = (
                int(
                    sql.execute(
                        "SELECT COALESCE(MAX(Revision),0) FROM crm_strategy.Operation"
                    ).fetchval()
                )
                if strategy_available
                else 0
            )
            if cursor and cursor.strategy > strategy_max:
                raise HTTPException(422, "activity_cursor_out_of_bounds")
            if optional:
                InboxOperations.verify(sql)
            maximum = sql.execute(
                "SELECT COALESCE((SELECT MAX(Revision) FROM crm.Operation),0),"
                + (
                    "COALESCE((SELECT MAX(Revision) FROM crm_inbox.Operation),0),"
                    if optional
                    else "CONVERT(bigint,0),"
                )
                + "COALESCE((SELECT MAX(Sequence) FROM crm.Message),0)"
            ).fetchone()
            if cursor and any(
                value > cap
                for value, cap in zip(
                    [cursor.crm, cursor.inbox, cursor.message], maximum, strict=True
                )
            ):
                raise HTTPException(422, "activity_cursor_out_of_bounds")
            watermarks = (
                [cursor.crm, cursor.inbox, cursor.message] if cursor else list(maximum)
            )
            page = rows(
                sql.execute(
                    activity_sql(optional, merge_available, strategy_available),
                    contact,
                    conversation,
                    *watermarks,
                    kind,
                    lower,
                    upper,
                    cursor.at[:-1] if cursor else None,
                    cursor.rank if cursor else None,
                    cursor.sourceId if cursor else None,
                    json.dumps(group["memberContactIds"]),
                    cursor.merge if cursor else merge_max,
                    cursor.strategy if cursor else strategy_max,
                )
            )
            summary = rows(
                sql.execute(
                    METRICS.format(
                        calculated=utc_text("@now"),
                        last_message=utc_text("MAX(CreatedAt)"),
                        task_columns=TASK_METRICS.format(
                            sla_started=utc_text("pending.startedAt"),
                            sla_due=utc_text("deadline.dueAt"),
                        )
                        if optional
                        else "",
                        sla_join=SLA_JOIN.replace("SYSUTCDATETIME()", "@now")
                        if optional
                        else "",
                    ),
                    conversation,
                )
            )[0]
            if len(group["memberContactIds"]) > 1:
                members_json = json.dumps(group["memberContactIds"])
                totals = rows(sql.execute(GROUP_MESSAGES, members_json))[0]
                summary.update(totals)
                if optional:
                    summary.update(rows(sql.execute(GROUP_TASKS, members_json))[0])
        items = []
        source_names = [
            "crm_operation",
            "message",
            "inbox_operation",
            "merge_operation",
            "strategy_operation",
        ]
        for item in page[:25]:
            item["source"] = source_names[item.pop("sourceRank")]
            item["id"] = item["source"] + ":" + item["sourceId"]
            items.append(item)
        next_cursor = None
        if len(page) > 25:
            last = items[-1]
            next_cursor = ActivityCursor(
                scope=scope,
                crm=watermarks[0],
                inbox=watermarks[1],
                message=watermarks[2],
                at=last["occurredAt"],
                rank=source_names.index(last["source"]),
                sourceId=last["sourceId"],
                merge=cursor.merge if cursor else merge_max,
                strategy=cursor.strategy if cursor else strategy_max,
            ).encode()
        metrics = {
            "scope": "current_group_all_messages_current_tasks"
            if len(group["memberContactIds"]) > 1
            else "selected_contact_all_messages_current_tasks",
            "memberCount": len(group["memberContactIds"]),
            "slaConversationId": conversation,
            "calculatedAt": summary["calculatedAt"],
            "messages": {
                key: summary[key]
                for key in ["messages", "incoming", "outgoing", "lastMessageAt"]
            },
            "tasks": {
                key: summary[key]
                for key in [
                    "pendingTasks",
                    "completedTasks",
                    "cancelledTasks",
                    "overdueTasks",
                ]
            }
            if optional
            else None,
            "sla": {
                "status": summary["slaStatus"],
                "startedAt": summary["slaStartedAt"],
                "dueAt": summary["slaDueAt"],
            }
            if optional
            else {"status": "unavailable", "startedAt": None, "dueAt": None},
        }
        return {
            "items": items,
            "limit": 25,
            "hasMore": len(page) > 25,
            "nextCursor": next_cursor,
            "metrics": metrics,
            "historyScope": {
                "contactId": contact,
                "primaryContactId": group["primaryContactId"],
                "memberContactIds": group["memberContactIds"],
                "kind": kind,
                "fromDate": str(start) if start else None,
                "toDate": str(end) if end else None,
                "dateZone": "America/Bogota",
                "upperBound": "exclusive_next_day",
                "timestamps": "UTC",
                "fieldHistory": "not_recorded",
                "actorIdentity": "local_label_not_authenticated",
                "inboxAvailable": optional,
            },
        }


def install_contact_activity(app: FastAPI):
    app.state.contact_activity = ContactActivity(app.state.sql_workspace)
    router = APIRouter(prefix="/api/local/crm/clients", tags=["local-contact-activity"])

    @router.get("/{contact_id}/activity")
    def activity(
        request: Request,
        contact_id: Identifier,
        kind: Kind = "all",
        fromDate: date | None = None,
        toDate: date | None = None,
        cursor: str | None = Query(None, min_length=1, max_length=1024),
    ):
        if request.app.state.settings.mode != "local_sql_copy":
            raise HTTPException(503, "local_sql_copy_disabled")
        try:
            return JSONResponse(
                request.app.state.contact_activity.read(
                    contact_id, kind, fromDate, toDate, cursor
                ),
                headers={"Cache-Control": "no-store"},
            )
        except (pyodbc.Error, CatalogUnavailable):
            raise HTTPException(503, "contact_activity_unavailable") from None

    app.include_router(router)
