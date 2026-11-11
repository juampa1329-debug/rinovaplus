"""Canonical method/path inventory and typed fail-closed local transport."""

import inspect
import re
from typing import Annotated, Literal

from fastapi import Body, FastAPI, Query, Request
from fastapi import Path as PathParameter
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

from app import schemas
from app.local_registry import LOCAL_CONTRACTS


class RouteContract(BaseModel):
    method: str
    path: str
    operation_id: str
    capability: str
    source_locator: str
    phase: str
    schema_status: Literal["provisional", "pending", "local_defined"]
    request_schema: str
    query_schema: str = "none"
    path_schema: str = "none"
    planned_result_schema: str = "none"
    schema_revision: str = "local-v2"
    connected_status: Literal[
        "approval_pending", "local_readonly_accepted", "local_operational"
    ] = "approval_pending"
    evidence: Literal["local_source", "local_proposal"] = "local_source"
    activation_gate: str
    response_status: int = 501
    disposition: str


# This finite vocabulary is the only authored route inventory.
GROUPS = (
    (
        "auth",
        "1",
        "docs/design/module-map.md#M-01",
        (
            "POST /auth/login",
            "POST /auth/logout",
            "POST /auth/reauthenticate",
            "GET /auth/me",
            "GET /auth/sessions",
            "DELETE /auth/sessions/{session_id}",
            "POST /auth/challenges",
            "POST /auth/recovery",
        ),
    ),
    ("overview", "2", "docs/design/module-map.md#M-02", ("GET /overview",)),
    (
        "clients",
        "2",
        "docs/design/settings-reference/scentra_clientes_especificacion.md",
        (
            "GET /clients",
            "POST /clients",
            "GET /clients/{client_id}",
            "PATCH /clients/{client_id}",
            "POST /clients/{client_id}/deactivation-requests",
            "GET /clients/{client_id}/timeline",
        ),
    ),
    (
        "crm",
        "2",
        "frontend/src/shared/crm.ts",
        (
            "GET /crm/configuration",
            "PUT /crm/configuration",
        ),
    ),
    (
        "conversations",
        "3",
        "docs/design/settings-reference/scentra_inbox_especificacion.md",
        (
            "GET /conversations",
            "GET /conversations/{conversation_id}",
            "GET /conversations/{conversation_id}/messages",
            "POST /conversations/{conversation_id}/messages",
            "PATCH /conversations/{conversation_id}/workflow",
            "POST /conversations/{conversation_id}/control",
            "POST /conversations/{conversation_id}/read",
            "GET /conversations/{conversation_id}/tasks",
            "POST /conversations/{conversation_id}/tasks",
            "PATCH /conversations/{conversation_id}/tasks/{task_id}",
            "GET /conversations/{conversation_id}/events",
            "GET /conversations/{conversation_id}/delivery-statuses",
            "POST /conversations/{conversation_id}/suggestions",
            "POST /conversations/{conversation_id}/analysis",
        ),
    ),
    (
        "comments",
        "2",
        "docs/design/settings-reference/scentra_inbox_especificacion.md",
        (
            "GET /comments",
            "GET /comments/{comment_id}",
            "POST /comments/{comment_id}/replies",
            "POST /comments/{comment_id}/reactions",
        ),
    ),
    (
        "catalog",
        "4",
        "docs/design/module-map.md#M-08",
        (
            "GET /catalog/programs",
            "GET /catalog/programs/{program_id}",
            "GET /catalog/schedules",
            "GET /catalog/attention-hours",
        ),
    ),
    (
        "form",
        "4",
        "frontend/src/shared/application.ts",
        (
            "POST /application-links",
            "GET /application-links/{link_reference}",
            "POST /application-links/{link_reference}/submissions",
        ),
    ),
    (
        "review",
        "5",
        "frontend/src/shared/review.ts",
        (
            "GET /applications",
            "GET /applications/{application_id}",
            "POST /applications/{application_id}/review-start",
            "POST /applications/{application_id}/review-decisions",
            "POST /applications/{application_id}/reopen",
            "POST /applications/{application_id}/core-registration",
        ),
    ),
    (
        "assistant",
        "3",
        "docs/design/settings-specification.md#SET-01",
        (
            "GET /assistant/configuration",
            "PUT /assistant/configuration",
            "POST /assistant/reviews",
            "POST /assistant/tests",
            "POST /assistant/publications",
        ),
    ),
    (
        "channels",
        "3",
        "docs/design/settings-specification.md#SET-02",
        (
            "GET /channels",
            "GET /channels/{channel}",
            "PUT /channels/{channel}/draft",
            "POST /channels/{channel}/oauth",
            "GET /channels/{channel}/oauth/callback",
            "POST /channels/{channel}/discovery",
            "GET /channels/{channel}/capabilities",
            "GET /channels/{channel}/webhook-reference",
            "POST /channels/{channel}/activation",
            "POST /channels/{channel}/pause",
            "POST /channels/{channel}/connection-tests",
            "GET /channels/whatsapp/numbers",
            "POST /channels/whatsapp/number-registration",
            "POST /channels/whatsapp/number-verification",
        ),
    ),
    (
        "webhooks",
        "3",
        "docs/design/settings-specification.md#CA-07",
        (
            "GET /webhooks/{channel}",
            "POST /webhooks/{channel}",
        ),
    ),
    (
        "providers",
        "3",
        "docs/design/settings-specification.md#SET-03",
        (
            "GET /providers",
            "GET /providers/{provider_reference}",
            "PUT /providers/{provider_reference}/draft",
            "POST /providers/{provider_reference}/authentication-tests",
            "GET /providers/{provider_reference}/models",
            "PUT /providers/{provider_reference}/model-reference",
            "POST /providers/{provider_reference}/tests",
            "POST /providers/{provider_reference}/activation",
            "POST /providers/{provider_reference}/rotation",
            "POST /providers/{provider_reference}/revocation",
            "POST /providers/{provider_reference}/pause",
        ),
    ),
    (
        "diagnostics",
        "6",
        "docs/design/settings-specification.md#SET-04",
        (
            "GET /diagnostics",
            "GET /diagnostics/endpoints",
            "GET /diagnostics/events",
            "GET /diagnostics/queues",
            "GET /diagnostics/incidents",
            "POST /diagnostics/process",
            "POST /diagnostics/simulations",
            "POST /diagnostics/pause",
            "POST /diagnostics/recovery-reviews",
            "POST /diagnostics/resume",
        ),
    ),
    (
        "users",
        "1",
        "docs/design/settings-specification.md#SET-05",
        (
            "GET /users",
            "POST /users/invitations",
            "PATCH /users/{user_id}",
            "POST /users/{user_id}/deactivation",
            "POST /users/{user_id}/reactivation",
            "GET /roles",
            "PUT /users/{user_id}/role",
        ),
    ),
    (
        "profile",
        "1",
        "docs/design/settings-specification.md#SET-06",
        (
            "GET /profile",
            "PUT /profile",
            "POST /profile/email-change",
            "POST /profile/email-verification",
        ),
    ),
    (
        "security",
        "1",
        "docs/design/settings-specification.md#SET-07",
        (
            "GET /security",
            "POST /security/password-change",
            "POST /security/two-factor/enrollment",
            "POST /security/two-factor/verification",
            "POST /security/two-factor/activation",
            "POST /security/two-factor/recovery",
            "POST /security/exports",
            "POST /security/deletion-requests",
            "GET /security/audit-events",
        ),
    ),
    (
        "media",
        "7A",
        "docs/roadmap.md",
        (
            "POST /media",
            "GET /media/{media_reference}",
            "POST /speech/transcriptions",
            "POST /speech/synthesis",
            "PUT /assistant/fallback-references",
        ),
    ),
    (
        "follow-ups",
        "7B",
        "docs/roadmap.md",
        (
            "GET /follow-ups",
            "POST /follow-ups",
            "POST /follow-ups/{follow_up_id}/cancellation",
        ),
    ),
    (
        "knowledge",
        "7C",
        "docs/roadmap.md",
        (
            "GET /knowledge/sources",
            "POST /knowledge/sources",
            "PATCH /knowledge/sources/{source_id}",
            "POST /knowledge/sources/{source_id}/removal-requests",
            "POST /knowledge/indexing",
            "GET /knowledge/aliases",
            "PUT /knowledge/aliases",
            "POST /knowledge/retrieval-tests",
            "POST /knowledge/evaluations",
            "POST /knowledge/publications",
            "GET /sales-memory",
            "GET /sales-memory/{case_id}",
        ),
    ),
    (
        "retention",
        "7D",
        "docs/design/module-map.md#M-11",
        (
            "GET /retention",
            "GET /retention/{reference_id}",
        ),
    ),
    (
        "corporate",
        "7E",
        "docs/design/module-map.md#M-12",
        (
            "GET /corporate-relations",
            "GET /corporate-relations/{reference_id}",
        ),
    ),
    (
        "creators",
        "7F",
        "docs/design/settings-reference/scentra_crm_subpestanas_especificacion.md",
        (
            "GET /creators",
            "POST /creators",
            "POST /creators/{creator_id}/contact-plans",
            "GET /creator-campaigns",
            "POST /creator-campaigns",
            "POST /creator-campaigns/{campaign_id}/deliverables",
            "PATCH /creator-deliverables/{deliverable_id}",
            "GET /creator-resources",
            "POST /creator-resources",
            "POST /creator-resources/{resource_id}/rights-reviews",
            "POST /creator-resources/{resource_id}/rights-revocation",
            "POST /creator-resources/{resource_id}/performance-analysis",
            "POST /creator-resources/{resource_id}/spark-preflight",
            "GET /creator-audit-events",
        ),
    ),
)

