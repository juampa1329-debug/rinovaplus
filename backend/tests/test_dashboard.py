"""Dashboard boundary fixtures. Native aggregate SQL is verified separately live."""
import json
import re
from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.institutional import dashboard
from app.institutional import operations_policy
from app.institutional.postgres_dialect import postgres_sql


def test_bogota_window_crosses_utc_midnight_without_an_extra_local_day():
    now = datetime(2026, 11, 20, 2, 0, tzinfo=timezone.utc)
    start, end = dashboard.window(7, now)
    assert start.isoformat() == "2026-11-13T05:00:00+00:00"
    assert end == now


def test_restricted_or_disabled_modules_never_query_private_aggregate_tables(monkeypatch):
    class Cursor:
        def execute(self, sql, *args):
            assert "Section='modules'" in sql
            return self

        def fetchval(self):
            return json.dumps({"enabled": {"overview": True, "inbox": True, "clients": False}})

        def native(self, *args):
            pytest.fail("private aggregate queried without permission/module")

    @contextmanager
    def transaction(*args, **kwargs):
        yield Cursor()

    monkeypatch.setattr(dashboard, "transaction", transaction)
    monkeypatch.setattr(dashboard, "authorize", lambda *args: {"Actions": '["crm.read"]'})
    settings = SimpleNamespace(ticket={"context": [["id", "00000000-0000-0000-0000-000000000001"]]})
    data = dashboard.read(settings, 7)
    assert data['inbox'] is data['comments'] is data['followups'] is None
    assert set(data) == {'generated_at', 'start', 'end', 'timezone', 'days', 'inbox', 'followups', 'comments'}


def test_permission_gate_needs_both_capability_and_enabled_module():
    assert dashboard.permitted(['crm.read'], {'clients': True}, 'crm.read', 'clients')
    assert not dashboard.permitted([], {'clients': True}, 'crm.read', 'clients')
    assert not dashboard.permitted(['crm.read'], {'clients': False}, 'crm.read', 'clients')


def test_auth_failure_stops_before_reading_any_data(monkeypatch):
    @contextmanager
    def transaction(*args, **kwargs):
        raise HTTPException(401, "session_required")
        yield
    monkeypatch.setattr(dashboard, "transaction", transaction)
    with pytest.raises(HTTPException) as error:
        dashboard.read(SimpleNamespace(), 7)
    assert error.value.status_code == 401


def test_all_dashboard_statements_parse_as_postgresql_including_daily_buckets(monkeypatch):
    # Development-only parser, not a runtime dependency or a live database claim.
    parser = pytest.importorskip("pglast")
    mapping = operations_policy.layout()['tables']
    parsed = []
    class Cursor:
        def native(self, sql, *args):
            self.sql = sql
            indexes = iter(range(1, 100))
            parser.parse_sql(re.sub(r'%s', lambda _: '$'+str(next(indexes)), sql))
            parsed.append(sql)
            return self
        def execute(self, sql, *args):
            return self.native(postgres_sql(sql, mapping), *args)
        def fetchval(self):
            return json.dumps({'enabled': {'overview': True, 'inbox': True, 'clients': True}})
        def fetchone(self):
            return (0, 0, 0, 0, 0) if 'WITH activity AS' in self.sql else (0, 0, 0) if 'FILTER' in self.sql else (0,)
        def fetchall(self):
            return []
    @contextmanager
    def transaction(*args, **kwargs):
        yield Cursor()
    monkeypatch.setattr(dashboard, 'transaction', transaction)
    monkeypatch.setattr(dashboard, 'authorize', lambda *args: {'Actions': '["crm.read","inbox.read"]'})
    data = dashboard.read(SimpleNamespace(ticket={'table_map': mapping, 'context': [[1, '00000000-0000-0000-0000-000000000001']]}))
    assert len(parsed) == 7
    assert data['inbox']['conversations'] == 0
