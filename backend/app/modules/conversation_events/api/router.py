"""Recoverable technical preparation from durable local source references."""

from datetime import datetime, timezone
from threading import Event, Thread
from uuid import UUID, uuid4

import pyodbc
from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.modules.catalog.domain.contracts import CatalogUnavailable
from app.modules.inbox.application.service import rows
from app.modules.inbox.application.operations import OPS_SHAPE
from app.schemas import LocalModel
from app.sql_workspace import Identifier, SqlWorkspace
from app.sql_workspace_shape import SHAPE_SQL

EVENT_SHAPE = SHAPE_SQL.replace("N'crm'", "N'crm_events'").replace(
    "N'crm.shape'", "N'crm_events.shape'"
)
SOURCES = {
    "baseline": """SELECT ConversationId AS SourceId,ConversationId,
        CONVERT(bigint,NULL) AS SourceRevision,CreatedAt AS SourceOccurredAt,
        CONVERT(varchar(24),'baseline_current') AS SourceAction
        FROM crm.Conversation""",
    "message": """SELECT MessageId AS SourceId,ConversationId,
        Sequence AS SourceRevision,CreatedAt AS SourceOccurredAt,
        CONVERT(varchar(24),'message_recorded') AS SourceAction FROM crm.Message""",
    "crm_operation": """SELECT OperationId AS SourceId,ConversationId,
        Revision AS SourceRevision,CreatedAt AS SourceOccurredAt,
        Action AS SourceAction FROM crm.Operation WHERE Action<>'add_message'""",
    "inbox_operation": """SELECT o.OperationId AS SourceId,t.ConversationId,
        o.Revision AS SourceRevision,o.CreatedAt AS SourceOccurredAt,
        o.Action AS SourceAction FROM crm_inbox.Operation o JOIN crm_inbox.Task t
        ON t.TaskId=TRY_CONVERT(uniqueidentifier,o.EntityKey)
        WHERE o.Action IN ('task_create','task_edit')""",
}
MISSING = """NOT EXISTS (SELECT 1 FROM crm_events.Event e
    WHERE e.SourceKind=? AND e.SourceId=s.SourceId)"""
OWNER = """EventId=? AND State='leased' AND LeaseToken=?
    AND LeaseUntil>SYSUTCDATETIME()"""


def source_queries(cursor):
    from app.modules.conversation_strategy.api.router import present

    if not present(cursor):
        return SOURCES
    # Existing operation source class, with an explicit automation ledger actor.
    return {
        **SOURCES,
        "inbox_operation": SOURCES["inbox_operation"]
        + """
        UNION ALL SELECT o.OperationId,o.ConversationId,o.Revision,o.CreatedAt,
        CONVERT(varchar(24),'task_create') FROM crm_strategy.Operation o
        JOIN crm_inbox.Task t ON t.TaskId=o.TaskId AND t.ConversationId=o.ConversationId
        WHERE o.Action='task_create' AND o.Actor='automation'""",
    }


class RetryRequest(LocalModel):
    operationId: Identifier


