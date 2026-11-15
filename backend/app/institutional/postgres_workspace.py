"""Native reads for the first PostgreSQL-backed CRM and Inbox routes."""

from fastapi import HTTPException

from app.institutional import db
from app.institutional.channel_workspace import Workspace as ChannelWorkspace
from app.institutional.workspace import PAGE, revision


class Workspace(ChannelWorkspace):
    def listing(
        self, area, q="", stage="", tag="", city="", contactType="", queue="all",
        user="", channel="", offset=0, anchor="", program="", program_id=None,
        state="", temperature="", riskLevel="",
    ):
        if area == "inbox":
            return super().listing(
                area, q=q, stage=stage, queue=queue, user=user, channel=channel,
                offset=offset, anchor=anchor, state=state, temperature=temperature,
                riskLevel=riskLevel,
            )
        if tag or city or contactType or program or program_id is not None:
            raise HTTPException(422, "rehearsal_filter_not_available")
        with self.transaction() as c:
            version = revision(c)
            if offset and not anchor:
                raise HTTPException(422, "page_anchor_required")
            if anchor and anchor != version:
                raise HTTPException(409, "page_changed")
            read = self.contacts
            filters = (q, stage)
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
