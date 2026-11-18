"""Per-user notification acknowledgement, independent of comment/AI workflow."""

import json
from datetime import datetime, timezone

from fastapi import HTTPException, Request
from pydantic import Field

from app.institutional.auth import authorize
from app.institutional.db import audit, institution, record_operation, replay, rows, utc
from app.institutional.models import Strict
from app.institutional.store import transaction

ACTION = "comments.notifications.read"


class Acknowledge(Strict):
    operation_id: str
    read_through: str = Field(max_length=40)


def parse_cutoff(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)
    except (ValueError, TypeError):
        raise HTTPException(422, "invalid_notification_cutoff") from None


def last_seen(c, settings, actor):
    value = c.execute(
        "SELECT MAX(ResourceRef) FROM crm_access.Operation WHERE InstitutionId=? "
        "AND ActorId=? AND Action=?",
        institution(settings),
        actor,
        ACTION,
    ).fetchval()
    return parse_cutoff(value) if value else datetime(1970, 1, 1)


class Notifications:
    def __init__(self, settings):
        self.settings = settings

    def read(self, authority):
        with transaction(self.settings, anonymous=True) as c:
            actor = authorize(c, self.settings, authority, "inbox.read")
            cutoff = c.execute("SELECT SYSUTCDATETIME()").fetchval()
            after = last_seen(c, self.settings, actor["UserId"])
            params = (institution(self.settings), after, cutoff)
            where = (
                " FROM crm_channels2.SocialComment s JOIN crm_channels2.Integration i "
                "ON i.InstitutionId=s.InstitutionId AND i.IntegrationId=s.IntegrationId "
                "WHERE s.InstitutionId=? AND s.ReceivedAt>? AND s.ReceivedAt<=? "
                "AND ISNULL(JSON_VALUE(s.Payload,'$._crm.state'),'new')='new'"
            )
            total = c.execute("SELECT COUNT(*)" + where, *params).fetchval()
            values = rows(
                c,
                "SELECT TOP(8) s.CommentId,s.Body,s.AuthorExternalId,s.Payload,"
                "s.ReceivedAt,i.Channel"
                + where
                + " ORDER BY s.ReceivedAt DESC,s.CommentId",
                *params,
            )
            return {
                "total": total,
                "read_through": utc(cutoff),
                "items": [
                    {
                        "id": str(v["CommentId"]).lower(),
                        "body": v["Body"],
                        "author": display_author(v),
                        "channel": v["Channel"],
                        "received_at": utc(v["ReceivedAt"]),
                    }
                    for v in values
                ],
            }

    def acknowledge(self, authority, body):
        cutoff = parse_cutoff(body.read_through)
        resource = cutoff.isoformat(timespec="microseconds") + "Z"
        with transaction(self.settings, True, anonymous=True) as c:
            actor = authorize(c, self.settings, authority, "inbox.write")
            digest, prior = replay(
                c,
                self.settings,
                actor["UserId"],
                body.operation_id,
                ACTION,
                resource,
                body.model_dump(),
            )
            if prior:
                return prior
            now = c.execute("SELECT SYSUTCDATETIME()").fetchval()
            if cutoff > now:
                raise HTTPException(422, "invalid_notification_cutoff")
            result = {"saved": True, "read_through": resource}
            record_operation(
                c,
                self.settings,
                actor["UserId"],
                body.operation_id,
                ACTION,
                resource,
                digest,
                result,
            )
            audit(c, self.settings, actor["UserId"], ACTION, resource)
            return result


def display_author(value):
    provider = json.loads(value.get("Payload") or "{}").get("provider") or {}
    actor = provider.get("from")
    if isinstance(actor, dict) and actor.get("id") == value["AuthorExternalId"]:
        for field in ("name", "username"):
            if isinstance(actor.get(field), str) and actor[field].strip():
                return actor[field].strip()[:100]
    return value["AuthorExternalId"]


def install(app, settings):
    service = Notifications(settings)

    @app.get("/api/institution/comments/notifications")
    def notifications(request: Request):
        return service.read(request.state.authority)

    @app.post("/api/institution/comments/notifications/read")
    def read(request: Request, body: Acknowledge):
        return service.acknowledge(request.state.authority, body)
