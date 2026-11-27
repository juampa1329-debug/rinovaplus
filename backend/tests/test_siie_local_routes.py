"""Route transaction/idempotency tests with an isolated in-memory SQL double."""
from contextlib import contextmanager
from copy import deepcopy
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.institutional import agents_api, siie_api, siie_environment


class Cursor:
    agent_user = 'fixture-owner'
    rowcount = 0
    def __init__(self):
        self.programs, self.profiles, self.sources, self.operations = {}, {}, {}, {}
        self.result = []
    def execute(self, sql, *p):
        self.rowcount = 0
        if sql.startswith('SELECT DISTINCT p.ProgramId'):
            self.result = [(id, v['name'], v['school'], v['schedule'], v['active'], v['revision']) for id,v in self.programs.items() if any(pid == id and source.get('environment') == {'fingerprint':p[3],'base_url':p[4]} and source['program_id'] == p[5] for (pid,_),source in self.sources.items())]
        elif sql.startswith('SELECT p.ProgramId'):
            self.result = [(id, v['name'], v['school'], v['schedule'], v['active'], v['revision']) for id,v in self.programs.items() if self.profiles.get(id,{}).get('siie_program_id') == p[1]]
        elif sql.startswith('SELECT COALESCE(MAX'):
            self.result = [(max(self.programs, default=0),)]
        elif sql.startswith('SELECT Revision FROM'):
            self.result = [(self.programs[p[1]]['revision'],)] if p[1] in self.programs else []
        elif sql.startswith('INSERT crm_agents5.Program'):
            self.programs[p[1]] = dict(name=p[2],school=p[3],schedule=p[4],active=p[5],revision=1);self.result=[]
        elif sql.startswith('UPDATE crm_agents5.Program'):
            value=self.programs[p[6]]
            assert value['revision']==p[7]
            value.update(name=p[0],school=p[1],schedule=p[2],active=p[3],revision=p[7]+1);self.rowcount=1;self.result=[]
        else: raise AssertionError(sql)
        return self
    def fetchval(self): return self.result[0][0] if self.result else None
    def fetchone(self): return self.result[0] if self.result else None
    def fetchall(self): return self.result


@pytest.fixture
def fixture(monkeypatch):
    monkeypatch.setenv('SIIE_BASE_URL','https://siieplus.online/SIIEWebPlustest/')
    c=Cursor(); state=SimpleNamespace(allowed=True, source_reads=0)
    @contextmanager
    def transaction(write=False):
        if not state.allowed: raise HTTPException(403,'permission_denied')
        before=deepcopy((c.programs,c.profiles,c.sources,c.operations))
        try: yield c
        except Exception:
            if write:c.programs,c.profiles,c.sources,c.operations=before
            raise
    service=SimpleNamespace(transaction=transaction)
    monkeypatch.setattr(agents_api,'Agents',lambda *_:service)
    monkeypatch.setattr(agents_api,'install_agents',lambda *_:None)
    monkeypatch.setattr(agents_api,'institution',lambda _: 'fixture-institution')
    from app.institutional import siie_local
    monkeypatch.setattr(siie_local,'institution',lambda _: 'fixture-institution')
    monkeypatch.setattr(agents_api,'read_profile',lambda c,_,id:c.profiles.get(id))
    monkeypatch.setattr(agents_api,'save_profile',lambda c,_,id,rev,actor,p:c.profiles.__setitem__(id,p.model_dump()))
    monkeypatch.setattr(agents_api,'local_source',lambda c,_,id,kind='offer': c.sources.get((id,kind)))
    monkeypatch.setattr(agents_api,'save_source',lambda c,_,id,rev,actor,source:c.sources.__setitem__((id,source['kind']),deepcopy(source)))
    def replay(c,settings,actor,id,action,resource,body):
        digest=json.dumps(body,sort_keys=True); prior=c.operations.get((id,action,resource))
        if prior and prior[0]!=digest:raise HTTPException(409,'operation_changed')
        return digest, prior[1] if prior else None
    monkeypatch.setattr(agents_api,'replay',replay)
    monkeypatch.setattr(agents_api,'record_operation',lambda c,settings,actor,id,action,resource,digest,result:c.operations.__setitem__((id,action,resource),(digest,deepcopy(result))))
    def read(*_):
        state.source_reads+=1
        return {'environment':siie_environment.current().document(),'data':{'source_revision':'fixture-revision','items':[{'program_id':'143','name':'Software ficticio','school':None,'duration_levels':4}]}}
    monkeypatch.setattr(siie_api,'read',read)
    app=FastAPI();agents_api.install(app,SimpleNamespace())
    return TestClient(app),c,state


def command():
    return {'environment':siie_environment.current().document(),'operation_id':str(uuid4()),'revision':0,'source_revision':'fixture-revision'}


