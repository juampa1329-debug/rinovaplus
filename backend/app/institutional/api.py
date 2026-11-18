"Institutional HTTP boundary. No owner-preview cookie, startup DDL or provider IO."

import logging
import os
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.routing import compile_path

from app.branding import PRODUCT_DESCRIPTION, PRODUCT_NAME
from app.institutional import deployment, models
from app.institutional.auth import Identity, cookie_name
from app.institutional.db import audit
from app.institutional.management import Management
from app.institutional.policy import request_authority
from app.institutional.settings import Settings
from app.institutional.store import Workspace, load, transaction
from app.modules.clients.api.router import install_clients
from app.modules.crm_configuration.application.service import install_crm_configuration
from app.modules.inbox.application.service import install_inbox

PUBLIC = {
    "/api/institution/auth/status",
    "/api/institution/auth/bootstrap",
    "/api/institution/auth/login",
    "/api/institution/auth/verify",
    "/api/institution/auth/redeem",
    "/api/institution/auth/recover-email",
}


def core_permission(path, method):
    if path.startswith("/api/institution/notifications"):
        return "self", None
    if path == "/api/institution/operations":
        return "users.manage", None
    if path.startswith("/api/institution/provider-catalog/"):
        return "settings.providers.read", "settings"
    if path.startswith('/api/institution/learning'):
        return 'agents.manage', 'intelligence'
    if path.startswith("/api/institution/ads"):
        return "ads.manage", "ads"
    if path.startswith("/api/institution/campaigns"):
        return "campaigns.manage", "campaigns"
    if path.startswith("/api/institution/broadcasts"):
        return "campaigns.manage", "broadcasts"
    if path.startswith("/api/institution/knowledge"):
        return "sources.manage", "knowledge"
    if path.startswith("/api/institution/memory"):
        return "sources.manage", "memory"
    if path.startswith("/api/institution/conversation-memory/"):
        return "inbox." + ("read" if method == "GET" else "write"), "inbox"
    if path.startswith("/api/v1/agents"):
        if "/conversations/" in path or path.endswith("/selection"):
            return "inbox." + ("read" if method == "GET" else "write"), "inbox"
        if "/sources/" in path:
            return "sources.manage", "agents"
        return "agents.manage", "agents"
    if path.startswith("/api/institution/media/"):
        return "inbox." + ("read" if method == "GET" else "write"), "inbox"
    if path.startswith("/api/institution/comments"):
        return "inbox." + ("read" if method == "GET" else "write"), "inbox"
    if path.startswith("/api/institution/workspace/"):
        local = path.removeprefix("/api/institution/workspace/")
        if local == "policy":
            return "settings.crm." + (
                "read" if method == "GET" else "write"
            ), "settings"
        inbox = local.startswith("inbox") or (
            local.startswith("conversations/")
            and (local.endswith(("/messages", "/social-profile")) or method != "GET")
            and not local.endswith("/manual")
        )
        return ("inbox." if inbox else "crm.") + (
            "read" if method == "GET" else "write"
        ), "inbox" if inbox else "clients"
    if path.startswith("/api/local/crm/configuration"):
        return "settings.crm." + ("read" if method == "GET" else "write"), "settings"
    if path.startswith("/api/local/crm/inbox") or "/conversations/" in path:
        if method == "PUT" and "/contacts/" in path:
            return "crm.write", "inbox"
        return "inbox." + ("read" if method == "GET" else "write"), "inbox"
    if path.startswith("/api/local/crm"):
        return "crm." + ("read" if method == "GET" else "write"), "clients"
    return "self", None


