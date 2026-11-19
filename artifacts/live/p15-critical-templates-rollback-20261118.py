from uuid import uuid4
from app.institutional import email_notifications as m
from app.institutional.postgres_rehearsal import apply_environment
from app.institutional.store import transaction
s=apply_environment(); marker='p15-critical-'+uuid4().hex
try:
 with transaction(s,True,anonymous=True) as c:
  cfg=m.transport(c,s)
  assert cfg['invitation_template']=='institucional' and cfg['recovery_template']=='institucional'
  for event in ['user.invited','password.reset']:
   source=m.transactional_source(c,s,event,cfg)
   assert source and source['published'] and 'font-family:Arial' in source['html']
   identity=m.enqueue(c,s,event,marker+event,'cbnaudiovisuales@gmail.com',{'enlace':'https://app.rinovaplus.com/access/redeem#token=synthetic-p15-only'},user_id='9f304694-b04d-408a-9376-3457b2aa8af4')
   item=m.native(c,'SELECT * FROM rinova_notify.outbox WHERE id=%s',identity)[0]
   message=m.build_message(c,s,item)
   assert 'synthetic-p15-only' in message.get_body(preferencelist=('html',)).get_content()
   assert 'synthetic-p15-only' in message.get_body(preferencelist=('plain',)).get_content()
  print('P15_CRITICAL_TEMPLATES_PUBLISHED_AND_LINKS_VALID',2,'SMTP',0)
  raise RuntimeError(marker)
except RuntimeError as error:
 if str(error)!=marker:raise
with transaction(s,anonymous=True) as c:
 assert m.native(c,'SELECT count(*) AS n FROM rinova_notify.outbox WHERE dedup LIKE %s',marker+'%')[0]['n']==0
 print('P15_CRITICAL_TEMPLATES_ROLLBACK_CONFIRMED')
