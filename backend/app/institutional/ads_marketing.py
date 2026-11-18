"""Marketing reads and versioned local drafts on the existing P9 journal."""

import hmac
import hashlib
import json
from datetime import timedelta
from typing import Literal
from uuid import uuid4

from fastapi import HTTPException, Request
from pydantic import Field, model_validator

from app.institutional.ads import Ads, account, clock, event, packed
from app.institutional.ads_meta_provider import MetaReader, validate_period
from app.institutional.ads_models import Command, SaveAccount, Account
from app.institutional.auth import authorize
from app.institutional.channel_operations import (
    account as channel_account,
    app_secret_kind,
)
from app.institutional.channel_secrets import get as secret_get, put as secret_put
from app.institutional.crypto import unseal
from app.institutional.db import (
    audit,
    bound_hash,
    institution,
    key,
    one,
    record_operation,
    replay,
    rows,
    uid,
)
from app.institutional.models import public_url
from app.modules.agents.domain import JsonUUID


class Source(Command):
    integration_id: JsonUUID


class Connect(Source):
    external_account_id: str = Field(pattern=r"^[0-9]{1,32}$")


class Complete(Source):
    oauth_session_id: JsonUUID


class Sync(Command):
    start: str
    end: str

    @model_validator(mode="after")
    def period(self):
        validate_period(self.start, self.end)
        return self


class Draft(Command):
    draft_id: JsonUUID | None = None
    draft_revision: int = Field(default=0, ge=0)
    entity: Literal["campaign", "adset", "ad"] = "campaign"
    mode: Literal["create", "edit"] = "create"
    target_id: str = Field(default="", pattern=r"^$|^[0-9]{1,32}$")
    parent_id: str = Field(default="", pattern=r"^$|^[0-9]{1,32}$")
    name: str = Field(min_length=1, max_length=180)
    objective: Literal[
        "OUTCOME_LEADS",
        "OUTCOME_TRAFFIC",
        "OUTCOME_ENGAGEMENT",
        "OUTCOME_AWARENESS",
        "OUTCOME_SALES",
    ] = "OUTCOME_LEADS"
    daily_budget_cents: int = Field(default=0, ge=0, le=1000000000000)
    body: str = Field(default="", max_length=8000)
    headline: str = Field(default="", max_length=250)
    destination_url: str = Field(default="", max_length=2000)
    image_url: str = Field(default="", max_length=2000)
    countries: list[str] = Field(default_factory=lambda: ["CO"], max_length=25)

    @model_validator(mode="after")
    def valid(self):
        if not self.name.strip() or len(self.name.encode("utf-16-le")) > 360:
            raise ValueError("invalid_name")
        for url in [self.destination_url, self.image_url]:
            if url:
                public_url(url)
        if any(
            len(v) != 2 or not v.isascii() or not v.isalpha() or v != v.upper()
            for v in self.countries
        ):
            raise ValueError("invalid_countries")
        if self.mode == "edit" and not self.target_id:
            raise ValueError("target_required")
        if self.entity != "campaign" and not self.parent_id:
            raise ValueError("parent_required")
        return self


def latest(c, s, identity, kind):
    order = (
        "JSON_VALUE(Document,'$.requested_at') DESC," if kind == "meta_snapshot" else ""
    )
    row = one(
        c,
        "SELECT TOP(1) Document,EventId FROM crm_ads9.Event WHERE InstitutionId=? AND AccountId=? AND Kind=? ORDER BY "
        + order
        + "CreatedAt DESC,EventId DESC",
        institution(s),
        uid(identity),
        kind,
    )
    return (
        (json.loads(row["Document"]), uid(str(row["EventId"]))) if row else (None, None)
    )


def source(c, s, identity):
    item = channel_account(c, s, str(identity))
    if (
        item["Provider"] != "meta"
        or item["IssuerProfile"] != "facebook_login"
        or item["VerifiedStatus"] == "retired"
        or item["ApplicationState"] == "retired"
        or item["EgressProfile"] == "synthetic_no_provider"
    ):
        raise HTTPException(409, "ads_meta_login_source_required")
    kind = (
        "instagram_user_access"
        if item["Channel"] == "instagram"
        else "facebook_user_access"
    )
    raw, secret = secret_get(c, s, "integration", str(identity), kind)
    fingerprint = [
        str(item["IntegrationId"]),
        bytes(item["RowVersion"]).hex(),
        bytes(item["ApplicationVersion"]).hex(),
        str(secret["SecretId"]),
    ]
    return item, raw, fingerprint


