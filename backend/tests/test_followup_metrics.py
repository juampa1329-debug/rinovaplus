from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4

from pglast import parse_sql
import pytest

from app.institutional import campaigns
from app.institutional.campaign_metrics import attempts_query
from app.institutional.operations_policy import layout
from app.institutional.postgres_dialect import postgres_sql


@pytest.mark.parametrize("materialized", [True, False])
def test_attempt_scope_and_authenticated_attribution_are_kept_without_correlated_reply_scan(materialized):
    sql = attempts_query(materialized=materialized)
    converted = postgres_sql(sql, layout()["tables"]).replace("%s", "NULL")
    parse_sql(converted)
    assert sql.count("?") == 2
    assert "e.InstitutionId=? AND e.FlowId=?" in sql
    assert "UNION ALL" in sql and "crm_broadcast7.Attempt" in sql
    assert "CurrentQueueId" not in sql
    assert "q.QueueId=b.QueueRef" in sql
    assert "LOWER(CONVERT(varchar(36),q.QueueId))" not in sql
    if materialized:
        assert "chat_links AS MATERIALIZED" in sql
    assert "i.IdentityId=a.IdentityId" in sql
    assert "reply.IntegrationId=a.IntegrationId" in sql
    assert "reply.EventRef COLLATE" in sql and "reply.EventAuthor COLLATE" in sql
    assert "reply.Status='processed'" in sql and "reply.Kind='message'" in sql
    assert "100001" in sql and "EXISTS(" not in sql
    assert ("AS MATERIALIZED" in sql) is materialized


def test_metrics_preserve_failed_attempt_after_retry_and_count_replied_person_once(monkeypatch):
    service = campaigns.Campaigns(SimpleNamespace(ticket={"context": [[1, str(uuid4())]]}, postgres_deployment=True))
    @contextmanager
    def tx(*_):
        yield None, None
    monkeypatch.setattr(service, "tx", tx)
    monkeypatch.setattr(campaigns, "get", lambda *_: {})
    def rows(_c, sql, *_):
        if "GROUP BY Variant,State" in sql:
            return [{"Variant": "A", "Total": 2}]
        return [
            {"Variant": "A", "EnrollmentId": "one", "State": "failed", "ExternalId": None, "Replied": 0},
            {"Variant": "A", "EnrollmentId": "one", "State": "read", "ExternalId": "provider1", "Replied": 1},
            {"Variant": "A", "EnrollmentId": "one", "State": "delivered", "ExternalId": "provider2", "Replied": 1},
            {"Variant": "A", "EnrollmentId": "two", "State": "uncertain", "ExternalId": None, "Replied": 0},
        ]
    monkeypatch.setattr(campaigns, "rows", rows)
    result = service.metrics(None, str(uuid4()))
    assert result["variants"][0] == {"variant": "A", "enrollments": 2, "attempts": 4,
        "accepted": 2, "delivered": 2, "read": 1, "failed": 1, "uncertain": 1,
        "replied": 1, "reply_percent": 50.0}
    assert result["conversion_inferred"] is False
