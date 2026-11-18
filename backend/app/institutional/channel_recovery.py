"""Recovery preserves receipts and unknown effects; it never blindly resends."""

import hashlib
import json

from fastapi import HTTPException, Request
from pydantic import Field

from app.institutional.auth import authorize
from app.institutional.channel_events import normalize
from app.institutional.channel_ingress import body_owner, strict_json
from app.institutional.channel_operations import account
from app.institutional.crypto import canonical, unseal
from app.institutional.db import (
    institution,
    key,
    one,
    record_operation,
    replay,
    rows,
    uid,
    utc,
)
from app.institutional.models import Strict
from app.institutional.store import transaction


class Recovery(Strict):
    operation_id: str
    resource_id: str
    row_version: str = Field(pattern=r"^[0-9a-f]{16}$")
    action: str = Field(
        pattern=r"^(reprocess_event|retry_media|abandon_uncertain|retry_send|resume_queued)$"
    )


class Recoveries:
    def __init__(self, settings):
        self.settings = settings

    def read(self, authority, identity):
        with transaction(self.settings, anonymous=True) as c:
            actor = authorize(c, self.settings, authority, "settings.channels.read")
            from app.institutional.settings import setting

            can_read = "inbox.read" in json.loads(actor["Actions"]) and setting(
                c, self.settings, "modules"
            )["document"]["enabled"].get("inbox", False)
            item = account(c, self.settings, identity)
            queue = rows(
                c,
                (
                    "SELECT TOP(25) QueueId,State,LastErrorCode,Attempts,CreatedA"
                    "t,RowVersion,Payload FROM crm_channels2.SendJob WHERE "
                    "InstitutionId="
                    "? AND IntegrationId=? ORDER BY CreatedAt DESC,QueueId"
                ),
                institution(self.settings),
                item["IntegrationId"],
            )
            events = rows(
                c,
                (
                    "SELECT TOP(25) e.EventId,e.Status,e.LastErrorCode,e.RowVersi"
                    "on,e.Kind,e.CreatedAt,e.Payload FROM crm_channels2.WebhookEvent e WHERE e.InstitutionId=?"
                    " AND e.ApplicationId=? AND (e.IntegrationId=? OR (e.Integrat"
                    "ionId IS NULL AND e.RouteKind=? AND e.RouteExternalId=?)) AN"
                    "D e.Status IN('quarantined','failed') ORDER BY e.CreatedAt D"
                    "ESC,e.EventId"
                ),
                institution(self.settings),
                item["ApplicationId"],
                item["IntegrationId"],
                "configured_" + item["Channel"],
                item["ExternalAccountId"] or "",
            )
            operations = rows(
                c,
                (
                    "SELECT TOP(25) OperationId,Action,Status,ResultCode FROM crm"
                    "_channels2.ProviderOperation WHERE InstitutionId=? AND Integ"
                    "rationId=? AND Status IN('uncertain','running','failed') ORD"
                    "ER BY CreatedAt DESC,OperationId"
                ),
                institution(self.settings),
                item["IntegrationId"],
            )
            oauth = one(
                c,
                "SELECT TOP(1) s.Status,s.CreatedAt,p.ResultCode "
                "FROM crm_channels2.OAuthSession s LEFT JOIN crm_channels2.ProviderOperation p "
                "ON p.InstitutionId=s.InstitutionId AND p.IntegrationId=s.IntegrationId "
                "AND p.OperationId=s.OperationId AND p.Action='oauth_discovery' "
                "WHERE s.InstitutionId=? AND s.IntegrationId=? AND s.ActorRef=? "
                "ORDER BY s.CreatedAt DESC,s.OAuthSessionId",
                institution(self.settings), item["IntegrationId"], str(actor["UserId"]).lower(),
            )
            return {
                "oauth": {
                    "status": oauth["Status"],
                    "code": oauth["ResultCode"],
                    "started_at": utc(oauth["CreatedAt"]),
                } if oauth else None,
                "queue": [
                    {
                        "id": uid(str(v["QueueId"])),
                        "state": v["State"],
                        "code": v["LastErrorCode"],
                        "attempts": v["Attempts"],
                        "created_at": utc(v["CreatedAt"]),
                        "row_version": bytes(v["RowVersion"]).hex(),
                        "body_preview": json.loads(v["Payload"]).get("body", "")[:500]
                        if can_read
                        else None,
                    }
                    for v in queue
                ],
                "events": [
                    {
                        "id": uid(str(v["EventId"])),
                        "state": v["Status"],
                        "code": v["LastErrorCode"],
                        "row_version": bytes(v["RowVersion"]).hex(),
                        "kind": v["Kind"],
                        "created_at": utc(v["CreatedAt"]),
                        "body_preview": str(json.loads(v["Payload"]).get("text", ""))[:500]
                        if can_read else None,
                    }
                    for v in events
                ],
                "operations": [
                    {
                        "id": uid(str(v["OperationId"])),
                        "action": v["Action"],
                        "status": v["Status"],
                        "code": v["ResultCode"],
                    }
                    for v in operations
                ],
            }

    def apply(self, authority, identity, body):
        with transaction(self.settings, True, anonymous=True) as c:
            actor = authorize(
                c, self.settings, authority, "settings.channels.write", recent=True
            )
            item = account(c, self.settings, identity)
            resource = uid(body.resource_id)
            digest, prior = replay(
                c,
                self.settings,
                actor["UserId"],
                body.operation_id,
                "channels.recovery",
                identity,
                body.model_dump(),
            )
            if prior:
                return prior
            queue_id = None
            if body.action in {"retry_send", "resume_queued"}:
                from app.institutional.channel_retry import recover_send

                queue_id = recover_send(c, self.settings, authority, actor, item, body)
            elif body.action == "reprocess_event":
                value = one(
                    c,
                    (
                        "SELECT e.*,r.BodyNonce,r.BodyCiphertext,r.Digest,r.Authentic"
                        "ation,p.Provider FROM crm_channels2.WebhookEvent e JOIN crm_"
                        "channels2.WebhookReceipt r ON r.InstitutionId=e.InstitutionI"
                        "d AND r.ReceiptId=e.ReceiptId AND r.EndpointId=e.EndpointId "
                        "AND r.ApplicationId=e.ApplicationId JOIN crm_channels2.Webho"
                        "okEndpoint p ON p.InstitutionId=e.InstitutionId AND p.Endpoi"
                        "ntId=e.EndpointId WHERE e.InstitutionId=? AND e.EventId=? AN"
                        "D e.ApplicationId=? AND r.Authentication='verified' AND p.Is"
                        "Active=1"
                    ),
                    institution(self.settings),
                    resource,
                    item["ApplicationId"],
                )
                if (
                    not value
                    or value["Status"] not in {"quarantined", "failed"}
                    or bytes(value["RowVersion"]).hex() != body.row_version
                    or not value["BodyCiphertext"]
                ):
                    raise HTTPException(409, "event_recovery_unavailable")
                if (
                    item["RequestedStatus"] != "connected"
                    or value["IntegrationId"]
                    and str(value["IntegrationId"]).lower() != uid(identity)
                ):
                    raise HTTPException(409, "event_account_mismatch")
                raw = unseal(
                    key(self.settings),
                    body_owner(self.settings, value["ReceiptId"], value["EndpointId"]),
                    value["BodyNonce"],
                    value["BodyCiphertext"],
                )
                if hashlib.sha256(raw.encode()).digest() != bytes(value["Digest"]):
                    raise HTTPException(409, "receipt_integrity_rejected")
                document = strict_json(raw)
                stored_effect = json.loads(value["Payload"])
                version = stored_effect.get("normalizer_version")
                effects = normalize(
                    value["Provider"], document,
                    whatsapp_names=version in (2, 3),
                    whatsapp_identifiers=version == 3,
                )
                if (
                    not value["SubeventPath"].isascii()
                    or not value["SubeventPath"].isdigit()
                    or len(value["SubeventPath"]) > 4
                    or int(value["SubeventPath"]) >= len(effects)
                ):
                    raise HTTPException(409, "event_source_index_invalid")
                index = int(value["SubeventPath"])
                effect = effects[index]
                if not effect.get("valid_source_ids", False):
                    raise HTTPException(409, "event_source_identity_invalid")
                if (
                    canonical(effect) != canonical(stored_effect)
                    or effect["route"] != item["ExternalAccountId"]
                    or effect["channel"] != item["Channel"]
                ):
                    raise HTTPException(409, "event_route_mismatch")
                route = c.execute(
                    (
                        "SELECT 1 FROM crm_channels2.EndpointIntegration WHERE Instit"
                        "utionId=? AND ApplicationId=? AND EndpointId=? AND Integrati"
                        "onId=? AND RouteKind=? AND ExternalId=? AND IsActive=1"
                    ),
                    institution(self.settings),
                    item["ApplicationId"],
                    value["EndpointId"],
                    item["IntegrationId"],
                    value["RouteKind"],
                    value["RouteExternalId"],
                ).fetchone()
                if not route:
                    raise HTTPException(409, "event_route_not_configured")
                if (
                    effect["channel"] == "whatsapp"
                    and effect["kind"] == "message"
                    and not effect["author"]
                    and value["LastErrorCode"] == "provider_author_missing"
                ):
                    revised = normalize(value["Provider"], document)[index]
                    if revised.get("whatsapp_user_id") and revised["author"] == revised["whatsapp_user_id"]:
                        effect = revised
                duplicate = c.execute(
                    (
                        "SELECT 1 FROM crm_channels2.WebhookEvent WHERE InstitutionId"
                        "=? AND IntegrationId=? AND DedupeKey=? AND EventId<>?"
                    ),
                    institution(self.settings),
                    item["IntegrationId"],
                    value["DedupeKey"],
                    resource,
                ).fetchone()
                if duplicate:
                    raise HTTPException(409, "event_already_processed")
                c.execute(
                    (
                        "UPDATE crm_channels2.WebhookEvent SET IntegrationId=?,Status"
                        "='queued',LastErrorCode=NULL,Payload=? WHERE InstitutionId=? AND Event"
                        "Id=? AND RowVersion=?"
                    ),
                    item["IntegrationId"],
                    json.dumps(effect, ensure_ascii=False),
                    institution(self.settings),
                    resource,
                    bytes.fromhex(body.row_version),
                )
            elif body.action == "retry_media":
                c.execute(
                    (
                        "UPDATE crm_channels4.MediaAsset SET State='pending',LastErro"
                        "rCode=NULL,UpdatedAt=SYSUTCDATETIME() WHERE InstitutionId=? "
                        "AND IntegrationId=? AND MediaId=? AND SourceKind='provider' "
                        "AND State='failed' AND RowVersion=?"
                    ),
                    institution(self.settings),
                    item["IntegrationId"],
                    resource,
                    bytes.fromhex(body.row_version),
                )
                if c.rowcount != 1:
                    raise HTTPException(409, "media_recovery_unavailable")
            else:
                value = one(
                    c,
                    (
                        "SELECT * FROM crm_channels2.SendJob WHERE InstitutionId=? AN"
                        "D IntegrationId=? AND QueueId=?"
                    ),
                    institution(self.settings),
                    item["IntegrationId"],
                    resource,
                )
                if (
                    not value
                    or value["State"] != "uncertain"
                    or bytes(value["RowVersion"]).hex() != body.row_version
                ):
                    raise HTTPException(409, "unknown_effect_required")
                # Historical attempts and a possibly billed quota remain recorded.
                c.execute(
                    (
                        "UPDATE crm_channels2.SendJob SET State='cancelled',LastError"
                        "Code='operator_abandoned_unknown_effect',CompletedAt=SYSUTCD"
                        "ATETIME() WHERE InstitutionId=? AND QueueId=?"
                    ),
                    institution(self.settings),
                    resource,
                )
                c.execute(
                    (
                        "UPDATE crm_channels2.ProviderOperation SET Status='abandoned"
                        "',ResultCode='operator_abandoned_unknown_effect',CompletedAt"
                        "=SYSUTCDATETIME() WHERE InstitutionId=? AND OperationId=? AN"
                        "D Status='uncertain'"
                    ),
                    institution(self.settings),
                    value["OperationId"],
                )
            result = {"saved": True, "provider_resend": False}
            if queue_id:
                result["queue_id"] = queue_id
            record_operation(
                c,
                self.settings,
                actor["UserId"],
                body.operation_id,
                "channels.recovery",
                identity,
                digest,
                result,
            )
            return result


