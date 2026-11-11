"""Offline P2 checkpoint, fixed metrics and frozen P1 replay; no SQL imports."""
import argparse
import copy
import hashlib
import json
import subprocess
import sys
import uuid
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PROOF=ROOT/'docs/adaptation/sql/p2_es_validation.json'
RELEASE='1a7ba0dc7435e1e5dd61b431cca7f2164d698d4b4b6df9dd53cd66e8b40b10b4'
PARENT='5457c8da43a9c303c5b7032cff625a3d7ae112c876187c61fdb31e7a8948e2d3'
ALLOWED={
 'AGENTS.md','README.md','docs/roadmap.md','docs/ADAPTATION_STATUS.md','docs/SCENTRA_ADAPTATION_ROADMAP.md','docs/adaptation/GRAPH_GUIDE.md','docs/adaptation/WORK_PROGRESS.md','docs/adaptation/RESUME.md','docs/adaptation/sql/P2_ES_PLAN.md','ai-memory/CURRENT_STATE.md','ai-memory/FILE_MAP.md','ai-memory/CRITICAL_WARNINGS.md','tasks/TASK_STATE.md',
 'docs/adaptation/phase-progress-contract.json','docs/adaptation/phase-work-progress.json','backend/tools/check_phase_progress.py','backend/tools/phase_work_progress.py','backend/tests/test_institutional_http.py',
 *['backend/app/institutional/'+name+'.py' for name in ['api','auth','channels','db','management','models','settings','store']],
 *['frontend/src/'+name for name in ['shared/runtimeCapabilities.tsx','modules/clients/api/clientsApi.ts','modules/clients/pages/Clients.tsx','modules/crm-configuration/api/crmConfigurationApi.ts','modules/crm-configuration/hooks/useCrmConfiguration.ts','modules/crm-configuration/pages/CrmConfiguration.tsx','modules/inbox/api/inboxApi.ts','modules/inbox/components/InboxContactEditor.tsx','modules/inbox/pages/Inbox.tsx']]
}


def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def require(value):
    if not value:raise ValueError('P2_ES_checkpoint_mismatch')


def validate(proof):
    require(proof['unit']=='P2-ES' and proof['P2_accepted'] is True and proof['institutional_production_accepted'] is False)
    package=ROOT/'backend/migrations/cbn_institutional_spanish_v1';require(digest(package/'release.json')==proof['release_sha256']==RELEASE)
    release=read(package/'release.json');require(len(release['inputs'])==14 and len(release['units'])==2 and release['parent_release']==PARENT)
    for name,expected in release['inputs'].items():require(digest(ROOT/name)==expected)
    require(digest(ROOT/'backend/migrations/cbn_spanish_schema_v2/release.json')==PARENT)
    baseline=read(ROOT/'docs/adaptation/sql/p2_es_input_baseline.json');require(len(baseline['files'])==872)
    archive=ROOT/'artifacts/p2-es/history/p1-public-preimages.zip';require(digest(archive)==baseline['source_archive_sha256']==proof['preimages_sha256'])
    changed={}
    with zipfile.ZipFile(archive) as saved:
        require(set(saved.namelist())=={e['archive_name'] for e in baseline['files']})
        for entry in baseline['files']:
            require(hashlib.sha256(saved.read(entry['archive_name'])).hexdigest()==entry['sha256'])
            current=digest((ROOT/entry['path']).resolve())
            if current!=entry['sha256']:
                require(entry['path'] in ALLOWED)
                changed[entry['path']]={'before':entry['sha256'],'after':current,'archive_name':entry['archive_name']}
    require(changed==proof['changed_predecessors'])
    for name,expected in proof['source_pins'].items():
        path=(ROOT/name).resolve();require(path.is_relative_to(ROOT) and path.is_file() and digest(path)==expected)
    review=read(ROOT/'artifacts/p2-es/acceptance-review.json');require(review['P2_accepted'] is True and not review['institutional_production_accepted'] and len(review['criteria'])==5 and all(c['accepted'] for c in review['criteria']))
    for entry in review['evidence'].values():require(digest(ROOT/entry['file'])==entry['sha256'])
    require(review['tables']==138 and review['new_tables']==39 and review['physical_foreign_keys']==221 and review['actions']==30 and review['method_path_rows']==55)
    source=read(ROOT/'artifacts/p2-es/source-preservation-result.json');require(source['status']=='passed' and source['before_sha256']==source['after_sha256'] and source['Windows_source_count']==6 and source['previous_SQL2019_count']==56)
    restart=read(ROOT/'artifacts/p2-es/restart-result.json');require(restart['status']=='passed' and restart['before']==restart['after'] and restart['opaque_session_survives_application_restart'])
    final=read(ROOT/'artifacts/p2-es/browser/final-result.json');require(final['status']=='passed' and final['image_digest']==restart['image_digest']==proof['image_digest'] and final['fixtures']==0)
    recovery=read(ROOT/'artifacts/p2-es/recovery-result.json');require(recovery['status']=='passed' and recovery['populated_accounts']==9 and recovery['all_ciphertexts_authenticated'] and recovery['SQL_clock_floor_with_process_skew'] and recovery['post_backup_consumed_recovery_rejected'])
    consumer=read(ROOT/'artifacts/p2-es/previous-consumer-result.json');require(consumer['previous_application_consumer']=='passed' and consumer['accounts_preserved']==9 and consumer['anonymous_and_password_only_access_rejected_before_MFA'])
    faults=read(ROOT/'artifacts/p2-es/migration-fault-result.json');require(faults['status']=='passed' and len(faults['scenarios'])==10 and sorted(faults['concurrency'])==['committed','noop'] and faults['data_drift_negatives']==5)
    from phase_work_progress import check as work_check
    work=work_check();require(work['accepted_criteria']==15 and work['milestone_count']==279 and work['done_milestones']==129 and work['pending_milestones']==150)
    require(work['phases'][2]['work_percent_display']=='100.00%' and work['phases'][4]['work_percent_display']=='38.29%' and work['phases'][4]['phase_accepted'] is False)
    from p2_es_graphs import check as graph_check
    graph=graph_check()
    return {'baseline_files_checked':872,'changed_predecessors':len(changed),'pinned_sources':len(proof['source_pins']),'P2':'100.00%','P4':'38.29% configuration work','graph':graph,'SQL_connections':0}


