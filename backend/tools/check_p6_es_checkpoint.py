"""Offline P6 checkpoint validation; no SQL connections or migration execution."""
import argparse
import copy
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
CRITERIA={'P6.1','P6.2','P6.3','P6.4','P6.close'}
REPORT_MIN={'api':45,'runtime':14,'replay-switch':5,'extras':13,'storage':12,'recovery':5}


def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def require(value):
    if not value:raise ValueError('P6ES_checkpoint_mismatch')


def validate(proof):
    require(proof['unit']=='P6-ES' and proof['status']=='accepted_local_canonical_scope' and proof['P6_accepted'] is True)
    require(proof['primary_port']==4178 and proof['engine']==15 and proof['compatibility']==150)
    require(proof['real_provider_calls']==0 and proof['academic_DDL_or_DML'] is False)
    require(proof['release_sha256']=='cf32dcab88a1e0467c5ae58fa2863e16df13ce906d246a3df43ceb8eb311f5ff')
    require(proof['database'].startswith('CBN_P6ES_TRIAL_20261027_') and proof['phase_percentages']['P6']=='100.00%' and proof['phase_percentages']['P4']=='82.29%')
    require(proof['fixed_milestones']==279 and proof['fixed_criteria']==56 and proof['done_milestones']==189 and proof['accepted_criteria']==31)
    required={'backend/app/institutional/'+n+'.py' for n in ['knowledge','knowledge_models','knowledge_api','knowledge_policy','agents','spanish','api']}
    required|={'frontend/src/institution/KnowledgeWorkspace.tsx','compose.knowledge.yaml','docker/Dockerfile.knowledge','backend/tools/check_p6_es_checkpoint.py','docs/adaptation/phase-work-progress.json','tasks/p6-es-progress.json'}
    require(required<=set(proof['source_pins']))
    for name,expected in proof['source_pins'].items():require(sha(ROOT/name)==expected)
    baseline=read(ROOT/'docs/adaptation/sql/p6_es_input_baseline.json')
    require(sha(ROOT/'.local/p6-es/public-preimages.zip')==baseline['source_archive_sha256'])
    require(sha(ROOT/'docs/adaptation/sql/p5_es_validation.json')==baseline['parent_P5_proof_sha256'])
    with zipfile.ZipFile(ROOT/'.local/p6-es/public-preimages.zip') as archive:
        for n,transition in proof['changed_predecessors'].items():
            entry=next(v for v in baseline['files'] if v['path']==n)
            require(hashlib.sha256(archive.read(entry['archive_name'])).hexdigest()==transition['before']==entry['sha256'])
            require(sha(ROOT/n)==transition['after'])
    for n,h in proof['frozen_releases'].items():require(sha(ROOT/n)==h)
    review=read(ROOT/'artifacts/p6-es/acceptance-review.json')
    require(review['P6_accepted'] and set(review['accepted_criteria'])==CRITERIA and review['dependencies_accepted']==['P3','P5'])
    for name,h in review['evidence'].items():require(sha(ROOT/name)==h)
    for name,minimum in REPORT_MIN.items():
        report=read(ROOT/('artifacts/p6-es/'+name+'-result.json'));require(report['status']=='passed' and len(report['checks'])>=minimum)
    for name in ['compile','demo','preservation','restart','deployment','media','parent-replay']:
        require(read(ROOT/('artifacts/p6-es/'+name+'-result.json'))['status']=='passed')
    for name in ['result','final-result']:require(read(ROOT/('artifacts/p6-es/browser/'+name+'.json'))['status']=='passed')
    checks=read(ROOT/'artifacts/p6-es/final-checks.json');require(checks['status']=='passed' and checks['checks']['backend']['passed']>=288 and checks['checks']['frontend']['passed']>=316)
    require(len(read(ROOT/'artifacts/p6-es/browser/result.json')['checks'])>=15)
    deployment=read(ROOT/'artifacts/p6-es/deployment-result.json')
    require(deployment['image_digest']==proof['image_digest'] and deployment['old_P5_container_retained_stopped'] and deployment['runtime_Python_application_files_match_workspace']==196)
    require(not read(ROOT/'graphify-out/p6-es/source-manifest.json')['old_graphs_rebuilt'])
    return {'status':'passed','P6':'100.00%','source_pins':len(proof['source_pins']),'memory_transitions':len(proof['memory_transitions']),'SQL_connected':False}


def replay_parent():
    baseline=read(ROOT/'docs/adaptation/sql/p6_es_input_baseline.json');archive=ROOT/'.local/p6-es/public-preimages.zip'
    require(sha(archive)==baseline['source_archive_sha256'])
    base=ROOT/'.local/r6';target=base/'CRM_CBN';target.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        for entry in baseline['files']:
            raw=z.read(entry['archive_name']);require(hashlib.sha256(raw).hexdigest()==entry['sha256'])
            p=(target/entry['path']).resolve();require(p.is_relative_to(base.resolve()))
            if p.exists():require(p.read_bytes()==raw)
            else:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    require(sha(target/'docs/adaptation/sql/p5_es_validation.json')==baseline['parent_P5_proof_sha256'])
    result=subprocess.run([sys.executable,'-X','utf8','-B','tools/check_p5_es_checkpoint.py','--self-test','--replay-parent'],cwd=target/'backend',capture_output=True)
    require(result.returncode==0)
    return {'status':'passed','exact_preimages':len(baseline['files']),'parent_checker_bytes_modified':False,'SQL_connected':False}


def self_test(proof):
    cases=[('engine',16),('compatibility',160),('primary_port',4173),('real_provider_calls',1),('academic_DDL_or_DML',True),('database','HORARIOSSIIE'),('done_milestones',279),('accepted_criteria',56)]
    for key,value in cases:
        bad=copy.deepcopy(proof);bad[key]=value
        try:validate(bad)
        except (ValueError,AssertionError):pass
        else:raise AssertionError('invalid_P6_checkpoint_accepted')
    return len(cases)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--self-test',action='store_true');parser.add_argument('--replay-parent',action='store_true');args=parser.parse_args()
    proof=read(ROOT/'docs/adaptation/sql/p6_es_validation.json');result=validate(proof)
    from phase_work_progress import check
    from p6_es_graphs import check as check_graph
    result['work_progress']=check(negatives=args.self_test);result['graph']=check_graph()
    if args.self_test:result['negative_cases_rejected']=self_test(proof)
    if args.replay_parent:result['parent']=replay_parent()
    print(json.dumps(result,ensure_ascii=False))
