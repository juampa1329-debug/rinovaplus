import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pglast import parse_sql
from pydantic import ValidationError

from app.institutional import campaign_runtime as runtime, campaigns, contact_preference
from app.institutional.campaign_models import Flow
from app.institutional.operations_policy import layout
from app.institutional.postgres_dialect import postgres_sql


@pytest.mark.parametrize("quiet,exit_response,allowed", [(True, True, True), (False, True, False), (True, False, False)])
def test_followup_requires_configured_silent_hours_and_stop_on_response(quiet, exit_response, allowed):
    value = dict(integration_id=str(uuid4()), followup_only=True, quiet_hours={"enabled": quiet},
                 exit_on_response=exit_response, steps=[{"kind": "wait", "wait_minutes": 480}])
    if allowed:
        assert Flow(**value).followup_only
    else:
        with pytest.raises(ValidationError):
            Flow(**value)


@pytest.mark.parametrize("followup", [False, True])
def test_inactivity_only_uses_authenticated_existing_conversations_when_selected(monkeypatch, followup):
    settings = SimpleNamespace(ticket={"context": [[1, str(uuid4())]]})
    trigger = {"Document": json.dumps({"flow_id": "flow", "idle_minutes": 480}), "RecordId": str(uuid4()), "CurrentVersion": 1}
    monkeypatch.setattr(runtime, "rows", lambda *_: [trigger])
    monkeypatch.setattr(runtime, "get", lambda *_: {"Document": json.dumps({"followup_only": followup, "integration_id": str(uuid4())})})
    monkeypatch.setattr(runtime, "authority", lambda *_: None)
    def inspect(_c, sql, *args):
        assert sql.count("?") == len(args)
        parse_sql(postgres_sql(sql, layout()["tables"]).replace("%s", "NULL"))
        assert ("inbound.ActorKind='external'" in sql) is followup
        assert ("received.CreatedAt<=q.CreatedAt" in sql) is followup
        assert "CROSS APPLY" not in sql and "GROUP BY q.QueueId,q.IdentityId" in sql
        assert "later.Sequence>anchor.Sequence" in sql
        assert "receipt.ProviderEventId COLLATE" in sql
        return None
    monkeypatch.setattr(runtime, "one", inspect)
    runtime.Worker(settings).inactivity(None)


def test_no_contact_status_covers_canonical_aliases_without_writes(monkeypatch):
    settings = SimpleNamespace(ticket={"context": [[1, str(uuid4())]]})
    queries = []
    class Cursor:
        def execute(self, sql, *args):
            assert sql.count("?") == len(args)
            parse_sql(postgres_sql(sql, layout()["tables"]).replace("%s", "NULL"))
            assert "e.Kind='opt_out'" in sql and "grantor.CreatedAt>e.CreatedAt" in sql
            assert "COALESCE(g.TargetContactId,i.ContactId)" in sql
            queries.append(sql)
            return self
        def fetchone(self):
            return (1,)
    assert contact_preference.blocked(Cursor(), settings, str(uuid4()))
    assert len(queries) == 1 and queries[0].startswith("SELECT")


@pytest.mark.parametrize("incoming,blocked,expected", [(0,False,"genuine_incoming_required"),(1,True,"no_contact"),(1,False,None)])
def test_send_guard_rechecks_incoming_and_no_contact_without_changing_consent(monkeypatch, incoming, blocked, expected):
    monkeypatch.setattr(campaigns, "marketing_allowed", lambda *_: True)
    monkeypatch.setattr(campaigns, "filters_for", lambda *_: [])
    monkeypatch.setattr(contact_preference, "blocked", lambda *_: blocked)
    p = {"IntegrationId": "account", "ControlMode": "ai", "ConversationState": "open", "CanonicalContactId": "contact", "IncomingCount": incoming, "LastIncomingAt": incoming or None}
    reasons = campaigns.reasons(None, None, {"integration_id":"account", "followup_only": True}, p)
    assert reasons == ([expected] if expected else [])