REQUEST_SCHEMAS = {
    ("POST", "/clients"): schemas.ClientDraft,
    ("PATCH", "/clients/{client_id}"): schemas.ClientDraft,
    ("PUT", "/crm/configuration"): schemas.CrmDraft,
    ("POST", "/conversations/{conversation_id}/messages"): schemas.MessageDraft,
    ("PATCH", "/conversations/{conversation_id}/workflow"): schemas.WorkflowDraft,
    ("POST", "/conversations/{conversation_id}/tasks"): schemas.TaskDraft,
    ("PATCH", "/conversations/{conversation_id}/tasks/{task_id}"): schemas.TaskDraft,
    ("POST", "/comments/{comment_id}/replies"): schemas.MessageDraft,
    (
        "POST",
        "/application-links/{link_reference}/submissions",
    ): schemas.ApplicationDraft,
    ("POST", "/applications/{application_id}/review-decisions"): schemas.ReviewDraft,
    ("PUT", "/assistant/configuration"): schemas.AssistantDraft,
    ("PUT", "/profile"): schemas.ProfileDraft,
    ("PUT", "/channels/{channel}/draft"): schemas.ChannelDraft,
}


def build_business_routes() -> tuple[RouteContract, ...]:
    routes = []
    for capability, phase, source, operations in GROUPS:
        for operation in operations:
            method, path = operation.split(" ")
            local = LOCAL_CONTRACTS[(method, path)]
            model = local.body_model
            routes.append(
                RouteContract(
                    method=method,
                    path="/api/v1" + path,
                    operation_id=method.lower()
                    + "_"
                    + re.sub(r"[^a-z0-9]+", "_", path.lower()).strip("_"),
                    capability=capability,
                    source_locator=source.split("#", 1)[0],
                    phase=phase,
                    schema_status="provisional"
                    if (method, path) in REQUEST_SCHEMAS
                    else "local_defined",
                    request_schema=model.__name__
                    if method in {"POST", "PUT", "PATCH"}
                    else "none",
                    query_schema=local.query_model.__name__,
                    path_schema=local.path_model.__name__,
                    planned_result_schema=local.result_model.__name__,
                    evidence=local.evidence,
                    activation_gate="phase_1_and_capability_contract_and_explicit_authorization",
                    disposition="conditional_proposal"
                    if phase.startswith("7")
                    else "local_stub_only",
                )
            )
    # Concrete routes precede parametric siblings; avoid a static route shadow.
    return tuple(
        sorted(
            routes, key=lambda route: (route.path.count("{"), route.path, route.method)
        )
    )