def credential(c, s, a):
    if not a["SecretId"]:
        if not a["IntegrationId"]:
            raise HTTPException(409, "ads_meta_login_source_required")
        return source(c, s, a["IntegrationId"])
    row = one(
        c,
        "SELECT * FROM crm_ads9.Secret WHERE InstitutionId=? AND AccountId=? AND SecretId=?",
        institution(s),
        a["AccountId"],
        a["SecretId"],
    )
    if not row:
        raise HTTPException(409, "credential_required")
    binding = dict(
        institution=institution(s),
        scope="ads9",
        owner=uid(str(a["AccountId"])),
        kind="access_token",
        version=row["VersionNo"],
        secret_id=uid(str(row["SecretId"])),
    )
    if row["KeyId"] != hashlib.sha256(key(s)).hexdigest()[:32]:
        raise HTTPException(503, "credential_key_mismatch")
    try:
        raw = unseal(key(s), binding, row["Nonce"], row["Ciphertext"])
    except Exception:
        raise HTTPException(503, "credential_authentication_failed") from None
    if a["IntegrationId"]:
        item = channel_account(c, s, str(a["IntegrationId"]))
        version = item["ApiVersion"]
    else:
        # Standalone legacy tokens require an explicitly bound app/version first.
        raise HTTPException(409, "ads_meta_login_source_required")
    return dict(ApiVersion=version), raw, [str(a["SecretId"])]


def draft_issues(doc, snapshot):
    problems = []
    if doc["entity"] == "adset" and not doc["daily_budget_cents"]:
        problems.append("Define el presupuesto diario propuesto del conjunto.")
    if doc["entity"] == "ad" and (
        not doc["body"].strip() or not doc["destination_url"] or not doc["image_url"]
    ):
        problems.append("Completa el texto, la imagen y el enlace del anuncio.")
    collection = {"campaign": "campaigns", "adset": "adsets", "ad": "ads"}
    if doc["mode"] == "edit" and not any(
        v["id"] == doc["target_id"] for v in snapshot[collection[doc["entity"]]]
    ):
        problems.append(
            "El objeto a editar ya no aparece en la captura de esta cuenta."
        )
    parent_collection = {"adset": "campaigns", "ad": "adsets"}.get(doc["entity"])
    if parent_collection and not any(
        v["id"] == doc["parent_id"] for v in snapshot[parent_collection]
    ):
        problems.append(
            "Selecciona un elemento padre de esta cuenta y vuelve a revisar."
        )
    return problems


