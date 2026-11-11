"""Validate C10 design/evidence offline. No CRM, ODBC, HTTP or environment IO."""

import argparse
import copy
import hashlib
import json
import re
import sys
import zipfile
from graphlib import TopologicalSorter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(value, code):
    if not value:
        raise ValueError(code)


def key_bytes(kind):
    sizes = {
        "uniqueidentifier": 16,
        "bit": 1,
        "tinyint": 1,
        "int": 4,
        "bigint": 8,
        "date": 3,
        "datetime2(7)": 8,
        "rowversion": 8,
    }
    if kind in sizes:
        return sizes[kind]
    match = re.fullmatch(r"(n?varchar|binary|varbinary)\((\d+)\)", kind)
    require(match is not None, "unbounded_or_unsupported_index_type")
    return int(match[2]) * (2 if match[1] == "nvarchar" else 1)


def fk_exists(model, table, columns, parent):
    return any(
        f["table"] == "crm_channels2." + table
        and f["columns"] == columns
        and f["references"] == "crm_channels2." + parent
        for f in model["foreign_keys"]
    )


def definition(model, ui, *, verify_sources=True):
    require(model["unit"] == ui["unit"] == "SQL-C10", "unit")
    require(model["status"] == "defined_offline_not_implemented", "design_only")
    require(
        not any(
            model["authorization"][k]
            for k in (
                "database_connections",
                "apply_migrations",
                "runtime_activation",
                "provider_calls",
            )
        ),
        "authorization_scope",
    )
    require(
        model["sql"]["minimum_major"] == 15
        and model["sql"]["institutional_compatibility"] == 150,
        "SQL2019_profile",
    )
    require(
        model["sql"]["json_type"] == "nvarchar(max)"
        and not model["sql"]["ddl_compiled"],
        "SQL2019_JSON_and_no_compilation_claim",
    )
    require(model["sql"]["max_key_bytes"] <= 900, "index_budget")
    require(
        not model["sql"]["local_engine16_compat160_is_institutional_acceptance"],
        "no_2022_acceptance_substitution",
    )
    tables = {t["name"]: t for t in model["tables"]}
    require(len(tables) == len(model["tables"]) == 24, "explicit_partition")
    require(all(n.startswith("crm_channels2.") for n in tables), "new_schema_only")
    p = model["preservation"]
    require(
        (
            p["academic_tables"],
            p["foundation_tables"],
            p["legacy_channels_tables"],
            p["new_table_count"],
            p["proposed_total_tables"],
        )
        == (50, 7, 8, 24, 89),
        "partition_counts",
    )
    require(
        not any(
            p[k]
            for k in (
                "alter_old_tables",
                "academic_foreign_keys",
                "source_or_shared_C5_C9_writes",
                "runtime_guards_changed",
                "live_reverified",
            )
        ),
        "preservation_scope",
    )
    for name, t in tables.items():
        require("InstitutionId" in t["columns"], "institution_scope")
        require(
            all(not t["columns"][c]["nullable"] for c in t["primary_key"]),
            "nullable_primary_key",
        )
        require(
            not any(t["columns"][c]["type"] == "rowversion" for c in t["primary_key"]),
            "rowversion_is_not_identity",
        )
        for index in (
            [{"columns": t["primary_key"]}]
            + [{"columns": u} for u in t["unique_keys"]]
            + t["indexes"]
        ):
            require(
                all(c in t["columns"] for c in index["columns"]), "index_unknown_column"
            )
            require(
                sum(key_bytes(t["columns"][c]["type"]) for c in index["columns"])
                <= model["sql"]["max_key_bytes"],
                "index_too_wide",
            )
        require(
            name.startswith("crm_channels2.") and t["checks"] is not None,
            "table_contract",
        )
    for f in model["foreign_keys"]:
        require(f["table"] in tables, "FK_unknown_child")
        require(
            f["on_delete"] == f["on_update"] == "NO ACTION",
            "no_cascading_history_deletion",
        )
        child = tables[f["table"]]["columns"]
        require(
            len(f["columns"]) == len(f["referenced_columns"])
            and all(c in child for c in f["columns"]),
            "FK_child_columns",
        )
        if f["references"] in tables:
            parent = tables[f["references"]]
            require(
                f["referenced_columns"]
                in [parent["primary_key"], *parent["unique_keys"]],
                "FK_nonunique_or_filtered_parent",
            )
            require(
                all(
                    child[a]["type"] == parent["columns"][b]["type"]
                    and child[a].get("collation")
                    == parent["columns"][b].get("collation")
                    for a, b in zip(f["columns"], f["referenced_columns"])
                ),
                "FK_type_mismatch",
            )
        else:
            require(
                model["external_parents"].get(f["references"])
                == f["referenced_columns"],
                "academic_or_unknown_FK",
            )
    must_bind = [
        (
            "OAuthSession",
            ["InstitutionId", "IntegrationId", "ApplicationId"],
            "Integration",
        ),
        (
            "ProviderAsset",
            ["InstitutionId", "OAuthSessionId", "IntegrationId", "ApplicationId"],
            "OAuthSession",
        ),
        (
            "ProviderOperation",
            ["InstitutionId", "EndpointId", "ApplicationId"],
            "WebhookEndpoint",
        ),
        (
            "QuotaReservation",
            ["InstitutionId", "IntegrationId", "OperationId"],
            "ProviderOperation",
        ),
        (
            "QuotaReservation",
            ["InstitutionId", "IntegrationId", "DayUtc", "Action"],
            "QuotaBucket",
        ),
        (
            "SendJob",
            ["InstitutionId", "IntegrationId", "OperationId"],
            "ProviderOperation",
        ),
        (
            "SendJob",
            ["InstitutionId", "IntegrationId", "ReservationId", "OperationId"],
            "QuotaReservation",
        ),
        (
            "WebhookEvent",
            ["InstitutionId", "ReceiptId", "EndpointId", "ApplicationId"],
            "WebhookReceipt",
        ),
        (
            "MessageRoute",
            ["InstitutionId", "IntegrationId", "QueueId", "IdentityId", "MessageId"],
            "SendJob",
        ),
    ]
    require(
        all(fk_exists(model, *entry) for entry in must_bind),
        "cross_account_provenance_FK",
    )
    units = {u["id"]: u for u in model["migration"]["units"]}
    require(
        len(units) == 5 and all(n.startswith("CBN-CHP") for n in units), "new_unit_ids"
    )
    require(
        all(d in units for u in units.values() for d in u["depends_on"]),
        "unknown_unit_dependency",
    )
    order = list(
        TopologicalSorter(
            {n: set(u["depends_on"]) for n, u in units.items()}
        ).static_order()
    )
    owner = {t: u["id"] for u in units.values() for t in u["tables"]}
    require(
        len(owner) == sum(len(u["tables"]) for u in units.values()) == len(tables)
        and set(owner) == set(tables),
        "units_exact_table_partition",
    )
    require(
        all(
            f["references"] not in tables
            or order.index(owner[f["references"]]) <= order.index(owner[f["table"]])
            for f in model["foreign_keys"]
        ),
        "FK_references_future_unit",
    )
    require(
        not model["migration"]["frozen_units_reused"]
        and not model["migration"]["apply_authorized_in_C10"],
        "no_frozen_release_reuse_or_apply",
    )
    secret = model["secret_contract"]
    require(
        secret["algorithm"] == "AES-256-GCM"
        and secret["nonce_bytes"] == 12
        and secret["tag_bytes"] == 16,
        "authenticated_encryption",
    )
    require(
        not secret["key_material_in_database"]
        and not secret["key_regenerate_if_missing"],
        "secret_key_protection",
    )
    require(secret["blank_secret_is_not_revoke"], "blank_preserves_secret")
    for owner_column in (
        "ApplicationId",
        "IntegrationId",
        "EndpointId",
        "OAuthSessionId",
        "AssetId",
    ):
        indexes = tables["crm_channels2.SecretVersion"]["indexes"]
        require(
            any(
                i["unique"]
                and i["columns"] == ["InstitutionId", owner_column, "Kind", "VersionNo"]
                and i["where"] == owner_column + " IS NOT NULL"
                for i in indexes
            ),
            "secret_owner_version_uniqueness",
        )
    require(
        "AssetId" in tables["crm_channels2.SecretVersion"]["columns"]
        and "ProviderAsset" in secret["scopes"],
        "per_page_token_owner",
    )
    require(
        tables["crm_channels2.ProviderAsset"]["mutable"] is False,
        "immutable_asset_snapshot",
    )
    require(
        "ClientSecretId" in tables["crm_channels2.OAuthSession"]["columns"]
        and "ClientSecretVersionNo" in tables["crm_channels2.OAuthSession"]["columns"],
        "OAuth_secret_pin",
    )
    oauth = model["oauth_contract"]
    require(
        0 < oauth["ttl_seconds"] <= oauth["maximum_ttl_seconds"] <= 1800
        and oauth["state_entropy_bytes"] >= 32,
        "OAuth_expiry_entropy",
    )
    require(
        oauth["browser_binding_required"]
        and all(
            k in oauth["binding"]
            for k in (
                "InstitutionId",
                "ApplicationId",
                "IntegrationId",
                "AuthSessionHash",
                "ActorRef",
                "ClientSecretId",
            )
        ),
        "OAuth_binding",
    )
    require(
        not oauth["states"]["completed"]
        and "uncertain" in oauth["states"]["exchanging"],
        "OAuth_terminal_and_unknown",
    )
    remote = model["remote_operations"]
    require(
        remote["intent_before_HTTP"]
        and not remote["hold_database_transaction_during_HTTP"]
        and remote["lease_fencing"]
        and not remote["uncertain_auto_retry"]
        and remote["new_uuid_does_not_bypass_uncertain"],
        "durable_fenced_effects",
    )
    require(
        "EffectKey" in tables["crm_channels2.ProviderOperation"]["columns"],
        "semantic_effect_identity",
    )
    webhook = model["webhook_contract"]
    require(
        webhook["signature_required"]
        and not webhook["public_default_active"]
        and not webhook["verify_token_is_POST_auth"]
        and webhook["raw_body_before_parsing"],
        "webhook_auth_default",
    )
    require(
        webhook["max_body_bytes"] <= 1000000
        and webhook["timestamp_window_seconds"] <= 300,
        "webhook_bounds",
    )
    require(
        set(webhook["headers_allowlist"]).isdisjoint(webhook["headers_forbidden"]),
        "webhook_sensitive_headers",
    )
    require(
        "SignatureSecretId" in tables["crm_channels2.WebhookReceipt"]["columns"]
        and "BodyPurgedAt" in tables["crm_channels2.WebhookReceipt"]["columns"],
        "receipt_provenance_retention",
    )
    receipt = tables["crm_channels2.WebhookReceipt"]
    require(
        receipt["columns"]["SignatureVerifiedAt"]["nullable"]
        and ["BodyKeyVersion", "BodyNonce"] not in receipt["unique_keys"]
        and any(
            i["unique"]
            and i["columns"] == ["BodyKeyVersion", "BodyNonce"]
            and i["where"] == "BodyKeyVersion IS NOT NULL AND BodyNonce IS NOT NULL"
            for i in receipt["indexes"]
        ),
        "legacy_unverified_and_multiple_receipt_purges",
    )
    tiktok = model["tiktok_contract"]
    require(
        tiktok["default_mode"] == "disabled" and tiktok["rollout_default"] == 0,
        "no_default_real_send",
    )
    require(
        not any(
            tiktok[k]
            for k in (
                "manual_attestation_is_signed_evidence",
                "diagnostic_ok_is_delivery_evidence",
                "local_stub_is_real_evidence",
            )
        ),
        "no_fabricated_evidence",
    )
    require(
        "signed_processed_real_event_evidence" in tiktok["live_gate"]
        and "quota_reservation" in tiktok["live_gate"],
        "real_gate",
    )
    require(
        tables["crm_channels2.TikTokPolicy"]["columns"]["AppReviewNotes"]["type"]
        == "nvarchar(2000)",
        "source_note_width",
    )
    require(
        model["permissions"]["no_CONTROL_or_db_owner"]
        and not model["permissions"]["source_and_C5_roles_changed"],
        "least_privilege",
    )
    require(
        model["api"]["C9_v1_unchanged"]
        and "POST integrations/{integrationId}/oauth/refresh"
        in model["api"]["planned_operations"],
        "source_refresh_and_C9_compatibility",
    )
    require(
        not any(
            model["activation"][k]
            for k in (
                "current_C5_changes",
                "current_C9_changes",
                "provider_credentials_requested",
                "public_routes_enabled",
                "workers_enabled",
                "institutional2019_acceptance",
            )
        ),
        "no_activation",
    )
    expected = {}
    expected_actions = {}
    for source in ui["sources"]:
        path = ROOT / source["path"]
        if verify_sources:
            require(digest(path) == source["sha256"], "source_inventory_pin")
        source_data = read(path)
        for field in source_data["ui_fields"] + source_data.get("ui_outputs", []):
            expected[(source["path"], field.get("id", field.get("key")))] = field
        for action in source_data["ui_actions"]:
            expected_actions[(source["path"], action.get("id", action.get("key")))] = (
                action
            )
    require(len(ui["fields"]) == len(expected) == 115, "all_source_fields_present")
    seen = set()
    dtos = model["api"]["request_dtos"]
    for field in ui["fields"]:
        key = (field["source_artifact"], field["source_id"])
        require(
            key not in seen and expected.get(key) == field["source_descriptor"],
            "source_field_descriptor_changed_or_repeated",
        )
        seen.add(key)
        require(
            not any(
                bad in json.dumps(field["source_descriptor"], ensure_ascii=False)
                for bad in ("\u00c3", "\u00c2", "\ufffd")
            ),
            "source_descriptor_UTF8",
        )
        require(field["dto"]["name"] in dtos, "field_DTO_missing")
        mode = field["binding"]["mode"]
        require(
            mode
            in (
                "sql",
                "sql_selection",
                "vault",
                "transient",
                "transient_auth",
                "derived",
                "one_time_output",
            ),
            "field_binding_mode",
        )
        for column in field["binding"]["columns"]:
            table, col = column.rsplit(".", 1)
            require(
                table in tables and col in tables[table]["columns"],
                "field_SQL_column_missing",
            )
        if "pin" in field["id"] or "current_password" in field["id"]:
            require(
                mode in ("transient", "transient_auth")
                and not field["binding"]["columns"],
                "PIN_password_must_be_transient",
            )
            require(
                field["binding"]["request"].split(".")[0] == field["dto"]["name"],
                "transient_DTO_consistency",
            )
        elif field["source_descriptor"].get("secret"):
            require(
                mode == "vault"
                or (
                    mode == "one_time_output" and field["dto"]["direction"] == "output"
                ),
                "secret_plaintext_or_dropped",
            )
        if "verify_token_once" in field["id"]:
            require(mode == "one_time_output", "verify_token_not_editable_or_replayed")
    require(seen == set(expected), "source_field_membership")
    bindings = {f["id"]: f["binding"] for f in ui["fields"]}
    require(
        bindings["meta:facebook_page_id"]["columns"]
        == ["crm_channels2.Integration.ExternalAccountId"],
        "Facebook_canonical_identity",
    )
    require(
        bindings["tiktok:tt_configured_assets"]["columns"]
        == [
            "crm_channels2.Integration.ExternalAccountId",
            "crm_channels2.Integration.BusinessAccountId",
            "crm_channels2.Integration.AdvertiserId",
        ]
        and bindings["tiktok:tt_modal_existing_token"].get("kind") == "tiktok_access"
        and bindings["tiktok:tt_modal_existing_token"].get("owner") == "Integration",
        "TikTok_display_authorities",
    )
    require(
        len(ui["actions"]) == 83 and len({a["id"] for a in ui["actions"]}) == 83,
        "all_source_actions_present",
    )
    actual_actions = {
        (a["source_artifact"], a["source_id"]): a["source_descriptor"]
        for a in ui["actions"]
    }
    require(
        actual_actions == expected_actions,
        "source_action_membership_or_descriptor_changed",
    )
    require(
        all(
            a["target_route"]
            and (a["dto"] == "local" or a["dto"] in dtos)
            and a["status"] == "planned_not_enabled"
            for a in ui["actions"]
        ),
        "action_route_DTO_or_scope",
    )
    require(
        "pyodbc" not in sys.modules and "app.config" not in sys.modules,
        "no_runtime_import",
    )
    return {
        "tables": len(tables),
        "foreign_keys": len(model["foreign_keys"]),
        "migration_units": len(units),
        "field_output_contexts": len(ui["fields"]),
        "action_instances": len(ui["actions"]),
    }


