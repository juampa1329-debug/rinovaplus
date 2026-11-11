"""Pure account identities, canonical digests and SQL authority for C12."""

import hashlib
import json
import re
import uuid

TARGET = re.compile(r"CBN_C12_(TRIAL|FAULT)_20261025_([0-9a-f]{8})\Z")
VERSION = "cbn-parity-repositories-c12-v1"
PREFIX = "cbn_parity_runtime_c12_"
IMPORTER = "cbn_parity_importer_c12"
SCHEMA = "crm_channels2"
DENIED = ("SELECT", "INSERT", "UPDATE", "DELETE", "ALTER", "REFERENCES", "EXECUTE")
RIGHTS = {
    "crm_channels2.Context": ("SELECT",),
    "crm_channels2.Application": ("SELECT", "INSERT", "UPDATE"),
    "crm_channels2.Integration": ("SELECT", "INSERT", "UPDATE"),
    "crm_channels2.Audit": ("SELECT", "INSERT"),
    "crm_channels2.ProviderOperation": ("SELECT", "INSERT", "UPDATE"),
    "crm_channels2.WebhookEndpoint": ("SELECT",),
    "crm_channels2.EndpointIntegration": ("SELECT",),
    "crm_channels2.ExternalIdentity": ("SELECT",),
    "crm_channels2.SocialComment": ("SELECT",),
    "crm_meta.MigrationJournal": ("SELECT",),
    "sys.sql_expression_dependencies": ("SELECT",),
}
COLUMNS = {
    "crm_channels2.SecretVersion": (
        "InstitutionId",
        "SecretId",
        "ApplicationId",
        "IntegrationId",
        "EndpointId",
        "Kind",
        "VersionNo",
        "State",
        "Hint",
        "ExpiresAt",
    ),
    "crm_channels2.WebhookReceipt": (
        "InstitutionId",
        "ReceiptId",
        "EndpointId",
        "ApplicationId",
        "Authentication",
        "Status",
        "ReceivedAt",
        "Attempts",
        "LastErrorCode",
        "BodyPurgedAt",
    ),
    "crm_channels2.WebhookEvent": (
        "InstitutionId",
        "EventId",
        "IntegrationId",
        "EndpointId",
        "Kind",
        "Status",
        "IdentityStrength",
        "CreatedAt",
    ),
    "crm_channels2.ExternalMessage": (
        "InstitutionId",
        "ExternalMessageId",
        "IntegrationId",
        "ExternalId",
        "MessageId",
        "CreatedAt",
    ),
    "crm_channels2.SendJob": (
        "InstitutionId",
        "QueueId",
        "IntegrationId",
        "Kind",
        "State",
        "Attempts",
        "LastErrorCode",
        "CreatedAt",
    ),
    "crm_channels2.LegacyBinding": (
        "InstitutionId",
        "BindingId",
        "LegacyTable",
        "SourceRowSha256",
        "TargetRowSha256",
        "MigrationUnit",
    ),
}


def require(value, code):
    if not value:
        raise ValueError(code)


def canonical(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def principal(database):
    match = TARGET.fullmatch(database)
    require(match is not None, "C12_isolated_target")
    return PREFIX + match[2]


def identifier(value, limit=200):
    require(
        isinstance(value, str)
        and 0 < len(value) <= limit
        and value == value.strip()
        and not any(ord(c) < 32 or ord(c) == 127 for c in value),
        "C12_external_identity",
    )
    return value


def namespace(provider, client_id, issuer):
    scope = (
        ["meta_global_v1"]
        if provider == "meta"
        else ["tiktok_app_v1", identifier(client_id, 128), identifier(issuer, 40)]
    )
    return hashlib.sha256(canonical(scope)).digest()


def secret_aad(institution, owner, owner_id, kind, version, key_version):
    require(
        owner in {"Application", "Integration", "WebhookEndpoint"},
        "C12_canonical_secret_owner",
    )
    return canonical(
        [
            "cbn.channels.v2",
            str(uuid.UUID(institution)),
            owner,
            str(uuid.UUID(owner_id)),
            kind,
            version,
            key_version,
        ]
    )
