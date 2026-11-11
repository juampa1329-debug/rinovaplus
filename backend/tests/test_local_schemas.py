"""Local-v2 definitions are finite validation contracts, never execution."""

import ast
import copy
import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import local_models as m
from app import schemas
from app.contracts import BUSINESS_ROUTES, REQUEST_SCHEMAS, STUB_ROUTES
from app.local_registry import LOCAL_CONTRACTS
from app.main import create_app

APP = create_app()
OPENAPI = APP.openapi()
NEW_ROUTES = tuple(
    route for route in BUSINESS_ROUTES if route.schema_status == "local_defined"
)
NEW_STUBS = tuple(route for route in NEW_ROUTES if route in STUB_ROUTES)
NEW_BODIES = tuple(
    route for route in NEW_ROUTES if route.method in {"POST", "PUT", "PATCH"}
)
INVALID = {"code": "invalid_local_contract_input", "mode": "local_demo"}


def definition(route):
    return LOCAL_CONTRACTS[(route.method, route.path.removeprefix("/api/v1"))]


def request_parts(route):
    local = definition(route)
    path = route.path
    for key, value in local.path_example.model_dump(mode="json").items():
        path = path.replace("{" + key + "}", value)
    return path, {
        "params": local.query_example.model_dump(mode="json", exclude_none=True),
        **(
            {"json": local.body_example.model_dump(mode="json", exclude_unset=True)}
            if local.body_example
            else {}
        ),
    }


@pytest.fixture(scope="module")
def client():
    with TestClient(APP) as transport:
        yield transport


def test_local_registry_closes_only_pending_operations():
    assert len(LOCAL_CONTRACTS) == 148
    assert (
        sum(route.schema_status == "local_defined" for route in BUSINESS_ROUTES) == 135
    )
    assert sum(route.schema_status == "provisional" for route in BUSINESS_ROUTES) == 13
    assert not any(route.schema_status == "pending" for route in BUSINESS_ROUTES)
    assert len(NEW_BODIES) == 77
    assert len(NEW_ROUTES) - len(NEW_BODIES) == 58
    assert set(LOCAL_CONTRACTS) == {
        (r.method, r.path.removeprefix("/api/v1")) for r in BUSINESS_ROUTES
    }
    for key, model in REQUEST_SCHEMAS.items():
        assert LOCAL_CONTRACTS[key].body_model is model


@pytest.mark.parametrize("route", BUSINESS_ROUTES, ids=lambda route: route.operation_id)
def test_examples_validate_as_actual_typed_models(route):
    local = definition(route)
    pairs = [
        (local.query_model, local.query_example),
        (local.path_model, local.path_example),
        (local.result_model, local.result_example),
    ]
    if local.body_model:
        pairs.append((local.body_model, local.body_example))
    for model, example in pairs:
        assert (
            model.model_validate_json(example.model_dump_json(exclude_unset=True))
            == example
        )
    assert local.result_example.execution == "planned_not_executed"


@pytest.mark.parametrize("route", NEW_STUBS, ids=lambda route: route.operation_id)
def test_every_new_valid_input_is_only_constant_501(client, route):
    path, kwargs = request_parts(route)
    response = client.request(route.method, path, **kwargs)
    assert response.status_code == 501
    assert (
        response.json()
        == schemas.StubUnavailable(
            operation_id=route.operation_id,
            schema_status="local_defined",
            activation_gate=route.activation_gate,
        ).model_dump()
    )
    assert not {"set-cookie", "location"} & set(response.headers)
    assert "planned_not_executed" not in response.text


