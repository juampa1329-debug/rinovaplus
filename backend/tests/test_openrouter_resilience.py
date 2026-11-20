import asyncio
from types import SimpleNamespace

import httpx2 as httpx
import pytest

from app.modules.ai.infrastructure.openrouter import OpenRouterClient
from app.modules.ai.infrastructure.providers import AiError


@pytest.mark.parametrize("status", [401, 402, 408, 500, 502, 504])
def test_ambiguous_or_auth_http_status_never_repeats_post(status):
    calls = []
    def respond(req):
        calls.append(req)
        return httpx.Response(status, json={"error": {"code": status}})
    with pytest.raises(AiError) as failure:
        asyncio.run(OpenRouterClient("fixture", httpx.MockTransport(respond)).complete(
            SimpleNamespace(primary_model="fixture:free", fallback_model="", temperature=0.3, max_tokens=100),
            [{"role": "user", "content": "Hola"}], lambda: None))
    assert len(calls) == 1
    assert failure.value.upstream_status == status
    if status == 402:
        assert failure.value.code == "openrouter_payment_required"


def test_explicit_busy_response_can_select_another_configured_route_without_waiting_past_retry_after():
    from app.modules.ai.domain.resilience import can_failover
    calls = []
    def respond(req):
        calls.append(req)
        return httpx.Response(503, headers={"retry-after": "120"}, json={"error": {"code": 503}})
    with pytest.raises(AiError) as failure:
        asyncio.run(OpenRouterClient("fixture", httpx.MockTransport(respond)).complete(
            SimpleNamespace(primary_model="fixture:free", fallback_model="", temperature=0.3, max_tokens=100),
            [{"role": "user", "content": "Hola"}], lambda: None))
    assert len(calls) == 1 and can_failover(failure.value)
