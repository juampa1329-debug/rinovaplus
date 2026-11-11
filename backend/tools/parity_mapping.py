"""C12 atomic B011 import. Source rows and the DDL journal stay immutable."""

import hashlib
import hmac
import json
import os
import uuid
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.channels_profile import load_settings
from app.modules.crm_configuration.application.service import Configuration
from app.parity_channels.policy import (
    canonical,
    identifier,
    namespace,
    require,
    secret_aad,
)
from tools.foundation_snapshot import encode, quote_name

UNIT = "CBN-CHMAP001"
KEYS = {
    "Account": ("Channel",),
    "Credential": ("Channel", "Kind"),
    "webhook_events": ("EventId",),
    "ExternalIdentity": ("IdentityId",),
    "ExternalMessage": ("Channel", "ExternalId"),
    "outbound_queue": ("QueueId",),
    "social_comments": ("CommentId",),
    "Audit": ("Revision",),
}


def account_scope(channel, config):
    require(
        channel in {"whatsapp", "facebook", "messenger", "instagram", "tiktok"},
        "C12_source_channel",
    )
    provider = "tiktok" if channel == "tiktok" else "meta"
    issuer = (
        "tiktok_business"
        if provider == "tiktok"
        else "meta_whatsapp"
        if channel == "whatsapp"
        else "instagram_login"
        if channel == "instagram" and config.get("instagramLogin") == "instagram"
        else "facebook_login"
    )
    return provider, identifier(config.get("appId"), 128), issuer


def stage_binding(document, revision, label):
    config = Configuration.model_validate_json(document)
    if not label:
        return None, None
    matches = [s for s in config.stages if s.active and s.label == label]
    require(len(matches) == 1, "C12_initial_stage_requires_review")
    return matches[0].key, hashlib.sha256(
        canonical({"revision": str(revision), "document": json.loads(document)})
    ).digest()


def new_key(path):
    if path.exists():
        value = path.read_bytes()
        require(len(value) == 32, "C12_key_corrupt")
        return value
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with os.fdopen(
        os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "wb"
    ) as f:
        value = os.urandom(32)
        f.write(value)
        f.flush()
        os.fsync(f.fileno())
    return value


def original_key():
    state = json.loads(Path("/tmp/cbn-c8-ready/state.json").read_text())
    settings = load_settings(Path(state["profile_directory"]))
    value = Path(settings.channels_key_path).read_bytes()
    require(
        len(value) == 32
        and hashlib.sha256(value).hexdigest() == settings.channels_key_sha256,
        "C12_original_key_unverified",
    )
    return value


def rows(cursor, table):
    require(table in KEYS, "C12_source_table")
    columns = cursor.execute(
        (
            "SELECT name,TYPE_NAME(system_type_id) FROM "
            "sys.columns WHERE object_id=OBJECT_ID(?) ORDER BY "
            "column_id"
        ),
        "crm_channels." + table,
    ).fetchall()
    projection = ",".join(
        (
            "CONVERT(varchar(33)," + quote_name(n) + ",126)"
            if t == "datetime2"
            else quote_name(n)
        )
        for n, t in columns
    )
    raw = cursor.execute(
        "SELECT " + projection + " FROM crm_channels." + quote_name(table)
    ).fetchall()
    result = []
    for row in raw:
        data = dict(zip((r[0] for r in columns), row))
        key = {k: str(data[k]) for k in KEYS[table]}
        predicates = " AND ".join(quote_name(k) + "=?" for k in KEYS[table])
        binary = cursor.execute(
            "SELECT "
            + ",".join(
                "CONVERT(varbinary(max)," + quote_name(n) + ")" for n, _ in columns
            )
            + " FROM crm_channels."
            + quote_name(table)
            + " WHERE "
            + predicates,
            *[data[k] for k in KEYS[table]],
        ).fetchone()
        result.append((data, key, hashlib.sha256(encode(list(binary))).digest()))
    return result


def insert(cursor, institution, table, values):
    data = {"InstitutionId": institution, **values}
    cursor.execute(
        "INSERT crm_channels2."
        + quote_name(table)
        + "("
        + ",".join(map(quote_name, data))
        + ") VALUES("
        + ",".join("?" for _ in data)
        + ")",
        *data.values(),
    )


