"""Publish planned schemas as components only, never business success responses."""

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder

from app.contracts import SUPERSEDED_PROPOSALS
from app.local_registry import LOCAL_CONTRACTS


def install_local_openapi(application: FastAPI) -> None:
    original_openapi = application.openapi

    def local_openapi():
        # Delegate FastAPI's route-version cache to its installed implementation.
        document = original_openapi()
        document["x-local-superseded-proposals"] = [
            {
                "method": route.method,
                "path": route.path,
                "disposition": "proposal_only_runtime_owned_by_live_adapter",
                "schemas": [
                    {"$ref": f"#/components/schemas/{model.__name__}"}
                    for model in LOCAL_CONTRACTS[
                        (route.method, route.path.removeprefix("/api/v1"))
                    ].models
                ],
            }
            for route in SUPERSEDED_PROPOSALS
        ]
        components = document.setdefault("components", {}).setdefault("schemas", {})
        models = {
            model for contract in LOCAL_CONTRACTS.values() for model in contract.models
        }
        for model in sorted(models, key=lambda model: model.__name__):
            schema = model.model_json_schema(
                ref_template="#/components/schemas/{model}"
            )
            definitions = schema.pop("$defs", {})
            definitions[model.__name__] = schema
            for name, definition in definitions.items():
                # Match get_openapi's exclude_none serialization, including
                # omitted null defaults, without overwriting legacy components.
                definition = jsonable_encoder(definition, exclude_none=True)
                if name in components and components[name] != definition:
                    raise RuntimeError("Local schema component collision: " + name)
                components[name] = definition
        application.openapi_schema = document
        return document

    application.openapi = local_openapi
