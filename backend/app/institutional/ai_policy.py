"""Revision-safe writes of validated, bounded AI policy sections."""

import json

from fastapi import HTTPException


def save(settings, authority, operation, revision, changed, action, *, recent=True):
    from app.institutional import db
    from app.institutional.auth import authorize
    from app.institutional.settings import setting, validate_links
    from app.institutional.store import transaction

    with transaction(settings, True, anonymous=True) as c:
        actor = authorize(c, settings, authority, "settings.ai.write", recent=recent)
        digest, previous = db.replay(
            c,
            settings,
            actor["UserId"],
            operation,
            action,
            "ai",
            {"revision": revision, **changed},
        )
        if previous:
            return previous
        current = setting(c, settings, "ai")
        if current["revision"] != revision:
            raise HTTPException(409, "revision_conflict")
        validate_links(c, settings, "ai", changed)
        document = {**current["document"], **changed}
        raw = json.dumps(document, ensure_ascii=False)
        c.execute(
            "UPDATE crm_access.Setting SET Document=?,Revision=Revision+1,UpdatedBy=?,UpdatedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND Section='ai' AND Revision=?",
            raw,
            actor["UserId"],
            db.institution(settings),
            revision,
        )
        if c.rowcount != 1:
            raise HTTPException(409, "revision_conflict")
        c.execute(
            "INSERT crm_access.SettingHistory(InstitutionId,Section,Revision,Document,RecordedAt,ActorId) VALUES(?,'ai',?,?,SYSUTCDATETIME(),?)",
            db.institution(settings),
            revision + 1,
            raw,
            actor["UserId"],
        )
        result = {"revision": revision + 1, "document": document}
        db.record_operation(
            c, settings, actor["UserId"], operation, action, "ai", digest, result
        )
        db.audit(
            c,
            settings,
            actor["UserId"],
            action,
            "ai",
            revision=revision + 1,
            fields=sorted(changed),
        )
        return result