def replay_p1():
    baseline=read(ROOT/'docs/adaptation/sql/p2_es_input_baseline.json');receipt=read(ROOT/'artifacts/p2-es/p1-replay-result.json');require(receipt['status']=='passed' and receipt['preimages']==872)
    base=(ROOT/'.local/p2-es'/('checkpoint-replay-'+uuid.uuid4().hex)).resolve();base.mkdir(parents=True);target=base/'CRM_CBN';target.mkdir()
    with zipfile.ZipFile(ROOT/receipt['archive']) as archive:
        for entry in baseline['files']:
            path=(target/entry['path']).resolve();require(path.is_relative_to(base));path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(archive.read(entry['archive_name']))
    old_registry=read(target/'docs/adaptation/phase-work-progress.json')['evidence_registry']
    supplement=ROOT/receipt['supplement_archive'];require(digest(supplement)==receipt['supplement_sha256'])
    with zipfile.ZipFile(supplement) as archive:
        require(set(archive.namelist())=={entry['archive_name'] for entry in receipt['frozen_registry_supplements']})
        for entry in receipt['frozen_registry_supplements']:
            raw=archive.read(entry['archive_name']);require(hashlib.sha256(raw).hexdigest()==entry['sha256'] and any(e['file']==entry['path'] and e['source_sha256_at_review']==entry['sha256'] for e in old_registry.values()))
            path=(target/entry['path']).resolve();require(path.is_relative_to(base));path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    result=subprocess.run([sys.executable,'-B',str(target/'backend/tools/check_p1_es_checkpoint.py'),'--self-test'],cwd=target,capture_output=True,encoding='utf-8',errors='replace')
    require(result.returncode==0)
    remaining=result.stdout.strip();documents=[];decoder=json.JSONDecoder()
    while remaining:
        value,end=decoder.raw_decode(remaining);documents.append(value);remaining=remaining[end:].lstrip()
    require(documents[-1]==receipt['replayed_result'])
    return {'frozen_P1_checker_replayed':True,'preimages':872,'independently_pinned_registry_supplements':len(receipt['frozen_registry_supplements']),'current_files_overwritten':False}


def negatives(proof):
    mutations=[lambda p:p.__setitem__('P2_accepted',False),lambda p:p.__setitem__('institutional_production_accepted',True),lambda p:p.__setitem__('release_sha256','0'*64),lambda p:p.__setitem__('preimages_sha256','0'*64),lambda p:p.__setitem__('image_digest','sha256:'+'0'*64),lambda p:p['source_pins'].pop('backend/tools/check_p2_es_checkpoint.py')]
    # Mandatory pins cannot be omitted even if remaining files match.
    count=0
    for mutate in mutations:
        wrong=copy.deepcopy(proof);mutate(wrong)
        try:
            require({'backend/tools/check_p2_es_checkpoint.py','docs/adaptation/phase-work-progress.json','graphify-out/p2-es/source-manifest.json'}<=set(wrong['source_pins']));validate(wrong)
        except (ValueError,AssertionError):count+=1
        else:raise AssertionError('invalid_P2_checkpoint_accepted')
    return count


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--self-test',action='store_true');parser.add_argument('--skip-replay',action='store_true');args=parser.parse_args();proof=read(PROOF)
    require({'backend/tools/check_p2_es_checkpoint.py','docs/adaptation/phase-work-progress.json','graphify-out/p2-es/source-manifest.json'}<=set(proof['source_pins']))
    result=validate(proof)
    if not args.skip_replay:result.update(replay_p1())
    if args.self_test:
        from phase_work_progress import check
        from check_phase_progress import self_test
        result['checkpoint_negatives_rejected']=negatives(proof);result['work_negatives_rejected']=check(negatives=True)['negative_cases_rejected'];result['canonical_negatives_rejected']=self_test(read(ROOT/'docs/adaptation/phase-progress-contract.json'))
    print(json.dumps(result,ensure_ascii=False,indent=2))
