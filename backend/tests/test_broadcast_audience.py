"""Segmentation rejects unknown facts and preserves observed receipt semantics."""
import json
from datetime import date
from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.institutional import broadcast_audience as audience
from app.institutional.broadcast_models import CampaignWrite

TODAY = date(2026, 11, 17)
PERSON = dict(Name="Ejemplo", City="Cartagena", Program="Software", Schedule="Nocturna", Type="Aspirante", Stage="Contactado", CustomValues=json.dumps({"genero":"Femenino","nacimiento":"2000-11-18","pais":"Colombia","activo":False,"cuotas":0}))
DOCUMENT = dict(demographic_fields={"gender":"genero","birth_date":"nacimiento","country":"pais"},filters={})


def command(**extra):
    return dict(operation_id=uuid4(),reason="Prueba",name="Campaña",integration_id=uuid4(),template_id=uuid4(),template_version=1,**extra)


def test_demographics_are_declared_and_age_changes_on_birthday():
    profile, age, _ = audience.details(PERSON,DOCUMENT,TODAY)
    assert age == 25 and profile["age_band"] == "25–34"
    assert profile["gender"] == "Mujer"
    assert "nacimiento" not in profile and "birth_date" not in profile
    assert audience.details(PERSON,DOCUMENT,date(2026,11,18))[1] == 26
    assert audience.details(PERSON,dict(filters={}),TODAY)[0]["gender"] == "Sin dato"


@pytest.mark.parametrize("birth",["invalid","2027-01-01","1800-01-01",None])
def test_unusable_birth_date_never_guesses_an_age(birth):
    person=dict(PERSON,CustomValues=json.dumps({"nacimiento":birth}))
    assert audience.details(person,DOCUMENT,TODAY)[1] is None
    assert not audience.matches(person,dict(DOCUMENT,filters={"age_min":18}),TODAY)


def test_gender_range_location_and_custom_conditions_are_combined():
    filters={"genders":["Mujer"],"age_min":25,"age_max":25,"countries":["colombia"],"custom_fields":[{"field_key":"cuotas","values":["0"]},{"field_key":"activo","values":["false"]}]}
    assert audience.matches(PERSON,dict(DOCUMENT,filters=filters),TODAY)
    assert not audience.matches(PERSON,dict(DOCUMENT,filters=dict(filters,genders=["Hombre"])),TODAY)
    assert not audience.matches(PERSON,dict(DOCUMENT,filters=dict(filters,age_min=26)),TODAY)


def test_inactive_demographic_field_cannot_silently_expand_audience():
    fields=[SimpleNamespace(key="genero",active=False,type="List")]
    with pytest.raises(HTTPException,match="broadcast_segment_field_unavailable"):
        audience.configuration(DOCUMENT,fields)


def test_age_requires_date_typed_field_and_explicit_mapping():
    with pytest.raises(HTTPException,match="broadcast_birth_date_field_required"):
        audience.configuration({"demographic_fields":{"birth_date":"age"}},[SimpleNamespace(key="age",type="Number",active=True)])
    with pytest.raises(ValidationError):
        CampaignWrite(**command(filters={"age_min":18}))
    with pytest.raises(ValidationError):
        CampaignWrite(**command(filters={"age_min":30,"age_max":20},demographic_fields={"birth_date":"nacimiento"}))
    with pytest.raises(ValidationError):
        CampaignWrite(**command(filters={"audience_mode":"contacts","contact_ids":[]}))


def test_statistics_count_receipts_not_acceptance_and_keep_legacy_unknown():
    snapshot=json.dumps({"audience_profile":{"gender":"Mujer","city":"Cartagena","age_band":"25–34"}})
    rows=[dict(Snapshot=snapshot,Status="read",DeliveredAt=None,ReadAt="observed",RepliedAt="reply"),dict(Snapshot=snapshot,Status="failed",DeliveredAt=None,ReadAt=None,RepliedAt=None),dict(Snapshot='{"body":"old"}',Status="accepted",DeliveredAt=None,ReadAt=None,RepliedAt=None)]
    result=audience.analytics(rows)
    assert result["totals"] == dict(total=3,delivered=1,read=1,replied=1,failed=1)
    assert result["dimensions"]["gender"] == [dict(label="Mujer",total=2,delivered=1,read=1,replied=1,failed=1),dict(label="Sin dato",total=1,delivered=0,read=0,replied=0,failed=0)]
    assert audience.analytics([])["totals"]["total"] == 0


