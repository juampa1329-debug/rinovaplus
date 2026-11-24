from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4

from app.institutional import broadcasts
from app.institutional.postgres_dialect import postgres_sql


def test_consent_search_is_scoped_bound_and_paginated_above_500(monkeypatch):
    service = object.__new__(broadcasts.Broadcasts)
    service.settings = SimpleNamespace()
    calls = []

    @contextmanager
    def tx(auth):
        yield None, {}

    def rows(c, sql, *params):
        calls.append((sql, params))
        return [{
            "IdentityId": str(uuid4()), "ContactId": str(uuid4()),
            "ConversationId": str(uuid4()), "ExternalId": "573001234567",
            "Name": "Persona revisada",
        } for _ in range(101)]

    service.tx = tx
    monkeypatch.setattr(broadcasts, "account", lambda *args: None)
    monkeypatch.setattr(broadcasts, "institution", lambda *args: "institution")
    monkeypatch.setattr(broadcasts, "rows", rows)
    monkeypatch.setattr(broadcasts, "consent", lambda *args: None)
    result = service.identities({}, "selected-account", search="Ana %'", offset=600)
    assert len(result["items"]) == 100 and result["has_more"]
    assert result["offset"] == 600
    sql, params = calls[0]
    assert "Ana %'" not in sql and "FETCH NEXT 101 ROWS ONLY" in sql
    assert params == (
        "institution", "selected-account", "Ana %'", "Ana %'", "Ana %'", 600,
    )
    converted = postgres_sql(sql, {
        "crm.Contact": "dbo.CRMContacto",
        "crm_channels2.ExternalIdentity": "dbo.CRMIdentidadExterna",
    })
    assert "CHARINDEX" not in converted
    assert 'strpos(lower(Name COLLATE "default"),lower(%s))' in converted
    assert "OFFSET %s ROWS FETCH NEXT 101 ROWS ONLY" in converted
