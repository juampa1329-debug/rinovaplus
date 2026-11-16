import asyncio

import httpx2 as httpx
import pytest
from fastapi import HTTPException

from app.institutional.program_commercial import agent_facts, import_program
from app.modules.ai.infrastructure.providers import ProviderGateway


def test_import_proposes_fields_from_only_the_permitted_program_url(monkeypatch):
    monkeypatch.setenv("FIRECRAWL_API_KEY", "fixture-key")
    monkeypatch.setenv("RINOVA_PROGRAM_SOURCE_HOSTS", "programs.example")
    url = "https://programs.example/enfermeria"
    hits = []

    def scrape(request):
        hits.append(request.url.host)
        assert request.headers["Authorization"] == "Bearer fixture-key"
        return httpx.Response(200, json={"success": True, "data": {
            "metadata": {"sourceURL": url, "url": url, "statusCode": 200},
            "json": {
                "name": "Auxiliar de Enfermería",
                "school": "Salud",
                "commercial": {"duration": "Tres semestres", "price_cop": 420000},
            },
        }})

    transport = httpx.MockTransport(scrape)
    with pytest.raises(HTTPException, match="program_source_host_not_allowed"):
        import_program("https://other.example/programa", transport=transport)
    assert not hits
    result = import_program(url, transport=transport)
    assert hits == ["api.firecrawl.dev"]
    assert result.commercial.source_url == url and result.commercial.source_checked_at
    assert result.commercial.duration == "Tres semestres"
    assert result.commercial.price_cop == 420000
    assert "price_cop" not in agent_facts(result.commercial.model_dump())
    assert agent_facts({
        "price_cop": 0, "price_concept": "Matrícula", "price_valid_until": "2099-12-31",
    })["price_cop"] == 0


def test_account_catalogs_use_the_saved_provider_and_keep_exact_ids():
    def catalog(request):
        if request.url.host == "generativelanguage.googleapis.com":
            assert request.headers["x-goog-api-key"] == "gemini-key"
            return httpx.Response(200, json={"models": [
                {"name": "models/gemini-fixture", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/text-embedding", "supportedGenerationMethods": ["embedContent"]},
                {"name": "models/gemini-fixture-tts", "supportedGenerationMethods": ["generateContent"]},
            ]})
        assert request.url.path == "/api/v1/models/user"
        assert request.headers["Authorization"] == "Bearer openrouter-key"
        return httpx.Response(200, json={"data": [{
            "id": "google/gemma-fixture:free",
            "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
            "supported_parameters": ["max_tokens"],
        }]})

    gateway = ProviderGateway(
        {"gemini": "gemini-key", "openrouter": "openrouter-key"}, httpx.MockTransport(catalog)
    )
    assert [m.id for m in asyncio.run(gateway.models("gemini", account_catalog=True))] == [
        "gemini-fixture",
    ]
    assert [m.id for m in asyncio.run(gateway.models("openrouter", account_catalog=True))] == [
        "google/gemma-fixture:free",
    ]
    assert asyncio.run(gateway.models("openrouter", "vision", account_catalog=True)) == []
