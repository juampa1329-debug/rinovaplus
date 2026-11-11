"""Connected C9 UI contract checks, never against a source or C5 write target."""

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pyodbc
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.channels_ui_app import ChannelUiStore, create_channels_ui_app
from app.channels_ui_contract import principal, transaction
from app.channels_ui_profile import load_settings
from app.sql_target import connection_string
from tools.crm_extension_snapshot_v2 import PARTITION, data_signature, require
from tools.rehearse_channels_ui import admin, load, save, snapshot, source_admin
from tools.rehearse_foundation_ui import signatures


def client(settings):
    return TestClient(
        create_channels_ui_app(settings),
        base_url="http://127.0.0.1:4175",
        client=("127.0.0.1", 52000),
        headers={"X-CRM-Local": "1"},
    )


def run(work):
    state = load(work / "state.json")
    require(not (work / "checks.json").exists(), "C9_checks_already_run")
    settings = load_settings(Path(state["profile_directory"]))
    app = client(settings)
    checks = []

    def check(label, condition):
        require(condition, "C9_check_" + label)
        checks.append(label)
        save(work / "checks.json", checks)

    with admin(state["database"], state["context"], readonly=True) as connection:
        state["prepared_snapshot"] = snapshot(connection)
        state["immutable_channels"] = data_signature(
            connection.cursor(),
            [
                t
                for t in PARTITION["extension"]
                if t not in {"crm_channels.Account", "crm_channels.Audit"}
            ],
        )
        save(work / "state.json", state)
    check(
        "runtime_v2_verified",
        app.get("/api/local/runtime").json()["version"] == "cbn-ui-capabilities-v2",
    )
    caps = app.get("/api/local/runtime").json()
    check(
        "no_other_modules_or_transport",
        caps["modules"] == ["settings"]
        and not any(caps["features"].values())
        and not any(
            caps["channels"][k]
            for k in (
                "credentials",
                "providerActions",
                "externalDelivery",
                "workers",
                "publicWebhooks",
            )
        ),
    )
    accounts = app.get("/api/v1/channels").json()["channels"]
    check(
        "five_accounts_no_credentials",
        len(accounts) == 5
        and all(
            not a["credentials"] and not a["capabilities"] and a["verifiedAt"] is None
            for a in accounts
        ),
    )
    stages = app.get("/api/local/channels/stages").json()["stages"]
    check("active_stages", len(stages) > 0)
    check(
        "local_status",
        app.get("/api/v1/channels/transport/status").json()
        == {
            "outboundRecords": 1,
            "receiptRecords": 1,
            "transportEnabled": False,
            "workersEnabled": False,
        },
    )
    comments = app.get("/api/v1/social-comments?offset=0&limit=1")
    check(
        "comments_read_only_page",
        comments.status_code == 200 and len(comments.json()["comments"]) == 1,
    )
    check(
        "comments_page_validation",
        app.get("/api/v1/social-comments?offset=-1").status_code == 422,
    )
    for label, path, method in (
        ("provider_validate", "/api/v1/channels/whatsapp/validate", "POST"),
        ("provider_send", "/api/v1/channels/whatsapp/test-message", "POST"),
        ("public_webhook", "/api/webhooks/meta", "POST"),
        ("crm", "/api/local/clients", "GET"),
        ("inbox", "/api/local/inbox", "GET"),
        ("comment_reply", "/api/v1/social-comments/unknown/reply", "POST"),
    ):
        check(
            "blocked_" + label,
            app.request(
                method, path, headers={"Content-Type": "application/json"}
            ).status_code
            == 503,
        )
    for label, headers in (
        ("missing_guard", {"X-CRM-Local": ""}),
        ("remote_origin", {"Origin": "https://invalid.test"}),
        ("foreign_host", {"Host": "invalid.test"}),
    ):
        check(label, app.get("/api/v1/channels", headers=headers).status_code == 403)
    for method in ("key", "secrets", "write_secret"):
        try:
            getattr(ChannelUiStore(settings), method)(
                None,
                *(
                    ["whatsapp"]
                    if method == "secrets"
                    else ["whatsapp", "accessToken", "synthetic"]
                    if method == "write_secret"
                    else []
                ),
            )
        except HTTPException as error:
            check("blocked_store_" + method, error.status_code == 503)
        else:
            raise ValueError("C9 credential access unexpectedly available")
    denied = (
        "SELECT TOP (0) KeyId FROM crm_channels.Credential",
        "SELECT TOP (0) Nonce FROM crm_channels.Credential",
        "SELECT TOP (0) Ciphertext FROM crm_channels.Credential",
        "SELECT TOP (0) * FROM " + PARTITION["academic"][0],
        "DELETE FROM crm_channels.outbound_queue WHERE 1=0",
        "UPDATE crm_config.Configuration SET Revision=Revision WHERE 1=0",
    )
    for i, sql in enumerate(denied):
        with pyodbc.connect(
            connection_string(settings), timeout=5, autocommit=True
        ) as connection:
            try:
                connection.cursor().execute(sql)
            except pyodbc.Error as error:
                check(
                    "sql_denial_" + str(i),
                    any("(" + str(code) + ")" in str(error) for code in (229, 230)),
                )
            else:
                raise ValueError("C9 permission unexpectedly available")
    # Synthetic configuration only. No credential fields or transport action.
    before = app.get("/api/v1/channels/tiktok").json()
    body = {
        "revision": before["revision"],
        "configuration": {
            "appId": "C9_UI_REHEARSAL",
            "environment": "development",
            "initialStage": stages[0],
        },
    }
    check(
        "secret_payload_rejected",
        app.put(
            "/api/v1/channels/tiktok/draft", json={**body, "accessToken": "synthetic"}
        ).status_code
        == 422,
    )
    check(
        "inactive_stage_rejected",
        app.put(
            "/api/v1/channels/tiktok/draft",
            json={
                **body,
                "configuration": {
                    **body["configuration"],
                    "initialStage": "C9-NONEXISTENT",
                },
            },
        ).status_code
        == 422,
    )
    saved = app.put("/api/v1/channels/tiktok/draft", json=body)
    check(
        "configuration_saved",
        saved.status_code == 200 and saved.json()["revision"] == before["revision"] + 1,
    )
    check(
        "configuration_readback",
        app.get("/api/v1/channels/tiktok").json() == saved.json(),
    )
    check(
        "stale_revision_rejected",
        app.put("/api/v1/channels/tiktok/draft", json=body).status_code == 409,
    )
    body = {
        "revision": saved.json()["revision"],
        "configuration": {
            **saved.json()["configuration"],
            "callbackUrl": "https://example.invalid/c9-draft",
        },
    }
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(
            pool.map(
                lambda _: (
                    client(settings)
                    .put("/api/v1/channels/tiktok/draft", json=body)
                    .status_code
                ),
                range(2),
            )
        )
    check("concurrent_one_commit_one_conflict", sorted(statuses) == [200, 409])
    current = app.get("/api/v1/channels/tiktok").json()
    try:
        with transaction(settings, write=True) as cursor:
            cursor.execute(
                "UPDATE crm_channels.Account SET Revision=Revision+1 "
                "WHERE Channel='tiktok'"
            )
            raise RuntimeError("C9 deliberate rollback")
    except RuntimeError:
        pass
    check(
        "rollback_preserved_revision",
        app.get("/api/v1/channels/tiktok").json() == current,
    )
    q = "[" + principal(state["database"]) + "]"
    with admin(state["database"], state["context"]) as connection:
        connection.cursor().execute(
            "GRANT SELECT ON OBJECT::crm_channels.Credential (KeyId) TO " + q
        )
        try:
            check(
                "column_acl_drift_blocks_manifest_and_reads",
                app.get("/api/local/runtime").status_code == 503
                and app.get("/api/v1/channels").status_code == 503,
            )
        finally:
            connection.cursor().execute(
                "REVOKE SELECT ON OBJECT::crm_channels.Credential (KeyId) FROM " + q
            )
    check("guard_recovers_exact_acl", app.get("/api/local/runtime").status_code == 200)
    check(
        "no_store",
        app.get("/api/v1/channels").headers.get("Cache-Control") == "no-store",
    )
    finish(work)
    print(
        json.dumps({"stage": "SQL-C9", "checks": len(checks), "passed": True}),
        flush=True,
    )


