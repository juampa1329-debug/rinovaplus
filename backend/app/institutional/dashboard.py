"""Read-only operational aggregates; UTC storage, Bogotá calendar, no provider IO."""

import json
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Query

from app.institutional.auth import authorize
from app.institutional.comment_threads import table
from app.institutional.db import institution
from app.institutional.policy import request_authority
from app.institutional.store import transaction

BOGOTA = timezone(timedelta(hours=-5))


def window(days, now=None):
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(BOGOTA).replace(hour=0, minute=0, second=0, microsecond=0)
    start = today - timedelta(days=days - 1)
    return start.astimezone(timezone.utc), now.astimezone(timezone.utc)


def permitted(actions, enabled, action, module):
    return action in actions and enabled.get(module, False) is True


def read(settings, days=7, now=None):
    start, end = window(days, now)
    # Native PG timestamps are UTC without a zone, as in the existing workspace.
    since, until = start.replace(tzinfo=None), end.replace(tzinfo=None)
    with transaction(settings, permission="self") as c:
        actor = authorize(c, settings, request_authority.get())
        actions = json.loads(actor["Actions"])
        document = c.execute("SELECT Document FROM crm_access.Setting WHERE InstitutionId=? AND Section='modules'", institution(settings)).fetchval()
        enabled = json.loads(document)["enabled"]
        if not enabled.get("overview", False):
            raise HTTPException(403, "module_disabled")
        result = {"generated_at": end.isoformat(), "start": start.isoformat(), "end": end.isoformat(), "timezone": "America/Bogota", "days": days, "inbox": None, "followups": None, "comments": None}
        if permitted(actions, enabled, "inbox.read", "inbox"):
            messages = table(settings, "crm.Message")
            conversations = table(settings, "crm.Conversation")
            routes = table(settings, "crm_channels2.MessageRoute")
            jobs = table(settings, "crm_channels2.SendJob")
            identities = table(settings, "crm_channels2.ExternalIdentity")
            accounts = table(settings, "crm_channels2.Integration")
            # One row per persisted message. EXISTS avoids receipt/job fan-out;
            # queued/failed/uncertain outgoing messages never count as sent.
            base = f"""WITH activity AS (
              SELECT m.messageid,m.conversationid,m.direction,m.createdat,m.sequence,
                COALESCE((SELECT i.channel FROM {identities} x JOIN {accounts} i
                  ON i.institutionid=x.institutionid AND i.integrationid=x.integrationid
                  WHERE x.institutionid=%s AND x.conversationid=m.conversationid
                  ORDER BY x.identityid LIMIT 1),'local') channel,
                EXISTS(SELECT 1 FROM {jobs} q WHERE q.institutionid=%s
                  AND q.messageid=m.messageid AND q.externalid IS NOT NULL
                  AND q.state IN ('sent','delivered','read')) confirmed,
                EXISTS(SELECT 1 FROM {routes} r WHERE r.institutionid=%s
                  AND r.messageid=m.messageid AND r.actorkind='bot') ai
              FROM {messages} m WHERE m.createdat>=%s AND m.createdat<=%s
            ) """
            args = (institution(settings),) * 3 + (since, until)
            totals = c.native(base + """SELECT
              count(DISTINCT conversationid) FILTER(WHERE direction='incoming'),
              count(DISTINCT a.conversationid) FILTER(WHERE a.direction='incoming' AND EXISTS(
                SELECT 1 FROM activity reply WHERE reply.conversationid=a.conversationid
                AND reply.sequence>a.sequence AND reply.direction='outgoing' AND reply.confirmed)),
              count(*) FILTER(WHERE direction='incoming'),
              count(*) FILTER(WHERE direction='outgoing' AND confirmed),
              count(*) FILTER(WHERE direction='outgoing' AND confirmed AND ai)
              FROM activity a""", *args).fetchone()
            daily = c.native(base + """SELECT (createdat-interval '5 hours')::date day,
              count(*) FILTER(WHERE direction='incoming'),
              count(*) FILTER(WHERE direction='outgoing' AND confirmed)
              FROM activity GROUP BY day ORDER BY day""", *args).fetchall()
            channels = c.native(base + """SELECT channel,count(*) FROM activity
              WHERE direction='incoming' GROUP BY channel ORDER BY count(*) DESC,channel""", *args).fetchall()
            states = c.native(f"SELECT controlmode,count(*) FROM {conversations} GROUP BY controlmode").fetchall()
            result["inbox"] = dict(zip(("conversations", "attended", "incoming", "sent", "ai_sent"), totals, strict=True))
            result["inbox"].update(daily=[{"day": str(row[0]), "incoming": row[1], "sent": row[2]} for row in daily], channels=[{"channel": row[0], "count": row[1]} for row in channels], modes=[{"mode": row[0], "count": row[1]} for row in states])
            from app.institutional.comment_threads import incoming_only_sql
            row = c.execute("SELECT COUNT(*) FROM crm_channels2.SocialComment s JOIN crm_channels2.Integration i ON i.InstitutionId=s.InstitutionId AND i.IntegrationId=s.IntegrationId WHERE s.InstitutionId=? AND s.ReceivedAt>=? AND s.ReceivedAt<=?" + incoming_only_sql(), institution(settings), since, until).fetchone()
            result["comments"] = {"received": row[0]}
        if permitted(actions, enabled, "crm.read", "clients"):
            tasks = table(settings, "crm_workspace.Task")
            totals = c.native(f"""SELECT count(*) FILTER(WHERE status='pending'),
              count(*) FILTER(WHERE status='pending' AND dueat<%s),
              count(*) FILTER(WHERE status='completed' AND updatedat>=%s AND updatedat<=%s)
              FROM {tasks} WHERE institutionid=%s""", until, since, until, institution(settings)).fetchone()
            result["followups"] = dict(zip(("pending", "overdue", "completed"), totals, strict=True))
    return result


def install(app, settings):
    @app.get("/api/institution/dashboard")
    def dashboard(days: int = Query(7, ge=1, le=30)):
        return read(settings, days)
