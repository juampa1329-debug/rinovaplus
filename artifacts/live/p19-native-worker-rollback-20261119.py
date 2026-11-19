"""Native P19 worker/frontier test. Actual SQL and ffmpeg; both paid providers mocked. Everything rolled back."""
import asyncio,json,subprocess,shutil
from contextlib import nullcontext,contextmanager
from uuid import uuid4
from fastapi import HTTPException
from app.institutional.postgres_rehearsal import apply_environment
from app.institutional.store import transaction
from app.institutional.db import institution,one
from app.institutional.channel_operations import account
from app.institutional.settings import setting
from app.institutional import voice_audio as v,whatsapp_gemini as w,channel_media as media,email_notifications as mail
from app.institutional.voice_policy import VoicePolicy
from app.modules.inbox.infrastructure import media_files as files
@contextmanager
def diagnostic_transaction(*args,**kwargs):
 with transaction(*args,**kwargs) as c:
  try:yield c
  except Exception as e:
   print('P19_NATIVE_DIAGNOSTIC',type(e).__name__,getattr(getattr(e,'diag',None),'constraint_name',None),getattr(getattr(e,'diag',None),'message_primary',None))
   raise
s=apply_environment(); inst=institution(s); made=set(); incoming_ids=[]; reply_ids=[]; calls={'gemini':0,'tts':0}; checks={}; mode='normal'
class Rollback(Exception): pass
original=(w.transaction,v.transaction,v.synthesize,mail.enabled)
try:
 with diagnostic_transaction(s,True,anonymous=True) as c:
  assert c.execute("SELECT COUNT(*) FROM crm_channels2.ProviderOperation WHERE InstitutionId=? AND Action=? AND Status='pending'",inst,w.ACTION).fetchval()==0,'preexisting_pending_work_do_not_touch'
  identity=one(c,"SELECT TOP(1) i.* FROM crm_channels2.ExternalIdentity i JOIN crm_channels2.Integration a ON a.InstitutionId=i.InstitutionId AND a.IntegrationId=i.IntegrationId WHERE i.InstitutionId=? AND a.Channel='whatsapp' AND a.DisplayName=? AND i.ExternalId LIKE '%44' ORDER BY i.CreatedAt",inst,'WhatsApp · CBN')
  assert identity
  item=account(c,s,str(identity['IntegrationId'])); conversation=str(identity['ConversationId'])
  c.execute("UPDATE crm.Conversation SET ControlMode='ai' WHERE ConversationId=?",conversation)
  document=setting(c,s,'ai')['document']; p=VoicePolicy.model_validate(document.get('voice',{})); assert p.profiles
  p.scope='selected_conversations'; p.conversation_ids=[conversation]; p.enabled=True; p.mode='voice_notes_or_long'; p.max_audio_seconds=60; base=v.usage(c,s,conversation)['used']; p.max_audios_per_conversation=base+1
  def write_policy():
   document['voice']=p.model_dump();c.execute("UPDATE crm_access.Setting SET Document=?,Revision=Revision+1 WHERE InstitutionId=? AND Section='ai'",json.dumps(document),inst)
  write_policy()
  sample=str(uuid4()); made.add(sample)
  subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i','sine=frequency=440:duration=1','-codec:a','libmp3lame','-f','mp3',str(files.path(sample,'.part'))],check=True,timeout=15)
  info=files.inspect_file(sample,'fixture.mp3');info['name']='nota-de-voz.ogg'
  w.transaction=v.transaction=lambda *_a,**_k:nullcontext(c)
  mail.enabled=lambda *_:False
  answer='Hola. Puedo orientarte con la información revisada de CBN. ¿Qué programa te interesa conocer?'
  class Gateway:
   def __init__(self,*_): pass
   async def gemini_generation(self,model,body,before_attempt):
    before_attempt(); calls['gemini']+=1
    assert 'conversación oral' in body['systemInstruction']['parts'][0]['text']
    if calls['gemini']==1: assert 'inlineData' in body['contents'][0]['parts'][1]
    return {'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps({'decision':'responder','text':answer})}]}}]}
  async def tts(value,profile,text,media_id,*_):
   calls['tts']+=1;made.add(media_id);assert text==answer
   shutil.copyfile(files.path(sample),files.path(media_id,'.part'))
   checked=files.inspect_file(media_id,'fixture.ogg');checked['name']='nota-de-voz.ogg'
   if mode=='human': c.execute("UPDATE crm.Conversation SET ControlMode='human' WHERE ConversationId=?",conversation)
   return checked,{'synthetic_receipt':True}
  v.synthesize=tts
  def incoming(with_voice):
   id=str(uuid4());incoming_ids.append(id)
   c.execute("INSERT crm.Message(MessageId,ConversationId,Body,Direction) VALUES(?,?,?,'incoming')",id,conversation,'[Adjunto]' if with_voice else 'Pregunta técnica sintética')
   epoch=c.execute('SELECT Epoch FROM crm_channels.ConversationControl WHERE ConversationId=?',conversation).fetchval()
   c.execute("INSERT crm_channels2.MessageRoute(InstitutionId,MessageId,IntegrationId,IdentityId,ActorKind,CompletedAt) VALUES(?,?,?,?,'external',SYSUTCDATETIME())",inst,id,identity['IntegrationId'],identity['IdentityId'])
   if with_voice:
    asset=str(uuid4());made.add(asset);shutil.copyfile(files.path(sample),files.path(asset))
    c.execute("INSERT crm_channels4.MediaAsset(MediaId,InstitutionId,IntegrationId,IdentityId,ConversationId,MessageId,SourceKind,State,Kind,FileName,ProviderReference) VALUES(?,?,?,?,?,?,'provider','processing','audio','nota-de-voz.ogg','{}')",asset,inst,identity['IntegrationId'],identity['IdentityId'],conversation,id)
    media.mark_ready(c,s,asset,dict(info),{'voice':True,'synthetic_fixture':True})
   w.schedule(c,s,item,identity,id)
   assert w.Worker(s,Gateway).once()
   row=one(c,'SELECT Status,ResultCode,ResultMetadata FROM crm_channels2.ProviderOperation WHERE InstitutionId=? AND OperationId=?',inst,id)
   data=json.loads(row['ResultMetadata'])
   if data.get('reply'):reply_ids.append(data['reply'])
   return id,row,data
  first,state,data=incoming(True)
  assert state['Status']=='confirmed',state.get('ResultCode')
  assert data['voiceMedia'] and calls=={'gemini':1,'tts':1}
  job=one(c,'SELECT * FROM crm_channels2.SendJob WHERE InstitutionId=? AND MessageId=?',inst,data['reply']);assert job
  payload={'origin':w.ORIGIN,'automationId':first,'body':answer,'mediaId':data['voiceMedia']}
  w.dispatch_authorized(c,s,job,payload)
  asset,_=media.file_for(c,s,data['voiceMedia'],conversation=conversation)
  assert str(asset['MessageId'])==data['reply'] and asset['FileName']=='nota-de-voz.ogg'
  checks['incoming_voice_to_grounded_reply_ogg_outbox_and_frontier']=True
  try:w.dispatch_authorized(c,s,job,{**payload,'mediaId':str(uuid4())});raise AssertionError('mismatch accepted')
  except HTTPException as e:assert e.detail=='voice_media_mismatch'
  checks['forged_media_rejected']=True
  second,state,data=incoming(False)
  assert state['Status']=='confirmed' and data['voiceMedia'] is None and data['voiceReason']=='voice_conversation_limit'
  assert calls=={'gemini':2,'tts':1}
  checks['next_turn_text_after_cap_without_paid_tts']=True
  p.max_audios_per_conversation=base+2;write_policy();mode='human'
  third,state,data=incoming(True)
  assert state['Status']=='abandoned' and not data.get('reply'),state.get('ResultCode')
  assert calls=={'gemini':3,'tts':2}
  checks['human_takeover_during_synthesis_prevents_enqueue']=True
  checks['paid_provider_calls']=0
  raise Rollback()
except Rollback:pass
finally:
 w.transaction,v.transaction,v.synthesize,mail.enabled=original
 for id in made:
  for suffix in ['.part','.checked','.bin']:files.path(id,suffix).unlink(missing_ok=True)
with transaction(s,anonymous=True) as c:
 for id in incoming_ids+reply_ids:assert not c.execute('SELECT 1 FROM crm.Message WHERE MessageId=?',id).fetchone()
 for id in incoming_ids:assert not c.execute('SELECT 1 FROM crm_channels2.ProviderOperation WHERE InstitutionId=? AND OperationId=?',inst,id).fetchone()
checks['rollback_messages_operations_and_exact_files']=True
print('P19_NATIVE_WORKER',json.dumps(checks))