def finish(work):
    state = load(work / "state.json")
    with source_admin(
        state["source_database"], state["context"], readonly=True
    ) as connection:
        require(snapshot(connection) == state["source"], "C9_C8_source_changed")
    require(
        signatures(state["context"], Path(state["runtime_directory"]))
        == state["c5_signatures"],
        "C9_C5_or_SIIE_changed",
    )
    from app.foundation import DATABASE
    from tools.rehearse_channels import c7_admin, capture
    from tools.rehearse_foundation import admin as foundation_admin

    c8 = load(Path(state["source_work"]) / "state.json")
    c7 = load(Path(c8["c7_work"]) / "state.json")
    from app.channels_catalog import metadata
    from tools.crm_extension_snapshot_v2 import sha

    with source_admin(
        state["source_database"], state["context"], readonly=True
    ) as connection:
        require(
            sha(metadata(connection.cursor())) == c8["ticket"]["catalog_sha256"],
            "C9_C8_accepted_catalog_changed",
        )
        require(
            state["source"]["journal_sha256"] == c8["ticket"]["journal_sha256"],
            "C9_C8_accepted_journal_changed",
        )
    with foundation_admin(DATABASE, state["context"], readonly=True) as connection:
        require(capture(connection) == c7["source"], "C9_full_C5_changed")
    with c7_admin(
        c8["source_ticket"]["identity"]["database"], state["context"], readonly=True
    ) as connection:
        require(capture(connection) == c8["source"], "C9_full_C7_changed")
    with admin(state["database"], state["context"], readonly=True) as connection:
        current = snapshot(connection)
        require(
            current["preservation"] == state["source"]["preservation"],
            "C9_academic_foundation_changed",
        )
        require(
            current["shape"] == state["prepared_snapshot"]["shape"],
            "C9_catalog_changed",
        )
        require(
            current["journal_sha256"] == state["source"]["journal_sha256"],
            "C9_journal_changed",
        )
        require(
            data_signature(
                connection.cursor(),
                [
                    t
                    for t in PARTITION["extension"]
                    if t not in {"crm_channels.Account", "crm_channels.Audit"}
                ],
            )
            == state["immutable_channels"],
            "C9_nonconfiguration_channels_changed",
        )
    save(
        work / "preservation-result.json",
        {
            "stage": "SQL-C9",
            "source_C8_unchanged": True,
            "source_SIIE_and_C5_unchanged": True,
            "source_C5_full_catalog_and_binary_rows_unchanged": True,
            "source_C7_full_catalog_and_binary_rows_unchanged": True,
            "trial_academic_tables": 50,
            "trial_academic_rows": 44180,
            "trial_business_rows": 203,
            "journal_rows": 7,
            "no_migrations": True,
            "nonconfiguration_channels_unchanged": True,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "finish"))
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    try:
        (run if args.action == "run" else finish)(args.work)
    except pyodbc.Error as error:
        raise SystemExit("C9 SQL error; SQLSTATE " + str(error.args[0])) from None