@pytest.mark.parametrize('stored_active', [0, 1, False, True])
def test_local_editor_round_trip_projects_legacy_bit_as_boolean(fixture, monkeypatch, stored_active):
    from app.institutional import db
    client, c, _ = fixture
    assert client.post('/api/v1/agents/programs', json={
        'operation_id': str(uuid4()), 'revision': 0, 'name': 'Turismo ficticio',
        'commercial': {'aliases': 'SHAT'},
    }).status_code == 200
    monkeypatch.setattr(db, 'one', lambda *_: {
        'ProgramId': 1, 'Name': 'Turismo ficticio', 'School': '', 'Schedule': '',
        'Active': stored_active, 'Revision': 1, 'Authority': 'declared_CRM',
    })
    read = client.get('/api/v1/agents/programs/1').json()
    assert read['program']['Active'] is bool(stored_active)
    body = {'operation_id': str(uuid4()), 'revision': read['revision'],
            'name': read['program']['Name'], 'active': read['program']['Active'],
            'commercial': {**read['commercial'], 'aliases': 'SHAT; Turismo'}}
    result = client.put('/api/v1/agents/programs/1', json=body)
    assert result.status_code == 200 and result.json()['revision'] == 2
    assert c.programs[1]['active'] is bool(stored_active)
    assert c.profiles[1]['aliases'] == 'SHAT; Turismo'


def test_program_write_keeps_strict_boolean_validation(fixture):
    client, c, _ = fixture
    result = client.post('/api/v1/agents/programs', json={
        'operation_id': str(uuid4()), 'revision': 0,
        'name': 'Programa ficticio', 'active': 1,
    })
    assert result.status_code == 422
    assert c.programs == {} and c.operations == {}


def test_copy_page_replay_and_repeated_sync_do_not_duplicate_and_preserve_manual_fields(fixture):
    client,c,state=fixture; body=command()
    assert client.post('/api/v1/agents/programs/sync-siie-page',json=body).json()['count']==1
    assert len(c.programs)==1 and (1,'program') in c.sources
    reads=state.source_reads
    assert client.post('/api/v1/agents/programs/sync-siie-page',json=body).status_code==200
    assert state.source_reads==reads and len(c.programs)==1
    c.profiles[1]['duration']='Duración revisada manualmente'
    assert client.post('/api/v1/agents/programs/sync-siie-page',json=command()).status_code==200
    assert c.profiles[1]['duration']=='Duración revisada manualmente' and len(c.programs)==1


def test_changed_source_or_revoked_authority_never_persists_unreviewed_programs(fixture,monkeypatch):
    client,c,state=fixture; body=command();body['source_revision']='old-revision'
    assert client.post('/api/v1/agents/programs/sync-siie-page',json=body).status_code==409
    assert not c.programs
    original=siie_api.read
    def revoke(*a):
        result=original(*a);state.allowed=False;return result
    monkeypatch.setattr(siie_api,'read',revoke)
    assert client.post('/api/v1/agents/programs/sync-siie-page',json=command()).status_code==403
    assert not c.programs and not c.sources


def test_manual_save_is_local_and_does_not_require_an_available_siie(fixture,monkeypatch):
    client,c,state=fixture
    client.post('/api/v1/agents/programs/sync-siie-page',json=command())
    monkeypatch.setattr(siie_api,'read',lambda *_:pytest.fail('offline edit must not consult SIIE'))
    profile=deepcopy(c.profiles[1]);profile['price_cop']=600000;profile['price_concept']='Enseñanza de nivel ficticio'
    result=client.put('/api/v1/agents/programs/1',json={'operation_id':str(uuid4()),'revision':1,'name':'Software ficticio','school':'','commercial':profile})
    assert result.status_code==200 and c.profiles[1]['price_cop']==600000
    assert c.profiles[1]['price_valid_until'] is None and (1,'program') in c.sources


def test_copy_failure_rolls_back_program_source_and_operation_together(fixture,monkeypatch):
    client,c,_=fixture
    def fail(*_): raise HTTPException(409,'fixture_storage_failure')
    monkeypatch.setattr(agents_api,'save_profile',fail)
    assert client.post('/api/v1/agents/programs/sync-siie-page',json=command()).status_code==409
    assert not c.programs and not c.sources and not c.operations


def test_two_review_tabs_cannot_create_a_second_program_with_the_same_source_identity(fixture):
    client,c,_=fixture
    client.post('/api/v1/agents/programs/sync-siie-page',json=command())
    body={'operation_id':str(uuid4()),'revision':0,'name':'Segundo borrador ficticio','school':'','commercial':deepcopy(c.profiles[1])}
    assert client.post('/api/v1/agents/programs',json=body).status_code==409
    assert len(c.programs)==1
