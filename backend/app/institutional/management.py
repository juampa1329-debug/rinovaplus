"""Institution user administration and self-service security, with atomic audit."""

import json
from urllib.parse import quote, urlencode
from uuid import uuid4

from fastapi import HTTPException

from app.institutional.auth import Identity, authorize, factor_code, rate, user
from app.institutional.crypto import (
    matching_step,
    password_hash,
    recovery_codes,
    token,
    token_hash,
    totp_secret,
)
from app.institutional.db import (
    audit,
    bound_hash,
    institution,
    one,
    public_user,
    read_factor_secret,
    record_operation,
    replay,
    rows,
    save_secret,
    uid,
    utc,
)
from app.institutional.policy import ACTIONS
from app.institutional.store import transaction


def revoke_user(cursor, settings, identity, *, keep=None):
    cursor.execute(
        "UPDATE crm_access.AccessUser SET AuthVersion=AuthVersion+1 WHERE InstitutionId=? AND UserId=?",
        institution(settings),
        identity,
    )
    text = "UPDATE crm_access.Session SET RevokedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND UserId=? AND RevokedAt IS NULL"
    cursor.execute(
        text + (" AND SessionId<>?" if keep else ""),
        *(institution(settings), identity, keep)
        if keep
        else (institution(settings), identity),
    )
    if keep:
        cursor.execute(
            "UPDATE s SET s.AuthVersion=u.AuthVersion FROM crm_access.Session s JOIN crm_access.AccessUser u ON u.InstitutionId=s.InstitutionId AND u.UserId=s.UserId WHERE s.InstitutionId=? AND s.SessionId=?",
            institution(settings),
            keep,
        )


def assigned_role(cursor, settings, actor, key):
    value = one(
        cursor,
        "SELECT * FROM crm_access.Role WHERE InstitutionId=? AND RoleKey=? AND Active=1",
        institution(settings),
        key,
    )
    if not value:
        raise HTTPException(422, "invalid_role")
    if key == "owner" and actor["RoleKey"] != "owner":
        raise HTTPException(403, "owner_required")
    if not set(json.loads(value["Actions"])) <= set(json.loads(actor["Actions"])):
        raise HTTPException(403, "delegation_exceeds_authority")
    return value


def manageable(cursor, settings, actor, target):
    if target["RoleKey"] == "owner" and actor["RoleKey"] != "owner":
        raise HTTPException(403, "owner_required")
    actions = cursor.execute(
        "SELECT Actions FROM crm_access.Role WHERE InstitutionId=? AND RoleKey=?",
        institution(settings),
        target["RoleKey"],
    ).fetchval()
    if actions is None or not set(json.loads(actions)) <= set(
        json.loads(actor["Actions"])
    ):
        raise HTTPException(403, "delegation_exceeds_authority")


def challenge(cursor, settings, identity, kind):
    cursor.execute(
        "UPDATE crm_access.Challenge SET ConsumedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND UserId=? AND Kind IN('invite','reset') AND ConsumedAt IS NULL",
        institution(settings),
        identity,
    )
    raw = token()
    version = cursor.execute(
        "SELECT AuthVersion FROM crm_access.AccessUser WHERE InstitutionId=? AND UserId=?",
        institution(settings),
        identity,
    ).fetchval()
    cursor.execute(
        "INSERT crm_access.Challenge(InstitutionId,ChallengeId,UserId,TokenHash,Kind,AuthVersion,Attempts,ExpiresAt) VALUES(?,?,?,?,?,?,0,DATEADD(hour,1,SYSUTCDATETIME()))",
        institution(settings),
        str(uuid4()),
        identity,
        bound_hash(settings, raw, "redeem"),
        kind,
        version,
    )
    return raw


