"""Analysis boundaries with synthetic provider responses; no external IO."""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from app.modules.ai.domain.models import ModelInfo
from app.modules.conversation_analysis.domain.models import AnalysisContext
from app.modules.conversation_analysis.application.runtime import AnalysisWorker, binding


def setup_worker(monkeypatch):
    policy = {
        "revision": "1",
        "enabled": True,
        "provider": "gemini",
        "model": "synthetic-model",
        "outputTokens": 700,
    }
    service = Mock()
    service.connection_snapshot.return_value = {
        "credential_revision": 0,
        "outbound_enabled": True,
    }
    service.repository.read.return_value = SimpleNamespace(revision=0)
    service.gateway.keys = {"gemini": "synthetic-key"}
    service.gateway.transport = None
    repository = Mock()
    repository.configuration.return_value = {"policy": policy}
    identifier = str(uuid4())
    job = {
        "policy": policy,
        "binding": binding(service, policy),
        "payload": {
            "messages": [
                {
                    "reference": "m1",
                    "direction": "outgoing",
                    "text": "Información registrada",
                }
            ]
        },
        "references": {"m1": (identifier, "outgoing")},
        "known": [],
    }
    repository.reserve.return_value = job
    gateway = Mock()
    gateway.models = AsyncMock(
        return_value=[ModelInfo(id="synthetic-model", name="Synthetic")]
    )
    gateway.generate = AsyncMock(
        return_value=json.dumps({key: [] for key in AnalysisContext.model_fields})
    )
    monkeypatch.setattr("app.modules.conversation_analysis.application.runtime.ProviderGateway", lambda *args: gateway)
    return (
        AnalysisWorker(repository, service),
        repository,
        service,
        gateway,
        job,
        identifier,
    )


def test_disabled_analysis_never_calls_provider(monkeypatch):
    worker, repository, service, gateway, _, _ = setup_worker(monkeypatch)
    repository.configuration.return_value = {"policy": None}
    assert asyncio.run(worker.cycle()) == "disabled"
    service.require_outbound.assert_not_called()
    gateway.generate.assert_not_called()
    repository.reserve.assert_not_called()


def test_reserved_job_uses_opaque_references_and_no_assistant_prompt(monkeypatch):
    worker, repository, _, gateway, job, identifier = setup_worker(monkeypatch)
    assert asyncio.run(worker.cycle()) == "running"
    repository.reserve.assert_called_once()
    args = gateway.generate.call_args.args
    assert args[0:2] == ("gemini", "synthetic-model")
    assert identifier not in args[4][0]["content"]
    assert "m1" in args[4][0]["content"]
    assert "prueba sintética aislada" not in args[3]
    assert "no generes SQL" in args[3]
    repository.complete.assert_called_once_with(
        job, {key: [] for key in AnalysisContext.model_fields}, job["binding"]
    )


def test_unsupported_reference_does_not_publish_context(monkeypatch):
    worker, repository, _, gateway, _, _ = setup_worker(monkeypatch)
    context = {key: [] for key in AnalysisContext.model_fields}
    context["summary"] = [
        {
            "text": "Injected claim",
            "subject": "operator",
            "kind": "declaration",
            "evidenceIds": ["m999"],
        }
    ]
    gateway.generate.return_value = json.dumps(context)
    asyncio.run(worker.cycle())
    repository.complete.assert_not_called()
    assert repository.fail.call_args.args[1] == "analysis_output_invalid"


def test_missing_key_does_not_reserve_budget_or_call_provider(monkeypatch):
    worker, repository, service, gateway, _, _ = setup_worker(monkeypatch)
    service.gateway.keys = {}
    assert asyncio.run(worker.cycle()) == "provider_key_missing"
    repository.reserve.assert_not_called()
    gateway.generate.assert_not_called()


def test_configuration_changed_before_generation_rejects_reserved_job(monkeypatch):
    worker, repository, _, gateway, job, _ = setup_worker(monkeypatch)
    repository.configuration.side_effect = [
        {"policy": job["policy"]},
        {"policy": {**job["policy"], "enabled": False, "revision": "2"}},
    ]
    assert asyncio.run(worker.cycle()) == "configuration_changed"
    gateway.generate.assert_not_called()
    repository.complete.assert_called_once_with(job, {}, None)


def test_assistant_preferences_do_not_invalidate_analysis(monkeypatch):
    _, _, service, _, job, _ = setup_worker(monkeypatch)
    original = binding(service, job["policy"])
    service.repository.read.return_value = SimpleNamespace(revision=99)
    assert binding(service, job["policy"]) == original
    service.connection_snapshot.return_value["credential_revision"] = 1
    assert binding(service, job["policy"]) != original