def maintenance(settings):
    with transaction(settings, True, anonymous=True) as c:
        inst = institution(settings)
        c.execute(
            (
                "UPDATE crm_channels2.ProviderOperation SET Status='uncertain"
                "',ResultCode='operation_lease_expired',LeaseId=NULL,LeaseUnt"
                "il=NULL WHERE InstitutionId=? AND Status='running' AND Lease"
                "Until<SYSUTCDATETIME() AND Action NOT IN('chat','comment_rep"
                "ly')"
            ),
            inst,
        )
        c.execute(
            (
                "UPDATE crm_channels2.OAuthSession SET Status='uncertain',Cla"
                "imId=NULL,ClaimUntil=NULL WHERE InstitutionId=? AND Status='"
                "exchanging' AND ClaimUntil<SYSUTCDATETIME()"
            ),
            inst,
        )
        c.execute(
            (
                "UPDATE crm_channels2.OAuthSession SET Status='expired',Compl"
                "etedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND Status IN("
                "'pending','assets_ready') AND ExpiresAt<=SYSUTCDATETIME()"
            ),
            inst,
        )
        c.execute(
            (
                "UPDATE crm_channels4.MediaAsset SET State='failed',LastError"
                "Code='media_processing_interrupted',UpdatedAt=SYSUTCDATETIME"
                "() WHERE InstitutionId=? AND SourceKind='provider' AND State"
                "='processing' AND UpdatedAt<DATEADD(minute,-5,SYSUTCDATETIME"
                "())"
            ),
            inst,
        )
        c.execute(
            (
                "UPDATE TOP(20) crm_channels2.WebhookReceipt SET BodyKeyVersi"
                "on=NULL,BodyNonce=NULL,BodyCiphertext=NULL,BodyPurgedAt=SYSU"
                "TCDATETIME() WHERE InstitutionId=? AND ExpiresAt<=SYSUTCDATE"
                "TIME() AND Status IN('processed','quarantined','failed') AND"
                " LeaseId IS NULL AND LeaseUntil IS NULL AND BodyPurgedAt IS "
                "NULL"
            ),
            inst,
        )


def install(app, settings):
    service = Recoveries(settings)

    @app.get("/api/institution/channels/{identity}/history")
    def history(request: Request, identity: str):
        return service.read(request.state.authority, identity)

    @app.post("/api/institution/channels/{identity}/recover")
    def recover(request: Request, identity: str, body: Recovery):
        return service.apply(request.state.authority, identity, body)