class Management:
    def __init__(self, settings):
        self.settings = settings

    def users(self, authority, *, after="", limit=50):
        after = uid(after) if after else "00000000-0000-0000-0000-000000000000"
        with transaction(self.settings, anonymous=True) as c:
            authorize(c, self.settings, authority, "users.read")
            result = rows(
                c,
                "SELECT TOP(?) * FROM crm_access.AccessUser WHERE InstitutionId=? AND UserId>? ORDER BY UserId",
                min(max(limit, 1), 100),
                institution(self.settings),
                after,
            )
        return {
            "items": [public_user(v) for v in result],
            "next": uid(str(result[-1]["UserId"])) if len(result) == limit else None,
        }

    def create_user(self, authority, body):
        resource = (
            "login:" + bound_hash(self.settings, body.email, "user-resource").hex()
        )
        payload = body.model_dump(mode="json")
        payload["password"] = (
            body.password.get_secret_value() if body.password else None
        )
        with transaction(self.settings, True, anonymous=True) as c:
            actor = authorize(c, self.settings, authority, "users.manage", recent=True)
            digest, prior = replay(
                c,
                self.settings,
                actor["UserId"],
                body.operation_id,
                "users.create",
                resource,
                payload,
            )
            if prior:
                return prior
            assigned_role(c, self.settings, actor, body.role)
            if c.execute(
                "SELECT 1 FROM crm_access.AccessUser WHERE InstitutionId=? AND NormalizedLogin=?",
                institution(self.settings),
                body.email,
            ).fetchone():
                raise HTTPException(409, "email_already_registered")
            encoded = (
                password_hash(body.password.get_secret_value())
                if body.password
                else None
            )
            identity = str(uuid4())
            profile = {
                "full_name": body.full_name,
                "phone": "",
                "role_label": "",
                "avatar_url": "",
                "timezone": "America/Bogota",
            }
            c.execute(
                "INSERT crm_access.AccessUser(InstitutionId,UserId,Login,NormalizedLogin,DisplayName,Profile,PasswordHash,RoleKey,Active,AuthVersion,Revision) VALUES(?,?,?,?,?,?,?,?,1,1,1)",
                institution(self.settings),
                identity,
                body.email,
                body.email,
                body.full_name,
                json.dumps(profile),
                encoded,
                body.role,
            )
            result = {"user": public_user(user(c, self.settings, identity))}
            record_operation(
                c,
                self.settings,
                actor["UserId"],
                body.operation_id,
                "users.create",
                resource,
                digest,
                result,
            )
            raw = (
                challenge(c, self.settings, identity, "invite")
                if encoded is None
                else None
            )
            audit(
                c,
                self.settings,
                actor["UserId"],
                "users.create",
                identity,
                role=body.role,
            )
            if raw:
                result = {**result, "activation_token": raw}
        return result

    def edit_user(self, authority, identity, body):
        identity = uid(identity)
        with transaction(self.settings, True, anonymous=True) as c:
            actor = authorize(c, self.settings, authority, "users.manage", recent=True)
            digest, prior = replay(
                c,
                self.settings,
                actor["UserId"],
                body.operation_id,
                "users.edit",
                identity,
                body.model_dump(mode="json"),
            )
            if prior:
                return prior
            current = one(
                c,
                "SELECT * FROM crm_access.AccessUser WITH(UPDLOCK,HOLDLOCK) WHERE InstitutionId=? AND UserId=?",
                institution(self.settings),
                identity,
            )
            if not current:
                raise HTTPException(404, "user_not_found")
            manageable(c, self.settings, actor, current)
            if current["Revision"] != body.revision:
                raise HTTPException(409, "revision_conflict")
            if current["RoleKey"] == "owner" and actor["RoleKey"] != "owner":
                raise HTTPException(403, "owner_required")
            assigned_role(c, self.settings, actor, body.role)
            if (
                current["Active"]
                and current["PasswordHash"] is not None
                and current["RoleKey"] == "owner"
                and (not body.active or body.role != "owner")
            ):
                owners = c.execute(
                    "SELECT COUNT(*) FROM crm_access.AccessUser WITH(UPDLOCK,HOLDLOCK) WHERE InstitutionId=? AND Active=1 AND PasswordHash IS NOT NULL AND RoleKey='owner'",
                    institution(self.settings),
                ).fetchval()
                if owners <= 1:
                    raise HTTPException(409, "last_owner_required")
            if (
                current["Active"]
                and current["PasswordHash"] is not None
                and current["RoleKey"] in {"owner", "admin"}
                and (not body.active or body.role not in {"owner", "admin"})
            ):
                count = c.execute(
                    "SELECT COUNT(*) FROM crm_access.AccessUser WITH(UPDLOCK,HOLDLOCK) WHERE InstitutionId=? AND Active=1 AND PasswordHash IS NOT NULL AND RoleKey IN('owner','admin')",
                    institution(self.settings),
                ).fetchval()
                if count <= 1:
                    raise HTTPException(409, "last_administrator_required")
            profile = json.loads(current["Profile"])
            if (
                current["RoleKey"] == "owner"
                and current["Active"]
                and current["PasswordHash"] is not None
                and (not body.active or body.role != "owner")
            ):
                owners = c.execute(
                    "SELECT COUNT(*) FROM crm_access.AccessUser WITH(UPDLOCK,HOLDLOCK) WHERE InstitutionId=? AND Active=1 AND PasswordHash IS NOT NULL AND RoleKey='owner'",
                    institution(self.settings),
                ).fetchval()
                if owners <= 1:
                    raise HTTPException(409, "last_owner_required")
            profile["full_name"] = body.full_name
            c.execute(
                "UPDATE crm_access.AccessUser SET DisplayName=?,Profile=?,RoleKey=?,Active=?,Revision=Revision+1,UpdatedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND UserId=? AND Revision=?",
                body.full_name,
                json.dumps(profile),
                body.role,
                int(body.active),
                institution(self.settings),
                identity,
                body.revision,
            )
            if c.rowcount != 1:
                raise HTTPException(409, "revision_conflict")
            revoke_user(c, self.settings, identity)
            result = {
                "user": public_user(
                    one(
                        c,
                        "SELECT * FROM crm_access.AccessUser WHERE InstitutionId=? AND UserId=?",
                        institution(self.settings),
                        identity,
                    )
                )
            }
            record_operation(
                c,
                self.settings,
                actor["UserId"],
                body.operation_id,
                "users.edit",
                identity,
                digest,
                result,
            )
            audit(
                c,
                self.settings,
                actor["UserId"],
                "users.edit",
                identity,
                role=body.role,
                revision=body.revision + 1,
            )
        return result

    def roles(self, authority):
        with transaction(self.settings, anonymous=True) as c:
            authorize(c, self.settings, authority, "roles.read")
            items = rows(
                c,
                "SELECT RoleKey,Name,Actions,Protected,Active,Revision FROM crm_access.Role WHERE InstitutionId=? ORDER BY RoleKey",
                institution(self.settings),
            )
        return {
            "items": [
                {
                    "key": v["RoleKey"],
                    "name": v["Name"],
                    "actions": json.loads(v["Actions"]),
                    "protected": bool(v["Protected"]),
                    "active": bool(v["Active"]),
                    "revision": v["Revision"],
                }
                for v in items
            ],
            "available_actions": list(ACTIONS),
        }

    def save_role(self, authority, role, body):
        import re

        if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", role):
            raise HTTPException(422, "invalid_role")
        with transaction(self.settings, True, anonymous=True) as c:
            actor = authorize(c, self.settings, authority, "roles.manage", recent=True)
            digest, prior = replay(
                c,
                self.settings,
                actor["UserId"],
                body.operation_id,
                "roles.edit",
                role,
                body.model_dump(mode="json"),
            )
            if prior:
                return prior
            current = one(
                c,
                "SELECT * FROM crm_access.Role WITH(UPDLOCK,HOLDLOCK) WHERE InstitutionId=? AND RoleKey=?",
                institution(self.settings),
                role,
            )
            if current and current["Protected"]:
                raise HTTPException(409, "protected_role")
            if current and not set(json.loads(current["Actions"])) <= set(
                json.loads(actor["Actions"])
            ):
                raise HTTPException(403, "delegation_exceeds_authority")
            if not set(body.actions) <= set(json.loads(actor["Actions"])):
                raise HTTPException(403, "delegation_exceeds_authority")
            if (current["Revision"] if current else 0) != body.revision:
                raise HTTPException(409, "revision_conflict")
            if current:
                c.execute(
                    "UPDATE crm_access.Role SET Name=?,Actions=?,Active=?,Revision=Revision+1 WHERE InstitutionId=? AND RoleKey=?",
                    body.name,
                    json.dumps(body.actions),
                    int(body.active),
                    institution(self.settings),
                    role,
                )
                c.execute(
                    "UPDATE u SET AuthVersion=AuthVersion+1 FROM crm_access.AccessUser u WHERE InstitutionId=? AND RoleKey=?",
                    institution(self.settings),
                    role,
                )
                c.execute(
                    "UPDATE s SET RevokedAt=SYSUTCDATETIME() FROM crm_access.Session s JOIN crm_access.AccessUser u ON s.InstitutionId=u.InstitutionId AND s.UserId=u.UserId WHERE s.InstitutionId=? AND u.RoleKey=? AND s.RevokedAt IS NULL",
                    institution(self.settings),
                    role,
                )
            else:
                c.execute(
                    "INSERT crm_access.Role(InstitutionId,RoleKey,Name,Actions,Protected,Active,Revision) VALUES(?,?,?,?,0,?,1)",
                    institution(self.settings),
                    role,
                    body.name,
                    json.dumps(body.actions),
                    int(body.active),
                )
            result = {"key": role, "revision": body.revision + 1}
            record_operation(
                c,
                self.settings,
                actor["UserId"],
                body.operation_id,
                "roles.edit",
                role,
                digest,
                result,
            )
            audit(
                c,
                self.settings,
                actor["UserId"],
                "roles.edit",
                role,
                revision=body.revision + 1,
            )
        return result

    def sessions(self, authority):
        with transaction(self.settings, anonymous=True) as c:
            actor = authorize(c, self.settings, authority)
            all_users = "sessions.manage" in json.loads(actor["Actions"])
            items = rows(
                c,
                "SELECT TOP(100) SessionId,UserId,IssuedAt,ExpiresAt,RevokedAt FROM crm_access.Session WHERE InstitutionId=? AND (?=1 OR UserId=?) ORDER BY IssuedAt DESC",
                institution(self.settings),
                int(all_users),
                actor["UserId"],
            )
        return {
            "items": [
                {
                    "id": uid(str(v["SessionId"])),
                    "user_id": uid(str(v["UserId"])),
                    "issued_at": utc(v["IssuedAt"]),
                    "expires_at": utc(v["ExpiresAt"]),
                    "revoked": v["RevokedAt"] is not None,
                    "current": uid(str(v["SessionId"])) == actor["SessionId"],
                }
                for v in items
            ]
        }

    def revoke_session(self, authority, identity):
        identity = uid(identity)
        with transaction(self.settings, True, anonymous=True) as c:
            actor = authorize(c, self.settings, authority)
            target = one(
                c,
                "SELECT UserId FROM crm_access.Session WHERE InstitutionId=? AND SessionId=?",
                institution(self.settings),
                identity,
            )
            if not target:
                raise HTTPException(404, "session_not_found")
            if uid(str(target["UserId"])) != actor["UserId"]:
                authorize(c, self.settings, authority, "sessions.manage", recent=True)
                target_user = one(
                    c,
                    "SELECT RoleKey FROM crm_access.AccessUser WHERE InstitutionId=? AND UserId=?",
                    institution(self.settings),
                    target["UserId"],
                )
                manageable(c, self.settings, actor, target_user)
            c.execute(
                "UPDATE crm_access.Session SET RevokedAt=ISNULL(RevokedAt,SYSUTCDATETIME()) WHERE InstitutionId=? AND SessionId=?",
                institution(self.settings),
                identity,
            )
            audit(c, self.settings, actor["UserId"], "sessions.revoke", identity)
        return {"revoked": True, "current": identity == actor["SessionId"]}

    def password(self, authority, body):
        Identity(self.settings).reauthenticate(authority, body)
        encoded = password_hash(body.new_password.get_secret_value())
        with transaction(self.settings, True, anonymous=True) as c:
            actor = authorize(c, self.settings, authority, recent=True)
            c.execute(
                "UPDATE crm_access.AccessUser SET PasswordHash=?,Revision=Revision+1,UpdatedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND UserId=?",
                encoded,
                institution(self.settings),
                actor["UserId"],
            )
            revoke_user(c, self.settings, actor["UserId"])
            c.execute(
                "UPDATE crm_access.Challenge SET ConsumedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND UserId=? AND ConsumedAt IS NULL",
                institution(self.settings),
                actor["UserId"],
            )
            audit(
                c,
                self.settings,
                actor["UserId"],
                "auth.password_changed",
                actor["UserId"],
            )
        return {"changed": True, "signed_out": True}

    def factor_setup(self, authority, body):
        Identity(self.settings).reauthenticate(authority, body)
        with transaction(self.settings, True, anonymous=True) as c:
            actor = authorize(c, self.settings, authority, recent=True)
            secret = totp_secret()
            saved = save_secret(
                c, self.settings, "totp", actor["UserId"], "totp", secret
            )
            setup = str(uuid4())
            current = c.execute(
                "SELECT 1 FROM crm_access.Factor WHERE InstitutionId=? AND UserId=?",
                institution(self.settings),
                actor["UserId"],
            ).fetchone()
            if current:
                c.execute(
                    "UPDATE crm_access.Factor SET PendingSecretId=?,SetupId=?,SetupSessionId=?,SetupAttempts=0,SetupExpiresAt=DATEADD(minute,10,SYSUTCDATETIME()) WHERE InstitutionId=? AND UserId=?",
                    saved["id"],
                    setup,
                    actor["SessionId"],
                    institution(self.settings),
                    actor["UserId"],
                )
            else:
                c.execute(
                    "INSERT crm_access.Factor(InstitutionId,UserId,PendingSecretId,State,LastStep,SetupId,SetupSessionId,SetupExpiresAt) VALUES(?,?,?,'disabled',-1,?,?,DATEADD(minute,10,SYSUTCDATETIME()))",
                    institution(self.settings),
                    actor["UserId"],
                    saved["id"],
                    setup,
                    actor["SessionId"],
                )
            audit(c, self.settings, actor["UserId"], "auth.totp_setup", actor["UserId"])
            uri = (
                "otpauth://totp/"
                + quote("CRM CBN:" + actor["Login"], safe="")
                + "?"
                + urlencode(
                    {
                        "secret": secret,
                        "issuer": "CRM CBN",
                        "algorithm": "SHA1",
                        "digits": 6,
                        "period": 30,
                    }
                )
            )
        return {"setup_id": setup, "secret": secret, "otpauth_uri": uri}

    def factor_verify(self, authority, body):
        with transaction(self.settings, True, anonymous=True) as c:
            actor = authorize(c, self.settings, authority, recent=True)
            pending = one(
                c,
                "SELECT * FROM crm_access.Factor WITH(UPDLOCK,HOLDLOCK) WHERE InstitutionId=? AND UserId=? AND SetupId=? AND SetupSessionId=? AND SetupExpiresAt>SYSUTCDATETIME() AND PendingSecretId IS NOT NULL AND SetupAttempts<8",
                institution(self.settings),
                actor["UserId"],
                uid(body.setup_id),
                actor["SessionId"],
            )
            step = None
            if pending:
                c.execute(
                    "UPDATE crm_access.Factor SET SetupAttempts=SetupAttempts+1 WHERE InstitutionId=? AND UserId=?",
                    institution(self.settings),
                    actor["UserId"],
                )
                secret = read_factor_secret(
                    c, self.settings, pending["PendingSecretId"], actor["UserId"]
                )
                now = c.execute(
                    "SELECT DATEDIFF_BIG(second,CONVERT(datetime2,'19700101'),SYSUTCDATETIME())"
                ).fetchval()
                step = matching_step(
                    secret,
                    body.code.get_secret_value(),
                    last=self.settings.ticket.get("mfa_floor", -1),
                    now=now,
                )
            codes = None
            if step is not None:
                c.execute(
                    "UPDATE crm_access.Factor SET SecretId=PendingSecretId,PendingSecretId=NULL,State='enabled',LastStep=?,SetupId=NULL,SetupSessionId=NULL,SetupExpiresAt=NULL WHERE InstitutionId=? AND UserId=?",
                    step,
                    institution(self.settings),
                    actor["UserId"],
                )
                codes = recovery_codes()
                c.execute(
                    "UPDATE crm_access.RecoveryCode SET ConsumedAt=ISNULL(ConsumedAt,SYSUTCDATETIME()) WHERE InstitutionId=? AND UserId=?",
                    institution(self.settings),
                    actor["UserId"],
                )
                for code in codes:
                    c.execute(
                        "INSERT crm_access.RecoveryCode(InstitutionId,UserId,CodeHash) VALUES(?,?,?)",
                        institution(self.settings),
                        actor["UserId"],
                        token_hash(code),
                    )
                revoke_user(c, self.settings, actor["UserId"], keep=actor["SessionId"])
                c.execute(
                    "UPDATE crm_access.Session SET MFAAt=SYSUTCDATETIME(),RecentAt=SYSUTCDATETIME() WHERE InstitutionId=? AND SessionId=?",
                    institution(self.settings),
                    actor["SessionId"],
                )
                audit(
                    c,
                    self.settings,
                    actor["UserId"],
                    "auth.totp_enabled",
                    actor["UserId"],
                    count=8,
                )
            else:
                audit(
                    c,
                    self.settings,
                    actor["UserId"],
                    "auth.totp_setup_failed",
                    actor["UserId"],
                    outcome="denied",
                )
        if codes is None:
            raise HTTPException(401, "invalid_setup_or_code")
        return {"enabled": True, "recovery_codes": codes}

    def factor_disable(self, authority, body):
        Identity(self.settings).reauthenticate(authority, body)
        with transaction(self.settings, True, anonymous=True) as c:
            actor = authorize(c, self.settings, authority, recent=True)
            c.execute(
                "UPDATE crm_access.Factor SET State='disabled',PendingSecretId=NULL,SetupId=NULL,SetupSessionId=NULL,SetupExpiresAt=NULL WHERE InstitutionId=? AND UserId=?",
                institution(self.settings),
                actor["UserId"],
            )
            c.execute(
                "UPDATE crm_access.RecoveryCode SET ConsumedAt=ISNULL(ConsumedAt,SYSUTCDATETIME()) WHERE InstitutionId=? AND UserId=?",
                institution(self.settings),
                actor["UserId"],
            )
            revoke_user(c, self.settings, actor["UserId"], keep=actor["SessionId"])
            audit(
                c, self.settings, actor["UserId"], "auth.totp_disabled", actor["UserId"]
            )
        return {"enabled": False}

    def issue_reset(self, authority, identity):
        identity = uid(identity)
        with transaction(self.settings, True, anonymous=True) as c:
            actor = authorize(c, self.settings, authority, "users.manage", recent=True)
            target = user(c, self.settings, identity)
            if not target:
                raise HTTPException(404, "user_not_found")
            manageable(c, self.settings, actor, target)
            if target["RoleKey"] == "owner" and actor["RoleKey"] != "owner":
                raise HTTPException(403, "owner_required")
            raw = challenge(c, self.settings, identity, "reset")
            audit(c, self.settings, actor["UserId"], "auth.reset_issued", identity)
        return {"reset_token": raw, "expires_in_seconds": 3600}

    def redeem(self, body):
        with transaction(self.settings, True, anonymous=True) as c:
            allowed = rate(c, self.settings, "redeem-global", 60, 60)
            value = one(
                c,
                "SELECT * FROM crm_access.Challenge WITH(UPDLOCK,HOLDLOCK) WHERE InstitutionId=? AND TokenHash=? AND Kind IN('invite','reset') AND ConsumedAt IS NULL AND Attempts<8 AND ExpiresAt>SYSUTCDATETIME()",
                institution(self.settings),
                bound_hash(self.settings, body.token.get_secret_value(), "redeem"),
            )
            accepted = False
            if allowed and value:
                identity = uid(str(value["UserId"]))
                target = user(c, self.settings, identity)
                c.execute(
                    "UPDATE crm_access.Challenge SET Attempts=Attempts+1 WHERE InstitutionId=? AND ChallengeId=?",
                    institution(self.settings),
                    value["ChallengeId"],
                )
                enabled = c.execute(
                    "SELECT COUNT(*) FROM crm_access.Factor WHERE InstitutionId=? AND UserId=? AND State='enabled'",
                    institution(self.settings),
                    identity,
                ).fetchval()
                if (
                    target
                    and value["AuthVersion"] == target["AuthVersion"]
                    and (
                        not enabled
                        or body.code
                        and factor_code(
                            c, self.settings, identity, body.code.get_secret_value()
                        )
                    )
                ):
                    encoded = password_hash(body.new_password.get_secret_value())
                    c.execute(
                        "UPDATE crm_access.AccessUser SET PasswordHash=?,Revision=Revision+1,UpdatedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND UserId=?",
                        encoded,
                        institution(self.settings),
                        identity,
                    )
                    c.execute(
                        "UPDATE crm_access.Challenge SET ConsumedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND UserId=? AND ConsumedAt IS NULL",
                        institution(self.settings),
                        identity,
                    )
                    revoke_user(c, self.settings, identity)
                    audit(c, self.settings, identity, "auth.access_redeemed", identity)
                    accepted = True
            if not accepted:
                audit(
                    c, self.settings, None, "auth.redemption_failed", outcome="denied"
                )
        if not accepted:
            raise HTTPException(401, "invalid_token_or_code")
        return {"activated": True}