class ConversationEvents:
    def __init__(self, workspace):
        self.workspace = workspace

    @staticmethod
    def verify(cursor):
        version = cursor.execute(
            "SELECT CONVERT(nvarchar(128),value) FROM sys.extended_properties "
            "WHERE class=3 AND major_id=SCHEMA_ID(N'crm_events') "
            "AND name=N'crm_events.contract'"
        ).fetchval()
        if version != "events-v1":
            raise HTTPException(503, "events_not_installed")
        if not cursor.execute(EVENT_SHAPE).fetchval():
            raise HTTPException(503, "events_shape_changed")
        if not cursor.execute(OPS_SHAPE).fetchval():
            raise HTTPException(503, "events_source_shape_changed")

    def capture(self):
        # ponytail: indexed absence scans fit local volume; measure before scaling.
        with self.workspace.transaction(write=True) as cursor:
            self.verify(cursor)
            count = 0
            for kind, source in source_queries(cursor).items():
                cursor.execute(
                    "INSERT crm_events.Event(SourceKind,SourceId,ConversationId,"
                    "SourceRevision,SourceOccurredAt,SourceAction) "
                    "SELECT TOP (100) ?,s.SourceId,s.ConversationId,"
                    "s.SourceRevision,s.SourceOccurredAt,s.SourceAction FROM ("
                    + source
                    + ") s WHERE "
                    + MISSING
                    + " ORDER BY s.SourceId",
                    kind,
                    kind,
                )
                count += cursor.rowcount
            return count

    def claim(self):
        with self.workspace.transaction(write=True) as cursor:
            self.verify(cursor)
            cursor.execute(
                "UPDATE crm_events.Event SET State='failed',LeaseToken=NULL,"
                "LeaseUntil=NULL,ErrorCode='lease_expired' WHERE State='leased' "
                "AND LeaseUntil<=SYSUTCDATETIME() AND Attempts>=5"
            )
            row = cursor.execute(
                "SELECT TOP (1) EventId FROM crm_events.Event "
                "WHERE Attempts<5 AND ((State='pending' "
                "AND NextAttemptAt<=SYSUTCDATETIME()) OR "
                "(State='leased' AND LeaseUntil<=SYSUTCDATETIME())) ORDER BY EventId"
            ).fetchone()
            if row is None:
                return None
            token = str(uuid4())
            cursor.execute(
                "UPDATE crm_events.Event SET State='leased',LeaseToken=?,"
                "LeaseUntil=DATEADD(second,30,SYSUTCDATETIME()),"
                "Attempts=Attempts+1,TotalAttempts=TotalAttempts+1 WHERE EventId=?",
                token,
                row[0],
            )
            return int(row[0]), token

    def prepare(self, event_id, token):
        with self.workspace.transaction(write=True) as cursor:
            self.verify(cursor)
            event = cursor.execute(
                "SELECT SourceKind,SourceId,ConversationId FROM crm_events.Event "
                "WHERE " + OWNER,
                event_id,
                token,
            ).fetchone()
            if event is None:
                raise HTTPException(409, "event_lease_lost")
            source = cursor.execute(
                "SELECT SourceId FROM (" + source_queries(cursor)[event[0]] + ") s "
                "WHERE SourceId=? AND ConversationId=?",
                event[1],
                event[2],
            ).fetchone()
            if source is None:
                raise HTTPException(422, "event_source_missing")
            values = cursor.execute(
                "SELECT COUNT_BIG(*),MAX(Sequence),"
                "(SELECT COALESCE(MAX(Revision),0) FROM crm.Operation "
                "WHERE ConversationId=?),"
                "(SELECT COALESCE(MAX(o.Revision),0) FROM crm_inbox.Operation o "
                "JOIN crm_inbox.Task t ON t.TaskId=TRY_CONVERT(uniqueidentifier,"
                "o.EntityKey) WHERE t.ConversationId=? "
                "AND o.Action IN ('task_create','task_edit')) "
                "FROM crm.Message WHERE ConversationId=?",
                event[2],
                event[2],
                event[2],
            ).fetchone()
            cursor.execute(
                "UPDATE crm_events.Event SET State='prepared',"
                "PreparedAt=SYSUTCDATETIME(),LeaseToken=NULL,LeaseUntil=NULL,"
                "ErrorCode=NULL WHERE " + OWNER,
                event_id,
                token,
            )
            if cursor.rowcount != 1:
                raise HTTPException(409, "event_lease_lost")
            if cursor.execute(
                "SELECT ConversationId FROM crm_events.Preparation "
                "WHERE ConversationId=?",
                event[2],
            ).fetchone():
                cursor.execute(
                    "UPDATE crm_events.Preparation SET "
                    "LastEventId=CASE WHEN LastEventId>? THEN LastEventId ELSE ? END,"
                    "MessageCount=?,LatestMessageSequence=?,SourceCrmRevision=?,"
                    "SourceInboxRevision=?,PreparedAt=SYSUTCDATETIME() "
                    "WHERE ConversationId=?",
                    event_id,
                    event_id,
                    *values,
                    event[2],
                )
            else:
                cursor.execute(
                    "INSERT crm_events.Preparation(ConversationId,LastEventId,"
                    "MessageCount,LatestMessageSequence,SourceCrmRevision,"
                    "SourceInboxRevision,PreparedAt) "
                    "VALUES(?,?,?,?,?,?,SYSUTCDATETIME())",
                    event[2],
                    event_id,
                    *values,
                )

    def fail(self, event_id, token, code="processing_unavailable"):
        with self.workspace.transaction(write=True) as cursor:
            self.verify(cursor)
            cursor.execute(
                "UPDATE crm_events.Event SET "
                "State=CASE WHEN Attempts>=5 THEN 'failed' ELSE 'pending' END,"
                "NextAttemptAt=DATEADD(second,POWER(2,Attempts),SYSUTCDATETIME()),"
                "ErrorCode=?,LeaseToken=NULL,LeaseUntil=NULL WHERE " + OWNER,
                "source_missing"
                if code == "event_source_missing"
                else "processing_unavailable",
                event_id,
                token,
            )

    def retry_failed(self, operation_id):
        with self.workspace.transaction(write=True) as cursor:
            self.verify(cursor)
            previous = cursor.execute(
                "SELECT RetriedCount FROM crm_events.RetryOperation "
                "WHERE OperationId=?",
                operation_id,
            ).fetchone()
            if previous is not None:
                return {"retried": previous[0]}
            cursor.execute(
                "UPDATE crm_events.Event SET State='pending',Attempts=0,"
                "NextAttemptAt=SYSUTCDATETIME(),ErrorCode=NULL "
                "WHERE EventId IN (SELECT TOP (25) EventId FROM crm_events.Event "
                "WHERE State='failed' ORDER BY EventId)"
            )
            count = cursor.rowcount
            cursor.execute(
                "INSERT crm_events.RetryOperation(OperationId,RetriedCount) "
                "VALUES(?,?)",
                operation_id,
                count,
            )
            return {"retried": count}

    def status(self):
        with self.workspace.transaction() as cursor:
            self.verify(cursor)
            counts = {state: 0 for state in ["pending", "leased", "prepared", "failed"]}
            for state, count in cursor.execute(
                "SELECT State,COUNT_BIG(*) FROM crm_events.Event GROUP BY State"
            ).fetchall():
                counts[state] = int(count)
            gaps = {}
            for kind, source in source_queries(cursor).items():
                gaps[kind] = int(
                    cursor.execute(
                        "SELECT COUNT_BIG(*) FROM (" + source + ") s WHERE " + MISSING,
                        kind,
                    ).fetchval()
                )
            coverage = rows(
                cursor.execute(
                    "SELECT (SELECT COUNT_BIG(*) FROM crm.Conversation) "
                    "AS conversations,COUNT_BIG(*) AS preparedConversations,"
                    "MAX(PreparedAt) AS lastPreparedAt FROM crm_events.Preparation"
                )
            )[0]
            return {"counts": counts, "uncaptured": gaps, **coverage}


