import re
import sqlite3
from contextlib import nullcontext
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pglast import parse_sql

from app.institutional import workspace
from app.institutional.operations_policy import layout
from app.institutional.postgres_dialect import postgres_sql


@pytest.mark.parametrize("area", ["inbox", "clients"])
@pytest.mark.parametrize("query", ["9990000", "3009990000"])
def test_actual_channel_number_matches_a_stale_crm_phone_without_crossing_owner_scope(monkeypatch, area, query):
    inst, contact, conversation = [str(uuid4()) for _ in range(3)]
    captured = []
    class Captured(Exception):
        pass
    class Cursor:
        def execute(self, sql, *params):
            captured.append((sql, params))
            raise Captured
    monkeypatch.setattr(workspace, "authorize", lambda *_: {"UserId": str(uuid4())})
    monkeypatch.setattr(workspace, "revision", lambda *_: "1")
    service = workspace.Workspace.__new__(workspace.Workspace)
    service.profile = SimpleNamespace(ticket={"context": [[1, inst]]})
    service.operational_channels = True
    service.transaction = lambda: nullcontext(Cursor())
    with pytest.raises(Captured):
        service.listing(area, q=query)
    sql, params = captured[0]
    converted = postgres_sql(sql, layout()["tables"])
    parse_sql(converted.replace("%s", "NULL"))
    assert sql.count("?") == len(params)
    match = re.search(r"EXISTS\(SELECT 1 FROM crm_channels2.ExternalIdentity phoneIdentity [^)]*\)", sql)
    assert match
    index = sql[:match.start()].count("?")
    bound = params[index:index+2]
    assert bound == (inst, "%" + query + "%")
    db = sqlite3.connect(":memory:")
    db.executescript("ATTACH ':memory:' AS crm_channels2; CREATE TABLE crm_channels2.ExternalIdentity(InstitutionId TEXT,ContactId TEXT,ConversationId TEXT,ExternalId TEXT)")
    alias = "p" if area == "inbox" else "f"
    select = "SELECT " + match.group() + " FROM (SELECT ? AS ContactId) " + alias + " CROSS JOIN (SELECT ? AS ConversationId) v"
    for owner, person, thread, expected in [
        (inst, contact, conversation, 1), (str(uuid4()), contact, conversation, 0),
        (inst, str(uuid4()), conversation, 0),
        (inst, contact, str(uuid4()), 0 if area == "inbox" else 1),
    ]:
        db.execute("DELETE FROM crm_channels2.ExternalIdentity")
        db.execute("INSERT INTO crm_channels2.ExternalIdentity VALUES(?,?,?,?)", (owner, person, thread, "573009990000"))
        assert db.execute(select, (*bound, contact, conversation)).fetchone()[0] == expected
    db.close()
