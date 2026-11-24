from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.institutional import channel_outbox as outbox
from app.institutional import channel_reservations as quota


def harness(monkeypatch, *, status="released", total=0, **changes):
    integration, operation, reservation = [str(uuid4()) for _ in range(3)]
    previous = {
        "ReservationId": reservation, "IntegrationId": integration,
        "Status": status, "Action": "outbound", "Units": 1,
    }
    job = {
        "IntegrationId": integration, "OperationId": operation, "State": "queued",
        "ExternalId": None, "LeaseId": None, "LeaseUntil": None,
        "LastErrorCode": "broadcast_cadence_wait", **changes,
    }
    provider = {"Status": "pending", "ResultCode": "broadcast_cadence_wait"}

    class Cursor:
        def __init__(self):
            self.writes = []
            self.increments = 0
            self.rowcount = 0

        def execute(self, sql, *params):
            if sql.startswith("UPDATE crm_channels2.QuotaReservation"):
                self.rowcount = int(previous["Status"] == "released")
                if self.rowcount:
                    previous["Status"] = "reserved"
            if sql.startswith(("UPDATE", "INSERT")):
                self.writes.append(sql)
            return self

        def fetchval(self):
            return total

        def native(self, sql, *params):
            self.increments += 1
            return self

    c = Cursor()
    monkeypatch.setattr(quota, "institution", lambda _: "institution")
    monkeypatch.setattr(outbox, "institution", lambda _: "institution")
    monkeypatch.setattr(outbox, "setting", lambda *args: {
        "document": {"daily_messages": 100},
    })
    monkeypatch.setattr(outbox, "one", lambda *args: None)
    monkeypatch.setattr(quota, "one", lambda _, sql, *args:
                        previous if "QuotaReservation" in sql else provider)
    return c, job, previous, provider, SimpleNamespace(postgres_profile=True)


def test_known_unsent_cadence_wait_reuses_one_reservation_and_counts_quota(monkeypatch):
    c, job, previous, _, settings = harness(monkeypatch)
    assert outbox.reserve(c, settings, job) == previous["ReservationId"]
    assert previous["Status"] == "reserved" and c.increments == 1
    assert len(c.writes) == 1
    assert "DayUtc=CONVERT(date,SYSUTCDATETIME())" in c.writes[0]
    assert not any(sql.startswith("INSERT") for sql in c.writes)
    with pytest.raises(HTTPException):
        outbox.reserve(c, settings, job)
    assert c.increments == 1


@pytest.mark.parametrize("status", ["reserved", "committed", "uncertain"])
def test_effectful_or_inflight_reservations_are_never_reused(monkeypatch, status):
    c, job, _, _, settings = harness(monkeypatch, status=status)
    with pytest.raises(HTTPException, match="outbound_reservation_review_required"):
        outbox.reserve(c, settings, job)
    assert c.writes == [] and c.increments == 0


@pytest.mark.parametrize("changes", [
    {"State": "uncertain"}, {"ExternalId": "wamid.accepted"},
    {"LeaseId": str(uuid4())}, {"LastErrorCode": "provider_result_unknown"},
])
def test_only_a_known_pre_provider_wait_can_be_restored(monkeypatch, changes):
    c, job, _, _, settings = harness(monkeypatch, **changes)
    with pytest.raises(HTTPException):
        outbox.reserve(c, settings, job)
    assert c.writes == [] and c.increments == 0


def test_daily_budget_still_blocks_before_reactivating_reservation(monkeypatch):
    c, job, previous, _, settings = harness(monkeypatch, total=100)
    with pytest.raises(HTTPException, match="outbound_budget_exhausted"):
        outbox.reserve(c, settings, job)
    assert previous["Status"] == "released" and c.writes == []


def test_provider_operation_must_confirm_same_known_wait(monkeypatch):
    c, job, _, provider, settings = harness(monkeypatch)
    provider["ResultCode"] = "provider_result_unknown"
    with pytest.raises(HTTPException):
        outbox.reserve(c, settings, job)
    assert c.writes == [] and c.increments == 0