def baselines():
    files = []
    for name, archive_name in (
        ("sql_c10_input_baseline.json", "public-input-preimages.zip"),
        ("sql_c10_reference_baseline.json", "reference-preimages.zip"),
    ):
        value = read(HERE / name)
        archive = ROOT / ".local/sql-c10" / archive_name
        expected = value.get("preimages_sha256", value.get("archive_sha256"))
        require(digest(archive) == expected, "baseline_archive_pin")
        with zipfile.ZipFile(archive) as source:
            require(
                len(source.namelist()) == len(value["files"])
                and source.testzip() is None,
                "baseline_CRC_membership",
            )
            for row in value["files"]:
                p = row["path"]
                member = (
                    "reference/" + p[3:]
                    if p.startswith("../")
                    else "target/CRM_CBN/" + p
                )
                require(
                    hashlib.sha256(source.read(member)).hexdigest() == row["sha256"],
                    "baseline_preimage_hash",
                )
        files.extend(value["files"])
    require(len({r["path"] for r in files}) == len(files), "baseline_overlap")
    return len(files)


def self_test(model, ui):
    mutations = [
        (
            "scope_connect",
            lambda m, u: m["authorization"].update(database_connections=True),
        ),
        ("apply", lambda m, u: m["authorization"].update(apply_migrations=True)),
        ("runtime", lambda m, u: m["authorization"].update(runtime_activation=True)),
        ("provider", lambda m, u: m["authorization"].update(provider_calls=True)),
        ("engine", lambda m, u: m["sql"].update(minimum_major=16)),
        (
            "compatibility",
            lambda m, u: m["sql"].update(institutional_compatibility=160),
        ),
        ("native_json", lambda m, u: m["sql"].update(json_type="json")),
        ("compile_claim", lambda m, u: m["sql"].update(ddl_compiled=True)),
        ("index_budget", lambda m, u: m["sql"].update(max_key_bytes=1700)),
        (
            "academic_mutation",
            lambda m, u: m["preservation"].update(alter_old_tables=True),
        ),
        ("core_FK", lambda m, u: m["foreign_keys"][0].update(references="dbo.Student")),
        ("cascade", lambda m, u: m["foreign_keys"][0].update(on_delete="CASCADE")),
        ("cross_account", lambda m, u: m["foreign_keys"].clear()),
        (
            "unit_cycle",
            lambda m, u: m["migration"]["units"][0]["depends_on"].append("CBN-CHP005"),
        ),
        ("old_unit", lambda m, u: m["migration"]["units"][0].update(id="CBN-B011")),
        (
            "frozen_release",
            lambda m, u: m["migration"].update(frozen_units_reused=True),
        ),
        ("cipher", lambda m, u: m["secret_contract"].update(algorithm="plaintext")),
        ("nonce", lambda m, u: m["secret_contract"].update(nonce_bytes=8)),
        (
            "key_in_DB",
            lambda m, u: m["secret_contract"].update(key_material_in_database=True),
        ),
        (
            "missing_key_reset",
            lambda m, u: m["secret_contract"].update(key_regenerate_if_missing=True),
        ),
        (
            "blank_revoke",
            lambda m, u: m["secret_contract"].update(blank_secret_is_not_revoke=False),
        ),
        ("state_expiry", lambda m, u: m["oauth_contract"].update(ttl_seconds=3600)),
        (
            "state_entropy",
            lambda m, u: m["oauth_contract"].update(state_entropy_bytes=8),
        ),
        (
            "browser_binding",
            lambda m, u: m["oauth_contract"].update(browser_binding_required=False),
        ),
        (
            "state_replay",
            lambda m, u: m["oauth_contract"]["states"]["completed"].append(
                "exchanging"
            ),
        ),
        (
            "network_TX",
            lambda m, u: m["remote_operations"].update(
                hold_database_transaction_during_HTTP=True
            ),
        ),
        (
            "unknown_retry",
            lambda m, u: m["remote_operations"].update(uncertain_auto_retry=True),
        ),
        (
            "new_UUID_bypass",
            lambda m, u: m["remote_operations"].update(
                new_uuid_does_not_bypass_uncertain=False
            ),
        ),
        (
            "signature_optional",
            lambda m, u: m["webhook_contract"].update(signature_required=False),
        ),
        (
            "active_default",
            lambda m, u: m["webhook_contract"].update(public_default_active=True),
        ),
        (
            "verify_token_auth",
            lambda m, u: m["webhook_contract"].update(verify_token_is_POST_auth=True),
        ),
        (
            "parsed_signature",
            lambda m, u: m["webhook_contract"].update(raw_body_before_parsing=False),
        ),
        (
            "large_raw",
            lambda m, u: m["webhook_contract"].update(max_body_bytes=9000000),
        ),
        (
            "replay_window",
            lambda m, u: m["webhook_contract"].update(timestamp_window_seconds=3600),
        ),
        (
            "credential_header",
            lambda m, u: m["webhook_contract"]["headers_allowlist"].append(
                "authorization"
            ),
        ),
        ("live_default", lambda m, u: m["tiktok_contract"].update(default_mode="live")),
        (
            "manual_evidence",
            lambda m, u: m["tiktok_contract"].update(
                manual_attestation_is_signed_evidence=True
            ),
        ),
        (
            "diagnostic_evidence",
            lambda m, u: m["tiktok_contract"].update(
                diagnostic_ok_is_delivery_evidence=True
            ),
        ),
        (
            "stub_evidence",
            lambda m, u: m["tiktok_contract"].update(local_stub_is_real_evidence=True),
        ),
        ("CONTROL", lambda m, u: m["permissions"].update(no_CONTROL_or_db_owner=False)),
        ("C9_profile", lambda m, u: m["api"].update(C9_v1_unchanged=False)),
        ("missing_field", lambda m, u: u["fields"].pop()),
        (
            "changed_options",
            lambda m, u: u["fields"][0]["source_descriptor"].update(label="Changed"),
        ),
        ("missing_action", lambda m, u: u["actions"].pop()),
        ("real_action_claim", lambda m, u: u["actions"][0].update(status="enabled")),
    ]

    def field(u, identity):
        return next(f for f in u["fields"] if f["id"] == identity)

    mutations.extend(
        [
            (
                "wrong_Facebook_identity",
                lambda m, u: field(u, "meta:facebook_page_id")["binding"].update(
                    columns=["crm_channels2.Integration.ParentExternalId"]
                ),
            ),
            (
                "wrong_TikTok_assets",
                lambda m, u: field(u, "tiktok:tt_configured_assets")["binding"].update(
                    columns=["crm_channels2.SecretVersion.Hint"]
                ),
            ),
            (
                "wrong_hint_owner",
                lambda m, u: field(u, "tiktok:tt_modal_existing_token")[
                    "binding"
                ].update(owner="Application"),
            ),
            (
                "wrong_transient_DTO",
                lambda m, u: field(u, "meta:meta_secret_rotation_current_password")[
                    "binding"
                ].update(request="UnknownIn.current_password"),
            ),
            (
                "nullable_nonce_UQ",
                lambda m, u: next(
                    t for t in m["tables"] if t["name"].endswith(".WebhookReceipt")
                )["unique_keys"].append(["BodyKeyVersion", "BodyNonce"]),
            ),
            (
                "fabricated_legacy_verified_at",
                lambda m, u: next(
                    t for t in m["tables"] if t["name"].endswith(".WebhookReceipt")
                )["columns"]["SignatureVerifiedAt"].update(nullable=False),
            ),
            (
                "FK_collation",
                lambda m, u: next(
                    t for t in m["tables"] if t["name"].endswith(".WebhookEvent")
                )["columns"]["RouteExternalId"].pop("collation"),
            ),
        ]
    )
    for label, mutate in mutations:
        m, u = copy.deepcopy(model), copy.deepcopy(ui)
        mutate(m, u)
        try:
            definition(m, u)
        except (ValueError, KeyError):
            pass
        else:
            raise AssertionError("Accepted unsafe design: " + label)
    return len(mutations)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    model, ui = (
        read(HERE / "channels-parity-contract.json"),
        read(HERE / "channels-ui-parity-contract.json"),
    )
    result = definition(model, ui)
    result["baseline_inputs"] = baselines()
    result["negative_designs_rejected"] = self_test(model, ui) if args.self_test else 0
    result["scope"] = "offline_definition_only_no_SQL_or_provider_acceptance"
    print(json.dumps(result))


if __name__ == "__main__":
    main()
