"""Synthetic HTTP and durable-intent tests; no real people, keys or SIIE writes."""

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from types import SimpleNamespace
from uuid import uuid4

import httpx2 as httpx
import pytest
from fastapi import HTTPException
from pglast import parse_sql

from app.institutional import siie_environment as environments, siie_preicfes as journey
from app.institutional import siie_preicfes_client as client, siie_records, workspace
from app.institutional.crypto import canonical
from app.institutional.operations_policy import layout
from app.institutional.postgres_dialect import postgres_sql


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("SIIE_BASE_URL","https://siie.example.test/SIIEWebPlustest/")
    monkeypatch.setenv("SIIE_API_HOSTS","siie.example.test")
    monkeypatch.setenv("SIIE_API_TOKEN","fixture-only-single-api-key-1234567890")
    return environments.current().document()


@pytest.mark.parametrize("url",["https://siie.example.test/SIIEWebPlustest", "http://siie.example.test/test/",
    "https://foreign.invalid/test/", "https://siie.example.test/test/?x=1/", "https://siie.example.test/a/../test/",
    "https://siie.example.test/a/%2e%2e/test/"])
def test_invalid_base_rejected_before_transport(env,monkeypatch,url):
    monkeypatch.setenv("SIIE_BASE_URL",url)
    with pytest.raises(HTTPException):environments.current()


def test_only_central_base_selects_the_entire_client(env,monkeypatch):
    monkeypatch.setenv("SIIE_API_BASE_URL","https://foreign.invalid/ignored/")
    assert environments.current().endpoint("Api/CRM/v1/Periodos.aspx")==env["base_url"]+"Api/CRM/v1/Periodos.aspx"
    for path in ["/Api/CRM", "../Api/CRM", "https://foreign.invalid/", "Api/%2fprivate", "Api/CRM?token=x"]:
        with pytest.raises(ValueError):environments.current().endpoint(path)
    monkeypatch.setenv("SIIE_BASE_URL","https://siie.example.test/SIIEWEBPLUS/")
    with pytest.raises(HTTPException,match="siie_environment_changed"):environments.require(env)


