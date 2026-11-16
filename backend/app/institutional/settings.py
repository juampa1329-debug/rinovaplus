"""Revisioned institutional settings, safe credentials and append-only history."""

import json

from fastapi import HTTPException

from app.institutional.auth import authorize
from app.institutional.crypto import password_matches
from app.institutional.db import (
    audit,
    institution,
    one,
    public_user,
    record_operation,
    replay,
    rows,
    save_secret,
    uid,
    utc,
)
from app.institutional.management import revoke_user
from app.institutional.models import SECTIONS
from app.institutional.policy import MODULES, READY
from app.institutional.store import transaction
from app.modules.ai.domain.models import PROVIDERS

SCOPES = {
    "institution": "institution",
    "ai": "ai",
    "models": "providers",
    "modules": "modules",
    "budgets": "budgets",
    "webhooks": "webhooks",
}


def scope(section, write=False):
    if section not in SCOPES:
        raise HTTPException(404, "setting_not_found")
    return "settings." + SCOPES[section] + (".write" if write else ".read")


def setting(cursor, settings, section):
    value = one(
        cursor,
        (
            "SELECT Document,Revision,UpdatedAt FRO"
            "M crm_access.Setting WHERE Institution"
            "Id=? AND Section=?"
        ),
        institution(settings),
        section,
    )
    if not value:
        raise HTTPException(503, "setting_unavailable")
    return {
        "document": json.loads(value["Document"]),
        "revision": value["Revision"],
        "updated_at": utc(value["UpdatedAt"]),
    }


def validate_links(cursor, settings, section, document):
    if section == "webhooks":
        for endpoint in document["endpoints"]:
            for identity in endpoint["integration_ids"]:
                value = one(
                    cursor,
                    (
                        "SELECT Provider,Channel FROM crm_chann"
                        "els2.Integration WHERE InstitutionId=?"
                        " AND IntegrationId=?"
                    ),
                    institution(settings),
                    uid(identity),
                )
                if not value or not (
                    endpoint["provider"] in {value["Provider"], value["Channel"]}
                    or endpoint["provider"] == "facebook"
                    and value["Channel"] == "messenger"
                ):
                    raise HTTPException(422, "webhook_integration_mismatch")


