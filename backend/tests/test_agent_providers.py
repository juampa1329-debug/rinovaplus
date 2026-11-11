"""Profile provider selection and execution without credentials or external IO."""

import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.modules.agents.domain import (
    AgentWrite,
    Configuration,
    digest,
    effective_configuration,
)
from app.modules.agents.generation import complete, provider_options, validate_selection
from app.modules.agents.service import replay
from app.modules.ai.application.admissions_prompt import AdmissionsPolicy
from app.modules.ai.domain.models import AiSettings, ModelInfo
from app.modules.ai.infrastructure.providers import AiError


def runtime(generate=None):
    settings = AiSettings(
        enabled=True,
        provider="gemini",
        model="saved-gemini",
        provider_models={"gemini": "saved-gemini"},
    )
    gateway = SimpleNamespace(
        keys={"gemini": "synthetic-only"},
        hermes_base="",
        last_usage=None,
        last_response_metadata={},
        generate=generate,
    )
    ai = SimpleNamespace(
        repository=SimpleNamespace(read=lambda: SimpleNamespace(settings=settings)),
        gateway=gateway,
        catalogs={},
        busy=False,
        outbound=True,
        refresh_credentials=lambda: None,
    )
    ai.connection_snapshot = lambda: {
        "credential_revision": 3,
        "providers": [
            {"id": "gemini", "configured": True},
            {"id": "openai", "configured": False},
        ],
    }
    return ai, settings


def test_provider_options_reads_cache_and_config_without_discovery():
    ai, _ = runtime()
    ai.catalogs = {
        "gemini": {"cached-gemini": ModelInfo(id="cached-gemini", name="Cached model")}
    }
    options = provider_options(ai)
    gemini = next(p for p in options["providers"] if p["id"] == "gemini")
    assert {m["id"]: m["origin"] for m in gemini["models"]} == {
        "cached-gemini": "cached_catalog",
        "saved-gemini": "saved_configuration",
    }
    assert gemini["configured"] and gemini["catalog_loaded"]
    assert not next(p for p in options["providers"] if p["id"] == "openai")["models"]
    assert not options["network_called"]


def test_changing_provider_cannot_reuse_another_providers_model():
    ai, _ = runtime()
    configuration = Configuration(
        provider="openai", primary_model="saved-gemini"
    ).model_dump(mode="json")
    with pytest.raises(AiError, match="agents_provider_model_catalog_required"):
        validate_selection(
            configuration,
            provider_options(ai),
            {"provider": "gemini", "primary_model": "saved-gemini"},
        )


def test_unchanged_saved_profile_remains_editable_after_catalog_cache_expires():
    ai, _ = runtime()
    configuration = Configuration(
        provider="gemini", primary_model="reviewed-profile-model"
    ).model_dump(mode="json")
    validate_selection(configuration, provider_options(ai), configuration)
    assert Configuration().provider == "openrouter"


def test_pre_provider_request_keeps_its_original_idempotency_hash():
    request = AgentWrite(
        operation_id=uuid4(),
        revision=0,
        name="Legacy guide",
        level="guide",
        configuration=Configuration(),
    )
    legacy = request.model_dump(mode="json")
    original_fields = {
        "instructions",
        "objectives",
        "rules",
        "tone",
        "channels",
        "capabilities",
        "document_ids",
        "primary_model",
        "fallback_model",
        "max_tokens",
        "monthly_token_limit",
        "allow_reply",
    }
    legacy["configuration"] = {
        k: v for k, v in legacy["configuration"].items() if k in original_fields
    }
    expected = digest(["agent_config", "legacy", legacy])
    cursor = SimpleNamespace(
        execute=lambda *args: SimpleNamespace(fetchone=lambda: (expected,))
    )
    assert replay(cursor, "agent_config", "legacy", request) == (True, expected)


def test_profile_configuration_roundtrips_provider_and_uuid_sources():
    config = Configuration(provider="gemini", document_ids=[uuid4()])
    effective = effective_configuration(
        [
            {
                "name": "Synthetic profile",
                "level": "guide",
                "configuration": config.model_dump(mode="json"),
            }
        ]
    )
    assert effective["provider"] == "gemini"
    assert effective["document_ids"] == config.model_dump(mode="json")["document_ids"]


def test_execution_uses_profile_provider_models_and_budget_without_global_writes():
    calls, guards = [], []
    ai, saved = runtime()

    async def generate(
        provider,
        model,
        settings,
        system,
        messages,
        before_attempt,
        response_schema=None,
    ):
        before_attempt()
        calls.append((provider, model, settings.max_tokens, settings.output_tokens))
        ai.gateway.last_usage = {"input": 12, "output": 6}
        ai.gateway.last_response_metadata = {}
        return '{"answer":"Synthetic reply","handoff":true,"references":[],"memory":[]}'

    ai.gateway.generate = generate
    selection = {
        "configuration": Configuration(
            provider="gemini", primary_model="profile-model", max_tokens=321
        ).model_dump(mode="json")
    }
    policy = AdmissionsPolicy(primary_model="profile-model", max_tokens=321)
    result = asyncio.run(
        complete(
            ai,
            selection,
            policy,
            [
                {"role": "system", "content": "Rules"},
                {"role": "user", "content": "Question"},
            ],
            lambda: guards.append(True),
        )
    )
    assert calls == [("gemini", "profile-model", 321, 321)]
    assert result["provider"] == "gemini" and result["model"] == "profile-model"
    assert result["usage"] == {"prompt_tokens": 12, "completion_tokens": 6}
    assert saved.model == "saved-gemini" and saved.max_tokens == 700
    assert len(guards) >= 3 and not ai.busy


@pytest.mark.parametrize(
    "code,expected",
    [
        ("provider_model_unavailable", ["first", "second"]),
        ("provider_response_timeout", ["first"]),
        ("provider_temporary_failure", ["first"]),
        ("provider_retries_exhausted", ["first"]),
        ("provider_timeout", ["first"]),
    ],
)
def test_fallback_is_explicit_same_provider_and_never_replays_uncertain_post(
    code, expected
):
    calls = []
    ai, _ = runtime()

    async def generate(provider, model, *args, **kwargs):
        calls.append(model)
        if model == "first":
            raise AiError(code, 503)
        return "{}"

    ai.gateway.generate = generate
    selection = {"configuration": {"provider": "gemini"}}
    policy = AdmissionsPolicy(primary_model="first", fallback_model="second")
    if len(expected) == 1:
        with pytest.raises(AiError, match=code):
            asyncio.run(complete(ai, selection, policy, [], lambda: None))
    else:
        result = asyncio.run(complete(ai, selection, policy, [], lambda: None))
        assert result["model"] == "second" and result["provider"] == "gemini"
    assert calls == expected and not ai.busy


def test_missing_selected_provider_blocks_without_using_configured_gemini():
    ai, _ = runtime()
    with pytest.raises(AiError, match="agents_provider_not_configured"):
        asyncio.run(
            complete(
                ai,
                {"configuration": {"provider": "openai"}},
                AdmissionsPolicy(primary_model="model"),
                [],
                lambda: None,
            )
        )
    assert not ai.busy
