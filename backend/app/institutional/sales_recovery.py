"""Explicit recovery of generation with no committed reply, never a resend."""
import json

from fastapi import HTTPException
from app.institutional import db
from app.institutional.auth import authorize
from app.institutional.models import Strict
from app.institutional.policy import request_authority
from app.institutional.whatsapp_gemini import ACTION, source
from app.modules.agents.domain import JsonUUID


class Retry(Strict):
    operation_id: JsonUUID
    generation_id: JsonUUID
    confirmed: bool
    acknowledge_consumption: bool


def latest(c, settings, conversation):
    return db.one(c, "SELECT TOP(1) OperationId,IntegrationId,Status,ResultCode,ResultMetadata,Attempts,"
                  "CASE WHEN LeaseUntil IS NULL OR LeaseUntil<=SYSUTCDATETIME() THEN 1 ELSE 0 END AS Expired "
                  "FROM crm_channels2.ProviderOperation WHERE InstitutionId=? AND Action=? "
                  "AND JSON_VALUE(ResultMetadata,'$.conversation')=? ORDER BY CreatedAt DESC,OperationId",
                  db.institution(settings), ACTION, conversation)


def review(c, settings, row):
    if not row or row["Status"] not in {"failed", "uncertain", "running"} or row["Status"] == "running" and not row["Expired"]:
        raise HTTPException(409, "sales_generation_not_recoverable")
    data = json.loads(row["ResultMetadata"])
    if data.get("reply") or data.get("generated_text") or row["Attempts"] >= 3:
        raise HTTPException(409, "sales_generation_not_recoverable")
    # A committed outgoing message (bot or human), newer incoming message,
    # changed control epoch, paused account or expired window rejects recovery.
    source(c, settings, row["IntegrationId"], data)
    return data


def summary(c, settings, conversation):
    row = latest(c, settings, conversation)
    if not row:
        return None
    can_retry = False
    try:
        review(c, settings, row)
        can_retry = True
    except HTTPException:
        pass
    return {"id": str(row["OperationId"]), "integration": str(row["IntegrationId"]),
            "status": row["Status"], "code": row["ResultCode"], "can_retry": can_retry}


def install(app, service, settings):
    @app.post("/api/institution/channels/{integration}/recover-generation")
    def recover(integration: str, body: Retry):
        if not body.confirmed or not body.acknowledge_consumption:
            raise HTTPException(422, "sales_generation_review_required")
        integration = db.uid(integration)
        with service.transaction(True) as c:
            authority = request_authority.get()
            actor = authorize(c, settings, authority, "settings.channels.write", recent=True)
            authorize(c, settings, authority, "inbox.write")
            checksum, prior = db.replay(c, settings, actor["UserId"], str(body.operation_id), "sales.recover-generation", integration, body.model_dump(mode="json"))
            if prior:
                return prior
            row = db.one(c, "SELECT OperationId,IntegrationId,Status,ResultCode,ResultMetadata,Attempts,"
                         "CASE WHEN LeaseUntil IS NULL OR LeaseUntil<=SYSUTCDATETIME() THEN 1 ELSE 0 END AS Expired "
                         "FROM crm_channels2.ProviderOperation WHERE InstitutionId=? AND IntegrationId=? AND OperationId=? AND Action=?",
                         db.institution(settings), integration, str(body.generation_id), ACTION)
            data = review(c, settings, row)
            data["operator_recoveries"] = [*data.get("operator_recoveries", []),
                {"operation": str(body.operation_id), "actor": actor["UserId"], "prior_status": row["Status"], "prior_code": row["ResultCode"], "prior_attempts": row["Attempts"]}]
            c.execute("UPDATE crm_channels2.ProviderOperation SET Status='pending',ResultCode='operator_generation_retry',ResultMetadata=?,"
                      "CompletedAt=NULL,LeaseUntil=NULL,LeaseId=NULL WHERE InstitutionId=? AND IntegrationId=? AND OperationId=? AND Status=?",
                      json.dumps(data), db.institution(settings), integration, str(body.generation_id), row["Status"])
            if c.rowcount != 1:
                raise HTTPException(409, "sales_generation_not_recoverable")
            result = {"saved": True, "status": "pending", "same_generation_id": str(body.generation_id), "message_resent": False}
            db.record_operation(c, settings, actor["UserId"], str(body.operation_id), "sales.recover-generation", integration, checksum, result)
            db.audit(c, settings, actor["UserId"], "sales.recover-generation", str(body.generation_id), reason="prior_status:" + row["Status"])
            return result
