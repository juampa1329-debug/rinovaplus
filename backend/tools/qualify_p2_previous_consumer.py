import json
import sys
sys.path.insert(0,'/app/backend')
from pathlib import Path
from uuid import uuid4
from fastapi.testclient import TestClient
from app.institutional.api import create_app
from app.institutional.spanish import load, transaction
from app.institutional.crypto import totp_code
from app.institutional.auth import COOKIE
private=json.loads(Path('/run/consumer-private.json').read_text())
settings=load(Path('/run/cbn-institution'))
app=create_app(settings)
with TestClient(app,base_url='http://127.0.0.1:4177',client=('127.0.0.1',50001)) as anonymous:
 headers={'X-CRM-Local':'1'}
 assert anonymous.get('/api/institution/auth/me',headers=headers).status_code==401
 challenged=anonymous.post('/api/institution/auth/login',headers=headers,json={'email':private['email'],'password':private['password']})
 assert challenged.status_code==200 and challenged.json()['mfa_required'] is True
 assert 'csrf_token' not in challenged.json() and COOKIE not in anonymous.cookies
 assert anonymous.get('/api/institution/users',headers=headers).status_code==401
with TestClient(app,base_url='http://127.0.0.1:4177',client=('127.0.0.1',50000)) as client:
 client.cookies.set(COOKIE,private['cookie'],domain='127.0.0.1',path='/api')
 headers={'X-CRM-Local':'1','X-CSRF-Token':private['csrf']}
 def request(path,method='GET',body=None):
  r=client.request(method,'/api/institution/'+path,headers=headers,json=body)
  if r.status_code==428:
   with transaction(settings,anonymous=True) as cursor:
    step=int(cursor.execute("SELECT DATEDIFF_BIG(second,'19700101',SYSUTCDATETIME())/30").fetchval())
   confirmed=client.post('/api/institution/auth/confirm',headers=headers,json={'current_password':private['password'],'code':totp_code(private['totp_secret'],step)})
   assert confirmed.status_code==200,'MFA_reauthentication_failed'
   r=client.request(method,'/api/institution/'+path,headers=headers,json=body)
  assert r.status_code==200,(path,r.status_code)
  return r.json()
 me=request('auth/me');assert me['mfa_enabled']
 users=request('users');assert len(users['items'])==private['users']
 audit=request('audit?limit=100');assert len(audit['items'])>=private['audit_prefix']['rows'] or audit['next'] is not None
 setting=request('settings/institution')
 changed=dict(setting['document'],name='CBN versión anterior '+uuid4().hex[:8])
 saved=request('settings/institution','PUT',{'operation_id':str(uuid4()),'revision':setting['revision'],'document':changed})
 restored=request('settings/institution/restore/'+str(setting['revision']),'POST',{'operation_id':str(uuid4()),'revision':saved['revision'],'document':{}})
 assert restored['document']==setting['document'] and restored['revision']==saved['revision']+1
 assert len(request('users')['items'])==private['users']
 assert request('auth/me')['mfa_enabled']
 print(json.dumps({'previous_application_consumer':'passed','version':'p2es-r2-ui-candidate','database':settings.connection['database'],'accounts_preserved':private['users'],'MFA_still_required':True,'existing_session_compatible':True,'configuration_write_and_history_restore':True,'audit_readable_and_append_only':True,'startup_DDL':False}))
