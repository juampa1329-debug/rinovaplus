from contextlib import nullcontext
from types import SimpleNamespace
from uuid import uuid4
import json
from unittest.mock import Mock

import pytest
from pglast import parse_sql

from app.institutional import automatic_optout as target, contact_preference, workspace, campaigns
from app.institutional.contact_intent import opted_out
from app.institutional.operations_policy import layout
from app.institutional.postgres_dialect import postgres_sql

@pytest.mark.parametrize('text', [
 'No quiero recibir más mensajes', 'no deseo recibir informacion',
 'Por favor, no me escriban más', 'No me contacten más, por favor',
 'Dejen de enviarme mensajes', 'Elimínenme de su lista', 'STOP',
 'No recibir mensajes', 'No quiero que me llamen', '¿Pueden dejar de escribirme por favor?',
 'No me envíen más mensajes', 'No quiero que me manden publicidad',
])
def test_clear_customer_stop_requests(text):
 assert opted_out(text)

@pytest.mark.parametrize('text', [
 'No gracias', 'No me interesa ese programa', 'No quiero pausar el seguimiento',
 '¿Qué significa no quiero mensajes?', 'No sé cuánto cuesta',
 'Mi mamá no quiere mensajes', '¿No me enviarían las cuotas?',
 'No tengo el abono, pero me interesa', 'Conocer el programa', None,
 'No me envíen el formulario todavía', 'No quiero que me manden un audio, prefiero texto',
])
def test_sales_objection_question_or_third_party_is_not_an_optout(text):
 assert not opted_out(text)


def fixture(monkeypatch, *, transcript=False, mismatch=False, replay=False):
 ids=[str(uuid4()) for _ in range(5)]
 inst,identity,message,conversation,contact=ids
 settings=SimpleNamespace(ticket={'version':'cbn-institutional-operations-p11-v1','context':[[1,inst]]})
 incoming={'ContactId':contact,'ConversationId':conversation,'Body':'No recibir mensajes' if not mismatch else 'Otra petición'}
 document={'message_id':message,'conversation_id':conversation,'text':'No recibir mensajes','authority':'automatic_audio_transcription_not_human_verified'}
 queries=[]
 def one(c,sql,*args):
  assert sql.count('?')==len(args)
  parse_sql(postgres_sql(sql,layout()['tables']).replace('%s','NULL'))
  queries.append(sql)
  if 'SourceKey' in sql:return {'EventId':str(uuid4())} if replay else None
  if 'Setting' in sql:return {'Document':json.dumps(document)}
  return incoming
 monkeypatch.setattr(target.db,'one',one)
 monkeypatch.setattr(workspace,'primary',lambda *a:contact)
 apply=Mock();events=[]
 monkeypatch.setattr(contact_preference,'apply_no_contact',apply)
 monkeypatch.setattr(campaigns,'event',lambda *a,**kw:events.append((a,kw)))
 return settings,identity,message,contact,document,queries,apply,events

@pytest.mark.parametrize('channel',['whatsapp','instagram','messenger'])
def test_authenticated_request_has_canonical_scope_without_operator_impersonation(monkeypatch,channel):
 settings,identity,message,contact,document,queries,apply,events=fixture(monkeypatch)
 assert target.receive(None,settings,identity,message,'No recibir mensajes')
 apply.assert_called_once()
 assert apply.call_args.args[2]==contact
 assert apply.call_args.kwargs['source']=='canonical_incoming_request'
 assert apply.call_args.kwargs['proof']['origin_identity_id']==identity
 assert 'actor' not in apply.call_args.kwargs
 assert 'i.ConversationId=m.ConversationId' in queries[1]
 assert [v[0][2] for v in events]==['opt_out','no_contact_applied']
 assert events[0][0][3]['message_id']==message


def test_same_incoming_replay_does_not_close_or_cancel_twice(monkeypatch):
 settings,identity,message,_,_,queries,apply,events=fixture(monkeypatch,replay=True)
 assert target.receive(None,settings,identity,message,'No recibir mensajes')
 assert len(queries)==1 and not apply.called and not events


