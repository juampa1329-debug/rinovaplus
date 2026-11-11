"""Paginated local conversations; no dependency on the workspace snapshot."""

import json
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

import pyodbc
from fastapi import APIRouter, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from app.modules.catalog.domain.contracts import CatalogUnavailable
from app.sql_workspace import (
    CONTACT_COLUMNS,
    CONTACT_KEYS,
    PRIORITIES,
    STATES,
    ContactMutation,
    ConversationMutation,
    Identifier,
    MessageMutation,
)

PAGE_SIZE = 25
MESSAGE_SIZE = 50


def rows(cursor):
    def value(item):
        if isinstance(item, datetime):
            return item.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
        if isinstance(item, UUID):
            return str(item).lower()
        return item

    keys = [column[0] for column in cursor.description]
    return [
        {key: value(item) for key, item in zip(keys, row, strict=True)}
        for row in cursor.fetchall()
    ]


def pattern(value):
    return "%" + value.replace("[", "[[]").replace("%", "[%]").replace("_", "[_]") + "%"


SUMMARY_SELECT = (
    "SELECT c.ConversationId AS id,c.ContactId AS "
    "clientId,\n    p.Name AS name,p.Phone AS phone"
    ",c.State AS state,c.Priority AS priority,\n   "
    " c.Assignee AS assignee,c.ControlMode AS mode"
    ",c.Unread AS unread,\n    c.CreatedAt AS creat"
    "edAt,c.UpdatedAt AS updatedAt,\n    m.Body AS "
    "preview,m.CreatedAt AS lastMessageAt\n    FROM"
    " crm.Conversation c JOIN crm.Contact p ON p.C"
    "ontactId=c.ContactId\n    OUTER APPLY (SELECT "
    "TOP (1) Body,CreatedAt FROM crm.Message\n     "
    "   WHERE ConversationId=c.ConversationId ORDE"
    "R BY Sequence DESC) m"
)


def thread(item):
    item = {
        **item,
        "id": str(item["id"]).lower(),
        "clientId": str(item["clientId"]).lower(),
    }
    return {
        **item,
        "channel": item.get("channel", "Local"),
        "messages": [],
        "workflow": {
            "state": STATES[item["state"]],
            "priority": PRIORITIES[item["priority"]],
            "assignee": item.get("assignee") or "Sin asignar",
            "revision": 0,
            "tasks": [],
            "events": [],
        },
    }


def channel_expression(cursor):
    if not cursor.execute(
        "SELECT OBJECT_ID(N'crm_channels.ExternalIdentity')"
    ).fetchone()[0]:
        return "N'Local'"
    return "COALESCE((SELECT STRING_AGG(ch.label,N', ') WITHIN GROUP(ORDER BY ch.label) FROM (SELECT DISTINCT CASE i.Channel WHEN 'whatsapp' THEN N'WhatsApp' WHEN 'messenger' THEN N'Messenger' WHEN 'instagram' THEN N'Instagram' WHEN 'tiktok' THEN N'TikTok' ELSE N'Facebook' END AS label FROM crm_channels.ExternalIdentity i WHERE i.ConversationId=c.ConversationId) ch),N'Local')"


def conversation_select(cursor):
    return SUMMARY_SELECT.replace(
        "p.Name AS name", channel_expression(cursor) + " AS channel,p.Name AS name"
    )