@pytest.mark.parametrize("route", NEW_BODIES, ids=lambda route: route.operation_id)
def test_each_new_body_rejects_empty_unknown_and_missing_fields(client, route):
    local = definition(route)
    path, kwargs = request_parts(route)
    cases = [{}, {**kwargs["json"], "unknown_password": "SECRET_SENTINEL"}]
    for name, field in local.body_model.model_fields.items():
        if not field.is_required():
            continue
        missing = copy.deepcopy(kwargs["json"])
        missing.pop(name)
        cases.append(missing)
        null = copy.deepcopy(kwargs["json"])
        null[name] = None
        cases.append(null)
        wrong = copy.deepcopy(kwargs["json"])
        wrong[name] = {"secret": "SECRET_SENTINEL"}
        cases.append(wrong)
    for body in cases:
        response = client.request(route.method, path, **{**kwargs, "json": body})
        assert response.status_code == 422
        assert response.json() == INVALID
        assert "SECRET_SENTINEL" not in response.text
        assert "unknown_password" not in response.text


@pytest.mark.parametrize("route", NEW_ROUTES, ids=lambda route: route.operation_id)
def test_each_planned_result_rejects_missing_and_unknown(route):
    local = definition(route)
    example = local.result_example.model_dump(mode="json", exclude_unset=True)
    required = local.result_model.model_json_schema()["required"]
    for name in required:
        missing = dict(example)
        missing.pop(name)
        with pytest.raises(ValidationError):
            local.result_model.model_validate_json(json.dumps(missing))
    with pytest.raises(ValidationError):
        local.result_model.model_validate_json(
            json.dumps({**example, "unknown_secret": "SECRET_SENTINEL"})
        )


@pytest.mark.parametrize(
    "route",
    tuple(r for r in BUSINESS_ROUTES if r.schema_status == "provisional"),
    ids=lambda route: route.operation_id,
)
def test_thirteen_legacy_empty_bodies_remain_501(client, route):
    path, kwargs = request_parts(route)
    assert (
        client.request(route.method, path, **{**kwargs, "json": {}}).status_code == 501
    )


@pytest.mark.parametrize("route", NEW_STUBS, ids=lambda route: route.operation_id)
def test_each_operation_rejects_unknown_query_without_reflection(client, route):
    path, kwargs = request_parts(route)
    kwargs["params"]["raw_unknown_secret"] = "SECRET_SENTINEL"
    response = client.request(route.method, path, **kwargs)
    assert response.status_code == 422
    assert response.json() == INVALID
    assert "SECRET_SENTINEL" not in response.text


@pytest.mark.parametrize("route", STUB_ROUTES, ids=lambda route: route.operation_id)
def test_registry_openapi_and_typed_parameters_agree(route):
    local = definition(route)
    operation = OPENAPI["paths"][route.path][route.method.lower()]
    assert set(operation["responses"]) == {"501", "422"}
    assert operation["x-local-contract"]["connected_status"] == "approval_pending"
    assert operation["x-local-contract"]["schema_revision"] == "local-v2"
    assert operation["x-local-contract-ref"].endswith("/" + local.result_model.__name__)
    params = {
        (parameter["name"], parameter["in"])
        for parameter in operation.get("parameters", [])
    }
    assert params == {(name, "path") for name in local.path_model.model_fields} | {
        (name, "query") for name in local.query_model.model_fields
    }
    if local.body_model is None:
        assert "requestBody" not in operation
    else:
        assert operation["requestBody"]["required"] is True
        assert local.body_model is not schemas.PendingRequest


def all_refs(value):
    if isinstance(value, str) and value.startswith("#/components/schemas/"):
        yield value.rsplit("/", 1)[-1]
    elif isinstance(value, dict):
        for child in value.values():
            yield from all_refs(child)
    elif isinstance(value, list):
        for child in value:
            yield from all_refs(child)


def test_all_component_refs_resolve_without_orphans_or_cache_drift():
    components = OPENAPI["components"]["schemas"]
    reached = set(all_refs(OPENAPI["paths"])) | set(
        all_refs(OPENAPI["x-local-superseded-proposals"])
    )
    pending = list(reached)
    while pending:
        name = pending.pop()
        assert name in components
        for ref in all_refs(components[name]):
            assert ref in components
            if ref not in reached:
                reached.add(ref)
                pending.append(ref)
    assert reached == set(components)
    assert APP.openapi() is OPENAPI
    assert create_app().openapi() == OPENAPI
    assert "PendingRequest" not in components


