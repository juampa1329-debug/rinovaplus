"""P19 boundaries, routing and cost receipts; no real paid IO."""
from contextlib import nullcontext
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.institutional import voice_audio as v
from app.institutional.voice_policy import VoicePolicy, choose_profile, reason
from app.modules.agents.domain import Configuration
from app.modules.ai.infrastructure.providers import AiError


def profiles():
    return VoicePolicy(enabled=True,scope='all',default_profile_id='default',profiles=[
        {'id':'default','name':'Institucional','voice_id':'first','model_id':'model'},
        {'id':'salud','name':'Salud','voice_id':'second','model_id':'model','schools':['Escuela Salud']},
        {'id':'direct','name':'Agente','voice_id':'third','model_id':'model'},
    ])


def test_direct_agent_choice_school_default_and_pinned_continuity():
    p=profiles(); agent=str(uuid4());p.profiles[0].agent_ids=[agent]
    assert choose_profile(p,agent,['Escuela Salud'],selected_profile='direct').voice_id=='third'
    assert choose_profile(p,None,['escuela salud']).voice_id=='second'
    assert choose_profile(p,None,[]).voice_id=='first'
    pinned=choose_profile(p,None,['Escuela Salud']).model_dump()
    assert choose_profile(p,agent,[],pinned,'direct').voice_id=='second'
    p.profiles[1].active=False
    assert choose_profile(p,agent,[],pinned,'direct') is None
    assert choose_profile(p,agent,[],selected_profile='removed') is None
    # A newly created catalog profile is selectable without changing the schema.
    p.profiles[1].active=True
    assert Configuration(voice_profile_id='salud').voice_profile_id=='salud'
    with pytest.raises(ValidationError):Configuration(voice_profile_id='../raw-provider-id')


@pytest.mark.parametrize('change,code',[
    ({'enabled':False},'voice_paused'),({'max_audios_per_conversation':0},'voice_conversation_limit'),
    ({'max_text_chars':120,'long_reply_min_chars':120},'voice_text_too_large'),
    ({'max_audio_seconds':1},'voice_duration_estimated_exceeded'),
])
def test_pause_and_limits_keep_complete_text(change,code):
    p=profiles().model_copy(update=change);text='Explicación completa sobre el programa. '*5
    assert reason(p,text,True,0)==code
    assert text.endswith('programa. ')


def test_provider_balance_excludes_payment_and_personal_data_and_never_infers_cost():
    result=v.public_balance({'character_count':120,'character_limit':1000,'tier':'starter',
        'next_character_count_reset_unix':1800000000,'open_invoices':[{'secret':'private'}],'email':'hidden@example.invalid'})
    assert result['remaining']==880 and result['used']==120
    assert 'open_invoices' not in result and 'email' not in result and 'cost_usd' not in result
    assert v.public_balance({'character_count':1100,'character_limit':1000})['remaining']==0
    for invalid in [{}, {'character_count':True,'character_limit':1000},{'character_count':-1,'character_limit':2}]:
        with pytest.raises(AiError):v.public_balance(invalid)


def test_new_options_route_checks_authority_before_reading_profiles(monkeypatch):
    app=FastAPI()
    @app.middleware('http')
    async def authority(request,next):
        request.state.authority='test';return await next(request)
    monkeypatch.setattr(v,'transaction',lambda *_a,**_k:nullcontext(None))
    def denied(*args,**kwargs):raise HTTPException(403,'action_denied')
    monkeypatch.setattr(v,'authorize',denied)
    monkeypatch.setattr(v,'assignment_options',lambda *_:pytest.fail('unauthorized read'))
    v.install(app,None)
    with TestClient(app) as client:response=client.get('/api/institution/voice/options')
    assert response.status_code==403


def test_check_accepts_json_identifiers_but_cannot_write_or_call_providers(monkeypatch):
    app=FastAPI()
    @app.middleware('http')
    async def authority(request,next):request.state.authority='test';return await next(request)
    monkeypatch.setattr(v,'transaction',lambda *_a,**_k:nullcontext(None))
    monkeypatch.setattr(v,'authorize',lambda *_a,**_k:None)
    seen=[]
    def check(c,s,body):
        seen.append(str(body.conversation_id));return {'network_called':False,'persisted':False}
    monkeypatch.setattr(v,'check_decision',check);v.install(app,None)
    conversation=str(uuid4())
    with TestClient(app) as client:
        response=client.post('/api/institution/voice/check',json={'conversation_id':conversation,'text':'Prueba','incoming_voice':True})
    assert response.status_code==200 and seen==[conversation]