class InboxRepository:
    def __init__(self, workspace):
        self.workspace = workspace

    def list(
        self,
        query="",
        channel="",
        state="",
        mode="",
        assignment="",
        assignee="",
        unread=False,
        offset=0,
        human_id=None,
        ai_id=None,
        sla_filter="",
        stage="",
    ):
        with self.workspace.transaction() as cursor:
            from app.modules.inbox.application.operations import (
                SLA_JOIN,
                InboxOperations,
            )

            available = InboxOperations.present(cursor)
            extra = ""
            predicates = ""
            extra_args = []
            if available:
                InboxOperations.verify(cursor)
                extra = SLA_JOIN
                predicates = (
                    " AND (? IS NULL OR ia.HumanEmployeeId=?) AND (? IS NULL OR "
                    "ia.AiAgentId=?) AND (?='' OR sla.status=?)"
                )
                extra_args = [human_id, human_id, ai_id, ai_id, sla_filter, sla_filter]
            elif human_id is not None or ai_id is not None or sla_filter:
                raise HTTPException(503, "inbox_operations_not_installed")
            query = query.strip()
            channel_filter = "(?='' OR (?='Local' AND NOT EXISTS(SELECT 1 FROM crm_channels.ExternalIdentity i WHERE i.ConversationId=c.ConversationId)) OR EXISTS(SELECT 1 FROM crm_channels.ExternalIdentity i WHERE i.ConversationId=c.ConversationId AND CASE i.Channel WHEN 'whatsapp' THEN 'WhatsApp' WHEN 'messenger' THEN 'Messenger' WHEN 'instagram' THEN 'Instagram' WHEN 'tiktok' THEN 'TikTok' ELSE 'Facebook' END=?))"
            found = rows(
                cursor.execute(
                    conversation_select(cursor)
                    + extra
                    + (
                        "\n                WHERE (?='' OR p.Name LIKE ?"
                        " OR p.Phone LIKE ? OR m.Body\nLIKE ?)\n        "
                        "        AND " + channel_filter + " AND (?='' OR "
                        "c.State=?)\n                AND (?='' OR c.Con"
                        "trolMode=?)\n                AND (?='' OR (?='"
                        "assigned'\n                    AND NULLIF(LTRI"
                        "M(RTRIM(c.Assignee)),'') IS NOT NULL)\n       "
                        "             OR (?='unassigned' AND\nNULLIF(LT"
                        "RIM(RTRIM(c.Assignee)),'') IS NULL))\n        "
                        "        AND (?='' OR LTRIM(RTRIM(c.Assignee))"
                        "=?)\n                AND (?=0 OR c.Unread=1) AND (?='' OR p.Stage=?)\n"
                    )
                    + predicates
                    + (
                        " ORDER BY c.UpdatedAt DESC,c.ConversationId\n "
                        "               OFFSET ? ROWS FETCH NEXT ? ROW"
                        "S ONLY"
                    ),
                    query,
                    pattern(query),
                    pattern(query),
                    pattern(query),
                    channel,
                    channel,
                    channel,
                    state,
                    state,
                    mode,
                    mode,
                    assignment,
                    assignment,
                    assignment,
                    assignee.strip(),
                    assignee.strip(),
                    int(unread),
                    stage,
                    stage,
                    *extra_args,
                    offset,
                    PAGE_SIZE + 1,
                )
            )
            return {
                "items": [thread(item) for item in found[:PAGE_SIZE]],
                "offset": offset,
                "limit": PAGE_SIZE,
                "hasMore": len(found) > PAGE_SIZE,
            }

    def options(self):
        with self.workspace.transaction() as cursor:
            has_rows = (
                cursor.execute(
                    "SELECT TOP (1) ConversationId FROM crm.Conversation"
                ).fetchone()
                is not None
            )
            values = rows(
                cursor.execute(
                    (
                        "SELECT DISTINCT LTRIM(RTRIM(Assignee)) AS lab"
                        "el\n                FROM crm.Conversation\n    "
                        "            WHERE NULLIF(LTRIM(RTRIM(Assignee"
                        ")),'') IS NOT NULL\n                ORDER BY l"
                        "abel"
                    )
                )
            )
            return {
                "channels": [
                    r[0]
                    for r in cursor.execute(
                        "SELECT DISTINCT CASE Channel WHEN 'whatsapp' THEN 'WhatsApp' WHEN 'messenger' THEN 'Messenger' WHEN 'instagram' THEN 'Instagram' WHEN 'tiktok' THEN 'TikTok' ELSE 'Facebook' END AS label FROM crm_channels.ExternalIdentity "
                        "UNION SELECT N'Local' WHERE EXISTS(SELECT 1 FROM crm.Conversation c WHERE NOT EXISTS(SELECT 1 FROM crm_channels.ExternalIdentity i WHERE i.ConversationId=c.ConversationId)) ORDER BY label"
                    ).fetchall()
                ]
                if has_rows
                else [],
                "assignees": [item["label"] for item in values],
            }

    def detail(self, contact_id):
        with self.workspace.transaction() as cursor:
            found = rows(
                cursor.execute(
                    conversation_select(cursor) + " WHERE c.ContactId=?", contact_id
                )
            )
            if not found:
                raise HTTPException(404, "conversation_not_found")
            row = cursor.execute(
                f"SELECT {CONTACT_COLUMNS} FROM crm.Contact WHERE ContactId=?",
                contact_id,
            ).fetchone()
            client = dict(zip(CONTACT_KEYS, row, strict=True))
            client["id"] = str(client["id"]).lower()
            client["customValues"] = json.loads(client["customValues"])
            from app.modules.contacts.api.router import decorate

            decorate(cursor, [client])
            from app.modules.contacts.application.merge import group_view
            from app.modules.inbox.application.operations import InboxOperations

            conversation_id = str(found[0]["id"])
            destinations = rows(
                cursor.execute(
                    "SELECT i.IdentityId AS id,i.Channel AS channel,i.ExternalId AS externalId,a.State AS state,a.Configuration AS configuration "
                    "FROM crm_channels.ExternalIdentity i JOIN crm_channels.Account a ON a.Channel=i.Channel "
                    "WHERE i.ConversationId=? ORDER BY i.Channel,i.IdentityId",
                    conversation_id,
                )
            )
            for destination in destinations:
                configuration = json.loads(destination.pop("configuration"))
                destination["mediaKinds"] = (
                    ["image", "audio", "document"]
                    if destination["channel"] in ("whatsapp", "messenger")
                    or (
                        destination["channel"] == "instagram"
                        and configuration.get("instagramLogin") == "facebook"
                        and configuration.get("pageId")
                    )
                    else ["image"]
                    if destination["channel"] == "tiktok"
                    else []
                )
            profile = cursor.execute(
                "SELECT LeadScore,Temperature,UpdatedAt FROM crm_channels.ConversationProfile WHERE ConversationId=?",
                conversation_id,
            ).fetchone()
            control = cursor.execute(
                "SELECT Epoch,ReadSequence FROM crm_channels.ConversationControl WHERE ConversationId=?",
                conversation_id,
            ).fetchone()
            in_flight = cursor.execute(
                "SELECT COUNT(*) FROM crm_channels.MessageRoute r JOIN crm.Message m ON m.MessageId=r.MessageId "
                "JOIN crm_channels.outbound_queue q ON q.QueueId=r.QueueId WHERE m.ConversationId=? AND r.StartedAt IS NOT NULL "
                "AND r.CompletedAt IS NULL AND q.State IN('sending','uncertain')",
                conversation_id,
            ).fetchval()
            operation = InboxOperations(self.workspace).conversation(
                conversation_id, cursor=cursor
            )
            mini_crm = {
                "prospect": {
                    "id": client["id"],
                    "name": client["name"],
                    "source": "crm_declared",
                },
                "programInterest": {
                    "id": client["programId"],
                    "label": client["program"],
                    "interests": client["interests"],
                },
                "priority": found[0]["priority"],
                "leadScore": profile[0] if profile else None,
                "temperature": profile[1] if profile else None,
                "assessmentSource": "manual" if profile else "not_evaluated",
                "takeover": found[0]["mode"] == "human",
                "controlEpoch": str(control[0] if control else 0),
                "readSequence": str(control[1] if control else 0),
                "inFlightOrUncertain": in_flight,
                "stateScope": "conversation",
                "assignment": operation["assignment"],
                "firstResponseDueAt": operation["assignment"]["firstResponseDueAt"],
                "slaDueAt": operation["assignment"]["dueAt"],
                "slaStatus": operation["assignment"]["slaStatus"],
            }

            return {
                "client": client,
                "contactGroup": group_view(cursor, client["id"]),
                "thread": thread(found[0]),
                "destinations": destinations,
                "miniCrm": mini_crm,
                "operation": operation,
                "revision": self.workspace.revision(cursor),
            }

    def messages(self, conversation_id, before=None):
        with self.workspace.transaction() as cursor:
            if (
                cursor.execute(
                    "SELECT ConversationId FROM crm.Conversation "
                    "WHERE ConversationId=?",
                    conversation_id,
                ).fetchone()
                is None
            ):
                raise HTTPException(404, "conversation_not_found")
            found = rows(
                cursor.execute(
                    "SELECT TOP(51) m.MessageId AS id,m.Body AS body,m.Direction AS direction,m.CreatedAt AS createdAt,m.Sequence AS sequence,"
                    "COALESCE(i.Channel,q.Channel,e.Channel,'local') AS channel,COALESCE(CONVERT(varchar(36),r.IdentityId),CONVERT(varchar(36),q.IdentityId)) AS identityId,"
                    "CASE WHEN m.Direction='incoming' THEN 'received' WHEN q.QueueId IS NULL THEN 'local' ELSE q.State END AS deliveryState,"
                    "q.LastError AS deliveryError,a.MediaId AS mediaId,a.State AS mediaState,a.Kind AS mediaKind,a.FileName AS mediaName,a.ActualMime AS mediaMime,a.ByteLength AS mediaSize,a.DurationSeconds AS mediaDuration,a.LastError AS mediaError FROM crm.Message m LEFT JOIN crm_channels.MessageRoute r ON r.MessageId=m.MessageId "
                    "LEFT JOIN crm_channels.MediaAsset a ON a.MessageId=m.MessageId AND a.ConversationId=m.ConversationId AND a.State<>'deleted' "
                    "LEFT JOIN crm_channels.ExternalIdentity i ON i.IdentityId=r.IdentityId LEFT JOIN crm_channels.outbound_queue q ON q.MessageId=m.MessageId "
                    "OUTER APPLY(SELECT TOP(1) Channel FROM crm_channels.ExternalMessage WHERE MessageId=m.MessageId ORDER BY Channel,ExternalId) e "
                    "WHERE m.ConversationId=? AND (? IS NULL OR m.Sequence<?) ORDER BY m.Sequence DESC",
                    conversation_id,
                    before,
                    before,
                )
            )
            selected = found[:MESSAGE_SIZE]
            # String cursors preserve SQL bigint precision in the browser.
            for item in selected:
                item["sequence"] = str(item["sequence"])
                item["attachment"] = (
                    {
                        "id": item["mediaId"],
                        "state": item["mediaState"],
                        "kind": item["mediaKind"],
                        "name": item["mediaName"],
                        "mime": item["mediaMime"],
                        "size": item["mediaSize"],
                        "duration": float(item["mediaDuration"])
                        if item["mediaDuration"] is not None
                        else None,
                        "error": item["mediaError"],
                    }
                    if item["mediaId"]
                    else None
                )
                for key in (
                    "mediaId",
                    "mediaState",
                    "mediaKind",
                    "mediaName",
                    "mediaMime",
                    "mediaSize",
                    "mediaDuration",
                    "mediaError",
                ):
                    item.pop(key, None)
            return {
                "items": list(reversed(selected)),
                "hasMore": len(found) > MESSAGE_SIZE,
                "before": selected[-1]["sequence"] if selected else None,
                "limit": MESSAGE_SIZE,
            }