BUSINESS_ROUTES = build_business_routes()

# Preserve the original proposal in the planning registry while installing
# exactly one owner for each live method/path pair.
CATALOG_ROUTES = tuple(
    RouteContract(
        method="GET",
        path=f"/api/v1/catalog/{name}",
        operation_id=f"catalog_{name}",
        capability="catalog",
        source_locator="backend/app/modules/catalog/api/router.py",
        phase="1-local-readonly",
        schema_status="provisional",
        request_schema="none",
        connected_status="local_readonly_accepted",
        activation_gate="explicit_local_readonly_catalog_and_restricted_identity",
        response_status=200,
        disposition="opt_in_readonly_catalog_503_when_disabled",
    )
    for name in ("periods", "schools", "modalities", "programs")
)
CATALOG_KEYS = frozenset((route.method, route.path) for route in CATALOG_ROUTES)
WEBHOOK_VERIFICATION_ROUTE = RouteContract(
    method="GET",
    path="/api/v1/webhooks/meta",
    operation_id="webhooks_meta_verification",
    capability="webhooks",
    source_locator="backend/app/modules/webhooks/api/router.py",
    phase="3-local-verification",
    schema_status="local_defined",
    request_schema="none",
    query_schema="meta_hub_query",
    activation_gate="configured_verify_token_digest_no_event_ingestion",
    response_status=200,
    disposition="subscription_challenge_only_503_when_unconfigured",
)
WEBHOOK_STATUS_ROUTE = RouteContract(
    method="GET",
    path="/api/v1/webhooks/meta/status",
    operation_id="webhooks_meta_status",
    capability="webhooks",
    source_locator="backend/app/modules/webhooks/api/router.py",
    phase="3-local-verification",
    schema_status="local_defined",
    request_schema="none",
    activation_gate="metadata_only_no_business_activation",
    response_status=200,
    disposition="local_status_without_credentials_or_event_ingestion",
)
CHANNEL_ROUTES = tuple(
    route.model_copy(
        update={
            "source_locator": "backend/app/modules/channels/router.py",
            "phase": "sprint-2-local-operational",
            "schema_status": "local_defined",
            "connected_status": "local_operational",
            "activation_gate": "local_operator_saved_encrypted_credentials_and_provider_grants",
            "response_status": 200,
            "disposition": "operational_local_sql_provider_access_requires_real_credentials",
        }
    )
    for route in BUSINESS_ROUTES
    if route.capability == "channels" and "/oauth" not in route.path
)
CHANNEL_KEYS = frozenset((route.method, route.path) for route in CHANNEL_ROUTES)
RECEIPT_ROUTES = tuple(
    RouteContract(
        method="POST",
        path=f"/api/v1/webhooks/{provider}",
        operation_id=f"webhooks_{provider}_receipt",
        capability="webhooks",
        source_locator="backend/app/modules/webhooks/api/router.py",
        phase="sprint-2-local-operational",
        schema_status="local_defined",
        request_schema="raw_signed_json",
        connected_status="local_operational",
        activation_gate="valid_signature_and_durable_sql_receipt",
        response_status=200,
        disposition="durable_receipt_with_separate_ingestion_worker",
    )
    for provider in ("meta", "tiktok")
)
LIVE_REPLACEMENT_KEYS = (
    CATALOG_KEYS | CHANNEL_KEYS | {("POST", "/api/v1/webhooks/{channel}")}
)
STUB_ROUTES = tuple(
    route
    for route in BUSINESS_ROUTES
    if (route.method, route.path) not in LIVE_REPLACEMENT_KEYS
)
SUPERSEDED_PROPOSALS = tuple(
    route
    for route in BUSINESS_ROUTES
    if (route.method, route.path) in LIVE_REPLACEMENT_KEYS
)


