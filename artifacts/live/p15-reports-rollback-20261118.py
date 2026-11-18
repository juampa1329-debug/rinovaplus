import json
from datetime import datetime,timedelta,timezone
from uuid import uuid4
from app.institutional.postgres_rehearsal import apply_environment
from app.institutional.store import transaction
from app.institutional.db import institution
from app.institutional.email_notifications import native,users,observe_service,due_reports,build_message
s=apply_environment()
marker='p15-'+uuid4().hex
try:
 with transaction(s,True,anonymous=True) as c:
  execute=c.execute
  def checked_execute(sql,*args):
   if 'FROM crm_access.Audit' in sql: sql=sql.replace('CreatedAt','OccurredAt')
   return execute(sql,*args)
  c.execute=checked_execute
  owner=next(u for u in users(c,s) if u['RoleKey']=='owner' and u['Active'])
  def put(kind,identity,body):
   c.native('INSERT INTO rinova_notify.document(institution,kind,id,revision,body,actor) VALUES(%s,%s,%s,1,%s::jsonb,%s)',institution(s),kind,identity,json.dumps(body),owner['UserId'])
  source=marker+'-source'
  put('template',source,{'name':'Rollback only','subject':'P15 {{evento}}','html':'<p>{{detalle}}</p><p>{{periodo}}</p>','signature':'<p>CBN</p>','published':True})
  baseline=native(c,'SELECT count(*) AS n FROM rinova_notify.outbox')[0]['n']
  for event in ['operations.failure','operations.recovered']:
   put('rule',marker+event,{'name':'Rollback only','enabled':True,'event':event,'template':source,'users':[str(owner['UserId'])],'roles':[],'groups':[]})
  observe_service(c,s,marker,failed=True)
  observe_service(c,s,marker,failed=True)
  observe_service(c,s,marker,failed=False)
  transitions=native(c,'SELECT count(*) AS n FROM rinova_notify.outbox')[0]['n']-baseline
  assert transitions==2,transitions
  schedule=marker+'-report'
  put('schedule',schedule,{'name':'Rollback only','enabled':True,'frequency':'daily','time':'08:00','zone':'America/Bogota','weekday':0,'template':source,'users':[str(owner['UserId'])],'roles':[],'groups':[]})
  due=datetime.now(timezone.utc)-timedelta(seconds=1)
  c.native('INSERT INTO rinova_notify.cursor(institution,key,value) VALUES(%s,%s,%s::jsonb)',institution(s),'schedule:'+schedule+':1',json.dumps({'next':due.isoformat()}))
  due_reports(c,s)
  due_reports(c,s)
  total=native(c,'SELECT count(*) AS n FROM rinova_notify.outbox')[0]['n']-baseline
  assert total==3,total
  print('P15_NATIVE_TRANSITIONS',transitions,'REPORT_ONCE',total-transitions,'SMTP_CALLS',0)
  raise RuntimeError(marker)
except RuntimeError as error:
 if str(error)!=marker: raise
with transaction(s,anonymous=True) as c:
 assert native(c,'SELECT count(*) AS n FROM rinova_notify.document WHERE id LIKE %s',marker+'%')[0]['n']==0
 print('P15_NATIVE_ROLLBACK_CONFIRMED')