@pytest.mark.parametrize(
    "model,bad",
    [
        (m.PresentationPatch, {}),
        (m.PresentationPatch, {"displayName": None}),
        (m.SourcePatch, {}),
        (m.SourcePatch, {"notes": None}),
        (m.DeliverablePatch, {}),
        (m.DeliverablePatch, {"title": " "}),
        (m.StageRecord, {"key": "demo", "label": "Demo", "probability": 101}),
        (m.StageRecord, {"key": "demo", "label": "Demo", "probability": -1}),
        (m.RecoveryChecks, {"isolation": True, "human": True, "reconciliation": False}),
    ],
)
def test_nonempty_patch_and_source_cross_invariants(model, bad):
    with pytest.raises(ValidationError):
        model.model_validate_json(json.dumps(bad))


@pytest.mark.parametrize(
    "model,field,bad",
    [
        (m.LoginIntent, "purpose", "challenge"),
        (m.ConversationControl, "target", "unknown"),
        (m.ReviewReopen, "reason", "abcd"),
        (m.ReviewReopen, "reason", "x" * 601),
        (m.SourceMetadata, "tags", ["Repeated", "Repeated"]),
        (m.SourceMetadata, "tags", ["x"] * 21),
        (
            m.AliasIntent,
            "aliases",
            [
                {"alias": "Demo", "sourceReference": "DEMO-A"},
                {"alias": "demo", "sourceReference": "DEMO-B"},
            ],
        ),
        (m.IndexIntent, "sourceReferences", []),
        (m.IndexIntent, "sourceReferences", ["DEMO-A", "DEMO-A"]),
        (m.ActivationIntent, "testedRevision", 2),
        (m.CoreRegistrationIntent, "applicationRevision", 2),
        (m.CoreRegistrationIntent, "confirmed", False),
        (m.CoreRegistrationIntent, "confirmed", 1),
        (m.SyntheticWebhook, "payload", {"kind": "unknown"}),
        (
            m.SyntheticWebhook,
            "payload",
            {"kind": "message", "deliveryReference": "DEMO-A"},
        ),
        (
            m.SyntheticWebhook,
            "payload",
            {
                "kind": "message",
                "messageReference": "DEMO-A",
                "senderReference": "DEMO-B",
                "text": "x" * 1501,
                "direction": "incoming",
            },
        ),
        (m.ProviderDraft, "capability", "vision"),
        (m.MediaMetadata, "byteLength", 10000001),
        (m.MediaMetadata, "contentType", "application/octet-stream"),
        (m.UserInvitation, "roleReferences", []),
        (m.RightsReview, "contractReference", "https://example.invalid"),
        (m.Control, "expectedRevision", -1),
        (m.Control, "expectedRevision", True),
        (m.Control, "expectedRevision", "1"),
    ],
)
def test_constraints_and_discriminants(model, field, bad):
    from app.local_samples import SAMPLES

    example = copy.deepcopy(
        SAMPLES.get(
            model.__name__, {"idempotencyReference": "DEMO-C", "expectedRevision": 1}
        )
    )
    example[field] = bad
    with pytest.raises(ValidationError):
        model.model_validate_json(json.dumps(example))


