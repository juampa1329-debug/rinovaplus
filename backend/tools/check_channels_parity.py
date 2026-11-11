"""Independent model/catalog comparison and rollback-only C11 SQL tests."""

import argparse
import datetime as dt
import hashlib
import json
import re
import uuid
from pathlib import Path

import pyodbc

from tools.channels_parity import guard
from tools.channels_parity_contract import (
    PACKAGE,
    literal,
    model,
    qualified,
    quote,
    require,
)
from tools.channels_parity_snapshot import metadata
from tools.rehearse_channels_parity import admin, load, protected_snapshots, save


def physical_shape(cursor, prefix=5):
    source = model()
    selected = {
        name for u in source["migration"]["units"][:prefix] for name in u["tables"]
    }
    shape = metadata(cursor)
    actual = {
        (r["table_name"], r["name"]): r
        for r in shape["columns"]
        if r["schema_name"] == "crm_channels2"
    }
    tables = [t for t in source["tables"] if t["name"] in selected]
    require(len(actual) == sum(len(t["columns"]) for t in tables), "C11_column_count")
    for table in tables:
        name = table["name"].split(".")[1]
        for field, spec in table["columns"].items():
            row = actual[name, field]
            kind = spec["type"].split("(")[0]
            require(
                row["type_name"] == ("timestamp" if kind == "rowversion" else kind)
                and bool(row["is_nullable"]) == spec["nullable"],
                "C11_column_type_nullability",
            )
            if spec.get("collation"):
                require(row["collation_name"] == spec["collation"], "C11_BIN2")
            if "(" in spec["type"] and kind in {
                "varchar",
                "nvarchar",
                "binary",
                "varbinary",
            }:
                size = spec["type"].split("(")[1][:-1]
                require(
                    row["max_length"]
                    == (
                        -1
                        if size == "max"
                        else int(size) * (2 if kind == "nvarchar" else 1)
                    ),
                    "C11_column_width",
                )
            if field in table["defaults"]:
                require(
                    row["default_name"] is not None
                    and normalize(row["default_definition"])
                    == normalize(literal(table["defaults"][field])),
                    "C11_default_value",
                )
        indexes = [
            r
            for r in shape["indexes"]
            if r["schema_name"] == "crm_channels2" and r["table_name"] == name
        ]
        for i, key in enumerate([table["primary_key"], *table["unique_keys"]]):
            ix = sorted(
                [r for r in indexes if r["name"] == "K_C11_" + name + "_" + str(i)],
                key=lambda r: r["key_ordinal"],
            )
            require(
                [r["column_name"] for r in ix] == key
                and all(r["is_unique"] and not r["is_disabled"] for r in ix),
                "C11_key",
            )
            require(
                all(
                    bool(r["is_primary_key"]) == (i == 0)
                    and bool(r["is_unique_constraint"]) == (i > 0)
                    and not r["has_filter"]
                    and r["type_desc"] == ("CLUSTERED" if i == 0 else "NONCLUSTERED")
                    for r in ix
                ),
                "C11_key_kind",
            )
        for index in table["indexes"]:
            ix = sorted(
                [r for r in indexes if r["name"] == index["name"]],
                key=lambda r: r["key_ordinal"],
            )
            require(
                [r["column_name"] for r in ix] == index["columns"]
                and all(
                    bool(r["is_unique"]) == index["unique"] and not r["is_disabled"]
                    for r in ix
                ),
                "C11_index",
            )
            require(
                all(bool(r["has_filter"]) == bool(index.get("where")) for r in ix),
                "C11_filtered_index",
            )
            require(
                all(
                    normalize(r["filter_definition"]) == normalize(index.get("where"))
                    for r in ix
                ),
                "C11_index_filter_value",
            )
        expected_names = {
            "K_C11_" + name + "_" + str(i) for i in range(len(table["unique_keys"]) + 1)
        } | {i["name"] for i in table["indexes"]}
        require({r["name"] for r in indexes} == expected_names, "C11_index_membership")
    expected_fks = [
        (i, fk)
        for i, fk in enumerate(source["foreign_keys"])
        if fk["table"] in selected
    ]
    for i, fk in expected_fks:
        rows = sorted(
            [
                r
                for r in shape["foreign_keys"]
                if r["schema_name"] == "crm_channels2"
                and r["name"] == "FK_C11_" + str(i)
            ],
            key=lambda r: r["ordinal"],
        )
        require(
            [r["column_name"] for r in rows] == fk["columns"]
            and [r["target_column"] for r in rows] == fk["referenced_columns"],
            "C11_FK_columns",
        )
        require(
            all(
                r["table_name"] == fk["table"].split(".")[1]
                and r["target_schema"] + "." + r["target_table"] == fk["references"]
                and not r["is_disabled"]
                and not r["is_not_trusted"]
                and r["delete_referential_action"]
                == r["update_referential_action"]
                == 0
                for r in rows
            ),
            "C11_trusted_FK",
        )
    checks = [r for r in shape["checks"] if r["schema_name"] == "crm_channels2"]
    reviewed = PACKAGE / "reviewed-checks.json"
    if reviewed.is_file():
        approved = json.loads(reviewed.read_text(encoding="utf-8"))["checks"]
        expected = {
            r["name"]: r
            for r in approved
            if "crm_channels2." + r["table_name"] in selected
        }
        require(
            {r["name"]: r for r in checks} == expected, "C11_reviewed_CHECK_definitions"
        )
    expected_checks = set()
    for unit in source["migration"]["units"][:prefix]:
        sql = (PACKAGE / (unit["id"] + ".sql")).read_text(encoding="utf-8")
        expected_checks.update(re.findall(r"CONSTRAINT \[([^\]]+)\] CHECK \(", sql))
    require({r["name"] for r in checks} == expected_checks, "C11_check_membership")
    require(
        all(not r["is_disabled"] and not r["is_not_trusted"] for r in checks),
        "C11_trusted_checks",
    )
    require(
        len(
            {
                r["name"]
                for r in shape["foreign_keys"]
                if r["schema_name"] == "crm_channels2"
            }
        )
        == len(expected_fks),
        "C11_no_extra_FK",
    )
    require(
        all(
            r["effective_owner"] == "dbo"
            for r in shape["object_owners"]
            if r["schema_name"] == "crm_channels2"
        ),
        "C11_new_object_owner",
    )
    return {
        "tables": len(tables),
        "columns": len(actual),
        "foreign_keys": len(expected_fks),
        "trusted_checks": len(checks),
    }


