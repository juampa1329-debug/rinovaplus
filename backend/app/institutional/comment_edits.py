"""Explicit edits of the connected Facebook Page's own published comments.

The submitted SendJob remains immutable. A separate edit history records what Meta
confirmed; an uncertain POST is never retried by a worker or by request replay.
"""

import hashlib
import json
import re
from datetime import datetime, timezone

from fastapi import HTTPException, Request
from pydantic import Field

from app.institutional.auth import authorize
from app.institutional.channel_operations import account, configuration
from app.institutional.channel_provider import provider_account
from app.institutional.comment_threads import is_account_comment
from app.institutional.db import bound_hash, institution, one, uid
from app.institutional.models import Strict
from app.institutional.store import transaction
from app.modules.channels import providers


class Edit(Strict):
    operation_id: str
    source: str = Field(pattern=r"^(meta|crm)$")
    revision: str = Field(pattern=r"^[0-9a-f]{64}$")
    body: str = Field(min_length=1, max_length=4000)


class Review(Strict):
    operation_id: str
    source: str = Field(pattern=r"^(meta|crm)$")


def revision(body):
    return hashlib.sha256(body.encode()).hexdigest()


def presentation(value, source):
    payload = json.loads(value.get("Payload") or "{}")
    state = payload.get("_crm", {})
    text = value["Body"] if source == "meta" else state.get("edited_body", payload.get("body", ""))
    return text, state.get("edits", [])


def edit_info(value, source, channel, state):
    text, history = presentation(value, source)
    return {
        "supported": channel == "facebook" and state not in {"deleted", "unavailable", "queued", "sending", "uncertain", "failed", "cancelled"} and bool(value.get("ExternalId")),
        "source": source,
        "revision": revision(text),
        "history": [{"previous": h["previous"], "body": h["body"], "at": h["at"]} for h in history if isinstance(h, dict) and all(k in h for k in ("previous", "body", "at"))][-20:],
    }


def load(c, settings, identity, source):
    table, key = ("SocialComment", "CommentId") if source == "meta" else ("SendJob", "QueueId")
    row = one(c, f"SELECT * FROM crm_channels2.{table} WHERE InstitutionId=? AND {key}=?", institution(settings), uid(identity))
    if not row:
        raise HTTPException(404, "comment_not_found")
    item = account(c, settings, str(row["IntegrationId"]))
    if item["Channel"] != "facebook":
        raise HTTPException(409, "comment_edit_unsupported_by_provider")
    payload = json.loads(row["Payload"])
    if source == "meta":
        own_job = one(c, "SELECT TOP(1) * FROM crm_channels2.SendJob WHERE InstitutionId=? AND IntegrationId=? AND ExternalId=? AND Kind='comment_reply' AND CommentId IS NOT NULL", institution(settings), item["IntegrationId"], row["ExternalId"])
        if not is_account_comment(row, item) and not own_job:
            raise HTTPException(403, "comment_edit_own_only")
        if payload.get("_crm", {}).get("state") in {"deleted", "unavailable"}:
            raise HTTPException(409, "comment_source_unavailable")
    elif row["Kind"] != "comment_reply" or not row.get("CommentId") or row["State"] not in {"accepted", "sent", "delivered", "read"}:
        raise HTTPException(409, "comment_edit_published_required")
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,200}", str(row.get("ExternalId") or "")):
        raise HTTPException(409, "comment_edit_published_required")
    return row, item


