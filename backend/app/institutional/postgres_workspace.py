"""Native reads for the first PostgreSQL-backed CRM and Inbox routes."""

from fastapi import HTTPException

from app.institutional import db
from app.institutional.channel_workspace import Workspace as ChannelWorkspace
from app.institutional.workspace import PAGE, revision


class Workspace(ChannelWorkspace):
    def listing(
        self, area, q="", stage="", tag="", city="", contactType="", queue="all",
        user="", channel="", offset=0, anchor="", program="", program_id=None,
    ):
        if tag or city or contactType or user or channel or program or program_id is not None:
            raise HTTPException(422, "rehearsal_filter_not_available")
        if queue not in {"all", "unread", "open", "waiting", "closed", "human", "ai"}:
            raise HTTPException(422, "rehearsal_filter_not_available")
        with self.transaction() as c:
            version = revision(c)
            if offset and not anchor:
                raise HTTPException(422, "page_anchor_required")
            if anchor and anchor != version:
                raise HTTPException(409, "page_changed")
            if area == "clients":
                read = self.contacts
                filters = (q, stage)
            else:
                read = self.inbox
                filters = (q, stage, queue)
            rows = read(c, *filters, offset)
            items = [
                dict(zip((col[0] for col in c.description[:-1]), row[:-1], strict=True))
                for row in rows
            ]
            first_rows = read(c, *filters, 0) if offset and not rows else rows
            count = first_rows[0][-1] if first_rows else 0
            for item in items:
                if item.get("updatedAt"):
                    item["updatedAt"] = db.utc(item["updatedAt"])
                if "unread" in item:
                    item["unread"] = bool(item["unread"])
            return {
                "items": items, "total": count, "offset": offset, "limit": PAGE,
                "hasMore": offset + len(items) < count, "revision": version,
            }

    def contacts(self, c, query, stage, offset):
        return c.native(
            """SELECT p.contactid AS id,p.name AS name,p.phone AS phone,p.city AS city,
               p.stage AS stage,p.tags AS tags,p.programid AS programId,p.updatedat AS updatedAt,
               count(*) OVER() AS total
               FROM rinovaplus_crm.crmcontacto p
               WHERE (%s='' OR strpos(lower(p.name COLLATE "default"),lower(%s))>0
                         OR strpos(p.phone COLLATE "C",%s)>0)
                   AND (%s='' OR p.stage=%s)
               ORDER BY p.updatedat DESC,p.contactid LIMIT %s OFFSET %s""",
            query, query, query, stage, stage, PAGE, offset,
        ).fetchall()

    def inbox(self, c, query, stage, queue, offset):
        return c.native(
            """SELECT v.conversationid AS conversationId,p.contactid AS id,
               p.name AS name,p.phone AS phone,p.city AS city,p.stage AS stage,p.tags AS tags,
               v.state AS state,v.priority AS priority,v.controlmode AS mode,
               v.unread AS unread,v.updatedat AS updatedAt,v.assignee AS assignee,
               coalesce(route.channel,'local') AS channel,count(*) OVER() AS total
               FROM rinovaplus_crm.crmconversacion v
               JOIN rinovaplus_crm.crmcontacto p ON p.contactid=v.contactid
               LEFT JOIN LATERAL (
                 SELECT a.channel FROM rinovaplus_crm.crmcanalinstitucionalidentidadexterna i
                 JOIN rinovaplus_crm.crmcanalinstitucionalintegracion a USING (institutionid,integrationid)
                 WHERE i.institutionid=%s AND i.conversationid=v.conversationid
                 ORDER BY i.identityid LIMIT 1
               ) route ON true
               WHERE (%s='' OR strpos(lower(p.name COLLATE "default"),lower(%s))>0
                          OR strpos(p.phone COLLATE "C",%s)>0)
                 AND (%s='' OR p.stage=%s)
                 AND (%s='all' OR (%s='unread' AND v.unread=1)
                      OR v.state=%s OR v.controlmode=%s)
               ORDER BY v.updatedat DESC,v.conversationid LIMIT %s OFFSET %s""",
            db.institution(self.profile), query, query, query, stage, stage,
            queue, queue, queue, queue, PAGE, offset,
        ).fetchall()

    def messages(self, conversation, before=None):
        before = int(before) if before else None
        if before is not None and before > 9223372036854775807:
            raise HTTPException(422, "invalid_message_cursor")
        with self.transaction() as c:
            self.exists(c, conversation)
            readings = c.native(
                "SELECT * FROM rinovaplus_crm.message_page(%s,%s,%s)",
                db.institution(self.profile), conversation, before,
            ).fetchall()
            entries = [
                {"id": row[0], "body": row[1], "direction": row[2],
                 "createdAt": db.utc(row[3]), "sequence": str(row[4])}
                for row in readings[:50]
            ]
            return {
                "items": list(reversed(entries)), "hasMore": len(readings) > 50,
                "before": entries[-1]["sequence"] if len(entries) == 50 else None,
                "revision": revision(c),
            }