class Marketing:
    def __init__(self, settings, reader=MetaReader):
        self.settings, self.reader = settings, reader
        self.ads = Ads(settings)

    def client(self, token, version):
        if (
            self.reader is MetaReader
            and getattr(self.settings, "postgres_profile", False)
            and not getattr(self.settings, "postgres_deployment", False)
        ):
            raise HTTPException(409, "provider_network_disabled")
        return self.reader(token, version)

    def discover(self, auth, body):
        s = self.settings
        with self.ads.tx(auth, recent=True) as (c, _):
            authorize(c, s, auth, "settings.channels.write", recent=True)
            item, token, stamp = source(c, s, body.integration_id)
        found = self.client(token, item["ApiVersion"]).accounts()
        with self.ads.tx(auth, recent=True) as (c, _):
            authorize(c, s, auth, "settings.channels.write", recent=True)
            if source(c, s, body.integration_id)[2] != stamp:
                raise HTTPException(409, "ads_meta_context_changed")
        return dict(items=found, provider_writes=False)

    def connect(self, auth, body):
        s = self.settings
        with self.ads.tx(auth, recent=True) as (c, _):
            authorize(c, s, auth, "settings.channels.write", recent=True)
            item, token, stamp = source(c, s, body.integration_id)
        remote = self.client(token, item["ApiVersion"]).account(
            body.external_account_id
        )
        from app.institutional.ads import stable

        identity = stable(institution(s), "meta", remote["id"])
        with self.ads.tx(auth, recent=True) as (c, _):
            if source(c, s, body.integration_id)[2] != stamp:
                raise HTTPException(409, "ads_meta_context_changed")
            old = one(
                c,
                "SELECT * FROM crm_ads9.Account WHERE InstitutionId=? AND AccountId=?",
                institution(s),
                identity,
            )
            previous = json.loads(old["Document"]) if old else {}
        doc = Account(
            **{
                **previous,
                "provider": "meta",
                "external_account_id": remote["id"],
                "name": remote["name"],
                "currency": remote["currency"],
                "timezone": remote["timezone"],
                "integration_id": str(body.integration_id),
                "status": "connected",
            }
        )

        def check(c):
            authorize(c, s, auth, "settings.channels.write", recent=True)
            if source(c, s, body.integration_id)[2] != stamp:
                raise HTTPException(409, "ads_meta_context_changed")

        result = self.ads.save_account(
            auth,
            SaveAccount(
                operation_id=body.operation_id,
                revision=old["Revision"] if old else 0,
                reason=body.reason,
                document=doc,
            ),
            identity if old else None,
            source_check=check,
        )
        return dict(result, meta_account=remote)

    def sync(self, auth, identity, body):
        s = self.settings
        requested_at = clock().isoformat() + "Z"
        with self.ads.tx(auth, recent=True) as (c, actor):
            authorize(c, s, auth, "settings.channels.write", recent=True)
            a = account(c, s, identity)
            if a["State"] != "connected" or a["Provider"] != "meta":
                raise HTTPException(409, "ads_account_paused")
            if a["Revision"] != body.revision:
                raise HTTPException(409, "revision_conflict")
            _, old = replay(
                c,
                s,
                actor["UserId"],
                str(body.operation_id),
                "ads9.meta_sync",
                identity,
                body.model_dump(mode="json"),
            )
            if old:
                return old
            item, token, stamp = credential(c, s, a)
        value = self.client(token, item["ApiVersion"]).snapshot(
            a["ExternalId"], body.start, body.end
        )
        value["requested_at"] = requested_at
        with self.ads.tx(auth, True, True) as (c, actor):
            authorize(c, s, auth, "settings.channels.write", recent=True)
            current = account(c, s, identity)
            if (
                current["Revision"] != a["Revision"]
                or current["State"] != "connected"
                or credential(c, s, current)[2] != stamp
            ):
                raise HTTPException(409, "ads_meta_context_changed")
            digest, prior = replay(
                c,
                s,
                actor["UserId"],
                str(body.operation_id),
                "ads9.meta_sync",
                identity,
                body.model_dump(mode="json"),
            )
            if prior:
                return prior
            if len(packed(value).encode()) > 1_500_000:
                raise HTTPException(413, "ads_meta_scope_limit")
            event(c, s, identity, actor, "meta_snapshot", value)
            record_operation(
                c,
                s,
                actor["UserId"],
                str(body.operation_id),
                "ads9.meta_sync",
                identity,
                digest,
                value,
            )
            return value

    def snapshot(self, auth, identity, start, end):
        validate_period(start, end)
        with self.ads.tx(auth) as (c, _):
            account(c, self.settings, identity)
            row = one(
                c,
                "SELECT TOP(1) Document FROM crm_ads9.Event WHERE InstitutionId=? AND AccountId=? AND Kind='meta_snapshot' AND JSON_VALUE(Document,'$.period.start')=? AND JSON_VALUE(Document,'$.period.end')=? ORDER BY JSON_VALUE(Document,'$.requested_at') DESC,CreatedAt DESC,EventId DESC",
                institution(self.settings),
                identity,
                start,
                end,
            )
            return {"snapshot": json.loads(row["Document"]) if row else None}

    def drafts(self, auth, identity):
        with self.ads.tx(auth) as (c, _):
            account(c, self.settings, identity)
            found = rows(
                c,
                "SELECT TOP(1001) Document FROM crm_ads9.Event WHERE InstitutionId=? AND AccountId=? AND Kind='meta_draft' ORDER BY CreatedAt DESC,EventId DESC",
                institution(self.settings),
                identity,
            )
            if len(found) > 1000:
                raise HTTPException(413, "ads_meta_draft_scope_limit")
            result = {}
            for value in found:
                doc = json.loads(value["Document"])
                result.setdefault(doc["id"], doc)
            _, snapshot_id = latest(c, self.settings, identity, "meta_snapshot")
            reviews = rows(
                c,
                "SELECT TOP(1001) Document FROM crm_ads9.Event WHERE InstitutionId=? AND AccountId=? AND Kind='meta_draft_review' ORDER BY CreatedAt DESC,EventId DESC",
                institution(self.settings),
                identity,
            )
            seen = set()
            for row in reviews:
                review = json.loads(row["Document"])
                if review["draft_id"] in seen:
                    continue
                seen.add(review["draft_id"])
                draft = result.get(review["draft_id"])
                if (
                    draft
                    and review["revision"] == draft["revision"]
                    and review["snapshot_id"] == snapshot_id
                    and review["reviewed"]
                ):
                    draft["review_valid"] = True
            return {"items": list(result.values()), "provider_writes": False}

    def save_draft(self, auth, identity, body):
        s = self.settings
        with self.ads.tx(auth, True) as (c, actor):
            a = account(c, s, identity)
            if a["Provider"] != "meta" or a["State"] != "connected":
                raise HTTPException(409, "ads_account_paused")
            digest, old = replay(
                c,
                s,
                actor["UserId"],
                str(body.operation_id),
                "ads9.meta_draft",
                identity,
                body.model_dump(mode="json"),
            )
            if old:
                return old
            snapshot, snapshot_id = latest(c, s, identity, "meta_snapshot")
            if not snapshot:
                raise HTTPException(409, "ads_meta_sync_required")
            draft_id = str(body.draft_id or uuid4())
            previous = one(
                c,
                "SELECT TOP(1) Document FROM crm_ads9.Event WHERE InstitutionId=? AND AccountId=? AND Kind='meta_draft' AND JSON_VALUE(Document,'$.id')=? ORDER BY CreatedAt DESC,EventId DESC",
                institution(s),
                identity,
                draft_id,
            )
            prior = json.loads(previous["Document"]) if previous else None
            if (prior["revision"] if prior else 0) != body.draft_revision:
                raise HTTPException(409, "revision_conflict")
            value = body.model_dump(
                mode="json",
                exclude={
                    "operation_id",
                    "revision",
                    "reason",
                    "draft_id",
                    "draft_revision",
                },
            )
            value.update(
                id=draft_id,
                revision=body.draft_revision + 1,
                account_id=identity,
                state="draft",
                source_snapshot_id=snapshot_id,
                provider_writes=False,
                updated_at=clock().isoformat() + "Z",
                review_valid=False,
            )
            problems = draft_issues(value, snapshot)
            value["issues"] = problems
            event(c, s, identity, actor, "meta_draft", value)
            record_operation(
                c,
                s,
                actor["UserId"],
                str(body.operation_id),
                "ads9.meta_draft",
                identity,
                digest,
                value,
            )
            return value

    def review(self, auth, identity, draft, body):
        s = self.settings
        with self.ads.tx(auth, True, True) as (c, actor):
            account(c, s, identity)
            digest, prior = replay(
                c,
                s,
                actor["UserId"],
                str(body.operation_id),
                "ads9.meta_review",
                draft,
                body.model_dump(mode="json"),
            )
            if prior:
                return prior
            row = one(
                c,
                "SELECT TOP(1) Document FROM crm_ads9.Event WHERE InstitutionId=? AND AccountId=? AND Kind='meta_draft' AND JSON_VALUE(Document,'$.id')=? ORDER BY CreatedAt DESC,EventId DESC",
                institution(s),
                identity,
                draft,
            )
            if not row:
                raise HTTPException(404, "ads_meta_draft_not_found")
            value = json.loads(row["Document"])
            if value["revision"] != body.revision:
                raise HTTPException(409, "revision_conflict")
            snapshot, snapshot_id = latest(c, s, identity, "meta_snapshot")
            issues = (
                draft_issues(value, snapshot)
                if snapshot
                else ["Sincroniza la cuenta antes de revisar."]
            )
            result = dict(
                draft_id=draft,
                revision=body.revision,
                snapshot_id=snapshot_id,
                issues=issues,
                reviewed=not issues,
                provider_writes=False,
                message="Revisión local completada. La publicación aún requiere autorización explícita.",
            )
            event(c, s, identity, actor, "meta_draft_review", result)
            record_operation(
                c,
                s,
                actor["UserId"],
                str(body.operation_id),
                "ads9.meta_review",
                draft,
                digest,
                result,
            )
            return result

    def complete(self, auth, body):
        s = self.settings
        with self.ads.tx(auth, True, True) as (c, actor):
            authorize(c, s, auth, "settings.channels.write", recent=True)
            session = one(
                c,
                "SELECT *,CASE WHEN ExpiresAt<=SYSUTCDATETIME() THEN 1 ELSE 0 END AS Expired FROM crm_channels2.OAuthSession WHERE InstitutionId=? AND OAuthSessionId=?",
                institution(s),
                str(body.oauth_session_id),
            )
            if (
                not session
                or session["ActorRef"] != str(actor["UserId"]).lower()
                or not hmac.compare_digest(
                    bytes(session["AuthSessionHash"]),
                    bound_hash(s, auth["token"], "oauth-session"),
                )
            ):
                raise HTTPException(404, "oauth_session_not_found")
            if str(session["IntegrationId"]).lower() != str(
                body.integration_id
            ) or json.loads(session["RequestedScopes"]) != ["ads_read"]:
                raise HTTPException(409, "ads_meta_oauth_scope_mismatch")
            item = channel_account(c, s, str(body.integration_id))
            if (
                item["Provider"] != "meta"
                or item["IssuerProfile"] != "facebook_login"
                or item["VerifiedStatus"] == "retired"
                or item["ApplicationState"] == "retired"
            ):
                raise HTTPException(409, "ads_meta_login_source_required")
            _, secret = secret_get(
                c, s, "application", str(item["ApplicationId"]), app_secret_kind(item)
            )
            if (
                str(item["ApplicationId"]) != str(session["ApplicationId"])
                or bytes(item["ApplicationVersion"])
                != bytes(session["ApplicationVersion"])
                or str(secret["SecretId"]) != str(session["ClientSecretId"])
            ):
                raise HTTPException(409, "oauth_application_changed")
            if session["Status"] == "completed":
                source(c, s, body.integration_id)
                return {"connected": True, "provider_writes": False}
            if session["Expired"] or session["Status"] != "assets_ready":
                raise HTTPException(409, "ads_meta_oauth_not_ready")
            access, _ = secret_get(
                c, s, "oauth", str(body.oauth_session_id), "oauth_provisional_access"
            )
            asset = one(
                c,
                "SELECT TOP(1) Metadata,ObservedAt FROM crm_channels2.ProviderAsset WHERE InstitutionId=? AND OAuthSessionId=? AND Kind='login_identity'",
                institution(s),
                str(body.oauth_session_id),
            )
            lifetime = (
                json.loads(asset["Metadata"]).get("expires_in") if asset else None
            )
            expires = (
                asset["ObservedAt"] + timedelta(seconds=max(1, lifetime - 60))
                if type(lifetime) is int and 1 <= lifetime <= 366 * 86400
                else None
            )
            kind = (
                "instagram_user_access"
                if item["Channel"] == "instagram"
                else "facebook_user_access"
            )
            secret_put(
                c,
                s,
                "integration",
                str(body.integration_id),
                kind,
                access,
                expires=expires,
            )
            c.execute(
                "UPDATE crm_channels2.OAuthSession SET Status='completed',CompletedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND OAuthSessionId=? AND Status='assets_ready'",
                institution(s),
                str(body.oauth_session_id),
            )
            audit(
                c,
                s,
                actor["UserId"],
                "ads9.meta_oauth_complete",
                str(body.integration_id),
            )
            return {"connected": True, "provider_writes": False}