class ContractCatalog(BaseModel):
    mode: Literal["local_demo"] = "local_demo"
    scope: str = (
        "Local contract stubs and opt-in read-only catalogs; "
        "AI bench has a separate namespace"
    )
    routes: list[RouteContract]
    superseded_proposals: list[RouteContract]
    exclusions: dict[str, str]


def contract_catalog() -> ContractCatalog:
    special = [
        RouteContract(
            method="GET",
            path=path,
            operation_id=identity,
            capability="metadata"
            if status == 200 and "contracts" in path
            else "health",
            source_locator="backend/app/main.py",
            phase="0",
            schema_status="provisional",
            request_schema="none",
            activation_gate="metadata_only_no_business_activation",
            response_status=status,
            disposition="local_metadata_only",
        )
        for path, identity, status in [
            ("/health/live", "health_live", 200),
            ("/health/ready", "health_ready", 503),
            ("/api/v1/contracts", "local_contract_catalog", 200),
        ]
    ]
    return ContractCatalog(
        routes=[
            *special,
            *STUB_ROUTES,
            *CATALOG_ROUTES,
            *CHANNEL_ROUTES,
            *RECEIPT_ROUTES,
            WEBHOOK_VERIFICATION_ROUTE,
            WEBHOOK_STATUS_ROUTE,
        ],
        superseded_proposals=list(SUPERSEDED_PROPOSALS),
        exclusions={
            "vision_search_intelligence_fusion": (
                "requires_discovery_not_an_approved_local_business_contract"
            ),
            "payments_vendor_industry_plan": (
                "excluded_no_SIIE_financial_authority_or_source_product_defaults"
            ),
            "creator_ad_publication_upload_email": (
                "excluded_contact_plan_is_not_send_"
                "URL_is_not_upload_Spark_is_not_publish"
            ),
        },
    )


