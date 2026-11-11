"""Short-lived, queue-bound delivery URL for Instagram Login media retrieval."""

import base64
import hmac
import time
from urllib.parse import urlencode

from fastapi import HTTPException, Query
from fastapi.responses import FileResponse

from app.institutional.channel_media import file_for
from app.institutional.channel_operations import configuration
from app.institutional.crypto import canonical
from app.institutional.db import institution, one, uid
from app.institutional.store import transaction


def signature(s, media, queue, expires):
    return hmac.digest(
        base64.b64decode(s.review["secrets_key"]),
        canonical(
            dict(
                domain="P8-Instagram-media-v1",
                institution=institution(s),
                media=uid(str(media)),
                queue=uid(str(queue)),
                expires=expires,
            )
        ),
        "sha256",
    ).hex()


def origin(c, s):
    base = configuration(c, s)["PublicBaseUrl"]
    if not base:
        raise HTTPException(409, "campaign_public_HTTPS_media_origin_required")
    return base


def delivery_url(c, s, job, media):
    expires = int(time.time()) + 600
    return (
        origin(c, s)
        + "/hooks/campaign-media/"
        + uid(str(media))
        + "/"
        + uid(str(job["QueueId"]))
        + "?"
        + urlencode(
            dict(expires=expires, sig=signature(s, media, job["QueueId"], expires))
        )
    )


def install(app, settings):
    @app.get("/hooks/campaign-media/{media}/{queue}")
    def deliver(
        media: str,
        queue: str,
        expires: int = Query(ge=0),
        sig: str = Query(pattern="^[0-9a-f]{64}$"),
    ):
        media, queue = uid(media), uid(queue)
        clock = int(time.time())
        if (
            expires < clock
            or expires > clock + 600
            or not hmac.compare_digest(sig, signature(settings, media, queue, expires))
        ):
            raise HTTPException(404, "campaign_delivery_unavailable")
        with transaction(settings, anonymous=True) as c:
            job = one(
                c,
                "SELECT q.MessageId,q.IntegrationId,q.State,r.EnrollmentId,r.State AS RunState,f.State AS FlowState,i.VerifiedStatus,i.RequestedStatus FROM crm_channels2.SendJob q JOIN crm_campaign8.Event e ON e.InstitutionId=q.InstitutionId AND e.Kind='native_chat' AND JSON_VALUE(e.Document,'$.queue_id')=CONVERT(varchar(36),q.QueueId) JOIN crm_campaign8.Enrollment r ON r.InstitutionId=e.InstitutionId AND r.EnrollmentId=e.EnrollmentId JOIN crm_campaign8.Record f ON f.InstitutionId=r.InstitutionId AND f.RecordId=r.FlowId JOIN crm_channels2.Integration i ON i.InstitutionId=q.InstitutionId AND i.IntegrationId=q.IntegrationId WHERE q.InstitutionId=? AND q.QueueId=?",
                institution(settings),
                queue,
            )
            if (
                not job
                or job["State"]
                not in {"sending", "accepted", "sent", "delivered", "read"}
                or job["RunState"] not in {"queued", "waiting", "completed"}
                or job["FlowState"] != "active"
                or job["VerifiedStatus"] != "verified"
                or job["RequestedStatus"] != "connected"
            ):
                raise HTTPException(404, "campaign_delivery_unavailable")
            from app.institutional.campaign_runtime import guard

            run = one(
                c,
                "SELECT * FROM crm_campaign8.Enrollment WHERE InstitutionId=? AND EnrollmentId=?",
                institution(settings),
                job["EnrollmentId"],
            )
            try:
                guard(c, settings, run, ignore_state=True)
            except HTTPException:
                raise HTTPException(404, "campaign_delivery_unavailable") from None
            value, info = file_for(c, settings, media)
            if str(value["MessageId"]) != str(job["MessageId"]) or str(
                value["IntegrationId"]
            ) != str(job["IntegrationId"]):
                raise HTTPException(404, "campaign_delivery_unavailable")
        return FileResponse(
            info["path"],
            media_type=info["mime"],
            headers={
                "Cache-Control": "no-store",
                "Content-Security-Policy": "default-src 'none'; sandbox",
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer",
            },
        )
