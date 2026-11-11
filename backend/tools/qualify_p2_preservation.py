"""Read-only recheck of the exact pre-P2 source database list."""
import contextlib
import json
from uuid import uuid4
from tools.rehearse_p2_spanish import WORK, read, save, source_2019
from tools.qualify_spanish_schema import source_snapshots
from tools.foundation_snapshot import sha


def main():
    before=read(WORK/'sources-before.json')
    assert len(before['Windows_SQL2022'])==6 and len(before['previous_SQL2019'])==56
    after={'Windows_SQL2022':source_snapshots(),'previous_SQL2019':source_2019(sorted(before['previous_SQL2019']))}
    save(WORK/'sources-after.json',after)
    differences=[group+'/'+name for group in before for name in before[group] if before[group][name]!=after[group].get(name)]
    if differences:
        save(WORK/'source-preservation-result.json',{'status':'failed','differences':differences})
        raise AssertionError('prior_source_catalog_or_data_changed')
    report={'status':'passed','before_sha256':sha(before),'after_sha256':sha(after),'exact_list_preserved':True,'Windows_source_count':6,'previous_SQL2019_count':56,'new_P2ES_copies_not_added_to_old_denominator':True,'Windows_sources':{k:{'before':sha(v),'after':sha(after['Windows_SQL2022'][k])} for k,v in before['Windows_SQL2022'].items()},'previous_SQL2019':{k:{'before':sha(v),'after':sha(after['previous_SQL2019'][k])} for k,v in before['previous_SQL2019'].items()},'source_DDL_or_DML':False,'TLS_verified':True}
    save(WORK/'source-preservation-result.json',report)
    print(json.dumps({'source_preservation':'passed','Windows_sources':6,'prior_SQL2019_copies':56}))


if __name__=='__main__':
    try:
        main()
    except BaseException as error:
        with contextlib.suppress(Exception):
            save(WORK/('preservation-failure-'+uuid4().hex+'.json'),{'type':type(error).__name__,'message':str(error)})
        print(json.dumps({'source_preservation':'failed','type':type(error).__name__}))
        raise SystemExit(1)