def test_two_consent_guards_exclude_one_person_once(monkeypatch):
    from app.institutional import broadcasts
    from app.institutional import campaigns
    from app.modules.crm_configuration.application import service

    person=dict(PERSON,IdentityId=str(uuid4()),ContactId=str(uuid4()),ConversationId=str(uuid4()),ExternalId="573000000000",ConversationState="open",ControlMode="ai",LastIncomingAt=None)
    settings=SimpleNamespace(ticket={"version":"cbn-institutional-operations-p11-v1"})
    account=dict(IntegrationId=str(uuid4()),Channel="whatsapp",RequestedStatus="connected",VerifiedStatus="verified",ApplicationState="active")
    monkeypatch.setattr(service,"read_configuration",lambda *a,**k:(SimpleNamespace(fields=[]),None))
    monkeypatch.setattr(broadcasts,"account",lambda *a:account)
    monkeypatch.setattr(broadcasts.templates,"approved",lambda *a,**k:None)
    monkeypatch.setattr(broadcasts,"enabled",lambda *a:True)
    monkeypatch.setattr(broadcasts,"institution",lambda *a:"institution")
    monkeypatch.setattr(broadcasts,"rows",lambda *a:[])
    monkeypatch.setattr(broadcasts,"candidate_rows",lambda *a:[person])
    monkeypatch.setattr(broadcasts,"consent",lambda *a:None)
    monkeypatch.setattr(campaigns,"marketing_allowed",lambda *a:False)
    cursor=SimpleNamespace(execute=lambda *a:SimpleNamespace(fetchall=lambda:[]))
    campaign=dict(CampaignId=str(uuid4()),IntegrationId=account["IntegrationId"],Name="Test",Document=json.dumps({"filters":{}}))
    result=broadcasts.preview(cursor,settings,campaign)
    assert result["counts"]==dict(matched=1,eligible=0,excluded=1)
    assert result["exclusions"]=={"marketing_consent_required":1}
    assert result["items"][0]["reasons"]==["marketing_consent_required"]


@pytest.mark.parametrize("state,external,attempts,allowed",[("failed",None,1,True),("failed","accepted-id",1,False),("uncertain",None,1,False),("sending",None,1,False),("failed",None,20,False)])
def test_retry_reprepares_only_definitive_unaccepted_work_without_provider_io(monkeypatch,state,external,attempts,allowed):
    from app.institutional import broadcasts
    from app.institutional.broadcast_models import Review
    settings=SimpleNamespace(ticket={"version":"cbn-institutional-broadcast-p7-v1"})
    service=broadcasts.Broadcasts(settings)
    recipient,identity,contact=str(uuid4()),str(uuid4()),str(uuid4())
    writes=[]
    cursor=SimpleNamespace(execute=lambda sql,*args:writes.append((sql,args)))
    actor=dict(UserId=str(uuid4()),AuthVersion=1,SessionId=str(uuid4()))
    @contextmanager
    def tx(auth,write=False,recent=False):
        assert write and recent
        yield cursor,actor
    monkeypatch.setattr(service,"tx",tx)
    monkeypatch.setattr(broadcasts,"institution",lambda *_:"institution")
    monkeypatch.setattr(broadcasts,"replay",lambda *a:("hash",None))
    monkeypatch.setattr(broadcasts,"current",lambda *a:dict(Revision=1,Epoch=1,State="running"))
    monkeypatch.setattr(broadcasts,"authorize",lambda *a,**k:None)
    monkeypatch.setattr(broadcasts,"one",lambda *a:dict(QueueState=state,ExternalId=external,Attempts=attempts,IdentityId=identity))
    candidate=dict(identity_id=identity,eligible=True,audience_profile={"gender":"Sin dato"},template={},text="Test",phone="573000000000",contact_id=contact,template_record={"ProviderMetadata":'{"material_revision":"version"}'},consent={"ConsentId":str(uuid4()),"VersionNo":1},person={"ControlEpoch":0})
    monkeypatch.setattr(broadcasts,"audience",lambda *a,**k:([candidate],{"RowVersion":b"version"}))
    monkeypatch.setattr(broadcasts,"record_operation",lambda *a:None)
    monkeypatch.setattr(broadcasts,"audit",lambda *a,**k:None)
    monkeypatch.setattr(service,"request",lambda *a,**k:pytest.fail("Retry command must not perform provider IO"))
    review=Review(operation_id=uuid4(),revision=1,reason="Controlled retry",confirmed=True,recipient_ids=[recipient])
    if not allowed:
        with pytest.raises(HTTPException,match="broadcast_retry_only_definitive_unaccepted_failure"):
            service.action(None,str(uuid4()),"retry",review)
        assert writes==[]
    else:
        assert service.action(None,str(uuid4()),"retry",review)["retried"]==1
        assert len(writes)==2 and "State='prepared',CurrentQueueId=NULL" in writes[0][0]
        assert json.loads(writes[0][1][-3])["audience_profile"]=={"gender":"Sin dato"}
        assert all("DELETE" not in sql and "crm_broadcast7.Attempt" not in sql for sql,_ in writes)