def source_manifest(cursor):
    return {table: rows(cursor, table) for table in KEYS}


def target_hashes(cursor, institution, targets):
    result = []
    for table, pk, value in targets:
        columns = cursor.execute(
            (
                "SELECT name FROM sys.columns WHERE "
                "object_id=OBJECT_ID(?) ORDER BY column_id"
            ),
            "crm_channels2." + table,
        ).fetchall()
        row = cursor.execute(
            "SELECT "
            + ",".join(
                "CONVERT(varbinary(max)," + quote_name(c[0]) + ")" for c in columns
            )
            + " FROM crm_channels2."
            + quote_name(table)
            + " WHERE InstitutionId=? AND "
            + quote_name(pk)
            + "=?",
            institution,
            value,
        ).fetchone()
        require(row is not None, "C12_binding_target_missing")
        result.append(hashlib.sha256(encode(list(row))).hexdigest())
    return result


def import_rows(cursor, work, *, fail_after=None):
    """Caller holds SERIALIZABLE transaction and both schema/local commit locks."""
    institution = str(
        cursor.execute(
            "SELECT InstitutionId FROM crm_channels2.Context WHERE ContextId=1"
        ).fetchval()
    ).lower()
    source = source_manifest(cursor)
    configrow = cursor.execute(
        "SELECT Document,Revision FROM crm_config.Configuration WHERE ConfigurationId=1"
    ).fetchone()
    require(configrow is not None, "C12_B006_configuration_required")
    oldkey = original_key() if source["Credential"] else None
    # A missing key after any binding is a hard failure, never a fresh key.
    existing = cursor.execute(
        "SELECT COUNT(*) FROM crm_channels2.LegacyBinding"
    ).fetchval()
    for path in ("vault.key", "receipt.key"):
        require(not existing or (work / path).exists(), "C12_missing_import_key")
    key, bodykey = new_key(work / "vault.key"), new_key(work / "receipt.key")

    def uid(kind, value):
        return str(
            uuid.uuid5(uuid.UUID(institution), kind + ":" + canonical(value).decode())
        )

    def binding(table, keyjson, digest, integration, targets):
        keyraw = canonical(keyjson)
        binding_id = uid(table, keyjson)
        snapshots = []
        for name, idcol, value in targets:
            cols = cursor.execute(
                (
                    "SELECT name FROM sys.columns WHERE "
                    "object_id=OBJECT_ID(?) ORDER BY column_id"
                ),
                "crm_channels2." + name,
            ).fetchall()
            snapshot = cursor.execute(
                "SELECT "
                + ",".join(
                    "CONVERT(varbinary(max)," + quote_name(c[0]) + ")" for c in cols
                )
                + " FROM crm_channels2."
                + quote_name(name)
                + " WHERE InstitutionId=? AND "
                + quote_name(idcol)
                + "=?",
                institution,
                value,
            ).fetchone()
            require(snapshot is not None, "C12_binding_target_missing")
            snapshots.append(hashlib.sha256(encode(list(snapshot))).hexdigest())
        insert(
            cursor,
            institution,
            "LegacyBinding",
            dict(
                BindingId=binding_id,
                LegacyTable="crm_channels." + table,
                LegacyKeyHash=hashlib.sha256(keyraw).digest(),
                LegacyKeyJson=keyraw.decode(),
                SourceRowSha256=digest,
                IntegrationId=integration,
                TargetKeyJson=canonical(targets).decode(),
                TargetRowSha256=hashlib.sha256(canonical(snapshots)).digest(),
                MigrationUnit=UNIT,
                CreatedAt=now,
            ),
        )

    bound = cursor.execute(
        (
            "SELECT LegacyTable,LegacyKeyJson,SourceRowSha256,M"
            "igrationUnit,TargetKeyJson,LegacyKeyHash,Integrati"
            "onId,TargetRowSha256 FROM "
            "crm_channels2.LegacyBinding WHERE InstitutionId=?"
        ),
        institution,
    ).fetchall()
    expected = {
        ("crm_channels." + t, canonical(k).decode(), bytes(d), UNIT)
        for t, values in source.items()
        for _, k, d in values
    }
    if bound:
        require(
            set((r[0], r[1], bytes(r[2]), r[3]) for r in bound) == expected,
            "C12_import_drift_or_partial",
        )
        permitted = {
            "Application": "ApplicationId",
            "Integration": "IntegrationId",
            "WebhookEndpoint": "EndpointId",
            "SecretVersion": "SecretId",
            "ExternalIdentity": "IdentityId",
            "ExternalMessage": "ExternalMessageId",
            "SocialComment": "CommentId",
            "WebhookReceipt": "ReceiptId",
            "Audit": "AuditId",
            "ProviderOperation": "OperationId",
            "SendJob": "QueueId",
        }
        bykey = {
            (t, canonical(k).decode()): d
            for t, items in source.items()
            for d, k, _ in items
        }
        for row in bound:
            table = row[0].split(".")[1]
            sourcekey = json.loads(row[1])
            data = bykey[(table, row[1])]
            channel = data.get("Channel")
            if table == "webhook_events":
                candidates = [
                    d["Channel"]
                    for d, _, _ in source["Account"]
                    if d["Channel"] == data["Provider"]
                    or account_scope(d["Channel"], json.loads(d["Configuration"]))[0]
                    == data["Provider"]
                ]
                require(len(candidates) == 1, "C12_ambiguous_legacy_receipt")
                channel = candidates[0]
            integration = uid("integration", {"Channel": channel})
            targetsets = {
                "Credential": [["SecretVersion", "SecretId", uid("secret", sourcekey)]],
                "ExternalIdentity": [
                    ["ExternalIdentity", "IdentityId", uid("identity", sourcekey)]
                ],
                "ExternalMessage": [
                    ["ExternalMessage", "ExternalMessageId", uid("message", sourcekey)]
                ],
                "social_comments": [
                    ["SocialComment", "CommentId", uid("comment", sourcekey)]
                ],
                "webhook_events": [
                    ["WebhookReceipt", "ReceiptId", uid("receipt", sourcekey)]
                ],
                "Audit": [["Audit", "AuditId", uid("audit", sourcekey)]],
            }
            if table == "Account":
                provider, client, issuer = account_scope(
                    channel, json.loads(data["Configuration"])
                )
                targetsets[table] = [
                    [
                        "Application",
                        "ApplicationId",
                        uid("application", [provider, client, issuer]),
                    ],
                    ["Integration", "IntegrationId", integration],
                    ["WebhookEndpoint", "EndpointId", uid("endpoint", sourcekey)],
                ]
                account_config = json.loads(data["Configuration"])
                expected_stage, expected_hash = stage_binding(
                    configrow[0], configrow[1], account_config.get("initialStage")
                )
                current = cursor.execute(
                    (
                        "SELECT a.Provider,a.ClientId,a.IssuerProfile,i.Cha"
                        "nnel,i.InitialStageKey,i.InitialStageConfigHash "
                        "FROM crm_channels2.Application a JOIN "
                        "crm_channels2.Integration i ON "
                        "i.InstitutionId=a.InstitutionId AND "
                        "i.ApplicationId=a.ApplicationId WHERE "
                        "i.InstitutionId=? AND i.IntegrationId=?"
                    ),
                    institution,
                    integration,
                ).fetchone()
                require(
                    current is not None
                    and tuple(current[:5])
                    == (provider, client, issuer, channel, expected_stage)
                    and (bytes(current[5]) if current[5] is not None else None)
                    == expected_hash,
                    "C12_immutable_account_binding",
                )
                external = (
                    account_config.get(
                        "phoneNumberId"
                        if channel == "whatsapp"
                        else "pageId"
                        if channel in {"facebook", "messenger"}
                        else "accountId"
                    )
                    or None
                )
                parent = (
                    account_config.get("wabaId")
                    if channel == "whatsapp"
                    else account_config.get("pageId")
                    if channel == "instagram" and issuer == "facebook_login"
                    else None
                ) or None
                immutable = cursor.execute(
                    (
                        "SELECT a.RedirectUri,a.EgressProfile,a.State,i.Env"
                        "ironment,i.ExternalAccountId,i.ParentExternalId,i."
                        "ExternalNamespace,i.DispatchMode,i.RequestedStatus"
                        ",i.VerifiedStatus FROM crm_channels2.Application a"
                        " JOIN crm_channels2.Integration i ON "
                        "i.InstitutionId=a.InstitutionId AND "
                        "i.ApplicationId=a.ApplicationId WHERE "
                        "i.InstitutionId=? AND i.IntegrationId=?"
                    ),
                    institution,
                    integration,
                ).fetchone()
                require(
                    tuple(immutable[:6])
                    == (
                        account_config.get("callbackUrl") or "",
                        "disabled-c12",
                        "draft",
                        account_config.get("environment") or "development",
                        external,
                        parent,
                    )
                    and bytes(immutable[6]) == namespace(provider, client, issuer)
                    and tuple(immutable[7:])
                    == ("disabled", "disconnected", "unverified"),
                    "C12_account_immutable_configuration",
                )
                endpoint = cursor.execute(
                    (
                        "SELECT ApplicationId,Provider,ChannelSelector,Sign"
                        "atureProfile,SignatureRequired,IsActive FROM "
                        "crm_channels2.WebhookEndpoint WHERE "
                        "InstitutionId=? AND EndpointId=?"
                    ),
                    institution,
                    uid("endpoint", sourcekey),
                ).fetchone()
                require(
                    endpoint is not None
                    and str(endpoint[0]).lower() == targetsets[table][0][2]
                    and tuple(endpoint[1:])
                    == (provider, channel, "legacy-review-required", True, False),
                    "C12_endpoint_immutable_configuration",
                )
            elif table == "outbound_queue":
                targetsets[table] = (
                    [["Audit", "AuditId", uid("unroutable-job", sourcekey)]]
                    if data["IdentityId"] is None or data["MessageId"] is None
                    else [
                        [
                            "ProviderOperation",
                            "OperationId",
                            uid("queue-operation", sourcekey),
                        ],
                        ["SendJob", "QueueId", uid("queue", sourcekey)],
                    ]
                )
            require(
                canonical(json.loads(row[4])) == canonical(targetsets[table])
                and str(row[6]).lower() == integration,
                "C12_binding_target_substitution",
            )
            require(
                bytes(row[5]) == hashlib.sha256(row[1].encode()).digest()
                and len(bytes(row[7])) == 32,
                "C12_binding_key_hash",
            )
            require(
                cursor.execute(
                    (
                        "SELECT 1 FROM crm_channels2.Integration WHERE "
                        "InstitutionId=? AND IntegrationId=?"
                    ),
                    institution,
                    row[6],
                ).fetchone(),
                "C12_binding_integration_missing",
            )
            targets = json.loads(row[4])
            for target_table, pk, value in targets:
                require(permitted.get(target_table) == pk, "C12_binding_target_kind")
                require(
                    cursor.execute(
                        "SELECT 1 FROM crm_channels2."
                        + quote_name(target_table)
                        + " WHERE InstitutionId=? AND "
                        + quote_name(pk)
                        + "=?",
                        institution,
                        str(uuid.UUID(value)),
                    ).fetchone(),
                    "C12_binding_target_missing",
                )
            if table != "Account":
                require(
                    hashlib.sha256(
                        canonical(target_hashes(cursor, institution, targets))
                    ).digest()
                    == bytes(row[7]),
                    "C12_immutable_target_content_drift",
                )
            if table == "webhook_events":
                receipt = cursor.execute(
                    (
                        "SELECT EndpointId,Digest,BodyKeyVersion,BodyNonce,"
                        "BodyCiphertext FROM crm_channels2.WebhookReceipt "
                        "WHERE InstitutionId=? AND ReceiptId=?"
                    ),
                    institution,
                    uid("receipt", sourcekey),
                ).fetchone()
                body = data["Payload"].encode()
                digest = hashlib.sha256(body).digest()
                require(
                    bytes(receipt[1]) == digest and receipt[2] == "c12-body-v1",
                    "C12_receipt_body_metadata",
                )
                aad = canonical(
                    [
                        "cbn.receipt.v1",
                        institution,
                        str(receipt[0]).lower(),
                        uid("receipt", sourcekey),
                        digest.hex(),
                        receipt[2],
                    ]
                )
                require(
                    hmac.compare_digest(
                        AESGCM(bodykey).decrypt(
                            bytes(receipt[3]), bytes(receipt[4]), aad
                        ),
                        body,
                    ),
                    "C12_receipt_body_keyring_or_content",
                )
        for data, keyjson, _ in source["Credential"]:
            require(
                data["KeyId"] == hashlib.sha256(oldkey).hexdigest()[:32],
                "C12_credential_key_mismatch",
            )
            original = AESGCM(oldkey).decrypt(
                bytes(data["Nonce"]),
                bytes(data["Ciphertext"]),
                (
                    "crm_channels:" + data["Channel"] + ":" + data["Kind"] + ":v1"
                ).encode(),
            )
            value = cursor.execute(
                (
                    "SELECT ApplicationId,IntegrationId,EndpointId,Kind"
                    ",VersionNo,KeyVersion,Nonce,Ciphertext,Fingerprint"
                    " FROM crm_channels2.SecretVersion WHERE "
                    "InstitutionId=? AND SecretId=?"
                ),
                institution,
                uid("secret", keyjson),
            ).fetchone()
            require(
                value is not None and value[5] == "c12-v1",
                "C12_imported_secret_missing",
            )
            owners = [
                (name, str(value[i]).lower())
                for i, name in enumerate(
                    ("Application", "Integration", "WebhookEndpoint")
                )
                if value[i] is not None
            ]
            require(len(owners) == 1, "C12_imported_secret_owner")
            aad = secret_aad(institution, *owners[0], value[3], value[4], value[5])
            require(
                hmac.compare_digest(
                    AESGCM(key).decrypt(bytes(value[6]), bytes(value[7]), aad), original
                )
                and hmac.compare_digest(
                    bytes(value[8]), hmac.digest(key, original, "sha256")
                ),
                "C12_imported_secret_keyring_or_content",
            )
        return {"status": "noop", "bindings": len(bound)}
    require(not existing, "C12_partial_binding")
    require(
        sum(
            cursor.execute(
                "SELECT COUNT(*) FROM crm_channels2." + quote_name(t)
            ).fetchval()
            for t in (
                "Application",
                "Integration",
                "SecretVersion",
                "Audit",
                "ProviderOperation",
                "WebhookReceipt",
                "ExternalIdentity",
                "ExternalMessage",
                "SendJob",
                "SocialComment",
            )
        )
        == 0,
        "C12_unbound_target_data",
    )
    now = cursor.execute("SELECT CONVERT(varchar(33),SYSUTCDATETIME(),126)").fetchval()
    accounts, endpoints = {}, {}
    for data, keyjson, digest in source["Account"]:
        channel = data["Channel"]
        config = json.loads(data["Configuration"])
        stage, stage_hash = stage_binding(
            configrow[0], configrow[1], config.get("initialStage")
        )
        provider = "tiktok" if channel == "tiktok" else "meta"
        issuer = (
            "tiktok_business"
            if provider == "tiktok"
            else "meta_whatsapp"
            if channel == "whatsapp"
            else "instagram_login"
            if channel == "instagram" and config.get("instagramLogin") == "instagram"
            else "facebook_login"
        )
        client = identifier(config.get("appId"), 128)
        app = uid("application", [provider, client, issuer])
        integration = uid("integration", keyjson)
        require(
            app not in {a["app"] for a in accounts.values()},
            "C12_application_merge_requires_review",
        )
        external = (
            config.get(
                "phoneNumberId"
                if channel == "whatsapp"
                else "pageId"
                if channel in {"facebook", "messenger"}
                else "accountId"
            )
            or None
        )
        if external is not None:
            identifier(external)
        api = config.get("apiVersion") or ""
        insert(
            cursor,
            institution,
            "Application",
            dict(
                ApplicationId=app,
                Provider=provider,
                ClientId=client,
                ApiVersion=api,
                IssuerProfile=issuer,
                RedirectUri=config.get("callbackUrl") or "",
                EgressProfile="disabled-c12",
                State="draft",
                CreatedAt=now,
                UpdatedAt=now,
            ),
        )
        insert(
            cursor,
            institution,
            "Integration",
            dict(
                IntegrationId=integration,
                ApplicationId=app,
                Provider=provider,
                Channel=channel,
                Environment=config.get("environment") or "development",
                DisplayName=channel,
                ExternalAccountId=external,
                ParentExternalId=(
                    config.get("wabaId")
                    if channel == "whatsapp"
                    else config.get("pageId")
                    if channel == "instagram" and issuer == "facebook_login"
                    else None
                )
                or None,
                InitialStageKey=stage,
                InitialStageConfigHash=stage_hash,
                ApiVersion=api,
                DispatchMode="disabled",
                RequestedStatus="disconnected",
                VerifiedStatus="unverified",
                CreatedAt=now,
                UpdatedAt=now,
                ExternalNamespace=namespace(provider, client, issuer),
            ),
        )
        endpoint = uid("endpoint", keyjson)
        insert(
            cursor,
            institution,
            "WebhookEndpoint",
            dict(
                EndpointId=endpoint,
                ApplicationId=app,
                Provider=provider,
                ChannelSelector=channel,
                EndpointKey="c12-" + uuid.UUID(endpoint).hex,
                SignatureProfile="legacy-review-required",
                SignatureRequired=True,
                IsActive=False,
                CreatedAt=now,
                UpdatedAt=now,
            ),
        )
        accounts[channel] = {
            "app": app,
            "id": integration,
            "endpoint": endpoint,
            "provider": provider,
            "issuer": issuer,
        }
        endpoints[endpoint] = bytes(
            cursor.execute(
                (
                    "SELECT RowVersion FROM "
                    "crm_channels2.WebhookEndpoint WHERE "
                    "InstitutionId=? AND EndpointId=?"
                ),
                institution,
                endpoint,
            ).fetchval()
        )
        binding(
            "Account",
            keyjson,
            digest,
            integration,
            [
                ["Application", "ApplicationId", app],
                ["Integration", "IntegrationId", integration],
                ["WebhookEndpoint", "EndpointId", endpoint],
            ],
        )
    require(fail_after != "accounts", "C12_injected_after_accounts")
    for data, keyjson, digest in source["Credential"]:
        account = accounts[data["Channel"]]
        require(
            data["KeyId"] == hashlib.sha256(oldkey).hexdigest()[:32],
            "C12_credential_key_mismatch",
        )
        plain = AESGCM(oldkey).decrypt(
            bytes(data["Nonce"]),
            bytes(data["Ciphertext"]),
            ("crm_channels:" + data["Channel"] + ":" + data["Kind"] + ":v1").encode(),
        )
        require(0 < len(plain) <= 32768, "C12_secret_size")
        if data["Kind"] == "appSecret":
            owner, owner_id, kind = (
                "Application",
                account["app"],
                "tiktok_client_secret"
                if account["provider"] == "tiktok"
                else "meta_app_secret",
            )
        elif data["Kind"] == "accessToken":
            owner, owner_id, kind = (
                "Integration",
                account["id"],
                {
                    "whatsapp": "meta_permanent_access",
                    "instagram": "instagram_user_access"
                    if account["issuer"] == "instagram_login"
                    else "instagram_page_access",
                    "facebook": "facebook_page_access",
                    "messenger": "facebook_page_access",
                    "tiktok": "tiktok_access",
                }[data["Channel"]],
            )
        elif data["Kind"] == "verifyToken":
            owner, owner_id, kind = (
                "WebhookEndpoint",
                account["endpoint"],
                "webhook_verify",
            )
        elif data["Kind"] == "refreshToken" and account["provider"] == "tiktok":
            owner, owner_id, kind = "Integration", account["id"], "tiktok_refresh"
        else:
            raise ValueError("C12_unsupported_secret_kind")
        version = "c12-v1"
        nonce = os.urandom(12)
        aad = secret_aad(institution, owner, owner_id, kind, 1, version)
        cipher = AESGCM(key).encrypt(nonce, plain, aad)
        require(
            hmac.compare_digest(AESGCM(key).decrypt(nonce, cipher, aad), plain),
            "C12_recipher_verification",
        )
        sid = uid("secret", keyjson)
        # A constant hint cannot reveal any part of a short legacy secret.
        insert(
            cursor,
            institution,
            "SecretVersion",
            {
                "SecretId": sid,
                (
                    "EndpointId" if owner == "WebhookEndpoint" else owner + "Id"
                ): owner_id,
                "Kind": kind,
                "VersionNo": 1,
                "State": "staged",
                "KeyVersion": version,
                "Nonce": nonce,
                "Ciphertext": cipher,
                "Hint": "****",
                "Fingerprint": hmac.digest(key, plain, "sha256"),
                "CreatedAt": now,
            },
        )
        binding(
            "Credential",
            keyjson,
            digest,
            account["id"],
            [["SecretVersion", "SecretId", sid]],
        )
    for data, keyjson, digest in source["ExternalIdentity"]:
        a = accounts[data["Channel"]]
        ident = uid("identity", keyjson)
        require(
            str(
                cursor.execute(
                    "SELECT ContactId FROM crm.Conversation WHERE ConversationId=?",
                    data["ConversationId"],
                ).fetchval()
            ).lower()
            == str(data["ContactId"]).lower(),
            "C12_identity_contact_mismatch",
        )
        insert(
            cursor,
            institution,
            "ExternalIdentity",
            dict(
                IdentityId=ident,
                IntegrationId=a["id"],
                ExternalId=identifier(data["ExternalId"]),
                ContactId=data["ContactId"],
                ConversationId=data["ConversationId"],
                LastIncomingAt=data["LastIncomingAt"],
                CreatedAt=now,
            ),
        )
        binding(
            "ExternalIdentity",
            keyjson,
            digest,
            a["id"],
            [["ExternalIdentity", "IdentityId", ident]],
        )
    for data, keyjson, digest in source["ExternalMessage"]:
        a = accounts[data["Channel"]]
        mid = uid("message", keyjson)
        insert(
            cursor,
            institution,
            "ExternalMessage",
            dict(
                ExternalMessageId=mid,
                IntegrationId=a["id"],
                ExternalId=identifier(data["ExternalId"]),
                MessageId=data["MessageId"],
                Payload=canonical(
                    {"migration": UNIT, "source_sha256": digest.hex()}
                ).decode(),
                CreatedAt=now,
            ),
        )
        binding(
            "ExternalMessage",
            keyjson,
            digest,
            a["id"],
            [["ExternalMessage", "ExternalMessageId", mid]],
        )
    for data, keyjson, digest in source["social_comments"]:
        a = accounts[data["Channel"]]
        cid = uid("comment", keyjson)
        insert(
            cursor,
            institution,
            "SocialComment",
            dict(
                CommentId=cid,
                IntegrationId=a["id"],
                ExternalId=identifier(data["ExternalId"]),
                AuthorExternalId=identifier(data["AuthorId"]),
                Body=data["Body"],
                Payload=canonical(
                    {"migration": UNIT, "source_sha256": digest.hex()}
                ).decode(),
                ReceivedAt=data["ReceivedAt"],
            ),
        )
        binding(
            "social_comments",
            keyjson,
            digest,
            a["id"],
            [["SocialComment", "CommentId", cid]],
        )
    for data, keyjson, digest in source["webhook_events"]:
        candidates = [
            a
            for ch, a in accounts.items()
            if ch == data["Provider"] or a["provider"] == data["Provider"]
        ]
        require(len(candidates) == 1, "C12_ambiguous_legacy_receipt")
        a = candidates[0]
        rid = uid("receipt", keyjson)
        body = data["Payload"].encode()
        bodydigest = hashlib.sha256(body).digest()
        nonce = os.urandom(12)
        require(len(body) <= 1000000, "C12_receipt_limit")
        aad = canonical(
            [
                "cbn.receipt.v1",
                institution,
                a["endpoint"],
                rid,
                bodydigest.hex(),
                "c12-body-v1",
            ]
        )
        cipher = AESGCM(bodykey).encrypt(nonce, body, aad)
        require(
            AESGCM(bodykey).decrypt(nonce, cipher, aad) == body, "C12_receipt_recipher"
        )
        insert(
            cursor,
            institution,
            "WebhookReceipt",
            dict(
                ReceiptId=rid,
                EndpointId=a["endpoint"],
                Digest=bodydigest,
                BodyKeyVersion="c12-body-v1",
                BodyNonce=nonce,
                BodyCiphertext=cipher,
                SignatureKeyVersion="legacy-unverified",
                SignatureProfile="legacy-review-required",
                Authentication="legacy_unverified",
                Status="quarantined",
                ReceivedAt=data["ReceivedAt"],
                ExpiresAt=now,
                ApplicationId=a["app"],
                EndpointVersion=endpoints[a["endpoint"]],
                LastErrorCode="legacy_review_required",
            ),
        )
        binding(
            "webhook_events",
            keyjson,
            digest,
            a["id"],
            [["WebhookReceipt", "ReceiptId", rid]],
        )
    for data, keyjson, digest in source["outbound_queue"]:
        a = accounts[data["Channel"]]
        qid = uid("queue", keyjson)
        op = uid("queue-operation", keyjson)
        if data["IdentityId"] is None or data["MessageId"] is None:
            # Preserve the source row; a quarantine record is not a routable job.
            aid = uid("unroutable-job", keyjson)
            insert(
                cursor,
                institution,
                "Audit",
                dict(
                    AuditId=aid,
                    IntegrationId=a["id"],
                    ActorRef="migration:SQL-C12",
                    Action="legacy_job_quarantine",
                    ResultCode="legacy_job_unroutable",
                    CreatedAt=now,
                ),
            )
            binding(
                "outbound_queue", keyjson, digest, a["id"], [["Audit", "AuditId", aid]]
            )
            continue
        ident = uid("identity", {"IdentityId": str(data["IdentityId"])})
        require(
            cursor.execute(
                (
                    "SELECT 1 FROM crm_channels2.ExternalIdentity WHERE"
                    " InstitutionId=? AND IdentityId=? AND "
                    "IntegrationId=?"
                ),
                institution,
                ident,
                a["id"],
            ).fetchone(),
            "C12_job_identity_scope",
        )
        insert(
            cursor,
            institution,
            "ProviderOperation",
            dict(
                OperationId=op,
                ApplicationId=a["app"],
                IntegrationId=a["id"],
                ActorRef="migration:SQL-C12",
                Action="legacy_job_import",
                RequestDigest=digest,
                Status="failed",
                ResultCode="legacy_review_required",
                ResultMetadata="{}",
                CreatedAt=now,
                CompletedAt=now,
                EffectKey=digest,
            ),
        )
        insert(
            cursor,
            institution,
            "SendJob",
            dict(
                QueueId=qid,
                IntegrationId=a["id"],
                IdentityId=ident,
                MessageId=data["MessageId"],
                OperationId=op,
                Kind="chat",
                State="blocked",
                Payload=canonical(
                    {"migration": UNIT, "source_sha256": digest.hex()}
                ).decode(),
                DueAt=data["DueAt"],
                Attempts=0,
                LastErrorCode="legacy_review_required",
                CreatedAt=data["CreatedAt"],
            ),
        )
        binding(
            "outbound_queue",
            keyjson,
            digest,
            a["id"],
            [["ProviderOperation", "OperationId", op], ["SendJob", "QueueId", qid]],
        )
    for data, keyjson, digest in source["Audit"]:
        a = accounts[data["Channel"]]
        aid = uid("audit", keyjson)
        insert(
            cursor,
            institution,
            "Audit",
            dict(
                AuditId=aid,
                IntegrationId=a["id"],
                ActorRef="migration:SQL-C12",
                Action=data["Action"],
                ResultCode="legacy_actor_unknown",
                CreatedAt=data["CreatedAt"],
            ),
        )
        binding("Audit", keyjson, digest, a["id"], [["Audit", "AuditId", aid]])
    require(fail_after != "complete", "C12_injected_before_commit")
    return {
        "status": "imported",
        "bindings": sum(map(len, source.values())),
        "applications": len(accounts),
        "secrets_reciphered": len(source["Credential"]),
        "receipts_quarantined": len(source["webhook_events"]),
        "jobs_blocked": cursor.execute(
            "SELECT COUNT(*) FROM crm_channels2.SendJob WHERE State='blocked'"
        ).fetchval(),
        "jobs_quarantined_unroutable": cursor.execute(
            (
                "SELECT COUNT(*) FROM crm_channels2.Audit WHERE "
                "Action='legacy_job_quarantine'"
            )
        ).fetchval(),
    }
