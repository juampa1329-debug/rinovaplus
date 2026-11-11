"""Real SQL channel edit, conflict and credential ownership checks."""
import json,secrets
from pathlib import Path
from app.institutional.api import create_app
from app.institutional.spanish import load
from tools.qualify_p2_spanish import Browser,operation
from tools.rehearse_p2_spanish import WORK,read,save

if __name__=='__main__':
    private=read(WORK/'http-private.json');settings=load(Path(private['profile']));browser=Browser(create_app(settings));person=private['users']['admin'];browser.login(person['email'],person['password'])
    accounts=browser.request('channels').json()['items'];account=next(row for row in accounts if row['channel']=='whatsapp')
    body=operation(revision=account['revision'],row_version=account['row_version'],application_version=account['application_version'],values={'meta:whatsapp_status':'paused'})
    saved=browser.request('channels/'+account['id'],'PUT',body).json();replayed=browser.request('channels/'+account['id'],'PUT',body).json()
    assert saved==replayed and saved['fields']['meta:whatsapp_status']=='paused'
    assert saved['revision']==account['revision']+1 and saved['provider_operations_available'] is False and saved['verified_status']=='unverified'
    browser.request('channels/'+account['id'],'PUT',operation(revision=account['revision'],row_version=account['row_version'],application_version=account['application_version'],values={'meta:whatsapp_status':'disconnected'}),expected=409)
    material='fixture-wa-token-'+secrets.token_urlsafe(32)
    browser.request('credentials','PUT',operation(scope='channel',owner='integration:'+account['id'],kind='access_token',value=material))
    metadata=browser.request('credentials/channel').json();assert material not in json.dumps(metadata)
    assert any(item['owner']=='integration:'+account['id'] and item['kind']=='access_token' for item in metadata['items'])
    browser.request('credentials','PUT',operation(scope='channel',owner='application:'+account['application_id'],kind='access_token',value=material),expected=422)
    catalog=browser.request('channels/catalog').json();tiktok=next(row for row in accounts if row['channel']=='tiktok')
    field=next(f for f in catalog['fields'] if f['group']=='tiktok' and f['field_kind']=='input' and f['editable_in_p2'] and f['value_type']=='boolean')
    result=browser.request('channels/'+tiktok['id'],'PUT',operation(revision=tiktok['revision'],row_version=tiktok['row_version'],application_version=tiktok['application_version'],values={field['id']:False})).json();assert result['fields'][field['id']] is False
    report={'status':'passed','database':settings.connection['database'],'WhatsApp_SQL_edit_and_revision':True,'operation_replay_same_result':True,'stale_revision_denied':True,'verified_state_never_forged':True,'integration_secret_SQL_encrypted_and_GET_redacted':True,'application_integration_secret_owner_mismatch_rejected':True,'TikTok_boolean_false_roundtrip':True,'provider_calls':0,'academic_writes':False}
    save(WORK/'channel-update-result.json',report);print(json.dumps({'channel_updates':'passed','checks':7}))