def normalize(value):
    """Defaults/AND-only filters only; not a CHECK semantic comparator."""
    tokens = re.findall(
        r"N?'(?:''|[^'])*'|\[[^\]]+\]|[A-Za-z_][A-Za-z_0-9]*|\d+|<>|>=|<=|\S",
        value or "",
    )
    return tuple(
        t[1:] if t.startswith("N'") else t[1:-1] if t.startswith("[") else t
        for t in tokens
        if t not in ("(", ")")
    )


def fixture(cursor, ticket):
    tables = {t["name"].split(".")[1]: t for t in model()["tables"]}
    now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    ids = {
        k: str(uuid.uuid4())
        for k in (
            "app",
            "app2",
            "account",
            "account2",
            "secret",
            "endpoint",
            "operation",
            "session",
            "asset",
            "receipt",
            "event",
            "identity",
            "reservation",
            "queue",
        )
    }
    core = cursor.execute(
        (
            "SELECT TOP(1) CONVERT(varchar(36),m.MessageId),C"
            "ONVERT(varchar(36),m.ConversationId),CONVERT(var"
            "char(36),c.ContactId) FROM crm.Message m JOIN cr"
            "m.Conversation c ON c.ConversationId=m.Conversat"
            "ionId ORDER BY m.MessageId"
        )
    ).fetchone()
    require(core is not None, "C11_fixture_core_keys")
    common = {
        "InstitutionId": ticket["institution_id"],
        "ApplicationId": ids["app"],
        "IntegrationId": ids["account"],
        "EndpointId": ids["endpoint"],
        "OperationId": ids["operation"],
        "ClientSecretId": ids["secret"],
        "ClientSecretVersionNo": 1,
        "OAuthSessionId": ids["session"],
        "DiscoveryOperationId": ids["operation"],
        "ReceiptId": ids["receipt"],
        "EventId": ids["event"],
        "IdentityId": ids["identity"],
        "ReservationId": ids["reservation"],
        "QueueId": ids["queue"],
        "MessageId": core[0],
        "ConversationId": core[1],
        "ContactId": core[2],
    }

    def insert(name, **changes):
        values = {}
        for field, spec in tables[name]["columns"].items():
            kind = spec["type"]
            if kind == "rowversion":
                continue
            if field in changes:
                value = changes[field]
            elif spec["nullable"]:
                value = None
            elif field in common:
                value = common[field]
            elif field in tables[name]["defaults"]:
                value = tables[name]["defaults"][field]
            elif kind == "uniqueidentifier":
                value = str(uuid.uuid4())
            elif kind.startswith("binary"):
                value = hashlib.sha256((name + field).encode()).digest()[
                    : int(re.search(r"\d+", kind)[0])
                ]
            elif kind.startswith("varbinary"):
                value = b"synthetic-not-encrypted-with-a-key"
            elif kind.startswith("datetime"):
                value = now + dt.timedelta(minutes=10) if field == "ExpiresAt" else now
            elif kind == "date":
                value = now.date()
            elif kind in {"bit", "tinyint", "int", "bigint"}:
                value = 1
            elif spec.get("json_validation"):
                value = "[]" if "Scopes" in field else "{}"
            else:
                value = "test"
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            values[field] = value
        cursor.execute(
            "INSERT "
            + qualified("crm_channels2." + name)
            + "("
            + ",".join(map(quote, values))
            + ") VALUES("
            + ",".join("?" for _ in values)
            + ")",
            tuple(values.values()),
        )

    insert(
        "Application", ApplicationId=ids["app"], Provider="meta", ClientId="client-a"
    )
    insert(
        "Application", ApplicationId=ids["app2"], Provider="meta", ClientId="client-b"
    )
    insert(
        "Integration",
        IntegrationId=ids["account"],
        Provider="meta",
        Channel="whatsapp",
        ExternalAccountId="PhoneA",
    )
    insert(
        "Integration",
        IntegrationId=ids["account2"],
        Provider="meta",
        Channel="whatsapp",
        ExternalAccountId="phonea",
    )
    insert(
        "SecretVersion",
        SecretId=ids["secret"],
        ApplicationId=ids["app"],
        Kind="meta_app_secret",
        VersionNo=1,
        State="active",
    )
    insert(
        "WebhookEndpoint",
        EndpointId=ids["endpoint"],
        Provider="meta",
        ChannelSelector="whatsapp",
        SignatureRequired=True,
    )
    insert(
        "ProviderOperation",
        OperationId=ids["operation"],
        IntegrationId=ids["account"],
        EndpointId=ids["endpoint"],
    )
    insert(
        "OAuthSession",
        OAuthSessionId=ids["session"],
        IntegrationId=ids["account"],
        GrantScope="bound_connection",
    )
    insert(
        "ProviderAsset",
        AssetId=ids["asset"],
        IntegrationId=ids["account"],
        Kind="phone",
    )
    insert("QuotaBucket", Action="outbound")
    insert(
        "QuotaReservation",
        ReservationId=ids["reservation"],
        OperationId=ids["operation"],
        Action="outbound",
        Status="reserved",
    )
    insert("EndpointIntegration", RouteKind="phone", ExternalId="PhoneA")
    insert(
        "WebhookReceipt",
        ReceiptId=ids["receipt"],
        Authentication="verified",
        SignatureSecretId=ids["secret"],
        SignatureVerifiedAt=now,
        Status="processed",
        BodyKeyVersion="synthetic",
        BodyNonce=uuid.uuid4().bytes[:12],
        BodyCiphertext=b"synthetic-ciphertext-placeholder-only",
    )
    insert(
        "WebhookEvent",
        EventId=ids["event"],
        IntegrationId=ids["account"],
        RouteKind="phone",
        RouteExternalId="PhoneA",
        IdentityStrength="strong",
        Status="processed",
    )
    insert(
        "VerificationEvidence",
        EventId=ids["event"],
        ReceiptId=ids["receipt"],
        EndpointId=ids["endpoint"],
        OperationId=ids["operation"],
        Kind="signed_event",
    )
    insert("ConversationProfile", Temperature="cold")
    insert("ConversationControl")
    insert("ExternalIdentity", IdentityId=ids["identity"])
    insert("ExternalMessage")
    insert("SocialComment")
    insert(
        "SendJob",
        QueueId=ids["queue"],
        Kind="chat",
        IdentityId=ids["identity"],
        MessageId=core[0],
        OperationId=ids["operation"],
        ReservationId=ids["reservation"],
    )
    insert("MessageRoute", ActorKind="external", QueueId=None)
    insert("LegacyBinding", LegacyTable="crm_channels.Account")
    return ids, insert


