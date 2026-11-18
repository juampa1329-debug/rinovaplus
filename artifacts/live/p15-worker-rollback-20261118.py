from contextlib import nullcontext
from uuid import uuid4
from app.institutional import email_notifications as m
from app.institutional.postgres_rehearsal import apply_environment
from app.institutional.store import transaction
from app.institutional.db import institution
s=apply_environment(); marker='p15-worker-'+uuid4().hex
try:
 with transaction(s,True,anonymous=True) as c:
  assert m.native(c,"SELECT count(*) AS n FROM rinova_notify.outbox WHERE state IN('queued','retry','sending')")[0]['n']==0
  owner=next(u for u in m.users(c,s) if u['RoleKey']=='owner' and u['Active'])
  m.transaction=lambda *args,**kwargs:nullcontext(c)
  calls=[]
  outcomes=iter([('retry','smtp_recipient_450'),('accepted',None),('uncertain','smtp_result_unknown')])
  def sender(message,recipient):
   calls.append(1)
   return next(outcomes)
  worker=m.Worker(s,send=sender)
  def enqueue(tag,**kwargs):
   return m.enqueue(c,s,'mail.test',marker+tag,owner['Login'],{},user_id=owner['UserId'],**kwargs)
  def row(identity): return m.native(c,'SELECT state,attempts,next_at>now() AS delayed FROM rinova_notify.outbox WHERE id=%s',identity)[0]
  identity=enqueue('-retry')
  assert worker.once() and row(identity)['state']=='retry' and row(identity)['attempts']==1 and row(identity)['delayed']
  assert not worker.once() and len(calls)==1
  c.native('UPDATE rinova_notify.outbox SET next_at=now() WHERE id=%s',identity)
  assert worker.once() and row(identity)['state']=='accepted' and row(identity)['attempts']==2
  assert not worker.once() and len(calls)==2
  uncertain=enqueue('-uncertain')
  assert worker.once() and row(uncertain)['state']=='uncertain'
  assert not worker.once() and len(calls)==3
  interrupted=enqueue('-interrupted')
  c.native("UPDATE rinova_notify.outbox SET state='sending',lease_until=now()-interval '1 second',attempts=1 WHERE id=%s",interrupted)
  assert not worker.once() and row(interrupted)['state']=='uncertain' and len(calls)==3
  expired=enqueue('-expired',expires=-1)
  assert not worker.once() and row(expired)['state']=='failed'
  paused=enqueue('-paused')
  c.native("UPDATE rinova_notify.document SET body=jsonb_set(body,'{enabled}','false'::jsonb) WHERE kind='transport' AND id='main'")
  assert not worker.once() and row(paused)['state']=='queued' and row(paused)['attempts']==0
  c.native("UPDATE rinova_notify.document SET body=jsonb_set(jsonb_set(body,'{enabled}','true'::jsonb),'{daily_limit}','1'::jsonb) WHERE kind='transport' AND id='main'")
  assert not worker.once() and row(paused)['attempts']==0
  print('P15_NATIVE_WORKER retry/backoff/accepted/no-duplicate/uncertain/expired-lease/expiry/pause/quota PASSED; STUB_CALLS',len(calls),'EXTERNAL_SMTP',0)
  raise RuntimeError(marker)
except RuntimeError as error:
 if str(error)!=marker: raise
with transaction(s,anonymous=True) as c:
 assert m.native(c,'SELECT count(*) AS n FROM rinova_notify.outbox WHERE dedup LIKE %s',marker+'%')[0]['n']==0
 print('P15_WORKER_ROLLBACK_CONFIRMED')