def test_webhooks_normalize_only_synthetic_event_shapes(client):
    local = LOCAL_CONTRACTS[("POST", "/webhooks/{channel}")]
    example = local.body_example.model_dump(mode="json", exclude_unset=True)
    for payload in (
        {
            "kind": "message",
            "messageReference": "DEMO-M",
            "senderReference": "DEMO-S",
            "text": "Synthetic text",
            "direction": "incoming",
        },
        {
            "kind": "delivery",
            "messageReference": "DEMO-M",
            "deliveryReference": "DEMO-D",
            "status": "uncertain",
        },
        {
            "kind": "reference",
            "objectReference": "DEMO-O",
            "evidenceReference": "DEMO-E",
        },
    ):
        assert (
            client.post(
                "/api/v1/webhooks/whatsapp", json={**example, "payload": payload}
            ).status_code
            == 501
        )
    response = client.post("/api/v1/webhooks/tiktok", json=example)
    assert response.status_code == 422 and response.json() == INVALID
    assert "challenge" not in response.text
    assert (
        client.get("/api/v1/webhooks/whatsapp?hub.challenge=SECRET_SENTINEL").json()
        == INVALID
    )
    assert (
        client.get("/api/v1/webhooks/whatsapp?verificationReference=DEMO-V").status_code
        == 501
    )


def test_semantic_query_path_negative_and_no_get_delete_body(client):
    paths = [
        "/api/v1/clients?limit=101",
        "/api/v1/clients?offset=10001",
        "/api/v1/clients?stage=",
        "/api/v1/clients?limit=1&limit=2",
        "/api/v1/conversations?channel=Messenger",
        "/api/v1/comments?platform=whatsapp",
        "/api/v1/applications?status=approved",
        "/api/v1/auth/me?password=SECRET_SENTINEL",
        "/api/v1/channels/invalid",
        "/api/v1/providers/SECRET%20SENTINEL",
        "/api/v1/channels/whatsapp/oauth/callback?authorizationEventReference=SECRET_SENTINEL",
    ]
    for path in paths:
        response = client.get(path)
        assert response.status_code == 422 and response.json() == INVALID
    assert client.get("/api/v1/auth/me", params={}).status_code == 501
    assert client.request("GET", "/api/v1/auth/me", json={}).json() == INVALID
    assert (
        client.request(
            "DELETE",
            "/api/v1/auth/sessions/DEMO-S",
            params={"revocationIntentReference": "DEMO-R", "expectedRevision": 1},
            json={},
        ).json()
        == INVALID
    )


def test_recursive_runtime_source_has_no_business_io_or_secret_fields():
    forbidden = {
        "sqlalchemy",
        "pyodbc",
        "redis",
        "requests",
        "httpx",
        "urllib",
        "subprocess",
        "dotenv",
        "aiohttp",
    }
    for path in [
        Path("app") / name
        for name in (
            "contracts.py",
            "schemas.py",
            "local_models.py",
            "local_plans.py",
            "local_registry.py",
            "local_samples.py",
            "local_openapi.py",
        )
    ]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert (
                    not {alias.name.split(".")[0] for alias in node.names} & forbidden
                )
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in forbidden
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {"open", "eval", "exec"}
    for route in NEW_BODIES:
        local = definition(route)
        fields = local.body_model.model_fields
        assert not {
            "password",
            "pin",
            "otp",
            "token",
            "secret",
            "url",
            "providerUrl",
            "credentials",
        } & set(fields)
        assert fields
        assert local.body_model.model_config["extra"] == "forbid"
        assert local.body_model.model_config["strict"] is True


