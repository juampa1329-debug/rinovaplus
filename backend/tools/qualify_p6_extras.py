"""Negative scope, extraction and concurrent-version qualification in the P6 fixture."""
import base64
import io
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4
from pypdf import PdfWriter
from app.institutional.api import create_app
from app.institutional.spanish import load
from app.institutional.spanish_bindings import Cursor
from tools.prepare_p6_knowledge import WORK,read,save,admin
from tools.qualify_p3_workspace import Browser


def main():
    settings=load(Path(read(WORK/'fixture-r5-profile.json')['directory']));access=read(WORK/'fixture-r5-access.json')
    app=create_app(settings);b=Browser(app);b.login(access['email'],access['password']);checks=[]
    def call(path,method='GET',body=None,expected=200):return b.request(path,method,body,expected).json()
    def check(name,ok=True):
        assert ok,name
        checks.append(name);save(WORK/'extras-result.json',{'status':'in_progress','checks':checks})
    def cmd(revision=0,**extra):return dict(operation_id=str(uuid4()),revision=revision,reason='Comprobación negativa controlada',**extra)
    stage=next(v for v in call('/api/v1/agents')['stages'] if v['approved'])
    key=str(uuid4());body=cmd(kind='document',title='Fuente de etapa controlada',body='Información de etapa alcanceetapa.',owner='Admisiones',origin='Prueba sintética',valid_until='2027-12-31',program_id=stage['program_id'],stage_id=stage['id'])
    call('knowledge/records/'+key,'PUT',body)
    call('knowledge/records/'+key+'/publish','POST',cmd(1,confirmed=True))
    def search(program,stage):return call('knowledge/search','POST',dict(query='alcanceetapa',program_id=program,stage_id=stage))['items']
    check('reviewed_stage_source_only_in_exact_program_and_stage',bool(search(stage['program_id'],stage['id'])) and not search(stage['program_id'],None) and not search(stage['program_id'],str(uuid4())) and not search(stage['program_id']+1,stage['id']))
    bad={**body,'operation_id':str(uuid4()),'stage_id':str(uuid4())}
    call('knowledge/records/'+str(uuid4()),'PUT',bad,422);check('unreviewed_foreign_stage_cannot_be_stored')
    bad={**body,'operation_id':str(uuid4()),'owner':'😀'*51};call('knowledge/records/'+str(uuid4()),'PUT',bad,422);check('real_SourceScope_owner_UTF16_limit_checked_before_SQL')
    call('knowledge/records/'+key+'/restore','POST',cmd(2,confirmed=True,version=1),409);check('draft_history_cannot_be_promoted_by_restore')
    values=[dict(body,operation_id=str(uuid4()),revision=2,body='Corrección concurrente '+str(i)) for i in range(2)]
    def edit(value):return b.client.put('/api/institution/knowledge/records/'+key,json=value,headers={'X-CRM-Local':'1','X-CSRF-Token':b.csrf}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:outcomes=list(pool.map(edit,values))
    check('concurrent_edit_commits_one_version_no_lost_update',sorted(outcomes)==[200,409])
    hist=call('knowledge/records/'+key+'/history')['items'];check('concurrent_history_remains_three_append_only_versions',len(hist)==3 and hist[0]['version']==3)
    mem=read(WORK/'api-records.json')['records']['collective']['id']
    call('knowledge/records/'+mem+'/history',expected=404);call('memory/records/'+key+'/history',expected=404);check('collection_routes_cannot_bypass_module_boundary')
    template=cmd(title='Carga negativa',filename='negative.pdf',content_base64='',owner='Admisiones',origin='PDF controlado',valid_until='2027-12-31',record_id=str(uuid4()))
    for name,mode,expected in [('active_PDF','active',415),('encrypted_PDF','encrypted',415),('OCR_only_PDF','blank',415),('oversize_TXT','large',413)]:
        writer=PdfWriter();writer.add_blank_page(612,792)
        if mode=='active':writer.add_js('app.alert("controlled")')
        if mode=='encrypted':writer.encrypt('controlled')
        out=io.BytesIO();writer.write(out);raw=out.getvalue()
        if mode=='large':raw=b'x'*5_000_001
        upload={**template,'operation_id':str(uuid4()),'record_id':str(uuid4()),'filename':'negative.txt' if mode=='large' else 'negative.pdf','content_base64':base64.b64encode(raw).decode()}
        call('knowledge/upload','POST',upload,expected);check(name+'_rejected_without_publication')
    # Feature switches stay authoritative for agent retrieval, too.
    root=next(v for v in call('/api/v1/agents')['agents'] if v['level']=='guide')
    def preview():return call('/api/v1/agents/simulate','POST',dict(agent_id=root['id'],config_version=root['version'],request_id=str(uuid4()),question='solazul',call_provider=False))
    settings_doc=call('settings/modules');flags=settings_doc['document']['enabled']
    disabled={**settings_doc['document'],'enabled':{**flags,'knowledge':False,'memory':False}}
    call('settings/modules','PUT',dict(operation_id=str(uuid4()),revision=settings_doc['revision'],document=disabled))
    response=preview();text=json.dumps(response,ensure_ascii=False)
    check('disabled_modules_remove_sources_shared_memory_and_DNA',not response['sources'] and 'marcadna' not in text and 'marcacolectiva' not in text)
    current=call('settings/modules');call('settings/modules','PUT',dict(operation_id=str(uuid4()),revision=current['revision'],document=settings_doc['document']))
    check('restored_module_switches_restore_effective_sources',bool(preview()['sources']))
    save(WORK/'extras-result.json',{'status':'passed','checks':checks,'academic_writes':False,'real_provider_calls':0})
    print(json.dumps({'P6_extra_checks':len(checks),'status':'passed'}))


if __name__=='__main__':main()
