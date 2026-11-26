from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pglast import parse_sql

from app.institutional import broadcast_dispatch, postgres_rehearsal, processing_lease
from app.institutional.operations_policy import layout
from app.institutional.postgres_dialect import postgres_sql


@pytest.mark.parametrize('waits', [0, 1, 2])
def test_lock_frontier_waits_without_repeating_business_work(monkeypatch, waits):
    entries, work, exits = [], [], []
    @contextmanager
    def acquire(*args, **kwargs):
        entries.append(kwargs)
        if len(entries) <= waits:
            raise HTTPException(503, 'storage_busy')
        try:
            yield 'authorized-live-cursor'
        finally:
            exits.append(True)
    monkeypatch.setattr(postgres_rehearsal, '_transaction', acquire)
    with postgres_rehearsal.transaction(None, True, anonymous=True) as c:
        work.append(c)
    assert len(entries) == waits + 1
    assert work == ['authorized-live-cursor'] and exits == [True]


def test_lock_frontier_stops_after_three_failures(monkeypatch):
    calls = []
    @contextmanager
    def acquire(*args, **kwargs):
        calls.append(True)
        raise HTTPException(503, 'storage_busy')
        yield
    monkeypatch.setattr(postgres_rehearsal, '_transaction', acquire)
    with pytest.raises(HTTPException, match='storage_busy'):
        with postgres_rehearsal.transaction(None, True):
            pytest.fail('business work cannot start')
    assert len(calls) == 3


@pytest.mark.parametrize('code,status,write', [('storage_busy', 503, False), ('permission_denied', 403, True), ('general_storage_unavailable', 503, True)])
def test_unknown_outcome_and_authority_failures_are_not_retried(monkeypatch, code, status, write):
    calls = []
    @contextmanager
    def acquire(*args, **kwargs):
        calls.append(True)
        raise HTTPException(status, code)
        yield
    monkeypatch.setattr(postgres_rehearsal, '_transaction', acquire)
    with pytest.raises(HTTPException, match=code):
        with postgres_rehearsal.transaction(None, write):
            pytest.fail('unauthorized work')
    assert len(calls) == 1


def test_body_failure_is_never_replayed_even_when_named_storage_busy(monkeypatch):
    calls, work = [], []
    @contextmanager
    def acquire(*args, **kwargs):
        calls.append(True)
        yield 'live'
    monkeypatch.setattr(postgres_rehearsal, '_transaction', acquire)
    with pytest.raises(HTTPException, match='storage_busy'):
        with postgres_rehearsal.transaction(None, True):
            work.append(True)
            raise HTTPException(503, 'storage_busy')
    assert calls == [True] and work == [True]


@pytest.mark.parametrize('left,expected', [(240, 180), (90, 90), (31, 31)])
def test_renewal_preserves_ownership_and_total_deadline(monkeypatch, left, expected):
    settings = SimpleNamespace(ticket={'context': [[1, str(uuid4())]]})
    c = Mock(rowcount=1)
    @contextmanager
    def tx(*args, **kwargs):
        assert args == (settings, True) and kwargs == {'anonymous': True}
        yield c
    monkeypatch.setattr(processing_lease, 'transaction', tx)
    monkeypatch.setattr(processing_lease, 'monotonic', lambda: 100)
    processing_lease.renew(settings, 'operation', 'lease', 100 + left)
    sql, seconds, institution, operation, lease = c.execute.call_args.args
    assert (seconds, operation, lease) == (expected, 'operation', 'lease')
    assert "Status='running' AND LeaseId=?" in sql and 'LeaseUntil>SYSUTCDATETIME()' in sql
    parse_sql(postgres_sql(sql, layout()['tables']).replace('%s', 'NULL'))


def test_expired_or_replaced_lease_cannot_be_resurrected(monkeypatch):
    settings = SimpleNamespace(ticket={'context': [[1, str(uuid4())]]})
    c = Mock(rowcount=0)
    @contextmanager
    def tx(*args, **kwargs):
        yield c
    monkeypatch.setattr(processing_lease, 'transaction', tx)
    monkeypatch.setattr(processing_lease, 'monotonic', lambda: 100)
    with pytest.raises(HTTPException, match='gemini_whatsapp_claim_changed'):
        processing_lease.renew(settings, 'operation', 'old-lease', 200)


def test_processing_deadline_stops_before_any_new_io(monkeypatch):
    tx = Mock(side_effect=AssertionError('no IO after deadline'))
    monkeypatch.setattr(processing_lease, 'transaction', tx)
    monkeypatch.setattr(processing_lease, 'monotonic', lambda: 171)
    with pytest.raises(HTTPException, match='ai_processing_deadline'):
        processing_lease.renew(None, 'operation', 'lease', 200)
    tx.assert_not_called()


def test_receipt_reconciliation_uses_persisted_authenticated_external_id():
    from app.institutional.channel_events import normalize
    event = normalize('meta', {'entry': [{'id': 'waba', 'changes': [{'field': 'messages', 'value': {
        'messaging_product': 'whatsapp', 'metadata': {'phone_number_id': 'account'},
        'statuses': [{'id': 'wamid.sent', 'status': 'delivered', 'recipient_id': '573000000000', 'timestamp': '1795734000'}]
    }}]}]})[0]
    assert event['kind'] == 'status' and event['external'] == 'wamid.sent'
    c = Mock()
    settings = SimpleNamespace(ticket={'context': [[1, str(uuid4())]]})
    broadcast_dispatch.reconcile_receipts(c, settings)
    sql = c.execute.call_args.args[0]
    assert 'q.ExternalId=e.ProviderEventId' in sql
    assert 'JSON_VALUE' not in sql and "Status='quarantined'" in sql
    assert 'q.InstitutionId=e.InstitutionId' in sql and 'q.IntegrationId=e.IntegrationId' in sql
    parse_sql(postgres_sql(sql, layout()['tables']).replace('%s', 'NULL'))
