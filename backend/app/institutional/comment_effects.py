"""Comment effects share C10 intent history; no implicit retry of external mutations."""

import json
import re
from datetime import datetime, timezone

from fastapi import HTTPException, Request
from pydantic import Field

from app.institutional.auth import authorize
from app.institutional.channel_operations import account, capabilities, configuration
from app.institutional.channel_provider import provider_account
from app.institutional.db import bound_hash, institution, one, uid
from app.institutional.models import Strict
from app.institutional.store import transaction
from app.modules.channels import providers


class Effect(Strict):
    operation_id: str
    row_version: str = Field(pattern=r"^[0-9a-f]{16}$")


def call_provider(adapter, action, comment):
    target = comment["ExternalId"]
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,200}", target):
        raise providers.ProviderFailure("comment_target_invalid")
    if action == "reconcile":
        try:
            value = providers.request(adapter, "GET", target, params={
                "fields": "id,text" if adapter["channel"] == "instagram" else "id,message",
            })
        except providers.ProviderFailure as error:
            # Meta does not distinguish an inaccessible object from a deleted one
            # reliably. Preserve the record and never fabricate a deletion event.
            if error.code != "provider_permission_or_request_rejected":
                raise
            return {"source": {"status": "unavailable", "reason": error.code}}
        if str(value.get("id")) != target:
            raise providers.ProviderFailure("comment_target_mismatch")
        text = value.get("text" if adapter["channel"] == "instagram" else "message")
        if not isinstance(text, str):
            raise providers.ProviderFailure("comment_source_invalid")
        return {"source": {"status": "available"}, "body": text[:4000]}
    if action in {"like", "unlike"}:
        value = providers.request(
            adapter, "POST" if action == "like" else "DELETE", target + "/likes", {}
        )
        if value.get("success") is not True:
            raise providers.ProviderFailure(
                "comment_reaction_not_confirmed", uncertain=True
            )
        return {"liked": action == "like"}
    raw = json.loads(comment["Payload"]).get("provider", {})
    post = str(raw.get("post_id") or (raw.get("media") or {}).get("id") or "")
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,200}", post):
        raise providers.ProviderFailure("comment_post_reference_missing")
    fields = (
        "id,caption,permalink,media_type,media_url,thumbnail_url,"
        "children{id,media_type,media_url,thumbnail_url}"
        if adapter["channel"] == "instagram"
        else "id,message,permalink_url,created_time,full_picture,"
        "attachments{media,type,url,subattachments{media,type,url}}"
    )
    value = providers.request(adapter, "GET", post, params={"fields": fields})
    if str(value.get("id")) != post:
        raise providers.ProviderFailure("comment_post_mismatch")
    media = []
    if adapter["channel"] == "instagram":
        children = (value.get("children") or {}).get("data") or [value]
        for child in children[:10]:
            source = child.get("media_url")
            if source:
                media.append({
                    "type": "video" if child.get("media_type") == "VIDEO" else "image",
                    "url": str(source)[:8192],
                    "poster": str(child.get("thumbnail_url") or "")[:8192],
                })
    else:
        for attachment in (value.get("attachments") or {}).get("data", [])[:10]:
            children = (attachment.get("subattachments") or {}).get("data") or [attachment]
            for child in children[:10]:
                content = child.get("media") or {}
                image = (content.get("image") or {}).get("src")
                source = content.get("source") or image
                if source and len(media) < 10:
                    media.append({
                        "type": "video" if content.get("source") else "image",
                        "url": str(source)[:8192],
                        "poster": str(image or "")[:8192],
                    })
        if not media and value.get("full_picture"):
            media.append({"type": "image", "url": str(value["full_picture"])[:8192]})
    return {
        "preview": {
            "id": post,
            "caption": str(value.get("caption") or value.get("message") or "")[:4000],
            "permalink": str(
                value.get("permalink") or value.get("permalink_url") or ""
            )[:2048],
            "media": media,
        }
    }