def edit_provider(adapter, target, previous, desired):
    """Read ownership and current text before writing, then verify exact read-back."""
    posted = accepted = False
    try:
        current = providers.request(adapter, "GET", target, params={"fields": "id,message,from"})
        if str(current.get("id")) != target or str((current.get("from") or {}).get("id")) != str(adapter["external_account_id"]):
            raise providers.ProviderFailure("comment_edit_own_only")
        if current.get("message") != previous:
            raise providers.ProviderFailure("comment_edit_source_changed")
        posted = True
        result = providers.request(adapter, "POST", target, {"message": desired})
        if result.get("success") is not True:
            raise providers.ProviderFailure("comment_edit_not_confirmed", uncertain=True)
        accepted = True
        current = providers.request(adapter, "GET", target, params={"fields": "id,message"})
        if str(current.get("id")) != target or current.get("message") != desired:
            raise providers.ProviderFailure("comment_edit_not_confirmed", uncertain=True)
    except providers.ProviderFailure as error:
        # A read failure cannot have modified the publication.
        raise providers.ProviderFailure(error.code, uncertain=accepted or posted and error.uncertain) from None
    except Exception:
        raise providers.ProviderFailure("comment_edit_result_unknown", uncertain=posted) from None


def write_projection(c, settings, item, target, desired, edit=None):
    """Keep the sent request immutable, and update only its display projection."""
    values = [
        ("SocialComment", "CommentId", one(c, "SELECT * FROM crm_channels2.SocialComment WHERE InstitutionId=? AND IntegrationId=? AND ExternalId=?", institution(settings), item["IntegrationId"], target)),
        ("SendJob", "QueueId", one(c, "SELECT TOP(1) * FROM crm_channels2.SendJob WHERE InstitutionId=? AND IntegrationId=? AND ExternalId=? AND Kind='comment_reply' AND CommentId IS NOT NULL", institution(settings), item["IntegrationId"], target)),
    ]
    for table, key, value in values:
        if not value:
            continue
        payload = json.loads(value["Payload"])
        state = payload.setdefault("_crm", {})
        if edit:
            state["edits"] = (state.get("edits", []) + [edit])[-20:]
        if table == "SendJob":
            state["edited_body"] = desired
        c.execute(f"UPDATE crm_channels2.{table} SET Payload=?" + (",Body=?" if table == "SocialComment" else "") + f" WHERE InstitutionId=? AND {key}=?", json.dumps(payload, ensure_ascii=False), *([desired] if table == "SocialComment" else []), institution(settings), value[key])
    c.execute("UPDATE crm_workspace.State SET Revision=Revision+1 WHERE StateId=1")