@pytest.fixture
def pilot(monkeypatch,env):
    ids=dict(zip(client.IDS,[101,102,103,104])); contact,conv,event,choice=[str(uuid4()) for _ in range(4)]
    proof={"identity_id":str(uuid4()),"contact_id":contact,"waId":"573000000000",
           "channelAccountId":str(uuid4()),"conversationId":conv}
    store={("se",event):{"revision":1,"metadata":{},"private":{"contact_id":contact,"event":{
        **ids,"event_type":"registration.created","documento":"FIXTURE123"}}}}
    active={"write":False}; calls=[]; fail={"assign":False,"pdf":False,"configuration":False,"writes":True}
    expires=(datetime.now(timezone.utc)+timedelta(hours=2)).isoformat()
    pdf=b"%PDF-1.7\nsynthetic integration test\n%%EOF";sha=hashlib.sha256(pdf).hexdigest()
    quote={**ids,"planId":201,"mode":"CONTADO","level":1,"currency":"COP","amountCop":800000,
        "quoteRevisionId":"a"*64,"expiresAtUtc":expires,"installments":[{"concept":"CONTADO","amountCop":800000,"dueDate":"2027-02-10"}]}
    assignment={"idInscripcion":101,"assignmentId":301,"state":"plan_assigned","academicEnrollmentApplied":False,
        "paymentConfirmed":False,"plan":{"planId":201,"mode":"CONTADO","quoteRevisionId":"a"*64,
        "installments":[{"installmentId":401,"concept":"CONTADO","amountCop":800000,"dueDate":"2027-02-10"}]}}
    order={"idInscripcion":101,"orderId":str(uuid4()),"idVolante":501,"assignmentId":301,"installmentId":401,
        "state":"issued","amountCop":800000,"currency":"COP","expiresAtUtc":expires,"paymentConfirmed":None,
        "pdf":{"mime":"application/pdf","sizeBytes":len(pdf),"sha256":sha,"version":sha,
               "maximumBytes":client.MAX_PDF,"endpoint":client.PDF_PATH,"requiresBinding":True}}
    def remote(request):
        assert not active["write"],"Network IO inside writer transaction"
        assert request.url.path.startswith('/SIIEWebPlustest/Api/CRM/v1/PreIcfes/')
        assert request.headers['X-API-Key']=='fixture-only-single-api-key-1234567890'
        name=request.url.path.rsplit('/',1)[-1];calls.append((request.method,name))
        body=json.loads(request.content) if request.method=='POST' else dict(request.url.params)
        if name=='Inscripcion.aspx':data={**ids,"documento":"FIXTURE123","celular":"3000000000","studentName":"Synthetic Person","status":"registration_confirmed"}
        elif name=='Conversacion.aspx':data={"idInscripcion":101,"bindingId":str(uuid4()),"expiresAtUtc":expires,
             "conversationId":conv,"channelAccountId":proof["channelAccountId"],"verificationBasis":"trusted_crm_sender_attestation_and_siie_phone_match"}
        elif name=='Plan.aspx' and request.method=='GET':data={"idInscripcion":101,"options":[quote],"requiresConfiguration":fail["configuration"],"canAssign":not fail["configuration"]}
        elif name=='Plan.aspx':
            assert not set(body)&{'level','amountCop','installments','dueDate'}
            assert any(k=='sx' and v['metadata']['state']=='pending_review' for (k,_),v in store.items())
            if fail['assign']:fail['assign']=False;raise httpx.ReadTimeout('uncertain fixture',request=request)
            data=assignment
        elif name=='ConsultaOperacion.aspx':data={"requestId":body['requestId'],"operation":body['operation'],"state":"confirmed","result":assignment}
        elif name=='Volante.aspx':assert body['assignmentId']==301 and body['installmentId']==401;data=order
        elif name=='VolantePdf.aspx':
            content=pdf+b'bad' if fail['pdf'] else pdf
            return httpx.Response(200,content=content,headers={'Content-Type':'application/pdf','Content-Length':str(len(content)),
                 'X-Content-SHA256':sha,'X-PDF-Version':sha,'Content-Disposition':'attachment; filename="test.pdf"'})
        elif name=='PagoEstado.aspx':data={"orderId":order['orderId'],"state":"pending","currency":"COP","paymentConfirmed":False,
              'verificationBasis':'verified_non_void_receipts_with_exact_voucher_and_deposit_reference'}
        else:pytest.fail(name)
        return httpx.Response(200,json={'status':'ok','schemaVersion':1,'data':data})
    real_request=client.request
    monkeypatch.setattr(client,'request',lambda kind,values,environment,**kw:real_request(kind,values,environment,transport=httpx.MockTransport(remote),**kw))
    @contextmanager
    def tx(self,write=False,**kw):
        active['write']=write
        try:yield None
        finally:active['write']=False
    monkeypatch.setattr(journey.Finance,'tx',tx)
    monkeypatch.setattr(journey,'actor',lambda *a:{'UserId':str(uuid4())})
    monkeypatch.setattr(journey,'sender',lambda *a:deepcopy(proof))
    monkeypatch.setattr(journey,'config',lambda *a:{'writes_enabled':fail['writes']})
    monkeypatch.setattr(journey,'rate',lambda *a:True)
    monkeypatch.setattr(workspace,'primary',lambda c,id:id)
    monkeypatch.setattr(journey.db,'audit',lambda *a,**k:None)
    monkeypatch.setattr(journey.db,'bound_hash',lambda s,v,*a:hashlib.sha256(canonical(v)).digest())
    monkeypatch.setattr(journey.db,'one',lambda *a:{'Body':'Elijo contado'})
    monkeypatch.setattr(siie_records,'get',lambda c,s,k,id:deepcopy(store.get((k,id))))
    def put(c,s,k,id,metadata,private,previous=None):
        assert active['write'];revision=(previous or {}).get('revision',0)+1
        assert (k,id) not in store or store[(k,id)]['revision']==previous['revision']
        store[(k,id)]={'revision':revision,'metadata':deepcopy(metadata),'private':deepcopy(private)}
        return revision
    monkeypatch.setattr(siie_records,'put',put)
    service=journey.Finance(SimpleNamespace(ticket={'context':[[1,str(uuid4())]]}))
    work=service.prepare(journey.Prepare(event_id=event,conversation_id=conv,environment=env,reviewed=True))
    def command(kind,**kw):
        work=service.read(work_id)
        body=journey.Command(operation_id=str(uuid4()),revision=work['revision'],reviewed=True,**kw)
        return body,service.command(work_id,kind,body)
    work_id=work['id']
    return SimpleNamespace(service=service,id=work_id,command=command,store=store,calls=calls,fail=fail,env=env,choice=choice,pdf=pdf,proof=proof)


def assigned(p):
    p.command('binding');p.service.query(p.id,'plans')
    return p.command('assign',plan_id=201,mode='CONTADO',quote_revision_id='a'*64,choice_message_id=p.choice)