class Effects:
    def __init__(self, settings, transport=None):
        self.settings = settings
        self.transport = transport or call_provider

    def preview(self, authority, identity):
        with transaction(self.settings, anonymous=True) as c:
            authorize(c, self.settings, authority, "inbox.read")
            if not configuration(c, self.settings)["ModuleEnabled"]:
                raise HTTPException(403, "module_disabled")
            comment = one(
                c,
                "SELECT * FROM crm_channels2.SocialComment WHERE InstitutionId=? AND CommentId=?",
                institution(self.settings), uid(identity),
            )
            if not comment:
                raise HTTPException(404, "comment_not_found")
            item = account(c, self.settings, str(comment["IntegrationId"]))
            if item["Channel"] not in {"facebook", "instagram"}:
                raise HTTPException(409, "comment_effect_unsupported_by_provider")
            adapter, _ = provider_account(c, self.settings, item)
        try:
            return self.transport(adapter, "preview", comment)["preview"]
        except (providers.ProviderFailure, KeyError):
            raise HTTPException(409, "comment_preview_unavailable") from None

    def perform(self, authority, identity, action, body):
        if action not in {"like", "unlike", "preview", "reconcile"}:
            raise HTTPException(404, "comment_effect_not_found")
        operation = uid(body.operation_id)
        digest = bound_hash(
            self.settings,
            {
                "comment": uid(identity),
                "action": action,
                "row_version": body.row_version,
            },
            "comment-effect",
        )
        with transaction(self.settings, True, anonymous=True) as c:
            actor = authorize(c, self.settings, authority, "inbox.write")
            if not configuration(c, self.settings)["ModuleEnabled"]:
                raise HTTPException(403, "module_disabled")
            comment = one(
                c,
                (
                    "SELECT * FROM crm_channels2.SocialComment WHER"
                    "E InstitutionId=? AND CommentId=?"
                ),
                institution(self.settings),
                uid(identity),
            )
            if not comment:
                raise HTTPException(404, "comment_not_found")
            item = account(c, self.settings, str(comment["IntegrationId"]))
            existing = one(
                c,
                (
                    "SELECT * FROM crm_channels2.ProviderOperation "
                    "WHERE InstitutionId=? AND OperationId=?"
                ),
                institution(self.settings),
                operation,
            )
            if existing:
                if (
                    bytes(existing["RequestDigest"]) != digest
                    or existing["ActorRef"] != actor["UserId"]
                    or existing["Action"] != "comment_" + action
                ):
                    raise HTTPException(409, "operation_conflict")
                return {
                    "status": existing["Status"],
                    "code": existing["ResultCode"],
                    "result": json.loads(existing["ResultMetadata"]),
                }
            if bytes(comment["RowVersion"]).hex() != body.row_version:
                raise HTTPException(409, "revision_conflict")
            if json.loads(comment["Payload"]).get("_crm", {}).get("state") == "deleted":
                raise HTTPException(409, "comment_deleted")
            if action != "reconcile" and json.loads(comment["Payload"]).get("_crm", {}).get("state") == "unavailable":
                raise HTTPException(409, "comment_source_unavailable")
            if (
                item["Channel"] == "tiktok"
                or action in {"like", "unlike"}
                and not capabilities(item)["comment_like"]
            ):
                raise HTTPException(409, "comment_effect_unsupported_by_provider")
            if action not in {"preview", "reconcile"} and (
                not configuration(c, self.settings)["OutboundEnabled"]
                or item["RequestedStatus"] != "connected"
                or item["VerifiedStatus"] != "verified"
            ):
                raise HTTPException(409, "verified_outbound_account_required")
            adapter, secret = provider_account(c, self.settings, item)
            c.execute(
                (
                    "INSERT crm_channels2.ProviderOperation(Institu"
                    "tionId,OperationId,ApplicationId,IntegrationId"
                    ",ActorRef,Action,RequestDigest,Status,ResultMe"
                    "tadata,EffectKey,CreatedAt,Attempts,LeaseUntil"
                    ") VALUES(?,?,?,?,?,?,?,'running','{}',?,SYSUTC"
                    "DATETIME(),1,DATEADD(second,60,SYSUTCDATETIME("
                    ")))"
                ),
                institution(self.settings),
                operation,
                item["ApplicationId"],
                item["IntegrationId"],
                actor["UserId"],
                "comment_" + action,
                digest,
                digest,
            )
        try:
            result = self.transport(adapter, action, comment)
            safe = (
                {"liked": bool(result["liked"])}
                if action in {"like", "unlike"} and type(result.get("liked")) is bool
                else {"preview": result["preview"]}
                if action == "preview" and isinstance(result.get("preview"), dict)
                else result
                if action == "reconcile" and valid_source_result(result)
                else None
            )
            if safe is None:
                raise providers.ProviderFailure(
                    "comment_effect_not_confirmed", uncertain=action != "preview"
                )
            status, code = "confirmed", None
        except providers.ProviderFailure as error:
            status, code, safe = (
                "uncertain" if error.uncertain else "failed",
                error.code,
                {},
            )
        except Exception:
            status, code, safe = (
                "uncertain" if action != "preview" else "failed",
                "comment_result_unknown",
                {},
            )
        with transaction(self.settings, True, anonymous=True) as c:
            current = one(
                c,
                (
                    "SELECT * FROM crm_channels2.SocialComment WHER"
                    "E InstitutionId=? AND CommentId=?"
                ),
                institution(self.settings),
                uid(identity),
            )
            current_item = account(c, self.settings, str(item["IntegrationId"]))
            active_intent = c.execute(
                (
                    "SELECT 1 FROM crm_channels2.ProviderOperation "
                    "WHERE InstitutionId=? AND OperationId=? AND St"
                    "atus='running' AND LeaseUntil>SYSUTCDATETIME()"
                ),
                institution(self.settings),
                operation,
            ).fetchone()
            try:
                authorize(c, self.settings, authority, "inbox.write")
                allowed = True
            except HTTPException:
                allowed = False
            if (
                not current
                or bytes(current["RowVersion"]) != bytes(comment["RowVersion"])
                or bytes(current_item["RowVersion"]) != bytes(item["RowVersion"])
                or not allowed
                or not active_intent
            ):
                status, code = "uncertain", "comment_or_authority_changed"
                safe = {}
            if status == "confirmed":
                payload = json.loads(current["Payload"])
                if action == "reconcile":
                    apply_source_result(payload, safe)
                else:
                    payload.setdefault("_crm", {}).update(safe)
                c.execute(
                    (
                        "UPDATE crm_channels2.SocialComment SET Payload"
                        "=?,Body=? WHERE InstitutionId=? AND CommentId=? AND R"
                        "owVersion=?"
                    ),
                    json.dumps(payload, ensure_ascii=False),
                    safe["body"] if action == "reconcile" and "body" in safe else current["Body"],
                    institution(self.settings),
                    uid(identity),
                    comment["RowVersion"],
                )
                if c.rowcount != 1:
                    raise HTTPException(409, "revision_conflict")
                c.execute("UPDATE crm_workspace.State SET Revision=Revision+1 WHERE StateId=1")
            c.execute(
                (
                    "UPDATE crm_channels2.ProviderOperation SET Sta"
                    "tus=?,ResultCode=?,ResultMetadata=?,CompletedA"
                    "t=SYSUTCDATETIME(),LeaseUntil=NULL WHERE Insti"
                    "tutionId=? AND OperationId=? AND Status='runni"
                    "ng'"
                ),
                status,
                code,
                json.dumps(safe),
                institution(self.settings),
                operation,
            )
        return {"status": status, "code": code, "result": safe}


def valid_source_result(result):
    source = result.get("source")
    return isinstance(source, dict) and (
        source == {"status": "available"} and isinstance(result.get("body"), str)
        and len(result["body"]) <= 4000 and set(result) == {"source", "body"}
        or source == {"status": "unavailable", "reason": "provider_permission_or_request_rejected"}
        and set(result) == {"source"}
    )


def apply_source_result(payload, result):
    state = payload.setdefault("_crm", {})
    state["source"] = {
        **result["source"], "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    if result["source"]["status"] == "unavailable":
        if state.get("state") != "unavailable":
            state["state_before_unavailable"] = state.get("state", "new")
        state["state"] = "unavailable"
    elif state.get("state") == "unavailable":
        state["state"] = state.pop("state_before_unavailable", "new")


def install(app, settings):
    service = Effects(settings)

    @app.get("/api/institution/comments/{identity}/preview")
    def preview(request: Request, identity: str):
        return service.preview(request.state.authority, identity)

    @app.post("/api/institution/comments/{identity}/effects/{action}")
    def effect(request: Request, identity: str, action: str, body: Effect):
        return service.perform(request.state.authority, identity, action, body)