def test_daily_limit_and_uncertain_reservations_are_durable_before_provider_io(monkeypatch):
    p=profiles();p.daily_character_limit=100
    monkeypatch.setattr(v,'uid',str);monkeypatch.setattr(v,'bound_hash',lambda *_:b'digest')
    monkeypatch.setattr(v,'one',lambda *_:None);monkeypatch.setattr(v,'policy',lambda *_:p)
    monkeypatch.setattr(v,'institution',lambda *_:'institution')
    monkeypatch.setattr(v,'usage',lambda *_:{'used':0,'daily_attempts':0,'daily_characters':90})
    cursor=SimpleNamespace(execute=lambda *_:pytest.fail('over-budget write'))
    with pytest.raises(HTTPException,match='voice_daily_limit'):
        v.reserve(cursor,None,str(uuid4()),'app','integration','actor',{'characters':11})
    p.daily_character_limit=0
    inserted=[];cursor.execute=lambda *args:inserted.append(args)
    monkeypatch.setattr(v,'institution',lambda *_:'institution')
    assert v.reserve(cursor,None,str(uuid4()),'app','integration','actor',{'characters':11})
    assert len(inserted)==1


def test_metered_usage_translates_to_native_postgres_without_replacing_missing_receipts(monkeypatch):
    from app.institutional.postgres_dialect import postgres_sql
    parse_sql=pytest.importorskip('pglast').parse_sql
    statements=[]
    class Cursor:
        def execute(self,sql,*params):statements.append(sql);return self
        def fetchone(self):return (0,None,2,1)
    monkeypatch.setattr(v,'institution',lambda *_:'institution')
    assert v.metered_usage(Cursor(),None)=={'reported_attempts':0,'reported_characters':None,'uncertain_attempts':2,'running_attempts':1}
    sql=postgres_sql(statements[0],{'crm_channels2.ProviderOperation':'rinovaplus_crm.provideroperation'})
    parse_sql(sql.replace('%s',"'fixture'"))


def test_read_only_check_uses_actual_control_and_never_accepts_forged_context(monkeypatch):
    monkeypatch.setattr(v,'policy',lambda *_:profiles())
    monkeypatch.setattr(v,'usage',lambda *_:{'used':2,'pinned':None,'daily_characters':90})
    monkeypatch.setattr(v,'institution',lambda *_:'institution')
    monkeypatch.setattr(v,'one',lambda *_:{'ControlMode':'human','State':'open'})
    body=v.VoiceCheck(text='Hola, ¿en qué puedo ayudarte?',incoming_voice=True,conversation_id=uuid4())
    result=v.check_decision(None,None,body)
    assert result['reason']=='voice_human_control' and not result['eligible']
    assert result['used']==2 and not result['network_called'] and not result['persisted']
    with pytest.raises(HTTPException,match='voice_check_context_immutable'):
        v.check_decision(None,None,body.model_copy(update={'agent_id':uuid4()}))


def test_check_reports_school_and_explicit_agent_using_saved_data(monkeypatch):
    from app.modules.agents import service
    p=profiles();agent=str(uuid4())
    monkeypatch.setattr(v,'policy',lambda *_:p)
    monkeypatch.setattr(v,'usage',lambda *_:{'used':0,'pinned':None,'daily_characters':90})
    monkeypatch.setattr(v,'institution',lambda *_:'institution')
    monkeypatch.setattr(v,'one',lambda *_:{'School':'Escuela Salud'})
    monkeypatch.setattr(service,'load',lambda *_:({agent:{'state':'active','program_id':7,'configuration':{'voice_profile_id':'direct'}}},{}))
    body=v.VoiceCheck(text='Hola, ¿en qué puedo ayudarte?',incoming_voice=True,program_id=7)
    assert v.check_decision(None,None,body)['profile_id']=='salud'
    assert v.check_decision(None,None,body.model_copy(update={'agent_id':agent}))['profile_id']=='direct'
    p.daily_character_limit=90
    assert v.check_decision(None,None,body)['reason']=='voice_daily_limit'
    p.daily_character_limit=0;p.enabled=False
    assert v.check_decision(None,None,body)['reason']=='voice_paused'


def test_account_usage_rechecks_authority_and_key_after_provider_read(monkeypatch):
    app=FastAPI()
    @app.middleware('http')
    async def authority(request,next):request.state.authority='test';return await next(request)
    monkeypatch.setattr(v,'transaction',lambda *_a,**_k:nullcontext(None))
    monkeypatch.setattr(v,'authorize',lambda *_a,**_k:None)
    keys=iter(['first','changed']);monkeypatch.setattr(v,'credential',lambda *_:next(keys))
    class Gateway:
        def __init__(self,*_):pass
        async def request(self,*args):
            assert args==('elevenlabs','GET','v1/user/subscription')
            return {'character_count':120,'character_limit':1000,'open_invoices':[{'private':'value'}]}
    monkeypatch.setattr(v,'MediaGateway',Gateway);v.install(app,None)
    with TestClient(app) as client:response=client.get('/api/institution/voice/balance')
    assert response.status_code==409 and 'private' not in response.text
