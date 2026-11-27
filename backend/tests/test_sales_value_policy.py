from copy import deepcopy
from app.modules.agents.skill_policy import for_turn, instructions, project_facts
from app.institutional.program_commercial import agent_facts


def test_scholarship_and_diplomas_stay_available_during_price_negotiation():
 facts={'presentation':'Beca opcional del 100 % para toda la carrera de Gestión Ambiental, con diploma al completarla.',
        'price_cop':1860000,'financial_plans':[{'initial_payment_cop':490000}], 'syllabus':'Detalle largo'}
 for question in ['¿Cuánto vale?', 'Me parece caro']:
  result=project_facts(facts,for_turn(question))
  assert result['presentation']==facts['presentation'] and result['financial_plans']==facts['financial_plans']
  assert 'syllabus' not in result


def test_common_agent_policy_uses_calendar_benefit_and_confirmed_university_conditions():
 for question in ['Información de Cocina','Me parece caro','¿Puedo homologar después?']:
  prompt=instructions(for_turn(question))
  assert 'tranquilidad y organización financiera' in prompt
  assert 'recuperar la inversión de la formación completa' in prompt
  assert 'cada universidad' in prompt and 'materias reconocidas' in prompt
  assert 'no cambies precios, fechas ni jornadas' in prompt
  assert 'No llames beca a una doble titulación obligatoria' in prompt


def test_derived_sales_facts_never_change_reviewed_price_or_payment_dates():
 for date in ['2027-03-08','2027-02-10']:
  profile={'price_cop':800000,'price_concept':'Primer semestre',
    'financial_plans':[{'external_id':'real','initial_payment_cop':220000,'initial_payment_due_date':'2026-12-16',
                        'total_cost_cop':880000,'installments':[{'number':1,'amount_cop':660000,'due_date':date}]}]}
  before=deepcopy(profile)
  result=agent_facts(profile)
  assert profile==before
  assert result['financial_plans']==profile['financial_plans']
  assert result['price_cop']==profile['price_cop']
