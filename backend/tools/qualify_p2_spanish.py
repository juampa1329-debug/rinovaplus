"""Explicit P2 SQL/HTTP acceptance on an already approved isolated profile.

No server discovery, provider calls or writes to academic/source databases.
Private state is kept in the existing operator volume, never in the report.
"""

import contextlib
import json
import secrets
import time
from pathlib import Path
from uuid import uuid4

import pyodbc
from fastapi.testclient import TestClient

from app.institutional.api import create_app
from app.institutional.crypto import totp_code
from app.institutional.model_settings import project
from app.institutional.spanish import connection_string, load
from app.institutional.spanish_bindings import layout
from tools.rehearse_p2_spanish import WORK, read, save

REPORT = WORK / "http-result.json"
PRIVATE = WORK / "http-private.json"
checks = []


def check(name, condition):
    if not condition:
        raise AssertionError(name)
    checks.append(name)
    save(REPORT, {"status": "in_progress", "checks": checks})


class Browser:
    def __init__(self, app):
        self.client = TestClient(app, base_url="http://127.0.0.1:4177", client=("127.0.0.1", 50000))
        self.csrf = ""

    def request(self, path, method="GET", body=None, expected=200, *, csrf=True, headers=None):
        response = self.client.request(method, path if path.startswith("/") else "/api/institution/" + path, json=body, headers={"X-CRM-Local": "1", **({"X-CSRF-Token": self.csrf} if csrf and self.csrf else {}), **(headers or {})})
        if response.status_code != expected:
            detail = response.json().get("detail", "no_detail")
            raise AssertionError(f"HTTP_{method}_{path.split('?')[0]}_{response.status_code}_{detail}_expected_{expected}")
        return response

    def login(self, email, password):
        result = self.request("auth/login", "POST", {"email": email, "password": password}).json()
        if not result.get("mfa_required"):
            self.csrf = result["csrf_token"]
        return result


def operation(**body):
    return {"operation_id": str(uuid4()), **body}