def test_provenance_mismatch_never_suppresses_another_person(monkeypatch):
 settings,identity,message,_,_,_,apply,events=fixture(monkeypatch,mismatch=True)
 assert not target.receive(None,settings,identity,message,'No recibir mensajes')
 assert not apply.called and not events


def test_saved_audio_request_is_bound_to_its_source_and_cannot_use_forged_text(monkeypatch):
 settings,identity,message,_,document,_,apply,_=fixture(monkeypatch,transcript=True,mismatch=True)
 assert target.receive(None,settings,identity,message,'No recibir mensajes',transcribed=True)
 assert apply.call_args.kwargs['proof']['input_kind']=='audio_transcription'
 apply.reset_mock();document['message_id']=str(uuid4())
 assert not target.receive(None,settings,identity,message,'No recibir mensajes',transcribed=True)
 assert not apply.called


def test_non_optout_does_not_add_database_reads(monkeypatch):
 settings,identity,message,_,_,queries,apply,_=fixture(monkeypatch)
 assert not target.receive(None,settings,identity,message,'Me parece caro')
 assert not queries and not apply.called


def test_legacy_reconciler_preserves_newer_consent_and_has_no_provider_io(monkeypatch):
 settings,identity,message,_,_,_,apply,events=fixture(monkeypatch)
 request={'EventId':str(uuid4()),'IdentityId':identity,'MessageId':message,'Body':'No recibir mensajes'}
 calls=[]
 def one(c,sql,*args):
  parse_sql(postgres_sql(sql,layout()['tables']).replace('%s','NULL'))
  calls.append(sql)
  return request if 'SELECT TOP(1)' in sql else {'Allowed':1}
 monkeypatch.setattr(target.db,'one',one)
 from app.institutional import store
 monkeypatch.setattr(store,'transaction',lambda *a,**kw:nullcontext(None))
 assert target.Reconciler(settings).once()
 assert not apply.called and len(events)==1
 assert events[0][0][3]['outcome']=='later_consent_preserved'
 assert 'TOP(1)' in calls[0] and 'no_contact_applied' in calls[0]

@pytest.mark.parametrize('channel',['whatsapp','instagram','messenger'])
def test_provider_ingress_stops_before_any_reply_scheduling(monkeypatch,channel):
 from datetime import datetime,timezone
 from app.institutional import channel_events,channel_media,comment_private,whatsapp_gemini,campaign_runtime
 settings,identity,_,contact,_,_,_,_=fixture(monkeypatch)
 conversation,integration=str(uuid4()),str(uuid4())
 linked={'IdentityId':identity,'ContactId':contact,'ConversationId':conversation}
 statements=[]
 class Cursor:
  def execute(self,sql,*args):
   statements.append(sql);self.duplicate='SELECT 1 FROM crm_channels2.ExternalMessage' in sql;return self
  def fetchone(self):return None if self.duplicate else (1,)
 monkeypatch.setattr(channel_events,'one',lambda *a:linked)
 monkeypatch.setattr(channel_media,'register_incoming',lambda *a:None)
 monkeypatch.setattr(comment_private,'incoming_source',lambda *a:None)
 monkeypatch.setattr(campaign_runtime,'observe_identity',lambda *a,**kw:None)
 scheduled=Mock();monkeypatch.setattr(whatsapp_gemini,'schedule',scheduled)
 def receive(c,s,identity_id,message,text):
  assert identity_id==identity and text=='No recibir mensajes'
  assert any('INSERT crm_channels2.MessageRoute' in sql for sql in statements)
  return True
 monkeypatch.setattr(target,'receive',receive)
 seconds=datetime.now(timezone.utc).timestamp()
 provider=({'type':'text','text':{'body':'No recibir mensajes'},'timestamp':str(int(seconds))}
           if channel=='whatsapp' else {'message':{'text':'No recibir mensajes'},'timestamp':int(seconds*1000)})
 channel_events.incoming(Cursor(),settings,{'Channel':channel,'IntegrationId':integration},
  {'author':'573000000000','external':'real-provider-id','text':'No recibir mensajes','provider':provider})
 assert not scheduled.called


