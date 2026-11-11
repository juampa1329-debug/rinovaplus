"""Inbox queries supported by B001 only; no channels or academic joins."""

import json

from fastapi import HTTPException

from app.modules.inbox.application.service import (
    MESSAGE_SIZE,
    PAGE_SIZE,
    SUMMARY_SELECT,
    pattern,
    rows,
    thread,
)
from app.sql_workspace import CONTACT_COLUMNS, CONTACT_KEYS


class FoundationInboxRepository:
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
        if (
            channel not in ("", "Local")
            or mode not in ("", "human")
            or assignee
            or human_id is not None
            or ai_id is not None
            or sla_filter
        ):
            raise HTTPException(503, "foundation_capability_unavailable")
        predicates, args = ["1=1"], []
        if query.strip():
            predicates.append("(p.Name LIKE ? OR p.Phone LIKE ? OR p.City LIKE ?)")
            args.extend([pattern(query.strip())] * 3)
        for expression, value in (
            ("c.State", state),
            ("c.ControlMode", mode),
            ("p.Stage", stage),
        ):
            if value:
                predicates.append(expression + "=?")
                args.append(value)
        if assignment:
            predicates.append(
                "c.Assignee IS " + ("NOT NULL" if assignment == "assigned" else "NULL")
            )
        if unread:
            predicates.append("c.Unread=1")
        with self.workspace.transaction() as cursor:
            found = rows(
                cursor.execute(
                    SUMMARY_SELECT
                    + " WHERE "
                    + " AND ".join(predicates)
                    + " ORDER BY c.UpdatedAt DESC,c.ConversationId "
                    "OFFSET ? ROWS FETCH NEXT ? ROWS ONLY",
                    *args,
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
            present = cursor.execute("SELECT TOP(1) 1 FROM crm.Conversation").fetchone()
            return {"channels": ["Local"] if present else [], "assignees": []}

    def detail(self, contact_id):
        with self.workspace.transaction() as cursor:
            found = rows(
                cursor.execute(SUMMARY_SELECT + " WHERE c.ContactId=?", contact_id)
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
            return {
                "client": client,
                "contactGroup": None,
                "thread": thread(found[0]),
                "destinations": [],
                "operation": None,
                "miniCrm": {
                    "priority": found[0]["priority"],
                    "leadScore": None,
                    "temperature": None,
                    "assessmentSource": "not_evaluated",
                    "takeover": True,
                    "stateScope": "conversation",
                },
                "revision": self.workspace.revision(cursor),
                "capabilities": {
                    "localText": True,
                    "assessment": False,
                    "assignment": False,
                    "academicProfile": False,
                    "externalDelivery": False,
                },
            }

    def messages(self, conversation_id, before=None):
        with self.workspace.transaction() as cursor:
            if not cursor.execute(
                "SELECT 1 FROM crm.Conversation WHERE ConversationId=?", conversation_id
            ).fetchone():
                raise HTTPException(404, "conversation_not_found")
            found = rows(
                cursor.execute(
                    "SELECT TOP(51) MessageId AS id,Body AS body,"
                    "Direction AS direction,"
                    "CreatedAt AS createdAt,Sequence AS sequence FROM crm.Message "
                    "WHERE ConversationId=? AND (? IS NULL OR Sequence<?) "
                    "ORDER BY Sequence DESC",
                    conversation_id,
                    before,
                    before,
                )
            )
            selected = found[:MESSAGE_SIZE]
            for item in selected:
                item.update(
                    sequence=str(item["sequence"]),
                    channel="local",
                    identityId=None,
                    deliveryState="local",
                    deliveryError=None,
                    attachment=None,
                )
            return {
                "items": list(reversed(selected)),
                "hasMore": len(found) > MESSAGE_SIZE,
                "before": selected[-1]["sequence"] if selected else None,
                "limit": MESSAGE_SIZE,
            }
