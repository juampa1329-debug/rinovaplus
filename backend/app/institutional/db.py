"""Small shared SQL helpers; all dynamic identities remain parameters."""

import base64
import hashlib
import hmac
import json
from datetime import timezone
from uuid import UUID, uuid4

from fastapi import HTTPException

from app.institutional.crypto import canonical, request_digest, seal, unseal


def institution(settings):
    return str(UUID(settings.ticket["context"][0][1]))


def utc(value):
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def uid(value):
    try:
        return str(UUID(value))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(422, "invalid_identifier") from None


def one(cursor, text, *params):
    cursor.execute(text, *params)
    fields = [c[0] for c in cursor.description]
    value = cursor.fetchone()
    return dict(zip(fields, value, strict=True)) if value is not None else None


def rows(cursor, text, *params):
    cursor.execute(text, *params)
    fields = [c[0] for c in cursor.description]
    return [dict(zip(fields, r, strict=True)) for r in cursor.fetchall()]


def key(settings):
    return base64.b64decode(settings.review["secrets_key"], validate=True)


def bound_hash(settings, value, purpose):
    context = {
        "database": settings.connection["database"],
        "institution": institution(settings),
        "purpose": purpose,
        "value": value,
    }
    return request_digest(settings.review["session_token"].encode(), context)


def csrf_token(settings, value):
    return bound_hash(settings, value, "csrf").hex()


def audit(cursor, settings, actor, action, resource="", outcome="accepted", **metadata):
    allowed = {
        "revision",
        "section",
        "fields",
        "count",
        "reason",
        "role",
        "scope",
        "kind",
        "version",
    }
    if set(metadata) - allowed:
        raise ValueError("invalid_audit_metadata")
    cursor.execute(
        "INSERT crm_access.Audit(InstitutionId,ActorId,Action,ResourceRef,Outcome,Metadata) VALUES(?,?,?,?,?,?)",
        institution(settings),
        actor,
        action,
        resource,
        outcome,
        canonical(metadata).decode(),
    )


def public_user(value):
    return {
        "id": uid(str(value["UserId"])),
        "email": value["Login"],
        "full_name": value["DisplayName"],
        "role": value["RoleKey"],
        "active": bool(value["Active"]),
        "revision": value["Revision"],
        "profile": json.loads(value["Profile"]),
        "employee_link": "not_bound",
        "account_kind": "human",
    }


def save_secret(cursor, settings, scope, owner, kind, value):
    inst = institution(settings)
    current = cursor.execute(
        "SELECT ISNULL(MAX(VersionNo),0) FROM crm_access.Secret WITH(UPDLOCK,HOLDLOCK) WHERE InstitutionId=? AND Scope=? AND OwnerRef=? AND Kind=?",
        inst,
        scope,
        owner,
        kind,
    ).fetchval()
    version, identity = int(current) + 1, str(uuid4())
    binding = {
        "institution": inst,
        "scope": scope,
        "owner": owner,
        "kind": kind,
        "version": version,
        "secret_id": identity,
    }
    secret_key = key(settings)
    nonce, ciphertext = seal(secret_key, binding, value)
    cursor.execute(
        "UPDATE crm_access.Secret SET State='retired' WHERE InstitutionId=? AND Scope=? AND OwnerRef=? AND Kind=? AND State='staged'",
        inst,
        scope,
        owner,
        kind,
    )
    hint = "" if scope == "totp" else "••••" + value[-4:]
    cursor.execute(
        "INSERT crm_access.Secret(InstitutionId,SecretId,Scope,OwnerRef,Kind,VersionNo,KeyId,Nonce,Ciphertext,Hint,State,CreatedAt) VALUES(?,?,?,?,?,?,?,?,?,?,'staged',SYSUTCDATETIME())",
        inst,
        identity,
        scope,
        owner,
        kind,
        version,
        hashlib.sha256(secret_key).hexdigest()[:32],
        nonce,
        ciphertext,
        hint,
    )
    return {"id": identity, "version": version, "hint": hint, "state": "staged"}


def read_factor_secret(cursor, settings, identity, user):
    value = one(
        cursor,
        "SELECT * FROM crm_access.Secret WHERE InstitutionId=? AND SecretId=? AND Scope='totp' AND OwnerRef=? AND Kind='totp'",
        institution(settings),
        identity,
        user,
    )
    if not value:
        raise HTTPException(503, "security_material_unavailable")
    secret_key = key(settings)
    if not hmac.compare_digest(
        value["KeyId"], hashlib.sha256(secret_key).hexdigest()[:32]
    ):
        raise HTTPException(503, "security_material_unavailable")
    binding = {
        "institution": institution(settings),
        "scope": "totp",
        "owner": user,
        "kind": "totp",
        "version": value["VersionNo"],
        "secret_id": uid(str(value["SecretId"])),
    }
    try:
        return unseal(secret_key, binding, value["Nonce"], value["Ciphertext"])
    except Exception:
        raise HTTPException(503, "security_material_unavailable") from None


def replay(cursor, settings, actor, operation, action, resource, payload):
    operation = uid(operation)
    digest = request_digest(
        key(settings),
        {"actor": actor, "action": action, "resource": resource, "payload": payload},
    )
    prior = one(
        cursor,
        "SELECT ActorId,Action,ResourceRef,PayloadHash,Result FROM crm_access.Operation WITH(UPDLOCK,HOLDLOCK) WHERE InstitutionId=? AND OperationId=?",
        institution(settings),
        operation,
    )
    if prior:
        if (
            uid(str(prior["ActorId"])) != actor
            or prior["Action"] != action
            or prior["ResourceRef"] != resource
            or not hmac.compare_digest(bytes(prior["PayloadHash"]), digest)
        ):
            raise HTTPException(409, "operation_conflict")
        return digest, json.loads(prior["Result"])
    return digest, None


def record_operation(
    cursor, settings, actor, operation, action, resource, digest, result
):
    cursor.execute(
        "INSERT crm_access.Operation(InstitutionId,OperationId,ActorId,Action,ResourceRef,PayloadHash,Result,CreatedAt) VALUES(?,?,?,?,?,?,?,SYSUTCDATETIME())",
        institution(settings),
        uid(operation),
        actor,
        action,
        resource,
        digest,
        canonical(result).decode(),
    )
