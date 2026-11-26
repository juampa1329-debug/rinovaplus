"""Short lock ownership without weakening authorization or dispatch fences."""
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import psycopg2
import pytest
from fastapi import HTTPException

from app.institutional import campaign_runtime as runtime
from app.institutional import postgres_rehearsal as postgres


class Busy(psycopg2.Error):
    @property
    def pgcode(self):
        return "55P03"


@pytest.mark.parametrize("write,where,expected", [
    (True, "lock", "storage_busy"),
    (True, "body", "general_storage_unavailable"),
    (False, "body", "general_storage_unavailable"),
])
def test_only_pre_work_lock_timeout_is_classified_as_retryable(monkeypatch, caplog, write, where, expected):
    raw = MagicMock()
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = raw
    raw.fetchone.return_value = ("db", "app", "institution")
    settings = SimpleNamespace(postgres_connect=lambda: conn,
                               connection={"database": "db"}, postgres_user="app",
                               ticket={"context": [[1, "institution"]], "table_map": {}},
                               postgres_columns={})
    monkeypatch.setattr(postgres, "Cursor", lambda *args: raw)
    def execute(sql, *args):
        if where == "lock" and "pg_advisory_xact_lock" in sql:
            raise Busy("PRIVATE SQL/credential must not be logged")
    raw.execute.side_effect = execute
    entered = False
    with pytest.raises(HTTPException) as failure:
        with postgres.transaction(settings, write, anonymous=True):
            entered = True
            raise Busy("PRIVATE SQL/credential must not be logged")
    assert failure.value.detail == expected
    assert entered is (where == "body")
    assert (failure.value.headers or {}).get("Retry-After") == ("1" if where == "lock" else None)
    calls = [c.args[0] for c in raw.execute.call_args_list]
    assert ("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY" in calls) is (not write)
    assert any("pg_advisory_xact_lock(" in sql for sql in calls) is write
    assert not any("pg_advisory_xact_lock_shared" in sql for sql in calls)
    assert "SET LOCAL lock_timeout='3s'" in calls
    assert "PRIVATE" not in caplog.text
    assert "state=55P03" in caplog.text
    conn.close.assert_called_once()


@pytest.mark.parametrize("write", [False, True])
@pytest.mark.parametrize("denied", [False, True])
def test_snapshot_reads_and_serialized_writes_both_require_live_scope_and_authority(monkeypatch, write, denied):
    from app.institutional import auth
    raw, conn = MagicMock(), MagicMock()
    conn.cursor.return_value.__enter__.return_value = raw
    raw.fetchone.return_value = ("db", "app", "institution")
    settings = SimpleNamespace(postgres_connect=lambda: conn,
        connection={"database": "db"}, postgres_user="app",
        ticket={"context": [[1, "institution"]], "table_map": {}}, postgres_columns={})
    monkeypatch.setattr(postgres, "Cursor", lambda *args: raw)
    authority = {"permission": "inbox.read", "token": "private-test-token"}
    token = postgres.request_authority.set(authority)
    checked = Mock(side_effect=HTTPException(403, "permission_denied") if denied else None)
    monkeypatch.setattr(auth, "authorize", checked)
    try:
        if denied:
            with pytest.raises(HTTPException, match="permission_denied"):
                with postgres.transaction(settings, write):
                    pytest.fail("unauthorized work must not begin")
        else:
            with postgres.transaction(settings, write) as cursor:
                assert cursor is raw
                checked.assert_called_once_with(raw, settings, authority, "inbox.read", recent=False)
        assert checked.call_count == 1
        calls = [call.args[0] for call in raw.execute.call_args_list]
        assert any("current_database(), current_user, institutionid" in sql for sql in calls)
        assert any("pg_advisory_xact_lock(" in sql for sql in calls) is write
    finally:
        postgres.request_authority.reset(token)


def test_campaign_future_contexts_release_writer_between_contacts_and_recheck_live_rows(monkeypatch):
    active = []
    guards = []
    selected = [{"EnrollmentId": str(n), "old": True} for n in range(12)]
    @contextmanager
    def tx(_s, write=False, **_kw):
        token = {"write": write, "guards": 0}
        assert not active, "no nested institutional transaction"
        active.append(token)
        try:
            yield token
        finally:
            active.pop()
            assert token["guards"] <= 1
    monkeypatch.setattr(runtime, "transaction", tx)
    monkeypatch.setattr(runtime, "institution", lambda _: "institution")
    monkeypatch.setattr(runtime, "enabled", lambda *_: True)
    monkeypatch.setattr(runtime, "rows", lambda *_: selected)
    def live(c, sql, institution, enrollment):
        assert c["write"]
        assert "State IN('waiting','queued')" in sql
        # Another transaction already cancelled this execution.
        return None if enrollment == "3" else {"EnrollmentId": enrollment, "live": True}
    monkeypatch.setattr(runtime, "one", live)
    def guard(c, s, row):
        assert c["write"] and row.get("live") and "old" not in row
        c["guards"] += 1
        guards.append(row["EnrollmentId"])
    monkeypatch.setattr(runtime, "guard", guard)
    assert runtime.Worker(SimpleNamespace()).review_pending() is False
    assert guards == [str(n) for n in range(12) if n != 3]


def test_campaign_changed_future_context_still_stops_before_due_work(monkeypatch):
    @contextmanager
    def tx(*_args, **_kwargs):
        yield Mock()
    monkeypatch.setattr(runtime, "transaction", tx)
    monkeypatch.setattr(runtime, "institution", lambda _: "institution")
    monkeypatch.setattr(runtime, "enabled", lambda *_: True)
    monkeypatch.setattr(runtime, "rows", lambda *_: [{"EnrollmentId":"run"}])
    current = {"EnrollmentId":"run", "State":"waiting"}
    monkeypatch.setattr(runtime, "one", lambda *_: current)
    monkeypatch.setattr(runtime, "guard", Mock(side_effect=HTTPException(409,"campaign_handoff_changed")))
    stop = Mock()
    monkeypatch.setattr(runtime, "stop", stop)
    worker = runtime.Worker(SimpleNamespace())
    worker.maintenance = Mock(side_effect=AssertionError("must stop first"))
    assert worker.once() is True
    assert stop.call_args.args[-2:] == (current, "campaign_handoff_changed")


def test_campaign_maintenance_releases_lock_between_independent_stages(monkeypatch):
    tokens, active = [], []
    @contextmanager
    def tx(_s, write=False, **_kw):
        assert not active
        token = {"write":write, "stages":[]}
        tokens.append(token)
        active.append(token)
        try:
            yield token
        finally:
            active.pop()
    monkeypatch.setattr(runtime, "transaction", tx)
    monkeypatch.setattr(runtime, "institution", lambda _: "institution")
    monkeypatch.setattr(runtime, "enabled", lambda *_: True)
    monkeypatch.setattr(runtime, "rows", lambda *_: [{"EventType":"inactivity"},{"EventType":"message_in"}])
    worker = runtime.Worker(SimpleNamespace())
    def stage(name):
        def run(c):
            assert c["write"]
            c["stages"].append(name)
        return run
    worker.observe, worker.inactivity, worker.triggers = [stage(n) for n in ("observe","inactivity","triggers")]
    worker.maintenance()
    assert [t["stages"] for t in tokens] == [[],["observe"],["inactivity"],["triggers"]]