def test_legacy_model_shapes_remain_exact_baseline():
    baseline = {
        "ClientDraft": (
            "6f430065577b7aba20013e29fe1b366b83860617c6bdcd731c7d205ca94b4b5e"
        ),
        "CrmDraft": (
            "5d60e484f97d846b18e205459e05f65d5b34e411e5e775036ad358eaba7ab13c"
        ),
        "MessageDraft": (
            "e00f69ebb57118c9336f5010435d29c940dc59cb9991df5a3e57a25d91614b70"
        ),
        "WorkflowDraft": (
            "ceffa82e19b112f3c840b365f20bfeb027e722c577666471f0075e8a14f91167"
        ),
        "TaskDraft": (
            "527fa94662c2b5cf5f57fabe51e89df4148e4c137f60c5340cc26a229a954e17"
        ),
        "ApplicationDraft": (
            "ae5e643a97746cdebedfb9569facc5ab28c3592abd08a0bcaf882b11228ea05d"
        ),
        "ReviewDraft": (
            "d7de0e430cc8cf262210c52481ef3c6a3c9c3e6970aed325898059a0c6aea50c"
        ),
        "AssistantDraft": (
            "50f576b23d155fd31c82b11afb36975f3c165ace045569f8a33f451a540511a8"
        ),
        "ProfileDraft": (
            "78b8a2889e7b2eb6c63cd65613f4675dad1a8b73b9045af9b181f668a2da33cd"
        ),
        "ChannelDraft": (
            "1f1285da676ae7083204266616884c4b0039e8e0975524f5cc0db71e2b91d5fd"
        ),
    }
    current = {
        model.__name__: hashlib.sha256(
            json.dumps(model.model_json_schema(), sort_keys=True).encode()
        ).hexdigest()
        for model in REQUEST_SCHEMAS.values()
    }
    assert current == baseline


@pytest.mark.parametrize("route", NEW_BODIES, ids=lambda route: route.operation_id)
def test_each_body_declared_local_bounds_reject_invalid_values(client, route):
    local = definition(route)
    sample = local.body_example.model_dump(mode="json", exclude_unset=True)
    schema = local.body_model.model_json_schema()
    definitions = schema.get("$defs", {})
    cases = []

    def collect(shape, value, trail):
        if "$ref" in shape:
            shape = definitions[shape["$ref"].rsplit("/", 1)[-1]]
        if "anyOf" in shape:
            shape = next(item for item in shape["anyOf"] if item.get("type") != "null")
        if "oneOf" in shape:
            shape = next(
                (
                    item
                    for item in shape["oneOf"]
                    if definitions.get(item.get("$ref", "").rsplit("/", 1)[-1], item)
                    .get("properties", {})
                    .get("kind", {})
                    .get("const")
                    == value.get("kind")
                ),
                shape["oneOf"][0],
            )
            return collect(shape, value, trail)
        replacements = []
        if shape.get("type") == "string":
            if shape.get("minLength", 0):
                replacements += ["", " "]
            if "maxLength" in shape:
                replacements.append("x" * (shape["maxLength"] + 1))
            if "pattern" in shape:
                replacements.append("SECRET SENTINEL")
        if "enum" in shape or "const" in shape:
            replacements.append("unknown_local_enum")
        if shape.get("type") in {"integer", "number"}:
            replacements.append("1")
            if "minimum" in shape:
                replacements.append(shape["minimum"] - 1)
            if "maximum" in shape:
                replacements.append(shape["maximum"] + 1)
        if shape.get("type") == "array":
            if shape.get("minItems", 0):
                replacements.append([])
            if "maxItems" in shape and value:
                replacements.append(value * (shape["maxItems"] + 1))
            if value:
                collect(shape["items"], value[0], [*trail, 0])
        for replacement in replacements:
            invalid = copy.deepcopy(sample)
            target = invalid
            for segment in trail[:-1]:
                target = target[segment]
            target[trail[-1]] = replacement
            cases.append(invalid)
        if shape.get("type") == "object":
            for name, child in shape.get("properties", {}).items():
                if name in value:
                    collect(child, value[name], [*trail, name])

    collect(schema, sample, [])
    assert cases
    path, kwargs = request_parts(route)
    for case in cases:
        response = client.request(route.method, path, **{**kwargs, "json": case})
        assert response.status_code == 422
        assert response.json() == INVALID


def test_boolean_literal_is_not_an_integer_confirmation():
    with pytest.raises(ValidationError):
        m.RecoveryChecks.model_validate_json(
            '{"isolation":1,"human":true,"reconciliation":true}'
        )
