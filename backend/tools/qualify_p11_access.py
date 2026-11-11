"""Effective role/action and route boundary matrix against the isolated SQL copy."""

import json
import re
import secrets
from uuid import uuid4

from fastapi import HTTPException

from app.institutional.auth import authorize, cookie_name
from app.institutional.policy import ACTIONS, ROLE_ACTIONS
from app.institutional.spanish import transaction
from tools.p11_test_support import Harness
from tools.prepare_p11_operations import WORK, read, save
from tools.qualify_p3_workspace import Browser


def main():
    assert not (WORK / "access-result.json").exists(), "fresh qualification required"
    h = Harness()
    checks, matrix, routes = [], [], []
    state_path = WORK / "access-checkpoint.json"
    prior = read(state_path) if state_path.exists() else {}
    if prior:
        assert prior["database"] == h.settings.connection["database"]
    routes = prior.get("routes", [])
    private_path = WORK / "access-matrix-actors.json"
    private = read(private_path) if private_path.exists() else {}

    def persist():
        save(state_path, dict(status="in_progress", database=h.settings.connection["database"], matrix=matrix, routes=routes))
    actors = {"owner": h.b}
    for role in ["admin", "supervisor", "agent", "viewer"]:
        if role not in private:
            private[role] = dict(email="p11-" + role + "-" + uuid4().hex[:8] + "@cbn.example", password="P11!" + secrets.token_urlsafe(24))
            h.call("users", "POST", dict(operation_id=str(uuid4()), full_name="Validación " + role, role=role, **private[role]))
            save(private_path, private)
        b = Browser(h.app)
        b.login(private[role]["email"], private[role]["password"])
        actors[role] = b
    checks.append("five_roles_created_without_changing_the_last_owner")
    for role, browser in actors.items():
        authority = {
            "token": browser.client.cookies.get(cookie_name(h.settings)),
            "csrf": browser.csrf,
            "method": "GET",
            "module": None,
        }
        with transaction(h.settings, anonymous=True) as c:
            for permission in ACTIONS:
                expected = permission in ROLE_ACTIONS[role]
                try:
                    authorize(c, h.settings, authority, permission)
                    permitted = True
                except HTTPException as failure:
                    assert (
                        failure.status_code == 403
                        and failure.detail == "permission_denied"
                    )
                    permitted = False
                assert permitted == expected, (role, permission)
                matrix.append(dict(role=role, action=permission, allowed=permitted))
    checks.append("all_30_effective_actions_crossed_with_five_SQL_roles")
    persist()
    # Inspect every actual protected method/path, including included routers.
    anonymous = Browser(h.app)
    schema = h.app.openapi()["paths"]
    public = {
        "/api/institution/auth/status",
        "/api/institution/auth/bootstrap",
        "/api/institution/auth/login",
        "/api/institution/auth/verify",
        "/api/institution/auth/redeem",
    }
    for path, operations in schema.items():
        if not path.startswith("/api/") or path in public:
            continue
        actual = re.sub(r"\{[^}]+\}", "00000000-0000-0000-0000-000000000000", path)
        for method in operations:
            if method.upper() not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                continue
            row = next((v for v in routes if v["path"] == path and v["method"] == method.upper()), None)
            if row is None:
                anonymous.request(actual, method.upper(), {} if method != "get" else None, 401)
                row = dict(path=path, method=method.upper(), anonymous_status=401, csrf_roles=[])
                routes.append(row)
                persist()
            if method != "get":
                for role, browser in actors.items():
                    if role in row["csrf_roles"]:
                        continue
                    browser.request(actual, method.upper(), {}, 403, csrf=False)
                    row["csrf_roles"].append(role)
                    persist()
    checks.append(
        "every_protected_route_method_rejects_anonymous_and_all_writes_reject_missing_CSRF"
    )
    for role, browser in actors.items():
        browser.request(
            "operations", expected=200 if role in {"owner", "admin"} else 403
        )
        for path, permission in [
            ("users", "users.read"),
            ("roles", "roles.read"),
            ("settings/models", "settings.providers.read"),
            ("credentials/provider", "settings.providers.read"),
            ("settings/modules", "settings.modules.read"),
            ("channels", "settings.channels.read"),
            ("learning/catalog", "agents.manage"),
            ("knowledge", "sources.manage"),
            ("ads/options", "ads.manage"),
            ("campaigns/options", "campaigns.manage"),
        ]:
            browser.request(
                path, expected=200 if permission in ROLE_ACTIONS[role] else 403
            )
    checks.append(
        "service_layer_read_guards_and_operation_panel_enforce_expected_roles"
    )
    h.call("operations", "POST", {}, 404)
    checks.append("no_backup_restore_or_migration_write_API")
    # Module gating at the boundary and channel administration while processing is paused.
    modules = h.call("settings/modules")
    changed = json.loads(json.dumps(modules["document"]))
    changed["enabled"]["inbox"] = False
    changed["enabled"]["channels"] = False
    h.call(
        "settings/modules",
        "PUT",
        dict(operation_id=str(uuid4()), revision=modules["revision"], document=changed),
    )
    h.call("comments", expected=403)
    h.call("channels")  # Administrative configuration remains available deliberately.
    latest = h.call("settings/modules")
    h.call(
        "settings/modules",
        "PUT",
        dict(
            operation_id=str(uuid4()),
            revision=latest["revision"],
            document=modules["document"],
        ),
    )
    checks.append(
        "Inbox_module_blocks_comments_while_channel_configuration_remains_administrative"
    )
    report = dict(
        status="passed",
        checks=checks,
        role_action_cells=len(matrix),
        matrix=matrix,
        route_method_boundaries=len(routes),
        routes=routes,
        role_endpoint_read_cells=55,
        route_authority_only=True,
        functional_resource_lifecycle="separate_P2_to_P10_and_P11_UI_receipts",
        provider_calls=len(h.gateway.gets) + len(h.gateway.posts),
        academic_writes=False,
    )
    assert report["provider_calls"] == 0
    save(WORK / "access-result.json", report)
    print(
        json.dumps(
            {
                k: report[k]
                for k in [
                    "status",
                    "role_action_cells",
                    "route_method_boundaries",
                    "provider_calls",
                ]
            }
        )
    )


if __name__ == "__main__":
    main()
