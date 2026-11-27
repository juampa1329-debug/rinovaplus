"""Fictitious commercial facts only. No SIIE credentials or real people."""
from copy import deepcopy
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.institutional.program_commercial import CommercialProfile, FinancialPlan, agent_facts
from app.institutional.siie_local import draft_from_source, reviewed_draft
from app.institutional.siie_catalog import preview
import httpx2 as httpx


def offer():
    return {"offer_id": "900-n1", "program_id": "143", "currency": "COP", "source_revision": "sha256:"+"a"*64,
            "schema_version": "siie-crm-commercial-v1", "source_system": "DBSIIE", "generated_at": datetime.now(timezone.utc).isoformat(),
            "name": "Programa ficticio", "school": "Escuela ficticia", "schedule": None, "active": True,
            "commercial": {"price_cop": 600000, "price_scope": "semester_tuition_only", "full_cost_cash_cop": 600000, "price_valid_from": None, "price_valid_until": None,
                           "financial_plans": [{"external_id": "900-n1-plan1", "name": "Plan ficticio", "valid_from": None, "valid_until": None, "initial_payment_cop": 200000, "initial_payment_due_date": None, "total_cost_cop": 600000, "conditions": None,
                                                "installments": [{"number": 1, "amount_cop": 400000, "due_date": None}]}]}}


def test_nullable_dates_keep_known_prices_and_explicit_agent_uncertainty():
    source = draft_from_source(offer())
    facts = agent_facts(source['values']['commercial'])
    assert facts['price_cop'] == 600000 and facts['full_cost_cash_cop'] == 600000
    assert facts['financial_plans'][0]['initial_payment_cop'] == 200000
    assert facts['financial_plans'][0]['installments'][0]['due_date'] is None
    assert 'price_valid_until' in facts['pending_confirmation']
    assert 'por confirmar' in facts['financial_guidance']


def test_manual_payment_modes_and_open_validity_survive_source_refresh():
    old = draft_from_source(offer()); current = deepcopy(old['values'])
    current['commercial'].update(payment_mode='financing', presentation='Presentación revisada',
                                  certification='Certificado de prueba', internships='Prácticas sujetas a confirmación')
    current['commercial']['financial_plans'][0]['valid_until_confirmed_open'] = True
    result, _ = reviewed_draft(current, old, draft_from_source(offer()))
    facts = agent_facts(result.commercial.model_dump())
    assert 'price_cop' not in facts and 'full_cost_cash_cop' not in facts
    assert facts['financial_plans'][0]['initial_payment_cop'] == 200000
    assert facts['presentation'] == 'Presentación revisada'
    assert not any('valid_until' in item for item in facts['pending_confirmation'])
    assert any('fecha cuota' in item for item in facts['pending_confirmation'])
    cash = agent_facts({**result.commercial.model_dump(), 'payment_mode': 'cash'})
    assert cash['price_cop'] == 600000 and 'financial_plans' not in cash
    with pytest.raises(ValidationError, match='financial_validity_open_conflict'):
        FinancialPlan.model_validate({**current['commercial']['financial_plans'][0], 'valid_until': '2099-01-01'})
    with pytest.raises(ValidationError):
        CommercialProfile(payment_mode='unknown')


def test_known_invalid_dates_and_money_totals_still_rejected():
    plan = draft_from_source(offer())['values']['commercial']['financial_plans'][0]
    for change in ({'initial_payment_due_date': '2026-02-30'}, {'total_cost_cop': 1}, {'initial_payment_cop': True}):
        with pytest.raises(ValidationError): FinancialPlan.model_validate({**plan, **change})
    partial = FinancialPlan.model_validate({**plan, 'total_cost_cop': None, 'initial_payment_cop': None})
    assert partial.initial_payment_cop is None


def test_refresh_updates_source_amounts_and_keeps_manual_due_date_even_if_source_changes():
    old = draft_from_source(offer()); current = deepcopy(old['values'])
    current['commercial']['financial_plans'][0]['installments'][0]['due_date'] = '2027-03-20'
    new = offer(); new['commercial']['financial_plans'][0]['installments'][0].update(amount_cop=450000, due_date='2027-03-25')
    new['commercial']['financial_plans'][0]['total_cost_cop'] = 650000
    result, kept = reviewed_draft(current, old, draft_from_source(new))
    plan = result.commercial.financial_plans[0]
    assert plan.installments[0].due_date == '2027-03-20'
    assert plan.installments[0].amount_cop == 450000 and plan.total_cost_cop == 650000
    assert any('due_date' in path for path in kept)


def test_refresh_does_not_copy_dates_to_a_different_offer_or_erase_finance_in_basic_sync():
    old = draft_from_source(offer()); current = deepcopy(old['values'])
    current['commercial']['financial_plans'][0]['initial_payment_due_date'] = '2027-03-20'
    other = offer();other['offer_id'] = '900-n2'
    result, _ = reviewed_draft(current, old, draft_from_source(other))
    assert result.commercial.financial_plans[0].initial_payment_due_date is None
    basic = draft_from_source({'program_id':'143','name':'Nombre nuevo','source_revision':'sha256:'+'b'*64,'duration_levels':4}, kind='program')
    result, _ = reviewed_draft(current, None, basic)
    assert result.commercial.price_cop == 600000
    assert result.commercial.financial_plans[0].initial_payment_due_date == '2027-03-20'


def test_known_inactive_source_offer_never_becomes_available_just_because_dates_are_null():
    raw=offer();raw['active']=False
    facts=agent_facts(draft_from_source(raw)['values']['commercial'])
    assert 'price_cop' not in facts and 'financial_plans' not in facts


def test_partial_offer_can_be_prepared_for_local_review_without_writing_source(monkeypatch):
    monkeypatch.setenv('SIIE_BASE_URL','https://siie.example.test/SIIEWebPlus/');monkeypatch.setenv('SIIE_API_HOSTS','siie.example.test');monkeypatch.setenv('SIIE_API_TOKEN','fixture-key-not-real-1234567890123456789')
    calls=[]
    def remote(request):
        calls.append(request.method)
        return httpx.Response(422,json={'code':'source_data_incomplete','quotable':False,'data_quality':[],'partial_offer':{**offer(),'quotable':False}})
    result=preview('900-n1',transport=httpx.MockTransport(remote))
    assert calls == ['GET'] and result['saved'] is False and result['siie_written'] is False
    assert result['draft'].commercial.financial_plans[0].valid_until is None


def test_inconsistent_plan_does_not_hide_a_valid_cash_price_or_publish_its_total():
    raw=offer();raw['commercial']['financial_plans'][0]['total_cost_cop']=1
    source=draft_from_source(raw)
    assert source['issues'] and source['values']['commercial']['price_cop']==600000
    assert source['values']['commercial']['financial_plans']==[]