def test_idle_history_reconciliation_is_bounded_and_throttled(monkeypatch):
 settings,_,_,_,_,_,_,_=fixture(monkeypatch)
 reads=Mock(return_value=None);monkeypatch.setattr(target.db,'one',reads)
 from app.institutional import store
 tx=Mock(side_effect=lambda *a,**kw:nullcontext(None));monkeypatch.setattr(store,'transaction',tx)
 worker=target.Reconciler(settings)
 assert worker.once() is False and worker.once() is False
 assert reads.call_count==2 and tx.call_args.kwargs=={'anonymous':True}


def test_unavailable_history_is_throttled_without_disabling_immediate_optouts(monkeypatch):
 settings,_,_,_,_,_,_,_=fixture(monkeypatch)
 reads=Mock(side_effect=RuntimeError('unavailable'));monkeypatch.setattr(target.db,'one',reads)
 from app.institutional import store
 monkeypatch.setattr(store,'transaction',lambda *a,**kw:nullcontext(None))
 worker=target.Reconciler(settings)
 with pytest.raises(RuntimeError):worker.once()
 assert worker.once() is False and reads.call_count==1


def test_history_recovery_failure_does_not_skip_other_channel_workers(monkeypatch,caplog):
 from app.institutional import channel_workers,channel_media,broadcast_catalog_refresh
 settings,_,_,_,_,_,_,_=fixture(monkeypatch)
 for module,name in [(channel_workers,'EventWorker'),(channel_workers,'Dispatcher'),
                     (channel_media,'MediaWorker'),(broadcast_catalog_refresh,'Refresher')]:
  monkeypatch.setattr(module,name,Mock())
 monkeypatch.setattr(target.Reconciler,'once',Mock(side_effect=RuntimeError('private details')))
 worker=channel_workers.Workers.__new__(channel_workers.Workers)
 worker.settings=settings;worker.fast_queues=True;worker.transport=None;worker.media_downloader=None
 worker.stop_event=SimpleNamespace(is_set=Mock(side_effect=[False,True]),wait=Mock())
 stages=[];worker.pulse=SimpleNamespace(observe=lambda stage,work:stages.append(stage))
 worker.run()
 assert stages==['media','campaigns','broadcasts','maintenance','agents']
 assert 'contact_preference_recovery_retry_required' in caplog.text
 assert 'private details' not in caplog.text


@pytest.mark.parametrize('still_blocked',[True,False])
def test_existing_recorded_optout_finishes_closure_only_after_live_authority_check(monkeypatch,still_blocked):
 settings,_,_,contact,_,_,apply,_=fixture(monkeypatch)
 queries=[]
 def one(c,sql,*args):
  parse_sql(postgres_sql(sql,layout()['tables']).replace('%s','NULL'))
  assert sql.count('?')==len(args)
  queries.append(sql)
  return {'ContactId':contact} if 'b.ContactId' in sql else None
 monkeypatch.setattr(target.db,'one',one)
 monkeypatch.setattr(contact_preference,'blocked',lambda *a:still_blocked)
 from app.institutional import store
 tx=Mock(side_effect=lambda *a,**kw:nullcontext(None));monkeypatch.setattr(store,'transaction',tx)
 assert target.Reconciler(settings).once() is still_blocked
 assert tx.call_args.args[1] is True
 assert apply.called is still_blocked
 if still_blocked:
  assert apply.call_args.kwargs['source']=='recorded_no_contact_recovery'
  assert apply.call_args.kwargs['proof']=={'authority':'existing_persisted_no_contact'}
 assert len(queries)==2 and "v.State<>'closed'" in queries[1]