def install(app, settings):
    service = Marketing(settings)

    @app.post("/api/institution/ads/meta/discover")
    def discover(request: Request, body: Source):
        return service.discover(request.state.authority, body)

    @app.post("/api/institution/ads/meta/connect")
    def connect(request: Request, body: Connect):
        return service.connect(request.state.authority, body)

    @app.post("/api/institution/ads/meta/oauth/complete")
    def complete(request: Request, body: Complete):
        return service.complete(request.state.authority, body)

    @app.get("/api/institution/ads/meta/{identity}/snapshot")
    def snapshot(request: Request, identity: str, start: str, end: str):
        return service.snapshot(request.state.authority, uid(identity), start, end)

    @app.post("/api/institution/ads/meta/{identity}/sync")
    def sync(request: Request, identity: str, body: Sync):
        return service.sync(request.state.authority, uid(identity), body)

    @app.get("/api/institution/ads/meta/{identity}/drafts")
    def drafts(request: Request, identity: str):
        return service.drafts(request.state.authority, uid(identity))

    @app.post("/api/institution/ads/meta/{identity}/drafts")
    def save_draft(request: Request, identity: str, body: Draft):
        return service.save_draft(request.state.authority, uid(identity), body)

    @app.post("/api/institution/ads/meta/{identity}/drafts/{draft}/review")
    def review(request: Request, identity: str, draft: str, body: Command):
        return service.review(request.state.authority, uid(identity), uid(draft), body)