def endpoint_for(route: RouteContract):
    # FastAPI resolves this exact explicit Signature into validation and OpenAPI.
    # Values are validated by transport only and deliberately never used/reflected.
    def unavailable(**values) -> schemas.StubUnavailable:
        request = values["_request"]
        if set(request.query_params) - set(local.query_model.model_fields):
            raise RequestValidationError([])
        if any(
            len(request.query_params.getlist(name)) != 1
            for name in request.query_params
        ):
            raise RequestValidationError([])
        if route.method in {"GET", "DELETE"} and (
            request.headers.get("content-length", "0") != "0"
            or request.headers.get("transfer-encoding")
        ):
            raise RequestValidationError([])
        body = values.get("body")
        if (
            route.capability == "webhooks"
            and route.method == "POST"
            and body.channel != values["channel"]
        ):
            raise RequestValidationError([])
        return schemas.StubUnavailable(
            operation_id=route.operation_id,
            schema_status=route.schema_status,
            activation_gate=route.activation_gate,
        )

    local = LOCAL_CONTRACTS[(route.method, route.path.removeprefix("/api/v1"))]
    parameters = [
        inspect.Parameter(
            "_request", inspect.Parameter.KEYWORD_ONLY, annotation=Request
        )
    ]
    for name, field in local.path_model.model_fields.items():
        annotation = Annotated[field.annotation, *field.metadata, PathParameter()]
        parameters.append(
            inspect.Parameter(
                name, inspect.Parameter.KEYWORD_ONLY, annotation=annotation
            )
        )
    for name, field in local.query_model.model_fields.items():
        parameters.append(
            inspect.Parameter(
                name,
                inspect.Parameter.KEYWORD_ONLY,
                default=inspect.Parameter.empty
                if field.is_required()
                else field.default,
                annotation=Annotated[
                    field.annotation,
                    *field.metadata,
                    Query(
                        description=(
                            "LOCAL transport proposal; not an accepted business policy"
                        )
                    ),
                ],
            )
        )
    if route.method in {"POST", "PUT", "PATCH"}:
        model = local.body_model
        parameters.append(
            inspect.Parameter(
                "body",
                inspect.Parameter.KEYWORD_ONLY,
                annotation=Annotated[
                    model,
                    Body(
                        description=(
                            "Provisional source fields or local-v2 proposal. "
                            "Synthetic input only; no credentials."
                        ),
                        examples=[
                            local.body_example.model_dump(
                                mode="json", exclude_unset=True
                            )
                        ],
                    ),
                ],
            )
        )
    unavailable.__signature__ = inspect.Signature(
        parameters, return_annotation=schemas.StubUnavailable
    )
    unavailable.__name__ = route.operation_id
    return unavailable


def register_contracts(application: FastAPI) -> None:
    application.add_api_route(
        "/api/v1/contracts",
        contract_catalog,
        methods=["GET"],
        operation_id="local_contract_catalog",
        response_model=ContractCatalog,
        summary="Local metadata only; never integration readiness",
    )
    for route in STUB_ROUTES:
        application.add_api_route(
            route.path,
            endpoint_for(route),
            methods=[route.method],
            operation_id=route.operation_id,
            response_model=schemas.StubUnavailable,
            status_code=501,
            tags=[route.capability],
            summary="Unavailable local stub: " + route.operation_id,
            description=(
                "No business execution. Schema and activation "
                "remain gated by phase 1 and discovery."
            ),
            responses={
                422: {
                    "model": schemas.InvalidInput,
                    "description": "Constant sanitized validation error",
                }
            },
            openapi_extra={
                "x-local-contract": route.model_dump(mode="json"),
                "x-local-contract-ref": "#/components/schemas/"
                + route.planned_result_schema,
                "x-local-path-ref": "#/components/schemas/" + route.path_schema,
                "x-local-query-ref": "#/components/schemas/" + route.query_schema,
            },
        )
