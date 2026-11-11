"""Offline C11 SQL2019 compiler. It never connects or imports the application."""

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "docs/adaptation/sql/channels-parity-contract.json"
MODEL_SHA = "376f5f1234347cd403fe9a71fb0c4421fa14f2eee552afc790e91ae95a1cd7ba"
PACKAGE = ROOT / "backend/migrations/cbn_channels_parity_v1"
ACTOR = "cbn_channels_parity_migrator_c11"
SCHEMA = "crm_channels2"
VERSION = "cbn-parity-shape-v1"
RELEASE = "CBN-channels-parity-v1"
TARGET = re.compile(r"CBN_C11_(REF|TRIAL|FAULT|RECOVERY)_20261025_[0-9a-f]{8}\Z")


def require(value, code):
    if not value:
        raise ValueError(code)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def model():
    require(digest(MODEL) == MODEL_SHA, "C10_contract_changed")
    return json.loads(MODEL.read_text(encoding="utf-8"))


def quote(name):
    require(bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,127}", name)), "identifier")
    return "[" + name + "]"


def qualified(name):
    parts = name.split(".")
    require(len(parts) == 2, "qualified_identifier")
    return ".".join(map(quote, parts))


def literal(value):
    if isinstance(value, bool):
        return str(int(value))
    if isinstance(value, int):
        return str(value)
    if isinstance(value, (dict, list)):
        value = json.dumps(value, separators=(",", ":"))
    return "N'" + str(value).replace("'", "''") + "'"


CHECKS = {
    "Context": ["ContextId=1"],
    "Application": [
        "Provider IN('meta','tiktok')",
        "State IN('draft','enabled','paused','retired')",
    ],
    "Integration": [
        (
            "(Provider='meta' AND Channel IN('whatsapp','instagram','face"
            "book','messenger')) OR (Provider='tiktok' AND Channel='tikto"
            "k')"
        ),
        "RequestedStatus IN('connected','paused','disconnected')",
    ],
    "OAuthSession": [
        "ExpiresAt>CreatedAt AND ExpiresAt<=DATEADD(minute,30,CreatedAt)",
        (
            "(GrantScope='create_connections' AND IntegrationId IS NULL) "
            "OR (GrantScope='bound_connection' AND IntegrationId IS NOT N"
            "ULL)"
        ),
        (
            "Status IN('pending','exchanging','assets_ready','completed',"
            "'failed','expired','cancelled','uncertain','reconciled','aba"
            "ndoned')"
        ),
        "ClaimVersion>=0",
        "ClientSecretVersionNo>=1",
        "PkceMethod IS NULL OR PkceMethod='S256'",
        (
            "(ClaimId IS NULL AND ClaimUntil IS NULL) OR (ClaimId IS NOT "
            "NULL AND ClaimUntil IS NOT NULL)"
        ),
    ],
    "WebhookEndpoint": [
        "SignatureRequired=1",
        "Provider IN('meta','tiktok')",
        "ChannelSelector IN('meta','whatsapp','instagram','facebook','tiktok')",
    ],
    "SecretVersion": [
        "VersionNo>=1",
        "State IN('staged','active','grace','retired','revoked')",
        "DATALENGTH(Ciphertext)>16 AND DATALENGTH(Ciphertext)<=32784",
        "+".join(
            "CASE WHEN " + c + " IS NULL THEN 0 ELSE 1 END"
            for c in (
                "ApplicationId",
                "IntegrationId",
                "EndpointId",
                "OAuthSessionId",
                "AssetId",
            )
        )
        + "=1",
        (
            "State<>'grace' OR (EndpointId IS NOT NULL AND Kind IN('tikto"
            "k_webhook_secret','endpoint_hmac') AND GraceUntil IS NOT NUL"
            "L)"
        ),
    ],
    "ProviderOperation": [
        (
            "Status IN('pending','running','confirmed','failed','uncertai"
            "n','reconciled','abandoned')"
        ),
        "LeaseVersion>=0 AND Attempts>=0",
    ],
    "TikTokPolicy": [
        "RolloutPercent BETWEEN 0 AND 100",
        (
            "DailyOutboundQuota BETWEEN 0 AND 1000000 AND DailyAiQuota BE"
            "TWEEN 0 AND 1000000"
        ),
        "ReviewStatus IN('untracked','pending','changes_requested','approved')",
        "OutboundMode IN('disabled','shadow','manual','live','stub')",
    ],
    "VerificationEvidence": [
        "EventId IS NULL OR (ReceiptId IS NOT NULL AND EndpointId IS NOT NULL)"
    ],
    "QuotaBucket": ["Reserved>=0 AND Committed>=0", "Action IN('outbound','ai')"],
    "QuotaReservation": [
        "Units>0",
        "Status IN('reserved','committed','released','uncertain')",
        "Action IN('outbound','ai')",
    ],
    "WebhookReceipt": [
        "Authentication IN('verified','legacy_unverified')",
        (
            "(Authentication='verified' AND SignatureSecretId IS NOT NULL"
            " AND SignatureVerifiedAt IS NOT NULL) OR (Authentication='le"
            "gacy_unverified' AND SignatureVerifiedAt IS NULL)"
        ),
        (
            "(BodyPurgedAt IS NULL AND BodyKeyVersion IS NOT NULL AND Bod"
            "yNonce IS NOT NULL AND BodyCiphertext IS NOT NULL) OR (BodyP"
            "urgedAt IS NOT NULL AND BodyKeyVersion IS NULL AND BodyNonce"
            " IS NULL AND BodyCiphertext IS NULL)"
        ),
        "BodyCiphertext IS NULL OR DATALENGTH(BodyCiphertext)<=1000016",
        (
            "BodyPurgedAt IS NULL OR (Status IN('processed','quarantined'"
            ",'failed') AND LeaseId IS NULL AND LeaseUntil IS NULL)"
        ),
        "Authentication<>'legacy_unverified' OR Status='quarantined'",
        "LeaseVersion>=0 AND Attempts>=0",
    ],
    "WebhookEvent": [
        "IntegrationId IS NOT NULL OR Status='quarantined'",
        "LeaseVersion>=0 AND Attempts>=0",
    ],
    "ConversationProfile": [
        "LeadScore IS NULL OR LeadScore BETWEEN 0 AND 100",
        "Temperature IS NULL OR Temperature IN('cold','warm','hot')",
    ],
    "ConversationControl": ["Epoch>=0 AND ReadSequence>=0"],
    "SendJob": [
        (
            "(Kind='chat' AND IdentityId IS NOT NULL AND MessageId IS NOT"
            " NULL AND CommentId IS NULL) OR (Kind='comment_reply' AND Co"
            "mmentId IS NOT NULL AND IdentityId IS NULL AND MessageId IS "
            "NULL)"
        ),
        "LeaseVersion>=0 AND Attempts>=0",
    ],
    "MessageRoute": [
        (
            "(ActorKind='bot' AND ControlEpoch IS NOT NULL AND ControlEpo"
            "ch>=0) OR (ActorKind IN('human','external') AND ControlEpoch"
            " IS NULL)"
        ),
        (
            "(ActorKind='external' AND QueueId IS NULL) OR (ActorKind IN("
            "'human','bot') AND QueueId IS NOT NULL)"
        ),
    ],
    "LegacyBinding": [
        (
            "LegacyTable IN('crm_channels.Account','crm_channels.Credenti"
            "al','crm_channels.webhook_events','crm_channels.Audit',"
            "'crm_channels.ExternalIdentity','crm_channels.ExternalMessage',"
            "'crm_channels.outbound_queue','crm_channels.social_comments')"
        )
    ],
}