@pytest.mark.parametrize("hours,incoming,basis,blocked,allowed", [(1,1,"customer_request",False,True),(25,1,"customer_request",False,False),(1,0,"customer_request",False,False),(1,1,"marketing",False,False),(1,1,"customer_request",True,False)])
def test_customer_requested_support_never_becomes_an_out_of_window_marketing_permission(monkeypatch,hours,incoming,basis,blocked,allowed):
    from datetime import datetime,timedelta
    moment=datetime(2026,11,24,17)
    monkeypatch.setattr(campaigns,"now",lambda:moment)
    monkeypatch.setattr(campaigns,"marketing_allowed",lambda *_:False)
    monkeypatch.setattr(campaigns,"filters_for",lambda *_:[])
    monkeypatch.setattr(contact_preference,"blocked",lambda *_:blocked)
    p={"IntegrationId":"account","ControlMode":"ai","ConversationState":"open","CanonicalContactId":"contact","IncomingCount":incoming,"LastIncomingAt":moment-timedelta(hours=hours)}
    doc={"integration_id":"account","followup_only":True,"contact_basis":basis}
    assert (not campaigns.reasons(None,None,doc,p)) is allowed
    p["ControlMode"]="human"
    assert "human_control" in campaigns.reasons(None,None,doc,p)


def test_request_basis_cannot_be_selected_for_cold_outreach():
    with pytest.raises(ValidationError):
        Flow(integration_id=str(uuid4()),contact_basis="customer_request",steps=[{"kind":"wait"}])


def test_customer_window_crm_preparation_binds_null_consent_without_provider_io(monkeypatch):
    from datetime import datetime,timedelta
    from app.institutional import campaign_chat,channel_operations,channel_outbox,broadcasts
    moment=datetime(2026,11,24,17)
    monkeypatch.setattr(campaigns,"now",lambda:moment)
    monkeypatch.setattr(campaign_chat,"now",lambda:moment)
    identity,account,conversation,flow_id,enrollment,step_id=[str(uuid4()) for _ in range(6)]
    monkeypatch.setattr(campaign_chat,"links",lambda *_:[])
    monkeypatch.setattr(channel_operations,"account",lambda *_:{"IntegrationId":account,"Channel":"whatsapp","RowVersion":b"version"})
    monkeypatch.setattr(campaign_chat,"capability",lambda *_:None)
    monkeypatch.setattr(campaign_chat,"one",lambda *_:{"Enabled":True,"NextAt":moment-timedelta(seconds=1),"WindowAt":moment-timedelta(days=2),"Reserved":0,"DailyLimit":100,"Revision":1})
    monkeypatch.setattr(campaign_chat,"parts",lambda *_:[{"kind":"text","text":"¿Qué duda podemos resolver?"}])
    monkeypatch.setattr(broadcasts,"consent",lambda *_:None)
    monkeypatch.setattr(campaign_chat,"authority",lambda *_:{"UserId":"operator"})
    monkeypatch.setattr(campaign_chat,"event",lambda *_a,**_k:None)
    captured=[]
    monkeypatch.setattr(channel_outbox,"enqueue",lambda _c,_s,_i,_a,_op,payload,**_kw:captured.append(payload) or str(uuid4()))
    class Cursor:
        def execute(self,sql,*args):
            assert sql.count("?")==len(args)
            parse_sql(postgres_sql(sql,layout()["tables"]).replace("%s","NULL"))
            return self
    settings=SimpleNamespace(ticket={"context":[[1,str(uuid4())]]})
    p={"IdentityId":identity,"ConversationId":conversation,"ControlEpoch":2,"IncomingCount":1,"LastIncomingAt":moment-timedelta(hours=2)}
    doc={"integration_id":account,"channel":"whatsapp","followup_only":True,"contact_basis":"customer_request","steps":[{"kind":"send"}],"quiet_hours":{"enabled":False}}
    campaign_chat.prepare(Cursor(),settings,{"RecordId":flow_id,"Name":"Seguimiento","ActorId":"operator"},doc,{"StepIndex":0,"Variant":"A","DueAt":moment,"EnrollmentId":enrollment},{"StepId":step_id},p)
    assert len(captured)==1 and captured[0]["consentVersion"] is None
    assert captured[0]["contactBasis"]=="customer_request"
