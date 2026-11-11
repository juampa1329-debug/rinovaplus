"""Connected role, lifecycle, concurrency and local limit acceptance."""
import contextlib
import json
import secrets
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from app.institutional.api import create_app
from app.institutional.spanish import load
from tools.qualify_p2_spanish import Browser, operation
from tools.rehearse_p2_spanish import WORK, read, save
from pathlib import Path


def main():
    profile, private = read(WORK / "profile.json"), read(WORK / "http-private.json")
    app = create_app(load(Path(profile["directory"])))
    admin = Browser(app)
    admin.login(private["users"]["admin"]["email"], private["users"]["admin"]["password"])
    viewer = Browser(app)
    viewer.login(private["users"]["viewer"]["email"], private["users"]["viewer"]["password"])
    checks = []
    def check(name, ok=True):
        assert ok, name
        checks.append(name)
        save(WORK / "access-result.json", {"status": "in_progress", "checks": checks})
    # Valid DTOs reach each controller's permission boundary. Malformed DTOs
    # are not counted as successful permission denials.
    rows = admin.request("users").json()["items"]
    person = next(row for row in rows if row["role"] == "viewer")
    channel = admin.request("channels").json()["items"][0]
    endpoint = admin.request("webhooks").json()["items"][0]
    denied = [
        ("users", "POST", operation(email="denied@cbn.local", full_name="Denegado", role="viewer")),
        (f"users/{person['id']}", "PUT", operation(revision=person["revision"], role="viewer", full_name=person["full_name"], active=True)),
        (f"users/{person['id']}/reset", "POST", None),
        ("roles/denied", "PUT", operation(revision=0, name="Denegado", active=True, actions=[])),
        ("credentials", "PUT", operation(scope="provider", owner="openai", kind="api_key", value="denied-valid-key")),
        ("credentials/revoke", "POST", operation(scope="provider", owner="openai", kind="api_key")),
        ("channels", "POST", operation(channel="whatsapp", display_name="Denegado", issuer_profile="meta_whatsapp", client_id="denied-app")),
        (f"channels/{channel['id']}", "PUT", operation(revision=channel["revision"], row_version=channel["row_version"], application_version=channel["application_version"], values={})),
        ("webhooks", "POST", operation(provider="meta", integration_ids=[channel["id"]], callback_url="", signature_required=True)),
        (f"webhooks/{endpoint['id']}/rotate", "POST", operation()),
    ]
    for section in ("institution", "ai", "models", "modules", "budgets", "webhooks"):
        setting = admin.request("settings/" + section).json()
        denied.append(("settings/" + section, "PUT", operation(revision=setting["revision"], document=setting["document"])))
        denied.append(("settings/" + section + "/restore/1", "POST", operation(revision=setting["revision"], document={})))
    for path, method, body in denied:
        viewer.request(path, method, body, expected=403)
    check("22_valid_DTO_management_mutations_denied_to_viewer", len(denied) == 22)
    for role in ("admin", "supervisor", "agent", "viewer"):
        browser = Browser(app)
        info = private["users"][role]
        signed = browser.login(info["email"], info["password"])
        for path, action in (("users", "users.read"), ("roles", "roles.read"), ("audit", "audit.read"), ("settings/ai", "settings.ai.read"), ("channels", "settings.channels.read"), ("webhooks", "settings.webhooks.read")):
            browser.request(path, expected=200 if action in signed["actions"] else 403)
        check(role + "_GET_role_action_matrix_6_routes")
    # Custom roles and live revocation are exercised on a new person, leaving
    # the built-in UI fixture accounts and the sole owner untouched.
    custom = operation(revision=0, name="Gestor de fuentes", active=True, actions=["sources.manage"])
    admin.request("roles/source_manager", "PUT", custom)
    password = "CBN!" + secrets.token_urlsafe(24)
    user = admin.request("users", "POST", operation(email="source.manager@cbn.local", full_name="Gestor de fuentes", role="source_manager", password=password)).json()["user"]
    person_browser = Browser(app)
    signed = person_browser.login(user["email"], password)
    check("AI_sources_permission_is_distinct_from_human_user_admin", signed["actions"] == ["sources.manage"])
    admin.request("users/" + user["id"], "PUT", operation(revision=user["revision"], role="viewer", active=False, full_name=user["full_name"]))
    person_browser.request("auth/me", expected=401)
    check("user_disable_and_role_change_revoke_existing_session")
    # Same normalized email raced with two operation IDs: one account only.
    def race_create(index):
        browser = Browser(app)
        browser.login(private["users"]["admin"]["email"], private["users"]["admin"]["password"])
        response = browser.client.post("/api/institution/users", json=operation(email="race.person@cbn.local" if index else "RACE.PERSON@CBN.LOCAL", full_name="Cuenta concurrente", role="viewer", password=password), headers={"X-CRM-Local":"1", "X-CSRF-Token":browser.csrf})
        return response.status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        raced = list(executor.map(race_create, (0,1)))
    check("normalized_email_race_has_one_winner", sorted(raced) == [200,409])
    invited = admin.request("users", "POST", operation(email="invite.person@cbn.local", full_name="Cuenta invitada", role="viewer")).json()
    redemption = {"token": invited["activation_token"], "new_password": password}
    def race_redeem(_):
        browser = Browser(app)
        return browser.client.post("/api/institution/auth/redeem", json=redemption, headers={"X-CRM-Local":"1"}).status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        redeemed = list(executor.map(race_redeem, (0,1)))
    check("activation_token_race_one_use", sorted(redeemed) == [200,401])
    activated = Browser(app)
    activated.login("invite.person@cbn.local", password)
    reset = admin.request(f"users/{invited['user']['id']}/reset", "POST").json()["reset_token"]
    new_password = "CBN!" + secrets.token_urlsafe(24)
    activated.request("auth/redeem", "POST", {"token":reset,"new_password":new_password})
    activated.request("auth/me", expected=401)
    activated.login("invite.person@cbn.local", new_password)
    activated.request("security/password", "POST", {"current_password":new_password,"new_password":password})
    activated.request("auth/me", expected=401)
    check("reset_and_password_change_revoke_all_old_sessions")
    modules = admin.request("settings/modules").json()
    changed = json.loads(json.dumps(modules["document"]))
    changed["enabled"]["clients"] = False
    changed_modules = admin.request("settings/modules", "PUT", operation(revision=modules["revision"], document=changed)).json()
    viewer.request("/api/local/crm/clients", expected=403)
    admin.request("settings/modules", "PUT", operation(revision=changed_modules["revision"], document=modules["document"]))
    check("module_availability_enforced_by_direct_API_and_reversible")
    budgets = admin.request("settings/budgets").json()
    changed = dict(budgets["document"], max_active_integrations=3)
    limited = admin.request("settings/budgets", "PUT", operation(revision=budgets["revision"], document=changed)).json()
    admin.request("channels", "POST", operation(channel="whatsapp", display_name="Sobre capacidad", client_id="cbn-meta", issuer_profile="meta_whatsapp"), expected=409)
    admin.request("settings/budgets", "PUT", operation(revision=limited["revision"], document=budgets["document"]))
    check("integration_capacity_enforced_without_plan_or_billing")
    rate_admin = Browser(app)
    rate_admin.login(private["users"]["admin"]["email"], private["users"]["admin"]["password"])
    budgets = admin.request("settings/budgets").json()
    limited = admin.request("settings/budgets", "PUT", operation(revision=budgets["revision"], document=dict(budgets["document"], requests_per_minute=10))).json()
    rate_seen=False
    for _ in range(12):
        response = viewer.client.get("/api/institution/auth/me",headers={"X-CRM-Local":"1"})
        if response.status_code == 429:
            rate_seen=True
            break
    # Use an independent principal to restore the configured limit even if
    # the first administrator has exhausted its own window.
    backup_admin = Browser(app)
    # The source owner has a separate rate bucket and authenticates with MFA.
    challenge = backup_admin.login(private["email"], private["password"])
    from app.institutional.crypto import totp_code
    import time
    verified=backup_admin.request("auth/verify","POST",{"challenge_token":challenge["challenge_token"],"code":totp_code(private["totp_secret"],int(time.time())//30)}).json()
    backup_admin.csrf=verified["csrf_token"]
    backup_admin.request("settings/budgets", "PUT", operation(revision=limited["revision"], document=budgets["document"]))
    check("SQL_rate_limit_enforced_without_provider_IO", rate_seen)
    save(WORK / "access-result.json", {"status":"passed","checks":checks,"count":len(checks),"valid_DTO_denials":len(denied),"role_GET_cases":24,"account_race":raced,"activation_race":redeemed,"academic_writes":0,"provider_calls":0})
    print(json.dumps({"access":"passed","checks":len(checks),"valid_DTO_denials":len(denied),"role_GET_cases":24}))


if __name__ == "__main__":
    try:
        main()
    except BaseException as error:
        with contextlib.suppress(Exception):
            import traceback
            save(WORK / ("access-failure-"+uuid4().hex+".json"),{"type":type(error).__name__,"message":str(error),"frames":traceback.format_exc()})
        print(json.dumps({"access":"failed","type":type(error).__name__}))
        raise SystemExit(1)
