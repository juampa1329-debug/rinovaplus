"""Explicit fictional examples for the fresh P6 main preview; never startup logic."""
import json
from pathlib import Path
from uuid import uuid4
from app.institutional.api import create_app
from app.institutional.spanish import load
from app.institutional.spanish_bindings import Cursor
from tools.prepare_p6_knowledge import WORK,read,save,admin
from tools.qualify_p3_workspace import Browser


def main():
    assert not (WORK/'demo-result.json').exists(),'fresh final seed only'
    settings=load(Path(read(WORK/'final-profile.json')['directory']));access=read(WORK/'final-access.json')
    b=Browser(create_app(settings));b.login(access['email'],access['password'])
    def call(path,method='GET',body=None):return b.request(path,method,body).json()
    def api(path='',method='GET',body=None):return call('/api/v1/agents'+path,method,body)
    assert not call('knowledge')['items'] and not call('memory')['items']
    records=[]
    for kind,title,text,dna in [
        ('document','Admisiones · guía de ejemplo','Este documento es ficticio y permite explorar las citas del CRM CBN. Para iniciar la orientación, indica el programa de interés y la jornada que deseas consultar. El equipo humano revisará los requisitos y la disponibilidad en el sistema académico SIIE. No confirma inscripciones, becas ni pagos.',None),
        ('document','Atención al aspirante · ejemplo','Este material es ficticio. Para consultar horarios o requisitos de matrícula, solicita revisión al equipo de admisiones. Los valores, fechas y resultados oficiales deben verificarse en SIIE. Si el aspirante pide una persona, deriva la conversación al asesor.',None),
        ('collective','Acompañamiento educativo · ejemplo','Criterio de ejemplo: escucha la consulta, utiliza un lenguaje claro, cita las fuentes vigentes y deriva las decisiones académicas al equipo humano. No reutilices datos personales de otras conversaciones.',None),
        ('dna','ADN institucional · ejemplo','',dict(mission='Ejemplo editable: acompañar al aspirante con información revisada.',voice='Clara, respetuosa y cercana.',principles='Usar fuentes vigentes y respetar la privacidad.',boundaries='SIIE conserva la autoridad académica. No confirmar pagos ni matrícula.',escalation='Derivar dudas y decisiones al equipo humano.')),
    ]:
        key=str(uuid4());prefix='knowledge/records' if kind=='document' else 'memory/records'
        body=dict(operation_id=str(uuid4()),revision=0,reason='Ejemplo ficticio persistido para explorar P6',kind=kind,title=title,body=text,owner='Equipo de admisiones · ejemplo',origin='Contenido ficticio creado para la demostración local; debe sustituirse por información institucional revisada.',valid_until='2027-10-27',confidence=80,visibility='agent_context',program_id=None,stage_id=None,dna=dna)
        call(prefix+'/'+key,'PUT',body)
        call(prefix+'/'+key+'/publish','POST',dict(operation_id=str(uuid4()),revision=1,reason='Revisión del ejemplo ficticio, sin autoridad académica',confirmed=True))
        records.append({'id':key,'kind':kind,'title':title})
    catalog=api();before={a['id']:a['state'] for a in catalog['agents']}
    docs=[v['id'] for v in records if v['kind']=='document']
    for a in sorted(catalog['agents'],key=lambda v:['guide','program','stage'].index(v['level'])):
        if a['parent_id'] and next(v for v in catalog['agents'] if v['id']==a['parent_id'])['state']!='active':
            continue
        config={**a['configuration'],'document_ids':docs,'memories':sorted(set(a['configuration']['memories'])|{'collective','semantic'})}
        api('/profiles/'+a['id'],'PUT',dict(operation_id=str(uuid4()),revision=a['revision'],name=a['name'],level=a['level'],parent_id=a['parent_id'],program_id=a['program_id'],stage_id=a['stage_id'],configuration=config))
    after=api()['agents'];assert before=={a['id']:a['state'] for a in after}
    root=next(a for a in after if a['level']=='guide')
    preview=api('/simulate','POST',dict(agent_id=root['id'],config_version=root['version'],request_id=str(uuid4()),question='¿Cómo consultar los requisitos de admisiones?',call_provider=False))
    assert preview['sources'] and not preview['network_called']
    with admin(settings.connection['database'],readonly=True) as db:
        c=Cursor(db.cursor(),settings.ticket['table_map']);counts={n:c.execute('SELECT COUNT(*) FROM '+n).fetchval() for n in ['crm.Contact','crm.Conversation','crm.Message','crm_workspace.Note','crm_workspace.Task','crm_channels2.SocialComment']}
    save(WORK/'demo-result.json',{'status':'passed','records':records,'academic_authority':False,'previous_agent_states_preserved':True,'counts':counts,'provider_calls':0,'automatic_messages':0,'preview_sources':len(preview['sources'])})
    print(json.dumps({'P6_persisted_examples':len(records),'profiles_preserve_pause':True,'provider_calls':0}))


def resume_profile_binding():
    """Explicitly finish this seed after the preserved paused ancestor gate."""
    assert not (WORK/'demo-result.json').exists()
    settings=load(Path(read(WORK/'final-profile.json')['directory']));access=read(WORK/'final-access.json')
    b=Browser(create_app(settings));b.login(access['email'],access['password'])
    catalog=b.request('/api/v1/agents').json();records=[]
    for path in ['knowledge','memory','memory?kind=dna']:
        for v in b.request(path).json()['items']:
            assert v['state']=='published' and 'ejemplo' in v['document']['title'] and 'ficticio' in v['document']['origin']
            records.append({'id':v['id'],'kind':v['kind'],'title':v['document']['title']})
    assert len(records)==4
    docs={v['id'] for v in records if v['kind']=='document'}
    for v in catalog['agents']:
        if v['level']!='stage':assert set(v['configuration']['document_ids'])==docs
    root=next(a for a in catalog['agents'] if a['level']=='guide')
    preview=b.request('/api/v1/agents/simulate','POST',dict(agent_id=root['id'],config_version=root['version'],request_id=str(uuid4()),question='¿Cómo consultar los requisitos de admisiones?',call_provider=False)).json()
    assert preview['sources'] and not preview['network_called']
    with admin(settings.connection['database'],readonly=True) as db:
        c=Cursor(db.cursor(),settings.ticket['table_map']);counts={n:c.execute('SELECT COUNT(*) FROM '+n).fetchval() for n in ['crm.Contact','crm.Conversation','crm.Message','crm_workspace.Note','crm_workspace.Task','crm_channels2.SocialComment']}
    save(WORK/'demo-result.json',{'status':'passed','records':records,'academic_authority':False,'previous_agent_states_preserved':True,'counts':counts,'provider_calls':0,'automatic_messages':0,'preview_sources':len(preview['sources']),'paused_ancestor_preserved':'Stage example retains original configuration while program ancestor paused; no forced activation for demo.'})
    print(json.dumps({'P6_persisted_examples':len(records),'profiles_preserve_pause':True,'provider_calls':0}))


if __name__=='__main__':main()
