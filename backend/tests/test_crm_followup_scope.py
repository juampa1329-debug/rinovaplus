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