def table_sql(table, source):
    name = table["name"].split(".")[1]
    columns = []
    for key, spec in table["columns"].items():
        kind = spec["type"]
        require(
            bool(
                re.fullmatch(
                    (
                        "(?:uniqueidentifier|bit|tinyint|int|bigint|date|"
                        "rowversion|datetime2\\(7\\)|"
                        "n?varchar\\((?:max|[0-9]+)\\)|"
                        "(?:var)?binary\\((?:max|[0-9]+)\\))"
                    ),
                    kind,
                )
            ),
            "SQL_type",
        )
        definition = quote(key) + " " + kind
        if "collation" in spec:
            require(spec["collation"] == "Latin1_General_100_BIN2", "collation")
            definition += " COLLATE Latin1_General_100_BIN2"
        definition += " NULL" if spec["nullable"] else " NOT NULL"
        if key in table["defaults"]:
            definition += (
                " CONSTRAINT "
                + quote("DF_C11_" + name + "_" + key)
                + " DEFAULT "
                + literal(table["defaults"][key])
            )
        columns.append(definition)
    keys = [table["primary_key"], *table["unique_keys"]]
    for index, key in enumerate(keys):
        columns.append(
            "CONSTRAINT "
            + quote("K_C11_" + name + "_" + str(index))
            + (" PRIMARY KEY" if index == 0 else " UNIQUE")
            + " ("
            + ",".join(map(quote, key))
            + ")"
        )
    checks = list(CHECKS.get(name, []))
    for key, spec in table["columns"].items():
        if spec.get("json_validation"):
            checks.append(
                quote(key) + " IS NULL OR ISJSON(" + quote(key) + ")=1"
                if spec["nullable"]
                else "ISJSON(" + quote(key) + ")=1"
            )
        if spec.get("collation"):
            checks.append(
                quote(key)
                + " IS NULL OR (DATALENGTH("
                + quote(key)
                + ")>0 AND DATALENGTH("
                + quote(key)
                + ")=DATALENGTH(RTRIM("
                + quote(key)
                + ")))"
            )
    if name == "SecretVersion":
        owner_columns = {
            "Application": "ApplicationId",
            "Integration": "IntegrationId",
            "WebhookEndpoint": "EndpointId",
            "OAuthSession": "OAuthSessionId",
            "ProviderAsset": "AssetId",
        }
        checks.append(
            " OR ".join(
                "("
                + owner_columns[owner]
                + " IS NOT NULL AND Kind IN("
                + ",".join(map(literal, kinds))
                + "))"
                for owner, kinds in source["secret_contract"]["scopes"].items()
            )
        )
    for index, expression in enumerate(checks):
        columns.append(
            "CONSTRAINT "
            + quote("CK_C11_" + name + "_" + str(index))
            + " CHECK ("
            + expression
            + ")"
        )
    sql = (
        "CREATE TABLE "
        + qualified(table["name"])
        + "(\n "
        + ",\n ".join(columns)
        + "\n);\n"
    )
    for index in table["indexes"]:
        sql += (
            "CREATE "
            + ("UNIQUE " if index["unique"] else "")
            + "INDEX "
            + quote(index["name"])
            + " ON "
            + qualified(table["name"])
            + " ("
            + ",".join(map(quote, index["columns"]))
            + ")"
        )
        if index.get("where"):
            sql += " WHERE " + index["where"]
        sql += ";\n"
    return sql