class Settings:
    def __init__(self, settings):
        self.settings = settings

    def read(self, authority, section):
        with transaction(self.settings, anonymous=True) as c:
            authorize(c, self.settings, authority, scope(section))
            result = setting(c, self.settings, section)
        if section == "webhooks":
            result["operational"] = False
        return result

    def save(self, authority, section, body):
        if (
            self.settings.ticket.get("version")
            in {
                "cbn-institutional-channels-p4-v1",
                "cbn-institutional-agents-p5-v1",
                "cbn-institutional-knowledge-p6-v1",
                "cbn-institutional-broadcast-p7-v1",
                "cbn-institutional-campaign-p8-v1",
                "cbn-institutional-ads-p9-v1",
            'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}
            and section == "webhooks"
        ):
            raise HTTPException(409, "webhooks_managed_by_channel")
        action = scope(section, True)
        document = (
            SECTIONS[section].model_validate(body.document).model_dump(mode="json")
        )
        with transaction(self.settings, True, anonymous=True) as c:
            actor = authorize(
                c,
                self.settings,
                authority,
                action,
                recent=section in {"models", "budgets", "webhooks"},
            )
            digest, prior = replay(
                c,
                self.settings,
                actor["UserId"],
                body.operation_id,
                action,
                section,
                {"revision": body.revision, "document": document},
            )
            if prior:
                return prior
            current = setting(c, self.settings, section)
            if current["revision"] != body.revision:
                raise HTTPException(409, "revision_conflict")
            if section == "ai" and document["comment_mode"] == "auto" and document["comment_auto_reply"].strip():
                changed_policy = any(
                    document[field] != current["document"].get(field)
                    for field in ("comment_mode", "comment_prompt", "comment_auto_reply")
                )
                if changed_policy:
                    authorize(c, self.settings, authority, action, recent=True)
            validate_links(c, self.settings, section, document)
            linked = None
            spanish = self.settings.ticket.get("version") in {
                "cbn-institutional-spanish-p2-v1",
                "cbn-institutional-spanish-p3-v1",
                "cbn-institutional-channels-p4-v1",
                "cbn-institutional-agents-p5-v1",
                "cbn-institutional-knowledge-p6-v1",
                "cbn-institutional-broadcast-p7-v1",
                "cbn-institutional-campaign-p8-v1",
                "cbn-institutional-ads-p9-v1",
            'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}
            if spanish and section in {"ai", "models"}:
                from app.institutional.model_settings import (
                    MEDIA_PROJECTIONS,
                    PROJECTIONS,
                    project,
                    validate_projection,
                )

                if section == "ai":
                    selected_models = setting(c, self.settings, "models")["document"]
                    # A form can change a provider while retaining its read-only
                    # projections. Recompute from the SQL authority in this same
                    # transaction; never require the client to forge those IDs.
                    unchanged = all(
                        document.get(key) == current["document"].get(key)
                        for key in PROJECTIONS
                    ) and all(
                        document.get("media", {}).get(key)
                        == current["document"].get("media", {}).get(key)
                        for key in MEDIA_PROJECTIONS
                    )
                    document = (
                        project(document, selected_models)
                        if unchanged
                        else validate_projection(document, selected_models)
                    )
                else:
                    old_ai = setting(c, self.settings, "ai")
                    new_ai = project(old_ai["document"], document)
                    if new_ai != old_ai["document"]:
                        linked = (old_ai, new_ai)
            if spanish and section == "webhooks":
                from app.institutional.webhooks import synchronize

                synchronize(c, self.settings, document)
            text = json.dumps(document, ensure_ascii=False)
            c.execute(
                (
                    "UPDATE crm_access.Setting SET Document"
                    "=?,Revision=Revision+1,UpdatedBy=?,Upd"
                    "atedAt=SYSUTCDATETIME() WHERE Institut"
                    "ionId=? AND Section=? AND Revision=?"
                ),
                text,
                actor["UserId"],
                institution(self.settings),
                section,
                body.revision,
            )
            if c.rowcount != 1:
                raise HTTPException(409, "revision_conflict")
            c.execute(
                (
                    "INSERT crm_access.SettingHistory(Insti"
                    "tutionId,Section,Revision,Document,Rec"
                    "ordedAt,ActorId) VALUES(?,?,?,?,SYSUTC"
                    "DATETIME(),?)"
                ),
                institution(self.settings),
                section,
                body.revision + 1,
                text,
                actor["UserId"],
            )
            if linked:
                previous, next_ai = linked
                ai_text = json.dumps(next_ai, ensure_ascii=False)
                c.execute(
                    (
                        "UPDATE crm_access.Setting SET Document"
                        "=?,Revision=Revision+1,UpdatedBy=?,Upd"
                        "atedAt=SYSUTCDATETIME() WHERE Institut"
                        "ionId=? AND Section='ai' AND Revision="
                        "?"
                    ),
                    ai_text,
                    actor["UserId"],
                    institution(self.settings),
                    previous["revision"],
                )
                if c.rowcount != 1:
                    raise HTTPException(409, "revision_conflict")
                c.execute(
                    (
                        "INSERT crm_access.SettingHistory(Insti"
                        "tutionId,Section,Revision,Document,Rec"
                        "ordedAt,ActorId) VALUES(?,'ai',?,?,SYS"
                        "UTCDATETIME(),?)"
                    ),
                    institution(self.settings),
                    previous["revision"] + 1,
                    ai_text,
                    actor["UserId"],
                )
            result = setting(c, self.settings, section)
            record_operation(
                c,
                self.settings,
                actor["UserId"],
                body.operation_id,
                action,
                section,
                digest,
                result,
            )
            audit(
                c,
                self.settings,
                actor["UserId"],
                action,
                section,
                revision=body.revision + 1,
                fields=sorted(document),
            )
        return result

    def history(self, authority, section):
        with transaction(self.settings, anonymous=True) as c:
            authorize(c, self.settings, authority, scope(section))
            result = rows(
                c,
                (
                    "SELECT TOP(100) Revision,RecordedAt FR"
                    "OM crm_access.SettingHistory WHERE Ins"
                    "titutionId=? AND Section=? ORDER BY Re"
                    "vision DESC"
                ),
                institution(self.settings),
                section,
            )
        return {
            "items": [
                {"revision": r["Revision"], "recorded_at": utc(r["RecordedAt"])}
                for r in result
            ]
        }

    def restore(self, authority, section, revision, body):
        if revision < 1:
            raise HTTPException(422, "invalid_revision")
        with transaction(self.settings, anonymous=True) as c:
            authorize(c, self.settings, authority, scope(section, True), recent=True)
            old = c.execute(
                (
                    "SELECT Document FROM crm_access.Settin"
                    "gHistory WHERE InstitutionId=? AND Sec"
                    "tion=? AND Revision=?"
                ),
                institution(self.settings),
                section,
                revision,
            ).fetchval()
            if old is None:
                raise HTTPException(404, "configuration_revision_not_found")
        # The save transaction rechecks session/rights/current revision and appends
        # history.
        from app.institutional.models import SettingEdit

        old_document = json.loads(old)
        if section == "ai" and self.settings.ticket.get("version") in {
            "cbn-institutional-spanish-p2-v1",
            "cbn-institutional-spanish-p3-v1",
            "cbn-institutional-channels-p4-v1",
            "cbn-institutional-agents-p5-v1",
            "cbn-institutional-knowledge-p6-v1",
            "cbn-institutional-broadcast-p7-v1",
            "cbn-institutional-campaign-p8-v1",
            "cbn-institutional-ads-p9-v1",
        'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
            from app.institutional.model_settings import project

            with transaction(self.settings, anonymous=True) as c:
                authorize(
                    c, self.settings, authority, scope(section, True), recent=True
                )
                old_document = project(
                    old_document, setting(c, self.settings, "models")["document"]
                )

        return self.save(
            authority,
            section,
            SettingEdit(
                operation_id=body.operation_id,
                revision=body.revision,
                document=old_document,
            ),
        )

    def availability(self, authority):
        with transaction(self.settings, anonymous=True) as c:
            actor = authorize(c, self.settings, authority)
            enabled = setting(c, self.settings, "modules")["document"]["enabled"]
        agents = self.settings.ticket.get("version") in {
            "cbn-institutional-agents-p5-v1",
            "cbn-institutional-knowledge-p6-v1",
            "cbn-institutional-broadcast-p7-v1",
            "cbn-institutional-campaign-p8-v1",
            "cbn-institutional-ads-p9-v1",
        'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}
        ready = set(READY) | ({"agents", "assistant"} if agents else set())
        knowledge = self.settings.ticket.get("version") in {
            "cbn-institutional-knowledge-p6-v1",
            "cbn-institutional-broadcast-p7-v1",
            "cbn-institutional-campaign-p8-v1",
            "cbn-institutional-ads-p9-v1",
        'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}
        if knowledge:
            ready |= {"knowledge", "memory"}
        broadcasts = self.settings.ticket.get("version") in {
            "cbn-institutional-broadcast-p7-v1",
            "cbn-institutional-campaign-p8-v1",
            "cbn-institutional-ads-p9-v1",
        'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}
        if broadcasts:
            ready |= {"broadcasts"}
        campaigns = self.settings.ticket.get("version") in {
            "cbn-institutional-ads-p9-v1",
            "cbn-institutional-campaign-p8-v1",
        'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}
        if campaigns:
            ready |= {"campaigns"}
        ads = self.settings.ticket.get("version") in {'cbn-institutional-ads-p9-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}
        if ads:
            ready |= {"ads"}
        learning = self.settings.ticket.get('version') in {'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}
        if learning:
            ready |= {'intelligence'}
        return {
            "institutional_operations": self.settings.ticket.get("version") == "cbn-institutional-operations-p11-v1",
            "learning_operations": learning,
            "broadcast_operations": broadcasts,
            "campaign_operations": campaigns,
            "ads_operations": ads,
            "modules": [
                {
                    "id": m,
                    "enabled": enabled[m],
                    "implemented": m in ready,
                    "operational": enabled[m] and m in ready,
                }
                for m in MODULES
            ],
            "actions": json.loads(actor["Actions"]),
            "institutional_auth": True,
            "agent_operations": agents,
            "knowledge_operations": knowledge,
            "channel_operations": self.settings.ticket.get("version")
            in {
                "cbn-institutional-channels-p4-v1",
                "cbn-institutional-agents-p5-v1",
                "cbn-institutional-knowledge-p6-v1",
                "cbn-institutional-broadcast-p7-v1",
                "cbn-institutional-campaign-p8-v1",
                "cbn-institutional-ads-p9-v1",
            'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'},
            "providers": False,
            "public_webhooks": False,
            "provider_workers": False,
        }

    def credentials(self, authority, scope_name):
        if self.settings.ticket.get("version") in {
            "cbn-institutional-channels-p4-v1",
            "cbn-institutional-agents-p5-v1",
            "cbn-institutional-knowledge-p6-v1",
            "cbn-institutional-broadcast-p7-v1",
            "cbn-institutional-campaign-p8-v1",
            "cbn-institutional-ads-p9-v1",
        'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'} and scope_name in {
            "channel",
            "webhook",
        }:
            from app.institutional.channel_operations import credentials

            return credentials(self.settings, authority, scope_name)
        permissions = {
            "provider": "providers",
            "channel": "channels",
            "webhook": "webhooks",
        }
        if scope_name not in permissions:
            raise HTTPException(404, "credential_scope_not_found")
        with transaction(self.settings, anonymous=True) as c:
            authorize(
                c,
                self.settings,
                authority,
                "settings." + permissions[scope_name] + ".read",
            )
            items = rows(
                c,
                (
                    "SELECT SecretId,OwnerRef,Kind,VersionN"
                    "o,Hint,State,CreatedAt FROM crm_access"
                    ".Secret WHERE InstitutionId=? AND Scop"
                    "e=? AND State='staged' ORDER BY OwnerR"
                    "ef,Kind"
                ),
                institution(self.settings),
                scope_name,
            )
        return {
            "items": [
                {
                    "id": uid(str(v["SecretId"])),
                    "owner": v["OwnerRef"],
                    "kind": v["Kind"],
                    "version": v["VersionNo"],
                    "hint": v["Hint"],
                    "state": v["State"],
                    "configured": True,
                    "verified": False,
                    "updated_at": utc(v["CreatedAt"]),
                }
                for v in items
            ]
        }

    def secret(self, authority, body, *, remove=False):
        if self.settings.ticket.get("version") in {
            "cbn-institutional-channels-p4-v1",
            "cbn-institutional-agents-p5-v1",
            "cbn-institutional-knowledge-p6-v1",
            "cbn-institutional-broadcast-p7-v1",
            "cbn-institutional-campaign-p8-v1",
            "cbn-institutional-ads-p9-v1",
        'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'} and body.scope in {
            "channel",
            "webhook",
        }:
            from app.institutional.channel_operations import save_credential

            return save_credential(self.settings, authority, body, remove)
        permissions = {
            "provider": "providers",
            "channel": "channels",
            "webhook": "webhooks",
        }
        action = "settings." + permissions[body.scope] + ".write"
        raw = body.value.get_secret_value() if body.value else None
        if (
            not remove
            and raw
            and (len(raw) < 8 or any(ord(v) < 33 or ord(v) > 126 for v in raw))
        ):
            raise HTTPException(422, "invalid_credential_value")
        with transaction(self.settings, True, anonymous=True) as c:
            actor = authorize(c, self.settings, authority, action, recent=True)
            if body.scope == "provider":
                if body.owner not in PROVIDERS or body.kind != "api_key":
                    raise HTTPException(422, "invalid_provider_credential")
            elif body.scope == "channel":
                prefix, _, identity = body.owner.partition(":")
                identity = uid(identity)
                if prefix == "application" and body.kind in {
                    "app_secret",
                    "client_secret",
                }:
                    found = c.execute(
                        (
                            "SELECT Provider FROM crm_channels2.App"
                            "lication WHERE InstitutionId=? AND App"
                            "licationId=?"
                        ),
                        institution(self.settings),
                        identity,
                    ).fetchval()
                    if (found, body.kind) not in {
                        ("meta", "app_secret"),
                        ("tiktok", "client_secret"),
                    }:
                        raise HTTPException(422, "credential_owner_mismatch")
                elif prefix == "integration" and body.kind in {
                    "access_token",
                    "page_access_token",
                }:
                    found = c.execute(
                        (
                            "SELECT Channel FROM crm_channels2.Inte"
                            "gration WHERE InstitutionId=? AND Inte"
                            "grationId=?"
                        ),
                        institution(self.settings),
                        identity,
                    ).fetchval()
                    if (
                        not found
                        or body.kind == "page_access_token"
                        and found not in {"instagram", "facebook", "messenger"}
                    ):
                        raise HTTPException(422, "credential_owner_mismatch")
                else:
                    raise HTTPException(422, "credential_owner_mismatch")
            else:
                prefix, _, identity = body.owner.partition(":")
                if (
                    self.settings.ticket.get("version")
                    == "cbn-institutional-spanish-p2-v1"
                ):
                    identity = uid(identity)
                    endpoints = c.execute(
                        (
                            "SELECT 1 FROM crm_channels2.WebhookEnd"
                            "point WHERE InstitutionId=? AND Endpoi"
                            "ntId=?"
                        ),
                        institution(self.settings),
                        identity,
                    ).fetchone()
                else:
                    endpoints = any(
                        v["key"] == identity
                        for v in setting(c, self.settings, "webhooks")["document"][
                            "endpoints"
                        ]
                    )
                if (
                    prefix != "endpoint"
                    or body.kind not in {"verify_token", "webhook_secret"}
                    or not endpoints
                ):
                    raise HTTPException(422, "credential_owner_mismatch")
            digest, prior = replay(
                c,
                self.settings,
                actor["UserId"],
                body.operation_id,
                action,
                body.owner,
                {
                    "scope": body.scope,
                    "kind": body.kind,
                    "value": raw,
                    "remove": remove,
                },
            )
            if prior:
                return prior
            if remove:
                c.execute(
                    (
                        "UPDATE crm_access.Secret SET State='re"
                        "tired' WHERE InstitutionId=? AND Scope"
                        "=? AND OwnerRef=? AND Kind=? AND State"
                        "='staged'"
                    ),
                    institution(self.settings),
                    body.scope,
                    body.owner,
                    body.kind,
                )
                result = {"removed": True}
            elif not raw:
                result = {"unchanged": True}
            else:
                result = save_secret(
                    c, self.settings, body.scope, body.owner, body.kind, raw
                )
            record_operation(
                c,
                self.settings,
                actor["UserId"],
                body.operation_id,
                action,
                body.owner,
                digest,
                result,
            )
            audit(
                c,
                self.settings,
                actor["UserId"],
                action,
                body.owner,
                scope=body.scope,
                kind=body.kind,
            )
        return result

    def own_profile(self, authority, body):
        with transaction(self.settings, True, anonymous=True) as c:
            actor = authorize(c, self.settings, authority)
            payload = body.model_dump(mode="json")
            payload.pop("current_password", None)
            digest, prior = replay(
                c,
                self.settings,
                actor["UserId"],
                body.operation_id,
                "profile.edit",
                actor["UserId"],
                payload,
            )
            if prior:
                return prior
            if actor["Revision"] != body.revision:
                raise HTTPException(409, "revision_conflict")
            email_changed = body.email != actor["Login"]
            if email_changed:
                authorize(c, self.settings, authority, recent=True)
                if not body.current_password or not password_matches(
                    body.current_password.get_secret_value(), actor["PasswordHash"]
                ):
                    raise HTTPException(401, "confirmation_failed")
                if c.execute(
                    (
                        "SELECT 1 FROM crm_access.AccessUser WH"
                        "ERE InstitutionId=? AND NormalizedLogi"
                        "n=? AND UserId<>?"
                    ),
                    institution(self.settings),
                    body.email,
                    actor["UserId"],
                ).fetchone():
                    raise HTTPException(409, "email_already_registered")
            c.execute(
                (
                    "UPDATE crm_access.AccessUser SET Login"
                    "=?,NormalizedLogin=?,DisplayName=?,Pro"
                    "file=?,Revision=Revision+1,UpdatedAt=S"
                    "YSUTCDATETIME() WHERE InstitutionId=? "
                    "AND UserId=? AND Revision=?"
                ),
                body.email,
                body.email,
                body.profile.full_name,
                body.profile.model_dump_json(),
                institution(self.settings),
                actor["UserId"],
                body.revision,
            )
            if c.rowcount != 1:
                raise HTTPException(409, "revision_conflict")
            if email_changed:
                revoke_user(c, self.settings, actor["UserId"])
            result = {
                "user": public_user(
                    one(
                        c,
                        (
                            "SELECT * FROM crm_access.AccessUser WH"
                            "ERE InstitutionId=? AND UserId=?"
                        ),
                        institution(self.settings),
                        actor["UserId"],
                    )
                ),
                "signed_out": email_changed,
            }
            record_operation(
                c,
                self.settings,
                actor["UserId"],
                body.operation_id,
                "profile.edit",
                actor["UserId"],
                digest,
                result,
            )
            audit(
                c,
                self.settings,
                actor["UserId"],
                "profile.edit",
                actor["UserId"],
                revision=body.revision + 1,
            )
        return result

    def audit_log(self, authority, *, after=0, limit=50):
        with transaction(self.settings, anonymous=True) as c:
            authorize(c, self.settings, authority, "audit.read")
            result = rows(
                c,
                (
                    "SELECT TOP(?) EventId,ActorId,Action,R"
                    "esourceRef,Outcome,Metadata,OccurredAt"
                    " FROM crm_access.Audit WHERE Instituti"
                    "onId=? AND EventId>? ORDER BY EventId"
                ),
                min(max(limit, 1), 100),
                institution(self.settings),
                after,
            )
        return {
            "items": [
                {
                    "id": v["EventId"],
                    "actor_id": uid(str(v["ActorId"])) if v["ActorId"] else None,
                    "action": v["Action"],
                    "resource": v["ResourceRef"],
                    "outcome": v["Outcome"],
                    "metadata": json.loads(v["Metadata"]),
                    "occurred_at": utc(v["OccurredAt"]),
                }
                for v in result
            ],
            "next": result[-1]["EventId"] if len(result) == limit else None,
        }