NEGATIVES = [
    ("owner_xor", "UPDATE crm_channels2.SecretVersion SET IntegrationId=?", "account"),
    ("owner_none", "UPDATE crm_channels2.SecretVersion SET ApplicationId=NULL", None),
    ("owner_kind", "UPDATE crm_channels2.SecretVersion SET Kind='tiktok_access'", None),
    ("secret_version", "UPDATE crm_channels2.SecretVersion SET VersionNo=0", None),
    ("cipher_size", "UPDATE crm_channels2.SecretVersion SET Ciphertext=0x01", None),
    ("bad_json", "UPDATE crm_channels2.Integration SET ConfiguredScopes=N'bad'", None),
    (
        "scope_null",
        "DELETE crm_channels2.ProviderAsset; "
        "UPDATE crm_channels2.OAuthSession SET IntegrationId=NULL",
        None,
    ),
    (
        "scope_create",
        ("UPDATE crm_channels2.OAuthSession SET GrantScope='create_connections'"),
        None,
    ),
    (
        "oauth_ttl",
        ("UPDATE crm_channels2.OAuthSession SET ExpiresAt=DATEADD(hour,1,CreatedAt)"),
        None,
    ),
    ("oauth_status", "UPDATE crm_channels2.OAuthSession SET Status='invented'", None),
    ("quota_counter", "UPDATE crm_channels2.QuotaBucket SET Reserved=-1", None),
    ("reserve_units", "UPDATE crm_channels2.QuotaReservation SET Units=0", None),
    (
        "reserve_account",
        "UPDATE crm_channels2.QuotaReservation SET IntegrationId=?",
        "account2",
    ),
    (
        "unsigned_endpoint",
        "UPDATE crm_channels2.WebhookEndpoint SET SignatureRequired=0",
        None,
    ),
    (
        "receipt_secret",
        ("UPDATE crm_channels2.WebhookReceipt SET SignatureSecretId=NULL"),
        None,
    ),
    (
        "receipt_time",
        ("UPDATE crm_channels2.WebhookReceipt SET SignatureVerifiedAt=NULL"),
        None,
    ),
    (
        "partial_purge",
        "UPDATE crm_channels2.WebhookReceipt SET BodyCiphertext=NULL",
        None,
    ),
    (
        "legacy_verified",
        (
            "UPDATE crm_channels2.WebhookReceipt SET Authenti"
            "cation='legacy_unverified',Status='quarantined'"
        ),
        None,
    ),
    (
        "event_account",
        "UPDATE crm_channels2.WebhookEvent SET IntegrationId=?",
        "account2",
    ),
    (
        "event_null",
        "DELETE crm_channels2.VerificationEvidence; "
        "UPDATE crm_channels2.WebhookEvent SET IntegrationId=NULL",
        None,
    ),
    (
        "evidence_receipt",
        "UPDATE crm_channels2.VerificationEvidence SET ReceiptId=NULL",
        None,
    ),
    (
        "evidence_endpoint",
        ("UPDATE crm_channels2.VerificationEvidence SET EndpointId=NULL"),
        None,
    ),
    ("score", "UPDATE crm_channels2.ConversationProfile SET LeadScore=101", None),
    ("epoch", "UPDATE crm_channels2.ConversationControl SET Epoch=-1", None),
    ("job_message", "UPDATE crm_channels2.SendJob SET MessageId=NULL", None),
    ("job_kind", "UPDATE crm_channels2.SendJob SET Kind='comment_reply'", None),
    (
        "bot_epoch",
        ("UPDATE crm_channels2.MessageRoute SET ActorKind='bot',QueueId=?"),
        "queue",
    ),
    ("external_queue", "UPDATE crm_channels2.MessageRoute SET QueueId=?", "queue"),
    ("human_queue", "UPDATE crm_channels2.MessageRoute SET ActorKind='human'", None),
    (
        "trailing_ID",
        "UPDATE crm_channels2.Integration SET ExternalAccountId='PhoneA ' "
        "WHERE IntegrationId=?",
        "account",
    ),
    (
        "duplicate_ID",
        "UPDATE crm_channels2.Integration SET ExternalAccountId='same'",
        None,
    ),
    (
        "endpoint_app",
        "UPDATE crm_channels2.WebhookEndpoint SET ApplicationId=?",
        "app2",
    ),
]


