"""Cited generation, effective-version invalidation and private context in SQL2019.

The injected gateway never opens a socket or incurs a provider charge.
"""
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

from app.institutional.api import create_app
from app.institutional.spanish import load
from app.institutional.spanish_bindings import Cursor
from tools.prepare_p6_knowledge import WORK,read,save,admin
from tools.qualify_p3_workspace import Browser


def main():
    label=os.environ.get('P6_RUNTIME_LABEL','runtime-r2')
    settings=load(Path(read(WORK/(label+'-profile.json'))['directory']))
    access=read(WORK/(label+'-access.json'));calls=[];entered=threading.Event();release=threading.Event();checks=[]
    class Gateway:
        def __init__(self,keys):
            self.keys=keys;self.hermes_base='';self.transport=None;self.last_usage=None;self.last_response_metadata={}
        async def generate(self,provider,model,config,system,messages,*,before_attempt=None,response_schema=None):
            if before_attempt:before_attempt()
            assert provider=='gemini' and model=='p6-controlled-model'
            evidence=json.loads(messages[0]['content'].split('\n',1)[1]) if messages[0]['content'].startswith('Contexto de referencia') else json.loads(next(m['content'].split('\n',1)[1] for m in messages if m['content'].startswith('Contexto de referencia')))
            sources=evidence['institutional_sources_sql_primary_documents_supplemental']
            calls.append({'system':system,'evidence':evidence})
            if 'P6_WAIT' in messages[-1]['content']:
                entered.set();assert release.wait(45)
            self.last_usage={'input':31,'output':19};self.last_response_metadata={'finish_reason':'STOP'}
            return json.dumps({'answer':'Según la guía revisada, consulta al equipo de admisiones.','handoff':False,'references':[sources[0]['id']] if sources else [],'memory':[]})
    app=create_app(settings,agent_gateway_factory=Gateway);b=Browser(app);b.login(access['email'],access['password'])
    def call(path,method='GET',body=None,expected=200):
        result=b.request(path,method,body,expected);return result.json()
    def api(path='',method='GET',body=None,expected=200):return call('/api/v1/agents'+path,method,body,expected)
    def sql(query,*params):
        with admin(settings.connection['database'],readonly=True) as db:return Cursor(db.cursor(),settings.ticket['table_map']).execute(query,*params).fetchall()
    def check(name,ok=True):
        assert ok,name
        checks.append(name);save(WORK/'runtime-result.json',{'status':'in_progress','checks':checks,'controlled_calls':len(calls),'real_provider_calls':0})
    def setting(section,**fields):
        old=call('settings/'+section);call('settings/'+section,'PUT',dict(operation_id=str(uuid4()),revision=old['revision'],document={**old['document'],**fields}))
    models=call('settings/models')['document'];selections=[v for v in models['selections'] if not(v['provider']=='gemini' and v['category']=='text')]+[dict(provider='gemini',category='text',selected_model='p6-controlled-model',display_name='Modelo controlado P6')]
    setting('models',selections=selections);setting('ai',enabled=True);setting('budgets',daily_tokens=10000000,daily_usd_micros=10000000)
    call('credentials','PUT',dict(operation_id=str(uuid4()),scope='provider',owner='gemini',kind='api_key',value='controlled-not-a-real-key-'+uuid4().hex))
    def create(kind,text,*,conversation=None,message=None,quote='',program=None,stage=None,visibility=None):
        key=str(uuid4());prefix='conversation-memory/'+conversation if conversation else 'knowledge/records' if kind=='document' else 'memory/records'
        body=dict(operation_id=str(uuid4()),revision=0,reason='Revisión controlada P6',kind=kind,title='Contenido controlado '+kind,body=text,owner='Admisiones',origin='Sintético controlado',valid_until='2027-12-31',confidence=80,visibility=visibility or ('conversation_only' if conversation else 'agent_context'),program_id=program,stage_id=stage,dna=None,source_message_id=message,quote=quote)
        if kind=='dna':body.update(body='',dna=dict(mission=text,voice='Clara',principles='Citar fuentes',boundaries='Autoridad académica SIIE',escalation='Revisión humana'))
        call(prefix+'/'+key,'PUT',body);entry={'id':key,'prefix':prefix,'revision':1,'body':body};transition(entry);return entry
    def transition(entry,action='publish',expected=200,**extra):
        result=call(entry['prefix']+'/'+entry['id']+'/'+action,'POST',dict(operation_id=str(uuid4()),revision=entry['revision'],reason='Revisión controlada de versión',confirmed=True,**extra),expected)
        if expected==200 and action!='reindex':entry['revision']=result['revision']
        return result
    doc=create('document','Requisitos solazul: documento y formulario de inscripción.')
    collective=create('collective','Memoria colectiva marca_compartida.')
    dna=create('dna','Misión educativa marca_adn.')
    staff=create('collective','No divulgar marca_reservada.',visibility='staff_only')
    guide=next(v for v in api()['agents'] if v['level']=='guide')
    cfg={**guide['configuration'],'provider':'gemini','primary_model':'p6-controlled-model','fallback_model':'','monthly_token_limit':10000000,'input_usd_per_million':1.0,'output_usd_per_million':1.0,'document_ids':[doc['id']], 'memories':sorted(set(guide['configuration']['memories'])|{'knowledge','semantic','collective','customer_profile'}),'capabilities':sorted(set(guide['configuration']['capabilities'])|{'sources.read','conversation.reply','human.handoff'})}
    api('/profiles/'+guide['id'],'PUT',dict(operation_id=str(uuid4()),revision=guide['revision'],name=guide['name'],level='guide',configuration=cfg))
    guide=next(v for v in api()['agents'] if v['id']==guide['id'])
    def command(question='solazul'):
        return dict(agent_id=guide['id'],config_version=guide['version'],question=question,request_id=str(uuid4()),call_provider=True,acknowledge_consumption=True,channel='local')
    cmd=command();result=api('/simulate','POST',cmd)
    check('controlled_response_cites_only_current_reviewed_chunk',result['network_called'] and result['references'] and len(calls)==1)
    text=json.dumps(calls[-1],ensure_ascii=False)
    check('shared_DNA_compose_without_editor_only_content','marca_compartida' in text and 'marca_adn' in text and 'marca_reservada' not in text)
    api('/simulate','POST',cmd);check('same_nonce_replays_without_second_charge',len(calls)==1)
    transition(collective,'archive');api('/simulate','POST',cmd,409);check('confirmed_replay_invalidated_after_memory_archive',len(calls)==1)
    transition(collective,'restore',version=2)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending=pool.submit(api,'/simulate','POST',command('solazul P6_WAIT'),409)
        assert entered.wait(40)
        transition(dna,'archive');release.set();pending.result(timeout=50)
    check('inflight_DNA_change_blocks_stale_result_without_retry',len(calls)==2)
    transition(dna,'restore',version=2)
    # Conversation-bound generation includes only private facts from its active
    # reviewed context. Generic simulations cannot select a conversation UUID.
    conv=str(sql("SELECT TOP(1) ConversationId FROM crm.Conversation WHERE State='open' ORDER BY ConversationId")[0][0]).lower()
    incoming=sql("SELECT TOP(1) MessageId,Body FROM crm.Message WHERE ConversationId=? AND Direction='incoming' ORDER BY Sequence",conv)[0]
    ctx=api('/conversations/'+conv)
    api('/conversations/'+conv+'/assignment','PUT',dict(operation_id=str(uuid4()),revision=ctx['revision'],mode='manual',agent_id=guide['id'],context_id=None,note='Selección controlada',confirmed=True))
    private=create('private',incoming[1][:100],conversation=conv,message=str(incoming[0]).lower(),quote=incoming[1][:2000])
    def draft():
        row=api('/conversations/'+conv)
        return api('/conversations/'+conv+'/draft','POST',dict(revision=row['revision'],request_id=str(uuid4()),question='solazul',channel='local',call_provider=True,acknowledge_consumption=True))
    draft();text=json.dumps(calls[-1],ensure_ascii=False)
    check('native_Inbox_draft_receives_only_its_grounded_private_memory',incoming[1][:100] in text and private['id'] in text)
    api('/simulate','POST',command());check('generic_simulation_never_reads_private_fact',private['id'] not in json.dumps(calls[-1]))
    program=api('/programs')['items'][0]['program_id'];context=str(uuid4())
    child=next(v for v in api()['agents'] if v['level']=='program' and v['program_id']==program)
    api('/profiles/'+child['id'],'PUT',dict(operation_id=str(uuid4()),revision=child['revision'],name=child['name'],level='program',parent_id=guide['id'],program_id=program,configuration=cfg))
    child=next(v for v in api()['agents'] if v['id']==child['id'])
    if child['state']!='active':
        api('/profiles/'+child['id']+'/state','POST',dict(operation_id=str(uuid4()),revision=child['revision'],state='active',note='Activación controlada de programa',confirmed=True))
    api('/conversations/'+conv+'/contexts/'+context,'PUT',dict(operation_id=str(uuid4()),revision=0,program_id=program,evidence='Programa confirmado por operador',confirmed=True))
    row=api('/conversations/'+conv)
    api('/conversations/'+conv+'/assignment','PUT',dict(operation_id=str(uuid4()),revision=row['revision'],mode='manual',agent_id=child['id'],context_id=context,note='Nuevo contexto revisado',confirmed=True))
    draft();check('changed_context_excludes_previous_private_fact',private['id'] not in json.dumps(calls[-1]))
    transition(private,'publish',expected=409);check('previous_context_fact_cannot_be_republished_silently')
    transition(private,'archive');check('previous_context_fact_can_be_archived')
    scoped_private=create('private',incoming[1][:100],conversation=conv,message=str(incoming[0]).lower(),quote=incoming[1][:2000])
    draft();check('new_context_explicit_review_can_include_fact',scoped_private['id'] in json.dumps(calls[-1]))
    api('/conversations/'+conv+'/contexts/'+context,'PUT',dict(operation_id=str(uuid4()),revision=1,program_id=program,evidence='Revisión actualizada del contexto',confirmed=True))
    draft();check('same_context_new_revision_excludes_old_fact',scoped_private['id'] not in json.dumps(calls[-1]))
    # Source expiry is metadata, checked before text retrieval, not an instruction.
    with admin(settings.connection['database']) as db:
        c=Cursor(db.cursor(),settings.ticket['table_map']);c.execute("UPDATE crm_knowledge6.Record SET ValidUntil='2020-01-01' WHERE RecordId=?",doc['id'])
    response=api('/simulate','POST',{**command(),'call_provider':False})
    check('SQL_expiry_removes_source_before_prompt_body',not response['sources'])
    check('zero_outbound_messages_created',sql('SELECT COUNT(*) FROM crm_channels2.SendJob WHERE State=\'queued\'')[0][0]==0)
    save(WORK/'runtime-result.json',{'status':'passed','checks':checks,'controlled_calls':len(calls),'real_provider_calls':0,'database':settings.connection['database']})
    print(json.dumps({'status':'passed','P6_runtime_checks':len(checks),'controlled_calls':len(calls)}))


if __name__=='__main__':main()