class EventWorker:
    def __init__(self, repository):
        self.repository = repository
        self.stop_event = Event()
        self.thread = None
        self.health = {"state": "stopped", "lastCycleAt": None}

    def start(self):
        self.thread = Thread(target=self.run, name="crm-event-preparation", daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=15)

    def cycle(self):
        self.repository.capture()
        for _ in range(20):
            if self.stop_event.is_set():
                break
            claimed = self.repository.claim()
            if claimed is None:
                break
            try:
                self.repository.prepare(*claimed)
            except HTTPException as error:
                if error.status_code != 409:
                    self.repository.fail(*claimed, code=error.detail)
            except Exception:
                self.repository.fail(*claimed)

    def run(self):
        while not self.stop_event.is_set():
            try:
                self.cycle()
                self.health = {
                    "state": "running",
                    "lastCycleAt": datetime.now(timezone.utc).isoformat(),
                }
            except Exception:
                self.health = {**self.health, "state": "storage_unavailable"}
            self.stop_event.wait(5)
        self.health = {**self.health, "state": "stopped"}


def install_events(app: FastAPI):
    repository = ConversationEvents(SqlWorkspace(app.state.settings))
    app.state.conversation_events = repository
    app.state.event_worker = EventWorker(repository)
    router = APIRouter(prefix="/api/local/crm/events", tags=["local-events"])

    def call(request, method, *args):
        if request.app.state.settings.mode != "local_sql_copy":
            raise HTTPException(503, "local_sql_copy_disabled")
        try:
            data = getattr(request.app.state.conversation_events, method)(*args)
            if method == "status":
                worker = request.app.state.event_worker
                data["worker"] = {
                    **worker.health,
                    "alive": bool(worker.thread and worker.thread.is_alive()),
                }
            return JSONResponse(data, headers={"Cache-Control": "no-store"})
        except (pyodbc.Error, CatalogUnavailable):
            raise HTTPException(503, "events_storage_unavailable") from None

    @router.get("/status")
    def status(request: Request):
        return call(request, "status")

    @router.post("/retry")
    def retry(request: Request, body: RetryRequest):
        return call(request, "retry_failed", str(UUID(body.operationId)))

    app.include_router(router)
