from types import SimpleNamespace

from app.institutional import agent_catalog


def test_agent_catalog_excludes_paused_programs_and_only_explicit_admin_listing_includes_them(monkeypatch):
    calls = []
    program = dict(ProgramId=1, Name="Oferta de prueba", Schedule="Diurna", School="Prueba", Authority="declared", Revision=2, Active=False)
    class Cursor:
        def execute(self, sql, *args):
            calls.append(sql)
            return self
        def fetchval(self):
            return 1
    monkeypatch.setattr(agent_catalog, "institution", lambda _: "inst")
    def rows(c, sql, *args):
        calls.append(sql)
        return [] if "Active=1" in sql else [program]
    monkeypatch.setattr(agent_catalog, "rows", rows)
    catalog = agent_catalog.Catalog(SimpleNamespace())
    assert catalog.programs(Cursor())["items"] == []
    result = catalog.programs(Cursor(), include_inactive=True)
    assert result["items"][0]["active"] is False
    assert all("Active=1" in sql for sql in calls[:2])
    assert all("Active=1" not in sql for sql in calls[2:])
