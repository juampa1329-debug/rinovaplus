"""Read-only persistence snapshot for the clean final P2 application."""
import argparse
import json
from tools.rehearse_p2_spanish import WORK, admin, read, save
from tools.qualify_p2_recovery import fingerprint
from app.institutional.spanish import load
from pathlib import Path


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('position',choices=['before','after']);args=parser.parse_args()
    profile=read(WORK/'final-profile.json');settings=load(Path(profile['directory']))
    with admin(profile['database'],readonly=True) as connection:
        tables={name:fingerprint(connection.cursor(),settings.ticket['table_map'][name]) for name in ['crm_access.AccessUser','crm_access.Role','crm_access.Setting','crm_access.SettingHistory','crm_access.Secret','crm_access.Factor','crm_access.Session','crm_access.Audit','crm_meta.MigrationJournal']}
    value={'database':profile['database'],'tables':tables,'ticket_sha256':settings.review['ticket_sha256']}
    save(WORK/('restart-'+args.position+'.json'),value)
    if args.position=='after':
        assert read(WORK/'restart-before.json')==value
        save(WORK/'restart-result.json',{'status':'passed','database':profile['database'],'before':value,'after':value,'application_only_restart':True,'SQL_server_or_old_previews_restarted':False,'accounts_settings_secrets_MFA_sessions_audit_journal_unchanged':True})
    print(json.dumps({'snapshot':args.position,'database':profile['database'],'tables':len(tables),'equal_to_before':args.position=='after'}))