def test_full_registration_binding_choice_assignment_order_and_verified_pdf(pilot):
    p=pilot;body,result=assigned(p)
    assert result['state']=='confirmed'
    p.command('order',installment_id=401)
    assert p.service.pdf(p.id).body==p.pdf
    assert p.service.query(p.id,'payment')['payment']['state']=='pending'
    assert [v[1] for v in p.calls]==['Inscripcion.aspx','Conversacion.aspx','Plan.aspx','Plan.aspx','Volante.aspx','VolantePdf.aspx','PagoEstado.aspx']
    assert p.service.command(p.id,'assign',body)['repeated']
    assert len(p.calls)==7


def test_timeout_preserves_intent_no_post_replay_and_operation_lookup_recovers(pilot):
    p=pilot;p.fail['assign']=True;body,result=assigned(p)
    assert result['state']=='uncertain' and p.service.read(p.id)['pending']==body.operation_id
    before=len(p.calls);assert p.service.command(p.id,'assign',body)['repeated'];assert len(p.calls)==before
    assert p.service.reconcile(p.id)['assignment']['assignmentId']==301
    assert p.calls[-1]==('GET','ConsultaOperacion.aspx')


def test_pending_test_work_never_uses_production_base(pilot,monkeypatch):
    p=pilot;p.fail['assign']=True;assigned(p);before=len(p.calls)
    monkeypatch.setenv('SIIE_BASE_URL','https://siie.example.test/SIIEWEBPLUS/')
    assert not p.service.read(p.id)['environment_current']
    with pytest.raises(HTTPException,match='siie_environment_changed'):p.service.reconcile(p.id)
    assert len(p.calls)==before and p.service.read(p.id)['environment']==p.env


def test_bad_pdf_never_downloads_and_does_not_confirm_payment(pilot):
    p=pilot;assigned(p);p.command('order',installment_id=401);p.fail['pdf']=True
    with pytest.raises(HTTPException,match='siie_finance_invalid_response'):p.service.pdf(p.id)
    assert 'payment' not in p.service.read(p.id)


def test_plan_requires_ready_configuration_and_explicit_choice(pilot):
    p=pilot;p.command('binding');p.fail['configuration']=True
    with pytest.raises(HTTPException,match='siie_finance_configuration_required'):p.service.query(p.id,'plans')
    p.fail['configuration']=False;p.service.query(p.id,'plans');before=len(p.calls)
    with pytest.raises(HTTPException,match='siie_finance_explicit_choice_required'):p.command('assign',plan_id=201,mode='CONTADO',quote_revision_id='a'*64)
    assert len(p.calls)==before


def test_disabled_writes_never_enter_transport(pilot):
    p=pilot;p.fail['writes']=False;before=len(p.calls)
    with pytest.raises(HTTPException,match='siie_registration_writes_disabled'):p.command('binding')
    assert len(p.calls)==before


def test_expired_binding_can_renew_without_losing_uncertain_assignment(pilot):
    p=pilot;p.fail['assign']=True;body,_=assigned(p)
    p.store[('sf',p.id)]['private']['binding']['expiresAtUtc']='2020-01-01T00:00:00Z'
    p.command('binding')
    assert p.service.read(p.id)['pending']==body.operation_id
    assert p.service.reconcile(p.id)['assignment']['assignmentId']==301
    assert sum(v==('POST','Plan.aspx') for v in p.calls)==1


def test_revoked_authority_preserves_receipt_without_exposing_result(pilot,monkeypatch):
    p=pilot;original=client.request;revoked=[False]
    def remote(*a,**kw):
        result=original(*a,**kw);revoked[0]=True;return result
    def who(*a):
        if revoked[0]:raise HTTPException(403,'permission_denied')
        return {'UserId':str(uuid4())}
    monkeypatch.setattr(client,'request',remote);monkeypatch.setattr(journey,'actor',who)
    with pytest.raises(HTTPException,match='permission_denied'):p.command('binding')
    assert p.store[('sf',p.id)]['private']['binding']['bindingId']
    assert p.calls[-1]==('POST','Conversacion.aspx')


def test_sender_sql_is_bound_to_real_incoming_route_and_unique_identity(env,monkeypatch):
    def rows(c,sql,*args):
        assert sql.count('?')==len(args)
        parse_sql(postgres_sql(sql,layout()['tables']).replace('%s','NULL'))
        assert "r.ActorKind='external'" in sql and "a.Channel='whatsapp'" in sql
        return []
    monkeypatch.setattr(journey.db,'rows',rows)
    settings=SimpleNamespace(ticket={'context':[[1,str(uuid4())]]})
    with pytest.raises(HTTPException,match='siie_finance_verified_sender_required'):journey.sender(None,settings,str(uuid4()))