def check(work):
    state = load(work / "state.json")
    trial = load(work / "trial-result.json")
    ticket = load(work / (trial["database"] + ".json"))
    passed = []
    with admin(trial["database"], state["context"]) as connection:
        c = connection.cursor()
        structure = physical_shape(c)
        for label, sql, parameter in NEGATIVES:
            c.execute("SET XACT_ABORT ON; BEGIN TRANSACTION;")
            try:
                ids, _ = fixture(c, ticket)
                try:
                    execute_case(c, sql, ids, parameter)
                except pyodbc.IntegrityError:
                    passed.append(label)
                else:
                    raise AssertionError("C11_constraint_accepted_" + label)
            finally:
                c.execute("IF @@TRANCOUNT>0 ROLLBACK;")
        c.execute("BEGIN TRANSACTION;")
        try:
            _, insert = fixture(c, ticket)
            for _ in range(2):
                insert(
                    "WebhookReceipt",
                    ReceiptId=str(uuid.uuid4()),
                    Authentication="legacy_unverified",
                    SignatureSecretId=None,
                    SignatureVerifiedAt=None,
                    Status="quarantined",
                    BodyKeyVersion=None,
                    BodyNonce=None,
                    BodyCiphertext=None,
                    BodyPurgedAt=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None),
                    Digest=uuid.uuid4().bytes + uuid.uuid4().bytes,
                )
            require(
                c.execute(
                    (
                        "SELECT COUNT(*) FROM crm_channels2.WebhookReceip"
                        "t WHERE BodyPurgedAt IS NOT NULL"
                    )
                ).fetchval()
                == 2,
                "C11_two_purged_receipts",
            )
            require(
                c.execute(
                    (
                        "SELECT COUNT(*) FROM crm_channels2.Integration W"
                        "HERE ExternalAccountId IN('PhoneA','phonea')"
                    )
                ).fetchval()
                == 2,
                "C11_case_sensitive_IDs",
            )
            c.execute("UPDATE crm_channels2.ProviderOperation SET Status='confirmed'")
        finally:
            c.execute("ROLLBACK;")
        require(
            guard(c, ticket, load(PACKAGE / "expected-shapes.json")) == 5,
            "C11_post_constraints",
        )
    require(
        protected_snapshots(state["context"]) == state["sources"],
        "C11_constraints_preserved_sources",
    )
    result = {
        "phase": "constraints",
        "physical_structure": structure,
        "negative_cases": passed,
        "positive_cases": [
            "all_synthetic_fixture_rows_rollback",
            "case_sensitive_IDs",
            "two_purged_NULL_nonces",
            "confirmed_remote_state",
        ],
        "all_synthetic_rows_rolled_back": True,
        "sources_unchanged": True,
    }
    save(work / "constraints-result.json", result)
    print(
        json.dumps(
            {
                "phase": "constraints",
                "structure": structure,
                "negative_cases": len(passed),
                "positive_cases": 4,
            }
        ),
        flush=True,
    )


def execute_case(cursor, sql, ids, parameter):
    for statement in sql.split(";"):
        if statement.strip():
            cursor.execute(
                statement, ids[parameter]
            ) if "?" in statement else cursor.execute(statement)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    try:
        check(args.work)
    except pyodbc.Error as error:
        raise SystemExit("C11 SQLSTATE " + str(error.args[0])) from None