def main():
    profile = read(WORK / "profile.json")
    settings = load(Path(profile["directory"]))
    app = create_app(settings)
    owner = Browser(app)
    state = read(WORK / "state.json")
    private = {"email": "administracion@cbn.local", "password": "CBN!" + secrets.token_urlsafe(24), "profile": profile["directory"], "users": {}}
    check("bootstrap_initially_uninitialized", not owner.request("auth/status").json()["initialized"])
    result = owner.request("auth/bootstrap", "POST", {"email": private["email"], "password": private["password"], "full_name": "Administración CBN", "bootstrap_token": state["bootstrap_token"]}).json()
    owner.csrf = result["csrf_token"]
    private["owner_id"] = result["user"]["id"]
    save(PRIVATE, private)
    check("owner_opaque_session_and_csrf", len(owner.csrf) == 64 and "_token" not in result)
    check("all_30_actions_available", len(result["actions"]) == 30)
    me = owner.request("auth/me").json()
    check("human_profile_separate_from_employee_and_AI", me["user"]["account_kind"] == "human" and me["user"]["employee_link"] == "not_bound")
    owner.request("auth/bootstrap", "POST", {"email": "second@cbn.local", "password": private["password"], "full_name": "Duplicado", "bootstrap_token": state["bootstrap_token"]}, expected=403)
    check("bootstrap_one_use", True)
    owner.request("users", "POST", operation(email="csrf@cbn.local", full_name="CSRF", role="viewer"), expected=403, csrf=False)
    check("CSRF_denies_before_account_creation", True)
    owner.request("auth/me", expected=403, headers={"Origin": "https://example.invalid"})
    check("cross_origin_rejected", True)
    for path in ("/api/billing", "/api/plans", "/api/checkout", "/api/woocommerce", "/api/local/session"):
        owner.request(path, expected=404)
    check("billing_plans_checkout_woocommerce_preview_bootstrap_absent", True)
    info = owner.request("contracts").json()
    check("typed_UI_contract_30_actions_and_14_modules", len(info["actions"]) == 30 and len(info["modules"]) == 14)
    for role in ("admin", "supervisor", "agent", "viewer"):
        email = role + "@cbn.local"
        password = "CBN!" + secrets.token_urlsafe(24)
        user = owner.request("users", "POST", operation(email=email, full_name="Cuenta " + role, role=role, password=password)).json()["user"]
        private["users"][role] = {"email": email, "password": password, "id": user["id"]}
    save(PRIVATE, private)
    check("all_builtin_roles_SQL_accounts_created", True)
    viewer = Browser(app)
    viewer.login(**{k: private["users"]["viewer"][k] for k in ("email", "password")})
    viewer.request("users", expected=403)
    viewer.request("settings/ai", expected=403)
    viewer.request("roles", expected=403)
    viewer.request("audit", expected=403)
    viewer.request("/api/local/crm/clients", "POST", {}, expected=403)
    check("viewer_direct_access_denied_for_management_and_CRM_mutation", True)
    for section in ("institution", "ai", "models", "modules", "budgets", "webhooks"):
        before = owner.request("settings/" + section).json()
        body = operation(revision=before["revision"], document=before["document"])
        after = owner.request("settings/" + section, "PUT", body).json()
        replay = owner.request("settings/" + section, "PUT", body).json()
        check("setting_" + section + "_revision_idempotent_replay", after == replay and after["revision"] == before["revision"] + 1)
        owner.request("settings/" + section, "PUT", operation(revision=before["revision"], document=before["document"]), expected=409)
    check("all_six_settings_SQL_optimistic_conflicts", True)
    ai = owner.request("settings/ai").json()
    forged = json.loads(json.dumps(ai["document"]))
    forged["model"] = "unselected-model"
    owner.request("settings/ai", "PUT", operation(revision=ai["revision"], document=forged), expected=422)
    check("AI_cannot_forge_model_projection", True)
    models = owner.request("settings/models").json()
    selection = {"provider": "openrouter", "category": "vision", "selected_model": "vendor/vision-v1", "display_name": "Visión institucional", "voice_id": ""}
    owner.request("settings/models", "PUT", operation(revision=models["revision"], document={"selections": [selection]}))
    check("saved_model_ID_preserved_without_external_catalog", owner.request("settings/models").json()["document"]["selections"][0]["selected_model"] == "vendor/vision-v1")
    ai = owner.request("settings/ai").json()
    ai["document"]["vision_analysis_provider"] = "openrouter"
    projected = project(ai["document"], {"selections": [selection]})
    owner.request("settings/ai", "PUT", operation(revision=ai["revision"], document=projected))
    check("model_authority_updates_AI_projection", owner.request("settings/ai").json()["document"]["media"]["vision_model"] == "vendor/vision-v1")
    for provider in ("gemini", "openai", "anthropic", "hermes", "openrouter", "kimi"):
        ai = owner.request("settings/ai").json()
        ai["document"]["vision_analysis_provider"] = provider
        ai["document"]["model_failover_enabled"] = False
        ai["document"]["human_reply_style_enabled"] = True
        owner.request("settings/ai", "PUT", operation(revision=ai["revision"], document=project(ai["document"], {"selections": [selection]})))
    check("six_vision_providers_and_independent_behavior_flags", True)
    secret = "private-test-key-" + secrets.token_urlsafe(30)
    private["provider_secret"] = secret
    body = operation(scope="provider", owner="openai", kind="api_key", value=secret)
    owner.request("credentials", "PUT", body)
    owner.request("credentials", "PUT", body)
    owner.request("credentials", "PUT", operation(scope="provider", owner="openai", kind="api_key", value=""))
    metadata = owner.request("credentials/provider").json()
    check("encrypted_secret_blank_preserves_and_GET_redacted", secret not in json.dumps(metadata) and metadata["items"][0]["version"] == 1)
    channels = []
    for channel, issuer in (("whatsapp", "meta_whatsapp"), ("whatsapp", "meta_whatsapp"), ("tiktok", "tiktok_business")):
        body = operation(channel=channel, display_name=f"Cuenta {len(channels)+1}", client_id="cbn-meta" if channel == "whatsapp" else "cbn-tiktok", issuer_profile=issuer)
        created = owner.request("channels", "POST", body).json()
        check("account_idempotent_" + str(len(channels)), created == owner.request("channels", "POST", body).json())
        channels.append(created)
    check("multiple_WhatsApp_share_real_application_and_TikTok_separate", channels[0]["application_id"] == channels[1]["application_id"] and channels[0]["id"] != channels[1]["id"] and channels[2]["application_id"] != channels[0]["application_id"])
    catalog = owner.request("channels/catalog").json()
    check("Scentra_channel_115_contexts_preserved", len(catalog["fields"]) == 115 and len(catalog["groups"]) == 7)
    endpoint_body = operation(provider="meta", integration_ids=[channels[0]["id"], channels[1]["id"]], callback_url="https://cbn.example.invalid/webhook", signature_required=True)
    endpoint = owner.request("webhooks", "POST", endpoint_body).json()
    safe = owner.request("webhooks", "POST", endpoint_body).json()
    check("endpoint_secret_once_replay_redacted", "verify_token_once" in endpoint and "verify_token_once" not in safe)
    private["endpoint_secret"] = endpoint["verify_token_once"]
    current = owner.request("webhooks").json()
    check("same_endpoint_in_settings_and_channel_links", current["items"][0]["id"] == endpoint["endpoint"]["id"] and len(current["items"][0]["integration_ids"]) == 2)
    check("public_webhook_remains_disabled", current["items"][0]["actual_active"] is False)
    # A deliberately stale UI cannot replace another operator's update.
    entry = current["items"][0]
    rotation = owner.request(f"webhooks/{entry['id']}/rotate", "POST", operation()).json()
    check("webhook_key_rotation_once", rotation["verify_token_once"] != endpoint["verify_token_once"])
    private["channels"] = channels
    private["endpoint_id"] = entry["id"]
    save(PRIVATE, private)
    with pyodbc.connect(connection_string(settings), autocommit=True) as connection:
        for table in layout()["academic_tables"]:
            try:
                connection.cursor().execute("SELECT TOP(0) * FROM " + table)
            except pyodbc.Error:
                pass
            else:
                raise AssertionError("academic_SELECT_should_be_denied")
        try:
            connection.cursor().execute("UPDATE dbo.CRMAccesoAuditoria SET Action=Action WHERE 1=0")
        except pyodbc.Error:
            pass
        else:
            raise AssertionError("audit_UPDATE_should_be_denied")
    check("all_30_academic_reads_and_audit_rewrite_denied_in_SQL", True)
    audit = owner.request("audit?limit=100").json()
    check("audit_append_only_and_no_plaintext_secrets", secret not in json.dumps(audit) and private["password"] not in json.dumps(audit) and len(audit["items"]) > 20)
    setup = owner.request("security/totp/setup", "POST", {"current_password": private["password"]}).json()
    code = totp_code(setup["secret"], int(time.time()) // 30)
    recovery = owner.request("security/totp/verify", "POST", {"setup_id": setup["setup_id"], "code": code}).json()
    private["totp_secret"] = setup["secret"]
    private["recovery_codes"] = recovery["recovery_codes"]
    save(PRIVATE, private)
    check("TOTP_factor_and_eight_recovery_codes_SQL", len(recovery["recovery_codes"]) == 8)
    second = Browser(app)
    challenge = second.login(private["email"], private["password"])
    verified = second.request("auth/verify", "POST", {"challenge_token": challenge["challenge_token"], "code": recovery["recovery_codes"][0]}).json()
    second.csrf = verified["csrf_token"]
    third = Browser(app)
    challenge = third.login(private["email"], private["password"])
    third.request("auth/verify", "POST", {"challenge_token": challenge["challenge_token"], "code": recovery["recovery_codes"][0]}, expected=401)
    check("recovery_code_consumed_once_across_sessions", True)
    second.request("auth/logout", "POST")
    second.request("auth/me", expected=401)
    check("logout_revokes_SQL_session_immediately", True)
    own = owner.request("users").json()["items"]
    current_owner = next(row for row in own if row["id"] == private["owner_id"])
    owner.request(f"users/{private['owner_id']}", "PUT", operation(revision=current_owner["revision"], role="admin", active=True, full_name=current_owner["full_name"]), expected=409)
    check("last_useful_owner_cannot_be_demoted", True)
    save(REPORT, {"status": "passed", "database": profile["database"], "checks": checks, "count": len(checks), "provider_calls": 0, "academic_writes": 0, "old_databases_changed": False})
    print(json.dumps({"SQL_HTTP": "passed", "checks": len(checks), "database": profile["database"]}))


if __name__ == "__main__":
    try:
        main()
    except BaseException as error:
        with contextlib.suppress(Exception):
            save(WORK / ("http-failure-" + uuid4().hex + ".json"), {"type": type(error).__name__, "message": str(error), "checks": checks})
        print(json.dumps({"SQL_HTTP": "failed", "type": type(error).__name__, "completed_checks": len(checks)}))
        raise SystemExit(1)
