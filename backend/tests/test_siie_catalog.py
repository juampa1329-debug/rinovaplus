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


def test_retired_catalog_url_never_selects_an_alternative_environment(monkeypatch):
    monkeypatch.delenv('SIIE_BASE_URL',raising=False)
    monkeypatch.setenv('SIIE_CATALOG_API_URL','https://siie.example.test/legacy/')
    monkeypatch.setenv('SIIE_CATALOG_API_HOSTS','siie.example.test')
    monkeypatch.setenv('SIIE_CATALOG_API_TOKEN','fixture-key-never-send-1234567890')
    with pytest.raises(HTTPException,match='siie_catalog_not_configured'):
        preview('900-n1',transport=httpx.MockTransport(lambda _:pytest.fail('legacy transport used')))


def test_preview_uses_shared_aspx_reader_and_preserves_environment(monkeypatch):
    from app.institutional import siie_api
    monkeypatch.setenv('SIIE_BASE_URL','https://siie.example.test/SIIEWebPlustest/')
    monkeypatch.setenv('SIIE_API_TOKEN','fixture-key-never-send-1234567890')
    source={'program_id':'143','offer_id':'900-n1','source_revision':'sha256:'+'a'*64,
            'name':'Programa fixture','currency':'COP','commercial':{'financial_plans':[plan()]}}
    env={'base_url':'https://siie.example.test/SIIEWebPlustest/','fingerprint':'b'*64}
    calls=[]
    def read(route,values,**kw):
        calls.append((route,values))
        return {'data':{'offer':source},'environment':env}
    monkeypatch.setattr(siie_api,'read',read)
    result=preview('900-n1')
    assert calls==[('offer',{'offer_id':'900-n1'})]
    assert result['source']['environment']==env
    assert result['saved'] is False and result['siie_written'] is False
    assert result['draft'].commercial.financial_plans[0].total_cost_cop==600000
