"""Explicit SQL/API C12 rehearsal; never invoked by graph or memory checks."""

import argparse
import json
import uuid
from pathlib import Path

import pyodbc
from fastapi.testclient import TestClient

from app.parity_channels.api import create_app
from app.parity_channels.policy import require
from app.parity_channels.profile import connection_string
from app.parity_channels.profile import load as settings_load
from tools.channels_parity_snapshot import OLD_TABLES
from tools.parity_data import signature
from tools.rehearse_parity_repositories import admin, load, save, sources


def check(work):
    state = load(work / "state.json")
    settings = settings_load(Path(state["profile_directory"]))
    passed = []

    def expect(value, name):
        require(value, "C12_check_" + name)
        passed.append(name)
        print(json.dumps({"passed": name}), flush=True)

    headers = {
        "Authorization": "Bearer " + settings.review["api_token"],
        "X-CRM-Local": "1",
    }

    def write_headers(operation=None, revision=None):
        value = {**headers, "Idempotency-Key": operation or str(uuid.uuid4())}
        if revision:
            value["If-Match"] = revision
        return value

    with TestClient(
        create_app(settings),
        base_url="http://127.0.0.1:4176",
        client=("127.0.0.1", 10001),
    ) as client:

        def get(path):
            r = client.get(path, headers=headers)
            expect(r.status_code == 200, "read_" + path.rsplit("/", 1)[-1])
            return r.json()

        expect(
            client.get("/api/channels/secrets").status_code == 403,
            "no_capability_before_SQL",
        )
        get("/api/capabilities")
        applications = get("/api/channels/applications")["items"]
        integrations = get("/api/channels/integrations")["items"]
        expect(len(applications) >= 2 and len(integrations) >= 2, "two_mapped_drafts")
        expect(
            all(a["State"] == "draft" for a in applications)
            and all(
                i["VerifiedStatus"] == "unverified"
                and i["RequestedStatus"] == "disconnected"
                for i in integrations
            ),
            "no_grandfathered_verification",
        )
        expect(
            any(
                i["Channel"] == "tiktok" and i["ExternalAccountId"] is None
                for i in integrations
            ),
            "missing_tiktok_ID_not_fabricated",
        )
        secret = get("/api/channels/secrets")["items"]
        receipt = get("/api/channels/receipts")["items"]
        binding = get("/api/channels/bindings")["items"]
        expect(
            len(secret) == 2
            and all(s["State"] == "staged" and s["Hint"] == "****" for s in secret),
            "two_staged_secrets_safe_projection",
        )
        expect(
            all(
                k not in json.dumps(secret) + json.dumps(receipt)
                for k in (
                    "Ciphertext",
                    "Nonce",
                    "Fingerprint",
                    "KeyVersion",
                    "BodyCiphertext",
                    "BodyNonce",
                    "Payload",
                )
            ),
            "encrypted_material_not_exposed",
        )
        expect(
            len(receipt) == 1
            and receipt[0]["Authentication"] == "legacy_unverified"
            and receipt[0]["Status"] == "quarantined",
            "legacy_receipt_quarantined",
        )
        expect(len(binding) == 23, "all_source_rows_accounted")
        for resource in ("identities", "comments", "messages", "jobs", "events"):
            get("/api/channels/" + resource)
        scenario_path = work / "API-scenario.json"
        if not scenario_path.exists():
            save(
                scenario_path,
                {
                    "original": integrations[0],
                    "operation": str(uuid.uuid4()),
                    "second_operation": str(uuid.uuid4()),
                    "app_operation": str(uuid.uuid4()),
                    "suffix": uuid.uuid4().hex[:12],
                },
            )
        scenario = load(scenario_path)
        original = scenario["original"]
        iid = original["IntegrationId"]
        edit = {
            "DisplayName": "C12 local reviewed draft",
            "ApiVersion": original["ApiVersion"],
        }
        op = scenario["operation"]
        r = client.patch(
            "/api/channels/integrations/" + iid,
            headers=write_headers(op, original["RowVersion"]),
            json=edit,
        )
        expect(r.status_code == 200, "optimistic_update_committed")
        result = r.json()
        replay = client.patch(
            "/api/channels/integrations/" + iid,
            headers=write_headers(op, original["RowVersion"]),
            json=edit,
        )
        expect(
            replay.status_code == 200 and replay.json() == result,
            "same_operation_exact_replay",
        )
        conflict = client.patch(
            "/api/channels/integrations/" + iid,
            headers=write_headers(op, original["RowVersion"]),
            json={**edit, "DisplayName": "other"},
        )
        expect(conflict.status_code == 409, "operation_payload_conflict")
        stale = client.patch(
            "/api/channels/integrations/" + iid,
            headers=write_headers(revision=original["RowVersion"]),
            json=edit,
        )
        expect(stale.status_code == 409, "stale_revision_rejected")
        expect(
            get("/api/operations/" + op)["status"] == "confirmed",
            "operation_reconciliation_read",
        )
        readback = get("/api/channels/integrations/" + iid)
        expect(
            readback["DisplayName"] == edit["DisplayName"]
            and readback["RowVersion"] == result["revision"],
            "persisted_readback",
        )
        unknown = str(uuid.uuid4())
        expect(
            client.get(
                "/api/channels/integrations/" + unknown, headers=headers
            ).status_code
            == 404,
            "unknown_integration_no_fallback",
        )
        expect(
            client.patch(
                "/api/channels/integrations/" + iid,
                headers=write_headers(revision=result["revision"]),
                json={**edit, "VerifiedStatus": "verified", "InstitutionId": unknown},
            ).status_code
            == 422,
            "mass_assignment_rejected",
        )
        meta = next(a for a in applications if a["Provider"] == "meta")
        # A second explicit WhatsApp integration demonstrates the new cardinality.
        external = "001-C12-" + scenario["suffix"]
        draft = {
            "ApplicationId": meta["ApplicationId"],
            "Channel": "whatsapp",
            "DisplayName": "C12 second WhatsApp",
            "ExternalAccountId": external,
            "ApiVersion": meta["ApiVersion"],
        }
        r = client.post(
            "/api/channels/integrations",
            headers=write_headers(scenario["second_operation"]),
            json=draft,
        )
        expect(r.status_code == 200, "multiple_whatsapp_accounts")
        second = r.json()
        expect(
            get("/api/channels/integrations/" + second["id"])["ExternalAccountId"]
            == external,
            "binary_external_ID_preserved",
        )
        expect(
            client.post(
                "/api/channels/integrations", headers=write_headers(), json=draft
            ).status_code
            == 409,
            "duplicate_external_account_rejected",
        )
        expect(
            client.post(
                "/api/channels/integrations",
                headers=write_headers(),
                json={**draft, "Channel": "tiktok"},
            ).status_code
            == 422,
            "cross_provider_application_rejected",
        )
        appdraft = {
            "Provider": "meta",
            "ClientId": "001-C12-" + scenario["suffix"],
            "ApiVersion": "v23.0",
            "IssuerProfile": "meta_whatsapp",
            "RedirectUri": "https://example.invalid/c12-callback",
        }
        newop = scenario["app_operation"]
        r = client.post(
            "/api/channels/applications", headers=write_headers(newop), json=appdraft
        )
        expect(r.status_code == 200, "application_create")
        aid = r.json()["id"]
        expect(
            get("/api/channels/applications/" + aid)["State"] == "draft",
            "application_safe_defaults",
        )
        expect(
            client.post(
                "/api/channels/applications", headers=write_headers(), json=appdraft
            ).status_code
            == 409,
            "duplicate_application_rejected",
        )
    with pyodbc.connect(
        connection_string(settings), autocommit=False, timeout=5
    ) as connection:
        cursor = connection.cursor()
        for name, sql in (
            (
                "academic_read_denied",
                "SELECT TOP (0) * FROM "
                + next(t for t in OLD_TABLES if t.startswith("dbo.")),
            ),
            (
                "legacy_credential_denied",
                "SELECT TOP(0) Ciphertext FROM crm_channels.Credential",
            ),
            (
                "new_ciphertext_denied",
                "SELECT TOP(0) Ciphertext FROM crm_channels2.SecretVersion",
            ),
            (
                "receipt_body_denied",
                "SELECT TOP(0) BodyCiphertext FROM crm_channels2.WebhookReceipt",
            ),
            ("old_core_update_denied", "DELETE FROM crm.Contact WHERE 1=0"),
            (
                "new_secret_insert_denied",
                (
                    "INSERT crm_channels2.SecretVersion(InstitutionId) "
                    "SELECT InstitutionId FROM crm_channels2.Context "
                    "WHERE 1=0"
                ),
            ),
            (
                "queue_insert_denied",
                (
                    "INSERT crm_channels2.SendJob(InstitutionId) SELECT"
                    " InstitutionId FROM crm_channels2.Context WHERE "
                    "1=0"
                ),
            ),
        ):
            try:
                cursor.execute(sql)
            except pyodbc.Error as error:
                # Exact SQL native denial, not a missing table/column false positive.
                expect(
                    "(229)" in str(error.args[1]) or "(230)" in str(error.args[1]), name
                )
            else:
                raise ValueError("C12_denial_not_enforced_" + name)
            finally:
                connection.rollback()
    state["connected_checks"] = passed
    save(work / "state.json", state)
    with admin(state["database"], state["context"], True) as c:
        expect(
            signature(c.cursor(), OLD_TABLES) == state["old_data"],
            "old65_binary_rows_unchanged",
        )
    expect(
        sources(state["context"]) == state["sources"],
        "SIIE_C5_C9_C11_catalog_and_data_unchanged",
    )
    state["connected_checks"] = passed
    save(work / "state.json", state)
    print(
        json.dumps(
            {
                "phase": "API_SQL_checked",
                "checks": len(passed),
                "database": state["database"],
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, required=True)
    check(parser.parse_args().work)