def compile_units(source=None):
    source = model() if source is None else source
    tables = {t["name"]: t for t in source["tables"]}
    result = {}
    for unit in source["migration"]["units"]:
        sql = (
            "-- SQL-C11 immutable restored-copy unit. Runner owns the tra"
            "nsaction.\nSET XACT_ABORT ON;\n"
        )
        sql += (
            "IF @@TRANCOUNT<>1 OR USER_NAME()<>N'"
            + ACTOR
            + (
                "' OR SESSION_CONTEXT(N'CBN_C11_TARGET') IS NULL OR DB_NAME()"
                " COLLATE Latin1_General_100_BIN2<>CONVERT(nvarchar(128),SESS"
                "ION_CONTEXT(N'CBN_C11_TARGET')) COLLATE Latin1_General_100_B"
                "IN2 OR DB_NAME() NOT LIKE N'CBN_C11[_]%' THROW 51111,'Approv"
                "ed C11 restoration and principal required.',1;\n"
            )
        )
        for name in unit["tables"]:
            sql += "-- C11_BOUNDARY\n" + table_sql(tables[name], source)
        sql += "-- C11_BOUNDARY\n"
        for number, fk in enumerate(source["foreign_keys"]):
            if fk["table"] in unit["tables"]:
                sql += (
                    "ALTER TABLE "
                    + qualified(fk["table"])
                    + " WITH CHECK ADD CONSTRAINT "
                    + quote("FK_C11_" + str(number))
                    + " FOREIGN KEY("
                    + ",".join(map(quote, fk["columns"]))
                    + ") REFERENCES "
                    + qualified(fk["references"])
                    + "("
                    + ",".join(map(quote, fk["referenced_columns"]))
                    + ");\n"
                )
        result[unit["id"]] = sql
    return result


def verify_sql_files():
    for unit, sql in compile_units().items():
        require(
            (PACKAGE / (unit + ".sql")).read_text(encoding="utf-8") == sql,
            "SQL_contract_mismatch",
        )


def assets():
    from tools.crm_extension_v2 import assets as legacy_assets

    require(
        legacy_assets()[1]
        == ("49f72eb835ce46b83ec9c6267da2f73c9d7799990de6fab8ed28762565985998"),
        "frozen_C7_transitive_assets",
    )
    release = json.loads((PACKAGE / "release.json").read_text(encoding="utf-8"))
    require(
        release["release_id"] == RELEASE and release["contract_sha256"] == MODEL_SHA,
        "release_identity",
    )
    require(
        release["institutional_sql2019_accepted"] is False, "institutional_acceptance"
    )
    paths = [r["path"] for r in release["files"]]
    expected = [
        "backend/migrations/cbn_channels_parity_v1/" + n
        for n in (
            *[u + ".sql" for u in compile_units()],
            "expected-shapes.json",
            "constraint-coverage.json",
            "reviewed-checks.json",
        )
    ]
    expected += [
        "backend/tools/channels_parity_contract.py",
        "backend/tools/channels_parity_snapshot.py",
        "backend/tools/channels_parity.py",
        "docs/adaptation/sql/channels-parity-contract.json",
    ]
    require(
        len(paths) == len(set(paths)) and set(paths) == set(expected), "release_files"
    )
    for record in release["files"]:
        require(
            digest(ROOT / record["path"]) == record["sha256"], "release_bytes_changed"
        )
    shapes = json.loads((PACKAGE / "expected-shapes.json").read_text(encoding="utf-8"))
    require(len(shapes) == len(set(shapes)) == 6, "release_prefix_shapes")
    expected_units = [
        {
            "id": u,
            "sha256": digest(PACKAGE / (u + ".sql")),
            "before_sha256": shapes[i],
            "after_sha256": shapes[i + 1],
        }
        for i, u in enumerate(compile_units())
    ]
    require(release["units"] == expected_units, "release_unit_chain")
    verify_sql_files()
    return release, digest(PACKAGE / "release.json")
