"""Confirmed paid-result replay also binds module authority; controlled gateway."""
import json
from pathlib import Path
from uuid import uuid4
from app.institutional.api import create_app
from app.institutional.spanish import load
from tools.prepare_p6_knowledge import WORK,read,save
from tools.qualify_p3_workspace import Browser


def main():
    settings=load(Path(read(WORK/'runtime-r3-profile.json')['directory']));access=read(WORK/'runtime-r3-access.json');calls=[];checks=[]
    class Gateway:
        def __init__(self,keys):
            self.keys=keys;self.hermes_base='';self.transport=None;self.last_usage=None;self.last_response_metadata={}
        async def generate(self,provider,model,config,system,messages,*,before_attempt=None,response_schema=None):
            if before_attempt:before_attempt()
            context=json.loads(messages[0]['content'].split('\n',1)[1]);sources=context['institutional_sources_sql_primary_documents_supplemental'];assert sources
            calls.append(1);self.last_usage={'input':31,'output':19};self.last_response_metadata={'finish_reason':'STOP'}
            return json.dumps({'answer':'Consulta la guía vigente.','handoff':False,'references':[sources[0]['id']],'memory':[]})
    b=Browser(create_app(settings,agent_gateway_factory=Gateway));b.login(access['email'],access['password'])
    def call(path,method='GET',body=None,expected=200):return b.request(path,method,body,expected).json()
    def check(name,ok=True):assert ok,name;checks.append(name)
    docs=call('knowledge')['items'];doc=next(v for v in docs if v['document']['title']=='Contenido controlado document')
    call('knowledge/records/'+doc['id']+'/restore','POST',dict(operation_id=str(uuid4()),revision=doc['revision'],reason='Restaurar vigencia para comprobar autoridad de replay',confirmed=True,version=2))
    guide=next(v for v in call('/api/v1/agents')['agents'] if v['level']=='guide')
    def command():return dict(agent_id=guide['id'],config_version=guide['version'],question='solazul',request_id=str(uuid4()),call_provider=True,acknowledge_consumption=True)
    for module in ['knowledge','memory']:
        cmd=command();result=call('/api/v1/agents/simulate','POST',cmd);check(module+'_initial_response_has_valid_current_reference',bool(result['references']))
        before=len(calls);old=call('settings/modules');document=old['document'];changed={**document,'enabled':{**document['enabled'],module:False}}
        call('settings/modules','PUT',dict(operation_id=str(uuid4()),revision=old['revision'],document=changed))
        call('/api/v1/agents/simulate','POST',cmd,409);check(module+'_disable_blocks_confirmed_replay_without_second_charge',len(calls)==before)
        latest=call('settings/modules');call('settings/modules','PUT',dict(operation_id=str(uuid4()),revision=latest['revision'],document=document))
    # Real TXT upload must preserve the visible editorial confidence, including0.
    import base64
    key=str(uuid4())
    call('knowledge/upload','POST',dict(operation_id=str(uuid4()),revision=0,reason='Confianza editorial cero conservada',record_id=key,title='Confianza cero controlada',filename='zero.txt',content_base64=base64.b64encode(b'Contenido controlado').decode(),owner='Admisiones',origin='Sintético',valid_until='2027-12-31',confidence=0))
    item=next(v for v in call('knowledge')['items'] if v['id']==key)
    check('base64_upload_confidence_zero_roundtrips_SQL',item['document']['confidence']==0)
    save(WORK/'replay-switch-result.json',{'status':'passed','checks':checks,'controlled_calls':len(calls),'real_provider_calls':0})
    print(json.dumps({'status':'passed','replay_and_upload_checks':len(checks),'controlled_calls':len(calls)}))


if __name__=='__main__':main()