def install_inbox(application: FastAPI):
    repository = InboxRepository
    if application.state.settings.mode == "local_foundation":
        from app.foundation_inbox import FoundationInboxRepository

        repository = FoundationInboxRepository
    application.state.inbox = repository(application.state.sql_workspace)
    router = APIRouter(prefix="/api/local/crm/inbox", tags=["local-sql-inbox"])

    def call(request, method, *args):
        if request.app.state.settings.mode not in (
            "local_sql_copy",
            "local_foundation",
        ):
            raise HTTPException(503, "local_sql_copy_disabled")
        try:
            result = getattr(request.app.state.inbox, method)(*args)
            return JSONResponse(result, headers={"Cache-Control": "no-store"})
        except (pyodbc.Error, CatalogUnavailable):
            raise HTTPException(503, "local_sql_unavailable") from None

    @router.get("")
    def listing(
        request: Request,
        q: str = Query("", max_length=200),
        channel: str = Query("", max_length=60),
        state: Literal["", "open", "waiting", "closed"] = "",
        mode: Literal["", "human", "ai"] = "",
        assignment: Literal["", "assigned", "unassigned"] = "",
        assignee: str = Query("", max_length=100),
        unread: bool = False,
        offset: int = Query(0, ge=0, le=1000000),
        humanId: int | None = Query(None, ge=1, le=2147483647),
        aiId: Identifier | None = None,
        sla: Literal[
            "", "not_configured", "closed", "no_incoming", "on_time", "overdue"
        ] = "",
        stage: str = Query("", max_length=60),
    ):
        return call(
            request,
            "list",
            q,
            channel,
            state,
            mode,
            assignment,
            assignee,
            unread,
            offset,
            humanId,
            aiId,
            sla,
            stage,
        )

    @router.get("/options")
    def options(request: Request):
        return call(request, "options")

    @router.get("/contacts/{contact_id}")
    def detail(request: Request, contact_id: Identifier):
        return call(request, "detail", contact_id)

    @router.get("/conversations/{conversation_id}/messages")
    def messages(
        request: Request,
        conversation_id: Identifier,
        before: int | None = Query(None, ge=1, le=9223372036854775807),
    ):
        return call(request, "messages", conversation_id, before)

    def mutate(request, action, identifier, body):
        if request.app.state.settings.mode not in (
            "local_sql_copy",
            "local_foundation",
        ):
            raise HTTPException(503, "local_sql_copy_disabled")
        try:
            result = request.app.state.sql_workspace.mutate(
                action, identifier, body, compact=True
            )
            return JSONResponse(result, headers={"Cache-Control": "no-store"})
        except (pyodbc.Error, CatalogUnavailable):
            raise HTTPException(503, "local_sql_unavailable") from None

    @router.put("/contacts/{contact_id}")
    def save_contact(request: Request, contact_id: Identifier, body: ContactMutation):
        return mutate(request, "edit_contact", contact_id, body)

    @router.put("/conversations/{conversation_id}")
    def change(
        request: Request, conversation_id: Identifier, body: ConversationMutation
    ):
        return mutate(request, "update_conversation", conversation_id, body)

    @router.post("/conversations/{conversation_id}/messages")
    def send(request: Request, conversation_id: Identifier, body: MessageMutation):
        return mutate(request, "add_message", conversation_id, body)

    application.include_router(router)
    from app.modules.inbox.application.media import install_media

    if application.state.settings.mode != "local_foundation":
        install_media(application)
