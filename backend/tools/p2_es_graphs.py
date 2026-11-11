"""Bounded Graphify checkpoint: current P2 sources, contracts and evidence."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'graphify-out/p2-es'
CODE=[f'backend/app/institutional/{name}.py' for name in ['api','auth','channels','crypto','db','management','models','model_settings','policy','settings','spanish','spanish_bindings','store','ui_contract','webhooks']]+[f'backend/tools/{name}.py' for name in ['p2_es_migrations','p2_es_recovery','p2_profile_restore','p2_permissions','p2_restart_snapshot','p2_es_graphs','check_p2_es_checkpoint','phase_work_progress']]+[f'frontend/src/institution/{name}.tsx' for name in ['InstitutionApp','Access','Settings','Channels','Fields','api']]+['frontend/src/institution/drafts.ts','frontend/src/shared/institutionSession.ts','frontend/src/shared/runtimeCapabilities.tsx']
DOCS=['docs/adaptation/phase-work-progress.json','docs/adaptation/phase-work-definition.json','docs/adaptation/phase-progress-contract.json','docs/adaptation/sql/p2-channel-fields.json','docs/adaptation/sql/p2-endpoint-permissions.json','backend/migrations/cbn_institutional_spanish_v1/release.json','backend/migrations/cbn_institutional_spanish_v1/table_map.json','backend/migrations/cbn_institutional_spanish_v1/expected-stages.json','artifacts/p2-es/acceptance-review.json','artifacts/p2-es/channel-ui-milestone-review.json','artifacts/p2-es/restart-result.json','artifacts/p2-es/source-preservation-result.json','artifacts/p2-es/ui-access-final-source-review.json','artifacts/p2-es/current-source-review.json','docs/adaptation/fragments/p2-es-ui-final.draft.json','docs/adaptation/fragments/p2-es-current.draft.json']


def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def build():
    from graphify.detect import detect
    from graphify.extract import extract
    from adaptation_graphs import render
    corpus=ROOT/'.local/p2-es/graph-corpus';corpus.mkdir(parents=True,exist_ok=True)
    for index,name in enumerate(CODE+DOCS):shutil.copyfile(ROOT/name,corpus/(str(index)+'_'+Path(name).name))
    detection=detect(corpus);assert 0<detection['total_files']<200 and detection['total_words']<2000000
    save(OUT/'detection.json',detection)
    data=extract([ROOT/name for name in CODE],root=ROOT,cache_root=ROOT/'.local/p2-es/graph-cache',max_workers=4)
    nodes={n['id']:n for n in data['nodes']};edges=list(data['edges'])
    def node(identity,label,source,location='$',**attrs):
        nodes.setdefault(identity,{'id':identity,'label':label,'file_type':'document','source_file':source,'source_location':location,**attrs})
    def edge(a,b,relation,source,location='$',**attrs):
        edges.append({'source':a,'target':b,'relation':relation,'confidence':'EXTRACTED','confidence_score':1,'source_file':source,'source_location':location,**attrs})
    for name in DOCS[-2:]:
        fragment=read(ROOT/name)
        for item in fragment['graph']['nodes']:nodes[item['id']]=item
        edges.extend(fragment['graph']['edges'])
    work=read(ROOT/DOCS[0])
    for phase in work['phases']:
        pid='p2es_phase_'+phase['id'];node(pid,phase['id']+' · '+phase['technical_work']['percent_display'],DOCS[0],domain='roadmap',accepted=phase['technical_work']['phase_accepted'])
        for criterion in phase['criteria']:
            cid='p2es_criterion_'+criterion['id'];node(cid,criterion['id']+' · '+criterion['technical_completion']['percent_display'],DOCS[0],domain=phase['id'],accepted=criterion['current_acceptance']['state']=='accepted');edge(pid,cid,'contains_fixed_canonical_criterion',DOCS[0])
            for milestone in criterion['milestones']:
                mid='p2es_milestone_'+milestone['id'];node(mid,milestone['id']+' · '+milestone['description'],DOCS[0],domain=phase['id'],state=milestone['state'],criterion_share=milestone['criterion_share']);edge(cid,mid,'contains_fixed_weight_milestone',DOCS[0])
                for ref in milestone['evidence_refs']:
                    evidence=work['evidence_registry'][ref];eid='p2es_evidence_'+ref;node(eid,ref+' · '+evidence['scope'],evidence['file'],evidence['source_location'],domain='evidence',sha256=evidence['source_sha256_at_review']);edge(mid,eid,'supported_in_declared_scope',DOCS[0])
    model_source='backend/migrations/cbn_institutional_spanish_v1/expected-stages.json';model=read(ROOT/model_source)['P2ES-002'];mapping=read(ROOT/'backend/migrations/cbn_institutional_spanish_v1/table_map.json');academics=set(mapping['academic_tables'])
    for table in model['tables']:
        name=table['schema']+'.'+table['name'];node('p2es_table_'+name,name,model_source,domain='academic_structure_read_denied' if name in academics else 'Spanish_CRM_storage',academic_write_allowed=False)
    for logical,physical in mapping['tables'].items():
        lid='p2es_logical_'+logical;node(lid,logical,'backend/migrations/cbn_institutional_spanish_v1/table_map.json',domain='trusted_SQL_identifier_mapping',database_alias_or_view=False);edge(lid,'p2es_table_'+physical,'maps_trusted_identifier_only','backend/migrations/cbn_institutional_spanish_v1/table_map.json')
    for foreign in model['foreign_keys']:
        table=foreign['schema']+'.'+foreign['table'];target=foreign['referenced_schema']+'.'+foreign['referenced_table'];fid='p2es_fk_'+table+'.'+foreign['name'];node(fid,foreign['name'],model_source,domain='physical_FK',columns=foreign['columns']);edge('p2es_table_'+table,fid,'defines_physical_FK',model_source);edge(fid,'p2es_table_'+target,'references_physical_table',model_source)
    permissions=read(ROOT/'docs/adaptation/sql/p2-endpoint-permissions.json')
    for action in permissions['known_actions']:node('p2es_action_'+action,action,'docs/adaptation/sql/p2-endpoint-permissions.json',domain='authorization')
    for row in permissions['rows']:
        rid='p2es_route_'+row['method']+'_'+row['path'];node(rid,row['method']+' '+row['path'],'docs/adaptation/sql/p2-endpoint-permissions.json',domain='installed_API',constraints=row['conditions'],recent_authentication=row['recent_authentication']);aid='p2es_action_'+row['action'];node(aid,row['action'],'docs/adaptation/sql/p2-endpoint-permissions.json',domain='authorization');edge(rid,aid,'requires_current_SQL_authority','docs/adaptation/sql/p2-endpoint-permissions.json')
    catalog=read(ROOT/'docs/adaptation/sql/p2-channel-fields.json')
    for field in catalog['fields']:
        fid='p2es_channel_field_'+field['id'];node(fid,field['label']+' · '+field['id'],'docs/adaptation/sql/p2-channel-fields.json',domain='Scentra_field_contract',kind=field['field_kind'],configuration_editable=field['editable_in_p2'],provider_action=field['requires_provider_action']);edge('p2es_milestone_P4.3.m5',fid,'configuration_control_or_explicit_restricted_context','docs/adaptation/sql/p2-channel-fields.json')
    for item in edges:
        for identity in (item['source'],item['target']):
            if identity not in nodes:node(identity,identity,item.get('source_file',DOCS[0]),domain='explicit_external_context')
    counts=render({**data,'nodes':list(nodes.values()),'edges':edges},OUT,detection,coverage_note='P2 accepted only as local SQL2019 institutional administration over an independent Spanish schema/profile. 138 physical tables,221 physical FKs,108 trusted identifier mappings. P4.3.m5 configuration UI completed; provider operations and full P4 remain pending. All279 fixed work milestones over56 canonical criteria preserve partial credit separately from acceptance. Earlier P1/C13/P2-WIP graphs remain unchanged; frozen P1 is replayed independently. Semantic reviews retain their inspected snapshot and execution evidence is sealed separately.')
    artifacts=['graph.json','graph.html','GRAPH_REPORT.md','detection.json']
    save(OUT/'source-manifest.json',{'unit':'P2-ES','scope':'local_SQL2019_administration_and_precise_partial_work','physical_tables':len(model['tables']),'physical_FKs':len(model['foreign_keys']),'logical_bindings':len(mapping['tables']),'channel_contexts':len(catalog['fields']),'fixed_milestones':279,'fixed_criteria':56,**counts,'sources':{name:digest(ROOT/name) for name in CODE+DOCS},'artifacts':{name:digest(OUT/name) for name in artifacts}})
    print(json.dumps({'bounded_files':detection['total_files'],'bounded_words':detection['total_words'],**counts}))


def check():
    value=read(OUT/'source-manifest.json');assert (value['physical_tables'],value['physical_FKs'],value['logical_bindings'],value['channel_contexts'],value['fixed_milestones'],value['fixed_criteria'])==(138,221,108,115,279,56)
    assert set(value['sources'])==set(CODE+DOCS)
    for name,expected in value['sources'].items():assert digest(ROOT/name)==expected,name
    for name,expected in value['artifacts'].items():assert digest(OUT/name)==expected,name
    graph=read(OUT/'graph.json');ids={node['id'] for node in graph['nodes']};links=graph.get('links',graph.get('edges'));assert len(ids)==len(graph['nodes'])==value['nodes'];assert all(e['source'] in ids and e['target'] in ids for e in links)
    assert 'p2es_milestone_P4.3.m5' in ids and 'p2es_criterion_P2.close' in ids
    return {'nodes':len(ids),'edges':len(links),'communities':value['communities'],'old_graphs_rebuilt':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    if args.check:print(json.dumps(check()))
    else:build()
