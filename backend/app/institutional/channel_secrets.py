"""C10 vault: authenticated owner binding and metadata-only reads."""

import hashlib
from uuid import uuid4

from fastapi import HTTPException

from app.institutional.crypto import seal, unseal
from app.institutional.db import institution, key, one, uid

OWNERS = {
    "application": "ApplicationId",
    "integration": "IntegrationId",
    "endpoint": "EndpointId",
    "oauth": "OAuthSessionId",
    "asset": "AssetId",
}
KINDS = {
    "application": {
        "meta_app_secret",
        "instagram_app_secret",
        "facebook_app_secret",
        "tiktok_client_secret",
    },
    "integration": {
        "meta_permanent_access",
        "instagram_user_access",
        "instagram_page_access",
        "facebook_user_access",
        "facebook_page_access",
        "tiktok_access",
        "tiktok_refresh",
    },
    "endpoint": {"webhook_verify", "endpoint_hmac", "tiktok_webhook_secret"},
    "oauth": {
        "oauth_provisional_access",
        "oauth_provisional_refresh",
        "oauth_pkce_verifier",
    },
    "asset": {"oauth_asset_access"},
}


def binding(settings, owner_type, owner, kind, version, identity):
    if kind not in KINDS.get(owner_type, set()):
        raise ValueError("credential_owner_kind")
    return {
        "institution": institution(settings),
        "owner_type": owner_type,
        "owner": uid(owner),
        "kind": kind,
        "version": version,
        "secret_id": uid(identity),
    }


def put(c, settings, owner_type, owner, kind, raw, *, expires=None, state="active"):
    column = OWNERS[owner_type]
    owner = uid(owner)
    if (
        not isinstance(raw, str)
        or not 8 <= len(raw.encode("utf-8")) <= 32768
        or any(ord(char) < 33 or ord(char) > 126 for char in raw)
        or state not in {"active", "staged"}
    ):
        raise HTTPException(422, "invalid_credential_value")
    version = c.execute(
        (
            "SELECT ISNULL(MAX(VersionNo),0)+1 FROM crm_channels2.SecretV"
            "ersion WITH(UPDLOCK,HOLDLOCK) WHERE InstitutionId=? AND "
        )
        + column
        + "=? AND Kind=?",
        institution(settings),
        owner,
        kind,
    ).fetchval()
    identity = str(uuid4())
    nonce, encrypted = seal(
        key(settings),
        binding(settings, owner_type, owner, kind, version, identity),
        raw,
    )
    c.execute(
        (
            "UPDATE crm_channels2.SecretVersion SET State='retired',Revok"
            "edAt=SYSUTCDATETIME() WHERE InstitutionId=? AND "
        )
        + column
        + "=? AND Kind=? AND State IN('active','staged')",
        institution(settings),
        owner,
        kind,
    )
    c.execute(
        "INSERT crm_channels2.SecretVersion(InstitutionId,SecretId,"
        + column
        + (
            ",Kind,VersionNo,State,Nonce,Ciphertext,KeyVersion,Fingerprin"
            "t,Hint,ExpiresAt,CreatedAt) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,S"
            "YSUTCDATETIME())"
        ),
        institution(settings),
        identity,
        owner,
        kind,
        version,
        state,
        nonce,
        encrypted,
        hashlib.sha256(key(settings)).hexdigest()[:32],
        hashlib.sha256(raw.encode()).digest(),
        raw[-4:],
        expires,
    )
    return {"id": identity, "version": version, "configured": True, "verified": False}


def get(c, settings, owner_type, owner, kind, *, identity=None):
    column = OWNERS[owner_type]
    condition, args = (" AND SecretId=?", [uid(identity)]) if identity else ("", [])
    row = one(
        c,
        "SELECT TOP(1) * FROM crm_channels2.SecretVersion WHERE InstitutionId=? AND "
        + column
        + (
            "=? AND Kind=? AND State IN('active','staged') AND (ExpiresAt"
            " IS NULL OR ExpiresAt>SYSUTCDATETIME())"
        )
        + condition
        + " ORDER BY VersionNo DESC",
        institution(settings),
        uid(owner),
        kind,
        *args,
    )
    if not row:
        raise HTTPException(409, "credential_required")
    if row["KeyVersion"] != hashlib.sha256(key(settings)).hexdigest()[:32]:
        raise HTTPException(503, "credential_key_unavailable")
    raw = unseal(
        key(settings),
        binding(
            settings, owner_type, owner, kind, row["VersionNo"], str(row["SecretId"])
        ),
        row["Nonce"],
        row["Ciphertext"],
    )
    return raw, row
