import json
from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4

from pglast import parse_sql
import pytest

from app.institutional import campaigns, contact_preference
from app.institutional.operations_policy import layout
from app.institutional.postgres_dialect import postgres_sql


def validate(sql, args):
    assert sql.count("?") == len(args)
    parse_sql(postgres_sql(sql, layout()["tables"]).replace("%s", "NULL"))


def test_no_contact_list_is_canonical_deduplicated_and_only_reads_requests(monkeypatch):
    def rows(c, sql, *args):
        validate(sql, args)
        assert "UNION" in sql and "UNION ALL" not in sql
        assert "COALESCE(g.TargetContactId,i.ContactId)" in sql
        assert "e.Kind='opt_out'" in sql
        assert "grantor.CreatedAt>e.CreatedAt" in sql
        assert "revoked" not in sql and "INSERT" not in sql
        assert args[-1] == 25
        return [{"ContactId": str(uuid4()), "Name": "Ejemplo", "Phone": "", "Stage": "Seguimiento"}] * 26
    monkeypatch.setattr(contact_preference.db, "rows", rows)
    settings = SimpleNamespace(ticket={"context": [[1, str(uuid4())]]})
    result = contact_preference.no_contact_list(None, settings, "nombre", 25)
    assert len(result["items"]) == 25 and result["has_more"] and result["read_only"]


@pytest.mark.parametrize("state,index,expected", [
    ("waiting", 1, "36 horas"), ("queued", 2, "36 horas"),
    ("completed", 2, None), ("cancelled", 1, None), ("waiting", 3, None),
])
def test_next_message_uses_frozen_version_not_current_document(state, index, expected):
    doc = {"steps": [{"kind": "send", "name": "8 horas"},
                     {"kind": "wait"}, {"kind": "send", "name": "36 horas"}]}
    assert campaigns.next_message_name({"State": state, "StepIndex": index,
                                        "VersionDocument": json.dumps(doc)}) == expected


def test_run_list_filters_whole_database_before_pagination_and_preserves_history(monkeypatch):
    settings = SimpleNamespace(ticket={"context": [[1, str(uuid4())]]})
    record = {"Document": json.dumps({"steps": [{"kind": "send"}, {"kind": "wait"}, {"kind": "send"}]}), "CurrentVersion": 3}
    class Cursor:
        def execute(self, sql, *args):
            validate(sql, args)
            assert "r.StepIndex>=?" in sql and "r.State IN" in sql
            assert args[-3:] == (3, 1, 2)
            return self
        def fetchval(self):
            return 0
    @contextmanager
    def tx(*args):
        yield Cursor(), None
    monkeypatch.setattr(campaigns, "get", lambda *_: record)
    monkeypatch.setattr(campaigns, "public", lambda _: {})
    service = campaigns.Campaigns(settings)
    monkeypatch.setattr(service, "tx", tx)
    def rows(c, sql, *args):
        validate(sql, args)
        assert "v.VersionNo=r.VersionNo" in sql
        assert args[-4:] == (3, 1, 2, 100)
        return []
    monkeypatch.setattr(campaigns, "rows", rows)
    result = service.runs(None, str(uuid4()), 100, "Persona", "waiting", 2)
    assert result["items"] == [] and len(result["lists"]) == 2
