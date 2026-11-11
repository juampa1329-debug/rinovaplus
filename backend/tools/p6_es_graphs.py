"""Bounded incremental Graphify P6 evidence; no preceding graph is rebuilt."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'graphify-out/p6-es'
CODE=sorted({p.relative_to(ROOT).as_posix() for pattern in [
    'backend/app/institutional/knowledge*.py','backend/tools/*p6*.py',
    'backend/tests/test_institutional_knowledge.py',
    'frontend/src/test/institutionKnowledgeP6.test.tsx',
] for p in ROOT.glob(pattern)}|{
    'backend/app/institutional/'+n+'.py' for n in ['agents','agents_api','api','auth','settings','spanish','store','channel_workspace','ui_contract']
}|{'backend/app/modules/agents/'+n+'.py' for n in ['service','runtime']}|{
    'frontend/src/institution/'+n+'.tsx' for n in ['KnowledgeWorkspace','InstitutionApp','Workspace','api']
}|{'frontend/src/modules/agents/AgentsPanel.tsx','frontend/src/modules/agents/api.ts'})
DOCS=['docs/adaptation/sql/SQL_P6_ES_REVIEW.md','docs/adaptation/phase-work-progress.json',
    'artifacts/p6-es/final-review.json','artifacts/p6-es/reference-final-review.json',
    'artifacts/p6-es/acceptance-review.json','artifacts/p6-es/final-checks.json',
    'artifacts/p6-es/browser/result.json','artifacts/p6-es/browser/final-result.json',
    *('artifacts/p6-es/'+n+'-result.json' for n in ['api','runtime','replay-switch','storage','recovery','extras','compile','demo','preservation','restart','deployment','media','parent-replay'])]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')


def build():
    from graphify.detect import detect
    from graphify.extract import extract
    from graphify.cache import save_semantic_cache
    from adaptation_graphs import render
    corpus=ROOT/'.local/p6-es'/('final-corpus-'+uuid4().hex[:8]);corpus.mkdir()
    (corpus/'.graphifyignore').write_text('!**/*.md\n!**/*.json\n')
    for i,n in enumerate(CODE+DOCS):shutil.copyfile(ROOT/n,corpus/(str(i)+'_'+Path(n).name))
    detection=detect(corpus);assert 0<detection['total_files']<100 and detection['total_words']<250000
    ast=extract([ROOT/n for n in CODE],root=ROOT,cache_root=ROOT/'.local/p6-es/final-cache',max_workers=3)
    fragments=[read(ROOT/'docs/adaptation/fragments'/n) for n in ['p6-final.draft.json','p6-reference-final.draft.json']]
    nodes={v['id']:v for v in ast['nodes']};edges=list(ast['edges']);hyper=[]
    for f in fragments:
        nodes.update({v['id']:v for v in f['nodes']});edges.extend(f['edges']);hyper.extend(f.get('hyperedges',[]))
        save_semantic_cache(f['nodes'],f['edges'],f.get('hyperedges',[]),root=ROOT,allowed_source_files=[ROOT/v['source_file'] for v in f['nodes']],cache_root=ROOT/'.local/p6-es/final-cache')
    for phase in read(ROOT/'docs/adaptation/phase-work-progress.json')['summary']['phases']:
        key='p6_progress_'+phase['id'];nodes[key]={'id':key,'label':phase['id']+' '+phase['work_percent_display'],'file_type':'document','source_file':'docs/adaptation/phase-work-progress.json','source_location':'$.summary.phases','accepted':phase['phase_accepted'],'domain':'fixed_weight_roadmap'}
    for edge in edges:
        for key in [edge['source'],edge['target']]:
            if key not in nodes:nodes[key]={'id':key,'label':key,'file_type':'document','source_file':edge['source_file'],'source_location':edge.get('source_location'),'domain':'explicit_context'}
    counts=render({**ast,'nodes':list(nodes.values()),'edges':edges,'hyperedges':hyper,'input_tokens':0,'output_tokens':0},OUT,detection,coverage_note='P6 canonical local acceptance on SQL2019: governed PDF/TXT sources, lexical citations, reviewed collective memory and institutional DNA, conversation-bound private facts, correction/archive/approved rollback and derived-only rebuild. Three synthetic relevance questions do not measure institutional production accuracy. No URL/OCR/vector service, automatic B011 producer, real provider calls or full academic mappings. Empty ready-blob volume only. P4 external acceptance remains pending. Initial/final semantic reviews are static; executed acceptance reports are distinct. Previous graphs frozen; token usage not measured.')
    save(OUT/'detection.json',detection)
    save(OUT/'source-manifest.json',{'unit':'P6-ES',**counts,'sources':{n:sha(ROOT/n) for n in CODE+DOCS},'artifacts':{n:sha(OUT/n) for n in ['graph.json','graph.html','GRAPH_REPORT.md','detection.json']},'old_graphs_rebuilt':False,'token_usage_measured':False})
    print(json.dumps({'files':detection['total_files'],**counts}))


def check():
    value=read(OUT/'source-manifest.json')
    for n,h in value['sources'].items():assert sha(ROOT/n)==h,n
    for n,h in value['artifacts'].items():assert sha(OUT/n)==h,n
    assert value['old_graphs_rebuilt'] is False
    return {'status':'passed','sources':len(value['sources'])}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['build','check']);args=parser.parse_args()
    build() if args.action=='build' else print(json.dumps(check()))