class Edits:
    def __init__(self, settings, transport=None):
        self.settings = settings
        self.transport = transport or edit_provider

    def status(self, authority, identity, source):
        if source not in {"meta", "crm"}:
            raise HTTPException(422, "invalid_source")
        with transaction(self.settings, anonymous=True) as c:
            authorize(c, self.settings, authority, "inbox.read")
            row, item = load(c, self.settings, identity, source)
            pending = one(c, "SELECT TOP(1) * FROM crm_channels2.ProviderOperation WHERE InstitutionId=? AND IntegrationId=? AND Action='comment_edit' AND (Status IN ('running','uncertain') OR (Status='failed' AND ResultCode='comment_edit_source_changed')) AND JSON_VALUE(ResultMetadata,'$.external_id')=? ORDER BY CreatedAt DESC", institution(self.settings), item["IntegrationId"], row["ExternalId"])
            return {"pending": {"operation_id": str(pending["OperationId"]), "status": pending["Status"], "code": pending["ResultCode"]} if pending else None}

    def reconcile(self, authority, identity, body):
        operation = uid(body.operation_id)
        with transaction(self.settings, anonymous=True) as c:
            actor = authorize(c, self.settings, authority, "inbox.write")
            row, item = load(c, self.settings, identity, body.source)
            intent = one(c, "SELECT *,CASE WHEN LeaseUntil>SYSUTCDATETIME() THEN 0 ELSE 1 END AS Expired FROM crm_channels2.ProviderOperation WHERE InstitutionId=? AND OperationId=?", institution(self.settings), operation)
            metadata = json.loads(intent["ResultMetadata"]) if intent else {}
            if not intent or intent["Action"] != "comment_edit" or str(intent["IntegrationId"]) != str(item["IntegrationId"]) or metadata.get("external_id") != row["ExternalId"]:
                raise HTTPException(404, "operation_not_found")
            if intent["Status"] not in {"running", "uncertain"} and not (intent["Status"] == "failed" and intent["ResultCode"] == "comment_edit_source_changed"):
                return {"status": intent["Status"], "code": intent["ResultCode"]}
            if intent["Status"] == "running" and not intent["Expired"]:
                raise HTTPException(409, "comment_edit_review_required")
            adapter, _ = provider_account(c, self.settings, item)
        try:
            current = providers.request(adapter, "GET", row["ExternalId"], params={"fields": "id,message,from"})
        except providers.ProviderFailure:
            raise HTTPException(409, "comment_preview_unavailable") from None
        observed = current.get("message")
        if str(current.get("id")) != row["ExternalId"] or str((current.get("from") or {}).get("id")) != str(item["ExternalAccountId"]) or not isinstance(observed, str) or len(observed) > 4000:
            raise HTTPException(409, "comment_edit_own_only")
        with transaction(self.settings, True, anonymous=True) as c:
            authorize(c, self.settings, authority, "inbox.write")
            fresh, fresh_item = load(c, self.settings, identity, body.source)
            if bytes(fresh["RowVersion"]) != bytes(row["RowVersion"]) or bytes(fresh_item["RowVersion"]) != bytes(item["RowVersion"]):
                raise HTTPException(409, "revision_conflict")
            now = datetime.now(timezone.utc).isoformat()
            before, history = presentation(fresh, body.source)
            if observed == metadata["body"] and not any(h.get("operation_id") == operation for h in history):
                before = metadata["previous"]
            edit = {"previous": before, "body": observed, "at": now, "actor": str(actor["UserId"]), "operation_id": operation, "reason": "provider_reconciliation"} if before != observed else None
            write_projection(c, self.settings, item, row["ExternalId"], observed, edit)
            confirmed = observed == metadata["body"]
            status, code = ("confirmed", None) if confirmed else ("failed", "comment_edit_not_applied" if observed == metadata["previous"] else "comment_edit_reconciled")
            metadata.update(observed_at=now, observed_body=observed)
            c.execute("UPDATE crm_channels2.ProviderOperation SET Status=?,ResultCode=?,ResultMetadata=?,CompletedAt=SYSUTCDATETIME(),LeaseUntil=NULL WHERE InstitutionId=? AND OperationId=? AND (Status IN ('running','uncertain') OR (Status='failed' AND ResultCode='comment_edit_source_changed'))", status, code, json.dumps(metadata, ensure_ascii=False), institution(self.settings), operation)
        return {"status": status, "code": code, "body": observed}

    def perform(self, authority, identity, body):
        desired = body.body.strip()
        if not desired:
            raise HTTPException(422, "comment_edit_text_required")
        operation = uid(body.operation_id)
        digest = bound_hash(self.settings, {"id": uid(identity), "source": body.source, "revision": body.revision, "body": desired}, "comment-edit")
        with transaction(self.settings, True, anonymous=True) as c:
            actor = authorize(c, self.settings, authority, "inbox.write")
            existing = one(c, "SELECT * FROM crm_channels2.ProviderOperation WHERE InstitutionId=? AND OperationId=?", institution(self.settings), operation)
            if existing:
                if existing["Action"] != "comment_edit" or existing["ActorRef"] != actor["UserId"] or bytes(existing["RequestDigest"]) != digest:
                    raise HTTPException(409, "operation_conflict")
                return {"status": existing["Status"], "code": existing["ResultCode"]}
            row, item = load(c, self.settings, identity, body.source)
            previous, _ = presentation(row, body.source)
            if revision(previous) != body.revision:
                raise HTTPException(409, "revision_conflict")
            if desired == previous:
                raise HTTPException(422, "comment_edit_unchanged")
            config = configuration(c, self.settings)
            if not config["ModuleEnabled"] or not config["OutboundEnabled"] or item["RequestedStatus"] != "connected" or item["VerifiedStatus"] != "verified":
                raise HTTPException(409, "verified_outbound_account_required")
            # The institutional write transaction serializes competing edit intents.
            busy = one(c, "SELECT TOP(1) * FROM crm_channels2.ProviderOperation WHERE InstitutionId=? AND IntegrationId=? AND Action='comment_edit' AND Status IN ('running','uncertain') AND JSON_VALUE(ResultMetadata,'$.external_id')=?", institution(self.settings), item["IntegrationId"], row["ExternalId"])
            if busy:
                raise HTTPException(409, "comment_edit_review_required")
            adapter, _ = provider_account(c, self.settings, item)
            metadata = {"external_id": row["ExternalId"], "previous": previous, "body": desired, "source": body.source, "id": uid(identity)}
            effect = bound_hash(self.settings, {"operation": operation, "request": digest.hex()}, "comment-edit-effect")
            c.execute("INSERT crm_channels2.ProviderOperation(InstitutionId,OperationId,ApplicationId,IntegrationId,ActorRef,Action,RequestDigest,Status,ResultMetadata,EffectKey,CreatedAt,Attempts,LeaseUntil) VALUES(?,?,?,?,?,'comment_edit',?,'running',?,?,SYSUTCDATETIME(),1,DATEADD(second,90,SYSUTCDATETIME()))", institution(self.settings), operation, item["ApplicationId"], item["IntegrationId"], actor["UserId"], digest, json.dumps(metadata, ensure_ascii=False), effect)
        try:
            self.transport({**adapter, "external_account_id": str(item["ExternalAccountId"])}, row["ExternalId"], previous, desired)
            status, code = "confirmed", None
        except providers.ProviderFailure as error:
            status, code = ("uncertain" if error.uncertain else "failed"), error.code
        except Exception:
            status, code = "uncertain", "comment_edit_result_unknown"
        with transaction(self.settings, True, anonymous=True) as c:
            try:
                authorize(c, self.settings, authority, "inbox.write")
                allowed = True
            except HTTPException:
                allowed = False
            current, current_item = load(c, self.settings, identity, body.source)
            intent = one(c, "SELECT * FROM crm_channels2.ProviderOperation WHERE InstitutionId=? AND OperationId=?", institution(self.settings), operation)
            if not allowed or not intent or intent["Status"] != "running" or bytes(current_item["RowVersion"]) != bytes(item["RowVersion"]):
                status, code = "uncertain", "comment_or_authority_changed"
            text, _ = presentation(current, body.source)
            if text not in {previous, desired}:
                status, code = "uncertain", "comment_edit_source_changed"
            if status == "confirmed":
                edit = {"previous": previous, "body": desired, "at": datetime.now(timezone.utc).isoformat(), "actor": str(actor["UserId"]), "operation_id": operation}
                write_projection(c, self.settings, item, row["ExternalId"], desired, edit)
            c.execute("UPDATE crm_channels2.ProviderOperation SET Status=?,ResultCode=?,CompletedAt=SYSUTCDATETIME(),LeaseUntil=NULL WHERE InstitutionId=? AND OperationId=? AND Status='running'", status, code, institution(self.settings), operation)
        return {"status": status, "code": code}


def install(app, settings):
    service = Edits(settings)

    @app.post("/api/institution/comments/{identity}/edit")
    def edit(request: Request, identity: str, body: Edit):
        return service.perform(request.state.authority, identity, body)

    @app.get("/api/institution/comments/{identity}/edit-status")
    def status(request: Request, identity: str, source: str):
        return service.status(request.state.authority, identity, source)

    @app.post("/api/institution/comments/{identity}/edit/reconcile")
    def reconcile(request: Request, identity: str, body: Review):
        return service.reconcile(request.state.authority, identity, body)
