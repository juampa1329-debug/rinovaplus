from types import SimpleNamespace

import pytest

from app.institutional import comment_private, db
from app.institutional.postgres_dialect import postgres_sql


def test_real_private_reply_attribution_converts_uuid_to_postgres_text(monkeypatch):
    queries = []

    def capture(cursor, statement, *parameters):
        queries.append((statement, parameters))
        return None

    monkeypatch.setattr(db, "institution", lambda _: "institution")
    monkeypatch.setattr(db, "one", capture)
    assert comment_private.incoming_source(
        None, SimpleNamespace(postgres_deployment=True),
        {"Channel": "messenger", "ApplicationId": "app", "ExternalAccountId": "page"},
        "recipient",
    ) is None
    statement, parameters = queries[0]
    tables = {
        "crm_channels2.SendJob": "dbo.CRMCanalInstitucionalEnvioTrabajo",
        "crm_channels2.ProviderOperation": (
            "dbo.CRMCanalInstitucionalOperacionProveedor"
        ),
        "crm_channels2.Integration": "dbo.CRMCanalInstitucionalIntegracion",
        "crm_channels2.ExternalMessage": "dbo.CRMCanalInstitucionalMensajeExterno",
    }
    sql = postgres_sql(statement, tables)
    assert "(j.CommentId)::text" in sql
    assert "CONVERT(" not in sql and "nvarchar" not in sql
    assert sql.count("%s") == len(parameters) == 5
    assert "'recipient'" not in sql


@pytest.mark.parametrize("type_name", ["varchar", "nvarchar", "NVARCHAR"])
def test_uuid_text_conversion_preserves_unicode_literals_and_bound_values(type_name):
    query = (
        f"SELECT CONVERT({type_name}(36),j.CommentId),"
        "N'CONVERT(nvarchar(36),j.CommentId)' WHERE j.CommentId=?"
    )
    assert postgres_sql(query, {}) == (
        "SELECT (j.CommentId)::text,'CONVERT(nvarchar(36),j.CommentId)' "
        "WHERE j.CommentId=%s"
    )