def create_app(
    settings, workspace=None, agent_gateway_factory=None, broadcast_gateway=None,
    *, channel_transport=None, media_downloader=None,
):
    app = FastAPI(
        title=PRODUCT_NAME,
        description=PRODUCT_DESCRIPTION,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    protected_routes = []
    app.state.settings = SimpleNamespace(mode="local_foundation")
    postgres = getattr(settings, "postgres_profile", False)
    rehearsal = postgres and not getattr(settings, "postgres_deployment", False)
    is_operational = getattr(settings, "ticket", {}).get("version") in {
        "cbn-institutional-channels-p4-v1",
        "cbn-institutional-agents-p5-v1",
        "cbn-institutional-knowledge-p6-v1",
        "cbn-institutional-broadcast-p7-v1",
        "cbn-institutional-campaign-p8-v1",
        "cbn-institutional-ads-p9-v1",
    'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}
    if is_operational:
        from app.institutional.channel_workers import lifespan

        app.router.lifespan_context = lifespan(
            settings, transport=channel_transport, media_downloader=media_downloader
        )
    is_workspace = getattr(settings, "ticket", {}).get("version") in {
        "cbn-institutional-spanish-p3-v1",
        "cbn-institutional-channels-p4-v1",
        "cbn-institutional-agents-p5-v1",
        "cbn-institutional-knowledge-p6-v1",
        "cbn-institutional-broadcast-p7-v1",
        "cbn-institutional-campaign-p8-v1",
        "cbn-institutional-ads-p9-v1",
    'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}
    if is_workspace and not is_operational and workspace is None:
        from app.institutional.workspace import Workspace as WorkspaceV3

        workspace = WorkspaceV3(settings)
    if is_operational and workspace is None:
        if rehearsal:
            from app.institutional.postgres_workspace import Workspace as WorkspaceV4
        else:
            from app.institutional.channel_workspace import Workspace as WorkspaceV4

        workspace = WorkspaceV4(settings)
    app.state.sql_workspace = workspace or Workspace(settings)
    port = 4178 if is_workspace else 4177
    public_host = getattr(settings, "public_host", None)
    public_origin = getattr(settings, "public_origin", None)
    local_cookie = cookie_name(settings)
    identity, management, configuration = (
        Identity(settings),
        Management(settings),
        Settings(settings),
    )
    if not is_workspace:
        install_clients(app)
    install_crm_configuration(app)
    if not is_workspace:
        install_inbox(app)

    @app.middleware("http")
    async def access(request: Request, call_next):
        host = request.headers.get("host")
        origin = request.headers.get("origin")
        path = request.url.path
        loopback = request.client and request.client.host in {"127.0.0.1", "::1"}
        if rehearsal and path.startswith("/hooks/") and not (
            loopback and host in {"127.0.0.1:8004", "127.0.0.1:4178", "localhost:4178"}
        ):
            return JSONResponse({"detail": "local_access_required"}, 403)
        if public_host and not (
            loopback and (
                host == public_host
                or (host in {f"127.0.0.1:{port}", f"localhost:{port}"} and path.startswith("/health/"))
            )
        ):
            return JSONResponse({"detail": "deployment_host_required"}, 403)
        if is_operational and path.startswith("/hooks/"):
            # Public ingress authenticates raw provider signatures, not local human
            # cookies.
            response = await call_next(request)
            response.headers["Cache-Control"] = "no-store"
            response.headers["Referrer-Policy"] = "no-referrer"
            response.headers["X-Content-Type-Options"] = "nosniff"
            return response
        if public_host:
            if origin not in {None, public_origin} or (
                path.startswith("/api/") and request.method not in {"GET", "HEAD", "OPTIONS"}
                and origin != public_origin
            ):
                return JSONResponse({"detail": "deployment_origin_required"}, 403)
        elif (
            not loopback
            or host not in {"127.0.0.1:8004", f"127.0.0.1:{port}", f"localhost:{port}"}
            or origin not in {None, f"http://127.0.0.1:{port}", f"http://localhost:{port}"}
        ):
            return JSONResponse({"detail": "local_access_required"}, 403)
        authority = None
        authenticated_actor = None
        context = None
        try:
            if request.url.path.startswith("/api/"):
                if request.headers.get("x-crm-local") != "1":
                    raise HTTPException(403, "local_access_required")
                # Check size before handlers parse passwords, tokens or documents.
                declared = request.headers.get("content-length", "0")
                size_limit = (
                    7_000_000
                    if is_operational
                    and (request.url.path in {
                        "/api/institution/media/upload",
                        "/api/institution/knowledge/upload",
                        "/api/institution/campaigns/assets",
                    } or (request.method == "POST"
                          and request.url.path.startswith("/api/institution/broadcasts/accounts/")
                          and request.url.path.endswith("/templates/sample")))
                    else 524288
                )
                if request.url.path == "/api/institution/notifications/assets" and request.method == "POST":
                    size_limit = 1_500_000
                if (
                    getattr(settings, "ticket", {}).get("version")
                    in {
                        "cbn-institutional-agents-p5-v1",
                        "cbn-institutional-knowledge-p6-v1",
                        "cbn-institutional-broadcast-p7-v1",
                        "cbn-institutional-campaign-p8-v1",
                        "cbn-institutional-ads-p9-v1",
                    'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}
                    and request.method == "PUT"
                    and request.url.path.startswith("/api/v1/agents/profiles/")
                ):
                    size_limit = 8_000_000
                if (
                    getattr(settings, "ticket", {}).get("version")
                    in {
                        "cbn-institutional-knowledge-p6-v1",
                        "cbn-institutional-broadcast-p7-v1",
                        "cbn-institutional-campaign-p8-v1",
                        "cbn-institutional-ads-p9-v1",
                    'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}
                    and request.method == "PUT"
                    and request.url.path.startswith(
                        "/api/institution/knowledge/records/"
                    )
                ):
                    size_limit = 7_000_000
                if not declared.isdigit() or int(declared) > size_limit:
                    raise HTTPException(413, "request_too_large")
                chunks = []
                size = 0
                async for chunk in request.stream():
                    size += len(chunk)
                    if size > size_limit:
                        raise HTTPException(413, "request_too_large")
                    chunks.append(chunk)
                # Replay the bounded body through Starlette's cached request.
                request._body = b"".join(chunks)
                resource = next(
                    (
                        path
                        for path, methods, expression in protected_routes
                        if request.method.lower() in methods
                        and expression.fullmatch(request.url.path)
                    ),
                    None,
                )
                if resource is None:
                    raise HTTPException(404, "resource_not_found")
                permission, module = core_permission(request.url.path, request.method)
                authority = {
                    "token": request.cookies.get(local_cookie, ""),
                    "csrf": request.headers.get("x-csrf-token", ""),
                    "method": request.method,
                    "permission": permission,
                    "module": module,
                    "resource": resource,
                }
                if request.url.path not in PUBLIC:
                    authenticated_actor = (
                        await run_in_threadpool(identity.authenticate, authority)
                    )["UserId"]
                context = request_authority.set(authority)
                request.state.authority = authority
            response = await call_next(request)
        except HTTPException as error:
            response = JSONResponse(
                {"detail": error.detail}, error.status_code, headers=error.headers,
            )
        finally:
            if context is not None:
                request_authority.reset(context)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        # Denied business transactions roll back; the independent audit
        # contains no request body or query.
        if authority and (
            response.status_code in {401, 403, 428}
            or authenticated_actor is not None
            and response.status_code in {409, 422, 429}
        ):
            try:
                with transaction(settings, True, anonymous=True) as c:
                    audit(
                        c,
                        settings,
                        authenticated_actor,
                        "access.denied"
                        if response.status_code in {401, 403, 428}
                        else "request.failed",
                        authority["resource"],
                        outcome="denied"
                        if response.status_code in {401, 403, 428}
                        else "failed",
                        reason=str(response.status_code),
                    )
            except HTTPException:
                response = JSONResponse(
                    {"detail": "audit_unavailable"},
                    503,
                    headers={
                        "Cache-Control": "no-store",
                        "X-Content-Type-Options": "nosniff",
                        "Referrer-Policy": "no-referrer",
                    },
                )
        return response

    @app.exception_handler(RequestValidationError)
    @app.exception_handler(ValidationError)
    async def invalid(request, error):
        return JSONResponse({"detail": "invalid_request"}, 422)

    def signed(result):
        result = dict(result)
        raw = result.pop("_token", None)
        response = JSONResponse(result)
        if raw:
            response.set_cookie(
                local_cookie,
                raw,
                httponly=True,
                secure=bool(public_host),
                samesite="lax" if is_operational else "strict",
                max_age=28800,
                path="/" if is_operational else "/api",
            )
        return response

    @app.get("/health/live")
    def live():
        return {"status": "alive"}

    @app.get("/api/institution/auth/status")
    def status():
        return identity.status()

    @app.post("/api/institution/auth/bootstrap")
    def bootstrap(body: models.Bootstrap):
        if postgres or getattr(settings, "deployment_transport", None):
            raise HTTPException(404, "resource_not_found")
        return signed(identity.bootstrap(body))

    @app.post("/api/institution/auth/login")
    def login(body: models.Login):
        return signed(identity.login(body))

    @app.post("/api/institution/auth/verify")
    def verify_login(body: models.MFA):
        return signed(identity.verify_login(body))

    @app.post("/api/institution/auth/redeem")
    def redeem(body: models.Redeem):
        return management.redeem(body)

    @app.get("/api/institution/auth/me")
    def me(request: Request):
        return identity.me(request.state.authority)

    @app.post("/api/institution/auth/logout")
    def logout(request: Request):
        result = identity.logout(request.state.authority)
        response = JSONResponse(result)
        response.delete_cookie(
            local_cookie, path="/" if is_operational else "/api", secure=bool(public_host),
            httponly=True, samesite="lax" if is_operational else "strict",
        )
        return response

    @app.post("/api/institution/auth/confirm")
    def confirm(request: Request, body: models.Reauthenticate):
        return identity.reauthenticate(request.state.authority, body)

    @app.get("/api/institution/runtime")
    def runtime(request: Request):
        return configuration.availability(request.state.authority)

    @app.get("/api/institution/settings/{section}")
    def read_setting(request: Request, section: str):
        return configuration.read(request.state.authority, section)

    @app.put("/api/institution/settings/{section}")
    def save_setting(request: Request, section: str, body: models.SettingEdit):
        return configuration.save(request.state.authority, section, body)

    @app.get("/api/institution/settings/{section}/history")
    def history(request: Request, section: str):
        return configuration.history(request.state.authority, section)

    @app.post(("/api/institution/settings/{section}/restore/{revision}"))
    def restore(
        request: Request, section: str, revision: int, body: models.SettingEdit
    ):
        return configuration.restore(request.state.authority, section, revision, body)

    @app.get("/api/institution/credentials/{scope}")
    def credentials(request: Request, scope: str):
        return configuration.credentials(request.state.authority, scope)

    if getattr(settings, "ticket", {}).get("version") == "cbn-institutional-operations-p11-v1":
        from app.institutional.provider_catalog import install as install_provider_catalog

        install_provider_catalog(app, settings)

    @app.put("/api/institution/credentials")
    def secret(request: Request, body: models.SecretEdit):
        return configuration.secret(request.state.authority, body)

    @app.post("/api/institution/credentials/revoke")
    def revoke_secret(request: Request, body: models.SecretEdit):
        return configuration.secret(request.state.authority, body, remove=True)

    @app.put("/api/institution/profile")
    def profile(request: Request, body: models.ProfileEdit):
        return configuration.own_profile(request.state.authority, body)

    @app.get("/api/institution/users")
    def users(request: Request, after: str = "", limit: int = 50):
        return management.users(request.state.authority, after=after, limit=limit)

    @app.post("/api/institution/users")
    def create_user(request: Request, body: models.UserCreate):
        return management.create_user(request.state.authority, body)

    @app.put("/api/institution/users/{user_id}")
    def edit_user(request: Request, user_id: str, body: models.UserEdit):
        return management.edit_user(request.state.authority, user_id, body)

    @app.post("/api/institution/users/{user_id}/reset")
    def reset_user(request: Request, user_id: str):
        return management.issue_reset(request.state.authority, user_id)

    @app.get("/api/institution/roles")
    def roles(request: Request):
        return management.roles(request.state.authority)

    @app.put("/api/institution/roles/{role}")
    def role(request: Request, role: str, body: models.RoleEdit):
        return management.save_role(request.state.authority, role, body)

    @app.get("/api/institution/sessions")
    def sessions(request: Request):
        return management.sessions(request.state.authority)

    @app.post("/api/institution/sessions/{session_id}/revoke")
    def revoke_session(request: Request, session_id: str):
        return management.revoke_session(request.state.authority, session_id)

    @app.post("/api/institution/security/password")
    def password(request: Request, body: models.PasswordChange):
        return management.password(request.state.authority, body)

    @app.post("/api/institution/security/totp/setup")
    def setup(request: Request, body: models.Reauthenticate):
        return management.factor_setup(request.state.authority, body)

    @app.post("/api/institution/security/totp/verify")
    def verify_factor(request: Request, body: models.VerifyFactor):
        return management.factor_verify(request.state.authority, body)

    @app.post("/api/institution/security/totp/disable")
    def disable_factor(request: Request, body: models.Reauthenticate):
        return management.factor_disable(request.state.authority, body)

    @app.get("/api/institution/audit")
    def audit_log(request: Request, after: int = 0, limit: int = 50):
        return configuration.audit_log(
            request.state.authority, after=after, limit=limit
        )

    from app.institutional.channels import install_channels

    if is_operational:
        from app.institutional.channel_operations import (
            OperationalChannels,
        )
        from app.institutional.channel_operations import (
            install as install_operations,
        )

        install_operations(app, settings)
        install_channels(app, settings, OperationalChannels(settings))
        from app.institutional.channel_ingress import install as install_ingress

        install_ingress(app, settings)
        from app.institutional.channel_provider import install as install_provider

        install_provider(app, settings)
        from app.institutional.channel_oauth import install as install_oauth

        install_oauth(app, settings)
        from app.institutional.channel_comments import install as install_comments

        install_comments(app, settings)
        from app.institutional.comment_ai import install as install_comment_ai
        from app.institutional.comment_effects import install as install_comment_effects

        install_comment_effects(app, settings)
        install_comment_ai(app, settings)
        from app.institutional.channel_media import install as install_media

        install_media(app, settings)
        from app.institutional.channel_recovery import install as install_recovery

        install_recovery(app, settings)
    else:
        install_channels(app, settings)
    if getattr(settings, "ticket", {}).get("version") in {
        "cbn-institutional-spanish-p2-v1",
        "cbn-institutional-spanish-p3-v1",
        "cbn-institutional-channels-p4-v1",
        "cbn-institutional-agents-p5-v1",
        "cbn-institutional-knowledge-p6-v1",
        "cbn-institutional-broadcast-p7-v1",
        "cbn-institutional-campaign-p8-v1",
        "cbn-institutional-ads-p9-v1",
    'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
        from app.institutional.ui_contract import install as install_ui_contract
        from app.institutional.webhooks import install as install_webhooks

        if not is_operational:
            install_webhooks(app, settings)
        install_ui_contract(app, settings)
    if is_workspace:
        from app.institutional.workspace import install as install_workspace

        if postgres:
            install_workspace(app, settings, app.state.sql_workspace)
        elif is_operational:
            from app.institutional.channel_workspace import Workspace as WorkspaceV4

            install_workspace(app, settings, WorkspaceV4(settings))
        else:
            install_workspace(app, settings)

    if getattr(settings, "ticket", {}).get("version") in {
        "cbn-institutional-agents-p5-v1",
        "cbn-institutional-knowledge-p6-v1",
        "cbn-institutional-broadcast-p7-v1",
        "cbn-institutional-campaign-p8-v1",
        "cbn-institutional-ads-p9-v1",
    'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
        from app.institutional.agents_api import install as install_agents

        install_agents(app, settings, agent_gateway_factory)

    if getattr(settings, "ticket", {}).get("version") in {
        "cbn-institutional-knowledge-p6-v1",
        "cbn-institutional-broadcast-p7-v1",
        "cbn-institutional-campaign-p8-v1",
        "cbn-institutional-ads-p9-v1",
    'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
        from app.institutional.knowledge_api import install as install_knowledge

        install_knowledge(app, settings)

    if getattr(settings, "ticket", {}).get("version") in {
        "cbn-institutional-broadcast-p7-v1",
        "cbn-institutional-campaign-p8-v1",
        "cbn-institutional-ads-p9-v1",
    'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
        from app.institutional.broadcast_api import install as install_broadcast

        install_broadcast(app, settings, broadcast_gateway)

    if getattr(settings, "ticket", {}).get("version") in {
        "cbn-institutional-ads-p9-v1",
        "cbn-institutional-campaign-p8-v1",
    'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
        from app.institutional.campaign_api import install as install_campaigns

        install_campaigns(app, settings, broadcast_gateway)

    if getattr(settings, "ticket", {}).get("version") in {'cbn-institutional-ads-p9-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
        from app.institutional.ads_api import install as install_ads

        install_ads(app, settings)

    if getattr(settings,'ticket',{}).get('version') in {'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
        from app.institutional.learning_api import install as install_learning
        install_learning(app,settings)

    if postgres or getattr(settings, "ticket", {}).get("version") == "cbn-institutional-operations-p11-v1":
        from app.institutional.operations import install as install_operations

        install_operations(app, settings)

    if getattr(settings, "postgres_deployment", False):
        from app.institutional.email_notifications import install as install_notifications
        install_notifications(app, settings)

    @app.api_route(
        "/api/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        include_in_schema=False,
    )
    def unavailable(path: str):
        raise HTTPException(404, "resource_not_found")

    # Public OpenAPI generation resolves included routers as well as direct
    # handlers. Keep only fixed method/path patterns; never log raw object IDs.
    if rehearsal:
        from app.institutional.postgres_rehearsal import REHEARSAL_ROUTES
        routes = REHEARSAL_ROUTES.items()
    else:
        routes = app.openapi()["paths"].items()
    protected_routes.extend(
        (path, set(methods), compile_path(path)[0])
        for path, methods in routes if path != "/api/{path}"
    )
    return app


def application():
    engine = os.environ.get("CRM_DATABASE_ENGINE")
    if engine not in (None, "sqlserver", "postgresql"):
        logging.getLogger(__name__).error("crm_database_engine_invalid")
        raise SystemExit(1)
    if engine == "postgresql" or (
        engine is None and "CRM_POSTGRES_URL" in os.environ and "CRM_SQL_URL" not in os.environ
    ):
        from app.institutional.postgres_rehearsal import ProfileError, apply_environment

        try:
            return create_app(apply_environment())
        except ProfileError as error:
            logging.getLogger(__name__).error("%s", error)
            raise SystemExit(1) from None
    try:
        transport = deployment.transport_from_env(os.environ)
        if transport:
            return create_app(deployment.load(transport, os.environ))
    except deployment.DeploymentError as error:
        logging.getLogger(__name__).error("%s", error)
        raise SystemExit(1) from None
    return create_app(load(Path(os.environ["CRM_INSTITUTIONAL_PROFILE_DIR"])))
