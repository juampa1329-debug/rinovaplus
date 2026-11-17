from datetime import datetime, timezone

import httpx2 as httpx
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.institutional.program_commercial import FinancialPlan, agent_facts
from app.institutional.siie_catalog import preview


def plan():
    return {
        "external_id": "fixture-plan",
        "name": "Plan de prueba unitario",
        "valid_from": "2020-01-01",
        "valid_until": "2099-12-31",
        "initial_payment_cop": 200000,
        "initial_payment_due_date": "2099-01-01",
        "total_cost_cop": 600000,
        "conditions": "Fixture, no oferta real",
        "installments": [
            {"number": 1, "amount_cop": 200000, "due_date": "2099-02-01"},
            {"number": 2, "amount_cop": 200000, "due_date": "2099-03-01"},
        ],
    }


@pytest.mark.parametrize(
    "change",
    [
        {"total_cost_cop": 1},
        {"initial_payment_cop": -1},
        {"initial_payment_cop": True},
        {"initial_payment_due_date": "2099-02-30"},
        {"initial_payment_due_date": "2099-04-01"},
        {"valid_until": "2000-01-01"},
        {
            "installments": [
                {"number": 2, "amount_cop": 400000, "due_date": "2099-03-01"}
            ]
        },
    ],
)
def test_financial_plan_rejects_inconsistent_totals_dates_and_numbering(change):
    with pytest.raises(ValidationError):
        FinancialPlan.model_validate({**plan(), **change})


def test_agent_finance_facts_drop_expired_or_future_prices_and_plans():
    assert FinancialPlan.model_validate(plan()).total_cost_cop == 600000
    expired = {**plan(), "valid_from": "1999-01-01", "valid_until": "2000-12-31"}
    future = {**plan(), "valid_from": "2099-01-01"}
    facts = agent_facts(
        {
            "price_cop": 500000,
            "full_cost_cash_cop": 550000,
            "price_concept": "Programa",
            "price_valid_from": "2099-01-01",
            "price_valid_until": "2099-12-31",
            "financial_plans": [expired, future, plan()],
        }
    )
    assert "price_cop" not in facts and "full_cost_cash_cop" not in facts
    assert facts["financial_plans"] == [plan()]


def test_siie_is_disabled_without_configuration_and_never_calls_network(monkeypatch):
    for name in (
        "SIIE_CATALOG_API_URL",
        "SIIE_CATALOG_API_HOSTS",
        "SIIE_CATALOG_API_TOKEN",
    ):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(HTTPException, match="siie_catalog_not_configured"):
        preview(
            "offer",
            transport=httpx.MockTransport(lambda *_: pytest.fail("network disabled")),
        )


def configure(monkeypatch):
    monkeypatch.setenv("SIIE_CATALOG_API_URL", "https://siie.example.test/api")
    monkeypatch.setenv("SIIE_CATALOG_API_HOSTS", "siie.example.test")
    monkeypatch.setenv("SIIE_CATALOG_API_TOKEN", "fixture-not-a-real-key")


def offer():
    return {
        "schema_version": "siie-crm-commercial-v1",
        "source_system": "DBSIIE",
        "source_revision": "fixture-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "active": True,
        "offer_id": "offer",
        "program_id": "software",
        "period_id": "period",
        "campus_id": "campus",
        "shift_id": "evening",
        "currency": "COP",
        "name": "Programa fixture",
        "school": "Escuela fixture",
        "schedule": "Noche",
        "commercial": {"duration": "3 semestres", "financial_plans": [plan()]},
    }


def test_siie_preview_only_gets_one_offer_and_preserves_source_without_saving(
    monkeypatch,
):
    configure(monkeypatch)
    calls = []

    def respond(request):
        calls.append(request)
        assert (
            request.method == "GET"
            and str(request.url) == "https://siie.example.test/api/v1/crm/offers/offer"
        )
        assert request.headers["Authorization"] == "Bearer fixture-not-a-real-key"
        return httpx.Response(200, json=offer())

    result = preview("offer", transport=httpx.MockTransport(respond))
    assert (
        len(calls) == 1 and result["saved"] is False and result["siie_written"] is False
    )
    assert result["draft"].commercial.siie_offer_id == "offer"
    assert result["draft"].commercial.siie_period_id == "period"
    assert result["draft"].commercial.financial_plans[0].total_cost_cop == 600000


@pytest.mark.parametrize(
    "change",
    [
        {"offer_id": "different"},
        {"active": False},
        {"generated_at": "2000-01-01T00:00:00Z"},
    ],
)
def test_siie_rejects_stale_or_wrong_offer(monkeypatch, change):
    configure(monkeypatch)
    with pytest.raises(HTTPException, match="siie_catalog_stale_or_mismatched"):
        preview(
            "offer",
            transport=httpx.MockTransport(
                lambda *_: httpx.Response(200, json={**offer(), **change})
            ),
        )


def test_siie_does_not_follow_redirects_or_accept_arbitrary_hosts(monkeypatch):
    configure(monkeypatch)
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(302, headers={"Location": "https://other.example/steal"})

    with pytest.raises(HTTPException, match="siie_catalog_unavailable"):
        preview("offer", transport=httpx.MockTransport(respond))
    assert len(calls) == 1
    monkeypatch.setenv("SIIE_CATALOG_API_URL", "https://other.example")
    with pytest.raises(HTTPException, match="siie_catalog_endpoint_invalid"):
        preview(
            "offer",
            transport=httpx.MockTransport(lambda *_: pytest.fail("not allowed")),
        )
